# Rapport de tir — journey-courte-1400-1996-20261107-controle429

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261107-controle429-004823.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 3 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 21 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.037 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 755224 — **débit émergent global** : 334.1 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53763 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 334.1 | **157.0** | 64.1 | **527.6** | — | 13766.9 | 0.04 | 100.0 | 0 | 0 | 245966/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 212374 | 288.16 | 0.01 | 812.3 |
| **1996 médecins** | 1080 | 933 | 383057 | 410.56 | 0.01 | 1482.1 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 59 / 647 (n=63316) | 69 / 602 (n=114180) |
| 2 | Ouvrir / rafraîchir l'inbox | 40 / 99 (n=31620) | 57 / 182 (n=57130) |
| 3 | Ouvrir un message enrichi (servi base) | 34 / 68 (n=15811) | 57 / 154 (n=28565) |
| 4 | Ouvrir un message froid (fetch IMAP) | 445 / 510 (n=6414) | 461 / 536 (n=11448) |
| 5 | Recherche | 328 / 606 (n=4690) | 373 / 734 (n=8646) |
| 6 | Envoi (acquittement UI) | 487 / 928 (n=4813) | 502 / 969 (n=8557) |
| 7 | Télécharger une PJ (~124 Ko) | 37 / 78 (n=6295) | 64 / 236 (n=11483) |
| 8 | Marquer lu | 36 / 86 (n=12644) | 68 / 138 (n=22823) |
| 9 | Rechercher un patient | 55 / 67 (n=4618) | 58 / 88 (n=8527) |
| 10 | Ouvrir la page d'un dossier patient | 57 / 114 (n=7010) | 88 / 251 (n=12729) |
| 11 | Fiche patient complète (ressenti médecin) | 307 / 520 (n=3505) | 452 / 1092 (n=6364) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.6 / 20 | 34.5 / 65 | 8020 | 520 |
| **1996 médecins** | 14.4 / 20 | 34.2 / 65 | 14292 | 1092 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2228 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 616 ms en moyenne, 13767 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2249 / 3112 (magasin) | 2249 / 3112 (magasin) |
| Backends Postgres (moy/max) | 1240 / 1436 | 1994 / 2040 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 40/189 (21 %) | 76/158 (48 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/189 (0 %) | 0/158 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 40/189 (21 %) | 76/158 (48 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 23.0 | 473.9 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 23.0 | 473.9 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 122 / 394 | 96 / 267 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 92 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1405 | 2008 |
| Backends **directs** — audit + provisionnement (max) | 29 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 98.6 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 1 / 16 |
| RSS par réplica api-mail, Mo (moy/max) | 1164 / 1569 (5 réplicas) | 2046 / 2389 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1436.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2040.0 / 2500** (81.6 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15811)
- palier 1996 : cohorte 1996 chauffée à 98.3 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28565)

> ⓘ Chauffe : **300 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 59 (300) | 647 (1500) | 63316 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 40 (300) | 99 (1000) | 31620 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 34 (100) | 68 (500) | 15811 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 445 (800) | 510 (2500) | 6414 | ✅ |
| 5 | Recherche | 328 (500) | 606 (2000) | 4690 | ✅ |
| 6 | Envoi (acquittement UI) | 487 (1000) | 928 (3000) | 4813 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 37 (500) | 78 (2000) | 6295 | ✅ |
| 8 | Marquer lu | 36 (200) | 86 (1000) | 12644 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 67 (1500) | 4618 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 57 (500) | 114 (2000) | 7010 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 307 (1500) | 520 (4000) | 3505 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 69 (300) | 602 (1500) | 114180 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 57 (300) | 182 (1000) | 57130 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 57 (100) | 154 (500) | 28565 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 461 (800) | 536 (2500) | 11448 | ✅ |
| 5 | Recherche | 373 (500) | 734 (2000) | 8646 | ✅ |
| 6 | Envoi (acquittement UI) | 502 (1000) | 969 (3000) | 8557 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 64 (500) | 236 (2000) | 11483 | ✅ |
| 8 | Marquer lu | 68 (200) | 138 (1000) | 22823 | ✅ |
| 9 | Rechercher un patient | 58 (300) | 88 (1500) | 8527 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 88 (500) | 251 (2000) | 12729 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 452 (1500) | 1092 (4000) | 6364 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114180 | 169 | 602 | 19271.9 | 42.7 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8557 | 640 | 969 | 5472.9 | 12.1 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11448 | 464 | 536 | 5310.4 | 11.8 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57130 | 73 | 182 | 4150.9 | 9.2 % |
| 🟢 | Recherche (`search`) | 8646 | 426 | 734 | 3685.9 | 8.2 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28565 | 70 | 154 | 2007.5 | 4.5 % |
| 🟢 | Marquer lu (`mark_read`) | 22823 | 72 | 138 | 1636.0 | 3.6 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 11483 | 97 | 236 | 1113.6 | 2.5 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7146 | 130 | 239 | 929.1 | 2.1 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6364 | 108 | 251 | 684.4 | 1.5 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8527 | 53 | 88 | 451.5 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6365 | 63 | 92 | 397.9 | 0.9 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 3 🟠 · 9 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 19271.9 s, 42.7 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 8.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 4150.9 s, 9.2 %)
  - **dispersion p95/p50 = 3.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 1113.6 s, 2.5 %)
  - **dispersion p95/p50 = 3.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15829 | 394 | 986 | 6139.7 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15829 | 59 | 498 | 2177.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15829 | 22 | 163 | 749.5 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15829 | 57 | 71 | 919.0 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15810 | 16 | 117 | 485.9 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15810 | 51 | 91 | 888.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28545 | 403 | 990 | 11388.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28545 | 67 | 510 | 4127.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28545 | 38 | 198 | 1902.0 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28545 | 62 | 97 | 1854.2 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28565 | 25 | 135 | 1282.3 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28565 | 84 | 203 | 2868.6 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (990 ms de p95, 403 ms de p50, n=28545), qui porte **aussi** le temps serveur de l'étape (11388.2 s, 59 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (203 ms de p95, 84 ms de p50, n=28565), qui porte **aussi** le temps serveur de l'étape (2868.6 s, 69 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21883 | 97.5 | 50.8 | 162.9 | 371.1 | 6826.4 |
| attachment,palier:1400 | 6295 | 43.8 | 37.3 | 63.5 | 78.0 | 1046.3 |
| attachment,palier:1996 | 11483 | 97.0 | 63.7 | 155.7 | 235.9 | 1226.8 |
| attachment,palier:transition | 606 | 156.6 | 50.7 | 430.6 | 615.2 | 1084.2 |
| dashboard | 219520 | 176.3 | 67.0 | 476.2 | 666.1 | 7702.2 |
| dashboard,call:coverage,palier:1400 | 15829 | 58.1 | 57.0 | 65.1 | 70.5 | 173.2 |
| dashboard,call:coverage,palier:1996 | 28545 | 65.0 | 62.2 | 84.4 | 97.0 | 661.7 |
| dashboard,call:coverage,palier:transition | 1096 | 109.8 | 87.3 | 195.9 | 231.9 | 875.7 |
| dashboard,call:folder,palier:1400 | 15829 | 387.9 | 393.7 | 759.9 | 985.6 | 1504.1 |
| dashboard,call:folder,palier:1996 | 28545 | 399.0 | 403.1 | 778.0 | 989.9 | 2439.0 |
| dashboard,call:folder,palier:transition | 1096 | 464.2 | 468.1 | 769.4 | 917.8 | 1485.8 |
| dashboard,call:folders,palier:1400 | 15829 | 47.4 | 21.9 | 148.5 | 163.4 | 421.8 |
| dashboard,call:folders,palier:1996 | 28545 | 66.6 | 38.1 | 172.4 | 197.6 | 832.8 |
| dashboard,call:folders,palier:transition | 1096 | 111.5 | 96.8 | 222.6 | 289.4 | 832.6 |
| dashboard,call:today,palier:1400 | 15829 | 137.5 | 59.1 | 475.9 | 498.4 | 784.5 |
| dashboard,call:today,palier:1996 | 28545 | 144.6 | 66.6 | 485.9 | 510.0 | 1034.2 |
| dashboard,call:today,palier:transition | 1096 | 315.8 | 208.8 | 612.9 | 655.9 | 1362.1 |
| dashboard,palier:1400 | 63316 | 157.7 | 59.3 | 458.7 | 647.2 | 1504.1 |
| dashboard,palier:1996 | 114180 | 168.8 | 69.3 | 467.3 | 601.6 | 2439.0 |
| dashboard,palier:transition | 4384 | 250.3 | 142.4 | 583.6 | 676.2 | 1485.8 |
| mark_read | 43731 | 79.0 | 60.9 | 118.0 | 173.3 | 7349.7 |
| mark_read,palier:1400 | 12644 | 47.7 | 36.1 | 78.0 | 85.9 | 274.0 |
| mark_read,palier:1996 | 22823 | 71.7 | 68.0 | 116.7 | 138.1 | 670.5 |
| mark_read,palier:transition | 1196 | 93.2 | 65.8 | 243.5 | 296.8 | 791.7 |
| patient_docs | 175098 | 87.6 | 57.0 | 162.9 | 238.0 | 8691.6 |
| patient_docs,palier:1400 | 51133 | 47.1 | 43.7 | 84.3 | 100.5 | 278.4 |
| patient_docs,palier:1996 | 91814 | 84.5 | 67.8 | 168.0 | 211.1 | 823.7 |
| patient_docs,palier:transition | 4432 | 96.9 | 50.9 | 261.1 | 393.5 | 937.5 |
| patient_dossier | 12125 | 116.2 | 72.4 | 195.9 | 292.6 | 8538.5 |
| patient_dossier,palier:1400 | 3505 | 58.5 | 53.2 | 96.6 | 114.0 | 223.1 |
| patient_dossier,palier:1996 | 6364 | 107.5 | 88.3 | 198.4 | 250.7 | 777.0 |
| patient_dossier,palier:transition | 323 | 129.2 | 66.7 | 373.3 | 536.1 | 1051.7 |
| patient_opposition | 12124 | 64.8 | 59.0 | 81.1 | 99.3 | 1950.8 |
| patient_opposition,palier:1400 | 3505 | 57.5 | 56.6 | 63.6 | 69.4 | 145.3 |
| patient_opposition,palier:1996 | 6365 | 62.5 | 61.4 | 81.6 | 92.1 | 287.8 |
| patient_opposition,palier:transition | 322 | 69.4 | 57.2 | 117.2 | 136.2 | 335.1 |
| patient_search | 16148 | 56.6 | 55.8 | 77.6 | 98.1 | 7349.5 |
| patient_search,palier:1400 | 4618 | 45.1 | 55.3 | 63.0 | 67.0 | 127.4 |
| patient_search,palier:1996 | 8527 | 52.9 | 58.4 | 77.9 | 87.6 | 611.5 |
| patient_search,palier:transition | 441 | 60.8 | 55.7 | 107.7 | 131.2 | 775.3 |
| read_content | 54880 | 75.9 | 45.0 | 123.9 | 198.4 | 7959.6 |
| read_content,palier:1400 | 15811 | 38.4 | 34.5 | 56.9 | 68.1 | 197.3 |
| read_content,palier:1996 | 28565 | 70.3 | 56.7 | 122.9 | 153.9 | 727.4 |
| read_content,palier:transition | 1385 | 103.7 | 46.5 | 292.0 | 367.9 | 854.6 |
| read_content_cold | 22115 | 467.4 | 455.8 | 519.6 | 549.8 | 6886.9 |
| read_content_cold,palier:1400 | 6414 | 447.0 | 445.0 | 495.4 | 509.7 | 673.6 |
| read_content_cold,palier:1996 | 11448 | 463.9 | 460.7 | 517.2 | 536.2 | 969.6 |
| read_content_cold,palier:transition | 612 | 483.4 | 468.8 | 567.5 | 629.2 | 1229.5 |
| read_list | 109760 | 79.2 | 48.7 | 144.2 | 230.7 | 7952.4 |
| read_list,call:emails,palier:1400 | 15810 | 56.2 | 51.4 | 77.7 | 90.8 | 223.4 |
| read_list,call:emails,palier:1996 | 28565 | 100.4 | 83.9 | 166.0 | 203.3 | 789.4 |
| read_list,call:emails,palier:transition | 1262 | 171.3 | 79.7 | 449.0 | 530.0 | 951.9 |
| read_list,call:folder,palier:1400 | 15810 | 30.7 | 15.6 | 39.0 | 116.8 | 526.1 |
| read_list,call:folder,palier:1996 | 28565 | 44.9 | 25.1 | 85.3 | 135.3 | 729.2 |
| read_list,call:folder,palier:transition | 1262 | 63.8 | 26.2 | 157.0 | 206.4 | 801.8 |
| read_list,palier:1400 | 31620 | 43.4 | 40.3 | 73.7 | 99.1 | 526.1 |
| read_list,palier:1996 | 57130 | 72.7 | 57.3 | 142.4 | 181.8 | 789.4 |
| read_list,palier:transition | 2524 | 117.5 | 59.7 | 336.0 | 459.5 | 951.9 |
| search | 16344 | 426.3 | 358.7 | 577.2 | 879.9 | 6468.4 |
| search,palier:1400 | 4690 | 377.6 | 327.9 | 463.6 | 605.9 | 1534.3 |
| search,palier:1996 | 8646 | 426.3 | 373.1 | 540.4 | 734.1 | 1730.3 |
| search,palier:transition | 450 | 444.4 | 359.4 | 695.5 | 840.6 | 1682.5 |
| send | 15732 | 658.0 | 522.7 | 931.7 | 974.2 | 3841.0 |
| send,palier:1400 | 4813 | 629.5 | 487.2 | 904.9 | 928.5 | 1205.6 |
| send,palier:1996 | 8557 | 639.6 | 502.2 | 934.1 | 968.9 | 1956.7 |
| send,palier:transition | 461 | 656.0 | 543.3 | 970.9 | 1051.3 | 1800.1 |
| treatment | 13794 | 126.5 | 88.4 | 178.4 | 320.2 | 5677.9 |
| treatment,palier:1400 | 4010 | 75.2 | 79.3 | 101.7 | 113.5 | 220.5 |
| treatment,palier:1996 | 7146 | 130.0 | 99.1 | 178.5 | 238.9 | 4542.7 |
| treatment,palier:transition | 372 | 168.8 | 92.9 | 384.3 | 505.9 | 973.1 |
| warmup | 21956 | 616.2 | 404.1 | 909.6 | 1960.1 | 13766.9 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-06T23:10:43.159000+00:00 → 2026-11-06T23:48:23.802000+00:00 (2261 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-controle429.csv`) | ✅ 75989 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-47120` | 0.95 | 17 | 23 | 0.033 | 4.91 |
| `DESKTOP-DEV-X2C-66852` | 0.92 | 32 | 26 | 0.045 | 20.82 |
| `DESKTOP-DEV-X2C-69684` | 0.92 | 22 | 29 | 0.038 | 7.86 |
| `DESKTOP-DEV-X2C-69832` | 0.95 | 19 | 24 | 0.025 | 4.69 |
| `DESKTOP-DEV-X2C-8740` | 0.96 | 22 | 29 | 0.035 | 8.01 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.37 | 4.58 | 2218 |
| `com.docker.backend#34124` | 0.01 | 0.23 | 40 |
| `dcp#15592` | 0.00 | 0.09 | 12 |
| `dcp#32760` | 0.00 | 0.00 | 12 |
| `dcp#35112` | 0.00 | 0.00 | 12 |
| `dcp#39168` | 0.00 | 0.00 | 12 |
| `dcp#41584` | 0.00 | 0.09 | 14 |
| `dcp#43988` | 0.00 | 0.04 | 12 |
| `dcp#44688` | 0.00 | 0.04 | 13 |
| `dcp#46204` | 0.00 | 0.04 | 12 |
| `dcp#53448` | 0.00 | 0.00 | 12 |
| `dcp#55580` | 0.82 | 2.51 | 3170 |
| `dcp#61700` | 0.00 | 0.04 | 11 |
| `dcp#63360` | 0.00 | 0.00 | 12 |
| `dcp#64900` | 0.00 | 0.14 | 14 |
| `dcp#69540` | 0.00 | 0.14 | 54 |
| `dcp#70312` | 0.00 | 0.14 | 14 |
| `k6#149754` | 0.87 | 1.89 | 2895 |
| `mss.mail.api#47120` | 0.63 | 2.31 | 2389 |
| `mss.mail.api#66852` | 0.67 | 2.48 | 2224 |
| `mss.mail.api#69684` | 0.67 | 2.90 | 2230 |
| `mss.mail.api#69832` | 0.68 | 2.59 | 2286 |
| `mss.mail.api#8740` | 0.69 | 2.87 | 2257 |
| `mss.mail.e2e#56424` | 0.01 | 0.19 | 33 |
| `vmmemWSL#36464` | 5.81 | 14.51 | 65463 |
| `loadtest-otel-collector-sbmhtkfx` | 0.02 | 0.14 | 120 |
| `loadtest-pgbouncer-mfqwhtse` | 0.51 | 0.96 | 53 |
| `mss-mail-flagsmith-app-b6152948` | 0.11 | 0.55 | 469 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.09 | 190 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.06 | 157 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.10 | 293 |
| `mss-mail-rabbitmq-mmjarfmw` | 0.01 | 0.06 | 159 |
| `mss-mail-redis-b6152948` | 0.27 | 1.38 | 948 |
| `mss-mail-rediscommander-suxnwzbc` | 0.00 | 0.29 | 51 |
| `mss-mail-seq-b6152948` | 0.11 | 1.04 | 13670 |
| `postgres-pgvector` | 2.27 | 11.05 | 48845 |

- **Hôte** : CPU 65.4 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 52
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9362, cl_waiting max 23, cl_waiting_maintenance max 23, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 474, maxwait_ms max 474, maxwait_practitioner_ms max 0, sv_active max 78, sv_idle max 1629, sv_login max 2
- **Backends Postgres** : audit max 5, cache_mb max 40560, direct max 29, idle_over_60s max 204, majfault_per_s max 28, pooler max 2008, practitioner_databases max 1999, provision max 5, rss_mb max 6183, started_last_60s max 394, total max 2040, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 6783.0 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2410.7 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 1736.8 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 3279.8 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 924.9 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 1919.2 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 1610.5 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2044.3 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2444.8 | 435 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 498.7 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 3017.9 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 430.3 | 442 |
| `api/v{version:apiVersion}/Search/semantic` | 2323.1 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 472.9 | 447 |

- **p95 client global (k6)** : 527.6 ms
- **p95 serveur le plus élevé** : 6783.0 ms
- **Écart** : -6255.4 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 1.56 |
| Documents CDA /s | 1.58 |
| Durée traitement CDA (s, p95) | 0.74 |
| Événements de session IMAP /s | 4.31 |
| Recherches (s, p95) | 1.704 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 61.5 | 235 | 0.0 (0.0 %), p95 5 | 35.5 (57.8 %), p95 215 | 26.0 (42.2 %), p95 220 |
| `GetMail` | 11.1 | 54.3 | 812 | 4.8 (8.8 %), p95 145 | 45.9 (84.5 %), p95 717 | 3.6 (6.7 %), p95 22 |
| `GetMailsByUids` | 14.7 | 81.0 | 812 | 0.1 (0.1 %), p95 5 | 69.5 (85.7 %), p95 731 | 11.5 (14.1 %), p95 74 |

- **`EnrichPersistMail`** — sur 61.5 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 35.5 ms exécution SQL, 26.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 54.3 ms en moyenne (11.1 requête(s) SQL par appel) : 4.8 ms attente d'une connexion, 45.9 ms exécution SQL, 3.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 81.0 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 69.5 ms exécution SQL, 11.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.6 | 340.8 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.8 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.2 | 11.5 | 55.3 | 18.7 | 28.6 | 18.7 | 30.5 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.6 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.8 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **340.8 µs**.

- **`GetMailsByUids`** — sur 11.5 ms de matérialisation, l'appel a construit 207.2 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.5 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **55.3 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4001.9 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 318.9 | 2200 | 128.5 (40.3 %), p95 249 | 12.4 (3.9 %), p95 73 | 87.3 (27.4 %), p95 737 | 46.9 (14.7 %), p95 229 | 43.7 (13.7 %), p95 220 |

- **Enrichir un message** — sur 318.9 ms en moyenne (3.8 message(s) par requête) : 128.5 ms fetch IMAP, 12.4 ms extraction XDM, 87.3 ms parsing CDA, 46.9 ms écritures base, 43.7 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **3.02 aller(s)-retour(s) IMAP par message enrichi** — 1.01 `fetch_whole_message`, 0.50 `open_folder`, 0.50 `resolve_folder`, 0.50 `fetch_bodystructure`, 0.50 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 275.6 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 638.2 | 1006 | 0.0 (0.0 %), p95 5 | 22.4 (3.5 %), p95 78 | 218.5 (34.2 %), p95 476 | 397.1 (62.2 %), p95 489 | 414.5 (64.9 %), p95 964 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 638.2 ms en moyenne : 0.0 ms garde d'opposition, 22.4 ms construction MIME, 218.5 ms obtention de session SMTP, 397.1 ms transmission + acquittement, 414.5 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.443 | 2.250 | 97.77 |
| `smtp_session` | 0.005 | 0.988 | 10.36 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.403 | 2.353 | 0.490 | 10.40 |
| `EnrichEmails` | 0.005 | 0.450 | — | 0.450 | 2.38 |
| `GetAttachmentStream` | 0.488 | 2.425 | 2.425 | 0.713 | 1.65 |
| `GetEmailContent` | 0.005 | 0.493 | — | 0.493 | 13.47 |
| `GetFolders` | 0.005 | 1.000 | 1.000 | 0.244 | 7.62 |
| `ReadFolder` | 0.500 | 2.400 | 2.400 | 0.487 | 35.67 |
| `ReadToday` | 0.005 | 0.497 | 2.425 | 0.497 | 7.87 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.24 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.489 | 0.0 % |
| `EnrichEmails` | **0.387** | 0.430 | 0.450 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.495 | 0.500 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.491 | 0.492 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.430** | 0.441 | 0.446 | 0.0 % |
| `ReadToday` | **0.489** | 0.490 | 0.491 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.488 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 97.77 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.500 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 23.00 clients | 0 clients | 100.0 % | 33.5 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 11.05 cœurs | 24 cœurs | 46.0 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-66852` | 32.00 éléments | 100 éléments | 32.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#69684` (CPU) | 2.90 cœurs | 24 cœurs | 12.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#8740` (CPU) | 2.87 cœurs | 24 cœurs | 12.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#69832` (CPU) | 2.59 cœurs | 24 cœurs | 10.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#66852` (CPU) | 2.48 cœurs | 24 cœurs | 10.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#47120` (CPU) | 2.31 cœurs | 24 cœurs | 9.6 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 33.5 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 690 108

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 8 166 |
| OpenAI | gpt-4o-mini | prompt | 681 942 |
| OpenAI | text-embedding-3-small | embedding | 1 023 072 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 361 | 0 (0.0 %) | 0 | 9.6 | 1.13 | 0.99 | 2.46 |
| étiquetage (chat) | OpenAI | 361 | 0 (0.0 %) | 0 | 9.6 | 1.06 | 0.93 | 2.45 |
| embedding | OpenAI | 362 | 0 (0.0 %) | 0 | 9.6 | 0.57 | 0.45 | 1.65 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 5 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.1 | 3.0 |
| GPU — VRAM occupée (Mo) | 1 906 | 1 930 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 582.2** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.52** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **4.7 ms** | sur 755 224 requêtes HTTP k6 |
| Taux de cache (blocs) | **96.02 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **20.10 Mo/s (2 573 blocs/s)** | attente disque : 11.9 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **760 484 / 35 283** | rapport 21.6 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **181.0** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.33 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 22 % |
| Sessions ouvertes / s | **2.90** | abandonnées 2, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **117.7 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 565 / 2 040** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **97 / 100 %** | fautes majeures/s max : 28.2 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **86 évictions `pg_stat_statements`** pendant le tir (99 250 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

135 formes de requête, 5 970 315 appels, **22.9 min** de temps serveur cumulé — soit **1.8 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **13.1 %** | 13 % | 166 052 | 0.22 | 1.09 | 1.0 | 18 | 23 % | 0 | 1 895 | **Postgres** — 23 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 2 | **12.1 %** | 25 % | 8 483 | 0.01 | 19.61 | 50.9 | 338 | 1 % | 0 | 888 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **11.2 %** | 36 % | 8 555 | 0.01 | 18.04 | 51.1 | 392 | 2 % | 0 | 900 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **8.5 %** | 45 % | 88 325 | 0.12 | 1.32 | 18.0 | 213 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **6.1 %** | 51 % | 3 941 | 0.01 | 21.41 | 29.7 | 471 | 37 % | 0 | 535 | **Postgres** — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 6 | **5.1 %** | 56 % | 754 955 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 7 | **4.7 %** | 61 % | 47 234 | 0.06 | 1.35 | 10.2 | 250 | 0 % | 0 | 1 442 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 8 | **3.5 %** | 64 % | 8 514 | 0.01 | 5.70 | 20.0 | 618 | 3 % | 0 | 890 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 9 | **3.4 %** | 68 % | 165 648 | 0.22 | 0.28 | 1.0 | 8 | 2 % | 0 | 1 884 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 10 | **2.9 %** | 71 % | 8 500 | 0.01 | 4.69 | 20.0 | 621 | 3 % | 0 | 888 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 11 | **2.6 %** | 73 % | 135 700 | 0.18 | 0.26 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 12 | **2.0 %** | 75 % | 88 328 | 0.12 | 0.31 | 18.0 | 21 | 0 % | 0 | 1 996 | — | `SELECT DISTINCT m."MailId" FROM "MailContents" AS m WHERE m."MailId" = ANY ($1)` |
| 13 | **1.8 %** | 77 % | 279 663 | 0.37 | 0.09 | 2.1 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 14 | **1.7 %** | 79 % | 15 770 | 0.02 | 1.51 | 1.0 | 24 | 55 % | 0 | 1 267 | **Postgres** — 55 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 15 | **1.6 %** | 80 % | 94 620 | 0.13 | 0.23 | 18.0 | 5 | 0 % | 0 | 1 756 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 16 | **1.6 %** | 82 % | 279 658 | 0.37 | 0.08 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 17 | **1.3 %** | 83 % | 4 736 | 0.01 | 3.77 | 178.0 | 540 | 2 % | 0 | 836 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 18 | **1.0 %** | 84 % | 35 892 | 0.05 | 0.40 | 1.0 | 9 | 4 % | 0 | 1 543 | — | `INSERT INTO "PendingActions" ("Id", "ActionType", "ClaimedAt", "CreatedAt", "FolderPath", "LastError", "MailUid", "Payl…` |
| 19 | **1.0 %** | 85 % | 88 325 | 0.12 | 0.16 | 18.0 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 20 | **1.0 %** | 86 % | 45 030 | 0.06 | 0.29 | 27.0 | 5 | 0 % | 0 | 1 404 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 95.4 % | 87.7 % |
| INSERT | 3.9 % | 3.0 % |
| UPDATE | 0.3 % | 1.3 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.3 % | 7.5 % |
| bases : praticien (N bases) | 92.0 % | 82.2 % |
| bases : unique (1 base) | 8.0 % | 17.8 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **21.4** | 7 613 | 3 941 | 6.1 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **19.6** | 165 | 8 483 | 12.1 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **18.0** | 195 | 8 555 | 11.2 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **5.7** | 320 | 8 514 | 3.5 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **4.7** | 206 | 8 500 | 2.9 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 924 | 229 152 | 210 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 211 | 144 109 | 0 | 5 | 0.1 Mo |
| `Mails` | 759 | 104 578 | 693 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 177 | 26 117 | 946 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 88 | 22 968 | 117 | 43 | 30.0 Mo |
| `MailRecipients` | 135 | 21 060 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 72 | 11 232 | 2 118 | 156 | 1.9 Mo |
| `PendingActions` | 156 | 4 570 | 0 | 31 | 0.1 Mo |
| `Tags` | 104 | 1 872 | 81 | 0 | 0.0 Mo |
| `MailFolders` | 308 | 838 | 279 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°6 (5.1 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 96.0 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°1 (13.1 % du temps SQL) — 23 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Postgres | 🟠 | requête n°5 (6.1 % du temps SQL) — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 22 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 177 fois (26117 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 88 fois (22968 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 72 fois (11232 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°17 (1.3 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Postgres | 🟡 | requête n°14 (1.7 % du temps SQL) — 55 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°8 (3.5 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°15 (1.6 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-004908.tsv`, `pgserver-journey-debut-001034.tsv`, `pgserver-journey-fin-004912.tsv`, `pgtables-journey-debut-001038.tsv`, `pgtables-journey-fin-004918.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 245966 — dont **245966** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261107-controle429-004823.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
