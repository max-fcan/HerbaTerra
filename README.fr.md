# HerbaTerra

**HerbaTerra** est une application web Flask permettant d'explorer des données mondiales d'occurrence végétale.  
Elle propose une carte-hub interactive par pays, un catalogue d'espèces filtrable, et un jeu d'identification de plantes inspiré de GeoGuessr — le tout alimenté par une réplique SQLite locale synchronisée depuis une base de données Turso dans le cloud au démarrage.

---

## Table des matières

- [Stack technique](#stack-technique)
- [Fonctionnalités principales](#fonctionnalités-principales)
- [Structure du projet](#structure-du-projet)
- [Démarrage rapide](#démarrage-rapide)
- [Variables d'environnement](#variables-denvironnement)
- [Aperçu des routes](#aperçu-des-routes)
- [Comportement du bootstrap de la réplique](#comportement-du-bootstrap-de-la-réplique)
- [Données et ressources](#données-et-ressources)
- [Journalisation](#journalisation)
- [Dépannage](#dépannage)
- [Limitations connues](#limitations-connues)

---

## Stack technique

| Couche | Technologie |
|---|---|
| Backend | Python 3, Flask |
| Base de données | Turso (cloud) + réplique embarquée libsql → SQLite |
| Mise en page front | Bootstrap 5 |
| Cartes | Leaflet + tuiles OpenStreetMap |
| Page d'accueil 3D | Three.js |
| Configuration | python-dotenv |

---

## Fonctionnalités principales

### Bootstrap de la réplique au démarrage
Au lancement de l'application, un thread d'arrière-plan synchronise une réplique SQLite locale depuis Turso.  
Tant que la synchronisation n'est pas terminée, les routes protégées sont bloquées et les utilisateurs sont automatiquement redirigés vers `/start`, qui interroge l'API de statut jusqu'à ce que la base de données soit prête.

### Carte hub (`/hub`)
Carte choroplèthe Leaflet interactive du monde entier. Chaque pays ouvre une popup avec des liens directs vers les vues Play et Catalogue filtrées sur ce pays.

### Catalogue (`/catalogue`)
- Recherche par nom d'espèce, nom vernaculaire, famille ou genre.
- Filtrage par pays et/ou continent.
- Tri par popularité, nombre d'images ou ordre alphabétique.
- Pages de détail par espèce avec :
  - puces d'occurrence par localisation,
  - carte Leaflet avec statistiques par pays,
  - galerie d'images paginée chargée via API.

### Mode Jeu (`/play`)
- Portée configurable : monde entier, continent ou pays spécifique.
- Une photo de plante est affichée ; le joueur devine son emplacement sur une carte Leaflet dans un temps imparti.
- Score calculé selon une formule inspirée de GeoGuessr (max 5 000 pts/manche, basé sur la distance de Haversine).
- Étape de révélation montrant la bonne localisation après chaque réponse.
- Sessions multi-manches gérées côté serveur via la session Flask.

### Endpoints opérationnels
- `GET /health` — vérification de la disponibilité.
- `GET /api/db/replica-status` — état courant du bootstrap.

---

## Structure du projet

```text
.
├── app/
│   ├── __init__.py             # Factory Flask + garde-fou des routes
│   ├── config.py               # Configuration pilotée par variables d'env
│   ├── logging_setup.py        # Journalisation console + fichier rotatif
│   ├── db/
│   │   ├── __init__.py         # Orchestration du thread de bootstrap
│   │   ├── bootstrap.py        # Logique de synchronisation de la réplique
│   │   └── connections.py      # Helpers SQLite + état de disponibilité
│   ├── routes/                 # Blueprints Flask
│   │   ├── api.py              # Endpoints JSON
│   │   ├── catalogue.py        # Routes /catalogue
│   │   ├── geojson.py          # Serveur de fichiers GeoJSON
│   │   ├── health.py           # Liveness /health
│   │   ├── home.py             # / et /about
│   │   ├── pages.py            # Page de chargement /start
│   │   └── play.py             # Routes du jeu /play
│   ├── services/               # Logique métier
│   │   ├── catalogue.py        # Requêtes et pagination du catalogue
│   │   ├── geocoding.py        # Correspondances pays/continent depuis CSV
│   │   └── play.py             # Planification des manches, score, sélection d'images
│   ├── templates/              # Templates Jinja2
│   └── static/                 # CSS, JS, images, assets Three.js
├── data/
│   ├── countries_high_resolution.geojson
│   ├── countries_medium_resolution.geojson
│   ├── countries_low_resolution.geojson
│   ├── iso3166_country_codes_continents_modified.csv
│   └── sql/                    # Scripts d'optimisation des index (optionnels)
├── docs/                       # Documentation du projet
├── logs/                       # Fichiers de log (créés automatiquement)
├── run.py                      # Point d'entrée de développement local
└── requirements.txt
```

---

## Démarrage rapide

### 1. Créer et activer un environnement virtuel

**Windows (PowerShell) :**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux :**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer l'environnement

Créer un fichier `.env.production` à la racine du projet (chargé automatiquement par `app/config.py`).

Voir [Variables d'environnement](#variables-denvironnement) pour la liste complète.

### 4. Lancer

```bash
python run.py
```

Ouvrir `http://127.0.0.1:5000/` (ou le port configuré).  
Le premier lancement peut prendre un moment le temps que la réplique locale se synchronise depuis Turso.

---

## Variables d'environnement

### Obligatoires

| Variable | Description |
|---|---|
| `TURSO100_DATABASE_URL` | URL de la base Turso (`libsql://...`) |
| `TURSO100_AUTH_TOKEN` | Jeton d'authentification Turso |

### Optionnelles

| Variable | Valeur par défaut | Description |
|---|---|---|
| `SECRET_KEY` | `super-secret-key` | Clé secrète de session Flask |
| `PORT` | `5000` | Port HTTP |
| `FLASK_DEBUG` | `false` | Activer le mode debug et le rechargement auto |
| `LOCAL_DB_PATH` | `temp/plants.db` | Chemin vers la réplique SQLite locale |
| `MAP_GEOJSON_RESOLUTION` | `medium` | Résolution GeoJSON : `low`, `medium` ou `high` |
| `PLAY_ROUNDS` | `4` | Nombre de manches par partie |
| `PLAY_GUESS_SECONDS` | `30` | Durée du timer par manche (secondes) |
| `PLAY_REVEAL_AFTER_SUBMIT` | `true` | Afficher la bonne localisation après chaque réponse |
| `PLAY_WORLD_ANTARCTICA_PROBABILITY` | `0.05` | Probabilité d'une manche en Antarctique (portée monde) |
| `LOG_LEVEL` | `INFO` | Niveau de journalisation (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_DIR` | `logs/` | Répertoire des fichiers de log |

---

## Aperçu des routes

### Pages

| Route | Description |
|---|---|
| `GET /` | Page d'accueil avec globe Three.js animé |
| `GET /start` | Page de chargement de la réplique (interroge l'API de statut) |
| `GET /hub` | Carte hub interactive par pays |
| `GET /play` | Jeu (accepte les paramètres `country_code` / `continent_code`) |
| `GET /catalogue` | Catalogue d'espèces avec filtres |
| `GET /catalogue/species/<nom>` | Page de détail d'une espèce |
| `GET /about` | Page À propos |

### API

| Route | Description |
|---|---|
| `GET /api/db/replica-status` | État courant du bootstrap |
| `GET /api/catalogue/filter-options` | Valeurs disponibles pour les filtres (pays, continents) |
| `GET /api/catalogue/species/<nom>/images` | Images paginées d'une espèce |
| `GET /api/catalogue/species/<nom>/map-stats` | Statistiques d'occurrence par pays |
| `POST /play/guess` | Soumettre une réponse sur la carte pour la manche en cours |
| `POST /play/score` | Finaliser la manche et calculer le score |

### Utilitaires

| Route | Description |
|---|---|
| `GET /health` | Vérification de disponibilité |
| `GET /geojson/<fichier>` | Servir un fichier GeoJSON (liste blanche) |

---

## Comportement du bootstrap de la réplique

`init_db()` démarre un thread daemon en arrière-plan qui synchronise la réplique Turso embarquée.

**États du bootstrap :**

| État | Signification |
|---|---|
| `idle` | Pas encore démarré |
| `starting` | Thread lancé |
| `syncing` | Synchronisation en cours depuis Turso |
| `ready` | Synchronisation terminée — base de données disponible |
| `already_exists` | Réplique locale déjà présente et valide |
| `error` | Échec de la synchronisation (consulter les logs) |

**Blocage des routes tant que la réplique n'est pas prête :**
- Routes de pages (sauf `/`, `/start`) → redirection vers `/start`.
- Routes API → réponse `503` avec le payload de statut.

La page `/start` interroge `GET /api/db/replica-status` et redirige vers `/hub` une fois prête.

---

## Données et ressources

- **Fichiers GeoJSON** servis depuis `/geojson/<fichier>` avec une liste blanche pilotée par la configuration.
- **Correspondances pays/continent** chargées depuis `data/iso3166_country_codes_continents_modified.csv`.
- **Scripts SQL d'index** dans `data/sql/` à appliquer manuellement pour optimiser les performances sur les répliques volumineuses :
  - `index_optimization.sql`
  - `index_optimization_small.sql`

---

## Journalisation

Configurée dans `app/logging_setup.py`. Sorties vers la console et un fichier rotatif.

| Paramètre | Valeur par défaut |
|---|---|
| Fichier de log | `logs/app.log` |
| Taille max | 1 Mo |
| Nombre de sauvegardes | 3 |

Format des logs :
```
%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s
```

---

## Dépannage

| Symptôme | Action |
|---|---|
| Application bloquée sur la page de chargement | Vérifier `GET /api/db/replica-status` ; contrôler l'URL/token Turso dans `.env.production` ; s'assurer de l'accès réseau pour la première synchronisation |
| `libsql is not installed` | Exécuter `pip install -r requirements.txt` |
| Carte non affichée | Vérifier la présence des fichiers GeoJSON dans `data/` ; inspecter la console du navigateur pour les erreurs Leaflet |
| Conflit de port | Définir une valeur différente pour `PORT` dans `.env.production` |
| `403 / 404` sur les GeoJSON | S'assurer que `MAP_GEOJSON_RESOLUTION` vaut `low`, `medium` ou `high` |

---

## Limitations connues

- Aucune suite de tests automatisés.
