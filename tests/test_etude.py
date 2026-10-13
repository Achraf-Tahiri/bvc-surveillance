import numpy as np
import pandas as pd

from bvcsurv.etude import boot_ci, event_day, measure


def test_event_day():
    # Mardi 6, mercredi 7, jeudi 8 octobre 2026 ; le Maroc est à UTC+0 depuis le 20 septembre.
    cal = pd.DatetimeIndex(["2026-10-06", "2026-10-07", "2026-10-08"])
    pub = pd.Series([
        "2026-10-06T10:00:00Z",   # pendant la séance -> même jour
        "2026-10-06T17:00:00Z",   # après 15h30 -> séance suivante
        "2026-10-06T00:00:00Z",   # date seule (horodatage à minuit) -> même jour
        "2026-10-04T12:00:00Z",   # dimanche -> séance suivante
        "2026-10-08T18:00:00Z",   # après la dernière séance connue -> hors calendrier
    ])
    assert list(event_day(pub, cal)) == [0, 1, 0, 0, -1]


def test_event_day_summer_time():
    # En juin 2026, le Maroc était à UTC+1 : 14h45 UTC = 15h45 locale, après la clôture.
    cal = pd.DatetimeIndex(["2026-06-10", "2026-06-11"])
    assert list(event_day(pd.Series(["2026-06-10T14:45:00Z", "2026-06-10T14:15:00Z"]), cal)) == [1, 0]


def test_measure_recovers_market_model_and_shock():
    rng = np.random.default_rng(0)
    n = 400
    rm = rng.normal(0, 0.01, n)
    ri = 0.0002 + 1.5 * rm + rng.normal(0, 0.005, n)
    pos0 = 350
    ri[pos0] += 0.08                              # choc de +8 % le jour 0
    tr = np.ones(n, bool)
    m = measure(pos0, ri, rm, tr, np.full(n, 100.0), np.zeros(n, bool))
    assert abs(m["beta"] - 1.5) < 0.1
    assert abs(m["car_ann"] - 0.08) < 0.02
    assert m["vr_ann"] > 50                       # (0,08 / 0,005)² / 2 ≈ 128
    assert abs(m["abvol_ann"]) < 1e-9
    flagged = np.zeros(n, bool)
    flagged[pos0 + 3] = True
    assert measure(pos0, ri, rm, tr, np.full(n, 100.0), flagged) == "rupture de prix dans la fenêtre"
    assert measure(100, ri, rm, tr, np.full(n, 100.0), np.zeros(n, bool)) == "hors calendrier"


def test_boot_ci_clusters():
    v = np.r_[np.ones(50), np.zeros(50)]
    lo, hi = boot_ci(v, np.r_[np.zeros(50), np.ones(50)].astype(str))
    # Deux grappes seulement : l'intervalle est très large (0 à 1), contrairement au tirage individuel.
    assert lo == 0.0 and hi == 1.0
    lo, hi = boot_ci(v, np.arange(100).astype(str))
    assert 0.35 < lo < 0.5 < hi < 0.65
