"""Session HTTP commune : relances, délai poli et chaîne TLS complétée.

Le serveur de casablanca-bourse.com n'envoie que son certificat feuille, sans
l'intermédiaire Sectigo « Public Server Authentication CA DV R36 ». Les
navigateurs le récupèrent seuls (AIA), pas requests. On l'ajoute donc au
magasin certifi au lieu de désactiver la vérification.
"""
import time
from pathlib import Path

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import CACHE, ROOT

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 bvcsurv (projet étudiant, github.com/Achraf-Tahiri)"
)


def ca_bundle() -> str:
    """Retourne un fichier CA = certifi + intermédiaires du dossier certs/."""
    out = CACHE / "ca-bundle.pem"
    extra = sorted((ROOT / "certs").glob("*.pem"))
    out.parent.mkdir(parents=True, exist_ok=True)
    parts = [Path(certifi.where()).read_text()] + [p.read_text() for p in extra]
    content = "\n".join(parts)
    if not out.exists() or out.read_text() != content:
        out.write_text(content)
    return str(out)


def session(retries: int = 4) -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    s.headers["Accept-Language"] = "fr-FR,fr;q=0.9"
    retry = Retry(
        total=retries,
        backoff_factor=3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.verify = ca_bundle()
    return s


def get(s: requests.Session, url: str, timeout: float = 60, attempts: int = 3) -> requests.Response:
    """GET avec relances supplémentaires sur les délais d'attente réseau."""
    last = None
    for i in range(attempts):
        try:
            r = s.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
            time.sleep(5 * (i + 1))
    raise last
