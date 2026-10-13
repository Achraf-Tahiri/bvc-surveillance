import csv

from bvcsurv import DATA
from bvcsurv.ammc import split_title
from bvcsurv.referentiel import classify, key, match_issuer


def ticker(issuer, title, day="2024-01-01T10:00:00Z"):
    a = match_issuer(issuer, title, day)
    return a.ticker if a else None


def test_key():
    assert key("Label'Vie S.A.") == key("Label Vie") == key("LABEL’VIE") == "labelvie"
    assert key("Fénié Brossette") == "feniebrossette"
    assert key("Mutandis SCA") == "mutandis"


def test_match_issuer():
    assert ticker("Maroc Télécom", "Maroc Télécom - CP") == "IAM"
    assert ticker("BMCE Bank", "BMCE Bank - CP") == "BOA"
    assert ticker("JLEC", "JLEC - CP") == "TQM"
    assert ticker("Crédit Agricole du Maroc", "Crédit Agricole du Maroc - CP") is None
    assert match_issuer("Crédit Agricole du Maroc", "x", "2024-01-01").statut == "non_cotee"
    # Holcim Maroc : ancienne société avant la fusion de 2016, nom repris par LHM ensuite.
    assert ticker("Holcim Maroc", "Holcim Maroc - CP", "2014-03-24T10:00:00Z") is None
    assert ticker("Holcim Maroc", "Holcim Maroc - CP", "2026-09-30T10:00:00Z") == "LHM"
    # Titres anciens sans séparateur.
    assert ticker(None, "Sonasid-Post AGO du 24/06/2016") == "SID"
    assert ticker(None, "CP IAM 1S11") == "IAM"
    assert ticker(None, "CP financier 2010") is None


def test_classify():
    def c(s):
        return classify(s, s)
    assert c("CP relatif aux indicateurs du 2ème trimestre 2025") == "indicateurs_trimestriels"
    assert c("Résultats financiers 2021 et avis de convocation à l'AGO du 12 mai 2022") == "resultats"
    assert c("Avis de convocation à l'AGO des obligataires du 22 juin 2020") == "dette"
    assert c("Avis de convocation à l'AGO du 25 avril 2017") == "assemblee_generale"
    assert c("CP relatif aux résultats de l'OPA obligatoire") == "operation_financiere"
    assert c("CP relatif aux résultats de l'emission obligataire") == "dette"
    assert c("CP relatif à la publication d'un profit warning") == "profit_warning"
    assert c("CP relatif à la nomination du PDG") == "gouvernance"
    assert c("CP RFA 2020") == "autre"


def test_classify_validation_sample():
    """Échantillon de 200 publications tiré au hasard et vérifié à la main (data/ref)."""
    with open(DATA / "ref" / "types_validation.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ok = sum(classify(split_title(r["title"])[1], r["title"]) == r["type_manuel"] for r in rows)
    assert len(rows) == 200
    assert ok / len(rows) >= 0.95, f"{ok}/{len(rows)}"


def test_joint_release_excluded():
    a = match_issuer("Aradei Capital et LabelVie", "Aradei Capital et LabelVie - CP", "2026-04-11T10:00:00Z")
    assert a.statut == "plusieurs" and a.ticker is None
