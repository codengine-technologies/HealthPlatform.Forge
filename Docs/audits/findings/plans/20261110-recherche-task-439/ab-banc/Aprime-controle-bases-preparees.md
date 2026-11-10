# Rapport de tir — journey-courte-1400-1996-20261110-t439-controle-bis

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261110-t439-controle-bis-163349.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 2 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** sur le chemin du médecin (`cl_waiting` non nul sur 21 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.022 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 756499 — **débit émergent global** : 335.0 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53819 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 335.0 | **148.4** | 62.5 | **517.4** | — | 9302.8 | 0.02 | 100.0 | 0 | 0 | 248728/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 212086 | 287.77 | 0.01 | 812.8 |
| **1996 médecins** | 1080 | 933 | 384133 | 411.72 | 0.01 | 1437.0 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 59 / 551 (n=63272) | 68 / 572 (n=114324) |
| 2 | Ouvrir / rafraîchir l'inbox | 42 / 99 (n=31624) | 57 / 176 (n=57134) |
| 3 | Ouvrir un message enrichi (servi base) | 35 / 65 (n=15834) | 55 / 147 (n=28590) |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 / 508 (n=6224) | 459 / 533 (n=11433) |
| 5 | Recherche | 332 / 620 (n=4687) | 367 / 737 (n=8618) |
| 6 | Envoi (acquittement UI) | 483 / 927 (n=4771) | 498 / 961 (n=8532) |
| 7 | Télécharger une PJ (~124 Ko) | 38 / 74 (n=6382) | 62 / 175 (n=11439) |
| 8 | Marquer lu | 35 / 83 (n=12681) | 66 / 139 (n=22866) |
| 9 | Rechercher un patient | 56 / 65 (n=4710) | 58 / 87 (n=8635) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 66 (n=7050) | 60 / 94 (n=12833) |
| 11 | Fiche patient complète (ressenti médecin) | 271 / 452 (n=3525) | 378 / 853 (n=6417) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.4 / 20 | 34.3 / 60 | 7884 | 452 |
| **1996 médecins** | 14.4 / 20 | 34.2 / 60 | 14324 | 853 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2253 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 615 ms en moyenne, 9303 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2233 / 3053 (magasin) | 2233 / 3053 (magasin) |
| Backends Postgres (moy/max) | 1242 / 1436 | 1988 / 2027 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` — chemin du médecin (échant. non nuls) | 36/174 (21 %) | 55/142 (39 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 36/174 (21 %) | 55/142 (39 %) |
| …dont **registre** des comptes (échant. non nuls) | 0/174 (0 %) | 0/142 (0 %) |
| …dont **maintenance** (échant. non nuls) | 0/174 (0 %) | 0/142 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 53.8 | 46.8 |
| …dont bases **praticien** — chemin du médecin | 53.8 | 46.8 |
| …dont **registre** des comptes — chemin du médecin | 0.0 | 0.0 |
| …dont **maintenance** (`postgres`, `pgbouncer`) | 0.0 | 0.0 |
| Attente PgBouncer cumulée — chemin du médecin (s) | 652.7 | 1405.8 |
| …par transaction du médecin (ms) | 0.3 | 0.5 |
| …part du temps des transactions (attente comprise) | 18.0 % | 19.0 % |
| …part du temps des requêtes HTTP du palier (k6) | 3.1 % | 3.2 % |
| Attente PgBouncer cumulée — maintenance (s) | 0.0 | 0.0 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | 0.009 / 0.014 / 0.027 | 0.012 / 0.017 / 0.032 |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 120 / 402 | 99 / 292 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 8 | 118 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1405 | 1996 |
| Backends **directs** — audit + provisionnement (max) | 29 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 4 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 99.6 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 0 / 5 |
| RSS par réplica api-mail, Mo (moy/max) | 1132 / 1500 (5 réplicas) | 2048 / 2224 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1436.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2027.0 / 2500** (81.1 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15834)
- palier 1996 : cohorte 1996 chauffée à 99.0 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28590)

> ⓘ Chauffe : **302 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 59 (300) | 551 (1500) | 63272 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 42 (300) | 99 (1000) | 31624 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 35 (100) | 65 (500) | 15834 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 (800) | 508 (2500) | 6224 | ✅ |
| 5 | Recherche | 332 (500) | 620 (2000) | 4687 | ✅ |
| 6 | Envoi (acquittement UI) | 483 (1000) | 927 (3000) | 4771 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 38 (500) | 74 (2000) | 6382 | ✅ |
| 8 | Marquer lu | 35 (200) | 83 (1000) | 12681 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 65 (1500) | 4710 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 66 (2000) | 7050 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 271 (1500) | 452 (4000) | 3525 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 68 (300) | 572 (1500) | 114324 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 57 (300) | 176 (1000) | 57134 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 55 (100) | 147 (500) | 28590 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 459 (800) | 533 (2500) | 11433 | ✅ |
| 5 | Recherche | 367 (500) | 737 (2000) | 8618 | ✅ |
| 6 | Envoi (acquittement UI) | 498 (1000) | 961 (3000) | 8532 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 62 (500) | 175 (2000) | 11439 | ✅ |
| 8 | Marquer lu | 66 (200) | 139 (1000) | 22866 | ✅ |
| 9 | Rechercher un patient | 58 (300) | 87 (1500) | 8635 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 60 (500) | 94 (2000) | 12833 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 378 (1500) | 853 (4000) | 6417 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114324 | 167 | 572 | 19109.1 | 43.5 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8532 | 633 | 961 | 5402.3 | 12.3 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11433 | 462 | 533 | 5286.3 | 12.0 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57134 | 72 | 176 | 4087.4 | 9.3 % |
| 🟢 | Recherche (`search`) | 8618 | 421 | 737 | 3628.5 | 8.3 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28590 | 68 | 147 | 1938.0 | 4.4 % |
| 🟢 | Marquer lu (`mark_read`) | 22866 | 71 | 139 | 1620.3 | 3.7 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11439 | 82 | 175 | 932.5 | 2.1 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7162 | 116 | 201 | 831.3 | 1.9 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8635 | 52 | 87 | 449.6 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6416 | 61 | 86 | 389.1 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6417 | 46 | 94 | 295.6 | 0.7 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 2 🟠 · 10 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 19109.1 s, 43.5 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 8.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 4087.4 s, 9.3 %)
  - **dispersion p95/p50 = 3.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15818 | 392 | 992 | 6089.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15818 | 59 | 496 | 2168.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15818 | 20 | 164 | 725.0 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15818 | 57 | 69 | 917.2 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15812 | 16 | 118 | 484.7 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15812 | 52 | 89 | 893.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28581 | 402 | 989 | 11351.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28581 | 66 | 509 | 4116.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28581 | 35 | 194 | 1818.1 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28581 | 62 | 93 | 1824.0 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28567 | 25 | 136 | 1272.4 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28567 | 83 | 199 | 2815.0 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (989 ms de p95, 402 ms de p50, n=28581), qui porte **aussi** le temps serveur de l'étape (11351.0 s, 59 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (199 ms de p95, 83 ms de p50, n=28567), qui porte **aussi** le temps serveur de l'étape (2815.0 s, 69 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21759 | 78.6 | 50.1 | 128.4 | 226.2 | 1687.0 |
| attachment,palier:1400 | 6382 | 42.7 | 38.0 | 61.4 | 74.2 | 270.1 |
| attachment,palier:1996 | 11439 | 81.5 | 62.2 | 133.7 | 175.4 | 1138.3 |
| attachment,palier:transition | 566 | 138.7 | 44.6 | 457.6 | 551.2 | 915.7 |
| dashboard | 219656 | 171.6 | 65.7 | 473.1 | 649.2 | 1559.5 |
| dashboard,call:coverage,palier:1400 | 15818 | 58.0 | 57.1 | 64.6 | 68.8 | 178.7 |
| dashboard,call:coverage,palier:1996 | 28581 | 63.8 | 61.9 | 82.9 | 93.0 | 624.2 |
| dashboard,call:coverage,palier:transition | 1061 | 128.3 | 87.3 | 258.5 | 306.9 | 465.7 |
| dashboard,call:folder,palier:1400 | 15818 | 385.0 | 391.9 | 760.5 | 991.8 | 1527.8 |
| dashboard,call:folder,palier:1996 | 28581 | 397.2 | 401.7 | 777.7 | 989.1 | 1559.5 |
| dashboard,call:folder,palier:transition | 1061 | 496.1 | 478.5 | 763.7 | 894.4 | 1527.7 |
| dashboard,call:folders,palier:1400 | 15818 | 45.8 | 20.4 | 147.9 | 163.6 | 370.1 |
| dashboard,call:folders,palier:1996 | 28581 | 63.6 | 34.7 | 170.9 | 194.1 | 902.0 |
| dashboard,call:folders,palier:transition | 1061 | 137.4 | 112.4 | 301.7 | 384.9 | 629.1 |
| dashboard,call:today,palier:1400 | 15818 | 137.1 | 59.0 | 475.3 | 496.1 | 777.4 |
| dashboard,call:today,palier:1996 | 28581 | 144.0 | 66.1 | 484.8 | 508.6 | 1251.4 |
| dashboard,call:today,palier:transition | 1061 | 338.3 | 313.7 | 655.7 | 706.4 | 1107.2 |
| dashboard,palier:1400 | 63272 | 156.5 | 59.2 | 456.4 | 550.8 | 1527.8 |
| dashboard,palier:1996 | 114324 | 167.1 | 68.3 | 466.7 | 572.3 | 1559.5 |
| dashboard,palier:transition | 4244 | 275.0 | 183.9 | 619.5 | 707.7 | 1527.7 |
| mark_read | 43669 | 70.6 | 58.2 | 110.0 | 161.3 | 634.4 |
| mark_read,palier:1400 | 12681 | 46.8 | 34.8 | 76.3 | 83.1 | 319.2 |
| mark_read,palier:1996 | 22866 | 70.9 | 65.6 | 113.3 | 139.3 | 618.4 |
| mark_read,palier:transition | 1160 | 113.2 | 65.8 | 348.6 | 430.5 | 634.4 |
| patient_docs | 176238 | 79.1 | 56.4 | 145.9 | 208.3 | 1430.3 |
| patient_docs,palier:1400 | 50909 | 47.0 | 43.6 | 84.5 | 99.2 | 290.7 |
| patient_docs,palier:1996 | 92547 | 78.7 | 65.3 | 151.8 | 188.9 | 768.5 |
| patient_docs,palier:transition | 4814 | 128.2 | 53.8 | 434.3 | 573.2 | 1216.9 |
| patient_dossier | 12218 | 46.1 | 31.0 | 74.1 | 113.9 | 665.1 |
| patient_dossier,palier:1400 | 3525 | 27.3 | 24.8 | 36.3 | 44.3 | 243.1 |
| patient_dossier,palier:1996 | 6417 | 46.1 | 37.9 | 75.9 | 94.2 | 665.1 |
| patient_dossier,palier:transition | 329 | 81.7 | 29.3 | 260.8 | 311.7 | 465.7 |
| patient_opposition | 12218 | 62.9 | 58.4 | 77.2 | 94.0 | 367.9 |
| patient_opposition,palier:1400 | 3525 | 57.0 | 56.4 | 62.3 | 65.5 | 117.5 |
| patient_opposition,palier:1996 | 6416 | 60.7 | 60.1 | 77.6 | 86.0 | 194.3 |
| patient_opposition,palier:transition | 329 | 80.4 | 58.2 | 163.0 | 201.6 | 324.1 |
| patient_search | 16381 | 52.9 | 55.8 | 76.2 | 94.6 | 582.4 |
| patient_search,palier:1400 | 4710 | 45.0 | 55.5 | 62.7 | 65.5 | 226.4 |
| patient_search,palier:1996 | 8635 | 52.1 | 58.0 | 77.4 | 87.1 | 582.4 |
| patient_search,palier:transition | 445 | 71.3 | 55.8 | 162.2 | 203.6 | 410.0 |
| read_content | 54914 | 67.3 | 44.1 | 110.9 | 170.8 | 954.0 |
| read_content,palier:1400 | 15834 | 38.1 | 34.8 | 53.8 | 65.4 | 259.6 |
| read_content,palier:1996 | 28590 | 67.8 | 55.0 | 116.1 | 147.3 | 658.1 |
| read_content,palier:transition | 1331 | 126.2 | 43.3 | 412.7 | 502.6 | 742.8 |
| read_content_cold | 21830 | 460.6 | 454.2 | 514.8 | 540.9 | 1124.1 |
| read_content_cold,palier:1400 | 6224 | 445.8 | 444.4 | 494.8 | 508.1 | 1053.4 |
| read_content_cold,palier:1996 | 11433 | 462.4 | 459.1 | 514.6 | 532.6 | 1124.1 |
| read_content_cold,palier:transition | 579 | 486.0 | 462.3 | 622.0 | 671.6 | 849.4 |
| read_list | 109828 | 71.1 | 49.1 | 135.5 | 200.7 | 1038.3 |
| read_list,call:emails,palier:1400 | 15812 | 56.5 | 52.1 | 75.9 | 89.2 | 243.8 |
| read_list,call:emails,palier:1996 | 28567 | 98.5 | 82.9 | 159.4 | 198.8 | 847.1 |
| read_list,call:emails,palier:transition | 1226 | 203.9 | 71.6 | 591.2 | 672.9 | 974.1 |
| read_list,call:folder,palier:1400 | 15812 | 30.7 | 15.8 | 37.1 | 118.1 | 515.4 |
| read_list,call:folder,palier:1996 | 28567 | 44.5 | 24.7 | 88.3 | 136.1 | 637.1 |
| read_list,call:folder,palier:transition | 1226 | 83.4 | 23.4 | 231.6 | 301.6 | 878.1 |
| read_list,palier:1400 | 31624 | 43.6 | 41.9 | 72.1 | 98.6 | 515.4 |
| read_list,palier:1996 | 57134 | 71.5 | 57.3 | 138.2 | 175.6 | 847.1 |
| read_list,palier:transition | 2452 | 143.7 | 60.4 | 449.9 | 595.8 | 974.1 |
| search | 16381 | 419.2 | 355.6 | 570.6 | 844.2 | 2188.9 |
| search,palier:1400 | 4687 | 382.6 | 332.3 | 468.5 | 620.4 | 1519.7 |
| search,palier:1996 | 8618 | 421.0 | 366.5 | 539.1 | 737.3 | 2147.1 |
| search,palier:transition | 418 | 457.2 | 349.9 | 816.0 | 945.7 | 1768.1 |
| send | 15761 | 645.6 | 511.5 | 923.6 | 961.0 | 1630.7 |
| send,palier:1400 | 4771 | 625.1 | 483.5 | 900.1 | 926.7 | 1142.5 |
| send,palier:1996 | 8532 | 633.2 | 498.0 | 927.3 | 961.2 | 1630.7 |
| send,palier:transition | 492 | 647.1 | 515.5 | 947.4 | 1113.2 | 1365.3 |
| treatment | 13676 | 110.7 | 88.0 | 157.2 | 225.1 | 5115.2 |
| treatment,palier:1400 | 3942 | 75.3 | 80.7 | 98.8 | 109.3 | 231.8 |
| treatment,palier:1996 | 7162 | 116.1 | 97.7 | 165.4 | 200.6 | 5115.2 |
| treatment,palier:transition | 324 | 170.4 | 89.2 | 499.5 | 590.9 | 804.6 |
| warmup | 21956 | 615.3 | 439.4 | 762.3 | 1734.5 | 9302.8 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-10T14:56:11.372000+00:00 → 2026-11-10T15:33:49.330000+00:00 (2258 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t439-controle-bis.csv`) | ✅ 75087 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-1492` | 0.98 | 8 | 32 | 0.024 | 4.47 |
| `DESKTOP-DEV-X2C-18056` | 0.99 | 16 | 35 | 0.027 | 4.47 |
| `DESKTOP-DEV-X2C-48780` | 1.00 | 14 | 33 | 0.037 | 5.02 |
| `DESKTOP-DEV-X2C-54228` | 1.09 | 8 | 34 | 0.037 | 4.91 |
| `DESKTOP-DEV-X2C-62508` | 0.99 | 7 | 32 | 0.025 | 4.67 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#34920` | 0.00 | 0.17 | 39 |
| `com.docker.backend#35896` | 1.12 | 3.80 | 2062 |
| `dcp#28064` | 0.00 | 0.04 | 14 |
| `dcp#48952` | 0.00 | 0.00 | 12 |
| `dcp#50280` | 0.00 | 0.25 | 13 |
| `dcp#51644` | 0.00 | 0.00 | 12 |
| `dcp#52304` | 0.00 | 0.00 | 12 |
| `dcp#5252` | 0.00 | 0.04 | 13 |
| `dcp#53916` | 0.00 | 0.00 | 12 |
| `dcp#56344` | 0.00 | 0.04 | 12 |
| `dcp#58068` | 0.00 | 0.00 | 12 |
| `dcp#60148` | 0.00 | 0.08 | 50 |
| `dcp#63784` | 0.77 | 2.60 | 3204 |
| `dcp#65824` | 0.00 | 0.04 | 11 |
| `dcp#65928` | 0.00 | 0.04 | 12 |
| `dcp#66792` | 0.00 | 0.04 | 13 |
| `dcp#67940` | 0.00 | 0.00 | 12 |
| `k6#354833` | 0.84 | 1.85 | 2892 |
| `mss.mail.api#1492` | 0.68 | 3.32 | 2203 |
| `mss.mail.api#18056` | 0.70 | 3.08 | 2141 |
| `mss.mail.api#48780` | 0.69 | 2.78 | 2245 |
| `mss.mail.api#54228` | 0.65 | 2.99 | 2221 |
| `mss.mail.api#62508` | 0.67 | 2.28 | 2186 |
| `mss.mail.e2e#65508` | 0.01 | 0.18 | 33 |
| `vmmemWSL#35316` | 5.46 | 11.45 | 54640 |
| `loadtest-otel-collector-vctksgsh` | 0.02 | 0.15 | 107 |
| `loadtest-pgbouncer-mutgghgd` | 0.44 | 0.86 | 48 |
| `mss-mail-flagsmith-app-b6152948` | 0.13 | 0.55 | 558 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.38 | 188 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.06 | 123 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.12 | 280 |
| `mss-mail-rabbitmq-shefptfj` | 0.01 | 0.03 | 136 |
| `mss-mail-redis-b6152948` | 0.27 | 1.38 | 944 |
| `mss-mail-rediscommander-jyzabtnn` | 0.00 | 0.24 | 24 |
| `mss-mail-seq-b6152948` | 0.12 | 4.47 | 1569 |
| `postgres-pgvector` | 2.16 | 8.07 | 36475 |

- **Hôte** : CPU 66.4 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 31
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9347, cl_waiting max 13, cl_waiting_doctor_path max 13, cl_waiting_maintenance max 0, cl_waiting_practitioner max 13, cl_waiting_registry max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 0, maxwait_ms max 54, maxwait_practitioner_ms max 54, maxwait_registry_ms max 0, sv_active max 79, sv_idle max 1604, sv_login max 2, wait_us_delta_maintenance max 0, wait_us_delta_practitioner max 87699989, wait_us_delta_registry max 0, xact_delta_maintenance max 2, xact_delta_practitioner max 40197, xact_delta_registry max 0, xact_us_delta_maintenance max 0, xact_us_delta_practitioner max 410617450, xact_us_delta_registry max 0
- **Backends Postgres** : audit max 5, cache_mb max 40809, direct max 29, idle_over_60s max 200, majfault_per_s max 5, pooler max 1996, practitioner_databases max 1986, provision max 4, rss_mb max 6220, seconds max 0, started_last_60s max 402, total max 2027, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 5406.6 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2483.0 | 452 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 702.4 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 797.5 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 746.0 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 700.2 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 474.2 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 741.1 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2040.6 | 432 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 231.6 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 428.4 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 245.3 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 1649.4 | 442 |
| `api/v{version:apiVersion}/Sync/coverage` | 309.7 | 447 |

- **p95 client global (k6)** : 517.4 ms
- **p95 serveur le plus élevé** : 5406.6 ms
- **Écart** : -4889.2 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.69 |
| Documents CDA /s | 0.67 |
| Durée traitement CDA (s, p95) | 0.91 |
| Événements de session IMAP /s | 4.02 |
| Recherches (s, p95) | 1.293 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 74.6 | 316 | 0.0 (0.0 %), p95 5 | 43.0 (57.6 %), p95 235 | 31.6 (42.3 %), p95 224 |
| `GetMail` | 11.1 | 50.2 | 496 | 4.7 (9.3 %), p95 66 | 41.7 (83.0 %), p95 470 | 3.8 (7.6 %), p95 17 |
| `GetMailsByUids` | 14.7 | 78.9 | 561 | 0.1 (0.1 %), p95 5 | 67.0 (85.0 %), p95 499 | 11.8 (14.9 %), p95 64 |

- **`EnrichPersistMail`** — sur 74.6 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 43.0 ms exécution SQL, 31.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 50.2 ms en moyenne (11.1 requête(s) SQL par appel) : 4.7 ms attente d'une connexion, 41.7 ms exécution SQL, 3.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 78.9 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 67.0 ms exécution SQL, 11.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est l'attente du **pool Npgsql** seul ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **L'attente PgBouncer n'est pas dans `attente d'une connexion`** (task-435). En mode transaction, le pooler attribue un serveur à la première requête de chaque transaction : son attente est comptée dans `exécution SQL`. Son coût se lit dans « Coûts résidents » (« Attente PgBouncer cumulée — chemin du médecin »).

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.8 | 355.8 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.1 | 11.8 | 56.8 | 18.7 | 28.6 | 18.7 | 30.4 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.8 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **355.8 µs**.

- **`GetMailsByUids`** — sur 11.8 ms de matérialisation, l'appel a construit 207.1 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.4 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **56.8 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3892.1 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 308.6 | 1394 | 132.1 (42.8 %), p95 243 | 14.7 (4.8 %), p95 139 | 58.1 (18.8 %), p95 700 | 54.3 (17.6 %), p95 242 | 49.5 (16.0 %), p95 242 |

- **Enrichir un message** — sur 308.6 ms en moyenne (3.8 message(s) par requête) : 132.1 ms fetch IMAP, 14.7 ms extraction XDM, 58.1 ms parsing CDA, 54.3 ms écritures base, 49.5 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 253.1 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 632.6 | 980 | 0.0 (0.0 %), p95 5 | 20.7 (3.3 %), p95 72 | 215.6 (34.1 %), p95 477 | 396.2 (62.6 %), p95 489 | 418.2 (66.1 %), p95 961 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 632.6 ms en moyenne : 0.0 ms garde d'opposition, 20.7 ms construction MIME, 215.6 ms obtention de session SMTP, 396.2 ms transmission + acquittement, 418.2 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.442 | 2.381 | 101.42 |
| `smtp_session` | 0.005 | 0.993 | 10.40 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.327 | 2.350 | 0.489 | 10.33 |
| `EnrichEmails` | 0.005 | 0.470 | — | 0.470 | 1.00 |
| `GetAttachmentStream` | 0.483 | 2.425 | 2.425 | 0.700 | 0.82 |
| `GetEmailContent` | 0.005 | 0.592 | — | 0.592 | 13.84 |
| `GetFolders` | 0.005 | 0.992 | 0.992 | 0.243 | 7.58 |
| `ReadFolder` | 0.752 | 2.381 | 2.381 | 0.487 | 35.36 |
| `ReadToday` | 0.005 | 0.497 | 2.425 | 0.497 | 7.56 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 27.26 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.350** | 0.453 | 0.464 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.650 | 0.700 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.490 | 0.491 | 0.0 % |
| `GetFolders` | **0.242** | 0.242 | 0.243 | 0.0 % |
| `ReadFolder` | **0.429** | 0.441 | 0.445 | 0.0 % |
| `ReadToday` | **0.488** | 0.490 | 0.491 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 101.42 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.752 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 13.00 clients | 0 clients | 100.0 % | 28.1 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.07 cœurs | 24 cœurs | 33.6 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 4.47 cœurs | 24 cœurs | 18.6 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-18056` | 16.00 éléments | 100 éléments | 16.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#1492` (CPU) | 3.32 cœurs | 24 cœurs | 13.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#18056` (CPU) | 3.08 cœurs | 24 cœurs | 12.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#54228` (CPU) | 2.99 cœurs | 24 cœurs | 12.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#48780` (CPU) | 2.78 cœurs | 24 cœurs | 11.6 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 28.1 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 239 586

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 2 950 |
| OpenAI | gpt-4o-mini | prompt | 236 636 |
| OpenAI | text-embedding-3-small | embedding | 353 156 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 128 | 0 (0.0 %) | 0 | 3.4 | 1.10 | 0.94 | 2.43 |
| étiquetage (chat) | OpenAI | 128 | 0 (0.0 %) | 0 | 3.4 | 1.04 | 0.90 | 2.41 |
| embedding | OpenAI | 128 | 0 (0.0 %) | 0 | 3.4 | 0.56 | 0.46 | 1.76 |

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
| GPU — utilisation (%) | 6.4 | 28.0 |
| GPU — VRAM occupée (Mo) | 1 926 | 2 086 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 587.3** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.20** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **3.7 ms** | sur 756 499 requêtes HTTP k6 |
| Taux de cache (blocs) | **97.84 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **9.21 Mo/s (1 179 blocs/s)** | attente disque : 6.2 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **245 447 / 30 601** | rapport 8.0 |
| Écritures de lignes / s (ins+upd+del) | **161.9** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.29 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 14 % |
| Sessions ouvertes / s | **3.04** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **54.8 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 558 / 2 027** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **10 / 17 / 32 ms** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **97 / 100 %** | fautes majeures/s max : 5.2 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 171.6 s | 8301 | `pages-par-ligne` | 11.2 pages par ligne rendue, 575 par appel, 36.4 Go lus | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 156.0 s | 8422 | `pages-par-ligne` | 11.0 pages par ligne rendue, 563 par appel, 36.2 Go lus | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 127.5 s | 166740 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, HtmlBody : 18.7 Go lus, 3.8 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 12.1 % du temps SQL, 45.3 % des lectures disque du tir | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 40.2 s | 8353 | `pages-par-ligne` | 32.1 pages par ligne rendue, 641 par appel, 40.9 Go lus | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 33.9 s | 8431 | `pages-par-ligne` | 31.9 pages par ligne rendue, 639 par appel, 41.1 Go lus | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 25.1 s | 166741 | `colonne-volumineuse` | sélectionne Body, BodyHtml : 6.8 Go lus, 0.1 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |
| 25.0 s | 15290 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Content : 2.7 Go lus, 1.8 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 2.4 % du temps SQL, 21.5 % des lectures disque du tir | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **86 évictions `pg_stat_statements`** pendant le tir (96 262 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

136 formes de requête, 5 973 421 appels, **17.5 min** de temps serveur cumulé — soit **1.4 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **16.3 %** | 16 % | 8 301 | 0.01 | 20.67 | 51.2 | 575 | 0 % | 0 | 805 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **14.8 %** | 31 % | 8 422 | 0.01 | 18.52 | 50.9 | 563 | 1 % | 0 | 816 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **12.1 %** | 43 % | 166 740 | 0.22 | 0.77 | 1.0 | 15 | 20 % | 0 | 1 877 | **Code** — 20 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 4 | **6.3 %** | 50 % | 756 342 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `PostgresTenantRegistryClient.GetMailboxAsync` ← `GET /api/v1/Mail/folders/{foldername}` | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 5 | **6.2 %** | 56 % | 88 401 | 0.12 | 0.74 | 18.0 | 104 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 6 | **3.8 %** | 60 % | 8 353 | 0.01 | 4.81 | 20.0 | 641 | 2 % | 0 | 807 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 7 | **3.3 %** | 63 % | 135 671 | 0.18 | 0.25 | 1.0 | 15 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 8 | **3.2 %** | 66 % | 8 431 | 0.01 | 4.01 | 20.0 | 639 | 1 % | 0 | 818 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 9 | **2.4 %** | 68 % | 166 741 | 0.22 | 0.15 | 1.0 | 5 | 1 % | 0 | 1 877 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |
| 10 | **2.4 %** | 71 % | 15 290 | 0.02 | 1.64 | 1.0 | 24 | 66 % | 0 | 1 202 | **Code** — 66 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 11 | **2.2 %** | 73 % | 94 882 | 0.13 | 0.24 | 18.0 | 8 | 0 % | 0 | 1 787 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | site inconnu ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}`<br>`MailRepository.LoadMailsReferencingAnyRootAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 12 | **2.1 %** | 75 % | 280 729 | 0.37 | 0.08 | 1.3 | 17 | 0 % | 0 | 1 996 | — | `MailRepository.ResolveActiveDuplicateRefsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 13 | **1.9 %** | 77 % | 4 820 | 0.01 | 4.04 | 180.0 | 540 | 1 % | 0 | 839 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 14 | **1.5 %** | 78 % | 88 395 | 0.12 | 0.18 | 18.0 | 8 | 0 % | 0 | 1 996 | — | `MailRepository.GetMailsByUidsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 15 | **1.5 %** | 80 % | 280 738 | 0.37 | 0.06 | 2.0 | 4 | 0 % | 0 | 1 996 | — | `MailRepository.EnrichManyWithBiologyAcksAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 16 | **1.3 %** | 81 % | 44 960 | 0.06 | 0.31 | 27.0 | 8 | 0 % | 0 | 1 401 | — | `MailRepository.GetLatestMessageIdsPerThreadAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **1.2 %** | 82 % | 143 304 | 0.19 | 0.09 | 20.8 | 8 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **1.2 %** | 84 % | 143 307 | 0.19 | 0.09 | 14.0 | 8 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **1.0 %** | 85 % | 187 186 | 0.25 | 0.06 | 1.5 | 6 | 0 % | 0 | 1 897 | — | `MailRepository.GetMailAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`, `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |
| 20 | **0.9 %** | 86 % | 88 404 | 0.12 | 0.11 | 5.6 | 9 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.7 % | 87.8 % |
| INSERT | 4.3 % | 2.9 % |
| UPDATE | 0.4 % | 1.3 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.5 % | 7.4 % |
| bases : praticien (N bases) | 90.0 % | 82.2 % |
| bases : unique (1 base) | 10.0 % | 17.8 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **20.7** | 152 | 8 301 | 16.3 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **18.5** | 95 | 8 422 | 14.8 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **4.8** | 103 | 8 353 | 3.8 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **4.0** | 92 | 4 820 | 1.9 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **4.0** | 79 | 8 431 | 3.2 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 224 | 145 656 | 0 | 0 | 0.1 Mo |
| `Mails` | 520 | 77 054 | 691 | 0 | 0.2 Mo |
| `MailTags` | 157 | 38 936 | 72 | 0 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 175 | 25 803 | 973 | 0 | 9.7 Mo |
| `MailRecipients` | 137 | 21 372 | 54 | 0 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 51 | 13 311 | 158 | 0 | 30.1 Mo |
| `MailContents` ⚠️ index candidat | 72 | 11 232 | 2 120 | 0 | 3.4 Mo |
| `PendingActions` | 162 | 4 757 | 0 | 31 | 0.1 Mo |
| `Tags` | 119 | 2 142 | 46 | 0 | 0.0 Mo |
| `MailFolders` | 315 | 864 | 186 | 4 | 0.1 Mo |

Index **non sollicités** pendant le tir sur des tables pourtant lues (≥ 1 Mo) :

| Index | Table | Taille |
|---|---|---|
| `IX_MailMedicalDocuments_SearchText` | `MailMedicalDocuments` | 1.3 Mo |
| `IX_MailContents_SearchText` | `MailContents` | 1.2 Mo |

Un index jamais lu coûte à chaque écriture ; un tir n'exerce pas toutes les routes — confirmer sur `pg_stat_user_indexes` d'une journée réelle avant de supprimer.

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Code | 🟠 | requête n°3 (12.1 % du temps SQL) — 20 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟠 | requête n°4 (6.3 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 97.8 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 175 fois (25803 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 51 fois (13311 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 72 fois (11232 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°10 (2.4 % du temps SQL) — 66 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°13 (1.9 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°6 (3.8 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°11 (2.2 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Schéma | 🟡 | index `IX_MailMedicalDocuments_SearchText` (1.3 Mo, table `MailMedicalDocuments`) jamais sollicité pendant le tir : candidat à la suppression si une journée réelle confirme (coût à chaque écriture) |
| Schéma | 🟡 | index `IX_MailContents_SearchText` (1.2 Mo, table `MailContents`) jamais sollicité pendant le tir : candidat à la suppression si une journée réelle confirme (coût à chaque écriture) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-163431.tsv`, `pgserver-journey-debut-155601.tsv`, `pgserver-journey-fin-163437.tsv`, `pgtables-journey-debut-155605.tsv`, `pgtables-journey-fin-163442.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 248728 — dont **248728** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261110-t439-controle-bis-163349.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
