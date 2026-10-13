import numpy as np
import pandas as pd

from bvcsurv import detection as D
from bvcsurv.etude import EST


def synthetic(n=700, seed=1):
    rng = np.random.default_rng(seed)
    cal = pd.bdate_range("2015-01-01", periods=n)
    rm = rng.normal(0, 0.01, n)
    rows = [{"ticker": "MASI", "day": d, "close": c, "volume": None}
            for d, c in zip(cal, 10000 * np.exp(np.cumsum(rm)))]
    for t, beta in (("AAA", 1.2), ("BBB", 0.6)):
        ri = 0.0001 + beta * rm + rng.normal(0, 0.008, n)
        vol = np.exp(rng.normal(8, 1, n)).round()
        rows += [{"ticker": t, "day": d, "close": c, "volume": v}
                 for d, c, v in zip(cal, 100 * np.exp(np.cumsum(ri)), vol)]
    return pd.DataFrame(rows), pd.DatetimeIndex(cal)


NO_FLAGS = pd.DataFrame(columns=["ticker", "day"])


def test_features_do_not_look_ahead():
    px, cal = synthetic()
    cut = cal[500]
    before = D.features(px, cal, ["AAA", "BBB"], NO_FLAGS)
    px2 = px.copy()
    future = px2.day > cut
    px2.loc[future, "close"] *= np.random.default_rng(2).uniform(0.8, 1.2, future.sum())
    px2.loc[future & px2.volume.notna(), "volume"] *= 50
    after = D.features(px2, cal, ["AAA", "BBB"], NO_FLAGS)
    cols = ["z", "ar", "abvol", "vol_ratio", "rang", "part_echangee"]
    a = before[before.day <= cut].set_index(["day", "ticker"])[cols]
    b = after[after.day <= cut].set_index(["day", "ticker"])[cols]
    pd.testing.assert_frame_equal(a, b)


def test_rolling_market_model_matches_polyfit():
    px, cal = synthetic()
    feat = D.features(px, cal, ["AAA", "BBB"], NO_FLAGS)
    t = 400
    row = feat[(feat.pos == t) & (feat.ticker == "AAA")].iloc[0]
    close = px[px.ticker == "AAA"].set_index("day").close.reindex(cal)
    masi = px[px.ticker == "MASI"].set_index("day").close.reindex(cal)
    ri, rm = np.log(close).diff().to_numpy(), np.log(masi).diff().to_numpy()
    est = slice(t + EST[0], t + EST[1] + 1)
    b, a = np.polyfit(rm[est], ri[est], 1)
    sigma = (ri[est] - a - b * rm[est]).std(ddof=2)
    assert np.isclose(row.ar, ri[t] - a - b * rm[t])
    assert np.isclose(row.z, (ri[t] - a - b * rm[t]) / sigma)


def test_flagged_day_is_excluded():
    px, cal = synthetic()
    flags = pd.DataFrame({"ticker": ["AAA"], "day": [cal[450].date()]})
    feat = D.features(px, cal, ["AAA", "BBB"], flags)
    assert not ((feat.ticker == "AAA") & (feat.pos == 450)).any()
    assert ((feat.ticker == "BBB") & (feat.pos == 450)).any()


def test_categorize():
    alerts = pd.DataFrame({"ticker": ["AAA", "AAA", "AAA", "BBB"], "pos": [10, 30, 50, 10]})
    pubs = pd.DataFrame({"id": [1, 2, 3], "ticker": ["AAA", "AAA", "AAA"], "pos0": [11, 35, 70],
                         "published_at": pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01"]),
                         "title": ["a", "b", "c"], "event_type": ["resultats"] * 3,
                         "day0": [None] * 3})
    out = D.categorize(alerts, pubs)
    assert list(out.categorie) == ["expliquee", "precede_publication", "sans_explication", "sans_explication"]
    assert list(out.ecart_seances[:2]) == [1, 5]
    assert out.communique_id[0] == 1


def test_publications_in_calendar_gap_are_dropped():
    cal = pd.DatetimeIndex(["2026-03-26", "2026-03-27", "2026-10-12", "2026-10-13"])
    com = pd.DataFrame({"id": [1, 2, 3], "ticker": ["AAA"] * 3, "event_type": ["autre"] * 3,
                        "title": ["x", "y", "z"],
                        "published_at": ["2026-03-26T10:00:00Z", "2026-06-15T10:00:00Z",
                                         "2026-10-13T18:00:00Z"]})
    out = D.publications(com, cal)
    # Juin tombe dans le trou (jour 0 = 12 octobre, trop loin) ; le 13 octobre au soir -> séance suivante.
    assert list(out.id) == [1, 3]
    assert list(out.pos0) == [0, len(cal)]


def test_lift():
    feat = pd.DataFrame({"ticker": ["A"] * 10 + ["B"] * 10,
                         "day": pd.bdate_range("2024-01-01", periods=20)})
    near = np.zeros(20, bool)
    near[[0, 1, 10]] = True          # fréquence de base : A 20 %, B 10 %
    sel = np.zeros(20, bool)
    sel[[0, 1, 2, 3]] = True         # 2 alertes sur 4 proches, toutes sur A
    out = D.lift(sel, near, feat, reps=200)
    assert np.isclose(out["part_proche_pct"], 50)
    assert np.isclose(out["part_hasard_pct"], 20)
    assert np.isclose(out["gain"], 2.5)
