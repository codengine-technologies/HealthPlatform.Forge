# Rapport de tir — journey-courte-1400-1996-20261107-task430

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261107-task430-105453.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 2 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 16 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.010 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 759056 — **débit émergent global** : 335.7 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53876 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 335.7 | **139.6** | 58.5 | **491.3** | — | 11189.9 | 0.01 | 100.0 | 0 | 0 | 246638/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 215010 | 291.74 | 0.00 | 806.6 |
| **1996 médecins** | 1080 | 933 | 382007 | 409.44 | 0.01 | 1452.2 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 58 / 556 (n=63556) | 64 / 584 (n=114160) |
| 2 | Ouvrir / rafraîchir l'inbox | 39 / 87 (n=31744) | 51 / 145 (n=57088) |
| 3 | Ouvrir un message enrichi (servi base) | 33 / 59 (n=15879) | 47 / 117 (n=28562) |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 / 508 (n=6407) | 453 / 523 (n=11443) |
| 5 | Recherche | 323 / 576 (n=4752) | 348 / 663 (n=8550) |
| 6 | Envoi (acquittement UI) | 497 / 922 (n=4701) | 485 / 948 (n=8652) |
| 7 | Télécharger une PJ (~124 Ko) | 36 / 66 (n=6485) | 52 / 156 (n=11409) |
| 8 | Marquer lu | 34 / 82 (n=12765) | 55 / 118 (n=22766) |
| 9 | Rechercher un patient | 55 / 64 (n=4832) | 56 / 80 (n=8327) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 64 (n=7256) | 59 / 80 (n=12536) |
| 11 | Fiche patient complète (ressenti médecin) | 257 / 411 (n=3628) | 342 / 731 (n=6268) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.2 / 65 | 8104 | 411 |
| **1996 médecins** | 14.6 / 20 | 34.6 / 65 | 14160 | 731 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2244 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 590 ms en moyenne, 11190 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2255 / 3076 (magasin) | 2255 / 3076 (magasin) |
| Backends Postgres (moy/max) | 1245 / 1437 | 1986 / 2024 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 30/192 (16 %) | 64/169 (38 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/192 (0 %) | 0/169 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 30/192 (16 %) | 64/169 (38 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 33.5 | 123.2 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 33.5 | 123.2 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 120 / 362 | 99 / 270 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 97 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1406 | 1993 |
| Backends **directs** — audit + provisionnement (max) | 30 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 98.2 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 2 | 0 / 3 |
| RSS par réplica api-mail, Mo (moy/max) | 1145 / 1630 (5 réplicas) | 2006 / 2224 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1437.0 / 2500** (57.5 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2024.0 / 2500** (81.0 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15879)
- palier 1996 : cohorte 1996 chauffée à 99.8 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28562)

> ⓘ Chauffe : **301 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 58 (300) | 556 (1500) | 63556 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 39 (300) | 87 (1000) | 31744 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 33 (100) | 59 (500) | 15879 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 (800) | 508 (2500) | 6407 | ✅ |
| 5 | Recherche | 323 (500) | 576 (2000) | 4752 | ✅ |
| 6 | Envoi (acquittement UI) | 497 (1000) | 922 (3000) | 4701 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 36 (500) | 66 (2000) | 6485 | ✅ |
| 8 | Marquer lu | 34 (200) | 82 (1000) | 12765 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 64 (1500) | 4832 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 64 (2000) | 7256 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 257 (1500) | 411 (4000) | 3628 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 64 (300) | 584 (1500) | 114160 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 51 (300) | 145 (1000) | 57088 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 47 (100) | 117 (500) | 28562 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 453 (800) | 523 (2500) | 11443 | ✅ |
| 5 | Recherche | 348 (500) | 663 (2000) | 8550 | ✅ |
| 6 | Envoi (acquittement UI) | 485 (1000) | 948 (3000) | 8652 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 52 (500) | 156 (2000) | 11409 | ✅ |
| 8 | Marquer lu | 55 (200) | 118 (1000) | 22766 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 80 (1500) | 8327 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 80 (2000) | 12536 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 342 (1500) | 731 (4000) | 6268 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114160 | 163 | 584 | 18624.0 | 44.3 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8652 | 626 | 948 | 5415.8 | 12.9 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11443 | 456 | 523 | 5213.1 | 12.4 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57088 | 62 | 145 | 3524.3 | 8.4 % |
| 🟢 | Recherche (`search`) | 8550 | 399 | 663 | 3413.4 | 8.1 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28562 | 58 | 117 | 1649.1 | 3.9 % |
| 🟢 | Marquer lu (`mark_read`) | 22766 | 66 | 118 | 1498.5 | 3.6 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 11409 | 77 | 156 | 879.5 | 2.1 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7080 | 112 | 182 | 792.3 | 1.9 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8327 | 49 | 80 | 408.5 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6268 | 59 | 80 | 370.3 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6268 | 40 | 79 | 249.0 | 0.6 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 2 🟠 · 10 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 18624.0 s, 44.3 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 9.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 879.5 s, 2.1 %)
  - **dispersion p95/p50 = 3.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15889 | 389 | 982 | 6083.5 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15889 | 58 | 496 | 2163.4 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15889 | 19 | 160 | 702.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15889 | 56 | 66 | 905.9 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15872 | 15 | 116 | 474.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15872 | 49 | 77 | 829.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28540 | 398 | 989 | 11217.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28540 | 63 | 504 | 4024.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28540 | 29 | 179 | 1644.1 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28540 | 60 | 84 | 1737.8 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28544 | 21 | 132 | 1142.6 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28544 | 70 | 156 | 2381.7 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (989 ms de p95, 398 ms de p50, n=28540), qui porte **aussi** le temps serveur de l'étape (11217.4 s, 60 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (156 ms de p95, 70 ms de p50, n=28544), qui porte **aussi** le temps serveur de l'étape (2381.7 s, 68 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21962 | 73.5 | 44.2 | 108.9 | 224.7 | 1311.4 |
| attachment,palier:1400 | 6485 | 40.5 | 36.1 | 55.5 | 66.0 | 1086.5 |
| attachment,palier:1996 | 11409 | 77.1 | 52.0 | 110.3 | 156.5 | 1253.7 |
| attachment,palier:transition | 641 | 120.0 | 44.9 | 336.1 | 407.2 | 981.5 |
| dashboard | 220004 | 165.0 | 62.5 | 468.5 | 585.1 | 2051.8 |
| dashboard,call:coverage,palier:1400 | 15889 | 57.0 | 56.2 | 63.1 | 66.2 | 162.2 |
| dashboard,call:coverage,palier:1996 | 28540 | 60.9 | 59.7 | 75.9 | 84.5 | 410.2 |
| dashboard,call:coverage,palier:transition | 1069 | 96.3 | 79.0 | 167.9 | 190.7 | 301.1 |
| dashboard,call:folder,palier:1400 | 15889 | 382.9 | 388.9 | 760.0 | 982.1 | 1514.6 |
| dashboard,call:folder,palier:1996 | 28540 | 393.0 | 398.4 | 771.1 | 989.5 | 1622.0 |
| dashboard,call:folder,palier:transition | 1069 | 444.9 | 453.1 | 720.6 | 816.9 | 1605.6 |
| dashboard,call:folders,palier:1400 | 15889 | 44.2 | 19.3 | 145.3 | 160.3 | 359.9 |
| dashboard,call:folders,palier:1996 | 28540 | 57.6 | 28.9 | 160.8 | 179.4 | 2051.8 |
| dashboard,call:folders,palier:transition | 1069 | 90.4 | 73.2 | 178.0 | 252.0 | 435.6 |
| dashboard,call:today,palier:1400 | 15889 | 136.2 | 58.2 | 475.7 | 496.2 | 818.0 |
| dashboard,call:today,palier:1996 | 28540 | 141.0 | 62.9 | 480.2 | 504.1 | 1036.7 |
| dashboard,call:today,palier:transition | 1069 | 298.3 | 182.2 | 567.0 | 596.0 | 816.3 |
| dashboard,palier:1400 | 63556 | 155.1 | 58.3 | 456.2 | 555.7 | 1514.6 |
| dashboard,palier:1996 | 114160 | 163.1 | 63.9 | 463.0 | 583.9 | 2051.8 |
| dashboard,palier:transition | 4276 | 232.5 | 123.7 | 545.4 | 596.3 | 1605.6 |
| mark_read | 43786 | 63.4 | 48.3 | 96.3 | 130.5 | 2277.4 |
| mark_read,palier:1400 | 12765 | 45.6 | 33.5 | 75.8 | 81.8 | 185.3 |
| mark_read,palier:1996 | 22766 | 65.8 | 55.1 | 98.6 | 117.6 | 2277.4 |
| mark_read,palier:transition | 1205 | 75.4 | 49.0 | 186.6 | 231.5 | 427.5 |
| patient_docs | 177801 | 69.0 | 51.3 | 123.4 | 170.3 | 2295.3 |
| patient_docs,palier:1400 | 52581 | 43.7 | 41.4 | 77.4 | 90.3 | 211.8 |
| patient_docs,palier:1996 | 91434 | 69.2 | 57.4 | 130.6 | 163.4 | 2295.3 |
| patient_docs,palier:transition | 4853 | 86.5 | 51.6 | 221.1 | 348.2 | 768.3 |
| patient_dossier | 12219 | 39.0 | 27.7 | 61.2 | 91.3 | 530.6 |
| patient_dossier,palier:1400 | 3628 | 25.3 | 23.4 | 32.9 | 39.6 | 98.1 |
| patient_dossier,palier:1996 | 6268 | 39.7 | 32.4 | 62.8 | 78.6 | 530.6 |
| patient_dossier,palier:transition | 337 | 53.5 | 27.2 | 136.6 | 178.0 | 408.3 |
| patient_opposition | 12219 | 60.2 | 57.4 | 71.1 | 83.6 | 609.4 |
| patient_opposition,palier:1400 | 3628 | 56.3 | 55.8 | 61.4 | 63.9 | 131.9 |
| patient_opposition,palier:1996 | 6268 | 59.1 | 58.8 | 71.8 | 79.5 | 437.7 |
| patient_opposition,palier:transition | 335 | 67.8 | 57.6 | 103.9 | 139.9 | 219.3 |
| patient_search | 16226 | 49.5 | 55.6 | 70.5 | 83.1 | 699.6 |
| patient_search,palier:1400 | 4832 | 44.1 | 55.2 | 60.5 | 63.7 | 124.8 |
| patient_search,palier:1996 | 8327 | 49.1 | 55.8 | 71.6 | 79.9 | 559.7 |
| patient_search,palier:transition | 443 | 55.9 | 55.8 | 92.9 | 122.0 | 303.6 |
| read_content | 55001 | 57.4 | 39.8 | 90.3 | 134.2 | 927.8 |
| read_content,palier:1400 | 15879 | 35.8 | 33.1 | 49.2 | 58.5 | 216.9 |
| read_content,palier:1996 | 28562 | 57.7 | 46.6 | 93.2 | 117.5 | 860.4 |
| read_content,palier:transition | 1385 | 91.8 | 40.8 | 263.5 | 309.8 | 476.7 |
| read_content_cold | 22028 | 454.4 | 449.8 | 506.4 | 527.8 | 1127.4 |
| read_content_cold,palier:1400 | 6407 | 445.9 | 444.0 | 494.8 | 507.9 | 591.9 |
| read_content_cold,palier:1996 | 11443 | 455.6 | 452.7 | 505.3 | 523.1 | 1127.4 |
| read_content_cold,palier:transition | 600 | 467.0 | 458.0 | 536.7 | 575.8 | 992.8 |
| read_list | 110002 | 61.7 | 45.4 | 115.1 | 158.6 | 1059.9 |
| read_list,call:emails,palier:1400 | 15872 | 52.3 | 49.0 | 68.6 | 77.4 | 185.9 |
| read_list,call:emails,palier:1996 | 28544 | 83.4 | 70.0 | 126.5 | 155.9 | 978.5 |
| read_list,call:emails,palier:transition | 1253 | 151.1 | 67.5 | 387.9 | 435.9 | 614.9 |
| read_list,call:folder,palier:1400 | 15872 | 29.9 | 15.0 | 32.4 | 116.3 | 527.1 |
| read_list,call:folder,palier:1996 | 28544 | 40.0 | 20.8 | 70.8 | 132.2 | 1059.9 |
| read_list,call:folder,palier:transition | 1253 | 50.6 | 20.6 | 121.8 | 156.1 | 573.2 |
| read_list,palier:1400 | 31744 | 41.1 | 39.2 | 65.8 | 87.3 | 527.1 |
| read_list,palier:1996 | 57088 | 61.7 | 51.2 | 116.6 | 145.0 | 1059.9 |
| read_list,palier:transition | 2506 | 100.9 | 53.4 | 309.0 | 397.6 | 614.9 |
| search | 16342 | 399.7 | 340.9 | 528.7 | 763.1 | 1899.1 |
| search,palier:1400 | 4752 | 373.7 | 323.5 | 452.9 | 575.8 | 1544.2 |
| search,palier:1996 | 8550 | 399.2 | 348.3 | 504.7 | 663.0 | 1833.8 |
| search,palier:transition | 448 | 444.8 | 351.2 | 632.9 | 1025.1 | 1649.3 |
| send | 15760 | 643.0 | 507.1 | 918.4 | 948.9 | 1697.2 |
| send,palier:1400 | 4701 | 635.4 | 496.9 | 901.5 | 922.2 | 1066.5 |
| send,palier:1996 | 8652 | 626.0 | 485.2 | 919.3 | 947.7 | 1697.2 |
| send,palier:transition | 455 | 634.4 | 508.5 | 950.9 | 997.4 | 1271.9 |
| treatment | 13736 | 104.7 | 83.7 | 137.2 | 223.5 | 4608.6 |
| treatment,palier:1400 | 4052 | 73.0 | 78.6 | 96.1 | 104.3 | 191.8 |
| treatment,palier:1996 | 7080 | 111.9 | 89.4 | 140.9 | 181.6 | 3583.6 |
| treatment,palier:transition | 338 | 145.8 | 85.4 | 366.9 | 406.8 | 778.6 |
| warmup | 21956 | 589.7 | 315.9 | 671.5 | 2541.1 | 11189.9 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-07T09:17:12.641000+00:00 → 2026-11-07T09:54:53.635000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-task430.csv`) | ✅ 78936 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-14168` | 0.91 | 8 | 25 | 0.036 | 4.47 |
| `DESKTOP-DEV-X2C-26768` | 0.96 | 13 | 24 | 0.029 | 5.02 |
| `DESKTOP-DEV-X2C-56460` | 0.97 | 10 | 29 | 0.029 | 4.96 |
| `DESKTOP-DEV-X2C-65264` | 0.91 | 9 | 24 | 0.031 | 4.73 |
| `DESKTOP-DEV-X2C-66520` | 0.96 | 12 | 26 | 0.028 | 5.04 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.16 | 3.90 | 1936 |
| `com.docker.backend#34124` | 0.00 | 0.19 | 40 |
| `dcp#16528` | 0.00 | 0.09 | 13 |
| `dcp#3456` | 0.00 | 0.00 | 12 |
| `dcp#52920` | 0.00 | 0.00 | 12 |
| `dcp#54408` | 0.00 | 0.18 | 13 |
| `dcp#56640` | 0.00 | 0.00 | 12 |
| `dcp#58136` | 0.00 | 0.00 | 12 |
| `dcp#59148` | 0.00 | 0.09 | 14 |
| `dcp#60916` | 0.00 | 0.00 | 12 |
| `dcp#61300` | 0.00 | 0.09 | 14 |
| `dcp#61436` | 0.00 | 0.09 | 52 |
| `dcp#62804` | 0.00 | 0.00 | 12 |
| `dcp#65940` | 0.00 | 0.00 | 12 |
| `dcp#67760` | 0.00 | 0.00 | 12 |
| `dcp#67880` | 0.00 | 0.00 | 12 |
| `dcp#70224` | 0.74 | 2.26 | 3190 |
| `k6#175531` | 0.78 | 1.74 | 2867 |
| `mss.mail.api#14168` | 0.64 | 2.89 | 2207 |
| `mss.mail.api#26768` | 0.65 | 2.75 | 2215 |
| `mss.mail.api#56460` | 0.65 | 2.69 | 2224 |
| `mss.mail.api#65264` | 0.64 | 2.66 | 2200 |
| `mss.mail.api#66520` | 0.62 | 2.23 | 2175 |
| `mss.mail.e2e#64468` | 0.01 | 0.14 | 34 |
| `vmmemWSL#36464` | 5.31 | 11.47 | 52053 |
| `loadtest-otel-collector-fcnkqxch` | 0.02 | 0.18 | 138 |
| `loadtest-pgbouncer-vjkbphqh` | 0.43 | 0.89 | 53 |
| `mss-mail-flagsmith-app-b6152948` | 0.12 | 0.53 | 474 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.29 | 154 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.08 | 158 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.08 | 233 |
| `mss-mail-rabbitmq-yruvhdba` | 0.01 | 0.04 | 153 |
| `mss-mail-redis-b6152948` | 0.26 | 1.38 | 956 |
| `mss-mail-rediscommander-sdknnhsd` | 0.00 | 0.24 | 35 |
| `mss-mail-seq-b6152948` | 0.11 | 3.78 | 10260 |
| `postgres-pgvector` | 2.04 | 8.33 | 45087 |

- **Hôte** : CPU 62.3 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 32
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9388, cl_waiting max 22, cl_waiting_maintenance max 22, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 123, maxwait_ms max 123, maxwait_practitioner_ms max 0, sv_active max 59, sv_idle max 1587, sv_login max 1
- **Backends Postgres** : audit max 5, cache_mb max 40455, direct max 30, idle_over_60s max 208, majfault_per_s max 3, pooler max 1993, practitioner_databases max 1986, provision max 5, rss_mb max 6208, started_last_60s max 362, total max 2024, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 8202.1 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2494.7 | 450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 728.5 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 747.4 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 729.8 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 710.3 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 463.2 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 738.9 | 447 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2080.9 | 435 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 226.3 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 426.6 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 224.0 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 1751.7 | 444 |
| `api/v{version:apiVersion}/Sync/coverage` | 242.2 | 448 |

- **p95 client global (k6)** : 491.3 ms
- **p95 serveur le plus élevé** : 8202.1 ms
- **Écart** : -7710.9 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.95 |
| Documents CDA /s | 0.95 |
| Durée traitement CDA (s, p95) | 0.95 |
| Événements de session IMAP /s | 4.11 |
| Recherches (s, p95) | 1.176 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.0 | 61.6 | 375 | 0.0 (0.0 %), p95 5 | 36.4 (59.2 %), p95 250 | 25.1 (40.8 %), p95 175 |
| `GetMail` | 11.1 | 43.8 | 605 | 4.1 (9.3 %), p95 77 | 36.3 (82.8 %), p95 497 | 3.5 (7.9 %), p95 18 |
| `GetMailsByUids` | 14.7 | 64.0 | 517 | 0.1 (0.1 %), p95 5 | 53.9 (84.1 %), p95 488 | 10.1 (15.7 %), p95 55 |

- **`EnrichPersistMail`** — sur 61.6 ms en moyenne (8.0 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 36.4 ms exécution SQL, 25.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 43.8 ms en moyenne (11.1 requête(s) SQL par appel) : 4.1 ms attente d'une connexion, 36.3 ms exécution SQL, 3.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 64.0 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 53.9 ms exécution SQL, 10.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.5 | 321.8 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.5 | 10.1 | 48.5 | 18.7 | 28.6 | 18.7 | 30.5 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.5 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **321.8 µs**.

- **`GetMailsByUids`** — sur 10.1 ms de matérialisation, l'appel a construit 207.5 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.5 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **48.5 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4561.2 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 282.6 | 1450 | 129.2 (45.7 %), p95 325 | 11.4 (4.0 %), p95 93 | 51.8 (18.3 %), p95 1450 | 47.0 (16.6 %), p95 250 | 43.2 (15.3 %), p95 235 |

- **Enrichir un message** — sur 282.6 ms en moyenne (3.8 message(s) par requête) : 129.2 ms fetch IMAP, 11.4 ms extraction XDM, 51.8 ms parsing CDA, 47.0 ms écritures base, 43.2 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **3.00 aller(s)-retour(s) IMAP par message enrichi** — 1.00 `fetch_whole_message`, 0.50 `open_folder`, 0.50 `resolve_folder`, 0.50 `fetch_bodystructure`, 0.50 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 251.5 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 634.2 | 977 | 0.0 (0.0 %), p95 5 | 17.5 (2.8 %), p95 57 | 220.6 (34.8 %), p95 476 | 395.9 (62.4 %), p95 488 | 416.2 (65.6 %), p95 950 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 634.2 ms en moyenne : 0.0 ms garde d'opposition, 17.5 ms construction MIME, 220.6 ms obtention de session SMTP, 395.9 ms transmission + acquittement, 416.2 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.443 | 2.400 | 96.62 |
| `smtp_session` | 0.005 | 0.988 | 9.98 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.279 | 2.324 | 0.488 | 9.98 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 1.40 |
| `GetAttachmentStream` | 0.488 | 2.350 | 2.425 | 0.550 | 1.47 |
| `GetEmailContent` | 0.005 | 0.696 | 2.425 | 0.696 | 13.00 |
| `GetFolders` | 0.005 | 0.992 | 0.992 | 0.243 | 7.76 |
| `ReadFolder` | 0.775 | 2.400 | 2.400 | 0.487 | 35.22 |
| `ReadToday` | 0.005 | 0.496 | — | 0.496 | 7.80 |
| `UpdateFlag` | 0.005 | 0.487 | — | 0.487 | 25.64 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.396** | 0.462 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.488 | 0.550 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.243 | 0.0 % |
| `ReadFolder` | **0.428** | 0.440 | 0.443 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 96.62 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.775 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 22.00 clients | 0 clients | 100.0 % | 26.2 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.33 cœurs | 24 cœurs | 34.7 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 3.78 cœurs | 24 cœurs | 15.7 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-26768` | 13.00 éléments | 100 éléments | 13.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#14168` (CPU) | 2.89 cœurs | 24 cœurs | 12.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#26768` (CPU) | 2.75 cœurs | 24 cœurs | 11.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#56460` (CPU) | 2.69 cœurs | 24 cœurs | 11.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#65264` (CPU) | 2.66 cœurs | 24 cœurs | 11.1 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 26.2 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 535 575

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 5 972 |
| OpenAI | gpt-4o-mini | prompt | 529 603 |
| OpenAI | text-embedding-3-small | embedding | 900 232 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 276 | 0 (0.0 %) | 0 | 7.3 | 1.16 | 1.01 | 2.49 |
| étiquetage (chat) | OpenAI | 276 | 0 (0.0 %) | 0 | 7.3 | 1.11 | 0.96 | 2.49 |
| embedding | OpenAI | 276 | 0 (0.0 %) | 0 | 7.3 | 0.56 | 0.47 | 1.51 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 6 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.8 | 24.0 |
| GPU — VRAM occupée (Mo) | 1 372 | 1 572 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.5 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 607.3** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.32** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **4.0 ms** | sur 759 056 requêtes HTTP k6 |
| Taux de cache (blocs) | **98.29 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **7.00 Mo/s (896 blocs/s)** | attente disque : 7.9 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **325 846 / 29 490** | rapport 11.0 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **179.3** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.37 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **7 / 0** | blocs écrits par les backends eux-mêmes : 32 % |
| Sessions ouvertes / s | **2.93** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **126.3 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 571 / 2 024** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **97 / 100 %** | fautes majeures/s max : 2.5 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **87 évictions `pg_stat_statements`** pendant le tir (98 813 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

133 formes de requête, 5 998 829 appels, **17.0 min** de temps serveur cumulé — soit **1.3 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **15.0 %** | 15 % | 8 451 | 0.01 | 18.09 | 50.8 | 334 | 0 % | 0 | 879 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **14.6 %** | 30 % | 167 326 | 0.22 | 0.90 | 1.0 | 18 | 14 % | 0 | 1 882 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 3 | **13.3 %** | 43 % | 8 421 | 0.01 | 16.20 | 50.8 | 389 | 0 % | 0 | 872 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **7.1 %** | 50 % | 88 487 | 0.12 | 0.82 | 18.1 | 122 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **6.3 %** | 56 % | 758 982 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 6 | **3.7 %** | 60 % | 167 041 | 0.22 | 0.23 | 1.0 | 8 | 1 % | 0 | 1 876 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 7 | **3.3 %** | 63 % | 15 879 | 0.02 | 2.10 | 1.0 | 25 | 61 % | 0 | 1 291 | **Postgres** — 61 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 8 | **3.1 %** | 66 % | 8 408 | 0.01 | 3.78 | 20.0 | 621 | 1 % | 0 | 874 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 9 | **3.1 %** | 70 % | 137 375 | 0.18 | 0.23 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 10 | **2.7 %** | 72 % | 8 336 | 0.01 | 3.35 | 20.0 | 624 | 0 % | 0 | 867 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 11 | **2.2 %** | 74 % | 5 081 | 0.01 | 4.41 | 178.0 | 540 | 1 % | 0 | 891 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 12 | **2.0 %** | 76 % | 281 306 | 0.37 | 0.07 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 13 | **2.0 %** | 78 % | 95 384 | 0.13 | 0.21 | 18.0 | 5 | 0 % | 0 | 1 821 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 14 | **1.5 %** | 80 % | 281 309 | 0.37 | 0.06 | 2.1 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 15 | **1.3 %** | 81 % | 88 479 | 0.12 | 0.15 | 18.0 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 16 | **1.2 %** | 82 % | 45 034 | 0.06 | 0.28 | 27.0 | 5 | 0 % | 0 | 1 406 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **1.0 %** | 83 % | 143 488 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **1.0 %** | 84 % | 143 490 | 0.19 | 0.07 | 14.0 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **1.0 %** | 85 % | 187 866 | 0.25 | 0.05 | 1.5 | 6 | 0 % | 0 | 1 900 | — | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |
| 20 | **0.8 %** | 86 % | 88 486 | 0.12 | 0.10 | 5.7 | 9 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.9 % | 87.6 % |
| INSERT | 4.1 % | 3.0 % |
| UPDATE | 0.4 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.5 % | 7.6 % |
| bases : praticien (N bases) | 90.1 % | 82.2 % |
| bases : unique (1 base) | 9.9 % | 17.8 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **18.1** | 88 | 8 451 | 15.0 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **16.2** | 204 | 8 421 | 13.3 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **4.4** | 63 | 5 081 | 2.2 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **3.8** | 59 | 8 408 | 3.1 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **3.4** | 58 | 8 336 | 2.7 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 497 | 178 143 | 0 | 5 | 0.1 Mo |
| `Mails` | 832 | 109 239 | 812 | 26 | 0.1 Mo |
| `MailTags` | 228 | 56 544 | 82 | 43 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 135 | 35 235 | 199 | 43 | 30.0 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 231 | 34 291 | 1 495 | 157 | 8.0 Mo |
| `MailRecipients` | 204 | 31 824 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 82 | 12 792 | 2 490 | 156 | 1.9 Mo |
| `PendingActions` | 174 | 5 134 | 0 | 31 | 0.1 Mo |
| `Tags` | 157 | 2 826 | 102 | 0 | 0.0 Mo |
| `MailFolders` | 422 | 1 138 | 442 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (6.3 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 98.3 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | 11 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailAttachments` balayée 135 fois (35235 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 231 fois (34291 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 82 fois (12792 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°11 (2.2 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Postgres | 🟡 | 32 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | requête n°7 (3.3 % du temps SQL) — 61 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°8 (3.1 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°13 (2.0 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-105530.tsv`, `pgserver-journey-debut-101701.tsv`, `pgserver-journey-fin-105535.tsv`, `pgtables-journey-debut-101706.tsv`, `pgtables-journey-fin-105541.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 246638 — dont **246638** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261107-task430-105453.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
