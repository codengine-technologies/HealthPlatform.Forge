# Rapport de tir — journey-courte-1400-1996-20261107-controle430

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261107-controle430-100433.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 1 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 23 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.013 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 760763 — **débit émergent global** : 336.5 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 54006 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 336.5 | **143.6** | 59.0 | **501.5** | — | 11377.6 | 0.01 | 100.0 | 0 | 0 | 246360/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 213459 | 289.63 | 0.01 | 813.7 |
| **1996 médecins** | 1080 | 933 | 386796 | 414.57 | 0.01 | 1483.8 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 58 / 620 (n=63500) | 64 / 641 (n=114692) |
| 2 | Ouvrir / rafraîchir l'inbox | 39 / 87 (n=31812) | 52 / 142 (n=57356) |
| 3 | Ouvrir un message enrichi (servi base) | 33 / 58 (n=15933) | 47 / 113 (n=28697) |
| 4 | Ouvrir un message froid (fetch IMAP) | 445 / 507 (n=6485) | 455 / 523 (n=11377) |
| 5 | Recherche | 322 / 609 (n=4773) | 350 / 636 (n=8617) |
| 6 | Envoi (acquittement UI) | 490 / 924 (n=4659) | 490 / 950 (n=8486) |
| 7 | Télécharger une PJ (~124 Ko) | 36 / 66 (n=6369) | 53 / 152 (n=11515) |
| 8 | Marquer lu | 32 / 80 (n=12657) | 54 / 112 (n=22767) |
| 9 | Rechercher un patient | 55 / 64 (n=4739) | 56 / 77 (n=8663) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 64 (n=7108) | 59 / 79 (n=13062) |
| 11 | Fiche patient complète (ressenti médecin) | 255 / 412 (n=3554) | 347 / 709 (n=6533) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.3 / 60 | 8020 | 412 |
| **1996 médecins** | 14.4 / 20 | 34.0 / 60 | 14498 | 709 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2204 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 637 ms en moyenne, 11378 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2257 / 3150 (magasin) | 2257 / 3150 (magasin) |
| Backends Postgres (moy/max) | 1248 / 1438 | 1987 / 2027 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 44/191 (23 %) | 61/164 (37 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/191 (0 %) | 0/164 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 44/191 (23 %) | 61/164 (37 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 24.2 | 369.5 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 24.2 | 369.5 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 119 / 376 | 98 / 273 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 109 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1407 | 1996 |
| Backends **directs** — audit + provisionnement (max) | 30 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 97.4 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 0 / 0 |
| RSS par réplica api-mail, Mo (moy/max) | 1165 / 1574 (5 réplicas) | 2029 / 2397 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1438.0 / 2500** (57.5 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2027.0 / 2500** (81.1 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.3 % (sur 15933)
- palier 1996 : cohorte 1996 chauffée à 100.0 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28697)

> ⓘ Chauffe : **301 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 58 (300) | 620 (1500) | 63500 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 39 (300) | 87 (1000) | 31812 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 33 (100) | 58 (500) | 15933 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 445 (800) | 507 (2500) | 6485 | ✅ |
| 5 | Recherche | 322 (500) | 609 (2000) | 4773 | ✅ |
| 6 | Envoi (acquittement UI) | 490 (1000) | 924 (3000) | 4659 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 36 (500) | 66 (2000) | 6369 | ✅ |
| 8 | Marquer lu | 32 (200) | 80 (1000) | 12657 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 64 (1500) | 4739 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 64 (2000) | 7108 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 255 (1500) | 412 (4000) | 3554 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 64 (300) | 641 (1500) | 114692 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 52 (300) | 142 (1000) | 57356 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 47 (100) | 113 (500) | 28697 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 455 (800) | 523 (2500) | 11377 | ✅ |
| 5 | Recherche | 350 (500) | 636 (2000) | 8617 | ✅ |
| 6 | Envoi (acquittement UI) | 490 (1000) | 950 (3000) | 8486 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 53 (500) | 152 (2000) | 11515 | ✅ |
| 8 | Marquer lu | 54 (200) | 112 (1000) | 22767 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 77 (1500) | 8663 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 79 (2000) | 13062 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 347 (1500) | 709 (4000) | 6533 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114692 | 163 | 641 | 18742.0 | 44.7 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8486 | 631 | 950 | 5356.0 | 12.8 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11377 | 457 | 523 | 5197.4 | 12.4 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57356 | 60 | 142 | 3462.4 | 8.3 % |
| 🟢 | Recherche (`search`) | 8617 | 399 | 636 | 3441.1 | 8.2 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28697 | 56 | 113 | 1611.8 | 3.8 % |
| 🟢 | Marquer lu (`mark_read`) | 22767 | 61 | 112 | 1378.4 | 3.3 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11515 | 77 | 152 | 890.6 | 2.1 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7249 | 115 | 178 | 832.9 | 2.0 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8663 | 49 | 77 | 420.5 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6529 | 59 | 79 | 383.1 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6533 | 39 | 75 | 252.1 | 0.6 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 1 🟠 · 11 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 18742.0 s, 44.7 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 10.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15875 | 390 | 911 | 6057.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15875 | 58 | 495 | 2166.5 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15875 | 21 | 162 | 722.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15875 | 56 | 66 | 905.5 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15906 | 15 | 115 | 468.9 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15906 | 49 | 77 | 829.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28673 | 400 | 995 | 11319.4 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28673 | 63 | 504 | 4014.8 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28673 | 31 | 182 | 1666.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28673 | 60 | 83 | 1741.8 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28678 | 21 | 128 | 1108.0 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28678 | 71 | 153 | 2354.4 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (995 ms de p95, 400 ms de p50, n=28673), qui porte **aussi** le temps serveur de l'étape (11319.4 s, 60 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (153 ms de p95, 71 ms de p50, n=28678), qui porte **aussi** le temps serveur de l'étape (2354.4 s, 68 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21912 | 78.2 | 44.7 | 114.3 | 272.3 | 1341.0 |
| attachment,palier:1400 | 6369 | 40.5 | 35.9 | 54.9 | 66.0 | 1031.8 |
| attachment,palier:1996 | 11515 | 77.3 | 53.1 | 110.0 | 151.6 | 1139.9 |
| attachment,palier:transition | 647 | 166.1 | 46.6 | 458.7 | 635.9 | 1064.5 |
| dashboard | 220380 | 167.9 | 62.9 | 471.2 | 624.8 | 1578.7 |
| dashboard,call:coverage,palier:1400 | 15875 | 57.0 | 56.3 | 62.7 | 65.7 | 206.7 |
| dashboard,call:coverage,palier:1996 | 28673 | 60.7 | 60.1 | 75.4 | 82.9 | 467.0 |
| dashboard,call:coverage,palier:transition | 1094 | 110.1 | 87.0 | 199.9 | 238.1 | 434.2 |
| dashboard,call:folder,palier:1400 | 15875 | 381.6 | 389.9 | 757.9 | 910.9 | 1534.6 |
| dashboard,call:folder,palier:1996 | 28673 | 394.8 | 400.0 | 774.1 | 995.2 | 1578.7 |
| dashboard,call:folder,palier:transition | 1094 | 438.4 | 450.3 | 703.2 | 808.9 | 1515.5 |
| dashboard,call:folders,palier:1400 | 15875 | 45.5 | 20.6 | 147.8 | 161.7 | 350.9 |
| dashboard,call:folders,palier:1996 | 28673 | 58.1 | 31.2 | 163.2 | 181.6 | 735.8 |
| dashboard,call:folders,palier:transition | 1094 | 118.1 | 94.9 | 251.8 | 318.2 | 634.3 |
| dashboard,call:today,palier:1400 | 15875 | 136.5 | 58.2 | 474.8 | 495.1 | 795.5 |
| dashboard,call:today,palier:1996 | 28673 | 140.0 | 63.3 | 481.5 | 504.1 | 1155.5 |
| dashboard,call:today,palier:transition | 1094 | 308.6 | 231.5 | 600.2 | 642.8 | 846.4 |
| dashboard,palier:1400 | 63500 | 155.1 | 58.3 | 456.4 | 620.3 | 1534.6 |
| dashboard,palier:1996 | 114692 | 163.4 | 64.2 | 464.7 | 640.5 | 1578.7 |
| dashboard,palier:transition | 4376 | 243.8 | 145.1 | 550.4 | 634.3 | 1515.5 |
| mark_read | 43715 | 64.8 | 48.5 | 96.1 | 135.0 | 1098.9 |
| mark_read,palier:1400 | 12657 | 45.2 | 32.5 | 75.1 | 79.7 | 297.6 |
| mark_read,palier:1996 | 22767 | 60.5 | 53.9 | 95.4 | 112.2 | 581.1 |
| mark_read,palier:transition | 1216 | 101.3 | 65.1 | 286.3 | 355.7 | 589.3 |
| patient_docs | 178272 | 71.3 | 51.7 | 125.2 | 175.0 | 1855.8 |
| patient_docs,palier:1400 | 51414 | 43.4 | 40.6 | 77.1 | 90.4 | 506.3 |
| patient_docs,palier:1996 | 94315 | 68.3 | 58.0 | 129.8 | 159.7 | 696.1 |
| patient_docs,palier:transition | 4739 | 107.4 | 49.4 | 291.3 | 497.5 | 1219.5 |
| patient_dossier | 12363 | 40.5 | 27.8 | 61.7 | 89.8 | 700.2 |
| patient_dossier,palier:1400 | 3554 | 25.4 | 23.2 | 32.4 | 38.8 | 179.4 |
| patient_dossier,palier:1996 | 6533 | 38.6 | 32.5 | 61.2 | 75.5 | 571.6 |
| patient_dossier,palier:transition | 335 | 69.4 | 26.2 | 213.7 | 270.3 | 423.7 |
| patient_opposition | 12363 | 60.9 | 57.4 | 71.1 | 83.7 | 565.1 |
| patient_opposition,palier:1400 | 3554 | 56.2 | 55.7 | 60.9 | 63.6 | 124.2 |
| patient_opposition,palier:1996 | 6529 | 58.7 | 59.1 | 71.7 | 78.5 | 406.4 |
| patient_opposition,palier:transition | 339 | 73.9 | 57.5 | 131.5 | 164.8 | 358.2 |
| patient_search | 16415 | 50.7 | 55.6 | 70.1 | 82.6 | 578.1 |
| patient_search,palier:1400 | 4739 | 44.2 | 55.2 | 60.4 | 63.6 | 115.5 |
| patient_search,palier:1996 | 8663 | 48.5 | 56.3 | 70.4 | 77.4 | 475.1 |
| patient_search,palier:transition | 426 | 63.2 | 55.5 | 135.6 | 171.8 | 258.2 |
| read_content | 55095 | 60.5 | 40.0 | 91.9 | 141.4 | 1489.3 |
| read_content,palier:1400 | 15933 | 35.8 | 33.0 | 48.0 | 57.6 | 323.7 |
| read_content,palier:1996 | 28697 | 56.2 | 47.1 | 91.8 | 113.0 | 560.1 |
| read_content,palier:transition | 1345 | 119.8 | 40.5 | 365.5 | 433.6 | 747.5 |
| read_content_cold | 22040 | 458.0 | 452.0 | 508.7 | 532.0 | 1102.2 |
| read_content_cold,palier:1400 | 6485 | 446.1 | 444.7 | 493.8 | 507.5 | 592.4 |
| read_content_cold,palier:1996 | 11377 | 456.8 | 454.9 | 506.4 | 523.5 | 895.5 |
| read_content_cold,palier:transition | 567 | 473.5 | 455.4 | 572.8 | 641.4 | 876.9 |
| read_list | 110190 | 65.1 | 45.7 | 118.5 | 171.7 | 1525.7 |
| read_list,call:emails,palier:1400 | 15906 | 52.1 | 48.9 | 67.4 | 77.1 | 333.6 |
| read_list,call:emails,palier:1996 | 28678 | 82.1 | 71.1 | 127.0 | 152.8 | 654.0 |
| read_list,call:emails,palier:transition | 1236 | 206.8 | 66.3 | 552.1 | 626.9 | 1020.4 |
| read_list,call:folder,palier:1400 | 15906 | 29.5 | 14.9 | 32.7 | 115.2 | 530.2 |
| read_list,call:folder,palier:1996 | 28678 | 38.6 | 20.9 | 64.8 | 127.7 | 612.0 |
| read_list,call:folder,palier:transition | 1236 | 73.2 | 21.0 | 192.2 | 245.8 | 689.2 |
| read_list,palier:1400 | 31812 | 40.8 | 39.5 | 64.7 | 86.6 | 530.2 |
| read_list,palier:1996 | 57356 | 60.4 | 51.6 | 115.8 | 142.3 | 654.0 |
| read_list,palier:transition | 2472 | 140.0 | 58.0 | 449.7 | 553.9 | 1020.4 |
| search | 16498 | 404.3 | 343.1 | 541.0 | 816.9 | 2437.0 |
| search,palier:1400 | 4773 | 373.4 | 321.7 | 451.0 | 608.6 | 1546.9 |
| search,palier:1996 | 8617 | 399.3 | 349.5 | 494.7 | 636.0 | 1761.8 |
| search,palier:transition | 424 | 488.7 | 374.3 | 845.5 | 989.0 | 1744.7 |
| send | 15601 | 648.1 | 516.7 | 920.5 | 951.9 | 1668.4 |
| send,palier:1400 | 4659 | 632.2 | 490.1 | 899.6 | 924.2 | 1072.0 |
| send,palier:1996 | 8486 | 631.2 | 490.5 | 920.4 | 949.6 | 1374.0 |
| send,palier:transition | 496 | 637.1 | 534.8 | 935.6 | 1044.4 | 1409.9 |
| treatment | 13949 | 110.6 | 83.9 | 143.0 | 250.2 | 3530.7 |
| treatment,palier:1400 | 4010 | 71.8 | 78.3 | 93.4 | 101.7 | 275.8 |
| treatment,palier:1996 | 7249 | 114.9 | 90.9 | 143.1 | 178.4 | 3378.7 |
| treatment,palier:transition | 355 | 195.7 | 87.8 | 498.4 | 616.5 | 1359.0 |
| warmup | 21956 | 636.6 | 301.0 | 942.7 | 3017.1 | 11377.6 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-07T08:26:52.685000+00:00 → 2026-11-07T09:04:33.616000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-controle430.csv`) | ✅ 77458 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-15704` | 0.91 | 17 | 36 | 0.028 | 4.87 |
| `DESKTOP-DEV-X2C-35456` | 0.97 | 20 | 23 | 0.026 | 4.85 |
| `DESKTOP-DEV-X2C-38540` | 0.94 | 6 | 28 | 0.033 | 4.64 |
| `DESKTOP-DEV-X2C-62040` | 0.88 | 6 | 33 | 0.035 | 4.84 |
| `DESKTOP-DEV-X2C-6864` | 1.01 | 40 | 26 | 0.036 | 5.11 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.18 | 4.74 | 2424 |
| `com.docker.backend#34124` | 0.00 | 0.14 | 40 |
| `dcp#29168` | 0.00 | 0.04 | 14 |
| `dcp#36344` | 0.74 | 2.24 | 3263 |
| `dcp#38588` | 0.00 | 0.14 | 12 |
| `dcp#43812` | 0.00 | 0.00 | 12 |
| `dcp#47000` | 0.00 | 0.00 | 12 |
| `dcp#48104` | 0.00 | 0.09 | 14 |
| `dcp#48716` | 0.00 | 0.14 | 12 |
| `dcp#52516` | 0.00 | 0.04 | 12 |
| `dcp#62172` | 0.00 | 0.00 | 12 |
| `dcp#63708` | 0.00 | 0.00 | 12 |
| `dcp#63904` | 0.00 | 0.09 | 53 |
| `dcp#67852` | 0.00 | 0.04 | 13 |
| `dcp#68796` | 0.00 | 0.04 | 14 |
| `dcp#69752` | 0.00 | 0.00 | 12 |
| `dcp#69800` | 0.00 | 0.00 | 12 |
| `k6#162944` | 0.90 | 1.96 | 2915 |
| `mss.mail.api#15704` | 0.63 | 3.04 | 2247 |
| `mss.mail.api#35456` | 0.63 | 2.75 | 2221 |
| `mss.mail.api#38540` | 0.60 | 2.41 | 2204 |
| `mss.mail.api#62040` | 0.61 | 2.47 | 2254 |
| `mss.mail.api#6864` | 0.62 | 2.66 | 2397 |
| `mss.mail.e2e#5556` | 0.01 | 0.33 | 34 |
| `vmmemWSL#36464` | 5.35 | 11.85 | 60155 |
| `loadtest-otel-collector-wedvhjcv` | 0.02 | 0.17 | 120 |
| `loadtest-pgbouncer-uahsaccw` | 0.43 | 0.89 | 53 |
| `mss-mail-flagsmith-app-b6152948` | 0.12 | 0.37 | 475 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.12 | 123 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.04 | 158 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.09 | 188 |
| `mss-mail-rabbitmq-ngsqcjeb` | 0.01 | 0.05 | 141 |
| `mss-mail-redis-b6152948` | 0.28 | 1.32 | 984 |
| `mss-mail-rediscommander-ebypnedd` | 0.00 | 0.16 | 33 |
| `mss-mail-seq-b6152948` | 0.10 | 3.17 | 12298 |
| `postgres-pgvector` | 2.08 | 8.66 | 46664 |

- **Hôte** : CPU 62.2 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 62
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9330, cl_waiting max 11, cl_waiting_maintenance max 11, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 369, maxwait_ms max 369, maxwait_practitioner_ms max 0, sv_active max 52, sv_idle max 1605, sv_login max 1
- **Backends Postgres** : audit max 5, cache_mb max 40392, direct max 30, idle_over_60s max 230, majfault_per_s max 1, pooler max 1996, practitioner_databases max 1986, provision max 5, rss_mb max 6249, started_last_60s max 376, total max 2027, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 8142.5 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2476.8 | 450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 925.1 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 1790.7 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 809.6 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 909.9 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 739.8 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 1642.7 | 447 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2163.3 | 434 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 425.5 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 577.7 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 404.0 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 1959.3 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 457.5 | 448 |

- **p95 client global (k6)** : 501.5 ms
- **p95 serveur le plus élevé** : 8142.5 ms
- **Écart** : -7641.0 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 1.49 |
| Documents CDA /s | 1.49 |
| Durée traitement CDA (s, p95) | 0.70 |
| Événements de session IMAP /s | 4.16 |
| Recherches (s, p95) | 1.075 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.0 | 51.8 | 235 | 0.0 (0.0 %), p95 5 | 30.4 (58.6 %), p95 124 | 21.4 (41.3 %), p95 90 |
| `GetMail` | 11.1 | 45.4 | 649 | 4.0 (8.8 %), p95 70 | 38.0 (83.6 %), p95 584 | 3.4 (7.5 %), p95 53 |
| `GetMailsByUids` | 14.7 | 66.0 | 678 | 0.1 (0.1 %), p95 5 | 55.6 (84.2 %), p95 641 | 10.4 (15.7 %), p95 86 |

- **`EnrichPersistMail`** — sur 51.8 ms en moyenne (8.0 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 30.4 ms exécution SQL, 21.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 45.4 ms en moyenne (11.1 requête(s) SQL par appel) : 4.0 ms attente d'une connexion, 38.0 ms exécution SQL, 3.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 66.0 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 55.6 ms exécution SQL, 10.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.4 | 319.9 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.8 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.2 | 10.4 | 50.0 | 18.7 | 28.6 | 18.7 | 30.4 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.1 |

- **`GetMail`** — sur 3.4 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.8 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **319.9 µs**.

- **`GetMailsByUids`** — sur 10.4 ms de matérialisation, l'appel a construit 207.2 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.4 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.1 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **50.0 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4424.9 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 261.9 | 1900 | 131.6 (50.3 %), p95 247 | 10.8 (4.1 %), p95 90 | 43.9 (16.7 %), p95 650 | 39.2 (15.0 %), p95 220 | 36.4 (13.9 %), p95 190 |

- **Enrichir un message** — sur 261.9 ms en moyenne (3.8 message(s) par requête) : 131.6 ms fetch IMAP, 10.8 ms extraction XDM, 43.9 ms parsing CDA, 39.2 ms écritures base, 36.4 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `open_folder`, inf `resolve_folder`, 1.00 `fetch_whole_message`, 0.50 `fetch_bodystructure`, 0.50 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 238.5 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 637.2 | 995 | 0.0 (0.0 %), p95 5 | 18.7 (2.9 %), p95 61 | 221.9 (34.8 %), p95 477 | 396.4 (62.2 %), p95 488 | 415.5 (65.2 %), p95 953 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 637.2 ms en moyenne : 0.0 ms garde d'opposition, 18.7 ms construction MIME, 221.9 ms obtention de session SMTP, 396.4 ms transmission + acquittement, 415.5 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.439 | 2.407 | 102.04 |
| `smtp_session` | 0.005 | 0.988 | 10.67 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.356 | 2.382 | 0.488 | 10.67 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 2.24 |
| `GetAttachmentStream` | 0.488 | 2.425 | 2.425 | 0.713 | 1.58 |
| `GetEmailContent` | 0.005 | 0.492 | — | 0.492 | 13.47 |
| `GetFolders` | 0.005 | 0.982 | 0.987 | 0.243 | 8.33 |
| `ReadFolder` | 0.499 | 2.407 | 2.407 | 0.489 | 35.75 |
| `ReadToday` | 0.005 | 0.500 | — | 0.500 | 8.22 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.44 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.387** | 0.444 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.496 | 0.675 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.490 | 0.491 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.243 | 0.0 % |
| `ReadFolder` | **0.427** | 0.443 | 0.449 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.491 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 102.04 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.499 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 11.00 clients | 0 clients | 100.0 % | 29.9 % des échantillons |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-6864` | 40.00 éléments | 100 éléments | 40.0 % | 0.0 % — transitoire |
| conteneur `postgres-pgvector` (CPU) | 8.66 cœurs | 24 cœurs | 36.1 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 3.17 cœurs | 24 cœurs | 13.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#15704` (CPU) | 3.04 cœurs | 24 cœurs | 12.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#35456` (CPU) | 2.75 cœurs | 24 cœurs | 11.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#6864` (CPU) | 2.66 cœurs | 24 cœurs | 11.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#62040` (CPU) | 2.47 cœurs | 24 cœurs | 10.3 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 29.9 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 769 755

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 9 185 |
| OpenAI | gpt-4o-mini | prompt | 760 570 |
| OpenAI | text-embedding-3-small | embedding | 1 164 015 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 394 | 0 (0.0 %) | 0 | 10.5 | 1.07 | 0.95 | 2.44 |
| étiquetage (chat) | OpenAI | 394 | 0 (0.0 %) | 0 | 10.5 | 1.02 | 0.90 | 2.43 |
| embedding | OpenAI | 394 | 0 (0.0 %) | 0 | 10.5 | 0.55 | 0.44 | 1.60 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 8 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.5 | 25.0 |
| GPU — VRAM occupée (Mo) | 979 | 1 321 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 605.3** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.28** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **3.9 ms** | sur 760 763 requêtes HTTP k6 |
| Taux de cache (blocs) | **98.55 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **7.15 Mo/s (915 blocs/s)** | attente disque : 9.3 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **758 708 / 27 622** | rapport 27.5 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **181.7** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.33 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **7 / 0** | blocs écrits par les backends eux-mêmes : 22 % |
| Sessions ouvertes / s | **3.05** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **118.8 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 572 / 2 027** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **97 / 100 %** | fautes majeures/s max : 1.2 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **88 évictions `pg_stat_statements`** pendant le tir (98 340 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

134 formes de requête, 6 020 545 appels, **19.6 min** de temps serveur cumulé — soit **1.5 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **13.9 %** | 14 % | 168 606 | 0.22 | 0.97 | 1.0 | 18 | 15 % | 0 | 1 896 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 2 | **13.5 %** | 27 % | 8 526 | 0.01 | 18.64 | 51.2 | 340 | 0 % | 0 | 869 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **12.2 %** | 40 % | 8 543 | 0.01 | 16.71 | 51.0 | 392 | 1 % | 0 | 869 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **9.5 %** | 49 % | 88 717 | 0.12 | 1.26 | 18.0 | 213 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **5.5 %** | 55 % | 760 671 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 6 | **5.3 %** | 60 % | 47 429 | 0.06 | 1.31 | 10.2 | 251 | 0 % | 0 | 1 445 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 7 | **3.4 %** | 63 % | 168 205 | 0.22 | 0.24 | 1.0 | 8 | 1 % | 0 | 1 889 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 8 | **3.1 %** | 67 % | 8 548 | 0.01 | 4.31 | 20.0 | 620 | 1 % | 0 | 867 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 9 | **2.7 %** | 69 % | 15 393 | 0.02 | 2.08 | 1.0 | 24 | 59 % | 0 | 1 237 | **Postgres** — 59 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 10 | **2.7 %** | 72 % | 138 540 | 0.18 | 0.23 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 11 | **2.7 %** | 75 % | 8 458 | 0.01 | 3.71 | 20.0 | 621 | 1 % | 0 | 861 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 12 | **2.2 %** | 77 % | 5 783 | 0.01 | 4.44 | 178.0 | 540 | 1 % | 0 | 1 011 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 13 | **2.0 %** | 79 % | 282 590 | 0.37 | 0.08 | 2.0 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 14 | **1.8 %** | 81 % | 282 584 | 0.37 | 0.07 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 15 | **1.7 %** | 82 % | 94 968 | 0.12 | 0.21 | 18.0 | 5 | 0 % | 0 | 1 813 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 16 | **1.2 %** | 83 % | 88 718 | 0.12 | 0.15 | 18.0 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 17 | **1.1 %** | 85 % | 45 124 | 0.06 | 0.28 | 27.0 | 5 | 0 % | 0 | 1 406 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **1.0 %** | 86 % | 188 360 | 0.25 | 0.07 | 3.2 | 8 | 0 % | 0 | 1 901 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |
| 19 | **0.9 %** | 86 % | 143 815 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **0.9 %** | 87 % | 188 802 | 0.25 | 0.05 | 1.5 | 6 | 0 % | 0 | 1 900 | — | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 95.4 % | 87.6 % |
| INSERT | 3.7 % | 3.0 % |
| UPDATE | 0.4 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.4 % | 7.6 % |
| bases : praticien (N bases) | 91.3 % | 82.1 % |
| bases : unique (1 base) | 8.7 % | 17.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **18.6** | 116 | 8 526 | 13.5 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **16.7** | 95 | 8 543 | 12.2 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **4.4** | 172 | 5 783 | 2.2 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **4.3** | 157 | 8 548 | 3.1 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **3.7** | 65 | 8 458 | 2.7 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 896 | 222 208 | 198 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 185 | 141 015 | 0 | 5 | 0.1 Mo |
| `Mails` | 718 | 94 572 | 670 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 177 | 26 421 | 1 111 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 101 | 26 361 | 147 | 43 | 30.0 Mo |
| `MailRecipients` | 154 | 24 024 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 62 | 9 672 | 1 992 | 156 | 1.9 Mo |
| `PendingActions` | 162 | 4 761 | 0 | 31 | 0.1 Mo |
| `Tags` | 126 | 2 268 | 58 | 0 | 0.0 Mo |
| `MailFolders` | 335 | 920 | 327 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (5.5 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 98.6 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | 27 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 177 fois (26421 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 101 fois (26361 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 62 fois (9672 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°12 (2.2 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Postgres | 🟡 | requête n°9 (2.7 % du temps SQL) — 59 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°8 (3.1 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°15 (1.7 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-100515.tsv`, `pgserver-journey-debut-092640.tsv`, `pgserver-journey-fin-100520.tsv`, `pgtables-journey-debut-092645.tsv`, `pgtables-journey-fin-100524.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 246360 — dont **246360** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261107-controle430-100433.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
