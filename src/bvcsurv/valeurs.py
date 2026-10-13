"""Référentiel des valeurs : secteur, compartiment, nombre de titres, appartenance au MASI 20.

Usage :
  python -m bvcsurv.valeurs fetch   # site de la Bourse -> data/ref/valeurs.csv
  python -m bvcsurv.valeurs load    # CSV -> table instruments (DATABASE_URL)

Sources (pages publiques, données intégrées au HTML) :
- /live-market/actions : bloc JSON « drupal-settings-json », une entrée par action
  (symbole officiel, émetteur, secteur, compartiment, nombre de titres) ;
- /live-market/indices/cours?symbol=MSI20 : tableau « Composition ».

La composition du MASI 20 est celle du jour de la collecte : elle change lors des
révisions de l'indice et ne doit pas servir à filtrer l'historique.
"""
import argparse
import csv
import json
import re
import sys
from datetime import date

from bs4 import BeautifulSoup

from . import DATA
from .http import get, session

BASE = "https://www.casablanca-bourse.com"
OUT = DATA / "ref" / "valeurs.csv"
FIELDS = ["ticker", "bvc_name", "emetteur", "secteur", "compartiment", "nombre_titres",
          "in_masi20", "as_of"]


def settings(html: str) -> dict:
    m = re.search(r'data-drupal-selector="drupal-settings-json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("bloc drupal-settings-json introuvable")
    return json.loads(m.group(1))


def parse_actions(html: str) -> list[dict]:
    lm = settings(html)["live_market"]
    names = {i["symbol"].strip(): i["label"]["fr"].strip() for i in lm["ticker"]["items"]}
    rows = []
    for a in lm["actions"]:
        t = a["symbol"].strip()
        rows.append({
            "ticker": t,
            "bvc_name": names.get(t),
            "emetteur": a["emetteur"]["fr"].strip(),
            "secteur": a["secteur"]["fr"].strip(),
            "compartiment": a["compartiment"]["fr"].strip(),
            "nombre_titres": a.get("nombreTitres"),
        })
    return rows


def parse_composition(html: str) -> list[str]:
    """Noms affichés des valeurs de l'indice (première colonne du tableau)."""
    table = BeautifulSoup(html, "lxml").select_one("table.comp-tbl")
    if table is None:
        raise ValueError("tableau de composition introuvable")
    return [tr.find("td").get_text(strip=True) for tr in table.select("tbody tr") if tr.find("td")]


def fetch() -> int:
    s = session()
    rows = parse_actions(get(s, BASE + "/live-market/actions", timeout=60).text)
    comp = set(parse_composition(get(s, BASE + "/live-market/indices/cours?symbol=MSI20", timeout=60).text))
    by_name = {r["bvc_name"]: r for r in rows}
    missing = comp - set(by_name)
    if missing or len(comp) != 20:
        raise RuntimeError(f"composition MASI 20 inattendue ({len(comp)} valeurs, inconnues : {missing})")
    today = date.today().isoformat()
    for r in rows:
        r["in_masi20"] = r["bvc_name"] in comp
        r["as_of"] = today
    rows.sort(key=lambda r: r["ticker"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} valeurs, {len({r['secteur'] for r in rows})} secteurs, "
          f"{sum(r['in_masi20'] for r in rows)} dans le MASI 20 -> {OUT}")
    return 0


def load() -> int:
    from .db import connect
    with open(OUT, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with connect() as conn, conn.cursor() as cur:
        for r in rows:
            # Les valeurs absentes de Kaggle (DIS, DLM, SAM, T2S) sont ajoutées ici.
            cur.execute(
                """INSERT INTO instruments (ticker, name, kind, sector, bvc_name, in_masi20)
                   VALUES (%s, %s, 'stock', %s, %s, %s)
                   ON CONFLICT (ticker) DO UPDATE SET sector = EXCLUDED.sector,
                                                      in_masi20 = EXCLUDED.in_masi20""",
                (r["ticker"], r["bvc_name"], r["secteur"], r["bvc_name"], r["in_masi20"] == "True"),
            )
        conn.commit()
        n = cur.execute("SELECT count(*) FILTER (WHERE sector IS NOT NULL), "
                        "count(*) FILTER (WHERE in_masi20) FROM instruments").fetchone()
    print(f"instruments : {n[0]} avec secteur, {n[1]} dans le MASI 20")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "load"])
    a = ap.parse_args(argv)
    return fetch() if a.cmd == "fetch" else load()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sys.exit(main())
