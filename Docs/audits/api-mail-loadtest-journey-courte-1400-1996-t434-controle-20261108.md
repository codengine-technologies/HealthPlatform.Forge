# Rapport de tir — journey-courte-1400-1996-20261108-t434-controle

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261108-t434-controle-141356.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 1 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 20 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.013 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 763477 — **débit émergent global** : 337.9 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 54106 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 337.9 | **139.1** | 59.2 | **495.9** | — | 10360.4 | 0.01 | 100.0 | 0 | 0 | 248216/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214257 | 290.72 | 0.00 | 774.5 |
| **1996 médecins** | 1080 | 933 | 388452 | 416.35 | 0.01 | 1422.5 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 59 / 543 (n=63984) | 65 / 639 (n=114996) |
| 2 | Ouvrir / rafraîchir l'inbox | 40 / 92 (n=31978) | 52 / 136 (n=57428) |
| 3 | Ouvrir un message enrichi (servi base) | 33 / 61 (n=15983) | 48 / 106 (n=28747) |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 / 509 (n=6397) | 452 / 519 (n=11526) |
| 5 | Recherche | 324 / 742 (n=4858) | 349 / 616 (n=8575) |
| 6 | Envoi (acquittement UI) | 502 / 926 (n=4731) | 485 / 948 (n=8479) |
| 7 | Télécharger une PJ (~124 Ko) | 36 / 68 (n=6357) | 54 / 124 (n=11585) |
| 8 | Marquer lu | 34 / 82 (n=12725) | 54 / 107 (n=23075) |
| 9 | Rechercher un patient | 55 / 64 (n=4722) | 56 / 76 (n=8663) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 65 (n=7064) | 59 / 77 (n=13124) |
| 11 | Fiche patient complète (ressenti médecin) | 260 / 427 (n=3532) | 348 / 681 (n=6562) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.6 / 20 | 34.4 / 60 | 7962 | 427 |
| **1996 médecins** | 14.5 / 20 | 34.1 / 60 | 14520 | 681 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2261 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 569 ms en moyenne, 10360 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> ⚠️ **Rectification (task-435, 2026-11-08) — ventilation fausse.** Depuis task-404 (2026-10-29), l'échantillonneur ne reconnaissait plus les bases praticien (nommage `u_l…`). Les lignes « dont bases **praticien** » valent donc 0 à tort, et « dont pool de **maintenance** — sonde de readiness » porte en réalité l'attente du chemin du médecin : la sonde de readiness ne traverse plus le pooler depuis task-249. La ligne « Login PostgreSQL depuis le conteneur » est « non relevé » pour la même cause. Le total `cl_waiting` et `maxwait` restent justes. Mesure corrigée : tir de qualification de task-435 (`api-mail-loadtest-journey-courte-1400-1996-t435-qualif-20261108.md`).

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2265 / 3133 (magasin) | 2265 / 3133 (magasin) |
| Backends Postgres (moy/max) | 1243 / 1437 | 1988 / 2025 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 3 |
| PgBouncer `cl_waiting` (échant. non nuls) | 37/188 (20 %) | 48/160 (30 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/188 (0 %) | 0/160 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 37/188 (20 %) | 48/160 (30 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 43.3 | 274.4 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 43.3 | 274.4 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 121 / 415 | 96 / 271 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 121 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1407 | 1993 |
| Backends **directs** — audit + provisionnement (max) | 29 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 4 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 96.6 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 | 0 / 1 |
| RSS par réplica api-mail, Mo (moy/max) | 1149 / 1573 (5 réplicas) | 2031 / 2315 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1437.0 / 2500** (57.5 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2025.0 / 2500** (81.0 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 99.9 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15983)
- palier 1996 : cohorte 1996 chauffée à 99.7 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28747)

> ⓘ Chauffe : **301 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 59 (300) | 543 (1500) | 63984 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 40 (300) | 92 (1000) | 31978 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 33 (100) | 61 (500) | 15983 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 (800) | 509 (2500) | 6397 | ✅ |
| 5 | Recherche | 324 (500) | 742 (2000) | 4858 | ✅ |
| 6 | Envoi (acquittement UI) | 502 (1000) | 926 (3000) | 4731 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 36 (500) | 68 (2000) | 6357 | ✅ |
| 8 | Marquer lu | 34 (200) | 82 (1000) | 12725 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 64 (1500) | 4722 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 65 (2000) | 7064 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 260 (1500) | 427 (4000) | 3532 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 65 (300) | 639 (1500) | 114996 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 52 (300) | 136 (1000) | 57428 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 48 (100) | 106 (500) | 28747 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 452 (800) | 519 (2500) | 11526 | ✅ |
| 5 | Recherche | 349 (500) | 616 (2000) | 8575 | ✅ |
| 6 | Envoi (acquittement UI) | 485 (1000) | 948 (3000) | 8479 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 54 (500) | 124 (2000) | 11585 | ✅ |
| 8 | Marquer lu | 54 (200) | 107 (1000) | 23075 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 76 (1500) | 8663 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 77 (2000) | 13124 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 348 (1500) | 681 (4000) | 6562 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114996 | 162 | 639 | 18648.1 | 44.8 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8479 | 625 | 948 | 5295.6 | 12.7 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11526 | 454 | 519 | 5230.8 | 12.6 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57428 | 60 | 136 | 3425.6 | 8.2 % |
| 🟢 | Recherche (`search`) | 8575 | 398 | 616 | 3416.4 | 8.2 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28747 | 56 | 106 | 1603.2 | 3.9 % |
| 🟢 | Marquer lu (`mark_read`) | 23075 | 60 | 107 | 1384.4 | 3.3 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11585 | 68 | 124 | 791.4 | 1.9 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7260 | 102 | 153 | 742.4 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8663 | 49 | 76 | 421.0 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6562 | 59 | 77 | 386.3 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6562 | 38 | 71 | 250.5 | 0.6 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 1 🟠 · 11 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 18648.1 s, 44.8 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 9.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15996 | 391 | 980 | 6136.5 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15996 | 58 | 495 | 2177.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15996 | 19 | 162 | 712.9 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15996 | 56 | 67 | 916.4 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15989 | 15 | 114 | 472.7 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15989 | 49 | 81 | 853.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28749 | 398 | 970 | 11274.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28749 | 64 | 503 | 4015.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28749 | 30 | 180 | 1611.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28749 | 60 | 82 | 1747.9 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28714 | 22 | 125 | 1095.3 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28714 | 72 | 143 | 2330.3 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (970 ms de p95, 398 ms de p50, n=28749), qui porte **aussi** le temps serveur de l'étape (11274.2 s, 60 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (143 ms de p95, 72 ms de p50, n=28714), qui porte **aussi** le temps serveur de l'étape (2330.3 s, 68 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21968 | 68.4 | 45.5 | 100.6 | 159.6 | 1514.2 |
| attachment,palier:1400 | 6357 | 40.3 | 36.0 | 56.3 | 67.8 | 442.0 |
| attachment,palier:1996 | 11585 | 68.3 | 53.9 | 100.5 | 123.9 | 1148.6 |
| attachment,palier:transition | 591 | 127.1 | 47.7 | 345.5 | 394.4 | 1164.7 |
| dashboard | 220928 | 166.5 | 63.2 | 469.8 | 631.5 | 1687.3 |
| dashboard,call:coverage,palier:1400 | 15996 | 57.3 | 56.4 | 63.2 | 66.5 | 187.2 |
| dashboard,call:coverage,palier:1996 | 28749 | 60.8 | 60.4 | 75.2 | 82.3 | 522.4 |
| dashboard,call:coverage,palier:transition | 1019 | 107.6 | 92.0 | 183.9 | 222.0 | 1233.0 |
| dashboard,call:folder,palier:1400 | 15996 | 383.6 | 391.0 | 760.2 | 980.3 | 1517.1 |
| dashboard,call:folder,palier:1996 | 28749 | 392.2 | 397.7 | 770.6 | 969.7 | 1564.0 |
| dashboard,call:folder,palier:transition | 1019 | 458.0 | 469.5 | 720.8 | 826.7 | 1687.3 |
| dashboard,call:folders,palier:1400 | 15996 | 44.6 | 19.3 | 147.6 | 162.3 | 397.8 |
| dashboard,call:folders,palier:1996 | 28749 | 56.0 | 29.7 | 160.4 | 180.0 | 700.0 |
| dashboard,call:folders,palier:transition | 1019 | 105.1 | 95.3 | 198.4 | 258.1 | 576.3 |
| dashboard,call:today,palier:1400 | 15996 | 136.1 | 58.3 | 475.5 | 495.4 | 780.9 |
| dashboard,call:today,palier:1996 | 28749 | 139.7 | 63.6 | 479.8 | 502.6 | 767.1 |
| dashboard,call:today,palier:transition | 1019 | 318.6 | 260.7 | 601.2 | 644.7 | 1536.4 |
| dashboard,palier:1400 | 63984 | 155.4 | 58.5 | 456.2 | 543.0 | 1517.1 |
| dashboard,palier:1996 | 114996 | 162.2 | 64.6 | 462.7 | 639.5 | 1564.0 |
| dashboard,palier:transition | 4076 | 247.3 | 138.1 | 571.3 | 633.3 | 1687.3 |
| mark_read | 44123 | 62.1 | 49.4 | 94.4 | 119.3 | 1253.6 |
| mark_read,palier:1400 | 12725 | 46.2 | 34.1 | 76.1 | 81.8 | 313.1 |
| mark_read,palier:1996 | 23075 | 60.0 | 54.2 | 94.2 | 107.0 | 592.9 |
| mark_read,palier:transition | 1191 | 88.4 | 68.8 | 203.9 | 254.7 | 1253.6 |
| patient_docs | 179399 | 69.6 | 52.1 | 122.3 | 166.3 | 2243.7 |
| patient_docs,palier:1400 | 51477 | 44.6 | 41.7 | 78.7 | 92.3 | 460.7 |
| patient_docs,palier:1996 | 94985 | 66.9 | 57.9 | 125.5 | 153.1 | 825.6 |
| patient_docs,palier:transition | 5167 | 113.1 | 55.4 | 329.5 | 440.9 | 2243.7 |
| patient_dossier | 12366 | 38.9 | 28.6 | 58.9 | 82.2 | 448.2 |
| patient_dossier,palier:1400 | 3532 | 25.8 | 23.5 | 33.5 | 40.3 | 230.5 |
| patient_dossier,palier:1996 | 6562 | 38.2 | 33.3 | 59.1 | 70.7 | 255.0 |
| patient_dossier,palier:transition | 344 | 59.9 | 28.5 | 164.8 | 199.2 | 296.6 |
| patient_opposition | 12366 | 60.3 | 57.8 | 70.9 | 80.2 | 601.0 |
| patient_opposition,palier:1400 | 3532 | 56.7 | 56.0 | 61.4 | 64.7 | 178.8 |
| patient_opposition,palier:1996 | 6562 | 58.9 | 59.4 | 71.5 | 76.7 | 148.7 |
| patient_opposition,palier:transition | 344 | 67.7 | 57.6 | 106.8 | 126.9 | 189.5 |
| patient_search | 16431 | 49.6 | 55.6 | 70.2 | 80.6 | 1391.8 |
| patient_search,palier:1400 | 4722 | 44.6 | 55.4 | 61.0 | 63.9 | 140.0 |
| patient_search,palier:1996 | 8663 | 48.6 | 56.3 | 70.8 | 76.2 | 211.5 |
| patient_search,palier:transition | 468 | 59.2 | 56.1 | 101.5 | 122.5 | 1391.8 |
| read_content | 55232 | 57.4 | 40.9 | 87.7 | 124.8 | 1708.6 |
| read_content,palier:1400 | 15983 | 36.3 | 33.4 | 50.0 | 60.6 | 356.1 |
| read_content,palier:1996 | 28747 | 55.8 | 48.4 | 88.9 | 106.2 | 694.3 |
| read_content,palier:transition | 1375 | 101.5 | 42.8 | 285.9 | 349.5 | 1708.6 |
| read_content_cold | 22084 | 454.2 | 449.6 | 505.9 | 527.2 | 978.5 |
| read_content_cold,palier:1400 | 6397 | 445.7 | 444.4 | 493.9 | 509.3 | 654.0 |
| read_content_cold,palier:1996 | 11526 | 453.8 | 451.6 | 503.5 | 519.3 | 968.9 |
| read_content_cold,palier:transition | 576 | 466.9 | 455.4 | 543.0 | 588.4 | 717.2 |
| read_list | 110464 | 61.2 | 45.6 | 113.4 | 151.3 | 2764.6 |
| read_list,call:emails,palier:1400 | 15989 | 53.4 | 49.4 | 70.4 | 81.1 | 407.6 |
| read_list,call:emails,palier:1996 | 28714 | 81.2 | 72.3 | 122.0 | 142.8 | 629.9 |
| read_list,call:emails,palier:transition | 1232 | 163.3 | 68.4 | 402.0 | 479.5 | 2764.6 |
| read_list,call:folder,palier:1400 | 15989 | 29.6 | 15.1 | 33.4 | 114.0 | 533.9 |
| read_list,call:folder,palier:1996 | 28714 | 38.1 | 21.7 | 59.9 | 124.8 | 592.3 |
| read_list,call:folder,palier:transition | 1232 | 58.9 | 21.2 | 140.8 | 187.3 | 617.0 |
| read_list,palier:1400 | 31978 | 41.5 | 39.7 | 66.9 | 91.6 | 533.9 |
| read_list,palier:1996 | 57428 | 59.6 | 51.6 | 113.0 | 135.7 | 629.9 |
| read_list,palier:transition | 2464 | 111.1 | 60.1 | 330.1 | 412.8 | 2764.6 |
| search | 16613 | 401.6 | 342.7 | 530.5 | 780.4 | 2068.5 |
| search,palier:1400 | 4858 | 383.0 | 324.2 | 477.9 | 741.9 | 1625.6 |
| search,palier:1996 | 8575 | 398.4 | 349.4 | 486.6 | 615.8 | 1590.7 |
| search,palier:transition | 466 | 431.2 | 343.0 | 649.3 | 815.2 | 1822.0 |
| send | 15657 | 645.1 | 509.2 | 919.2 | 951.2 | 1956.8 |
| send,palier:1400 | 4731 | 638.9 | 501.9 | 903.3 | 926.0 | 1027.2 |
| send,palier:1996 | 8479 | 624.6 | 484.9 | 918.2 | 947.6 | 1337.1 |
| send,palier:transition | 442 | 645.1 | 563.8 | 936.3 | 997.8 | 1252.5 |
| treatment | 13876 | 101.3 | 84.7 | 133.1 | 183.3 | 3623.5 |
| treatment,palier:1400 | 3981 | 73.3 | 79.2 | 95.6 | 105.4 | 315.8 |
| treatment,palier:1996 | 7260 | 102.3 | 90.6 | 132.9 | 153.3 | 3623.5 |
| treatment,palier:transition | 343 | 154.5 | 87.6 | 375.8 | 430.2 | 964.5 |
| warmup | 21956 | 569.4 | 384.9 | 681.3 | 1725.7 | 10360.4 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-08T12:36:17.163000+00:00 → 2026-11-08T13:13:56.469000+00:00 (2259 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t434-controle.csv`) | ✅ 77755 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-49636` | 0.91 | 12 | 31 | 0.036 | 4.65 |
| `DESKTOP-DEV-X2C-68068` | 0.89 | 12 | 33 | 0.030 | 4.58 |
| `DESKTOP-DEV-X2C-73788` | 0.99 | 14 | 44 | 0.032 | 4.78 |
| `DESKTOP-DEV-X2C-79016` | 0.98 | 17 | 31 | 0.025 | 4.89 |
| `DESKTOP-DEV-X2C-79852` | 1.02 | 12 | 31 | 0.032 | 4.84 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.22 | 4.95 | 2490 |
| `com.docker.backend#34124` | 0.00 | 0.09 | 40 |
| `dcp#17864` | 0.00 | 0.04 | 12 |
| `dcp#26768` | 0.00 | 0.04 | 14 |
| `dcp#29344` | 0.00 | 0.17 | 12 |
| `dcp#42632` | 0.00 | 0.04 | 13 |
| `dcp#47440` | 0.00 | 0.22 | 14 |
| `dcp#49392` | 0.00 | 0.04 | 14 |
| `dcp#55184` | 0.00 | 0.00 | 12 |
| `dcp#60088` | 0.00 | 0.04 | 12 |
| `dcp#60908` | 0.00 | 0.04 | 12 |
| `dcp#63708` | 0.80 | 2.23 | 3238 |
| `dcp#65256` | 0.00 | 0.00 | 12 |
| `dcp#71692` | 0.00 | 0.13 | 12 |
| `dcp#72428` | 0.00 | 0.22 | 51 |
| `dcp#72568` | 0.00 | 0.04 | 12 |
| `dcp#77676` | 0.00 | 0.00 | 12 |
| `k6#293149` | 0.78 | 1.68 | 2883 |
| `mss.mail.api#49636` | 0.63 | 2.69 | 2186 |
| `mss.mail.api#68068` | 0.61 | 2.51 | 2148 |
| `mss.mail.api#73788` | 0.66 | 2.74 | 2340 |
| `mss.mail.api#79016` | 0.66 | 3.03 | 2311 |
| `mss.mail.api#79852` | 0.65 | 2.59 | 2208 |
| `mss.mail.e2e#74048` | 0.00 | 0.13 | 38 |
| `vmmemWSL#36464` | 5.33 | 12.26 | 60387 |
| `loadtest-otel-collector-ggzwkwrx` | 0.02 | 0.14 | 114 |
| `loadtest-pgbouncer-xesqppte` | 0.43 | 0.89 | 53 |
| `mss-mail-flagsmith-app-b6152948` | 0.12 | 0.43 | 472 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.12 | 162 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.05 | 161 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.16 | 314 |
| `mss-mail-rabbitmq-dmyjzppy` | 0.01 | 0.04 | 154 |
| `mss-mail-redis-b6152948` | 0.27 | 1.35 | 985 |
| `mss-mail-rediscommander-qwfwpteh` | 0.00 | 0.21 | 70 |
| `mss-mail-seq-b6152948` | 0.11 | 2.58 | 5767 |
| `postgres-pgvector` | 2.02 | 8.01 | 46725 |

- **Hôte** : CPU 63.3 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 69
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9474, cl_waiting max 20, cl_waiting_maintenance max 20, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 274, maxwait_ms max 274, maxwait_practitioner_ms max 0, sv_active max 70, sv_idle max 1594, sv_login max 3
- **Backends Postgres** : audit max 5, cache_mb max 39662, direct max 29, idle_over_60s max 195, majfault_per_s max 1, pooler max 1993, practitioner_databases max 1989, provision max 4, rss_mb max 6183, started_last_60s max 415, total max 2025, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 7361.5 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2425.0 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 714.7 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 731.2 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 737.5 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 651.8 | 442 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 461.6 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 722.6 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2069.2 | 433 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 229.3 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 419.3 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 225.9 | 442 |
| `api/v{version:apiVersion}/Search/semantic` | 1259.1 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 311.3 | 447 |

- **p95 client global (k6)** : 495.9 ms
- **p95 serveur le plus élevé** : 7361.5 ms
- **Écart** : -6865.6 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.69 |
| Documents CDA /s | 0.73 |
| Durée traitement CDA (s, p95) | 2.23 |
| Événements de session IMAP /s | 4.24 |
| Recherches (s, p95) | 1.259 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.0 | 63.7 | 242 | 0.0 (0.0 %), p95 5 | 38.7 (60.7 %), p95 175 | 25.0 (39.3 %), p95 223 |
| `GetMail` | 11.1 | 44.0 | 561 | 4.1 (9.4 %), p95 84 | 36.3 (82.6 %), p95 479 | 3.5 (8.0 %), p95 106 |
| `GetMailsByUids` | 14.7 | 68.6 | 487 | 0.1 (0.1 %), p95 5 | 58.1 (84.7 %), p95 475 | 10.4 (15.2 %), p95 67 |

- **`EnrichPersistMail`** — sur 63.7 ms en moyenne (8.0 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 38.7 ms exécution SQL, 25.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 44.0 ms en moyenne (11.1 requête(s) SQL par appel) : 4.1 ms attente d'une connexion, 36.3 ms exécution SQL, 3.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 68.6 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 58.1 ms exécution SQL, 10.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.8 | 3.5 | 325.8 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.1 | 10.4 | 50.4 | 18.7 | 28.6 | 18.7 | 30.4 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.5 ms de matérialisation, l'appel a construit 10.8 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **325.8 µs**.

- **`GetMailsByUids`** — sur 10.4 ms de matérialisation, l'appel a construit 207.1 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.4 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **50.4 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4389.2 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 391.9 | 2228 | 132.3 (33.8 %), p95 243 | 12.9 (3.3 %), p95 955 | 154.2 (39.4 %), p95 2228 | 51.4 (13.1 %), p95 198 | 41.1 (10.5 %), p95 455 |

- **Enrichir un message** — sur 391.9 ms en moyenne (3.8 message(s) par requête) : 132.3 ms fetch IMAP, 12.9 ms extraction XDM, 154.2 ms parsing CDA, 51.4 ms écritures base, 41.1 ms le reste (DTO, notifications). **Poste dominant : parsing CDA.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`, 0.43 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 282.6 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 635.4 | 984 | 0.0 (0.0 %), p95 5 | 18.0 (2.8 %), p95 61 | 221.0 (34.8 %), p95 476 | 396.3 (62.4 %), p95 488 | 415.9 (65.5 %), p95 945 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 635.4 ms en moyenne : 0.0 ms garde d'opposition, 18.0 ms construction MIME, 221.0 ms obtention de session SMTP, 396.3 ms transmission + acquittement, 415.9 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.443 | 2.411 | 96.15 |
| `smtp_session` | 0.005 | 0.988 | 10.24 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.174 | 2.312 | 0.488 | 10.27 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 1.04 |
| `GetAttachmentStream` | 0.487 | 2.350 | 2.425 | 0.725 | 0.67 |
| `GetEmailContent` | 0.005 | 0.491 | — | 0.491 | 13.15 |
| `GetFolders` | 0.005 | 0.996 | 0.996 | 0.242 | 7.80 |
| `ReadFolder` | 0.762 | 2.413 | 2.413 | 0.487 | 35.13 |
| `ReadToday` | 0.005 | 0.494 | — | 0.494 | 7.75 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.16 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.372** | 0.462 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.495 | 0.497 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `GetFolders` | **0.241** | 0.241 | 0.242 | 0.0 % |
| `ReadFolder` | **0.428** | 0.441 | 0.448 | 0.0 % |
| `ReadToday` | **0.487** | 0.489 | 0.490 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 96.15 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.762 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 20.00 clients | 0 clients | 100.0 % | 25.1 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.01 cœurs | 24 cœurs | 33.4 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-79016` | 17.00 éléments | 100 éléments | 17.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#79016` (CPU) | 3.03 cœurs | 24 cœurs | 12.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#73788` (CPU) | 2.74 cœurs | 24 cœurs | 11.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#49636` (CPU) | 2.69 cœurs | 24 cœurs | 11.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#79852` (CPU) | 2.59 cœurs | 24 cœurs | 10.8 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 2.58 cœurs | 24 cœurs | 10.7 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 25.1 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 292 903

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 3 385 |
| OpenAI | gpt-4o-mini | prompt | 289 518 |
| OpenAI | text-embedding-3-small | embedding | 539 501 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 149 | 0 (0.0 %) | 0 | 4.0 | 1.14 | 1.01 | 2.67 |
| étiquetage (chat) | OpenAI | 149 | 0 (0.0 %) | 0 | 4.0 | 1.09 | 0.95 | 2.67 |
| embedding | OpenAI | 151 | 0 (0.0 %) | 0 | 4.0 | 0.56 | 0.46 | 1.37 |

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
| GPU — utilisation (%) | 1.8 | 16.0 |
| GPU — VRAM occupée (Mo) | 1 754 | 1 782 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 609.6** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.18** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **3.6 ms** | sur 763 477 requêtes HTTP k6 |
| Taux de cache (blocs) | **98.34 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **6.68 Mo/s (855 blocs/s)** | attente disque : 3.9 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **278 602 / 30 139** | rapport 9.2 |
| Écritures de lignes / s (ins+upd+del) | **164.2** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.28 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 15 % |
| Sessions ouvertes / s | **2.91** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **43.5 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 568 / 2 025** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **96 / 100 %** | fautes majeures/s max : 1.2 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 140.7 s | 168539 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, Embedding, HtmlBody, MetadataJson : 22.8 Go lus, 3.2 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 13.8 % du temps SQL, 53.8 % des lectures disque du tir | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 37.6 s | 168372 | `colonne-volumineuse` | sélectionne Body, BodyHtml, Embedding : 10.7 Go lus, 0.1 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 35.2 s | 9002 | `pages-par-ligne` | 31.1 pages par ligne rendue, 623 par appel, 42.8 Go lus | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 29.5 s | 8902 | `pages-par-ligne` | 31.3 pages par ligne rendue, 626 par appel, 42.5 Go lus | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 27.5 s | 15307 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Content : 2.8 Go lus, 1.7 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 2.7 % du temps SQL, 28.4 % des lectures disque du tir | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **86 évictions `pg_stat_statements`** pendant le tir (97 982 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

136 formes de requête, 6 028 921 appels, **17.0 min** de temps serveur cumulé — soit **1.3 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **16.2 %** | 16 % | 8 989 | 0.01 | 18.38 | 51.2 | 340 | 0 % | 0 | 914 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **14.4 %** | 31 % | 8 957 | 0.01 | 16.39 | 51.2 | 394 | 0 % | 0 | 910 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **13.8 %** | 44 % | 168 539 | 0.22 | 0.83 | 1.0 | 18 | 14 % | 0 | 1 885 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **6.5 %** | 51 % | 763 387 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `PostgresTenantRegistryClient.GetMailboxAsync` ← `GET /api/v1/Mail/folders/{foldername}` | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 5 | **6.0 %** | 57 % | 88 900 | 0.12 | 0.69 | 18.0 | 99 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 6 | **3.7 %** | 61 % | 168 372 | 0.22 | 0.22 | 1.0 | 8 | 1 % | 0 | 1 883 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 7 | **3.5 %** | 64 % | 9 002 | 0.01 | 3.91 | 20.0 | 623 | 0 % | 0 | 913 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 8 | **3.2 %** | 67 % | 137 870 | 0.18 | 0.24 | 1.0 | 15 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 9 | **2.9 %** | 70 % | 8 902 | 0.01 | 3.32 | 20.0 | 626 | 0 % | 0 | 907 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 10 | **2.7 %** | 73 % | 15 307 | 0.02 | 1.80 | 1.0 | 24 | 60 % | 0 | 1 214 | **Code** — 60 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 11 | **2.0 %** | 75 % | 282 955 | 0.37 | 0.07 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `MailRepository.ResolveActiveDuplicateRefsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 12 | **2.0 %** | 77 % | 96 024 | 0.13 | 0.21 | 18.0 | 5 | 0 % | 0 | 1 826 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | site inconnu ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}`<br>`MailRepository.LoadMailsReferencingAnyRootAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 13 | **1.7 %** | 79 % | 5 056 | 0.01 | 3.53 | 178.0 | 540 | 1 % | 0 | 870 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 14 | **1.4 %** | 80 % | 282 966 | 0.37 | 0.05 | 2.1 | 4 | 0 % | 0 | 1 996 | — | `MailRepository.EnrichManyWithBiologyAcksAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 15 | **1.3 %** | 81 % | 88 898 | 0.12 | 0.15 | 18.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.GetMailsByUidsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 16 | **1.2 %** | 82 % | 45 170 | 0.06 | 0.28 | 27.0 | 5 | 0 % | 0 | 1 400 | — | `MailRepository.GetLatestMessageIdsPerThreadAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **1.0 %** | 83 % | 144 131 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **1.0 %** | 84 % | 189 223 | 0.25 | 0.05 | 1.5 | 6 | 0 % | 0 | 1 908 | — | `MailRepository.GetMailAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`, `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |
| 19 | **1.0 %** | 85 % | 144 132 | 0.19 | 0.07 | 14.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **1.0 %** | 86 % | 88 902 | 0.12 | 0.11 | 17.9 | 18 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."ContentType", $2 AS "Body" FROM "MailContents" AS m WHERE m."MailId" = ANY ($1)` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.9 % | 87.8 % |
| INSERT | 4.1 % | 2.9 % |
| UPDATE | 0.4 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.5 % | 7.5 % |
| bases : praticien (N bases) | 89.9 % | 82.2 % |
| bases : unique (1 base) | 10.1 % | 17.8 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **18.4** | 126 | 8 989 | 16.2 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **16.4** | 113 | 8 957 | 14.4 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **3.9** | 1 301 | 9 002 | 3.5 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **3.5** | 49 | 5 056 | 1.7 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **3.3** | 56 | 8 902 | 2.9 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 297 | 154 343 | 0 | 5 | 0.1 Mo |
| `Mails` | 726 | 92 475 | 711 | 26 | 0.1 Mo |
| `MailTags` | 200 | 49 600 | 70 | 43 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 203 | 29 895 | 1 274 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 110 | 28 710 | 190 | 43 | 30.0 Mo |
| `MailRecipients` | 183 | 28 548 | 58 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 81 | 12 636 | 2 155 | 156 | 1.9 Mo |
| `PendingActions` | 174 | 5 131 | 0 | 31 | 0.1 Mo |
| `Tags` | 136 | 2 448 | 89 | 0 | 0.0 Mo |
| `MailFolders` | 359 | 956 | 330 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°4 (6.5 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 98.3 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 203 fois (29895 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 110 fois (28710 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 81 fois (12636 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°10 (2.7 % du temps SQL) — 60 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°13 (1.7 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°7 (3.5 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°12 (2.0 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-141438.tsv`, `pgserver-journey-debut-133608.tsv`, `pgserver-journey-fin-141445.tsv`, `pgtables-journey-debut-133613.tsv`, `pgtables-journey-fin-141449.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 248216 — dont **248216** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261108-t434-controle-141356.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
