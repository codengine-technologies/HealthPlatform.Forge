# Rapport de tir — journey-courte-1400-1996-20261107-bilan-avant-1

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261107-bilan-avant-1-001645.json`.

> ## ⛔ TIR VOID — panne du serveur SMTP du banc
>
> Ce rapport s'ouvre sur ORANGE, mais **ses chiffres ne se comparent pas**. Le serveur SMTP du banc a calé de
> 22:51:45 à 23:02:12 UTC (voir « Analyse Seq ») : envoi p50 31,7 s, 2 606 erreurs, 9 % de requêtes en moins, et
> toutes les autres étapes allégées d'autant. Le bilan du lot repose sur le seul tir **avant-2**. Synthèse :
> `api-mail-loadtest-ab-bilan-lot-20261108.md`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1400 médecins, 1 étape(s) dépassent le temps de réponse attendu : « Envoi (acquittement UI) »
- 5 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 22 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.210 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 687365 — **débit émergent global** : 304.0 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 48474 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 304.0 | **674.3** | 109.3 | **829.2** | — | 120016.5 | 0.21 | 99.8 | 0 | 0 | 247884/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 171059 | 232.10 | 0.51 | 656.3 |
| **1996 médecins** | 1080 | 933 | 370425 | 397.03 | 0.03 | 1348.6 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 69 / 704 (n=50604) | 124 / 730 (n=110660) |
| 2 | Ouvrir / rafraîchir l'inbox | 48 / 123 (n=25340) | 119 / 424 (n=55232) |
| 3 | Ouvrir un message enrichi (servi base) | 44 / 96 (n=12680) | 127 / 373 (n=27555) |
| 4 | Ouvrir un message froid (fetch IMAP) | 454 / 522 (n=5078) | 502 / 698 (n=11033) |
| 5 | Recherche | 406 / 666 (n=3936) | 542 / 1057 (n=8251) |
| 6 | Envoi (acquittement UI) | 31713 / 120001 (n=4101) | 848 / 31973 (n=8121) |
| 7 | Télécharger une PJ (~124 Ko) | 47 / 103 (n=5149) | 138 / 410 (n=10912) |
| 8 | Marquer lu | 49 / 103 (n=10257) | 120 / 343 (n=21774) |
| 9 | Rechercher un patient | 61 / 84 (n=3786) | 83 / 240 (n=8125) |
| 10 | Ouvrir la page d'un dossier patient | 66 / 161 (n=5686) | 164 / 485 (n=12322) |
| 11 | Fiche patient complète (ressenti médecin) | 366 / 696 (n=2843) | 789 / 2365 (n=6162) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.4 / 65 | 6324 | 696 |
| **1996 médecins** | 14.5 / 20 | 34.3 / 65 | 13924 | 2365 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2012 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 922 ms en moyenne, 10094 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2271 / 3075 (magasin) | 2271 / 3075 (magasin) |
| Backends Postgres (moy/max) | 1249 / 1437 | 1989 / 2033 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 2 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 39/181 (22 %) | 86/141 (61 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/181 (0 %) | 0/141 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 39/181 (22 %) | 86/141 (61 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 82.3 | 183.1 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 82.3 | 183.1 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 142 / 354 | 119 / 465 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 95 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1406 | 2002 |
| Backends **directs** — audit + provisionnement (max) | 30 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 2 / 24 |
| RSS par réplica api-mail, Mo (moy/max) | 1181 / 1601 (5 réplicas) | 2050 / 2324 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1437.0 / 2500** (57.5 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2033.0 / 2500** (81.3 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 12680)
- palier 1996 : cohorte 1996 chauffée à 100.0 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 27555)

> ⓘ Chauffe : **309 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **29 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 69 (300) | 704 (1500) | 50604 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 48 (300) | 123 (1000) | 25340 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 44 (100) | 96 (500) | 12680 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 454 (800) | 522 (2500) | 5078 | ✅ |
| 5 | Recherche | 406 (500) | 666 (2000) | 3936 | ✅ |
| 6 | Envoi (acquittement UI) | 31713 (1000) | 120001 (3000) | 4101 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 47 (500) | 103 (2000) | 5149 | ✅ |
| 8 | Marquer lu | 49 (200) | 103 (1000) | 10257 | ✅ |
| 9 | Rechercher un patient | 61 (300) | 84 (1500) | 3786 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 66 (500) | 161 (2000) | 5686 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 366 (1500) | 696 (4000) | 2843 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 124 (300) | 730 (1500) | 110660 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 119 (300) | 424 (1000) | 55232 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 127 (100) | 373 (500) | 27555 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 502 (800) | 698 (2500) | 11033 | ✅ |
| 5 | Recherche | 542 (500) | 1057 (2000) | 8251 | ❌ |
| 6 | Envoi (acquittement UI) | 848 (1000) | 31973 (3000) | 8121 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 138 (500) | 410 (2000) | 10912 | ✅ |
| 8 | Marquer lu | 120 (200) | 343 (1000) | 21774 | ✅ |
| 9 | Rechercher un patient | 83 (300) | 240 (1500) | 8125 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 164 (500) | 485 (2000) | 12322 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 789 (1500) | 2365 (4000) | 6162 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Envoi (acquittement UI) (`send`) | 8121 | 4205 | 31973 | 34151.9 | 37.1 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 110660 | 222 | 730 | 24610.2 | 26.8 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 55232 | 158 | 424 | 8749.8 | 9.5 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11033 | 523 | 698 | 5774.4 | 6.3 % |
| 🟠 | Recherche (`search`) | 8251 | 604 | 1057 | 4979.9 | 5.4 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 27555 | 159 | 373 | 4368.5 | 4.8 % |
| 🟢 | Marquer lu (`mark_read`) | 21774 | 148 | 343 | 3229.4 | 3.5 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 10912 | 173 | 410 | 1882.7 | 2.0 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 6962 | 210 | 447 | 1462.7 | 1.6 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6162 | 202 | 485 | 1244.2 | 1.4 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8125 | 103 | 240 | 835.5 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6160 | 109 | 249 | 670.7 | 0.7 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 1 🔴 · 4 🟠 · 7 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Envoi (acquittement UI)** (`send`, 34151.9 s, 37.1 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (4205 ms)
  - **dispersion p95/p50 = 37.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Arrivée dashboard** (`dashboard`, 24610.2 s, 26.8 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 5.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 8749.8 s, 9.5 %)
  - **dispersion p95/p50 = 3.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 4979.9 s, 5.4 %)
  - **hors grille** — le médecin attend trop
- **Ouvrir un message enrichi (servi base)** (`read_content`, 4368.5 s, 4.8 %)
  - **hors grille** — le médecin attend trop

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 12651 | 394 | 1036 | 5059.3 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 12651 | 68 | 509 | 1965.4 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 12651 | 33 | 179 | 771.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 12651 | 65 | 89 | 849.8 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 12670 | 24 | 125 | 506.2 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 12670 | 61 | 122 | 874.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 27665 | 421 | 1048 | 12218.7 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 27665 | 106 | 570 | 5518.8 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 27665 | 94 | 346 | 3728.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 27665 | 89 | 256 | 3144.2 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 27616 | 70 | 345 | 3012.6 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 27616 | 175 | 454 | 5737.2 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (1048 ms de p95, 421 ms de p50, n=27665), qui porte **aussi** le temps serveur de l'étape (12218.7 s, 50 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (454 ms de p95, 175 ms de p50, n=27616), qui porte **aussi** le temps serveur de l'étape (5737.2 s, 66 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 19639 | 154.2 | 92.1 | 309.0 | 479.6 | 2274.1 |
| attachment,palier:1400 | 5149 | 54.7 | 46.8 | 84.2 | 103.2 | 1016.3 |
| attachment,palier:1996 | 10912 | 172.5 | 138.5 | 313.4 | 409.6 | 1247.6 |
| attachment,palier:transition | 488 | 187.1 | 63.0 | 665.3 | 810.1 | 1278.9 |
| dashboard | 198392 | 233.2 | 112.6 | 561.6 | 785.6 | 2413.2 |
| dashboard,call:coverage,palier:1400 | 12651 | 67.2 | 64.5 | 81.0 | 88.9 | 290.0 |
| dashboard,call:coverage,palier:1996 | 27665 | 113.7 | 89.2 | 183.8 | 256.2 | 1259.2 |
| dashboard,call:coverage,palier:transition | 972 | 278.3 | 202.5 | 626.7 | 771.0 | 1047.2 |
| dashboard,call:folder,palier:1400 | 12651 | 399.9 | 393.6 | 784.9 | 1036.1 | 1492.7 |
| dashboard,call:folder,palier:1996 | 27665 | 441.7 | 420.9 | 812.5 | 1047.9 | 1920.4 |
| dashboard,call:folder,palier:transition | 972 | 680.0 | 591.8 | 1119.3 | 1375.0 | 2170.3 |
| dashboard,call:folders,palier:1400 | 12651 | 61.0 | 32.9 | 162.2 | 178.7 | 557.8 |
| dashboard,call:folders,palier:1996 | 27665 | 134.8 | 94.1 | 270.4 | 345.5 | 1494.2 |
| dashboard,call:folders,palier:transition | 972 | 320.4 | 223.2 | 747.7 | 873.1 | 1241.8 |
| dashboard,call:today,palier:1400 | 12651 | 155.4 | 68.0 | 488.4 | 509.2 | 1285.7 |
| dashboard,call:today,palier:1996 | 27665 | 199.5 | 105.7 | 522.4 | 569.8 | 1642.5 |
| dashboard,call:today,palier:transition | 972 | 542.6 | 543.5 | 984.9 | 1094.6 | 1396.1 |
| dashboard,palier:1400 | 50604 | 170.8 | 69.1 | 473.1 | 704.3 | 1492.7 |
| dashboard,palier:1996 | 110660 | 222.4 | 123.9 | 506.7 | 730.4 | 1920.4 |
| dashboard,palier:transition | 3888 | 455.3 | 448.1 | 899.7 | 1056.6 | 2170.3 |
| mark_read | 39433 | 137.7 | 89.1 | 252.3 | 401.9 | 2067.8 |
| mark_read,palier:1400 | 10257 | 58.2 | 48.9 | 91.3 | 103.4 | 316.5 |
| mark_read,palier:1996 | 21774 | 148.3 | 120.5 | 259.8 | 343.4 | 1317.6 |
| mark_read,palier:transition | 1048 | 181.1 | 80.8 | 567.5 | 724.0 | 1379.8 |
| patient_docs | 160680 | 157.0 | 96.1 | 323.2 | 473.7 | 2132.9 |
| patient_docs,palier:1400 | 41280 | 63.1 | 56.1 | 112.3 | 134.7 | 326.9 |
| patient_docs,palier:1996 | 89478 | 167.0 | 135.0 | 325.4 | 404.3 | 1331.9 |
| patient_docs,palier:transition | 4540 | 237.9 | 86.0 | 735.7 | 957.9 | 1617.0 |
| patient_dossier | 11085 | 186.4 | 120.4 | 369.8 | 563.9 | 2614.1 |
| patient_dossier,palier:1400 | 2843 | 76.4 | 65.5 | 134.2 | 161.2 | 318.7 |
| patient_dossier,palier:1996 | 6162 | 201.9 | 164.2 | 372.5 | 485.5 | 1392.1 |
| patient_dossier,palier:transition | 308 | 266.8 | 92.2 | 821.4 | 1143.7 | 1821.7 |
| patient_opposition | 11083 | 112.5 | 75.1 | 172.1 | 312.1 | 1681.5 |
| patient_opposition,palier:1400 | 2843 | 66.2 | 64.0 | 79.5 | 87.0 | 133.0 |
| patient_opposition,palier:1996 | 6160 | 108.9 | 86.8 | 177.8 | 248.8 | 1240.1 |
| patient_opposition,palier:transition | 308 | 148.9 | 72.7 | 432.1 | 543.6 | 843.6 |
| patient_search | 14731 | 106.3 | 69.4 | 173.5 | 316.3 | 1970.9 |
| patient_search,palier:1400 | 3786 | 53.4 | 60.7 | 75.5 | 83.7 | 151.6 |
| patient_search,palier:1996 | 8125 | 102.8 | 83.1 | 174.0 | 240.3 | 1172.8 |
| patient_search,palier:transition | 435 | 162.5 | 70.9 | 514.5 | 677.5 | 986.5 |
| read_content | 49598 | 138.9 | 83.6 | 276.9 | 415.4 | 2100.2 |
| read_content,palier:1400 | 12680 | 50.8 | 44.0 | 78.9 | 95.9 | 251.5 |
| read_content,palier:1996 | 27555 | 158.5 | 126.9 | 289.7 | 372.6 | 1499.1 |
| read_content,palier:transition | 1159 | 218.8 | 81.1 | 670.0 | 841.2 | 1399.2 |
| read_content_cold | 19928 | 518.0 | 480.9 | 610.7 | 750.4 | 2212.0 |
| read_content_cold,palier:1400 | 5078 | 455.6 | 454.0 | 506.0 | 521.7 | 709.1 |
| read_content_cold,palier:1996 | 11033 | 523.4 | 501.5 | 618.8 | 698.3 | 1566.3 |
| read_content_cold,palier:transition | 498 | 560.5 | 476.9 | 929.7 | 1113.9 | 1434.8 |
| read_list | 99196 | 141.7 | 79.0 | 314.1 | 465.2 | 2132.3 |
| read_list,call:emails,palier:1400 | 12670 | 69.0 | 61.4 | 102.3 | 122.4 | 328.5 |
| read_list,call:emails,palier:1996 | 27616 | 207.8 | 174.6 | 365.1 | 454.3 | 1431.5 |
| read_list,call:emails,palier:transition | 1146 | 311.3 | 130.1 | 860.7 | 1019.7 | 1523.0 |
| read_list,call:folder,palier:1400 | 12670 | 40.0 | 23.6 | 60.9 | 124.9 | 512.7 |
| read_list,call:folder,palier:1996 | 27616 | 109.1 | 69.6 | 216.7 | 345.2 | 1414.0 |
| read_list,call:folder,palier:transition | 1146 | 176.8 | 60.4 | 516.1 | 692.3 | 1046.1 |
| read_list,palier:1400 | 25340 | 54.5 | 47.6 | 95.8 | 123.5 | 512.7 |
| read_list,palier:1996 | 55232 | 158.4 | 119.2 | 321.9 | 424.2 | 1431.5 |
| read_list,palier:transition | 2292 | 244.0 | 100.6 | 720.5 | 896.3 | 1523.0 |
| search | 14985 | 573.7 | 487.6 | 862.4 | 1213.8 | 3206.9 |
| search,palier:1400 | 3936 | 446.9 | 405.6 | 549.0 | 666.3 | 1705.5 |
| search,palier:1996 | 8251 | 603.5 | 542.3 | 840.4 | 1057.3 | 2759.3 |
| search,palier:transition | 389 | 668.3 | 466.9 | 1369.1 | 1586.3 | 2933.8 |
| send | 14202 | 22266.4 | 942.3 | 108469.5 | 120000.4 | 120016.5 |
| send,palier:1400 | 4101 | 50502.6 | 31712.5 | 120000.6 | 120000.9 | 120016.5 |
| send,palier:1996 | 8121 | 4205.4 | 848.2 | 1273.3 | 31973.1 | 89903.1 |
| send,palier:transition | 379 | 17530.7 | 821.5 | 96509.5 | 101807.9 | 120001.1 |
| treatment | 12443 | 185.8 | 124.0 | 336.5 | 494.4 | 5092.0 |
| treatment,palier:1400 | 3162 | 87.7 | 87.5 | 122.0 | 138.7 | 315.2 |
| treatment,palier:1996 | 6962 | 210.1 | 169.0 | 349.1 | 447.5 | 5092.0 |
| treatment,palier:transition | 240 | 269.2 | 119.3 | 762.8 | 930.3 | 1274.9 |
| warmup | 21956 | 922.2 | 555.7 | 1474.6 | 3332.9 | 10094.4 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-07T22:39:05.014000+00:00 → 2026-11-07T23:16:45.817000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-bilan-avant-1.csv`) | ✅ 55416 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-14316` | 0.99 | 14 | 31 | 0.025 | 43.02 |
| `DESKTOP-DEV-X2C-51012` | 1.06 | 10 | 25 | 0.035 | 62.06 |
| `DESKTOP-DEV-X2C-59160` | 1.04 | 8 | 24 | 0.023 | 50.44 |
| `DESKTOP-DEV-X2C-6340` | 1.15 | 12 | 24 | 0.024 | 53.53 |
| `DESKTOP-DEV-X2C-63472` | 1.07 | 15 | 41 | 0.032 | 52.01 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.67 | 4.58 | 2565 |
| `com.docker.backend#34124` | 0.00 | 0.09 | 40 |
| `dcp#11092` | 0.77 | 2.49 | 3219 |
| `dcp#28432` | 0.00 | 0.04 | 12 |
| `dcp#30892` | 0.00 | 0.00 | 12 |
| `dcp#30956` | 0.00 | 0.09 | 52 |
| `dcp#32136` | 0.00 | 0.00 | 13 |
| `dcp#35544` | 0.00 | 0.08 | 14 |
| `dcp#44580` | 0.00 | 0.00 | 12 |
| `dcp#55708` | 0.00 | 0.08 | 14 |
| `dcp#60800` | 0.00 | 0.00 | 12 |
| `dcp#61600` | 0.00 | 0.00 | 12 |
| `dcp#61696` | 0.00 | 0.00 | 12 |
| `dcp#64292` | 0.00 | 0.00 | 12 |
| `dcp#65856` | 0.00 | 0.00 | 12 |
| `dcp#69528` | 0.00 | 0.00 | 12 |
| `dcp#70392` | 0.00 | 0.08 | 13 |
| `k6#239652` | 0.77 | 1.87 | 2865 |
| `mss.mail.api#14316` | 0.73 | 2.85 | 2225 |
| `mss.mail.api#51012` | 0.71 | 2.88 | 2243 |
| `mss.mail.api#59160` | 0.65 | 1.96 | 2251 |
| `mss.mail.api#6340` | 0.71 | 2.23 | 2315 |
| `mss.mail.api#63472` | 0.76 | 2.54 | 2324 |
| `mss.mail.e2e#67596` | 0.01 | 0.18 | 34 |
| `vmmemWSL#36464` | 6.85 | 11.68 | 56880 |
| `loadtest-otel-collector-qyfstqva` | 0.03 | 0.17 | 101 |
| `loadtest-pgbouncer-bqskafnt` | 0.52 | 0.95 | 48 |
| `mss-mail-flagsmith-app-b6152948` | 0.12 | 0.46 | 471 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.11 | 150 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.07 | 160 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.49 | 201 |
| `mss-mail-rabbitmq-afthdrgn` | 0.01 | 0.05 | 136 |
| `mss-mail-redis-b6152948` | 0.26 | 1.35 | 968 |
| `mss-mail-rediscommander-cwszdwtd` | 0.00 | 0.22 | 24 |
| `mss-mail-seq-b6152948` | 0.10 | 0.98 | 6811 |
| `postgres-pgvector` | 3.35 | 9.49 | 46664 |

- **Hôte** : CPU 72.1 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 47
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9613, cl_waiting max 30, cl_waiting_maintenance max 30, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 183, maxwait_ms max 183, maxwait_practitioner_ms max 0, sv_active max 84, sv_idle max 1710, sv_login max 2
- **Backends Postgres** : audit max 5, cache_mb max 41431, direct max 30, idle_over_60s max 477, majfault_per_s max 24, pooler max 2002, practitioner_databases max 1993, provision max 5, rss_mb max 6050, started_last_60s max 466, total max 2033, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 7244.9 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2549.5 | 450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 2163.2 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2383.6 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 2262.7 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 2162.5 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 2125.7 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2151.4 | 447 |
| `api/v{version:apiVersion}/Mail/sendmail` | 60000.0 | 432 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1988.0 | 444 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 2288.7 | 444 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 1931.3 | 444 |
| `api/v{version:apiVersion}/Search/semantic` | 2317.1 | 444 |
| `api/v{version:apiVersion}/Sync/coverage` | 1895.3 | 447 |

- **p95 client global (k6)** : 829.2 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -59170.8 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.44 |
| Documents CDA /s | 0.44 |
| Durée traitement CDA (s, p95) | 1.60 |
| Événements de session IMAP /s | 5.71 |
| Recherches (s, p95) | 1.596 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 115.6 | 550 | 0.0 (0.0 %), p95 5 | 73.4 (63.5 %), p95 550 | 42.1 (36.5 %), p95 205 |
| `GetMail` | 11.1 | 68.7 | 592 | 6.0 (8.7 %), p95 91 | 58.9 (85.7 %), p95 520 | 3.9 (5.6 %), p95 55 |
| `GetMailsByUids` | 14.7 | 92.3 | 498 | 0.1 (0.1 %), p95 5 | 80.3 (87.0 %), p95 488 | 11.9 (12.9 %), p95 58 |

- **`EnrichPersistMail`** — sur 115.6 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 73.4 ms exécution SQL, 42.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 68.7 ms en moyenne (11.1 requête(s) SQL par appel) : 6.0 ms attente d'une connexion, 58.9 ms exécution SQL, 3.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 92.3 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 80.3 ms exécution SQL, 11.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.9 | 361.9 | 0.9 | 1.4 | 0.9 | 2.7 | non relevé | 0.0 | 0.9 | 2.8 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 206.2 | 11.9 | 57.5 | 18.6 | 28.5 | 18.6 | 30.3 | 18.6 | 0.0 | 18.6 | 5.9 | 0.0 | 18.5 | 44.6 | 4.0 |

- **`GetMail`** — sur 3.9 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.7 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.8 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **361.9 µs**.

- **`GetMailsByUids`** — sur 11.9 ms de matérialisation, l'appel a construit 206.2 objets, dont 18.6 messages, 28.5 étiquettes, 18.6 destinataires, 30.3 pièces jointes, 18.6 identifiants enrichis, 0.0 acquittements, 18.6 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.5 corps de messages, 44.6 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **57.5 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3846.2 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 424.8 | 2350 | 135.8 (32.0 %), p95 425 | 16.7 (3.9 %), p95 160 | 102.1 (24.0 %), p95 2050 | 95.5 (22.5 %), p95 550 | 74.6 (17.6 %), p95 242 |

- **Enrichir un message** — sur 424.8 ms en moyenne (3.8 message(s) par requête) : 135.8 ms fetch IMAP, 16.7 ms extraction XDM, 102.1 ms parsing CDA, 95.5 ms écritures base, 74.6 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 239.4 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 26744.9 | 23062 | 0.0 (0.0 %), p95 5 | 27.7 (0.1 %), p95 81 | 12892.1 (48.2 %), p95 19491 | 9404.6 (35.2 %), p95 18689 | 406.7 (1.5 %), p95 908 | 4377.4 (16.4 %), p95 12095 |

- **Envoyer un message** — sur 26744.9 ms en moyenne : 0.0 ms garde d'opposition, 27.7 ms construction MIME, 12892.1 ms obtention de session SMTP, 9404.6 ms transmission + acquittement, 406.7 ms archivage Sent, 4377.4 ms le reste. **Poste dominant : obtention de session SMTP.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.455 | 2.350 | 107.68 |
| `smtp_session` | 13.125 | ≥ 60 ⚠️ | 9.93 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.483 | 2.356 | 0.629 | 15.22 |
| `EnrichEmails` | 0.005 | 0.475 | — | 0.475 | 0.67 |
| `GetAttachmentStream` | 0.471 | 2.350 | 2.425 | 0.678 | 0.44 |
| `GetEmailContent` | 0.005 | 0.703 | — | 0.703 | 13.73 |
| `GetFolders` | 0.005 | 0.983 | 0.985 | 0.243 | 9.42 |
| `ReadFolder` | 0.837 | 2.375 | 2.425 | 0.568 | 39.44 |
| `ReadToday` | 0.035 | 0.615 | 2.425 | 0.615 | 16.71 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 27.80 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.350** | 0.454 | 0.475 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.489 | 0.490 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.426** | 0.449 | 0.454 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.492 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.488 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 107.68 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.837 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 30.00 clients | 0 clients | 100.0 % | 38.2 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 9.49 cœurs | 24 cœurs | 39.5 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-63472` | 15.00 éléments | 100 éléments | 15.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#51012` (CPU) | 2.88 cœurs | 24 cœurs | 12.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#14316` (CPU) | 2.85 cœurs | 24 cœurs | 11.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#63472` (CPU) | 2.54 cœurs | 24 cœurs | 10.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#6340` (CPU) | 2.23 cœurs | 24 cœurs | 9.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#59160` (CPU) | 1.96 cœurs | 24 cœurs | 8.2 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 38.2 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 198 835

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 2 404 |
| OpenAI | gpt-4o-mini | prompt | 196 431 |
| OpenAI | text-embedding-3-small | embedding | 326 293 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 111 | 0 (0.0 %) | 0 | 2.9 | 1.09 | 0.96 | 2.39 |
| étiquetage (chat) | OpenAI | 111 | 0 (0.0 %) | 0 | 2.9 | 1.06 | 0.94 | 2.38 |
| embedding | OpenAI | 112 | 0 (0.0 %) | 0 | 3.0 | 0.57 | 0.51 | 1.45 |

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
| GPU — utilisation (%) | 0.2 | 5.0 |
| GPU — VRAM occupée (Mo) | 1 443 | 1 628 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **6 258.5** | annulées : 0.0 % |
| Backends actifs (équivalent) | **2.32** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **7.8 ms** | sur 687 365 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.25 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **19.99 Mo/s (2 559 blocs/s)** | attente disque : 11.4 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **485 669 / 43 264** | rapport 11.2 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **149.3** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.27 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **7 / 0** | blocs écrits par les backends eux-mêmes : 18 % |
| Sessions ouvertes / s | **3.21** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **39.9 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 552 / 2 033** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **98 / 100 %** | fautes majeures/s max : 23.7 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 732.1 s | 43507 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body : 92.3 Go lus, 0.3 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 26.4 % du temps SQL, 1.8 % des lectures disque du tir | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 700.0 s | 43520 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body : 107.7 Go lus, 0.8 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 25.2 % du temps SQL, 5.2 % des lectures disque du tir | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 225.7 s | 154813 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, Embedding, HtmlBody, MetadataJson : 20.9 Go lus, 5.2 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 8.1 % du temps SQL, 34.4 % des lectures disque du tir | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 109.4 s | 2037187 | `appels-par-requete` | 2.96 appels par requête HTTP : relecture ou surcoût de session (cache, invalidation, `No Reset On Close`) | — | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 96.1 s | 2037187 | `appels-par-requete` | 2.96 appels par requête HTTP : relecture ou surcoût de session (cache, invalidation, `No Reset On Close`) | — | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 87.4 s | 4896032 | `appels-par-requete` | 7.12 appels par requête HTTP : relecture ou surcoût de session (cache, invalidation, `No Reset On Close`) | — | `DISCARD ALL` |
| 82.3 s | 3014 | `pages-par-ligne`, `colonne-volumineuse`, `poids-dans-le-tir` | 15.8 pages par ligne rendue, 461 par appel, 10.6 Go lus · sélectionne Content : 10.6 Go lus, 4.1 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 3.0 % du temps SQL, 27.2 % des lectures disque du tir | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 65.1 s | 41795 | `pages-par-ligne`, `sous-requete-correlee` | 25.1 pages par ligne rendue, 256 par appel, 81.6 Go lus · sous-requête corrélée dans une forme qui lit beaucoup de pages par ligne : index sur la clé de corrélation, ou un seul agrégat groupé joint | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 61.5 s | 6926 | `pages-par-ligne` | 31.2 pages par ligne rendue, 624 par appel, 33.0 Go lus | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 54.5 s | 154702 | `colonne-volumineuse` | sélectionne Body, BodyHtml, Embedding : 10.0 Go lus, 0.3 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 49.0 s | 7045 | `pages-par-ligne` | 31.4 pages par ligne rendue, 628 par appel, 33.7 Go lus | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 28.9 s | 12313 | `colonne-volumineuse` | sélectionne Content : 2.3 Go lus, 1.3 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | — | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **78 évictions `pg_stat_statements`** pendant le tir (96 409 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

132 formes de requête, 14 482 949 appels, **46.3 min** de temps serveur cumulé — soit **4.0 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **26.4 %** | 26 % | 43 507 | 0.06 | 16.83 | 32.7 | 278 | 0 % | 0 | 1 980 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 2 | **25.2 %** | 52 % | 43 520 | 0.06 | 16.09 | 32.7 | 324 | 1 % | 0 | 1 980 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 3 | **8.1 %** | 60 % | 154 813 | 0.23 | 1.46 | 1.0 | 18 | 25 % | 0 | 1 877 | **Code** — 25 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **3.9 %** | 64 % | 2 037 187 | 2.96 | 0.05 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 5 | **3.5 %** | 67 % | 2 037 187 | 2.96 | 0.05 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 6 | **3.1 %** | 70 % | 4 896 032 | 7.12 | 0.02 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | — | `DISCARD ALL` |
| 7 | **3.0 %** | 73 % | 3 014 | 0.00 | 27.31 | 29.2 | 461 | 39 % | 0 | 389 | **Code** — 39 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 8 | **2.7 %** | 76 % | 81 845 | 0.12 | 0.90 | 17.8 | 99 | 0 % | 0 | 1 996 | — | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 9 | **2.3 %** | 78 % | 41 795 | 0.06 | 1.56 | 10.2 | 256 | 0 % | 0 | 1 415 | — | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 10 | **2.2 %** | 80 % | 6 926 | 0.01 | 8.88 | 20.0 | 624 | 4 % | 0 | 709 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 11 | **2.0 %** | 82 % | 154 702 | 0.23 | 0.35 | 1.0 | 8 | 3 % | 0 | 1 874 | — | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 12 | **1.8 %** | 84 % | 7 045 | 0.01 | 6.95 | 20.0 | 628 | 3 % | 0 | 720 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 13 | **1.6 %** | 86 % | 687 274 | 1.00 | 0.07 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 14 | **1.4 %** | 87 % | 118 896 | 0.17 | 0.33 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 15 | **1.1 %** | 88 % | 6 410 | 0.01 | 4.68 | 178.0 | 540 | 1 % | 0 | 1 100 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 16 | **1.0 %** | 89 % | 12 313 | 0.02 | 2.35 | 1.0 | 25 | 54 % | 0 | 1 062 | **Code** — 54 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | — | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 17 | **0.8 %** | 90 % | 259 827 | 0.38 | 0.09 | 1.3 | 16 | 0 % | 0 | 1 996 | — | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 18 | **0.8 %** | 91 % | 83 602 | 0.12 | 0.26 | 18.0 | 5 | 0 % | 0 | 1 598 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **0.6 %** | 92 % | 259 828 | 0.38 | 0.07 | 2.0 | 4 | 0 % | 0 | 1 996 | — | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 20 | **0.5 %** | 92 % | 81 838 | 0.12 | 0.18 | 17.8 | 5 | 0 % | 0 | 1 996 | — | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.5 % | 61.6 % |
| INSERT | 2.0 % | 1.1 % |
| UPDATE | 0.2 % | 0.5 % |
| DELETE | 0.0 % | 0.2 % |
| AUTRE | 3.3 % | 36.6 % |
| bases : praticien (N bases) | 89.3 % | 65.3 % |
| bases : unique (1 base) | 10.7 % | 34.7 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **27.3** | 464 | 3 014 | 3.0 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **16.8** | 264 | 43 507 | 26.4 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailCo…` |
| **16.1** | 264 | 43 520 | 25.2 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMe…` |
| **8.9** | 375 | 6 926 | 2.2 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **7.0** | 111 | 7 045 | 1.8 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 1 011 | 250 728 | 222 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 339 | 159 341 | 0 | 5 | 0.1 Mo |
| `Mails` | 783 | 101 266 | 724 | 26 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 122 | 31 842 | 164 | 43 | 30.0 Mo |
| `MailRecipients` | 180 | 28 080 | 56 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 165 | 25 145 | 1 236 | 157 | 8.0 Mo |
| `MailContents` ⚠️ index candidat | 42 | 6 552 | 2 210 | 156 | 1.9 Mo |
| `PendingActions` | 168 | 4 965 | 0 | 31 | 0.1 Mo |
| `Tags` | 139 | 2 502 | 84 | 0 | 0.0 Mo |
| `MailFolders` | 369 | 1 004 | 362 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🔴 | requête n°1 (26.4 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Code | 🟠 | requête n°3 (8.1 % du temps SQL) — 25 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Postgres | 🟠 | taux de cache 96.2 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | 11 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailAttachments` balayée 122 fois (31842 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 165 fois (25145 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 42 fois (6552 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°7 (3.0 % du temps SQL) — 39 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Code | 🟡 | requête n°16 (1.0 % du temps SQL) — 54 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°4 (3.9 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°6 (3.1 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Infra | 🟡 | requête n°15 (1.1 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°10 (2.2 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-001729.tsv`, `pgserver-journey-debut-233856.tsv`, `pgserver-journey-fin-001733.tsv`, `pgtables-journey-debut-233900.tsv`, `pgtables-journey-fin-001738.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 247884 — dont **247884** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261107-bilan-avant-1-001645.jsonl`.

Requêtes `/api/data` sur la fenêtre du tir, 22:38:54 → 23:16:45 UTC le 2026-11-07.

- **❌ Panne du serveur SMTP du banc (GreenMail, cluster), de 22:51:45 à 23:02:12 UTC.** 2 606 erreurs :
  - 1 006 `[SendMailAsync] Failed to send email` : `TaskCanceledException` pendant la négociation TLS (`SslStream.EnsureFullTlsFrameAsync`), et `SmtpProtocolException` « The SMTP server has unexpectedly disconnected » en pleine phase DATA ;
  - 342 `SMTP connection failed` (dont 120 « A task was canceled ») et leurs 342 `[CreateConnectedClientAsync] Failed to create SMTP connection` ;
  - 458 réponses HTTP 500 (`Unhandled exception`) sur l'envoi.
- **Effet** : obtention de session SMTP 12,9 s en moyenne par envoi, transmission 9,4 s. Envoi p50 31,7 s au palier 1400, p95 32 s au palier 1996. Les médecins bloqués dans l'envoi émettent 9 % de requêtes en moins, ce qui allège toutes les autres étapes.
- **Cause côté banc, pas côté API** : le même code A tourne sans une erreur au tir avant-2 (01:09). L'état du pod GreenMail n'a pas pu être relevé, le poste n'a pas d'accès `kubectl`. Hypothèse non vérifiée : tas JVM de GreenMail rempli par les envois des tirs précédents.
- **Récidive** du tir A2 du 2026-11-07 (task-432, VOID pour la même cause). Le rapport classe pourtant ce tir ORANGE « exploitable » : aucun contrôle de validité ne voit une panne du serveur SMTP du banc.
- **Marqueurs de régression** : `Failed to parse entity headers` 0, `SecurityTokenMalformedException` 0, événements `Debug` 0 (niveau de log nominal).
- **429** : 0. **Échecs d'embedding** : 0. **Reprises d'étiquetage IA** (`[TaggingRecovery]`) : 0.
- **Parsings CDA** (`Parsing completed`) : 0. Attendu : population hydratée (`JOURNEY_WARMUP_HYDRATED=1`), le tir n'analyse aucun nouveau document.
- **Avertissements bénins**, du même ordre dans les trois tirs : `[TlsCertificateValidationSession] Allowing untrusted certificate` (~15 000, certificat auto-signé du banc), `[MailClientSession] ♻️ Session expired` (~5 000, recyclage nominal), `[PractitionerContactPublisher] SKIPPED - Invalid RPPS` (≤ 16, identités synthétiques).
