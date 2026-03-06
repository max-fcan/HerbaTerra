# Présentation du modèle

## Présentation globale

### Naissance de l’idée

Dans le cadre d’un projet de cours réalisé pour le concours des Trophées NSI (thème « nature et informatique »), nous avons voulu proposer une expérience qui relie biodiversité et jeu : apprendre des espèces végétales en essayant de se rappeler de caractéristiques biologiques et géographique.

### Problématique initiale

Comment rendre l’exploration de la biodiversité végétale plus engageante et plus mémorable, en s’appuyant sur des données fiables ?

### Objectifs de la solution proposée

1. **Diversité géographique et biologique** : proposer au moins **100 espèces** différentes, avec des observations sur **chaque continent** (version locale minimale).
2. **Catalogue dynamique** : permettre d’explorer un catalogue qui **affiche des images** et **décrit des caractéristiques biologiques** (taxonomie, informations clés, galerie).
3. **Jeu engageant** : proposer un jeu où l’utilisateur doit **deviner l’origine géographique** d’une plante **sous contrainte de temps**, avec un retour immédiat et un score.

### Description synthétique (au moment du dépôt)

HerbaTerra est une plateforme web interactive composée de deux blocs principaux :

- un **jeu de localisation** où l’utilisateur doit estimer le lieu d’origine / d’observation d’une plante à partir d’une image,
- un **catalogue** permettant d’explorer des espèces via filtres et pages détaillées (géographie, taxonomie, galerie d’images).  
  Une version locale (subset) coexiste avec une version cloud plus complète pour gérer une base de données volumineuse.

### Originalité (différenciateurs concrets)

- **Apprentissage par le jeu** : la mémorisation passe par une boucle courte “image → hypothèse géographique → feedback”.
- **Données ouvertes et traçables** : les images proviennent de GBIF et sont **créditées** (auteur + licence, et lien si disponible).
- **Architecture pensée pour évoluer** : séparation claire des fonctionnalités (pages/sections), et stratégie “local subset vs cloud” imposée par les contraintes de taille.

---

## Présentation de l'équipe

### Présentation

Projet réalisé en binôme :

- **Maxence Tanguy**
- **Erwann Feddal**

### Rôle de chacun et chacune

- **Maxence** : backend, base de données (schéma + index), réplication/bootstrapping de la base locale, services.
- **Erwann** : frontend, UI/UX, templates, intégration et cohérence du routage côté pages.

### Répartition des tâches (livrables techniques)

**Backend / données**

- Architecture Flask et modularisation (blueprints, routes, services)
- Conception du schéma de base de données (tables, relations, index)
- Stratégie “local embedded replica” + bootstrapping au démarrage
- Intégration de la source de données (GBIF) et des crédits images (auteur/licence)
- Optimisation des requêtes de lecture (ordre des requêtes, cas limites, performance)

**Frontend / UI**

- Mise en page et structure des templates
- Parcours utilisateur (navigation jeu ↔ carte ↔ catalogue)
- Responsive (mobile/desktop) et clarté visuelle
- Intégration des composants interactifs (cartes, filtres catalogue, retours de jeu)

### Temps passé

- **Maxence** : ~26 h
- **Erwann** : ~20 h  
  Période de travail : **20/11/2025 → dépôt** (finalisations jusqu’à début mars).

### Organisation du travail

- Travail principalement **en classe**.
- Début de séance : définition d’objectifs concrets.
- Fin de tâche : commit ; si une partie reste incomplète, c’est indiqué dans le message de commit.

### Workflow Git

- Branches par préfixe :
  - `develop/…` : développement backend (Maxence)
  - `ui/…` : développement UI (Erwann)

---

## Étapes du projet

1. **20/11/2025 — Démarrage** : création du dépôt et mise en place de la base du projet (squelette Flask).
2. **Semaine 1 — Structuration** : refactor en architecture modulaire par sections/pages (blueprints), pour garder un routage cohérent et faciliter l’évolution.
3. **Décembre → mi-février — Fonctionnalités cœur** : implémentation progressive du jeu, du catalogue, et stabilisation d’une version “démo” ; figement du périmètre juste avant les vacances de février.
4. **Vacances de février — Données & contrainte de taille** : intégration de la base de données locale + cloud (contrainte de ~20 MB par fichier), et mise en place du bootstrapping au démarrage.
5. **Fin février → dépôt — Finition** : correctifs, optimisation de requêtes, gestion de cas limites (ex. espèce sans image), stabilisation UX.

Décisions structurantes :

- **Architecture Flask en blueprints** (modularisation) pour un routage robuste et une base maintenable.
- **Données GBIF** pour images/observations, avec crédits systématiques.
- **Séparation local subset vs cloud full DB** pour gérer une base “énorme” malgré les contraintes de taille.

---

## Validation de l’opérationnalité et du fonctionnement

### État d’avancement au moment du dépôt

**Fait**

- Jeu : boucle principale jouable (deviner une localisation à partir d’une plante affichée)
- Catalogue : affichage dynamique + filtres + pages détaillées
- Carte : interaction fonctionnelle (chargement/affichage selon données)

**Partiel**

- Quiz : pages/structure prévues, finalisation incomplète selon sections

**Non fait / hors périmètre final**

- Tournois, leaderboard, profils complets, daily challenge (prévu/prototypé mais exclu du périmètre final)

### Approches pour vérifier l’absence de bugs (tests manuels réels)

Checklist de validation :

- Carte dynamique : chargement correct, interactions utilisables
- Catalogue : filtres cohérents, affichage des résultats stable
- Jeu : sélection/chargement d’images suffisamment rapide pour rester fluide

Cas limites testés :

- Espèce **sans image**
- Requête DB **lente** (et ajustements d’ordre des requêtes)
- Carte sur mobile : **zoom** / manipulation tactile
- Bootstrapping : cohérence de la réplication locale
- Logs : messages d’erreur compréhensibles et exploitables

### Difficultés rencontrées et solutions apportées

**Difficultés (Maxence)**

1. Schéma DB : assurer des requêtes de lecture rapides et fiables → travail sur structure + index + organisation des accès.
2. Ordre des requêtes et robustesse : nombreux tests manuels et itérations → ajout de TODO internes et besoin d’organigrammes de flux.
3. Bootstrapping / réplication locale : comprendre le principe de “local embedded replica” et trouver une solution compatible → choix Turso Cloud + bootstrapping via libsql.

**Difficultés (Erwann) — à compléter**

- [À compléter] Responsive et cohérence visuelle sur différentes tailles d’écran
- [À compléter] Intégration carte interactive + performance front
- [À compléter] Parcours utilisateur et navigation (templates / routage)

---

## Ouverture

### Idées d’amélioration (Top 4)

P1. **Internationalisation** : ajouter FR/EN (prévu mais non priorisé).  
P2. **Profils & multijoueur** : séparation en 2 étapes (création de profils → fonctionnalités multi).  
P3. **Accessibilité** : alt-text systématique, navigation clavier, focus visible, contrastes et tailles de police.  
P4. **Extension des données & UX** : enrichissement du catalogue (filtres plus fins, meilleure exploration), amélioration des performances côté requêtes et cache.

### Analyse critique (actionnable)

- Produire des **organigrammes** décrivant les flux (API, requêtes DB, jeu) pour garantir cohérence, uniformité et maintenance.
- Définir des **parcours utilisateurs** précis (scénarios de démo, points de friction, critères “done”).

### Compétences personnelles développées

**Maxence**

- Conception de schémas DB orientés performance (indexation, lecture, ordonnancement des requêtes)
- Mise en place d’une stratégie de bootstrapping/replica locale
- Production de logs propres et exploitables en cas d’erreur

**Erwann — à compléter**

- [À compléter] Intégration UI/UX web (templates, responsive, ergonomie)
- [À compléter] Gestion de composants interactifs (carte, filtres, performance front)
- [À compléter] Structuration des pages et navigation

### Démarche d'inclusion

- Objectif initial : proposer **FR/EN** ; non réalisé par manque de temps, priorité donnée au jeu, aux cartes et au catalogue.
- Accessibilité : prise en compte partielle ; des améliorations sont nécessaires (alt-text, navigation clavier, focus visible, contrastes).
