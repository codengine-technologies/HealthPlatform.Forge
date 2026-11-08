# Rapport de tir — journey-courte-1400-1996-20261108-bilan-apres

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261108-bilan-apres-005656.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 1 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 16 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.009 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 759657 — **débit émergent global** : 336.2 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53985 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 336.2 | **143.9** | 58.6 | **548.4** | — | 7170.7 | 0.01 | 100.0 | 0 | 0 | 247726/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214072 | 290.46 | 0.01 | 817.7 |
| **1996 médecins** | 1080 | 933 | 383886 | 411.45 | 0.01 | 1467.7 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 58 / 552 (n=63352) | 64 / 558 (n=114624) |
| 2 | Ouvrir / rafraîchir l'inbox | 39 / 90 (n=31682) | 51 / 132 (n=57316) |
| 3 | Ouvrir un message enrichi (servi base) | 33 / 61 (n=15852) | 46 / 103 (n=28648) |
| 4 | Ouvrir un message froid (fetch IMAP) | 443 / 505 (n=6379) | 454 / 520 (n=11537) |
| 5 | Recherche | 323 / 581 (n=4706) | 345 / 640 (n=8685) |
| 6 | Envoi (acquittement UI) | 491 / 923 (n=4720) | 492 / 950 (n=8520) |
| 7 | Télécharger une PJ (~124 Ko) | 36 / 67 (n=6377) | 51 / 124 (n=11513) |
| 8 | Marquer lu | 33 / 80 (n=12618) | 52 / 105 (n=22945) |
| 9 | Rechercher un patient | 55 / 64 (n=4768) | 56 / 75 (n=8424) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 65 (n=7168) | 59 / 77 (n=12808) |
| 11 | Fiche patient complète (ressenti médecin) | 261 / 417 (n=3584) | 339 / 672 (n=6404) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.6 / 20 | 34.6 / 65 | 8078 | 417 |
| **1996 médecins** | 14.3 / 20 | 33.8 / 65 | 14304 | 672 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2225 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 609 ms en moyenne, 7171 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2259 / 3080 (magasin) | 2259 / 3080 (magasin) |
| Backends Postgres (moy/max) | 1245 / 1435 | 1990 / 2034 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 5 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 30/188 (16 %) | 55/162 (34 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/188 (0 %) | 0/162 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 30/188 (16 %) | 55/162 (34 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 167.3 | 204.9 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 167.3 | 204.9 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 122 / 433 | 98 / 279 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 112 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1406 | 2003 |
| Backends **directs** — audit + provisionnement (max) | 29 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 4 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 97.6 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 0 / 4 |
| RSS par réplica api-mail, Mo (moy/max) | 1170 / 1565 (5 réplicas) | 2005 / 2253 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1435.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2034.0 / 2500** (81.4 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15852)
- palier 1996 : cohorte 1996 chauffée à 100.0 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28648)

> ⓘ Chauffe : **301 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 58 (300) | 552 (1500) | 63352 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 39 (300) | 90 (1000) | 31682 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 33 (100) | 61 (500) | 15852 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 443 (800) | 505 (2500) | 6379 | ✅ |
| 5 | Recherche | 323 (500) | 581 (2000) | 4706 | ✅ |
| 6 | Envoi (acquittement UI) | 491 (1000) | 923 (3000) | 4720 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 36 (500) | 67 (2000) | 6377 | ✅ |
| 8 | Marquer lu | 33 (200) | 80 (1000) | 12618 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 64 (1500) | 4768 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 65 (2000) | 7168 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 261 (1500) | 417 (4000) | 3584 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 64 (300) | 558 (1500) | 114624 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 51 (300) | 132 (1000) | 57316 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 46 (100) | 103 (500) | 28648 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 454 (800) | 520 (2500) | 11537 | ✅ |
| 5 | Recherche | 345 (500) | 640 (2000) | 8685 | ✅ |
| 6 | Envoi (acquittement UI) | 492 (1000) | 950 (3000) | 8520 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 51 (500) | 124 (2000) | 11513 | ✅ |
| 8 | Marquer lu | 52 (200) | 105 (1000) | 22945 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 75 (1500) | 8424 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 77 (2000) | 12808 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 339 (1500) | 672 (4000) | 6404 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114624 | 162 | 558 | 18524.4 | 44.8 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8520 | 633 | 950 | 5394.2 | 13.0 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11537 | 456 | 520 | 5258.5 | 12.7 % |
| 🟢 | Recherche (`search`) | 8685 | 396 | 640 | 3436.7 | 8.3 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57316 | 58 | 132 | 3314.3 | 8.0 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28648 | 54 | 103 | 1540.9 | 3.7 % |
| 🟢 | Marquer lu (`mark_read`) | 22945 | 59 | 105 | 1354.0 | 3.3 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11513 | 68 | 124 | 779.9 | 1.9 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7152 | 102 | 152 | 726.7 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8424 | 48 | 75 | 405.0 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6404 | 59 | 77 | 376.2 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6404 | 37 | 67 | 235.1 | 0.6 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 1 🟠 · 11 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 18524.4 s, 44.8 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 8.8×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15838 | 390 | 996 | 6078.7 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15838 | 58 | 495 | 2157.0 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15838 | 19 | 160 | 703.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15838 | 56 | 67 | 905.5 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15841 | 15 | 116 | 473.4 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15841 | 49 | 79 | 832.7 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28656 | 398 | 994 | 11219.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28656 | 63 | 504 | 4002.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28656 | 28 | 180 | 1570.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28656 | 60 | 81 | 1732.6 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28658 | 21 | 126 | 1080.8 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28658 | 69 | 137 | 2233.5 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (994 ms de p95, 398 ms de p50, n=28656), qui porte **aussi** le temps serveur de l'étape (11219.0 s, 61 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (137 ms de p95, 69 ms de p50, n=28658), qui porte **aussi** le temps serveur de l'étape (2233.5 s, 67 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21993 | 74.0 | 44.5 | 98.3 | 173.5 | 1493.2 |
| attachment,palier:1400 | 6377 | 40.2 | 36.3 | 55.4 | 67.0 | 164.4 |
| attachment,palier:1996 | 11513 | 67.7 | 51.4 | 98.8 | 124.4 | 1122.5 |
| attachment,palier:transition | 644 | 185.4 | 43.2 | 616.4 | 747.6 | 1125.4 |
| dashboard | 220252 | 169.1 | 62.5 | 472.6 | 666.4 | 1663.5 |
| dashboard,call:coverage,palier:1400 | 15838 | 57.2 | 56.3 | 63.1 | 66.5 | 134.5 |
| dashboard,call:coverage,palier:1996 | 28656 | 60.5 | 60.0 | 73.8 | 80.6 | 604.2 |
| dashboard,call:coverage,palier:transition | 1044 | 139.5 | 106.1 | 275.4 | 331.1 | 606.6 |
| dashboard,call:folder,palier:1400 | 15838 | 383.8 | 390.2 | 762.1 | 996.0 | 1510.4 |
| dashboard,call:folder,palier:1996 | 28656 | 391.5 | 397.8 | 772.7 | 994.0 | 1569.7 |
| dashboard,call:folder,palier:transition | 1044 | 527.3 | 499.5 | 895.5 | 1042.7 | 1610.2 |
| dashboard,call:folders,palier:1400 | 15838 | 44.4 | 19.4 | 146.4 | 160.2 | 279.1 |
| dashboard,call:folders,palier:1996 | 28656 | 54.8 | 28.0 | 161.0 | 180.0 | 627.1 |
| dashboard,call:folders,palier:transition | 1044 | 157.2 | 142.1 | 318.9 | 419.5 | 1019.7 |
| dashboard,call:today,palier:1400 | 15838 | 136.2 | 58.2 | 474.8 | 495.2 | 791.5 |
| dashboard,call:today,palier:1996 | 28656 | 139.7 | 62.9 | 481.6 | 504.3 | 1055.9 |
| dashboard,call:today,palier:transition | 1044 | 352.0 | 305.0 | 675.2 | 718.4 | 1028.1 |
| dashboard,palier:1400 | 63352 | 155.4 | 58.4 | 455.5 | 552.2 | 1510.4 |
| dashboard,palier:1996 | 114624 | 161.6 | 63.6 | 463.2 | 558.2 | 1569.7 |
| dashboard,palier:transition | 4176 | 294.0 | 195.8 | 653.7 | 756.8 | 1610.2 |
| mark_read | 43826 | 65.7 | 47.2 | 92.7 | 121.3 | 1106.6 |
| mark_read,palier:1400 | 12618 | 45.4 | 33.3 | 75.1 | 80.4 | 163.8 |
| mark_read,palier:1996 | 22945 | 59.0 | 51.8 | 92.4 | 105.5 | 631.3 |
| mark_read,palier:transition | 1179 | 132.3 | 64.1 | 410.7 | 508.8 | 844.4 |
| patient_docs | 177611 | 74.8 | 51.9 | 121.6 | 170.9 | 2914.4 |
| patient_docs,palier:1400 | 52411 | 44.0 | 41.5 | 77.8 | 91.3 | 222.2 |
| patient_docs,palier:1996 | 91714 | 66.3 | 57.5 | 123.7 | 150.6 | 783.5 |
| patient_docs,palier:transition | 4437 | 171.7 | 56.7 | 551.3 | 780.1 | 2365.3 |
| patient_dossier | 12271 | 41.6 | 28.0 | 56.2 | 82.2 | 889.1 |
| patient_dossier,palier:1400 | 3584 | 25.8 | 23.6 | 33.6 | 40.3 | 125.6 |
| patient_dossier,palier:1996 | 6404 | 36.7 | 32.0 | 55.9 | 66.8 | 583.3 |
| patient_dossier,palier:transition | 301 | 95.2 | 28.9 | 304.3 | 359.0 | 602.1 |
| patient_opposition | 12271 | 62.3 | 57.6 | 70.6 | 82.8 | 937.6 |
| patient_opposition,palier:1400 | 3584 | 56.6 | 55.8 | 61.7 | 64.7 | 148.5 |
| patient_opposition,palier:1996 | 6404 | 58.7 | 59.1 | 70.8 | 76.7 | 147.1 |
| patient_opposition,palier:transition | 302 | 90.8 | 58.3 | 207.3 | 247.0 | 523.7 |
| patient_search | 16204 | 51.4 | 55.6 | 69.2 | 82.7 | 630.0 |
| patient_search,palier:1400 | 4768 | 44.3 | 55.4 | 60.9 | 63.8 | 129.6 |
| patient_search,palier:1996 | 8424 | 48.1 | 56.3 | 69.1 | 75.4 | 476.6 |
| patient_search,palier:transition | 402 | 77.9 | 56.9 | 170.7 | 235.4 | 455.3 |
| read_content | 55063 | 60.7 | 40.1 | 84.4 | 119.0 | 1640.6 |
| read_content,palier:1400 | 15852 | 36.3 | 33.5 | 49.8 | 60.6 | 148.6 |
| read_content,palier:1996 | 28648 | 53.8 | 46.3 | 85.5 | 103.2 | 673.5 |
| read_content,palier:transition | 1308 | 144.2 | 40.6 | 492.8 | 616.0 | 1302.1 |
| read_content_cold | 22039 | 456.6 | 450.1 | 506.0 | 528.6 | 1357.6 |
| read_content_cold,palier:1400 | 6379 | 443.5 | 442.8 | 490.4 | 504.7 | 654.8 |
| read_content_cold,palier:1996 | 11537 | 455.8 | 453.9 | 505.0 | 520.3 | 1010.6 |
| read_content_cold,palier:transition | 551 | 491.9 | 458.3 | 647.7 | 722.0 | 992.8 |
| read_list | 110126 | 64.3 | 45.0 | 110.2 | 152.6 | 1657.2 |
| read_list,call:emails,palier:1400 | 15841 | 52.6 | 49.2 | 68.7 | 79.4 | 199.2 |
| read_list,call:emails,palier:1996 | 28658 | 77.9 | 69.0 | 116.9 | 136.7 | 800.2 |
| read_list,call:emails,palier:transition | 1228 | 233.4 | 63.3 | 739.5 | 893.2 | 1657.2 |
| read_list,call:folder,palier:1400 | 15841 | 29.9 | 15.1 | 32.3 | 116.1 | 800.8 |
| read_list,call:folder,palier:1996 | 28658 | 37.7 | 20.6 | 57.6 | 126.0 | 689.9 |
| read_list,call:folder,palier:transition | 1228 | 82.2 | 18.5 | 237.1 | 336.6 | 845.8 |
| read_list,palier:1400 | 31682 | 41.2 | 39.4 | 66.0 | 90.4 | 800.8 |
| read_list,palier:1996 | 57316 | 57.8 | 50.8 | 108.4 | 132.4 | 800.2 |
| read_list,palier:transition | 2456 | 157.8 | 55.4 | 496.3 | 740.9 | 1657.2 |
| search | 16487 | 405.2 | 339.8 | 532.6 | 894.1 | 2894.9 |
| search,palier:1400 | 4706 | 372.7 | 323.5 | 448.3 | 580.8 | 1527.4 |
| search,palier:1996 | 8685 | 395.7 | 345.5 | 483.1 | 640.5 | 1631.5 |
| search,palier:transition | 448 | 507.6 | 347.4 | 993.0 | 1288.3 | 1768.3 |
| send | 15689 | 650.7 | 515.5 | 920.6 | 951.7 | 1986.3 |
| send,palier:1400 | 4720 | 635.9 | 491.2 | 901.7 | 922.6 | 1078.0 |
| send,palier:1996 | 8520 | 633.1 | 491.7 | 923.4 | 949.8 | 1392.1 |
| send,palier:transition | 470 | 660.1 | 576.3 | 942.9 | 1137.7 | 1565.5 |
| treatment | 13855 | 103.9 | 83.7 | 127.7 | 174.1 | 3945.4 |
| treatment,palier:1400 | 4039 | 71.9 | 78.7 | 94.8 | 103.9 | 163.9 |
| treatment,palier:1996 | 7152 | 101.6 | 89.1 | 130.6 | 151.7 | 3945.4 |
| treatment,palier:transition | 326 | 193.5 | 84.3 | 604.2 | 761.2 | 1234.8 |
| warmup | 21956 | 608.7 | 506.8 | 992.3 | 1308.4 | 7170.7 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-07T23:19:16.964000+00:00 → 2026-11-07T23:56:56.725000+00:00 (2260 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-bilan-apres.csv`) | ✅ 77466 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-14580` | 0.95 | 6 | 27 | 0.031 | 4.62 |
| `DESKTOP-DEV-X2C-55496` | 0.91 | 7 | 24 | 0.037 | 4.71 |
| `DESKTOP-DEV-X2C-66008` | 0.89 | 4 | 29 | 0.027 | 4.91 |
| `DESKTOP-DEV-X2C-67684` | 0.92 | 27 | 33 | 0.035 | 4.62 |
| `DESKTOP-DEV-X2C-71596` | 0.95 | 10 | 25 | 0.028 | 4.47 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.19 | 4.37 | 2539 |
| `com.docker.backend#34124` | 0.00 | 0.31 | 40 |
| `dcp#48172` | 0.00 | 0.00 | 12 |
| `dcp#55180` | 0.00 | 0.04 | 14 |
| `dcp#61096` | 0.00 | 0.00 | 12 |
| `dcp#61372` | 0.00 | 0.00 | 12 |
| `dcp#69252` | 0.00 | 0.00 | 13 |
| `dcp#69528` | 0.00 | 0.00 | 12 |
| `dcp#70012` | 0.00 | 0.00 | 12 |
| `dcp#70760` | 0.00 | 0.00 | 12 |
| `dcp#72368` | 0.00 | 0.04 | 14 |
| `dcp#72460` | 0.00 | 0.08 | 14 |
| `dcp#72572` | 0.00 | 0.00 | 12 |
| `dcp#73284` | 0.00 | 0.14 | 51 |
| `dcp#74392` | 0.75 | 2.32 | 3198 |
| `dcp#75972` | 0.00 | 0.00 | 12 |
| `dcp#78484` | 0.00 | 0.04 | 12 |
| `k6#252707` | 0.84 | 1.91 | 2899 |
| `mss.mail.api#14580` | 0.61 | 2.33 | 2226 |
| `mss.mail.api#55496` | 0.64 | 2.32 | 2171 |
| `mss.mail.api#66008` | 0.58 | 1.74 | 2118 |
| `mss.mail.api#67684` | 0.62 | 2.60 | 2253 |
| `mss.mail.api#71596` | 0.63 | 3.00 | 2179 |
| `mss.mail.e2e#57704` | 0.01 | 0.39 | 35 |
| `vmmemWSL#36464` | 5.20 | 12.38 | 65910 |
| `loadtest-otel-collector-hhgbpxnx` | 0.02 | 0.13 | 108 |
| `loadtest-pgbouncer-kjkwmybx` | 0.43 | 0.94 | 53 |
| `mss-mail-flagsmith-app-b6152948` | 0.12 | 0.45 | 471 |
| `mss-mail-flagsmith-db-b6152948` | 0.01 | 0.10 | 164 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.05 | 160 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.13 | 246 |
| `mss-mail-rabbitmq-rygjpqmv` | 0.01 | 0.03 | 152 |
| `mss-mail-redis-b6152948` | 0.28 | 1.49 | 968 |
| `mss-mail-rediscommander-ycxcnhnz` | 0.00 | 0.19 | 32 |
| `mss-mail-seq-b6152948` | 0.09 | 1.01 | 6827 |
| `postgres-pgvector` | 1.96 | 9.57 | 46387 |

- **Hôte** : CPU 62.2 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 55
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9361, cl_waiting max 19, cl_waiting_maintenance max 19, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 205, maxwait_ms max 205, maxwait_practitioner_ms max 0, sv_active max 78, sv_idle max 1592, sv_login max 5
- **Backends Postgres** : audit max 5, cache_mb max 40249, direct max 29, idle_over_60s max 218, majfault_per_s max 4, pooler max 2003, practitioner_databases max 1993, provision max 4, rss_mb max 6211, started_last_60s max 433, total max 2034, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 4585.6 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2470.7 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 1352.0 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2198.7 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 740.7 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 966.4 | 442 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 745.2 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 1877.1 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2065.2 | 433 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 417.6 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 605.5 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 370.8 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 2204.6 | 444 |
| `api/v{version:apiVersion}/Sync/coverage` | 433.9 | 447 |

- **p95 client global (k6)** : 548.4 ms
- **p95 serveur le plus élevé** : 4585.6 ms
- **Écart** : -4037.2 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.80 |
| Documents CDA /s | 0.82 |
| Durée traitement CDA (s, p95) | 2.35 |
| Événements de session IMAP /s | 4.07 |
| Recherches (s, p95) | 1.918 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 62.1 | 235 | 0.0 (0.0 %), p95 5 | 38.2 (61.5 %), p95 180 | 23.9 (38.5 %), p95 73 |
| `GetMail` | 11.1 | 47.6 | 908 | 4.5 (9.4 %), p95 131 | 39.6 (83.2 %), p95 754 | 3.5 (7.4 %), p95 17 |
| `GetMailsByUids` | 14.7 | 83.0 | 833 | 0.1 (0.1 %), p95 5 | 71.7 (86.4 %), p95 755 | 11.2 (13.5 %), p95 120 |

- **`EnrichPersistMail`** — sur 62.1 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 38.2 ms exécution SQL, 23.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 47.6 ms en moyenne (11.1 requête(s) SQL par appel) : 4.5 ms attente d'une connexion, 39.6 ms exécution SQL, 3.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 83.0 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 71.7 ms exécution SQL, 11.2 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.5 | 326.2 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.1 | 11.2 | 54.1 | 18.7 | 28.6 | 18.7 | 30.4 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.5 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **326.2 µs**.

- **`GetMailsByUids`** — sur 11.2 ms de matérialisation, l'appel a construit 207.1 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.4 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **54.1 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4090.0 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 346.1 | 2350 | 137.2 (39.7 %), p95 475 | 17.0 (4.9 %), p95 235 | 102.7 (29.7 %), p95 2350 | 48.2 (13.9 %), p95 208 | 41.0 (11.9 %), p95 145 |

- **Enrichir un message** — sur 346.1 ms en moyenne (3.8 message(s) par requête) : 137.2 ms fetch IMAP, 17.0 ms extraction XDM, 102.7 ms parsing CDA, 48.2 ms écritures base, 41.0 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 248.5 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 638.9 | 996 | 0.0 (0.0 %), p95 5 | 18.9 (3.0 %), p95 68 | 222.2 (34.8 %), p95 478 | 397.7 (62.2 %), p95 489 | 418.7 (65.5 %), p95 967 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 638.9 ms en moyenne : 0.0 ms garde d'opposition, 18.9 ms construction MIME, 222.2 ms obtention de session SMTP, 397.7 ms transmission + acquittement, 418.7 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.442 | 2.239 | 95.37 |
| `smtp_session` | 0.005 | 0.987 | 9.80 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.431 | 2.354 | 0.489 | 9.76 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 1.15 |
| `GetAttachmentStream` | 0.488 | 2.425 | 2.425 | 0.521 | 1.13 |
| `GetEmailContent` | 0.005 | 0.497 | — | 0.497 | 13.36 |
| `GetFolders` | 0.005 | 1.572 | 1.572 | 0.243 | 8.20 |
| `ReadFolder` | 0.771 | 2.239 | 2.243 | 0.487 | 34.44 |
| `ReadToday` | 0.005 | 0.497 | — | 0.497 | 7.91 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 25.80 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.412** | 0.450 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.494 | 0.494 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.490 | 0.490 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.427** | 0.442 | 0.444 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 95.37 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.771 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| conteneur `postgres-pgvector` (CPU) | 9.57 cœurs | 24 cœurs | 39.9 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-67684` | 27.00 éléments | 100 éléments | 27.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#71596` (CPU) | 3.00 cœurs | 24 cœurs | 12.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#67684` (CPU) | 2.60 cœurs | 24 cœurs | 10.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#14580` (CPU) | 2.33 cœurs | 24 cœurs | 9.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#55496` (CPU) | 2.32 cœurs | 24 cœurs | 9.7 % | 0.0 % — transitoire |
| processus `k6#252707` (CPU) | 1.91 cœurs | 24 cœurs | 7.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#66008` (CPU) | 1.74 cœurs | 24 cœurs | 7.2 % | 0.0 % — transitoire |

> ⚠️ **Désignée par un palier, écartée par la moyenne du tir.** Le verdict ci-dessus est rendu sur la fenêtre ENTIÈRE, qui mélange des populations différentes. Les ressources suivantes sont durablement présentes à un palier et diluées sur le tir — **c'est le palier qui décide d'une conclusion de capacité**, pas la moyenne des paliers.

| Ressource | Palier qui la désigne | Présence à ce palier | Présence sur le tir entier |
|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 1996 médecins | 34.0 % des échantillons du palier | 23.9 % — sous le seuil de 25 % |

**Ressource épinglée au palier 1996 médecins : PgBouncer — clients en attente (`cl_waiting`)** — présente sur 34.0 % des échantillons de CE palier (23.9 % sur le tir entier, sous le seuil de 25 %). Le tir entier ne l'épingle donc pas, et c'est une propriété de la statistique, pas du système : conclure sur la moyenne des paliers reviendrait à certifier la population la plus haute avec les mesures de la plus basse.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 300 359

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 3 666 |
| OpenAI | gpt-4o-mini | prompt | 296 693 |
| OpenAI | text-embedding-3-small | embedding | 515 557 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 160 | 0 (0.0 %) | 0 | 4.2 | 1.08 | 0.97 | 2.41 |
| étiquetage (chat) | OpenAI | 160 | 0 (0.0 %) | 0 | 4.2 | 1.02 | 0.91 | 2.40 |
| embedding | OpenAI | 160 | 0 (0.0 %) | 0 | 4.2 | 0.55 | 0.45 | 1.50 |

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
| GPU — utilisation (%) | 0.0 | 1.0 |
| GPU — VRAM occupée (Mo) | 1 427 | 1 439 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 594.7** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.19** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **3.6 ms** | sur 759 657 requêtes HTTP k6 |
| Taux de cache (blocs) | **98.24 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **6.91 Mo/s (885 blocs/s)** | attente disque : 9.9 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **276 303 / 29 520** | rapport 9.4 |
| Écritures de lignes / s (ins+upd+del) | **166.9** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.29 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **7 / 0** | blocs écrits par les backends eux-mêmes : 15 % |
| Sessions ouvertes / s | **2.59** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **56.7 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 572 / 2 034** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **97 / 100 %** | fautes majeures/s max : 3.6 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 151.5 s | 168211 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, Embedding, HtmlBody, MetadataJson : 22.7 Go lus, 3.2 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 14.7 % du temps SQL, 52.4 % des lectures disque du tir | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`<br>site inconnu ← `bus:AddNewMail` | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 38.5 s | 168039 | `colonne-volumineuse` | sélectionne Body, BodyHtml, Embedding : 10.7 Go lus, 0.1 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 33.8 s | 8960 | `pages-par-ligne` | 31.0 pages par ligne rendue, 621 par appel, 42.4 Go lus | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 30.6 s | 15848 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Content : 3.1 Go lus, 1.8 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 3.0 % du temps SQL, 29.5 % des lectures disque du tir | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}`<br>`MailRepository.UpdateAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 29.5 s | 8900 | `pages-par-ligne` | 31.2 pages par ligne rendue, 625 par appel, 42.4 Go lus | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **84 évictions `pg_stat_statements`** pendant le tir (99 003 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

133 formes de requête, 6 002 131 appels, **17.2 min** de temps serveur cumulé — soit **1.4 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **16.0 %** | 16 % | 8 929 | 0.01 | 18.47 | 51.4 | 340 | 0 % | 0 | 920 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **14.7 %** | 31 % | 168 211 | 0.22 | 0.90 | 1.0 | 18 | 14 % | 0 | 1 892 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`<br>site inconnu ← `bus:AddNewMail` | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 3 | **14.3 %** | 45 % | 9 029 | 0.01 | 16.28 | 51.1 | 392 | 0 % | 0 | 929 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **6.2 %** | 51 % | 759 597 | 1.00 | 0.08 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `PostgresTenantRegistryClient.GetMailboxAsync` ← `GET /api/v1/Mail/folders/{foldername}` | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 5 | **6.1 %** | 57 % | 88 670 | 0.12 | 0.71 | 18.0 | 100 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 6 | **3.7 %** | 61 % | 168 039 | 0.22 | 0.23 | 1.0 | 8 | 1 % | 0 | 1 888 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 7 | **3.3 %** | 64 % | 8 960 | 0.01 | 3.77 | 20.0 | 621 | 1 % | 0 | 925 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 8 | **3.1 %** | 67 % | 136 868 | 0.18 | 0.23 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 9 | **3.0 %** | 70 % | 15 848 | 0.02 | 1.93 | 1.0 | 25 | 60 % | 0 | 1 309 | **Code** — 60 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}`<br>`MailRepository.UpdateAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 10 | **2.9 %** | 73 % | 8 900 | 0.01 | 3.31 | 20.0 | 625 | 1 % | 0 | 918 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 11 | **2.1 %** | 75 % | 282 657 | 0.37 | 0.07 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `MailRepository.ResolveActiveDuplicateRefsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 12 | **2.0 %** | 77 % | 96 796 | 0.13 | 0.21 | 18.0 | 5 | 0 % | 0 | 1 914 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | site inconnu ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}`<br>`MailRepository.LoadMailsReferencingAnyRootAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 13 | **1.4 %** | 79 % | 282 653 | 0.37 | 0.05 | 2.0 | 4 | 0 % | 0 | 1 996 | — | `MailRepository.EnrichManyWithBiologyAcksAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 14 | **1.3 %** | 80 % | 88 658 | 0.12 | 0.15 | 18.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.GetMailsByUidsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 15 | **1.2 %** | 81 % | 45 011 | 0.06 | 0.28 | 27.0 | 5 | 0 % | 0 | 1 420 | — | `MailRepository.GetLatestMessageIdsPerThreadAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 16 | **1.2 %** | 82 % | 2 529 | 0.00 | 4.75 | 178.0 | 540 | 1 % | 0 | 465 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 17 | **1.0 %** | 83 % | 143 726 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **1.0 %** | 84 % | 143 730 | 0.19 | 0.07 | 14.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **1.0 %** | 85 % | 188 684 | 0.25 | 0.05 | 1.5 | 6 | 0 % | 0 | 1 909 | — | `MailRepository.GetMailAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`, `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |
| 20 | **0.9 %** | 86 % | 88 659 | 0.12 | 0.11 | 27.5 | 7 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkMailLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MailId", t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."Urg…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 95.0 % | 88.0 % |
| INSERT | 4.2 % | 2.9 % |
| UPDATE | 0.4 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.4 % | 7.3 % |
| bases : praticien (N bases) | 90.3 % | 82.3 % |
| bases : unique (1 base) | 9.7 % | 17.7 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **18.5** | 249 | 8 929 | 16.0 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **16.3** | 378 | 9 029 | 14.3 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **4.7** | 139 | 2 529 | 1.2 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **3.8** | 110 | 8 960 | 3.3 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **3.3** | 261 | 8 900 | 2.9 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 426 | 169 694 | 0 | 5 | 0.1 Mo |
| `Mails` | 784 | 102 672 | 723 | 26 | 0.1 Mo |
| `MailTags` | 205 | 50 840 | 80 | 43 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 212 | 31 460 | 1 269 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 116 | 30 276 | 177 | 43 | 30.0 Mo |
| `MailRecipients` | 183 | 28 548 | 64 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 77 | 12 012 | 2 408 | 156 | 1.9 Mo |
| `PendingActions` | 192 | 5 653 | 0 | 31 | 0.1 Mo |
| `Tags` | 144 | 2 592 | 90 | 0 | 0.0 Mo |
| `MailFolders` | 390 | 1 050 | 336 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°4 (6.2 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 98.2 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 212 fois (31460 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 116 fois (30276 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 77 fois (12012 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°9 (3.0 % du temps SQL) — 60 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°16 (1.2 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°7 (3.3 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°12 (2.0 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-005739.tsv`, `pgserver-journey-debut-001907.tsv`, `pgserver-journey-fin-005747.tsv`, `pgtables-journey-debut-001911.tsv`, `pgtables-journey-fin-005751.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 247726 — dont **247726** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261108-bilan-apres-005656.jsonl`.

Requêtes `/api/data` sur la fenêtre du tir, 23:19:05 → 23:56:56 UTC le 2026-11-07.

- **2 erreurs** : une seule requête, `PUT /mail/folders/INBOX/emails/463/status/read` en 500. `NpgsqlException` « Exception while reading from stream », connexion Postgres coupée, reprise EF épuisée. Isolée (1 sur 759 657).
- **Envoi sain** : obtention de session SMTP 222 ms, transmission 398 ms. 2 sessions SMTP poolées fermées par le serveur avant DATA, reprises.
- **Marqueurs de régression** : `Failed to parse entity headers` 0, `SecurityTokenMalformedException` 0, événements `Debug` 0 (niveau de log nominal).
- **429** : 0. **Échecs d'embedding** : 0. **Reprises d'étiquetage IA** (`[TaggingRecovery]`) : 0.
- **Parsings CDA** (`Parsing completed`) : 0. Attendu : population hydratée (`JOURNEY_WARMUP_HYDRATED=1`), le tir n'analyse aucun nouveau document.
- **Avertissements bénins**, du même ordre dans les trois tirs : `[TlsCertificateValidationSession] Allowing untrusted certificate` (~15 000, certificat auto-signé du banc), `[MailClientSession] ♻️ Session expired` (~5 000, recyclage nominal), `[PractitionerContactPublisher] SKIPPED - Invalid RPPS` (≤ 16, identités synthétiques).

## Findings — analyse de code

> - **Tir** : `journey-courte-1400-1996-20261108-bilan-apres`. **Code** : api-mail `5b4e394f` (journal de la campagne,
>   `code : 5b4e394f (variante B)`). **Mesures** : `pgstats-journey-005739.tsv`, 759 657 requêtes HTTP. **Mode** :
>   normal. Les findings réglés au registre sont remesurés, pas ré-explorés.
> - **Site** : commentaire `site=` de task-432, complété par `git grep` au commit du tir. Le SQL d'audit, écrit à la
>   main hors EF, n'a pas de commentaire : son site est cherché à la main, avec la recherche citée.
> - **Plans** : `Docs/audits/findings/plans/20261108-bilan-apres/`, joués sur la base de banc la plus volumineuse
>   (`u_l9l_b27c2b6f659b50f6240b3481927d0381`, la même qu'au rejeu du 2026-11-07), et sur `mss_registry_loadtest` pour
>   l'audit. Paramètres tirés de la base, jamais recopiés. Aucune migration entre le commit du tir et `develop` : le
>   schéma des plans est celui du tir. Les bases ont vécu un tir de plus (avant-2) depuis.
> - **Contrôle de non-confabulation** : `python Tools/loadtest-findings/findings.py check` — **99 éléments, 0 écart**.

**Candidats** : 8 sur 8.
- Quatre formes signalées par les détecteurs de task-431. Trois sont des findings ouverts du registre (FND-007,
  FND-009, FND-010), à ré-explorer. La quatrième est nouvelle : le téléchargement d'une pièce jointe.
- Quatre formes non signalées, les plus coûteuses en temps : l'écriture d'audit, la résolution des doublons, la
  recherche des messages qui citent un fil, et les acquittements de biologie.

| Finding | Verdict | Classe | Temps SQL | Lu sur disque | Gain borné |
|---|---|---|---|---|---|
| FND-007 Document médical chargé entier, vecteur compris, à l'ouverture d'un message | **confirmé — récidive** | `colonne-volumineuse` | 151.5 s | 3.2 Go | ≈ 13 % de la forme, à mesurer par A/B |
| FND-009 Contenu du message chargé avec son vecteur | **confirmé — récidive** | `colonne-volumineuse` | 38.5 s | 0.1 Go | ≈ 68 % de la forme, à mesurer par A/B |
| FND-010 Recherche vectorielle exacte, sans index | **plausible** | `pages-par-ligne` | 33.8 s | 0.4 Go | dépend de la taille des boîtes |
| FND-014 Messages qui citent un fil : `LIKE '%…%'` sur `References` | **plausible** | `hors-détecteur` | 20.4 s | 0.0 Go | dépend de la taille des boîtes |
| FND-011 Téléchargement d'une pièce jointe | **écarté** | `colonne-volumineuse` | 30.6 s | 1.8 Go | — |
| FND-012 Écriture du journal d'audit | **écarté** | `hors-détecteur` | 31.8 s | 0.0 Go | — |
| FND-013 Résolution des doublons actifs | **écarté** | `hors-détecteur` | 21.2 s | 0.0 Go | — |
| FND-015 Acquittements de biologie | **écarté** | `hors-détecteur` | 14.3 s | 0.0 Go | — |

**Ce que le lot a changé.** FND-003 et FND-005 sont absents du tir : leurs correctifs (task-429, task-430) tiennent.
Par effet de report, **FND-007 porte désormais 52.4 % des lectures disque du tir**, contre 33.1 % au tir du
2026-11-06 : c'est le premier lecteur de disque restant. Il reste ouvert.

#### FND-007 — Le document médical est chargé entier, vecteur compris, à l'ouverture d'un message

- **Verdict** : **confirmé — récidive**. La classe `colonne-volumineuse` a été corrigée sur le chemin groupé
  (task-322, task-323) et sur le dossier patient (FND-003, task-429). Le chemin d'un message seul en mode
  `WithContent` reste ouvert. Constat identique au rejeu du 2026-11-07.
- **Forme** : `9a63b74fac8c0708f158bb2588df9b57`
- **Détecteurs** : `colonne-volumineuse` (Body, Embedding, HtmlBody, MetadataJson) et `poids-dans-le-tir`.
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1260` (`PopulateMailContentAsync`, branche
  `WithContent` : l'entité entière). Le DTO est construit par `BuildMedicalDocumentDto`
  (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:1355`). La projection d'en-tête existe déjà
  (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:1759`). Retrouvé par le commentaire
  `site=MailRepository.PopulateMailContentAsync` sur la route `GET …/emails/content/{emailid}`. Un second site,
  `bus:AddNewMail`, n'est pas résolu (`site=?`).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 168 211 |
| Temps SQL | 151.5 s |
| Part du temps SQL | 14.7 % |
| ms par appel | 0.90 |
| Pages par appel | 18 |
| Pages lues | 22.7 Go |
| Lu sur disque | 3.2 Go |
| Part des lectures disque | 52.4 % |

- **Cause** : en `WithContent`, `MailMedicalDocument` est matérialisé entier. `Embedding` et `MetadataJson` sont lus,
  détoastés, transférés, puis jetés : le DTO n'en recopie rien.
- **Preuve** : sous PostgreSQL 16, `EXPLAIN ANALYZE` ne détoaste pas (`FND-007.txt` : 2 pages, contre 18 par appel au
  tir). La preuve est le poids de chaque colonne. **Plan** : `FND-007-colonnes.txt`

```text
| lignes | Body (octets/ligne) | HtmlBody (octets/ligne) | Embedding (octets/ligne) | MetadataJson (octets/ligne) |
| 157 | 2482 | 37860 | 6148 |  |
```

- **Gain borné** : `Embedding` pèse 6 148 octets sur 46 490 par ligne, soit 13 % des octets détoastés de la forme. Au
  plus ≈ 13 % de 151.5 s et de 22.7 Go, à mesurer par A/B. `HtmlBody` (37 860 octets) est affiché : il reste.
- **Correctif proposé** : projeter `MailMedicalDocument` sans `Embedding` ni `MetadataJson` en `WithContent`.
- **Test qui le prouverait** : un test d'intégration sur `GET /api/v1/Mail/folders/{folderName}/emails/content/{emailId}`
  qui ouvre un message à document. Le SQL relevé ne sélectionne ni `"Embedding"` ni `"MetadataJson"`, et le document
  rendu garde `Body` et `HtmlBody`. Vu rouge sur le code d'avant.
- **Prévention manquante** : la consigne `groupby-final-materialise-l-entite` de `conventions/csharp.md` existe, mais sa
  garde (`AttachmentBytesReadEndToEndTests`) ne couvre que `Content` des pièces jointes. Il manque la garde « aucune
  route de lecture du parcours ne sélectionne `Embedding` ni `MetadataJson`, hors recherche vectorielle ». Elle était
  déjà nommée le 2026-11-07 et n'a pas été posée.

#### FND-009 — Le contenu du message est chargé avec son vecteur

- **Verdict** : **confirmé — récidive**. Même classe et même chemin que FND-007.
- **Forme** : `4b9380ddd1837d2bc365a5afbc833f85`
- **Détecteurs** : `colonne-volumineuse` (Body, BodyHtml, Embedding).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1323` (`PopulateMailContentAsync`, branche
  `WithContent`). Le DTO ne recopie que `Body`, `BodyHtml`, `ContentType` et `Summary`
  (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:1337`). La projection d'en-tête existe
  (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:1795`). Retrouvé par le commentaire
  `site=MailRepository.PopulateMailContentAsync`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 168 039 |
| Temps SQL | 38.5 s |
| Pages par appel | 8 |
| Pages lues | 10.7 Go |
| Lu sur disque | 0.1 Go |

- **Cause** : en `WithContent`, `MailContent` est matérialisé entier, `Embedding` compris, que rien n'affiche.
- **Preuve** : **Plan** : `FND-009-colonnes.txt`

```text
| lignes | Body (octets/ligne) | BodyHtml (octets/ligne) | Summary (octets/ligne) | Embedding (octets/ligne) |
| 156 | 2842 |  |  | 6148 |
```

- **Gain borné** : `Embedding` pèse 6 148 octets sur 8 990 par ligne, soit 68 %. Au plus ≈ 68 % de 38.5 s et de
  10.7 Go, à mesurer par A/B.
- **Correctif proposé** : le même que FND-007, sur `MailContent`.
- **Test qui le prouverait** : le même que FND-007.
- **Prévention manquante** : la même que FND-007.

#### FND-010 — La recherche vectorielle calcule la distance de chaque document du dossier

- **Verdict** : **plausible**, inchangé.
- **Forme** : `9b0276b995554c73320b5caa00935e87`. Variante : `90fed31c06a6aff57d1fb5c7c8d25a5d`.
- **Détecteurs** : `pages-par-ligne`.
- **Site** : `src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs:295`
  (`SearchMedicalDocumentsByVectorAsync`, `src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs:249`).
  Retrouvé par le commentaire `site=SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 8 960 |
| Temps SQL | 33.8 s |
| ms par appel | 3.77 |
| Pages par appel | 621 |
| Lu sur disque | 0.4 Go |

- **Cause probable** : aucun index vectoriel. Chaque recherche détoaste le vecteur de tous les documents du dossier.
- **Preuve** : **Plan** : `FND-010.txt`

```text
->  Seq Scan on "MailMedicalDocuments" m (actual time=0.029..5.980 rows=23 loops=1)
Rows Removed by Filter: 134
Buffers: shared hit=425 read=151
```

- **Pourquoi plausible** : à 157 documents par boîte, la recherche exacte est le bon plan. Le défaut n'existe que si
  les boîtes grossissent.
- **Gain borné** : au plus 33.8 s pour cette forme, plus sa variante. À trancher par un tir sur des boîtes 10 fois
  plus grosses.

#### FND-014 — Les messages qui citent un fil sont cherchés par `LIKE '%…%'` sur `References`

- **Verdict** : **plausible**. Même raison que FND-010 : le coût croît avec la taille de la boîte.
- **Forme** : `a5978bf1120a527de14ca8d1c8283f21`
- **Détecteurs** : `hors-détecteur` (coût seul).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:2498` (`LoadMailsReferencingAnyRootAsync`), qui
  applique `ReferencesAnyOf` (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:2402`) : un `OR` de `LIKE`
  par racine de fil de la page. Retrouvé par le commentaire `site=MailRepository.LoadMailsReferencingAnyRootAsync`,
  route `GET …/emails/{ids}` (page d'en-têtes).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 96 796 |
| Temps SQL | 20.4 s |
| ms par appel | 0.21 |
| Lignes par appel | 18.0 |
| Pages par appel | 5 |

- **Cause** : un `LIKE` à joker de tête ne peut pas utiliser d'index B-tree. Chaque page d'en-têtes balaie toute la
  table `Mails` de la boîte.
- **Preuve** : **Plan** : `FND-014.txt`

```text
Seq Scan on "Mails" m (actual time=0.006..0.134 rows=16 loops=1)
Rows Removed by Filter: 140
Buffers: shared hit=5
```

- **Pourquoi plausible** : 156 messages par boîte au banc, 5 pages. Le balayage coûte peu ici, mais il croît
  linéairement avec la boîte, et la page d'en-têtes est la requête la plus fréquente du parcours.
- **Gain borné** : au plus 20.4 s au banc. À trancher par le même tir que FND-010.
- **Correctif à évaluer** : une table de liens de fil (message → racine), indexée, alimentée à l'écriture.
- **Test qui le prouverait** : un plan sur une boîte de 10 000 messages, avec et sans la table de liens.

#### FND-011 — Le téléchargement d'une pièce jointe lit son contenu

- **Verdict** : **écarté**. C'est le faux positif connu de D2 (« le chemin qui sert ce contenu ») : la forme sert
  `Content` sur la route qui le rend.
- **Forme** : `4c9c73a7b84af06ddf5fcf9b73b3c7ab`
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:3090` (`GetAttachmentAsync`), appelé par
  `src/Application/Services/Implementation/ImapService.cs:3552`. Le second site du commentaire,
  `UpdateAttachmentAsync` (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:3131`), ne s'exécute que si la
  base n'a pas le contenu (`src/Application/Services/Implementation/ImapService.cs:3602`).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 15 848 |
| Temps SQL | 30.6 s |
| Pages par appel | 25 |
| Lu sur disque | 1.8 Go |
| Part des lectures disque | 29.5 % |

- **Preuve** : le plan est une recherche indexée d'une ligne (`FND-011.txt`), et le poids est celui du contenu servi.
  **Plan** : `FND-011-colonnes.txt`

```text
| lignes | Content (octets/ligne) | FileName (octets/ligne) | ContentType (octets/ligne) |
| 261 | 184586 | 12 | 16 |
```

- **Raison** : 25 pages par appel, c'est le contenu rendu au médecin. Sa part des lectures disque (29.5 %) dit que les
  pièces jointes ne tiennent pas en cache. C'est la question de stockage de `pieces-jointes-en-base`, pas un défaut
  de requête.

#### FND-012 — L'écriture du journal d'audit

- **Verdict** : **écarté**.
- **Forme** : `5148cb399674048f3066e09be6ab72ed` (lot d'une trace). Trois autres formes portent les lots de 2, 3 et 4
  traces.
- **Site** : `src/Infrastructure/Repositories/TenantDb/PostgresAuditSink.cs:198` (`InsertChunkAsync`). Retrouvé par
  `git grep -n "ON CONFLICT DO NOTHING"` au commit du tir : SQL écrit à la main, sans commentaire `site=`. Le trigger
  `audit_traces_fill_mailbox` est créé par
  `src/Infrastructure/Migrations/TenantDb/20261029130000_AddAuditActor.cs:57`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 136 868 |
| Temps SQL | 31.8 s |
| ms par appel | 0.23 |
| Lignes par appel | 1.0 |
| Pages par appel | 13 |
| Bases | 1 |

- **Preuve** : **Plan** : `FND-012.txt`

```text
Insert on audit_traces (actual time=0.877..0.878 rows=0 loops=1)
Tuples Inserted: 1
Trigger audit_traces_fill_mailbox on audit_traces_2026m11: time=0.453 calls=1
```

- **Raison** : 13 pages par ligne, c'est le tas plus trois index (clé primaire, deux index horodatés) plus la
  recherche par clé du trigger. C'est le coût normal d'une écriture. Le temps du trigger dans ce plan est celui d'un
  premier appel de session (compilation PL/pgSQL), pas celui du tir.
- **Constat annexe** : sur les quatre formes, 141 316 traces partent en 138 927 instructions, soit 1,02 trace par
  lot. L'écrivain groupe, mais à ce débit il trouve presque toujours une seule trace. Grouper davantage économiserait
  les transactions (`SET LOCAL ROLE` 1,6 s, `COMMIT` 0,2 s sur le tir), pas les pages. Gain négligeable.

#### FND-013 — La résolution des doublons actifs

- **Verdict** : **écarté**.
- **Forme** : `8f9a23fbdfe763775fed3766b575821b`
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:4823` (`ResolveActiveDuplicateRefsAsync`),
  appelé pour un message seul par `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1274`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 282 657 |
| Temps SQL | 21.2 s |
| ms par appel | 0.07 |
| Pages par appel | 16 |

- **Preuve** : **Plan** : `FND-013.txt`

```text
Nested Loop Anti Join (actual time=0.067..0.072 rows=2 loops=1)
Buffers: shared hit=20
->  Bitmap Index Scan on "PK_MailMedicalDocuments" (actual time=0.027..0.027 rows=2 loops=1)
```

- **Raison** : chaque table est lue par index. Le poids vient de la fréquence (0,37 appel par requête HTTP), pas de la
  forme.

#### FND-015 — Les acquittements de biologie

- **Verdict** : **écarté**.
- **Forme** : `9ecf42a479e49a52787a30295de1f894`
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:5380` (`EnrichManyWithBiologyAcksAsync`),
  appelé pour un message seul par `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1318`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 282 653 |
| Temps SQL | 14.3 s |
| ms par appel | 0.05 |
| Pages par appel | 4 |

- **Preuve** : **Plan** : `FND-015.txt`

```text
Seq Scan on "MailMedicalDocumentBiology" m (actual time=0.028..0.028 rows=0 loops=1)
Rows Removed by Filter: 119
Buffers: shared hit=3
```

- **Raison** : 119 lignes dans la table de la base de banc. Le planificateur préfère le balayage à l'index de task-430,
  pour 3 pages. Coût normal à cette taille.

### Finding d'instrument — « Émise par » n'est pas une répartition

- **Constat** : FND-013 et FND-015 sont attribués à la seule route `POST …/emails/enrich/sync`, émise uniquement par la
  chauffe (21 956 requêtes). Or leurs méthodes sont appelées par l'ouverture d'un message et par la page d'en-têtes,
  qui pèsent bien plus.
- **Cause** : `pg_stat_statements` ne garde **qu'un texte par forme et par base**, celui de la première exécution,
  commentaire `site=` compris. La chauffe passe la première sur chaque base, et c'est donc son commentaire qui reste.
  La colonne `call_sites` liste les **premiers sites vus**, jamais la part de chacun.
- **Effet** : la colonne « Émise par » du rapport et du dossier de candidats peut désigner une route qui ne porte
  presque rien de la forme. Un correctif aiguillé sur cette route manquerait sa cible.
- **Prévention proposée** : écrire la limite dans l'en-tête de `report_postgres.py` et dans le playbook
  (`agents/loadtest-findings.md`, étape 3b), et renommer la colonne « Émise par (premier site vu) ». Une répartition
  réelle demanderait un compteur côté application (route × site), hors du périmètre de `pg_stat_statements`.

### Connus du registre — remesurés

- **FND-001** (corrigé et mesuré) : 0.4 s, 0.0 % du temps, 0.2 Go lus, 0.0 Go sur disque.
- **FND-002** (corrigé et mesuré) : 164.9 s, 16.0 % du temps, 23.1 Go lus, 0.0 Go sur disque. Première forme du tir en
  temps SQL. Elle a été ré-explorée et écartée au rejeu du 2026-11-07 : c'est le coût du plein texte après task-427.
- **FND-003** (corrigé et mesuré) : forme absente du tir. Le correctif de task-429 tient.
- **FND-004** (corrigé et mesuré) : 62.9 s, 6.1 % du temps, 67.5 Go lus, 0.0 Go sur disque.
- **FND-005** (corrigé et mesuré) : forme absente du tir. Le correctif de task-430 tient.
- **FND-006** (écarté) : 63.9 s, 6.2 % du temps, 52.2 Go lus, 0.0 Go sur disque.
- **FND-008** (ouvert, non exploré) : hors des 8 candidats. 2 529 appels, 12.0 s, 1.2 % du temps SQL.

### Ce que l'humain décide

La forge ne rédige aucune task d'elle-même. Propositions, par gain borné décroissant :

1. **FND-007 + FND-009** : projeter le document médical et le contenu sans vecteur à l'ouverture d'un message, et
   poser la garde « aucune route de lecture ne sélectionne `Embedding` ». Une seule task. C'est le premier lecteur de
   disque du tir (52.4 % pour FND-007 seul), et la garde manquante était déjà nommée le 2026-11-07.
2. **FND-010 + FND-014** : un tir sur des boîtes 10 fois plus grosses, pour trancher l'index vectoriel et la table de
   liens de fil. Les deux défauts croissent avec la boîte, et le banc ne les mesure pas à sa taille actuelle.
3. **Finding d'instrument** : documenter que « Émise par » est le premier site vu, pas une répartition.
