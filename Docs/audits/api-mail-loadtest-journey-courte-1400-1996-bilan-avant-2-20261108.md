# Rapport de tir — journey-courte-1400-1996-20261108-bilan-avant-2

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261108-bilan-avant-2-014657.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1996 médecins, 2 étape(s) dépassent le temps de réponse attendu : « Ouvrir un message enrichi (servi base) », « Recherche »
- 4 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 28 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.013 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 749569 — **débit émergent global** : 331.5 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53416 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 331.5 | **214.4** | 103.1 | **742.6** | — | 10631.3 | 0.01 | 100.0 | 0 | 0 | 247884/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 212181 | 287.90 | 0.01 | 795.3 |
| **1996 médecins** | 1080 | 933 | 381094 | 408.46 | 0.01 | 1412.1 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 71 / 596 (n=63560) | 114 / 677 (n=113444) |
| 2 | Ouvrir / rafraîchir l'inbox | 51 / 130 (n=31804) | 110 / 342 (n=56708) |
| 3 | Ouvrir un message enrichi (servi base) | 47 / 100 (n=15911) | 119 / 301 (n=28385) |
| 4 | Ouvrir un message froid (fetch IMAP) | 457 / 525 (n=6366) | 498 / 641 (n=11438) |
| 5 | Recherche | 407 / 668 (n=4793) | 518 / 920 (n=8514) |
| 6 | Envoi (acquittement UI) | 507 / 941 (n=4758) | 577 / 1059 (n=8385) |
| 7 | Télécharger une PJ (~124 Ko) | 51 / 110 (n=6258) | 132 / 348 (n=11328) |
| 8 | Marquer lu | 52 / 109 (n=12814) | 116 / 282 (n=22685) |
| 9 | Rechercher un patient | 63 / 87 (n=4656) | 80 / 188 (n=8488) |
| 10 | Ouvrir la page d'un dossier patient | 66 / 151 (n=7011) | 148 / 397 (n=12698) |
| 11 | Fiche patient complète (ressenti médecin) | 383 / 705 (n=3505) | 740 / 1884 (n=6349) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.4 / 20 | 34.0 / 60 | 7878 | 705 |
| **1996 médecins** | 14.5 / 20 | 34.2 / 60 | 14122 | 1884 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2243 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 815 ms en moyenne, 10631 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> ⚠️ **Rectification (task-435, 2026-11-08) — ventilation fausse.** Depuis task-404 (2026-10-29), l'échantillonneur ne reconnaissait plus les bases praticien (nommage `u_l…`). Les lignes « dont bases **praticien** » valent donc 0 à tort, et « dont pool de **maintenance** — sonde de readiness » porte en réalité l'attente du chemin du médecin : la sonde de readiness ne traverse plus le pooler depuis task-249. La ligne « Login PostgreSQL depuis le conteneur » est « non relevé » pour la même cause. Le total `cl_waiting` et `maxwait` restent justes. Mesure corrigée : tir de qualification de task-435 (`api-mail-loadtest-journey-courte-1400-1996-t435-qualif-20261108.md`).

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2231 / 3074 (magasin) | 2231 / 3074 (magasin) |
| Backends Postgres (moy/max) | 1235 / 1435 | 1991 / 2030 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 48/173 (28 %) ⚠️ soutenu | 81/136 (60 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/173 (0 %) | 0/136 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 48/173 (28 %) | 81/136 (60 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 57.9 | 142.2 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 57.9 | 142.2 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 119 / 368 | 92 / 275 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 104 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1404 | 1999 |
| Backends **directs** — audit + provisionnement (max) | 30 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 98.9 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 | 0 / 0 |
| RSS par réplica api-mail, Mo (moy/max) | 1158 / 1591 (5 réplicas) | 2050 / 2310 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1435.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2030.0 / 2500** (81.2 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15911)
- palier 1996 : cohorte 1996 chauffée à 100.0 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28385)

> ⓘ Chauffe : **305 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 71 (300) | 596 (1500) | 63560 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 51 (300) | 130 (1000) | 31804 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 47 (100) | 100 (500) | 15911 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 457 (800) | 525 (2500) | 6366 | ✅ |
| 5 | Recherche | 407 (500) | 668 (2000) | 4793 | ✅ |
| 6 | Envoi (acquittement UI) | 507 (1000) | 941 (3000) | 4758 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 51 (500) | 110 (2000) | 6258 | ✅ |
| 8 | Marquer lu | 52 (200) | 109 (1000) | 12814 | ✅ |
| 9 | Rechercher un patient | 63 (300) | 87 (1500) | 4656 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 66 (500) | 151 (2000) | 7011 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 383 (1500) | 705 (4000) | 3505 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 114 (300) | 677 (1500) | 113444 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 110 (300) | 342 (1000) | 56708 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 119 (100) | 301 (500) | 28385 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 498 (800) | 641 (2500) | 11438 | ✅ |
| 5 | Recherche | 518 (500) | 920 (2000) | 8514 | ❌ |
| 6 | Envoi (acquittement UI) | 577 (1000) | 1059 (3000) | 8385 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 132 (500) | 348 (2000) | 11328 | ✅ |
| 8 | Marquer lu | 116 (200) | 282 (1000) | 22685 | ✅ |
| 9 | Rechercher un patient | 80 (300) | 188 (1500) | 8488 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 148 (500) | 397 (2000) | 12698 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 740 (1500) | 1884 (4000) | 6349 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 113444 | 208 | 677 | 23552.2 | 38.9 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 56708 | 139 | 342 | 7883.1 | 13.0 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11438 | 511 | 641 | 5840.1 | 9.6 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8385 | 693 | 1059 | 5808.5 | 9.6 % |
| 🟠 | Recherche (`search`) | 8514 | 569 | 920 | 4848.7 | 8.0 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 28385 | 140 | 301 | 3962.7 | 6.5 % |
| 🟢 | Marquer lu (`mark_read`) | 22685 | 135 | 282 | 3061.0 | 5.1 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11328 | 159 | 348 | 1806.1 | 3.0 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7061 | 192 | 374 | 1357.7 | 2.2 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6349 | 176 | 397 | 1118.1 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8488 | 90 | 188 | 764.0 | 1.3 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6349 | 96 | 190 | 611.0 | 1.0 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 4 🟠 · 8 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 23552.2 s, 38.9 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 5.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 7883.1 s, 13.0 %)
  - **dispersion p95/p50 = 3.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 4848.7 s, 8.0 %)
  - **hors grille** — le médecin attend trop
- **Ouvrir un message enrichi (servi base)** (`read_content`, 3962.7 s, 6.5 %)
  - **hors grille** — le médecin attend trop

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15890 | 397 | 995 | 6275.8 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15890 | 70 | 509 | 2356.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15890 | 34 | 183 | 964.8 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15890 | 66 | 91 | 1088.6 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15902 | 26 | 130 | 687.4 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15902 | 66 | 129 | 1181.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28361 | 417 | 1019 | 12154.8 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28361 | 99 | 553 | 5198.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28361 | 87 | 296 | 3366.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28361 | 86 | 198 | 2833.0 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28354 | 66 | 253 | 2663.1 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28354 | 163 | 371 | 5220.1 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (1019 ms de p95, 417 ms de p50, n=28361), qui porte **aussi** le temps serveur de l'étape (12154.8 s, 52 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (371 ms de p95, 163 ms de p50, n=28354), qui porte **aussi** le temps serveur de l'étape (5220.1 s, 66 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21453 | 150.4 | 91.4 | 287.0 | 437.6 | 2352.3 |
| attachment,palier:1400 | 6258 | 59.0 | 50.6 | 91.7 | 109.8 | 317.1 |
| attachment,palier:1996 | 11328 | 159.4 | 132.4 | 279.5 | 348.3 | 1425.5 |
| attachment,palier:transition | 590 | 223.5 | 80.8 | 674.0 | 863.5 | 1395.0 |
| dashboard | 218000 | 223.5 | 104.5 | 529.6 | 769.7 | 3126.1 |
| dashboard,call:coverage,palier:1400 | 15890 | 68.5 | 65.8 | 82.7 | 91.3 | 279.0 |
| dashboard,call:coverage,palier:1996 | 28361 | 99.9 | 86.3 | 155.3 | 197.6 | 798.1 |
| dashboard,call:coverage,palier:transition | 1046 | 252.8 | 157.8 | 545.5 | 685.0 | 1035.8 |
| dashboard,call:folder,palier:1400 | 15890 | 395.0 | 397.4 | 770.5 | 994.6 | 1517.3 |
| dashboard,call:folder,palier:1996 | 28361 | 428.6 | 416.9 | 801.0 | 1019.3 | 1683.9 |
| dashboard,call:folder,palier:transition | 1046 | 588.4 | 546.7 | 968.1 | 1110.3 | 1945.1 |
| dashboard,call:folders,palier:1400 | 15890 | 60.7 | 34.0 | 164.2 | 182.5 | 350.1 |
| dashboard,call:folders,palier:1996 | 28361 | 118.7 | 86.7 | 243.6 | 296.4 | 789.2 |
| dashboard,call:folders,palier:transition | 1046 | 262.3 | 173.8 | 614.0 | 758.0 | 1270.4 |
| dashboard,call:today,palier:1400 | 15890 | 148.3 | 69.5 | 486.5 | 509.1 | 1097.7 |
| dashboard,call:today,palier:1996 | 28361 | 183.3 | 98.9 | 514.6 | 552.5 | 1343.0 |
| dashboard,call:today,palier:transition | 1046 | 469.7 | 495.9 | 870.7 | 966.4 | 1458.2 |
| dashboard,palier:1400 | 63560 | 168.1 | 70.5 | 464.6 | 595.8 | 1517.3 |
| dashboard,palier:1996 | 113444 | 207.6 | 114.3 | 488.4 | 677.4 | 1683.9 |
| dashboard,palier:transition | 4184 | 393.3 | 368.2 | 814.1 | 948.9 | 1945.1 |
| mark_read | 43424 | 131.9 | 89.1 | 230.1 | 345.5 | 2383.5 |
| mark_read,palier:1400 | 12814 | 61.0 | 52.4 | 95.5 | 108.9 | 291.6 |
| mark_read,palier:1996 | 22685 | 134.9 | 116.4 | 228.2 | 281.9 | 828.3 |
| mark_read,palier:transition | 1142 | 193.9 | 84.4 | 576.5 | 728.9 | 1179.2 |
| patient_docs | 173864 | 143.5 | 91.7 | 286.1 | 395.8 | 2393.3 |
| patient_docs,palier:1400 | 50311 | 64.4 | 57.7 | 112.8 | 134.3 | 403.3 |
| patient_docs,palier:1996 | 91960 | 151.5 | 127.6 | 289.2 | 347.3 | 1009.1 |
| patient_docs,palier:transition | 4706 | 174.3 | 85.0 | 505.9 | 694.6 | 1457.6 |
| patient_dossier | 12050 | 166.6 | 108.5 | 318.4 | 475.0 | 3140.5 |
| patient_dossier,palier:1400 | 3505 | 75.3 | 66.3 | 124.5 | 150.9 | 380.6 |
| patient_dossier,palier:1996 | 6349 | 176.1 | 147.9 | 315.3 | 397.2 | 971.4 |
| patient_dossier,palier:transition | 331 | 219.2 | 95.1 | 666.3 | 774.9 | 1320.0 |
| patient_opposition | 12050 | 106.0 | 74.4 | 148.2 | 243.9 | 2138.8 |
| patient_opposition,palier:1400 | 3506 | 67.8 | 65.4 | 82.0 | 89.2 | 165.6 |
| patient_opposition,palier:1996 | 6349 | 96.2 | 84.2 | 147.5 | 189.8 | 699.9 |
| patient_opposition,palier:transition | 331 | 150.3 | 74.2 | 422.8 | 564.1 | 955.4 |
| patient_search | 16116 | 98.3 | 68.8 | 147.0 | 246.6 | 2177.4 |
| patient_search,palier:1400 | 4656 | 55.4 | 62.9 | 78.9 | 86.8 | 231.4 |
| patient_search,palier:1996 | 8488 | 90.0 | 80.0 | 146.2 | 187.7 | 722.5 |
| patient_search,palier:transition | 431 | 139.6 | 70.8 | 406.9 | 558.1 | 933.4 |
| read_content | 54500 | 130.0 | 80.4 | 245.2 | 348.9 | 2318.9 |
| read_content,palier:1400 | 15911 | 53.9 | 46.9 | 83.9 | 100.2 | 395.7 |
| read_content,palier:1996 | 28385 | 139.6 | 118.9 | 248.1 | 300.7 | 925.5 |
| read_content,palier:transition | 1288 | 217.3 | 79.5 | 642.3 | 813.6 | 1348.3 |
| read_content_cold | 21739 | 511.3 | 481.4 | 589.9 | 679.4 | 2616.7 |
| read_content_cold,palier:1400 | 6366 | 458.9 | 456.8 | 509.2 | 524.7 | 659.0 |
| read_content_cold,palier:1996 | 11438 | 510.6 | 498.1 | 593.4 | 641.0 | 1135.5 |
| read_content_cold,palier:transition | 558 | 578.0 | 482.1 | 937.1 | 1111.7 | 1446.4 |
| read_list | 109000 | 133.6 | 77.3 | 279.1 | 414.1 | 2603.2 |
| read_list,call:emails,palier:1400 | 15902 | 74.3 | 65.8 | 109.3 | 129.4 | 348.2 |
| read_list,call:emails,palier:1996 | 28354 | 184.1 | 162.7 | 312.9 | 370.8 | 846.3 |
| read_list,call:emails,palier:transition | 1252 | 287.9 | 120.4 | 763.5 | 932.5 | 1413.1 |
| read_list,call:folder,palier:1400 | 15902 | 43.2 | 25.5 | 68.6 | 130.4 | 544.9 |
| read_list,call:folder,palier:1996 | 28354 | 93.9 | 65.8 | 179.2 | 252.6 | 1102.5 |
| read_list,call:folder,palier:transition | 1252 | 166.7 | 55.5 | 494.0 | 649.6 | 1349.7 |
| read_list,palier:1400 | 31804 | 58.8 | 51.4 | 103.1 | 129.7 | 544.9 |
| read_list,palier:1996 | 56708 | 139.0 | 110.4 | 277.6 | 341.8 | 1102.5 |
| read_list,palier:transition | 2504 | 227.3 | 92.4 | 666.2 | 830.9 | 1413.1 |
| search | 16372 | 556.5 | 475.2 | 796.7 | 1169.0 | 3327.8 |
| search,palier:1400 | 4793 | 451.5 | 406.8 | 549.4 | 667.6 | 1708.0 |
| search,palier:1996 | 8514 | 569.5 | 517.8 | 754.2 | 919.7 | 2130.5 |
| search,palier:transition | 423 | 642.1 | 467.5 | 1279.2 | 1473.4 | 2544.6 |
| send | 15544 | 709.9 | 622.5 | 997.9 | 1087.9 | 2852.8 |
| send,palier:1400 | 4758 | 645.1 | 506.7 | 919.6 | 940.6 | 1071.5 |
| send,palier:1996 | 8385 | 692.7 | 576.6 | 1003.6 | 1059.3 | 1602.4 |
| send,palier:transition | 481 | 735.4 | 720.0 | 1126.5 | 1362.0 | 1875.4 |
| treatment | 13487 | 175.5 | 120.5 | 300.1 | 429.7 | 4131.3 |
| treatment,palier:1400 | 3939 | 90.6 | 90.4 | 127.1 | 144.9 | 276.0 |
| treatment,palier:1996 | 7061 | 192.3 | 159.8 | 305.5 | 373.5 | 4131.3 |
| treatment,palier:transition | 307 | 254.1 | 107.3 | 707.8 | 871.4 | 1337.9 |
| warmup | 21956 | 815.1 | 551.7 | 1451.7 | 2287.1 | 10631.3 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-08T00:09:16.870000+00:00 → 2026-11-08T00:46:57.775000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-bilan-avant-2.csv`) | ✅ 71878 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-13580` | 1.04 | 13 | 32 | 0.032 | 4.73 |
| `DESKTOP-DEV-X2C-64804` | 1.19 | 11 | 29 | 0.035 | 4.80 |
| `DESKTOP-DEV-X2C-71196` | 1.28 | 17 | 24 | 0.037 | 4.93 |
| `DESKTOP-DEV-X2C-76448` | 1.03 | 14 | 24 | 0.025 | 4.64 |
| `DESKTOP-DEV-X2C-77500` | 1.06 | 12 | 34 | 0.038 | 5.20 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.77 | 5.01 | 2660 |
| `com.docker.backend#34124` | 0.00 | 0.22 | 40 |
| `dcp#15872` | 0.00 | 0.14 | 14 |
| `dcp#48340` | 0.00 | 0.08 | 12 |
| `dcp#49592` | 0.00 | 0.00 | 12 |
| `dcp#51928` | 0.00 | 0.00 | 12 |
| `dcp#55288` | 0.00 | 0.21 | 13 |
| `dcp#62500` | 0.00 | 0.04 | 14 |
| `dcp#64836` | 0.00 | 0.00 | 12 |
| `dcp#66428` | 0.00 | 0.04 | 13 |
| `dcp#67852` | 0.78 | 2.33 | 3177 |
| `dcp#72068` | 0.00 | 0.04 | 12 |
| `dcp#72760` | 0.00 | 0.00 | 12 |
| `dcp#74864` | 0.00 | 0.00 | 12 |
| `dcp#75724` | 0.00 | 0.13 | 52 |
| `dcp#76124` | 0.00 | 0.00 | 12 |
| `dcp#79500` | 0.00 | 0.00 | 12 |
| `k6#265784` | 0.88 | 1.86 | 2906 |
| `mss.mail.api#13580` | 0.75 | 2.28 | 2171 |
| `mss.mail.api#64804` | 0.77 | 2.74 | 2218 |
| `mss.mail.api#71196` | 0.85 | 2.84 | 2310 |
| `mss.mail.api#76448` | 0.71 | 2.81 | 2228 |
| `mss.mail.api#77500` | 0.74 | 2.51 | 2180 |
| `mss.mail.e2e#49360` | 0.01 | 0.09 | 32 |
| `vmmemWSL#36464` | 6.88 | 12.36 | 71896 |
| `loadtest-otel-collector-ebsktupn` | 0.02 | 0.20 | 132 |
| `loadtest-pgbouncer-jyymxdaq` | 0.55 | 0.92 | 52 |
| `mss-mail-flagsmith-app-b6152948` | 0.12 | 0.38 | 471 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.11 | 175 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.05 | 160 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.13 | 304 |
| `mss-mail-rabbitmq-qmuqdwfy` | 0.01 | 0.03 | 145 |
| `mss-mail-redis-b6152948` | 0.29 | 1.38 | 964 |
| `mss-mail-rediscommander-cpwqryas` | 0.00 | 0.16 | 42 |
| `mss-mail-seq-b6152948` | 0.11 | 0.41 | 5968 |
| `postgres-pgvector` | 3.40 | 8.87 | 47022 |

- **Hôte** : CPU 75.2 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 64
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9396, cl_waiting max 18, cl_waiting_maintenance max 18, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 142, maxwait_ms max 142, maxwait_practitioner_ms max 0, sv_active max 60, sv_idle max 1618, sv_login max 1
- **Backends Postgres** : audit max 5, cache_mb max 40609, direct max 30, idle_over_60s max 210, majfault_per_s max 1, pooler max 1999, practitioner_databases max 1993, provision max 5, rss_mb max 6196, started_last_60s max 368, total max 2030, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 6939.3 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2489.5 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 2192.0 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2378.8 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 2257.7 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 2240.1 | 442 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 2164.1 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2241.9 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2438.1 | 432 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 2039.4 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 2288.5 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 2008.7 | 442 |
| `api/v{version:apiVersion}/Search/semantic` | 2438.9 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 2148.5 | 447 |

- **p95 client global (k6)** : 742.6 ms
- **p95 serveur le plus élevé** : 6939.3 ms
- **Écart** : -6196.7 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.73 |
| Documents CDA /s | 0.76 |
| Durée traitement CDA (s, p95) | 0.94 |
| Événements de session IMAP /s | 3.98 |
| Recherches (s, p95) | 1.621 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 102.2 | 287 | 0.0 (0.0 %), p95 5 | 60.8 (59.5 %), p95 242 | 41.4 (40.5 %), p95 235 |
| `GetMail` | 11.1 | 65.7 | 431 | 5.7 (8.6 %), p95 83 | 56.1 (85.5 %), p95 373 | 3.8 (5.9 %), p95 20 |
| `GetMailsByUids` | 14.7 | 90.1 | 483 | 0.1 (0.1 %), p95 5 | 78.0 (86.6 %), p95 471 | 11.9 (13.2 %), p95 65 |

- **`EnrichPersistMail`** — sur 102.2 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 60.8 ms exécution SQL, 41.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 65.7 ms en moyenne (11.1 requête(s) SQL par appel) : 5.7 ms attente d'une connexion, 56.1 ms exécution SQL, 3.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 90.1 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 78.0 ms exécution SQL, 11.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.8 | 359.1 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.3 | 11.9 | 57.6 | 18.7 | 28.6 | 18.7 | 30.5 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.8 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **359.1 µs**.

- **`GetMailsByUids`** — sur 11.9 ms de matérialisation, l'appel a construit 207.3 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.5 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **57.6 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3841.7 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 350.7 | 1225 | 130.3 (37.2 %), p95 248 | 18.0 (5.1 %), p95 98 | 53.6 (15.3 %), p95 700 | 77.9 (22.2 %), p95 235 | 70.9 (20.2 %), p95 287 |

- **Enrichir un message** — sur 350.7 ms en moyenne (3.8 message(s) par requête) : 130.3 ms fetch IMAP, 18.0 ms extraction XDM, 53.6 ms parsing CDA, 77.9 ms écritures base, 70.9 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 276.5 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 644.0 | 979 | 0.0 (0.0 %), p95 5 | 28.0 (4.4 %), p95 80 | 218.4 (33.9 %), p95 476 | 397.3 (61.7 %), p95 488 | 421.4 (65.4 %), p95 989 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 644.0 ms en moyenne : 0.0 ms garde d'opposition, 28.0 ms construction MIME, 218.4 ms obtention de session SMTP, 397.3 ms transmission + acquittement, 421.4 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.442 | 2.391 | 102.83 |
| `smtp_session` | 0.005 | 0.988 | 10.29 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.418 | 2.345 | 0.488 | 10.29 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 1.15 |
| `GetAttachmentStream` | 0.478 | 2.425 | 2.425 | 0.495 | 0.91 |
| `GetEmailContent` | 0.005 | 0.494 | — | 0.494 | 14.15 |
| `GetFolders` | 0.005 | 0.991 | 0.991 | 0.243 | 7.87 |
| `ReadFolder` | 0.762 | 2.391 | 2.391 | 0.488 | 38.00 |
| `ReadToday` | 0.005 | 0.494 | 2.425 | 0.494 | 7.93 |
| `UpdateFlag` | 0.043 | 0.488 | — | 0.488 | 26.42 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.331** | 0.448 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.488 | 0.495 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.490 | 0.490 | 0.0 % |
| `GetFolders` | **0.242** | 0.242 | 0.243 | 0.0 % |
| `ReadFolder` | **0.425** | 0.443 | 0.445 | 0.0 % |
| `ReadToday` | **0.488** | 0.490 | 0.493 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 102.83 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.762 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 18.00 clients | 0 clients | 100.0 % | 41.1 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.87 cœurs | 24 cœurs | 36.9 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-71196` | 17.00 éléments | 100 éléments | 17.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#71196` (CPU) | 2.84 cœurs | 24 cœurs | 11.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#76448` (CPU) | 2.81 cœurs | 24 cœurs | 11.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#64804` (CPU) | 2.74 cœurs | 24 cœurs | 11.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#77500` (CPU) | 2.51 cœurs | 24 cœurs | 10.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#13580` (CPU) | 2.28 cœurs | 24 cœurs | 9.5 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 41.1 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 296 908

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 3 615 |
| OpenAI | gpt-4o-mini | prompt | 293 293 |
| OpenAI | text-embedding-3-small | embedding | 453 069 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 157 | 0 (0.0 %) | 0 | 4.2 | 1.12 | 1.07 | 2.46 |
| étiquetage (chat) | OpenAI | 157 | 0 (0.0 %) | 0 | 4.2 | 1.06 | 0.96 | 2.44 |
| embedding | OpenAI | 158 | 0 (0.0 %) | 0 | 4.2 | 0.57 | 0.46 | 1.51 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 4 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.0 | 1.0 |
| GPU — VRAM occupée (Mo) | 1 424 | 1 434 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.7 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **6 781.2** | annulées : 0.0 % |
| Backends actifs (équivalent) | **2.29** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **7.1 ms** | sur 749 569 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.39 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **20.12 Mo/s (2 575 blocs/s)** | attente disque : 8.7 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **525 257 / 45 476** | rapport 11.6 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **161.9** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.29 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **7 / 0** | blocs écrits par les backends eux-mêmes : 40 % |
| Sessions ouvertes / s | **2.68** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **46.2 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 548 / 2 030** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **97 / 100 %** | fautes majeures/s max : 0.8 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 761.5 s | 47327 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body : 100.9 Go lus, 0.2 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 27.6 % du temps SQL, 1.4 % des lectures disque du tir | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 722.2 s | 47329 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body : 117.6 Go lus, 0.6 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 26.2 % du temps SQL, 4.0 % des lectures disque du tir | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 189.8 s | 164487 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, Embedding, HtmlBody, MetadataJson : 22.1 Go lus, 5.3 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 6.9 % du temps SQL, 32.6 % des lectures disque du tir | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 114.2 s | 2222094 | `appels-par-requete` | 2.96 appels par requête HTTP : relecture ou surcoût de session (cache, invalidation, `No Reset On Close`) | — | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 92.9 s | 5339152 | `appels-par-requete` | 7.12 appels par requête HTTP : relecture ou surcoût de session (cache, invalidation, `No Reset On Close`) | — | `DISCARD ALL` |
| 90.7 s | 2222094 | `appels-par-requete` | 2.96 appels par requête HTTP : relecture ou surcoût de session (cache, invalidation, `No Reset On Close`) | — | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 70.5 s | 46669 | `pages-par-ligne`, `sous-requete-correlee` | 25.2 pages par ligne rendue, 258 par appel, 91.7 Go lus · sous-requête corrélée dans une forme qui lit beaucoup de pages par ligne : index sur la clé de corrélation, ou un seul agrégat groupé joint | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 58.9 s | 3759 | `pages-par-ligne`, `colonne-volumineuse`, `poids-dans-le-tir` | 15.7 pages par ligne rendue, 450 par appel, 12.9 Go lus · sélectionne Content : 12.9 Go lus, 5.0 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 2.1 % du temps SQL, 31.2 % des lectures disque du tir | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 55.9 s | 8812 | `pages-par-ligne` | 31.2 pages par ligne rendue, 623 par appel, 41.9 Go lus | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 48.4 s | 164321 | `colonne-volumineuse` | sélectionne Body, BodyHtml, Embedding : 10.4 Go lus, 0.2 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 45.1 s | 8859 | `pages-par-ligne` | 31.4 pages par ligne rendue, 628 par appel, 42.4 Go lus | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 29.2 s | 14929 | `colonne-volumineuse` | sélectionne Content : 2.7 Go lus, 1.5 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | — | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **80 évictions `pg_stat_statements`** pendant le tir (95 321 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

117 formes de requête, 15 728 322 appels, **46.0 min** de temps serveur cumulé — soit **3.7 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **27.6 %** | 28 % | 47 327 | 0.06 | 16.09 | 32.8 | 279 | 0 % | 0 | 1 976 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 2 | **26.2 %** | 54 % | 47 329 | 0.06 | 15.26 | 32.8 | 326 | 1 % | 0 | 1 976 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | — | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 3 | **6.9 %** | 61 % | 164 487 | 0.22 | 1.15 | 1.0 | 18 | 24 % | 0 | 1 876 | **Code** — 24 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **4.1 %** | 65 % | 2 222 094 | 2.96 | 0.05 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 5 | **3.4 %** | 68 % | 5 339 152 | 7.12 | 0.02 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | — | `DISCARD ALL` |
| 6 | **3.3 %** | 71 % | 2 222 094 | 2.96 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 7 | **2.7 %** | 74 % | 87 664 | 0.12 | 0.85 | 18.1 | 100 | 0 % | 0 | 1 996 | — | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 8 | **2.6 %** | 77 % | 46 669 | 0.06 | 1.51 | 10.2 | 258 | 0 % | 0 | 1 428 | — | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 9 | **2.1 %** | 79 % | 3 759 | 0.01 | 15.66 | 28.6 | 450 | 39 % | 0 | 428 | **Code** — 39 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 10 | **2.0 %** | 81 % | 8 812 | 0.01 | 6.34 | 20.0 | 623 | 3 % | 0 | 833 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 11 | **1.8 %** | 83 % | 164 321 | 0.22 | 0.29 | 1.0 | 8 | 2 % | 0 | 1 870 | — | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 12 | **1.7 %** | 84 % | 749 497 | 1.00 | 0.06 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 13 | **1.6 %** | 86 % | 8 859 | 0.01 | 5.09 | 20.0 | 628 | 3 % | 0 | 838 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | — | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 14 | **1.4 %** | 87 % | 131 317 | 0.18 | 0.30 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 15 | **1.1 %** | 88 % | 14 929 | 0.02 | 1.95 | 1.0 | 24 | 56 % | 0 | 1 142 | **Code** — 56 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | — | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 16 | **0.9 %** | 89 % | 277 268 | 0.37 | 0.09 | 1.3 | 16 | 0 % | 0 | 1 995 | — | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 17 | **0.9 %** | 90 % | 92 618 | 0.12 | 0.25 | 18.0 | 5 | 0 % | 0 | 1 538 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **0.8 %** | 91 % | 4 822 | 0.01 | 4.69 | 178.0 | 540 | 2 % | 0 | 835 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 19 | **0.6 %** | 92 % | 277 353 | 0.37 | 0.06 | 2.1 | 4 | 0 % | 0 | 1 996 | — | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 20 | **0.6 %** | 92 % | 87 655 | 0.12 | 0.17 | 18.1 | 5 | 0 % | 0 | 1 996 | — | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.4 % | 61.5 % |
| INSERT | 1.9 % | 1.1 % |
| UPDATE | 0.2 % | 0.5 % |
| DELETE | 0.1 % | 0.2 % |
| AUTRE | 3.5 % | 36.7 % |
| bases : praticien (N bases) | 89.3 % | 65.2 % |
| bases : unique (1 base) | 10.7 % | 34.8 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **16.1** | 218 | 47 327 | 27.6 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailCo…` |
| **15.7** | 387 | 3 759 | 2.1 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **15.3** | 249 | 47 329 | 26.2 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMe…` |
| **6.3** | 98 | 8 812 | 2.0 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **5.1** | 100 | 8 859 | 1.6 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 871 | 216 008 | 186 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 191 | 141 729 | 0 | 5 | 0.1 Mo |
| `Mails` | 771 | 98 694 | 783 | 26 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 107 | 27 927 | 180 | 43 | 30.0 Mo |
| `MailRecipients` | 176 | 27 456 | 54 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 175 | 26 107 | 1 297 | 157 | 8.0 Mo |
| `MailContents` ⚠️ index candidat | 62 | 9 672 | 1 949 | 156 | 1.9 Mo |
| `PendingActions` | 162 | 4 822 | 0 | 31 | 0.1 Mo |
| `Tags` | 119 | 2 142 | 103 | 0 | 0.0 Mo |
| `MailFolders` | 351 | 952 | 397 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🔴 | requête n°1 (27.6 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Code | 🟠 | requête n°3 (6.9 % du temps SQL) — 24 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Postgres | 🟠 | taux de cache 96.4 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | 12 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailAttachments` balayée 107 fois (27927 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 175 fois (26107 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 62 fois (9672 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°9 (2.1 % du temps SQL) — 39 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Code | 🟡 | requête n°15 (1.1 % du temps SQL) — 56 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°4 (4.1 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°5 (3.4 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Postgres | 🟡 | 40 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Schéma | 🟡 | requête n°10 (2.0 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-014743.tsv`, `pgserver-journey-debut-010907.tsv`, `pgserver-journey-fin-014748.tsv`, `pgtables-journey-debut-010911.tsv`, `pgtables-journey-fin-014753.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 247884 — dont **247884** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261108-bilan-avant-2-014657.jsonl`.

Requêtes `/api/data` sur la fenêtre du tir, 00:09:05 → 00:46:57 UTC le 2026-11-08.

- **0 erreur.** Aucune réponse 5xx.
- **Envoi sain** : obtention de session SMTP 218 ms, transmission 397 ms. 2 sessions SMTP poolées fermées par le serveur avant DATA, reprises une fois.
- **Marqueurs de régression** : `Failed to parse entity headers` 0, `SecurityTokenMalformedException` 0, événements `Debug` 0 (niveau de log nominal).
- **429** : 0. **Échecs d'embedding** : 0. **Reprises d'étiquetage IA** (`[TaggingRecovery]`) : 0.
- **Parsings CDA** (`Parsing completed`) : 0. Attendu : population hydratée (`JOURNEY_WARMUP_HYDRATED=1`), le tir n'analyse aucun nouveau document.
- **Avertissements bénins**, du même ordre dans les trois tirs : `[TlsCertificateValidationSession] Allowing untrusted certificate` (~15 000, certificat auto-signé du banc), `[MailClientSession] ♻️ Session expired` (~5 000, recyclage nominal), `[PractitionerContactPublisher] SKIPPED - Invalid RPPS` (≤ 16, identités synthétiques).
