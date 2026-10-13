"""Outils de lecture des nombres et dates au format français."""
import re
from datetime import date

MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}


def fr_number(text: str | None) -> float | None:
    """'1 060,00' -> 1060.0 ; '+0,18%' -> 0.18 ; '-' -> None."""
    if text is None:
        return None
    t = re.sub(r"[\s  %]", "", text)
    if t in ("", "-", "--"):
        return None
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def fr_date(text: str) -> date:
    """'Mardi 13 octobre 2026' -> date(2026, 10, 13)."""
    m = re.search(r"(\d{1,2})\s+([a-zéûè]+)\s+(\d{4})", text.lower())
    if not m:
        raise ValueError(f"date illisible : {text!r}")
    return date(int(m.group(3)), MOIS[m.group(2)], int(m.group(1)))
