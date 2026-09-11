# Rapport de tir — journey-1000-task296-legA-24G-20260911

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-task296-legA-24G-20260911-175909.json`.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- le multiplexeur PostgreSQL a **refusé** des connexions (2131 refus `server_login_retry` sur la fenêtre) au lieu de les faire attendre : les demandes touchées ont reçu une erreur, et les latences des autres sont des bornes optimistes — refus PgBouncer présents (2131) ET login p95 > 1 s (1.05 s) : **le login lent est la cause probable** — voir `task-294` (réglage du pooler) et `Docs/plan_remediation_fable.md` (phase 0)

À instruire une fois le tir refait :
- à 1000 médecins, 11 étape(s) dépassent le temps de réponse attendu : « Arrivée dashboard », « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) »
- 12 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 15 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.370 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1138084 — **débit émergent global** : 89.9 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 95229 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 89.9 | **1983.3** | 140.5 | **9982.6** | — | 299997.9 | 0.37 | 99.7 | 0 | 0 | 0/247 |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 249858 | 19.83 | 1.47 | 1056.1 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 239 / 2416 (n=84412) |
| 2 | Ouvrir / rafraîchir l'inbox | 1521 / 45614 (n=42220) |
| 3 | Ouvrir un message enrichi (servi base) | 2342 / 7204 (n=21076) |
| 4 | Ouvrir un message froid (fetch IMAP) | 823 / 2342 (n=4059) |
| 5 | Recherche | 11407 / 37524 (n=6370) |
| 6 | Envoi (acquittement UI) | 1185 / 4208 (n=6300) |
| 7 | Télécharger une PJ (~124 Ko) | 3331 / 11190 (n=8409) |
| 8 | Marquer lu | 1121 / 4717 (n=16795) |
| 9 | Rechercher un patient | 119 / 2448 (n=5033) |
| 10 | Ouvrir la page d'un dossier patient | 10938 / 27362 (n=6243) |
| 11 | Fiche patient complète (ressenti médecin) | 28220 / 70885 (n=3115) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 15.0 / 20 | 35.0 / 60 | 4056 | 70885 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 4042 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 2969 ms en moyenne, 60003 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 765 / 1260 (magasin) |
| Backends Postgres (moy/max) | 1257 / 2400 |
| PgBouncer `sv_login` — backends en login (moy/max) | 2 / 157 |
| PgBouncer `cl_waiting` (échant. non nuls) | 279/1881 (15 %) |
| …dont bases **praticien** (échant. non nuls) | 279/1881 (15 %) |
| …dont pool de **maintenance** (échant. non nuls) | 3/1881 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 19253.8 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 19253.8 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 967.0 |
| PgBouncer refus `server_login_retry` (total du palier) | 2099 🔴 refus |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | 0.010 / 1.015 / 307.820 |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 292 / 740 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 13 |
| Backends venant du **pooler** (réseau Docker `172.x`, max) | 2394 |
| Backends **directs** — provisionnement, sonde, journal d'audit (max) | 0 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 134 / 1120 |
| RSS par réplica api-mail, Mo (moy/max) | 1425 / 3924 (5 réplicas) |

- à 1000 médecins : ⚠️ login PostgreSQL > 1 s (p95 1.01 s, max 307.82 s) — l'ouverture d'un backend n'est plus une opération courte ; voir `task-294` (réglage du pooler) et `Docs/plan_remediation_fable.md` (phase 0)
- à 1000 médecins : refus PgBouncer présents (2099) ET login p95 > 1 s (1.01 s) : **le login lent est la cause probable** — voir `task-294` (réglage du pooler) et `Docs/plan_remediation_fable.md` (phase 0)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 95.9 %** des 1000 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⚠️ Chauffe : **10005 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **79 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 239 (300) | 2416 (1500) | 84412 | ❌ |
| 2 | Ouvrir / rafraîchir l'inbox | 1521 (300) | 45614 (1000) | 42220 | ❌ |
| 3 | Ouvrir un message enrichi (servi base) | 2342 (100) | 7204 (500) | 21076 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 823 (800) | 2342 (2500) | 4059 | ❌ |
| 5 | Recherche | 11407 (500) | 37524 (2000) | 6370 | ❌ |
| 6 | Envoi (acquittement UI) | 1185 (1000) | 4208 (3000) | 6300 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 3331 (500) | 11190 (2000) | 8409 | ❌ |
| 8 | Marquer lu | 1121 (200) | 4717 (1000) | 16795 | ❌ |
| 9 | Rechercher un patient | 119 (300) | 2448 (1500) | 5033 | ❌ |
| 10 | Ouvrir la page d'un dossier patient | 10938 (500) | 27362 (2000) | 6243 | ❌ |
| 11 | Fiche patient complète (ressenti médecin) | 28220 (1500) | 70885 (4000) | 3115 | ❌ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 42220 | 15037 | 45614 | 634865.2 | 64.3 % |
| 🔴 | Recherche (`search`) | 6370 | 15402 | 37524 | 98111.2 | 9.9 % |
| 🔴 | Ouvrir un message enrichi (servi base) (`read_content`) | 21076 | 2923 | 7204 | 61602.4 | 6.2 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 84412 | 689 | 2416 | 58178.9 | 5.9 % |
| 🔴 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 3115 | 12076 | 27362 | 37615.2 | 3.8 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 8409 | 4316 | 11190 | 36289.9 | 3.7 % |
| 🔴 | Marquer lu (`mark_read`) | 16795 | 1653 | 4717 | 27766.8 | 2.8 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 6300 | 2241 | 4208 | 14115.4 | 1.4 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 2028 | 5713 | 14161 | 11586.1 | 1.2 % |
| 🔴 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 4059 | 1027 | 2342 | 4167.2 | 0.4 % |
| 🟠 | Rechercher un patient (`patient_search`) | 5033 | 473 | 2448 | 2378.5 | 0.2 % |
| 🟠 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 3128 | 380 | 1399 | 1189.6 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 8 🔴 · 4 🟠 · 0 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Ouvrir / rafraîchir l'inbox** (`read_list`, 634865.2 s, 64.3 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (15037 ms)
  - **dispersion p95/p50 = 30.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 98111.2 s, 9.9 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (15402 ms)
  - **dispersion p95/p50 = 3.3×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 61602.4 s, 6.2 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2923 ms)
  - **dispersion p95/p50 = 3.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Arrivée dashboard** (`dashboard`, 58178.9 s, 5.9 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 10.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 37615.2 s, 3.8 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (12076 ms)
- **Télécharger une PJ (~124 Ko)** (`attachment`, 36289.9 s, 3.7 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (4316 ms)
  - **dispersion p95/p50 = 3.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Marquer lu** (`mark_read`, 27766.8 s, 2.8 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1653 ms)
  - **dispersion p95/p50 = 4.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Envoi (acquittement UI)** (`send`, 14115.4 s, 1.4 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2241 ms)
  - **dispersion p95/p50 = 3.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 11586.1 s, 1.2 %)
  - **coût par appel élevé** (5713 ms)
  - **dispersion p95/p50 = 3.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message froid (fetch IMAP)** (`read_content_cold`, 4167.2 s, 0.4 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1027 ms)
- **Rechercher un patient** (`patient_search`, 2378.5 s, 0.2 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 20.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_opposition`, 1189.6 s, 0.1 %)
  - **dispersion p95/p50 = 6.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 21105 | 491 | 1565 | 15887.3 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 21103 | 67 | 834 | 7412.2 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 21102 | 625 | 5054 | 28332.3 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 21102 | 31 | 1011 | 6547.1 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 21110 | 115 | 629 | 5523.2 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 21110 | 29325 | 50309 | 629342.0 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folders`** (5054 ms de p95, 625 ms de p50, n=21102), qui porte **aussi** le temps serveur de l'étape (28332.3 s, 49 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (50309 ms de p95, 29325 ms de p50, n=21110), qui porte **aussi** le temps serveur de l'étape (629342.0 s, 99 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 38271 | 1637.2 | 239.4 | 4533.1 | 6765.6 | 120000.5 |
| attachment,palier:1000 | 8409 | 4315.6 | 3331.0 | 8435.7 | 11190.3 | 120000.5 |
| attachment,palier:transition | 121 | 2802.3 | 1668.1 | 6987.7 | 8232.1 | 21458.6 |
| dashboard | 383696 | 350.5 | 99.0 | 829.2 | 1244.7 | 60008.9 |
| dashboard,call:coverage,palier:1000 | 21102 | 310.3 | 31.0 | 545.7 | 1010.9 | 60001.7 |
| dashboard,call:coverage,palier:transition | 8 | 30.5 | 31.7 | 52.8 | 66.6 | 80.4 |
| dashboard,call:folder,palier:1000 | 21105 | 752.8 | 490.6 | 1213.9 | 1564.9 | 60008.9 |
| dashboard,call:folder,palier:transition | 8 | 398.1 | 442.4 | 480.0 | 489.7 | 499.4 |
| dashboard,call:folders,palier:1000 | 21102 | 1342.6 | 624.8 | 3414.5 | 5054.1 | 60000.5 |
| dashboard,call:folders,palier:transition | 8 | 15.1 | 14.8 | 21.4 | 22.0 | 22.6 |
| dashboard,call:today,palier:1000 | 21103 | 351.2 | 66.9 | 653.8 | 834.1 | 60002.1 |
| dashboard,call:today,palier:transition | 8 | 472.3 | 477.1 | 516.2 | 527.2 | 538.2 |
| dashboard,palier:1000 | 84412 | 689.2 | 239.4 | 1365.5 | 2416.4 | 60008.9 |
| dashboard,palier:transition | 32 | 229.0 | 62.9 | 492.3 | 502.7 | 538.2 |
| mark_read | 76429 | 692.4 | 111.5 | 1715.8 | 2765.9 | 60000.1 |
| mark_read,palier:1000 | 16795 | 1653.3 | 1120.8 | 3381.8 | 4716.6 | 60000.1 |
| mark_read,palier:transition | 237 | 940.9 | 397.5 | 2392.5 | 3529.6 | 8506.2 |
| patient_docs | 205855 | 1908.5 | 93.6 | 6177.1 | 8765.5 | 60018.4 |
| patient_docs,palier:1000 | 46791 | 5449.1 | 4115.1 | 11319.7 | 14518.1 | 60018.4 |
| patient_docs,palier:transition | 842 | 1032.4 | 383.0 | 3000.8 | 4650.2 | 10763.3 |
| patient_dossier | 13916 | 4832.9 | 489.8 | 16589.4 | 22248.5 | 59999.5 |
| patient_dossier,palier:1000 | 3115 | 12075.5 | 10938.3 | 24263.7 | 27361.6 | 59999.5 |
| patient_dossier,palier:transition | 49 | 4642.4 | 3367.3 | 11155.5 | 14921.6 | 20133.8 |
| patient_opposition | 13916 | 142.3 | 15.8 | 259.2 | 368.0 | 59999.4 |
| patient_opposition,palier:1000 | 3128 | 380.3 | 207.7 | 598.8 | 1398.7 | 59999.4 |
| patient_opposition,palier:transition | 57 | 123.3 | 31.2 | 151.5 | 632.5 | 1832.8 |
| patient_search | 22673 | 167.5 | 10.7 | 187.9 | 478.9 | 60003.4 |
| patient_search,palier:1000 | 5033 | 472.6 | 118.8 | 982.7 | 2447.8 | 60003.4 |
| patient_search,palier:transition | 72 | 745.7 | 23.5 | 3305.4 | 4442.1 | 11823.7 |
| read_content | 95872 | 1150.5 | 155.4 | 3117.8 | 4403.3 | 60002.0 |
| read_content,palier:1000 | 21076 | 2922.9 | 2341.9 | 5440.1 | 7204.0 | 60002.0 |
| read_content,palier:transition | 358 | 1755.0 | 953.3 | 4488.7 | 6216.0 | 16270.8 |
| read_content_cold | 18259 | 733.5 | 516.2 | 1134.4 | 1507.1 | 20069.1 |
| read_content_cold,palier:1000 | 4059 | 1026.7 | 823.4 | 1522.3 | 2341.6 | 20069.1 |
| read_content_cold,palier:transition | 40 | 651.2 | 512.9 | 929.9 | 1174.5 | 2319.9 |
| read_list | 191845 | 6068.1 | 164.5 | 27062.9 | 36435.7 | 60012.1 |
| read_list,call:emails,palier:1000 | 21110 | 29812.5 | 29325.1 | 45585.9 | 50308.8 | 60012.1 |
| read_list,call:emails,palier:transition | 84 | 14687.4 | 15531.7 | 23526.0 | 24721.0 | 25559.9 |
| read_list,call:folder,palier:1000 | 21110 | 261.6 | 115.4 | 441.6 | 628.9 | 60004.7 |
| read_list,call:folder,palier:transition | 85 | 136.2 | 28.8 | 191.9 | 421.9 | 3171.3 |
| read_list,palier:1000 | 42220 | 15037.1 | 1521.0 | 40064.6 | 45614.4 | 60012.1 |
| read_list,palier:transition | 169 | 7368.7 | 212.1 | 20447.5 | 23468.1 | 25559.9 |
| search | 28963 | 5786.9 | 820.2 | 17764.7 | 27281.9 | 120000.2 |
| search,palier:1000 | 6370 | 15402.1 | 11407.1 | 31715.7 | 37524.2 | 120000.2 |
| search,palier:transition | 94 | 8051.5 | 7143.8 | 15841.3 | 18762.3 | 21570.1 |
| send | 28287 | 1192.4 | 847.5 | 1819.6 | 2561.9 | 120000.0 |
| send,palier:1000 | 6300 | 2240.5 | 1185.0 | 2998.0 | 4207.5 | 120000.0 |
| send,palier:transition | 92 | 1219.3 | 899.7 | 2844.9 | 3845.0 | 8126.1 |
| treatment | 9093 | 2125.3 | 284.4 | 5900.7 | 8775.1 | 299997.9 |
| treatment,palier:1000 | 2028 | 5713.1 | 4077.7 | 11159.6 | 14161.3 | 299997.9 |
| treatment,palier:transition | 25 | 3604.4 | 3210.8 | 5699.9 | 6886.7 | 16398.9 |
| warmup | 11000 | 2968.9 | 409.5 | 9166.4 | 15010.9 | 60003.1 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-11T12:28:05.301000+00:00 → 2026-09-11T15:59:09.038000+00:00 (12664 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-142753.csv`) | ✅ 225693 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-38444` | 0.62 | 8 | 25 | 0.031 | 42.06 |
| `DESKTOP-DEV-X2C-44332` | 0.62 | 10 | 20 | 0.034 | 27.53 |
| `DESKTOP-DEV-X2C-50740` | 0.59 | 7 | 20 | 0.036 | 72.80 |
| `DESKTOP-DEV-X2C-52420` | 0.59 | 4 | 21 | 0.026 | 34.47 |
| `DESKTOP-DEV-X2C-53896` | 0.56 | 9 | 20 | 0.028 | 34.82 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#31916` | 0.01 | 0.30 | 41 |
| `com.docker.backend#34656` | 1.83 | 5.05 | 1407 |
| `dcp#12672` | 0.00 | 0.25 | 12 |
| `dcp#23804` | 0.00 | 0.04 | 12 |
| `dcp#29016` | 0.00 | 0.00 | 11 |
| `dcp#37152` | 0.00 | 0.05 | 12 |
| `dcp#38072` | 0.70 | 2.40 | 1277 |
| `dcp#41264` | 0.00 | 0.14 | 41 |
| `dcp#43056` | 0.00 | 0.20 | 12 |
| `dcp#50200` | 0.00 | 0.10 | 12 |
| `dcp#54620` | 0.00 | 0.20 | 12 |
| `dcp#5604` | 0.00 | 0.00 | 12 |
| `k6#51960` | 0.17 | 3.38 | 2060 |
| `mss.mail.api#38444` | 0.30 | 2.12 | 3443 |
| `mss.mail.api#44332` | 0.28 | 1.83 | 3302 |
| `mss.mail.api#50740` | 0.31 | 1.95 | 3924 |
| `mss.mail.api#52420` | 0.30 | 1.80 | 3262 |
| `mss.mail.api#53896` | 0.28 | 1.51 | 3225 |
| `vmmemWSL#34068` | 5.73 | 16.84 | 50614 |
| `loadtest-otel-collector-kcgvpthu` | 0.02 | 0.19 | 129 |
| `loadtest-pgbouncer-fcmfffxc` | 0.43 | 1.04 | 31 |
| `mss-mail-grafana-ab5b4678` | 0.01 | 0.14 | 153 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.03 | 153 |
| `mss-mail-prometheus-ab5b4678` | 0.01 | 0.91 | 268 |
| `mss-mail-prometheus-b6152948` | 0.00 | 0.00 | 210 |
| `mss-mail-rabbitmq-thqqgbnc` | 0.01 | 0.03 | 135 |
| `mss-mail-redis-ab5b4678` | 0.19 | 1.17 | 2869 |
| `mss-mail-redis-b6152948` | 0.00 | 0.02 | 46 |
| `mss-mail-seq-ab5b4678` | 0.01 | 0.08 | 164 |
| `mss-mail-seq-b6152948` | 0.00 | 0.01 | 164 |
| `postgres-pgvector` | 2.78 | 15.59 | 23470 |

- **Hôte** : CPU 54.5 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 91
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 3577, cl_waiting max 78, cl_waiting_maintenance max 2, cl_waiting_practitioner max 78, count max 1002, login_retry_delta max 440, maxwait_maintenance_ms max 967, maxwait_ms max 19254, maxwait_practitioner_ms max 19254, sv_active max 553, sv_idle max 1091, sv_login max 157
- **Backends Postgres** : cache_mb max 21143, direct max 0, idle_over_60s max 995, majfault_per_s max 1516, pooler max 2394, practitioner_databases max 2389, rss_mb max 3783, seconds max 308, started_last_60s max 740, total max 2400, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 17600.0 | 2487 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 4975.3 | 2487 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 25941.5 | 2487 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 2478 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 4085.5 | 2487 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 26090.9 | 2487 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 12437.5 | 2487 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 60000.0 | 2487 |
| `api/v{version:apiVersion}/Mail/sendmail` | 8312.5 | 2487 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 7500.0 | 2485 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 53500.0 | 2485 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 4593.7 | 2485 |
| `api/v{version:apiVersion}/Search/semantic` | 58612.5 | 2487 |
| `api/v{version:apiVersion}/Sync/coverage` | 4095.0 | 2487 |

- **p95 client global (k6)** : 9982.6 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -50017.4 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.47 |
| Documents CDA /s | 0.47 |
| Durée traitement CDA (s, p95) | 2.35 |
| Événements de session IMAP /s | 1.45 |
| Recherches (s, p95) | 58.574 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 4338.8 | 29000 | 8.3 (0.2 %), p95 1975 | 3978.1 (91.7 %), p95 29000 | 352.4 (8.1 %), p95 9750 |
| `GetMail` | 11.4 | 1790.5 | 26719 | 106.2 (5.9 %), p95 4386 | 1261.9 (70.5 %), p95 25874 | 422.4 (23.6 %), p95 217 |
| `GetMailsByUids` | 14.7 | 8928.6 | 60000 | 10.0 (0.1 %), p95 5 | 1571.8 (17.6 %), p95 27850 | 7346.8 (82.3 %), p95 57280 |

- **`EnrichPersistMail`** — sur 4338.8 ms en moyenne (7.9 requête(s) SQL par appel) : 8.3 ms attente d'une connexion, 3978.1 ms exécution SQL, 352.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 1790.5 ms en moyenne (11.4 requête(s) SQL par appel) : 106.2 ms attente d'une connexion, 1261.9 ms exécution SQL, 422.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 8928.6 ms en moyenne (14.7 requête(s) SQL par appel) : 10.0 ms attente d'une connexion, 1571.8 ms exécution SQL, 7346.8 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.0 | 422.4 | 42159.1 | 0.9 | 1.3 | 0.9 | 2.5 | non relevé | 0.0 | 0.9 | 2.3 | 0.1 | 0.9 | non relevé | 0.2 |
| `GetMailsByUids` | 240.7 | 7346.8 | 30529.0 | 21.6 | 32.9 | 21.6 | 35.1 | 21.6 | 0.0 | 21.6 | 6.7 | 0.0 | 21.5 | 51.9 | 6.2 |

- **`GetMail`** — sur 422.4 ms de matérialisation, l'appel a construit 10.0 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.5 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.3 résultats de biologie, 0.1 éléments de synthèse, 0.9 corps de messages, 0.2 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **42159.1 µs**.

- **`GetMailsByUids`** — sur 7346.8 ms de matérialisation, l'appel a construit 240.7 objets, dont 21.6 messages, 32.9 étiquettes, 21.6 destinataires, 35.1 pièces jointes, 21.6 identifiants enrichis, 0.0 acquittements, 21.6 documents médicaux, 6.7 résultats de biologie, 0.0 éléments de synthèse, 21.5 corps de messages, 51.9 objets de fil, 6.2 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **30529.0 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **7.2 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.2 | 5336.5 | 57750 | 149.6 (2.8 %), p95 475 | 32.9 (0.6 %), p95 242 | 33.6 (0.6 %), p95 725 | 4636.6 (86.9 %), p95 29000 | 483.9 (9.1 %), p95 9750 |

- **Enrichir un message** — sur 5336.5 ms en moyenne (5.2 message(s) par requête) : 149.6 ms fetch IMAP, 32.9 ms extraction XDM, 33.6 ms parsing CDA, 4636.6 ms écritures base, 483.9 ms le reste (DTO, notifications). **Poste dominant : écritures base.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 336.5 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 1264.6 | 2178 | 0.0 (0.0 %), p95 5 | 303.6 (24.0 %), p95 1152 | 210.0 (16.6 %), p95 645 | 418.3 (33.1 %), p95 496 | 505.8 (40.0 %), p95 1606 | 332.6 (26.3 %), p95 75 |

- **Envoyer un message** — sur 1264.6 ms en moyenne : 0.0 ms garde d'opposition, 303.6 ms construction MIME, 210.0 ms obtention de session SMTP, 418.3 ms transmission + acquittement, 505.8 ms archivage Sent, 332.6 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.488 | 7.375 | 0.05 |
| `imap_session` | 0.549 | 2.898 | 38.73 |
| `in_process_fetch` | 0.005 | 7.375 | 0.05 |
| `smtp_session` | 0.029 | 2.450 | 4.09 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.021 | 3.833 | 5.000 | 3.856 | 4.05 |
| `EnrichEmails` | 0.005 | 2.275 | 2.425 | 2.275 | 0.71 |
| `GetAttachmentStream` | 1.600 | 26.500 | 29.000 | 26.500 | 0.71 |
| `GetEmailContent` | 0.005 | 4.536 | 4.875 | 4.536 | 2.80 |
| `GetFolders` | 0.364 | 27.667 | ≥ 60 ⚠️ | 3.319 | 3.53 |
| `ProcessEmailUid` | 0.005 | 4.875 | — | 4.875 | 0.05 |
| `ReadFolder` | 1.348 | 3.092 | ≥ 60 ⚠️ | 3.121 | 19.33 |
| `UpdateFlag` | 0.640 | 2.788 | 7.250 | 2.788 | 10.44 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.700** | 0.784 | 0.953 | 0.0 % |
| `EnrichEmails` | **0.477** | 0.675 | 2.275 | 1.6 % |
| `GetAttachmentStream` | **4.656** | 20.000 | 25.500 | 100.0 % |
| `GetEmailContent` | **0.972** | 1.770 | 2.775 | 4.9 % |
| `GetFolders` | **0.476** | 0.662 | 0.920 | 0.0 % |
| `ProcessEmailUid` | **0.487** | 0.738 | 0.988 | 0.0 % |
| `ReadFolder` | **0.713** | 0.748 | 1.257 | 0.0 % |
| `UpdateFlag` | **0.858** | 1.365 | 1.718 | 0.0 % |

- 🟠 **`EnrichEmails` : pointe non représentative.** Médiane **0.477 s**, p90 0.675 s, mais une pointe à 2.275 s sur 1.6 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🔴 **`GetAttachmentStream` : détention tenue en régime** — médiane 4.656 s et **100.0 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🟠 **`GetEmailContent` : pointe non représentative.** Médiane **0.972 s**, p90 1.770 s, mais une pointe à 2.775 s sur 4.9 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.

> ⚠️ **Pourquoi cette table existe** (task-276). La table qui la précède réduit chaque série à sa **pointe**. Au tir du 2026-08-29, `ReadFolder` y valait 11,871 s — lu comme « la fusion de task-270 a allongé la section critique », alors que sa médiane en régime valait 0,469 s, **sous** les 0,692 s de l'opération qu'elle remplace. La pointe était réelle ; la conclusion qu'on en tirait, non. Même famille de piège que les buckets en millisecondes (task-211), le plafond d'histogramme (task-245) et la saturation lue comme un timeout (task-271).
| Voie | Acquisitions /s |
|---|---|
| `read` | 38.73 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.021 s au p95, contre 1.600 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

> ⓘ **PgBouncer — transitoire d'attente, écarté du verdict.** 280 échantillon(s) sur 1891 portent une attente cliente non nulle (14.8 %, pointe à 78), sous le seuil de présence soutenue de 25 %. Ce profil est celui d'une **ouverture de palier**, pas d'un pooler qui n'absorbe plus — il ne désigne donc pas de facteur limitant. À surveiller tout de même : sur la campagne du 2026-07-29, cette pointe croît avec la charge.

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| conteneur `postgres-pgvector` (CPU) | 15.59 cœurs | 24 cœurs | 65.0 % | 0.0 % — transitoire |
| processus `k6#51960` (CPU) | 3.38 cœurs | 24 cœurs | 14.1 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-44332` | 10.00 éléments | 100 éléments | 10.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#38444` (CPU) | 2.12 cœurs | 24 cœurs | 8.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#50740` (CPU) | 1.95 cœurs | 24 cœurs | 8.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#44332` (CPU) | 1.83 cœurs | 24 cœurs | 7.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#52420` (CPU) | 1.80 cœurs | 24 cœurs | 7.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#53896` (CPU) | 1.51 cœurs | 24 cœurs | 6.3 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (conteneur `postgres-pgvector` (CPU)) monte à 65.0 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## Vérification par base (propriété + complétude)

> ⚠️ La vérification automatique a tourné **pendant la tempête de connexions post-tir** (Postgres à `max_connections`,
> « sorry, too many clients already ») et a rendu « aucune base trouvée » à tort. Rejouée à 18h05, Postgres revenu à 6 connexions :

- **Bases inspectées** : 1000
- **Mails stockés (total)** : 123949 — dont **123949** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Attendu par boîte** : 247 (complétude relative au périmètre du scénario)
- **Verdict propriété** : PASS

`SUMMARY dbs=1000 mails=123949 owned=123949 foreign=0 unmarked=0 expected_per_user=247 verdict=PASS`

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-1000-task296-legA-24G-20260911-175909.jsonl`.

### Objet du tir — task-296, jambe A : Postgres du banc à **24 Go** (au lieu de 12), un seul facteur

A/B contre le tir de référence 12 Go du matin (`report-journey-1000-postlot-292-294-20260911-123951.md`, même jour, mêmes 1000
bases hydratées gardées, même plan journey, journal d'audit actif). **Système sous test identique** : `d04f2ca`, servi depuis un
worktree détaché `Api/Mail-ref` (le tip de `develop`, `5855604`, embarque `cf685ac` qui change ~40 paquets de production — exclu
pour ne pas ajouter un second facteur). Harnais k6 / `observe.ps1` / `report.py` : `develop` avec task-295 (coût du login,
churn des backends, pression du cgroup — **première lecture sur la même grille de temps**). Postgres recréé à 14h05
(`limits.memory` 24G, `effective_cache_size` 16GB, `shared_buffers` 4GB, `max_connections` 2500), cache de pages froid au
départ comme le matin. RTT 5 ms → `LATENCY_MS=96`. Fenêtre 14h28 → 17h58, régime 17h20 → 17h58. k6 exit 0.

### Verdict — 🔴 ROUGE encore, mais la panne recule de 2 h 20 et s'affaiblit d'un facteur 30 à 50 : **24 Go ne suffisent pas**, jambe B requise

| Grandeur | Référence 12 Go (matin) | **Jambe A 24 Go** | Rapport |
|---|---|---|---|
| Erreurs k6 tir complet / **régime** | 11,98 % / ~28 % | **0,37 % / 1,5 %** | ÷32 / ÷19 |
| Refus PgBouncer `08P01 server_login_retry` | 110 693 | **2 099** (Seq : 1 955) | ÷53 |
| HTTP 500 / 503 (Seq) | 74 603 / 56 446 | **2 244 / 1 069** | ÷33 / ÷53 |
| Requêtes serveur > 30 min / file active max | 3 105 / 9 782 | **0 / 927** | — |
| Début des timeouts Npgsql → premier `08P01` | +1 h 47 (10h55) → +2 h 01 (11h10) | **+2 h 32 (17h00) → +2 h 52 (17h20)** | +45 min / +51 min |
| Login Postgres (sonde task-295) p50 / p95 / max | non instrumenté (10-16 s au `psql` manuel le 09/09) | **10 ms / 1,0 s / 307,8 s** | — |
| Backends créés / 60 s (moy / max) | 344 → 0 pendant la panne | **292 / 740**, 0 à 17h20 | — |
| `sv_login` max / `cl_waiting` (% relevés) / `maxwait` max | 467 / 13 % / 19,1 s | **157 / 15 % / 19,3 s** | — |
| Fautes de page majeures (cumul tir / max par s) | 9,2 M / — | **3,87 M / 1 120 par s** | ÷2,4 |
| `memory.failcnt` (cumul tir) | 159 M | **50,2 M** | ÷3,2 |
| CPU Postgres régime (cœurs) / hôte | 11,3 – 15 / 96-100 % | **12 – 12,8 / 92-96 %** | ≈ |
| Journal d'audit : émises = persistées / `LOST` / `Channel full` | 175 651 = 175 651 / 0 / 12 030 (mi-tir) | **191 459 = 191 459 / 0 / 61 704** | 0 perte les deux fois |
| Timeouts cache Redis | 201 | **11 725** | ×58 (Redis neuf, cache froid — hors sujet task-296) |
| Verdict SLO (11 étapes) | 8 ❌ | **11 ❌** (contaminé par les refus en régime) | non opposable les deux fois |

### Chronologie de la jambe A (heure locale, grille 10 min de l'échantillonneur task-295)

| Heure | k6 OK/s | Backends | Créés/60 s | Cache cgroup | Fautes maj./s | Login max | `sv_login` | Refus `08P01` |
|---|---|---|---|---|---|---|---|---|
| 14h28 → 15h20 | 10 → 67 | 800 → 900 | 40 → 240 | 8 → **20,5 Go, cgroup à 100 %** dès 15h20 | 0 | 13-20 ms | 0 | 0 |
| 15h20 → 16h00 | 67 → 114 | 900 → 1 500 | 240 → 400 | 20,5 → 17,8 Go (le cache recule) | 0 → **153** | 20-40 ms | 0-1 | 0 |
| 16h00 → 16h40 | 114 → 133 | 1 500 → 2 070 | 400 → 516 | 17,8 → 15,4 Go | 187 → **704** | 90 ms → **1,6 s** | 1-2 | 0 |
| 16h40 → 17h00 | 133 → 115 | 2 070 → 2 125 (`max_connections` 2 500 en vue) | 460 → 230 | 15,4 → 14,6 Go | 830 → 976 | **4 → 5,3 s** | 3 → 7 | 0 |
| **17h00 → 17h10** | 106 → 101 | 2 060 | 230 → **104** | 14,6 Go | 960 | **307 s** | 56 | 0 → premiers timeouts Npgsql, 138 × 500 |
| **17h20 → 17h58 (régime)** | 109 → 96 | 1 650 → 1 870 | **0 → 111** | 14,6 Go | 960 → **1 120** | 160-190 s | 136 → **157** | **53 → 440 par 10 min**, 503 en rafale |
| 18h00 → 18h05 (post-tir) | 0 | **2 473 → 2 500** | 592 → 1 114 | 14,1 Go | 693 | 10 ms | 0 | rejeu du spill : 29 000 « too many clients », `psql` refusé 6 min |

### Causes — ce que la jambe A établit

1. **La mémoire est bien le facteur, mais 24 Go restent en dessous du jeu de travail.** Le cgroup atteint 100 % à 15h20, puis
   le cache de pages recule de 20,5 à 14,6 Go pendant que les backends montent de 900 à 2 100 (≈ 2 Mo de RSS chacun, 3,5 Go au
   pic) : chaque nouveau backend est pris sur le cache. Les fautes majeures démarrent exactement quand le cache passe sous ~18 Go
   (16h00), le login dépasse 1 s à 16h40 (cache < 15,5 Go), et la spirale connue (`sv_login` → `server_connect_timeout` →
   `server_login_retry` en cache → `08P01`) s'amorce à 17h10. C'est la même mécanique que le matin, déclenchée **2 h 20 plus
   tard** et **30 à 50 fois moins violente** parce que le cache disponible est deux fois plus grand.
2. **Le nombre de backends est le second terme de l'équation, et il suit le temps, pas la charge.** 1000 pools PgBouncer ×
   `max_db_connections=3` avec `server_idle_timeout=600` (task-294) laissent les serveurs vivre 10 min : les backends croissent
   linéairement de 800 à 2 100 sur 2 h alors que le débit k6 plafonne à ~130 req/s dès 16h20. À 1000 bases, **chaque backend a son
   catalogue** (une base = un jeu de catalogues système) : le login d'une base froide relit son catalogue sur disque quand le cache ne le
   tient plus — c'est ce qui fait un login à 300 s. *Mesuré* : la corrélation backends ↔ fautes ↔ login ; *lu dans le code / la
   conf* : le mécanisme catalogue par base.
3. **Le journal d'audit tient (0 perte) mais son rejeu post-tir sature encore Postgres** : 2 473 → 2 500 backends à 18h00, 29 000
   « too many clients », administration refusée 6 min (même finding que le matin ; la vérification automatique du rapport y a
   échoué et a été rejouée à la main).
4. **Hors facteur** : timeouts Redis ×58 (Redis de la nouvelle famille de conteneurs, cache froid, `HMSET mail:email:*` 1,5 Mo —
   finding cache déjà ouvert) ; `Channel full` ×5 (le drain d'audit paie lui aussi le login lent, drain série task-292).

### Décision proposée pour task-296

- **Jambe B nécessaire** : 32 Go **et** `shared_buffers` 8 Go, comme prévu par l'US si la jambe A ne ramène pas le login sous 1 s
  en régime (ici : p95 1,0 s sur le tir, 160-300 s en régime). Prévoir que le jeu de travail utile de 1000 bases hydratées
  (57 Go) n'entrera pas non plus dans 32 Go : la jambe B mesurera la **pente** (délai d'apparition et intensité de la spirale),
  pas forcément sa disparition.
- **À instruire en parallèle, hors task-296 (un facteur par jambe)** : plafond de backends résidents (`server_idle_timeout`
  600 → 60-120, ou `max_db_connections` 3 → 2) pour découpler le nombre de backends du temps ; cache d'échec de login
  PgBouncer (`server_login_retry`) ; plafond global de connexions du rejeu d'audit.
- **Ce que la jambe A n'établit pas** : la capacité au palier 1000 (tir ROUGE, refus en régime) et le comportement à Redis chaud.

### Bruit de fond et régressions surveillées

- `Parsing completed` 510 (bases hydratées, chauffe court-circuitée) ; `Failed to parse entity headers` 0 ; 429 : 0 ;
  `Spill buffer unreachable` 0 ; `query_wait_timeout` 79 (attente task-294 conforme) ; `LOST` 0 ; Fatal 0.
- Requêtes > 30 min côté serveur : **0** (3 105 le matin) — le convoi derrière le verrou de session IMAP n'apparaît qu'avec des
  refus massifs.
- Dump : 600 événements Error/Fatal les plus récents dans `seq-journey-1000-task296-legA-24G-20260911-175909.jsonl`.
