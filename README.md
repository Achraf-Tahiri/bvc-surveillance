# Surveillance des marchés de la Bourse de Casablanca

> Projet en cours de construction. README complet, résultats et limites à venir.

Deux volets :

1. **Étude d'événements** sur les publications des émetteurs (AMMC) et l'historique des cours depuis 2012 : rendements anormaux avant et après chaque annonce, par type d'annonce et par secteur.
2. **Surveillance quotidienne** : collecte des cours après chaque séance (GitHub Actions, PostgreSQL), détection des séances atypiques (Isolation Forest et règles statistiques), rapprochement avec les publications.

Un mouvement repéré avant une publication est un **signal statistique**, jamais une accusation contre un émetteur.

## Données

| Source | Contenu | Accès |
|---|---|---|
| [casablanca-bourse.com](https://www.casablanca-bourse.com/) | cours des 81 valeurs (ouverture, plus haut, plus bas, clôture, volume), MASI, MASI 20, tops ; secteurs et composition du MASI 20 | page d'accueil et `/live-market/actions`, collectées chaque jour |
| [Kaggle, farihomar](https://www.kaggle.com/datasets/farihomar/moroccan-stocks-and-indices-historical-prices) (MIT, données TradingView) | OHLCV quotidiens, 77 actions et 32 indices, mars 2012 à mars 2026 | zip public |
| [AMMC](https://www.ammc.ma/fr/communiques-presse-emetteurs) | communiqués des émetteurs (date, émetteur, objet) | pages publiques |

## Référentiels (`data/ref/`)

| Fichier | Contenu |
|---|---|
| `emetteurs_alias.csv` | écritures des émetteurs AMMC → ticker, ou émetteur non coté / sans historique (changements de nom datés, ex. Holcim Maroc avant et après 2016) |
| `types_validation.csv` | 200 publications tirées au hasard et classées à la main : le classement automatique par type en retrouve 196 (98,0 %) |
| `valeurs.csv` | 81 valeurs : symbole officiel, secteur, compartiment, nombre de titres, appartenance actuelle au MASI 20 |
| `ruptures_prix.csv` | variations au-delà de la limite de ±10 % par séance (cumulée sur les séances sans cotation), exclues des fenêtres d'événement |

L'historique Kaggle est déjà ajusté des divisions du nominal (aucun saut aux divisions de HPS en 2023 et de Sothema en 2021) ; son volume est exprimé en nombre de titres.

Le serveur de la Bourse n'envoie pas son certificat intermédiaire : il est fourni dans `certs/` et ajouté au magasin `certifi` (la vérification TLS reste active).

## Démarrage

```bash
uv venv && uv pip install -e ".[analysis,dev]"
cp .env.example .env              # renseigner DATABASE_URL
python -m bvcsurv.kaggle          # historique des cours -> PostgreSQL
python -m bvcsurv.live            # cours du jour
python -m bvcsurv.ammc fetch      # historique des publications (reprise automatique)
python -m bvcsurv.ammc parse && python -m bvcsurv.ammc load   # avec ticker et type
python -m bvcsurv.valeurs fetch && python -m bvcsurv.valeurs load  # secteurs, MASI 20
python -m bvcsurv.qualite         # sauts de prix
pytest
```

## Licence

MIT. Les données restent la propriété de leurs sources respectives.
