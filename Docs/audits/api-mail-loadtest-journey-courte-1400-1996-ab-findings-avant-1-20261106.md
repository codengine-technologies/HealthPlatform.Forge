# Rapport de tir — journey-courte-1400-1996-20261106-avant-1

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261106-avant-1-184039.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1996 médecins, 2 étape(s) dépassent le temps de réponse attendu : « Ouvrir un message enrichi (servi base) », « Recherche »
- 10 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 28 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.011 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 743709 — **débit émergent global** : 328.9 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 52671 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 328.9 | **259.1** | 118.7 | **873.5** | — | 19366.2 | 0.01 | 100.0 | 0 | 0 | 244252/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 212485 | 288.31 | 0.00 | 826.3 |
| **1996 médecins** | 1080 | 933 | 379242 | 406.48 | 0.01 | 1391.4 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 71 / 556 (n=63348) | 133 / 748 (n=112384) |
| 2 | Ouvrir / rafraîchir l'inbox | 52 / 129 (n=31706) | 137 / 478 (n=56098) |
| 3 | Ouvrir un message enrichi (servi base) | 48 / 103 (n=15850) | 147 / 440 (n=28051) |
| 4 | Ouvrir un message froid (fetch IMAP) | 457 / 526 (n=6370) | 513 / 761 (n=11365) |
| 5 | Recherche | 414 / 672 (n=4802) | 563 / 1219 (n=8407) |
| 6 | Envoi (acquittement UI) | 516 / 941 (n=4738) | 642 / 1134 (n=8335) |
| 7 | Télécharger une PJ (~124 Ko) | 53 / 124 (n=6377) | 170 / 777 (n=11195) |
| 8 | Marquer lu | 54 / 110 (n=12629) | 136 / 435 (n=22608) |
| 9 | Rechercher un patient | 63 / 87 (n=4762) | 87 / 328 (n=8490) |
| 10 | Ouvrir la page d'un dossier patient | 70 / 162 (n=7147) | 180 / 578 (n=12846) |
| 11 | Fiche patient complète (ressenti médecin) | 391 / 727 (n=3573) | 907 / 2915 (n=6423) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.2 / 20 | 33.7 / 60 | 7846 | 727 |
| **1996 médecins** | 14.4 / 20 | 33.9 / 60 | 14182 | 2915 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2201 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 1060 ms en moyenne, 19366 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2221 / 3039 (magasin) | 2221 / 3039 (magasin) |
| Backends Postgres (moy/max) | 1238 / 1432 | 1988 / 2029 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 2 | 0 / 2 |
| PgBouncer `cl_waiting` (échant. non nuls) | 47/170 (28 %) ⚠️ soutenu | 76/130 (58 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/170 (0 %) | 0/130 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 47/170 (28 %) | 76/130 (58 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 84.2 | 215.3 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 84.2 | 215.3 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 121 / 341 | 91 / 256 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 108 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1401 | 1998 |
| Backends **directs** — audit + provisionnement (max) | 30 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 90.3 | 98.3 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 10 / 57 | 18 / 48 |
| RSS par réplica api-mail, Mo (moy/max) | 1186 / 1650 (5 réplicas) | 2127 / 2431 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1432.0 / 2500** (57.3 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2029.0 / 2500** (81.2 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 99.9 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15850)
- palier 1996 : cohorte 1996 chauffée à 99.8 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28051)

> ⓘ Chauffe : **308 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **29 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 71 (300) | 556 (1500) | 63348 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 52 (300) | 129 (1000) | 31706 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 48 (100) | 103 (500) | 15850 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 457 (800) | 526 (2500) | 6370 | ✅ |
| 5 | Recherche | 414 (500) | 672 (2000) | 4802 | ✅ |
| 6 | Envoi (acquittement UI) | 516 (1000) | 941 (3000) | 4738 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 53 (500) | 124 (2000) | 6377 | ✅ |
| 8 | Marquer lu | 54 (200) | 110 (1000) | 12629 | ✅ |
| 9 | Rechercher un patient | 63 (300) | 87 (1500) | 4762 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 70 (500) | 162 (2000) | 7147 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 391 (1500) | 727 (4000) | 3573 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 133 (300) | 748 (1500) | 112384 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 137 (300) | 478 (1000) | 56098 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 147 (100) | 440 (500) | 28051 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 513 (800) | 761 (2500) | 11365 | ✅ |
| 5 | Recherche | 563 (500) | 1219 (2000) | 8407 | ❌ |
| 6 | Envoi (acquittement UI) | 642 (1000) | 1134 (3000) | 8335 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 170 (500) | 777 (2000) | 11195 | ✅ |
| 8 | Marquer lu | 136 (200) | 435 (1000) | 22608 | ✅ |
| 9 | Rechercher un patient | 87 (300) | 328 (1500) | 8490 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 180 (500) | 578 (2000) | 12846 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 907 (1500) | 2915 (4000) | 6423 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 112384 | 237 | 748 | 26682.8 | 37.2 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 56098 | 182 | 478 | 10189.2 | 14.2 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11365 | 545 | 761 | 6196.3 | 8.6 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8335 | 734 | 1134 | 6119.4 | 8.5 % |
| 🟠 | Recherche (`search`) | 8407 | 638 | 1219 | 5365.2 | 7.5 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 28051 | 184 | 440 | 5159.6 | 7.2 % |
| 🟠 | Marquer lu (`mark_read`) | 22608 | 178 | 435 | 4024.9 | 5.6 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 11195 | 248 | 777 | 2777.5 | 3.9 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 7091 | 268 | 851 | 1901.0 | 2.6 % |
| 🟠 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6423 | 233 | 578 | 1494.6 | 2.1 % |
| 🟠 | Rechercher un patient (`patient_search`) | 8490 | 123 | 328 | 1045.5 | 1.5 % |
| 🟠 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6423 | 127 | 328 | 813.4 | 1.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 10 🟠 · 2 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 26682.8 s, 37.2 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 5.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 10189.2 s, 14.2 %)
  - **dispersion p95/p50 = 3.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 5365.2 s, 7.5 %)
  - **hors grille** — le médecin attend trop
- **Ouvrir un message enrichi (servi base)** (`read_content`, 5159.6 s, 7.2 %)
  - **hors grille** — le médecin attend trop
- **Marquer lu** (`mark_read`, 4024.9 s, 5.6 %)
  - **dispersion p95/p50 = 3.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 2777.5 s, 3.9 %)
  - **dispersion p95/p50 = 4.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 1901.0 s, 2.6 %)
  - **dispersion p95/p50 = 4.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 1494.6 s, 2.1 %)
  - **dispersion p95/p50 = 3.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Rechercher un patient** (`patient_search`, 1045.5 s, 1.5 %)
  - **dispersion p95/p50 = 3.8×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_opposition`, 813.4 s, 1.1 %)
  - **dispersion p95/p50 = 3.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15837 | 394 | 972 | 6172.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15837 | 70 | 509 | 2346.4 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15837 | 35 | 179 | 955.4 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15837 | 66 | 92 | 1086.4 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15853 | 26 | 127 | 658.7 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15853 | 68 | 130 | 1204.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28096 | 425 | 1053 | 12705.7 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28096 | 112 | 595 | 6025.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28096 | 103 | 400 | 4326.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28096 | 94 | 328 | 3624.9 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28049 | 79 | 430 | 3535.7 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28049 | 198 | 518 | 6653.5 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (1053 ms de p95, 425 ms de p50, n=28096), qui porte **aussi** le temps serveur de l'étape (12705.7 s, 48 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (518 ms de p95, 198 ms de p50, n=28049), qui porte **aussi** le temps serveur de l'étape (6653.5 s, 65 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21427 | 224.9 | 112.5 | 564.2 | 831.2 | 3577.7 |
| attachment,palier:1400 | 6377 | 70.7 | 52.6 | 96.7 | 124.4 | 1145.2 |
| attachment,palier:1996 | 11195 | 248.1 | 170.0 | 549.9 | 776.6 | 3036.8 |
| attachment,palier:transition | 605 | 373.8 | 183.3 | 978.4 | 1211.5 | 1804.9 |
| dashboard | 215248 | 255.2 | 117.1 | 601.1 | 838.4 | 3688.9 |
| dashboard,call:coverage,palier:1400 | 15837 | 68.6 | 66.0 | 83.3 | 91.9 | 238.6 |
| dashboard,call:coverage,palier:1996 | 28096 | 129.0 | 94.3 | 212.0 | 327.8 | 1962.6 |
| dashboard,call:coverage,palier:transition | 1008 | 372.0 | 258.8 | 842.9 | 1061.4 | 1427.0 |
| dashboard,call:folder,palier:1400 | 15837 | 389.8 | 394.0 | 765.4 | 972.4 | 1563.4 |
| dashboard,call:folder,palier:1996 | 28096 | 452.2 | 424.7 | 819.4 | 1053.1 | 2627.4 |
| dashboard,call:folder,palier:transition | 1008 | 702.4 | 588.3 | 1258.3 | 1425.8 | 2191.1 |
| dashboard,call:folders,palier:1400 | 15837 | 60.3 | 34.7 | 162.3 | 179.5 | 312.3 |
| dashboard,call:folders,palier:1996 | 28096 | 154.0 | 103.3 | 298.9 | 399.7 | 2086.0 |
| dashboard,call:folders,palier:transition | 1008 | 404.9 | 283.3 | 939.0 | 1167.7 | 1615.2 |
| dashboard,call:today,palier:1400 | 15837 | 148.2 | 70.0 | 486.9 | 508.9 | 788.2 |
| dashboard,call:today,palier:1996 | 28096 | 214.5 | 111.8 | 539.0 | 594.7 | 2430.9 |
| dashboard,call:today,palier:transition | 1008 | 597.6 | 563.4 | 1093.4 | 1251.3 | 1825.7 |
| dashboard,palier:1400 | 63348 | 166.7 | 71.0 | 461.4 | 555.5 | 1563.4 |
| dashboard,palier:1996 | 112384 | 237.4 | 133.1 | 530.4 | 748.0 | 2627.4 |
| dashboard,palier:transition | 4032 | 519.2 | 489.7 | 1062.6 | 1248.8 | 2191.1 |
| mark_read | 42913 | 172.5 | 98.2 | 311.4 | 557.6 | 3245.0 |
| mark_read,palier:1400 | 12629 | 61.9 | 54.5 | 97.3 | 109.8 | 266.1 |
| mark_read,palier:1996 | 22608 | 178.0 | 136.0 | 309.3 | 434.6 | 2046.5 |
| mark_read,palier:transition | 1169 | 266.2 | 98.2 | 768.2 | 979.8 | 1437.5 |
| patient_docs | 173657 | 181.2 | 103.3 | 361.4 | 571.4 | 4155.9 |
| patient_docs,palier:1400 | 50833 | 66.3 | 58.5 | 117.4 | 140.3 | 514.5 |
| patient_docs,palier:1996 | 92363 | 192.7 | 153.3 | 359.1 | 464.6 | 2150.6 |
| patient_docs,palier:transition | 4605 | 278.0 | 106.8 | 812.0 | 1042.9 | 1867.3 |
| patient_dossier | 12124 | 218.1 | 126.6 | 429.3 | 693.4 | 3965.9 |
| patient_dossier,palier:1400 | 3573 | 79.4 | 70.4 | 134.7 | 161.7 | 339.3 |
| patient_dossier,palier:1996 | 6423 | 232.7 | 179.5 | 426.9 | 578.3 | 2007.0 |
| patient_dossier,palier:transition | 312 | 342.3 | 118.9 | 1001.1 | 1251.2 | 1765.5 |
| patient_opposition | 12124 | 137.8 | 78.2 | 211.0 | 439.1 | 2706.9 |
| patient_opposition,palier:1400 | 3574 | 67.9 | 65.7 | 82.3 | 89.3 | 174.3 |
| patient_opposition,palier:1996 | 6423 | 126.6 | 91.3 | 209.2 | 327.7 | 1860.8 |
| patient_opposition,palier:transition | 312 | 232.8 | 78.3 | 624.2 | 952.1 | 1375.2 |
| patient_search | 16120 | 133.4 | 71.7 | 209.0 | 447.1 | 2910.3 |
| patient_search,palier:1400 | 4762 | 55.5 | 63.1 | 79.4 | 86.8 | 200.2 |
| patient_search,palier:1996 | 8490 | 123.1 | 87.1 | 209.3 | 327.9 | 1881.0 |
| patient_search,palier:transition | 424 | 222.6 | 77.3 | 654.1 | 928.0 | 1291.1 |
| read_content | 53812 | 169.6 | 96.2 | 327.5 | 536.2 | 3574.5 |
| read_content,palier:1400 | 15850 | 55.2 | 48.0 | 85.4 | 102.8 | 270.3 |
| read_content,palier:1996 | 28051 | 183.9 | 146.7 | 326.5 | 439.8 | 1979.1 |
| read_content,palier:transition | 1190 | 309.5 | 121.4 | 819.2 | 1122.7 | 1601.3 |
| read_content_cold | 21667 | 544.5 | 488.5 | 647.6 | 865.9 | 3393.3 |
| read_content_cold,palier:1400 | 6370 | 459.0 | 457.1 | 508.6 | 525.6 | 639.3 |
| read_content_cold,palier:1996 | 11365 | 545.2 | 513.0 | 652.7 | 761.3 | 2317.7 |
| read_content_cold,palier:transition | 565 | 653.1 | 503.8 | 1125.9 | 1325.4 | 1838.6 |
| read_list | 107624 | 174.5 | 88.0 | 374.4 | 586.9 | 3596.9 |
| read_list,call:emails,palier:1400 | 15853 | 76.0 | 67.9 | 111.4 | 129.8 | 371.9 |
| read_list,call:emails,palier:1996 | 28049 | 237.2 | 198.4 | 402.3 | 517.9 | 2164.5 |
| read_list,call:emails,palier:transition | 1122 | 423.5 | 242.9 | 1032.4 | 1327.4 | 1662.0 |
| read_list,call:folder,palier:1400 | 15853 | 41.6 | 25.8 | 63.8 | 126.5 | 523.4 |
| read_list,call:folder,palier:1996 | 28049 | 126.1 | 78.6 | 253.1 | 430.2 | 2056.0 |
| read_list,call:folder,palier:transition | 1122 | 275.2 | 120.5 | 752.6 | 1046.5 | 1623.6 |
| read_list,palier:1400 | 31706 | 58.8 | 51.8 | 104.4 | 128.6 | 523.4 |
| read_list,palier:1996 | 56098 | 181.6 | 137.1 | 359.0 | 477.7 | 2164.5 |
| read_list,palier:transition | 2244 | 349.4 | 161.9 | 941.6 | 1190.6 | 1662.0 |
| search | 16100 | 615.8 | 503.5 | 971.6 | 1405.7 | 3960.9 |
| search,palier:1400 | 4802 | 458.2 | 413.5 | 565.3 | 672.2 | 1703.1 |
| search,palier:1996 | 8407 | 638.2 | 562.6 | 908.6 | 1219.4 | 2751.5 |
| search,palier:transition | 458 | 738.0 | 525.2 | 1459.9 | 1616.2 | 2582.1 |
| send | 15395 | 749.6 | 769.5 | 1042.5 | 1214.1 | 3884.2 |
| send,palier:1400 | 4738 | 651.0 | 516.1 | 920.0 | 941.1 | 1106.2 |
| send,palier:1996 | 8335 | 734.2 | 641.8 | 1046.6 | 1133.6 | 2771.7 |
| send,palier:transition | 432 | 817.5 | 833.0 | 1374.2 | 1601.6 | 2262.7 |
| treatment | 13528 | 232.1 | 138.2 | 451.7 | 831.6 | 3777.5 |
| treatment,palier:1400 | 3923 | 94.2 | 91.1 | 128.9 | 149.6 | 3734.1 |
| treatment,palier:1996 | 7091 | 268.1 | 194.0 | 479.0 | 851.0 | 3777.5 |
| treatment,palier:transition | 276 | 381.7 | 170.7 | 872.8 | 1048.2 | 2098.9 |
| warmup | 21956 | 1060.3 | 410.9 | 2039.3 | 4637.0 | 19366.2 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-06T17:02:58.290000+00:00 → 2026-11-06T17:40:39.512000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-avant-1.csv`) | ✅ 68789 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-24784` | 1.32 | 16 | 31 | 0.038 | 5.06 |
| `DESKTOP-DEV-X2C-42844` | 0.97 | 8 | 21 | 0.029 | 4.33 |
| `DESKTOP-DEV-X2C-46212` | 1.26 | 11 | 33 | 0.035 | 4.95 |
| `DESKTOP-DEV-X2C-48260` | 0.99 | 10 | 34 | 0.033 | 4.93 |
| `DESKTOP-DEV-X2C-49108` | 0.99 | 8 | 30 | 0.033 | 5.16 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.58 | 3.88 | 1898 |
| `com.docker.backend#34124` | 0.01 | 0.45 | 39 |
| `dcp#24820` | 0.00 | 0.04 | 12 |
| `dcp#25240` | 0.00 | 0.00 | 12 |
| `dcp#30608` | 0.00 | 0.00 | 11 |
| `dcp#38252` | 0.00 | 0.04 | 13 |
| `dcp#38984` | 0.00 | 0.09 | 51 |
| `dcp#47604` | 0.00 | 0.00 | 12 |
| `dcp#48700` | 0.83 | 2.11 | 3216 |
| `dcp#50340` | 0.00 | 0.00 | 12 |
| `dcp#51568` | 0.00 | 0.00 | 12 |
| `dcp#54084` | 0.00 | 0.04 | 14 |
| `dcp#63484` | 0.00 | 0.00 | 12 |
| `dcp#63688` | 0.00 | 0.04 | 14 |
| `dcp#63864` | 0.00 | 0.00 | 12 |
| `dcp#64072` | 0.00 | 0.00 | 12 |
| `dcp#65196` | 0.00 | 0.09 | 14 |
| `k6#98519` | 0.85 | 1.83 | 2885 |
| `mss.mail.api#24784` | 0.88 | 3.21 | 2453 |
| `mss.mail.api#42844` | 0.68 | 2.16 | 2214 |
| `mss.mail.api#46212` | 0.90 | 3.34 | 2406 |
| `mss.mail.api#48260` | 0.71 | 3.28 | 2382 |
| `mss.mail.api#49108` | 0.75 | 2.89 | 2238 |
| `mss.mail.e2e#54396` | 0.01 | 0.14 | 33 |
| `vmmemWSL#36464` | 7.32 | 13.05 | 59325 |
| `loadtest-otel-collector-fdpsmnaw` | 0.03 | 0.18 | 100 |
| `loadtest-pgbouncer-yyrtstyw` | 0.56 | 0.90 | 52 |
| `mss-mail-flagsmith-app-b6152948` | 0.13 | 0.48 | 567 |
| `mss-mail-flagsmith-db-b6152948` | 0.01 | 0.59 | 196 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.06 | 164 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.11 | 170 |
| `mss-mail-rabbitmq-weznupua` | 0.01 | 0.07 | 160 |
| `mss-mail-redis-b6152948` | 0.30 | 1.36 | 974 |
| `mss-mail-rediscommander-fzdajzeh` | 0.00 | 0.21 | 58 |
| `mss-mail-seq-b6152948` | 0.12 | 0.94 | 22589 |
| `postgres-pgvector` | 3.64 | 8.72 | 45855 |

- **Hôte** : CPU 79.2 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 56
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9362, cl_waiting max 22, cl_waiting_maintenance max 22, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 215, maxwait_ms max 215, maxwait_practitioner_ms max 0, sv_active max 144, sv_idle max 1638, sv_login max 2
- **Backends Postgres** : audit max 5, cache_mb max 38626, direct max 30, idle_over_60s max 200, majfault_per_s max 57, pooler max 1998, practitioner_databases max 1989, provision max 5, rss_mb max 5808, started_last_60s max 341, total max 2029, usage_pct max 99

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 11360.7 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 3764.5 | 450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 2413.5 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 3279.4 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 2452.2 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 2481.4 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 2459.1 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2436.6 | 447 |
| `api/v{version:apiVersion}/Mail/sendmail` | 4307.8 | 434 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 2428.6 | 444 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 3392.0 | 444 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 2364.1 | 444 |
| `api/v{version:apiVersion}/Search/semantic` | 4399.0 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 2394.4 | 447 |

- **p95 client global (k6)** : 873.5 ms
- **p95 serveur le plus élevé** : 11360.7 ms
- **Écart** : -10487.2 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 2.33 |
| Documents CDA /s | 2.35 |
| Durée traitement CDA (s, p95) | 0.69 |
| Événements de session IMAP /s | 4.00 |
| Recherches (s, p95) | 2.030 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.0 | 113.4 | 488 | 0.0 (0.0 %), p95 5 | 67.7 (59.7 %), p95 242 | 45.6 (40.2 %), p95 235 |
| `GetMail` | 11.1 | 76.0 | 481 | 6.4 (8.5 %), p95 81 | 65.6 (86.3 %), p95 460 | 4.0 (5.2 %), p95 136 |
| `GetMailsByUids` | 14.7 | 97.4 | 682 | 0.1 (0.1 %), p95 5 | 84.8 (87.0 %), p95 634 | 12.5 (12.8 %), p95 48 |

- **`EnrichPersistMail`** — sur 113.4 ms en moyenne (8.0 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 67.7 ms exécution SQL, 45.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 76.0 ms en moyenne (11.1 requête(s) SQL par appel) : 6.4 ms attente d'une connexion, 65.6 ms exécution SQL, 4.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 97.4 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 84.8 ms exécution SQL, 12.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 4.0 | 372.3 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.0 | 12.5 | 60.4 | 18.7 | 28.6 | 18.7 | 30.4 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 4.0 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **372.3 µs**.

- **`GetMailsByUids`** — sur 12.5 ms de matérialisation, l'appel a construit 207.0 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.4 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **60.4 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3659.7 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 341.5 | 2275 | 131.1 (38.4 %), p95 243 | 8.4 (2.5 %), p95 205 | 40.1 (11.7 %), p95 712 | 89.1 (26.1 %), p95 475 | 72.7 (21.3 %), p95 243 |

- **Enrichir un message** — sur 341.5 ms en moyenne (3.8 message(s) par requête) : 131.1 ms fetch IMAP, 8.4 ms extraction XDM, 40.1 ms parsing CDA, 89.1 ms écritures base, 72.7 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **3.03 aller(s)-retour(s) IMAP par message enrichi** — 1.01 `fetch_whole_message`, 0.51 `resolve_folder`, 0.51 `fetch_bodystructure`, 0.50 `close_folder`, 0.50 `open_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 279.6 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 653.3 | 991 | 0.0 (0.0 %), p95 5 | 33.9 (5.2 %), p95 107 | 221.9 (34.0 %), p95 477 | 397.2 (60.8 %), p95 489 | 412.2 (63.1 %), p95 944 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 653.3 ms en moyenne : 0.0 ms garde d'opposition, 33.9 ms construction MIME, 221.9 ms obtention de session SMTP, 397.2 ms transmission + acquittement, 412.2 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.437 | 2.425 | 99.13 |
| `smtp_session` | 0.005 | 0.988 | 10.02 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.275 | 2.323 | 0.493 | 10.15 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 3.49 |
| `GetAttachmentStream` | 0.483 | 2.281 | 2.425 | 0.800 | 2.84 |
| `GetEmailContent` | 0.005 | 0.495 | — | 0.495 | 14.20 |
| `GetFolders` | 0.005 | 0.983 | 1.954 | 0.244 | 7.73 |
| `ReadFolder` | 0.499 | 2.425 | 2.425 | 0.490 | 40.35 |
| `ReadToday` | 0.005 | 0.500 | 0.742 | 0.500 | 7.64 |
| `UpdateFlag` | 0.005 | 0.490 | — | 0.490 | 26.27 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.489 | 0.0 % |
| `EnrichEmails` | **0.400** | 0.443 | 0.458 | 0.0 % |
| `GetAttachmentStream` | **0.496** | 0.600 | 0.787 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.490 | 0.490 | 0.0 % |
| `GetFolders` | **0.242** | 0.243 | 0.244 | 0.0 % |
| `ReadFolder` | **0.430** | 0.440 | 0.441 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.492 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.488 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 99.13 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.499 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 22.00 clients | 0 clients | 100.0 % | 40.4 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.72 cœurs | 24 cœurs | 36.3 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-24784` | 16.00 éléments | 100 éléments | 16.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#46212` (CPU) | 3.34 cœurs | 24 cœurs | 13.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#48260` (CPU) | 3.28 cœurs | 24 cœurs | 13.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#24784` (CPU) | 3.21 cœurs | 24 cœurs | 13.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#49108` (CPU) | 2.89 cœurs | 24 cœurs | 12.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#42844` (CPU) | 2.16 cœurs | 24 cœurs | 9.0 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 40.4 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 1 310 205

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 15 520 |
| OpenAI | gpt-4o-mini | prompt | 1 294 685 |
| OpenAI | text-embedding-3-small | embedding | 1 932 348 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 678 | 0 (0.0 %) | 0 | 18.0 | 1.11 | 0.98 | 2.43 |
| étiquetage (chat) | OpenAI | 678 | 0 (0.0 %) | 0 | 18.0 | 1.05 | 0.93 | 2.42 |
| embedding | OpenAI | 678 | 0 (0.0 %) | 0 | 18.0 | 0.58 | 0.51 | 1.52 |

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
| GPU — utilisation (%) | 0.9 | 16.0 |
| GPU — VRAM occupée (Mo) | 1 820 | 1 848 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **6 741.0** | annulées : 0.0 % |
| Backends actifs (équivalent) | **2.66** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **8.3 ms** | sur 743 709 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.64 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **19.90 Mo/s (2 548 blocs/s)** | attente disque : 14.0 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **751 489 / 42 136** | rapport 17.8 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **215.5** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.40 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 33 % |
| Sessions ouvertes / s | **2.82** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **280.7 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 543 / 2 029** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **92 / 99 %** | fautes majeures/s max : 56.8 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **82 évictions `pg_stat_statements`** pendant le tir (99 833 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

134 formes de requête, 15 628 258 appels, **52.4 min** de temps serveur cumulé — soit **4.2 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **25.4 %** | 25 % | 46 653 | 0.06 | 17.12 | 32.3 | 274 | 0 % | 0 | 1 971 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 2 | **24.4 %** | 50 % | 46 680 | 0.06 | 16.42 | 32.3 | 320 | 1 % | 0 | 1 973 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 3 | **7.5 %** | 57 % | 164 831 | 0.22 | 1.44 | 1.0 | 18 | 24 % | 0 | 1 893 | **Postgres** — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **4.4 %** | 62 % | 86 768 | 0.12 | 1.59 | 18.0 | 212 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **3.9 %** | 66 % | 2 203 380 | 2.96 | 0.06 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 6 | **3.2 %** | 69 % | 5 296 486 | 7.12 | 0.02 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 7 | **3.2 %** | 72 % | 3 966 | 0.01 | 25.36 | 28.7 | 442 | 37 % | 0 | 540 | **Postgres** — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 8 | **3.0 %** | 75 % | 2 203 381 | 2.96 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 9 | **2.4 %** | 77 % | 46 083 | 0.06 | 1.67 | 10.1 | 248 | 0 % | 0 | 1 428 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 10 | **2.3 %** | 80 % | 8 410 | 0.01 | 8.66 | 20.0 | 616 | 4 % | 0 | 928 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 11 | **1.8 %** | 82 % | 164 133 | 0.22 | 0.35 | 1.0 | 8 | 2 % | 0 | 1 885 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 12 | **1.8 %** | 83 % | 8 379 | 0.01 | 6.84 | 20.0 | 618 | 3 % | 0 | 925 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 13 | **1.6 %** | 85 % | 743 630 | 1.00 | 0.07 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 14 | **1.3 %** | 86 % | 130 137 | 0.17 | 0.32 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 15 | **1.2 %** | 88 % | 5 771 | 0.01 | 6.58 | 178.0 | 540 | 1 % | 0 | 998 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 16 | **1.2 %** | 89 % | 15 735 | 0.02 | 2.36 | 1.0 | 22 | 53 % | 0 | 1 266 | **Postgres** — 53 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 17 | **1.0 %** | 90 % | 276 209 | 0.37 | 0.11 | 2.0 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 18 | **0.9 %** | 91 % | 276 211 | 0.37 | 0.10 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 19 | **0.8 %** | 91 % | 90 949 | 0.12 | 0.27 | 18.0 | 5 | 0 % | 0 | 1 507 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **0.5 %** | 92 % | 183 796 | 0.25 | 0.09 | 3.2 | 8 | 0 % | 0 | 1 901 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.4 % | 61.5 % |
| INSERT | 2.0 % | 1.1 % |
| UPDATE | 0.2 % | 0.5 % |
| DELETE | 0.1 % | 0.2 % |
| AUTRE | 3.4 % | 36.7 % |
| bases : praticien (N bases) | 89.9 % | 65.2 % |
| bases : unique (1 base) | 10.1 % | 34.8 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **25.4** | 895 | 3 966 | 3.2 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **17.1** | 1 314 | 46 653 | 25.4 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailCo…` |
| **16.4** | 1 879 | 46 680 | 24.4 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMe…` |
| **8.7** | 334 | 8 410 | 2.3 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **6.8** | 275 | 8 379 | 1.8 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 869 | 215 512 | 186 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 179 | 140 301 | 0 | 5 | 0.1 Mo |
| `Mails` | 741 | 93 391 | 741 | 26 | 0.1 Mo |
| `MailRecipients` | 169 | 26 364 | 0 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 167 | 24 851 | 1 201 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 92 | 24 012 | 197 | 43 | 30.0 Mo |
| `MailContents` ⚠️ index candidat | 62 | 9 672 | 1 922 | 156 | 1.9 Mo |
| `PendingActions` | 144 | 4 260 | 0 | 31 | 0.1 Mo |
| `Tags` | 126 | 2 268 | 86 | 0 | 0.0 Mo |
| `MailFolders` | 344 | 922 | 323 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🔴 | requête n°1 (25.4 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Postgres | 🟠 | taux de cache 96.6 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°3 (7.5 % du temps SQL) — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 18 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 167 fois (24851 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 92 fois (24012 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 62 fois (9672 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°5 (3.9 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°6 (3.2 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Infra | 🟡 | requête n°15 (1.2 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Postgres | 🟡 | 33 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | requête n°7 (3.2 % du temps SQL) — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Postgres | 🟡 | requête n°16 (1.2 % du temps SQL) — 53 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°10 (2.3 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-184121.tsv`, `pgserver-journey-debut-180245.tsv`, `pgserver-journey-fin-184125.tsv`, `pgtables-journey-debut-180252.tsv`, `pgtables-journey-fin-184131.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 244252 — dont **244252** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261106-avant-1-184039.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
