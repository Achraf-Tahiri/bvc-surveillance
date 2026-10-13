# Tableau de bord

Next.js (App Router, TypeScript), Tailwind CSS, shadcn/ui et TradingView Lightweight Charts. Les données
quotidiennes (cours, publications, alertes) sont lues dans PostgreSQL avec un compte en **lecture seule** ;
les résultats historiques (étude d'événements, validation de la détection) viennent de `data/*.json`,
produits par `python -m bvcsurv.export`.

Les pages sont générées à l'avance et rafraîchies au plus une fois par heure (`cacheLife`, `lib/data.ts`) :
l'affichage est instantané et la base Neon, qui se met en veille, n'est sollicitée qu'une fois par heure.

## En local

```bash
cp .env.example .env.local   # puis y mettre l'adresse du compte bvc_lecture
npm install
npm run dev                  # http://localhost:3000
npm run build                # contrôle avant mise en ligne
```

Le compte en lecture seule se crée avec `sql/lecture.sql` (voir l'en-tête du fichier).

## Pages

- `/` : dernière séance, MASI, alertes et publications récentes
- `/alertes` : toutes les alertes, filtrables par année, valeur, catégorie et période
- `/valeurs/[symbole]` : cours en chandeliers et volume, alertes et publications sur le graphique, réactions passées
- `/etude` : résultats de l'étude d'événements
- `/methode` : méthode, validation hors période et limites
