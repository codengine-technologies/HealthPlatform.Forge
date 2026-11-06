# Rapport de tir — journey-courte-1400-1996-20261106-task426-registre

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261106-task426-registre-154211.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 5 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 30 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.014 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 755955 — **débit émergent global** : 334.6 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53674 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 334.6 | **182.7** | 83.3 | **581.8** | — | 11901.8 | 0.01 | 100.0 | 0 | 0 | 242840/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214906 | 291.60 | 0.00 | 786.8 |
| **1996 médecins** | 1080 | 933 | 382833 | 410.32 | 0.01 | 1434.6 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 61 / 540 (n=64244) | 87 / 661 (n=113400) |
| 2 | Ouvrir / rafraîchir l'inbox | 44 / 114 (n=32084) | 84 / 303 (n=56758) |
| 3 | Ouvrir un message enrichi (servi base) | 38 / 83 (n=16035) | 92 / 264 (n=28377) |
| 4 | Ouvrir un message froid (fetch IMAP) | 449 / 514 (n=6178) | 480 / 584 (n=11321) |
| 5 | Recherche | 343 / 631 (n=4889) | 420 / 827 (n=8578) |
| 6 | Envoi (acquittement UI) | 496 / 931 (n=4730) | 544 / 1024 (n=8474) |
| 7 | Télécharger une PJ (~124 Ko) | 43 / 378 (n=6347) | 123 / 792 (n=11379) |
| 8 | Marquer lu | 43 / 95 (n=12850) | 92 / 237 (n=22691) |
| 9 | Rechercher un patient | 56 / 72 (n=4740) | 63 / 126 (n=8592) |
| 10 | Ouvrir la page d'un dossier patient | 59 / 134 (n=7190) | 125 / 397 (n=12896) |
| 11 | Fiche patient complète (ressenti médecin) | 330 / 618 (n=3595) | 632 / 1774 (n=6448) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.4 / 20 | 33.9 / 60 | 8050 | 618 |
| **1996 médecins** | 14.5 / 20 | 34.2 / 60 | 14174 | 1774 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2264 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 770 ms en moyenne, 11902 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2261 / 3121 (magasin) | 2261 / 3121 (magasin) |
| Backends Postgres (moy/max) | 1248 / 1438 | 1992 / 2030 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 2 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 53/178 (30 %) ⚠️ soutenu | 73/141 (52 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/178 (0 %) | 0/141 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 53/178 (30 %) | 73/141 (52 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 28.6 | 317.5 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 28.6 | 317.5 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 117 / 372 | 97 / 279 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 116 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1406 | 1999 |
| Backends **directs** — audit + provisionnement (max) | 30 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 | 2 / 18 |
| RSS par réplica api-mail, Mo (moy/max) | 1204 / 1718 (5 réplicas) | 2122 / 2434 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1438.0 / 2500** (57.5 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2030.0 / 2500** (81.2 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 16035)
- palier 1996 : cohorte 1996 chauffée à 99.8 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28377)

> ⓘ Chauffe : **305 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 61 (300) | 540 (1500) | 64244 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 44 (300) | 114 (1000) | 32084 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 38 (100) | 83 (500) | 16035 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 449 (800) | 514 (2500) | 6178 | ✅ |
| 5 | Recherche | 343 (500) | 631 (2000) | 4889 | ✅ |
| 6 | Envoi (acquittement UI) | 496 (1000) | 931 (3000) | 4730 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 43 (500) | 378 (2000) | 6347 | ✅ |
| 8 | Marquer lu | 43 (200) | 95 (1000) | 12850 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 72 (1500) | 4740 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 134 (2000) | 7190 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 330 (1500) | 618 (4000) | 3595 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 87 (300) | 661 (1500) | 113400 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 84 (300) | 303 (1000) | 56758 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 92 (100) | 264 (500) | 28377 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 480 (800) | 584 (2500) | 11321 | ✅ |
| 5 | Recherche | 420 (500) | 827 (2000) | 8578 | ✅ |
| 6 | Envoi (acquittement UI) | 544 (1000) | 1024 (3000) | 8474 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 123 (500) | 792 (2000) | 11379 | ✅ |
| 8 | Marquer lu | 92 (200) | 237 (1000) | 22691 | ✅ |
| 9 | Rechercher un patient | 63 (300) | 126 (1500) | 8592 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 125 (500) | 397 (2000) | 12896 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 632 (1500) | 1774 (4000) | 6448 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 113400 | 186 | 661 | 21103.1 | 38.5 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 56758 | 113 | 303 | 6427.8 | 11.7 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8474 | 669 | 1024 | 5671.4 | 10.4 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11321 | 488 | 584 | 5523.7 | 10.1 % |
| 🟢 | Recherche (`search`) | 8578 | 475 | 827 | 4072.7 | 7.4 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28377 | 114 | 264 | 3222.9 | 5.9 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 11379 | 234 | 792 | 2658.5 | 4.9 % |
| 🟢 | Marquer lu (`mark_read`) | 22691 | 109 | 237 | 2477.7 | 4.5 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 7087 | 217 | 897 | 1539.3 | 2.8 % |
| 🟠 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6448 | 160 | 397 | 1034.6 | 1.9 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8592 | 65 | 126 | 562.2 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6448 | 72 | 127 | 465.9 | 0.9 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 5 🟠 · 7 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 21103.1 s, 38.5 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 7.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 6427.8 s, 11.7 %)
  - **dispersion p95/p50 = 3.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 2658.5 s, 4.9 %)
  - **dispersion p95/p50 = 6.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 1539.3 s, 2.8 %)
  - **dispersion p95/p50 = 6.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 1034.6 s, 1.9 %)
  - **dispersion p95/p50 = 3.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 16061 | 393 | 970 | 6166.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 16061 | 60 | 501 | 2226.7 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 16061 | 25 | 167 | 810.8 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 16061 | 58 | 76 | 955.4 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 16042 | 17 | 119 | 531.9 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 16042 | 57 | 111 | 1024.9 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28350 | 413 | 995 | 11755.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28350 | 80 | 530 | 4552.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28350 | 61 | 247 | 2627.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28350 | 70 | 138 | 2168.4 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28379 | 42 | 187 | 1914.1 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28379 | 134 | 353 | 4513.7 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (995 ms de p95, 413 ms de p50, n=28350), qui porte **aussi** le temps serveur de l'étape (11755.3 s, 56 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (353 ms de p95, 134 ms de p50, n=28379), qui porte **aussi** le temps serveur de l'étape (4513.7 s, 70 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21675 | 188.4 | 82.0 | 553.0 | 746.1 | 1921.5 |
| attachment,palier:1400 | 6347 | 78.5 | 43.1 | 90.9 | 378.2 | 1139.5 |
| attachment,palier:1996 | 11379 | 233.6 | 123.1 | 688.6 | 791.7 | 1682.1 |
| attachment,palier:transition | 571 | 264.2 | 121.0 | 670.0 | 764.4 | 1354.5 |
| dashboard | 219092 | 186.1 | 82.1 | 484.2 | 670.2 | 1642.1 |
| dashboard,call:coverage,palier:1400 | 16061 | 59.5 | 58.2 | 69.1 | 76.2 | 167.6 |
| dashboard,call:coverage,palier:1996 | 28350 | 76.5 | 69.6 | 112.8 | 137.7 | 764.0 |
| dashboard,call:coverage,palier:transition | 1023 | 124.1 | 100.0 | 234.3 | 280.7 | 528.6 |
| dashboard,call:folder,palier:1400 | 16061 | 383.9 | 393.1 | 759.5 | 970.3 | 1547.7 |
| dashboard,call:folder,palier:1996 | 28350 | 414.7 | 412.7 | 794.3 | 995.3 | 1642.1 |
| dashboard,call:folder,palier:transition | 1023 | 488.8 | 472.1 | 776.5 | 885.2 | 1623.9 |
| dashboard,call:folders,palier:1400 | 16061 | 50.5 | 24.8 | 152.3 | 167.1 | 347.4 |
| dashboard,call:folders,palier:1996 | 28350 | 92.7 | 61.1 | 207.5 | 246.5 | 1210.6 |
| dashboard,call:folders,palier:transition | 1023 | 139.6 | 123.4 | 298.0 | 387.4 | 737.5 |
| dashboard,call:today,palier:1400 | 16061 | 138.6 | 60.5 | 479.7 | 501.3 | 802.1 |
| dashboard,call:today,palier:1996 | 28350 | 160.6 | 79.8 | 498.8 | 529.7 | 1154.0 |
| dashboard,call:today,palier:transition | 1023 | 336.2 | 318.5 | 626.3 | 668.2 | 1281.8 |
| dashboard,palier:1400 | 64244 | 158.1 | 60.9 | 457.6 | 539.8 | 1547.7 |
| dashboard,palier:1996 | 113400 | 186.1 | 87.1 | 481.2 | 661.2 | 1642.1 |
| dashboard,palier:transition | 4092 | 272.2 | 179.3 | 588.0 | 688.9 | 1623.9 |
| mark_read | 43713 | 99.0 | 75.2 | 183.8 | 278.9 | 1130.0 |
| mark_read,palier:1400 | 12850 | 52.5 | 42.6 | 83.7 | 95.4 | 467.8 |
| mark_read,palier:1996 | 22691 | 109.2 | 92.0 | 185.7 | 236.9 | 1130.0 |
| mark_read,palier:transition | 1154 | 126.1 | 72.9 | 336.8 | 408.4 | 634.2 |
| patient_docs | 176970 | 115.4 | 75.1 | 246.3 | 350.9 | 1848.7 |
| patient_docs,palier:1400 | 51594 | 54.6 | 48.5 | 101.2 | 122.5 | 296.4 |
| patient_docs,palier:1996 | 93280 | 129.0 | 101.4 | 260.4 | 331.8 | 1215.4 |
| patient_docs,palier:transition | 4222 | 138.2 | 65.6 | 394.5 | 536.2 | 1193.8 |
| patient_dossier | 12242 | 148.9 | 94.6 | 287.5 | 438.2 | 2395.5 |
| patient_dossier,palier:1400 | 3595 | 66.2 | 59.0 | 113.7 | 133.9 | 303.4 |
| patient_dossier,palier:1996 | 6448 | 160.4 | 124.9 | 300.3 | 397.3 | 1638.6 |
| patient_dossier,palier:transition | 302 | 174.0 | 84.0 | 439.0 | 622.2 | 1359.6 |
| patient_opposition | 12241 | 72.0 | 61.6 | 102.7 | 139.9 | 621.0 |
| patient_opposition,palier:1400 | 3595 | 58.8 | 57.9 | 68.0 | 74.1 | 158.4 |
| patient_opposition,palier:1996 | 6448 | 72.3 | 67.5 | 104.4 | 127.2 | 321.0 |
| patient_opposition,palier:transition | 301 | 80.6 | 59.8 | 146.6 | 219.0 | 370.3 |
| patient_search | 16228 | 63.7 | 59.2 | 99.7 | 142.8 | 886.9 |
| patient_search,palier:1400 | 4740 | 46.7 | 55.6 | 66.0 | 71.8 | 149.1 |
| patient_search,palier:1996 | 8592 | 65.4 | 62.6 | 101.6 | 126.0 | 886.9 |
| patient_search,palier:transition | 396 | 76.7 | 59.5 | 173.4 | 195.7 | 468.0 |
| read_content | 54773 | 101.7 | 63.5 | 207.0 | 319.1 | 1159.2 |
| read_content,palier:1400 | 16035 | 43.9 | 38.4 | 68.0 | 82.8 | 281.6 |
| read_content,palier:1996 | 28377 | 113.6 | 91.8 | 207.8 | 263.7 | 1044.5 |
| read_content,palier:transition | 1306 | 156.7 | 65.6 | 438.0 | 524.5 | 765.1 |
| read_content_cold | 21655 | 479.9 | 468.9 | 550.8 | 596.7 | 1258.8 |
| read_content_cold,palier:1400 | 6178 | 450.9 | 449.4 | 499.2 | 514.1 | 639.6 |
| read_content_cold,palier:1996 | 11321 | 487.9 | 480.2 | 555.2 | 584.4 | 1258.8 |
| read_content_cold,palier:transition | 605 | 499.3 | 473.8 | 630.1 | 671.8 | 958.5 |
| read_list | 109546 | 103.1 | 61.8 | 228.2 | 344.5 | 1231.0 |
| read_list,call:emails,palier:1400 | 16042 | 63.9 | 56.9 | 93.9 | 111.0 | 240.8 |
| read_list,call:emails,palier:1996 | 28379 | 159.0 | 133.6 | 276.8 | 352.9 | 1142.9 |
| read_list,call:emails,palier:transition | 1211 | 233.1 | 120.6 | 566.8 | 683.8 | 965.3 |
| read_list,call:folder,palier:1400 | 16042 | 33.2 | 17.3 | 47.8 | 119.0 | 553.9 |
| read_list,call:folder,palier:1996 | 28379 | 67.4 | 42.3 | 138.4 | 186.9 | 920.8 |
| read_list,call:folder,palier:transition | 1211 | 86.5 | 42.5 | 209.3 | 264.1 | 742.5 |
| read_list,palier:1400 | 32084 | 48.5 | 43.9 | 88.6 | 113.7 | 553.9 |
| read_list,palier:1996 | 56758 | 113.2 | 84.3 | 233.4 | 303.2 | 1142.9 |
| read_list,palier:transition | 2422 | 159.8 | 80.1 | 450.2 | 575.4 | 965.3 |
| search | 16578 | 460.9 | 392.9 | 668.2 | 929.6 | 2476.9 |
| search,palier:1400 | 4889 | 391.8 | 342.7 | 482.6 | 630.7 | 1571.5 |
| search,palier:1996 | 8578 | 474.8 | 419.9 | 637.0 | 827.3 | 1947.3 |
| search,palier:transition | 442 | 492.6 | 387.5 | 822.2 | 966.2 | 1519.7 |
| send | 15614 | 674.8 | 572.5 | 962.8 | 1018.7 | 1711.6 |
| send,palier:1400 | 4730 | 637.7 | 496.0 | 909.0 | 930.5 | 1059.8 |
| send,palier:1996 | 8474 | 669.3 | 543.8 | 975.3 | 1024.5 | 1686.4 |
| send,palier:transition | 480 | 665.3 | 600.2 | 984.2 | 1060.8 | 1503.9 |
| treatment | 13658 | 177.8 | 106.3 | 335.1 | 665.0 | 4320.4 |
| treatment,palier:1400 | 4025 | 84.5 | 82.5 | 112.8 | 128.0 | 3119.3 |
| treatment,palier:1996 | 7087 | 217.2 | 138.6 | 376.6 | 896.7 | 2642.2 |
| treatment,palier:transition | 314 | 245.6 | 107.9 | 602.9 | 749.5 | 1484.9 |
| warmup | 21956 | 769.8 | 437.4 | 884.8 | 3358.1 | 11901.8 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-06T14:04:32.162000+00:00 → 2026-11-06T14:42:11.195000+00:00 (2259 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t426.csv`) | ✅ 72481 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-38008` | 0.99 | 12 | 44 | 0.041 | 4.60 |
| `DESKTOP-DEV-X2C-52556` | 0.98 | 16 | 31 | 0.037 | 4.56 |
| `DESKTOP-DEV-X2C-61376` | 1.04 | 12 | 32 | 0.038 | 5.11 |
| `DESKTOP-DEV-X2C-62652` | 1.02 | 14 | 31 | 0.028 | 5.04 |
| `DESKTOP-DEV-X2C-7348` | 0.99 | 21 | 44 | 0.037 | 4.67 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.39 | 3.87 | 2136 |
| `com.docker.backend#34124` | 0.00 | 0.18 | 39 |
| `dcp#12016` | 0.00 | 0.00 | 12 |
| `dcp#35080` | 0.00 | 0.04 | 13 |
| `dcp#39332` | 0.00 | 0.13 | 51 |
| `dcp#43400` | 0.00 | 0.00 | 12 |
| `dcp#49348` | 0.00 | 0.09 | 12 |
| `dcp#50732` | 0.00 | 0.00 | 12 |
| `dcp#56768` | 0.00 | 0.00 | 12 |
| `dcp#57696` | 0.00 | 0.18 | 12 |
| `dcp#58152` | 0.00 | 0.00 | 12 |
| `dcp#59660` | 0.00 | 0.00 | 12 |
| `dcp#60264` | 0.00 | 0.04 | 13 |
| `dcp#61704` | 0.83 | 2.51 | 3214 |
| `dcp#62308` | 0.00 | 0.04 | 14 |
| `dcp#62596` | 0.00 | 0.00 | 12 |
| `dcp#63392` | 0.00 | 0.14 | 14 |
| `k6#73129` | 0.84 | 1.89 | 2892 |
| `mss.mail.api#38008` | 0.69 | 2.95 | 2434 |
| `mss.mail.api#52556` | 0.67 | 1.99 | 2339 |
| `mss.mail.api#61376` | 0.67 | 3.06 | 2383 |
| `mss.mail.api#62652` | 0.66 | 2.30 | 2365 |
| `mss.mail.api#7348` | 0.69 | 2.74 | 2272 |
| `mss.mail.e2e#4552` | 0.01 | 0.24 | 34 |
| `vmmemWSL#36464` | 5.85 | 11.48 | 54586 |
| `loadtest-otel-collector-jxqhxusd` | 0.03 | 0.18 | 105 |
| `loadtest-pgbouncer-efkkhjqq` | 0.54 | 0.97 | 49 |
| `mss-mail-flagsmith-app-b6152948` | 0.13 | 0.44 | 567 |
| `mss-mail-flagsmith-db-b6152948` | 0.01 | 0.14 | 214 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.07 | 164 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.10 | 186 |
| `mss-mail-rabbitmq-zmkwtyee` | 0.01 | 0.10 | 157 |
| `mss-mail-redis-b6152948` | 0.29 | 1.38 | 954 |
| `mss-mail-rediscommander-rxgybxuh` | 0.00 | 0.23 | 26 |
| `mss-mail-seq-b6152948` | 0.12 | 0.81 | 17848 |
| `postgres-pgvector` | 2.64 | 8.56 | 47544 |

- **Hôte** : CPU 73.6 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 44
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9597, cl_waiting max 15, cl_waiting_maintenance max 15, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 396, maxwait_ms max 396, maxwait_practitioner_ms max 0, sv_active max 36, sv_idle max 1563, sv_login max 2
- **Backends Postgres** : audit max 5, cache_mb max 41402, direct max 30, idle_over_60s max 200, majfault_per_s max 33, pooler max 1999, practitioner_databases max 1990, provision max 5, rss_mb max 6298, started_last_60s max 372, total max 2030, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `/health` | 487.5 | 425 |
| `api/v{version:apiVersion}/Mail/folders` | 8924.7 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2381.7 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 841.9 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 1871.0 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 759.9 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 995.7 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 660.8 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 958.8 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2222.3 | 432 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 418.1 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 2075.4 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 406.9 | 442 |
| `api/v{version:apiVersion}/Search/semantic` | 2129.0 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 442.2 | 447 |

- **p95 client global (k6)** : 581.8 ms
- **p95 serveur le plus élevé** : 8924.7 ms
- **Écart** : -8342.9 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 3.35 |
| Documents CDA /s | 3.33 |
| Durée traitement CDA (s, p95) | 1.05 |
| Événements de session IMAP /s | 4.11 |
| Recherches (s, p95) | 1.531 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 89.1 | 432 | 0.0 (0.0 %), p95 5 | 53.1 (59.6 %), p95 237 | 36.0 (40.4 %), p95 205 |
| `GetMail` | 11.1 | 70.8 | 591 | 6.2 (8.7 %), p95 138 | 60.3 (85.1 %), p95 490 | 4.4 (6.2 %), p95 26 |
| `GetMailsByUids` | 14.7 | 98.8 | 638 | 0.1 (0.1 %), p95 5 | 84.8 (85.8 %), p95 499 | 13.9 (14.0 %), p95 83 |

- **`EnrichPersistMail`** — sur 89.1 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 53.1 ms exécution SQL, 36.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 70.8 ms en moyenne (11.1 requête(s) SQL par appel) : 6.2 ms attente d'une connexion, 60.3 ms exécution SQL, 4.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 98.8 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 84.8 ms exécution SQL, 13.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 4.4 | 408.0 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.8 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 208.1 | 13.9 | 66.7 | 18.8 | 28.7 | 18.8 | 30.6 | 18.8 | 0.0 | 18.8 | 5.9 | 0.0 | 18.7 | 45.0 | 4.0 |

- **`GetMail`** — sur 4.4 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.8 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **408.0 µs**.

- **`GetMailsByUids`** — sur 13.9 ms de matérialisation, l'appel a construit 208.1 objets, dont 18.8 messages, 28.7 étiquettes, 18.8 destinataires, 30.6 pièces jointes, 18.8 identifiants enrichis, 0.0 acquittements, 18.8 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.7 corps de messages, 45.0 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **66.7 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3318.2 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 330.2 | 1563 | 132.8 (40.2 %), p95 246 | 12.8 (3.9 %), p95 594 | 55.0 (16.6 %), p95 1563 | 69.7 (21.1 %), p95 388 | 59.9 (18.1 %), p95 239 |

- **Enrichir un message** — sur 330.2 ms en moyenne (3.8 message(s) par requête) : 132.8 ms fetch IMAP, 12.8 ms extraction XDM, 55.0 ms parsing CDA, 69.7 ms écritures base, 59.9 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 259.6 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 647.9 | 1012 | 0.0 (0.0 %), p95 5 | 30.5 (4.7 %), p95 103 | 219.1 (33.8 %), p95 478 | 398.1 (61.4 %), p95 489 | 414.0 (63.9 %), p95 966 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 647.9 ms en moyenne : 0.0 ms garde d'opposition, 30.5 ms construction MIME, 219.1 ms obtention de session SMTP, 398.1 ms transmission + acquittement, 414.0 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.441 | 2.190 | 103.75 |
| `smtp_session` | 0.005 | 0.988 | 10.51 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.474 | 2.361 | 0.490 | 10.51 |
| `EnrichEmails` | 0.005 | 0.487 | — | 0.487 | 5.04 |
| `GetAttachmentStream` | 0.476 | 2.243 | 2.425 | 0.637 | 4.62 |
| `GetEmailContent` | 0.005 | 0.494 | — | 0.494 | 13.62 |
| `GetFolders` | 0.008 | 0.992 | 1.075 | 0.243 | 7.51 |
| `ReadFolder` | 0.499 | 2.388 | 2.388 | 0.487 | 36.31 |
| `ReadToday` | 0.005 | 0.494 | — | 0.494 | 7.55 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.44 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.489 | 0.0 % |
| `EnrichEmails` | **0.412** | 0.439 | 0.448 | 0.0 % |
| `GetAttachmentStream` | **0.495** | 0.550 | 0.637 | 0.0 % |
| `GetEmailContent` | **0.490** | 0.492 | 0.494 | 0.0 % |
| `GetFolders` | **0.242** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.432** | 0.440 | 0.444 | 0.0 % |
| `ReadToday` | **0.488** | 0.490 | 0.494 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.488 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 103.75 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.499 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 15.00 clients | 0 clients | 100.0 % | 38.5 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.56 cœurs | 24 cœurs | 35.7 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-7348` | 21.00 éléments | 100 éléments | 21.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#61376` (CPU) | 3.06 cœurs | 24 cœurs | 12.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#38008` (CPU) | 2.95 cœurs | 24 cœurs | 12.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#7348` (CPU) | 2.74 cœurs | 24 cœurs | 11.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#62652` (CPU) | 2.30 cœurs | 24 cœurs | 9.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#52556` (CPU) | 1.99 cœurs | 24 cœurs | 8.3 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 38.5 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 2 126 401

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 24 798 |
| OpenAI | gpt-4o-mini | prompt | 2 101 603 |
| OpenAI | text-embedding-3-small | embedding | 2 881 327 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 1 124 | 0 (0.0 %) | 0 | 29.9 | 1.13 | 1.01 | 2.45 |
| étiquetage (chat) | OpenAI | 1 124 | 0 (0.0 %) | 0 | 29.9 | 1.07 | 0.95 | 2.45 |
| embedding | OpenAI | 1 124 | 0 (0.0 %) | 0 | 29.9 | 0.56 | 0.47 | 1.48 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 7 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 9.6 | 38.0 |
| GPU — VRAM occupée (Mo) | 2 060 | 2 310 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.9 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 578.0** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.81** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **5.6 ms** | sur 755 955 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.12 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **19.62 Mo/s (2 511 blocs/s)** | attente disque : 14.0 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **745 395 / 34 919** | rapport 21.3 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **277.0** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.55 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **7 / 0** | blocs écrits par les backends eux-mêmes : 40 % |
| Sessions ouvertes / s | **2.97** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **544.2 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 556 / 2 030** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **98 / 100 %** | fautes majeures/s max : 33.1 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **90 évictions `pg_stat_statements`** pendant le tir (99 240 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

137 formes de requête, 5 984 775 appels, **25.6 min** de temps serveur cumulé — soit **2.0 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **14.2 %** | 14 % | 168 265 | 0.22 | 1.30 | 1.0 | 18 | 24 % | 0 | 1 913 | **Postgres** — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 2 | **12.1 %** | 26 % | 8 671 | 0.01 | 21.43 | 50.6 | 334 | 1 % | 0 | 883 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **11.2 %** | 38 % | 8 682 | 0.01 | 19.77 | 50.7 | 388 | 3 % | 0 | 882 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **8.4 %** | 46 % | 87 730 | 0.12 | 1.47 | 18.1 | 212 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **5.4 %** | 51 % | 3 600 | 0.00 | 22.82 | 30.2 | 456 | 36 % | 0 | 491 | **Postgres** — 36 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 6 | **5.0 %** | 56 % | 755 854 | 1.00 | 0.10 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 7 | **4.5 %** | 61 % | 46 971 | 0.06 | 1.47 | 10.1 | 246 | 0 % | 0 | 1 429 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 8 | **4.1 %** | 65 % | 8 720 | 0.01 | 7.30 | 20.0 | 611 | 4 % | 0 | 890 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 9 | **3.7 %** | 69 % | 167 040 | 0.22 | 0.34 | 1.0 | 8 | 3 % | 0 | 1 897 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 10 | **3.4 %** | 72 % | 8 639 | 0.01 | 5.97 | 20.0 | 614 | 3 % | 0 | 878 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 11 | **2.5 %** | 74 % | 133 428 | 0.18 | 0.29 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 12 | **2.0 %** | 76 % | 280 011 | 0.37 | 0.11 | 2.0 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 13 | **1.9 %** | 78 % | 17 085 | 0.02 | 1.75 | 1.0 | 20 | 51 % | 0 | 1 329 | **Postgres** — 51 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 14 | **1.6 %** | 80 % | 279 870 | 0.37 | 0.09 | 1.3 | 16 | 0 % | 0 | 1 994 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 15 | **1.5 %** | 82 % | 93 678 | 0.12 | 0.25 | 18.0 | 5 | 0 % | 0 | 1 788 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 16 | **1.0 %** | 83 % | 187 053 | 0.25 | 0.08 | 3.2 | 8 | 0 % | 0 | 1 911 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |
| 17 | **1.0 %** | 84 % | 87 724 | 0.12 | 0.18 | 18.1 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 18 | **0.9 %** | 84 % | 44 927 | 0.06 | 0.33 | 27.0 | 5 | 0 % | 0 | 1 411 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **0.9 %** | 85 % | 3 360 | 0.00 | 4.28 | 178.0 | 540 | 1 % | 0 | 602 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 20 | **0.9 %** | 86 % | 35 926 | 0.05 | 0.37 | 1.0 | 9 | 4 % | 0 | 1 540 | — | `INSERT INTO "PendingActions" ("Id", "ActionType", "ClaimedAt", "CreatedAt", "FolderPath", "LastError", "MailUid", "Payl…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 95.1 % | 87.6 % |
| INSERT | 4.1 % | 3.0 % |
| UPDATE | 0.4 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.3 % | 7.5 % |
| bases : praticien (N bases) | 92.0 % | 82.2 % |
| bases : unique (1 base) | 8.0 % | 17.8 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **22.8** | 642 | 3 600 | 5.4 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **21.4** | 249 | 8 671 | 12.1 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **19.8** | 113 | 8 682 | 11.2 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **7.3** | 161 | 8 720 | 4.1 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **6.0** | 134 | 8 639 | 3.4 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 1 125 | 279 000 | 252 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 448 | 172 312 | 0 | 5 | 0.1 Mo |
| `Mails` | 827 | 109 018 | 739 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 212 | 31 460 | 1 135 | 157 | 8.0 Mo |
| `MailRecipients` | 181 | 28 236 | 0 | 26 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 104 | 27 144 | 175 | 43 | 29.9 Mo |
| `MailContents` ⚠️ index candidat | 77 | 12 012 | 2 451 | 156 | 1.9 Mo |
| `PendingActions` | 198 | 5 876 | 0 | 31 | 0.1 Mo |
| `Tags` | 150 | 2 700 | 58 | 0 | 0.0 Mo |
| `MailFolders` | 382 | 1 030 | 255 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Postgres | 🟠 | taux de cache 96.1 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°1 (14.2 % du temps SQL) — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Postgres | 🟠 | requête n°5 (5.4 % du temps SQL) — 36 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 21 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 212 fois (31460 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 104 fois (27144 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 77 fois (12012 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°6 (5.0 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟡 | 40 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | requête n°13 (1.9 % du temps SQL) — 51 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°8 (4.1 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°15 (1.5 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-154311.tsv`, `pgserver-journey-debut-150421.tsv`, `pgserver-journey-fin-154315.tsv`, `pgtables-journey-debut-150425.tsv`, `pgtables-journey-fin-154322.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 242840 — dont **242840** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261106-task426-registre-154211.jsonl`.

_Analyse seq-local, fenêtre du tir (14:05 → 14:43 UTC)._

- **5xx en régime : 0** (`StatusCode >= 500` sur `RequestLoggingMiddleware`, 14:05 → 14:41:50).
- **Registre** : aucune `TenantRegistryUnavailableException`.
- **IMAP** : 0 `Failed to parse entity headers` (Dovecot sert bien `BODY[part]`).
- **Erreurs et avertissements** : uniquement à l'arrêt des VUs (14:42:10). Ce sont des 499 (annulation client) et un
  `POST /sendmail` en 503, dont la connexion SMTP a été annulée par le client (`UnavailableException: SMTP connection
  failed: A task was canceled`). S'y ajoutent les `Session expired` du recyclage nominal.
- **Constat hors task (préexistant)** : une annulation du client pendant l'ouverture de la connexion SMTP sort en
  `UnavailableException` (503 `MAIL_SERVER_UNAVAILABLE`), pas en 499. Bruit de fin de tir, à confirmer avant d'en faire
  une task.
