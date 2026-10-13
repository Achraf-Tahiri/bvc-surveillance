"""Rapprochement des publications AMMC avec les valeurs cotées et classement par type.

Usage : python -m bvcsurv.referentiel   # rapport de couverture sur data/ammc/communiques.csv

Émetteur : la table data/ref/emetteurs_alias.csv associe chaque écriture
rencontrée à un ticker (ou la marque non cotée / sans historique). Les clés
sont comparées après normalisation (casse, accents, ponctuation, espaces,
suffixe « SA »). Si l'émetteur extrait du titre n'est pas reconnu, on essaie
le début du titre (titres anciens sans séparateur : « Sonasid-Post AGO »).

Type : mots-clés appliqués à l'objet de la publication, dans un ordre de
priorité (un « avis de convocation à l'AGO des obligataires » relève de la
dette, pas des assemblées générales d'actionnaires).
"""
import csv
import re
import sys
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from . import DATA

ALIASES = DATA / "ref" / "emetteurs_alias.csv"


def plain(text: str) -> str:
    """Minuscules sans accents, ponctuation remplacée par des espaces."""
    t = unicodedata.normalize("NFKD", text.replace("’", "'"))
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", t))


def key(name: str) -> str:
    """Clé de comparaison d'un nom d'émetteur : « Label'Vie S.A. » -> « labelvie »."""
    words = plain(name).split()
    for suffix in (["s", "a"], ["sa"], ["sca"]):
        if len(words) > len(suffix) and words[-len(suffix):] == suffix:
            words = words[:-len(suffix)]
            break
    return "".join(words)


@dataclass(frozen=True)
class Alias:
    alias: str
    ticker: str | None
    statut: str          # cotee | sans_historique | non_cotee | plusieurs
    du: str              # bornes de validité (AAAA-MM-JJ), vides si toujours valable
    au: str

    def valid(self, day: str) -> bool:
        return (not self.du or day >= self.du) and (not self.au or day <= self.au)


@lru_cache
def aliases() -> dict[str, list[Alias]]:
    table: dict[str, list[Alias]] = {}
    with open(ALIASES, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a = Alias(r["alias"], r["ticker"] or None, r["statut"], r["du"], r["au"])
            table.setdefault(key(a.alias), []).append(a)
    return table


def _lookup(k: str, day: str) -> Alias | None:
    for a in aliases().get(k, []):
        if a.valid(day):
            return a
    return None


def match_issuer(issuer_raw: str | None, title: str, published_at: str) -> Alias | None:
    """Alias reconnu pour une publication, ou None si l'émetteur est inconnu."""
    day = published_at[:10]
    if issuer_raw:
        a = _lookup(key(issuer_raw), day)
        if a:
            return a
    # Repli 1 : les premiers mots du titre (du plus long au plus court).
    words = plain(title).split()
    for n in range(min(6, len(words)), 0, -1):
        a = _lookup(key(" ".join(words[:n])), day)
        if a:
            return a
    # Repli 2 : un nom de société cotée ailleurs dans le titre (« CP IAM 1S11 »),
    # accepté seulement s'il désigne une seule valeur. « Total » est trop ambigu.
    found = {}
    for i in range(1, len(words)):
        for n in range(min(6, len(words) - i), 0, -1):
            k = key(" ".join(words[i:i + n]))
            a = _lookup(k, day) if len(k) >= 3 and k != "total" else None
            if a and a.ticker:
                found[a.ticker] = a
                break
    return next(iter(found.values())) if len(found) == 1 else None


# Ordre de priorité : la première règle qui correspond l'emporte.
TYPES = [
    ("profit_warning", r"profit ?warning|avertissement sur (les )?resultats"),
    # « Rendements trimestriels » des foncières : ce sont des distributions, pas des indicateurs.
    ("operation_financiere", r"paiement d[ue]s? .{0,25}rendements?"),
    ("indicateurs_trimestriels",
     r"indicateur|trimestr|\bt ?[1-4]\b|\b[1-4] ?(er|e|eme) trim|\bventes\b|unites vendues"),
    # Résultats annoncés avec la convocation à l'AG : le résultat est l'information principale.
    ("resultats", r"resultats (financiers|annuels|consolides|semestriels)"),
    ("dette",
     r"obligataire|obligations?\b|\boca\b|emprunt|billets? de tresorerie|(?<!maghreb )titrisation"
     r"|\bfpct\b|taux (facial|d interet)|coupon|certificats? de depot|bons de societes de financement|\bbsf\b|porteurs"),
    ("assemblee_generale", r"\bag[omex]?\b|assemblee|convocation|convoc|avis de reunion"),
    ("operation_financiere",
     r"augmentation (de |du )?capital|reduction (de |du )?capital|\bop[aerv]\b|offre publique"
     r"|introduction en bourse|fusion|absorption|acquisition|acquerir|\bcession|\bceder|rachat"
     r"|prise de (participation|controle)|division (du )?nominal|dividende|rendements|radiation|retrait"
     r"|scission|apport|actionnariat|participation|rapprochement|combiner|franchissement|seuil"
     r"|prospectus|actions (nouvelles|gratuites)"
     r"|emission d actions|attribution gratuite|conversion|closing|restructuration"),
    ("resultats",
     r"resultat|cp financier|communication financiere|communique financier|comptes"
     r"|etats financiers|\bs ?[12]\b|semestr|exercice|annuel|chiffre d affaires|\bpnb\b|\bca et rn\b"),
    ("gouvernance",
     r"nomination|nomme|demission|conseil d administration|conseil de surveil+ance|directoire"
     r"|directeur|president|\bpdg\b|\bdga?\b|gouvernance|administrateur|deces|depart|mandat"
     r"|commissaires? aux comptes|post (ca|cs|conseil)|cooptation|management"),
]
_TYPES = [(name, re.compile(rx)) for name, rx in TYPES]
EVENT_TYPES = list(dict.fromkeys(name for name, _ in TYPES)) + ["autre"]


def classify(subject: str | None, title: str) -> str:
    text = plain(subject or title)
    for name, rx in _TYPES:
        if rx.search(text):
            return name
    return "autre"


def enrich(rows: list[dict]) -> list[dict]:
    """Ajoute ticker, statut de l'émetteur et type à chaque publication."""
    out = []
    for r in rows:
        a = match_issuer(r.get("issuer_raw") or None, r["title"], r["published_at"])
        out.append({**r,
                    "ticker": a.ticker if a else None,
                    "issuer_status": a.statut if a else "inconnu",
                    "event_type": classify(r.get("subject") or None, r["title"])})
    return out


def report() -> int:
    from collections import Counter

    from .ammc import OUT
    with open(OUT, newline="", encoding="utf-8") as f:
        rows = enrich(list(csv.DictReader(f)))
    n = len(rows)
    st = Counter(r["issuer_status"] for r in rows)
    print(f"{n} publications")
    for s, c in st.most_common():
        print(f"  {s:16s} {c:6d}  ({100 * c / n:.1f} %)")
    unknown = Counter((r["issuer_raw"] or r["title"]) for r in rows if r["issuer_status"] == "inconnu")
    print(f"émetteurs inconnus : {len(unknown)} écritures distinctes")
    for name, c in unknown.most_common(40):
        print(f"  {c:4d}  {name}")
    print("types (émetteurs cotés) :")
    ty = Counter(r["event_type"] for r in rows if r["ticker"])
    for t in EVENT_TYPES:
        print(f"  {t:26s} {ty[t]:6d}")
    print(f"valeurs avec au moins une publication : {len({r['ticker'] for r in rows if r['ticker']})}")
    return 0


if __name__ == "__main__":
    sys.exit(report())
