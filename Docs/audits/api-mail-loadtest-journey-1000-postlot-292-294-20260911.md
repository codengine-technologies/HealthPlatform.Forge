# Rapport de tir — journey-1000-postlot-292-294-20260911

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-postlot-292-294-20260911-123951.json`.

## 🔴 ROUGE — ce tir ne peut pas servir à conclure

Quelque chose s'est mal passé pendant la mesure. Les chiffres de ce rapport ne décrivent pas fidèlement l'application : il faut corriger la cause et **refaire le tir** avant d'en tirer une conclusion.

- 11.98 % des demandes ont échoué (au-delà du plafond de 1 %)
- le multiplexeur PostgreSQL a **refusé** des connexions (110693 refus `server_login_retry` sur la fenêtre) au lieu de les faire attendre : les demandes touchées ont reçu une erreur, et les latences des autres sont des bornes optimistes

À instruire une fois le tir refait :
- à 1000 médecins, 10 étape(s) dépassent le temps de réponse attendu : « Arrivée dashboard », « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) »
- une étape ne mesure pas ce que son nom annonce — son chiffre décrit un autre geste
- 12 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 13 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1176820 — **débit émergent global** : 92.9 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 101584 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 92.9 | **1751.5** | 151.5 | **8208.8** | — | 300000.1 | 11.98 | 88.2 | 0 | 0 | 61680/247 |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 323343 | 25.66 | 27.18 | 1011.9 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 152 / 2353 (n=116894) |
| 2 | Ouvrir / rafraîchir l'inbox | 279 / 15007 (n=58482) |
| 3 | Ouvrir un message enrichi (servi base) | 407 / 2945 (n=29282) |
| 4 | Ouvrir un message froid (fetch IMAP) | 571 / 2959 (n=5565) |
| 5 | Recherche | 2650 / 15191 (n=8859) |
| 6 | Envoi (acquittement UI) | 800 / 30042 (n=8700) |
| 7 | Télécharger une PJ (~124 Ko) | 560 / 4499 (n=11507) |
| 8 | Marquer lu | 297 / 2894 (n=23341) |
| 9 | Rechercher un patient | 32 / 287 (n=6651) |
| 10 | Ouvrir la page d'un dossier patient | 806 / 5839 (n=8248) |
| 11 | Fiche patient complète (ressenti médecin) | 2515 / 183715 (n=4125) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 10.4 / 20 | 24.5 / 60 | 5676 | 183715 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3722 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 11469 ms en moyenne, 60012 ms au pire — soit **0.1 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 713 / 1192 (magasin) |
| Backends Postgres (moy/max) | 850 / 1457 |
| PgBouncer `sv_login` — backends en login (moy/max) | 16 / 467 |
| PgBouncer `cl_waiting` (échant. non nuls) | 165/1243 (13 %) |
| …dont bases **praticien** (échant. non nuls) | 165/1243 (13 %) |
| …dont pool de **maintenance** (échant. non nuls) | 0/1243 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 19147.0 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 19147.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 0.0 |
| PgBouncer refus `server_login_retry` (total du palier) | 109157 🔴 refus |
| RSS par réplica api-mail, Mo (moy/max) | 1103 / 3866 (5 réplicas) |

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

⛔ **Chauffe insuffisante — les étapes 2, 3, 10, 11 ne sont pas opposables.** **62.6 %** des médecins ont terminé leur chauffe (plancher **90 %**, sur 1000 médecins) ; 3685 lot(s) d'analyse perdu(s) ; 85.6 % des ouvertures de l'étape 3 servies par la base (plancher 95 %). Ces étapes sont **servies par la base des messages analysés** : une base peu peuplée les rend rapides sans rien dire de la charge visée — au tir `journey-remote-n500` du 2026-08-09, `GetMailsByUids` coûtait **55,4 ms / 7,8 requêtes** par appel contre **1 199,7 ms / 14,8** sur un tir dont la base était peuplée. **Ce tir ne mesure donc pas la capacité** : ses latences sont flattées, quelle que soit leur valeur. Relancer après une chauffe aboutie (lots `JOURNEY_WARMUP_BATCH`, task-244).

> ⚠️ Chauffe : **10032 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **80 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

⛔ **Étape 3 « servi base » refusée — elle ne mesure pas ce que son nom annonce.** Seules **85.6 %** de ses ouvertures portent les documents de l'analyse, pour un plancher de 95 % : le reste a basculé sur le serveur de messagerie, donc cette étape mesure en partie des ouvertures **froides** et son chiffre n'est **pas** un verdict, quelle que soit sa valeur (pour situer : 12.07 sollicitations/s du serveur de messagerie sur la fenêtre, étapes 3/4 et rafale dossier confondues). Causes connues : bande chaude non analysée par la chauffe (task-224, défaut 5 — les 440 ms du 2026-08-03), ou mails de chauffe estampillés **génération 0** (UIDVALIDITY) donc inatteignables en base (certification du 2026-08-06 — la chauffe doit lister les dossiers AVANT d'analyser).

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 152 (300) | 2353 (1500) | 116894 | ❌ |
| 2 | Ouvrir / rafraîchir l'inbox | 279 (300) | 15007 (1000) | 58482 | ⛔ non opposable — chauffe insuffisante |
| 3 | Ouvrir un message enrichi (servi base) | 407 (100) | 2945 (500) | 29282 | ⛔ étape mal nommée — mesure du froid |
| 4 | Ouvrir un message froid (fetch IMAP) | 571 (800) | 2959 (2500) | 5565 | ❌ |
| 5 | Recherche | 2650 (500) | 15191 (2000) | 8859 | ❌ |
| 6 | Envoi (acquittement UI) | 800 (1000) | 30042 (3000) | 8700 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 560 (500) | 4499 (2000) | 11507 | ❌ |
| 8 | Marquer lu | 297 (200) | 2894 (1000) | 23341 | ❌ |
| 9 | Rechercher un patient | 32 (300) | 287 (1500) | 6651 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 806 (500) | 5839 (2000) | 8248 | ⛔ non opposable — chauffe insuffisante |
| 11 | Fiche patient complète (ressenti médecin) | 2515 (1500) | 183715 (4000) | 4125 | ⛔ non opposable — chauffe insuffisante |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 58482 | 2871 | 15007 | 167892.6 | 36.2 % |
| 🔴 | Arrivée dashboard (`dashboard`) | 116894 | 1095 | 2353 | 127992.3 | 27.6 % |
| 🔴 | Ouvrir un message enrichi (servi base) (`read_content`) | 29282 | 1202 | 2945 | 35194.8 | 7.6 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 8700 | 4041 | 30042 | 35158.6 | 7.6 % |
| 🔴 | Recherche (`search`) | 8859 | 3701 | 15191 | 32789.4 | 7.1 % |
| 🔴 | Marquer lu (`mark_read`) | 23341 | 1105 | 2894 | 25787.8 | 5.6 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 11507 | 1516 | 4499 | 17447.2 | 3.8 % |
| 🔴 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 5565 | 1355 | 2959 | 7539.3 | 1.6 % |
| 🔴 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 4125 | 1715 | 5839 | 7073.4 | 1.5 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 2838 | 1891 | 7435 | 5365.9 | 1.2 % |
| 🟠 | Rechercher un patient (`patient_search`) | 6651 | 163 | 287 | 1082.8 | 0.2 % |
| 🟠 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 4123 | 123 | 227 | 506.4 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 9 🔴 · 3 🟠 · 0 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Ouvrir / rafraîchir l'inbox** (`read_list`, 167892.6 s, 36.2 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2871 ms)
  - **dispersion p95/p50 = 53.8×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Arrivée dashboard** (`dashboard`, 127992.3 s, 27.6 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1095 ms)
  - **dispersion p95/p50 = 15.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 35194.8 s, 7.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1202 ms)
  - **dispersion p95/p50 = 7.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Envoi (acquittement UI)** (`send`, 35158.6 s, 7.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (4041 ms)
  - **dispersion p95/p50 = 37.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 32789.4 s, 7.1 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (3701 ms)
  - **dispersion p95/p50 = 5.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Marquer lu** (`mark_read`, 25787.8 s, 5.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1105 ms)
  - **dispersion p95/p50 = 9.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 17447.2 s, 3.8 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1516 ms)
  - **dispersion p95/p50 = 8.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message froid (fetch IMAP)** (`read_content_cold`, 7539.3 s, 1.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1355 ms)
  - **dispersion p95/p50 = 5.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 7073.4 s, 1.5 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1715 ms)
  - **dispersion p95/p50 = 7.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Traitement (plateforme)** (`treatment`, 5365.9 s, 1.2 %)
  - **coût par appel élevé** (1891 ms)
  - **dispersion p95/p50 = 12.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Rechercher un patient** (`patient_search`, 1082.8 s, 0.2 %)
  - **dispersion p95/p50 = 8.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir la page d'un dossier patient** (`patient_opposition`, 506.4 s, 0.1 %)
  - **dispersion p95/p50 = 5.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 29228 | 392 | 3106 | 40567.7 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 29224 | 120 | 1994 | 31134.4 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 29222 | 182 | 2574 | 32032.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 29220 | 59 | 914 | 24257.7 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 29241 | 133 | 2192 | 27888.8 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 29241 | 3655 | 15010 | 140003.8 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (3106 ms de p95, 392 ms de p50, n=29228), qui porte **aussi** le temps serveur de l'étape (40567.7 s, 32 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (15010 ms de p95, 3655 ms de p50, n=29241), qui porte **aussi** le temps serveur de l'étape (140003.8 s, 83 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 40589 | 1124.8 | 356.6 | 1927.7 | 3459.9 | 120001.9 |
| attachment,palier:1000 | 11507 | 1516.2 | 559.6 | 2116.2 | 4499.5 | 120001.1 |
| attachment,palier:transition | 166 | 501.1 | 262.5 | 1193.0 | 1630.3 | 4509.8 |
| dashboard | 408602 | 746.1 | 90.5 | 768.0 | 1288.7 | 60010.9 |
| dashboard,call:coverage,palier:1000 | 29220 | 830.2 | 58.5 | 315.3 | 914.4 | 60004.9 |
| dashboard,call:coverage,palier:transition | 8 | 38.1 | 40.7 | 64.3 | 67.0 | 69.8 |
| dashboard,call:folder,palier:1000 | 29228 | 1388.0 | 392.1 | 1425.5 | 3105.7 | 60007.2 |
| dashboard,call:folder,palier:transition | 8 | 417.4 | 455.0 | 503.1 | 541.2 | 579.4 |
| dashboard,call:folders,palier:1000 | 29222 | 1096.2 | 182.0 | 996.4 | 2574.1 | 60004.7 |
| dashboard,call:folders,palier:transition | 8 | 19.8 | 18.8 | 26.3 | 29.7 | 33.1 |
| dashboard,call:today,palier:1000 | 29224 | 1065.4 | 120.0 | 804.2 | 1994.3 | 60010.9 |
| dashboard,call:today,palier:transition | 8 | 454.6 | 440.6 | 498.1 | 505.0 | 511.9 |
| dashboard,palier:1000 | 116894 | 1094.9 | 152.4 | 980.6 | 2352.6 | 60010.9 |
| dashboard,palier:transition | 32 | 232.5 | 65.9 | 471.5 | 501.1 | 579.4 |
| mark_read | 81615 | 749.0 | 146.4 | 1006.5 | 1972.6 | 60001.5 |
| mark_read,palier:1000 | 23341 | 1104.8 | 297.0 | 1316.1 | 2894.1 | 60001.5 |
| mark_read,palier:transition | 302 | 305.3 | 144.6 | 781.0 | 1120.8 | 2667.4 |
| patient_docs | 186092 | 3569.0 | 170.0 | 2867.1 | 10270.1 | 60027.8 |
| patient_docs,palier:1000 | 42837 | 8440.1 | 839.1 | 59996.5 | 59998.9 | 60027.8 |
| patient_docs,palier:transition | 488 | 314.0 | 187.8 | 804.0 | 1062.8 | 2058.4 |
| patient_dossier | 14474 | 1741.2 | 560.7 | 4677.5 | 7122.9 | 59997.2 |
| patient_dossier,palier:1000 | 4125 | 1714.8 | 806.0 | 4284.7 | 5838.6 | 59996.9 |
| patient_dossier,palier:transition | 56 | 675.3 | 433.4 | 1496.2 | 2410.3 | 3517.9 |
| patient_opposition | 14474 | 83.1 | 22.7 | 115.6 | 211.4 | 59999.6 |
| patient_opposition,palier:1000 | 4123 | 122.8 | 45.7 | 153.6 | 227.2 | 59999.0 |
| patient_opposition,palier:transition | 59 | 24.9 | 11.5 | 61.4 | 85.0 | 181.4 |
| patient_search | 23468 | 115.2 | 14.9 | 137.2 | 290.5 | 60030.5 |
| patient_search,palier:1000 | 6651 | 162.8 | 32.3 | 178.3 | 287.4 | 60030.5 |
| patient_search,palier:transition | 95 | 96.7 | 16.9 | 229.7 | 488.9 | 1610.7 |
| read_content | 102137 | 850.6 | 225.6 | 1234.7 | 2193.8 | 60009.1 |
| read_content,palier:1000 | 29282 | 1201.9 | 406.9 | 1453.9 | 2945.4 | 60009.1 |
| read_content,palier:transition | 226 | 541.7 | 299.1 | 1179.5 | 1662.5 | 10666.5 |
| read_content_cold | 19423 | 972.7 | 498.4 | 890.5 | 1373.0 | 60003.8 |
| read_content_cold,palier:1000 | 5565 | 1354.8 | 570.6 | 1315.9 | 2958.6 | 60001.4 |
| read_content_cold,palier:transition | 57 | 669.0 | 537.9 | 1063.8 | 1186.6 | 3863.9 |
| read_list | 204288 | 2506.5 | 169.6 | 8177.9 | 14983.9 | 60009.5 |
| read_list,call:emails,palier:1000 | 29241 | 4787.9 | 3654.5 | 10913.3 | 15009.9 | 60003.6 |
| read_list,call:emails,palier:transition | 122 | 2083.6 | 1907.5 | 4879.7 | 5258.3 | 5811.0 |
| read_list,call:folder,palier:1000 | 29241 | 953.8 | 133.4 | 707.0 | 2191.7 | 60009.5 |
| read_list,call:folder,palier:transition | 122 | 375.9 | 171.7 | 699.9 | 1397.5 | 4795.0 |
| read_list,palier:1000 | 58482 | 2870.8 | 279.0 | 8855.7 | 15007.3 | 60009.5 |
| read_list,palier:transition | 244 | 1229.8 | 430.4 | 3559.8 | 4884.6 | 5811.0 |
| search | 30559 | 3897.3 | 2345.6 | 10023.7 | 15198.7 | 119999.7 |
| search,palier:1000 | 8859 | 3701.3 | 2649.7 | 7767.4 | 15191.5 | 119999.3 |
| search,palier:transition | 108 | 1453.6 | 1125.2 | 2876.9 | 3383.7 | 12181.2 |
| send | 30411 | 2648.8 | 698.4 | 1774.2 | 2962.6 | 120006.4 |
| send,palier:1000 | 8700 | 4041.2 | 800.2 | 2371.8 | 30042.2 | 120005.2 |
| send,palier:transition | 127 | 617.0 | 518.5 | 1216.0 | 1389.5 | 4227.2 |
| treatment | 9679 | 1311.6 | 379.4 | 2353.7 | 4319.2 | 300000.1 |
| treatment,palier:1000 | 2838 | 1890.7 | 617.5 | 3385.4 | 7435.2 | 299998.4 |
| treatment,palier:transition | 19 | 585.2 | 359.3 | 1392.8 | 1705.0 | 3324.3 |
| warmup | 11000 | 11468.7 | 893.0 | 59998.0 | 59999.2 | 60012.1 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-11T07:08:48.417000+00:00 → 2026-09-11T10:39:51.097000+00:00 (12663 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-090754.csv`) | ✅ 147097 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-19728` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-23624` | 0.48 | 99 | 19 | 0.023 | 210.80 |
| `DESKTOP-DEV-X2C-24364` | 0.48 | 4 | 17 | 0.015 | 255.58 |
| `DESKTOP-DEV-X2C-32508` | 0.46 | 7 | 22 | 0.022 | 210.22 |
| `DESKTOP-DEV-X2C-3376` | 0.00 | 0 | 25 | 0.000 | — |
| `DESKTOP-DEV-X2C-40016` | 1.11 | 15 | 32 | 0.040 | 645.99 |
| `DESKTOP-DEV-X2C-4036` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-45088` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-45096` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-45584` | 0.48 | 6 | 19 | 0.018 | 181.90 |
| `DESKTOP-DEV-X2C-46576` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-48592` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-52092` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-52688` | 0.00 | 0 | 25 | 0.000 | — |
| `DESKTOP-DEV-X2C-53760` | 0.00 | 0 | 24 | 0.000 | — |
| `DESKTOP-DEV-X2C-54704` | 0.00 | 0 | 25 | 0.000 | — |
| `DESKTOP-DEV-X2C-56260` | 0.00 | 0 | 25 | 0.000 | — |
| `mss-mail-api-0` | 0.17 | 1 | 25 | 0.019 | 3.83 |
| `mss-mail-api-1` | 0.13 | 1 | 25 | 0.011 | 0.60 |

> Valeurs **maximales** sur la fenêtre (19 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#31916` | 0.00 | 0.19 | 41 |
| `com.docker.backend#34656` | 1.19 | 4.97 | 769 |
| `dcp#14920` | 0.00 | 0.04 | 12 |
| `dcp#16500` | 0.51 | 1.94 | 1433 |
| `dcp#21196` | 0.00 | 0.30 | 11 |
| `dcp#21936` | 0.00 | 0.00 | 12 |
| `dcp#26332` | 0.00 | 0.00 | 12 |
| `dcp#31392` | 0.00 | 0.19 | 12 |
| `dcp#31516` | 0.00 | 0.05 | 12 |
| `dcp#35856` | 0.00 | 0.30 | 11 |
| `dcp#38420` | 0.00 | 0.30 | 40 |
| `dcp#42960` | 0.00 | 0.04 | 12 |
| `k6#47524` | 0.16 | 3.09 | 2195 |
| `mss.mail.api#23624` | 0.21 | 1.80 | 2014 |
| `mss.mail.api#24364` | 0.22 | 1.39 | 1958 |
| `mss.mail.api#32508` | 0.22 | 1.54 | 2109 |
| `mss.mail.api#40016` | 0.24 | 1.70 | 3866 |
| `mss.mail.api#45584` | 0.22 | 1.73 | 1990 |
| `vmmemWSL#34068` | 5.34 | 17.47 | 36519 |
| `loadtest-otel-collector-gvpyzunz` | 0.02 | 0.21 | 127 |
| `loadtest-pgbouncer-vzbdjgqe` | 0.32 | 0.99 | 26 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.12 | 142 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.14 | 242 |
| `mss-mail-rabbitmq-kbxthekg` | 0.00 | 0.04 | 152 |
| `mss-mail-redis-b6152948` | 0.12 | 1.14 | 2294 |
| `mss-mail-seq-b6152948` | 0.01 | 0.53 | 164 |
| `postgres-pgvector` | 3.11 | 16.40 | 11704 |

- **Hôte** : CPU 51.7 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 60
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 2404, cl_waiting max 170, cl_waiting_maintenance max 0, cl_waiting_practitioner max 170, count max 1001, login_retry_delta max 5733, maxwait_maintenance_ms max 0, maxwait_ms max 19147, maxwait_practitioner_ms max 19147, sv_active max 207, sv_idle max 1016, sv_login max 467
- **Backends Postgres** : direct max 1, idle_over_60s max 996, pooler max 1457, practitioner_databases max 1451, started_last_60s max 606, total max 1457

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 21981.1 | 2529 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 17869.6 | 2533 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 17730.0 | 2526 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 2527 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 19666.7 | 2524 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 21901.9 | 2517 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 17722.2 | 2522 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 52878.0 | 2527 |
| `api/v{version:apiVersion}/Mail/sendmail` | 47470.6 | 2508 |
| `api/v{version:apiVersion}/Patients/resolve` | 48.8 | 24 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 4450.0 | 2513 |
| `api/v{version:apiVersion}/Patients/validate-ins` | 48.8 | 11 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 29407.4 | 2506 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 2350.0 | 2506 |
| `api/v{version:apiVersion}/Search/semantic` | 49147.1 | 2512 |
| `api/v{version:apiVersion}/Sync/coverage` | 18591.8 | 2524 |
| `—` | 48.8 | 22 |

- **p95 client global (k6)** : 8208.8 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -51791.2 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.73 |
| Documents CDA /s | 0.73 |
| Durée traitement CDA (s, p95) | 2.20 |
| Événements de session IMAP /s | 2.00 |
| Recherches (s, p95) | 49.147 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 1200.6 | 28000 | 3.3 (0.3 %), p95 887 | 1116.2 (93.0 %), p95 28000 | 81.1 (6.8 %), p95 2238 |
| `GetMail` | 10.9 | 4057.1 | 19194 | 188.7 (4.6 %), p95 3899 | 486.1 (12.0 %), p95 9571 | 3382.3 (83.4 %), p95 155 |
| `GetMailsByUids` | 13.6 | 3426.4 | 51950 | 269.3 (7.9 %), p95 17804 | 658.0 (19.2 %), p95 15379 | 2499.1 (72.9 %), p95 42333 |

- **`EnrichPersistMail`** — sur 1200.6 ms en moyenne (7.9 requête(s) SQL par appel) : 3.3 ms attente d'une connexion, 1116.2 ms exécution SQL, 81.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 4057.1 ms en moyenne (10.9 requête(s) SQL par appel) : 188.7 ms attente d'une connexion, 486.1 ms exécution SQL, 3382.3 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

- **`GetMailsByUids`** — sur 3426.4 ms en moyenne (13.6 requête(s) SQL par appel) : 269.3 ms attente d'une connexion, 658.0 ms exécution SQL, 2499.1 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 9.5 | 3382.3 | 354742.4 | 0.9 | 1.3 | 0.9 | 2.3 | non relevé | 0.0 | 0.9 | 2.2 | 0.1 | 0.9 | non relevé | 0.2 |
| `GetMailsByUids` | 220.9 | 2499.1 | 11312.7 | 19.8 | 30.3 | 19.8 | 32.2 | 19.8 | 0.0 | 19.8 | 6.2 | 0.0 | 19.7 | 47.6 | 5.6 |

- **`GetMail`** — sur 3382.3 ms de matérialisation, l'appel a construit 9.5 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.3 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.2 résultats de biologie, 0.1 éléments de synthèse, 0.9 corps de messages, 0.2 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **354742.4 µs**.

- **`GetMailsByUids`** — sur 2499.1 ms de matérialisation, l'appel a construit 220.9 objets, dont 19.8 messages, 30.3 étiquettes, 19.8 destinataires, 32.2 pièces jointes, 19.8 identifiants enrichis, 0.0 acquittements, 19.8 documents médicaux, 6.2 résultats de biologie, 0.0 éléments de synthèse, 19.7 corps de messages, 47.6 objets de fil, 5.6 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **11312.7 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **19.6 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.4 | 1772.7 | 28000 | 151.2 (8.5 %), p95 488 | 31.8 (1.8 %), p95 338 | 34.4 (1.9 %), p95 2350 | 1316.1 (74.2 %), p95 28000 | 239.2 (13.5 %), p95 3750 |

- **Enrichir un message** — sur 1772.7 ms en moyenne (5.4 message(s) par requête) : 151.2 ms fetch IMAP, 31.8 ms extraction XDM, 34.4 ms parsing CDA, 1316.1 ms écritures base, 239.2 ms le reste (DTO, notifications). **Poste dominant : écritures base.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 199.4 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 2331.8 | 6988 | 0.0 (0.0 %), p95 5 | 210.0 (9.0 %), p95 922 | 170.2 (7.3 %), p95 613 | 376.9 (16.2 %), p95 490 | 486.2 (20.9 %), p95 1458 | 1573.6 (67.5 %), p95 5195 |

- **Envoyer un message** — sur 2331.8 ms en moyenne : 0.0 ms garde d'opposition, 210.0 ms construction MIME, 170.2 ms obtention de session SMTP, 376.9 ms transmission + acquittement, 486.2 ms archivage Sent, 1573.6 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.738 | 2.425 | 0.05 |
| `imap_session` | 0.484 | 21.644 | 47.15 |
| `in_process_fetch` | 0.005 | 2.425 | 0.05 |
| `smtp_session` | 0.005 | 2.446 | 3.42 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.010 | 3.788 | 4.438 | 3.670 | 3.44 |
| `EnrichEmails` | 0.005 | 3.875 | — | 3.875 | 1.09 |
| `GetAttachmentStream` | 1.900 | 25.000 | 9.875 | 26.000 | 0.80 |
| `GetEmailContent` | 0.005 | 2.425 | 4.875 | 2.425 | 2.40 |
| `GetFolderStatus` | 0.005 | 0.005 | 0.005 | — | 0.02 |
| `GetFolders` | 0.256 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 1.818 | 6.80 |
| `ProcessEmailUid` | 0.005 | 0.738 | — | 0.738 | 0.05 |
| `ReadFolder` | 0.879 | 23.881 | 29.400 | 1.778 | 27.73 |
| `UpdateFlag` | 0.594 | 2.273 | 6.625 | 2.273 | 8.69 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.743** | 1.465 | 3.670 | 2.5 % |
| `EnrichEmails` | **0.499** | 1.600 | 3.875 | 2.5 % |
| `GetAttachmentStream` | **2.287** | 3.875 | 8.125 | 73.9 % |
| `GetEmailContent` | **0.887** | 1.928 | 2.425 | 7.2 % |
| `GetFolders` | **0.497** | 1.125 | 1.818 | 0.0 % |
| `ProcessEmailUid` | **0.487** | 0.487 | 0.738 | 0.0 % |
| `ReadFolder` | **0.714** | 1.173 | 1.778 | 0.0 % |
| `UpdateFlag` | **0.918** | 1.909 | 2.273 | 6.7 % |

- 🟠 **`AppendToSent` : pointe non représentative.** Médiane **0.743 s**, p90 1.465 s, mais une pointe à 3.670 s sur 2.5 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🟠 **`EnrichEmails` : pointe non représentative.** Médiane **0.499 s**, p90 1.600 s, mais une pointe à 3.875 s sur 2.5 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🔴 **`GetAttachmentStream` : détention tenue en régime** — médiane 2.287 s et **73.9 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🟠 **`GetEmailContent` : pointe non représentative.** Médiane **0.887 s**, p90 1.928 s, mais une pointe à 2.425 s sur 7.2 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.
- 🟠 **`UpdateFlag` : pointe non représentative.** Médiane **0.918 s**, p90 1.909 s, mais une pointe à 2.273 s sur 6.7 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.

> ⚠️ **Pourquoi cette table existe** (task-276). La table qui la précède réduit chaque série à sa **pointe**. Au tir du 2026-08-29, `ReadFolder` y valait 11,871 s — lu comme « la fusion de task-270 a allongé la section critique », alors que sa médiane en régime valait 0,469 s, **sous** les 0,692 s de l'opération qu'elle remplace. La pointe était réelle ; la conclusion qu'on en tirait, non. Même famille de piège que les buckets en millisecondes (task-211), le plafond d'histogramme (task-245) et la saturation lue comme un timeout (task-271).
| Voie | Acquisitions /s |
|---|---|
| `read` | 47.15 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

✅ **Lecture rétablie** pour `GetFolders` : l'agrégat est saturé (« ≥ 60 s », c'est-à-dire *non mesuré* — `histogram_quantile` rend la dernière borne finie quand le quantile tombe dans `+Inf`), mais l'exploitation, elle, tient dans l'instrument. La queue appartient à la chauffe, pas au régime établi.

**Archivage vs reste** : `AppendToSent` attend 0.010 s au p95, contre 1.900 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

> ⓘ **PgBouncer — transitoire d'attente, écarté du verdict.** 168 échantillon(s) sur 1255 portent une attente cliente non nulle (13.4 %, pointe à 170), sous le seuil de présence soutenue de 25 %. Ce profil est celui d'une **ouverture de palier**, pas d'un pooler qui n'absorbe plus — il ne désigne donc pas de facteur limitant. À surveiller tout de même : sur la campagne du 2026-07-29, cette pointe croît avec la charge.

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| file ThreadPool du réplica `DESKTOP-DEV-X2C-23624` | 99.00 éléments | 100 éléments | 99.0 % | 0.0 % — transitoire |
| conteneur `postgres-pgvector` (CPU) | 16.40 cœurs | 24 cœurs | 68.3 % | 0.0 % — transitoire |
| processus `k6#47524` (CPU) | 3.09 cœurs | 24 cœurs | 12.9 % | 0.0 % — transitoire |
| processus `mss.mail.api#23624` (CPU) | 1.80 cœurs | 24 cœurs | 7.5 % | 0.0 % — transitoire |
| processus `mss.mail.api#45584` (CPU) | 1.73 cœurs | 24 cœurs | 7.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#40016` (CPU) | 1.70 cœurs | 24 cœurs | 7.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#32508` (CPU) | 1.54 cœurs | 24 cœurs | 6.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#24364` (CPU) | 1.39 cœurs | 24 cœurs | 5.8 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (file ThreadPool du réplica `DESKTOP-DEV-X2C-23624`) monte à 99.0 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 61680 — dont **61680** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Attendu par boîte** : 247 (complétude relative au périmètre du scénario)
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-1000-postlot-292-294-20260911-123951.jsonl`.

### Objet du tir — post-merge du lot task-292 / 293 / 294 sur `develop` (`d04f2ca`), iso-protocole du tir de confirmation `3d8f2ed` du 09/09

Mêmes 1000 bases hydratées (57 Go, gardées, non purgées), même plan (`JOURNEY_STAGES=1000:12600s`, `MESSAGES_PER_USER=247`,
`UID_BASE=365`, `CORPUS_THREAD_SHARE=0.3`, `JOURNEY_P_TREATMENT=0.095`, `JOURNEY_P_READ_COLD=0.19`), journal d'audit **actif**.
Divergences assumées : RTT poste ↔ cluster mesuré **6 ms** (10 connexions TCP, médiane 5,2) → `LATENCY_MS=95` pour garder
101 ms simulés (le 09/09 : RTT 23 → 78) ; Postgres redémarré le matin (cache de pages froid au départ, `shared_buffers` 4 Go,
cgroup **12 Go inchangé** — task-296 non livrée). Fenêtre 09h09 → 12h39 (heure locale), chauffe jusqu'à ~12h02, régime 12h02 → 12h39.
k6 exit 0, aucune itération interrompue, chauffe aboutie.

### Verdict — 🔴 ROUGE, et ce n'est pas le journal d'audit

| Grandeur | Confirmation `3d8f2ed` (09/09) | **Post-lot `d04f2ca` (11/09)** |
|---|---|---|
| Traces émises / persistées / `LOST` | 178 145 / 178 145 / 0 | **175 651 / 175 651 / 0** — DOD task-292 toujours tenue |
| Erreurs k6 (tir complet / dernière heure) | 0,16 % | **11,98 % / ~28 %** (39 échecs/s sur ~150 req/s) |
| Refus PgBouncer `08P01 server_login_retry` | 203 | **110 693** (Seq : 110 499 exceptions) |
| HTTP 500 / 503 (Seq, requêtes loguées) | 173 / 0 | **74 603 / 56 446** |
| `sv_login` PgBouncer (backends bloqués en login, max) | — | **467** |
| Backends Postgres créés / 60 s (avant → pendant) | — | 344 → **0** de 10h55 à 11h20 |
| Timeouts cache Redis | 10 773 | 201 (en baisse ×50, hors sujet ici) |
| `Channel full` (spill audit) | 102 231 | 12 030 au régime, spill vidé après le tir |

### Chronologie de la panne (heure locale) — trois sources concordantes (k6 → Prometheus, serveur → Prometheus, Seq)

| Heure | Charge k6 (req/s OK) | Ce qui se passe |
|---|---|---|
| 09h09 → 10h45 | 0 → 100 | Rampe des 1000 médecins puis chauffe. **0 erreur**, 0 exception Postgres. Host CPU 82 → 96 %, Postgres 5,6 → 14 cœurs, mémoire conteneur 11,1 → 11,4 Go / 12. |
| 10h45 → 10h55 | 100 | `maxwait` PgBouncer passe de 0,3 s à 1,3 s puis **2,5 s** ; `cl_waiting` 3 → 19 (attente conforme à task-294, pas de rejet). Backends créés/60 s : 255 → 102 → **19**. Mémoire Postgres **11,6 Go / 12**. |
| **10h55:13** | 99 | **Premier `NpgsqlException: The operation has timed out`** (15 s d'ouverture de connexion, Seq) → premiers 500 (`/folders`, `/folders/INBOX`). k6 : 0,3 échec/s à 10h59, 1,3/s à 11h04. |
| 11h00 → 11h10 | 85 → 90 | Backends créés/60 s = **0**. `sv_login` 53 → 177 : les connexions serveur de PgBouncer restent en login > `server_connect_timeout` (30 s). |
| **11h09:58** | 90 | **Premier `08P01 server_login_retry`** : PgBouncer met l'échec de login en cache et le rend à **tous** les clients du pool → 503 (`IsDatabaseUnavailable`, task-294) en 70 ms (p50). |
| 11h10 → 12h39 | 100 → 111 | Spirale : les backends existants se ferment (`server_idle_timeout`) et ne sont pas remplacés (total 1 427 → ~800), `sv_login` 300 → 467, refus 28 → 5 700 par 5 min. Erreurs k6 13 → 39/s. Host CPU 94-100 %. |
| 12h39 → 12h46 | 0 (tir fini) | **Rejeu du spill audit** : backends 924 → **2 493** (route directe : 1 193 connexions, `Connection Idle Lifetime=600` ; PgBouncer : 1 378) → `max_connections=2500` atteint, **146 717 « sorry, too many clients already »**, `psql -U postgres` refusé. Résorbé à 12h50 (6 connexions). |

### Causes — établies par la mesure

1. **Cause racine : Postgres n'arrive plus à créer de backends** à partir de 10h50, sous pression mémoire du cgroup (11,6-11,7 Go
   pour 12 Go de plafond ; `memory.failcnt` 159 M, 9,2 M fautes de page majeures) et avec l'hôte à 96-100 % CPU. Un login
   Postgres dépasse alors 15 s (Npgsql `Timeout`) puis 30 s (`server_connect_timeout`). C'est **task-296** (mémoire du Postgres
   de banc, `shared_buffers`), déjà instruite le 09/09 (login 10-16 s mesurés au `psql`), **non livrée** — le tir le confirme.
2. **Amplificateur : le cache d'échec de login de PgBouncer** (`server_login_retry`). Dès qu'un login serveur échoue, tout le pool
   reçoit `08P01` sans réessayer → 110 693 refus pour quelques centaines de logins réellement en échec. Task-294 a bien remplacé
   le *rejet par file pleine* par l'attente (`cl_waiting` ≤ 151, `maxwait` 20 s, 30 `query_wait_timeout` seulement), mais le
   rejet par *login en échec* est un autre chemin, qu'elle ne couvre pas.
3. **Convoi derrière le verrou de session IMAP** : `ReadFolder:INBOX` et `GetFolders` tiennent le verrou **15,0 s au p50**
   (8 461 + 2 920 « Lock released (long) ») — exactement le timeout Npgsql : le médecin dont une requête attend Postgres
   bloque ses propres requêtes suivantes. Queue de requêtes actives côté serveur : 16 à 10h30 → **9 782 à 12h40**, avec
   **3 105 requêtes de plus de 30 min** (2 097 rendues 200, 879 en 500, 21 en 503, 108 en 499) ; une requête tracée
   (`298441b6…`) attend **60 min** entre `[GetEmail] Start` et la première tentative de provisionnement — aucun évènement
   entre les deux, donc l'attente est dans le pool Npgsql / le verrou, pas dans PgBouncer.
4. **Post-tir : le rejeu du spill ouvre ~1 connexion directe par base** (1 000 bases) tandis que PgBouncer garde ses 1 378
   serveurs 600 s → `max_connections` 2 500 atteint 3 min après la fin du tir. Pas de perte (émises = persistées), mais le
   drain sature Postgres pour ~8 min et refuse même l'administration. À dimensionner (pool direct par base, ou plafond global
   de connexions du drain).

### Ce que le tir établit et n'établit pas

- **Établi** : la DOD task-292 tient encore sous cette panne (0 perte, 0 `LOST`) ; task-294 fait bien attendre au lieu de
  rejeter sur le chemin « file pleine » ; task-293 : 0 `[XDM.Load]` lié au scratch (15 erreurs XDM, à qualifier).
- **Non établi** : la capacité au palier 1000 — **tir non opposable** (ROUGE), à refaire **après task-296**. Les latences SLO
  publiées ci-dessus sont des bornes optimistes (13 % d'échantillons en refus).
- **Panneau Grafana « Taux d'erreur HTTP » : 69,6 % à 12h30 pour un taux réel de 28,1 %.** Sa formule
  `sum(k6_http_req_failed_rate) / count(k6_http_req_failed_rate)` moyenne **56 séries sans pondération** — et les séries
  portent les labels `status` / `expected_response` / `error`, donc toute série d'erreur vaut 1,0 par construction. Le chiffre
  mesure la *part de séries en erreur*, pas la part de requêtes. Seul `report.py` (et `rate(k6_http_reqs_total{expected_response="false"}) / rate(k6_http_reqs_total)`) fait foi.

### Bruit de fond et régressions surveillées

- `Parsing completed` : 195 seulement — attendu, les bases sont hydratées, la chauffe court-circuite (99,9 % aboutie).
- `Failed to parse entity headers` : 0. 429 : 0. `SecurityTokenMalformedException` : 0. `Spill buffer unreachable` : 0.
- `FATAL: database "(end" does not exist` : 12 par 10 min **toute la journée, dès le démarrage de l'AppHost** — une sonde
  périodique (~50 s) avec un nom de base mal formé ; sans effet sur le tir, à identifier (hors task).
- `FATAL: received unencrypted data after SSL request` : 58 765 sur la fenêtre de panne, corrélés aux logins qui expirent
  (client qui abandonne la poignée de main) — symptôme, pas cause.
- Erreurs Redis : 201 timeouts (contre 10 773 le 09/09), 215 `Best-effort Set failed`.
