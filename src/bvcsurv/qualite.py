"""Contrôle des sauts de prix.

Usage : python -m bvcsurv.qualite   # prices_daily -> data/ref/ruptures_prix.csv et table price_flags

La variation d'un cours est plafonnée à ±10 % par séance. Une valeur peu liquide
peut rester plusieurs séances sans cotation : entre deux cours séparés de k
séances du MASI, la variation admissible va de 0,9^k à 1,1^k. Un écart au-delà
signale une rupture qui ne vient pas d'échanges normaux (division du nominal non
ajustée, détachement important, erreur de données). Ces jours sont exclus des
fenêtres d'événement.

L'historique Kaggle (TradingView) est déjà ajusté des divisions (HPS 2023 et
Sothema 2021 ne présentent aucun saut) ; les cours collectés en direct ne le sont
pas.
"""
import sys

import numpy as np
import pandas as pd

from . import DATA

OUT = DATA / "ref" / "ruptures_prix.csv"
LIMIT = 0.10
TOL = 0.005   # marge pour les arrondis au pas de cotation


def limit_breaks(px: pd.DataFrame, calendar: pd.Series) -> pd.DataFrame:
    """px : colonnes ticker, day, close. calendar : jours de séance (MASI)."""
    pos = pd.Series(np.arange(len(calendar)), index=pd.to_datetime(sorted(calendar)))
    df = px[["ticker", "day", "close"]].copy()
    df["day"] = pd.to_datetime(df["day"])
    df = df.sort_values(["ticker", "day"])
    g = df.groupby("ticker")
    df["prev_day"] = g["day"].shift()
    df["prev"] = g["close"].shift()
    df["prev2"] = g["close"].shift(2)
    df["next"] = g["close"].shift(-1)
    # Un jour absent du calendrier du MASI compte comme une séance.
    k = df["day"].map(pos) - df["prev_day"].map(pos)
    df["sessions"] = k.fillna(1).clip(lower=1).astype(int)
    df["ratio"] = df["close"] / df["prev"]
    up = (1 + LIMIT) ** df["sessions"] * (1 + TOL)
    down = (1 - LIMIT) ** df["sessions"] / (1 + TOL)
    out = df[(df["ratio"] > up) | (df["ratio"] < down)].copy()

    # Aller-retour : un point isolé très éloigné, le cours revient ensuite au niveau
    # d'avant (erreur probable). Les deux jambes sont étiquetées.
    def near(a, b):
        return (a / b > 1 / (1 + 2 * LIMIT)) & (a / b < 1 + 2 * LIMIT)

    far = (out["ratio"] > 1.5) | (out["ratio"] < 1 / 1.5)
    spike = far & near(out["next"], out["prev"])
    back = far & near(out["close"], out["prev2"])
    out["kind"] = np.where(spike | back, "aller_retour", "rupture")
    out["day"] = out["day"].dt.date
    out["prev_day"] = out["prev_day"].dt.date
    return out[["ticker", "day", "prev_day", "prev", "close", "sessions", "ratio", "kind"]]


def main() -> int:
    from .db import connect
    with connect() as conn:
        with conn.cursor() as cur:
            px = pd.DataFrame(cur.execute(
                "SELECT p.ticker, p.day, p.close FROM prices_daily p "
                "JOIN instruments i USING (ticker) WHERE i.kind = 'stock'").fetchall(),
                columns=["ticker", "day", "close"])
            cal = [d for (d,) in cur.execute("SELECT day FROM prices_daily WHERE ticker = 'MASI'")]
            flags = limit_breaks(px, pd.Series(cal))
            cur.execute("DELETE FROM price_flags")
            cur.executemany(
                "INSERT INTO price_flags VALUES (%s,%s,%s,%s,%s)",
                [(r.ticker, r.day, r.kind, float(r.ratio), int(r.sessions)) for r in flags.itertuples()],
            )
        conn.commit()
    flags.round({"prev": 3, "close": 3, "ratio": 4}).to_csv(OUT, index=False)
    print(f"{len(px)} cours, {len(flags)} ruptures sur {flags.ticker.nunique()} actions -> {OUT}")
    print(flags.to_string(index=False))
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sys.exit(main())
