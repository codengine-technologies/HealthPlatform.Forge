# Rapport de tir — journey-1000-task292-fix-20260909

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-task292-fix-20260909-211858.json`.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- 1.37 % des demandes ont échoué (au-delà du plafond de 1 %)

À instruire une fois le tir refait :
- à 1000 médecins, 8 étape(s) dépassent le temps de réponse attendu : « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) », « Recherche »
- 10 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 52 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné

## 🎯 Objet du tir — re-tir de la branche corrigée `2354b44` (F-292-1/2/4), journal ACTIF — RÉSULTAT NÉGATIF

Code sous test : `feat/task-292-audit-trail-decoupled` @ `2354b44` — repli par trace re-spillé avec plafond de 5 essais, **drain
parallèle (8 groupes praticien concurrents)**, idle du pool audit 60 s, chaînes de connexion hors du spill. Même protocole et mêmes
bases que les deux tirs précédents du jour (matin `c2c108b` journal actif ; après-midi journal désactivé). RTT 23 ms → latence 78 ms.
Fenêtre 17h47 → 21h18, régime 20h40 → 21h18. **k6 exit 99 : `http_req_failed` 1,37 % > 1 %.**

| Grandeur | Matin (drain série) | A/B journal off | **Soir (drain parallèle 8)** |
|---|---|---|---|
| Erreurs k6 / p95 client | 0,44 % / 10 526 ms | 0,16 % / 9 418 ms | **1,37 % / 11 079 ms** |
| Refus PgBouncer `08P01` | 646 | 270 | **15 873** |
| HTTP 500 / 503 (Seq) | 724 / 11 | 340 / 0 | 14 280 / 8 |
| Traces émises / persistées en base (1000 bases) | 198 545 / 198 542 (−3) | 0 (journal off) | 181 308 / **180 181 (−1 127)** |
| `mss_audit_traces_dropped_total` (Critical `LOST`) | 0 | — | **1 034** (Fatal Seq 1 034) |
| `Channel full` / spillées / rejouées | 111 678 / 111 678 / 111 681 | — | 96 679 / **166 567** / 166 474 (les traces qui échouent recirculent) |
| Contre-pression : attentes / refus | 18 / 18 (borne atteinte) | — | **38 / 18** dès 20h58 à 70 k sur 120 k (`Spill buffer unreachable` : Redis à 1,1 cœur) |
| Échecs de persistance lot / trace | 49 / 6 | — | 62 211 / 70 942 |
| Login Postgres mesuré (psql dans le conteneur, en régime) | non mesuré | non mesuré | **10 à 16 s** ; ~3,8 backends/s ; cgroup mémoire à la limite (12 Go, +15 600 échecs d'allocation/s) |
| Postgres CPU moy tir / max | 5,76 / 14,63 | 5,93 / 15,07 | 6,51 / 15,09 |
| Timeouts cache Redis | 21 835 | 6 568 | 8 778 |
| Chauffe aboutie | 86,5 % | 93,7 % | 86,2 % (étapes 2/3/10/11 ⛔) |

**Ce que ce tir prouve, et qu'il fallait mesurer plutôt que supposer :**

1. **Le drain parallèle aggrave** (F-292-2, remède invalidé). La ressource rare n'est pas la sérialisation du drain mais la capacité de
   Postgres à créer des backends : un login prend 10 à 16 s sous saturation, le serveur n'en accepte que ~3,8/s. Quarante logins
   directs concurrents (8 × 5 réplicas) se disputent cette capacité avec les logins serveur de PgBouncer (`server_connect_timeout`
   15 s) : le pooler expire, met l'échec en cache et **rejette les requêtes du médecin** — 15 873 refus contre 646 le matin,
   1,37 % d'erreurs contre 0,44 %. → `Audit:DrainParallelism` **repasse à 1 par défaut** (le bouton reste).
2. **Le plafond de 5 essais sur toute panne perd des traces** (F-292-1, correctif incomplet). Le rejeu du spill contre un serveur qui
   refuse les logins a fait échouer les mêmes traces 5 fois en quelques minutes : **1 034 traces perdues**, comptées et journalisées en
   Critical — pire que les 3 du matin. → le plafond ne s'applique plus qu'aux traces **poison** (SqlState 22/23/42) ; un timeout ou
   un login refusé est rejoué sans limite.
3. **La cause racine est la pression mémoire du conteneur Postgres** : 54 Go de bases pour 12 Go de cgroup, cache de pages à la
   limite, 15 600 échecs d'allocation par seconde, 27 backends en `DataFileRead`. C'est elle qui rend le login à 15 s, donc les
   `08P01` du pooler et le drain lent — sur les trois tirs du jour. → task-294 (monter la limite mémoire, `shared_buffers`).
4. **Redis en tampon n'est fiable que si Redis n'est pas lui-même saturé** : 38 attentes / 18 refus de contre-pression dès 70 000
   entrées sur 120 000, sur `Spill buffer unreachable` — Redis à 1,1 cœur sur les `HMSET` du cache (F-292-3, finding cache).
   → borne du spill portée de 60 à 180 min ; la saturation Redis relève du cache, pas du journal.

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1097681 — **débit émergent global** : 86.7 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 91707 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 86.7 | **2206.1** | 210.4 | **11079.3** | — | 120001.2 | 1.37 | 98.7 | 0 | 0 | 84086/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 248749 | 19.74 | 3.02 | 1060.8 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 231 / 1147 (n=84940) |
| 2 | Ouvrir / rafraîchir l'inbox | 485 / 48517 (n=42518) |
| 3 | Ouvrir un message enrichi (servi base) | 2098 / 4767 (n=21240) |
| 4 | Ouvrir un message froid (fetch IMAP) | 741 / 1459 (n=4009) |
| 5 | Recherche | 7943 / 37538 (n=6394) |
| 6 | Envoi (acquittement UI) | 4858 / 31031 (n=6416) |
| 7 | Télécharger une PJ (~124 Ko) | 3006 / 7996 (n=8481) |
| 8 | Marquer lu | 988 / 2022 (n=16956) |
| 9 | Rechercher un patient | 155 / 634 (n=5061) |
| 10 | Ouvrir la page d'un dossier patient | 11065 / 29009 (n=6144) |
| 11 | Fiche patient complète (ressenti médecin) | 25778 / 58192 (n=3070) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 14.5 / 20 | 34.0 / 60 | 3774 | 58192 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3823 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 4886 ms en moyenne, 60005 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 746 / 1272 (magasin) |
| Backends Postgres (moy/max) | 1008 / 1589 |
| PgBouncer `cl_waiting` (échant. non nuls) | 1251/2390 (52 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 1251/2390 (52 %) |
| …dont pool de **maintenance** (échant. non nuls) | 61/2390 (3 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 87893.5 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 87893.5 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 42534.9 |
| RSS par réplica api-mail, Mo (moy/max) | 1840 / 4255 (5 réplicas) |

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

⛔ **Chauffe insuffisante — les étapes 2, 3, 10, 11 ne sont pas opposables.** **86.2 %** des médecins ont terminé leur chauffe (plancher **90 %**, sur 1000 médecins) ; 258 lot(s) d'analyse perdu(s) ; 97.8 % des ouvertures de l'étape 3 servies par la base (plancher 95 %). Ces étapes sont **servies par la base des messages analysés** : une base peu peuplée les rend rapides sans rien dire de la charge visée — au tir `journey-remote-n500` du 2026-08-09, `GetMailsByUids` coûtait **55,4 ms / 7,8 requêtes** par appel contre **1 199,7 ms / 14,8** sur un tir dont la base était peuplée. **Ce tir ne mesure donc pas la capacité** : ses latences sont flattées, quelle que soit leur valeur. Relancer après une chauffe aboutie (lots `JOURNEY_WARMUP_BATCH`, task-244).

> ⚠️ Chauffe : **9954 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **79 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 231 (300) | 1147 (1500) | 84940 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 485 (300) | 48517 (1000) | 42518 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 2098 (100) | 4767 (500) | 21240 | ⛔ non opposable — chauffe insuffisante |
| 4 | Ouvrir un message froid (fetch IMAP) | 741 (800) | 1459 (2500) | 4009 | ✅ |
| 5 | Recherche | 7943 (500) | 37538 (2000) | 6394 | ❌ |
| 6 | Envoi (acquittement UI) | 4858 (1000) | 31031 (3000) | 6416 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 3006 (500) | 7996 (2000) | 8481 | ❌ |
| 8 | Marquer lu | 988 (200) | 2022 (1000) | 16956 | ❌ |
| 9 | Rechercher un patient | 155 (300) | 634 (1500) | 5061 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 11065 (500) | 29009 (2000) | 6144 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 25778 (1500) | 58192 (4000) | 3070 | ⛔ non opposable — chauffe insuffisante |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 42518 | 15940 | 48517 | 677744.3 | 68.0 % |
| 🔴 | Recherche (`search`) | 6394 | 10940 | 37538 | 69950.4 | 7.0 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 6416 | 9920 | 31031 | 63645.3 | 6.4 % |
| 🔴 | Ouvrir un message enrichi (servi base) (`read_content`) | 21240 | 2342 | 4767 | 49741.9 | 5.0 % |
| 🔴 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 3070 | 12147 | 29009 | 37291.6 | 3.7 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 84940 | 386 | 1147 | 32785.5 | 3.3 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 8481 | 3634 | 7996 | 30823.8 | 3.1 % |
| 🔴 | Marquer lu (`mark_read`) | 16956 | 1213 | 2022 | 20568.4 | 2.1 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 1887 | 4563 | 10847 | 8611.0 | 0.9 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 4009 | 886 | 1459 | 3553.9 | 0.4 % |
| 🟠 | Rechercher un patient (`patient_search`) | 5061 | 238 | 634 | 1204.4 | 0.1 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 3074 | 273 | 445 | 840.7 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 7 🔴 · 3 🟠 · 2 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Ouvrir / rafraîchir l'inbox** (`read_list`, 677744.3 s, 68.0 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (15940 ms)
  - **dispersion p95/p50 = 100.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 69950.4 s, 7.0 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (10940 ms)
  - **dispersion p95/p50 = 4.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Envoi (acquittement UI)** (`send`, 63645.3 s, 6.4 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (9920 ms)
  - **dispersion p95/p50 = 6.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 49741.9 s, 5.0 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2342 ms)
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 37291.6 s, 3.7 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (12147 ms)
- **Arrivée dashboard** (`dashboard`, 32785.5 s, 3.3 %)
  - **dispersion p95/p50 = 5.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 30823.8 s, 3.1 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (3634 ms)
- **Marquer lu** (`mark_read`, 20568.4 s, 2.1 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1213 ms)
- **Traitement (plateforme)** (`treatment`, 8611.0 s, 0.9 %)
  - **coût par appel élevé** (4563 ms)
- **Rechercher un patient** (`patient_search`, 1204.4 s, 0.1 %)
  - **dispersion p95/p50 = 4.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation

> Re-tir de vérification (task-292). Les candidats mécaniques ci-dessus sont ceux du palier 1000 sur base hydratée (référence 26/08, E015). Findings du journal :

- **F-292-2 invalidé, remède retiré** : le drain parallèle (8) coûte 15 873 refus PgBouncer et 1,37 % d'erreurs. La ressource rare est la création de backends Postgres (~3,8/s, login 10-16 s) : ne jamais ajouter de logins concurrents sur un serveur qui en manque. `DrainParallelism` = 1 par défaut.
- **F-292-1b — le plafond d'essais doit distinguer poison et transitoire** : 1 034 traces perdues par un plafond appliqué à des timeouts. Corrigé (`IsPoison` : SqlState 22/23/42 uniquement).
- **F-292-6 — la mémoire du conteneur Postgres est la cause racine du jour** (mesurée) : cgroup à 12 Go pour 54 Go de bases, +15 600 échecs d'allocation/s, login à 15 s, `DataFileRead` sur 27 backends. Remède : limite 24-32 Go, `shared_buffers` 8 Go (task-294, `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md`). Gain attendu : logins < 1 s, disparition des `08P01`, drain d'audit qui suit l'émission — à mesurer par un tir A/B mémoire.
- **F-292-3 (cache Redis)** : voir le rapport A/B — Redis sature sur le cache seul ; le spill en pâtit (contre-pression prématurée). Finding cache à proposer en `/po` (taille des entrées `mail:email:*`).
- **Borne du spill** : 60 → 180 min (360 000 entrées, ~350 Mo Redis au pire), dimensionnée sur la durée de saturation observée (80 min) et le déficit de drain mesuré (~1 200/min), plus une marge.


## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 21235 | 381 | 1179 | 11065.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 21235 | 44 | 639 | 4456.2 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 21235 | 380 | 1609 | 13484.1 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 21235 | 27 | 628 | 3779.6 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 21259 | 71 | 466 | 3584.0 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 21259 | 31795 | 52707 | 674160.3 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folders`** (1609 ms de p95, 380 ms de p50, n=21235), qui porte **aussi** le temps serveur de l'étape (13484.1 s, 41 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (52707 ms de p95, 31795 ms de p50, n=21259), qui porte **aussi** le temps serveur de l'étape (674160.3 s, 99 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 36669 | 1662.3 | 944.8 | 3821.1 | 4755.1 | 78144.4 |
| attachment,palier:1000 | 8481 | 3634.5 | 3006.2 | 5410.9 | 7996.3 | 38273.0 |
| attachment,palier:transition | 116 | 1943.3 | 1819.1 | 3424.3 | 3839.2 | 8152.7 |
| dashboard | 369512 | 266.1 | 111.7 | 692.0 | 945.6 | 60000.9 |
| dashboard,call:coverage,palier:1000 | 21235 | 178.0 | 26.9 | 501.8 | 627.8 | 5813.1 |
| dashboard,call:coverage,palier:transition | 8 | 32.6 | 35.4 | 45.1 | 50.3 | 55.6 |
| dashboard,call:folder,palier:1000 | 21235 | 521.1 | 381.3 | 903.3 | 1179.3 | 38322.8 |
| dashboard,call:folder,palier:transition | 8 | 334.8 | 372.4 | 416.9 | 425.7 | 434.6 |
| dashboard,call:folders,palier:1000 | 21235 | 635.0 | 380.4 | 1273.9 | 1608.9 | 37640.4 |
| dashboard,call:folders,palier:transition | 8 | 16.5 | 15.8 | 19.9 | 21.0 | 22.1 |
| dashboard,call:today,palier:1000 | 21235 | 209.8 | 44.5 | 500.1 | 639.1 | 16020.0 |
| dashboard,call:today,palier:transition | 8 | 376.7 | 370.8 | 409.2 | 418.9 | 428.5 |
| dashboard,palier:1000 | 84940 | 386.0 | 230.9 | 858.9 | 1146.8 | 38322.8 |
| dashboard,palier:transition | 32 | 190.1 | 48.1 | 400.8 | 417.9 | 434.6 |
| mark_read | 73839 | 603.5 | 477.6 | 1249.3 | 1537.7 | 59997.9 |
| mark_read,palier:1000 | 16956 | 1213.0 | 987.7 | 1628.4 | 2021.9 | 38226.6 |
| mark_read,palier:transition | 228 | 657.0 | 675.7 | 1142.7 | 1248.9 | 2235.4 |
| patient_docs | 199137 | 1767.7 | 186.1 | 5668.3 | 7598.7 | 60027.6 |
| patient_docs,palier:1000 | 44611 | 4165.8 | 3776.2 | 8688.6 | 10646.4 | 60027.6 |
| patient_docs,palier:transition | 871 | 1355.9 | 382.1 | 4253.1 | 5836.9 | 9035.8 |
| patient_dossier | 13495 | 5078.0 | 1406.3 | 16854.4 | 22971.1 | 44868.2 |
| patient_dossier,palier:1000 | 3070 | 12147.1 | 11064.7 | 25528.8 | 29008.6 | 44868.2 |
| patient_dossier,palier:transition | 38 | 3317.1 | 1607.5 | 9029.2 | 10354.4 | 15489.7 |
| patient_opposition | 13495 | 120.5 | 54.4 | 275.7 | 328.2 | 24910.5 |
| patient_opposition,palier:1000 | 3074 | 273.5 | 239.1 | 359.7 | 445.1 | 24910.5 |
| patient_opposition,palier:transition | 57 | 153.8 | 178.4 | 259.5 | 320.4 | 443.3 |
| patient_search | 21888 | 119.7 | 51.6 | 302.2 | 457.2 | 14034.4 |
| patient_search,palier:1000 | 5061 | 238.0 | 155.0 | 466.2 | 634.1 | 5423.9 |
| patient_search,palier:transition | 62 | 128.4 | 89.1 | 264.9 | 474.0 | 623.4 |
| read_content | 92324 | 1056.1 | 549.3 | 2532.9 | 3036.2 | 59998.3 |
| read_content,palier:1000 | 21240 | 2341.9 | 2098.0 | 3441.9 | 4766.7 | 55481.2 |
| read_content,palier:transition | 365 | 1171.3 | 1104.1 | 2303.1 | 2687.2 | 7383.2 |
| read_content_cold | 17561 | 654.0 | 569.5 | 968.6 | 1215.3 | 38167.8 |
| read_content_cold,palier:1000 | 4009 | 886.5 | 741.3 | 1167.1 | 1458.8 | 27827.8 |
| read_content_cold,palier:transition | 39 | 611.7 | 592.0 | 789.4 | 940.6 | 1320.2 |
| read_list | 184756 | 6692.6 | 189.2 | 28583.9 | 38582.1 | 60028.2 |
| read_list,call:emails,palier:1000 | 21259 | 31711.8 | 31795.1 | 48517.6 | 52707.3 | 60028.2 |
| read_list,call:emails,palier:transition | 71 | 17034.7 | 20072.7 | 23840.4 | 24383.6 | 25142.1 |
| read_list,call:folder,palier:1000 | 21259 | 168.6 | 71.5 | 325.6 | 466.2 | 18313.2 |
| read_list,call:folder,palier:transition | 71 | 75.5 | 39.1 | 155.4 | 240.7 | 423.5 |
| read_list,palier:1000 | 42518 | 15940.2 | 485.4 | 43131.2 | 48517.5 | 60028.2 |
| read_list,palier:transition | 142 | 8555.1 | 229.2 | 22299.5 | 23822.8 | 25142.1 |
| search | 27522 | 7284.6 | 4349.7 | 18041.8 | 33842.4 | 81676.4 |
| search,palier:1000 | 6394 | 10940.0 | 7943.1 | 22548.1 | 37537.5 | 68958.5 |
| search,palier:transition | 37 | 6885.7 | 4992.8 | 8505.0 | 15920.3 | 43228.9 |
| send | 27640 | 6396.5 | 885.7 | 16248.2 | 29109.2 | 120001.2 |
| send,palier:1000 | 6416 | 9919.8 | 4858.2 | 28906.1 | 31031.2 | 95412.3 |
| send,palier:transition | 105 | 4412.6 | 1356.9 | 11043.0 | 11830.6 | 13871.8 |
| treatment | 8834 | 1857.4 | 771.7 | 4887.5 | 6380.1 | 41556.1 |
| treatment,palier:1000 | 1887 | 4563.3 | 3627.7 | 8059.1 | 10847.2 | 41556.1 |
| treatment,palier:transition | 48 | 2530.5 | 2088.0 | 5723.6 | 7397.2 | 10970.1 |
| warmup | 11000 | 4886.3 | 571.9 | 13014.5 | 25726.2 | 60005.2 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-09T15:47:54.327000+00:00 → 2026-09-09T19:18:58.370000+00:00 (12664 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-174753.csv`) | ✅ 257648 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-46012` | 0.53 | 8 | 38 | 0.030 | 82.06 |
| `DESKTOP-DEV-X2C-47788` | 0.56 | 6 | 22 | 0.029 | 80.87 |
| `DESKTOP-DEV-X2C-53696` | 0.62 | 10 | 39 | 0.034 | 76.90 |
| `DESKTOP-DEV-X2C-56584` | 0.55 | 6 | 40 | 0.029 | 80.01 |
| `DESKTOP-DEV-X2C-58936` | 0.52 | 5 | 20 | 0.024 | 61.24 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#32776` | 0.01 | 0.19 | 40 |
| `com.docker.backend#34112` | 1.82 | 5.01 | 1576 |
| `dcp#17592` | 0.00 | 0.24 | 12 |
| `dcp#27092` | 0.77 | 2.27 | 1344 |
| `dcp#43524` | 0.00 | 0.09 | 12 |
| `dcp#47176` | 0.00 | 0.04 | 12 |
| `dcp#52460` | 0.00 | 0.14 | 40 |
| `dcp#53932` | 0.00 | 0.29 | 12 |
| `dcp#53992` | 0.00 | 0.04 | 12 |
| `dcp#54124` | 0.00 | 0.19 | 12 |
| `dcp#54392` | 0.00 | 0.04 | 12 |
| `dcp#8376` | 0.00 | 0.04 | 12 |
| `k6#31096` | 0.18 | 3.02 | 2140 |
| `mss.mail.api#46012` | 0.31 | 1.65 | 3604 |
| `mss.mail.api#47788` | 0.32 | 1.60 | 3632 |
| `mss.mail.api#53696` | 0.36 | 1.73 | 4255 |
| `mss.mail.api#56584` | 0.30 | 1.59 | 3436 |
| `mss.mail.api#58936` | 0.30 | 1.44 | 3197 |
| `vmmemWSL#35744` | 8.67 | 16.82 | 33368 |
| `loadtest-otel-collector-vzjxsbcs` | 0.03 | 0.24 | 108 |
| `loadtest-pgbouncer-dxnfqqgs` | 0.55 | 1.01 | 28 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.19 | 182 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.16 | 348 |
| `mss-mail-rabbitmq-ydedmqrf` | 0.01 | 0.05 | 123 |
| `mss-mail-redis-b6152948` | 0.22 | 1.21 | 2637 |
| `mss-mail-seq-b6152948` | 0.01 | 0.23 | 181 |
| `postgres-pgvector` | 6.51 | 15.09 | 11510 |

- **Hôte** : CPU 68.6 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 71
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 3655, cl_waiting max 153, cl_waiting_maintenance max 3, cl_waiting_practitioner max 153, count max 1002, maxwait_maintenance_ms max 42535, maxwait_ms max 87893, maxwait_practitioner_ms max 87893, sv_active max 520, sv_idle max 1014
- **Backends Postgres** : practitioner_databases max 1815, total max 1829

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 6771.6 | 2523 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 12521.7 | 2529 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 22134.3 | 2525 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 2525 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 8833.3 | 2523 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 25444.4 | 2518 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 23111.1 | 2522 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 60000.0 | 2522 |
| `api/v{version:apiVersion}/Mail/sendmail` | 55081.4 | 2490 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 2141.7 | 2503 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 52285.7 | 2503 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 1325.0 | 2503 |
| `api/v{version:apiVersion}/Search/semantic` | 56500.0 | 2510 |
| `api/v{version:apiVersion}/Settings` | 241.3 | 9 |
| `api/v{version:apiVersion}/Settings/getsettings` | 9.3 | 9 |
| `api/v{version:apiVersion}/Sync/coverage` | 3947.6 | 2523 |

- **p95 client global (k6)** : 11079.3 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -48920.7 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.55 |
| Documents CDA /s | 0.58 |
| Durée traitement CDA (s, p95) | 1.14 |
| Événements de session IMAP /s | 1.60 |
| Recherches (s, p95) | 56.500 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.0 | 2354.9 | 27000 | 11.1 (0.5 %), p95 3875 | 2196.7 (93.3 %), p95 27000 | 147.0 (6.2 %), p95 2200 |
| `GetMail` | 11.3 | 1330.2 | 22684 | 95.2 (7.2 %), p95 3193 | 1172.6 (88.2 %), p95 18561 | 62.4 (4.7 %), p95 166 |
| `GetMailsByUids` | 14.6 | 9267.6 | 60000 | 2.9 (0.0 %), p95 187 | 1186.9 (12.8 %), p95 9112 | 8077.7 (87.2 %), p95 59853 |

- **`EnrichPersistMail`** — sur 2354.9 ms en moyenne (8.0 requête(s) SQL par appel) : 11.1 ms attente d'une connexion, 2196.7 ms exécution SQL, 147.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 1330.2 ms en moyenne (11.3 requête(s) SQL par appel) : 95.2 ms attente d'une connexion, 1172.6 ms exécution SQL, 62.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 9267.6 ms en moyenne (14.6 requête(s) SQL par appel) : 2.9 ms attente d'une connexion, 1186.9 ms exécution SQL, 8077.7 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.0 | 62.4 | 6246.1 | 0.9 | 1.3 | 0.9 | 2.5 | non relevé | 0.0 | 0.9 | 2.3 | 0.1 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 235.7 | 8077.7 | 34275.2 | 21.1 | 32.3 | 21.1 | 34.3 | 21.1 | 0.0 | 21.1 | 6.6 | 0.0 | 21.0 | 50.8 | 6.1 |

- **`GetMail`** — sur 62.4 ms de matérialisation, l'appel a construit 10.0 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.5 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.3 résultats de biologie, 0.1 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **6246.1 µs**.

- **`GetMailsByUids`** — sur 8077.7 ms de matérialisation, l'appel a construit 235.7 objets, dont 21.1 messages, 32.3 étiquettes, 21.1 destinataires, 34.3 pièces jointes, 21.1 identifiants enrichis, 0.0 acquittements, 21.1 documents médicaux, 6.6 résultats de biologie, 0.0 éléments de synthèse, 21.0 corps de messages, 50.8 objets de fil, 6.1 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **34275.2 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **6.5 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.3 | 3099.6 | 29000 | 132.2 (4.3 %), p95 687 | 31.9 (1.0 %), p95 941 | 30.2 (1.0 %), p95 691 | 2601.3 (83.9 %), p95 29000 | 303.9 (9.8 %), p95 4583 |

- **Enrichir un message** — sur 3099.6 ms en moyenne (5.3 message(s) par requête) : 132.2 ms fetch IMAP, 31.9 ms extraction XDM, 30.2 ms parsing CDA, 2601.3 ms écritures base, 303.9 ms le reste (DTO, notifications). **Poste dominant : écritures base.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 3781.4 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 5049.6 | 18031 | 0.0 (0.0 %), p95 5 | 3975.0 (78.7 %), p95 14372 | 182.5 (3.6 %), p95 633 | 323.0 (6.4 %), p95 487 | 432.4 (8.6 %), p95 1068 | 569.1 (11.3 %), p95 4540 |

- **Envoyer un message** — sur 5049.6 ms en moyenne : 0.0 ms garde d'opposition, 3975.0 ms construction MIME, 182.5 ms obtention de session SMTP, 323.0 ms transmission + acquittement, 432.4 ms archivage Sent, 569.1 ms le reste. **Poste dominant : construction MIME.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.488 | 2.425 | 0.05 |
| `imap_session` | 0.642 | 6.467 | 42.36 |
| `in_process_fetch` | 0.005 | 2.425 | 0.05 |
| `smtp_session` | 0.055 | 22.833 | 3.60 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.027 | 6.219 | 4.250 | 6.406 | 3.60 |
| `EnrichEmails` | 0.005 | 3.375 | 2.425 | 3.375 | 0.87 |
| `GetAttachmentStream` | 1.900 | 8.000 | 9.875 | 8.125 | 1.11 |
| `GetEmailContent` | 0.045 | 6.400 | 4.875 | 6.425 | 2.36 |
| `GetFolders` | 0.342 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 5.000 | 5.44 |
| `ProcessEmailUid` | 0.005 | 2.425 | — | 2.425 | 0.05 |
| `ReadFolder` | 1.158 | 6.387 | ≥ 60 ⚠️ | 6.145 | 22.87 |
| `UpdateFlag` | 0.944 | 8.514 | 4.875 | 8.514 | 9.04 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.499** | 0.689 | 6.406 | 3.1 % |
| `EnrichEmails` | **0.453** | 0.738 | 3.375 | 1.4 % |
| `GetAttachmentStream` | **2.486** | 4.562 | 8.125 | 100.0 % |
| `GetEmailContent` | **0.838** | 1.180 | 6.425 | 3.4 % |
| `GetFolders` | **0.377** | 0.474 | 5.000 | 2.5 % |
| `ProcessEmailUid` | **0.487** | 0.487 | 0.738 | 0.0 % |
| `ReadFolder` | **0.554** | 0.672 | 6.145 | 3.4 % |
| `UpdateFlag` | **0.688** | 0.829 | 8.514 | 3.1 % |

- 🟠 **`AppendToSent` : pointe non représentative.** Médiane **0.499 s**, p90 0.689 s, mais une pointe à 6.406 s sur 3.1 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🟠 **`EnrichEmails` : pointe non représentative.** Médiane **0.453 s**, p90 0.738 s, mais une pointe à 3.375 s sur 1.4 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🔴 **`GetAttachmentStream` : détention tenue en régime** — médiane 2.486 s et **100.0 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🟠 **`GetEmailContent` : pointe non représentative.** Médiane **0.838 s**, p90 1.180 s, mais une pointe à 6.425 s sur 3.4 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🟠 **`GetFolders` : pointe non représentative.** Médiane **0.377 s**, p90 0.474 s, mais une pointe à 5.000 s sur 2.5 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🟠 **`ReadFolder` : pointe non représentative.** Médiane **0.554 s**, p90 0.672 s, mais une pointe à 6.145 s sur 3.4 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🟠 **`UpdateFlag` : pointe non représentative.** Médiane **0.688 s**, p90 0.829 s, mais une pointe à 8.514 s sur 3.1 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.

> ⚠️ **Pourquoi cette table existe** (task-276). La table qui la précède réduit chaque série à sa **pointe**. Au tir du 2026-08-29, `ReadFolder` y valait 11,871 s — lu comme « la fusion de task-270 a allongé la section critique », alors que sa médiane en régime valait 0,469 s, **sous** les 0,692 s de l'opération qu'elle remplace. La pointe était réelle ; la conclusion qu'on en tirait, non. Même famille de piège que les buckets en millisecondes (task-211), le plafond d'histogramme (task-245) et la saturation lue comme un timeout (task-271).
| Voie | Acquisitions /s |
|---|---|
| `read` | 42.36 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

✅ **Lecture rétablie** pour `GetFolders` : l'agrégat est saturé (« ≥ 60 s », c'est-à-dire *non mesuré* — `histogram_quantile` rend la dernière borne finie quand le quantile tombe dans `+Inf`), mais l'exploitation, elle, tient dans l'instrument. La queue appartient à la chauffe, pas au régime établi.

**Archivage vs reste** : `AppendToSent` attend 0.027 s au p95, contre 1.900 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 153.00 clients | 0 clients | 100.0 % | 52.3 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 15.09 cœurs | 24 cœurs | 62.9 % | 0.0 % — transitoire |
| processus `k6#31096` (CPU) | 3.02 cœurs | 24 cœurs | 12.6 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-53696` | 10.00 éléments | 100 éléments | 10.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#53696` (CPU) | 1.73 cœurs | 24 cœurs | 7.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#46012` (CPU) | 1.65 cœurs | 24 cœurs | 6.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#47788` (CPU) | 1.60 cœurs | 24 cœurs | 6.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#56584` (CPU) | 1.59 cœurs | 24 cœurs | 6.6 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 52.3 % des échantillons de la fenêtre.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 84086 — dont **84086** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Comptages API Seq bornés `rangeStartUtc`/`rangeEndUtc` + `@Timestamp` (15:47Z → 19:30Z).

| Requête | Compte | Lecture |
|---|---|---|
| `@Level = 'Fatal'` = Critical `… it is LOST` | **1 034** | Toutes du nouveau chemin `ParkFailedTraceAsync` après 5 essais transitoires (timeouts Npgsql au rejeu). Défaut de conception du plafond, corrigé : poison seulement. |
| `[Audit] Channel full` | 96 679 | Canal plein de 19h50 à la fin. |
| `[Audit] Journal saturated` / `parked … refused` | 38 / 18 | Contre-pression **avant la borne** (70 k / 120 k) : le spill Redis n'a pas répondu. |
| `Spill buffer unreachable` / `threw` | 39 | Redis mono-thread à 1,1 cœur sur le cache applicatif. |
| `Failed to persist a batch` / `Failed to persist audit trace` | 62 211 / 70 942 | Timeouts de login Npgsql (15 s par défaut, login à 10-16 s). |
| `[Cache] Timeout getting key` | 8 778 | 21 835 le matin, 6 568 sans journal. |
| `08P01` | **15 873** (log PgBouncer : 15 873 refus) | 646 le matin : la concurrence des logins directs a fait basculer le pooler en rejet. |
| `HTTP … Status=500` / `503` | 14 280 / 8 | 724 / 11 le matin. |
| Error+Fatal / Warning | 174435 / 208 611 | 2 454 / 185 105 le matin. |
| scratch `mss-ihe-xdm` | 0 (garde : 1 recréation à 14h41, pendant le tir A/B) | — |

