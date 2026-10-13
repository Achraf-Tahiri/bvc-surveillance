# Surveillance des marchés de la Bourse de Casablanca

> Projet en cours de construction. README complet, résultats et limites à venir.

Deux volets :

1. **Étude d'événements** sur les publications des émetteurs (AMMC) et l'historique des cours depuis 2012 : rendements anormaux avant et après chaque annonce, par type d'annonce et par secteur.
2. **Surveillance quotidienne** : collecte des cours après chaque séance (GitHub Actions, PostgreSQL), détection des séances atypiques (Isolation Forest et règles statistiques), rapprochement avec les publications.

Un mouvement repéré avant une publication est un **signal statistique**, jamais une accusation contre un émetteur.

## Données

| Source | Contenu | Accès |
|---|---|---|
| [casablanca-bourse.com](https://www.casablanca-bourse.com/) | cours et variations des 81 valeurs, MASI, MASI 20, tops | page d'accueil, collectée chaque jour |
| [Kaggle, farihomar](https://www.kaggle.com/datasets/farihomar/moroccan-stocks-and-indices-historical-prices) (MIT, données TradingView) | OHLCV quotidiens, 77 actions et 32 indices, mars 2012 à mars 2026 | zip public |
| [AMMC](https://www.ammc.ma/fr/communiques-presse-emetteurs) | communiqués des émetteurs (date, émetteur, objet) | pages publiques |

Le serveur de la Bourse n'envoie pas son certificat intermédiaire : il est fourni dans `certs/` et ajouté au magasin `certifi` (la vérification TLS reste active).

## Démarrage

```bash
uv venv && uv pip install -e ".[analysis,dev]"
cp .env.example .env              # renseigner DATABASE_URL
python -m bvcsurv.kaggle          # historique des cours -> PostgreSQL
python -m bvcsurv.live            # cours du jour
python -m bvcsurv.ammc fetch      # historique des publications (reprise automatique)
python -m bvcsurv.ammc parse && python -m bvcsurv.ammc load
pytest
```

## Licence

MIT. Les données restent la propriété de leurs sources respectives.
