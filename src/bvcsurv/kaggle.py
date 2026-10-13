"""Historique des cours (jeu Kaggle farihomar, licence MIT, données TradingView).

Usage : python -m bvcsurv.kaggle [--no-download]

Télécharge le zip public (sans compte Kaggle), le décompresse dans
data/cache/kaggle/ puis charge instruments et cours quotidiens dans PostgreSQL.
"""
import argparse
import io
import sys
import zipfile

import pandas as pd

from . import CACHE
from .http import get, session

URL = ("https://www.kaggle.com/api/v1/datasets/download/"
       "farihomar/moroccan-stocks-and-indices-historical-prices")
DIR = CACHE / "kaggle"


def download() -> None:
    s = session()
    # Un User-Agent de navigateur déclenche un reCAPTCHA ; un client script reçoit le zip.
    s.headers["User-Agent"] = "bvcsurv/0.1 (+https://github.com/Achraf-Tahiri)"
    r = get(s, URL, timeout=180)
    if not r.content.startswith(b"PK"):
        raise RuntimeError(f"réponse inattendue de Kaggle ({r.headers.get('content-type')})")
    DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for m in z.infolist():
            # On n'extrait que les CSV attendus, sans chemin absolu ni remontée.
            if m.filename.startswith("cse-data/") and m.filename.endswith(".csv") and ".." not in m.filename:
                z.extract(m, DIR)
    print(f"zip de {len(r.content) / 1e6:.1f} Mo décompressé dans {DIR}")


def read_all() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = DIR / "cse-data"
    info = pd.read_csv(base / "info.csv")
    frames = []
    for kind, folder in (("stock", "stock"), ("index", "index")):
        for p in sorted((base / folder).glob("*.csv")):
            df = pd.read_csv(p)
            df["ticker"] = p.stem
            df["kind"] = kind
            frames.append(df)
    px = pd.concat(frames, ignore_index=True).rename(columns=str.lower).rename(columns={"time": "day"})
    px["day"] = pd.to_datetime(px["day"]).dt.date
    return info, px


def load(conn, info: pd.DataFrame, px: pd.DataFrame) -> None:
    kinds = px.groupby("ticker")["kind"].first()
    names = info.set_index("Symbol")["Asset"].to_dict()
    with conn.cursor() as cur:
        for t, k in kinds.items():
            name = names.get(t)
            cur.execute(
                """INSERT INTO instruments (ticker, name, kind, bvc_name) VALUES (%s,%s,%s,%s)
                   ON CONFLICT (ticker) DO UPDATE SET name=EXCLUDED.name, kind=EXCLUDED.kind""",
                (t, name, k, name if k == "stock" else None),
            )
        cur.execute("DELETE FROM prices_daily WHERE source='kaggle'")
        cols = ["ticker", "day", "open", "high", "low", "close", "volume"]
        with cur.copy("COPY prices_daily (ticker, day, open, high, low, close, volume, source) FROM STDIN") as cp:
            for row in px[cols].itertuples(index=False):
                cp.write_row((*row, "kaggle"))
    conn.commit()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-download", action="store_true")
    a = ap.parse_args(argv)
    if not a.no_download:
        download()
    info, px = read_all()
    print(f"{px.ticker.nunique()} séries ({(px.kind == 'stock').groupby(px.ticker).first().sum()} actions), "
          f"{len(px)} lignes, du {px.day.min()} au {px.day.max()}")
    from .db import connect
    with connect() as conn:
        load(conn, info, px)
    print("chargé dans PostgreSQL")
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sys.exit(main())
