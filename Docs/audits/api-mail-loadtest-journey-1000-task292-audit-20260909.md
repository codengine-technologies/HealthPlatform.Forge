# Rapport de tir — journey-1000-task292-audit-20260909

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-task292-audit-20260909-123235.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1000 médecins, 10 étape(s) dépassent le temps de réponse attendu : « Arrivée dashboard », « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) »
- 11 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 47 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.444 % des demandes ont échoué (sous le plafond, mais non nul)

## 🎯 Objet du tir — vérification task-292 (journal d'audit PGSSI-S découplé)

Code sous test : `feat/task-292-audit-trail-decoupled` @ `c2c108b` (PR api-mail #225). Référence de saturation : tir 1000 r2 du 2026-09-08
(`develop` `9bd8a72`, journal task-186) ; référence de latence sur base hydratée : tir 1000 du 2026-08-26 (`70afc1d`).
Protocole iso 08/09 r2 (1000 médecins, `1000:12600s`, réserves 365..462 / 463..536 / 537..611, traitement 0,095, froid 0,19,
corpus fileté 0,3, cluster 192.168.1.69, `UID_BASE=365`), **bases praticien gardées du 08/09 (hydratées, non purgées)**,
RTT p50 20 ms → latence injectée 81 ms. Fenêtre 09h01 → 12h32 (local), régime 11h54 → 12h32.

| Grandeur (fenêtre du tir) | 08/09 r2 (task-186) | **09/09 (task-292)** |
|---|---|---|
| Traces émises / persistées en base | 413 939 / **1 477 perdues** (Fatal `LOST`) | 198 545 / **198 542** (1000 bases comptées) — **0 Fatal, 0 `LOST`** |
| `[Audit] Channel full` (bascule spill) | 113 248 | 111 678 (= compteur `spilled`) |
| Rejouées depuis le spill | — | 111 681 (1 118 lots) ; spill Redis **vide 6 min après la fin du tir** |
| Contre-pression : attentes / refus | n/a | **18 / 18** (12h17-12h18, spill à sa borne 120 000) ; 11 réponses 503 côté HTTP, 7 refus après effet de bord (200) |
| Échecs de persistance (lot → repli par trace) | 1 914 / 3 372 | 49 / **6** (Npgsql timeout sur la route directe, 11h21-11h52 et 12h21-12h22) |
| **Écart émises − en base** | 1 477 + non compté | **3 traces** — perte silencieuse du repli par trace (F-292-1) |
| Retard du tampon (max) / âge de la plus vieille trace (max) | non instrumenté | 767 s / **5 307 s** (1 h 28) |
| `08P01 server_login_retry` (PgBouncer) | 85 787 | **646** (−99 %) |
| HTTP 500 / 503 (Seq) | 66 643 / — | 724 / 11 |
| `[Cache] Timeout getting key` (Redis, cache applicatif) | 10 233 | **21 835** ⚠️ (non attribuable au spill sans A/B — F-292-3) |
| Redis : mémoire pic / base logique du spill | instance partagée, `db0` | 2,80 Go pic ; spill `db1` (1000 marqueurs de purge résiduels), cache `db0` |
| Postgres CPU moy tir / régime / max (cœurs) | 11,14 / — / 15,51 | 5,76 / 11,30 / 14,63 |
| PgBouncer `cl_waiting` (échant. non nuls) / CPU moy | 100 % / 0,70 | 47 % / 0,53 (pic 1,02 — **mono-thread à son plafond**) |
| Erreurs k6 / p95 client | 5,21 % / 2 670 ms (12 % de rejets en 10 ms flattent tout) | 0,44 % / 10 526 ms (≈ référence 26/08 : 0,06 % / 8 940 ms) |

**Verdict task-292 : l'objectif produit est tenu sur le fond — aucune trace jetée par le mécanisme de spill (0 `LOST`, 0 Fatal),
le journal ne transite plus par le pooler praticien (INSERT observés depuis l'hôte 172.24.0.1, jamais depuis PgBouncer 172.24.0.3),
les rejets 08P01 du pooler tombent de 99 %.** Trois réserves mesurées : (1) **3 traces perdues silencieusement** par le repli
« par trace » (`PersistIndividuallyAsync` journalise en Error et abandonne — aucun compteur `dropped`, aucun re-spill) ;
(2) le **drain est sérialisé par praticien et paie un login Postgres par groupe** : 0,2 à 0,45 trace/s persistée par réplica pour
~4/s émises sous saturation — la borne de 60 min a été atteinte à 3 h 16 de tir et la contre-pression a refusé 18 gestes du médecin ;
(3) les timeouts du cache Redis ont **doublé**, sans qu'on puisse l'imputer au spill sans le tir « journal désactivé » (non joué).

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1083205 — **débit émergent global** : 85.5 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 90777 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 85.5 | **2311.4** | 207.4 | **10526.0** | — | 119999.5 | 0.44 | 99.6 | 0 | 0 | 119861/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 242618 | 19.26 | 0.95 | 1013.1 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 360 / 1949 (n=82052) |
| 2 | Ouvrir / rafraîchir l'inbox | 5734 / 58022 (n=41034) |
| 3 | Ouvrir un message enrichi (servi base) | 2551 / 6856 (n=20566) |
| 4 | Ouvrir un message froid (fetch IMAP) | 933 / 2821 (n=3960) |
| 5 | Recherche | 8884 / 40670 (n=6191) |
| 6 | Envoi (acquittement UI) | 6653 / 16244 (n=6149) |
| 7 | Télécharger une PJ (~124 Ko) | 3763 / 8592 (n=8222) |
| 8 | Marquer lu | 1351 / 3401 (n=16415) |
| 9 | Rechercher un patient | 182 / 690 (n=4896) |
| 10 | Ouvrir la page d'un dossier patient | 10024 / 32613 (n=6093) |
| 11 | Fiche patient complète (ressenti médecin) | 23655 / 66156 (n=3039) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 14.7 / 20 | 33.8 / 60 | 3930 | 66156 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3784 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 6546 ms en moyenne, 60014 ms au pire — soit **0.1 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 795 / 1697 (magasin) |
| Backends Postgres (moy/max) | 924 / 1583 |
| PgBouncer `cl_waiting` (échant. non nuls) | 1108/2371 (47 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 1107/2371 (47 %) |
| …dont pool de **maintenance** (échant. non nuls) | 267/2371 (11 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 63498.3 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 41111.5 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 63498.3 |
| RSS par réplica api-mail, Mo (moy/max) | 1887 / 3946 (5 réplicas) |

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

⛔ **Chauffe insuffisante — les étapes 2, 3, 10, 11 ne sont pas opposables.** **86.5 %** des médecins ont terminé leur chauffe (plancher **90 %**, sur 1000 médecins) ; 378 lot(s) d'analyse perdu(s) ; 98.3 % des ouvertures de l'étape 3 servies par la base (plancher 95 %). Ces étapes sont **servies par la base des messages analysés** : une base peu peuplée les rend rapides sans rien dire de la charge visée — au tir `journey-remote-n500` du 2026-08-09, `GetMailsByUids` coûtait **55,4 ms / 7,8 requêtes** par appel contre **1 199,7 ms / 14,8** sur un tir dont la base était peuplée. **Ce tir ne mesure donc pas la capacité** : ses latences sont flattées, quelle que soit leur valeur. Relancer après une chauffe aboutie (lots `JOURNEY_WARMUP_BATCH`, task-244).

> ⚠️ Chauffe : **10128 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **80 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 360 (300) | 1949 (1500) | 82052 | ❌ |
| 2 | Ouvrir / rafraîchir l'inbox | 5734 (300) | 58022 (1000) | 41034 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 2551 (100) | 6856 (500) | 20566 | ⛔ non opposable — chauffe insuffisante |
| 4 | Ouvrir un message froid (fetch IMAP) | 933 (800) | 2821 (2500) | 3960 | ❌ |
| 5 | Recherche | 8884 (500) | 40670 (2000) | 6191 | ❌ |
| 6 | Envoi (acquittement UI) | 6653 (1000) | 16244 (3000) | 6149 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 3763 (500) | 8592 (2000) | 8222 | ❌ |
| 8 | Marquer lu | 1351 (200) | 3401 (1000) | 16415 | ❌ |
| 9 | Rechercher un patient | 182 (300) | 690 (1500) | 4896 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 10024 (500) | 32613 (2000) | 6093 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 23655 (1500) | 66156 (4000) | 3039 | ⛔ non opposable — chauffe insuffisante |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 41034 | 16593 | 58022 | 680857.5 | 66.0 % |
| 🔴 | Recherche (`search`) | 6191 | 12310 | 40670 | 76213.4 | 7.4 % |
| 🔴 | Ouvrir un message enrichi (servi base) (`read_content`) | 20566 | 2985 | 6856 | 61399.3 | 6.0 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 82052 | 604 | 1949 | 49569.9 | 4.8 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 6149 | 7189 | 16244 | 44206.2 | 4.3 % |
| 🔴 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 3039 | 12150 | 32613 | 36924.9 | 3.6 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 8222 | 4315 | 8592 | 35476.8 | 3.4 % |
| 🔴 | Marquer lu (`mark_read`) | 16415 | 1663 | 3401 | 27292.8 | 2.6 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 1965 | 5936 | 14478 | 11663.8 | 1.1 % |
| 🔴 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 3960 | 1282 | 2821 | 5075.9 | 0.5 % |
| 🟠 | Rechercher un patient (`patient_search`) | 4896 | 257 | 690 | 1256.8 | 0.1 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 3054 | 298 | 542 | 911.3 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 8 🔴 · 3 🟠 · 1 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Ouvrir / rafraîchir l'inbox** (`read_list`, 680857.5 s, 66.0 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (16593 ms)
  - **dispersion p95/p50 = 10.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 76213.4 s, 7.4 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (12310 ms)
  - **dispersion p95/p50 = 4.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 61399.3 s, 6.0 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2985 ms)
- **Arrivée dashboard** (`dashboard`, 49569.9 s, 4.8 %)
  - **hors grille** — le médecin attend trop
  - **dispersion p95/p50 = 5.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Envoi (acquittement UI)** (`send`, 44206.2 s, 4.3 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (7189 ms)
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 36924.9 s, 3.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (12150 ms)
  - **dispersion p95/p50 = 3.3×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 35476.8 s, 3.4 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (4315 ms)
- **Marquer lu** (`mark_read`, 27292.8 s, 2.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1663 ms)
- **Traitement (plateforme)** (`treatment`, 11663.8 s, 1.1 %)
  - **coût par appel élevé** (5936 ms)
  - **dispersion p95/p50 = 3.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message froid (fetch IMAP)** (`read_content_cold`, 5075.9 s, 0.5 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1282 ms)
  - **dispersion p95/p50 = 3.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Rechercher un patient** (`patient_search`, 1256.8 s, 0.1 %)
  - **dispersion p95/p50 = 3.8×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation

> Tir de **vérification de correctif** (task-292) : les 11 candidats mécaniques ci-dessus sont ceux du palier 1000 sur base hydratée, déjà instruits par la référence du 26/08 (page d'en-têtes hydratée = 66 % du temps serveur, task-273 / E015). Ils ne sont pas re-décomposés ici. Findings propres au journal d'audit :

- **F-292-1 — Perte silencieuse par le repli « par trace » (défaut du correctif, à corriger avant merge).** `AuditBackgroundService.PersistIndividuallyAsync` attrape l'exception, journalise en Error et **passe à la suivante** : ni `TracesDropped`, ni re-spill, ni Fatal. Mesuré : 6 échecs (`Npgsql timeout` sur la route directe), **3 traces absentes des 1000 bases** (198 542 lignes pour 198 545 émises). Remède : re-spiller la trace (`ForceSpillAsync`) ou la remettre au canal avec compteur d'essais ; incrémenter `dropped` (alertable) si l'abandon reste inévitable. Gain : le zéro perte redevient « par construction ». Risque : nul.
- **F-292-2 — Le drain est borné par le login Postgres, pas par l'INSERT (cause mesurée).** Le drain traite les groupes séquentiellement (un praticien = une base = une chaîne = **un pool Npgsql distinct**, idle 5 s, pool 2) et chaque groupe rouvre un backend. Sous saturation : 0,20-0,45 trace/s persistée par réplica pour 3,5-5,9/s émises → retard max 767 s, plus vieille trace 1 h 28, borne de 60 min atteinte à 3 h 16, 18 refus. Le 08/09, PgBouncer amortissait ce login. Remèdes mesurables : paralléliser les groupes (degré 8-16, borné), allonger l'idle du pool audit (5 s → 60-120 s), écrire par lot multi-tenant, ou dimensionner la borne du spill sur le débit de **drain** réel plutôt que sur le pic d'émission. Gain attendu : drain ≥ émission (×10 à ×20), plus de contre-pression à 1000. Risque : pression de connexions directes sur Postgres (borner le degré).
- **F-292-3 — Timeouts du cache Redis ×2,1, cause non établie.** À trancher par le tir « journal désactivé » (`MSS_LOADTEST_AUDIT_DISABLED=true`) à protocole égal — c'est aussi le point 5 de l'US (coût du journal sur Postgres). Non joué dans cette session (3 h 30 supplémentaires).
- **F-292-4 — Payload du spill Redis : chaînes de connexion avec mot de passe en clair** (`RPUSH mss:audit:spill {"transportConnectionStringServer":"Host=…;Password=…` vu au slowlog). Déjà suggéré par la revue de code (`[JsonIgnore]`) : à faire avant merge, le spill peut séjourner une heure dans une surface partagée.
- **F-292-5 — PgBouncer à 1,02 cœur en pointe, 0,82 en régime** : le pooler mono-thread est à son plafond CPU. Il attend (cl_waiting 47 %) au lieu de rejeter — mieux que le 08/09, mais c'est le prochain goulet du chemin de données (task-294).


## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 20513 | 528 | 2782 | 18025.7 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 20513 | 119 | 1297 | 7949.4 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 20513 | 587 | 2312 | 17954.8 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 20513 | 75 | 960 | 5640.0 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 20517 | 137 | 2156 | 9892.5 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 20517 | 30991 | 60000 | 670965.0 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (2782 ms de p95, 528 ms de p50, n=20513), qui porte **aussi** le temps serveur de l'étape (18025.7 s, 36 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (60000 ms de p95, 30991 ms de p50, n=20517), qui porte **aussi** le temps serveur de l'étape (670965.0 s, 99 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 36501 | 2003.8 | 1011.3 | 5118.4 | 6410.1 | 119997.5 |
| attachment,palier:1000 | 8222 | 4314.9 | 3763.1 | 6811.0 | 8591.5 | 30821.5 |
| attachment,palier:transition | 129 | 2114.7 | 1943.4 | 4272.9 | 4820.0 | 9454.6 |
| dashboard | 365912 | 330.7 | 115.1 | 853.0 | 1262.5 | 60002.4 |
| dashboard,call:coverage,palier:1000 | 20513 | 274.9 | 75.0 | 712.7 | 959.8 | 10656.5 |
| dashboard,call:coverage,palier:transition | 10 | 26.0 | 17.2 | 58.6 | 61.1 | 63.6 |
| dashboard,call:folder,palier:1000 | 20513 | 878.7 | 528.2 | 1627.6 | 2782.1 | 18688.3 |
| dashboard,call:folder,palier:transition | 10 | 279.3 | 343.7 | 400.4 | 404.1 | 407.8 |
| dashboard,call:folders,palier:1000 | 20513 | 875.3 | 586.8 | 1783.3 | 2312.4 | 23958.4 |
| dashboard,call:folders,palier:transition | 10 | 16.3 | 13.7 | 22.8 | 26.9 | 31.0 |
| dashboard,call:today,palier:1000 | 20513 | 387.5 | 118.7 | 779.1 | 1296.6 | 16786.4 |
| dashboard,call:today,palier:transition | 10 | 302.6 | 363.1 | 403.5 | 404.5 | 405.6 |
| dashboard,palier:1000 | 82052 | 604.1 | 360.0 | 1357.5 | 1949.1 | 23958.4 |
| dashboard,palier:transition | 40 | 156.1 | 41.0 | 392.3 | 403.4 | 407.8 |
| mark_read | 72861 | 749.8 | 409.8 | 1834.6 | 2286.3 | 19007.8 |
| mark_read,palier:1000 | 16415 | 1662.7 | 1351.4 | 2507.2 | 3400.7 | 19007.8 |
| mark_read,palier:transition | 237 | 663.8 | 641.7 | 1287.9 | 1668.2 | 2677.3 |
| patient_docs | 194168 | 1795.4 | 146.3 | 5729.7 | 7935.8 | 60003.7 |
| patient_docs,palier:1000 | 44901 | 4046.2 | 3672.9 | 8820.9 | 10845.3 | 36399.9 |
| patient_docs,palier:transition | 927 | 1066.7 | 432.8 | 2703.6 | 3834.8 | 11346.9 |
| patient_dossier | 13237 | 5248.4 | 1032.3 | 17837.0 | 24963.2 | 60000.7 |
| patient_dossier,palier:1000 | 3039 | 12150.3 | 10024.2 | 26616.7 | 32612.7 | 60000.7 |
| patient_dossier,palier:transition | 42 | 5008.6 | 4500.5 | 10668.4 | 13885.1 | 17826.2 |
| patient_opposition | 13237 | 135.2 | 49.8 | 375.6 | 442.9 | 8366.4 |
| patient_opposition,palier:1000 | 3054 | 298.4 | 283.9 | 459.4 | 542.3 | 2191.0 |
| patient_opposition,palier:transition | 55 | 141.9 | 146.8 | 263.9 | 364.1 | 444.0 |
| patient_search | 21382 | 120.6 | 37.2 | 325.1 | 490.8 | 8781.8 |
| patient_search,palier:1000 | 4896 | 256.7 | 182.1 | 524.7 | 690.3 | 3463.1 |
| patient_search,palier:transition | 65 | 139.0 | 93.2 | 337.1 | 507.6 | 727.6 |
| read_content | 91448 | 1306.6 | 486.8 | 3405.6 | 4299.6 | 60001.5 |
| read_content,palier:1000 | 20566 | 2985.5 | 2550.8 | 4729.9 | 6856.3 | 34880.7 |
| read_content,palier:transition | 400 | 1158.7 | 999.9 | 2430.2 | 2842.9 | 7195.8 |
| read_content_cold | 17580 | 789.7 | 571.7 | 1384.6 | 1811.1 | 38581.1 |
| read_content_cold,palier:1000 | 3960 | 1281.8 | 933.4 | 2021.0 | 2820.9 | 38581.1 |
| read_content_cold,palier:transition | 68 | 676.4 | 629.6 | 926.0 | 988.8 | 2535.2 |
| read_list | 182956 | 7172.0 | 197.3 | 30012.6 | 44492.8 | 60023.8 |
| read_list,call:emails,palier:1000 | 20517 | 32702.9 | 30991.4 | 58022.5 | 60000.4 | 60017.6 |
| read_list,call:emails,palier:transition | 82 | 16054.8 | 17031.8 | 22281.0 | 23152.9 | 24049.9 |
| read_list,call:folder,palier:1000 | 20517 | 482.2 | 137.3 | 915.8 | 2156.0 | 18571.6 |
| read_list,call:folder,palier:transition | 82 | 84.7 | 34.6 | 235.7 | 388.3 | 559.8 |
| read_list,palier:1000 | 41034 | 16592.5 | 5733.6 | 47913.0 | 58022.5 | 60017.6 |
| read_list,palier:transition | 164 | 8069.8 | 243.9 | 20669.4 | 22268.2 | 24049.9 |
| search | 27256 | 7462.9 | 4084.8 | 19015.6 | 34207.8 | 119998.8 |
| search,palier:1000 | 6191 | 12310.4 | 8884.2 | 27164.6 | 40669.8 | 74371.1 |
| search,palier:transition | 72 | 4440.0 | 3194.7 | 9060.6 | 10785.2 | 17284.0 |
| send | 26942 | 3314.0 | 1011.8 | 9929.7 | 12578.5 | 119999.5 |
| send,palier:1000 | 6149 | 7189.2 | 6653.4 | 14180.1 | 16243.6 | 47160.8 |
| send,palier:transition | 79 | 2632.8 | 1466.0 | 7027.4 | 8094.2 | 9289.8 |
| treatment | 8716 | 2554.2 | 804.8 | 7213.0 | 9945.4 | 43297.1 |
| treatment,palier:1000 | 1965 | 5935.8 | 4739.8 | 11304.4 | 14478.4 | 38088.9 |
| treatment,palier:transition | 38 | 2745.9 | 1854.5 | 5753.4 | 6653.4 | 11624.4 |
| warmup | 11000 | 6545.7 | 341.7 | 22346.0 | 53055.1 | 60013.6 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-09T07:01:31.107000+00:00 → 2026-09-09T10:32:35.303000+00:00 (12664 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-090130.csv`) | ✅ 255115 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-10368` | 0.54 | 12 | 35 | 0.042 | 66.72 |
| `DESKTOP-DEV-X2C-44088` | 0.53 | 24 | 28 | 0.041 | 59.84 |
| `DESKTOP-DEV-X2C-44312` | 0.57 | 14 | 32 | 0.038 | 56.08 |
| `DESKTOP-DEV-X2C-44768` | 0.52 | 10 | 35 | 0.042 | 56.51 |
| `DESKTOP-DEV-X2C-584` | 0.64 | 16 | 34 | 0.042 | 68.60 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#32776` | 0.00 | 0.20 | 40 |
| `com.docker.backend#34112` | 1.50 | 4.89 | 1107 |
| `dcp#17224` | 0.00 | 0.30 | 12 |
| `dcp#19568` | 0.00 | 0.05 | 12 |
| `dcp#27112` | 0.00 | 0.21 | 12 |
| `dcp#29320` | 0.00 | 0.00 | 12 |
| `dcp#31924` | 0.00 | 0.14 | 12 |
| `dcp#37832` | 0.00 | 0.05 | 11 |
| `dcp#40492` | 0.75 | 2.43 | 1396 |
| `dcp#43220` | 0.00 | 0.20 | 12 |
| `dcp#43952` | 0.00 | 0.21 | 40 |
| `dcp#9144` | 0.00 | 0.25 | 12 |
| `k6#22900` | 0.19 | 3.67 | 2223 |
| `mss.mail.api#10368` | 0.30 | 2.05 | 3674 |
| `mss.mail.api#44088` | 0.31 | 1.76 | 3823 |
| `mss.mail.api#44312` | 0.30 | 1.72 | 3797 |
| `mss.mail.api#44768` | 0.30 | 1.71 | 3562 |
| `mss.mail.api#584` | 0.34 | 2.32 | 3946 |
| `vmmemWSL#35744` | 7.83 | 16.71 | 33041 |
| `loadtest-otel-collector-snuxvazf` | 0.03 | 0.25 | 126 |
| `loadtest-pgbouncer-mkxpxncg` | 0.54 | 1.02 | 35 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.22 | 173 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.19 | 232 |
| `mss-mail-rabbitmq-azxxqvck` | 0.01 | 0.10 | 192 |
| `mss-mail-redis-b6152948` | 0.21 | 1.18 | 2873 |
| `mss-mail-seq-b6152948` | 0.01 | 0.08 | 161 |
| `postgres-pgvector` | 5.77 | 14.63 | 11438 |

- **Hôte** : CPU 65.3 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 78
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 4516, cl_waiting max 102, cl_waiting_maintenance max 5, cl_waiting_practitioner max 102, count max 1002, maxwait_maintenance_ms max 63498, maxwait_ms max 63498, maxwait_practitioner_ms max 41112, sv_active max 614, sv_idle max 1154
- **Backends Postgres** : practitioner_databases max 1567, total max 1583

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 60000.0 | 2528 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 14484.4 | 2529 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 60000.0 | 2525 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 2510 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 7555.6 | 2525 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 21263.2 | 2516 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 19631.6 | 2524 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 60000.0 | 2527 |
| `api/v{version:apiVersion}/Mail/sendmail` | 50580.0 | 2492 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1459.4 | 2507 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 55000.0 | 2507 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 1075.0 | 2507 |
| `api/v{version:apiVersion}/Search/semantic` | 57750.0 | 2502 |
| `api/v{version:apiVersion}/Settings` | 242.5 | 4 |
| `api/v{version:apiVersion}/Settings/getsettings` | 9.3 | 4 |
| `api/v{version:apiVersion}/Sync/coverage` | 3386.9 | 2525 |

- **p95 client global (k6)** : 10526.0 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -49474.0 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 5.45 |
| Documents CDA /s | 5.49 |
| Durée traitement CDA (s, p95) | 0.95 |
| Événements de session IMAP /s | 3.18 |
| Recherches (s, p95) | 57.750 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.1 | 1945.2 | 24250 | 34.4 (1.8 %), p95 2200 | 1778.2 (91.4 %), p95 24250 | 132.6 (6.8 %), p95 1875 |
| `GetMail` | 11.4 | 1764.1 | 60000 | 100.4 (5.7 %), p95 3686 | 1267.1 (71.8 %), p95 23662 | 396.6 (22.5 %), p95 60000 |
| `GetMailsByUids` | 14.7 | 10981.0 | 60000 | 1.4 (0.0 %), p95 5 | 1425.3 (13.0 %), p95 10125 | 9554.3 (87.0 %), p95 60000 |

- **`EnrichPersistMail`** — sur 1945.2 ms en moyenne (8.1 requête(s) SQL par appel) : 34.4 ms attente d'une connexion, 1778.2 ms exécution SQL, 132.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 1764.1 ms en moyenne (11.4 requête(s) SQL par appel) : 100.4 ms attente d'une connexion, 1267.1 ms exécution SQL, 396.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 10981.0 ms en moyenne (14.7 requête(s) SQL par appel) : 1.4 ms attente d'une connexion, 1425.3 ms exécution SQL, 9554.3 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.0 | 396.6 | 39714.9 | 0.9 | 1.3 | 0.9 | 2.5 | non relevé | 0.0 | 0.9 | 2.3 | 0.1 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 240.3 | 9554.3 | 39760.8 | 21.7 | 32.7 | 21.7 | 35.1 | 21.4 | 0.0 | 21.4 | 6.7 | 0.0 | 21.3 | 52.1 | 6.1 |

- **`GetMail`** — sur 396.6 ms de matérialisation, l'appel a construit 10.0 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.5 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.3 résultats de biologie, 0.1 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **39714.9 µs**.

- **`GetMailsByUids`** — sur 9554.3 ms de matérialisation, l'appel a construit 240.3 objets, dont 21.7 messages, 32.7 étiquettes, 21.7 destinataires, 35.1 pièces jointes, 21.4 identifiants enrichis, 0.0 acquittements, 21.4 documents médicaux, 6.7 résultats de biologie, 0.0 éléments de synthèse, 21.3 corps de messages, 52.1 objets de fil, 6.1 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **39760.8 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **5.6 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.3 | 2710.7 | 25600 | 132.7 (4.9 %), p95 475 | 29.9 (1.1 %), p95 235 | 32.0 (1.2 %), p95 975 | 2104.3 (77.6 %), p95 25600 | 411.7 (15.2 %), p95 21333 |

- **Enrichir un message** — sur 2710.7 ms en moyenne (5.3 message(s) par requête) : 132.7 ms fetch IMAP, 29.9 ms extraction XDM, 32.0 ms parsing CDA, 2104.3 ms écritures base, 411.7 ms le reste (DTO, notifications). **Poste dominant : écritures base.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 3075.6 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 2805.2 | 8703 | 0.0 (0.0 %), p95 5 | 2094.2 (74.7 %), p95 7420 | 224.0 (8.0 %), p95 765 | 355.7 (12.7 %), p95 489 | 497.5 (17.7 %), p95 1310 | 131.3 (4.7 %), p95 316 |

- **Envoyer un message** — sur 2805.2 ms en moyenne : 0.0 ms garde d'opposition, 2094.2 ms construction MIME, 224.0 ms obtention de session SMTP, 355.7 ms transmission + acquittement, 497.5 ms archivage Sent, 131.3 ms le reste. **Poste dominant : construction MIME.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 4.875 | 2.425 | 0.05 |
| `imap_session` | 1.254 | 6.159 | 43.11 |
| `in_process_fetch` | 0.005 | 7.375 | 0.05 |
| `smtp_session` | 0.031 | 8.750 | 3.96 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.007 | 7.181 | 18.000 | 6.208 | 4.07 |
| `EnrichEmails` | 0.005 | 5.687 | 4.625 | 5.687 | 6.96 |
| `GetAttachmentStream` | 1.662 | 13.400 | 28.333 | 7.917 | 2.36 |
| `GetEmailContent` | 0.069 | 8.906 | 4.375 | 8.906 | 2.73 |
| `GetFolders` | 0.402 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 6.646 | 4.07 |
| `ProcessEmailUid` | 0.005 | 2.425 | — | 2.425 | 0.05 |
| `ReadFolder` | 1.498 | 5.978 | ≥ 60 ⚠️ | 5.956 | 22.07 |
| `UpdateFlag` | 2.104 | 6.324 | 4.083 | 6.324 | 10.29 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.699** | 3.391 | 6.208 | 13.7 % |
| `EnrichEmails` | **0.489** | 2.500 | 5.687 | 12.1 % |
| `GetAttachmentStream` | **4.054** | 5.750 | 7.917 | 100.0 % |
| `GetEmailContent` | **0.994** | 4.375 | 8.906 | 14.6 % |
| `GetFolders` | **0.472** | 4.000 | 6.646 | 13.7 % |
| `ProcessEmailUid` | **0.487** | 0.988 | 2.425 | 10.3 % |
| `ReadFolder` | **0.704** | 3.643 | 5.956 | 13.9 % |
| `UpdateFlag` | **0.922** | 4.307 | 6.324 | 14.6 % |

- 🔴 **`AppendToSent` : détention tenue en régime** — médiane 0.699 s et **13.7 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🔴 **`EnrichEmails` : détention tenue en régime** — médiane 0.489 s et **12.1 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🔴 **`GetAttachmentStream` : détention tenue en régime** — médiane 4.054 s et **100.0 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🔴 **`GetEmailContent` : détention tenue en régime** — médiane 0.994 s et **14.6 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🔴 **`GetFolders` : détention tenue en régime** — médiane 0.472 s et **13.7 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🔴 **`ProcessEmailUid` : détention tenue en régime** — médiane 0.487 s et **10.3 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🔴 **`ReadFolder` : détention tenue en régime** — médiane 0.704 s et **13.9 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🔴 **`UpdateFlag` : détention tenue en régime** — médiane 0.922 s et **14.6 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.

> ⚠️ **Pourquoi cette table existe** (task-276). La table qui la précède réduit chaque série à sa **pointe**. Au tir du 2026-08-29, `ReadFolder` y valait 11,871 s — lu comme « la fusion de task-270 a allongé la section critique », alors que sa médiane en régime valait 0,469 s, **sous** les 0,692 s de l'opération qu'elle remplace. La pointe était réelle ; la conclusion qu'on en tirait, non. Même famille de piège que les buckets en millisecondes (task-211), le plafond d'histogramme (task-245) et la saturation lue comme un timeout (task-271).
| Voie | Acquisitions /s |
|---|---|
| `read` | 43.11 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

✅ **Lecture rétablie** pour `GetFolders` : l'agrégat est saturé (« ≥ 60 s », c'est-à-dire *non mesuré* — `histogram_quantile` rend la dernière borne finie quand le quantile tombe dans `+Inf`), mais l'exploitation, elle, tient dans l'instrument. La queue appartient à la chauffe, pas au régime établi.

**Archivage vs reste** : `AppendToSent` attend 0.007 s au p95, contre 2.104 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 102.00 clients | 0 clients | 100.0 % | 46.7 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 14.63 cœurs | 24 cœurs | 60.9 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-44088` | 24.00 éléments | 100 éléments | 24.0 % | 0.0 % — transitoire |
| processus `k6#22900` (CPU) | 3.67 cœurs | 24 cœurs | 15.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#584` (CPU) | 2.32 cœurs | 24 cœurs | 9.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#10368` (CPU) | 2.05 cœurs | 24 cœurs | 8.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#44088` (CPU) | 1.76 cœurs | 24 cœurs | 7.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#44312` (CPU) | 1.72 cœurs | 24 cœurs | 7.2 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 46.7 % des échantillons de la fenêtre.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 119861 — dont **119861** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-1000-task292-audit-20260909-123235.jsonl` (Error+Fatal, `[Audit]%`, timeouts cache — 1 000 événements max par famille).
> Comptages exhaustifs via l'API Seq (`/api/data`, fenêtre 07:01Z → 10:40Z bornée par `@Timestamp`). ⚠️ `fromDateUtc`/`toDateUtc` sont **ignorés** par `/api/data` : un premier passage a compté toute l'histoire (Fatal 1 477 = ceux du 08/09). Toujours borner par `rangeStartUtc`/`rangeEndUtc` **et** `@Timestamp`.

| Requête | Compte | Lecture |
|---|---|---|
| `@Level = 'Fatal'` / `LOST` | **0 / 0** | 08/09 : 1 477 / 1 476. Le `LOST` du spill plein a disparu par construction. |
| `[Audit] Channel full` | 111 678 | = `mss_audit_traces_spilled_total`. Canal de 5 000 plein en continu de 11h00 à la fin : sous saturation le spill est le **régime normal**, pas un secours. |
| `[Audit] Journal saturated` (attente) / `parked, the traced action is refused` | 18 / 18 | 12h17:52 → 12h18:39, sur 4 réplicas. Le spill a touché sa borne (120 000 = 2 000/min × 60 min) à 3 h 16 : la contre-pression a fait ce qui était prévu, et 18 gestes (MailRead, AttachmentDownload, MailReceive) ont été refusés. Aucun `Spill threw` : ce n'est pas une panne Redis, c'est la **borne**. |
| `Failed to persist a batch` / `Failed to persist audit trace` | 49 / **6** | `Npgsql.NpgsqlException: The operation has timed out` sur la **route directe** (login Postgres à 11-14 cœurs). 49 lots (1-2 traces) repliés en « par trace », 6 traces individuelles **abandonnées après journalisation** (12h21:54 → 12h22:54). 3 sont pourtant en base (timeout après commit) : **3 traces manquent** dans les 1000 bases. |
| `[Audit] Replayed … spilled trace(s)` | 1 118 lots | 111 681 traces rejouées ; drain complet à 12h39 (Redis `LLEN mss:audit:spill` = 0). |
| `[Cache] Timeout getting key` / `Best-effort Set failed` | **21 835** / 287 | ×2,1 vs 08/09 (10 233) alors que Redis est à 0,21 cœur moyen (0,37 le 08/09) et que le spill vit en `db1`. Le slowlog Redis montre des `HMSET mail:email:*` de **1,47 Mo** (corps de message en cache) à 15 ms et des `RPUSH mss:audit:spill` à 11-16 ms. Cause **non établie** : Redis mono-thread bloqué par les gros HMSET, ou attente côté client (hôte à 96 %). Le tir « journal désactivé » est le seul test qui tranche. |
| `08P01 server_login_retry` | **646** | 85 787 le 08/09 : −99 %. 0,18 transaction d'audit par requête retirée du pooler, et PgBouncer n'atteint plus le mode « rejet en cache » : il **attend** (cl_waiting 47 %, maxwait 41 s praticien) au lieu de rejeter — objet de task-294. |
| `HTTP … Status=500` / `503` | 724 / 11 | 66 643 le 08/09. Les 500 restants : `Error retrieving attachment`, `sendmail` sous 08P01 résiduel. Les 503 = contre-pression audit (7 des 18 refus sont arrivés après l'effet de bord, en 200 — `enrich/sync`). |
| `Parsing completed` | 7 377 | Étape traitement + 378 lots de chauffe perdus (bases déjà hydratées : la chauffe court-circuite l'essentiel). |
| `Failed to parse entity headers` / scratch `mss-ihe-xdm` / `8192 tokens` / 429 | 0 / 0 / 0 / 0 | RAS. Garde scratch : 0 recréation. Keep-awake armé (preuve : état précédent 0x80000000). |
| `@Level = 'Debug'` | 0 | Niveau Information (task-203) respecté. |
| Error+Fatal / Warning | 2 454 / 185 105 | 185 320 / 360 616 le 08/09. |

## Télémétrie fine — où va le temps du journal

- **Route** : `pg_stat_activity` échantillonné pendant le tir — `INSERT INTO "MssAuditTraces"` **uniquement** depuis `172.24.0.1` (passerelle Docker = hôte = route directe `MSS-MAIL-CONNECTIONSTRING-DIRECT`), jamais depuis `172.24.0.3` (PgBouncer). Backends : 604 pooler / 71 directs à 10h06 ; 1 206 / 43 à 11h08 ; 1 338 / 2 à 11h35.
- **Drain** : à 11h30, `rate(mss_audit_traces_persisted_total[5m])` = 0,41 / 0,20 / 0,00 / 0,45 / 0,00 trace/s par réplica pour 3,7-5,9/s émises ; connexions directes quasi toutes `idle` (1 active sur 43, puis sur 2) ; ThreadPool en file 0-2, 14-19 threads ; CPU processus 0,43-0,57 cœur. **Le writer n'attend ni Postgres ni un thread : il rouvre un backend par groupe** (2-5 `backend_start` récents toutes les 3 s), avec un login à plusieurs centaines de ms sous 11-14 cœurs Postgres. Après la fin du tir (Postgres libre), le même drain a écoulé ~96 000 traces en 6 min (≈ 270/s).
- **Ce que la télémétrie n'a pas pu dire** : la durée du login Postgres par connexion directe (pas d'histogramme d'ouverture de connexion côté Npgsql), et la part des timeouts Redis due au spill vs aux gros HMSET du cache — les deux exigent le tir A/B « journal désactivé ».

