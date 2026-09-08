# Rapport de tir — journey-1000-lot288-194-20260908r2

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-lot288-194-20260908r2-204719.json`.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- 5.21 % des demandes ont échoué (au-delà du plafond de 1 %)

À instruire une fois le tir refait :
- à 1000 médecins, 8 étape(s) dépassent le temps de réponse attendu : « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) », « Recherche »
- une étape ne mesure pas ce que son nom annonce — son chiffre décrit un autre geste
- 11 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 100 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1319859 — **débit émergent global** : 104.2 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 112701 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 104.2 | **827.1** | 128.1 | **2669.9** | — | 300000.0 | 5.21 | 94.8 | 0 | 0 | 112693/247 |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 391158 | 31.04 | 12.00 | 1506.2 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 96 / 781 (n=136376) |
| 2 | Ouvrir / rafraîchir l'inbox | 208 / 5058 (n=68188) |
| 3 | Ouvrir un message enrichi (servi base) | 344 / 1221 (n=34136) |
| 4 | Ouvrir un message froid (fetch IMAP) | 505 / 1348 (n=6531) |
| 5 | Recherche | 2255 / 5474 (n=10016) |
| 6 | Envoi (acquittement UI) | 788 / 38185 (n=10196) |
| 7 | Télécharger une PJ (~124 Ko) | 796 / 2280 (n=13695) |
| 8 | Marquer lu | 240 / 1166 (n=27334) |
| 9 | Rechercher un patient | 23 / 222 (n=7865) |
| 10 | Ouvrir la page d'un dossier patient | 690 / 2677 (n=9869) |
| 11 | Fiche patient complète (ressenti médecin) | 2108 / 9697 (n=4933) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 12.9 / 20 | 28.8 / 60 | 6508 | 9697 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3969 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 9656 ms en moyenne, 60012 ms au pire — soit **0.1 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 779 / 1327 (magasin) |
| Backends Postgres (moy/max) | 1078 / 1225 |
| PgBouncer `cl_waiting` (échant. non nuls) | 309/309 (100 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 309/309 (100 %) |
| …dont pool de **maintenance** (échant. non nuls) | 76/309 (25 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 120193.6 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 120193.6 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 72640.5 |
| RSS par réplica api-mail, Mo (moy/max) | 2430 / 2946 (5 réplicas) |

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

⛔ **Chauffe insuffisante — les étapes 2, 3, 10, 11 ne sont pas opposables.** **75.6 %** des médecins ont terminé leur chauffe (plancher **90 %**, sur 1000 médecins) ; 1002 lot(s) d'analyse perdu(s) ; 84.5 % des ouvertures de l'étape 3 servies par la base (plancher 95 %). Ces étapes sont **servies par la base des messages analysés** : une base peu peuplée les rend rapides sans rien dire de la charge visée — au tir `journey-remote-n500` du 2026-08-09, `GetMailsByUids` coûtait **55,4 ms / 7,8 requêtes** par appel contre **1 199,7 ms / 14,8** sur un tir dont la base était peuplée. **Ce tir ne mesure donc pas la capacité** : ses latences sont flattées, quelle que soit leur valeur. Relancer après une chauffe aboutie (lots `JOURNEY_WARMUP_BATCH`, task-244).

> ⚠️ Chauffe : **9985 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **79 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

⛔ **Étape 3 « servi base » refusée — elle ne mesure pas ce que son nom annonce.** Seules **84.5 %** de ses ouvertures portent les documents de l'analyse, pour un plancher de 95 % : le reste a basculé sur le serveur de messagerie, donc cette étape mesure en partie des ouvertures **froides** et son chiffre n'est **pas** un verdict, quelle que soit sa valeur (pour situer : 24.71 sollicitations/s du serveur de messagerie sur la fenêtre, étapes 3/4 et rafale dossier confondues). Causes connues : bande chaude non analysée par la chauffe (task-224, défaut 5 — les 440 ms du 2026-08-03), ou mails de chauffe estampillés **génération 0** (UIDVALIDITY) donc inatteignables en base (certification du 2026-08-06 — la chauffe doit lister les dossiers AVANT d'analyser).

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 96 (300) | 781 (1500) | 136376 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 208 (300) | 5058 (1000) | 68188 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 344 (100) | 1221 (500) | 34136 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 505 (800) | 1348 (2500) | 6531 | ✅ |
| 5 | Recherche | 2255 (500) | 5474 (2000) | 10016 | ❌ |
| 6 | Envoi (acquittement UI) | 788 (1000) | 38185 (3000) | 10196 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 796 (500) | 2280 (2000) | 13695 | ❌ |
| 8 | Marquer lu | 240 (200) | 1166 (1000) | 27334 | ❌ |
| 9 | Rechercher un patient | 23 (300) | 222 (1500) | 7865 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 690 (500) | 2677 (2000) | 9869 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 2108 (1500) | 9697 (4000) | 4933 | ⛔ non opposable — chauffe insuffisante |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Envoi (acquittement UI) (`send`) | 10196 | 8392 | 38185 | 85560.1 | 30.4 % |
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 68188 | 1218 | 5058 | 83029.2 | 29.5 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 136376 | 242 | 781 | 32970.8 | 11.7 % |
| 🔴 | Recherche (`search`) | 10016 | 2526 | 5474 | 25301.4 | 9.0 % |
| 🟠 | Ouvrir un message enrichi (servi base) (`read_content`) | 34136 | 452 | 1221 | 15414.9 | 5.5 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 13695 | 995 | 2280 | 13621.8 | 4.8 % |
| 🟠 | Marquer lu (`mark_read`) | 27334 | 390 | 1166 | 10660.6 | 3.8 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 3254 | 1811 | 3517 | 5893.7 | 2.1 % |
| 🟠 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 4933 | 931 | 2677 | 4592.5 | 1.6 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 6531 | 604 | 1348 | 3947.4 | 1.4 % |
| 🟠 | Rechercher un patient (`patient_search`) | 7865 | 63 | 222 | 494.4 | 0.2 % |
| 🟠 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 4936 | 52 | 159 | 255.9 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 3 🔴 · 8 🟠 · 1 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Envoi (acquittement UI)** (`send`, 85560.1 s, 30.4 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (8392 ms)
  - **dispersion p95/p50 = 48.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 83029.2 s, 29.5 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1218 ms)
  - **dispersion p95/p50 = 24.3×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Arrivée dashboard** (`dashboard`, 32970.8 s, 11.7 %)
  - **dispersion p95/p50 = 8.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 25301.4 s, 9.0 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2526 ms)
- **Ouvrir un message enrichi (servi base)** (`read_content`, 15414.9 s, 5.5 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 3.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 13621.8 s, 4.8 %)
  - **hors grille** — le médecin attend trop
- **Marquer lu** (`mark_read`, 10660.6 s, 3.8 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 4.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 5893.7 s, 2.1 %)
  - **coût par appel élevé** (1811 ms)
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 4592.5 s, 1.6 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 3.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Rechercher un patient** (`patient_search`, 494.4 s, 0.2 %)
  - **dispersion p95/p50 = 9.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_opposition`, 255.9 s, 0.1 %)
  - **dispersion p95/p50 = 4.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation

> Tir du lot **288-285-289-184-186-291-193-183-194** (9 PR mergées entre le 2026-09-01 et le 2026-09-08),
> code sous test `develop` `9bd8a72`. Référence du palier : `report-journey-1000-solo-send272-20260826-184235`
> (code `70afc1d`). Conditions : 1000 médecins, journey K=1, 12 600 s, réserves 365..462 / 463..536 / 537..611,
> probabilités traitement 0,095 / lecture froide 0,19 (celles de la référence), corpus fileté 0,3 sur le cluster
> (192.168.1.69), RTT p50 **14,6 ms** → latence injectée **86 ms**.
>
> **Écarts d'iso-conditions déclarés, à lire avant tout chiffre :**
> 1. **Bases Postgres retrouvées VIDES au départ** (purgées par l'A/B task-194 du matin) : la chauffe a dû
>    hydrater 1000 boîtes de zéro, là où le 26/08 partait de bases peuplées par le 25/08. Résultat : chauffe
>    **75,6 %** (98,8 % en référence), 1002 lots d'analyse perdus, étapes 2/3/10/11 **non opposables**, et une
>    charge d'écriture d'enrichissement encore présente pendant la fenêtre de régime.
> 2. **Premier lancement (r1) avorté à 17h10** : le répertoire scratch `%TEMP%\mss-ihe-xdm` a été supprimé par un
>    acteur externe à 17h02 et l'application ne le recrée jamais (F-SCRATCH-1). Purge des tables, garde posée, relance r2.
> 3. Le tir est classé **ROUGE par le harnais** (5,21 % d'échecs) : les latences ci-dessous sont celles d'un système
>    qui **rejette** ~12 % de son trafic en régime (voir F-08P01-1). Un rejet en ~10 ms fait baisser les percentiles
>    des étapes touchées : les gains sont à lire avec cette réserve, les pertes sont, elles, certaines.

#### F-08P01-1 — 🛑 Nouveau mode de défaillance à 1000 : le pooler REJETTE au lieu de faire attendre

| Grandeur | 26/08 (référence) | 08/09 (ce tir) |
|---|---|---|
| Erreurs HTTP | 0,058 % | **5,21 %** (66 643 × HTTP 500 dans Seq, 88 863 `08P01`) |
| `cl_waiting` praticien | 45 % des relevés, pointe 109 | **100 %** des relevés, pointe 135, `maxwait` 120 s |
| Refus PgBouncer `server_login_retry` | non relevé | **85 787** sur le tir, 7 798 / 5 min en régime |
| Backends en cours de login (`sv_login`) | — | **212 à 243** simultanés en régime |
| Postgres (CPU, conteneur) | 15 cœurs en pointe | 11,1 moy / 15,5 pointe ; hôte 95 % moy |
| `PostgresException` (compteur runtime) | — | **2 178 414** (1 561 018 dans les 38 min de régime) |

**Cause mesurée.** Postgres saturé (11–15 cœurs, 50 backends en CPU + 31 en lecture disque à l'instant relevé, requêtes
dominantes : lecture des `MailMedicalDocuments` avec leur `Body`, puis `MailAttachments`) → l'ouverture d'un **nouveau**
backend dépasse `server_connect_timeout` → PgBouncer met l'échec **en cache** (`server_login_retry`, 15 s) et répond
`08P01` **en ~10 ms** à tout client du pool concerné. Avec `server_idle_timeout = 60` sur **1000 pools** (1 base par
praticien), les backends inactifs se ferment en permanence et doivent se rouvrir : c'est un **orage de logins** que
la saturation transforme en refus. Le premier refus apparaît à **19h30** (base hydratée à ~60 %), les 23 derniers
s'éteignent 15 min après la fin du tir. Contrôles faits : résolution IPv4 seule (`getent` → `172.24.0.2`), 0 refus
pendant les 2 h 15 premières, aucune charge étrangère significative (SQL Server 0,8 cœur, Ollama 0,08).

**Conséquences en cascade mesurées.** (a) `GetMail` : SQL 829 → 251 ms mais « le reste » 26 → **1 932 ms**
(2,2 s par ouverture) — ce sont les rejeux d'EF Core (`NpgsqlExecutionStrategy`, 49 742 `NpgsqlException` +
138 873 `InvalidOperationException` transitoires) qui paient le backoff, pas la matérialisation (9,4 objets) ;
(b) `send` : « le reste » 11,7 → **2 995 ms**, p95 **38 s**, `build_mime` 1 381 → 1 513 ms (ses deux lectures
base passent par le même chemin), 4 090 envois rendus en 500 en régime ; (c) l'audit (F-AUDIT-1).

**Remède à instruire (US).** Deux leviers **de configuration du pooler** à mesurer avant tout code :
`server_idle_timeout` ≫ 60 s (ou `min_pool_size ≥ 1`) pour supprimer la réouverture permanente sur 1000 pools, et
`server_login_retry` court + `query_wait_timeout` pour faire **attendre** plutôt que rejeter. Le levier applicatif
reste celui du 26/08 : le coût Postgres de la page hydratée et de la recherche (`Search/semantic` p95 serveur 27 s).
Gain attendu : retour à ≤ 0,1 % d'erreurs à 1000, ce qui rend les latences opposables. Risque : masquer la
saturation derrière une file (`cl_waiting`) au lieu de la traiter.

#### F-AUDIT-1 — 🛑 task-186 : le journal PGSSI-S a PERDU des traces sous saturation (Fatal)

| Grandeur | Valeur |
|---|---|
| Traces d'audit écrites pendant le tir (1000 bases, table `MssAuditTraces`) | **413 939** (MailReceive 107 020, MedicalDocumentProcess 106 999, MailRead 84 096, AttachmentDownload 42 104, MailSend 26 811, MailArchiveSent 26 481, SmtpConnect 10 742, ImapConnect 9 322) — ≈ 0,31 insertion par requête HTTP |
| `[Audit] Channel full — diverting trace to the spill buffer` (Warning) | **113 248** |
| `Failed to persist a batch … falling back to per-trace persistence` (Error) | 1 914 |
| `Failed to persist audit trace` (Error) | 3 372 |
| **`[Audit] Spill buffer is full (100000 traces) — trace … is LOST` (Fatal)** | **1 477**, première à **20h26** (régime), dernière à la fin du tir ; 0 depuis |
| Redis (`mss-mail-redis`) pendant le spill | 1,18 cœur en pointe, RSS 3,2 Go ; `[Cache] Timeout getting key` **10 233**, `Best-effort Set failed` 1 158 |

**Cause mesurée.** Les écritures d'audit passent par le même pooler saturé (F-08P01-1) : elles échouent, basculent
dans le canal mémoire, puis dans la liste Redis `mss:audit:spill` plafonnée à **100 000** traces (`MaxSpillLength`),
qui s'est remplie en ~1 h de régime. Au-delà, la trace est **perdue**, et le code le dit lui-même : « The audit trail
is no longer exhaustive (PGSSI-S) ». Le mécanisme de résilience a fonctionné (spill puis drainage complet : la clé
n'existe plus après le tir), mais son plafond est atteint dès que Postgres sature ~20 min. Effet de bord : la file
Redis d'audit a contendu le **cache** applicatif (10 233 timeouts de lecture de clé), autre chemin du médecin.

**Remède à instruire (US, priorité conformité).** Découpler le journal d'audit du chemin de données du praticien
(base ou schéma dédié hors des 1000 pools, ou écriture par lot asynchrone avec back-pressure sans perte) ; dimensionner
le spill par durée et non par nombre ; séparer l'instance Redis du spill de celle du cache. Gain attendu : 0 trace
perdue quel que soit l'état de Postgres, retrait de ~414 k transactions courtes par 3,5 h du pooler praticien.

#### F-SCRATCH-1 — 🛑 Robustesse : un répertoire scratch supprimé tue le traitement CDA jusqu'au redémarrage

Mesuré sur le lancement r1 : documents CDA créés normalement de 16h38 à 17h02, puis **0** à partir de 17h03 avec
~900 `DirectoryNotFoundException`/min (`IheXdmScratchDirectory.CreateFile`, `Could not find a part of the path
…\mss-ihe-xdm\<guid>.zip`). `IheXdmScratchDirectory` (task-185) crée le répertoire **une seule fois** à la
construction du singleton et le `Sweep` de démarrage ne le recrée pas : toute suppression externe (nettoyage de
`%TEMP%`, outil tiers) rend l'enrichissement définitivement inopérant, en **HTTP 200** côté médecin, jusqu'au
redémarrage du processus. L'auteur de la suppression n'est **pas attribué** (aucune autre session, aucun test en
cours, Storage Sense non configuré) ; une garde du banc recrée désormais le répertoire et daterait une récidive
(aucune sur r2). **Remède** : `EnsureCreated()` dans `CreateFile()` (ou rattrapage de `DirectoryNotFoundException`
par recréation + un seul rejeu). Gain : suppression d'une classe d'incident de production silencieuse. Risque : nul.

#### F-194-1 — ⭐ task-194 confirmée à 1000 : la page d'en-têtes hydratée coûte 5 à 14 fois moins

| Grandeur (`GetMailsByUids` / appel `emails` de l'inbox) | 26/08 | 08/09 | Facteur |
|---|---|---|---|
| p50 / p95 client de la page d'en-têtes | 26 028 / 46 167 ms | **1 851 / 6 292 ms** | ÷14 / ÷7,3 |
| Moyenne totale `GetMailsByUids` | 7 648,6 ms | **1 376,1 ms** | ÷5,6 |
| dont matérialisation | 6 619,5 ms | 1 038,6 ms | ÷6,4 |
| dont exécution SQL | 1 028,2 ms | 334,7 ms | ÷3,1 |
| Objets construits / appel | 270,1 | 247,1 | −9 % |
| **Coût par objet** | 24 512 µs | **4 203 µs** | **÷5,8** |
| Temps serveur cumulé de l'inbox sur le palier | 626 343 s (67 %) | 83 029 s (30 %) | ÷7,5 |

Le nombre d'objets est quasi constant (dont objets de fil 60,0 → 56,6) : le gain est bien un **coût par objet**, pas
une page plus légère — cohérent avec l'A/B du matin (allocations ÷13, gen2 ÷8). Réserve : ~12 % de la charge en
régime a été délestée par les rejets `08P01`, ce qui allège Postgres pour les requêtes restantes ; le facteur exact
sera confirmé par le tir 500 (0 rejet). La page reste **hors grille** à 1000 (p95 6,3 s pour 1 s) : le levier
suivant est le scan `References LIKE` côté Postgres (mémoire de l'A/B), inchangé par task-194.

#### F-GAINS-1 — Étapes IMAP et session : 2 à 4 fois plus rapides à 1000 (avec la réserve du délestage)

| Étape | 26/08 p50 / p95 | 08/09 p50 / p95 | Verdict |
|---|---|---|---|
| 1 Arrivée dashboard | 401 / 2 336 | **96 / 781** | ❌ → ✅ |
| 4 Message froid (IMAP) | 1 048 / 3 211 | **505 / 1 348** | ❌ → ✅ |
| 5 Recherche | 6 481 / 11 384 | 2 255 / 5 474 | ❌ (÷2,9, `Search/semantic` p95 serveur 27 s inchangé) |
| 6 Envoi | 2 448 / 14 272 | 788 / **38 185** | ❌ (p50 ÷3, p95 ×2,7 : F-08P01-1) |
| 7 PJ | 1 689 / 4 597 | 796 / 2 280 | ❌ (÷2) |
| 8 Marquer lu | 1 310 / 3 372 | 240 / 1 166 | ❌ (÷5,5 ; `UpdateFlag` attend 1,3 s au p95 sur `imap_session`) |
| 9 Rechercher un patient | 137 / 528 | **23 / 222** | ✅ |
| Documents CDA analysés /s (pointe) | 24,3 | **42,8** | +76 % |
| `EnrichPersistMail` moyenne | 720 ms | 256 ms | ÷2,8 |

Attribution **partielle** : la baisse générale du coût Postgres par requête (F-194-1) libère du CPU pour tout le
reste — c'est cohérent avec des gains uniformes sur des étapes qui ne touchent pas au comptage de fils. La part de
task-282 (clé du pool de sessions par client) et task-285 n'est pas séparable dans ce tir. Le délestage par rejets
(~12 %) flatte ces chiffres d'une part non chiffrée : ils sont des **bornes optimistes** tant que le palier n'est
pas rejoué sans `08P01`.

#### F-EXC-1 — Familles d'exceptions : hygiène tenue sur les marqueurs, bruit dominé par 08P01

Zéros tenus : `Failed to parse entity headers` **0**, HTTP 429 **0**, `Error extracting IHE-XDM` **0** (r2),
échec d'embedding 8192 tokens **0**, `FolderNotFoundException` absente. `SmtpCommandException` 11 261 et
`keep-alive NOOP failed` 5 992 : le serveur SMTP du banc coupe toujours les NOOP (connu depuis task-269). `SocketException`
6 059 sur un seul réplica en début de tir, non journalisée (avalée), à instruire si elle croît. Conflits de contact
(`CONFLIT METIER`, apport perdu) : **153** pour 26 811 envois (0,6 %) — connu, en hausse relative sous saturation.
`[CdaParsingService] Missing values` 188 776 = preuve que le parseur descend dans le CDA (bénin).

**Propositions de tasks `/po` (à arbitrer par le PO)** : (1) F-AUDIT-1 — journal d'audit découplé du pooler praticien,
spill sans perte ; (2) F-SCRATCH-1 — recréation du scratch à la demande ; (3) F-08P01-1 — réglage PgBouncer
(`server_idle_timeout`, `min_pool_size`, `server_login_retry`) **mesuré au banc** avant d'être porté en DevOps ;
(4) instruction Postgres de la page hydratée (`References LIKE`) et de la recherche sémantique, déjà au backlog.

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 34094 | 256 | 1101 | 15022.3 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 34094 | 59 | 650 | 6301.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 34094 | 116 | 779 | 9165.3 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 34094 | 27 | 213 | 2481.6 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 34094 | 76 | 543 | 5795.0 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 34094 | 1851 | 6292 | 77234.2 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (1101 ms de p95, 256 ms de p50, n=34094), qui porte **aussi** le temps serveur de l'étape (15022.3 s, 46 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (6292 ms de p95, 1851 ms de p50, n=34094), qui porte **aussi** le temps serveur de l'étape (77234.2 s, 93 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 45329 | 893.7 | 623.0 | 1706.6 | 2221.9 | 120000.5 |
| attachment,palier:1000 | 13695 | 994.7 | 795.7 | 1766.2 | 2280.5 | 38196.6 |
| attachment,palier:transition | 163 | 554.6 | 516.8 | 1003.4 | 1167.8 | 2264.7 |
| dashboard | 452724 | 213.6 | 73.4 | 526.1 | 755.7 | 60007.4 |
| dashboard,call:coverage,palier:1000 | 34094 | 72.8 | 27.4 | 133.9 | 213.4 | 60001.2 |
| dashboard,call:coverage,palier:transition | 8 | 7.0 | 6.9 | 9.3 | 9.4 | 9.6 |
| dashboard,call:folder,palier:1000 | 34094 | 440.6 | 256.3 | 828.2 | 1101.0 | 60000.3 |
| dashboard,call:folder,palier:transition | 8 | 350.8 | 379.7 | 405.1 | 405.4 | 405.6 |
| dashboard,call:folders,palier:1000 | 34094 | 268.8 | 116.1 | 539.7 | 779.1 | 60002.7 |
| dashboard,call:folders,palier:transition | 8 | 6.1 | 6.1 | 7.7 | 7.8 | 8.0 |
| dashboard,call:today,palier:1000 | 34094 | 184.8 | 58.7 | 486.6 | 650.3 | 60007.4 |
| dashboard,call:today,palier:transition | 8 | 362.9 | 365.8 | 373.7 | 374.6 | 375.6 |
| dashboard,palier:1000 | 136376 | 241.8 | 96.2 | 551.6 | 780.6 | 60007.4 |
| dashboard,palier:transition | 32 | 181.7 | 63.6 | 381.1 | 401.2 | 405.6 |
| mark_read | 90448 | 300.4 | 137.4 | 741.3 | 1076.2 | 59999.6 |
| mark_read,palier:1000 | 27334 | 390.0 | 240.2 | 823.6 | 1165.9 | 38113.3 |
| mark_read,palier:transition | 310 | 144.6 | 94.0 | 325.8 | 419.6 | 1368.4 |
| patient_docs | 222663 | 852.4 | 110.2 | 1324.1 | 1867.1 | 60013.9 |
| patient_docs,palier:1000 | 63559 | 896.6 | 439.5 | 1554.9 | 2030.2 | 60012.0 |
| patient_docs,palier:transition | 855 | 232.6 | 87.9 | 814.6 | 1032.8 | 1874.0 |
| patient_dossier | 16164 | 729.0 | 275.6 | 2038.3 | 2739.8 | 13927.1 |
| patient_dossier,palier:1000 | 4933 | 931.0 | 690.4 | 2120.4 | 2676.9 | 7632.8 |
| patient_dossier,palier:transition | 63 | 417.3 | 279.0 | 925.2 | 1537.7 | 2175.5 |
| patient_opposition | 16164 | 37.9 | 21.1 | 77.7 | 124.2 | 2185.0 |
| patient_opposition,palier:1000 | 4936 | 51.9 | 32.8 | 100.2 | 159.4 | 901.3 |
| patient_opposition,palier:transition | 63 | 17.7 | 8.7 | 29.7 | 42.5 | 291.6 |
| patient_search | 25885 | 47.1 | 15.0 | 100.2 | 195.9 | 38045.0 |
| patient_search,palier:1000 | 7865 | 62.9 | 23.5 | 131.6 | 222.0 | 38045.0 |
| patient_search,palier:transition | 101 | 24.1 | 10.4 | 68.1 | 100.6 | 199.3 |
| read_content | 113181 | 355.7 | 198.1 | 841.7 | 1179.2 | 60006.0 |
| read_content,palier:1000 | 34136 | 451.6 | 343.8 | 903.5 | 1221.1 | 60006.0 |
| read_content,palier:transition | 192 | 287.9 | 197.0 | 567.7 | 755.6 | 3095.9 |
| read_content_cold | 21834 | 549.9 | 454.8 | 829.3 | 1122.3 | 38182.1 |
| read_content_cold,palier:1000 | 6531 | 604.4 | 505.1 | 1006.8 | 1348.2 | 38073.6 |
| read_content_cold,palier:transition | 78 | 556.7 | 435.6 | 573.7 | 848.6 | 8624.0 |
| read_list | 226362 | 1044.3 | 131.2 | 3642.1 | 5270.6 | 60000.6 |
| read_list,call:emails,palier:1000 | 34094 | 2265.3 | 1851.2 | 5049.7 | 6291.6 | 60000.6 |
| read_list,call:emails,palier:transition | 102 | 1526.7 | 1517.3 | 3024.0 | 3314.4 | 4250.7 |
| read_list,call:folder,palier:1000 | 34094 | 170.0 | 75.6 | 351.6 | 542.7 | 59998.9 |
| read_list,call:folder,palier:transition | 102 | 65.9 | 25.3 | 163.6 | 185.5 | 1129.4 |
| read_list,palier:1000 | 68188 | 1217.7 | 208.4 | 3789.2 | 5057.7 | 60000.6 |
| read_list,palier:transition | 204 | 796.3 | 110.2 | 2629.6 | 3023.8 | 4250.7 |
| search | 33977 | 2027.9 | 1476.1 | 4487.8 | 5564.6 | 120000.2 |
| search,palier:1000 | 10016 | 2526.1 | 2255.0 | 4539.5 | 5474.1 | 38531.5 |
| search,palier:transition | 123 | 1385.9 | 1198.7 | 2914.7 | 3185.5 | 4285.3 |
| send | 33533 | 7248.3 | 755.2 | 30411.6 | 38179.8 | 120010.8 |
| send,palier:1000 | 10196 | 8391.5 | 788.1 | 38090.9 | 38185.2 | 120010.8 |
| send,palier:transition | 143 | 1003.2 | 446.8 | 1113.4 | 4576.2 | 12789.3 |
| treatment | 10586 | 1610.5 | 1286.1 | 3104.9 | 3857.6 | 300000.0 |
| treatment,palier:1000 | 3254 | 1811.2 | 1686.4 | 2972.8 | 3516.8 | 300000.0 |
| treatment,palier:transition | 14 | 1307.1 | 1294.2 | 2493.6 | 2644.1 | 2684.0 |
| warmup | 11000 | 9655.7 | 2860.9 | 24860.2 | 59999.1 | 60012.1 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-08T15:16:16.742000+00:00 → 2026-09-08T18:47:19.813000+00:00 (12663 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-201927.csv`) | ✅ 39332 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-10448` | 1.11 | 9 | 22 | 0.037 | 267.75 |
| `DESKTOP-DEV-X2C-43044` | 0.84 | 7 | 20 | 0.041 | 262.78 |
| `DESKTOP-DEV-X2C-49216` | 1.08 | 10 | 26 | 0.039 | 319.99 |
| `DESKTOP-DEV-X2C-50208` | 0.92 | 8 | 20 | 0.038 | 243.31 |
| `DESKTOP-DEV-X2C-7276` | 0.97 | 11 | 20 | 0.041 | 263.51 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#34056` | 1.96 | 3.71 | 1465 |
| `com.docker.backend#35624` | 0.00 | 0.10 | 33 |
| `dcp#12760` | 0.00 | 0.00 | 11 |
| `dcp#18040` | 0.00 | 0.00 | 12 |
| `dcp#20636` | 0.00 | 0.05 | 12 |
| `dcp#30600` | 0.00 | 0.00 | 12 |
| `dcp#33096` | 0.00 | 0.00 | 12 |
| `dcp#46432` | 0.00 | 0.20 | 40 |
| `dcp#47052` | 0.00 | 0.00 | 11 |
| `dcp#47728` | 0.00 | 0.00 | 12 |
| `dcp#48432` | 0.00 | 0.00 | 12 |
| `dcp#6680` | 1.08 | 2.18 | 2281 |
| `k6#47668` | 0.32 | 3.57 | 2044 |
| `mss.mail.api#10448` | 0.49 | 1.75 | 2688 |
| `mss.mail.api#43044` | 0.54 | 2.09 | 2655 |
| `mss.mail.api#49216` | 0.67 | 2.24 | 2846 |
| `mss.mail.api#50208` | 0.51 | 1.86 | 2946 |
| `mss.mail.api#7276` | 0.56 | 1.65 | 2797 |
| `vmmemWSL#33512` | 13.04 | 16.20 | 36882 |
| `loadtest-otel-collector-erfrwjkp` | 0.05 | 0.26 | 128 |
| `loadtest-pgbouncer-bywthhgq` | 0.70 | 0.97 | 38 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.06 | 110 |
| `mss-mail-prometheus-b6152948` | 0.02 | 0.16 | 248 |
| `mss-mail-rabbitmq-bqnqhrzh` | 0.04 | 0.16 | 182 |
| `mss-mail-redis-b6152948` | 0.37 | 1.18 | 3199 |
| `mss-mail-seq-b6152948` | 0.01 | 0.03 | 161 |
| `postgres-pgvector` | 11.14 | 15.51 | 10414 |

- **Hôte** : CPU 95.4 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 58
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 6459, cl_waiting max 135, cl_waiting_maintenance max 4, cl_waiting_practitioner max 135, count max 1002, maxwait_maintenance_ms max 72640, maxwait_ms max 120194, maxwait_practitioner_ms max 120194, sv_active max 167, sv_idle max 1440
- **Backends Postgres** : practitioner_databases max 1548, total max 1559

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 60000.0 | 2531 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2846.0 | 2532 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 60000.0 | 2525 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 2530 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 1969.8 | 2527 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 5593.7 | 2521 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 3487.2 | 2523 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 29385.3 | 2526 |
| `api/v{version:apiVersion}/Mail/sendmail` | 60000.0 | 2510 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1150.0 | 2503 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 17600.0 | 2503 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 587.5 | 2503 |
| `api/v{version:apiVersion}/Search/semantic` | 27280.7 | 2520 |
| `api/v{version:apiVersion}/Sync/coverage` | 708.9 | 2527 |

- **p95 client global (k6)** : 2669.9 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -57330.1 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 42.80 |
| Documents CDA /s | 42.82 |
| Durée traitement CDA (s, p95) | 0.13 |
| Événements de session IMAP /s | 3.00 |
| Recherches (s, p95) | 27.246 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.2 | 256.2 | 4317 | 2.2 (0.9 %), p95 320 | 218.8 (85.4 %), p95 4183 | 35.1 (13.7 %), p95 1093 |
| `GetMail` | 10.9 | 2205.0 | 60000 | 19.8 (0.9 %), p95 889 | 250.7 (11.4 %), p95 4350 | 1932.1 (87.6 %), p95 60000 |
| `GetMailsByUids` | 13.7 | 1376.1 | 29330 | 2.8 (0.2 %), p95 152 | 334.7 (24.3 %), p95 6358 | 1038.6 (75.5 %), p95 28419 |

- **`EnrichPersistMail`** — sur 256.2 ms en moyenne (8.2 requête(s) SQL par appel) : 2.2 ms attente d'une connexion, 218.8 ms exécution SQL, 35.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 2205.0 ms en moyenne (10.9 requête(s) SQL par appel) : 19.8 ms attente d'une connexion, 250.7 ms exécution SQL, 1932.1 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

- **`GetMailsByUids`** — sur 1376.1 ms en moyenne (13.7 requête(s) SQL par appel) : 2.8 ms attente d'une connexion, 334.7 ms exécution SQL, 1038.6 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 9.4 | 1932.1 | 205108.4 | 0.9 | 1.2 | 0.9 | 2.3 | non relevé | 0.0 | 0.9 | 2.2 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 247.1 | 1038.6 | 4202.7 | 23.6 | 32.1 | 23.6 | 36.7 | 21.0 | 0.0 | 21.0 | 6.6 | 0.0 | 20.9 | 56.6 | 4.7 |

- **`GetMail`** — sur 1932.1 ms de matérialisation, l'appel a construit 9.4 objets, dont 0.9 messages, 1.2 étiquettes, 0.9 destinataires, 2.3 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.2 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **205108.4 µs**.

- **`GetMailsByUids`** — sur 1038.6 ms de matérialisation, l'appel a construit 247.1 objets, dont 23.6 messages, 32.1 étiquettes, 23.6 destinataires, 36.7 pièces jointes, 21.0 identifiants enrichis, 0.0 acquittements, 21.0 documents médicaux, 6.6 résultats de biologie, 0.0 éléments de synthèse, 20.9 corps de messages, 56.6 objets de fil, 4.7 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **4202.7 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **52.6 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.7 | 480.0 | 4746 | 132.1 (27.5 %), p95 420 | 23.0 (4.8 %), p95 190 | 11.7 (2.4 %), p95 151 | 264.7 (55.1 %), p95 4332 | 48.5 (10.1 %), p95 1245 |

- **Enrichir un message** — sur 480.0 ms en moyenne (5.7 message(s) par requête) : 132.1 ms fetch IMAP, 23.0 ms extraction XDM, 11.7 ms parsing CDA, 264.7 ms écritures base, 48.5 ms le reste (DTO, notifications). **Poste dominant : écritures base.**
  - 🔁 **1.94 aller(s)-retour(s) IMAP par message enrichi** — 1.02 `fetch_whole_message`, 0.24 `resolve_folder`, 0.24 `fetch_bodystructure`, 0.23 `close_folder`, 0.22 `open_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 420.3 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 6033.7 | 19455 | 0.0 (0.0 %), p95 5 | 1512.7 (25.1 %), p95 9504 | 825.4 (13.7 %), p95 1853 | 678.1 (11.2 %), p95 1380 | 411.9 (6.8 %), p95 928 | 2995.4 (49.6 %), p95 15074 |

- **Envoyer un message** — sur 6033.7 ms en moyenne : 0.0 ms garde d'opposition, 1512.7 ms construction MIME, 825.4 ms obtention de session SMTP, 678.1 ms transmission + acquittement, 411.9 ms archivage Sent, 2995.4 ms le reste. **Poste dominant : construction MIME.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.713 | 28.000 | 0.31 |
| `imap_session` | 1.490 | ≥ 60 ⚠️ | 76.52 |
| `in_process_fetch` | 0.005 | 28.000 | 0.31 |
| `smtp_session` | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 3.96 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.011 | 5.413 | 4.500 | 5.513 | 6.71 |
| `EnrichEmails` | 0.031 | 1.764 | 7.375 | 1.764 | 48.46 |
| `GetAttachmentStream` | 0.334 | 3.760 | 6.625 | 3.865 | 5.20 |
| `GetEmailContent` | 0.005 | 3.302 | 2.425 | 3.302 | 4.96 |
| `GetFolders` | 0.475 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 1.945 | 4.58 |
| `ProcessEmailUid` | 0.044 | 28.000 | — | 28.000 | 0.31 |
| `ReadFolder` | 2.094 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 1.699 | 26.95 |
| `UpdateFlag` | 1.308 | 2.193 | 4.875 | 2.182 | 11.49 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.646** | 0.908 | 5.513 | 4.3 % |
| `EnrichEmails` | **0.462** | 0.494 | 1.764 | 0.0 % |
| `GetAttachmentStream` | **1.502** | 2.097 | 3.865 | 16.6 % |
| `GetEmailContent` | **0.718** | 0.999 | 3.302 | 4.3 % |
| `GetFolders` | **0.413** | 0.508 | 1.175 | 0.0 % |
| `ProcessEmailUid` | **0.487** | 4.850 | 7.375 | 28.4 % |
| `ReadFolder` | **0.496** | 0.704 | 1.699 | 0.0 % |
| `UpdateFlag` | **0.696** | 0.985 | 2.182 | 1.6 % |

- 🟠 **`AppendToSent` : pointe non représentative.** Médiane **0.646 s**, p90 0.908 s, mais une pointe à 5.513 s sur 4.3 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🔴 **`GetAttachmentStream` : détention tenue en régime** — médiane 1.502 s et **16.6 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🟠 **`GetEmailContent` : pointe non représentative.** Médiane **0.718 s**, p90 0.999 s, mais une pointe à 3.302 s sur 4.3 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🔴 **`ProcessEmailUid` : détention tenue en régime** — médiane 0.487 s et **28.4 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🟠 **`UpdateFlag` : pointe non représentative.** Médiane **0.696 s**, p90 0.985 s, mais une pointe à 2.182 s sur 1.6 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.

> ⚠️ **Pourquoi cette table existe** (task-276). La table qui la précède réduit chaque série à sa **pointe**. Au tir du 2026-08-29, `ReadFolder` y valait 11,871 s — lu comme « la fusion de task-270 a allongé la section critique », alors que sa médiane en régime valait 0,469 s, **sous** les 0,692 s de l'opération qu'elle remplace. La pointe était réelle ; la conclusion qu'on en tirait, non. Même famille de piège que les buckets en millisecondes (task-211), le plafond d'histogramme (task-245) et la saturation lue comme un timeout (task-271).
| Voie | Acquisitions /s |
|---|---|
| `read` | 76.52 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

✅ **Lecture rétablie** pour `GetFolders`, `ReadFolder` : l'agrégat est saturé (« ≥ 60 s », c'est-à-dire *non mesuré* — `histogram_quantile` rend la dernière borne finie quand le quantile tombe dans `+Inf`), mais l'exploitation, elle, tient dans l'instrument. La queue appartient à la chauffe, pas au régime établi.

**Archivage vs reste** : `AppendToSent` attend 0.011 s au p95, contre 2.094 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 135.00 clients | 0 clients | 100.0 % | 99.7 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 15.51 cœurs | 24 cœurs | 64.6 % | 0.0 % — transitoire |
| processus `k6#47668` (CPU) | 3.57 cœurs | 24 cœurs | 14.9 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-7276` | 11.00 éléments | 100 éléments | 11.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#49216` (CPU) | 2.24 cœurs | 24 cœurs | 9.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#43044` (CPU) | 2.09 cœurs | 24 cœurs | 8.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#50208` (CPU) | 1.86 cœurs | 24 cœurs | 7.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#10448` (CPU) | 1.75 cœurs | 24 cœurs | 7.3 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 99.7 % des échantillons de la fenêtre.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 112693 — dont **112693** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Attendu par boîte** : 247 (complétude relative au périmètre du scénario)
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-1000-lot288-194-20260908r2-204719.jsonl`
> (échantillon : 1 500 `Error`/`Fatal` hors middleware HTTP + 500 `Warning`, 6,5 Mo). Comptages exhaustifs sur la
> fenêtre 15:16:16Z → 18:47:20Z par l'API Seq (`select count(*)`), MCP `seq-local` pour les décompositions.

| Requête | Résultat | Lecture |
|---|---|---|
| `@Level in ['Error','Fatal']` | **185 320** (dont **1 477 Fatal**) | dominé par 08P01 : `HTTP … Status=500` 66 643, `Unhandled exception` 43 512, `Result-mapped …` 23 131, `{Reason} for folder {Folder}` 15 736, `Unexpected error getting folders` 4 332 |
| `@Level = 'Warning'` | 360 616 | `Missing values` 188 776 (bénin), **`[Audit] Channel full` 113 248**, certificat non approuvé 20 475 (banc), `[Cache] Timeout getting key` 10 233, `Session expired` 8 749, RPPS invalide 7 575 (corpus), `R-RETRY` MassTransit 1 610 |
| `Failed to parse entity headers` | **0** | Dovecot sert `BODY[part]` — pas de régression |
| `[CdaParsingService] Parsing completed` | **107 549** | = 106 999 traces `MedicalDocumentProcess` : les deux compteurs se recoupent |
| `maximum input length is 8192 tokens` | **0** | task-196 tenue ; mais `Embedding failed for MailId` **5 366** (`SemanticSearchService` 1 730 erreurs) — à ouvrir : famille à établir (OpenAI ? 08P01 sur la lecture ?) |
| `StatusCode = 429` | **0** | limiteur jamais atteint |
| `Error extracting IHE-XDM` | **0** (r2) | F-SCRATCH-1 ne s'est pas reproduit avec la garde |
| `keep-alive NOOP failed` | 5 992 | serveur SMTP du banc, connu |
| `Failed to persist audit trace` / `Spill buffer is full … LOST` | 3 372 / **1 477** | F-AUDIT-1 |
| `CONFLIT METIER` (contact) | 153 | 0,6 % des envois |
| `[BackgroundQueue] Background work failed` | 5 552 | à ventiler par `Label` (sous 08P01, très probablement l'archivage/audit) |
| `[Tagging] Failed for MailId` | 2 715 | étage IA, à recouper avec `ClientResultException` (mémoire : c'est OpenAI, pas Flagsmith) |
| Corrélation `UserEmail` sur les consumers bus | présente (`AddNewMailConsumer` 8 081 erreurs portent `UserEmail`) | enrichissement task-198 actif |

**Findings Seq.** (1) Aucun marqueur de régression IMAP/CDA. (2) Le bruit d'erreurs est à ~90 % la même cause
(08P01) vue de quatre couches (middleware, handler global, controller, `ImapService.ConnectInternal` qui lit
`UserSettings` en base) — un rejet du pooler produit **4 lignes d'erreur** par requête. (3) Deux familles à
instruire hors saturation : `Embedding failed` (5 366) et `[Tagging] Failed` (2 715), dont on ne sait pas encore la
part imputable à 08P01. (4) Le journal d'audit n'est pas exhaustif sur ce tir (Fatal) : c'est le finding de
conformité de la campagne.
