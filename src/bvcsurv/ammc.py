"""Historique des publications des émetteurs (site de l'AMMC).

Usage :
  python -m bvcsurv.ammc fetch --start 0 --end 1100   # récupère les pages (reprise automatique)
  python -m bvcsurv.ammc parse                        # pages en cache -> data/ammc/communiques.csv
  python -m bvcsurv.ammc update                       # nouvelles publications (premières pages)
  python -m bvcsurv.ammc load                         # CSV -> PostgreSQL (DATABASE_URL)

Chaque page brute est mise en cache (data/cache/ammc/page_N.html.gz) : une
interruption ne fait perdre que la page en cours. Les pages déjà présentes
sont sautées, sauf avec --refresh.
"""
import argparse
import csv
import gzip
import html as htmllib
import re
import sys
import time
from datetime import datetime

from bs4 import BeautifulSoup

from . import CACHE, DATA
from .http import get, session

BASE = "https://www.ammc.ma"
LIST_URL = BASE + "/fr/communiques-presse-emetteurs?page={}"
PAGES = CACHE / "ammc"
OUT = DATA / "ammc" / "communiques.csv"
FIELDS = ["published_at", "title", "issuer_raw", "subject", "pdf_url", "page"]

# « Émetteur - objet » : le séparateur varie (« - », « – », « — », espaces manquants).
SEP = re.compile(r"\s+[-–—]\s*|\s*[–—]\s+|\s*[-–—]\s+")


def split_title(title: str) -> tuple[str | None, str]:
    m = SEP.search(title)
    if not m or m.start() == 0:
        return None, title.strip()
    return title[: m.start()].strip(), title[m.end():].strip()


def parse_page(html: str, page: int) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for li in soup.select("li.actualites-row"):
        t = li.find("time")
        title_el = li.select_one(".views-field-title")
        if not t or not title_el:
            continue
        title = " ".join(htmllib.unescape(title_el.get_text(" ", strip=True)).split())
        a = li.find("a", href=True)
        issuer, subject = split_title(title)
        rows.append({
            "published_at": t["datetime"],
            "title": title,
            "issuer_raw": issuer,
            "subject": subject,
            "pdf_url": (BASE + a["href"]) if a and a["href"].startswith("/") else (a["href"] if a else None),
            "page": page,
        })
    return rows


def page_path(n: int):
    return PAGES / f"page_{n:04d}.html.gz"


def fetch(start: int, end: int, delay: float, refresh: bool, stop_year: int | None) -> int:
    PAGES.mkdir(parents=True, exist_ok=True)
    s = session()
    failures = []
    for n in range(start, end + 1):
        p = page_path(n)
        if p.exists() and not refresh:
            continue
        t0 = time.time()
        try:
            html = get(s, LIST_URL.format(n), timeout=90).text
        except Exception as e:  # noqa: BLE001 : on note et on continue
            failures.append(n)
            print(f"page {n} : ÉCHEC {type(e).__name__}", flush=True)
            time.sleep(delay * 5)
            continue
        rows = parse_page(html, n)
        if not rows:
            print(f"page {n} : aucune ligne, fin de la liste", flush=True)
            break
        tmp = p.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.write(html)
        tmp.rename(p)
        last = rows[-1]["published_at"][:10]
        print(f"page {n} : {len(rows)} lignes, jusqu'au {last} ({time.time() - t0:.1f} s)", flush=True)
        if stop_year and int(last[:4]) < stop_year:
            print(f"année {last[:4]} < {stop_year} : arrêt", flush=True)
            break
        time.sleep(delay)
    if failures:
        print(f"pages en échec ({len(failures)}) : {failures} ; relancer la même commande pour les reprendre")
    return 1 if failures else 0


def parse_all() -> int:
    """Fusionne le CSV existant et les pages en cache (les pages en cache priment)."""
    found = {}
    if OUT.exists():
        with open(OUT, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                found[(r["published_at"], r["title"])] = r
    seen = set()
    for p in sorted(PAGES.glob("page_*.html.gz")):
        n = int(p.stem.split("_")[1].split(".")[0])
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for r in parse_page(f.read(), n):
                key = (r["published_at"], r["title"])
                if key not in seen:  # les pages glissent quand l'AMMC publie : doublons possibles
                    seen.add(key)
                    found[key] = r
    rows = list(found.values())
    rows.sort(key=lambda r: r["published_at"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    years = sorted({r["published_at"][:4] for r in rows})
    print(f"{len(rows)} publications uniques ({years[0]} à {years[-1]}) -> {OUT}")
    return 0


def load_db() -> int:
    from .db import connect
    with open(OUT, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with connect() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO communiques (published_at, title, issuer_raw, subject, pdf_url)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (published_at, title) DO NOTHING""",
            [(r["published_at"], r["title"], r["issuer_raw"] or None, r["subject"], r["pdf_url"] or None)
             for r in rows],
        )
        conn.commit()
        n = cur.execute("SELECT count(*) FROM communiques").fetchone()[0]
    print(f"{n} publications en base")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--start", type=int, default=0)
    f.add_argument("--end", type=int, default=1100)
    f.add_argument("--delay", type=float, default=2.0)
    f.add_argument("--refresh", action="store_true")
    f.add_argument("--stop-year", type=int, default=2011)
    sub.add_parser("parse")
    sub.add_parser("load")
    u = sub.add_parser("update")
    u.add_argument("--pages", type=int, default=3)
    a = ap.parse_args(argv)
    print(f"démarrage {datetime.now():%F %T}", flush=True)
    if a.cmd == "fetch":
        return fetch(a.start, a.end, a.delay, a.refresh, a.stop_year)
    if a.cmd == "update":
        code = fetch(0, a.pages - 1, 2.0, True, None)
        return parse_all() or code
    if a.cmd == "load":
        return load_db()
    return parse_all()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sys.exit(main())
