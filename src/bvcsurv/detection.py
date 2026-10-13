"""Détection des séances atypiques : Isolation Forest et règles statistiques.

Usage : python -m bvcsurv.detection   # PostgreSQL (DATABASE_URL) -> table alerts et results/detection/

Méthode
- Une observation = une valeur un jour de séance où elle a été échangée. Chaque
  variable n'utilise que l'information disponible à la clôture du jour :
  * z : rendement anormal du jour (modèle de marché sur le MASI estimé sur les
    séances [-250, -30], comme dans l'étude d'événements) divisé par l'écart type
    des résidus de l'estimation ;
  * volume anormal : log(1 + titres échangés) moins la médiane des 250 séances
    précédentes, divisé par l'écart absolu médian de ces séances (×1,4826) : le
    volume en titres varie énormément d'une séance à l'autre, un écart brut ne
    serait pas comparable entre valeurs ;
  * ratio de volatilité (log) : écart type des rendements sur 20 séances / 250 séances ;
  * rang du |z| parmi les valeurs échangées le même jour (0 à 1) ;
  * part des 20 dernières séances où la valeur a été échangée.
- Isolation Forest (graine fixe) entraîné sur 2013 à 2022. Seuil : le 1 % des
  observations d'entraînement les plus isolées. Testé hors période sur 2023 à
  2026, puis appliqué chaque jour aux nouvelles séances (le modèle est réentraîné
  à l'identique à chaque lancement : mêmes données, même graine).
- Règle statistique en complément : |z| > 4 déclenche une alerte même si
  l'Isolation Forest ne la retient pas. Pas de règle sur le volume seul : sur
  2013 à 2022, un volume extrême n'était pas plus proche des publications que le
  hasard (gain 0,87).
- Ces choix (variables, seuils) ont été faits sur 2013 à 2022 uniquement
  (entraînement 2013 à 2019, validation 2020 à 2022), avant de regarder le test.
- Exclusions : jours de rupture de prix (bvcsurv.qualite), lendemain d'un trou du
  calendrier, estimation avec moins de 150 séances échangées.
- Catégorie de l'alerte (séance d) selon les publications de la valeur (jour 0
  calculé comme dans l'étude d'événements) : expliquée si une publication tombe
  dans [d-1, d+1], précède une publication si elle tombe dans [d+2, d+10], sans
  explication sinon. Pour les séances récentes, la catégorie peut changer quand
  de nouvelles publications arrivent.
- Validation sur 2023 à 2026 : part des alertes à moins de 2 séances d'une
  publication (fenêtre [d-1, d+1]) comparée à la même part pour des séances tirées
  au hasard dans les mêmes valeurs (moyenne, sur les alertes, de la fréquence de
  base de leur valeur). Gain = rapport des deux, intervalle à 95 % par bootstrap
  en grappes de dates. Calculé pour toutes les publications, puis pour les
  résultats et profit warnings seuls.
"""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from . import ROOT
from .etude import EST, MIN_EST, SEED, event_day, load_db, panel

OUT = ROOT / "results" / "detection"
TRAIN = ("2013-01-01", "2022-12-31")
TEST = ("2023-01-01", "2026-03-31")
FEATURES = ["z", "abvol", "log_vol_ratio", "rang", "part_echangee"]
QUANTILE = 0.01
Z_RULE = 4.0
RESULTS = ["resultats", "profit_warning"]
EXPLAINED = (-1, 1)
BEFORE = (2, 10)
MAX_LAG_DAYS = 7      # au-delà, la publication tombe dans un trou du calendrier
REPS = 2000


# ---------------------------------------------------------------- variables

def features(px: pd.DataFrame, cal: pd.DatetimeIndex, stocks: list[str],
             flags: pd.DataFrame) -> pd.DataFrame:
    """Variables par (valeur, séance), calculées sans regarder l'avenir."""
    r, traded, vol, bad = panel(px, cal, stocks + ["MASI"])
    rm = r.pop("MASI")
    traded = traded[r.columns]
    vol = vol[r.columns]
    flagged = pd.DataFrame(False, index=cal, columns=r.columns)
    for t, g in flags.groupby("ticker"):
        if t in flagged:
            flagged.loc[flagged.index.isin(pd.to_datetime(g["day"])), t] = True
    valid = traded & r.notna() & ~flagged
    ok = valid & rm.notna().to_numpy()[:, None]

    # Modèle de marché glissant sur [t-250, t-30] par sommes cumulées.
    width, lag = EST[1] - EST[0] + 1, -EST[1]
    x = pd.DataFrame(np.repeat(rm.to_numpy()[:, None], r.shape[1], 1), index=cal, columns=r.columns)
    x, y = x.where(ok), r.where(ok)

    def roll(df):
        return df.fillna(0.0).rolling(width, min_periods=1).sum().shift(lag)

    n = roll(ok.astype(float))
    sx, sy, sxx, sxy, syy = roll(x), roll(y), roll(x * x), roll(x * y), roll(y * y)
    cxx, cxy, cyy = sxx - sx ** 2 / n, sxy - sx * sy / n, syy - sy ** 2 / n
    beta = cxy / cxx
    alpha = (sy - beta * sx) / n
    sigma = np.sqrt((cyy - beta * cxy).clip(lower=0) / (n - 2))
    usable = valid & (n >= MIN_EST) & (sigma > 0)
    ar = r - (alpha + beta.mul(rm, axis=0))
    z = (ar / sigma).where(usable)

    rv = r.where(valid)
    vol_ratio = rv.rolling(20, min_periods=10).std() / rv.rolling(250, min_periods=MIN_EST).std()
    lv = np.log1p(vol.where(traded))
    med = lv.rolling(250, min_periods=100).median().shift(1)
    mad = (lv - med).abs().rolling(250, min_periods=100).median().shift(1) * 1.4826
    abvol = (lv - med) / mad.where(mad > 0)
    part = traded.astype(float).rolling(20, min_periods=20).mean()
    rang = z.abs().rank(axis=1, pct=True)

    cols = {"z": z, "ar": ar.where(usable), "sigma": sigma.where(usable), "rendement": np.expm1(r.where(usable)),
            "abvol": abvol, "vol_ratio": vol_ratio,
            "log_vol_ratio": np.log(vol_ratio.where(vol_ratio > 0)), "rang": rang, "part_echangee": part}
    long = pd.concat({k: v.stack(future_stack=True) for k, v in cols.items()}, axis=1)
    long.index.names = ["day", "ticker"]
    long = long.dropna(subset=FEATURES + ["ar"]).reset_index()
    long["pos"] = cal.get_indexer(long["day"])
    return long


# ---------------------------------------------------------------- modèle

def fit_score(feat: pd.DataFrame) -> pd.DataFrame:
    train = feat.day.between(*TRAIN)
    model = IsolationForest(n_estimators=300, max_samples=512, random_state=SEED, n_jobs=-1)
    model.fit(feat.loc[train, FEATURES].to_numpy())
    feat = feat.copy()
    feat["score"] = -model.score_samples(feat[FEATURES].to_numpy())   # plus haut = plus isolé
    threshold = np.quantile(feat.loc[train, "score"], 1 - QUANTILE)
    feat["iforest"] = feat.score >= threshold
    feat["regle_z"] = feat.z.abs() > Z_RULE
    feat["alerte"] = feat.iforest | feat.regle_z
    feat["periode"] = np.select([train, feat.day.between(*TEST)], ["entrainement", "test"], "direct")
    feat.attrs["seuil"] = float(threshold)
    return feat


def publications(com: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """Jour 0 de chaque publication. Une publication après la dernière séance connue
    prend la position len(cal) (séance suivante, pas encore collectée)."""
    com = com.copy()
    pos = event_day(com["published_at"], cal)
    pub_day = pd.to_datetime(com["published_at"], utc=True).dt.tz_localize(None).dt.normalize()
    after = pos < 0
    pos = np.where(after, len(cal), pos)
    day0 = pd.Series(np.where(after, pd.NaT, cal[np.clip(pos, 0, len(cal) - 1)]), index=com.index)
    lag = (pd.to_datetime(day0) - pub_day).dt.days
    com["pos0"] = pos
    com["day0"] = pd.to_datetime(day0).dt.date
    keep = after | (lag <= MAX_LAG_DAYS)
    return com[keep & (pub_day >= cal[0])].reset_index(drop=True)


def categorize(alerts: pd.DataFrame, pubs: pd.DataFrame) -> pd.DataFrame:
    """Catégorie de chaque alerte et publication la plus proche."""
    by_ticker = {t: g.sort_values(["pos0", "published_at"]) for t, g in pubs.groupby("ticker")}
    rows = []
    for a in alerts.itertuples():
        g = by_ticker.get(a.ticker)
        cat, best = "sans_explication", None
        if g is not None:
            off = g.pos0.to_numpy() - a.pos
            near = np.flatnonzero((off >= EXPLAINED[0]) & (off <= EXPLAINED[1]))
            before = np.flatnonzero((off >= BEFORE[0]) & (off <= BEFORE[1]))
            if len(near):
                cat, best = "expliquee", near[np.argmin(np.abs(off[near]))]
            elif len(before):
                cat, best = "precede_publication", before[0]
        row = {"categorie": cat, "communique_id": None, "communique_title": None,
               "communique_type": None, "communique_day0": None, "ecart_seances": None}
        if best is not None:
            p = g.iloc[best]
            row.update(communique_id=int(p["id"]), communique_title=p["title"],
                       communique_type=p["event_type"], communique_day0=p["day0"],
                       ecart_seances=int(p["pos0"] - a.pos))
        rows.append(row)
    return pd.concat([alerts.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


# ---------------------------------------------------------------- validation

def near_matrix(feat: pd.DataFrame, pubs: pd.DataFrame, window: tuple[int, int]) -> np.ndarray:
    """Pour chaque observation : une publication de la valeur tombe-t-elle dans [d+w0, d+w1] ?"""
    out = np.zeros(len(feat), bool)
    pos_by = {t: np.sort(g.pos0.unique()) for t, g in pubs.groupby("ticker")}
    for t, idx in feat.groupby("ticker").indices.items():
        p = pos_by.get(t)
        if p is None:
            continue
        d = feat["pos"].to_numpy()[idx]
        lo = np.searchsorted(p, d + window[0], side="left")
        hi = np.searchsorted(p, d + window[1], side="right")
        out[idx] = hi > lo
    return out


def lift(sel: np.ndarray, near: np.ndarray, feat: pd.DataFrame, reps: int = REPS,
         seed: int = SEED) -> dict:
    """Part des alertes proches d'une publication, part attendue au hasard dans les
    mêmes valeurs, gain et intervalle à 95 % (bootstrap en grappes de dates)."""
    base = pd.Series(near).groupby(feat["ticker"].to_numpy()).mean()
    obs = near[sel].astype(float)
    exp = base.reindex(feat.loc[sel, "ticker"]).to_numpy()
    days = feat.loc[sel, "day"].astype(str).to_numpy()
    codes, inv = np.unique(days, return_inverse=True)
    so, se, cnt = (np.bincount(inv, weights=obs), np.bincount(inv, weights=exp), np.bincount(inv))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(codes), size=(reps, len(codes)))
    gains = (so[idx].sum(1) / cnt[idx].sum(1)) / (se[idx].sum(1) / cnt[idx].sum(1))
    lo, hi = np.percentile(gains, [2.5, 97.5])
    return {"alertes": int(sel.sum()), "seances_d_alerte": len(codes), "valeurs": feat.loc[sel, "ticker"].nunique(),
            "part_proche_pct": 100 * obs.mean(), "part_hasard_pct": 100 * exp.mean(),
            "gain": obs.mean() / exp.mean(), "gain_ic_bas": lo, "gain_ic_haut": hi}


def validate(feat: pd.DataFrame, pubs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    detectors = {"alertes (Isolation Forest ou |z| > 4)": feat.alerte, "Isolation Forest": feat.iforest,
                 "règle |z| > 4": feat.regle_z}
    sets = {"toutes": pubs, "résultats et profit warnings": pubs[pubs.event_type.isin(RESULTS)]}
    for pname, pp in sets.items():
        near = near_matrix(feat, pp, EXPLAINED)
        before = near_matrix(feat, pp, BEFORE) & ~near
        for periode in ("entrainement", "test"):
            m = (feat.periode == periode).to_numpy()
            sub = feat[m].reset_index(drop=True)
            for name, sel in detectors.items():
                s = sel.to_numpy()[m]
                if s.sum() == 0:
                    continue
                for fen, nm in (("[d-1, d+1]", near[m]), ("[d+2, d+10] seulement", before[m])):
                    rows.append({"publications": pname, "periode": periode, "detecteur": name,
                                 "fenetre": fen, **lift(s, nm, sub)})
    val = pd.DataFrame(rows)

    # Profil : part des alertes avec une publication de la valeur à d+k, contre le hasard.
    test = feat[feat.periode == "test"].reset_index(drop=True)
    prof = []
    for k in range(-10, 11):
        nk = near_matrix(test, pubs, (k, k))
        base = pd.Series(nk).groupby(test["ticker"].to_numpy()).mean()
        s = test.alerte.to_numpy()
        prof.append({"k": k, "alertes_pct": 100 * nk[s].mean(),
                     "hasard_pct": 100 * base.reindex(test.loc[s, "ticker"]).mean()})
    return val, pd.DataFrame(prof)


def recall(feat: pd.DataFrame, pubs: pd.DataFrame) -> pd.DataFrame:
    """Part des publications de la période de test suivies d'une alerte sur [0, +1]."""
    test = feat[feat.periode == "test"]
    alert_pos = {t: set(g.pos) for t, g in test[test.alerte].groupby("ticker")}
    obs_pos = {t: set(g.pos) for t, g in test.groupby("ticker")}
    p = pubs[pubs.ticker.isin(obs_pos)].drop_duplicates(["ticker", "pos0", "event_type"])
    p = p[pd.to_datetime(p.day0).between(*TEST)]
    rows = []
    for t, g in p.groupby("event_type"):
        hit = [bool(alert_pos.get(r.ticker, set()) & {r.pos0, r.pos0 + 1}) for r in g.itertuples()
               if {r.pos0, r.pos0 + 1} & obs_pos[r.ticker]]
        if hit:
            rows.append({"event_type": t, "publications": len(hit), "avec_alerte_pct": 100 * np.mean(hit)})
    return pd.DataFrame(rows).sort_values("publications", ascending=False)


def figure(prof: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .figures import BLUE, INK2, MUTED, SURFACE, style

    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURFACE)
    ax.bar(prof.k, prof.alertes_pct, color=BLUE, width=0.7, label="séances d'alerte")
    ax.plot(prof.k, prof.hasard_pct, color=INK2, lw=1.4, marker="o", ms=3.5,
            label="séances au hasard, mêmes valeurs")
    style(ax, "Publications de la valeur autour des alertes (test 2023 à 2026)",
          "part avec une publication à d+k (%)")
    ax.set_xlabel("k : séances entre l'alerte (d) et le jour 0 de la publication", color=MUTED, fontsize=9)
    ax.set_xticks(prof.k)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "publications_autour_des_alertes.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- base

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    ticker            TEXT NOT NULL,
    day               DATE NOT NULL,
    score             DOUBLE PRECISION NOT NULL,   -- isolement (Isolation Forest), plus haut = plus atypique
    iforest           BOOLEAN NOT NULL,
    regles            TEXT,                        -- règle déclenchée (|z| > 4) ou vide
    z                 DOUBLE PRECISION,
    rendement         DOUBLE PRECISION,            -- rendement simple du jour
    ar                DOUBLE PRECISION,            -- rendement anormal (log)
    abvol             DOUBLE PRECISION,            -- volume anormal standardisé
    vol_ratio         DOUBLE PRECISION,
    rang              DOUBLE PRECISION,
    part_echangee     DOUBLE PRECISION,
    categorie         TEXT NOT NULL,               -- expliquee | precede_publication | sans_explication
    communique_id     BIGINT,
    communique_title  TEXT,
    communique_type   TEXT,
    communique_day0   DATE,
    ecart_seances     INTEGER,                     -- jour 0 de la publication moins séance de l'alerte
    periode           TEXT NOT NULL,               -- entrainement | test | direct
    PRIMARY KEY (ticker, day)
);
CREATE INDEX IF NOT EXISTS alerts_day_idx ON alerts (day);
"""

COLUMNS = ["ticker", "day", "score", "iforest", "regles", "z", "rendement", "ar", "abvol", "vol_ratio",
           "rang", "part_echangee", "categorie", "communique_id", "communique_title", "communique_type",
           "communique_day0", "ecart_seances", "periode"]


def to_rows(alerts: pd.DataFrame) -> list[tuple]:
    df = alerts.copy()
    df["day"] = pd.to_datetime(df.day).dt.date
    df["regles"] = np.where(df.regle_z, "|z| > 4", None)
    df = df[COLUMNS].astype(object).where(df[COLUMNS].notna(), None)
    return [tuple(None if v is None else (v.item() if hasattr(v, "item") else v) for v in row)
            for row in df.itertuples(index=False)]


def save(conn, alerts: pd.DataFrame) -> None:
    rows = to_rows(alerts)
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute("DELETE FROM alerts")
        cur.executemany(f"INSERT INTO alerts ({', '.join(COLUMNS)}) VALUES ({', '.join(['%s'] * len(COLUMNS))})", rows)
    conn.commit()


# ---------------------------------------------------------------- principal

def run(data: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    px, ins = data["px"], data["instruments"]
    cal = pd.DatetimeIndex(sorted(pd.to_datetime(px.loc[px.ticker == "MASI", "day"])))
    stocks = [t for t in ins.loc[ins.kind == "stock", "ticker"] if t in set(px.ticker)]
    with np.errstate(invalid="ignore", divide="ignore"):
        feat = fit_score(features(px, cal, stocks, data["flags"]))
    com = data["communiques"].dropna(subset=["ticker"])
    pubs = publications(com, cal)
    return feat, pubs, cal


def main() -> int:
    from .db import connect
    with connect() as conn:
        data = load_db(conn)
        feat, pubs, cal = run(data)
        alerts = categorize(feat[feat.alerte], pubs)
        save(conn, alerts)

    OUT.mkdir(parents=True, exist_ok=True)
    val, prof = validate(feat, pubs)
    val.round(4).to_csv(OUT / "validation.csv", index=False)
    prof.round(4).to_csv(OUT / "profil_publications.csv", index=False)
    figure(prof)
    recall(feat, pubs).round(2).to_csv(OUT / "rappel_par_type.csv", index=False)
    counts = (alerts.assign(annee=pd.to_datetime(alerts.day).dt.year)
              .pivot_table(index="annee", columns="categorie", values="ticker", aggfunc="count", fill_value=0))
    counts["observations"] = feat.groupby(pd.to_datetime(feat.day).dt.year).size()
    counts.to_csv(OUT / "alertes_par_annee.csv")
    pd.DataFrame({
        "periode": ["entrainement", "test", "direct"],
        "observations": [int((feat.periode == p).sum()) for p in ("entrainement", "test", "direct")],
        "alertes": [int((alerts.periode == p).sum()) for p in ("entrainement", "test", "direct")],
    }).to_csv(OUT / "periodes.csv", index=False)

    print(f"{len(feat)} observations (valeur, séance), {feat.ticker.nunique()} valeurs, "
          f"du {feat.day.min().date()} au {feat.day.max().date()} ; seuil d'isolement {feat.attrs['seuil']:.4f}")
    print(f"{len(alerts)} alertes enregistrées (dont {int((alerts.periode == 'direct').sum())} en direct), "
          f"dernière séance : {cal[-1].date()}")
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(val[val.periode == "test"].drop(columns="periode").round(2).to_string(index=False))
        print(recall(feat, pubs).round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sys.exit(main())
