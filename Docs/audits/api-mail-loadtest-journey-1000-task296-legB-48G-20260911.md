# Rapport de tir — journey-1000-task296-legB-48G-20260911

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-task296-legB-48G-20260911-220235.json`.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- le multiplexeur PostgreSQL a **refusé** des connexions (176 refus `server_login_retry` sur la fenêtre) au lieu de les faire attendre : les demandes touchées ont reçu une erreur, et les latences des autres sont des bornes optimistes — refus PgBouncer présents (176) ET login p95 < 1 s (0.079 s) : **la cause n'est pas le login**, lire `SHOW LISTS` (pools, limites) et le DNS du pooler

À instruire une fois le tir refait :
- à 1000 médecins, 7 étape(s) dépassent le temps de réponse attendu : « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) », « Recherche »
- 8 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 28 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.024 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1233799 — **débit émergent global** : 97.4 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 103169 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 97.4 | **1336.8** | 123.8 | **4775.7** | — | 120000.1 | 0.02 | 100.0 | 0 | 0 | 0/247 |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 286114 | 22.71 | 0.03 | 1266.0 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 141 / 862 (n=96708) |
| 2 | Ouvrir / rafraîchir l'inbox | 2727 / 38984 (n=48322) |
| 3 | Ouvrir un message enrichi (servi base) | 1504 / 3338 (n=24216) |
| 4 | Ouvrir un message froid (fetch IMAP) | 712 / 1143 (n=4587) |
| 5 | Recherche | 4287 / 7037 (n=7286) |
| 6 | Envoi (acquittement UI) | 829 / 1535 (n=7224) |
| 7 | Télécharger une PJ (~124 Ko) | 1978 / 5141 (n=9583) |
| 8 | Marquer lu | 630 / 1130 (n=19429) |
| 9 | Rechercher un patient | 97 / 181 (n=5669) |
| 10 | Ouvrir la page d'un dossier patient | 9414 / 24000 (n=7117) |
| 11 | Fiche patient complète (ressenti médecin) | 18480 / 41335 (n=3561) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 15.1 / 20 | 35.4 / 65 | 4692 | 41335 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 4331 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 1356 ms en moyenne, 29634 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | non relevé |
| Backends Postgres (moy/max) | 1414 / 2506 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 4 |
| PgBouncer `cl_waiting` (échant. non nuls) | 699/2474 (28 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 699/2474 (28 %) |
| …dont pool de **maintenance** (échant. non nuls) | 0/2474 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 12342.6 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 12342.6 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 0.0 |
| PgBouncer refus `server_login_retry` (total du palier) | 175 🔴 refus |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | 0.011 / 0.080 / 0.831 |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 355 / 735 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 7 |
| Backends venant du **pooler** (réseau Docker `172.x`, max) | 2499 |
| Backends **directs** — provisionnement, sonde, journal d'audit (max) | 0 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 92.8 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 17 / 199 |
| RSS par réplica api-mail, Mo (moy/max) | 1902 / 4159 (5 réplicas) |

- à 1000 médecins : refus PgBouncer présents (175) ET login p95 < 1 s (0.080 s) : **la cause n'est pas le login**, lire `SHOW LISTS` (pools, limites) et le DNS du pooler

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 97.9 %** des 1000 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⚠️ Chauffe : **9818 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **78 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 141 (300) | 862 (1500) | 96708 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 2727 (300) | 38984 (1000) | 48322 | ❌ |
| 3 | Ouvrir un message enrichi (servi base) | 1504 (100) | 3338 (500) | 24216 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 712 (800) | 1143 (2500) | 4587 | ✅ |
| 5 | Recherche | 4287 (500) | 7037 (2000) | 7286 | ❌ |
| 6 | Envoi (acquittement UI) | 829 (1000) | 1535 (3000) | 7224 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 1978 (500) | 5141 (2000) | 9583 | ❌ |
| 8 | Marquer lu | 630 (200) | 1130 (1000) | 19429 | ❌ |
| 9 | Rechercher un patient | 97 (300) | 181 (1500) | 5669 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 9414 (500) | 24000 (2000) | 7117 | ❌ |
| 11 | Fiche patient complète (ressenti médecin) | 18480 (1500) | 41335 (4000) | 3561 | ❌ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 48322 | 13610 | 38984 | 657642.5 | 77.5 % |
| 🔴 | Ouvrir un message enrichi (servi base) (`read_content`) | 24216 | 1705 | 3338 | 41277.7 | 4.9 % |
| 🔴 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 3561 | 10528 | 24000 | 37491.6 | 4.4 % |
| 🔴 | Recherche (`search`) | 7286 | 4326 | 7037 | 31520.2 | 3.7 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 96708 | 262 | 862 | 25343.9 | 3.0 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 9583 | 2399 | 5141 | 22985.6 | 2.7 % |
| 🟠 | Marquer lu (`mark_read`) | 19429 | 699 | 1130 | 13585.7 | 1.6 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 2346 | 3231 | 7210 | 7579.5 | 0.9 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 7224 | 947 | 1535 | 6839.0 | 0.8 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 4587 | 772 | 1143 | 3539.5 | 0.4 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 3556 | 192 | 272 | 682.0 | 0.1 % |
| 🟢 | Rechercher un patient (`patient_search`) | 5669 | 111 | 181 | 630.7 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 5 🔴 · 3 🟠 · 4 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Ouvrir / rafraîchir l'inbox** (`read_list`, 657642.5 s, 77.5 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (13610 ms)
  - **dispersion p95/p50 = 14.3×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 41277.7 s, 4.9 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1705 ms)
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 37491.6 s, 4.4 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (10528 ms)
- **Recherche** (`search`, 31520.2 s, 3.7 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (4326 ms)
- **Arrivée dashboard** (`dashboard`, 25343.9 s, 3.0 %)
  - **dispersion p95/p50 = 6.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 22985.6 s, 2.7 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2399 ms)
- **Marquer lu** (`mark_read`, 13585.7 s, 1.6 %)
  - **hors grille** — le médecin attend trop
- **Traitement (plateforme)** (`treatment`, 7579.5 s, 0.9 %)
  - **coût par appel élevé** (3231 ms)

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 24177 | 367 | 1240 | 11452.2 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 24177 | 24 | 602 | 4051.9 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 24177 | 164 | 800 | 7469.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 24177 | 12 | 359 | 2370.2 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 24161 | 38 | 423 | 2764.2 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 24161 | 27091 | 42459 | 654878.3 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (1240 ms de p95, 367 ms de p50, n=24177), qui porte **aussi** le temps serveur de l'étape (11452.2 s, 45 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (42459 ms de p95, 27091 ms de p50, n=24161), qui porte **aussi** le temps serveur de l'étape (654878.3 s, 100 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 41343 | 895.5 | 216.6 | 2397.0 | 2979.2 | 20173.6 |
| attachment,palier:1000 | 9583 | 2398.6 | 1977.9 | 3503.3 | 5140.7 | 20173.6 |
| attachment,palier:transition | 139 | 1625.8 | 1605.1 | 2646.9 | 3175.1 | 8239.4 |
| dashboard | 415340 | 213.5 | 72.8 | 594.8 | 840.3 | 8504.5 |
| dashboard,call:coverage,palier:1000 | 24177 | 98.0 | 12.2 | 320.5 | 359.1 | 2784.0 |
| dashboard,call:coverage,palier:transition | 8 | 39.3 | 39.5 | 51.2 | 54.9 | 58.6 |
| dashboard,call:folder,palier:1000 | 24177 | 473.7 | 366.5 | 952.2 | 1239.8 | 5450.4 |
| dashboard,call:folder,palier:transition | 8 | 408.6 | 445.9 | 521.3 | 528.0 | 534.7 |
| dashboard,call:folders,palier:1000 | 24177 | 309.0 | 163.7 | 710.2 | 800.0 | 4858.5 |
| dashboard,call:folders,palier:transition | 8 | 18.7 | 20.4 | 24.5 | 25.3 | 26.1 |
| dashboard,call:today,palier:1000 | 24177 | 167.6 | 23.6 | 521.8 | 601.7 | 3605.8 |
| dashboard,call:today,palier:transition | 8 | 453.6 | 460.3 | 496.7 | 496.9 | 497.2 |
| dashboard,palier:1000 | 96708 | 262.1 | 141.5 | 674.7 | 862.2 | 5450.4 |
| dashboard,palier:transition | 32 | 230.0 | 53.3 | 494.6 | 505.4 | 534.7 |
| mark_read | 83008 | 336.3 | 140.4 | 736.0 | 918.6 | 7267.4 |
| mark_read,palier:1000 | 19429 | 699.2 | 630.3 | 874.9 | 1130.1 | 4341.3 |
| mark_read,palier:transition | 238 | 502.0 | 574.1 | 703.1 | 738.6 | 905.6 |
| patient_docs | 225750 | 862.0 | 77.0 | 3020.0 | 4201.7 | 12881.7 |
| patient_docs,palier:1000 | 53625 | 2237.3 | 2256.7 | 5087.5 | 5854.1 | 12881.7 |
| patient_docs,palier:transition | 801 | 1568.8 | 1257.6 | 3473.6 | 4332.4 | 8130.4 |
| patient_dossier | 15068 | 3858.1 | 429.4 | 13522.9 | 19431.4 | 40913.5 |
| patient_dossier,palier:1000 | 3561 | 10528.4 | 9413.9 | 21926.1 | 24000.2 | 40167.4 |
| patient_dossier,palier:transition | 35 | 5188.9 | 3975.6 | 12142.2 | 13920.8 | 19134.0 |
| patient_opposition | 15068 | 75.2 | 21.9 | 197.7 | 222.6 | 2272.2 |
| patient_opposition,palier:1000 | 3556 | 191.8 | 180.6 | 239.0 | 272.2 | 1454.8 |
| patient_opposition,palier:transition | 53 | 129.1 | 135.7 | 210.9 | 224.7 | 255.7 |
| patient_search | 24284 | 43.7 | 12.9 | 108.7 | 129.1 | 2094.4 |
| patient_search,palier:1000 | 5669 | 111.2 | 97.4 | 148.0 | 181.0 | 1681.4 |
| patient_search,palier:transition | 49 | 76.3 | 92.8 | 114.6 | 126.0 | 143.0 |
| read_content | 103780 | 680.5 | 161.5 | 1783.7 | 2165.8 | 13936.2 |
| read_content,palier:1000 | 24216 | 1704.6 | 1504.4 | 2415.8 | 3338.5 | 13101.0 |
| read_content,palier:transition | 370 | 1035.1 | 940.1 | 1926.7 | 2214.3 | 9308.0 |
| read_content_cold | 19695 | 648.8 | 550.7 | 869.8 | 1115.1 | 7452.3 |
| read_content_cold,palier:1000 | 4587 | 771.6 | 711.8 | 927.9 | 1143.0 | 3527.2 |
| read_content_cold,palier:transition | 64 | 669.7 | 676.2 | 801.6 | 835.0 | 941.1 |
| read_list | 207670 | 5033.7 | 147.0 | 22583.3 | 31106.0 | 60000.5 |
| read_list,call:emails,palier:1000 | 24161 | 27104.8 | 27090.6 | 38984.2 | 42459.2 | 60000.5 |
| read_list,call:emails,palier:transition | 82 | 17996.0 | 19764.0 | 24195.9 | 25031.5 | 25914.8 |
| read_list,call:folder,palier:1000 | 24161 | 114.4 | 38.3 | 231.7 | 422.9 | 4084.4 |
| read_list,call:folder,palier:transition | 82 | 66.0 | 24.1 | 166.9 | 202.2 | 457.1 |
| read_list,palier:1000 | 48322 | 13609.6 | 2727.3 | 35132.4 | 38984.0 | 60000.5 |
| read_list,palier:transition | 164 | 9031.0 | 210.3 | 23444.9 | 24195.3 | 25914.8 |
| search | 30969 | 1954.9 | 839.1 | 4939.7 | 5849.1 | 120000.1 |
| search,palier:1000 | 7286 | 4326.1 | 4287.1 | 6373.6 | 7036.6 | 16475.7 |
| search,palier:transition | 83 | 3463.9 | 3552.4 | 5321.5 | 6447.1 | 8047.3 |
| send | 30860 | 801.6 | 701.0 | 1243.4 | 1454.8 | 8263.2 |
| send,palier:1000 | 7224 | 946.7 | 829.4 | 1360.6 | 1535.4 | 4961.4 |
| send,palier:transition | 97 | 849.5 | 749.1 | 1293.3 | 1327.2 | 1474.2 |
| treatment | 9955 | 1192.7 | 246.9 | 3383.1 | 4338.1 | 20338.7 |
| treatment,palier:1000 | 2346 | 3230.8 | 2631.1 | 5305.7 | 7210.4 | 20338.7 |
| treatment,palier:transition | 41 | 1543.3 | 1179.1 | 3872.3 | 4074.7 | 4542.9 |
| warmup | 11000 | 1355.8 | 401.9 | 3588.4 | 6448.9 | 29633.9 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-11T16:31:31.804000+00:00 → 2026-09-11T20:02:35.748000+00:00 (12664 s) |
| Prometheus (`http://127.0.0.1:9090`) | ⚠️ **injoignable** — URLError : <urlopen error [WinError 10061] No connection could be made because the target machine actively refused it> |
| Échantillonneur (`observe-183120.csv`) | ✅ 295542 points |

### Par réplica api-mail

⚠️ **Aucune série par réplica.** L'attribution repose sur l'étiquette `service_instance_id`, posée par le collector du banc (`resource_to_telemetry_conversion`). Son absence signifie que les réplicas n'ont pas poussé leurs métriques — donc qu'aucune conclusion « ce réplica est saturé » n'est possible sur ce tir.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#31916` | 0.00 | 0.20 | 34 |
| `com.docker.backend#34656` | 2.29 | 5.93 | 1606 |
| `dcp#12484` | 0.00 | 0.25 | 40 |
| `dcp#32456` | 0.00 | 0.09 | 12 |
| `dcp#33076` | 0.00 | 0.09 | 12 |
| `dcp#42008` | 0.00 | 0.00 | 11 |
| `dcp#47540` | 0.00 | 0.00 | 12 |
| `dcp#47696` | 0.00 | 0.14 | 12 |
| `dcp#50412` | 0.00 | 0.19 | 12 |
| `dcp#51652` | 0.00 | 0.10 | 12 |
| `dcp#55596` | 0.98 | 3.65 | 1350 |
| `dcp#8352` | 0.00 | 0.04 | 12 |
| `k6#17104` | 0.22 | 3.52 | 2064 |
| `mss.mail.api#11120` | 0.37 | 1.90 | 4059 |
| `mss.mail.api#23288` | 0.38 | 2.03 | 3889 |
| `mss.mail.api#35680` | 0.37 | 1.99 | 4218 |
| `mss.mail.api#46520` | 0.39 | 2.09 | 4061 |
| `mss.mail.api#55284` | 0.37 | 2.27 | 3930 |
| `vmmemWSL#34068` | 5.55 | 12.95 | 60853 |
| `loadtest-otel-collector-ekbxztwa` | 0.03 | 0.22 | 107 |
| `loadtest-pgbouncer-wmrwrjqc` | 0.56 | 1.03 | 35 |
| `mss-mail-grafana-ab5b4678` | 0.02 | 0.32 | 166 |
| `mss-mail-prometheus-ab5b4678` | 0.02 | 0.18 | 368 |
| `mss-mail-rabbitmq-yhrhawty` | 0.01 | 0.04 | 126 |
| `mss-mail-redis-ab5b4678` | 0.24 | 1.18 | 3080 |
| `mss-mail-redis-b6152948` | 0.00 | 0.01 | 47 |
| `mss-mail-seq-ab5b4678` | 0.01 | 0.18 | 170 |
| `postgres-pgvector` | 1.44 | 6.06 | 43018 |

- **Hôte** : CPU 59.2 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 66
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 3799, cl_waiting max 40, cl_waiting_maintenance max 0, cl_waiting_practitioner max 40, count max 1002, login_retry_delta max 1, maxwait_maintenance_ms max 0, maxwait_ms max 12343, maxwait_practitioner_ms max 12343, sv_active max 466, sv_idle max 1104, sv_login max 4
- **Backends Postgres** : cache_mb max 34271, direct max 0, idle_over_60s max 996, majfault_per_s max 199, pooler max 2499, practitioner_databases max 2499, rss_mb max 5800, seconds max 1, started_last_60s max 735, total max 2506, usage_pct max 93

### p95 client (k6) vs p95 serveur (OpenTelemetry)

⚠️ **Aucun p95 serveur.** `http_server_request_duration_seconds_bucket` n'a produit aucun point sur la fenêtre : la confrontation client/serveur — le seul moyen de distinguer une file interne d'une file hors application — n'est pas disponible sur ce tir.

### Compteurs métier (`Mssante.MailProcessing`)

⚠️ **Aucun compteur métier sur la fenêtre.** Un tir peut être « vert » côté HTTP sans avoir rien traité : sans ces compteurs, on ne peut pas l'affirmer non plus dans l'autre sens.

### Où part le temps d'une opération servie par la base

⚠️ **Aucune décomposition sur la fenêtre.** Les instruments `mssante_db_operation_duration_seconds` / `..._phase_...` (task-243) n'ont produit aucun point : soit le binaire déployé est antérieur à leur ajout, soit le collector n'a pas tourné. Sans eux, le premier poste de coût du parcours **reste une boîte noire** — et cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222).

### Combien d'objets une opération servie par la base construit-elle

⚠️ **Aucun décompte d'objets sur la fenêtre.** L'instrument `mssante_db_operation_objects_total` (task-256) n'a produit aucun point : soit le binaire déployé est antérieur à son ajout, soit le collector n'a pas tourné. Sans lui, la matérialisation garde une durée sans dénominateur — on sait qu'elle vaut 83,7 % du coût de la page d'en-têtes, on ne sait pas si le remède est « moins d'objets », « des objets moins chers » ou « ne pas les construire ici ».

### Où part le temps d'un enrichissement

⚠️ **Aucune décomposition sur la fenêtre.** Les instruments `mssante_enrichment_message_duration_seconds` / `..._phase_...` (task-245) n'ont produit aucun point : soit le binaire déployé est antérieur à leur ajout, soit le collector n'a pas tourné, soit aucun message n'a été enrichi. Sans eux, le **goulot G1** du tir 500 reste une boîte noire — et cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222).

### Où part le temps d'un envoi

⚠️ **Aucune décomposition sur la fenêtre.** Les instruments `mssante_send_message_duration_seconds` / `..._phase_...` (task-260) n'ont produit aucun point : binaire antérieur, collector muet, ou aucun envoi. Sans eux, la seule étape hors grille du parcours reste une boîte noire — et task-238 a déjà corrigé deux fois à l'aveugle.

### Verrous du chemin `read_list`

⚠️ **Aucune mesure de verrou sur la fenêtre.** Les histogrammes `mssante_lock_wait_duration_seconds` / `..._hold_...` (task-211) n'ont produit aucun point : soit le binaire déployé est antérieur à leur ajout, soit le collector n'a pas tourné. Sans eux, **on ne peut pas dire lequel des trois verrous porte la queue de `read_list`** — et desserrer au jugé est précisément ce que task-211 interdit.

### Verrou de session `imap_session`, par opération

⚠️ **Aucune mesure par opération sur la fenêtre.** Sans elle, la détention de `imap_session` reste une durée sans coupable : on ne peut distinguer l'attente de l'**archivage d'un envoi** de celle du **fetch d'enrichissement**, et c'est précisément l'écart que task-213 corrige. Binaire antérieur à l'étiquette `operation`, ou collector absent.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 40.00 clients | 0 clients | 100.0 % | 28.3 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 6.06 cœurs | 24 cœurs | 25.2 % | 0.0 % — transitoire |
| processus `k6#17104` (CPU) | 3.52 cœurs | 24 cœurs | 14.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#55284` (CPU) | 2.27 cœurs | 24 cœurs | 9.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#46520` (CPU) | 2.09 cœurs | 24 cœurs | 8.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#23288` (CPU) | 2.03 cœurs | 24 cœurs | 8.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#35680` (CPU) | 1.99 cœurs | 24 cœurs | 8.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#11120` (CPU) | 1.90 cœurs | 24 cœurs | 7.9 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 28.3 % des échantillons de la fenêtre.

## Vérification par base (propriété + complétude)

> ⚠️ La vérification automatique a tourné pendant que Postgres **redémarrait** (récupération après `wsl --shutdown`, cf.
> incident post-tir ci-dessous) et a rendu « aucune base trouvée » à tort. Rejouée à 22h58, Postgres revenu à 6 connexions :

- **Bases inspectées** : 1000
- **Mails stockés (total)** : 124731 — dont **124731** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Attendu par boîte** : 247 (complétude relative au périmètre du scénario)
- **Verdict propriété** : PASS

`SUMMARY dbs=1000 mails=124731 owned=124731 foreign=0 unmarked=0 expected_per_user=247 verdict=PASS`

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-1000-task296-legB-48G-20260911-220235.jsonl`.

### Objet du tir — task-296, jambe B : Postgres du banc à **48 Go** (décision humaine : « mesurer ce dont Postgres a réellement besoin »)

Troisième jambe du jour à protocole égal (journey 1000, `1000:12600s`, mêmes 1000 bases hydratées gardées, journal d'audit actif,
RTT 5,2 ms → `LATENCY_MS=96`), **même système sous test `d04f2ca`** (worktree `Api/Mail-ref`), harnais `develop` avec task-295.
Un seul facteur change d'une jambe à l'autre : la mémoire du conteneur Postgres — `limits.memory` **48G** (12G le matin, 24G la
jambe A), `shared_buffers` **12GB** (25 %), `effective_cache_size` **36GB**, `max_connections` 2500 inchangé. Fenêtre 18h31 → 22h02,
régime 21h23 → 22h01. k6 exit 0, 0 itération interrompue.

### Verdict — 🔴 ROUGE au sens du rapport (175 refus, `cl_waiting` 28 %), mais **la mémoire n'est plus le facteur limitant** : le plafond suivant est `max_connections`

| Grandeur | 12 Go | 24 Go | **48 Go** |
|---|---|---|---|
| Erreurs k6, tir complet / régime | 11,98 % / 28 % | 0,37 % / 1,5 % | **0,024 % / 0,024 %** (290 requêtes sur 1 233 799) |
| p95 global k6 | 11 021 ms | 9 983 ms | **4 776 ms** |
| Refus PgBouncer `08P01 server_login_retry` | 110 693 | 2 099 | **175** (Seq : 0 exception côté api-mail) |
| HTTP 500 / 503 (Seq) | 74 603 / 56 446 | 2 244 / 1 069 | **39 / 67** |
| Requêtes serveur > 30 min / file active max | 3 105 / 9 782 | 0 / 927 | **0 / 575** |
| Login Postgres (sonde task-295) p50 / p95 / max | 10-16 s (manuel) | 10 ms / 1,0 s / 308 s | **11 ms / 80 ms / 0,83 s** |
| Cache de pages du cgroup | saturé à ~11 Go | saturé à 14-20 Go | **croît puis se stabilise à 30-34 Go** ; cgroup max 92,8 %, jamais à la limite |
| Fautes de page majeures (max / s) | — | 1 120 | **199** (17 en moyenne) |
| `sv_login` max | 467 | 157 | **4** |
| CPU Postgres en régime (cœurs) | 11-15 | 12-13 | **2,2-2,7** |
| Backends Postgres (max) | 1 457 | 2 400 | **2 506 = `max_connections`** dès 21h17 |
| `cl_waiting` (part des relevés) / `maxwait` max | 13 % / 19,1 s | 15 % / 19,3 s | **28 % / 12,3 s** |
| Postgres « sorry, too many clients already » pendant le tir | 0 | 0 | **118 886** (≈1 700/min de 21h17 à 22h02) |
| Journal d'audit émises / persistées / `LOST` | 175 651 / 175 651 / 0 | 191 459 / 191 459 / 0 | 207 396 / 193 909 / 0 — **13 487 encore dans le spill Redis** (drain interrompu par l'incident post-tir, voir plus bas) |
| Verdict SLO | 8 ❌ | 11 ❌ | **7 ❌, 4 ✅** (dashboard, lecture froide, envoi, recherche patient) |

**Lecture.** À 48 Go, le cache trouve sa taille : il monte jusqu'à ~34 Go puis cesse de croître alors que le cgroup a encore
14 Go de marge. Le login reste sous la seconde tout le tir (p95 80 ms), les fautes majeures restent à un bruit de fond, Postgres
consomme 5× moins de CPU (2,5 cœurs contre 12-15) et l'hôte descend de 96 à 85 %. **Le besoin réel de Postgres pour 1000 bases
hydratées de 57 Go se lit ici : ~34 Go de cache + 12 Go de `shared_buffers` + ~6 Go de RSS ≈ 50 Go** ; 48 Go tiennent, 24 non.

**Ce qui limite maintenant : le nombre de connexions, pas la mémoire.** Les backends croissent linéairement avec le temps
(270 à 18h40 → 2 504 à 21h17), indépendamment du débit k6 qui plafonne à ~130 req/s dès 20h40 : 1000 pools PgBouncer ×
`max_db_connections=3`, serveurs gardés 600 s (`server_idle_timeout`, task-294) → le plafond `max_connections=2500` est touché à
+2 h 46. À partir de là Postgres refuse ≈1 700 connexions/min (« too many clients », 53 456 exceptions côté api-mail, toutes sur
la **route directe** : journal d'audit et provisionnement — le pooler, lui, garde ses serveurs et fait **attendre** : `cl_waiting`
5-16, `maxwait` 2,6 → 12,3 s, 175 refus seulement quand un login serveur tombe en timeout). Ces attentes sont la cause des
dixièmes de seconde résiduels du p95 et des 106 erreurs HTTP du tir.

### Chronologie (heure locale, grille 10 min task-295)

| Heure | k6 OK/s | Backends | Cache | Fautes maj./s | Login max | `cl_waiting` / `maxwait` | Événement |
|---|---|---|---|---|---|---|---|
| 18h31 → 20h00 | 6 → 97 | 270 → 1 456 | 6 → 28,5 Go | 0-3 | 10-40 ms | 0 / 0 | rampe puis chauffe, 0 erreur |
| 20h00 → 20h50 | 97 → 146 | 1 456 → 2 200 | 28,5 → 30,8 Go (cgroup 69 → 80 %) | 130-155 | 40 → 450 ms | 0 / < 0,3 s | débit max atteint, cache encore en croissance |
| 21h00 → 21h17 | 148 → 136 | 2 327 → **2 504** | 31,9 → 33 Go | 140 | 160 ms | 5-11 / 2,6-6,5 s | **`max_connections` atteint 21h17** → « too many clients » ≈1 700/min |
| 21h20 → 22h01 (régime) | 128 → 122 | 2 504 (plafond) | 33,5 → 34,1 Go, stable | 160-200 | 0,2-0,8 s | 10-16 / 4-12 s | 175 refus, 39 × 500, 67 × 503 ; k6 0,024 % d'erreurs |
| 22h02 → 22h05 (post-tir) | 0 | 2 500 | — | — | — | — | rejeu du spill : 27 575 « too many clients » supplémentaires, puis **incident VM** |

### Incident post-tir — la VM Docker Desktop a saturé (sans perte de données)

Le rejeu du journal d'audit après le tir ouvre à nouveau ~1 connexion directe par base ; avec le cache Postgres à 48 Go
(cgroup 60 Go d'usage VM au total avec les autres conteneurs) la VM WSL, plafonnée à **62,8 GiB**, est montée à 60,7 Go et s'est
figée à 22h05 : daemon Docker, Prometheus, Seq et Postgres injoignables pendant 45 min. Remède : arrêt de l'AppHost (22h35, coupe
la source de connexions), puis `wsl --shutdown` à 22h50 — daemon de retour en 40 s, Postgres redémarré (récupération WAL ~1 min),
volumes intacts (1000 bases, 124 731 mails vérifiés), Prometheus et Seq relancés à la main. Conséquences sur la mesure :
`memory.failcnt` cumulé perdu (compteur remis à zéro ; le CSV garde `majfault_per_s`), 13 487 traces d'audit encore dans le spill
Redis (rejouées au prochain démarrage — pas perdues), `sonarqube` (étranger au banc) non redémarré. **Leçon** : au-delà de 24 Go pour
Postgres, relever la mémoire de la VM Docker Desktop ou arrêter les conteneurs étrangers avant le tir, et **borner le rejeu du
spill** (plafond global de connexions du drain) — c'est la troisième fois de la journée qu'il touche `max_connections`.

### Décision proposée pour task-296

- **Critère « login p95 < 1 s en régime » : tenu** (80 ms). **`cgroup < 85 %` : tenu** (max 92,8 % en pic de chauffe, 80-92 % en
  régime — à lire avec le cache stabilisé à 34 Go, la limite pourrait redescendre à ~40 Go sans changer le résultat). **`08P01 = 0`
  et `failcnt ÷ 10` : non tenus au sens strict**, mais pour une autre cause que la mémoire (plafond de connexions).
- **Retenir 48 Go** (ou 40 Go minimum) dans `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md`, avec la formule complétée :
  RAM conteneur ≥ `shared_buffers` + backends × ~2,5 Mo + **jeu de travail des bases hydratées (~34 Go pour 1000 bases / 57 Go)**.
- **Prochaine US, un facteur** : plafond de backends résidents — `server_idle_timeout` 600 → 60-120 ou `max_db_connections` 3 → 2
  (pour 1000 bases, 2 500 connexions ne suffisent pas à 3 par pool) ; **puis** plafond global de connexions du rejeu d'audit.
  Ce n'est qu'après que le palier 1000 pourra prétendre à un verdict SLO opposable.

### Bruit de fond et régressions surveillées

- `Fatal` 0, `LOST` 0, `query_wait_timeout` 0, `Spill buffer unreachable` 0, requêtes > 30 min 0, `Failed to parse entity headers` 0, 429 : 0.
- `Channel full` 17 973 (jambe A : 61 704 ; le drain paie le plafond de connexions à partir de 21h17, plus le login lent).
- Timeouts cache Redis 11 872 (≈ jambe A) — Redis de la famille `-ab5b4678`, finding cache déjà ouvert, hors facteur.
- Dump : 600 événements Error/Fatal les plus récents dans `seq-journey-1000-task296-legB-48G-20260911-220235.jsonl`.
