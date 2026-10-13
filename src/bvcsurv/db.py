"""Accès PostgreSQL (DATABASE_URL) : schéma et insertions idempotentes."""
import csv
import os

import psycopg

from . import DATA, ROOT

# Indices du bandeau -> tickers de l'historique Kaggle.
INDEX_TICKERS = {"MASI": "MASI", "MASI 20": "MSI20"}


def connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL non défini (voir .env.example)")
    conn = psycopg.connect(url)
    with conn.cursor() as cur:
        cur.execute((ROOT / "sql" / "schema.sql").read_text())
        apply_aliases(cur)
    conn.commit()
    return conn


def apply_aliases(cur) -> None:
    """Noms du site de la Bourse qui diffèrent des noms Kaggle (data/ref/bvc_aliases.csv)."""
    with open(DATA / "ref" / "bvc_aliases.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute("UPDATE instruments SET bvc_name=NULL WHERE bvc_name=%s AND ticker<>%s",
                        (row["bvc_name"], row["ticker"]))
            cur.execute("UPDATE instruments SET bvc_name=%s WHERE ticker=%s",
                        (row["bvc_name"], row["ticker"]))


def upsert_live(conn: psycopg.Connection, snap: dict) -> None:
    d = snap["session_date"]
    masi = snap["indices"].get("MASI", {})
    m20 = snap["indices"].get("MASI 20", {})
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO live_sessions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (session_date) DO UPDATE SET
                 market_status=EXCLUDED.market_status, closed=EXCLUDED.closed,
                 masi=EXCLUDED.masi, masi_var_pct=EXCLUDED.masi_var_pct,
                 masi20=EXCLUDED.masi20, masi20_var_pct=EXCLUDED.masi20_var_pct,
                 capitalisation_mad=EXCLUDED.capitalisation_mad,
                 volume_global_mad=EXCLUDED.volume_global_mad,
                 same_prices_as_previous=EXCLUDED.same_prices_as_previous,
                 fetched_at_utc=EXCLUDED.fetched_at_utc""",
            (d, snap["market_status"], snap["closed"], masi.get("value"), masi.get("var_pct"),
             m20.get("value"), m20.get("var_pct"), snap["capitalisation_mad"],
             snap["volume_global_mad"], snap["same_prices_as_previous_session"],
             snap["fetched_at_utc"]),
        )
        cur.execute("DELETE FROM live_quotes WHERE session_date=%s", (d,))
        cur.executemany(
            "INSERT INTO live_quotes VALUES (%s,%s,%s,%s)",
            [(d, q["name"], q["price"], q["var_pct"]) for q in snap["quotes"]],
        )
        cur.execute("DELETE FROM live_tops WHERE session_date=%s", (d,))
        cur.executemany(
            "INSERT INTO live_tops VALUES (%s,%s,%s,%s,%s,%s)",
            [(d, t["kind"], t["rank"], t["name"], t.get("price"), t["value"]) for t in snap["tops"]],
        )
        stocks = snap.get("stocks")
        cur.execute("DELETE FROM live_stocks WHERE session_date=%s", (d,))
        if stocks:
            cols = ["ticker", "status", "open", "high", "low", "last", "reference", "var_pct",
                    "volume_mad", "quantity", "trades", "capitalisation_mad", "shares"]
            cur.executemany(
                f"INSERT INTO live_stocks (session_date, {', '.join(cols)}) "
                f"VALUES (%s, {', '.join(['%s'] * len(cols))})",
                [(d, *(q[c] for c in cols)) for q in stocks],
            )
        # Les cours de clôture prolongent l'historique. On ignore les jours où la page
        # n'a pas changé (férié probable).
        if snap["closed"] and not snap["same_prices_as_previous_session"] and stocks:
            # Comme dans Kaggle : une ligne seulement pour les valeurs échangées, volume en titres.
            cur.execute(
                """INSERT INTO prices_daily (ticker, day, open, high, low, close, volume, source)
                   SELECT ticker, session_date, open, high, low, last, quantity, 'live'
                   FROM live_stocks
                   WHERE session_date = %s AND status = 'T' AND quantity > 0 AND last IS NOT NULL
                   ON CONFLICT (ticker, day) DO UPDATE SET
                     open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                     close = EXCLUDED.close, volume = EXCLUDED.volume
                   WHERE prices_daily.source = 'live'""",
                (d,),
            )
        elif snap["closed"] and not snap["same_prices_as_previous_session"]:
            # Repli sans la page des actions : dernier cours du bandeau, sans OHLV.
            cur.execute(
                """INSERT INTO prices_daily (ticker, day, close, source)
                   SELECT i.ticker, q.session_date, q.price, 'live'
                   FROM live_quotes q JOIN instruments i ON i.bvc_name = q.bvc_name
                   WHERE q.session_date = %s AND q.price IS NOT NULL
                   ON CONFLICT (ticker, day) DO UPDATE SET close = EXCLUDED.close
                   WHERE prices_daily.source = 'live'""",
                (d,),
            )
        if snap["closed"] and not snap["same_prices_as_previous_session"]:
            for name, ticker in INDEX_TICKERS.items():
                v = snap["indices"].get(name, {}).get("value")
                if v is not None:
                    cur.execute(
                        """INSERT INTO prices_daily (ticker, day, close, source) VALUES (%s,%s,%s,'live')
                           ON CONFLICT (ticker, day) DO UPDATE SET close = EXCLUDED.close
                           WHERE prices_daily.source = 'live'""",
                        (ticker, d, v),
                    )
    conn.commit()
