"""Étude d'événements : réaction des cours aux publications des émetteurs (AMMC).

Usage : python -m bvcsurv.etude   # PostgreSQL (DATABASE_URL) -> results/etude/

Méthode
- Jour 0 : séance de la publication. L'heure est convertie en heure de Casablanca ;
  une publication après la clôture (15h30) ou un jour sans séance compte pour la
  séance suivante. Avant 2020, l'AMMC ne donne que la date (horodatage à minuit
  UTC) : le jour 0 est alors la date de publication et la fenêtre [0, +1] couvre
  le cas d'une publication après la clôture.
- Modèle de marché sur le MASI (rendements logarithmiques), estimé sur [-250, -30]
  avec au moins 150 séances réellement échangées. Rendement anormal :
  AR = r - (a + b r_MASI).
- Fenêtres : [-10, -1] (avant), [0, +1] (annonce), [+2, +10] (après).
- Sans prévision d'analystes, le signe d'une annonce de résultats est inconnu :
  la moyenne signée des CAR tend vers zéro. On mesure donc aussi l'intensité de
  la réaction (rapport de variance AR² / σ² sur [0, +1], volume anormal) et
  l'anticipation : CAR[-10, -1] pris dans le sens de la réaction à l'annonce.
- Tests : t transversal sur les CAR standardisés (Boehmer, Masumeci et Poulsen,
  1991) et intervalles de confiance à 95 % par bootstrap en grappes de dates
  (les publications de résultats tombent souvent le même jour).
- Placebo : mêmes mesures sur des dates tirées au hasard sans publication de la
  valeur dans les ±10 séances. C'est la référence du « normal ».
- Exclusions : fenêtre [-10, +10] contenant une rupture de prix (bvcsurv.qualite)
  ou un trou du calendrier ; ruptures retirées de l'estimation.
- Valeurs liquides (étude principale) : cours présent sur plus de 90 % des séances
  de leur période de cotation. Les autres sont traitées à part.
"""
import csv
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy import stats

from . import DATA, ROOT

OUT = ROOT / "results" / "etude"
TZ = ZoneInfo("Africa/Casablanca")
CLOSE_MIN = 15 * 60 + 30
EST = (-250, -30)
MIN_EST = 150
EV = (-10, 10)
WINDOWS = {"pre": (-10, -1), "ann": (0, 1), "post": (2, 10)}
LIQUID = 0.90
MAX_MISSING = 10      # jours ouvrés sans séance au-delà desquels on parle de trou
REPS = 2000
SEED = 20261013


# ---------------------------------------------------------------- données

def load_db(conn) -> dict:
    with conn.cursor() as cur:
        def frame(sql, cols):
            return pd.DataFrame(cur.execute(sql).fetchall(), columns=cols)
        px = frame("SELECT ticker, day, close, volume FROM prices_daily", ["ticker", "day", "close", "volume"])
        ins = frame("SELECT ticker, kind, sector FROM instruments", ["ticker", "kind", "sector"])
        com = frame("SELECT published_at, ticker, event_type, title FROM communiques "
                    "WHERE ticker IS NOT NULL", ["published_at", "ticker", "event_type", "title"])
        flags = frame("SELECT ticker, day FROM price_flags", ["ticker", "day"])
    return {"px": px, "instruments": ins, "communiques": com, "flags": flags}


def sector_groups() -> dict:
    with open(DATA / "ref" / "secteurs_groupes.csv", newline="", encoding="utf-8") as f:
        return {r["secteur"]: r["groupe"] for r in csv.DictReader(f)}


def event_day(published_at: pd.Series, cal: pd.DatetimeIndex) -> np.ndarray:
    """Position dans le calendrier de la séance de réaction (jour 0) ; -1 si hors calendrier."""
    ts = pd.to_datetime(published_at, utc=True)
    date_only = (ts.dt.hour == 0) & (ts.dt.minute == 0) & (ts.dt.second == 0)
    loc = ts.dt.tz_convert(TZ)
    day = loc.dt.tz_localize(None).dt.normalize()
    day = day.where(~date_only, ts.dt.tz_localize(None).dt.normalize())
    after_close = ~date_only & (loc.dt.hour * 60 + loc.dt.minute > CLOSE_MIN)
    day = day + pd.to_timedelta(after_close.astype(int), unit="D")
    pos = np.searchsorted(cal.values, day.values.astype("datetime64[ns]"), side="left")
    pos = np.where(pos < len(cal), pos, -1)
    return pos


def panel(px: pd.DataFrame, cal: pd.DatetimeIndex, tickers: list[str]):
    """Rendements logarithmiques sur le calendrier du MASI, jours échangés, volumes."""
    p = px[px.ticker.isin(tickers)].copy()
    p["day"] = pd.to_datetime(p["day"])
    close = p.pivot(index="day", columns="ticker", values="close").reindex(cal)
    vol = p.pivot(index="day", columns="ticker", values="volume").reindex(cal)
    traded = close.notna()
    logp = np.log(close).ffill()
    r = logp.diff()
    # Après un trou du calendrier (avril à octobre 2026), le rendement n'a pas de sens.
    gaps = np.busday_count(cal[:-1].values.astype("datetime64[D]"), cal[1:].values.astype("datetime64[D]"))
    bad = np.r_[True, gaps - 1 > MAX_MISSING]
    r[bad] = np.nan
    return r, traded, vol, bad


# ---------------------------------------------------------------- calcul

def measure(pos0: int, ri: np.ndarray, rm: np.ndarray, tr: np.ndarray, vo: np.ndarray,
            flagged: np.ndarray) -> dict | str:
    """Mesures d'un événement pour une valeur (tableaux alignés sur le calendrier),
    ou le motif du rejet."""
    lo, hi = pos0 + EV[0], pos0 + EV[1]
    e0, e1 = pos0 + EST[0], pos0 + EST[1]
    if e0 < 0 or hi >= len(rm):
        return "hors calendrier"
    ev = slice(lo, hi + 1)
    if np.isnan(ri[ev]).any() or np.isnan(rm[ev]).any():
        return "fenêtre sans cours (avant cotation ou trou)"
    if flagged[ev].any():
        return "rupture de prix dans la fenêtre"
    est = slice(e0, e1 + 1)
    ok = ~np.isnan(ri[est]) & ~np.isnan(rm[est]) & tr[est] & ~flagged[est]
    if ok.sum() < MIN_EST:
        return f"moins de {MIN_EST} séances échangées pour l'estimation"
    y, x = ri[est][ok], rm[est][ok]
    b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    sigma = resid.std(ddof=2)
    if not sigma > 0:
        return "variance nulle"
    ar = ri[ev] - (a + b * rm[ev])
    out = {"alpha": a, "beta": b, "sigma": sigma, "n_est": int(ok.sum())}
    for name, (w0, w1) in WINDOWS.items():
        seg = ar[w0 - EV[0]: w1 - EV[0] + 1]
        car = seg.sum()
        out[f"car_{name}"] = car
        out[f"scar_{name}"] = car / (sigma * np.sqrt(len(seg)))
        out[f"vr_{name}"] = float(np.mean(seg ** 2) / sigma ** 2)
    out["anticipation"] = float(np.sign(out["car_ann"]) * out["car_pre"])
    # Volume anormal : écart de log(1 + titres échangés) avec la période d'estimation.
    lv = np.log1p(np.nan_to_num(vo, nan=0.0))
    out["abvol_ann"] = float(lv[pos0: pos0 + 2].mean() - lv[est][~np.isnan(ri[est])].mean())
    out["abvol_pre"] = float(lv[pos0 - 10: pos0].mean() - lv[est][~np.isnan(ri[est])].mean())
    out["traded_share"] = float(tr[ev].mean())
    out["ar"] = ar
    return out


def run(data: dict) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, dict]:
    px, ins = data["px"], data["instruments"]
    masi = px[px.ticker == "MASI"].copy()
    cal = pd.DatetimeIndex(sorted(pd.to_datetime(masi["day"])))
    stocks = ins.loc[ins.kind == "stock", "ticker"].tolist()
    r, traded, vol, bad = panel(px, cal, stocks + ["MASI"])
    rm = r["MASI"].to_numpy()

    # Couverture : séances avec cours / séances de la période de cotation (hors trou).
    coverage = {}
    for t in stocks:
        if t not in traded:
            continue
        s = traded[t]
        if not s.any():
            continue
        span = s.loc[s.idxmax(): s[::-1].idxmax()]
        coverage[t] = float(s.loc[span.index].mean())

    flags = data["flags"].copy()
    flags["day"] = pd.to_datetime(flags["day"])
    fl = {t: np.isin(cal, g["day"].values) for t, g in flags.groupby("ticker")}
    groups = sector_groups()
    sector = ins.set_index("ticker")["sector"].to_dict()

    com = data["communiques"].copy()
    attrition = {"publications rattachées à une valeur": len(com)}
    com["pos0"] = event_day(com["published_at"], cal)
    com = com[(com.pos0 >= 0) & com.ticker.isin(coverage)]
    attrition["valeur avec historique de cours"] = len(com)
    # Une même valeur, un même jour, un même type : un seul événement.
    com = com.sort_values("published_at").drop_duplicates(["ticker", "pos0", "event_type"])
    attrition["après dédoublonnage (valeur, jour, type)"] = len(com)
    rejects = {}

    rows, ars = [], []
    rng = np.random.default_rng(SEED)
    for t, g in com.groupby("ticker"):
        ri, tr = r[t].to_numpy(), traded[t].to_numpy()
        vo = vol[t].to_numpy(dtype=float)
        flagged = fl.get(t, np.zeros(len(cal), bool))
        pubs = np.sort(g.pos0.unique())
        for ev in g.itertuples():
            m = measure(ev.pos0, ri, rm, tr, vo, flagged)
            if isinstance(m, str):
                rejects[m] = rejects.get(m, 0) + 1
                continue
            others = pubs[(np.abs(pubs - ev.pos0) <= EV[1]) & (pubs != ev.pos0)]
            ars.append(m.pop("ar"))
            rows.append({"ticker": t, "day0": cal[ev.pos0].date(), "event_type": ev.event_type,
                         "title": ev.title, "isolated": len(others) == 0, **m})
        # Placebo : autant de dates au hasard que de publications, loin de toute publication.
        near = np.zeros(len(cal), bool)
        for p in pubs:
            near[max(0, p - EV[1]): p + EV[1] + 1] = True
        cand = np.flatnonzero(~near)
        cand = cand[(cand + EST[0] >= 0) & (cand + EV[1] < len(cal))]
        for p in rng.permutation(cand)[: len(g)]:
            m = measure(int(p), ri, rm, tr, vo, flagged)
            if isinstance(m, str):
                continue
            ars.append(m.pop("ar"))
            rows.append({"ticker": t, "day0": cal[p].date(), "event_type": "placebo",
                         "title": "", "isolated": True, **m})
    df = pd.DataFrame(rows)
    df["coverage"] = df.ticker.map(coverage)
    df["liquid"] = df["coverage"] > LIQUID
    df["sector"] = df.ticker.map(sector)
    df["sector_group"] = df.sector.map(groups)
    df["year"] = pd.to_datetime(df.day0).dt.year
    cov = pd.DataFrame({"ticker": list(coverage), "coverage": list(coverage.values())})
    for reason, n in sorted(rejects.items(), key=lambda x: -x[1]):
        attrition[f"rejet : {reason}"] = -n
    attrition["événements retenus"] = int((df.event_type != "placebo").sum())
    return df, cov, np.vstack(ars), attrition


# ---------------------------------------------------------------- statistiques

def boot_ci(values: np.ndarray, clusters: np.ndarray, reps: int = REPS, seed: int = SEED):
    """Intervalle à 95 % de la moyenne, bootstrap en grappes (tirage des dates avec remise)."""
    ok = ~np.isnan(values)
    values, clusters = values[ok], clusters[ok]
    if len(values) < 2:
        return np.nan, np.nan
    codes, inv = np.unique(clusters, return_inverse=True)
    sums = np.bincount(inv, weights=values)
    counts = np.bincount(inv)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(codes), size=(reps, len(codes)))
    means = sums[idx].sum(1) / counts[idx].sum(1)
    return tuple(np.percentile(means, [2.5, 97.5]))


def summarize(df: pd.DataFrame, by: str) -> pd.DataFrame:
    out = []
    for key, g in df.groupby(by, sort=False):
        cl = g["day0"].astype(str).to_numpy()
        row = {by: key, "n": len(g), "valeurs": g.ticker.nunique()}
        for w in WINDOWS:
            car = g[f"car_{w}"].to_numpy()
            scar = g[f"scar_{w}"].to_numpy()
            t, p = stats.ttest_1samp(scar, 0.0) if len(g) > 1 else (np.nan, np.nan)
            lo, hi = boot_ci(car, cl)
            row.update({f"car_{w}_pct": 100 * car.mean(), f"car_{w}_ic_bas": 100 * lo,
                        f"car_{w}_ic_haut": 100 * hi, f"t_bmp_{w}": t, f"p_{w}": p})
        row["abs_car_ann_pct"] = 100 * g["car_ann"].abs().mean()
        for w in ("ann", "pre", "post"):
            vr = g[f"vr_{w}"].to_numpy()
            lo, hi = boot_ci(vr, cl)
            row.update({f"vr_{w}": vr.mean(), f"vr_{w}_ic_bas": lo, f"vr_{w}_ic_haut": hi})
        for w in ("ann", "pre"):
            av = g[f"abvol_{w}"].to_numpy()
            lo, hi = boot_ci(av, cl)
            row.update({f"volume_anormal_{w}": av.mean(), f"volume_anormal_{w}_ic_bas": lo,
                        f"volume_anormal_{w}_ic_haut": hi})
        an = g["anticipation"].to_numpy()
        lo, hi = boot_ci(an, cl)
        row.update({"anticipation_pct": 100 * an.mean(), "anticipation_ic_bas": 100 * lo,
                    "anticipation_ic_haut": 100 * hi})
        out.append(row)
    return pd.DataFrame(out).sort_values("n", ascending=False)


ORDER = ["resultats", "profit_warning", "indicateurs_trimestriels", "assemblee_generale",
         "operation_financiere", "dette", "gouvernance", "autre", "placebo"]


def main() -> int:
    from .db import connect
    with connect() as conn:
        data = load_db(conn)
    df, cov, ars, attrition = run(data)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.Series(attrition, name="n").rename_axis("étape").to_csv(OUT / "attrition.csv")
    for k, v in attrition.items():
        print(f"  {v:6d}  {k}")
    df.round(6).to_csv(OUT / "evenements.csv", index=False)
    cov.sort_values("coverage").round(4).to_csv(OUT / "couverture.csv", index=False)
    np.save(OUT / "ar.npy", ars)

    liq = df[df.liquid]
    t_type = summarize(liq, "event_type").set_index("event_type").reindex(ORDER).dropna(how="all").reset_index()
    t_type.round(4).to_csv(OUT / "par_type_liquides.csv", index=False)
    summarize(df[~df.liquid], "event_type").round(4).to_csv(OUT / "par_type_autres.csv", index=False)
    summarize(liq[liq.isolated], "event_type").round(4).to_csv(OUT / "par_type_liquides_isoles.csv", index=False)
    res = liq[liq.event_type.isin(["resultats", "placebo"])]
    summarize(res[res.event_type == "resultats"], "sector_group").round(4).to_csv(
        OUT / "resultats_par_secteur.csv", index=False)
    summarize(liq[liq.event_type != "placebo"], "sector_group").round(4).to_csv(
        OUT / "par_secteur_liquides.csv", index=False)
    summarize(liq[liq.event_type == "resultats"], "year").sort_values("year").round(4).to_csv(
        OUT / "resultats_par_annee.csv", index=False)

    ev = df[df.event_type != "placebo"]
    print(f"{len(ev)} événements retenus ({ev.liquid.sum()} sur {liq.ticker.nunique()} valeurs liquides), "
          f"{(df.event_type == 'placebo').sum()} dates placebo, du {ev.day0.min()} au {ev.day0.max()}")
    cols = ["event_type", "n", "car_ann_pct", "car_ann_ic_bas", "car_ann_ic_haut", "p_ann",
            "abs_car_ann_pct", "vr_ann", "vr_ann_ic_bas", "vr_ann_ic_haut", "vr_pre", "vr_pre_ic_bas",
            "vr_pre_ic_haut", "anticipation_pct", "volume_anormal_ann", "volume_anormal_pre"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(t_type[cols].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sys.exit(main())
