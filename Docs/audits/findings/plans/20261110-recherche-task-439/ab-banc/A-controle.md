# Rapport de tir — journey-courte-1400-1996-20261110-t439-controle

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261110-t439-controle-140348.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 1 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** sur le chemin du médecin (`cl_waiting` non nul sur 15 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.013 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 765996 — **débit émergent global** : 338.9 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 54091 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 338.9 | **134.4** | 58.0 | **482.4** | — | 11154.6 | 0.01 | 100.0 | 0 | 0 | 248516/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214920 | 291.61 | 0.00 | 802.7 |
| **1996 médecins** | 1080 | 933 | 387632 | 415.47 | 0.01 | 1425.8 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 58 / 636 (n=63672) | 64 / 585 (n=114620) |
| 2 | Ouvrir / rafraîchir l'inbox | 39 / 89 (n=31832) | 51 / 140 (n=57256) |
| 3 | Ouvrir un message enrichi (servi base) | 32 / 56 (n=15900) | 44 / 110 (n=28626) |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 / 506 (n=6386) | 455 / 523 (n=11414) |
| 5 | Recherche | 321 / 577 (n=4862) | 344 / 620 (n=8622) |
| 6 | Envoi (acquittement UI) | 502 / 922 (n=4716) | 487 / 946 (n=8570) |
| 7 | Télécharger une PJ (~124 Ko) | 36 / 63 (n=6440) | 50 / 130 (n=11472) |
| 8 | Marquer lu | 33 / 80 (n=12826) | 52 / 111 (n=22975) |
| 9 | Rechercher un patient | 55 / 64 (n=4772) | 56 / 79 (n=8689) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 63 (n=7068) | 59 / 79 (n=13047) |
| 11 | Fiche patient complète (ressenti médecin) | 257 / 402 (n=3534) | 336 / 680 (n=6523) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.9 / 20 | 35.2 / 60 | 7902 | 402 |
| **1996 médecins** | 14.6 / 20 | 34.4 / 60 | 14384 | 680 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2248 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 545 ms en moyenne, 11155 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2274 / 3098 (magasin) | 2274 / 3098 (magasin) |
| Backends Postgres (moy/max) | 1244 / 1431 | 1991 / 2027 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` — chemin du médecin (échant. non nuls) | 28/184 (15 %) | 59/157 (38 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 28/184 (15 %) | 59/157 (38 %) |
| …dont **registre** des comptes (échant. non nuls) | 0/184 (0 %) | 0/157 (0 %) |
| …dont **maintenance** (échant. non nuls) | 0/184 (0 %) | 0/157 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 24.9 | 21.5 |
| …dont bases **praticien** — chemin du médecin | 24.9 | 21.5 |
| …dont **registre** des comptes — chemin du médecin | 0.0 | 0.0 |
| …dont **maintenance** (`postgres`, `pgbouncer`) | 0.0 | 0.0 |
| Attente PgBouncer cumulée — chemin du médecin (s) | 635.9 | 1115.9 |
| …par transaction du médecin (ms) | 0.3 | 0.4 |
| …part du temps des transactions (attente comprise) | 18.6 % | 19.4 % |
| …part du temps des requêtes HTTP du palier (k6) | 3.0 % | 2.7 % |
| Attente PgBouncer cumulée — maintenance (s) | 0.0 | 0.0 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | 0.008 / 0.013 / 0.026 | 0.011 / 0.017 / 0.027 |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 118 / 367 | 100 / 281 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 12 | 121 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1402 | 1996 |
| Backends **directs** — audit + provisionnement (max) | 30 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 75.7 | 96.9 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 | 0 / 0 |
| RSS par réplica api-mail, Mo (moy/max) | 1175 / 1653 (5 réplicas) | 2042 / 2279 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1431.0 / 2500** (57.2 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2027.0 / 2500** (81.1 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 99.9 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15900)
- palier 1996 : cohorte 1996 chauffée à 99.7 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28626)

> ⓘ Chauffe : **301 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 58 (300) | 636 (1500) | 63672 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 39 (300) | 89 (1000) | 31832 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 32 (100) | 56 (500) | 15900 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 (800) | 506 (2500) | 6386 | ✅ |
| 5 | Recherche | 321 (500) | 577 (2000) | 4862 | ✅ |
| 6 | Envoi (acquittement UI) | 502 (1000) | 922 (3000) | 4716 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 36 (500) | 63 (2000) | 6440 | ✅ |
| 8 | Marquer lu | 33 (200) | 80 (1000) | 12826 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 64 (1500) | 4772 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 63 (2000) | 7068 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 257 (1500) | 402 (4000) | 3534 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 64 (300) | 585 (1500) | 114620 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 51 (300) | 140 (1000) | 57256 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 44 (100) | 110 (500) | 28626 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 455 (800) | 523 (2500) | 11414 | ✅ |
| 5 | Recherche | 344 (500) | 620 (2000) | 8622 | ✅ |
| 6 | Envoi (acquittement UI) | 487 (1000) | 946 (3000) | 8570 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 50 (500) | 130 (2000) | 11472 | ✅ |
| 8 | Marquer lu | 52 (200) | 111 (1000) | 22975 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 79 (1500) | 8689 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 79 (2000) | 13047 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 336 (1500) | 680 (4000) | 6523 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114620 | 163 | 585 | 18651.2 | 45.1 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8570 | 626 | 946 | 5363.6 | 13.0 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11414 | 457 | 523 | 5213.9 | 12.6 % |
| 🟢 | Recherche (`search`) | 8622 | 393 | 620 | 3388.2 | 8.2 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57256 | 59 | 140 | 3361.2 | 8.1 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28626 | 54 | 110 | 1534.7 | 3.7 % |
| 🟢 | Marquer lu (`mark_read`) | 22975 | 59 | 111 | 1366.9 | 3.3 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11472 | 66 | 130 | 753.5 | 1.8 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7192 | 100 | 159 | 718.6 | 1.7 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8689 | 48 | 79 | 421.3 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6524 | 58 | 79 | 381.3 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6523 | 38 | 74 | 245.4 | 0.6 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 1 🟠 · 11 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 18651.2 s, 45.1 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 9.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15918 | 390 | 992 | 6118.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15918 | 58 | 495 | 2164.0 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15918 | 19 | 161 | 698.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15918 | 56 | 66 | 906.2 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15916 | 15 | 117 | 471.6 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15916 | 48 | 76 | 814.9 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28655 | 400 | 994 | 11299.1 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28655 | 63 | 505 | 4019.1 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28655 | 28 | 181 | 1592.9 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28655 | 60 | 83 | 1740.1 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28628 | 20 | 126 | 1089.5 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28628 | 68 | 151 | 2271.7 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (994 ms de p95, 400 ms de p50, n=28655), qui porte **aussi** le temps serveur de l'étape (11299.1 s, 61 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (151 ms de p95, 68 ms de p50, n=28628), qui porte **aussi** le temps serveur de l'étape (2271.7 s, 68 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21945 | 63.1 | 43.6 | 98.9 | 148.2 | 1183.2 |
| attachment,palier:1400 | 6440 | 39.4 | 35.8 | 53.8 | 63.3 | 184.7 |
| attachment,palier:1996 | 11472 | 65.7 | 49.9 | 101.3 | 130.1 | 1183.2 |
| attachment,palier:transition | 642 | 117.3 | 51.4 | 285.9 | 446.0 | 1045.1 |
| dashboard | 220840 | 164.3 | 62.2 | 468.7 | 578.6 | 1623.4 |
| dashboard,call:coverage,palier:1400 | 15918 | 56.9 | 56.2 | 62.8 | 65.8 | 136.0 |
| dashboard,call:coverage,palier:1996 | 28655 | 60.7 | 59.7 | 74.9 | 83.3 | 277.1 |
| dashboard,call:coverage,palier:transition | 1056 | 88.6 | 69.9 | 148.7 | 172.7 | 494.5 |
| dashboard,call:folder,palier:1400 | 15918 | 384.3 | 390.0 | 761.0 | 991.8 | 1538.6 |
| dashboard,call:folder,palier:1996 | 28655 | 394.3 | 399.8 | 775.9 | 994.0 | 1579.4 |
| dashboard,call:folder,palier:transition | 1056 | 434.5 | 449.3 | 702.5 | 808.1 | 1623.4 |
| dashboard,call:folders,palier:1400 | 15918 | 43.9 | 18.9 | 146.7 | 161.4 | 421.0 |
| dashboard,call:folders,palier:1996 | 28655 | 55.6 | 27.6 | 161.4 | 181.3 | 467.8 |
| dashboard,call:folders,palier:transition | 1056 | 81.6 | 63.5 | 170.1 | 217.5 | 417.6 |
| dashboard,call:today,palier:1400 | 15918 | 135.9 | 58.0 | 474.5 | 495.3 | 737.1 |
| dashboard,call:today,palier:1996 | 28655 | 140.3 | 62.8 | 481.4 | 504.7 | 1092.0 |
| dashboard,call:today,palier:transition | 1056 | 287.2 | 137.9 | 580.5 | 612.7 | 1169.8 |
| dashboard,palier:1400 | 63672 | 155.3 | 58.2 | 457.5 | 636.0 | 1538.6 |
| dashboard,palier:1996 | 114620 | 162.7 | 63.6 | 464.6 | 584.7 | 1579.4 |
| dashboard,palier:transition | 4224 | 223.0 | 113.0 | 536.0 | 602.0 | 1623.4 |
| mark_read | 44174 | 59.0 | 46.7 | 93.8 | 119.1 | 497.3 |
| mark_read,palier:1400 | 12826 | 45.1 | 32.7 | 75.0 | 79.7 | 247.6 |
| mark_read,palier:1996 | 22975 | 59.5 | 52.3 | 95.4 | 110.6 | 423.1 |
| mark_read,palier:transition | 1247 | 79.3 | 66.7 | 173.1 | 207.3 | 410.1 |
| patient_docs | 181883 | 63.0 | 50.7 | 114.5 | 153.4 | 960.3 |
| patient_docs,palier:1400 | 52486 | 42.7 | 40.4 | 75.3 | 88.0 | 187.1 |
| patient_docs,palier:1996 | 95138 | 65.0 | 56.2 | 121.6 | 150.8 | 513.0 |
| patient_docs,palier:transition | 4842 | 75.4 | 52.4 | 163.2 | 257.5 | 585.0 |
| patient_dossier | 12396 | 36.3 | 27.6 | 57.4 | 79.7 | 438.4 |
| patient_dossier,palier:1400 | 3534 | 25.3 | 23.2 | 32.7 | 40.1 | 108.4 |
| patient_dossier,palier:1996 | 6523 | 37.6 | 31.3 | 59.5 | 73.8 | 296.7 |
| patient_dossier,palier:transition | 332 | 51.6 | 29.7 | 124.7 | 157.0 | 354.2 |
| patient_opposition | 12396 | 59.2 | 57.4 | 69.6 | 80.7 | 382.0 |
| patient_opposition,palier:1400 | 3534 | 56.1 | 55.6 | 60.8 | 63.2 | 122.8 |
| patient_opposition,palier:1996 | 6524 | 58.4 | 58.8 | 70.7 | 78.5 | 215.3 |
| patient_opposition,palier:transition | 332 | 67.4 | 57.9 | 95.3 | 134.3 | 382.0 |
| patient_search | 16593 | 48.7 | 55.6 | 68.5 | 79.6 | 443.0 |
| patient_search,palier:1400 | 4772 | 44.1 | 55.3 | 60.5 | 63.7 | 118.6 |
| patient_search,palier:1996 | 8689 | 48.5 | 56.2 | 69.9 | 78.9 | 165.9 |
| patient_search,palier:transition | 450 | 58.4 | 56.9 | 89.6 | 115.6 | 443.0 |
| read_content | 55210 | 52.3 | 38.7 | 84.9 | 122.8 | 775.5 |
| read_content,palier:1400 | 15900 | 34.6 | 32.3 | 46.9 | 55.8 | 153.8 |
| read_content,palier:1996 | 28626 | 53.6 | 44.5 | 88.2 | 110.4 | 421.4 |
| read_content,palier:transition | 1405 | 78.2 | 43.2 | 207.6 | 261.0 | 526.5 |
| read_content_cold | 22091 | 454.5 | 451.4 | 506.1 | 524.8 | 1137.2 |
| read_content_cold,palier:1400 | 6386 | 445.1 | 443.8 | 492.9 | 506.4 | 633.0 |
| read_content_cold,palier:1996 | 11414 | 456.8 | 455.2 | 507.1 | 523.4 | 698.2 |
| read_content_cold,palier:transition | 646 | 462.5 | 454.2 | 523.0 | 567.3 | 777.4 |
| read_list | 110420 | 57.7 | 44.8 | 110.2 | 149.7 | 759.7 |
| read_list,call:emails,palier:1400 | 15916 | 51.2 | 48.0 | 67.0 | 75.7 | 163.3 |
| read_list,call:emails,palier:1996 | 28628 | 79.4 | 68.0 | 122.4 | 151.0 | 527.3 |
| read_list,call:emails,palier:transition | 1242 | 133.8 | 73.6 | 332.5 | 373.7 | 631.3 |
| read_list,call:folder,palier:1400 | 15916 | 29.6 | 14.8 | 33.7 | 117.1 | 525.0 |
| read_list,call:folder,palier:1996 | 28628 | 38.1 | 20.3 | 65.3 | 126.1 | 568.3 |
| read_list,call:folder,palier:transition | 1242 | 53.6 | 23.2 | 124.0 | 157.7 | 575.6 |
| read_list,palier:1400 | 31832 | 40.4 | 38.8 | 64.6 | 89.0 | 525.0 |
| read_list,palier:1996 | 57256 | 58.7 | 50.6 | 111.7 | 139.6 | 568.3 |
| read_list,palier:transition | 2484 | 93.7 | 55.1 | 270.0 | 341.7 | 631.3 |
| search | 16620 | 396.3 | 340.9 | 523.1 | 714.7 | 1784.6 |
| search,palier:1400 | 4862 | 370.3 | 321.4 | 454.9 | 576.7 | 1544.6 |
| search,palier:1996 | 8622 | 393.0 | 343.9 | 481.8 | 620.1 | 1657.9 |
| search,palier:transition | 426 | 415.8 | 351.3 | 605.1 | 745.4 | 1518.5 |
| send | 15645 | 643.1 | 509.3 | 914.7 | 944.4 | 1405.6 |
| send,palier:1400 | 4716 | 637.9 | 501.7 | 901.4 | 921.8 | 1033.4 |
| send,palier:1996 | 8570 | 625.9 | 486.9 | 916.2 | 946.0 | 1258.6 |
| send,palier:transition | 437 | 609.6 | 492.5 | 915.1 | 950.1 | 1278.1 |
| treatment | 13813 | 94.8 | 83.3 | 128.6 | 172.7 | 4988.9 |
| treatment,palier:1400 | 3951 | 71.4 | 78.0 | 93.5 | 101.1 | 176.2 |
| treatment,palier:1996 | 7192 | 99.9 | 88.9 | 133.0 | 159.4 | 4988.9 |
| treatment,palier:transition | 364 | 125.9 | 85.1 | 279.6 | 326.9 | 1206.5 |
| warmup | 21956 | 544.6 | 247.6 | 584.3 | 2671.8 | 11154.6 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-10T12:26:08.230000+00:00 → 2026-11-10T13:03:48.185000+00:00 (2260 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t439-controle.csv`) | ✅ 80325 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-22304` | 1.02 | 11 | 24 | 0.029 | 4.56 |
| `DESKTOP-DEV-X2C-44308` | 0.94 | 9 | 26 | 0.028 | 4.58 |
| `DESKTOP-DEV-X2C-60072` | 1.01 | 14 | 31 | 0.036 | 4.78 |
| `DESKTOP-DEV-X2C-61720` | 0.99 | 10 | 24 | 0.028 | 4.76 |
| `DESKTOP-DEV-X2C-61800` | 0.93 | 20 | 24 | 0.034 | 4.84 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#34920` | 0.00 | 0.13 | 44 |
| `com.docker.backend#35896` | 1.12 | 3.52 | 1840 |
| `dcp#18072` | 0.00 | 0.09 | 13 |
| `dcp#18296` | 0.00 | 0.00 | 12 |
| `dcp#18808` | 0.72 | 2.46 | 3220 |
| `dcp#25612` | 0.00 | 0.04 | 13 |
| `dcp#25924` | 0.00 | 0.04 | 13 |
| `dcp#34684` | 0.00 | 0.09 | 52 |
| `dcp#35064` | 0.00 | 0.04 | 13 |
| `dcp#45788` | 0.00 | 0.00 | 12 |
| `dcp#52160` | 0.00 | 0.00 | 12 |
| `dcp#54692` | 0.00 | 0.00 | 11 |
| `dcp#54828` | 0.00 | 0.00 | 12 |
| `dcp#55228` | 0.00 | 0.00 | 12 |
| `dcp#56084` | 0.00 | 0.00 | 12 |
| `dcp#61344` | 0.00 | 0.04 | 12 |
| `dcp#64224` | 0.00 | 0.00 | 12 |
| `k6#328459` | 0.86 | 1.83 | 2909 |
| `mss.mail.api#22304` | 0.65 | 2.63 | 2310 |
| `mss.mail.api#44308` | 0.61 | 2.46 | 2150 |
| `mss.mail.api#60072` | 0.63 | 2.77 | 2222 |
| `mss.mail.api#61720` | 0.62 | 2.34 | 2216 |
| `mss.mail.api#61800` | 0.64 | 2.69 | 2237 |
| `mss.mail.e2e#47832` | 0.01 | 0.27 | 32 |
| `vmmemWSL#35316` | 4.98 | 11.21 | 58594 |
| `loadtest-otel-collector-zecckkhe` | 0.02 | 0.16 | 102 |
| `loadtest-pgbouncer-vcvdbajn` | 0.41 | 0.78 | 48 |
| `mss-mail-flagsmith-app-b6152948` | 0.11 | 0.43 | 555 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.12 | 167 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.11 | 123 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.21 | 200 |
| `mss-mail-rabbitmq-mdepcnpe` | 0.01 | 0.05 | 154 |
| `mss-mail-redis-b6152948` | 0.27 | 1.39 | 957 |
| `mss-mail-rediscommander-bsvvnayz` | 0.00 | 0.19 | 26 |
| `mss-mail-seq-b6152948` | 0.09 | 0.45 | 1275 |
| `postgres-pgvector` | 1.94 | 7.26 | 26051 |

- **Hôte** : CPU 59.9 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 68
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9410, cl_waiting max 7, cl_waiting_doctor_path max 7, cl_waiting_maintenance max 0, cl_waiting_practitioner max 7, cl_waiting_registry max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 0, maxwait_ms max 25, maxwait_practitioner_ms max 25, maxwait_registry_ms max 0, sv_active max 40, sv_idle max 1602, sv_login max 1, wait_us_delta_maintenance max 0, wait_us_delta_practitioner max 38543146, wait_us_delta_registry max 0, xact_delta_maintenance max 2, xact_delta_practitioner max 38183, xact_delta_registry max 0, xact_us_delta_maintenance max 0, xact_us_delta_practitioner max 243062339, xact_us_delta_registry max 0
- **Backends Postgres** : audit max 5, cache_mb max 37655, direct max 30, idle_over_60s max 233, majfault_per_s max 0, pooler max 1996, practitioner_databases max 1986, provision max 5, rss_mb max 6173, seconds max 0, started_last_60s max 367, total max 2027, usage_pct max 97

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 6787.1 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2470.0 | 452 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 538.4 | 445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 700.6 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 736.5 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 521.9 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 414.4 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 633.5 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2104.9 | 434 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 210.2 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 310.9 | 443 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 211.6 | 443 |
| `api/v{version:apiVersion}/Search/semantic` | 1276.9 | 444 |
| `api/v{version:apiVersion}/Sync/coverage` | 238.9 | 447 |

- **p95 client global (k6)** : 482.4 ms
- **p95 serveur le plus élevé** : 6787.1 ms
- **Écart** : -6304.7 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.62 |
| Documents CDA /s | 0.62 |
| Durée traitement CDA (s, p95) | 2.35 |
| Événements de session IMAP /s | 4.36 |
| Recherches (s, p95) | 1.277 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 54.2 | 459 | 0.0 (0.1 %), p95 5 | 28.9 (53.3 %), p95 145 | 25.3 (46.6 %), p95 459 |
| `GetMail` | 11.1 | 38.9 | 397 | 3.6 (9.2 %), p95 58 | 31.9 (82.2 %), p95 349 | 3.3 (8.6 %), p95 87 |
| `GetMailsByUids` | 14.7 | 55.4 | 457 | 0.1 (0.2 %), p95 5 | 45.5 (82.2 %), p95 448 | 9.8 (17.7 %), p95 50 |

- **`EnrichPersistMail`** — sur 54.2 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 28.9 ms exécution SQL, 25.3 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 38.9 ms en moyenne (11.1 requête(s) SQL par appel) : 3.6 ms attente d'une connexion, 31.9 ms exécution SQL, 3.3 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 55.4 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 45.5 ms exécution SQL, 9.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est l'attente du **pool Npgsql** seul ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **L'attente PgBouncer n'est pas dans `attente d'une connexion`** (task-435). En mode transaction, le pooler attribue un serveur à la première requête de chaque transaction : son attente est comptée dans `exécution SQL`. Son coût se lit dans « Coûts résidents » (« Attente PgBouncer cumulée — chemin du médecin »).

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.8 | 3.3 | 311.3 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.1 | 9.8 | 47.2 | 18.7 | 28.6 | 18.7 | 30.4 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.8 | 4.0 |

- **`GetMail`** — sur 3.3 ms de matérialisation, l'appel a construit 10.8 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **311.3 µs**.

- **`GetMailsByUids`** — sur 9.8 ms de matérialisation, l'appel a construit 207.1 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.4 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.8 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **47.2 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4683.3 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 386.0 | 4588 | 130.2 (33.7 %), p95 243 | 19.6 (5.1 %), p95 959 | 153.8 (39.9 %), p95 2425 | 39.1 (10.1 %), p95 209 | 43.3 (11.2 %), p95 709 |

- **Enrichir un message** — sur 386.0 ms en moyenne (3.8 message(s) par requête) : 130.2 ms fetch IMAP, 19.6 ms extraction XDM, 153.8 ms parsing CDA, 39.1 ms écritures base, 43.3 ms le reste (DTO, notifications). **Poste dominant : parsing CDA.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `fetch_whole_message`, 0.46 `fetch_bodystructure`, 0.46 `open_folder`, 0.46 `resolve_folder`, 0.45 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 265.5 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 635.6 | 976 | 0.0 (0.0 %), p95 5 | 16.3 (2.6 %), p95 51 | 222.7 (35.0 %), p95 477 | 396.5 (62.4 %), p95 488 | 422.0 (66.4 %), p95 979 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 635.6 ms en moyenne : 0.0 ms garde d'opposition, 16.3 ms construction MIME, 222.7 ms obtention de session SMTP, 396.5 ms transmission + acquittement, 422.0 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.443 | 2.405 | 95.22 |
| `smtp_session` | 0.005 | 0.988 | 9.82 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.474 | 2.365 | 0.488 | 9.84 |
| `EnrichEmails` | 0.005 | 0.459 | — | 0.459 | 0.93 |
| `GetAttachmentStream` | 0.484 | 2.425 | 2.425 | 0.488 | 0.87 |
| `GetEmailContent` | 0.005 | 0.492 | — | 0.492 | 13.38 |
| `GetFolders` | 0.005 | 0.983 | 0.988 | 0.242 | 7.78 |
| `ReadFolder` | 0.754 | 2.405 | 2.407 | 0.487 | 35.26 |
| `ReadToday` | 0.005 | 0.499 | — | 0.499 | 7.76 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.46 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.248** | 0.425 | 0.450 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `GetEmailContent` | **0.489** | 0.489 | 0.491 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.428** | 0.440 | 0.447 | 0.0 % |
| `ReadToday` | **0.488** | 0.490 | 0.491 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 95.22 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.754 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 7.00 clients | 0 clients | 100.0 % | 25.3 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 7.26 cœurs | 24 cœurs | 30.2 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-61800` | 20.00 éléments | 100 éléments | 20.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#60072` (CPU) | 2.77 cœurs | 24 cœurs | 11.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#61800` (CPU) | 2.69 cœurs | 24 cœurs | 11.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#22304` (CPU) | 2.63 cœurs | 24 cœurs | 11.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#44308` (CPU) | 2.46 cœurs | 24 cœurs | 10.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#61720` (CPU) | 2.34 cœurs | 24 cœurs | 9.8 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 25.3 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 216 757

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 2 122 |
| OpenAI | gpt-4o-mini | prompt | 214 635 |
| OpenAI | text-embedding-3-small | embedding | 402 107 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 113 | 0 (0.0 %) | 0 | 3.0 | 1.28 | 1.13 | 3.23 |
| étiquetage (chat) | OpenAI | 113 | 0 (0.0 %) | 0 | 3.0 | 1.22 | 1.00 | 2.98 |
| embedding | OpenAI | 114 | 0 (0.0 %) | 0 | 3.0 | 0.59 | 0.46 | 1.72 |

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
| GPU — utilisation (%) | 0.8 | 31.0 |
| GPU — VRAM occupée (Mo) | 1 491 | 1 636 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 619.8** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.21** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **3.7 ms** | sur 765 996 requêtes HTTP k6 |
| Taux de cache (blocs) | **97.78 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **8.86 Mo/s (1 134 blocs/s)** | attente disque : 19.0 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **279 186 / 29 467** | rapport 9.5 |
| Écritures de lignes / s (ins+upd+del) | **154.2** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.26 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 13 % |
| Sessions ouvertes / s | **3.19** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **30.4 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 568 / 2 027** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **9 / 15 / 27 ms** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **76 / 97 %** | fautes majeures/s max : 0.0 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 123.8 s | 170690 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, HtmlBody : 18.6 Go lus, 3.5 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 12.2 % du temps SQL, 39.6 % des lectures disque du tir | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 47.2 s | 8592 | `pages-par-ligne` | 31.2 pages par ligne rendue, 625 par appel, 41.0 Go lus | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 31.7 s | 15123 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Content : 2.8 Go lus, 1.7 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 3.1 % du temps SQL, 19.6 % des lectures disque du tir | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 31.1 s | 8682 | `pages-par-ligne` | 31.5 pages par ligne rendue, 630 par appel, 41.7 Go lus | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 26.3 s | 170694 | `colonne-volumineuse` | sélectionne Body, BodyHtml : 6.0 Go lus, 0.1 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **88 évictions `pg_stat_statements`** pendant le tir (95 847 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

135 formes de requête, 6 061 595 appels, **16.9 min** de temps serveur cumulé — soit **1.3 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **14.9 %** | 15 % | 8 581 | 0.01 | 17.62 | 51.4 | 341 | 1 % | 0 | 815 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **13.9 %** | 29 % | 8 628 | 0.01 | 16.31 | 51.5 | 395 | 1 % | 0 | 819 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **12.2 %** | 41 % | 170 690 | 0.22 | 0.72 | 1.0 | 14 | 19 % | 0 | 1 871 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 4 | **6.5 %** | 48 % | 88 839 | 0.12 | 0.75 | 18.0 | 100 | 1 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **6.0 %** | 54 % | 765 901 | 1.00 | 0.08 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `PostgresTenantRegistryClient.GetMailboxAsync` ← `GET /api/v1/Mail/folders/{foldername}` | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 6 | **4.7 %** | 58 % | 8 592 | 0.01 | 5.49 | 20.0 | 625 | 2 % | 0 | 816 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 7 | **3.3 %** | 62 % | 139 713 | 0.18 | 0.24 | 1.0 | 15 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 8 | **3.1 %** | 65 % | 15 123 | 0.02 | 2.10 | 1.0 | 25 | 61 % | 0 | 1 180 | **Code** — 61 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 9 | **3.1 %** | 68 % | 8 682 | 0.01 | 3.59 | 20.0 | 630 | 2 % | 0 | 825 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 10 | **3.0 %** | 71 % | 6 103 | 0.01 | 5.05 | 178.0 | 540 | 1 % | 0 | 1 051 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 11 | **2.6 %** | 73 % | 170 694 | 0.22 | 0.15 | 1.0 | 5 | 2 % | 0 | 1 871 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |
| 12 | **2.0 %** | 75 % | 285 302 | 0.37 | 0.07 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `MailRepository.ResolveActiveDuplicateRefsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 13 | **2.0 %** | 77 % | 95 890 | 0.13 | 0.21 | 18.0 | 5 | 0 % | 0 | 1 886 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | site inconnu ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}`<br>`MailRepository.LoadMailsReferencingAnyRootAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 14 | **1.3 %** | 79 % | 285 298 | 0.37 | 0.05 | 2.0 | 4 | 0 % | 0 | 1 996 | — | `MailRepository.EnrichManyWithBiologyAcksAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 15 | **1.3 %** | 80 % | 88 844 | 0.12 | 0.15 | 18.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.GetMailsByUidsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 16 | **1.2 %** | 81 % | 45 061 | 0.06 | 0.28 | 27.0 | 5 | 0 % | 0 | 1 401 | — | `MailRepository.GetLatestMessageIdsPerThreadAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **1.0 %** | 82 % | 88 849 | 0.12 | 0.12 | 29.3 | 5 | 2 % | 0 | 1 996 | — | `MailRepository.LoadBulkMailLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."DocumentId", m."Guid", m."FileName", m."ContentType", m."Size" FROM "MailAttachments" AS …` |
| 18 | **1.0 %** | 83 % | 191 430 | 0.25 | 0.05 | 1.5 | 6 | 0 % | 0 | 1 888 | — | `MailRepository.GetMailAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`, `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |
| 19 | **1.0 %** | 84 % | 144 052 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **1.0 %** | 85 % | 144 053 | 0.19 | 0.07 | 14.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.6 % | 87.6 % |
| INSERT | 4.4 % | 2.9 % |
| UPDATE | 0.4 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.5 % | 7.6 % |
| bases : praticien (N bases) | 90.1 % | 82.1 % |
| bases : unique (1 base) | 9.9 % | 17.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **17.6** | 70 | 8 581 | 14.9 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **16.3** | 114 | 8 628 | 13.9 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **5.5** | 279 | 8 592 | 4.7 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **5.1** | 71 | 6 103 | 3.0 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **3.6** | 79 | 8 682 | 3.1 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 309 | 155 771 | 0 | 0 | 0.1 Mo |
| `Mails` | 714 | 92 466 | 663 | 0 | 0.1 Mo |
| `MailTags` | 201 | 49 848 | 70 | 0 | 0.1 Mo |
| `MailRecipients` | 183 | 28 548 | 56 | 0 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 108 | 28 188 | 187 | 0 | 30.0 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 167 | 25 155 | 1 266 | 0 | 8.0 Mo |
| `MailContents` ⚠️ index candidat | 52 | 8 112 | 2 158 | 0 | 1.9 Mo |
| `PendingActions` | 168 | 4 969 | 0 | 31 | 0.1 Mo |
| `Tags` | 130 | 2 340 | 106 | 0 | 0.0 Mo |
| `MailFolders` | 368 | 986 | 337 | 0 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (6.0 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 97.8 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | `MailAttachments` balayée 108 fois (28188 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 167 fois (25155 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 52 fois (8112 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°8 (3.1 % du temps SQL) — 61 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°10 (3.0 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°6 (4.7 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°13 (2.0 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-140429.tsv`, `pgserver-journey-debut-132558.tsv`, `pgserver-journey-fin-140437.tsv`, `pgtables-journey-debut-132602.tsv`, `pgtables-journey-fin-140442.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 248516 — dont **248516** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261110-t439-controle-140348.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
