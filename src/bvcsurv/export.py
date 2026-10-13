"""Export des résultats (étude d'événements, validation de la détection) pour le tableau de bord.

Usage : python -m bvcsurv.export   # results/etude et results/detection -> dashboard/data/*.json

Ces résultats portent sur l'historique et ne changent pas d'un jour à l'autre : le
tableau de bord les lit dans des fichiers versionnés plutôt que dans la base.
Les données quotidiennes (cours, publications, alertes) viennent de PostgreSQL.
"""
import json
import sys

import numpy as np
import pandas as pd

from . import ROOT
from .etude import EV, OUT as ETUDE, SEED, boot_ci
from .detection import OUT as DETECTION
from .figures import NAMES

DEST = ROOT / "dashboard" / "data"
DAYS = list(range(EV[0], EV[1] + 1))


def clean(obj):
    """Valeurs JSON : NaN -> null, numpy -> Python, arrondi à 4 décimales."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return None if not np.isfinite(obj) else round(float(obj), 4)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def records(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    return [clean(r) for r in df[cols].to_dict("records")]


def etude() -> dict:
    df = pd.read_csv(ETUDE / "evenements.csv")
    ars = np.load(ETUDE / "ar.npy")
    assert len(df) == len(ars)
    cols = ["n", "valeurs", "vr_ann", "vr_ann_ic_bas", "vr_ann_ic_haut", "car_ann_pct", "car_ann_ic_bas",
            "car_ann_ic_haut", "abs_car_ann_pct", "volume_anormal_ann", "volume_anormal_ann_ic_bas",
            "volume_anormal_ann_ic_haut", "volume_anormal_pre", "volume_anormal_pre_ic_bas",
            "volume_anormal_pre_ic_haut", "car_post_pct", "car_post_ic_bas", "car_post_ic_haut"]
    par_type = pd.read_csv(ETUDE / "par_type_liquides.csv")
    par_type["nom"] = par_type.event_type.map(NAMES).fillna("Dates sans publication")
    isoles = pd.read_csv(ETUDE / "par_type_liquides_isoles.csv")
    isoles["nom"] = isoles.event_type.map(NAMES).fillna("Dates sans publication")
    secteurs = pd.read_csv(ETUDE / "resultats_par_secteur.csv")
    annees = pd.read_csv(ETUDE / "resultats_par_annee.csv")
    attrition = pd.read_csv(ETUDE / "attrition.csv")

    # Profil de variance (valeurs liquides, événements isolés) et trajectoire des profit warnings.
    liq_iso = (df.liquid & df.isolated).to_numpy()
    z2 = ars ** 2 / df["sigma"].to_numpy()[:, None] ** 2
    variance = {}
    for key in ("resultats", "indicateurs_trimestriels", "placebo"):
        m = liq_iso & (df.event_type == key).to_numpy()
        variance[key] = {"n": int(m.sum()), "y": z2[m].mean(0).tolist()}
    paths = {}
    for key in ("profit_warning", "placebo"):
        m = (df.liquid & (df.event_type == key)).to_numpy()
        car = np.cumsum(ars[m], axis=1) * 100
        item = {"n": int(m.sum()), "y": car.mean(0).tolist()}
        if key == "profit_warning":
            cl = df.loc[m, "day0"].astype(str).to_numpy()
            ci = np.array([boot_ci(car[:, j], cl, seed=SEED + j) for j in range(car.shape[1])])
            item["bas"], item["haut"] = ci[:, 0].tolist(), ci[:, 1].tolist()
        paths[key] = item

    ev = df[df.event_type != "placebo"]
    return clean({
        "periode": [str(ev.day0.min()), str(ev.day0.max())],
        "evenements": int(len(ev)),
        "evenements_liquides": int(ev.liquid.sum()),
        "valeurs_liquides": int(ev[ev.liquid].ticker.nunique()),
        "attrition": attrition.to_dict("records"),
        "jours": DAYS,
        "par_type": records(par_type, ["event_type", "nom"] + cols),
        "par_type_isoles": records(isoles, ["event_type", "nom"] + cols),
        "resultats_par_secteur": records(secteurs, ["sector_group", "n", "valeurs", "vr_ann", "vr_ann_ic_bas",
                                                    "vr_ann_ic_haut"]),
        "resultats_par_annee": records(annees, ["year", "n", "vr_ann", "vr_ann_ic_bas", "vr_ann_ic_haut"]),
        "profil_variance": variance,
        "profit_warnings": paths,
    })


def reactions() -> dict:
    """Réactions passées aux publications, par valeur (pour les pages des valeurs)."""
    df = pd.read_csv(ETUDE / "evenements.csv")
    df = df[df.event_type != "placebo"].sort_values("day0", ascending=False)
    out = {}
    for t, g in df.groupby("ticker"):
        out[t] = records(g.assign(car_ann_pct=100 * g.car_ann),
                         ["day0", "event_type", "title", "car_ann_pct", "vr_ann", "abvol_ann", "liquid"])
    return out


def detection() -> dict:
    val = pd.read_csv(DETECTION / "validation.csv")
    prof = pd.read_csv(DETECTION / "profil_publications.csv")
    per = pd.read_csv(DETECTION / "periodes.csv")
    rappel = pd.read_csv(DETECTION / "rappel_par_type.csv")
    rappel["nom"] = rappel.event_type.map(NAMES)
    annees = pd.read_csv(DETECTION / "alertes_par_annee.csv")
    return clean({
        "validation": val.to_dict("records"),
        "profil": prof.to_dict("records"),
        "periodes": per.to_dict("records"),
        "rappel": rappel.to_dict("records"),
        "par_annee": annees.to_dict("records"),
    })


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, data in (("etude", etude()), ("reactions", reactions()), ("detection", detection())):
        path = DEST / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {path.stat().st_size / 1024:.0f} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main())
