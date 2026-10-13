"""Collecteur quotidien : casablanca-bourse.com.

Usage : python -m bvcsurv.live [--no-db] [--html FICHIER] [--actions-html FICHIER]

Chaque exécution :
1. télécharge la page d'accueil (HTML rendu côté serveur) et la page
   /live-market/actions (JSON intégré : ouverture, plus haut, plus bas, dernier
   cours, volume et quantité de chaque valeur, statut de la séance) ;
2. archive le HTML brut compressé dans data/live/raw/ (pour pouvoir relire
   les pages si le parseur change) ;
3. extrait cours, variations, indices, tops et contrats à terme ;
4. écrit un instantané JSON par séance dans data/live/sessions/ ;
5. si DATABASE_URL est défini, insère ou met à jour la base PostgreSQL.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from . import DATA
from .http import get, session
from .parsing import fr_date, fr_number
from .valeurs import settings

URL = "https://www.casablanca-bourse.com/fr"
ACTIONS_URL = "https://www.casablanca-bourse.com/live-market/actions"
LIVE = DATA / "live"


def _txt(el) -> str:
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def parse_home(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    date_el = soup.find(id="current-date-1") or soup.find(class_="date-text")
    status_el = soup.find(id="market-status-1") or soup.find(class_="market-status")
    session_date = fr_date(_txt(date_el))
    status = _txt(status_el)

    # Bandeau défilant : toutes les valeurs cotées.
    quotes = []
    for li in soup.select("ul#ticker > li"):
        name = _txt(li.find(class_="ticker"))
        price = fr_number(_txt(li.find(class_="stockprice")))
        var_el = li.find(class_="stockpricevar")
        var = fr_number(_txt(var_el)) if var_el else 0.0
        classes = var_el.get("class", []) if var_el else []
        if "decrease" in classes:
            var = -abs(var)
        elif "increase" in classes:
            var = abs(var)
        else:  # « nocrease » ou absence de div : variation nulle
            var = var or 0.0
        if name:
            quotes.append({"name": name, "price": price, "var_pct": var})

    # Blocs du carrousel : MASI 20, MASI, capitalisation, volume global.
    blocks = {}
    for b in soup.select("div.data-block"):
        title = _txt(b.find(class_="block-title")).upper()
        value = fr_number(_txt(b.find(class_="main-value")))
        var_el = b.find(class_="variation-value")
        var = fr_number(_txt(var_el)) if var_el and "%" in _txt(var_el) else None
        if title and title not in blocks:
            blocks[title] = {"value": value, "var_pct": var}

    indices = {k: blocks[k] for k in ("MASI", "MASI 20") if k in blocks}
    capitalisation = blocks.get("CAPITALISATION", {}).get("value")
    volume_global = blocks.get("VOLUME GLOBAL", {}).get("value")

    # Tableaux « Marché au comptant » (volume, hausses, baisses) et « Marché à Terme ».
    tops, futures = [], []
    for dash in soup.select("div.dashboard-container"):
        market = _txt(dash.find(class_="market-title")).lower()
        for pane in dash.select("div.tab-pane"):
            kind = pane.get("id", "")
            for rank, tr in enumerate(pane.select("tbody tr"), start=1):
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                inst = _txt(tds[0])
                if "terme" in market:
                    futures.append({
                        "contract": inst,
                        "price": fr_number(_txt(tds[1])),
                        "var_pct": fr_number(_txt(tds[2])) if len(tds) > 2 else None,
                    })
                elif kind == "volume":
                    tops.append({"kind": "volume", "rank": rank, "name": inst,
                                 "value": fr_number(_txt(tds[1]))})
                elif kind in ("hausses", "baisses"):
                    tops.append({"kind": kind, "rank": rank, "name": inst,
                                 "price": fr_number(_txt(tds[1])),
                                 "value": fr_number(_txt(tds[2])) if len(tds) > 2 else None})

    links = sorted({a["href"] for a in soup.find_all("a", href=True)
                    if "/sites/default/files/pemetteur/" in a["href"]})

    return {
        "session_date": session_date.isoformat(),
        "market_status": status,
        "closed": is_closed_text(status),
        "indices": indices,
        "capitalisation_mad": capitalisation,
        "volume_global_mad": volume_global,
        "quotes": quotes,
        "tops": tops,
        "futures": futures,
        "communique_links": links,
    }


def is_closed_text(status: str) -> bool:
    s = status.lower()
    return "ferm" in s or "clôtur" in s or "clotur" in s


def parse_actions(html: str) -> tuple[str | None, list[dict]]:
    """Statut de séance (« open » ou « closed ») et détail des valeurs de /live-market/actions."""
    lm = settings(html)["live_market"]
    stocks = []
    for a in lm["actions"]:
        stocks.append({
            "ticker": a["symbol"].strip(),
            "status": a["statut"]["fr"],          # T traité, NT non traité, S suspendu
            "open": a.get("ouverture"),
            "high": a.get("plusHaut"),
            "low": a.get("plusBas"),
            "last": a.get("dernierCours"),
            "reference": a.get("reference"),
            "var_pct": a.get("variation"),
            "volume_mad": a.get("volume"),
            "quantity": a.get("quantite"),
            "trades": a.get("nbTransactions"),
            "capitalisation_mad": a.get("capitalisation"),
            "shares": a.get("nombreTitres"),
        })
    return (lm.get("session") or {}).get("status"), stocks


def fingerprint(snap: dict) -> str:
    key = json.dumps([(q["name"], q["price"]) for q in snap["quotes"]], sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def save_snapshot(snap: dict, html: str, fetched_at: datetime,
                  actions_html: str | None = None) -> tuple[str, bool]:
    """Archive le HTML, écrit le JSON de la séance. Retourne (chemin, écrit ?)."""
    d = snap["session_date"]
    raw = LIVE / "raw" / d
    raw.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw / f"{fetched_at:%H%M%S}Z.html.gz", "wt", encoding="utf-8") as f:
        f.write(html)
    if actions_html:
        with gzip.open(raw / f"{fetched_at:%H%M%S}Z_actions.html.gz", "wt", encoding="utf-8") as f:
            f.write(actions_html)

    sessions = LIVE / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    path = sessions / f"{d}.json"

    # Séance précédente : si les cours sont identiques, la page n'a sans doute
    # pas été mise à jour (jour férié) ; on le signale sans rien perdre.
    prev = sorted(p for p in sessions.glob("*.json") if p.stem < d)
    snap["fingerprint"] = fingerprint(snap)
    snap["same_prices_as_previous_session"] = bool(
        prev and json.loads(prev[-1].read_text()).get("fingerprint") == snap["fingerprint"]
    )
    snap["fetched_at_utc"] = fetched_at.isoformat(timespec="seconds")

    if path.exists():
        old = json.loads(path.read_text())
        # Ne jamais remplacer un instantané de clôture par un instantané intrajournalier.
        if old.get("closed") and not snap["closed"]:
            return str(path), False
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=1))
    return str(path), True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-db", action="store_true", help="ne pas écrire dans PostgreSQL")
    ap.add_argument("--html", help="relire un fichier HTML local au lieu du site")
    ap.add_argument("--actions-html", help="relire une page /live-market/actions locale")
    args = ap.parse_args(argv)

    fetched_at = datetime.now(timezone.utc)
    s = session()
    if args.html:
        html = open(args.html, encoding="utf-8").read()
    else:
        html = get(s, URL, timeout=60).text

    snap = parse_home(html)
    n = len(snap["quotes"])
    if n < 50 or "MASI" not in snap["indices"]:
        print(f"ERREUR : page incomplète ({n} valeurs, indices={list(snap['indices'])})", file=sys.stderr)
        return 2

    # Page des actions : complément (OHLC et volume par valeur). Son échec ne bloque pas la collecte.
    actions_html, api_status, stocks = None, None, None
    try:
        if args.actions_html:
            actions_html = open(args.actions_html, encoding="utf-8").read()
        elif not args.html:
            actions_html = get(s, ACTIONS_URL, timeout=60).text
        if actions_html:
            api_status, stocks = parse_actions(actions_html)
    except Exception as e:  # noqa: BLE001
        print(f"ATTENTION : page des actions inutilisable ({type(e).__name__}: {e})", file=sys.stderr)
    snap["api_session_status"] = api_status
    snap["stocks"] = stocks
    # Deux sources pour la clôture : le texte de la page d'accueil et l'indicateur de la page des actions.
    snap["closed"] = snap["closed"] or api_status == "closed"

    path, written = save_snapshot(snap, html, fetched_at, actions_html)
    masi = snap["indices"]["MASI"]
    print(f"séance {snap['session_date']} | {snap['market_status']} (page des actions : {api_status}) | "
          f"{n} valeurs, détail de {len(stocks or [])} | "
          f"MASI {masi['value']} ({masi['var_pct']:+.2f} %) | {'écrit' if written else 'conservé'} {path}")
    if snap["same_prices_as_previous_session"]:
        print("ATTENTION : cours identiques à la séance précédente (jour férié ?)")

    if not args.no_db and os.environ.get("DATABASE_URL") and written:
        from .db import connect, upsert_live
        with connect() as conn:
            upsert_live(conn, snap)
        print("base PostgreSQL mise à jour")
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sys.exit(main())
