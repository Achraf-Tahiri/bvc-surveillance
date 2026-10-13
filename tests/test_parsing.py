from pathlib import Path

from bvcsurv.ammc import parse_page, split_title
from bvcsurv.live import parse_home
from bvcsurv.parsing import fr_date, fr_number

FIX = Path(__file__).parent / "fixtures"


def test_fr_number():
    assert fr_number("1 060,00") == 1060.0
    assert fr_number("1 060,00") == 1060.0
    assert fr_number("+0,18%") == 0.18
    assert fr_number("-2,94%") == -2.94
    assert fr_number("-") is None


def test_fr_date():
    assert fr_date("Mardi 13 octobre 2026").isoformat() == "2026-10-13"
    assert fr_date("Lundi 3 août 2026").isoformat() == "2026-08-03"


def test_parse_home():
    s = parse_home((FIX / "bvc_home_2026-10-13_open.html").read_text(encoding="utf-8"))
    assert s["session_date"] == "2026-10-13"
    assert s["market_status"] == "Séance ouverte" and not s["closed"]
    assert len(s["quotes"]) == 81
    q = {x["name"]: x for x in s["quotes"]}
    assert q["AKDITAL"] == {"name": "AKDITAL", "price": 1060.0, "var_pct": 2.91}
    assert q["OULMES"]["var_pct"] == -2.94          # classe « decrease »
    assert q["AFMA"]["var_pct"] == 0.0              # classe « nocrease »
    assert s["indices"]["MASI"] == {"value": 16985.08, "var_pct": 0.18}
    assert s["indices"]["MASI 20"]["value"] == 1228.77
    # Les tops concordent avec le bandeau.
    for t in s["tops"]:
        if t["kind"] in ("hausses", "baisses"):
            assert q[t["name"]]["var_pct"] == t["value"]
    assert [t["name"] for t in s["tops"] if t["kind"] == "volume"][0] == "ATTIJARIWAFA BANK"
    assert len(s["futures"]) == 4


def test_split_title():
    assert split_title("SODEP-Marsa Maroc - Résultats") == ("SODEP-Marsa Maroc", "Résultats")
    assert split_title("Label’Vie – Résultats annuels") == ("Label’Vie", "Résultats annuels")
    assert split_title("Jet Contractors -Indicateurs") == ("Jet Contractors", "Indicateurs")
    assert split_title("Résultats annuels 2009") == (None, "Résultats annuels 2009")


def test_parse_ammc_page():
    rows = parse_page((FIX / "ammc_page0_2026-10-13.html").read_text(encoding="utf-8"), 0)
    assert len(rows) == 10
    assert rows[0]["published_at"] == "2026-10-07T09:51:31Z"
    assert rows[0]["issuer_raw"] == "Auto Nejma"
    assert rows[0]["pdf_url"].startswith("https://www.ammc.ma/sites/default/files/")
