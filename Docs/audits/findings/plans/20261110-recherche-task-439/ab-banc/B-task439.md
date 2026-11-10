# Rapport de tir — journey-courte-1400-1996-20261110-t439-task

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261110-t439-task-154252.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 1 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** sur le chemin du médecin (`cl_waiting` non nul sur 24 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.015 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 755325 — **débit émergent global** : 334.5 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53822 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 334.5 | **161.2** | 66.0 | **508.9** | — | 22671.0 | 0.02 | 100.0 | 0 | 0 | 248600/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214544 | 291.10 | 0.00 | 844.9 |
| **1996 médecins** | 1080 | 933 | 384119 | 411.70 | 0.01 | 1452.1 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 61 / 572 (n=63856) | 69 / 575 (n=114492) |
| 2 | Ouvrir / rafraîchir l'inbox | 44 / 111 (n=31956) | 59 / 169 (n=57242) |
| 3 | Ouvrir un message enrichi (servi base) | 38 / 76 (n=15992) | 57 / 141 (n=28639) |
| 4 | Ouvrir un message froid (fetch IMAP) | 446 / 512 (n=6425) | 458 / 530 (n=11484) |
| 5 | Recherche | 310 / 649 (n=4811) | 331 / 656 (n=8662) |
| 6 | Envoi (acquittement UI) | 500 / 933 (n=4696) | 494 / 964 (n=8529) |
| 7 | Télécharger une PJ (~124 Ko) | 41 / 87 (n=6456) | 64 / 164 (n=11425) |
| 8 | Marquer lu | 38 / 88 (n=12837) | 64 / 130 (n=22946) |
| 9 | Rechercher un patient | 56 / 70 (n=4738) | 59 / 84 (n=8493) |
| 10 | Ouvrir la page d'un dossier patient | 57 / 71 (n=7186) | 61 / 94 (n=12656) |
| 11 | Fiche patient complète (ressenti médecin) | 296 / 517 (n=3593) | 394 / 842 (n=6328) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.4 / 20 | 34.0 / 60 | 7966 | 517 |
| **1996 médecins** | 14.6 / 20 | 34.8 / 60 | 14172 | 842 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2194 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 905 ms en moyenne, 22671 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2253 / 3089 (magasin) | 2253 / 3089 (magasin) |
| Backends Postgres (moy/max) | 1244 / 1434 | 1987 / 2026 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 2 | 0 / 1 |
| PgBouncer `cl_waiting` — chemin du médecin (échant. non nuls) | 40/166 (24 %) | 65/138 (47 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 40/166 (24 %) | 65/138 (47 %) |
| …dont **registre** des comptes (échant. non nuls) | 0/166 (0 %) | 0/138 (0 %) |
| …dont **maintenance** (échant. non nuls) | 0/166 (0 %) | 0/138 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 152.1 | 336.1 |
| …dont bases **praticien** — chemin du médecin | 152.1 | 336.1 |
| …dont **registre** des comptes — chemin du médecin | 0.0 | 0.0 |
| …dont **maintenance** (`postgres`, `pgbouncer`) | 0.0 | 0.0 |
| Attente PgBouncer cumulée — chemin du médecin (s) | 825.3 | 1798.4 |
| …par transaction du médecin (ms) | 0.4 | 0.7 |
| …part du temps des transactions (attente comprise) | 19.3 % | 20.6 % |
| …part du temps des requêtes HTTP du palier (k6) | 3.8 % | 4.1 % |
| Attente PgBouncer cumulée — maintenance (s) | 0.0 | 0.0 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | 0.010 / 0.021 / 0.106 | 0.013 / 0.031 / 0.152 |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 116 / 331 | 99 / 275 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 11 | 114 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1403 | 1995 |
| Backends **directs** — audit + provisionnement (max) | 30 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 32 / 303 | 6 / 40 |
| RSS par réplica api-mail, Mo (moy/max) | 1151 / 1570 (5 réplicas) | 1993 / 2177 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1434.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2026.0 / 2500** (81.0 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15992)
- palier 1996 : cohorte 1996 chauffée à 100.0 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28639)

> ⓘ Chauffe : **306 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 61 (300) | 572 (1500) | 63856 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 44 (300) | 111 (1000) | 31956 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 38 (100) | 76 (500) | 15992 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 446 (800) | 512 (2500) | 6425 | ✅ |
| 5 | Recherche | 310 (500) | 649 (2000) | 4811 | ✅ |
| 6 | Envoi (acquittement UI) | 500 (1000) | 933 (3000) | 4696 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 41 (500) | 87 (2000) | 6456 | ✅ |
| 8 | Marquer lu | 38 (200) | 88 (1000) | 12837 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 70 (1500) | 4738 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 57 (500) | 71 (2000) | 7186 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 296 (1500) | 517 (4000) | 3593 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 69 (300) | 575 (1500) | 114492 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 59 (300) | 169 (1000) | 57242 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 57 (100) | 141 (500) | 28639 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 458 (800) | 530 (2500) | 11484 | ✅ |
| 5 | Recherche | 331 (500) | 656 (2000) | 8662 | ✅ |
| 6 | Envoi (acquittement UI) | 494 (1000) | 964 (3000) | 8529 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 64 (500) | 164 (2000) | 11425 | ✅ |
| 8 | Marquer lu | 64 (200) | 130 (1000) | 22946 | ✅ |
| 9 | Rechercher un patient | 59 (300) | 84 (1500) | 8493 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 61 (500) | 94 (2000) | 12656 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 394 (1500) | 842 (4000) | 6328 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114492 | 167 | 575 | 19089.8 | 43.9 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8529 | 632 | 964 | 5389.5 | 12.4 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11484 | 461 | 530 | 5288.8 | 12.2 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57242 | 71 | 169 | 4058.7 | 9.3 % |
| 🟢 | Recherche (`search`) | 8662 | 384 | 656 | 3328.0 | 7.6 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28639 | 68 | 141 | 1935.9 | 4.4 % |
| 🟢 | Marquer lu (`mark_read`) | 22946 | 69 | 130 | 1583.7 | 3.6 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11425 | 81 | 164 | 929.9 | 2.1 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7086 | 112 | 185 | 795.0 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8493 | 52 | 84 | 439.3 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6328 | 61 | 87 | 387.9 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6328 | 47 | 94 | 295.9 | 0.7 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 1 🟠 · 11 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 19089.8 s, 43.9 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 8.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15964 | 392 | 982 | 6160.5 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15964 | 60 | 498 | 2208.7 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15964 | 22 | 167 | 771.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15964 | 58 | 73 | 945.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15978 | 17 | 118 | 522.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15978 | 57 | 106 | 1011.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28623 | 402 | 992 | 11367.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28623 | 67 | 507 | 4094.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28623 | 36 | 192 | 1806.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28623 | 62 | 92 | 1821.6 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28621 | 25 | 132 | 1252.8 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28621 | 85 | 188 | 2806.0 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (992 ms de p95, 402 ms de p50, n=28623), qui porte **aussi** le temps serveur de l'étape (11367.5 s, 60 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (188 ms de p95, 85 ms de p50, n=28621), qui porte **aussi** le temps serveur de l'étape (2806.0 s, 69 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21825 | 85.3 | 53.9 | 147.7 | 246.0 | 1548.5 |
| attachment,palier:1400 | 6456 | 47.7 | 41.1 | 71.4 | 86.8 | 1101.2 |
| attachment,palier:1996 | 11425 | 81.4 | 63.8 | 131.2 | 163.6 | 1311.5 |
| attachment,palier:transition | 575 | 159.6 | 58.7 | 373.0 | 507.3 | 1116.0 |
| dashboard | 219816 | 172.2 | 68.0 | 473.4 | 613.8 | 1612.5 |
| dashboard,call:coverage,palier:1400 | 15964 | 59.2 | 58.1 | 67.6 | 73.5 | 184.2 |
| dashboard,call:coverage,palier:1996 | 28623 | 63.6 | 62.4 | 82.7 | 91.6 | 415.4 |
| dashboard,call:coverage,palier:transition | 1015 | 124.3 | 109.6 | 201.5 | 254.5 | 698.5 |
| dashboard,call:folder,palier:1400 | 15964 | 385.9 | 391.8 | 763.5 | 981.7 | 1546.0 |
| dashboard,call:folder,palier:1996 | 28623 | 397.1 | 401.7 | 775.1 | 992.1 | 1612.5 |
| dashboard,call:folder,palier:transition | 1015 | 480.3 | 477.0 | 776.4 | 887.2 | 1551.8 |
| dashboard,call:folders,palier:1400 | 15964 | 48.3 | 22.3 | 150.5 | 166.6 | 378.6 |
| dashboard,call:folders,palier:1996 | 28623 | 63.1 | 35.7 | 170.0 | 192.2 | 776.1 |
| dashboard,call:folders,palier:transition | 1015 | 138.5 | 116.6 | 282.5 | 345.6 | 685.6 |
| dashboard,call:today,palier:1400 | 15964 | 138.4 | 60.2 | 477.8 | 498.2 | 774.9 |
| dashboard,call:today,palier:1996 | 28623 | 143.0 | 66.5 | 482.3 | 507.2 | 1136.0 |
| dashboard,call:today,palier:transition | 1015 | 333.9 | 287.8 | 605.8 | 642.7 | 1186.4 |
| dashboard,palier:1400 | 63856 | 157.9 | 60.6 | 457.8 | 572.3 | 1546.0 |
| dashboard,palier:1996 | 114492 | 166.7 | 68.6 | 465.5 | 575.1 | 1612.5 |
| dashboard,palier:transition | 4060 | 269.3 | 160.7 | 572.4 | 650.5 | 1551.8 |
| mark_read | 43817 | 74.3 | 60.2 | 119.3 | 180.8 | 1027.6 |
| mark_read,palier:1400 | 12837 | 49.2 | 38.1 | 79.3 | 88.1 | 314.4 |
| mark_read,palier:1996 | 22946 | 69.0 | 64.3 | 110.1 | 130.1 | 699.8 |
| mark_read,palier:transition | 1141 | 117.3 | 72.0 | 271.9 | 320.5 | 616.7 |
| patient_docs | 174913 | 87.7 | 61.0 | 162.9 | 240.6 | 1528.1 |
| patient_docs,palier:1400 | 51608 | 54.0 | 48.7 | 98.8 | 118.5 | 307.7 |
| patient_docs,palier:1996 | 92454 | 80.3 | 67.0 | 154.9 | 190.0 | 839.2 |
| patient_docs,palier:transition | 4878 | 151.2 | 68.1 | 426.3 | 538.3 | 1241.6 |
| patient_dossier | 12105 | 51.2 | 34.0 | 84.7 | 137.8 | 750.7 |
| patient_dossier,palier:1400 | 3593 | 30.6 | 27.0 | 43.8 | 53.1 | 130.9 |
| patient_dossier,palier:1996 | 6328 | 46.8 | 39.7 | 76.3 | 94.0 | 580.4 |
| patient_dossier,palier:transition | 335 | 93.8 | 37.2 | 222.1 | 273.1 | 582.0 |
| patient_opposition | 12105 | 64.8 | 59.5 | 80.8 | 98.8 | 730.2 |
| patient_opposition,palier:1400 | 3593 | 58.4 | 57.4 | 65.6 | 71.0 | 162.8 |
| patient_opposition,palier:1996 | 6328 | 61.3 | 61.2 | 78.8 | 86.6 | 183.1 |
| patient_opposition,palier:transition | 335 | 82.3 | 60.6 | 140.0 | 173.7 | 573.6 |
| patient_search | 16148 | 55.1 | 57.3 | 79.4 | 99.4 | 605.8 |
| patient_search,palier:1400 | 4738 | 46.4 | 55.6 | 64.0 | 70.2 | 319.1 |
| patient_search,palier:1996 | 8493 | 51.7 | 58.6 | 76.4 | 84.1 | 502.5 |
| patient_search,palier:transition | 447 | 73.9 | 59.5 | 128.9 | 175.7 | 541.1 |
| read_content | 54954 | 75.1 | 48.5 | 131.3 | 216.4 | 1471.3 |
| read_content,palier:1400 | 15992 | 42.6 | 37.9 | 62.9 | 76.4 | 351.0 |
| read_content,palier:1996 | 28639 | 67.6 | 56.6 | 114.1 | 140.6 | 718.5 |
| read_content,palier:transition | 1232 | 159.1 | 78.2 | 357.8 | 422.7 | 873.1 |
| read_content_cold | 21977 | 462.2 | 454.9 | 517.6 | 546.1 | 1308.2 |
| read_content_cold,palier:1400 | 6425 | 447.5 | 445.6 | 497.2 | 512.4 | 685.8 |
| read_content_cold,palier:1996 | 11484 | 460.5 | 457.8 | 512.0 | 529.9 | 957.6 |
| read_content_cold,palier:transition | 571 | 489.6 | 474.4 | 592.8 | 631.6 | 998.0 |
| read_list | 109908 | 78.5 | 53.6 | 147.2 | 239.0 | 1504.6 |
| read_list,call:emails,palier:1400 | 15978 | 63.3 | 56.9 | 90.3 | 106.2 | 352.9 |
| read_list,call:emails,palier:1996 | 28621 | 98.0 | 84.9 | 155.8 | 187.6 | 751.0 |
| read_list,call:emails,palier:transition | 1165 | 265.9 | 260.6 | 499.8 | 629.4 | 1286.7 |
| read_list,call:folder,palier:1400 | 15978 | 32.7 | 17.0 | 44.1 | 118.3 | 600.0 |
| read_list,call:folder,palier:1996 | 28621 | 43.8 | 25.5 | 76.4 | 132.4 | 607.1 |
| read_list,call:folder,palier:transition | 1165 | 88.0 | 73.0 | 181.6 | 230.0 | 614.3 |
| read_list,palier:1400 | 31956 | 48.0 | 44.5 | 85.4 | 111.3 | 600.0 |
| read_list,palier:1996 | 57242 | 70.9 | 58.7 | 136.2 | 168.7 | 751.0 |
| read_list,palier:transition | 2330 | 177.0 | 98.9 | 425.7 | 506.5 | 1286.7 |
| search | 16517 | 392.6 | 329.0 | 538.3 | 795.9 | 1867.0 |
| search,palier:1400 | 4811 | 365.8 | 310.2 | 463.8 | 648.6 | 1582.6 |
| search,palier:1996 | 8662 | 384.2 | 331.4 | 482.8 | 656.5 | 1810.6 |
| search,palier:transition | 408 | 457.2 | 363.4 | 729.6 | 943.2 | 1700.3 |
| send | 15696 | 653.3 | 525.0 | 932.9 | 970.3 | 1655.5 |
| send,palier:1400 | 4696 | 640.3 | 499.7 | 908.4 | 932.9 | 1171.1 |
| send,palier:1996 | 8529 | 631.9 | 494.1 | 931.6 | 963.6 | 1467.5 |
| send,palier:transition | 466 | 650.6 | 543.7 | 982.3 | 1044.8 | 1249.2 |
| treatment | 13574 | 119.9 | 91.7 | 177.5 | 287.2 | 6061.5 |
| treatment,palier:1400 | 3983 | 79.6 | 83.3 | 107.1 | 121.9 | 238.4 |
| treatment,palier:1996 | 7086 | 112.2 | 99.0 | 157.8 | 184.8 | 4021.3 |
| treatment,palier:transition | 294 | 236.7 | 132.0 | 489.5 | 641.4 | 1054.3 |
| warmup | 21956 | 904.7 | 297.1 | 906.6 | 5440.5 | 22671.0 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-10T14:05:14.542000+00:00 → 2026-11-10T14:42:52.545000+00:00 (2258 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t439-task.csv`) | ✅ 73787 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-52004` | 0.97 | 11 | 32 | 0.039 | 4.62 |
| `DESKTOP-DEV-X2C-53328` | 0.96 | 13 | 33 | 0.043 | 5.22 |
| `DESKTOP-DEV-X2C-58280` | 0.97 | 7 | 32 | 0.049 | 4.75 |
| `DESKTOP-DEV-X2C-67448` | 1.03 | 12 | 33 | 0.042 | 4.91 |
| `DESKTOP-DEV-X2C-68472` | 1.11 | 10 | 32 | 0.037 | 5.18 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#34920` | 0.01 | 0.17 | 40 |
| `com.docker.backend#35896` | 1.09 | 3.07 | 1936 |
| `dcp#17592` | 0.00 | 0.00 | 12 |
| `dcp#23460` | 0.00 | 0.00 | 12 |
| `dcp#2516` | 0.00 | 0.00 | 12 |
| `dcp#25180` | 0.00 | 0.00 | 12 |
| `dcp#2712` | 0.00 | 0.00 | 12 |
| `dcp#51944` | 0.00 | 0.00 | 12 |
| `dcp#52756` | 0.00 | 0.00 | 12 |
| `dcp#52796` | 0.00 | 0.00 | 13 |
| `dcp#53372` | 0.00 | 0.04 | 14 |
| `dcp#58968` | 0.00 | 0.00 | 13 |
| `dcp#59032` | 0.76 | 2.56 | 3163 |
| `dcp#59096` | 0.00 | 0.00 | 13 |
| `dcp#59396` | 0.00 | 0.25 | 54 |
| `dcp#63180` | 0.00 | 0.00 | 11 |
| `dcp#65540` | 0.00 | 0.04 | 13 |
| `k6#341767` | 0.79 | 1.75 | 2885 |
| `mss.mail.api#52004` | 0.65 | 1.55 | 2140 |
| `mss.mail.api#53328` | 0.68 | 2.26 | 2101 |
| `mss.mail.api#58280` | 0.68 | 2.21 | 2190 |
| `mss.mail.api#67448` | 0.67 | 2.38 | 2153 |
| `mss.mail.api#68472` | 0.71 | 2.54 | 2172 |
| `mss.mail.e2e#55184` | 0.01 | 0.21 | 31 |
| `vmmemWSL#35316` | 5.57 | 11.95 | 60154 |
| `loadtest-otel-collector-tfjbddxc` | 0.03 | 0.17 | 105 |
| `loadtest-pgbouncer-fzpebbvy` | 0.44 | 0.83 | 48 |
| `mss-mail-flagsmith-app-b6152948` | 0.13 | 0.47 | 557 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.13 | 161 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.08 | 123 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.09 | 254 |
| `mss-mail-rabbitmq-jtdkyeev` | 0.01 | 0.06 | 136 |
| `mss-mail-redis-b6152948` | 0.28 | 1.39 | 966 |
| `mss-mail-rediscommander-zawxwbdp` | 0.00 | 0.22 | 24 |
| `mss-mail-seq-b6152948` | 0.12 | 3.94 | 1441 |
| `postgres-pgvector` | 2.46 | 10.14 | 28365 |

- **Hôte** : CPU 70.1 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 44
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9379, cl_waiting max 21, cl_waiting_doctor_path max 21, cl_waiting_maintenance max 0, cl_waiting_practitioner max 21, cl_waiting_registry max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 0, maxwait_ms max 336, maxwait_practitioner_ms max 336, maxwait_registry_ms max 0, sv_active max 63, sv_idle max 1604, sv_login max 2, wait_us_delta_maintenance max 0, wait_us_delta_practitioner max 114430517, wait_us_delta_registry max 0, xact_delta_maintenance max 2, xact_delta_practitioner max 41071, xact_delta_registry max 0, xact_us_delta_maintenance max 0, xact_us_delta_practitioner max 481856055, xact_us_delta_registry max 0
- **Backends Postgres** : audit max 5, cache_mb max 46588, direct max 30, idle_over_60s max 205, majfault_per_s max 303, pooler max 1995, practitioner_databases max 1987, provision max 5, rss_mb max 5906, seconds max 0, started_last_60s max 331, total max 2026, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 15297.9 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2545.4 | 452 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 891.1 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 1146.6 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 748.5 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 855.9 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 690.9 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 988.0 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2181.2 | 433 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 415.8 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 614.1 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 423.7 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 1534.9 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 429.3 | 447 |

- **p95 client global (k6)** : 508.9 ms
- **p95 serveur le plus élevé** : 15297.9 ms
- **Écart** : -14789.0 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.36 |
| Documents CDA /s | 0.36 |
| Durée traitement CDA (s, p95) | 0.95 |
| Événements de session IMAP /s | 4.33 |
| Recherches (s, p95) | 1.100 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.0 | 81.5 | 240 | 0.1 (0.1 %), p95 5 | 45.5 (55.8 %), p95 160 | 36.0 (44.1 %), p95 220 |
| `GetMail` | 11.1 | 56.1 | 662 | 5.0 (9.0 %), p95 164 | 47.0 (83.8 %), p95 546 | 4.1 (7.2 %), p95 75 |
| `GetMailsByUids` | 14.7 | 75.0 | 668 | 0.1 (0.2 %), p95 5 | 63.2 (84.2 %), p95 615 | 11.8 (15.7 %), p95 74 |

- **`EnrichPersistMail`** — sur 81.5 ms en moyenne (8.0 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 45.5 ms exécution SQL, 36.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 56.1 ms en moyenne (11.1 requête(s) SQL par appel) : 5.0 ms attente d'une connexion, 47.0 ms exécution SQL, 4.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 75.0 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 63.2 ms exécution SQL, 11.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est l'attente du **pool Npgsql** seul ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **L'attente PgBouncer n'est pas dans `attente d'une connexion`** (task-435). En mode transaction, le pooler attribue un serveur à la première requête de chaque transaction : son attente est comptée dans `exécution SQL`. Son coût se lit dans « Coûts résidents » (« Attente PgBouncer cumulée — chemin du médecin »).

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 4.1 | 379.5 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.1 | 11.8 | 56.7 | 18.7 | 28.6 | 18.7 | 30.4 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 4.1 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **379.5 µs**.

- **`GetMailsByUids`** — sur 11.8 ms de matérialisation, l'appel a construit 207.1 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.4 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **56.7 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3899.1 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 317.6 | 950 | 130.9 (41.2 %), p95 243 | 12.4 (3.9 %), p95 160 | 56.6 (17.8 %), p95 700 | 58.9 (18.6 %), p95 235 | 58.8 (18.5 %), p95 235 |

- **Enrichir un message** — sur 317.6 ms en moyenne (3.8 message(s) par requête) : 130.9 ms fetch IMAP, 12.4 ms extraction XDM, 56.6 ms parsing CDA, 58.9 ms écritures base, 58.8 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **3.04 aller(s)-retour(s) IMAP par message enrichi** — 1.01 `fetch_whole_message`, 0.51 `open_folder`, 0.51 `resolve_folder`, 0.51 `fetch_bodystructure`, 0.50 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 223.6 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 639.2 | 1001 | 0.0 (0.0 %), p95 5 | 23.3 (3.6 %), p95 71 | 219.1 (34.3 %), p95 477 | 396.7 (62.1 %), p95 489 | 417.2 (65.3 %), p95 951 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 639.2 ms en moyenne : 0.0 ms garde d'opposition, 23.3 ms construction MIME, 219.1 ms obtention de session SMTP, 396.7 ms transmission + acquittement, 417.2 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.441 | 2.411 | 104.53 |
| `smtp_session` | 0.005 | 0.990 | 10.82 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.286 | 2.350 | 0.491 | 10.76 |
| `EnrichEmails` | 0.005 | 0.481 | — | 0.481 | 0.55 |
| `GetAttachmentStream` | 0.488 | 2.425 | 2.425 | 0.988 | 0.96 |
| `GetEmailContent` | 0.005 | 0.491 | — | 0.491 | 14.49 |
| `GetFolders` | 0.005 | 0.984 | 0.988 | 0.243 | 7.89 |
| `ReadFolder` | 0.757 | 2.411 | 2.411 | 0.491 | 37.64 |
| `ReadToday` | 0.005 | 0.621 | 2.425 | 0.621 | 7.67 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 27.84 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.388** | 0.462 | 0.481 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.662 | 0.712 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.490 | 0.490 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.431** | 0.439 | 0.446 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 104.53 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.757 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 21.00 clients | 0 clients | 100.0 % | 34.6 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 10.14 cœurs | 24 cœurs | 42.2 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 3.94 cœurs | 24 cœurs | 16.4 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-53328` | 13.00 éléments | 100 éléments | 13.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#68472` (CPU) | 2.54 cœurs | 24 cœurs | 10.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#67448` (CPU) | 2.38 cœurs | 24 cœurs | 9.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#53328` (CPU) | 2.26 cœurs | 24 cœurs | 9.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#58280` (CPU) | 2.21 cœurs | 24 cœurs | 9.2 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 34.6 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 166 337

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 1 701 |
| OpenAI | gpt-4o-mini | prompt | 164 636 |
| OpenAI | text-embedding-3-small | embedding | 297 977 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 84 | 0 (0.0 %) | 0 | 2.2 | 1.18 | 1.00 | 2.90 |
| étiquetage (chat) | OpenAI | 84 | 0 (0.0 %) | 0 | 2.2 | 1.11 | 0.92 | 2.90 |
| embedding | OpenAI | 84 | 0 (0.0 %) | 0 | 2.2 | 0.60 | 0.47 | 1.97 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 2 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 8.7 | 30.0 |
| GPU — VRAM occupée (Mo) | 2 036 | 2 535 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.7 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 563.2** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.32** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **4.0 ms** | sur 755 325 requêtes HTTP k6 |
| Taux de cache (blocs) | **97.55 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **10.70 Mo/s (1 369 blocs/s)** | attente disque : 17.1 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **244 906 / 33 168** | rapport 7.4 |
| Écritures de lignes / s (ins+upd+del) | **163.3** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.33 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 7 % |
| Sessions ouvertes / s | **3.16** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **51.7 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 559 / 2 026** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **11 / 27 / 152 ms** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **100 / 100 %** | fautes majeures/s max : 302.5 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 234.4 s | 9019 | `pages-par-ligne` | 108.8 pages par ligne rendue, 1305 par appel, 89.8 Go lus | `SemanticSearchRepository.FindFullTextMatchesAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Id", m1."Uid", m1."FolderPath", m."MatchedTerms" FROM ( SELECT h.mail_id AS "MailId", count(DISTINCT h.i)::i…` |
| 192.1 s | 165612 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, HtmlBody : 18.5 Go lus, 4.0 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 15.4 % du temps SQL, 38.1 % des lectures disque du tir | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 56.0 s | 9097 | `pages-par-ligne` | 32.0 pages par ligne rendue, 639 par appel, 44.4 Go lus | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 43.6 s | 165612 | `colonne-volumineuse` | sélectionne Body, BodyHtml : 6.8 Go lus, 0.3 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |
| 43.1 s | 9018 | `pages-par-ligne` | 31.9 pages par ligne rendue, 637 par appel, 43.8 Go lus | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 34.1 s | 15992 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Content : 2.9 Go lus, 1.8 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 2.7 % du temps SQL, 17.1 % des lectures disque du tir | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **82 évictions `pg_stat_statements`** pendant le tir (97 353 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

136 formes de requête, 5 965 959 appels, **20.8 min** de temps serveur cumulé — soit **1.7 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **18.7 %** | 19 % | 9 019 | 0.01 | 25.99 | 12.0 | 1 305 | 0 % | 0 | 904 | **Schéma** — ~109 blocs lus par ligne rendue : balayage probable — index sur le prédicat `WHERE`/`ORDER BY` (confirmer par `explain (analyze, buffers)`) | `SemanticSearchRepository.FindFullTextMatchesAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Id", m1."Uid", m1."FolderPath", m."MatchedTerms" FROM ( SELECT h.mail_id AS "MailId", count(DISTINCT h.i)::i…` |
| 2 | **15.4 %** | 34 % | 165 612 | 0.22 | 1.16 | 1.0 | 15 | 22 % | 0 | 1 882 | **Code** — 22 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 3 | **7.5 %** | 42 % | 88 383 | 0.12 | 1.06 | 18.1 | 104 | 1 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 4 | **5.8 %** | 47 % | 755 217 | 1.00 | 0.10 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `PostgresTenantRegistryClient.GetMailboxAsync` ← `GET /api/v1/Mail/folders/{foldername}` | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 5 | **4.5 %** | 52 % | 9 097 | 0.01 | 6.15 | 20.0 | 639 | 3 % | 0 | 911 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 6 | **3.7 %** | 56 % | 136 843 | 0.18 | 0.34 | 1.0 | 15 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 7 | **3.5 %** | 59 % | 165 612 | 0.22 | 0.26 | 1.0 | 5 | 4 % | 0 | 1 881 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |
| 8 | **3.5 %** | 62 % | 9 018 | 0.01 | 4.78 | 20.0 | 637 | 2 % | 0 | 904 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 9 | **3.3 %** | 66 % | 6 312 | 0.01 | 6.55 | 180.0 | 540 | 1 % | 0 | 1 088 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 10 | **2.7 %** | 69 % | 15 992 | 0.02 | 2.13 | 1.0 | 23 | 63 % | 0 | 1 282 | **Code** — 63 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 11 | **2.0 %** | 71 % | 279 591 | 0.37 | 0.09 | 2.1 | 4 | 0 % | 0 | 1 996 | — | `MailRepository.EnrichManyWithBiologyAcksAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 12 | **2.0 %** | 73 % | 279 494 | 0.37 | 0.09 | 1.3 | 17 | 0 % | 0 | 1 995 | — | `MailRepository.ResolveActiveDuplicateRefsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 13 | **1.9 %** | 74 % | 94 130 | 0.12 | 0.26 | 18.0 | 8 | 0 % | 0 | 1 655 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | site inconnu ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}`<br>`MailRepository.LoadMailsReferencingAnyRootAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 14 | **1.8 %** | 76 % | 88 384 | 0.12 | 0.26 | 18.1 | 19 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkMailLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT DISTINCT m."MailId" FROM "MailContents" AS m WHERE m."MailId" = ANY ($1)` |
| 15 | **1.4 %** | 78 % | 88 380 | 0.12 | 0.20 | 18.1 | 8 | 0 % | 0 | 1 996 | — | `MailRepository.GetMailsByUidsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 16 | **1.4 %** | 79 % | 35 838 | 0.05 | 0.48 | 1.0 | 9 | 6 % | 0 | 1 491 | — | `PendingActionRepository.AddAsync` ← `PUT /api/v1/Mail/folders/{foldername}/emails/{emailid}/status/read` | `INSERT INTO "PendingActions" ("Id", "ActionType", "ClaimedAt", "CreatedAt", "FolderPath", "LastError", "MailUid", "Payl…` |
| 17 | **1.2 %** | 80 % | 186 110 | 0.25 | 0.08 | 2.1 | 3 | 0 % | 0 | 1 903 | — | `MailRepository.GetMailAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`, `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."FileName", m."ContentType", m."Size" FROM "MailAttachments" AS m WHERE m."MailId" = $1` |
| 18 | **1.2 %** | 81 % | 44 914 | 0.06 | 0.33 | 27.0 | 8 | 0 % | 0 | 1 400 | — | `MailRepository.GetLatestMessageIdsPerThreadAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **1.1 %** | 83 % | 143 339 | 0.19 | 0.10 | 14.0 | 8 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **1.1 %** | 84 % | 143 337 | 0.19 | 0.10 | 20.8 | 8 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 93.5 % | 87.4 % |
| INSERT | 5.4 % | 2.9 % |
| UPDATE | 0.5 % | 1.3 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.5 % | 7.8 % |
| bases : praticien (N bases) | 89.7 % | 82.1 % |
| bases : unique (1 base) | 10.3 % | 17.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **26.0** | 521 | 9 019 | 18.7 % | `SELECT m1."Id", m1."Uid", m1."FolderPath", m."MatchedTerms" FROM ( SELECT h.mail_id AS "MailId", co…` |
| **6.5** | 191 | 6 312 | 3.3 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **6.2** | 344 | 9 097 | 4.5 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **4.8** | 259 | 9 018 | 3.5 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |
| **2.1** | 524 | 15 992 | 2.7 % | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m.…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 066 | 126 854 | 0 | 0 | 0.1 Mo |
| `Mails` | 463 | 69 621 | 800 | 0 | 0.2 Mo |
| `MailTags` | 165 | 40 920 | 56 | 0 | 0.1 Mo |
| `MailRecipients` | 148 | 23 088 | 40 | 0 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 147 | 21 255 | 1 194 | 0 | 9.7 Mo |
| `MailAttachments` ⚠️ index candidat | 67 | 17 487 | 190 | 0 | 30.1 Mo |
| `MailContents` ⚠️ index candidat | 53 | 8 268 | 1 732 | 0 | 3.4 Mo |
| `PendingActions` | 120 | 3 549 | 0 | 31 | 0.1 Mo |
| `Tags` | 111 | 1 998 | 79 | 0 | 0.0 Mo |
| `MailFolders` | 310 | 850 | 337 | 4 | 0.1 Mo |

Index **non sollicités** pendant le tir sur des tables pourtant lues (≥ 1 Mo) :

| Index | Table | Taille |
|---|---|---|
| `IX_MailMedicalDocuments_SearchText` | `MailMedicalDocuments` | 1.3 Mo |
| `IX_MailContents_SearchText` | `MailContents` | 1.2 Mo |

Un index jamais lu coûte à chaque écriture ; un tir n'exerce pas toutes les routes — confirmer sur `pg_stat_user_indexes` d'une journée réelle avant de supprimer.

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Code | 🟠 | requête n°2 (15.4 % du temps SQL) — 22 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟠 | requête n°4 (5.8 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 97.5 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | requête n°1 (18.7 % du temps SQL) — ~109 blocs lus par ligne rendue : balayage probable — index sur le prédicat `WHERE`/`ORDER BY` (confirmer par `explain (analyze, buffers)`) |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 147 fois (21255 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 67 fois (17487 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 53 fois (8268 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°10 (2.7 % du temps SQL) — 63 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°9 (3.3 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°5 (4.5 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°13 (1.9 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Schéma | 🟡 | index `IX_MailMedicalDocuments_SearchText` (1.3 Mo, table `MailMedicalDocuments`) jamais sollicité pendant le tir : candidat à la suppression si une journée réelle confirme (coût à chaque écriture) |
| Schéma | 🟡 | index `IX_MailContents_SearchText` (1.2 Mo, table `MailContents`) jamais sollicité pendant le tir : candidat à la suppression si une journée réelle confirme (coût à chaque écriture) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-154334.tsv`, `pgserver-journey-debut-150501.tsv`, `pgserver-journey-fin-154341.tsv`, `pgtables-journey-debut-150508.tsv`, `pgtables-journey-fin-154347.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 248600 — dont **248600** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261110-t439-task-154252.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
