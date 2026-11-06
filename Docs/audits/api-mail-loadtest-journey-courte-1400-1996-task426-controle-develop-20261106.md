# Rapport de tir — journey-courte-1400-1996-20261106-task426-controle-develop

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261106-task426-controle-develop-163436.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1996 médecins, 1 étape(s) dépassent le temps de réponse attendu : « Ouvrir un message enrichi (servi base) »
- 5 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 24 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.009 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 748440 — **débit émergent global** : 331.1 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53269 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 331.1 | **219.8** | 96.3 | **831.3** | — | 8810.2 | 0.01 | 100.0 | 0 | 0 | 243572/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 213140 | 289.20 | 0.01 | 800.2 |
| **1996 médecins** | 1080 | 933 | 381029 | 408.39 | 0.01 | 1473.6 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 71 / 548 (n=64004) | 105 / 672 (n=113412) |
| 2 | Ouvrir / rafraîchir l'inbox | 52 / 128 (n=32004) | 98 / 310 (n=56712) |
| 3 | Ouvrir un message enrichi (servi base) | 47 / 99 (n=15999) | 105 / 269 (n=28335) |
| 4 | Ouvrir un message froid (fetch IMAP) | 458 / 527 (n=6292) | 491 / 616 (n=11391) |
| 5 | Recherche | 348 / 610 (n=4692) | 424 / 855 (n=8556) |
| 6 | Envoi (acquittement UI) | 518 / 944 (n=4670) | 557 / 1038 (n=8457) |
| 7 | Télécharger une PJ (~124 Ko) | 51 / 130 (n=6316) | 127 / 743 (n=11587) |
| 8 | Marquer lu | 54 / 108 (n=12843) | 104 / 246 (n=22683) |
| 9 | Rechercher un patient | 63 / 87 (n=4666) | 75 / 166 (n=8474) |
| 10 | Ouvrir la page d'un dossier patient | 67 / 146 (n=7026) | 133 / 350 (n=12664) |
| 11 | Fiche patient complète (ressenti médecin) | 381 / 680 (n=3513) | 678 / 1693 (n=6332) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.4 / 20 | 34.2 / 60 | 7846 | 680 |
| **1996 médecins** | 14.5 / 20 | 34.2 / 60 | 14160 | 1693 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2164 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 953 ms en moyenne, 8810 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2237 / 3057 (magasin) | 2237 / 3057 (magasin) |
| Backends Postgres (moy/max) | 1242 / 1436 | 1992 / 2031 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 2 | 0 / 3 |
| PgBouncer `cl_waiting` (échant. non nuls) | 42/176 (24 %) | 67/145 (46 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/176 (0 %) | 0/145 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 42/176 (24 %) | 67/145 (46 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 47.0 | 106.3 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 47.0 | 106.3 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 122 / 403 | 92 / 265 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 104 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1405 | 2000 |
| Backends **directs** — audit + provisionnement (max) | 30 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 | 0 / 3 |
| RSS par réplica api-mail, Mo (moy/max) | 1177 / 1624 (5 réplicas) | 2139 / 2405 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1436.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2031.0 / 2500** (81.2 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15999)
- palier 1996 : cohorte 1996 chauffée à 99.8 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28335)

> ⓘ Chauffe : **305 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 71 (300) | 548 (1500) | 64004 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 52 (300) | 128 (1000) | 32004 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 47 (100) | 99 (500) | 15999 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 458 (800) | 527 (2500) | 6292 | ✅ |
| 5 | Recherche | 348 (500) | 610 (2000) | 4692 | ✅ |
| 6 | Envoi (acquittement UI) | 518 (1000) | 944 (3000) | 4670 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 51 (500) | 130 (2000) | 6316 | ✅ |
| 8 | Marquer lu | 54 (200) | 108 (1000) | 12843 | ✅ |
| 9 | Rechercher un patient | 63 (300) | 87 (1500) | 4666 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 67 (500) | 146 (2000) | 7026 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 381 (1500) | 680 (4000) | 3513 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 105 (300) | 672 (1500) | 113412 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 98 (300) | 310 (1000) | 56712 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 105 (100) | 269 (500) | 28335 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 491 (800) | 616 (2500) | 11391 | ✅ |
| 5 | Recherche | 424 (500) | 855 (2000) | 8556 | ✅ |
| 6 | Envoi (acquittement UI) | 557 (1000) | 1038 (3000) | 8457 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 127 (500) | 743 (2000) | 11587 | ✅ |
| 8 | Marquer lu | 104 (200) | 246 (1000) | 22683 | ✅ |
| 9 | Rechercher un patient | 75 (300) | 166 (1500) | 8474 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 133 (500) | 350 (2000) | 12664 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 678 (1500) | 1693 (4000) | 6332 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 113412 | 200 | 672 | 22667.9 | 39.2 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 56712 | 125 | 310 | 7101.5 | 12.3 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8457 | 678 | 1038 | 5737.3 | 9.9 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11391 | 503 | 616 | 5730.6 | 9.9 % |
| 🟢 | Recherche (`search`) | 8556 | 478 | 855 | 4092.0 | 7.1 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 28335 | 126 | 269 | 3561.5 | 6.2 % |
| 🟢 | Marquer lu (`mark_read`) | 22683 | 121 | 246 | 2751.5 | 4.8 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 11587 | 206 | 743 | 2383.5 | 4.1 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 7080 | 207 | 726 | 1462.8 | 2.5 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6332 | 158 | 350 | 999.6 | 1.7 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8474 | 84 | 166 | 712.3 | 1.2 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6332 | 91 | 167 | 575.3 | 1.0 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 5 🟠 · 7 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 22667.9 s, 39.2 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 6.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 7101.5 s, 12.3 %)
  - **dispersion p95/p50 = 3.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 3561.5 s, 6.2 %)
  - **hors grille** — le médecin attend trop
- **Télécharger une PJ (~124 Ko)** (`attachment`, 2383.5 s, 4.1 %)
  - **dispersion p95/p50 = 5.8×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 1462.8 s, 2.5 %)
  - **dispersion p95/p50 = 4.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 16001 | 392 | 1004 | 6221.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 16001 | 70 | 509 | 2357.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 16001 | 34 | 177 | 953.0 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 16001 | 66 | 91 | 1091.8 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 16002 | 26 | 130 | 689.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 16002 | 67 | 126 | 1185.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28353 | 413 | 992 | 11930.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28353 | 92 | 544 | 5021.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28353 | 77 | 269 | 3068.9 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28353 | 83 | 172 | 2647.2 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28356 | 58 | 226 | 2416.9 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28356 | 143 | 333 | 4684.6 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (992 ms de p95, 413 ms de p50, n=28353), qui porte **aussi** le temps serveur de l'étape (11930.4 s, 53 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (333 ms de p95, 143 ms de p50, n=28356), qui porte **aussi** le temps serveur de l'étape (4684.6 s, 66 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21770 | 194.0 | 89.4 | 526.5 | 779.7 | 3278.5 |
| attachment,palier:1400 | 6316 | 75.5 | 51.5 | 96.9 | 129.9 | 1343.2 |
| attachment,palier:1996 | 11587 | 205.7 | 127.0 | 511.7 | 742.8 | 1583.3 |
| attachment,palier:transition | 578 | 405.4 | 189.1 | 1076.7 | 1224.0 | 1990.0 |
| dashboard | 217608 | 229.6 | 98.2 | 555.2 | 804.5 | 3306.4 |
| dashboard,call:coverage,palier:1400 | 16001 | 68.2 | 65.9 | 83.0 | 90.6 | 213.0 |
| dashboard,call:coverage,palier:1996 | 28353 | 93.4 | 83.0 | 138.9 | 171.8 | 1094.3 |
| dashboard,call:coverage,palier:transition | 1042 | 402.2 | 255.9 | 978.1 | 1073.7 | 1544.6 |
| dashboard,call:folder,palier:1400 | 16001 | 388.8 | 391.8 | 764.8 | 1004.0 | 1565.2 |
| dashboard,call:folder,palier:1996 | 28353 | 420.8 | 412.7 | 794.8 | 991.6 | 1598.7 |
| dashboard,call:folder,palier:transition | 1042 | 749.6 | 709.6 | 1278.9 | 1394.7 | 2095.3 |
| dashboard,call:folders,palier:1400 | 16001 | 59.6 | 34.2 | 160.1 | 176.8 | 418.9 |
| dashboard,call:folders,palier:1996 | 28353 | 108.2 | 76.6 | 224.3 | 269.2 | 1449.5 |
| dashboard,call:folders,palier:transition | 1042 | 427.0 | 272.7 | 1012.8 | 1153.5 | 1678.6 |
| dashboard,call:today,palier:1400 | 16001 | 147.3 | 69.6 | 487.4 | 509.0 | 784.8 |
| dashboard,call:today,palier:1996 | 28353 | 177.1 | 92.3 | 510.8 | 544.5 | 1590.3 |
| dashboard,call:today,palier:transition | 1042 | 639.0 | 623.5 | 1224.3 | 1370.2 | 1950.2 |
| dashboard,palier:1400 | 64004 | 166.0 | 70.6 | 461.1 | 547.7 | 1565.2 |
| dashboard,palier:1996 | 113412 | 199.9 | 104.9 | 485.4 | 671.9 | 1598.7 |
| dashboard,palier:transition | 4168 | 554.4 | 507.1 | 1130.2 | 1302.4 | 2095.3 |
| mark_read | 43365 | 133.0 | 83.9 | 201.8 | 347.8 | 2534.9 |
| mark_read,palier:1400 | 12843 | 61.3 | 53.8 | 95.4 | 108.0 | 300.2 |
| mark_read,palier:1996 | 22683 | 121.3 | 103.6 | 199.9 | 246.2 | 1251.8 |
| mark_read,palier:transition | 1175 | 284.2 | 82.0 | 1008.3 | 1168.0 | 1661.6 |
| patient_docs | 173616 | 142.4 | 87.0 | 263.3 | 391.7 | 2651.0 |
| patient_docs,palier:1400 | 50705 | 64.1 | 57.7 | 112.7 | 133.3 | 404.6 |
| patient_docs,palier:1996 | 91678 | 138.0 | 114.7 | 261.9 | 318.1 | 927.0 |
| patient_docs,palier:transition | 4419 | 272.3 | 77.7 | 943.0 | 1159.6 | 1755.5 |
| patient_dossier | 12005 | 164.7 | 101.0 | 287.0 | 464.3 | 2743.1 |
| patient_dossier,palier:1400 | 3513 | 74.0 | 66.6 | 123.9 | 145.6 | 265.6 |
| patient_dossier,palier:1996 | 6332 | 157.9 | 132.6 | 284.4 | 349.7 | 1145.2 |
| patient_dossier,palier:transition | 323 | 318.1 | 86.2 | 1083.8 | 1337.6 | 1907.7 |
| patient_opposition | 12005 | 112.2 | 72.8 | 133.3 | 231.1 | 2312.3 |
| patient_opposition,palier:1400 | 3513 | 67.6 | 65.4 | 81.6 | 88.2 | 202.0 |
| patient_opposition,palier:1996 | 6332 | 90.9 | 81.5 | 132.9 | 167.0 | 634.6 |
| patient_opposition,palier:transition | 322 | 244.4 | 71.7 | 907.3 | 1048.7 | 1504.0 |
| patient_search | 15993 | 104.8 | 67.5 | 129.8 | 239.3 | 2346.4 |
| patient_search,palier:1400 | 4666 | 56.0 | 63.1 | 79.0 | 87.1 | 174.3 |
| patient_search,palier:1996 | 8474 | 84.1 | 75.4 | 129.9 | 165.9 | 929.9 |
| patient_search,palier:transition | 421 | 230.8 | 67.3 | 822.2 | 1032.9 | 1416.3 |
| read_content | 54402 | 128.5 | 73.5 | 218.3 | 329.6 | 2538.7 |
| read_content,palier:1400 | 15999 | 53.9 | 47.3 | 82.8 | 98.8 | 313.8 |
| read_content,palier:1996 | 28335 | 125.7 | 105.2 | 220.2 | 269.4 | 1158.6 |
| read_content,palier:transition | 1227 | 321.6 | 78.1 | 1048.9 | 1223.0 | 1670.2 |
| read_content_cold | 21712 | 515.1 | 478.0 | 573.9 | 677.1 | 2893.5 |
| read_content_cold,palier:1400 | 6292 | 460.3 | 458.3 | 511.4 | 527.4 | 640.9 |
| read_content_cold,palier:1996 | 11391 | 503.1 | 491.2 | 574.7 | 615.7 | 1577.7 |
| read_content_cold,palier:transition | 567 | 665.5 | 484.9 | 1316.9 | 1484.7 | 1916.7 |
| read_list | 108804 | 131.7 | 73.3 | 252.2 | 419.3 | 2619.9 |
| read_list,call:emails,palier:1400 | 16002 | 74.1 | 66.7 | 108.4 | 126.4 | 338.3 |
| read_list,call:emails,palier:1996 | 28356 | 165.2 | 143.1 | 279.5 | 333.3 | 1165.1 |
| read_list,call:emails,palier:transition | 1171 | 408.0 | 138.0 | 1149.5 | 1330.5 | 1804.9 |
| read_list,call:folder,palier:1400 | 16002 | 43.1 | 25.6 | 68.9 | 129.6 | 556.6 |
| read_list,call:folder,palier:1996 | 28356 | 85.2 | 57.7 | 160.7 | 226.4 | 1606.5 |
| read_list,call:folder,palier:transition | 1171 | 295.3 | 79.4 | 929.6 | 1117.2 | 1548.3 |
| read_list,palier:1400 | 32004 | 58.6 | 51.8 | 102.9 | 127.8 | 556.6 |
| read_list,palier:1996 | 56712 | 125.2 | 97.7 | 245.9 | 309.9 | 1606.5 |
| read_list,palier:transition | 2342 | 351.6 | 114.7 | 1046.5 | 1226.4 | 1804.9 |
| search | 16215 | 484.7 | 397.7 | 691.1 | 1152.7 | 3893.8 |
| search,palier:1400 | 4692 | 396.0 | 348.0 | 482.8 | 610.5 | 1593.9 |
| search,palier:1996 | 8556 | 478.3 | 424.1 | 629.9 | 854.5 | 1843.0 |
| search,palier:transition | 399 | 671.9 | 430.9 | 1495.8 | 1654.5 | 2511.6 |
| send | 15457 | 707.9 | 599.5 | 984.6 | 1076.3 | 3252.9 |
| send,palier:1400 | 4670 | 652.2 | 517.6 | 919.5 | 944.4 | 1096.5 |
| send,palier:1996 | 8457 | 678.4 | 556.8 | 985.2 | 1037.8 | 1961.7 |
| send,palier:transition | 452 | 799.6 | 769.3 | 1432.5 | 1678.3 | 2226.7 |
| treatment | 13518 | 191.9 | 115.9 | 300.0 | 769.4 | 4907.3 |
| treatment,palier:1400 | 3923 | 92.0 | 91.0 | 128.3 | 145.2 | 2805.6 |
| treatment,palier:1996 | 7080 | 206.6 | 149.3 | 305.0 | 725.7 | 4685.1 |
| treatment,palier:transition | 309 | 418.5 | 140.7 | 1142.8 | 1321.5 | 4907.3 |
| warmup | 21956 | 952.8 | 693.8 | 1638.5 | 2472.0 | 8810.2 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-06T14:56:55.368000+00:00 → 2026-11-06T15:34:36.149000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t426-ctrl.csv`) | ✅ 72035 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-35160` | 1.07 | 10 | 27 | 0.036 | 5.09 |
| `DESKTOP-DEV-X2C-51548` | 1.06 | 15 | 33 | 0.037 | 4.89 |
| `DESKTOP-DEV-X2C-56880` | 1.15 | 16 | 37 | 0.040 | 5.02 |
| `DESKTOP-DEV-X2C-59188` | 1.29 | 13 | 24 | 0.029 | 5.06 |
| `DESKTOP-DEV-X2C-64928` | 1.02 | 12 | 44 | 0.025 | 4.64 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.55 | 4.13 | 2166 |
| `com.docker.backend#34124` | 0.00 | 0.19 | 40 |
| `dcp#19564` | 0.00 | 0.00 | 12 |
| `dcp#34508` | 0.82 | 2.84 | 3167 |
| `dcp#40332` | 0.00 | 0.04 | 13 |
| `dcp#42676` | 0.00 | 0.04 | 12 |
| `dcp#4268` | 0.00 | 0.00 | 12 |
| `dcp#42816` | 0.00 | 0.00 | 12 |
| `dcp#44124` | 0.00 | 0.04 | 13 |
| `dcp#49636` | 0.01 | 0.18 | 53 |
| `dcp#59604` | 0.00 | 0.00 | 12 |
| `dcp#60744` | 0.00 | 0.23 | 12 |
| `dcp#61376` | 0.00 | 0.04 | 13 |
| `dcp#61924` | 0.00 | 0.04 | 14 |
| `dcp#62020` | 0.00 | 0.00 | 12 |
| `dcp#63960` | 0.00 | 0.00 | 12 |
| `dcp#65376` | 0.00 | 0.09 | 12 |
| `k6#85763` | 0.85 | 1.87 | 2908 |
| `mss.mail.api#35160` | 0.75 | 3.27 | 2208 |
| `mss.mail.api#51548` | 0.74 | 2.61 | 2316 |
| `mss.mail.api#56880` | 0.80 | 2.63 | 2405 |
| `mss.mail.api#59188` | 0.86 | 3.21 | 2380 |
| `mss.mail.api#64928` | 0.75 | 2.71 | 2282 |
| `mss.mail.e2e#40132` | 0.01 | 0.09 | 32 |
| `vmmemWSL#36464` | 6.71 | 11.77 | 57624 |
| `loadtest-otel-collector-mjebaeuw` | 0.03 | 0.18 | 100 |
| `loadtest-pgbouncer-nydetdqu` | 0.53 | 0.89 | 48 |
| `mss-mail-flagsmith-app-b6152948` | 0.13 | 0.41 | 567 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.12 | 150 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.07 | 164 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.12 | 265 |
| `mss-mail-rabbitmq-vnahzyfd` | 0.01 | 0.10 | 139 |
| `mss-mail-redis-b6152948` | 0.30 | 1.34 | 963 |
| `mss-mail-rediscommander-ncsrmhsx` | 0.01 | 0.23 | 24 |
| `mss-mail-seq-b6152948` | 0.12 | 4.04 | 20029 |
| `postgres-pgvector` | 3.10 | 8.43 | 47565 |

- **Hôte** : CPU 76.2 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 37
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9466, cl_waiting max 20, cl_waiting_maintenance max 20, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 106, maxwait_ms max 106, maxwait_practitioner_ms max 0, sv_active max 36, sv_idle max 1599, sv_login max 3
- **Backends Postgres** : audit max 5, cache_mb max 41368, direct max 30, idle_over_60s max 212, majfault_per_s max 12, pooler max 2000, practitioner_databases max 1990, provision max 5, rss_mb max 6368, started_last_60s max 403, total max 2031, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 8258.6 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 3089.4 | 450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 2207.3 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2413.6 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 2281.5 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 2272.3 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 2230.2 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2202.1 | 447 |
| `api/v{version:apiVersion}/Mail/sendmail` | 3155.0 | 435 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 2221.3 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 2290.0 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 2203.5 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 2581.5 | 444 |
| `api/v{version:apiVersion}/Sync/coverage` | 2167.8 | 448 |

- **p95 client global (k6)** : 831.3 ms
- **p95 serveur le plus élevé** : 8258.6 ms
- **Écart** : -7427.3 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 2.22 |
| Documents CDA /s | 2.25 |
| Durée traitement CDA (s, p95) | 3.74 |
| Événements de session IMAP /s | 3.93 |
| Recherches (s, p95) | 1.080 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 97.7 | 275 | 0.0 (0.0 %), p95 5 | 61.0 (62.4 %), p95 235 | 36.7 (37.5 %), p95 96 |
| `GetMail` | 11.1 | 61.8 | 406 | 5.6 (9.0 %), p95 72 | 52.3 (84.6 %), p95 320 | 3.9 (6.3 %), p95 17 |
| `GetMailsByUids` | 14.7 | 86.4 | 469 | 0.1 (0.1 %), p95 5 | 74.0 (85.6 %), p95 442 | 12.3 (14.2 %), p95 78 |

- **`EnrichPersistMail`** — sur 97.7 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 61.0 ms exécution SQL, 36.7 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 61.8 ms en moyenne (11.1 requête(s) SQL par appel) : 5.6 ms attente d'une connexion, 52.3 ms exécution SQL, 3.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 86.4 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 74.0 ms exécution SQL, 12.3 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.9 | 366.6 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.8 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.9 | 12.3 | 58.9 | 18.8 | 28.7 | 18.8 | 30.5 | 18.8 | 0.0 | 18.8 | 5.9 | 0.0 | 18.7 | 44.9 | 4.1 |

- **`GetMail`** — sur 3.9 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.8 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **366.6 µs**.

- **`GetMailsByUids`** — sur 12.3 ms de matérialisation, l'appel a construit 207.9 objets, dont 18.8 messages, 28.7 étiquettes, 18.8 destinataires, 30.5 pièces jointes, 18.8 identifiants enrichis, 0.0 acquittements, 18.8 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.7 corps de messages, 44.9 objets de fil, 4.1 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **58.9 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3754.0 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 368.1 | 4500 | 131.7 (35.8 %), p95 450 | 11.7 (3.2 %), p95 98 | 82.1 (22.3 %), p95 4500 | 78.6 (21.4 %), p95 246 | 64.0 (17.4 %), p95 242 |

- **Enrichir un message** — sur 368.1 ms en moyenne (3.8 message(s) par requête) : 131.7 ms fetch IMAP, 11.7 ms extraction XDM, 82.1 ms parsing CDA, 78.6 ms écritures base, 64.0 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 283.1 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 643.9 | 978 | 0.0 (0.0 %), p95 5 | 26.6 (4.1 %), p95 77 | 220.0 (34.2 %), p95 478 | 397.1 (61.7 %), p95 489 | 414.6 (64.4 %), p95 946 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 643.9 ms en moyenne : 0.0 ms garde d'opposition, 26.6 ms construction MIME, 220.0 ms obtention de session SMTP, 397.1 ms transmission + acquittement, 414.6 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.440 | 2.375 | 103.37 |
| `smtp_session` | 0.005 | 0.988 | 10.47 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.244 | 2.353 | 0.489 | 10.51 |
| `EnrichEmails` | 0.005 | 0.481 | — | 0.481 | 3.33 |
| `GetAttachmentStream` | 0.487 | 2.140 | 2.425 | 0.687 | 3.49 |
| `GetEmailContent` | 0.050 | 0.668 | — | 0.668 | 13.49 |
| `GetFolders` | 0.005 | 0.981 | 0.982 | 0.242 | 7.80 |
| `ReadFolder` | 0.766 | 2.375 | 2.375 | 0.487 | 36.75 |
| `ReadToday` | 0.005 | 0.499 | 1.521 | 0.499 | 7.80 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.06 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.489 | 0.0 % |
| `EnrichEmails` | **0.407** | 0.444 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.492** | 0.509 | 0.642 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.490 | 0.491 | 0.0 % |
| `GetFolders` | **0.242** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.430** | 0.441 | 0.447 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 103.37 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.766 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 20.00 clients | 0 clients | 100.0 % | 33.2 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.43 cœurs | 24 cœurs | 35.1 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 4.04 cœurs | 24 cœurs | 16.8 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-56880` | 16.00 éléments | 100 éléments | 16.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#35160` (CPU) | 3.27 cœurs | 24 cœurs | 13.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#59188` (CPU) | 3.21 cœurs | 24 cœurs | 13.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#64928` (CPU) | 2.71 cœurs | 24 cœurs | 11.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#56880` (CPU) | 2.63 cœurs | 24 cœurs | 11.0 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 33.2 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 1 386 154

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 16 414 |
| OpenAI | gpt-4o-mini | prompt | 1 369 740 |
| OpenAI | text-embedding-3-small | embedding | 1 806 974 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 732 | 0 (0.0 %) | 0 | 19.4 | 1.19 | 1.02 | 2.77 |
| étiquetage (chat) | OpenAI | 732 | 0 (0.0 %) | 0 | 19.4 | 1.12 | 0.95 | 2.71 |
| embedding | OpenAI | 732 | 0 (0.0 %) | 0 | 19.4 | 0.58 | 0.46 | 1.62 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 9 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 2.5 | 29.0 |
| GPU — VRAM occupée (Mo) | 1 931 | 2 067 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.8 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **6 745.6** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.96** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **6.1 ms** | sur 748 440 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.31 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **19.80 Mo/s (2 534 blocs/s)** | attente disque : 9.9 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **746 461 / 36 153** | rapport 20.6 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **239.6** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.46 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 33 % |
| Sessions ouvertes / s | **2.72** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **372.3 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 561 / 2 031** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **98 / 100 %** | fautes majeures/s max : 11.6 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **88 évictions `pg_stat_statements`** pendant le tir (98 896 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

135 formes de requête, 15 671 996 appels, **27.5 min** de temps serveur cumulé — soit **2.2 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **11.5 %** | 11 % | 165 069 | 0.22 | 1.15 | 1.0 | 18 | 24 % | 0 | 1 897 | **Postgres** — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 2 | **10.5 %** | 22 % | 8 302 | 0.01 | 20.90 | 50.0 | 331 | 1 % | 0 | 861 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **9.6 %** | 32 % | 8 250 | 0.01 | 19.28 | 50.1 | 385 | 3 % | 0 | 857 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **7.4 %** | 39 % | 87 340 | 0.12 | 1.40 | 18.1 | 213 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **6.5 %** | 45 % | 2 220 521 | 2.97 | 0.05 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 6 | **5.5 %** | 51 % | 5 336 218 | 7.13 | 0.02 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 7 | **5.4 %** | 56 % | 2 220 530 | 2.97 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 8 | **4.1 %** | 60 % | 46 295 | 0.06 | 1.46 | 10.1 | 248 | 0 % | 0 | 1 408 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 9 | **3.9 %** | 64 % | 3 715 | 0.00 | 17.14 | 30.4 | 462 | 35 % | 0 | 506 | **Postgres** — 35 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 10 | **3.1 %** | 67 % | 8 296 | 0.01 | 6.26 | 20.0 | 612 | 4 % | 0 | 860 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 11 | **2.9 %** | 70 % | 164 300 | 0.22 | 0.29 | 1.0 | 8 | 2 % | 0 | 1 887 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 12 | **2.8 %** | 73 % | 748 395 | 1.00 | 0.06 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 13 | **2.6 %** | 76 % | 8 259 | 0.01 | 5.12 | 20.0 | 615 | 3 % | 0 | 854 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 14 | **2.4 %** | 78 % | 132 672 | 0.18 | 0.29 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 15 | **1.7 %** | 80 % | 277 140 | 0.37 | 0.10 | 2.1 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 16 | **1.6 %** | 81 % | 16 715 | 0.02 | 1.60 | 1.0 | 21 | 52 % | 0 | 1 305 | **Postgres** — 52 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 17 | **1.4 %** | 83 % | 277 142 | 0.37 | 0.09 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 18 | **1.4 %** | 84 % | 93 094 | 0.12 | 0.25 | 18.0 | 5 | 0 % | 0 | 1 778 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **1.2 %** | 86 % | 4 334 | 0.01 | 4.69 | 178.0 | 540 | 2 % | 0 | 766 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 20 | **0.9 %** | 86 % | 87 340 | 0.12 | 0.17 | 18.1 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 90.5 % | 61.3 % |
| INSERT | 3.4 % | 1.1 % |
| UPDATE | 0.3 % | 0.5 % |
| DELETE | 0.1 % | 0.2 % |
| AUTRE | 5.7 % | 36.9 % |
| bases : praticien (N bases) | 82.7 % | 65.1 % |
| bases : unique (1 base) | 17.3 % | 34.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **20.9** | 129 | 8 302 | 10.5 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **19.3** | 223 | 8 250 | 9.6 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **17.1** | 423 | 3 715 | 3.9 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **6.3** | 333 | 8 296 | 3.1 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **5.1** | 178 | 8 259 | 2.6 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 842 | 208 816 | 192 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 104 | 131 376 | 0 | 5 | 0.1 Mo |
| `Mails` | 662 | 90 070 | 590 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 150 | 22 334 | 824 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 75 | 19 575 | 106 | 43 | 29.9 Mo |
| `MailRecipients` | 122 | 19 032 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 57 | 8 892 | 1 925 | 156 | 1.9 Mo |
| `PendingActions` | 144 | 4 227 | 0 | 31 | 0.1 Mo |
| `Tags` | 97 | 1 746 | 66 | 0 | 0.0 Mo |
| `MailFolders` | 277 | 764 | 225 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (6.5 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟠 | requête n°6 (5.5 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Postgres | 🟠 | taux de cache 96.3 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°1 (11.5 % du temps SQL) — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 21 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 150 fois (22334 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 75 fois (19575 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 57 fois (8892 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°19 (1.2 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Postgres | 🟡 | 33 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | requête n°9 (3.9 % du temps SQL) — 35 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Postgres | 🟡 | requête n°16 (1.6 % du temps SQL) — 52 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°10 (3.1 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°18 (1.4 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-163529.tsv`, `pgserver-journey-debut-155645.tsv`, `pgserver-journey-fin-163533.tsv`, `pgtables-journey-debut-155649.tsv`, `pgtables-journey-fin-163539.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 243572 — dont **243572** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261106-task426-controle-develop-163436.jsonl`.

_Analyse seq-local, fenêtre du tir (14:57 → 15:35 UTC)._

- **5xx en régime : 0** (`StatusCode >= 500` sur `RequestLoggingMiddleware`, 14:57:30 → 15:34).
- **Registre** : aucune `TenantRegistryUnavailableException`. 0 `Failed to parse entity headers`.
- Tir de contrôle de task-426 : code `develop` (`b0cf4143`), sans task-426, joué juste après le tir task-426 dans les
  mêmes conditions.
