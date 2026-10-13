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

## Résultats de l'étude d'événements

`python -m bvcsurv.etude && python -m bvcsurv.figures` (tableaux et figures dans `results/etude/`).

**Échantillon.** 7 817 publications AMMC rattachées à une valeur, 3 965 événements retenus de mars 2013 à mars 2026 (détail des rejets dans `results/etude/attrition.csv` : surtout des valeurs trop peu échangées pour estimer le modèle). Étude principale : 2 148 événements sur 27 valeurs liquides (cours présent sur plus de 90 % des séances).

**Méthode.** Modèle de marché sur le MASI estimé sur [−250, −30] ; rendements anormaux cumulés (CAR) sur [−10, −1], [0, +1] et [+2, +10]. Sans prévision d'analystes, on ne sait pas si un résultat est une bonne ou une mauvaise nouvelle : la moyenne signée tend vers zéro. L'intensité de la réaction se mesure donc par le **rapport de variance** (AR² / σ², 1 pour une séance ordinaire) et par le **volume anormal** (écart de log du nombre de titres échangés avec la période d'estimation : +0,92 ≈ volume multiplié par 2,5). Intervalles de confiance à 95 % par bootstrap en grappes de dates. La référence est un **placebo** : les mêmes mesures sur des dates tirées au hasard sans publication de la valeur.

| Type | Événements | CAR [0, +1] | IC 95 % | Rapport de variance [0, +1] | IC 95 % | Volume anormal [0, +1] |
|---|---:|---:|---|---:|---|---:|
| Résultats | 599 | −0,3 % | −0,7 à +0,1 | 2,41 | 2,09 à 2,75 | +0,92 |
| Profit warnings | 30 | −7,4 % | −9,5 à −5,2 | 6,07 | 3,67 à 9,11 | +1,95 |
| Indicateurs trimestriels | 599 | 0,0 % | −0,3 à +0,3 | 1,46 | 1,28 à 1,64 | +0,53 |
| Assemblées générales | 415 | 0,0 % | −0,3 à +0,3 | 1,42 | 1,13 à 1,76 | +0,33 |
| Opérations financières | 125 | +0,1 % | −0,8 à +0,9 | 2,45 | 1,68 à 3,46 | +0,44 |
| Dette | 196 | 0,0 % | −0,3 à +0,3 | 1,01 | 0,80 à 1,24 | +0,23 |
| Gouvernance | 51 | −0,2 % | −1,8 à +1,2 | 3,06 | 1,33 à 5,89 | +0,24 |
| Autres | 133 | +1,1 % | +0,5 à +1,7 | 2,02 | 1,26 à 2,99 | +0,18 |
| *Dates sans publication (placebo)* | 1 843 | +0,1 % | 0,0 à +0,3 | 1,01 | 0,93 à 1,09 | −0,02 |

![Variance anormale autour des publications](results/etude/profil_variance.png)

**Lecture.**
- Les publications de **résultats** font bouger les cours : variance multipliée par 2,4 et volume par 2,5 sur [0, +1]. L'effet est net dans 6 groupes de secteurs sur 7 ; il est plus faible pour les banques (1,29, IC 0,92 à 1,77), qui sont de grandes capitalisations très suivies. L'intervalle est entièrement au-dessus de 1 pour 10 années sur 14. Le placebo reste à 1,01 : le modèle est bien calibré.
- Les **profit warnings** provoquent une baisse moyenne de 7,4 % en deux séances. La **dette** (émissions obligataires, assemblées d'obligataires) ne fait pas réagir l'action, ce qui est attendu.
- **Avant la publication** : sur les événements isolés (aucune autre publication de la valeur à ±10 séances), le volume avant les résultats ne s'écarte pas du placebo (+0,06, IC −0,08 à +0,21). Avant les profit warnings, il est plus élevé (+0,73, IC +0,22 à +1,25 ; 24 événements, 11 valeurs). C'est un **signal statistique** sur un petit échantillon, pas la preuve d'une fuite d'information ni une accusation contre un émetteur.

![Profit warnings](results/etude/profit_warnings.png)

![Réaction par type](results/etude/variance_par_type.png)

**Limites.**
- Avant 2020, l'AMMC ne donne que la date de publication : le jour 0 peut précéder d'une séance la vraie réaction, d'où la fenêtre [0, +1].
- La couverture AMMC est inégale (environ 300 publications par an jusqu'en 2018, environ 1 000 ensuite).
- Le jeu Kaggle ne contient que les valeurs cotées en 2026 (biais du survivant) et s'arrête au 27 mars 2026 ; la collecte quotidienne reprend au 13 octobre 2026.
- Les groupes de secteurs ne comptent que 1 à 8 valeurs liquides chacun (`results/etude/resultats_par_secteur.csv`).
- Le classement par type est automatique (98 % de justes sur un échantillon vérifié à la main).

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
python -m bvcsurv.etude && python -m bvcsurv.figures   # étude d'événements
pytest
```

## Licence

MIT. Les données restent la propriété de leurs sources respectives.
