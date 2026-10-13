from pathlib import Path

import pandas as pd

from bvcsurv.qualite import limit_breaks
from bvcsurv.valeurs import parse_actions, parse_composition

FIX = Path(__file__).parent / "fixtures"


def test_parse_actions():
    rows = parse_actions((FIX / "bvc_actions_2026-10-13.html").read_text(encoding="utf-8"))
    assert len(rows) == 81
    r = {x["ticker"]: x for x in rows}
    assert r["IAM"]["bvc_name"] == "ITISSALAT AL-MAGHRIB"
    assert r["IAM"]["secteur"] == "Télécommunications"
    assert r["ATW"]["secteur"] == "Banques"
    assert r["LHM"]["bvc_name"] == "Holcim Maroc S.A"
    assert {"DIS", "DLM", "SAM", "T2S"} <= set(r)


def test_parse_composition():
    comp = parse_composition((FIX / "bvc_msi20_2026-10-13.html").read_text(encoding="utf-8"))
    assert len(comp) == 20
    assert "ATTIJARIWAFA BANK" in comp and "ITISSALAT AL-MAGHRIB" in comp


def test_limit_breaks():
    cal = pd.Series(pd.bdate_range("2024-01-01", periods=10))
    d = list(cal)
    px = pd.DataFrame({
        "ticker": ["A"] * 4 + ["B"] * 3 + ["C"] * 3,
        "day": [d[0], d[1], d[2], d[3], d[0], d[3], d[4], d[0], d[1], d[2]],
        # A : -10 % (limite) puis division par 10 ; B : +30 % sur 3 séances (admis) ;
        # C : point aberrant x10 puis retour.
        "close": [100, 90, 9, 9, 100, 130, 131, 50, 500, 51],
    })
    f = limit_breaks(px, cal)
    assert list(zip(f.ticker, f.kind)) == [("A", "rupture"), ("C", "aller_retour"), ("C", "aller_retour")]
    assert f.iloc[0]["day"] == d[2].date()
