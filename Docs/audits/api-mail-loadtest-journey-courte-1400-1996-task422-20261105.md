# Rapport de tir — journey-courte-1400-1996-20261105-task422-pool1-toxifix

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261105-task422-pool1-toxifix-220712.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1996 médecins, 2 étape(s) dépassent le temps de réponse attendu : « Ouvrir un message enrichi (servi base) », « Recherche »
- 5 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 21 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.012 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 751261 — **débit émergent global** : 332.5 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53057 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 332.5 | **222.5** | 105.0 | **823.9** | — | 3862.8 | 0.01 | 100.0 | 0 | 0 | 239750/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 212579 | 288.44 | 0.01 | 809.6 |
| **1996 médecins** | 1080 | 933 | 382038 | 409.47 | 0.01 | 1456.8 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 69 / 559 (n=62820) | 117 / 678 (n=112860) |
| 2 | Ouvrir / rafraîchir l'inbox | 51 / 121 (n=31404) | 116 / 356 (n=56390) |
| 3 | Ouvrir un message enrichi (servi base) | 46 / 92 (n=15702) | 125 / 318 (n=28225) |
| 4 | Ouvrir un message froid (fetch IMAP) | 457 / 523 (n=6218) | 510 / 658 (n=11370) |
| 5 | Recherche | 396 / 671 (n=4702) | 532 / 992 (n=8486) |
| 6 | Envoi (acquittement UI) | 504 / 940 (n=4814) | 592 / 1067 (n=8375) |
| 7 | Télécharger une PJ (~124 Ko) | 56 / 714 (n=6332) | 334 / 987 (n=11246) |
| 8 | Marquer lu | 51 / 102 (n=12572) | 121 / 298 (n=22577) |
| 9 | Rechercher un patient | 62 / 83 (n=4832) | 83 / 200 (n=8516) |
| 10 | Ouvrir la page d'un dossier patient | 65 / 131 (n=7164) | 156 / 430 (n=12819) |
| 11 | Fiche patient complète (ressenti médecin) | 374 / 641 (n=3582) | 800 / 2034 (n=6410) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.4 / 65 | 7888 | 641 |
| **1996 médecins** | 14.7 / 20 | 34.9 / 65 | 14114 | 2034 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2214 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 792 ms en moyenne, 3863 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2259 / 3101 (magasin) | 2259 / 3101 (magasin) |
| Backends Postgres (moy/max) | 1236 / 1426 | 1989 / 2027 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 3 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 38/183 (21 %) | 96/137 (70 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/183 (0 %) | 0/137 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 38/183 (21 %) | 96/137 (70 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 135.4 | 317.1 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 135.4 | 317.1 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 121 / 410 | 90 / 287 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 115 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1395 | 1996 |
| Backends **directs** — audit + provisionnement (max) | 25 | 26 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 0 | 1 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 3 | 1 / 14 |
| RSS par réplica api-mail, Mo (moy/max) | 1314 / 2199 (5 réplicas) | 2335 / 2830 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1426.0 / 2500** (57.0 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2027.0 / 2500** (81.1 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 99.9 %** des 1996 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⓘ Chauffe : **304 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 69 (300) | 559 (1500) | 62820 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 51 (300) | 121 (1000) | 31404 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 46 (100) | 92 (500) | 15702 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 457 (800) | 523 (2500) | 6218 | ✅ |
| 5 | Recherche | 396 (500) | 671 (2000) | 4702 | ✅ |
| 6 | Envoi (acquittement UI) | 504 (1000) | 940 (3000) | 4814 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 56 (500) | 714 (2000) | 6332 | ✅ |
| 8 | Marquer lu | 51 (200) | 102 (1000) | 12572 | ✅ |
| 9 | Rechercher un patient | 62 (300) | 83 (1500) | 4832 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 65 (500) | 131 (2000) | 7164 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 374 (1500) | 641 (4000) | 3582 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 117 (300) | 678 (1500) | 112860 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 116 (300) | 356 (1000) | 56390 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 125 (100) | 318 (500) | 28225 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 510 (800) | 658 (2500) | 11370 | ✅ |
| 5 | Recherche | 532 (500) | 992 (2000) | 8486 | ❌ |
| 6 | Envoi (acquittement UI) | 592 (1000) | 1067 (3000) | 8375 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 334 (500) | 987 (2000) | 11246 | ✅ |
| 8 | Marquer lu | 121 (200) | 298 (1000) | 22577 | ✅ |
| 9 | Rechercher un patient | 83 (300) | 200 (1500) | 8516 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 156 (500) | 430 (2000) | 12819 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 800 (1500) | 2034 (4000) | 6410 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 112860 | 211 | 678 | 23860.4 | 35.7 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 56390 | 145 | 356 | 8175.3 | 12.2 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11370 | 524 | 658 | 5958.6 | 8.9 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8375 | 704 | 1067 | 5896.9 | 8.8 % |
| 🟠 | Recherche (`search`) | 8486 | 589 | 992 | 5000.3 | 7.5 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11246 | 425 | 987 | 4784.9 | 7.2 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 28225 | 148 | 318 | 4163.4 | 6.2 % |
| 🟢 | Marquer lu (`mark_read`) | 22577 | 141 | 298 | 3187.9 | 4.8 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 7057 | 439 | 1193 | 3099.3 | 4.6 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6410 | 190 | 430 | 1217.7 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8516 | 94 | 200 | 804.4 | 1.2 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6409 | 102 | 203 | 651.9 | 1.0 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 5 🟠 · 7 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 23860.4 s, 35.7 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 5.8×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 8175.3 s, 12.2 %)
  - **dispersion p95/p50 = 3.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 5000.3 s, 7.5 %)
  - **hors grille** — le médecin attend trop
- **Ouvrir un message enrichi (servi base)** (`read_content`, 4163.4 s, 6.2 %)
  - **hors grille** — le médecin attend trop
- **Traitement (plateforme)** (`treatment`, 3099.3 s, 4.6 %)
  - **dispersion p95/p50 = 5.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (analyse du 2026-11-05)

**F1 — Recherche : `ILIKE '%mot%'` sur le corps de tous les messages d'un dossier, 50,6 % du temps SQL du tir.**
- Formes n° 1 et 2 de `pg_stat_statements` : `MailContents.Body` et `MailMedicalDocuments.Body`, environ 46 000
  appels chacune, environ 15,5 ms et 270 à 310 blocs de 8 Ko par appel.
- Émises par `SemanticSearchRepository.ExecuteFullTextSearchAsync` : jusqu'à 3 termes × 2 tables, soit 6 requêtes
  séquentielles par recherche.
- Aucun index ne sert un `ILIKE` à joker initial : chaque appel balaie les corps du dossier.
- Côté médecin, c'est l'étape « Recherche », dont le p50 sort de la grille à 1996 actifs (532 ms pour 500).
- Remèdes à départager **par le plan**, avec `EXPLAIN (ANALYZE, BUFFERS)` sur une base échantillon :
  - index GIN `pg_trgm` sur `Body`, qui garde la sémantique d'`ILIKE` mais a un coût disque, mémoire et écriture,
    alors que la mémoire Postgres est la prochaine limite ;
  - une colonne `tsvector`, qui change la sémantique (racinisation) : décision produit ;
  - un seul aller-retour par table pour tous les termes.

**F2 — Le cache du compte du registre ne sert jamais : environ 6 lectures du registre par requête HTTP.**
- Formes n° 5, 6 et 12 : `accounts` et l'ancre PSC, chacune 2 226 391 appels (2,96 par requête HTTP), plus
  `mss_accounts` (1,00 par requête HTTP).
- Toutes portent sur **la** base commune du registre, point de contention unique qui croît avec le trafic total.
- Cause établie dans le code : `UserContextEnricherMiddleware` appelle `TenantRegistrySynchronizer.SynchroniseAsync`
  à **chaque** requête. Ce dernier appelle `PostgresTenantRegistryClient.EnsureAccountAsync`, qui relit la ligne
  (2 SELECT) et l'ancre, puis appelle **`InvalidateAccountAsync` sans condition**. Le cache de 10 min de
  `GetAccountAsync` est donc vidé juste avant d'être lu, et `GetAccountAsync` relit à son tour compte et ancre.
- Remède : n'invalider que si `EnsureAccountAsync` a écrit (création ou projection Keycloak changée), et servir
  `EnsureAccountAsync` depuis le cache quand rien ne change.
- Gain attendu : environ 2/3 des lectures du registre, soit environ 4,5 millions de requêtes en 39 min de tir.
- S'y ajoute `DISCARD ALL` (forme n° 7, 7,1 par requête HTTP, 3,3 % du temps SQL), réinitialisation Npgsql au
  retour au pool, à réexaminer avec F2 (`No Reset On Close`).

**Hors code — F3 : mémoire Postgres.**
- Le cgroup du conteneur est à 100 % de 48 Go aux deux paliers, le taux de cache à 96,7 %, et 18,8 Mo/s sont lus
  sur disque (formes n° 3, 9 et 17, lecture des contenus).
- C'est la prochaine limite du banc. En production, elle relève du dimensionnement, déjà recommandé dans task-422.

**Déjà connu — verrou `imap_session`.** L'appel `folder` du dashboard porte 51 % du temps de l'étape (p95 1 013 ms).
L'attente du verrou pour `ReadFolder` est de 0,76 s au p95 à 1996 : même chantier que les tâches 323 et 270.

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15705 | 396 | 972 | 6154.8 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15705 | 69 | 508 | 2320.9 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15705 | 33 | 176 | 914.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15705 | 65 | 88 | 1059.5 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15702 | 25 | 127 | 648.6 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15702 | 65 | 118 | 1122.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28215 | 422 | 1013 | 12145.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28215 | 102 | 563 | 5325.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28215 | 88 | 306 | 3470.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28215 | 89 | 204 | 2920.1 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28195 | 67 | 258 | 2721.5 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28195 | 170 | 386 | 5453.8 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (1013 ms de p95, 422 ms de p50, n=28215), qui porte **aussi** le temps serveur de l'étape (12145.0 s, 51 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (386 ms de p95, 170 ms de p50, n=28195), qui porte **aussi** le temps serveur de l'étape (5453.8 s, 67 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21470 | 349.6 | 175.5 | 831.9 | 1003.6 | 3420.9 |
| attachment,palier:1400 | 6332 | 173.2 | 56.0 | 646.4 | 713.9 | 1305.1 |
| attachment,palier:1996 | 11246 | 425.5 | 333.8 | 853.8 | 987.1 | 1870.9 |
| attachment,palier:transition | 591 | 452.2 | 412.5 | 945.7 | 1132.6 | 2028.3 |
| dashboard | 216708 | 223.1 | 104.3 | 535.8 | 777.9 | 2932.3 |
| dashboard,call:coverage,palier:1400 | 15705 | 67.5 | 65.2 | 80.5 | 87.7 | 191.1 |
| dashboard,call:coverage,palier:1996 | 28215 | 103.5 | 88.8 | 160.3 | 203.7 | 1034.8 |
| dashboard,call:coverage,palier:transition | 1006 | 242.0 | 123.9 | 596.0 | 755.8 | 1354.8 |
| dashboard,call:folder,palier:1400 | 15705 | 391.9 | 395.5 | 765.5 | 971.5 | 1497.2 |
| dashboard,call:folder,palier:1996 | 28215 | 430.4 | 422.5 | 806.6 | 1013.0 | 1751.3 |
| dashboard,call:folder,palier:transition | 1006 | 614.7 | 573.4 | 1047.2 | 1206.3 | 1986.6 |
| dashboard,call:folders,palier:1400 | 15705 | 58.2 | 32.8 | 159.5 | 175.8 | 313.0 |
| dashboard,call:folders,palier:1996 | 28215 | 123.0 | 88.2 | 250.3 | 305.5 | 1249.4 |
| dashboard,call:folders,palier:transition | 1006 | 248.0 | 144.9 | 660.1 | 871.1 | 1355.5 |
| dashboard,call:today,palier:1400 | 15705 | 147.8 | 68.7 | 487.1 | 508.5 | 1116.1 |
| dashboard,call:today,palier:1996 | 28215 | 188.7 | 102.0 | 523.8 | 563.0 | 1456.5 |
| dashboard,call:today,palier:transition | 1006 | 470.0 | 495.7 | 909.7 | 1077.2 | 1709.4 |
| dashboard,palier:1400 | 62820 | 166.3 | 69.3 | 463.0 | 559.2 | 1497.2 |
| dashboard,palier:1996 | 112860 | 211.4 | 117.3 | 498.6 | 678.1 | 1751.3 |
| dashboard,palier:transition | 4024 | 393.7 | 336.3 | 847.5 | 1011.2 | 1986.6 |
| mark_read | 43227 | 134.7 | 89.1 | 236.1 | 357.1 | 1936.2 |
| mark_read,palier:1400 | 12572 | 59.2 | 50.8 | 91.8 | 102.3 | 196.6 |
| mark_read,palier:1996 | 22577 | 141.2 | 121.1 | 240.7 | 298.3 | 1123.3 |
| mark_read,palier:transition | 1168 | 180.2 | 87.4 | 528.3 | 719.8 | 1481.5 |
| patient_docs | 177945 | 144.6 | 90.9 | 292.6 | 403.0 | 2363.3 |
| patient_docs,palier:1400 | 52075 | 61.5 | 56.0 | 107.5 | 126.3 | 283.5 |
| patient_docs,palier:1996 | 94117 | 160.1 | 133.3 | 307.2 | 371.4 | 1364.5 |
| patient_docs,palier:transition | 4796 | 164.3 | 81.8 | 436.4 | 704.8 | 1453.6 |
| patient_dossier | 12147 | 170.6 | 107.1 | 331.3 | 486.9 | 2974.6 |
| patient_dossier,palier:1400 | 3582 | 69.2 | 63.1 | 111.9 | 131.2 | 219.1 |
| patient_dossier,palier:1996 | 6410 | 190.0 | 156.2 | 348.5 | 430.1 | 1490.4 |
| patient_dossier,palier:transition | 323 | 194.6 | 97.8 | 517.4 | 766.9 | 1655.4 |
| patient_opposition | 12147 | 106.8 | 74.9 | 151.5 | 231.6 | 1589.0 |
| patient_opposition,palier:1400 | 3582 | 66.6 | 64.7 | 78.4 | 85.5 | 153.4 |
| patient_opposition,palier:1996 | 6409 | 101.7 | 87.4 | 159.9 | 203.1 | 734.5 |
| patient_opposition,palier:transition | 325 | 122.7 | 72.4 | 272.3 | 458.8 | 1144.3 |
| patient_search | 16243 | 98.2 | 68.9 | 146.4 | 230.6 | 1741.5 |
| patient_search,palier:1400 | 4832 | 54.5 | 62.4 | 75.5 | 82.8 | 147.6 |
| patient_search,palier:1996 | 8516 | 94.5 | 82.9 | 156.2 | 199.7 | 1027.0 |
| patient_search,palier:transition | 437 | 123.4 | 71.2 | 316.7 | 486.0 | 919.2 |
| read_content | 54177 | 132.4 | 82.7 | 254.4 | 361.1 | 2015.4 |
| read_content,palier:1400 | 15702 | 51.5 | 45.9 | 77.3 | 92.3 | 215.3 |
| read_content,palier:1996 | 28225 | 147.5 | 125.0 | 260.8 | 317.6 | 1141.3 |
| read_content,palier:transition | 1273 | 206.2 | 98.8 | 625.8 | 823.4 | 1783.6 |
| read_content_cold | 21582 | 517.9 | 487.6 | 599.5 | 689.4 | 2313.0 |
| read_content_cold,palier:1400 | 6218 | 458.3 | 456.7 | 507.9 | 523.3 | 659.7 |
| read_content_cold,palier:1996 | 11370 | 524.1 | 509.6 | 609.2 | 658.4 | 1495.2 |
| read_content_cold,palier:transition | 541 | 559.4 | 493.1 | 823.3 | 1026.1 | 1840.3 |
| read_list | 108354 | 132.4 | 76.8 | 279.5 | 409.3 | 2206.3 |
| read_list,call:emails,palier:1400 | 15702 | 71.5 | 64.9 | 102.6 | 118.1 | 269.7 |
| read_list,call:emails,palier:1996 | 28195 | 193.4 | 169.7 | 326.6 | 385.9 | 1227.5 |
| read_list,call:emails,palier:transition | 1199 | 281.5 | 152.4 | 755.5 | 965.0 | 1638.4 |
| read_list,call:folder,palier:1400 | 15702 | 41.3 | 24.6 | 59.7 | 126.9 | 547.1 |
| read_list,call:folder,palier:1996 | 28195 | 96.5 | 66.9 | 185.1 | 258.2 | 1031.7 |
| read_list,call:folder,palier:transition | 1199 | 173.9 | 63.7 | 504.8 | 719.9 | 1306.2 |
| read_list,palier:1400 | 31404 | 56.4 | 50.6 | 97.7 | 120.9 | 547.1 |
| read_list,palier:1996 | 56390 | 145.0 | 116.1 | 287.5 | 355.9 | 1227.5 |
| read_list,palier:transition | 2398 | 227.7 | 109.4 | 642.1 | 860.2 | 1638.4 |
| search | 16191 | 565.7 | 479.3 | 830.2 | 1233.0 | 3352.2 |
| search,palier:1400 | 4702 | 442.2 | 396.1 | 538.4 | 670.8 | 1613.4 |
| search,palier:1996 | 8486 | 589.2 | 532.3 | 794.6 | 991.6 | 1997.7 |
| search,palier:transition | 423 | 632.5 | 482.0 | 1229.4 | 1452.0 | 2968.9 |
| send | 15547 | 712.4 | 643.8 | 996.4 | 1083.4 | 2826.4 |
| send,palier:1400 | 4814 | 646.1 | 504.3 | 916.4 | 939.8 | 1067.5 |
| send,palier:1996 | 8375 | 704.1 | 592.4 | 1010.1 | 1066.7 | 1750.8 |
| send,palier:transition | 441 | 752.6 | 783.4 | 1219.7 | 1404.0 | 2279.4 |
| treatment | 13553 | 327.8 | 138.9 | 971.5 | 1123.4 | 3407.8 |
| treatment,palier:1400 | 3944 | 129.7 | 91.0 | 135.5 | 652.9 | 3268.9 |
| treatment,palier:1996 | 7057 | 439.2 | 219.9 | 1056.2 | 1193.4 | 2513.6 |
| treatment,palier:transition | 307 | 423.3 | 203.3 | 950.8 | 1070.0 | 2609.1 |
| warmup | 21956 | 791.6 | 732.6 | 1328.2 | 1564.0 | 3862.8 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-05T20:29:32.971000+00:00 → 2026-11-05T21:07:12.335000+00:00 (2259 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t422b.csv`) | ✅ 71011 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-41348` | 1.09 | 7 | 34 | 0.031 | 4.65 |
| `DESKTOP-DEV-X2C-43016` | 1.15 | 12 | 30 | 0.025 | 5.89 |
| `DESKTOP-DEV-X2C-53488` | 1.13 | 11 | 35 | 0.044 | 5.05 |
| `DESKTOP-DEV-X2C-56072` | 1.29 | 12 | 42 | 0.032 | 5.02 |
| `DESKTOP-DEV-X2C-56988` | 1.19 | 15 | 29 | 0.040 | 5.84 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.58 | 4.22 | 2194 |
| `com.docker.backend#34124` | 0.00 | 0.09 | 39 |
| `dcp#38528` | 0.00 | 0.14 | 12 |
| `dcp#48640` | 0.00 | 0.04 | 13 |
| `dcp#50120` | 0.00 | 0.00 | 12 |
| `dcp#52528` | 0.00 | 0.04 | 13 |
| `dcp#55216` | 0.00 | 0.04 | 12 |
| `dcp#55356` | 0.00 | 0.14 | 50 |
| `dcp#55816` | 0.00 | 0.00 | 12 |
| `dcp#56616` | 0.00 | 0.09 | 12 |
| `dcp#57260` | 0.00 | 0.00 | 13 |
| `dcp#59276` | 0.83 | 2.17 | 3382 |
| `dcp#59548` | 0.00 | 0.00 | 12 |
| `dcp#59780` | 0.00 | 0.18 | 11 |
| `dcp#63256` | 0.00 | 0.00 | 12 |
| `dcp#64084` | 0.00 | 0.00 | 12 |
| `dcp#64404` | 0.00 | 0.09 | 13 |
| `k6#39201` | 0.88 | 1.94 | 2872 |
| `mss.mail.api#41348` | 0.82 | 3.15 | 2502 |
| `mss.mail.api#43016` | 0.78 | 2.80 | 2841 |
| `mss.mail.api#53488` | 0.87 | 3.34 | 2420 |
| `mss.mail.api#56072` | 0.83 | 2.84 | 2571 |
| `mss.mail.api#56988` | 0.84 | 2.91 | 2485 |
| `mss.mail.e2e#49664` | 0.01 | 0.18 | 39 |
| `vmmemWSL#36464` | 6.90 | 13.02 | 63081 |
| `loadtest-otel-collector-dndxjdcz` | 0.03 | 0.20 | 98 |
| `loadtest-pgbouncer-egxvtqjk` | 0.58 | 0.95 | 50 |
| `mss-mail-flagsmith-app-b6152948` | 0.13 | 0.43 | 562 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.13 | 195 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.22 | 198 |
| `mss-mail-prometheus-b6152948` | 0.02 | 0.99 | 249 |
| `mss-mail-rabbitmq-gmwxvsde` | 0.03 | 0.16 | 144 |
| `mss-mail-redis-b6152948` | 0.29 | 1.38 | 978 |
| `mss-mail-rediscommander-bedyegxa` | 0.00 | 0.20 | 34 |
| `mss-mail-seq-b6152948` | 0.11 | 3.12 | 1794 |
| `postgres-pgvector` | 3.49 | 9.26 | 41339 |

- **Hôte** : CPU 74.4 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 36
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 10273, cl_waiting max 24, cl_waiting_maintenance max 24, cl_waiting_practitioner max 0, count max 2001, login_retry_delta max 0, maxwait_maintenance_ms max 317, maxwait_ms max 317, maxwait_practitioner_ms max 0, sv_active max 77, sv_idle max 1587, sv_login max 24
- **Backends Postgres** : audit max 5, cache_mb max 41789, direct max 26, idle_over_60s max 413, majfault_per_s max 22, pooler max 1996, practitioner_databases max 1989, provision max 1, rss_mb max 6570, started_last_60s max 410, total max 2027, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 2361.7 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2425.0 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 2077.7 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2388.5 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 2165.7 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 2306.0 | 441 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 2150.6 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2130.7 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2383.0 | 435 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1966.2 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 2221.4 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 1875.0 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 2455.5 | 442 |
| `api/v{version:apiVersion}/Settings` | 215.0 | 1 |
| `api/v{version:apiVersion}/Settings/getsettings` | 24.2 | 1 |
| `api/v{version:apiVersion}/Settings/mail-server` | 24.8 | 1 |
| `api/v{version:apiVersion}/Sync/coverage` | 2035.0 | 446 |

- **p95 client global (k6)** : 823.9 ms
- **p95 serveur le plus élevé** : 2455.5 ms
- **Écart** : -1631.6 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 6.64 |
| Documents CDA /s | 6.67 |
| Durée traitement CDA (s, p95) | 1.86 |
| Événements de session IMAP /s | 4.31 |
| Recherches (s, p95) | 1.995 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 77.6 | 453 | 0.0 (0.0 %), p95 5 | 48.9 (63.0 %), p95 386 | 28.7 (37.0 %), p95 195 |
| `GetMail` | 11.1 | 68.6 | 491 | 5.4 (7.9 %), p95 76 | 59.3 (86.5 %), p95 468 | 3.8 (5.5 %), p95 18 |
| `GetMailsByUids` | 14.7 | 96.6 | 639 | 0.1 (0.1 %), p95 5 | 83.9 (86.9 %), p95 621 | 12.6 (13.0 %), p95 61 |

- **`EnrichPersistMail`** — sur 77.6 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 48.9 ms exécution SQL, 28.7 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 68.6 ms en moyenne (11.1 requête(s) SQL par appel) : 5.4 ms attente d'une connexion, 59.3 ms exécution SQL, 3.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 96.6 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 83.9 ms exécution SQL, 12.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.8 | 3.8 | 352.4 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 213.2 | 12.6 | 58.9 | 19.3 | 29.4 | 19.3 | 31.3 | 19.3 | 0.0 | 19.3 | 6.0 | 0.0 | 19.1 | 46.2 | 4.1 |

- **`GetMail`** — sur 3.8 ms de matérialisation, l'appel a construit 10.8 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **352.4 µs**.

- **`GetMailsByUids`** — sur 12.6 ms de matérialisation, l'appel a construit 213.2 objets, dont 19.3 messages, 29.4 étiquettes, 19.3 destinataires, 31.3 pièces jointes, 19.3 identifiants enrichis, 0.0 acquittements, 19.3 documents médicaux, 6.0 résultats de biologie, 0.0 éléments de synthèse, 19.1 corps de messages, 46.2 objets de fil, 4.1 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **58.9 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3756.2 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 280.1 | 1936 | 132.3 (47.2 %), p95 246 | 6.8 (2.4 %), p95 220 | 28.9 (10.3 %), p95 906 | 63.4 (22.6 %), p95 409 | 48.6 (17.4 %), p95 238 |

- **Enrichir un message** — sur 280.1 ms en moyenne (3.8 message(s) par requête) : 132.3 ms fetch IMAP, 6.8 ms extraction XDM, 28.9 ms parsing CDA, 63.4 ms écritures base, 48.6 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **2.95 aller(s)-retour(s) IMAP par message enrichi** — 1.00 `fetch_whole_message`, 0.50 `resolve_folder`, 0.50 `fetch_bodystructure`, 0.50 `close_folder`, 0.44 `open_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 257.2 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 650.4 | 987 | 0.0 (0.0 %), p95 5 | 27.9 (4.3 %), p95 84 | 223.9 (34.4 %), p95 478 | 398.4 (61.3 %), p95 489 | 415.0 (63.8 %), p95 1001 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 650.4 ms en moyenne : 0.0 ms garde d'opposition, 27.9 ms construction MIME, 223.9 ms obtention de session SMTP, 398.4 ms transmission + acquittement, 415.0 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.439 | 2.425 | 110.43 |
| `smtp_session` | 0.005 | 0.988 | 10.09 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.747 | 2.369 | 0.496 | 10.06 |
| `EnrichEmails` | 0.005 | 0.446 | — | 0.446 | 9.82 |
| `GetAttachmentStream` | 0.477 | 1.833 | 2.425 | 0.683 | 7.13 |
| `GetEmailContent` | 0.005 | 0.499 | — | 0.499 | 13.31 |
| `GetFolders` | 0.005 | 0.989 | 0.998 | 0.245 | 7.75 |
| `ReadFolder` | 0.756 | 2.425 | 2.425 | 0.487 | 36.31 |
| `ReadToday` | 0.005 | 0.499 | — | 0.499 | 7.69 |
| `UpdateFlag` | 0.088 | 0.492 | — | 0.492 | 25.97 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.493 | 0.496 | 0.0 % |
| `EnrichEmails` | **0.419** | 0.435 | 0.441 | 0.0 % |
| `GetAttachmentStream` | **0.496** | 0.552 | 0.644 | 0.0 % |
| `GetEmailContent` | **0.490** | 0.495 | 0.499 | 0.0 % |
| `GetFolders` | **0.242** | 0.243 | 0.245 | 0.0 % |
| `ReadFolder` | **0.429** | 0.443 | 0.446 | 0.0 % |
| `ReadToday` | **0.489** | 0.493 | 0.499 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.490 | 0.492 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 110.43 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.756 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 24.00 clients | 0 clients | 100.0 % | 40.9 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 9.26 cœurs | 24 cœurs | 38.6 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-56988` | 15.00 éléments | 100 éléments | 15.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#53488` (CPU) | 3.34 cœurs | 24 cœurs | 13.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#41348` (CPU) | 3.15 cœurs | 24 cœurs | 13.1 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 3.12 cœurs | 24 cœurs | 13.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#56988` (CPU) | 2.91 cœurs | 24 cœurs | 12.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#56072` (CPU) | 2.84 cœurs | 24 cœurs | 11.8 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 40.9 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 9 754 784

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 116 032 |
| OpenAI | gpt-4o-mini | prompt | 9 638 752 |
| OpenAI | text-embedding-3-small | embedding | 12 316 145 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 5 127 | 0 (0.0 %) | 0 | 136.2 | 1.13 | 1.00 | 2.47 |
| étiquetage (chat) | OpenAI | 5 127 | 0 (0.0 %) | 0 | 136.2 | 1.07 | 0.94 | 2.47 |
| embedding | OpenAI | 5 130 | 0 (0.0 %) | 0 | 136.2 | 0.57 | 0.47 | 1.52 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 19 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 1.4 | 20.0 |
| GPU — VRAM occupée (Mo) | 2 482 | 2 616 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.9 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **6 792.7** | annulées : 0.0 % |
| Backends actifs (équivalent) | **2.49** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **7.7 ms** | sur 751 261 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.74 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **18.77 Mo/s (2 402 blocs/s)** | attente disque : 8.9 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **726 262 / 39 758** | rapport 18.3 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **578.5** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **1.30 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **6 / 2** | blocs écrits par les backends eux-mêmes : 47 % |
| Sessions ouvertes / s | **1.97** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **1 783.3 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 545 / 2 027** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **99 / 100 %** | fautes majeures/s max : 22.3 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **89 évictions `pg_stat_statements`** pendant le tir (95 667 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

131 formes de requête, 15 891 675 appels, **47.3 min** de temps serveur cumulé — soit **3.8 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **25.9 %** | 26 % | 46 074 | 0.06 | 15.99 | 31.6 | 269 | 0 % | 0 | 1 922 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 2 | **24.7 %** | 51 % | 46 083 | 0.06 | 15.20 | 31.6 | 314 | 1 % | 0 | 1 924 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 3 | **7.6 %** | 58 % | 173 129 | 0.23 | 1.24 | 1.0 | 17 | 23 % | 0 | 1 941 | **Postgres** — 23 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **4.4 %** | 63 % | 84 983 | 0.11 | 1.49 | 18.5 | 213 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **4.1 %** | 67 % | 2 226 391 | 2.96 | 0.05 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 6 | **3.5 %** | 70 % | 2 226 391 | 2.96 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 7 | **3.3 %** | 73 % | 5 351 884 | 7.12 | 0.02 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 8 | **2.4 %** | 76 % | 45 892 | 0.06 | 1.49 | 10.0 | 241 | 0 % | 0 | 1 400 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 9 | **2.3 %** | 78 % | 3 590 | 0.00 | 17.95 | 29.8 | 430 | 37 % | 0 | 408 | **Postgres** — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 10 | **1.9 %** | 80 % | 167 330 | 0.22 | 0.32 | 1.0 | 8 | 2 % | 0 | 1 872 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 11 | **1.8 %** | 82 % | 8 463 | 0.01 | 5.97 | 20.0 | 604 | 4 % | 0 | 781 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 12 | **1.7 %** | 84 % | 751 209 | 1.00 | 0.07 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 13 | **1.6 %** | 85 % | 139 606 | 0.19 | 0.32 | 1.0 | 13 | 1 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 14 | **1.5 %** | 87 % | 8 432 | 0.01 | 4.91 | 20.0 | 606 | 3 % | 0 | 780 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 15 | **1.0 %** | 88 % | 277 424 | 0.37 | 0.10 | 2.0 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 16 | **0.9 %** | 88 % | 277 426 | 0.37 | 0.09 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 17 | **0.8 %** | 89 % | 21 196 | 0.03 | 1.11 | 1.0 | 15 | 45 % | 0 | 1 276 | **Postgres** — 45 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 18 | **0.8 %** | 90 % | 89 062 | 0.12 | 0.26 | 18.0 | 5 | 0 % | 0 | 1 405 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **0.6 %** | 91 % | 186 933 | 0.25 | 0.09 | 3.3 | 8 | 0 % | 0 | 1 878 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |
| 20 | **0.6 %** | 91 % | 84 987 | 0.11 | 0.18 | 18.5 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 93.4 % | 61.4 % |
| INSERT | 2.9 % | 1.3 % |
| UPDATE | 0.2 % | 0.5 % |
| DELETE | 0.1 % | 0.3 % |
| AUTRE | 3.4 % | 36.6 % |
| bases : praticien (N bases) | 88.8 % | 65.4 % |
| bases : unique (1 base) | 11.2 % | 34.6 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **17.9** | 520 | 3 590 | 2.3 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **16.0** | 620 | 46 074 | 25.9 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailCo…` |
| **15.2** | 1 161 | 46 083 | 24.7 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMe…` |
| **6.0** | 225 | 8 463 | 1.8 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **5.4** | 27 | 143 | 0.0 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 1 026 | 254 448 | 234 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 329 | 158 151 | 0 | 5 | 0.1 Mo |
| `Mails` | 859 | 113 917 | 820 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 207 | 30 371 | 996 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 105 | 27 405 | 122 | 43 | 29.9 Mo |
| `MailRecipients` | 148 | 23 088 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 87 | 13 572 | 2 408 | 26 | 1.9 Mo |
| `PendingActions` | 186 | 5 499 | 0 | 31 | 0.1 Mo |
| `Tags` | 116 | 2 088 | 81 | 0 | 0.0 Mo |
| `MailFolders` | 348 | 970 | 234 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🔴 | requête n°1 (25.9 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Postgres | 🟠 | taux de cache 96.7 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°3 (7.6 % du temps SQL) — 23 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 18 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 207 fois (30371 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 105 fois (27405 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 87 fois (13572 lignes lues, 26 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°5 (4.1 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°7 (3.3 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Postgres | 🟡 | 47 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | requête n°9 (2.3 % du temps SQL) — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°11 (1.8 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-220814.tsv`, `pgserver-journey-debut-212923.tsv`, `pgserver-journey-fin-220818.tsv`, `pgtables-journey-debut-212927.tsv`, `pgtables-journey-fin-220823.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 239750 — dont **239750** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261105-task422-pool1-toxifix-220712.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
