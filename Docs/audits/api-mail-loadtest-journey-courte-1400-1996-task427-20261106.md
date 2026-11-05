# Rapport de tir — journey-courte-1400-1996-20261105-task427-recherche

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261105-task427-recherche-235108.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 3 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 16 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.010 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 751772 — **débit émergent global** : 332.5 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53348 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 332.5 | **179.4** | 79.4 | **656.8** | — | 9469.5 | 0.01 | 100.0 | 0 | 0 | 241716/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 212521 | 288.36 | 0.00 | 784.0 |
| **1996 médecins** | 1080 | 933 | 381222 | 408.60 | 0.01 | 1435.8 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 67 / 554 (n=63568) | 86 / 579 (n=113144) |
| 2 | Ouvrir / rafraîchir l'inbox | 47 / 106 (n=31794) | 74 / 202 (n=56548) |
| 3 | Ouvrir un message enrichi (servi base) | 42 / 76 (n=15895) | 77 / 170 (n=28300) |
| 4 | Ouvrir un message froid (fetch IMAP) | 454 / 520 (n=6350) | 477 / 558 (n=11310) |
| 5 | Recherche | 335 / 623 (n=4687) | 384 / 704 (n=8548) |
| 6 | Envoi (acquittement UI) | 503 / 932 (n=4767) | 521 / 986 (n=8535) |
| 7 | Télécharger une PJ (~124 Ko) | 46 / 641 (n=6230) | 107 / 786 (n=11328) |
| 8 | Marquer lu | 45 / 95 (n=12664) | 84 / 162 (n=22677) |
| 9 | Rechercher un patient | 61 / 77 (n=4626) | 68 / 111 (n=8502) |
| 10 | Ouvrir la page d'un dossier patient | 63 / 112 (n=7038) | 99 / 238 (n=12772) |
| 11 | Fiche patient complète (ressenti médecin) | 351 / 561 (n=3519) | 549 / 1119 (n=6386) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.1 / 65 | 7982 | 561 |
| **1996 médecins** | 14.5 / 20 | 34.2 / 65 | 14192 | 1119 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2236 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 739 ms en moyenne, 9469 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2250 / 3084 (magasin) | 2250 / 3084 (magasin) |
| Backends Postgres (moy/max) | 1240 / 1435 | 1987 / 2025 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 30/186 (16 %) | 70/156 (45 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/186 (0 %) | 0/156 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 30/186 (16 %) | 70/156 (45 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 22.4 | 116.4 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 22.4 | 116.4 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 122 / 376 | 96 / 266 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 98 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1403 | 1994 |
| Backends **directs** — audit + provisionnement (max) | 29 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 4 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 0 / 0 |
| RSS par réplica api-mail, Mo (moy/max) | 1205 / 1744 (5 réplicas) | 2236 / 2573 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1435.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2025.0 / 2500** (81.0 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 100.0 %** des 1996 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⓘ Chauffe : **303 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 67 (300) | 554 (1500) | 63568 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 47 (300) | 106 (1000) | 31794 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 42 (100) | 76 (500) | 15895 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 454 (800) | 520 (2500) | 6350 | ✅ |
| 5 | Recherche | 335 (500) | 623 (2000) | 4687 | ✅ |
| 6 | Envoi (acquittement UI) | 503 (1000) | 932 (3000) | 4767 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 46 (500) | 641 (2000) | 6230 | ✅ |
| 8 | Marquer lu | 45 (200) | 95 (1000) | 12664 | ✅ |
| 9 | Rechercher un patient | 61 (300) | 77 (1500) | 4626 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 63 (500) | 112 (2000) | 7038 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 351 (1500) | 561 (4000) | 3519 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 86 (300) | 579 (1500) | 113144 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 74 (300) | 202 (1000) | 56548 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 77 (100) | 170 (500) | 28300 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 477 (800) | 558 (2500) | 11310 | ✅ |
| 5 | Recherche | 384 (500) | 704 (2000) | 8548 | ✅ |
| 6 | Envoi (acquittement UI) | 521 (1000) | 986 (3000) | 8535 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 107 (500) | 786 (2000) | 11328 | ✅ |
| 8 | Marquer lu | 84 (200) | 162 (1000) | 22677 | ✅ |
| 9 | Rechercher un patient | 68 (300) | 111 (1500) | 8502 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 99 (500) | 238 (2000) | 12772 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 549 (1500) | 1119 (4000) | 6386 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 113144 | 181 | 579 | 20533.5 | 40.2 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8535 | 655 | 986 | 5590.5 | 10.9 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11310 | 481 | 558 | 5439.3 | 10.6 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 56548 | 90 | 202 | 5105.6 | 10.0 % |
| 🟢 | Recherche (`search`) | 8548 | 435 | 704 | 3715.2 | 7.3 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 11328 | 255 | 786 | 2883.2 | 5.6 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28300 | 87 | 170 | 2467.3 | 4.8 % |
| 🟢 | Marquer lu (`mark_read`) | 22677 | 89 | 162 | 2015.8 | 3.9 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 7096 | 226 | 914 | 1603.7 | 3.1 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6386 | 114 | 238 | 725.2 | 1.4 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8502 | 66 | 111 | 564.8 | 1.1 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6386 | 77 | 115 | 490.3 | 1.0 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 3 🟠 · 9 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 20533.5 s, 40.2 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 6.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 2883.2 s, 5.6 %)
  - **dispersion p95/p50 = 7.3×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 1603.7 s, 3.1 %)
  - **dispersion p95/p50 = 7.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15892 | 394 | 988 | 6201.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15892 | 66 | 506 | 2304.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15892 | 30 | 170 | 868.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15892 | 64 | 81 | 1039.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15897 | 23 | 124 | 606.0 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15897 | 59 | 98 | 1014.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28286 | 407 | 927 | 11477.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28286 | 82 | 526 | 4509.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28286 | 56 | 218 | 2334.1 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28286 | 76 | 120 | 2212.4 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28274 | 42 | 155 | 1730.6 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28274 | 107 | 218 | 3375.0 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (927 ms de p95, 407 ms de p50, n=28286), qui porte **aussi** le temps serveur de l'étape (11477.4 s, 56 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (218 ms de p95, 107 ms de p50, n=28274), qui porte **aussi** le temps serveur de l'étape (3375.0 s, 66 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21478 | 217.8 | 77.6 | 695.5 | 782.0 | 2321.1 |
| attachment,palier:1400 | 6230 | 105.3 | 46.4 | 361.7 | 640.5 | 1150.1 |
| attachment,palier:1996 | 11328 | 254.5 | 107.3 | 719.7 | 786.1 | 1283.1 |
| attachment,palier:transition | 609 | 387.6 | 379.4 | 859.4 | 1043.7 | 2172.9 |
| dashboard | 217832 | 195.3 | 82.5 | 497.6 | 729.8 | 2332.3 |
| dashboard,call:coverage,palier:1400 | 15892 | 65.4 | 63.8 | 75.0 | 81.3 | 167.5 |
| dashboard,call:coverage,palier:1996 | 28286 | 78.2 | 75.9 | 105.2 | 119.8 | 366.8 |
| dashboard,call:coverage,palier:transition | 1029 | 262.9 | 172.2 | 610.3 | 815.4 | 1158.1 |
| dashboard,call:folder,palier:1400 | 15892 | 390.2 | 394.4 | 764.2 | 988.1 | 1608.3 |
| dashboard,call:folder,palier:1996 | 28286 | 405.8 | 406.8 | 785.4 | 927.5 | 1624.7 |
| dashboard,call:folder,palier:transition | 1029 | 582.7 | 529.6 | 998.7 | 1154.9 | 1774.7 |
| dashboard,call:folders,palier:1400 | 15892 | 54.6 | 29.8 | 155.5 | 169.9 | 404.5 |
| dashboard,call:folders,palier:1996 | 28286 | 82.5 | 55.6 | 191.2 | 218.2 | 969.4 |
| dashboard,call:folders,palier:transition | 1029 | 274.4 | 174.5 | 665.1 | 857.9 | 1245.9 |
| dashboard,call:today,palier:1400 | 15892 | 145.0 | 66.3 | 484.3 | 505.8 | 746.3 |
| dashboard,call:today,palier:1996 | 28286 | 159.4 | 82.4 | 499.7 | 526.2 | 1259.2 |
| dashboard,call:today,palier:transition | 1029 | 480.5 | 512.9 | 918.3 | 1007.6 | 1492.3 |
| dashboard,palier:1400 | 63568 | 163.8 | 66.7 | 462.4 | 553.9 | 1608.3 |
| dashboard,palier:1996 | 113144 | 181.5 | 85.8 | 475.3 | 578.8 | 1624.7 |
| dashboard,palier:transition | 4116 | 400.1 | 367.3 | 852.7 | 970.2 | 1774.7 |
| mark_read | 43412 | 94.5 | 74.0 | 140.4 | 193.6 | 1681.4 |
| mark_read,palier:1400 | 12664 | 55.2 | 44.9 | 86.0 | 95.3 | 375.0 |
| mark_read,palier:1996 | 22677 | 88.9 | 83.8 | 139.8 | 162.4 | 467.9 |
| mark_read,palier:transition | 1194 | 201.3 | 79.6 | 612.7 | 828.0 | 1175.7 |
| patient_docs | 175940 | 102.5 | 71.1 | 182.4 | 254.0 | 1690.5 |
| patient_docs,palier:1400 | 50911 | 55.6 | 52.1 | 94.4 | 109.2 | 295.1 |
| patient_docs,palier:1996 | 92451 | 100.9 | 87.7 | 183.7 | 218.7 | 617.4 |
| patient_docs,palier:transition | 4925 | 194.2 | 78.6 | 600.8 | 751.9 | 1377.6 |
| patient_dossier | 12147 | 115.2 | 79.1 | 195.1 | 280.9 | 2027.3 |
| patient_dossier,palier:1400 | 3519 | 61.9 | 57.3 | 98.4 | 112.5 | 342.5 |
| patient_dossier,palier:1996 | 6386 | 113.6 | 99.5 | 195.7 | 237.8 | 493.6 |
| patient_dossier,palier:transition | 341 | 230.9 | 85.6 | 708.9 | 868.7 | 2027.3 |
| patient_opposition | 12147 | 86.8 | 68.5 | 101.9 | 134.4 | 1583.4 |
| patient_opposition,palier:1400 | 3519 | 64.9 | 63.4 | 73.8 | 79.9 | 153.2 |
| patient_opposition,palier:1996 | 6386 | 76.8 | 75.5 | 101.8 | 115.3 | 307.3 |
| patient_opposition,palier:transition | 341 | 167.9 | 71.1 | 461.0 | 620.0 | 1074.6 |
| patient_search | 16113 | 76.0 | 63.5 | 97.7 | 128.9 | 1537.1 |
| patient_search,palier:1400 | 4626 | 52.1 | 60.9 | 71.5 | 76.7 | 154.9 |
| patient_search,palier:1996 | 8502 | 66.4 | 67.7 | 97.5 | 111.4 | 407.3 |
| patient_search,palier:transition | 435 | 152.1 | 66.8 | 428.4 | 624.6 | 977.0 |
| read_content | 54458 | 87.6 | 57.7 | 141.5 | 194.1 | 1853.5 |
| read_content,palier:1400 | 15895 | 45.5 | 41.7 | 64.3 | 75.7 | 238.0 |
| read_content,palier:1996 | 28300 | 87.2 | 76.7 | 144.2 | 169.7 | 540.4 |
| read_content,palier:transition | 1218 | 202.7 | 67.5 | 594.9 | 813.0 | 1218.3 |
| read_content_cold | 21667 | 485.0 | 468.3 | 536.9 | 572.0 | 2084.4 |
| read_content_cold,palier:1400 | 6350 | 455.2 | 453.7 | 504.1 | 519.9 | 611.4 |
| read_content_cold,palier:1996 | 11310 | 480.9 | 477.1 | 537.8 | 557.7 | 1099.7 |
| read_content_cold,palier:transition | 542 | 574.9 | 480.8 | 944.3 | 1120.9 | 1459.6 |
| read_list | 108916 | 92.8 | 59.8 | 168.1 | 248.4 | 1852.2 |
| read_list,call:emails,palier:1400 | 15897 | 63.8 | 59.2 | 86.1 | 98.0 | 287.0 |
| read_list,call:emails,palier:1996 | 28274 | 119.4 | 107.2 | 188.9 | 217.7 | 509.8 |
| read_list,call:emails,palier:transition | 1183 | 286.4 | 108.0 | 777.6 | 1011.7 | 1337.6 |
| read_list,call:folder,palier:1400 | 15897 | 38.1 | 22.7 | 49.6 | 123.6 | 509.8 |
| read_list,call:folder,palier:1996 | 28274 | 61.2 | 41.7 | 113.6 | 155.0 | 731.9 |
| read_list,call:folder,palier:transition | 1183 | 176.8 | 59.8 | 547.8 | 735.4 | 1158.0 |
| read_list,palier:1400 | 31794 | 51.0 | 47.3 | 82.3 | 105.6 | 509.8 |
| read_list,palier:1996 | 56548 | 90.3 | 74.4 | 168.0 | 202.0 | 731.9 |
| read_list,palier:transition | 2366 | 231.6 | 92.3 | 685.2 | 860.3 | 1337.6 |
| search | 16348 | 440.4 | 368.1 | 595.2 | 1006.5 | 2428.5 |
| search,palier:1400 | 4687 | 386.5 | 335.4 | 476.2 | 622.9 | 1542.4 |
| search,palier:1996 | 8548 | 434.6 | 384.5 | 543.7 | 703.6 | 1765.1 |
| search,palier:transition | 460 | 580.3 | 406.4 | 1143.8 | 1379.2 | 2317.4 |
| send | 15670 | 673.8 | 547.4 | 947.1 | 991.6 | 2439.1 |
| send,palier:1400 | 4767 | 642.2 | 503.1 | 908.6 | 932.4 | 1075.4 |
| send,palier:1996 | 8535 | 655.0 | 521.0 | 952.0 | 985.6 | 1379.7 |
| send,palier:transition | 444 | 699.2 | 572.6 | 1046.4 | 1263.4 | 1844.5 |
| treatment | 13674 | 182.1 | 101.2 | 349.2 | 855.0 | 4867.8 |
| treatment,palier:1400 | 3991 | 88.6 | 86.3 | 109.4 | 121.8 | 4867.8 |
| treatment,palier:1996 | 7096 | 226.0 | 124.2 | 800.4 | 914.4 | 1676.6 |
| treatment,palier:transition | 310 | 315.0 | 114.6 | 823.4 | 1014.6 | 2222.3 |
| warmup | 21956 | 738.6 | 395.0 | 1249.9 | 2914.0 | 9469.5 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-05T22:13:27.352000+00:00 → 2026-11-05T22:51:08.093000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t427.csv`) | ✅ 72137 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-16924` | 1.17 | 7 | 24 | 0.034 | 5.02 |
| `DESKTOP-DEV-X2C-49908` | 1.10 | 15 | 29 | 0.032 | 5.16 |
| `DESKTOP-DEV-X2C-57348` | 1.10 | 5 | 24 | 0.033 | 4.73 |
| `DESKTOP-DEV-X2C-60976` | 1.26 | 7 | 40 | 0.034 | 5.27 |
| `DESKTOP-DEV-X2C-62972` | 1.10 | 9 | 38 | 0.032 | 4.58 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.61 | 4.53 | 2145 |
| `com.docker.backend#34124` | 0.00 | 0.04 | 30 |
| `dcp#25968` | 0.00 | 0.00 | 12 |
| `dcp#44268` | 0.00 | 0.04 | 12 |
| `dcp#45948` | 0.82 | 2.41 | 3306 |
| `dcp#47656` | 0.00 | 0.04 | 13 |
| `dcp#49656` | 0.00 | 0.00 | 12 |
| `dcp#51356` | 0.00 | 0.00 | 12 |
| `dcp#54700` | 0.00 | 0.09 | 54 |
| `dcp#55420` | 0.00 | 0.09 | 13 |
| `dcp#55548` | 0.00 | 0.00 | 12 |
| `dcp#55872` | 0.00 | 0.00 | 12 |
| `dcp#59272` | 0.00 | 0.05 | 13 |
| `dcp#59944` | 0.00 | 0.04 | 12 |
| `dcp#61756` | 0.00 | 0.04 | 14 |
| `dcp#62936` | 0.00 | 0.00 | 12 |
| `dcp#64504` | 0.00 | 0.00 | 12 |
| `k6#52487` | 0.89 | 1.85 | 2877 |
| `mss.mail.api#16924` | 0.79 | 2.88 | 2521 |
| `mss.mail.api#49908` | 0.77 | 2.96 | 2363 |
| `mss.mail.api#57348` | 0.79 | 3.08 | 2537 |
| `mss.mail.api#60976` | 0.82 | 3.31 | 2518 |
| `mss.mail.api#62972` | 0.82 | 2.77 | 2605 |
| `mss.mail.e2e#65344` | 0.00 | 0.14 | 36 |
| `vmmemWSL#36464` | 6.40 | 11.37 | 67188 |
| `loadtest-otel-collector-fgwmcmsh` | 0.02 | 0.17 | 103 |
| `loadtest-pgbouncer-pbxhtevz` | 0.50 | 0.91 | 48 |
| `mss-mail-flagsmith-app-b6152948` | 0.11 | 0.39 | 564 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.17 | 226 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.05 | 165 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.10 | 284 |
| `mss-mail-rabbitmq-arsphjft` | 0.01 | 0.11 | 140 |
| `mss-mail-redis-b6152948` | 0.28 | 1.37 | 958 |
| `mss-mail-rediscommander-tvwcxcbc` | 0.00 | 0.22 | 42 |
| `mss-mail-seq-b6152948` | 0.12 | 3.85 | 1997 |
| `postgres-pgvector` | 2.81 | 8.77 | 46326 |

- **Hôte** : CPU 70.7 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 36
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9658, cl_waiting max 10, cl_waiting_maintenance max 10, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 116, maxwait_ms max 116, maxwait_practitioner_ms max 0, sv_active max 36, sv_idle max 1579, sv_login max 1
- **Backends Postgres** : audit max 5, cache_mb max 41354, direct max 30, idle_over_60s max 206, majfault_per_s max 1, pooler max 1994, practitioner_databases max 1986, provision max 5, rss_mb max 6535, started_last_60s max 376, total max 2025, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `/health` | 159.1 | 7 |
| `api/v{version:apiVersion}/Mail/folders` | 9119.5 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 3971.0 | 450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 1800.5 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2287.4 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 1901.1 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 1957.2 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 1451.7 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 1807.3 | 447 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2268.1 | 433 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1520.3 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 1947.1 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 1392.9 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 2215.9 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 1265.6 | 447 |

- **p95 client global (k6)** : 656.8 ms
- **p95 serveur le plus élevé** : 9119.5 ms
- **Écart** : -8462.7 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 4.16 |
| Documents CDA /s | 4.09 |
| Durée traitement CDA (s, p95) | 0.70 |
| Événements de session IMAP /s | 4.13 |
| Recherches (s, p95) | 1.450 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 65.1 | 425 | 0.0 (0.0 %), p95 5 | 40.6 (62.4 %), p95 231 | 24.5 (37.6 %), p95 205 |
| `GetMail` | 11.1 | 48.9 | 362 | 4.4 (9.0 %), p95 68 | 41.1 (83.9 %), p95 279 | 3.5 (7.1 %), p95 134 |
| `GetMailsByUids` | 14.7 | 67.2 | 415 | 0.1 (0.1 %), p95 5 | 56.5 (84.0 %), p95 385 | 10.6 (15.8 %), p95 50 |

- **`EnrichPersistMail`** — sur 65.1 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 40.6 ms exécution SQL, 24.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 48.9 ms en moyenne (11.1 requête(s) SQL par appel) : 4.4 ms attente d'une connexion, 41.1 ms exécution SQL, 3.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 67.2 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 56.5 ms exécution SQL, 10.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.5 | 323.5 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 209.1 | 10.6 | 50.9 | 18.9 | 28.9 | 18.9 | 30.7 | 18.9 | 0.0 | 18.9 | 5.9 | 0.0 | 18.8 | 45.2 | 4.1 |

- **`GetMail`** — sur 3.5 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **323.5 µs**.

- **`GetMailsByUids`** — sur 10.6 ms de matérialisation, l'appel a construit 209.1 objets, dont 18.9 messages, 28.9 étiquettes, 18.9 destinataires, 30.7 pièces jointes, 18.9 identifiants enrichis, 0.0 acquittements, 18.9 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.8 corps de messages, 45.2 objets de fil, 4.1 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **50.9 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4349.8 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 266.1 | 962 | 134.2 (50.4 %), p95 300 | 9.0 (3.4 %), p95 205 | 28.0 (10.5 %), p95 623 | 52.4 (19.7 %), p95 235 | 42.5 (16.0 %), p95 425 |

- **Enrichir un message** — sur 266.1 ms en moyenne (3.8 message(s) par requête) : 134.2 ms fetch IMAP, 9.0 ms extraction XDM, 28.0 ms parsing CDA, 52.4 ms écritures base, 42.5 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 269.0 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 639.3 | 976 | 0.0 (0.0 %), p95 5 | 20.2 (3.2 %), p95 56 | 222.1 (34.7 %), p95 477 | 396.9 (62.1 %), p95 488 | 414.9 (64.9 %), p95 947 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 639.3 ms en moyenne : 0.0 ms garde d'opposition, 20.2 ms construction MIME, 222.1 ms obtention de session SMTP, 396.9 ms transmission + acquittement, 414.9 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.440 | 2.379 | 107.46 |
| `smtp_session` | 0.005 | 0.990 | 10.69 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.535 | 2.338 | 0.491 | 10.64 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 6.09 |
| `GetAttachmentStream` | 0.476 | 1.990 | 2.425 | 0.545 | 5.33 |
| `GetEmailContent` | 0.005 | 0.495 | — | 0.495 | 13.04 |
| `GetFolders` | 0.005 | 0.981 | 0.988 | 0.242 | 7.62 |
| `ReadFolder` | 0.766 | 2.379 | 2.379 | 0.487 | 35.07 |
| `ReadToday` | 0.005 | 0.610 | 2.425 | 0.610 | 7.55 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.46 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.409** | 0.425 | 0.435 | 0.0 % |
| `GetAttachmentStream` | **0.491** | 0.495 | 0.498 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.490 | 0.491 | 0.0 % |
| `GetFolders` | **0.242** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.428** | 0.441 | 0.447 | 0.0 % |
| `ReadToday` | **0.487** | 0.489 | 0.491 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 107.46 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.766 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 10.00 clients | 0 clients | 100.0 % | 28.2 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.77 cœurs | 24 cœurs | 36.6 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 3.85 cœurs | 24 cœurs | 16.1 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-49908` | 15.00 éléments | 100 éléments | 15.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#60976` (CPU) | 3.31 cœurs | 24 cœurs | 13.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#57348` (CPU) | 3.08 cœurs | 24 cœurs | 12.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#49908` (CPU) | 2.96 cœurs | 24 cœurs | 12.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#16924` (CPU) | 2.88 cœurs | 24 cœurs | 12.0 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 28.2 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 3 673 152

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 44 434 |
| OpenAI | gpt-4o-mini | prompt | 3 628 718 |
| OpenAI | text-embedding-3-small | embedding | 4 669 226 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 1 952 | 0 (0.0 %) | 0 | 51.8 | 1.14 | 0.98 | 2.48 |
| étiquetage (chat) | OpenAI | 1 952 | 0 (0.0 %) | 0 | 51.8 | 1.09 | 0.93 | 2.47 |
| embedding | OpenAI | 1 957 | 0 (0.0 %) | 0 | 51.9 | 0.56 | 0.45 | 1.59 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 13 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.0 | 0.0 |
| GPU — VRAM occupée (Mo) | 2 052 | 2 068 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.1 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **6 926.1** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.79** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **5.4 ms** | sur 751 772 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.34 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **20.28 Mo/s (2 595 blocs/s)** | attente disque : 8.7 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **756 372 / 36 873** | rapport 20.5 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **372.8** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.77 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **7 / 1** | blocs écrits par les backends eux-mêmes : 43 % |
| Sessions ouvertes / s | **2.92** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **913.0 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 562 / 2 025** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **98 / 100 %** | fautes majeures/s max : 0.6 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **94 évictions `pg_stat_statements`** pendant le tir (95 560 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

132 formes de requête, 15 804 488 appels, **24.6 min** de temps serveur cumulé — soit **2.0 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **10.7 %** | 11 % | 169 246 | 0.23 | 0.94 | 1.0 | 18 | 24 % | 0 | 1 921 | **Postgres** — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 2 | **10.7 %** | 21 % | 8 227 | 0.01 | 19.23 | 50.2 | 334 | 1 % | 0 | 777 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **10.2 %** | 32 % | 8 298 | 0.01 | 18.07 | 50.0 | 385 | 2 % | 0 | 783 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **7.5 %** | 39 % | 86 943 | 0.12 | 1.27 | 18.2 | 212 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **6.4 %** | 46 % | 2 233 675 | 2.97 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 6 | **5.5 %** | 51 % | 5 372 170 | 7.15 | 0.01 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 7 | **5.4 %** | 57 % | 2 233 676 | 2.97 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 8 | **4.3 %** | 61 % | 46 262 | 0.06 | 1.36 | 10.1 | 246 | 0 % | 0 | 1 408 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 9 | **3.6 %** | 64 % | 3 605 | 0.00 | 14.82 | 28.9 | 441 | 36 % | 0 | 409 | **Postgres** — 36 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 10 | **3.0 %** | 67 % | 8 175 | 0.01 | 5.39 | 20.0 | 609 | 4 % | 0 | 774 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 11 | **2.9 %** | 70 % | 167 063 | 0.22 | 0.26 | 1.0 | 8 | 3 % | 0 | 1 883 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 12 | **2.9 %** | 73 % | 751 716 | 1.00 | 0.06 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 13 | **2.5 %** | 76 % | 139 548 | 0.19 | 0.27 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 14 | **2.5 %** | 78 % | 8 254 | 0.01 | 4.45 | 20.0 | 611 | 3 % | 0 | 780 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 15 | **1.7 %** | 80 % | 279 227 | 0.37 | 0.09 | 2.0 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 16 | **1.5 %** | 81 % | 279 229 | 0.37 | 0.08 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 17 | **1.5 %** | 83 % | 93 148 | 0.12 | 0.23 | 18.0 | 5 | 0 % | 0 | 1 759 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **1.4 %** | 84 % | 18 387 | 0.02 | 1.10 | 1.0 | 18 | 48 % | 0 | 1 316 | **Postgres** — 48 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 19 | **1.0 %** | 85 % | 86 934 | 0.12 | 0.16 | 18.2 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 20 | **0.9 %** | 86 % | 186 806 | 0.25 | 0.07 | 3.3 | 8 | 0 % | 0 | 1 892 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 90.0 % | 61.2 % |
| INSERT | 3.9 % | 1.2 % |
| UPDATE | 0.3 % | 0.5 % |
| DELETE | 0.1 % | 0.2 % |
| AUTRE | 5.7 % | 36.9 % |
| bases : praticien (N bases) | 82.5 % | 65.1 % |
| bases : unique (1 base) | 17.5 % | 34.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **19.2** | 123 | 8 227 | 10.7 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **18.1** | 249 | 8 298 | 10.2 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **14.8** | 371 | 3 605 | 3.6 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **5.4** | 169 | 8 175 | 3.0 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **4.7** | 47 | 1 370 | 0.4 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 1 051 | 260 648 | 240 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 366 | 162 554 | 0 | 5 | 0.1 Mo |
| `Mails` | 867 | 120 337 | 797 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 210 | 30 842 | 1 049 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 111 | 28 971 | 113 | 43 | 29.9 Mo |
| `MailRecipients` | 151 | 23 556 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 87 | 13 572 | 2 409 | 156 | 1.9 Mo |
| `PendingActions` | 180 | 5 320 | 0 | 31 | 0.1 Mo |
| `Tags` | 111 | 1 998 | 99 | 0 | 0.0 Mo |
| `MailFolders` | 338 | 918 | 319 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (6.4 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟠 | requête n°6 (5.5 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Postgres | 🟠 | taux de cache 96.3 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°1 (10.7 % du temps SQL) — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 21 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 210 fois (30842 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 111 fois (28971 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 87 fois (13572 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Postgres | 🟡 | 43 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | requête n°9 (3.6 % du temps SQL) — 36 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Postgres | 🟡 | requête n°18 (1.4 % du temps SQL) — 48 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°10 (3.0 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°17 (1.5 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-235120.tsv`, `pgserver-journey-debut-231317.tsv`, `pgserver-journey-fin-235124.tsv`, `pgtables-journey-debut-231321.tsv`, `pgtables-journey-fin-235129.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 241716 — dont **241716** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261105-task427-recherche-235108.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
