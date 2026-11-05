# Rapport de tir — journey-escalier-1996-20261105-task422-pool1

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-escalier-1996-20261105-task422-pool1-185011.json`.

## Analyse — task-422, jambe B (`default_pool_size` 2 → 1) : **réglage retenu**

> Rédigée à la main après le rapport généré. Référence : jambe A,
> `report-journey-escalier-1996-20261104-ia-simulee-013324.md` (même escalier, même banc, même IA simulée).
> Seul écart voulu : `default_pool_size = 1` dans `src/AppHost/pgbouncer/pgbouncer.ini`.

**Verdict ROUGE ci-dessous = panne du banc, pas de l'application.** Le pod Toxiproxy du cluster mail (192.168.1.69) a
redémarré vers 17:27 UTC (+5 310 s, palier 1400 en régime depuis +4 568 s) et ses proxies `dovecot-imap` /
`greenmail-smtp` ont disparu : IMAP et SMTP répondent `ConnectionRefused` jusqu'à la fin du tir (constaté à 18:55 :
`GET /proxies` = `{}`, ports 30993 et 30465 fermés ; proxies recréés ensuite par le seed `--messages 0`).

| Fenêtre (statuts k6, Prometheus `k6_http_reqs_total`) | 200 | 503 | 500 | 0 (réseau) |
|---|---|---|---|---|
| Palier 1400, régime avant la panne (17:14:40 → 17:26:30 UTC) | ≈ 201 654 | 0 | 0 | 7 (relais du poste, `dial i/o timeout`) |
| Palier 1400, après la panne (17:26:30 → 17:31:00 UTC) | ≈ 39 443 | ≈ 6 934 | ≈ 11 328 | ≈ 201 |

Les 7,6 % d'erreurs du palier 1400 et tout le palier 1996 sont donc **VOID**. Les 500 de la panne (`dashboard`,
`read_list` : « An unexpected error occurred ») sont des pannes IMAP rendues en 500 : c'est le périmètre de
**task-425**, reproduit ici gratuitement.

| Critère task-422 | Jambe A (pool 2) | Jambe B (pool 1) | Tenu |
|---|---|---|---|
| Backends Postgres par médecin actif à 1000 (max) | 1 955 → **1,96** | 1 038 → **1,04** | ✅ (< 1,6) |
| Erreurs à 1400 | 24,8 % (`53300`, `08P01`) | **0** applicative avant la panne du banc | ✅ |
| Backends au pic à 1400 | 2 506 / 2 500 | 1 436 / 2 500 | — |
| p95 d'étape, pire écart B/A entre 200 et 1000 | — | **+7,7 %** (fiche patient à 400 : 392 contre 364 ms) | ✅ (≤ 20 %) |
| `cl_waiting` sur les bases praticien | 0 % | 0 % à tous les paliers | ✅ |
| Mémoire du conteneur Postgres (max, 200 → 1000) | 100 % partout | 16 → 72 % | gain |

p95 d'étape à 1000, A → B : dashboard 525 → 525, inbox 112 → 88, message enrichi 82 → 60, message froid 525 → 516,
recherche 643 → 630, envoi 931 → 927, PJ 991 → 737, marquer lu 99 → 86, patient 81 → 71, dossier 103 → 86,
fiche patient 531 → 451 ms.

**Réserves d'iso-conditions** (aucune n'inverse le verdict) : lignée de code `develop` + task-423 (gestion d'erreurs,
hors chemin nominal) ; bases plus âgées d'un tir, réserves froides en partie consommées par la jambe A (étape 4 et
étape 3 à lire avec prudence, d'où le refus « servi base » à 93,4 %) ; cluster redémarré avant le tir.

**Pourquoi ce réglage avait été écarté le 2026-07-27** : famille `mixed` à 60 VU compressés, plusieurs requêtes
simultanées par praticien. La famille `journey` (1 VU = 1 médecin au rythme réel) ne montre aucune attente sur les
bases praticien : la concurrence réelle d'un médecin est de 1.

**Nouveau mur estimé** : `max_connections` / 1,04 ≈ **2 400 médecins actifs** (contre ≈ 1 300), sous réserve
d'un tir qui le mesure.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- 14.18 % des demandes ont échoué (au-delà du plafond de 1 %)
- le stock de messages de test s'est épuisé pendant le tir : le corpus a changé de forme en cours de mesure, les chiffres ne se comparent plus

À instruire une fois le tir refait :
- à 200 médecins, 4 étape(s) dépassent le temps de réponse attendu : « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) », « Ouvrir la page d'un dossier patient »
- une étape ne mesure pas ce que son nom annonce — son chiffre décrit un autre geste
- 7 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 200 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 2 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 6660s — **Latence** : mssante
- **Requêtes** : 1241929 — **débit émergent global** : 185.3 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 89813 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 185.3 | **477.6** | 70.6 | **2116.8** | — | 74334.3 | 14.18 | 85.3 | 0 | 0 | 234613/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **200 médecins** | 1080 | 1031 | 42688 | 41.40 | 0.00 | 167.2 |
| **400 médecins** | 1080 | 1031 | 85777 | 83.20 | 0.00 | 348.0 |
| **700 médecins** | 1080 | 982 | 143562 | 146.19 | 0.00 | 533.1 |
| **1000 médecins** | 1080 | 982 | 202600 | 206.31 | 0.00 | 748.6 |
| **1400 médecins** | 1080 | 982 | 262807 | 267.62 | 7.60 | 868.6 |
| **1996 médecins** | 1080 | 933 | 329710 | 353.39 | 39.97 | 172.0 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 200 médecins | 400 médecins | 700 médecins | 1000 médecins | 1400 médecins | 1996 médecins |
|---|---|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 60 / 509 (n=12736) | 61 / 513 (n=25552) | 62 / 517 (n=42840) | 64 / 525 (n=60192) | 76 / 2107 (n=78932) | 2093 / 2245 (n=97804) |
| 2 | Ouvrir / rafraîchir l'inbox | 34 / 54 (n=6362) | 39 / 63 (n=12780) | 39 / 76 (n=21404) | 42 / 88 (n=30084) | 58 / 2059 (n=39294) | 1399 / 2124 (n=48906) |
| 3 | Ouvrir un message enrichi (servi base) | 31 / 41 (n=3181) | 34 / 46 (n=6399) | 35 / 52 (n=10708) | 37 / 60 (n=15044) | 48 / 137 (n=19639) | 88 / 2131 (n=24408) |
| 4 | Ouvrir un message froid (fetch IMAP) | 448 / 505 (n=1278) | 449 / 514 (n=2596) | 449 / 513 (n=4282) | 453 / 516 (n=6032) | 478 / 2111 (n=7800) | 2097 / 2173 (n=9879) |
| 5 | Recherche | 353 / 608 (n=955) | 355 / 579 (n=1888) | 359 / 634 (n=3213) | 363 / 630 (n=4556) | 396 / 731 (n=5955) | 451 / 828 (n=7520) |
| 6 | Envoi (acquittement UI) | 777 / 921 (n=938) | 484 / 919 (n=1887) | 481 / 917 (n=3184) | 482 / 927 (n=4535) | 836 / 21058 (n=5897) | 2099 / 2206 (n=7257) |
| 7 | Télécharger une PJ (~124 Ko) | 36 / 697 (n=1294) | 41 / 711 (n=2612) | 45 / 716 (n=4283) | 53 / 737 (n=6005) | 433 / 4122 (n=7901) | 2109 / 4178 (n=9872) |
| 8 | Marquer lu | 31 / 75 (n=2553) | 34 / 78 (n=5153) | 35 / 81 (n=8579) | 38 / 86 (n=12060) | 52 / 111 (n=15733) | 80 / 172 (n=19596) |
| 9 | Rechercher un patient | 57 / 63 (n=931) | 59 / 65 (n=1899) | 59 / 68 (n=3186) | 59 / 71 (n=4439) | 62 / 85 (n=5796) | 68 / 115 (n=7378) |
| 10 | Ouvrir la page d'un dossier patient | 58 / 66 (n=1416) | 60 / 73 (n=2837) | 60 / 78 (n=4803) | 61 / 86 (n=6755) | 65 / 134 (n=8718) | 97 / 231 (n=11022) |
| 11 | Fiche patient complète (ressenti médecin) | 257 / 367 (n=708) | 276 / 392 (n=1418) | 280 / 416 (n=2401) | 303 / 451 (n=3378) | 370 / 665 (n=4359) | 549 / 1284 (n=5512) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **200 médecins** | 14.5 / 20 | 34.8 / 65 | 1580 | 367 |
| **400 médecins** | 14.5 / 20 | 34.7 / 65 | 3174 | 392 |
| **700 médecins** | 14.3 / 20 | 34.1 / 65 | 5498 | 416 |
| **1000 médecins** | 14.6 / 20 | 34.7 / 65 | 7536 | 451 |
| **1400 médecins** | 14.3 / 20 | 34.0 / 65 | 9804 | 665 |
| **1996 médecins** | 14.5 / 20 | 34.4 / 65 | 12256 | 1284 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3570 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- ⚠️ **Réserve épuisée en cours de tir** (1 fois) — le corpus a changé de forme pendant la mesure : soit le traitement n'a plus alimenté le dossier, soit « ouvrir un message froid » a relu du déjà-ouvert. Tir à refaire sur une boîte plus grande ou une campagne plus courte.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 483 ms en moyenne, 11309 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 200 médecins | 400 médecins | 700 médecins | 1000 médecins | 1400 médecins | 1996 médecins |
|---|---|---|---|---|---|---|
| Sessions IMAP (moy/max) | 1096 / 2233 (magasin) | 1096 / 2233 (magasin) | 1096 / 2233 (magasin) | 1096 / 2233 (magasin) | 1096 / 2233 (magasin) | 1096 / 2233 (magasin) |
| Backends Postgres (moy/max) | 226 / 246 | 429 / 441 | 726 / 738 | 1024 / 1038 | 1417 / 1436 | 1989 / 2029 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 1 | 0 / 1 | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 4/210 (2 %) | 8/208 (4 %) | 22/203 (11 %) | 25/197 (13 %) | 41/179 (23 %) | 67/156 (43 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/210 (0 %) | 0/208 (0 %) | 0/203 (0 %) | 0/197 (0 %) | 0/179 (0 %) | 0/156 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 4/210 (2 %) | 8/208 (4 %) | 22/203 (11 %) | 25/197 (13 %) | 41/179 (23 %) | 67/156 (43 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 11.2 | 8.3 | 24.6 | 14.4 | 24.4 | 163.1 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 11.2 | 8.3 | 24.6 | 14.4 | 24.4 | 163.1 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 | 0 | 0 | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé | non relevé | non relevé | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 31 / 237 | 39 / 242 | 52 / 245 | 63 / 245 | 78 / 261 | 97 / 273 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 15 | 21 | 54 | 28 | 94 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 217 | 410 | 707 | 1007 | 1404 | 1997 |
| Backends **directs** — audit + provisionnement (max) | 24 | 25 | 25 | 26 | 28 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 | 5 | 5 | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 0 | 0 | 1 | 1 | 3 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 16.5 | 30.4 | 51.1 | 71.7 | 91.7 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 4 / 89 |
| RSS par réplica api-mail, Mo (moy/max) | 454 / 569 (5 réplicas) | 663 / 825 (5 réplicas) | 1107 / 1367 (5 réplicas) | 1523 / 1728 (5 réplicas) | 2025 / 2212 (5 réplicas) | 2171 / 2324 (5 réplicas) |

- à 200 médecins : Backends Postgres au pic : **246.0 / 2500** (9.8 % de `max_connections`)
- à 400 médecins : Backends Postgres au pic : **441.0 / 2500** (17.6 % de `max_connections`)
- à 700 médecins : Backends Postgres au pic : **738.0 / 2500** (29.5 % de `max_connections`)
- à 1000 médecins : Backends Postgres au pic : **1038.0 / 2500** (41.5 % de `max_connections`)
- à 1400 médecins : Backends Postgres au pic : **1436.0 / 2500** (57.4 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2029.0 / 2500** (81.2 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

⛔ **Chauffe insuffisante — les étapes 2, 3, 10, 11 ne sont pas opposables.** **99.9 %** des médecins ont terminé leur chauffe (plancher **90 %**, sur 1996 médecins) ; 1 lot(s) d'analyse perdu(s) ; 93.4 % des ouvertures de l'étape 3 servies par la base (plancher 95 %). Ces étapes sont **servies par la base des messages analysés** : une base peu peuplée les rend rapides sans rien dire de la charge visée — au tir `journey-remote-n500` du 2026-08-09, `GetMailsByUids` coûtait **55,4 ms / 7,8 requêtes** par appel contre **1 199,7 ms / 14,8** sur un tir dont la base était peuplée. **Ce tir ne mesure donc pas la capacité** : ses latences sont flattées, quelle que soit leur valeur. Relancer après une chauffe aboutie (lots `JOURNEY_WARMUP_BATCH`, task-244).

> ⓘ Chauffe : **115 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **11 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 200 : chauffe [+30 s..+79 s] (5 % de la fenêtre) ; **régime [+79 s..+1110 s]** porte le verdict
>   palier 400 : chauffe [+1140 s..+1189 s] (5 % de la fenêtre) ; **régime [+1189 s..+2220 s]** porte le verdict
>   palier 700 : chauffe [+2250 s..+2348 s] (9 % de la fenêtre) ; **régime [+2348 s..+3330 s]** porte le verdict
>   palier 1000 : chauffe [+3360 s..+3458 s] (9 % de la fenêtre) ; **régime [+3458 s..+4440 s]** porte le verdict
>   palier 1400 : chauffe [+4470 s..+4568 s] (9 % de la fenêtre) ; **régime [+4568 s..+5550 s]** porte le verdict
>   palier 1996 : chauffe [+5580 s..+5727 s] (14 % de la fenêtre) ; **régime [+5727 s..+6660 s]** porte le verdict

⛔ **Étape 3 « servi base » refusée — elle ne mesure pas ce que son nom annonce.** Seules **93.4 %** de ses ouvertures portent les documents de l'analyse, pour un plancher de 95 % : le reste a basculé sur le serveur de messagerie, donc cette étape mesure en partie des ouvertures **froides** et son chiffre n'est **pas** un verdict, quelle que soit sa valeur (pour situer : 50.58 sollicitations/s du serveur de messagerie sur la fenêtre, étapes 3/4 et rafale dossier confondues). Causes connues : bande chaude non analysée par la chauffe (task-224, défaut 5 — les 440 ms du 2026-08-03), ou mails de chauffe estampillés **génération 0** (UIDVALIDITY) donc inatteignables en base (certification du 2026-08-06 — la chauffe doit lister les dossiers AVANT d'analyser).

### 200 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 60 (300) | 509 (1500) | 12736 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 34 (300) | 54 (1000) | 6362 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 31 (100) | 41 (500) | 3181 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 448 (800) | 505 (2500) | 1278 | ✅ |
| 5 | Recherche | 353 (500) | 608 (2000) | 955 | ✅ |
| 6 | Envoi (acquittement UI) | 777 (1000) | 921 (3000) | 938 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 36 (500) | 697 (2000) | 1294 | ✅ |
| 8 | Marquer lu | 31 (200) | 75 (1000) | 2553 | ✅ |
| 9 | Rechercher un patient | 57 (300) | 63 (1500) | 931 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 58 (500) | 66 (2000) | 1416 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 257 (1500) | 367 (4000) | 708 | ⛔ non opposable — chauffe insuffisante |

### 400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 61 (300) | 513 (1500) | 25552 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 39 (300) | 63 (1000) | 12780 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 34 (100) | 46 (500) | 6399 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 449 (800) | 514 (2500) | 2596 | ✅ |
| 5 | Recherche | 355 (500) | 579 (2000) | 1888 | ✅ |
| 6 | Envoi (acquittement UI) | 484 (1000) | 919 (3000) | 1887 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 41 (500) | 711 (2000) | 2612 | ✅ |
| 8 | Marquer lu | 34 (200) | 78 (1000) | 5153 | ✅ |
| 9 | Rechercher un patient | 59 (300) | 65 (1500) | 1899 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 60 (500) | 73 (2000) | 2837 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 276 (1500) | 392 (4000) | 1418 | ⛔ non opposable — chauffe insuffisante |

### 700 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 62 (300) | 517 (1500) | 42840 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 39 (300) | 76 (1000) | 21404 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 35 (100) | 52 (500) | 10708 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 449 (800) | 513 (2500) | 4282 | ✅ |
| 5 | Recherche | 359 (500) | 634 (2000) | 3213 | ✅ |
| 6 | Envoi (acquittement UI) | 481 (1000) | 917 (3000) | 3184 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 45 (500) | 716 (2000) | 4283 | ✅ |
| 8 | Marquer lu | 35 (200) | 81 (1000) | 8579 | ✅ |
| 9 | Rechercher un patient | 59 (300) | 68 (1500) | 3186 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 60 (500) | 78 (2000) | 4803 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 280 (1500) | 416 (4000) | 2401 | ⛔ non opposable — chauffe insuffisante |

### 1000 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 64 (300) | 525 (1500) | 60192 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 42 (300) | 88 (1000) | 30084 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 37 (100) | 60 (500) | 15044 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 453 (800) | 516 (2500) | 6032 | ✅ |
| 5 | Recherche | 363 (500) | 630 (2000) | 4556 | ✅ |
| 6 | Envoi (acquittement UI) | 482 (1000) | 927 (3000) | 4535 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 53 (500) | 737 (2000) | 6005 | ✅ |
| 8 | Marquer lu | 38 (200) | 86 (1000) | 12060 | ✅ |
| 9 | Rechercher un patient | 59 (300) | 71 (1500) | 4439 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 61 (500) | 86 (2000) | 6755 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 303 (1500) | 451 (4000) | 3378 | ⛔ non opposable — chauffe insuffisante |

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 76 (300) | 2107 (1500) | 78932 | ❌ |
| 2 | Ouvrir / rafraîchir l'inbox | 58 (300) | 2059 (1000) | 39294 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 48 (100) | 137 (500) | 19639 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 478 (800) | 2111 (2500) | 7800 | ✅ |
| 5 | Recherche | 396 (500) | 731 (2000) | 5955 | ✅ |
| 6 | Envoi (acquittement UI) | 836 (1000) | 21058 (3000) | 5897 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 433 (500) | 4122 (2000) | 7901 | ❌ |
| 8 | Marquer lu | 52 (200) | 111 (1000) | 15733 | ✅ |
| 9 | Rechercher un patient | 62 (300) | 85 (1500) | 5796 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 65 (500) | 134 (2000) | 8718 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 370 (1500) | 665 (4000) | 4359 | ⛔ non opposable — chauffe insuffisante |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 2093 (300) | 2245 (1500) | 97804 | ❌ |
| 2 | Ouvrir / rafraîchir l'inbox | 1399 (300) | 2124 (1000) | 48906 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 88 (100) | 2131 (500) | 24408 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 2097 (800) | 2173 (2500) | 9879 | ❌ |
| 5 | Recherche | 451 (500) | 828 (2000) | 7520 | ✅ |
| 6 | Envoi (acquittement UI) | 2099 (1000) | 2206 (3000) | 7257 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 2109 (500) | 4178 (2000) | 9872 | ❌ |
| 8 | Marquer lu | 80 (200) | 172 (1000) | 19596 | ✅ |
| 9 | Rechercher un patient | 68 (300) | 115 (1500) | 7378 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 97 (500) | 231 (2000) | 11022 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 549 (1500) | 1284 (4000) | 5512 | ⛔ non opposable — chauffe insuffisante |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Arrivée dashboard (`dashboard`) | 97804 | 1692 | 2245 | 165479.6 | 53.9 % |
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 48906 | 1104 | 2124 | 53994.2 | 17.6 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 9872 | 2485 | 4178 | 24534.5 | 8.0 % |
| 🔴 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 9879 | 2102 | 2173 | 20766.9 | 6.8 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 7257 | 2106 | 2206 | 15283.9 | 5.0 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 24408 | 438 | 2131 | 10679.4 | 3.5 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 6128 | 1489 | 2172 | 9125.3 | 3.0 % |
| 🟢 | Recherche (`search`) | 7520 | 503 | 828 | 3785.6 | 1.2 % |
| 🟢 | Marquer lu (`mark_read`) | 19596 | 88 | 172 | 1718.1 | 0.6 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 5512 | 111 | 231 | 613.1 | 0.2 % |
| 🟢 | Rechercher un patient (`patient_search`) | 7378 | 67 | 115 | 494.8 | 0.2 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 5510 | 77 | 118 | 424.7 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 5 🔴 · 2 🟠 · 5 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 165479.6 s, 53.9 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1692 ms)
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 53994.2 s, 17.6 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1104 ms)
- **Télécharger une PJ (~124 Ko)** (`attachment`, 24534.5 s, 8.0 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2485 ms)
- **Ouvrir un message froid (fetch IMAP)** (`read_content_cold`, 20766.9 s, 6.8 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2102 ms)
- **Envoi (acquittement UI)** (`send`, 15283.9 s, 5.0 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2106 ms)
- **Ouvrir un message enrichi (servi base)** (`read_content`, 10679.4 s, 3.5 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 24.3×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 9125.3 s, 3.0 %)
  - **coût par appel élevé** (1489 ms)

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 200 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 3184 | 380 | 811 | 1169.5 |
| 200 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 3184 | 60 | 491 | 420.5 |
| 200 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 3184 | 21 | 155 | 135.5 |
| 200 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 3184 | 58 | 65 | 186.2 |
| 200 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 3181 | 17 | 112 | 92.1 |
| 200 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 3181 | 41 | 53 | 132.5 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 6388 | 385 | 796 | 2355.7 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 6388 | 62 | 496 | 872.4 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 6388 | 23 | 159 | 293.8 |
| 400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 6388 | 60 | 68 | 386.4 |
| 400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 6390 | 19 | 117 | 204.2 |
| 400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 6390 | 45 | 59 | 298.6 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 10710 | 385 | 810 | 3982.2 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 10710 | 62 | 497 | 1499.3 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 10710 | 24 | 159 | 506.5 |
| 700 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 10710 | 60 | 70 | 654.5 |
| 700 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 10702 | 19 | 120 | 360.9 |
| 700 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 10702 | 47 | 68 | 522.8 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15048 | 389 | 819 | 5661.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15048 | 63 | 501 | 2129.5 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15048 | 26 | 164 | 747.0 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15048 | 61 | 74 | 940.7 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15042 | 20 | 124 | 531.2 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15042 | 51 | 78 | 813.8 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 19733 | 431 | 4096 | 35696.9 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 19733 | 75 | 2121 | 12968.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 19733 | 37 | 2100 | 5992.7 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 19733 | 66 | 96 | 1375.6 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 19647 | 29 | 2069 | 9928.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 19647 | 66 | 135 | 1479.1 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 24451 | 2100 | 4145 | 57454.8 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 24451 | 2111 | 4041 | 54387.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 24451 | 2108 | 2175 | 51613.2 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 24451 | 80 | 134 | 2024.1 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 24453 | 2076 | 2145 | 50969.7 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 24453 | 108 | 241 | 3024.5 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (4145 ms de p95, 2100 ms de p50, n=24451), qui porte **aussi** le temps serveur de l'étape (57454.8 s, 35 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (2145 ms de p95, 2076 ms de p50, n=24453), qui porte **aussi** le temps serveur de l'étape (50969.7 s, 94 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 36241 | 1337.3 | 431.8 | 4103.6 | 4149.2 | 74334.3 |
| attachment,palier:1000 | 6005 | 269.5 | 53.2 | 690.5 | 737.4 | 1255.5 |
| attachment,palier:1400 | 7901 | 1894.3 | 433.5 | 2101.4 | 4121.8 | 74334.3 |
| attachment,palier:1996 | 9872 | 2485.3 | 2109.3 | 4158.3 | 4178.3 | 4348.7 |
| attachment,palier:200 | 1294 | 199.0 | 36.1 | 656.9 | 697.2 | 1077.3 |
| attachment,palier:400 | 2612 | 221.7 | 41.0 | 665.6 | 711.0 | 1191.3 |
| attachment,palier:700 | 4283 | 247.0 | 45.3 | 676.8 | 716.1 | 1175.1 |
| attachment,palier:transition | 951 | 1505.0 | 798.0 | 4134.5 | 4164.3 | 4354.9 |
| dashboard | 364144 | 769.4 | 105.0 | 2119.3 | 2155.2 | 60001.4 |
| dashboard,call:coverage,palier:1000 | 15048 | 62.5 | 61.4 | 69.1 | 73.6 | 157.1 |
| dashboard,call:coverage,palier:1400 | 19733 | 69.7 | 65.8 | 84.3 | 95.6 | 450.5 |
| dashboard,call:coverage,palier:1996 | 24451 | 82.8 | 79.5 | 115.3 | 134.1 | 525.6 |
| dashboard,call:coverage,palier:200 | 3184 | 58.5 | 58.1 | 63.0 | 64.9 | 79.1 |
| dashboard,call:coverage,palier:400 | 6388 | 60.5 | 59.7 | 65.4 | 67.8 | 133.9 |
| dashboard,call:coverage,palier:700 | 10710 | 61.1 | 60.3 | 66.9 | 69.8 | 133.8 |
| dashboard,call:coverage,palier:transition | 2803 | 101.5 | 75.5 | 175.7 | 232.2 | 633.8 |
| dashboard,call:folder,palier:1000 | 15048 | 376.2 | 388.5 | 751.3 | 819.3 | 1497.9 |
| dashboard,call:folder,palier:1400 | 19733 | 1809.0 | 430.7 | 2098.7 | 4095.7 | 60001.4 |
| dashboard,call:folder,palier:1996 | 24451 | 2349.8 | 2099.9 | 4095.6 | 4145.0 | 4346.8 |
| dashboard,call:folder,palier:200 | 3184 | 367.3 | 380.0 | 739.8 | 811.2 | 1458.0 |
| dashboard,call:folder,palier:400 | 6388 | 368.8 | 385.3 | 741.0 | 796.2 | 1530.8 |
| dashboard,call:folder,palier:700 | 10710 | 371.8 | 384.9 | 741.5 | 809.8 | 1501.5 |
| dashboard,call:folder,palier:transition | 2803 | 926.1 | 458.3 | 2216.2 | 2316.2 | 4335.7 |
| dashboard,call:folders,palier:1000 | 15048 | 49.6 | 25.6 | 148.6 | 163.7 | 277.6 |
| dashboard,call:folders,palier:1400 | 19733 | 303.7 | 37.1 | 2079.7 | 2099.7 | 60001.1 |
| dashboard,call:folders,palier:1996 | 24451 | 2110.9 | 2107.7 | 2155.4 | 2175.5 | 2508.0 |
| dashboard,call:folders,palier:200 | 3184 | 42.6 | 21.3 | 140.5 | 155.4 | 263.6 |
| dashboard,call:folders,palier:400 | 6388 | 46.0 | 23.4 | 145.2 | 159.5 | 219.7 |
| dashboard,call:folders,palier:700 | 10710 | 47.3 | 23.9 | 145.5 | 159.0 | 237.9 |
| dashboard,call:folders,palier:transition | 2803 | 593.4 | 61.9 | 2174.3 | 2249.7 | 2685.4 |
| dashboard,call:today,palier:1000 | 15048 | 141.5 | 63.4 | 479.7 | 500.6 | 916.8 |
| dashboard,call:today,palier:1400 | 19733 | 657.2 | 75.5 | 2103.4 | 2121.1 | 60001.1 |
| dashboard,call:today,palier:1996 | 24451 | 2224.3 | 2111.0 | 2180.9 | 4040.8 | 4220.4 |
| dashboard,call:today,palier:200 | 3184 | 132.1 | 59.8 | 470.5 | 490.8 | 793.8 |
| dashboard,call:today,palier:400 | 6388 | 136.6 | 61.5 | 475.4 | 495.6 | 624.0 |
| dashboard,call:today,palier:700 | 10710 | 140.0 | 62.1 | 477.3 | 497.2 | 788.2 |
| dashboard,call:today,palier:transition | 2803 | 821.1 | 495.6 | 2204.3 | 2295.5 | 4119.1 |
| dashboard,palier:1000 | 60192 | 157.5 | 63.5 | 455.3 | 525.1 | 1497.9 |
| dashboard,palier:1400 | 78932 | 709.9 | 75.6 | 2083.8 | 2107.4 | 60001.4 |
| dashboard,palier:1996 | 97804 | 1692.0 | 2092.5 | 2159.9 | 2245.1 | 4346.8 |
| dashboard,palier:200 | 12736 | 150.1 | 59.7 | 444.7 | 509.3 | 1458.0 |
| dashboard,palier:400 | 25552 | 153.0 | 61.5 | 449.0 | 512.7 | 1530.8 |
| dashboard,palier:700 | 42840 | 155.1 | 62.2 | 450.8 | 517.0 | 1501.5 |
| dashboard,palier:transition | 11212 | 610.5 | 170.0 | 2159.1 | 2250.1 | 4335.7 |
| mark_read | 72634 | 71.3 | 58.0 | 112.5 | 146.7 | 1728.4 |
| mark_read,palier:1000 | 12060 | 49.7 | 37.9 | 79.7 | 85.6 | 183.7 |
| mark_read,palier:1400 | 15733 | 61.5 | 52.2 | 95.6 | 110.8 | 376.2 |
| mark_read,palier:1996 | 19596 | 87.7 | 79.6 | 145.2 | 172.2 | 653.4 |
| mark_read,palier:200 | 2553 | 44.3 | 31.3 | 73.0 | 75.5 | 94.2 |
| mark_read,palier:400 | 5153 | 46.3 | 33.7 | 75.6 | 78.5 | 110.9 |
| mark_read,palier:700 | 8579 | 47.3 | 35.1 | 76.6 | 81.3 | 213.2 |
| mark_read,palier:transition | 1934 | 105.3 | 75.8 | 230.5 | 300.5 | 690.9 |
| patient_docs | 293308 | 76.7 | 54.9 | 140.8 | 195.2 | 21037.3 |
| patient_docs,palier:1000 | 49130 | 45.6 | 44.7 | 73.0 | 83.8 | 191.1 |
| patient_docs,palier:1400 | 62240 | 63.1 | 56.9 | 107.4 | 128.8 | 487.2 |
| patient_docs,palier:1996 | 79940 | 108.0 | 88.5 | 199.9 | 249.5 | 21037.3 |
| patient_docs,palier:200 | 10254 | 38.1 | 38.8 | 59.1 | 65.3 | 124.9 |
| patient_docs,palier:400 | 20587 | 41.1 | 41.6 | 63.4 | 70.8 | 145.7 |
| patient_docs,palier:700 | 34331 | 42.9 | 42.6 | 67.6 | 76.8 | 228.9 |
| patient_docs,palier:transition | 7787 | 112.7 | 74.0 | 259.6 | 351.5 | 793.9 |
| patient_dossier | 20290 | 81.9 | 58.8 | 144.5 | 193.7 | 2021.0 |
| patient_dossier,palier:1000 | 3378 | 50.3 | 47.4 | 76.2 | 86.3 | 195.5 |
| patient_dossier,palier:1400 | 4359 | 68.7 | 61.2 | 111.4 | 133.6 | 461.2 |
| patient_dossier,palier:1996 | 5512 | 111.2 | 96.7 | 192.6 | 231.1 | 660.2 |
| patient_dossier,palier:200 | 708 | 41.5 | 40.0 | 60.4 | 65.8 | 127.9 |
| patient_dossier,palier:400 | 1418 | 44.6 | 43.6 | 64.7 | 72.7 | 156.2 |
| patient_dossier,palier:700 | 2401 | 46.0 | 43.9 | 68.4 | 78.0 | 167.5 |
| patient_dossier,palier:transition | 538 | 127.4 | 80.9 | 287.0 | 362.4 | 681.9 |
| patient_opposition | 20290 | 73.4 | 63.2 | 87.7 | 104.1 | 1545.9 |
| patient_opposition,palier:1000 | 3377 | 61.9 | 61.1 | 67.8 | 71.8 | 133.1 |
| patient_opposition,palier:1400 | 4359 | 67.3 | 64.9 | 81.5 | 88.5 | 249.5 |
| patient_opposition,palier:1996 | 5510 | 77.1 | 74.9 | 103.2 | 118.0 | 283.0 |
| patient_opposition,palier:200 | 708 | 58.1 | 58.1 | 61.7 | 63.8 | 84.9 |
| patient_opposition,palier:400 | 1419 | 60.1 | 59.6 | 64.2 | 66.6 | 94.4 |
| patient_opposition,palier:700 | 2402 | 60.8 | 60.0 | 65.7 | 69.6 | 111.3 |
| patient_opposition,palier:transition | 538 | 92.1 | 70.4 | 152.0 | 217.5 | 468.9 |
| patient_search | 27004 | 61.8 | 59.8 | 85.5 | 102.5 | 1643.9 |
| patient_search,palier:1000 | 4439 | 49.1 | 59.5 | 67.2 | 70.9 | 131.6 |
| patient_search,palier:1400 | 5796 | 54.8 | 62.2 | 78.1 | 85.3 | 247.1 |
| patient_search,palier:1996 | 7378 | 67.1 | 67.7 | 100.7 | 115.5 | 447.8 |
| patient_search,palier:200 | 931 | 45.5 | 57.3 | 62.5 | 63.5 | 82.0 |
| patient_search,palier:400 | 1899 | 47.3 | 59.0 | 63.5 | 65.0 | 100.9 |
| patient_search,palier:700 | 3186 | 48.1 | 59.1 | 64.3 | 67.8 | 143.5 |
| patient_search,palier:transition | 739 | 83.9 | 67.6 | 151.1 | 226.0 | 595.0 |
| read_content | 91036 | 189.6 | 44.7 | 157.6 | 2085.0 | 15135.2 |
| read_content,palier:1000 | 15044 | 39.4 | 37.0 | 51.9 | 59.8 | 158.9 |
| read_content,palier:1400 | 19639 | 129.0 | 47.8 | 91.4 | 137.3 | 15135.2 |
| read_content,palier:1996 | 24408 | 437.5 | 87.8 | 2107.4 | 2131.0 | 2528.9 |
| read_content,palier:200 | 3181 | 31.8 | 31.4 | 38.2 | 41.2 | 80.3 |
| read_content,palier:400 | 6399 | 35.2 | 34.3 | 42.1 | 46.4 | 93.0 |
| read_content,palier:700 | 10708 | 36.4 | 34.9 | 46.2 | 52.2 | 131.5 |
| read_content,palier:transition | 2843 | 238.8 | 62.2 | 325.2 | 2101.4 | 2679.6 |
| read_content_cold | 36315 | 1370.1 | 487.6 | 2120.2 | 2148.3 | 60001.4 |
| read_content_cold,palier:1000 | 6032 | 453.8 | 452.5 | 502.5 | 515.9 | 606.5 |
| read_content_cold,palier:1400 | 7800 | 2222.9 | 477.6 | 2089.1 | 2110.7 | 60001.4 |
| read_content_cold,palier:1996 | 9879 | 2102.1 | 2097.0 | 2149.8 | 2173.2 | 2515.5 |
| read_content_cold,palier:200 | 1278 | 450.1 | 448.4 | 492.8 | 505.4 | 561.4 |
| read_content_cold,palier:400 | 2596 | 450.6 | 449.3 | 499.5 | 514.4 | 568.9 |
| read_content_cold,palier:700 | 4282 | 450.0 | 448.8 | 498.0 | 512.8 | 611.2 |
| read_content_cold,palier:transition | 917 | 1326.9 | 2044.2 | 2176.8 | 2251.9 | 2630.4 |
| read_list | 182072 | 442.4 | 57.6 | 2071.0 | 2093.5 | 60001.6 |
| read_list,call:emails,palier:1000 | 15042 | 54.1 | 51.2 | 69.1 | 77.5 | 180.3 |
| read_list,call:emails,palier:1400 | 19647 | 75.3 | 66.1 | 110.3 | 135.2 | 450.0 |
| read_list,call:emails,palier:1996 | 24453 | 123.7 | 108.5 | 202.3 | 240.7 | 769.5 |
| read_list,call:emails,palier:200 | 3181 | 41.6 | 41.0 | 49.0 | 52.5 | 82.9 |
| read_list,call:emails,palier:400 | 6390 | 46.7 | 45.4 | 55.3 | 59.4 | 122.6 |
| read_list,call:emails,palier:700 | 10702 | 48.9 | 46.7 | 60.9 | 67.6 | 174.8 |
| read_list,call:emails,palier:transition | 2929 | 139.9 | 85.9 | 323.3 | 402.5 | 898.6 |
| read_list,call:folder,palier:1000 | 15042 | 35.3 | 20.2 | 39.4 | 123.9 | 589.3 |
| read_list,call:folder,palier:1400 | 19647 | 505.3 | 29.5 | 2058.9 | 2069.1 | 60001.6 |
| read_list,call:folder,palier:1996 | 24453 | 2084.4 | 2076.5 | 2124.0 | 2145.0 | 2487.5 |
| read_list,call:folder,palier:200 | 3181 | 29.0 | 17.5 | 23.5 | 111.7 | 497.7 |
| read_list,call:folder,palier:400 | 6390 | 32.0 | 18.9 | 27.6 | 117.4 | 489.8 |
| read_list,call:folder,palier:700 | 10702 | 33.7 | 19.1 | 33.0 | 119.8 | 484.5 |
| read_list,call:folder,palier:transition | 2929 | 747.2 | 54.3 | 2143.9 | 2234.3 | 2658.3 |
| read_list,palier:1000 | 30084 | 44.7 | 41.9 | 66.9 | 88.5 | 589.3 |
| read_list,palier:1400 | 39294 | 290.3 | 57.6 | 523.8 | 2058.9 | 60001.6 |
| read_list,palier:1996 | 48906 | 1104.0 | 1399.0 | 2104.0 | 2124.0 | 2487.5 |
| read_list,palier:200 | 6362 | 35.3 | 34.1 | 47.8 | 54.5 | 497.7 |
| read_list,palier:400 | 12780 | 39.3 | 38.8 | 53.8 | 62.8 | 489.8 |
| read_list,palier:700 | 21404 | 41.3 | 38.5 | 59.1 | 76.4 | 484.5 |
| read_list,palier:transition | 5858 | 443.5 | 80.5 | 2070.5 | 2143.9 | 2658.3 |
| search | 27363 | 457.7 | 397.5 | 603.2 | 839.6 | 3073.8 |
| search,palier:1000 | 4556 | 411.0 | 363.2 | 497.3 | 629.9 | 1580.0 |
| search,palier:1400 | 5955 | 446.6 | 395.9 | 555.2 | 731.0 | 1651.6 |
| search,palier:1996 | 7520 | 503.4 | 451.4 | 646.0 | 828.2 | 1845.6 |
| search,palier:200 | 955 | 403.6 | 353.2 | 485.9 | 607.6 | 1548.1 |
| search,palier:400 | 1888 | 396.5 | 355.5 | 474.4 | 579.3 | 1569.6 |
| search,palier:700 | 3213 | 407.6 | 358.8 | 484.9 | 634.2 | 1652.7 |
| search,palier:transition | 731 | 521.3 | 440.4 | 774.9 | 996.1 | 1751.7 |
| send | 26427 | 1675.6 | 876.4 | 2133.4 | 2185.7 | 67866.2 |
| send,palier:1000 | 4535 | 624.7 | 481.5 | 903.0 | 926.7 | 1053.1 |
| send,palier:1400 | 5897 | 3153.3 | 835.9 | 2097.2 | 21058.4 | 67866.2 |
| send,palier:1996 | 7257 | 2106.1 | 2099.4 | 2170.0 | 2205.9 | 2908.9 |
| send,palier:200 | 938 | 651.9 | 777.2 | 903.5 | 920.7 | 1038.2 |
| send,palier:400 | 1887 | 631.0 | 484.4 | 895.3 | 919.0 | 993.9 |
| send,palier:700 | 3184 | 625.8 | 481.1 | 897.0 | 917.5 | 1079.1 |
| send,palier:transition | 756 | 1431.4 | 2049.8 | 2216.6 | 2301.5 | 2690.7 |
| treatment | 22835 | 749.1 | 99.3 | 2114.2 | 2139.0 | 68057.6 |
| treatment,palier:1000 | 3768 | 193.9 | 85.0 | 729.7 | 790.0 | 1269.6 |
| treatment,palier:1400 | 4902 | 993.8 | 138.1 | 2064.6 | 2102.7 | 68057.6 |
| treatment,palier:1996 | 6128 | 1489.1 | 2087.1 | 2149.3 | 2171.9 | 2427.9 |
| treatment,palier:200 | 790 | 72.1 | 78.3 | 86.1 | 88.4 | 98.6 |
| treatment,palier:400 | 1587 | 76.9 | 80.3 | 89.4 | 93.2 | 2665.0 |
| treatment,palier:700 | 2749 | 97.2 | 80.8 | 95.5 | 107.2 | 2649.2 |
| treatment,palier:transition | 695 | 726.9 | 127.2 | 2129.6 | 2217.6 | 2618.9 |
| warmup | 21956 | 482.6 | 183.4 | 1106.2 | 2067.2 | 11308.6 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-05T15:58:30.091000+00:00 → 2026-11-05T17:50:11.090000+00:00 (6701 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t422.csv`) | ✅ 203277 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-24784` | 1.18 | 10 | 45 | 0.035 | 349.27 |
| `DESKTOP-DEV-X2C-27324` | 1.22 | 8 | 47 | 0.030 | 385.22 |
| `DESKTOP-DEV-X2C-38224` | 1.49 | 5 | 40 | 0.038 | 447.28 |
| `DESKTOP-DEV-X2C-48408` | 1.35 | 12 | 38 | 0.030 | 415.61 |
| `DESKTOP-DEV-X2C-61512` | 1.29 | 13 | 44 | 0.032 | 437.62 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 0.91 | 4.29 | 1712 |
| `com.docker.backend#34124` | 0.00 | 0.14 | 39 |
| `dcp#24856` | 0.00 | 0.09 | 12 |
| `dcp#27728` | 0.00 | 0.14 | 52 |
| `dcp#39444` | 0.00 | 0.04 | 12 |
| `dcp#41012` | 0.00 | 0.04 | 14 |
| `dcp#47980` | 0.00 | 0.24 | 13 |
| `dcp#48288` | 0.00 | 0.09 | 12 |
| `dcp#53012` | 0.00 | 0.14 | 14 |
| `dcp#53860` | 0.00 | 0.04 | 12 |
| `dcp#54096` | 0.41 | 1.77 | 2939 |
| `dcp#54612` | 0.00 | 0.09 | 12 |
| `dcp#55756` | 0.00 | 0.04 | 12 |
| `dcp#56732` | 0.00 | 0.00 | 12 |
| `dcp#59036` | 0.00 | 0.04 | 14 |
| `dcp#60064` | 0.00 | 0.00 | 12 |
| `dcp#9040` | 0.00 | 0.00 | 11 |
| `k6#2945` | 0.48 | 1.63 | 3009 |
| `mss.mail.api#24784` | 0.45 | 3.13 | 2238 |
| `mss.mail.api#27324` | 0.45 | 3.13 | 2209 |
| `mss.mail.api#38224` | 0.46 | 3.06 | 2324 |
| `mss.mail.api#48408` | 0.45 | 3.00 | 2241 |
| `mss.mail.api#61512` | 0.48 | 3.03 | 2263 |
| `mss.mail.e2e#46376` | 0.00 | 0.23 | 34 |
| `vmmemWSL#36464` | 3.80 | 12.03 | 60672 |
| `loadtest-otel-collector-hgzuypcd` | 0.02 | 0.21 | 117 |
| `loadtest-pgbouncer-vjsyjhdx` | 0.26 | 0.88 | 50 |
| `mss-mail-flagsmith-app-b6152948` | 0.09 | 0.39 | 560 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.17 | 185 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.22 | 169 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.24 | 240 |
| `mss-mail-rabbitmq-pajqdmxy` | 0.01 | 0.09 | 169 |
| `mss-mail-redis-b6152948` | 0.15 | 1.30 | 807 |
| `mss-mail-rediscommander-yrypsruc` | 0.00 | 0.20 | 35 |
| `mss-mail-seq-b6152948` | 0.07 | 4.25 | 1516 |
| `postgres-pgvector` | 1.51 | 8.33 | 30822 |

- **Hôte** : CPU 47.5 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 52
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 8494, cl_waiting max 13, cl_waiting_maintenance max 13, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 163, maxwait_ms max 163, maxwait_practitioner_ms max 0, sv_active max 34, sv_idle max 1648, sv_login max 1
- **Backends Postgres** : audit max 5, cache_mb max 39844, direct max 30, idle_over_60s max 467, majfault_per_s max 89, pooler max 1997, practitioner_databases max 1988, provision max 5, rss_mb max 6284, started_last_60s max 273, total max 2029, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 4610.7 | 1337 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 60000.0 | 1338 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 60000.0 | 1334 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 1336 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 23109.1 | 1334 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 60000.0 | 1331 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 1922.1 | 1331 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 2046.1 | 1335 |
| `api/v{version:apiVersion}/Mail/sendmail` | 60000.0 | 1321 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1807.1 | 1331 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 2104.3 | 1331 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 1822.8 | 1331 |
| `api/v{version:apiVersion}/Search/semantic` | 2291.5 | 1331 |
| `api/v{version:apiVersion}/Sync/coverage` | 1699.6 | 1335 |

- **p95 client global (k6)** : 2116.8 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -57883.2 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 6.49 |
| Documents CDA /s | 6.49 |
| Durée traitement CDA (s, p95) | 0.70 |
| Événements de session IMAP /s | 34.73 |
| Recherches (s, p95) | 1.795 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 34.4 | 228 | 0.0 (0.0 %), p95 5 | 20.7 (60.3 %), p95 161 | 13.6 (39.6 %), p95 71 |
| `GetMail` | 11.0 | 31.5 | 364 | 2.7 (8.6 %), p95 65 | 25.8 (82.1 %), p95 263 | 2.9 (9.3 %), p95 205 |
| `GetMailsByUids` | 14.8 | 36.4 | 442 | 0.1 (0.3 %), p95 18 | 28.7 (79.0 %), p95 422 | 7.5 (20.7 %), p95 45 |

- **`EnrichPersistMail`** — sur 34.4 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 20.7 ms exécution SQL, 13.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 31.5 ms en moyenne (11.0 requête(s) SQL par appel) : 2.7 ms attente d'une connexion, 25.8 ms exécution SQL, 2.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 36.4 ms en moyenne (14.8 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 28.7 ms exécution SQL, 7.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 2.9 | 272.0 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 227.0 | 7.5 | 33.2 | 20.5 | 31.3 | 20.5 | 33.4 | 20.5 | 0.0 | 20.5 | 6.5 | 0.0 | 20.4 | 49.0 | 4.3 |

- **`GetMail`** — sur 2.9 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **272.0 µs**.

- **`GetMailsByUids`** — sur 7.5 ms de matérialisation, l'appel a construit 227.0 objets, dont 20.5 messages, 31.3 étiquettes, 20.5 destinataires, 33.4 pièces jointes, 20.5 identifiants enrichis, 0.0 acquittements, 20.5 documents médicaux, 6.5 résultats de biologie, 0.0 éléments de synthèse, 20.4 corps de messages, 49.0 objets de fil, 4.3 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **33.2 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **6666.9 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 2.8 | 231.1 | 2275 | 146.8 (63.5 %), p95 981 | 6.6 (2.8 %), p95 98 | 25.4 (11.0 %), p95 700 | 27.8 (12.0 %), p95 204 | 24.5 (10.6 %), p95 111 |

- **Enrichir un message** — sur 231.1 ms en moyenne (2.8 message(s) par requête) : 146.8 ms fetch IMAP, 6.6 ms extraction XDM, 25.4 ms parsing CDA, 27.8 ms écritures base, 24.5 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `fetch_bodystructure`, inf `open_folder`, inf `resolve_folder`, 0.98 `fetch_whole_message`, 0.49 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 253.7 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 1182.7 | 1890 | 0.0 (0.0 %), p95 5 | 13.5 (1.1 %), p95 36 | 762.9 (64.5 %), p95 1492 | 315.2 (26.7 %), p95 390 | 793.9 (67.1 %), p95 1549 | 87.1 (7.4 %), p95 456 |

- **Envoyer un message** — sur 1182.7 ms en moyenne : 0.0 ms garde d'opposition, 13.5 ms construction MIME, 762.9 ms obtention de session SMTP, 315.2 ms transmission + acquittement, 793.9 ms archivage Sent, 87.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 57.886 | ≥ 60 ⚠️ | 161.67 |
| `smtp_session` | 51.443 | ≥ 60 ⚠️ | 8.69 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 7.25 |
| `EnrichEmails` | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 7.503 | ≥ 60 ⚠️ | 9.73 |
| `GetAttachmentStream` | ≥ 60 ⚠️ | ≥ 60 ⚠️ | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 10.04 |
| `GetEmailContent` | 57.164 | 58.618 | 9.879 | 58.688 | 16.58 |
| `GetFolders` | 0.006 | 58.500 | 9.125 | 58.500 | 30.51 |
| `ReadFolder` | 54.947 | 57.970 | 54.450 | 58.861 | 55.31 |
| `ReadToday` | 1.885 | 58.500 | 19.945 | 58.500 | 27.87 |
| `UpdateFlag` | 59.000 | ≥ 60 ⚠️ | 9.549 | ≥ 60 ⚠️ | 22.31 |

> ⚠️ **Repliement impossible : la phase `operate` n'est pas mesurée sur la fenêtre de régime.** Les chiffres ci-dessus restent toutes fenêtres. Ce n'est pas « aucune détention » — c'est « aucune mesure » (task-214).

| Voie | Acquisitions /s |
|---|---|
| `read` | 161.67 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

🚨 **Détention d'EXPLOITATION saturée** pour `AppendToSent`, `EnrichEmails`, `GetAttachmentStream`, `UpdateFlag` — et celle-là ne s'explique pas par la chauffe. Le verrou de session est tenu ≥ 60 s hors établissement : c'est sa **portée** qu'il faut discuter, et les buckets ne suffisent plus à la mesurer (borne haute à 60 s).

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 60.000 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| conteneur `postgres-pgvector` (CPU) | 8.33 cœurs | 24 cœurs | 34.7 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 4.25 cœurs | 24 cœurs | 17.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#24784` (CPU) | 3.13 cœurs | 24 cœurs | 13.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#27324` (CPU) | 3.13 cœurs | 24 cœurs | 13.0 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-61512` | 13.00 éléments | 100 éléments | 13.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#38224` (CPU) | 3.06 cœurs | 24 cœurs | 12.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#61512` (CPU) | 3.03 cœurs | 24 cœurs | 12.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#48408` (CPU) | 3.00 cœurs | 24 cœurs | 12.5 % | 0.0 % — transitoire |

> ⚠️ **Désignée par un palier, écartée par la moyenne du tir.** Le verdict ci-dessus est rendu sur la fenêtre ENTIÈRE, qui mélange des populations différentes. Les ressources suivantes sont durablement présentes à un palier et diluées sur le tir — **c'est le palier qui décide d'une conclusion de capacité**, pas la moyenne des paliers.

| Ressource | Palier qui la désigne | Présence à ce palier | Présence sur le tir entier |
|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 1996 médecins | 42.9 % des échantillons du palier | 14.5 % — sous le seuil de 25 % |

**Ressource épinglée au palier 1996 médecins : PgBouncer — clients en attente (`cl_waiting`)** — présente sur 42.9 % des échantillons de CE palier (14.5 % sur le tir entier, sous le seuil de 25 %). Le tir entier ne l'épingle donc pas, et c'est une propriété de la statistique, pas du système : conclure sur la moyenne des paliers reviendrait à certifier la population la plus haute avec les mesures de la plus basse.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 9 931 479

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 117 842 |
| OpenAI | gpt-4o-mini | prompt | 9 813 637 |
| OpenAI | text-embedding-3-small | embedding | 12 814 216 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 5 195 | 0 (0.0 %) | 0 | 46.5 | 1.11 | 0.96 | 2.46 |
| étiquetage (chat) | OpenAI | 5 195 | 0 (0.0 %) | 0 | 46.5 | 1.06 | 0.91 | 2.46 |
| embedding | OpenAI | 5 195 | 0 (0.0 %) | 0 | 46.5 | 0.54 | 0.43 | 1.55 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 14 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 4.7 | 28.0 |
| GPU — VRAM occupée (Mo) | 2 633 | 2 894 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **112.3 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **3 899.0** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.18** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **6.4 ms** | sur 1 241 929 requêtes HTTP k6 |
| Taux de cache (blocs) | **97.93 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **6.69 Mo/s (856 blocs/s)** | attente disque : 9.0 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **358 240 / 23 143** | rapport 15.5 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **297.4** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.60 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **21 / 1** | blocs écrits par les backends eux-mêmes : 36 % |
| Sessions ouvertes / s | **1.68** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **2 447.2 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **910 / 2 029** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **55 / 100 %** | fautes majeures/s max : 89.0 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **106 évictions `pg_stat_statements`** pendant le tir (98 329 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

134 formes de requête, 26 651 900 appels, **60.5 min** de temps serveur cumulé — soit **2.9 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **24.1 %** | 24 % | 68 682 | 0.06 | 12.72 | 32.7 | 279 | 0 % | 0 | 1 292 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 2 | **22.7 %** | 47 % | 68 616 | 0.06 | 12.02 | 32.7 | 325 | 0 % | 0 | 1 290 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 3 | **7.2 %** | 54 % | 278 220 | 0.22 | 0.94 | 1.0 | 17 | 15 % | 0 | 1 805 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **4.8 %** | 59 % | 13 771 | 0.01 | 12.54 | 29.7 | 431 | 17 % | 0 | 829 | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 5 | **4.5 %** | 63 % | 3 694 373 | 2.97 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 6 | **4.2 %** | 67 % | 125 380 | 0.10 | 1.22 | 19.9 | 232 | 0 % | 0 | 1 995 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 7 | **3.8 %** | 71 % | 3 694 373 | 2.97 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 8 | **3.3 %** | 75 % | 9 000 970 | 7.25 | 0.01 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 9 | **2.9 %** | 77 % | 20 237 | 0.02 | 5.13 | 20.0 | 614 | 2 % | 0 | 977 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 10 | **2.5 %** | 80 % | 324 590 | 0.26 | 0.28 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 11 | **2.1 %** | 82 % | 20 256 | 0.02 | 3.71 | 20.0 | 616 | 2 % | 0 | 978 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 12 | **2.0 %** | 84 % | 272 686 | 0.22 | 0.26 | 1.0 | 8 | 2 % | 0 | 1 788 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 13 | **1.8 %** | 86 % | 1 241 852 | 1.00 | 0.05 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 14 | **1.4 %** | 87 % | 57 138 | 0.05 | 0.87 | 8.3 | 206 | 0 % | 0 | 1 131 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 15 | **0.9 %** | 88 % | 430 010 | 0.35 | 0.07 | 2.1 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 16 | **0.8 %** | 89 % | 154 122 | 0.12 | 0.19 | 18.0 | 5 | 0 % | 0 | 1 253 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **0.8 %** | 90 % | 429 997 | 0.35 | 0.07 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 18 | **0.5 %** | 90 % | 125 398 | 0.10 | 0.15 | 19.9 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 19 | **0.5 %** | 91 % | 70 437 | 0.06 | 0.26 | 27.0 | 5 | 0 % | 0 | 1 026 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **0.5 %** | 91 % | 296 201 | 0.24 | 0.06 | 3.3 | 8 | 0 % | 0 | 1 801 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 91.9 % | 59.5 % |
| INSERT | 3.9 % | 1.7 % |
| UPDATE | 0.7 % | 0.6 % |
| DELETE | 0.0 % | 0.2 % |
| AUTRE | 3.5 % | 38.0 % |
| bases : praticien (N bases) | 86.8 % | 64.9 % |
| bases : unique (1 base) | 13.2 % | 35.1 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **12.7** | 216 | 68 682 | 24.1 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailCo…` |
| **12.5** | 601 | 13 771 | 4.8 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **12.0** | 399 | 68 616 | 22.7 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMe…` |
| **5.1** | 489 | 20 237 | 2.9 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **3.7** | 482 | 20 256 | 2.1 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 2 252 | 492 989 | 578 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 3 554 | 410 663 | 0 | 5 | 0.1 Mo |
| `Mails` | 2 677 | 332 554 | 1 575 | 26 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 403 | 90 619 | 208 | 43 | 29.9 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 473 | 62 984 | 2 981 | 157 | 8.0 Mo |
| `MailRecipients` | 376 | 52 134 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 189 | 26 586 | 6 541 | 26 | 1.9 Mo |
| `PendingActions` | 669 | 11 652 | 0 | 33 | 0.1 Mo |
| `Tags` | 294 | 5 292 | 251 | 0 | 0.0 Mo |
| `MailFolders` | 878 | 2 364 | 746 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🔴 | requête n°1 (24.1 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Postgres | 🟠 | taux de cache 97.9 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | 15 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailAttachments` balayée 403 fois (90619 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 473 fois (62984 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 189 fois (26586 lignes lues, 26 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°5 (4.5 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°8 (3.3 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Postgres | 🟡 | 36 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Schéma | 🟡 | requête n°9 (2.9 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-185032.tsv`, `pgserver-journey-debut-165817.tsv`, `pgserver-journey-fin-185036.tsv`, `pgtables-journey-debut-165822.tsv`, `pgtables-journey-fin-185040.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 234613 — dont **234613** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-escalier-1996-20261105-task422-pool1-185011.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
