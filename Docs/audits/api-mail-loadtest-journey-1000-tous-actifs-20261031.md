# Rapport de tir — journey-1000-20261031-tous-actifs-openai-sans-tag

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-20261031-tous-actifs-openai-sans-tag-152654.json`.

> **Qualification de l'analyste (2026-10-31).** Le rouge ci-dessous vient du seul seuil `journey_budget_exhausted` : **4 tirages** sur environ 61 600 tirages « traitement » et « lecture froide » ont trouvé leur réserve vide en toute fin de tir. Dans ce cas, le harnais **saute** l'étape (`scenarios/journey.js:910`, `:950`) ; il ne relit pas du déjà-ouvert. Le corpus n'a donc pas changé de forme, et aucune mesure n'est contaminée (0,006 % des tirages). **Le tir est jugé exploitable.**
> Le rouge applicatif réel est la **Recherche** (finding F1 : connexions IPv6 vers OpenAI, cause mesurée).
>
> Conditions particulières :
> - tout OpenAI, **étiquetage IA désactivé** par drapeau, vectorisation conservée. La partie bus et IA ne se compare donc pas aux tirs étiquetés ;
> - tireur k6bench, banc mail cluster ;
> - durée de 1 h 45 imposée par les réserves : 3 h refusées par le contrôle de budget ;
> - parcours postérieur aux journey 1000 de septembre. Les débits ne se comparent qu'étape par étape ;
> - c'est une **nouvelle référence « journey 1000 tous actifs »**.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- le stock de messages de test s'est épuisé pendant le tir : le corpus a changé de forme en cours de mesure, les chiffres ne se comparent plus

À instruire une fois le tir refait :
- à 1000 médecins, 1 étape(s) dépassent le temps de réponse attendu : « Recherche »
- 2 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 6 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.020 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 6330s — **Latence** : mssante
- **Requêtes** : 1280473 — **débit émergent global** : 201.1 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 93906 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 201.1 | **220.1** | 63.1 | **704.1** | — | 43920.7 | 0.02 | 100.0 | 0 | 0 | 145508/247 |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1000 médecins** | 6300 | 6055 | 1229409 | 203.04 | 0.02 | 4679.8 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 70 / 536 (n=365200) |
| 2 | Ouvrir / rafraîchir l'inbox | 49 / 131 (n=182636) |
| 3 | Ouvrir un message enrichi (servi base) | 46 / 104 (n=91348) |
| 4 | Ouvrir un message froid (fetch IMAP) | 466 / 539 (n=36484) |
| 5 | Recherche | 385 / 28346 (n=27347) |
| 6 | Envoi (acquittement UI) | 485 / 939 (n=27425) |
| 7 | Télécharger une PJ (~124 Ko) | 479 / 1018 (n=36510) |
| 8 | Marquer lu | 51 / 113 (n=73182) |
| 9 | Rechercher un patient | 62 / 87 (n=27319) |
| 10 | Ouvrir la page d'un dossier patient | 64 / 127 (n=41182) |
| 11 | Fiche patient complète (ressenti médecin) | 344 / 615 (n=20590) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 14.5 / 20 | 34.4 / 60 | 46108 | 615 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3948 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- ⚠️ **Réserve épuisée en cours de tir** (4 fois) — le corpus a changé de forme pendant la mesure : soit le traitement n'a plus alimenté le dossier, soit « ouvrir un message froid » a relu du déjà-ouvert. Tir à refaire sur une boîte plus grande ou une campagne plus courte.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 498 ms en moyenne, 1806 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 1445 / 1582 (magasin) |
| Backends Postgres (moy/max) | 1871 / 1985 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 |
| PgBouncer `cl_waiting` (échant. non nuls) | 62/1091 (6 %) |
| …dont bases **praticien** (échant. non nuls) | 0/1091 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 62/1091 (6 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 10.8 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 10.8 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 185 / 602 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1954 |
| Backends **directs** — audit + provisionnement (max) | 25 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 0 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 4 |
| RSS par réplica api-mail, Mo (moy/max) | 2027 / 2481 (5 réplicas) |

- à 1000 médecins : Backends Postgres au pic : **1985.0 / 2500** (79.4 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 100.0 %** des 1000 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⓘ Chauffe : **204 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 6300 s, soit **3 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+275 s] (4 % de la fenêtre) ; **régime [+275 s..+6330 s]** porte le verdict

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 70 (300) | 536 (1500) | 365200 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 49 (300) | 131 (1000) | 182636 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 46 (100) | 104 (500) | 91348 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 466 (800) | 539 (2500) | 36484 | ✅ |
| 5 | Recherche | 385 (500) | 28346 (2000) | 27347 | ❌ |
| 6 | Envoi (acquittement UI) | 485 (1000) | 939 (3000) | 27425 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 479 (500) | 1018 (2000) | 36510 | ✅ |
| 8 | Marquer lu | 51 (200) | 113 (1000) | 73182 | ✅ |
| 9 | Rechercher un patient | 62 (300) | 87 (1500) | 27319 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 64 (500) | 127 (2000) | 41182 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 344 (1500) | 615 (4000) | 20590 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Recherche (`search`) | 27347 | 3386 | 28346 | 92585.9 | 37.0 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 365200 | 168 | 536 | 61276.3 | 24.5 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 23054 | 828 | 1046 | 19077.8 | 7.6 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 36510 | 521 | 1018 | 19020.0 | 7.6 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 36484 | 469 | 539 | 17100.7 | 6.8 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 27425 | 623 | 939 | 17094.7 | 6.8 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 182636 | 58 | 131 | 10519.1 | 4.2 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 91348 | 55 | 104 | 4998.8 | 2.0 % |
| 🟢 | Marquer lu (`mark_read`) | 73182 | 61 | 113 | 4471.3 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 27319 | 56 | 87 | 1520.3 | 0.6 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 20592 | 67 | 89 | 1385.2 | 0.6 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 20590 | 65 | 127 | 1330.8 | 0.5 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 1 🔴 · 1 🟠 · 10 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Recherche** (`search`, 92585.9 s, 37.0 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (3386 ms)
  - **dispersion p95/p50 = 73.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Arrivée dashboard** (`dashboard`, 61276.3 s, 24.5 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 7.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

#### F1 — Recherche : la queue vient de l'ouverture des connexions vers OpenAI par IPv6 (cause mesurée, corrigée côté poste le 2026-10-31)

- **Symptôme (serveur, `mssante_search_duration_seconds`)** : p50 0,4 s, p90 11,6 s, p95 27,7 s, p99 53 s, max 55,6 s.
  - Environ 10 % des recherches dépassent 10 s, et 1 213 dépassent 30 s.
  - Le phénomène est uniforme sur les 5 réplicas et stable sur toute la fenêtre (~300 recherches > 10 s par tranche de 10 min).
- **Ce qui est écarté** :
  - le SQL : les requêtes vectorielles font 5 ms en moyenne, 84 ms au pire ; aucune requête du tir ne dépasse 286 ms ;
  - le mode dégradé : aucun avertissement `Search engine … unavailable` ;
  - le débit OpenAI : 122 939 appels, tous en 200, aucun 429 ;
  - le DNS : 5 955 résolutions, toutes < 0,5 s.
- **Cause** : `http_client_request_time_in_queue_seconds{server_address="api.openai.com"}` montre que 7 688 requêtes ont **attendu une connexion**, dont **3 875 plus de 10 s**. Ce nombre rejoint les 3 895 appels OpenAI > 10 s.
  - 1 487 connexions ont été ouvertes en 1 h 46. Elles se ferment au bout de 60 à 120 s d'inactivité, et `PooledConnectionLifetime` vaut 5 min.
  - `api.openai.com` publie 2 adresses IPv6 et 2 IPv4, et .NET tente l'IPv6 d'abord.
  - **Mesure directe : la connexion TCP IPv6 échoue au bout de 21 036 ms, l'IPv4 aboutit en 15 ms.** Une ou deux tentatives IPv6 avant l'IPv4 donnent 21 s ou 42 s, ce qui recoupe le p95 (28 s) et le p99 (53 s).
  - **Pourquoi l'IPv6 échouait — c'était le poste, pas le réseau** :
    - le ping IPv6 passait, et k6bench, derrière la même Freebox, joignait OpenAI en IPv6 en 20 ms ;
    - seul le **TCP IPv6 du poste** échouait, vers toutes les destinations ;
    - pare-feu et filtres WFP hors de cause.
    - Cause : l'option **« TCP Checksum Offload (IPv6) » de la carte Intel X520-1** (pilote 4.1.254.0). Une fois désactivée (2026-10-31, 16 h), le TCP IPv6 vers OpenAI aboutit en ~40 ms et l'API ouvre ses connexions OpenAI en IPv6 (`2a06:98c1:58::f3`).
- **Pourquoi la recherche plus que la vectorisation** (~10 % de recherches > 10 s contre ~1 % des embeddings de fond) : **non établi**. Hypothèse : la recherche, en rafales, tombe plus souvent sur une connexion à ouvrir. À vérifier par trace.
- **Banc ou produit ?**
  - Le défaut est celui de la **carte réseau du poste**.
  - Mais le client HTTP d'OpenAI n'a **ni délai de connexion** (`SocketsHttpHandler.ConnectTimeout` infini par défaut) **ni course IPv4/IPv6** (*Happy Eyeballs*). Un hôte de production avec un IPv6 cassé subirait exactement ce symptôme.
  - Le résultat du médecin attend une connexion qui n'aboutira jamais, au lieu de basculer vers le plein texte.
- **Remèdes** :
  1. **Banc** : ✅ **fait** — délégation du calcul TCP IPv6 désactivée sur la X520. À re-contrôler avant chaque tir (`curl.exe -6 https://api.openai.com`), car une mise à jour du pilote peut la réactiver. Les tirs antérieurs ont probablement subi la même queue sur tout appel OpenAI interactif.
  2. **Code** (`AddPooledClient`, `SemanticKernelExtensions.cs`) :
     - poser un `ConnectTimeout` court (2 à 5 s) ;
     - poser un `ConnectCallback` qui tente IPv4 et IPv6 en parallèle, ou préfère IPv4 ;
     - allonger `PooledConnectionIdleTimeout` pour garder des connexions chaudes.
  3. **Recherche** : donner à l'embedding de la requête un budget de temps propre (~2 s), au-delà duquel le mode hybride répond en plein texte, dégradé et signalé, comme le prévoit déjà task-338.
- **Gain attendu** : p95 de la recherche de ~28 s vers ~0,5 s (la médiane actuelle est à 0,4 s). La recherche pèse **37 % du temps serveur** de ce tir.
- **Décision humaine (2026-10-31) : pas de task produit.** En production, la connectivité réseau (IPv6, délais de connexion) relève de l'équipe infra. Les remèdes 2 et 3 ne sont pas retenus ; le remède 1 (banc) est appliqué.

#### F2 — Arrivée dashboard (🟠) : appel `folder`, latence IMAP

- 58 % du temps serveur de l'étape vient de l'appel `GET /mail/folders/{folder}` (p50 402 ms, p95 845 ms).
- La détention médiane du verrou `ReadFolder` est de 0,43 s, soit environ 4 à 5 allers-retours IMAP à 96 ms.
- C'est un coût de latence du lien, pas de CPU. L'étape est verte au SLO ; rien à faire en priorité.

#### F3 — Débit d'analyse : la constante de 9,5 mails/s n'est pas un plafond

- **Pendant le tir** : la demande a atteint **9,7 mails/s** (compteur `Mails traités /s`, max), et la file `add-new-mail-queue` a fini à 0. Le pipeline a donc suivi au-dessus de la constante.
- **Temps d'un enrichissement** : **230 ms par message**, dont 58 % de fetch IMAP, avec **2,91 allers-retours IMAP par message**.
  - Le coût est dominé par la latence, et sérialisé par session (verrou `imap_session`).
  - Le débit d'analyse croît donc avec le **nombre de sessions qui analysent en parallèle**, pas avec le CPU.
- **Chauffe du matin** : un lot de 10 mails prend 2,6 s en médiane avec 8 médecins simultanés, soit ~30 mails/s possibles. Or la chauffe est **cadencée** à 9,5 : le serveur n'a été occupé qu'environ un tiers du temps.
- **Suite** :
  - un tir dédié d'enrichissement sans délai de vague, à concurrence croissante (8, 16, 32, 64), pour tracer le débit selon la concurrence ;
  - puis le regroupement des allers-retours IMAP (`resolve_folder`, `open_folder`, `fetch_bodystructure` et `close_folder` comptent 1,91 aller-retour sur 2,91).

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 91300 | 402 | 845 | 35531.7 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 91300 | 69 | 511 | 13734.0 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 91300 | 33 | 202 | 5796.7 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 91300 | 65 | 91 | 6214.0 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 91318 | 25 | 134 | 3914.6 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 91318 | 62 | 128 | 6604.5 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (845 ms de p95, 402 ms de p50, n=91300), qui porte **aussi** le temps serveur de l'étape (35531.7 s, 58 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (134 ms de p95, 25 ms de p50, n=91318) ; le temps serveur total, lui, est porté par **`emails`** (6604.5 s, 63 % du temps ventilé). Les deux porteurs diffèrent : la queue et le volume ne se corrigent pas de la même façon.

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 37640 | 519.5 | 477.1 | 777.9 | 1018.3 | 1981.9 |
| attachment,palier:1000 | 36510 | 521.0 | 478.7 | 777.2 | 1017.8 | 1564.3 |
| attachment,palier:transition | 171 | 513.2 | 454.2 | 801.1 | 1013.7 | 1089.6 |
| dashboard | 377684 | 170.3 | 69.9 | 475.9 | 551.5 | 1638.2 |
| dashboard,call:coverage,palier:1000 | 91300 | 68.1 | 64.8 | 81.8 | 90.8 | 412.7 |
| dashboard,call:coverage,palier:transition | 210 | 147.4 | 91.7 | 277.5 | 344.2 | 585.6 |
| dashboard,call:folder,palier:1000 | 91300 | 389.2 | 401.9 | 776.1 | 845.0 | 1638.2 |
| dashboard,call:folder,palier:transition | 210 | 543.8 | 529.0 | 701.9 | 816.3 | 891.5 |
| dashboard,call:folders,palier:1000 | 91300 | 63.5 | 33.2 | 174.9 | 202.0 | 628.0 |
| dashboard,call:folders,palier:transition | 210 | 152.5 | 111.5 | 293.0 | 363.1 | 578.7 |
| dashboard,call:today,palier:1000 | 91300 | 150.4 | 68.6 | 490.0 | 511.4 | 1141.0 |
| dashboard,call:today,palier:transition | 210 | 564.3 | 550.4 | 751.9 | 844.9 | 999.2 |
| dashboard,palier:1000 | 365200 | 167.8 | 69.6 | 473.0 | 535.6 | 1638.2 |
| dashboard,palier:transition | 840 | 352.0 | 364.9 | 649.2 | 724.3 | 999.2 |
| mark_read | 75600 | 62.2 | 50.5 | 97.1 | 114.7 | 1020.2 |
| mark_read,palier:1000 | 73182 | 61.1 | 50.5 | 96.6 | 112.9 | 611.0 |
| mark_read,palier:transition | 328 | 49.1 | 35.7 | 81.9 | 92.7 | 146.9 |
| patient_docs | 306971 | 58.0 | 49.2 | 92.6 | 114.1 | 21055.3 |
| patient_docs,palier:1000 | 297722 | 57.0 | 49.2 | 92.0 | 112.3 | 21055.3 |
| patient_docs,palier:transition | 1454 | 44.8 | 41.6 | 72.9 | 89.5 | 157.3 |
| patient_dossier | 21220 | 65.5 | 56.5 | 105.1 | 128.7 | 998.0 |
| patient_dossier,palier:1000 | 20590 | 64.6 | 56.7 | 104.5 | 127.0 | 497.4 |
| patient_dossier,palier:transition | 100 | 53.4 | 45.7 | 81.3 | 111.5 | 172.5 |
| patient_opposition | 21220 | 67.9 | 64.3 | 80.8 | 90.0 | 903.4 |
| patient_opposition,palier:1000 | 20592 | 67.3 | 64.3 | 80.5 | 89.2 | 334.8 |
| patient_opposition,palier:transition | 100 | 62.5 | 59.7 | 71.5 | 80.9 | 116.1 |
| patient_search | 28141 | 56.4 | 61.9 | 78.9 | 87.7 | 872.0 |
| patient_search,palier:1000 | 27319 | 55.6 | 61.9 | 78.5 | 87.5 | 345.7 |
| patient_search,palier:transition | 132 | 47.5 | 58.5 | 64.4 | 66.7 | 87.4 |
| read_content | 94421 | 55.7 | 45.9 | 83.0 | 105.7 | 1027.9 |
| read_content,palier:1000 | 91348 | 54.7 | 45.9 | 82.3 | 103.6 | 709.8 |
| read_content,palier:transition | 348 | 41.8 | 38.0 | 57.1 | 69.8 | 132.8 |
| read_content_cold | 37685 | 469.4 | 465.8 | 522.1 | 539.9 | 1376.2 |
| read_content_cold,palier:1000 | 36484 | 468.7 | 465.9 | 521.7 | 538.8 | 771.8 |
| read_content_cold,palier:transition | 169 | 456.6 | 455.5 | 503.5 | 517.6 | 533.7 |
| read_list | 188842 | 58.8 | 48.7 | 101.5 | 133.8 | 1091.9 |
| read_list,call:emails,palier:1000 | 91318 | 72.3 | 62.4 | 104.9 | 128.0 | 867.0 |
| read_list,call:emails,palier:transition | 299 | 66.6 | 51.7 | 83.4 | 119.7 | 434.0 |
| read_list,call:folder,palier:1000 | 91318 | 42.9 | 24.6 | 72.8 | 134.2 | 707.4 |
| read_list,call:folder,palier:transition | 299 | 40.1 | 20.0 | 114.4 | 144.7 | 470.8 |
| read_list,palier:1000 | 182636 | 57.6 | 48.7 | 100.2 | 131.1 | 867.0 |
| read_list,palier:transition | 598 | 53.3 | 42.2 | 102.6 | 142.5 | 470.8 |
| search | 28220 | 3336.2 | 384.4 | 11757.3 | 28011.8 | 43920.7 |
| search,palier:1000 | 27347 | 3385.6 | 385.5 | 12211.5 | 28346.4 | 43920.7 |
| search,palier:transition | 105 | 3408.4 | 377.0 | 580.7 | 30949.9 | 40087.9 |
| send | 27993 | 627.0 | 487.1 | 914.9 | 940.8 | 1659.5 |
| send,palier:1000 | 27425 | 623.3 | 484.8 | 913.9 | 939.2 | 1222.7 |
| send,palier:transition | 139 | 597.8 | 464.9 | 898.1 | 921.2 | 979.1 |
| treatment | 23822 | 828.9 | 810.4 | 961.5 | 1052.2 | 2268.8 |
| treatment,palier:1000 | 23054 | 827.5 | 810.4 | 958.9 | 1046.0 | 2201.7 |
| treatment,palier:transition | 90 | 784.5 | 776.2 | 891.1 | 908.4 | 986.3 |
| warmup | 11000 | 498.0 | 446.4 | 898.6 | 1072.8 | 1805.8 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-10-31T12:40:46.441000+00:00 → 2026-10-31T14:26:54.968000+00:00 (6369 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-134006.csv`) | ✅ 174859 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-13004` | 0.92 | 3 | 19 | 0.034 | 8.60 |
| `DESKTOP-DEV-X2C-29356` | 0.89 | 4 | 22 | 0.032 | 7.65 |
| `DESKTOP-DEV-X2C-51560` | 0.91 | 11 | 18 | 0.032 | 8.11 |
| `DESKTOP-DEV-X2C-51676` | 0.91 | 9 | 22 | 0.031 | 8.22 |
| `DESKTOP-DEV-X2C-67224` | 0.85 | 9 | 17 | 0.032 | 8.18 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#35984` | 1.33 | 4.13 | 1723 |
| `com.docker.backend#7260` | 0.00 | 0.15 | 39 |
| `dcp#14012` | 0.00 | 0.05 | 15 |
| `dcp#16988` | 0.00 | 0.00 | 12 |
| `dcp#19976` | 0.62 | 3.18 | 2329 |
| `dcp#22728` | 0.00 | 0.09 | 14 |
| `dcp#27428` | 0.00 | 0.04 | 11 |
| `dcp#28696` | 0.00 | 0.14 | 51 |
| `dcp#29792` | 0.00 | 0.00 | 11 |
| `dcp#44476` | 0.00 | 0.09 | 12 |
| `dcp#44656` | 0.00 | 0.24 | 15 |
| `dcp#55696` | 0.00 | 0.00 | 11 |
| `dcp#56460` | 0.00 | 0.00 | 11 |
| `dcp#61432` | 0.00 | 0.00 | 11 |
| `dcp#68636` | 0.00 | 0.10 | 15 |
| `dcp#7084` | 0.00 | 0.05 | 11 |
| `k6#282729` | 0.73 | 1.37 | 1781 |
| `mss.mail.api#13004` | 0.65 | 3.73 | 2425 |
| `mss.mail.api#29356` | 0.62 | 3.23 | 2427 |
| `mss.mail.api#51560` | 0.64 | 2.83 | 2264 |
| `mss.mail.api#51676` | 0.64 | 3.21 | 2481 |
| `mss.mail.api#67224` | 0.63 | 2.96 | 2387 |
| `vmmemWSL#14992` | 5.13 | 13.02 | 60149 |
| `loadtest-otel-collector-fqgcdggm` | 0.03 | 0.21 | 111 |
| `loadtest-pgbouncer-ravkcurj` | 0.33 | 0.79 | 40 |
| `mss-mail-flagsmith-app-b6152948` | 0.11 | 0.39 | 570 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.17 | 243 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.19 | 176 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.45 | 256 |
| `mss-mail-rabbitmq-fhabqyzk` | 0.05 | 0.36 | 166 |
| `mss-mail-redis-b6152948` | 0.20 | 1.26 | 486 |
| `mss-mail-rediscommander-dajcgecw` | 0.00 | 0.25 | 42 |
| `mss-mail-seq-b6152948` | 0.13 | 9.28 | 1678 |
| `postgres-pgvector` | 1.96 | 7.10 | 26624 |

- **Hôte** : CPU 59.9 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 45
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 7150, cl_waiting max 4, cl_waiting_maintenance max 4, cl_waiting_practitioner max 0, count max 1001, login_retry_delta max 0, maxwait_maintenance_ms max 11, maxwait_ms max 11, maxwait_practitioner_ms max 0, sv_active max 21, sv_idle max 1383, sv_login max 1
- **Backends Postgres** : audit max 5, cache_mb max 40069, direct max 25, idle_over_60s max 388, majfault_per_s max 4, pooler max 1954, practitioner_databases max 1952, provision max 0, rss_mb max 6099, started_last_60s max 602, total max 1985, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 2343.5 | 1271 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2425.0 | 1273 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 634.5 | 1269 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2105.3 | 1271 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 927.8 | 1271 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 1862.5 | 1268 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 640.5 | 1267 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 697.8 | 1270 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2197.2 | 1256 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 595.0 | 1267 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 610.4 | 1267 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 430.2 | 1267 |
| `api/v{version:apiVersion}/Search/semantic` | 55636.4 | 1260 |
| `api/v{version:apiVersion}/Sync/coverage` | 609.9 | 1271 |

- **p95 client global (k6)** : 704.1 ms
- **p95 serveur le plus élevé** : 55636.4 ms
- **Écart** : -54932.3 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 9.71 |
| Documents CDA /s | 9.66 |
| Durée traitement CDA (s, p95) | 0.08 |
| Événements de session IMAP /s | 2.56 |
| Recherches (s, p95) | 55.636 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.0 | 32.5 | 198 | 0.0 (0.1 %), p95 5 | 19.6 (60.4 %), p95 113 | 12.8 (39.5 %), p95 65 |
| `GetMail` | 11.0 | 28.1 | 202 | 1.8 (6.3 %), p95 24 | 23.0 (81.9 %), p95 187 | 3.3 (11.8 %), p95 8 |
| `GetMailsByUids` | 14.8 | 41.5 | 399 | 0.1 (0.2 %), p95 5 | 33.4 (80.5 %), p95 351 | 8.0 (19.2 %), p95 46 |

- **`EnrichPersistMail`** — sur 32.5 ms en moyenne (7.0 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 19.6 ms exécution SQL, 12.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 28.1 ms en moyenne (11.0 requête(s) SQL par appel) : 1.8 ms attente d'une connexion, 23.0 ms exécution SQL, 3.3 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 41.5 ms en moyenne (14.8 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 33.4 ms exécution SQL, 8.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.3 | 3.3 | 319.8 | 0.9 | 0.9 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 255.6 | 8.0 | 31.2 | 24.3 | 24.3 | 24.3 | 39.5 | 24.3 | 0.0 | 24.3 | 7.5 | 0.0 | 24.1 | 58.3 | 4.8 |

- **`GetMail`** — sur 3.3 ms de matérialisation, l'appel a construit 10.3 objets, dont 0.9 messages, 0.9 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **319.8 µs**.

- **`GetMailsByUids`** — sur 8.0 ms de matérialisation, l'appel a construit 255.6 objets, dont 24.3 messages, 24.3 étiquettes, 24.3 destinataires, 39.5 pièces jointes, 24.3 identifiants enrichis, 0.0 acquittements, 24.3 documents médicaux, 7.5 résultats de biologie, 0.0 éléments de synthèse, 24.1 corps de messages, 58.3 objets de fil, 4.8 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **31.2 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **7082.6 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 2.3 | 229.7 | 486 | 133.4 (58.1 %), p95 246 | 24.3 (10.6 %), p95 64 | 15.9 (6.9 %), p95 74 | 30.0 (13.1 %), p95 168 | 26.1 (11.3 %), p95 125 |

- **Enrichir un message** — sur 229.7 ms en moyenne (2.3 message(s) par requête) : 133.4 ms fetch IMAP, 24.3 ms extraction XDM, 15.9 ms parsing CDA, 30.0 ms écritures base, 26.1 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **2.91 aller(s)-retour(s) IMAP par message enrichi** — 1.00 `fetch_whole_message`, 0.50 `resolve_folder`, 0.50 `fetch_bodystructure`, 0.50 `close_folder`, 0.41 `open_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 979.8 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 596.1 | 970 | 0.0 (0.0 %), p95 5 | 13.8 (2.3 %), p95 39 | 186.2 (31.2 %), p95 472 | 395.9 (66.4 %), p95 488 | 423.4 (71.0 %), p95 1041 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 596.1 ms en moyenne : 0.0 ms garde d'opposition, 13.8 ms construction MIME, 186.2 ms obtention de session SMTP, 395.9 ms transmission + acquittement, 423.4 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.024 | 0.737 | 0.15 |
| `imap_session` | 0.435 | 2.425 | 70.08 |
| `in_process_fetch` | 0.005 | 0.737 | 0.15 |
| `smtp_session` | 0.005 | 0.987 | 5.44 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.753 | 2.402 | 0.490 | 5.36 |
| `EnrichEmails` | 0.005 | 0.428 | — | 0.428 | 14.62 |
| `GetAttachmentStream` | 0.482 | 1.576 | 2.419 | 0.497 | 6.25 |
| `GetEmailContent` | 0.049 | 0.499 | 2.425 | 0.497 | 7.51 |
| `GetFolders` | 0.005 | 0.993 | 0.993 | 0.375 | 4.13 |
| `ProcessEmailUid` | 0.022 | 0.737 | — | 0.737 | 0.15 |
| `ReadFolder` | 0.500 | 2.425 | 2.425 | 0.487 | 18.78 |
| `ReadToday` | 0.005 | 0.497 | 2.425 | 0.497 | 4.18 |
| `UpdateFlag` | 0.005 | 0.491 | — | 0.491 | 13.56 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.489 | 0.490 | 0.0 % |
| `EnrichEmails` | **0.397** | 0.412 | 0.428 | 0.0 % |
| `GetAttachmentStream` | **0.491** | 0.493 | 0.496 | 0.0 % |
| `GetEmailContent` | **0.490** | 0.492 | 0.497 | 0.0 % |
| `GetFolders` | **0.242** | 0.242 | 0.247 | 0.0 % |
| `ProcessEmailUid` | **0.487** | 0.488 | 0.737 | 0.0 % |
| `ReadFolder` | **0.432** | 0.442 | 0.449 | 0.0 % |
| `ReadToday` | **0.488** | 0.490 | 0.493 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.491 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 70.08 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.500 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

> ⓘ **PgBouncer — transitoire d'attente, écarté du verdict.** 62 échantillon(s) sur 1107 portent une attente cliente non nulle (5.6 %, pointe à 4), sous le seuil de présence soutenue de 25 %. Ce profil est celui d'une **ouverture de palier**, pas d'un pooler qui n'absorbe plus — il ne désigne donc pas de facteur limitant. À surveiller tout de même : sur la campagne du 2026-07-29, cette pointe croît avec la charge.

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| conteneur `mss-mail-seq-b6152948` (CPU) | 9.28 cœurs | 24 cœurs | 38.7 % | 0.0 % — transitoire |
| conteneur `postgres-pgvector` (CPU) | 7.10 cœurs | 24 cœurs | 29.6 % | 0.0 % — transitoire |
| processus `mss.mail.api#13004` (CPU) | 3.73 cœurs | 24 cœurs | 15.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#29356` (CPU) | 3.23 cœurs | 24 cœurs | 13.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#51676` (CPU) | 3.21 cœurs | 24 cœurs | 13.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#67224` (CPU) | 2.96 cœurs | 24 cœurs | 12.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#51560` (CPU) | 2.83 cœurs | 24 cœurs | 11.8 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-51560` | 11.00 éléments | 100 éléments | 11.0 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (conteneur `mss-mail-seq-b6152948` (CPU)) monte à 38.7 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## IA — fournisseurs, étiquetage, file du bus

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 0

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | text-embedding-3-small | embedding | 175 748 112 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 47 604 | 0 (0.0 %) | 0 | 448.5 | 1.32 | 0.42 | 0.74 |
| étiquetage (chat) | OpenAI | 0 | — | 47 604 | 0.0 | — | — | — |
| embedding | OpenAI | 47 604 | 0 (0.0 %) | 0 | 448.5 | 1.31 | 0.42 | 0.74 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 183 | 0 | 100 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.6 | 28.0 |
| GPU — VRAM occupée (Mo) | 980 | 1 175 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **111.4 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **4 140.3** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.21** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **6.3 ms** | sur 1 280 473 requêtes HTTP k6 |
| Taux de cache (blocs) | **99.43 %** | ✅ ≥ 99 % |
| Lecture disque | **2.41 Mo/s (308 blocs/s)** | attente disque : 1.0 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **425 420 / 30 465** | rapport 14.0 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **1 073.2** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **2.47 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **2 / 27** | blocs écrits par les backends eux-mêmes : 36 % |
| Sessions ouvertes / s | **3.25** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **11 106.4 Mo** | 1 000 bases |
| Backends (échantillonneur, moy / max) | **1 859 / 1 985** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **100 / 100 %** | fautes majeures/s max : 3.6 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **18 évictions `pg_stat_statements`** pendant le tir (97 807 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

124 formes de requête, 29 653 825 appels, **75.7 min** de temps serveur cumulé — soit **3.5 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **24.6 %** | 25 % | 84 630 | 0.07 | 13.20 | 31.7 | 280 | 0 % | 0 | 1 000 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailContents" AS m INNER J…` |
| 2 | **22.9 %** | 47 % | 84 627 | 0.07 | 12.27 | 31.7 | 323 | 0 % | 0 | 1 000 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMedicalDocuments" AS m…` |
| 3 | **5.6 %** | 53 % | 340 059 | 0.27 | 0.75 | 1.0 | 17 | 6 % | 0 | 999 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 4 | **3.2 %** | 56 % | 3 810 582 | 2.98 | 0.04 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 5 | **3.1 %** | 59 % | 103 985 | 0.08 | 1.37 | 23.5 | 274 | 0 % | 0 | 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 6 | **2.9 %** | 62 % | 13 894 | 0.01 | 9.45 | 30.2 | 395 | 5 % | 0 | 779 | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 7 | **2.8 %** | 65 % | 9 238 879 | 7.22 | 0.01 | 0.0 | 0 | — | 0 | 1 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 8 | **2.7 %** | 68 % | 24 482 | 0.02 | 5.01 | 20.0 | 870 | 0 % | 0 | 930 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 9 | **2.6 %** | 70 % | 3 810 582 | 2.98 | 0.03 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 10 | **2.6 %** | 73 % | 24 516 | 0.02 | 4.77 | 20.0 | 900 | 0 % | 0 | 932 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 11 | **2.4 %** | 75 % | 77 374 | 0.06 | 1.42 | 1.0 | 124 | 0 % | 0 | 999 | — | `INSERT INTO "MailAttachments" ("Id", "Content", "ContentType", "DocumentId", "FileName", "Guid", "MailId", "Size") VALU…` |
| 12 | **2.1 %** | 77 % | 95 421 | 0.07 | 0.98 | 5.4 | 201 | 0 % | 0 | 1 000 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 13 | **1.7 %** | 79 % | 330 978 | 0.26 | 0.23 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 14 | **1.6 %** | 81 % | 46 971 | 0.04 | 1.59 | 1.0 | 92 | 0 % | 0 | 993 | — | `INSERT INTO "MailMedicalDocuments" ("Id", "Body", "Category", "ContentFingerprint", "CreatedAt", "Date", "DocumentId", …` |
| 15 | **1.6 %** | 82 % | 27 139 | 0.02 | 2.71 | 1.0 | 244 | 0 % | 0 | 933 | — | `UPDATE "MailAttachments" SET "Content" = $1, "Size" = $2 WHERE "Id" = $3` |
| 16 | **1.5 %** | 84 % | 292 744 | 0.23 | 0.23 | 1.0 | 9 | 0 % | 0 | 999 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 17 | **1.4 %** | 85 % | 1 280 423 | 1.00 | 0.05 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 18 | **1.2 %** | 86 % | 90 626 | 0.07 | 0.58 | 1.0 | 12 | 0 % | 0 | 999 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 19 | **0.8 %** | 87 % | 188 340 | 0.15 | 0.20 | 18.0 | 5 | 0 % | 0 | 999 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **0.8 %** | 88 % | 433 452 | 0.34 | 0.08 | 2.1 | 8 | 0 % | 0 | 999 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 87.0 % | 60.3 % |
| INSERT | 7.5 % | 2.8 % |
| UPDATE | 2.6 % | 1.0 % |
| DELETE | 0.1 % | 0.3 % |
| AUTRE | 2.9 % | 35.6 % |
| bases : praticien (N bases) | 88.2 % | 36.5 % |
| bases : unique (1 base) | 11.8 % | 63.5 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **13.2** | 226 | 84 630 | 24.6 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailCo…` |
| **12.3** | 255 | 84 627 | 22.9 % | `SELECT m."MailId", m1."Uid"::bigint AS "Uid", m1."FolderPath", m1."SentDate", m."Body" FROM "MailMe…` |
| **9.4** | 286 | 13 894 | 2.9 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **5.0** | 84 | 24 482 | 2.7 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **4.8** | 53 | 24 516 | 2.6 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l3l_6a40d49b947850c73013d4abda4877bd` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 7 798 | 1 136 176 | 313 | 164 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 2 066 | 944 646 | 0 | 386 | 0.1 Mo |
| `Mails` | 1 973 | 254 156 | 1 281 | 162 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 459 | 102 806 | 251 | 275 | 31.2 Mo |
| `MailRecipients` | 354 | 49 394 | 0 | 162 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 272 | 32 513 | 2 529 | 164 | 8.2 Mo |
| `MailContents` ⚠️ index candidat | 136 | 19 196 | 1 080 | 162 | 1.9 Mo |
| `MailFolders` | 501 | 2 054 | 578 | 4 | 0.1 Mo |
| `ContactMssAddresses` | 104 | 729 | 0 | 9 | 0.0 Mo |
| `Tags` | 81 | 642 | 487 | 10 | 0.0 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🔴 | requête n°1 (24.6 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Schéma | 🟠 | 14 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailAttachments` balayée 459 fois (102806 lignes lues, 275 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 272 fois (32513 lignes lues, 164 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 136 fois (19196 lignes lues, 162 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°4 (3.2 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°7 (2.8 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Postgres | 🟡 | 36 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | plus de checkpoints forcés que programmés : `max_wal_size` trop petit pour le débit d'écriture du tir |
| Schéma | 🟡 | requête n°8 (2.7 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-153158.tsv`, `pgserver-journey-debut-134038.tsv`, `pgserver-journey-fin-153202.tsv`, `pgtables-journey-debut-134040.tsv`, `pgtables-journey-fin-153205.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 145508 — dont **145508** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Attendu par boîte** : 247 (complétude relative au périmètre du scénario)
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-1000-20261031-tous-actifs-openai-sans-tag-152654.jsonl`.

Fenêtre analysée : 2026-10-31 12:40 → 14:27 UTC (régime du tir), comptages par `/api/data`.

| Niveau | Source | Message | Nombre | Lecture |
|---|---|---|---|---|
| Warning | `CdaParsingService` | `Missing values: {Name} in {Section}` | 24 690 | Corpus synthétique incomplet, attendu au banc |
| Warning | `CdaParsingService` | `CDA validation failed` | 291 | Idem, CDA du kit volontairement imparfaits |
| Warning | `TlsCertificateValidationSession` | `Allowing untrusted certificate … due to configuration` | 23 046 | Certificat autosigné du Dovecot de banc, attendu |
| Warning | `MailClientSessionManager` | `Session expired` | 9 798 | Rotation des sessions inactives, attendu |
| Warning | `PractitionerContactPublisher` | `SKIPPED - Invalid RPPS` | 3 393 | Données du corpus |
| Warning | `PractitionerContactService` | `SKIPPED - Empty FullName` | 568 | Données du corpus |
| Warning | `MailRepository` | `biology results skipped (missing Name)` | 559 | Données du corpus |
| Warning | `ImapService` | `Email UID={EmailId} not found` | 155 | **Toutes** sur `loadtest-600`, boîte vide côté cluster depuis le 2026-10-07 |
| Error | `MailController` | `Attachment not found.` | 46 | Idem : les 201 événements 404 viennent tous de `loadtest-600` |
| Error | `SmtpService` / `SmtpConnectionFactory` | — | 5 | Arrêt du tir (requêtes coupées à 15:26) |

- **Aucun** `429`, **aucun** échec d'embedding, **aucun** `Failed to parse entity headers`, aucune reprise d'étiquetage (étiquetage désactivé par drapeau).
- **Aucun** avertissement `Search engine … unavailable` : la recherche lente n'est jamais passée en mode dégradé, elle a **attendu** (voir le finding Recherche).
- Seq lui-même a consommé jusqu'à **9,3 cœurs** (pointe) : à surveiller, il partage l'hôte du système sous test.
