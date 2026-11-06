# Rapport de tir — journey-escalier-1996-20261104-ia-simulee

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-escalier-1996-20261104-ia-simulee-013324.json`.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- 18.10 % des demandes ont échoué (au-delà du plafond de 1 %)
- le stock de messages de test s'est épuisé pendant le tir : le corpus a changé de forme en cours de mesure, les chiffres ne se comparent plus
- le multiplexeur PostgreSQL a **refusé** des connexions (1382 refus `server_login_retry` sur la fenêtre) au lieu de les faire attendre : les demandes touchées ont reçu une erreur, et les latences des autres sont des bornes optimistes — refus PgBouncer présents (1382) mais coût du login **non relevé** : corrélation impossible — armer la sonde `postgres/login/seconds` (task-295) avant de conclure

À instruire une fois le tir refait :
- à 200 médecins, 4 étape(s) dépassent le temps de réponse attendu : « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) », « Ouvrir la page d'un dossier patient »
- une étape ne mesure pas ce que son nom annonce — son chiffre décrit un autre geste
- 7 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 200 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 3 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné

## Analyse — itération 1 de la campagne « limites » (escalier journey, IA simulée, 2026-11-05)

**La limite est trouvée : entre 1000 et 1400 médecins actifs en continu, et c'est un mur, pas une pente.** Le rouge global ci-dessus est l'effet de ce mur sur les deux derniers paliers ; les quatre premiers sont propres.

| Palier | Débit (req/s) | Erreurs | Backends Postgres (max) | Dashboard p95 | Fiche patient p95 |
|---|---|---|---|---|---|
| 200 | 41 | 0 % | 437 | 507 ms | 343 ms |
| 400 | 82 | 0 % | 816 | 507 ms | 364 ms |
| 700 | 144 | 0 % | 1 399 | 523 ms | 417 ms |
| 1000 | 209 | 0 % | 1 955 | 525 ms | 531 ms |
| 1400 | 254 | **24,8 %** | **2 506** | 2 165 ms | 757 ms |
| 1996 | 351 | **40,5 %** | **2 506** | 2 461 ms | 2 949 ms |

**Cause établie (Seq, 2026-11-04T23:57Z, début du palier 1400)** : `53300 sorry, too many clients already` — PostgreSQL atteint `max_connections` = 2500 — puis PgBouncer met l'échec en cache (`08P01 … server_login_retry`, 1 382 refus). Les backends venant du pooler suivent le **nombre de médecins actifs**, pas le débit : **~1,9 backend par médecin** à chaque palier (407/200, 786/400, 1 368/700, 1 924/1000). Le plafond se calcule donc d'avance : (2500 − 25 directs) ÷ 1,9 ≈ **1 300 médecins actifs**. C'est le plafond annoncé par task-296/298 (`max_connections`), désormais mesuré.

- **Ce n'est pas le CPU** : ≤ 1,6 cœur par réplica au pire, file ThreadPool ≤ 27. Ni l'IA (simulée, 0,01 cœur), ni IMAP.
- **Avant le mur, la dégradation est douce** : de 200 à 1000 médecins (×5 de débit), le p95 du dashboard passe de 507 à 525 ms, la fiche patient de 343 à 531 ms. Toutes les étapes mesurées restent dans la grille jusqu'à 1000.
- **Verdicts « ❌ » des paliers 200 à 1000 : non probants, pas des échecs de latence.** Ils viennent (1) de la chauffe agrégée sur tout le tir (88,3 % < 90 %, les lots perdus sont ceux des cohortes 1400/1996 pendant l'effondrement), (2) de l'étape 3 servie à 91 % par la base (l'itération 0 a consommé des messages en tête de réserve), (3) de paliers de 18 min < 30 min exigés. Verdict **indicatif**.
- **Équivalence terrain** : ~10,4 inscrits par actif (itération 0 : 1996 inscrits → 190 actifs) — le mur à ~1 300 actifs correspond à **~13 500 inscrits** sur ce banc, à configuration Postgres inchangée.

### Findings

- **F1 — plafond `max_connections` (cause du mur).** ~1,9 backend par médecin actif : le coût suit la population de bases, pas le trafic. Leviers à instruire, mesurés avant/après : réduire les connexions serveur retenues par base dans PgBouncer (taille de pool par base, `server_idle_timeout`), ou relever `max_connections` — mais le cgroup Postgres est déjà à 100 % de sa mémoire sur tout le tir.
- **F2 — panne de base rendue en 500 au lieu de 503 (règle 12).** `GET /mail/folders` : `ImapService.GetFoldersAsync` attrape l'exception Npgsql (« Unexpected error getting folders ») et rend un 500 générique (4 323 réponses 500), au lieu de la laisser au `GlobalExceptionHandler` qui la classe `DATABASE_UNAVAILABLE` → 503 sur les autres routes.
- **F3 — registre indisponible rendu en 403 `MAILBOX_NOT_ATTACHED` (probable).** Au même instant, `TenantRegistrySynchronizer` journalise « Synchronisation ignorée — registre indisponible » (`53300` en connexion directe) et les réponses suivantes sont des 403 (915) : une panne d'infrastructure présentée au médecin comme un défaut de rattachement. Chaîne causale à confirmer trace par trace.
- **F4 — chauffe jugée sur tout le tir.** Le plancher de 90 % est calculé tous paliers confondus : l'effondrement du palier 1400 rend non opposables les étapes 2, 3, 10, 11 des paliers 200 à 1000, où la chauffe avait réussi. Correctif harnais : juger la chauffe par cohorte de palier.

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 6660s — **Latence** : mssante
- **Requêtes** : 1220355 — **débit émergent global** : 182.2 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 88145 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 182.2 | **568.6** | 82.1 | **2144.6** | — | 70228.9 | 18.10 | 81.4 | 0 | 0 | 229418/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **200 médecins** | 1080 | 1031 | 42366 | 41.09 | 0.00 | 177.4 |
| **400 médecins** | 1080 | 1031 | 84187 | 81.66 | 0.00 | 320.9 |
| **700 médecins** | 1080 | 982 | 141278 | 143.87 | 0.00 | 524.1 |
| **1000 médecins** | 1080 | 982 | 205102 | 208.86 | 0.00 | 749.0 |
| **1400 médecins** | 1080 | 982 | 249347 | 253.92 | 24.82 | 427.9 |
| **1996 médecins** | 1080 | 933 | 327424 | 350.94 | 40.45 | 193.7 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 200 médecins | 400 médecins | 700 médecins | 1000 médecins | 1400 médecins | 1996 médecins |
|---|---|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 59 / 507 (n=12588) | 60 / 507 (n=25260) | 63 / 523 (n=42036) | 67 / 525 (n=60664) | 427 / 2165 (n=73920) | 2104 / 2461 (n=97832) |
| 2 | Ouvrir / rafraîchir l'inbox | 34 / 61 (n=6282) | 36 / 68 (n=12616) | 40 / 85 (n=21032) | 47 / 112 (n=30314) | 87 / 2072 (n=36750) | 1315 / 2176 (n=48890) |
| 3 | Ouvrir un message enrichi (servi base) | 30 / 42 (n=3139) | 32 / 47 (n=6316) | 36 / 60 (n=10506) | 43 / 82 (n=15174) | 55 / 2104 (n=18372) | 118 / 2160 (n=24396) |
| 4 | Ouvrir un message froid (fetch IMAP) | 449 / 510 (n=1310) | 449 / 509 (n=2550) | 451 / 514 (n=4193) | 458 / 525 (n=6075) | 2057 / 2124 (n=7433) | 2114 / 2244 (n=9692) |
| 5 | Recherche | 335 / 596 (n=940) | 343 / 606 (n=1862) | 358 / 651 (n=3107) | 379 / 643 (n=4482) | 403 / 753 (n=5388) | 475 / 921 (n=7299) |
| 6 | Envoi (acquittement UI) | 791 / 913 (n=940) | 480 / 914 (n=1896) | 479 / 921 (n=3200) | 487 / 931 (n=4521) | 2061 / 22548 (n=5488) | 2122 / 2293 (n=7219) |
| 7 | Télécharger une PJ (~124 Ko) | 373 / 778 (n=1313) | 393 / 942 (n=2588) | 404 / 969 (n=4175) | 426 / 991 (n=5922) | 2051 / 4148 (n=7469) | 2137 / 4220 (n=9818) |
| 8 | Marquer lu | 30 / 75 (n=2515) | 32 / 77 (n=5013) | 37 / 84 (n=8380) | 46 / 99 (n=12097) | 54 / 123 (n=14803) | 100 / 250 (n=19481) |
| 9 | Rechercher un patient | 56 / 63 (n=965) | 58 / 64 (n=1869) | 59 / 70 (n=3181) | 61 / 81 (n=4603) | 63 / 92 (n=5638) | 76 / 163 (n=7241) |
| 10 | Ouvrir la page d'un dossier patient | 57 / 65 (n=1423) | 59 / 69 (n=2764) | 60 / 80 (n=4812) | 63 / 103 (n=6899) | 66 / 160 (n=8378) | 117 / 292 (n=10911) |
| 11 | Fiche patient complète (ressenti médecin) | 249 / 343 (n=712) | 258 / 364 (n=1382) | 281 / 417 (n=2406) | 329 / 531 (n=3450) | 380 / 757 (n=4189) | 710 / 2949 (n=5456) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **200 médecins** | 14.3 / 20 | 33.4 / 60 | 1604 | 343 |
| **400 médecins** | 14.4 / 20 | 34.3 / 60 | 3116 | 364 |
| **700 médecins** | 14.1 / 20 | 33.4 / 60 | 5270 | 417 |
| **1000 médecins** | 14.7 / 20 | 34.7 / 60 | 7640 | 531 |
| **1400 médecins** | 14.6 / 20 | 34.5 / 60 | 9182 | 757 |
| **1996 médecins** | 14.4 / 20 | 34.0 / 60 | 12158 | 2949 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3415 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- ⚠️ **Réserve épuisée en cours de tir** (2 fois) — le corpus a changé de forme pendant la mesure : soit le traitement n'a plus alimenté le dossier, soit « ouvrir un message froid » a relu du déjà-ouvert. Tir à refaire sur une boîte plus grande ou une campagne plus courte.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 558 ms en moyenne, 9713 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 200 médecins | 400 médecins | 700 médecins | 1000 médecins | 1400 médecins | 1996 médecins |
|---|---|---|---|---|---|---|
| Sessions IMAP (moy/max) | 1053 / 2211 (magasin) | 1053 / 2211 (magasin) | 1053 / 2211 (magasin) | 1053 / 2211 (magasin) | 1053 / 2211 (magasin) | 1053 / 2211 (magasin) |
| Backends Postgres (moy/max) | 404 / 437 | 777 / 816 | 1337 / 1399 | 1908 / 1955 | 2209 / 2506 | 2490 / 2506 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 1 | 0 / 1 | 0 / 1 | 0 / 5 | 0 / 2 |
| PgBouncer `cl_waiting` (échant. non nuls) | 6/211 (3 %) | 2/209 (1 %) | 4/203 (2 %) | 10/190 (5 %) | 23/178 (13 %) | 33/152 (22 %) |
| …dont bases **praticien** (échant. non nuls) | 0/211 (0 %) | 0/209 (0 %) | 0/203 (0 %) | 0/190 (0 %) | 0/178 (0 %) | 0/152 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 6/211 (3 %) | 2/209 (1 %) | 4/203 (2 %) | 10/190 (5 %) | 23/178 (13 %) | 33/152 (22 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 6.0 | 0.5 | 6.5 | 2.8 | 28.3 | 13.9 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 6.0 | 0.5 | 6.5 | 2.8 | 28.3 | 13.9 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 | 0 | 0 | 701 🔴 refus | 671 🔴 refus |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé | non relevé | non relevé | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 59 / 429 | 93 / 474 | 147 / 503 | 187 / 549 | 258 / 587 | 302 / 638 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 45 | 95 | 197 | 53 | 319 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 407 | 786 | 1368 | 1924 | 2477 | 2475 |
| Backends **directs** — audit + provisionnement (max) | 24 | 25 | 25 | 25 | 25 | 25 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 | 5 | 5 | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 0 | 0 | 0 | 0 | 0 | 0 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 34 | 1 / 14 | 0 / 25 | 0 / 13 | 2 / 24 | 2 / 19 |
| RSS par réplica api-mail, Mo (moy/max) | 1535 / 1690 (5 réplicas) | 1625 / 1746 (5 réplicas) | 1948 / 2250 (5 réplicas) | 2270 / 2519 (5 réplicas) | 2473 / 2799 (5 réplicas) | 2511 / 2709 (5 réplicas) |

- à 200 médecins : Backends Postgres au pic : **437.0 / 2500** (17.5 % de `max_connections`)
- à 400 médecins : Backends Postgres au pic : **816.0 / 2500** (32.6 % de `max_connections`)
- à 700 médecins : Backends Postgres au pic : **1399.0 / 2500** (56.0 % de `max_connections`)
- à 1000 médecins : Backends Postgres au pic : **1955.0 / 2500** (78.2 % de `max_connections`)
- à 1400 médecins : Backends Postgres au pic : **2506.0 / 2500** (100.2 % de `max_connections`)
- à 1400 médecins : 🔴 **Postgres à `max_connections`** — le tir mesure le plafond, pas le produit : le trafic délesté flatte les latences servies, aucun verdict SLO n'est opposable.
- à 1400 médecins : refus PgBouncer présents (701) mais coût du login **non relevé** : corrélation impossible — armer la sonde `postgres/login/seconds` (task-295) avant de conclure
- à 1996 médecins : Backends Postgres au pic : **2506.0 / 2500** (100.2 % de `max_connections`)
- à 1996 médecins : 🔴 **Postgres à `max_connections`** — le tir mesure le plafond, pas le produit : le trafic délesté flatte les latences servies, aucun verdict SLO n'est opposable.
- à 1996 médecins : refus PgBouncer présents (671) mais coût du login **non relevé** : corrélation impossible — armer la sonde `postgres/login/seconds` (task-295) avant de conclure

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

⛔ **Chauffe insuffisante — les étapes 2, 3, 10, 11 ne sont pas opposables.** **88.3 %** des médecins ont terminé leur chauffe (plancher **90 %**, sur 1996 médecins) ; 1228 lot(s) d'analyse perdu(s) ; 91.0 % des ouvertures de l'étape 3 servies par la base (plancher 95 %). Ces étapes sont **servies par la base des messages analysés** : une base peu peuplée les rend rapides sans rien dire de la charge visée — au tir `journey-remote-n500` du 2026-08-09, `GetMailsByUids` coûtait **55,4 ms / 7,8 requêtes** par appel contre **1 199,7 ms / 14,8** sur un tir dont la base était peuplée. **Ce tir ne mesure donc pas la capacité** : ses latences sont flattées, quelle que soit leur valeur. Relancer après une chauffe aboutie (lots `JOURNEY_WARMUP_BATCH`, task-244).

ⓘ **Ventilation par palier non disponible pour ce tir** (harnais antérieur à task-424) : la chauffe et la part servie par la base sont jugées sur tout le tir, et ce verdict global s'applique à chaque palier. Palier par palier, **on ne sait pas** lequel a échoué.

> ⓘ Chauffe : **112 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **10 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 200 : chauffe [+30 s..+79 s] (5 % de la fenêtre) ; **régime [+79 s..+1110 s]** porte le verdict
>   palier 400 : chauffe [+1140 s..+1189 s] (5 % de la fenêtre) ; **régime [+1189 s..+2220 s]** porte le verdict
>   palier 700 : chauffe [+2250 s..+2348 s] (9 % de la fenêtre) ; **régime [+2348 s..+3330 s]** porte le verdict
>   palier 1000 : chauffe [+3360 s..+3458 s] (9 % de la fenêtre) ; **régime [+3458 s..+4440 s]** porte le verdict
>   palier 1400 : chauffe [+4470 s..+4568 s] (9 % de la fenêtre) ; **régime [+4568 s..+5550 s]** porte le verdict
>   palier 1996 : chauffe [+5580 s..+5727 s] (14 % de la fenêtre) ; **régime [+5727 s..+6660 s]** porte le verdict

⛔ **Étape 3 « servi base » refusée — elle ne mesure pas ce que son nom annonce.** Seules **91.0 %** de ses ouvertures portent les documents de l'analyse, pour un plancher de 95 % : le reste a basculé sur le serveur de messagerie, donc cette étape mesure en partie des ouvertures **froides** et son chiffre n'est **pas** un verdict, quelle que soit sa valeur (pour situer : 46.42 sollicitations/s du serveur de messagerie sur la fenêtre, étapes 3/4 et rafale dossier confondues). Causes connues : bande chaude non analysée par la chauffe (task-224, défaut 5 — les 440 ms du 2026-08-03), ou mails de chauffe estampillés **génération 0** (UIDVALIDITY) donc inatteignables en base (certification du 2026-08-06 — la chauffe doit lister les dossiers AVANT d'analyser).

### 200 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 59 (300) | 507 (1500) | 12588 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 34 (300) | 61 (1000) | 6282 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 30 (100) | 42 (500) | 3139 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 449 (800) | 510 (2500) | 1310 | ✅ |
| 5 | Recherche | 335 (500) | 596 (2000) | 940 | ✅ |
| 6 | Envoi (acquittement UI) | 791 (1000) | 913 (3000) | 940 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 373 (500) | 778 (2000) | 1313 | ✅ |
| 8 | Marquer lu | 30 (200) | 75 (1000) | 2515 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 63 (1500) | 965 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 57 (500) | 65 (2000) | 1423 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 249 (1500) | 343 (4000) | 712 | ⛔ non opposable — chauffe insuffisante |

### 400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 60 (300) | 507 (1500) | 25260 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 36 (300) | 68 (1000) | 12616 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 32 (100) | 47 (500) | 6316 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 449 (800) | 509 (2500) | 2550 | ✅ |
| 5 | Recherche | 343 (500) | 606 (2000) | 1862 | ✅ |
| 6 | Envoi (acquittement UI) | 480 (1000) | 914 (3000) | 1896 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 393 (500) | 942 (2000) | 2588 | ✅ |
| 8 | Marquer lu | 32 (200) | 77 (1000) | 5013 | ✅ |
| 9 | Rechercher un patient | 58 (300) | 64 (1500) | 1869 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 69 (2000) | 2764 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 258 (1500) | 364 (4000) | 1382 | ⛔ non opposable — chauffe insuffisante |

### 700 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 63 (300) | 523 (1500) | 42036 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 40 (300) | 85 (1000) | 21032 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 36 (100) | 60 (500) | 10506 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 451 (800) | 514 (2500) | 4193 | ✅ |
| 5 | Recherche | 358 (500) | 651 (2000) | 3107 | ✅ |
| 6 | Envoi (acquittement UI) | 479 (1000) | 921 (3000) | 3200 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 404 (500) | 969 (2000) | 4175 | ✅ |
| 8 | Marquer lu | 37 (200) | 84 (1000) | 8380 | ✅ |
| 9 | Rechercher un patient | 59 (300) | 70 (1500) | 3181 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 60 (500) | 80 (2000) | 4812 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 281 (1500) | 417 (4000) | 2406 | ⛔ non opposable — chauffe insuffisante |

### 1000 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 67 (300) | 525 (1500) | 60664 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 47 (300) | 112 (1000) | 30314 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 43 (100) | 82 (500) | 15174 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 458 (800) | 525 (2500) | 6075 | ✅ |
| 5 | Recherche | 379 (500) | 643 (2000) | 4482 | ✅ |
| 6 | Envoi (acquittement UI) | 487 (1000) | 931 (3000) | 4521 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 426 (500) | 991 (2000) | 5922 | ✅ |
| 8 | Marquer lu | 46 (200) | 99 (1000) | 12097 | ✅ |
| 9 | Rechercher un patient | 61 (300) | 81 (1500) | 4603 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 63 (500) | 103 (2000) | 6899 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 329 (1500) | 531 (4000) | 3450 | ⛔ non opposable — chauffe insuffisante |

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 427 (300) | 2165 (1500) | 73920 | ❌ |
| 2 | Ouvrir / rafraîchir l'inbox | 87 (300) | 2072 (1000) | 36750 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 55 (100) | 2104 (500) | 18372 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 2057 (800) | 2124 (2500) | 7433 | ❌ |
| 5 | Recherche | 403 (500) | 753 (2000) | 5388 | ✅ |
| 6 | Envoi (acquittement UI) | 2061 (1000) | 22548 (3000) | 5488 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 2051 (500) | 4148 (2000) | 7469 | ❌ |
| 8 | Marquer lu | 54 (200) | 123 (1000) | 14803 | ✅ |
| 9 | Rechercher un patient | 63 (300) | 92 (1500) | 5638 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 66 (500) | 160 (2000) | 8378 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 380 (1500) | 757 (4000) | 4189 | ⛔ non opposable — chauffe insuffisante |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 2104 (300) | 2461 (1500) | 97832 | ❌ |
| 2 | Ouvrir / rafraîchir l'inbox | 1315 (300) | 2176 (1000) | 48890 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 118 (100) | 2160 (500) | 24396 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 2114 (800) | 2244 (2500) | 9692 | ❌ |
| 5 | Recherche | 475 (500) | 921 (2000) | 7299 | ✅ |
| 6 | Envoi (acquittement UI) | 2122 (1000) | 2293 (3000) | 7219 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 2137 (500) | 4220 (2000) | 9818 | ❌ |
| 8 | Marquer lu | 100 (200) | 250 (1000) | 19481 | ✅ |
| 9 | Rechercher un patient | 76 (300) | 163 (1500) | 7241 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 117 (500) | 292 (2000) | 10911 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 710 (1500) | 2949 (4000) | 5456 | ⛔ non opposable — chauffe insuffisante |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Arrivée dashboard (`dashboard`) | 97832 | 1713 | 2461 | 167591.7 | 53.4 % |
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 48890 | 1140 | 2176 | 55738.1 | 17.8 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 9818 | 2539 | 4220 | 24932.8 | 7.9 % |
| 🔴 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 9692 | 2126 | 2244 | 20608.6 | 6.6 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 7219 | 2093 | 2293 | 15110.0 | 4.8 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 24396 | 487 | 2160 | 11885.3 | 3.8 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 6079 | 1601 | 2228 | 9735.1 | 3.1 % |
| 🟢 | Recherche (`search`) | 7299 | 530 | 921 | 3868.4 | 1.2 % |
| 🟢 | Marquer lu (`mark_read`) | 19481 | 119 | 250 | 2323.4 | 0.7 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 5456 | 138 | 292 | 751.9 | 0.2 % |
| 🟢 | Rechercher un patient (`patient_search`) | 7241 | 84 | 163 | 611.5 | 0.2 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 5455 | 87 | 155 | 476.1 | 0.2 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 5 🔴 · 2 🟠 · 5 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 167591.7 s, 53.4 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1713 ms)
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 55738.1 s, 17.8 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1140 ms)
- **Télécharger une PJ (~124 Ko)** (`attachment`, 24932.8 s, 7.9 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2539 ms)
- **Ouvrir un message froid (fetch IMAP)** (`read_content_cold`, 20608.6 s, 6.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2126 ms)
- **Envoi (acquittement UI)** (`send`, 15110.0 s, 4.8 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2093 ms)
- **Ouvrir un message enrichi (servi base)** (`read_content`, 11885.3 s, 3.8 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 18.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 9735.1 s, 3.1 %)
  - **coût par appel élevé** (1601 ms)

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 200 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 3147 | 381 | 787 | 1135.6 |
| 200 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 3147 | 59 | 495 | 445.8 |
| 200 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 3147 | 21 | 155 | 136.9 |
| 200 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 3147 | 57 | 65 | 182.6 |
| 200 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 3141 | 17 | 118 | 95.8 |
| 200 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 3141 | 40 | 56 | 131.3 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 6315 | 381 | 795 | 2294.4 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 6315 | 60 | 497 | 854.5 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 6315 | 22 | 156 | 283.8 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 6315 | 59 | 67 | 374.7 |
| 400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 6308 | 18 | 115 | 199.6 |
| 400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 6308 | 43 | 63 | 286.4 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 10509 | 385 | 815 | 3914.7 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 10509 | 63 | 501 | 1495.2 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 10509 | 25 | 162 | 519.8 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 10509 | 61 | 72 | 651.1 |
| 700 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 10516 | 20 | 118 | 357.0 |
| 700 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 10516 | 50 | 76 | 553.0 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15166 | 391 | 814 | 5693.2 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15166 | 66 | 506 | 2216.0 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15166 | 30 | 171 | 839.0 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15166 | 64 | 84 | 997.6 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15157 | 23 | 127 | 601.6 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15157 | 60 | 104 | 987.5 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 18480 | 2058 | 4124 | 47300.7 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 18480 | 2089 | 2708 | 27933.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 18480 | 2051 | 2119 | 20986.6 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 18480 | 68 | 105 | 1350.6 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 18375 | 2049 | 2082 | 25295.5 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 18375 | 73 | 165 | 1569.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 24458 | 2117 | 4170 | 57955.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 24458 | 2126 | 4051 | 55015.7 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 24458 | 2120 | 2238 | 52157.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 24458 | 86 | 192 | 2463.2 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 24445 | 2095 | 2219 | 51603.7 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 24445 | 144 | 347 | 4134.4 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (4170 ms de p95, 2117 ms de p50, n=24458), qui porte **aussi** le temps serveur de l'étape (57955.5 s, 35 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (2219 ms de p95, 2095 ms de p50, n=24445), qui porte **aussi** le temps serveur de l'étape (51603.7 s, 93 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 35500 | 1636.3 | 693.3 | 4131.1 | 4172.8 | 70228.9 |
| attachment,palier:1000 | 5922 | 455.4 | 426.3 | 738.0 | 991.5 | 1308.5 |
| attachment,palier:1400 | 7469 | 2858.2 | 2050.8 | 4131.0 | 4147.5 | 70228.9 |
| attachment,palier:1996 | 9818 | 2539.5 | 2137.4 | 4188.8 | 4220.0 | 5370.0 |
| attachment,palier:200 | 1313 | 347.6 | 373.5 | 700.2 | 778.4 | 1198.3 |
| attachment,palier:400 | 2588 | 402.0 | 392.6 | 709.8 | 941.9 | 1179.9 |
| attachment,palier:700 | 4175 | 423.2 | 404.2 | 722.6 | 968.9 | 1256.4 |
| attachment,palier:transition | 874 | 1594.1 | 974.3 | 4127.3 | 4151.6 | 4384.0 |
| dashboard | 357344 | 910.7 | 138.0 | 2143.3 | 2220.3 | 60005.0 |
| dashboard,call:coverage,palier:1000 | 15166 | 65.8 | 63.6 | 76.7 | 84.0 | 216.1 |
| dashboard,call:coverage,palier:1400 | 18480 | 73.1 | 67.8 | 90.8 | 104.6 | 657.2 |
| dashboard,call:coverage,palier:1996 | 24458 | 100.7 | 85.7 | 149.1 | 192.1 | 3808.8 |
| dashboard,call:coverage,palier:200 | 3147 | 58.0 | 57.3 | 62.7 | 64.8 | 94.4 |
| dashboard,call:coverage,palier:400 | 6315 | 59.3 | 58.6 | 64.2 | 66.6 | 115.1 |
| dashboard,call:coverage,palier:700 | 10509 | 62.0 | 60.8 | 68.0 | 72.2 | 158.1 |
| dashboard,call:coverage,palier:transition | 2774 | 140.8 | 75.8 | 321.1 | 484.5 | 1027.7 |
| dashboard,call:folder,palier:1000 | 15166 | 375.4 | 391.0 | 749.5 | 814.2 | 1498.4 |
| dashboard,call:folder,palier:1400 | 18480 | 2559.6 | 2057.5 | 2741.9 | 4123.6 | 60005.0 |
| dashboard,call:folder,palier:1996 | 24458 | 2369.6 | 2116.5 | 4109.9 | 4169.7 | 4531.3 |
| dashboard,call:folder,palier:200 | 3147 | 360.9 | 381.1 | 733.3 | 787.3 | 1515.9 |
| dashboard,call:folder,palier:400 | 6315 | 363.3 | 380.7 | 738.0 | 794.9 | 1481.7 |
| dashboard,call:folder,palier:700 | 10509 | 372.5 | 385.3 | 747.7 | 814.6 | 1509.1 |
| dashboard,call:folder,palier:transition | 2774 | 989.9 | 463.6 | 2382.3 | 2729.7 | 4334.7 |
| dashboard,call:folders,palier:1000 | 15166 | 55.3 | 29.8 | 156.2 | 171.2 | 354.7 |
| dashboard,call:folders,palier:1400 | 18480 | 1135.6 | 2050.8 | 2110.3 | 2118.6 | 21083.3 |
| dashboard,call:folders,palier:1996 | 24458 | 2132.5 | 2119.7 | 2195.7 | 2237.6 | 3833.9 |
| dashboard,call:folders,palier:200 | 3147 | 43.5 | 21.1 | 139.7 | 155.2 | 253.7 |
| dashboard,call:folders,palier:400 | 6315 | 44.9 | 22.3 | 141.5 | 156.0 | 384.6 |
| dashboard,call:folders,palier:700 | 10509 | 49.5 | 25.3 | 148.8 | 162.3 | 516.6 |
| dashboard,call:folders,palier:transition | 2774 | 670.8 | 87.5 | 2173.3 | 2423.7 | 3069.6 |
| dashboard,call:today,palier:1000 | 15166 | 146.1 | 66.2 | 485.5 | 505.9 | 790.3 |
| dashboard,call:today,palier:1400 | 18480 | 1511.5 | 2088.8 | 2127.3 | 2708.0 | 60000.9 |
| dashboard,call:today,palier:1996 | 24458 | 2249.4 | 2126.1 | 2251.0 | 4051.2 | 4361.4 |
| dashboard,call:today,palier:200 | 3147 | 141.7 | 59.5 | 476.6 | 495.0 | 814.9 |
| dashboard,call:today,palier:400 | 6315 | 135.3 | 60.3 | 474.7 | 497.0 | 629.7 |
| dashboard,call:today,palier:700 | 10509 | 142.3 | 62.9 | 479.7 | 500.5 | 760.0 |
| dashboard,call:today,palier:transition | 2774 | 876.0 | 498.9 | 2232.8 | 2545.3 | 4157.9 |
| dashboard,palier:1000 | 60664 | 160.7 | 66.8 | 457.9 | 524.9 | 1498.4 |
| dashboard,palier:1400 | 73920 | 1320.0 | 427.2 | 2111.9 | 2165.3 | 60005.0 |
| dashboard,palier:1996 | 97832 | 1713.1 | 2103.6 | 2209.2 | 2460.6 | 4531.3 |
| dashboard,palier:200 | 12588 | 151.0 | 59.3 | 448.5 | 506.8 | 1515.9 |
| dashboard,palier:400 | 25260 | 150.7 | 60.3 | 446.5 | 507.2 | 1481.7 |
| dashboard,palier:700 | 42036 | 156.6 | 63.0 | 453.7 | 523.2 | 1509.1 |
| dashboard,palier:transition | 11096 | 669.4 | 310.7 | 2150.6 | 2459.2 | 4334.7 |
| mark_read | 71035 | 89.0 | 67.4 | 146.8 | 206.4 | 8501.1 |
| mark_read,palier:1000 | 12097 | 56.4 | 46.1 | 87.9 | 98.9 | 347.7 |
| mark_read,palier:1400 | 14803 | 65.2 | 53.9 | 104.3 | 123.2 | 1117.7 |
| mark_read,palier:1996 | 19481 | 119.3 | 99.7 | 199.6 | 250.4 | 3637.9 |
| mark_read,palier:200 | 2515 | 43.4 | 30.4 | 72.7 | 75.4 | 144.9 |
| mark_read,palier:400 | 5013 | 45.2 | 32.5 | 74.3 | 77.1 | 151.7 |
| mark_read,palier:700 | 8380 | 49.2 | 36.9 | 78.7 | 83.8 | 369.6 |
| mark_read,palier:transition | 1930 | 144.7 | 75.3 | 382.2 | 576.0 | 1120.7 |
| patient_docs | 289295 | 91.3 | 54.4 | 165.5 | 246.3 | 21033.3 |
| patient_docs,palier:1000 | 50531 | 49.4 | 45.8 | 80.0 | 94.2 | 325.7 |
| patient_docs,palier:1400 | 61117 | 64.9 | 55.6 | 110.6 | 136.8 | 21033.3 |
| patient_docs,palier:1996 | 78566 | 142.9 | 104.0 | 247.0 | 335.9 | 5622.7 |
| patient_docs,palier:200 | 10149 | 34.6 | 35.0 | 50.3 | 59.9 | 110.5 |
| patient_docs,palier:400 | 19895 | 36.0 | 36.3 | 52.9 | 62.3 | 159.7 |
| patient_docs,palier:700 | 34021 | 40.8 | 39.7 | 62.9 | 73.4 | 172.6 |
| patient_docs,palier:transition | 7621 | 147.8 | 70.1 | 391.5 | 598.6 | 1292.0 |
| patient_dossier | 20024 | 96.1 | 63.8 | 177.9 | 248.0 | 3689.1 |
| patient_dossier,palier:1000 | 3450 | 57.9 | 53.5 | 89.5 | 103.5 | 318.8 |
| patient_dossier,palier:1400 | 4189 | 75.5 | 64.7 | 127.8 | 159.5 | 488.4 |
| patient_dossier,palier:1996 | 5456 | 137.8 | 116.6 | 238.2 | 292.0 | 1348.2 |
| patient_dossier,palier:200 | 712 | 38.9 | 37.6 | 56.2 | 65.3 | 123.3 |
| patient_dossier,palier:400 | 1382 | 40.9 | 38.8 | 60.6 | 69.2 | 137.8 |
| patient_dossier,palier:700 | 2406 | 46.7 | 44.5 | 70.1 | 80.4 | 143.0 |
| patient_dossier,palier:transition | 532 | 177.4 | 79.0 | 480.8 | 703.7 | 1564.2 |
| patient_opposition | 20024 | 79.6 | 64.6 | 99.3 | 128.6 | 3078.6 |
| patient_opposition,palier:1000 | 3449 | 65.2 | 63.1 | 75.8 | 82.9 | 153.6 |
| patient_opposition,palier:1400 | 4189 | 69.1 | 66.0 | 84.5 | 93.6 | 510.6 |
| patient_opposition,palier:1996 | 5455 | 87.3 | 80.5 | 123.5 | 155.2 | 1108.6 |
| patient_opposition,palier:200 | 711 | 57.9 | 57.4 | 61.5 | 63.3 | 133.4 |
| patient_opposition,palier:400 | 1382 | 59.1 | 58.5 | 63.3 | 65.6 | 121.7 |
| patient_opposition,palier:700 | 2406 | 61.7 | 60.4 | 67.2 | 71.4 | 128.3 |
| patient_opposition,palier:transition | 535 | 117.5 | 69.9 | 248.6 | 361.4 | 1024.0 |
| patient_search | 26696 | 73.3 | 61.8 | 99.5 | 133.7 | 3992.1 |
| patient_search,palier:1000 | 4603 | 53.6 | 60.7 | 73.1 | 80.8 | 208.9 |
| patient_search,palier:1400 | 5638 | 58.1 | 63.1 | 82.9 | 91.5 | 1067.0 |
| patient_search,palier:1996 | 7241 | 84.4 | 76.2 | 129.5 | 162.7 | 3061.0 |
| patient_search,palier:200 | 965 | 45.1 | 55.6 | 60.2 | 63.1 | 91.4 |
| patient_search,palier:400 | 1869 | 47.0 | 57.8 | 63.1 | 64.0 | 127.4 |
| patient_search,palier:700 | 3181 | 48.9 | 59.3 | 66.6 | 70.5 | 147.5 |
| patient_search,palier:transition | 692 | 112.6 | 66.5 | 243.5 | 454.3 | 995.5 |
| read_content | 89333 | 251.7 | 51.9 | 379.7 | 2107.4 | 15640.1 |
| read_content,palier:1000 | 15174 | 47.5 | 42.5 | 68.6 | 81.5 | 287.7 |
| read_content,palier:1400 | 18372 | 304.1 | 55.1 | 2087.0 | 2103.8 | 15640.1 |
| read_content,palier:1996 | 24396 | 487.2 | 118.5 | 2123.1 | 2160.1 | 3235.5 |
| read_content,palier:200 | 3139 | 31.3 | 30.3 | 38.2 | 41.6 | 118.9 |
| read_content,palier:400 | 6316 | 33.6 | 32.3 | 41.9 | 47.4 | 153.0 |
| read_content,palier:700 | 10506 | 38.9 | 36.5 | 51.5 | 60.2 | 150.4 |
| read_content,palier:transition | 2761 | 296.6 | 65.6 | 732.2 | 2101.9 | 3065.3 |
| read_content_cold | 35691 | 1505.7 | 519.2 | 2146.1 | 2196.7 | 60001.8 |
| read_content_cold,palier:1000 | 6075 | 459.3 | 457.6 | 509.3 | 525.2 | 711.5 |
| read_content_cold,palier:1400 | 7433 | 2837.0 | 2056.9 | 2110.7 | 2124.4 | 60001.8 |
| read_content_cold,palier:1996 | 9692 | 2126.4 | 2114.4 | 2199.0 | 2244.0 | 3762.9 |
| read_content_cold,palier:200 | 1310 | 448.9 | 448.8 | 497.6 | 510.4 | 548.8 |
| read_content_cold,palier:400 | 2550 | 449.7 | 448.9 | 496.9 | 509.0 | 656.9 |
| read_content_cold,palier:700 | 4193 | 452.5 | 450.8 | 500.1 | 514.1 | 617.9 |
| read_content_cold,palier:transition | 992 | 1369.1 | 2045.2 | 2155.2 | 2478.2 | 3074.4 |
| read_list | 178672 | 555.6 | 73.4 | 2085.7 | 2124.1 | 60001.2 |
| read_list,call:emails,palier:1000 | 15157 | 65.1 | 59.9 | 90.8 | 104.4 | 341.4 |
| read_list,call:emails,palier:1400 | 18375 | 85.4 | 72.8 | 132.4 | 165.1 | 1446.3 |
| read_list,call:emails,palier:1996 | 24445 | 169.1 | 143.5 | 282.3 | 347.4 | 3483.4 |
| read_list,call:emails,palier:200 | 3141 | 41.8 | 40.1 | 51.5 | 55.9 | 91.2 |
| read_list,call:emails,palier:400 | 6308 | 45.4 | 43.4 | 56.5 | 62.7 | 149.0 |
| read_list,call:emails,palier:700 | 10516 | 52.6 | 49.7 | 67.9 | 76.3 | 173.0 |
| read_list,call:emails,palier:transition | 2927 | 192.0 | 91.3 | 517.7 | 715.0 | 1591.3 |
| read_list,call:folder,palier:1000 | 15157 | 39.7 | 22.7 | 59.2 | 127.0 | 552.6 |
| read_list,call:folder,palier:1400 | 18375 | 1376.6 | 2048.7 | 2072.1 | 2081.9 | 60001.2 |
| read_list,call:folder,palier:1996 | 24445 | 2111.0 | 2094.8 | 2175.8 | 2218.8 | 3550.5 |
| read_list,call:folder,palier:200 | 3141 | 30.5 | 16.7 | 24.9 | 118.5 | 520.2 |
| read_list,call:folder,palier:400 | 6308 | 31.6 | 17.7 | 27.7 | 114.9 | 508.3 |
| read_list,call:folder,palier:700 | 10516 | 33.9 | 19.7 | 38.3 | 117.8 | 497.2 |
| read_list,call:folder,palier:transition | 2927 | 787.8 | 78.8 | 2107.9 | 2313.3 | 3056.9 |
| read_list,palier:1000 | 30314 | 52.4 | 47.1 | 87.5 | 112.3 | 552.6 |
| read_list,palier:1400 | 36750 | 731.0 | 87.4 | 2063.7 | 2072.1 | 60001.2 |
| read_list,palier:1996 | 48890 | 1140.1 | 1314.6 | 2140.1 | 2175.8 | 3550.5 |
| read_list,palier:200 | 6282 | 36.1 | 34.0 | 50.3 | 61.0 | 520.2 |
| read_list,palier:400 | 12616 | 38.5 | 35.8 | 54.9 | 68.1 | 508.3 |
| read_list,palier:700 | 21032 | 43.3 | 40.2 | 65.5 | 84.7 | 497.2 |
| read_list,palier:transition | 5854 | 489.9 | 90.2 | 2065.9 | 2107.8 | 3056.9 |
| search | 26386 | 474.7 | 407.1 | 645.7 | 961.7 | 4065.7 |
| search,palier:1000 | 4482 | 426.6 | 379.4 | 512.4 | 642.8 | 1619.3 |
| search,palier:1400 | 5388 | 455.8 | 403.4 | 571.1 | 752.9 | 3292.6 |
| search,palier:1996 | 7299 | 530.0 | 474.7 | 692.8 | 920.9 | 2089.7 |
| search,palier:200 | 940 | 383.4 | 335.3 | 453.8 | 596.2 | 1488.1 |
| search,palier:400 | 1862 | 392.1 | 342.6 | 474.7 | 605.9 | 1522.6 |
| search,palier:700 | 3107 | 408.5 | 357.9 | 489.1 | 650.9 | 1561.7 |
| search,palier:transition | 712 | 566.9 | 442.4 | 983.1 | 1219.5 | 2611.3 |
| send | 26042 | 1800.4 | 916.2 | 2172.6 | 2260.4 | 68007.4 |
| send,palier:1000 | 4521 | 626.9 | 487.3 | 908.9 | 930.5 | 1104.7 |
| send,palier:1400 | 5488 | 3868.5 | 2060.6 | 2125.2 | 22548.5 | 68007.4 |
| send,palier:1996 | 7219 | 2093.1 | 2121.7 | 2231.0 | 2293.1 | 5769.1 |
| send,palier:200 | 940 | 656.2 | 791.0 | 893.7 | 913.4 | 971.1 |
| send,palier:400 | 1896 | 624.4 | 480.1 | 895.2 | 914.1 | 1009.8 |
| send,palier:700 | 3200 | 622.2 | 478.9 | 899.1 | 921.4 | 1009.8 |
| send,palier:transition | 712 | 1489.9 | 2053.1 | 2207.4 | 2497.7 | 3085.7 |
| treatment | 22343 | 1120.3 | 754.4 | 2137.8 | 2179.8 | 65713.0 |
| treatment,palier:1000 | 3820 | 554.0 | 709.6 | 853.2 | 928.2 | 1521.4 |
| treatment,palier:1400 | 4591 | 1785.0 | 969.7 | 2111.2 | 2120.5 | 65713.0 |
| treatment,palier:1996 | 6079 | 1601.4 | 2104.5 | 2192.8 | 2227.9 | 3801.6 |
| treatment,palier:200 | 802 | 344.9 | 83.2 | 766.9 | 800.8 | 1207.3 |
| treatment,palier:400 | 1558 | 415.6 | 578.4 | 784.5 | 830.3 | 1247.9 |
| treatment,palier:700 | 2635 | 484.8 | 669.5 | 810.5 | 858.1 | 1310.9 |
| treatment,palier:transition | 696 | 995.8 | 780.1 | 2137.2 | 2439.9 | 2990.4 |
| warmup | 21956 | 557.7 | 256.4 | 1358.4 | 2042.8 | 9713.0 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-04T22:41:46.302000+00:00 → 2026-11-05T00:33:24.956000+00:00 (6699 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-233500.csv`) | ✅ 202932 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-3516` | 1.54 | 23 | 44 | 0.028 | 442.33 |
| `DESKTOP-DEV-X2C-44492` | 1.42 | 19 | 38 | 0.038 | 532.25 |
| `DESKTOP-DEV-X2C-47684` | 1.53 | 18 | 39 | 0.034 | 635.88 |
| `DESKTOP-DEV-X2C-57364` | 1.63 | 19 | 44 | 0.041 | 483.78 |
| `DESKTOP-DEV-X2C-57992` | 1.46 | 27 | 43 | 0.039 | 628.43 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#35328` | 0.00 | 0.28 | 40 |
| `com.docker.backend#35368` | 0.98 | 4.10 | 1624 |
| `dcp#19984` | 0.00 | 0.00 | 9 |
| `dcp#2848` | 0.00 | 0.04 | 9 |
| `dcp#3656` | 0.00 | 0.00 | 9 |
| `dcp#37992` | 0.00 | 0.09 | 12 |
| `dcp#47568` | 0.00 | 0.04 | 9 |
| `dcp#49496` | 0.00 | 0.14 | 9 |
| `dcp#51532` | 0.00 | 0.23 | 9 |
| `dcp#55120` | 0.00 | 0.04 | 9 |
| `dcp#55208` | 0.00 | 0.23 | 49 |
| `dcp#55964` | 0.00 | 0.09 | 13 |
| `dcp#56396` | 0.00 | 0.04 | 9 |
| `dcp#57944` | 0.00 | 0.14 | 9 |
| `dcp#58212` | 0.46 | 3.39 | 3237 |
| `dcp#60088` | 0.00 | 0.14 | 13 |
| `dcp#60360` | 0.00 | 0.04 | 12 |
| `k6#598919` | 0.48 | 1.55 | 2989 |
| `mss.mail.api#3516` | 0.51 | 3.46 | 2679 |
| `mss.mail.api#44492` | 0.51 | 2.73 | 2662 |
| `mss.mail.api#47684` | 0.50 | 3.39 | 2649 |
| `mss.mail.api#57364` | 0.51 | 4.01 | 2656 |
| `mss.mail.api#57992` | 0.51 | 4.17 | 2799 |
| `mss.mail.e2e#41016` | 0.01 | 0.23 | 33 |
| `vmmemWSL#36000` | 4.11 | 14.59 | 65367 |
| `loadtest-otel-collector-zejthbeh` | 0.03 | 0.24 | 129 |
| `loadtest-pgbouncer-awutcxdw` | 0.27 | 0.90 | 49 |
| `mss-mail-flagsmith-app-b6152948` | 0.10 | 0.46 | 561 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.11 | 212 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.07 | 182 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.15 | 358 |
| `mss-mail-rabbitmq-yufcxmzj` | 0.02 | 0.14 | 155 |
| `mss-mail-redis-b6152948` | 0.15 | 1.36 | 788 |
| `mss-mail-rediscommander-ntajvaub` | 0.00 | 0.21 | 51 |
| `mss-mail-seq-b6152948` | 0.06 | 1.16 | 3412 |
| `postgres-pgvector` | 1.64 | 7.63 | 43192 |

- **Hôte** : CPU 47.6 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 60
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 8070, cl_waiting max 72, cl_waiting_maintenance max 72, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 31, maxwait_maintenance_ms max 28, maxwait_ms max 28, maxwait_practitioner_ms max 0, sv_active max 64, sv_idle max 1977, sv_login max 5
- **Backends Postgres** : audit max 5, cache_mb max 45597, direct max 25, idle_over_60s max 1070, majfault_per_s max 34, pooler max 2477, practitioner_databases max 2477, provision max 0, rss_mb max 7673, started_last_60s max 638, total max 2506, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 7541.7 | 1336 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 60000.0 | 1337 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 4376.7 | 1334 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 1336 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 7842.7 | 1334 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 60000.0 | 1331 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 1893.1 | 1332 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2094.4 | 1335 |
| `api/v{version:apiVersion}/Mail/sendmail` | 60000.0 | 1322 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1331.6 | 1332 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 1783.6 | 1332 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 940.5 | 1332 |
| `api/v{version:apiVersion}/Search/semantic` | 2333.5 | 1331 |
| `api/v{version:apiVersion}/Sync/coverage` | 1515.8 | 1335 |

- **p95 client global (k6)** : 2144.6 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -57855.4 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 7.96 |
| Documents CDA /s | 8.00 |
| Durée traitement CDA (s, p95) | 0.13 |
| Événements de session IMAP /s | 35.06 |
| Recherches (s, p95) | 1.875 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 30.7 | 247 | 0.0 (0.1 %), p95 5 | 19.2 (62.4 %), p95 210 | 11.5 (37.6 %), p95 95 |
| `GetMail` | 10.9 | 30.7 | 397 | 2.7 (8.7 %), p95 73 | 25.0 (81.6 %), p95 273 | 3.0 (9.7 %), p95 14 |
| `GetMailsByUids` | 14.8 | 44.1 | 467 | 0.5 (1.2 %), p95 18 | 35.4 (80.2 %), p95 454 | 8.2 (18.6 %), p95 48 |

- **`EnrichPersistMail`** — sur 30.7 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 19.2 ms exécution SQL, 11.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 30.7 ms en moyenne (10.9 requête(s) SQL par appel) : 2.7 ms attente d'une connexion, 25.0 ms exécution SQL, 3.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 44.1 ms en moyenne (14.8 requête(s) SQL par appel) : 0.5 ms attente d'une connexion, 35.4 ms exécution SQL, 8.2 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.6 | 3.0 | 281.1 | 0.9 | 1.3 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.8 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 243.4 | 8.2 | 33.7 | 22.0 | 33.6 | 22.0 | 35.8 | 22.0 | 0.0 | 22.0 | 6.9 | 0.0 | 21.9 | 52.8 | 4.5 |

- **`GetMail`** — sur 3.0 ms de matérialisation, l'appel a construit 10.6 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.8 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **281.1 µs**.

- **`GetMailsByUids`** — sur 8.2 ms de matérialisation, l'appel a construit 243.4 objets, dont 22.0 messages, 33.6 étiquettes, 22.0 destinataires, 35.8 pièces jointes, 22.0 identifiants enrichis, 0.0 acquittements, 22.0 documents médicaux, 6.9 résultats de biologie, 0.0 éléments de synthèse, 21.9 corps de messages, 52.8 objets de fil, 4.5 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **33.7 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **6572.7 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 2.8 | 197.7 | 650 | 132.5 (67.0 %), p95 400 | 3.4 (1.7 %), p95 40 | 15.3 (7.8 %), p95 190 | 25.6 (13.0 %), p95 227 | 20.8 (10.5 %), p95 215 |

- **Enrichir un message** — sur 197.7 ms en moyenne (2.8 message(s) par requête) : 132.5 ms fetch IMAP, 3.4 ms extraction XDM, 15.3 ms parsing CDA, 25.6 ms écritures base, 20.8 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `fetch_bodystructure`, inf `open_folder`, inf `resolve_folder`, 1.00 `fetch_whole_message`, 0.50 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 255.3 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 1194.5 | 1833 | 0.0 (0.0 %), p95 5 | 15.3 (1.3 %), p95 40 | 819.9 (68.6 %), p95 1444 | 290.2 (24.3 %), p95 361 | 833.5 (69.8 %), p95 1730 | 66.6 (5.6 %), p95 454 |

- **Envoyer un message** — sur 1194.5 ms en moyenne : 0.0 ms garde d'opposition, 15.3 ms construction MIME, 819.9 ms obtention de session SMTP, 290.2 ms transmission + acquittement, 833.5 ms archivage Sent, 66.6 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 54.056 | ≥ 60 ⚠️ | 160.05 |
| `smtp_session` | 52.526 | ≥ 60 ⚠️ | 8.18 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 6.71 |
| `EnrichEmails` | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 2.442 | ≥ 60 ⚠️ | 11.93 |
| `GetAttachmentStream` | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 46.900 | ≥ 60 ⚠️ | 10.42 |
| `GetEmailContent` | 56.457 | 58.674 | 13.500 | 58.745 | 16.31 |
| `GetFolders` | 0.005 | 9.308 | 9.308 | 4.500 | 30.00 |
| `ReadFolder` | 53.357 | 58.445 | 58.500 | 58.439 | 54.46 |
| `ReadToday` | 1.986 | 58.500 | 4.971 | 58.500 | 27.37 |
| `UpdateFlag` | 57.672 | ≥ 60 ⚠️ | 4.900 | ≥ 60 ⚠️ | 21.95 |

> ⚠️ **Repliement impossible : la phase `operate` n'est pas mesurée sur la fenêtre de régime.** Les chiffres ci-dessus restent toutes fenêtres. Ce n'est pas « aucune détention » — c'est « aucune mesure » (task-214).

| Voie | Acquisitions /s |
|---|---|
| `read` | 160.05 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

🚨 **Détention d'EXPLOITATION saturée** pour `AppendToSent`, `EnrichEmails`, `GetAttachmentStream`, `UpdateFlag` — et celle-là ne s'explique pas par la chauffe. Le verrou de session est tenu ≥ 60 s hors établissement : c'est sa **portée** qu'il faut discuter, et les buckets ne suffisent plus à la mesurer (borne haute à 60 s).

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 60.000 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

> ⓘ **PgBouncer — transitoire d'attente, écarté du verdict.** 82 échantillon(s) sur 1201 portent une attente cliente non nulle (6.8 %, pointe à 72), sous le seuil de présence soutenue de 25 %. Ce profil est celui d'une **ouverture de palier**, pas d'un pooler qui n'absorbe plus — il ne désigne donc pas de facteur limitant. À surveiller tout de même : sur la campagne du 2026-07-29, cette pointe croît avec la charge.

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| conteneur `postgres-pgvector` (CPU) | 7.63 cœurs | 24 cœurs | 31.8 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-57992` | 27.00 éléments | 100 éléments | 27.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#57992` (CPU) | 4.17 cœurs | 24 cœurs | 17.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#57364` (CPU) | 4.01 cœurs | 24 cœurs | 16.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#3516` (CPU) | 3.46 cœurs | 24 cœurs | 14.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#47684` (CPU) | 3.39 cœurs | 24 cœurs | 14.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#44492` (CPU) | 2.73 cœurs | 24 cœurs | 11.4 % | 0.0 % — transitoire |
| processus `k6#598919` (CPU) | 1.55 cœurs | 24 cœurs | 6.5 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (conteneur `postgres-pgvector` (CPU)) monte à 31.8 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 28 121 631

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 331 129 |
| OpenAI | gpt-4o-mini | prompt | 27 790 502 |
| OpenAI | text-embedding-3-small | embedding | 36 311 354 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 14 778 | 0 (0.0 %) | 0 | 132.4 | 1.09 | 0.96 | 2.46 |
| étiquetage (chat) | OpenAI | 14 778 | 0 (0.0 %) | 0 | 132.4 | 1.05 | 0.92 | 2.45 |
| embedding | OpenAI | 14 778 | 0 (0.0 %) | 0 | 132.4 | 0.54 | 0.43 | 1.46 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 20 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.0 | 4.0 |
| GPU — VRAM occupée (Mo) | 2 377 | 2 391 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

⚠️ **non relevé** — photos `pgserver-*-debut` / `pgserver-*-fin` absentes du répertoire du tir. `run.sh` les pose quand `pg_stat_statements` est chargé (`pg-statements.sh check`) ; sans elles, aucune grandeur serveur n'est publiée.

### Top 20 des requêtes par temps serveur cumulé

124 formes de requête, 26 466 706 appels, **55.9 min** de temps serveur cumulé.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **22.4 %** | 22 % | 61 068 | 0.05 | 12.32 | 30.9 | 264 | 0 % | 0 | 1 070 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 2 | **20.9 %** | 43 % | 61 005 | 0.05 | 11.48 | 30.9 | 307 | 0 % | 0 | 1 057 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 3 | **8.1 %** | 51 % | 282 295 | 0.23 | 0.96 | 1.0 | 18 | 14 % | 0 | 1 747 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **4.6 %** | 56 % | 3 625 765 | 2.97 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 5 | **4.2 %** | 60 % | 111 110 | 0.09 | 1.26 | 21.1 | 235 | 0 % | 0 | 1 830 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 6 | **3.9 %** | 64 % | 11 660 | 0.01 | 11.15 | 29.8 | 399 | 17 % | 0 | 659 | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 7 | **3.8 %** | 68 % | 3 626 333 | 2.97 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 8 | **3.7 %** | 72 % | 8 873 023 | 7.27 | 0.01 | 0.0 | 0 | — | 0 | 1 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 9 | **2.7 %** | 74 % | 354 060 | 0.29 | 0.26 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 10 | **2.3 %** | 77 % | 18 178 | 0.01 | 4.23 | 20.0 | 574 | 2 % | 0 | 858 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 11 | **2.2 %** | 79 % | 267 725 | 0.22 | 0.28 | 1.0 | 9 | 2 % | 0 | 1 745 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 12 | **2.0 %** | 81 % | 1 219 275 | 1.00 | 0.05 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 13 | **1.9 %** | 83 % | 18 191 | 0.01 | 3.56 | 20.0 | 578 | 2 % | 0 | 859 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 14 | **1.1 %** | 84 % | 48 368 | 0.04 | 0.75 | 6.3 | 183 | 0 % | 0 | 1 000 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 15 | **1.0 %** | 85 % | 22 337 | 0.02 | 1.47 | 1.0 | 123 | 0 % | 0 | 654 | — | `INSERT INTO "MailAttachments" ("Id", "Content", "ContentType", "DocumentId", "FileName", "Guid", "MailId", "Size") VALU…` |
| 16 | **0.9 %** | 86 % | 407 927 | 0.33 | 0.07 | 2.1 | 8 | 0 % | 0 | 1 952 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 17 | **0.9 %** | 87 % | 407 913 | 0.33 | 0.07 | 1.3 | 15 | 0 % | 0 | 1 952 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 18 | **0.8 %** | 87 % | 139 951 | 0.11 | 0.19 | 18.0 | 5 | 0 % | 0 | 1 046 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **0.8 %** | 88 % | 9 509 | 0.01 | 2.78 | 1.0 | 241 | 0 % | 0 | 492 | — | `UPDATE "MailAttachments" SET "Content" = $1, "Size" = $2 WHERE "Id" = $3` |
| 20 | **0.6 %** | 89 % | 111 047 | 0.09 | 0.18 | 21.1 | 5 | 0 % | 0 | 1 828 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 88.7 % | 58.6 % |
| INSERT | 6.0 % | 2.2 % |
| UPDATE | 1.4 % | 0.7 % |
| DELETE | 0.0 % | 0.1 % |
| AUTRE | 3.9 % | 38.4 % |
| bases : praticien (N bases) | 82.3 % | 31.4 % |
| bases : unique (1 base) | 17.7 % | 68.6 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **12.3** | 541 | 61 068 | 22.4 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailCo…` |
| **11.5** | 371 | 61 005 | 20.9 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMe…` |
| **11.2** | 453 | 11 660 | 3.9 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **4.2** | 113 | 18 178 | 2.3 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **3.6** | 255 | 18 191 | 1.9 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

⚠️ **non relevé** — photos `pgtables-*-debut` / `pgtables-*-fin` absentes.

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🔴 | requête n°1 (22.4 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Infra | 🟡 | requête n°4 (4.6 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°8 (3.7 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Schéma | 🟡 | requête n°10 (2.3 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-013350.tsv`, `pgserver-journey-fin-013354.tsv`, `pgtables-journey-fin-013358.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 229418 — dont **229418** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-escalier-1996-20261104-ia-simulee-013324.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
