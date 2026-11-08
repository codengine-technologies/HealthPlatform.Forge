# Rapport de tir — journey-courte-1400-1996-20261108-t434-task

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261108-t434-task-132336.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 1 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 24 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.008 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 759639 — **débit émergent global** : 336.0 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 54186 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 336.0 | **142.4** | 58.2 | **492.0** | — | 14492.0 | 0.01 | 100.0 | 0 | 0 | 248060/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214412 | 290.93 | 0.01 | 831.9 |
| **1996 médecins** | 1080 | 933 | 385398 | 413.07 | 0.01 | 1474.2 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 58 / 530 (n=64044) | 63 / 551 (n=115232) |
| 2 | Ouvrir / rafraîchir l'inbox | 39 / 90 (n=32018) | 50 / 134 (n=57604) |
| 3 | Ouvrir un message enrichi (servi base) | 33 / 60 (n=16010) | 45 / 104 (n=28800) |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 / 508 (n=6367) | 451 / 516 (n=11524) |
| 5 | Recherche | 328 / 563 (n=4825) | 348 / 664 (n=8588) |
| 6 | Envoi (acquittement UI) | 494 / 926 (n=4693) | 485 / 946 (n=8569) |
| 7 | Télécharger une PJ (~124 Ko) | 36 / 67 (n=6476) | 51 / 123 (n=11471) |
| 8 | Marquer lu | 33 / 80 (n=12819) | 51 / 105 (n=23039) |
| 9 | Rechercher un patient | 55 / 64 (n=4722) | 56 / 76 (n=8528) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 64 (n=7099) | 59 / 77 (n=12786) |
| 11 | Fiche patient complète (ressenti médecin) | 254 / 427 (n=3550) | 331 / 685 (n=6393) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.5 / 60 | 7890 | 427 |
| **1996 médecins** | 14.4 / 20 | 33.9 / 60 | 14402 | 685 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2271 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 696 ms en moyenne, 14492 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2234 / 3091 (magasin) | 2234 / 3091 (magasin) |
| Backends Postgres (moy/max) | 1242 / 1440 | 1988 / 2023 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 44/186 (24 %) | 53/163 (33 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/186 (0 %) | 0/163 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 44/186 (24 %) | 53/163 (33 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 51.5 | 433.6 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 51.5 | 433.6 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 120 / 348 | 99 / 276 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 114 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1409 | 1992 |
| Backends **directs** — audit + provisionnement (max) | 30 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 2 / 23 |
| RSS par réplica api-mail, Mo (moy/max) | 1148 / 1583 (5 réplicas) | 2033 / 2213 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1440.0 / 2500** (57.6 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2023.0 / 2500** (80.9 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 16010)
- palier 1996 : cohorte 1996 chauffée à 99.8 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28800)

> ⓘ Chauffe : **303 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 58 (300) | 530 (1500) | 64044 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 39 (300) | 90 (1000) | 32018 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 33 (100) | 60 (500) | 16010 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 (800) | 508 (2500) | 6367 | ✅ |
| 5 | Recherche | 328 (500) | 563 (2000) | 4825 | ✅ |
| 6 | Envoi (acquittement UI) | 494 (1000) | 926 (3000) | 4693 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 36 (500) | 67 (2000) | 6476 | ✅ |
| 8 | Marquer lu | 33 (200) | 80 (1000) | 12819 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 64 (1500) | 4722 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 64 (2000) | 7099 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 254 (1500) | 427 (4000) | 3550 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 63 (300) | 551 (1500) | 115232 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 50 (300) | 134 (1000) | 57604 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 45 (100) | 104 (500) | 28800 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 451 (800) | 516 (2500) | 11524 | ✅ |
| 5 | Recherche | 348 (500) | 664 (2000) | 8588 | ✅ |
| 6 | Envoi (acquittement UI) | 485 (1000) | 946 (3000) | 8569 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 51 (500) | 123 (2000) | 11471 | ✅ |
| 8 | Marquer lu | 51 (200) | 105 (1000) | 23039 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 76 (1500) | 8528 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 77 (2000) | 12786 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 331 (1500) | 685 (4000) | 6393 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 115232 | 161 | 551 | 18511.9 | 45.0 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8569 | 624 | 946 | 5350.3 | 13.0 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11524 | 453 | 516 | 5217.6 | 12.7 % |
| 🟢 | Recherche (`search`) | 8588 | 399 | 664 | 3427.9 | 8.3 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57604 | 57 | 134 | 3296.7 | 8.0 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28800 | 53 | 104 | 1524.4 | 3.7 % |
| 🟢 | Marquer lu (`mark_read`) | 23039 | 58 | 105 | 1337.4 | 3.2 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11471 | 66 | 123 | 756.7 | 1.8 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7201 | 101 | 156 | 729.4 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8528 | 48 | 76 | 413.0 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6393 | 59 | 77 | 374.7 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6393 | 37 | 70 | 235.7 | 0.6 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 1 🟠 · 11 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 18511.9 s, 45.0 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 8.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 16011 | 389 | 973 | 6077.3 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 16011 | 58 | 496 | 2166.8 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 16011 | 19 | 162 | 705.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 16011 | 56 | 66 | 913.2 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 16009 | 15 | 116 | 469.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 16009 | 49 | 80 | 834.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28808 | 396 | 953 | 11201.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28808 | 63 | 502 | 4013.7 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28808 | 27 | 177 | 1557.7 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28808 | 60 | 81 | 1738.8 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28802 | 20 | 125 | 1060.9 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28802 | 68 | 140 | 2235.8 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (953 ms de p95, 396 ms de p50, n=28808), qui porte **aussi** le temps serveur de l'étape (11201.6 s, 61 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (140 ms de p95, 68 ms de p50, n=28802), qui porte **aussi** le temps serveur de l'étape (2235.8 s, 68 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21951 | 67.9 | 43.8 | 100.8 | 174.9 | 1289.2 |
| attachment,palier:1400 | 6476 | 40.5 | 36.3 | 56.7 | 67.4 | 959.0 |
| attachment,palier:1996 | 11471 | 66.0 | 50.9 | 99.5 | 123.1 | 1289.2 |
| attachment,palier:transition | 630 | 146.0 | 41.5 | 416.4 | 494.4 | 1162.4 |
| dashboard | 221240 | 164.4 | 62.4 | 466.8 | 579.4 | 1840.4 |
| dashboard,call:coverage,palier:1400 | 16011 | 57.0 | 56.2 | 63.1 | 66.4 | 153.0 |
| dashboard,call:coverage,palier:1996 | 28808 | 60.4 | 59.7 | 73.4 | 81.2 | 604.9 |
| dashboard,call:coverage,palier:transition | 1030 | 113.5 | 96.1 | 204.0 | 242.5 | 377.0 |
| dashboard,call:folder,palier:1400 | 16011 | 379.6 | 389.0 | 758.9 | 973.2 | 1522.7 |
| dashboard,call:folder,palier:1996 | 28808 | 388.8 | 395.8 | 767.3 | 952.5 | 1840.4 |
| dashboard,call:folder,palier:transition | 1030 | 455.9 | 457.8 | 724.8 | 858.2 | 1517.8 |
| dashboard,call:folders,palier:1400 | 16011 | 44.0 | 19.1 | 146.8 | 162.0 | 312.4 |
| dashboard,call:folders,palier:1996 | 28808 | 54.1 | 27.5 | 158.4 | 177.3 | 633.5 |
| dashboard,call:folders,palier:transition | 1030 | 119.5 | 105.3 | 246.0 | 305.9 | 496.4 |
| dashboard,call:today,palier:1400 | 16011 | 135.3 | 58.2 | 475.5 | 496.5 | 1038.0 |
| dashboard,call:today,palier:1996 | 28808 | 139.3 | 62.6 | 479.6 | 501.8 | 1086.7 |
| dashboard,call:today,palier:transition | 1030 | 324.4 | 268.6 | 601.4 | 647.1 | 836.0 |
| dashboard,palier:1400 | 64044 | 154.0 | 58.3 | 456.2 | 529.7 | 1522.7 |
| dashboard,palier:1996 | 115232 | 160.6 | 63.3 | 459.6 | 550.8 | 1840.4 |
| dashboard,palier:transition | 4120 | 253.3 | 157.4 | 562.6 | 636.7 | 1517.8 |
| mark_read | 44103 | 61.2 | 46.5 | 92.6 | 122.7 | 1005.8 |
| mark_read,palier:1400 | 12819 | 45.3 | 33.2 | 75.1 | 80.0 | 173.3 |
| mark_read,palier:1996 | 23039 | 58.0 | 51.1 | 91.7 | 105.0 | 722.4 |
| mark_read,palier:transition | 1249 | 101.9 | 63.7 | 283.6 | 333.6 | 597.0 |
| patient_docs | 175703 | 69.1 | 50.4 | 123.1 | 175.5 | 1491.8 |
| patient_docs,palier:1400 | 51394 | 44.1 | 40.7 | 80.3 | 94.9 | 245.2 |
| patient_docs,palier:1996 | 92056 | 66.1 | 55.7 | 126.3 | 157.6 | 632.6 |
| patient_docs,palier:transition | 5104 | 130.3 | 55.4 | 438.0 | 542.4 | 950.6 |
| patient_dossier | 12202 | 39.0 | 27.5 | 58.9 | 90.4 | 904.6 |
| patient_dossier,palier:1400 | 3550 | 25.8 | 23.5 | 33.7 | 40.2 | 142.3 |
| patient_dossier,palier:1996 | 6393 | 36.9 | 31.2 | 57.8 | 70.4 | 575.6 |
| patient_dossier,palier:transition | 353 | 82.1 | 28.3 | 230.2 | 277.0 | 389.0 |
| patient_opposition | 12202 | 60.5 | 57.4 | 70.3 | 82.2 | 364.5 |
| patient_opposition,palier:1400 | 3549 | 56.4 | 55.8 | 61.3 | 63.8 | 188.1 |
| patient_opposition,palier:1996 | 6393 | 58.6 | 58.7 | 70.6 | 76.5 | 194.7 |
| patient_opposition,palier:transition | 353 | 80.9 | 57.7 | 153.5 | 194.8 | 364.5 |
| patient_search | 16309 | 49.9 | 55.6 | 69.4 | 82.7 | 859.7 |
| patient_search,palier:1400 | 4722 | 43.8 | 55.3 | 61.0 | 63.9 | 130.3 |
| patient_search,palier:1996 | 8528 | 48.4 | 55.9 | 69.4 | 75.6 | 446.3 |
| patient_search,palier:transition | 478 | 69.6 | 55.9 | 144.4 | 173.6 | 266.3 |
| read_content | 55310 | 57.1 | 38.9 | 86.9 | 137.3 | 1067.3 |
| read_content,palier:1400 | 16010 | 35.6 | 32.7 | 49.2 | 60.0 | 232.7 |
| read_content,palier:1996 | 28800 | 52.9 | 44.8 | 85.6 | 104.0 | 708.2 |
| read_content,palier:transition | 1333 | 127.0 | 40.9 | 384.3 | 449.8 | 684.2 |
| read_content_cold | 22089 | 454.1 | 449.3 | 505.8 | 526.9 | 1225.4 |
| read_content_cold,palier:1400 | 6367 | 445.7 | 444.4 | 493.9 | 507.9 | 585.6 |
| read_content_cold,palier:1996 | 11524 | 452.8 | 450.5 | 501.0 | 516.3 | 1025.4 |
| read_content_cold,palier:transition | 650 | 479.0 | 463.0 | 585.4 | 636.3 | 834.9 |
| read_list | 110620 | 61.6 | 44.9 | 113.0 | 162.4 | 1199.8 |
| read_list,call:emails,palier:1400 | 16009 | 52.1 | 48.7 | 68.7 | 79.8 | 180.3 |
| read_list,call:emails,palier:1996 | 28802 | 77.6 | 68.1 | 117.6 | 140.3 | 775.6 |
| read_list,call:emails,palier:transition | 1244 | 207.6 | 74.9 | 511.8 | 588.6 | 793.0 |
| read_list,call:folder,palier:1400 | 16009 | 29.3 | 14.9 | 31.9 | 116.4 | 544.6 |
| read_list,call:folder,palier:1996 | 28802 | 36.8 | 20.0 | 58.0 | 125.3 | 598.5 |
| read_list,call:folder,palier:transition | 1244 | 69.6 | 24.6 | 175.1 | 216.1 | 546.4 |
| read_list,palier:1400 | 32018 | 40.7 | 38.9 | 65.3 | 89.6 | 544.6 |
| read_list,palier:1996 | 57604 | 57.2 | 49.5 | 107.9 | 134.2 | 775.6 |
| read_list,palier:transition | 2488 | 138.6 | 61.0 | 439.3 | 515.0 | 793.0 |
| search | 16494 | 403.2 | 344.2 | 539.2 | 790.3 | 2332.1 |
| search,palier:1400 | 4825 | 372.1 | 327.6 | 456.7 | 562.9 | 1548.5 |
| search,palier:1996 | 8588 | 399.2 | 347.8 | 493.2 | 664.3 | 1643.7 |
| search,palier:transition | 472 | 448.4 | 343.6 | 761.6 | 892.5 | 1710.5 |
| send | 15665 | 644.5 | 507.7 | 918.6 | 951.0 | 1871.7 |
| send,palier:1400 | 4693 | 636.4 | 493.7 | 905.0 | 926.2 | 1142.7 |
| send,palier:1996 | 8569 | 624.4 | 484.5 | 916.9 | 945.9 | 1293.4 |
| send,palier:transition | 426 | 653.8 | 558.2 | 988.5 | 1084.6 | 1322.0 |
| treatment | 13781 | 101.3 | 83.3 | 134.0 | 210.4 | 4100.3 |
| treatment,palier:1400 | 3945 | 72.6 | 78.6 | 94.4 | 103.6 | 199.8 |
| treatment,palier:1996 | 7201 | 101.3 | 88.1 | 131.7 | 156.2 | 4100.3 |
| treatment,palier:transition | 334 | 171.2 | 87.2 | 437.5 | 506.6 | 801.0 |
| warmup | 21956 | 695.8 | 292.4 | 716.3 | 3925.3 | 14492.0 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-08T11:45:55.274000+00:00 → 2026-11-08T12:23:36.410000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t434-task.csv`) | ✅ 77461 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-44852` | 0.90 | 15 | 24 | 0.030 | 4.51 |
| `DESKTOP-DEV-X2C-52784` | 0.97 | 12 | 27 | 0.038 | 4.95 |
| `DESKTOP-DEV-X2C-55092` | 0.95 | 9 | 31 | 0.036 | 4.76 |
| `DESKTOP-DEV-X2C-57368` | 0.97 | 15 | 24 | 0.032 | 4.65 |
| `DESKTOP-DEV-X2C-72180` | 0.91 | 11 | 32 | 0.025 | 4.82 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.17 | 4.21 | 2350 |
| `com.docker.backend#34124` | 0.00 | 0.13 | 40 |
| `dcp#10012` | 0.00 | 0.04 | 12 |
| `dcp#21136` | 0.00 | 0.04 | 12 |
| `dcp#34712` | 0.00 | 0.08 | 12 |
| `dcp#36408` | 0.74 | 2.27 | 3193 |
| `dcp#37960` | 0.00 | 0.00 | 12 |
| `dcp#39856` | 0.00 | 0.22 | 12 |
| `dcp#45044` | 0.00 | 0.04 | 14 |
| `dcp#53084` | 0.00 | 0.08 | 14 |
| `dcp#65516` | 0.00 | 0.00 | 12 |
| `dcp#67268` | 0.00 | 0.04 | 13 |
| `dcp#70112` | 0.00 | 0.13 | 12 |
| `dcp#7036` | 0.00 | 0.04 | 14 |
| `dcp#71292` | 0.00 | 0.00 | 12 |
| `dcp#72548` | 0.00 | 0.00 | 12 |
| `dcp#77496` | 0.00 | 0.09 | 54 |
| `k6#280119` | 0.79 | 1.67 | 2881 |
| `mss.mail.api#44852` | 0.62 | 2.26 | 2232 |
| `mss.mail.api#52784` | 0.66 | 3.11 | 2237 |
| `mss.mail.api#55092` | 0.64 | 2.38 | 2185 |
| `mss.mail.api#57368` | 0.67 | 3.19 | 2168 |
| `mss.mail.api#72180` | 0.63 | 2.39 | 2250 |
| `mss.mail.e2e#43876` | 0.00 | 0.13 | 36 |
| `vmmemWSL#36464` | 5.32 | 11.28 | 52983 |
| `loadtest-otel-collector-tnarwpkh` | 0.02 | 0.18 | 100 |
| `loadtest-pgbouncer-pshedwkf` | 0.42 | 0.87 | 52 |
| `mss-mail-flagsmith-app-b6152948` | 0.12 | 0.62 | 472 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.15 | 200 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.04 | 161 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.09 | 261 |
| `mss-mail-rabbitmq-uaczgvrd` | 0.01 | 0.04 | 136 |
| `mss-mail-redis-b6152948` | 0.26 | 1.44 | 971 |
| `mss-mail-rediscommander-bmbduqxu` | 0.00 | 0.19 | 35 |
| `mss-mail-seq-b6152948` | 0.10 | 1.05 | 5805 |
| `postgres-pgvector` | 2.12 | 9.52 | 45640 |

- **Hôte** : CPU 62.4 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 56
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9301, cl_waiting max 10, cl_waiting_maintenance max 10, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 434, maxwait_ms max 434, maxwait_practitioner_ms max 0, sv_active max 52, sv_idle max 1604, sv_login max 1
- **Backends Postgres** : audit max 5, cache_mb max 43376, direct max 30, idle_over_60s max 211, majfault_per_s max 23, pooler max 1992, practitioner_databases max 1985, provision max 5, rss_mb max 6064, started_last_60s max 348, total max 2023, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 9657.5 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 3811.8 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 735.4 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 814.8 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 727.9 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 691.7 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 488.4 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 743.8 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2087.5 | 430 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 242.1 | 441 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 449.5 | 441 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 234.0 | 441 |
| `api/v{version:apiVersion}/Search/semantic` | 1681.8 | 442 |
| `api/v{version:apiVersion}/Sync/coverage` | 330.9 | 447 |

- **p95 client global (k6)** : 492.0 ms
- **p95 serveur le plus élevé** : 9657.5 ms
- **Écart** : -9165.4 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.69 |
| Documents CDA /s | 0.67 |
| Durée traitement CDA (s, p95) | 0.69 |
| Événements de session IMAP /s | 4.05 |
| Recherches (s, p95) | 1.144 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 54.9 | 235 | 0.0 (0.0 %), p95 5 | 32.8 (59.8 %), p95 235 | 22.1 (40.2 %), p95 88 |
| `GetMail` | 11.1 | 44.1 | 565 | 4.1 (9.3 %), p95 92 | 36.7 (83.3 %), p95 482 | 3.3 (7.4 %), p95 12 |
| `GetMailsByUids` | 14.7 | 63.3 | 513 | 0.1 (0.1 %), p95 5 | 53.2 (84.2 %), p95 487 | 9.9 (15.7 %), p95 62 |

- **`EnrichPersistMail`** — sur 54.9 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 32.8 ms exécution SQL, 22.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 44.1 ms en moyenne (11.1 requête(s) SQL par appel) : 4.1 ms attente d'une connexion, 36.7 ms exécution SQL, 3.3 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 63.3 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 53.2 ms exécution SQL, 9.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.3 | 306.4 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.3 | 9.9 | 47.9 | 18.7 | 28.6 | 18.7 | 30.5 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.3 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **306.4 µs**.

- **`GetMailsByUids`** — sur 9.9 ms de matérialisation, l'appel a construit 207.3 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.5 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **47.9 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4615.6 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 275.2 | 950 | 129.4 (47.0 %), p95 243 | 13.4 (4.9 %), p95 235 | 52.5 (19.1 %), p95 700 | 42.1 (15.3 %), p95 235 | 37.7 (13.7 %), p95 175 |

- **Enrichir un message** — sur 275.2 ms en moyenne (3.8 message(s) par requête) : 129.4 ms fetch IMAP, 13.4 ms extraction XDM, 52.5 ms parsing CDA, 42.1 ms écritures base, 37.7 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`, 0.51 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 268.1 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 635.3 | 992 | 0.0 (0.0 %), p95 5 | 18.2 (2.9 %), p95 58 | 219.8 (34.6 %), p95 477 | 397.2 (62.5 %), p95 489 | 413.6 (65.1 %), p95 943 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 635.3 ms en moyenne : 0.0 ms garde d'opposition, 18.2 ms construction MIME, 219.8 ms obtention de session SMTP, 397.2 ms transmission + acquittement, 413.6 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.441 | 2.425 | 96.11 |
| `smtp_session` | 0.005 | 0.988 | 9.84 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.080 | 2.310 | 0.488 | 9.82 |
| `EnrichEmails` | 0.005 | 0.481 | — | 0.481 | 1.04 |
| `GetAttachmentStream` | 0.487 | 2.350 | 2.425 | 0.681 | 0.80 |
| `GetEmailContent` | 0.005 | 0.501 | — | 0.501 | 13.40 |
| `GetFolders` | 0.005 | 1.937 | 1.937 | 0.242 | 7.73 |
| `ReadFolder` | 0.498 | 2.425 | 2.425 | 0.494 | 36.06 |
| `ReadToday` | 0.005 | 0.499 | — | 0.499 | 7.55 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 25.82 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.387** | 0.444 | 0.481 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.586 | 0.669 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.428** | 0.441 | 0.443 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 96.11 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.498 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 10.00 clients | 0 clients | 100.0 % | 28.0 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 9.52 cœurs | 24 cœurs | 39.7 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-44852` | 15.00 éléments | 100 éléments | 15.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#57368` (CPU) | 3.19 cœurs | 24 cœurs | 13.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#52784` (CPU) | 3.11 cœurs | 24 cœurs | 13.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#72180` (CPU) | 2.39 cœurs | 24 cœurs | 10.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#55092` (CPU) | 2.38 cœurs | 24 cœurs | 9.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#44852` (CPU) | 2.26 cœurs | 24 cœurs | 9.4 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 28.0 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 320 542

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 3 678 |
| OpenAI | gpt-4o-mini | prompt | 316 864 |
| OpenAI | text-embedding-3-small | embedding | 462 305 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 172 | 0 (0.0 %) | 0 | 4.6 | 1.16 | 0.98 | 2.61 |
| étiquetage (chat) | OpenAI | 172 | 0 (0.0 %) | 0 | 4.6 | 1.10 | 0.94 | 2.61 |
| embedding | OpenAI | 172 | 0 (0.0 %) | 0 | 4.6 | 0.56 | 0.45 | 1.51 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 3 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 1.0 | 18.0 |
| GPU — VRAM occupée (Mo) | 1 744 | 1 759 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.7 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 594.5** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.29** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **3.9 ms** | sur 759 639 requêtes HTTP k6 |
| Taux de cache (blocs) | **98.01 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **7.94 Mo/s (1 016 blocs/s)** | attente disque : 14.4 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **277 435 / 29 548** | rapport 9.4 |
| Écritures de lignes / s (ins+upd+del) | **165.0** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.28 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 15 % |
| Sessions ouvertes / s | **3.03** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **44.5 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 571 / 2 023** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **99 / 100 %** | fautes majeures/s max : 23.1 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 161.7 s | 166290 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, HtmlBody : 18.0 Go lus, 3.3 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 14.6 % du temps SQL, 45.6 % des lectures disque du tir | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 44.6 s | 8838 | `pages-par-ligne` | 31.1 pages par ligne rendue, 622 par appel, 41.9 Go lus | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 39.7 s | 15236 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Content : 2.9 Go lus, 1.8 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 3.6 % du temps SQL, 24.5 % des lectures disque du tir | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}`<br>`MailRepository.UpdateAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 38.5 s | 8759 | `pages-par-ligne` | 31.3 pages par ligne rendue, 625 par appel, 41.8 Go lus | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 23.4 s | 166260 | `colonne-volumineuse` | sélectionne Body, BodyHtml : 5.8 Go lus, 0.1 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **87 évictions `pg_stat_statements`** pendant le tir (97 977 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

135 formes de requête, 6 005 674 appels, **18.5 min** de temps serveur cumulé — soit **1.5 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **15.0 %** | 15 % | 8 778 | 0.01 | 18.96 | 51.3 | 339 | 0 % | 0 | 885 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **14.6 %** | 30 % | 166 290 | 0.22 | 0.97 | 1.0 | 14 | 18 % | 0 | 1 873 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 3 | **13.5 %** | 43 % | 8 810 | 0.01 | 17.07 | 51.2 | 392 | 1 % | 0 | 887 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **6.7 %** | 50 % | 88 881 | 0.12 | 0.83 | 18.1 | 100 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **5.9 %** | 56 % | 759 576 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `PostgresTenantRegistryClient.GetMailboxAsync` ← `GET /api/v1/Mail/folders/{foldername}` | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 6 | **4.0 %** | 60 % | 8 838 | 0.01 | 5.05 | 20.0 | 622 | 1 % | 0 | 890 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 7 | **3.6 %** | 63 % | 15 236 | 0.02 | 2.61 | 1.0 | 25 | 60 % | 0 | 1 237 | **Code** — 60 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}`<br>`MailRepository.UpdateAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 8 | **3.5 %** | 67 % | 8 759 | 0.01 | 4.39 | 20.0 | 625 | 1 % | 0 | 880 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 9 | **3.1 %** | 70 % | 138 620 | 0.18 | 0.25 | 1.0 | 14 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 10 | **2.9 %** | 73 % | 6 035 | 0.01 | 5.26 | 178.0 | 540 | 1 % | 0 | 1 041 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 11 | **2.1 %** | 75 % | 166 260 | 0.22 | 0.14 | 1.0 | 5 | 1 % | 0 | 1 872 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |
| 12 | **2.0 %** | 77 % | 281 000 | 0.37 | 0.08 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `MailRepository.ResolveActiveDuplicateRefsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 13 | **1.8 %** | 79 % | 94 804 | 0.12 | 0.21 | 18.0 | 5 | 0 % | 0 | 1 783 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | site inconnu ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}`<br>`MailRepository.LoadMailsReferencingAnyRootAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 14 | **1.3 %** | 80 % | 88 875 | 0.12 | 0.16 | 18.1 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.GetMailsByUidsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 15 | **1.2 %** | 81 % | 281 003 | 0.37 | 0.05 | 2.1 | 4 | 0 % | 0 | 1 996 | — | `MailRepository.EnrichManyWithBiologyAcksAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 16 | **1.2 %** | 82 % | 45 359 | 0.06 | 0.28 | 27.0 | 5 | 0 % | 0 | 1 401 | — | `MailRepository.GetLatestMessageIdsPerThreadAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **0.9 %** | 83 % | 144 203 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **0.9 %** | 84 % | 186 927 | 0.25 | 0.05 | 1.5 | 6 | 0 % | 0 | 1 895 | — | `MailRepository.GetMailAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`, `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |
| 19 | **0.9 %** | 85 % | 144 199 | 0.19 | 0.07 | 14.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **0.9 %** | 86 % | 88 886 | 0.12 | 0.11 | 5.7 | 9 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.9 % | 87.6 % |
| INSERT | 4.2 % | 3.0 % |
| UPDATE | 0.4 % | 1.3 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.4 % | 7.6 % |
| bases : praticien (N bases) | 90.4 % | 82.1 % |
| bases : unique (1 base) | 9.6 % | 17.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **19.0** | 219 | 8 778 | 15.0 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **17.1** | 177 | 8 810 | 13.5 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **5.3** | 135 | 6 035 | 2.9 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **5.1** | 95 | 8 838 | 4.0 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **4.4** | 75 | 8 759 | 3.5 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 293 | 153 867 | 0 | 5 | 0.1 Mo |
| `Mails` | 722 | 93 861 | 698 | 26 | 0.1 Mo |
| `MailTags` | 197 | 48 856 | 70 | 43 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 193 | 28 629 | 1 269 | 157 | 8.0 Mo |
| `MailRecipients` | 178 | 27 768 | 58 | 26 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 103 | 26 883 | 186 | 43 | 30.0 Mo |
| `MailContents` ⚠️ index candidat | 72 | 11 232 | 2 150 | 156 | 1.9 Mo |
| `PendingActions` | 174 | 5 131 | 0 | 31 | 0.1 Mo |
| `Tags` | 135 | 2 430 | 88 | 0 | 0.0 Mo |
| `MailFolders` | 368 | 990 | 347 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (5.9 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 98.0 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 193 fois (28629 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 103 fois (26883 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 72 fois (11232 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°7 (3.6 % du temps SQL) — 60 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°10 (2.9 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°6 (4.0 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°13 (1.8 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-132416.tsv`, `pgserver-journey-debut-124542.tsv`, `pgserver-journey-fin-132423.tsv`, `pgtables-journey-debut-124550.tsv`, `pgtables-journey-fin-132428.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 248060 — dont **248060** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261108-t434-task-132336.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._

## Findings — analyse de code

> - **Tir** : `journey-courte-1400-1996-20261108-t434-task`, code api-mail `dfda613b` (branche de task-434, journal de
>   la campagne : `code : dfda613b (variante B)`). **Mesures** : `pgstats-journey-132416.tsv`, 759 639 requêtes HTTP.
>   **Mode** : normal.
> - **Site** : commentaire `site=` de task-432, complété par `git grep` au commit du tir.
> - **Plans** : `Docs/audits/findings/plans/20261108-t434-task/`, base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la
>   plus volumineuse du banc, la même que les rejeux précédents). Aucune migration entre le commit du tir et `develop`.
> - **Contrôle de non-confabulation** : `python Tools/loadtest-findings/findings.py check` — **79 éléments, 0 écart**.

**Candidats** : 8 sur 8.
- Trois formes signalées par les détecteurs de task-431. Deux sont les **formes d'après correctif** de FND-007 et
  FND-009 (task-434), la troisième est FND-010.
- Cinq formes non signalées, les plus coûteuses en temps : FND-008, FND-014, et trois formes nouvelles du parcours
  (FND-016 à FND-018).

| Finding | Verdict | Classe | Temps SQL | Lu sur disque | Gain borné |
|---|---|---|---|---|---|
| FND-007 Document médical à l'ouverture d'un message — forme d'après correctif | **écarté** (corrigé) | `colonne-volumineuse` | 161.7 s | 3.3 Go | — |
| FND-009 Contenu du message — forme d'après correctif | **écarté** (corrigé) | `colonne-volumineuse` | 23.4 s | 0.1 Go | — |
| FND-010 Recherche vectorielle exacte, sans index | **plausible** | `pages-par-ligne` | 44.6 s | 0.6 Go | dépend de la taille des boîtes |
| FND-014 Messages qui citent un fil : `LIKE '%…%'` sur `References` | **plausible** | `hors-détecteur` | 20.3 s | 0.0 Go | dépend de la taille des boîtes |
| FND-008 Chargement du catalogue des types par Npgsql | **écarté** | `hors-détecteur` | 31.7 s | 0.3 Go | — |
| FND-016 Les messages d'une page, lus par UID | **écarté** | `hors-détecteur` | 14.1 s | 0.0 Go | — |
| FND-017 Les étiquettes d'un message | **écarté** | `hors-détecteur` | 10.1 s | 0.0 Go | — |
| FND-018 Les résultats de biologie marqués d'une page | **écarté** | `hors-détecteur` | 10.0 s | 0.0 Go | — |

**Ce que la task a changé** :
- les formes d'avant correctif disparaissent : FND-009 est absent du tir. FND-007 ne garde que **20 appels**, émis par
  la voie du bus (`bus:AddNewMail`, l'indexation, hors du périmètre de la task), contre 168 539 au contrôle ;
- les formes d'après correctif ne lisent plus que les corps, sur la route qui les affiche.

#### FND-007 — Le document médical à l'ouverture d'un message, forme d'après correctif

- **Verdict** : **écarté** — le défaut est corrigé. La forme ne lit plus ni `Embedding` ni `MetadataJson`, et sert
  `Body` et `HtmlBody` sur la route qui les affiche (faux positif connu de D2, « le chemin qui sert ce contenu »).
- **Forme** : `bc5acb2c69c5d6799de85c3fd161a904` (après correctif ; avant : `9a63b74fac8c0708f158bb2588df9b57`)
- **Détecteurs** : `colonne-volumineuse` (Body, HtmlBody) et `poids-dans-le-tir`.
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1254` (`PopulateMailContentAsync`), projection
  `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1808` (`MedicalDocumentContentProjection`). Retrouvé par
  le commentaire `site=MailRepository.PopulateMailContentAsync`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 166 290 |
| Temps SQL | 161.7 s |
| Part du temps SQL | 14.6 % |
| Pages lues | 18.0 Go |
| Pages par appel | 14 |
| Lu sur disque | 3.3 Go |
| Part des lectures disque | 45.6 % |

- **Cause du coût restant** : `HtmlBody` pèse 37 860 octets par ligne, sur 46 490 pour l'entité entière. C'est le
  HTML du compte rendu, que le médecin regarde.
- **Preuve** : plan par index, 2 pages, sans détoastage sous PostgreSQL 16. Les 14 pages par appel du tir sont le
  détoastage des corps. **Plan** : `FND-007-colonnes.txt`

```text
| lignes | Body (octets/ligne) | HtmlBody (octets/ligne) | Embedding (octets/ligne) | MetadataJson (octets/ligne) |
| 157 | 2482 | 37860 | 6148 |  |
```

- **Gain mesuré par l'A/B** : pages lues de la forme 24,4 → 19,3 Go (−21 %), lectures disque inchangées (3,5 Go),
  voir la section « Mesure au banc » de task-434.
- **Piste suivante, à instruire** : le document reste le premier lecteur de disque du tir à cause de `HtmlBody`. Si
  les clients n'affichent le HTML du document qu'à son dépliage, le servir à part en retirerait la lecture de
  l'ouverture. Cela suppose de relire les trois clients avant toute task.

#### FND-009 — Le contenu du message, forme d'après correctif

- **Verdict** : **écarté** — le défaut est corrigé. La forme sert `Body`, `BodyHtml` et `Summary` sur la route qui
  les affiche, sans `Embedding`.
- **Forme** : `2a6ce021d70dc17b91701c8f338e7a6f` (après correctif ; avant : `4b9380ddd1837d2bc365a5afbc833f85`, absente
  du tir)
- **Détecteurs** : `colonne-volumineuse` (Body, BodyHtml).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1254` (`PopulateMailContentAsync`), projection
  `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1816` (`ContentProjection`).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 166 260 |
| Temps SQL | 23.4 s |
| Pages lues | 5.8 Go |
| Pages par appel | 5 |
| Lu sur disque | 0.1 Go |

- **Preuve** : **Plan** : `FND-009-colonnes.txt`

```text
| lignes | Body (octets/ligne) | BodyHtml (octets/ligne) | Summary (octets/ligne) | Embedding (octets/ligne) |
| 156 | 2842 |  |  | 6148 |
```

- **Gain mesuré par l'A/B** : 37,6 → 23,4 s, pages lues 11,5 → 6,3 Go (−45 %).

#### FND-010 — La recherche vectorielle calcule la distance de chaque document du dossier

- **Verdict** : **plausible**, inchangé : le code n'a pas bougé.
- **Forme** : `9b0276b995554c73320b5caa00935e87`. Variante : `90fed31c06a6aff57d1fb5c7c8d25a5d`.
- **Détecteurs** : `pages-par-ligne`.
- **Site** : `src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs:249`
  (`SearchMedicalDocumentsByVectorAsync`). Retrouvé par le commentaire `site=`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 8 838 |
| Temps SQL | 44.6 s |
| ms par appel | 5.05 |
| Pages par appel | 622 |
| Lu sur disque | 0.6 Go |

- **Cause probable** : aucun index vectoriel. Chaque recherche détoaste le vecteur de tous les documents du dossier.
- **Preuve** : **Plan** : `FND-010.txt`

```text
->  Seq Scan on "MailMedicalDocuments" m (actual time=0.021..2.848 rows=2 loops=1)
Rows Removed by Filter: 155
```

- **Pourquoi plausible** : à 157 documents par boîte, la recherche exacte est le bon plan. À trancher par un tir sur
  des boîtes 10 fois plus grosses.

#### FND-014 — Les messages qui citent un fil sont cherchés par `LIKE '%…%'` sur `References`

- **Verdict** : **plausible**, inchangé.
- **Forme** : `a5978bf1120a527de14ca8d1c8283f21`
- **Détecteurs** : `hors-détecteur` (coût seul).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:2536` (`LoadMailsReferencingAnyRootAsync`), qui
  applique `src/Infrastructure/Repositories/MailDb/MailRepository.cs:2440` (`ReferencesAnyOf`).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 94 804 |
| Temps SQL | 20.3 s |
| ms par appel | 0.21 |
| Pages par appel | 5 |

- **Preuve** : **Plan** : `FND-014.txt`

```text
Seq Scan on "Mails" m (actual time=0.006..0.138 rows=16 loops=1)
Rows Removed by Filter: 140
```

- **Pourquoi plausible** : le balayage coûte 5 pages au banc, mais il croît avec la boîte. Même tir que FND-010.

#### FND-008 — Npgsql charge le catalogue des types à chaque source de données neuve

- **Verdict** : **écarté** — coût de démarrage, une fois par réplica et par base.
- **Forme** : `e759630c6a29f7fe648e9fb10ab88668`
- **Détecteurs** : `hors-détecteur` (coût seul).
- **Site** : requête interne de Npgsql, sans commentaire `site=`. Recherche citée :
  `git grep -n -E "NpgsqlDataSourceBuilder|NpgsqlDataSource\.Create|\.UseNpgsql\(" dfda613b -- src/`. Les sources de
  données des bases praticien sont construites et **mises en cache par processus et par chaîne de connexion** dans
  `src/Infrastructure/Repositories/MailDb/BaseRepository.cs:317` (`GetOrCreateDataSource`).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 6 035 |
| Temps SQL | 31.7 s |
| ms par appel | 5.26 |
| Bases | 1 041 |

- **Cause** : Npgsql charge le catalogue des types à la première connexion d'une source de données. Le cache par
  processus le borne à une fois par réplica et par base. 6 035 appels sur 1 041 bases, soit environ 6 par base, pour
  5 réplicas redémarrés avec l'AppHost du tir. En régime établi, ce coût ne se paie qu'au déploiement.
- **Pas de plan** : la requête porte sur le catalogue système, et son coût est fixe par appel. C'est le code qui
  tranche.

#### FND-016 — Les messages d'une page, lus par UID

- **Verdict** : **écarté** — coût normal.
- **Forme** : `38927728f1f6554f6d1a7c88063a13be`
- **Détecteurs** : `hors-détecteur` (coût seul).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1656` (`GetMailsByUidsAsync`). Retrouvé par
  le commentaire `site=MailRepository.GetMailsByUidsAsync`, route `POST …/emails/enrich/sync`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 88 875 |
| Temps SQL | 14.1 s |
| ms par appel | 0.16 |
| Lignes par appel | 18.1 |
| Pages par appel | 5 |

- **Preuve** : 5 pages ; l'index `IX_Mails_FolderPath_UidValidity_Uid_Unique` existe, et le planificateur lui préfère
  le balayage d'une table de 156 lignes. **Plan** : `FND-016.txt`

```text
Seq Scan on "Mails" m (actual time=0.005..0.036 rows=18 loops=1)
Rows Removed by Filter: 138
```

#### FND-017 — Les étiquettes d'un message

- **Verdict** : **écarté** — coût normal. Le poids vient de la fréquence (2 appels par ouverture servie par la base).
- **Forme** : `be95a8c47cbdd9a4824f427030e5ec35`
- **Détecteurs** : `hors-détecteur` (coût seul).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1186` (`GetMailAsync`). Retrouvé par le
  commentaire `site=MailRepository.GetMailAsync`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 186 927 |
| Temps SQL | 10.1 s |
| ms par appel | 0.05 |
| Pages par appel | 6 |

- **Preuve** : l'index `IX_MailTags_MailId_TagId` existe ; à 248 lignes, le balayage est le bon plan. **Plan** :
  `FND-017.txt`

```text
->  Seq Scan on "MailTags" m (actual time=0.003..0.044 rows=2 loops=1)
Rows Removed by Filter: 246
```

#### FND-018 — Les résultats de biologie marqués d'une page

- **Verdict** : **écarté** — coût normal.
- **Forme** : `11c8c9fdd0b35ceb0f59532bd9ba2471`
- **Détecteurs** : `hors-détecteur` (coût seul).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:2047` (`LoadBulkContentLookupsAsync`, lignes
  marquées seules en mode en-tête). Retrouvé par le commentaire `site=MailRepository.LoadBulkContentLookupsAsync`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 88 886 |
| Temps SQL | 10.0 s |
| ms par appel | 0.11 |
| Pages par appel | 9 |

- **Preuve** : l'index `IX_MailMedicalDocumentBiology_MedicalDocumentId` existe ; à 119 lignes, le balayage est le
  bon plan. **Plan** : `FND-018.txt`

```text
Seq Scan on "MailMedicalDocumentBiology" m (actual time=0.030..0.030 rows=0 loops=1)
Rows Removed by Filter: 119
```

### Connus du registre — remesurés

- FND-001, FND-002, FND-004 : correctifs en place (voir le dossier de candidats) ; FND-003 et FND-005 : formes
  absentes, les correctifs tiennent.
- FND-006, FND-011, FND-012, FND-013, FND-015 : écartés, remesurés sans changement de nature.

### Ce que l'humain décide

1. **FND-007, piste suivante** : le HTML du document (`HtmlBody`, 37 Ko par ligne) reste le premier lecteur de disque
   du tir (45,6 %). Vérifier dans les trois clients s'il est affiché dès l'ouverture du message. Si non, le servir à
   part, au dépliage du document.
2. **FND-010 et FND-014** : un tir sur des boîtes 10 fois plus grosses, toujours dû.
