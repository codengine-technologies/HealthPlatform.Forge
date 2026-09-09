# Rapport de tir — journey-1000-task292-fix2-20260909

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-task292-fix2-20260909-010943.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1000 médecins, 8 étape(s) dépassent le temps de réponse attendu : « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) », « Recherche »
- 10 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- 0.163 % des demandes ont échoué (sous le plafond, mais non nul)

## 🎯 Objet du tir — CONFIRMATION de la branche corrigée `3d8f2ed` (task-292), journal ACTIF — ✅ DOD tenue

Code sous test : `feat/task-292-audit-trail-decoupled` @ `3d8f2ed` (PR api-mail #225) : repli par trace re-spillé, plafond d'essais
réservé aux traces poison (SqlState 22/23/42), **drain série** (`DrainParallelism` 1), idle du pool audit 60 s, borne du spill
**180 min** (360 000), chaînes de connexion hors du spill. Quatrième tir du jour à protocole égal, mêmes 1000 bases hydratées,
RTT 23 ms → latence 78 ms. Fenêtre 21h38 → 01h09, régime 00h31 → 01h09. **k6 exit 0.**

| Grandeur | Matin `c2c108b` | A/B journal OFF | Soir `2354b44` (parallèle) | **Confirmation `3d8f2ed`** |
|---|---|---|---|---|
| Traces émises / persistées / **lignes en base (1000 bases)** | 198 545 / 198 542 / 198 542 (−3) | — | 181 308 / 180 181 / 180 181 (−1 127) | **178 145 / 178 145 / 178 145 (0)** |
| `LOST` / Fatal | 0 / 0 | — | 1 034 / 1 034 | **0 / 0** |
| Contre-pression : attentes / refus | 18 / 18 | — | 38 / 18 | **0 / 0** |
| Spill : bascules / rejouées / pic en attente / vidé après | 111 678 / 111 681 / ~102 k / 6 min | — | 166 567 / 166 474 / ~82 k / 8 min | 148 396 / 148 396 / **~95 k** (borne 360 k) / **8 min** |
| Échecs de persistance lot / trace (re-spillées, jamais perdues) | 49 / 6 | — | 62 211 / 70 942 | 36 090 / 46 165 |
| Refus PgBouncer `08P01` | 646 | 270 | 15 873 | **203** |
| Erreurs k6 / p95 client / moy. | 0,44 % / 10 526 / 2 311 ms | 0,16 % / 9 418 / 2 103 ms | 1,37 % / 11 079 / 2 206 ms | **0,16 %** / 11 021 / 2 509 ms |
| HTTP 500 / 503 (Seq) | 724 / 11 | 340 / 0 | 14 280 / 8 | 173 / 0 |
| Timeouts cache Redis | 21 835 | 6 568 | 8 778 | 10 773 |
| Postgres CPU régime / max (cœurs) | 11,30 / 14,63 | 11,47 / 14,28 | — / 15,09 | 11,53 / 14,60 |
| PgBouncer CPU régime / Redis pic | 0,82 / 1,18 | 0,87 / 1,15 | — / 1,21 | 0,86 / 1,16 |
| Chauffe aboutie | 86,5 % | 93,7 % | 86,2 % | **99,9 %** (toutes les étapes opposables) |

**Verdict : la DOD « mesure au banc » est tenue.** Zéro trace perdue (émises = lignes en base sur les 1000 bases, contrôle indépendant
des compteurs), zéro `LOST`, zéro contre-pression, et le journal actif ramène le pooler **au niveau du tir sans journal**
(0,16 % d'erreurs, 203 refus contre 270 sans journal et 646 le matin). Le spill reste le régime normal sous saturation (canal plein
de 23h40 à la fin, ~95 000 en attente au pic, retard 10 min) et se vide en 8 minutes dès que la charge cesse : c'est le
comportement attendu tant que la cause racine — la création de backends Postgres à ~3,8/s sous pression mémoire (task-294) — n'est
pas traitée. Les latences médecin (11 étapes, 8 rouges) sont celles du palier 1000 sur base hydratée (référence 26/08, E015), pas du journal.

**Ce que ce tir n'établit pas** : la persistance sous une saturation de plus de 3 h (borne 180 min non atteinte : 95 k / 360 k), et
le comportement avec un Redis lui-même saturé (aucun `Spill buffer unreachable` cette fois — 0 contre 39 au tir du soir).

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1055195 — **débit émergent global** : 83.3 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 88229 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 83.3 | **2508.9** | 251.7 | **11021.3** | — | 65821.3 | 0.16 | 99.8 | 0 | 0 | 0/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 236361 | 18.76 | 0.51 | 994.1 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 253 / 1215 (n=79420) |
| 2 | Ouvrir / rafraîchir l'inbox | 1352 / 56158 (n=39682) |
| 3 | Ouvrir un message enrichi (servi base) | 2467 / 5281 (n=19912) |
| 4 | Ouvrir un message froid (fetch IMAP) | 763 / 1403 (n=3776) |
| 5 | Recherche | 9009 / 37370 (n=5942) |
| 6 | Envoi (acquittement UI) | 4774 / 12435 (n=5906) |
| 7 | Télécharger une PJ (~124 Ko) | 3329 / 7800 (n=8044) |
| 8 | Marquer lu | 1110 / 1878 (n=15904) |
| 9 | Rechercher un patient | 177 / 659 (n=4886) |
| 10 | Ouvrir la page d'un dossier patient | 13660 / 33539 (n=6080) |
| 11 | Fiche patient complète (ressenti médecin) | 30016 / 62403 (n=3042) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 14.8 / 20 | 34.7 / 60 | 3816 | 62403 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3732 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 3517 ms en moyenne, 59999 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

⚠️ **aucun point d'échantillonneur repliable par palier** — CSV `observe-*.csv` absent, fenêtre du tir absente du JSON k6, ou calendrier des paliers non déclaré. Relancer avec `observe.sh` armé (voir `docs/loadtest.md` § 4c) pour que cette table existe.

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 99.9 %** des 1000 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⚠️ Chauffe : **9885 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **78 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 253 (300) | 1215 (1500) | 79420 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 1352 (300) | 56158 (1000) | 39682 | ❌ |
| 3 | Ouvrir un message enrichi (servi base) | 2467 (100) | 5281 (500) | 19912 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 763 (800) | 1403 (2500) | 3776 | ✅ |
| 5 | Recherche | 9009 (500) | 37370 (2000) | 5942 | ❌ |
| 6 | Envoi (acquittement UI) | 4774 (1000) | 12435 (3000) | 5906 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 3329 (500) | 7800 (2000) | 8044 | ❌ |
| 8 | Marquer lu | 1110 (200) | 1878 (1000) | 15904 | ❌ |
| 9 | Rechercher un patient | 177 (300) | 659 (1500) | 4886 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 13660 (500) | 33539 (2000) | 6080 | ❌ |
| 11 | Fiche patient complète (ressenti médecin) | 30016 (1500) | 62403 (4000) | 3042 | ❌ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 39682 | 19733 | 56158 | 783053.7 | 72.5 % |
| 🔴 | Recherche (`search`) | 5942 | 11618 | 37370 | 69037.0 | 6.4 % |
| 🔴 | Ouvrir un message enrichi (servi base) (`read_content`) | 19912 | 2763 | 5281 | 55012.8 | 5.1 % |
| 🔴 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 3042 | 14855 | 33539 | 45188.7 | 4.2 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 8044 | 3910 | 7800 | 31453.8 | 2.9 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 5906 | 5282 | 12435 | 31196.1 | 2.9 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 79420 | 376 | 1215 | 29828.5 | 2.8 % |
| 🔴 | Marquer lu (`mark_read`) | 15904 | 1210 | 1878 | 19248.9 | 1.8 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 1908 | 5349 | 12820 | 10206.7 | 0.9 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 3776 | 865 | 1403 | 3268.1 | 0.3 % |
| 🟠 | Rechercher un patient (`patient_search`) | 4886 | 260 | 659 | 1267.9 | 0.1 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 3038 | 314 | 500 | 953.2 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 7 🔴 · 3 🟠 · 2 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Ouvrir / rafraîchir l'inbox** (`read_list`, 783053.7 s, 72.5 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (19733 ms)
  - **dispersion p95/p50 = 41.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 69037.0 s, 6.4 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (11618 ms)
  - **dispersion p95/p50 = 4.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 55012.8 s, 5.1 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2763 ms)
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 45188.7 s, 4.2 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (14855 ms)
- **Télécharger une PJ (~124 Ko)** (`attachment`, 31453.8 s, 2.9 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (3910 ms)
- **Envoi (acquittement UI)** (`send`, 31196.1 s, 2.9 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (5282 ms)
- **Arrivée dashboard** (`dashboard`, 29828.5 s, 2.8 %)
  - **dispersion p95/p50 = 4.8×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Marquer lu** (`mark_read`, 19248.9 s, 1.8 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1210 ms)
- **Traitement (plateforme)** (`treatment`, 10206.7 s, 0.9 %)
  - **coût par appel élevé** (5349 ms)
  - **dispersion p95/p50 = 3.0×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Rechercher un patient** (`patient_search`, 1267.9 s, 0.1 %)
  - **dispersion p95/p50 = 3.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation

> Tir de confirmation (task-292). Les candidats mécaniques ci-dessus sont ceux du palier 1000 sur base hydratée (référence 26/08, E015). Restent ouverts, hors task-292 :

- **F-292-6 (task-294) — mémoire du conteneur Postgres** : cause racine mesurée des logins à 10-16 s et de ~3,8 backends/s ; c'est elle qui fait du spill le régime normal à 1000. Tir A/B mémoire (limite 24-32 Go, `shared_buffers` 8 Go) à jouer sur cette même base.
- **F-292-3 (cache Redis)** : `HMSET mail:email:*` de 1,5 Mo, Redis à 1,1 cœur, timeouts du cache même sans journal — à proposer en `/po`.
- **Bruit de journal du repli** : `Failed to persist a batch` / `… audit trace` en Error alors que la trace est re-spillée et persistée — passer en Warning avec un compteur, garder l'Error pour le poison.


## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 19855 | 393 | 1110 | 9034.5 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 19855 | 30 | 545 | 3283.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 19855 | 493 | 1674 | 13793.7 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 19855 | 20 | 692 | 3716.7 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 19841 | 40 | 344 | 1872.7 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 19841 | 39926 | 60000 | 781181.0 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folders`** (1674 ms de p95, 493 ms de p50, n=19855), qui porte **aussi** le temps serveur de l'étape (13793.7 s, 46 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (60000 ms de p95, 39926 ms de p50, n=19841), qui porte **aussi** le temps serveur de l'étape (781181.0 s, 100 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 35219 | 1842.6 | 1258.5 | 4178.7 | 5039.9 | 27081.7 |
| attachment,palier:1000 | 8044 | 3910.2 | 3328.6 | 5424.3 | 7800.4 | 27081.7 |
| attachment,palier:transition | 123 | 2569.8 | 2476.9 | 4537.2 | 4946.0 | 8571.8 |
| dashboard | 355736 | 288.3 | 118.8 | 766.8 | 1072.1 | 21603.3 |
| dashboard,call:coverage,palier:1000 | 19855 | 187.2 | 19.7 | 564.2 | 692.3 | 2708.6 |
| dashboard,call:coverage,palier:transition | 10 | 27.8 | 23.5 | 52.9 | 60.0 | 67.1 |
| dashboard,call:folder,palier:1000 | 19855 | 455.0 | 393.0 | 878.9 | 1109.6 | 12380.6 |
| dashboard,call:folder,palier:transition | 10 | 295.7 | 354.6 | 431.6 | 434.2 | 436.9 |
| dashboard,call:folders,palier:1000 | 19855 | 694.7 | 492.7 | 1388.2 | 1673.8 | 15188.0 |
| dashboard,call:folders,palier:transition | 10 | 16.7 | 13.4 | 24.9 | 25.4 | 25.8 |
| dashboard,call:today,palier:1000 | 19855 | 165.4 | 29.6 | 457.4 | 545.0 | 2833.9 |
| dashboard,call:today,palier:transition | 10 | 303.7 | 370.0 | 396.2 | 416.8 | 437.3 |
| dashboard,palier:1000 | 79420 | 375.6 | 252.7 | 937.2 | 1215.0 | 15188.0 |
| dashboard,palier:transition | 40 | 161.0 | 42.7 | 393.7 | 431.3 | 437.3 |
| mark_read | 70666 | 679.3 | 665.7 | 1408.7 | 1697.4 | 25634.9 |
| mark_read,palier:1000 | 15904 | 1210.3 | 1109.8 | 1637.1 | 1878.1 | 18477.6 |
| mark_read,palier:transition | 228 | 827.6 | 869.5 | 1312.4 | 1466.6 | 2115.9 |
| patient_docs | 190830 | 1840.8 | 239.5 | 5613.8 | 7711.3 | 51451.3 |
| patient_docs,palier:1000 | 44852 | 4005.0 | 3902.0 | 8623.5 | 9746.7 | 40734.5 |
| patient_docs,palier:transition | 1030 | 1613.0 | 808.4 | 4301.2 | 6002.0 | 9074.1 |
| patient_dossier | 12988 | 6555.2 | 1855.7 | 21185.7 | 28271.7 | 48750.2 |
| patient_dossier,palier:1000 | 3042 | 14854.9 | 13659.6 | 31118.0 | 33538.5 | 48750.2 |
| patient_dossier,palier:transition | 42 | 6936.4 | 4522.2 | 18397.2 | 18643.0 | 22122.4 |
| patient_opposition | 12988 | 145.6 | 85.0 | 317.6 | 379.7 | 23548.2 |
| patient_opposition,palier:1000 | 3038 | 313.8 | 278.1 | 401.9 | 500.0 | 23548.2 |
| patient_opposition,palier:transition | 64 | 157.8 | 157.4 | 264.4 | 269.7 | 330.5 |
| patient_search | 21027 | 134.1 | 74.5 | 343.5 | 490.7 | 7270.5 |
| patient_search,palier:1000 | 4886 | 259.5 | 177.0 | 495.5 | 659.0 | 7270.5 |
| patient_search,palier:transition | 69 | 142.5 | 99.8 | 328.1 | 365.1 | 612.6 |
| read_content | 88867 | 1272.4 | 782.5 | 2931.8 | 3456.7 | 27879.0 |
| read_content,palier:1000 | 19912 | 2762.8 | 2466.7 | 3754.3 | 5281.2 | 27879.0 |
| read_content,palier:transition | 379 | 1437.8 | 1304.5 | 2758.5 | 3091.8 | 8014.4 |
| read_content_cold | 16802 | 679.4 | 620.1 | 1035.1 | 1293.5 | 11746.4 |
| read_content_cold,palier:1000 | 3776 | 865.5 | 763.5 | 1168.5 | 1403.0 | 11746.4 |
| read_content_cold,palier:transition | 45 | 732.5 | 682.8 | 962.9 | 1039.6 | 1499.4 |
| read_list | 177868 | 8521.3 | 200.4 | 35573.4 | 46370.6 | 60044.3 |
| read_list,call:emails,palier:1000 | 19841 | 39372.1 | 39925.7 | 56157.6 | 60000.1 | 60044.3 |
| read_list,call:emails,palier:transition | 67 | 17723.3 | 19278.8 | 24683.8 | 25116.8 | 26394.1 |
| read_list,call:folder,palier:1000 | 19841 | 94.4 | 40.3 | 215.8 | 343.5 | 2660.7 |
| read_list,call:folder,palier:transition | 67 | 94.9 | 27.3 | 240.8 | 387.0 | 614.3 |
| read_list,palier:1000 | 39682 | 19733.2 | 1351.7 | 51195.4 | 56157.6 | 60044.3 |
| read_list,palier:transition | 134 | 8909.1 | 254.1 | 23283.4 | 24677.9 | 26394.1 |
| search | 26680 | 7714.3 | 5184.3 | 17143.2 | 33867.5 | 65821.3 |
| search,palier:1000 | 5942 | 11618.5 | 9008.5 | 19369.3 | 37370.4 | 65821.3 |
| search,palier:transition | 68 | 6021.2 | 5078.6 | 9855.8 | 11800.7 | 44052.4 |
| send | 26139 | 3341.5 | 1145.6 | 9291.5 | 11358.9 | 38603.6 |
| send,palier:1000 | 5906 | 5282.1 | 4773.5 | 10958.6 | 12434.9 | 32452.0 |
| send,palier:transition | 65 | 2109.4 | 1411.2 | 4852.5 | 5439.4 | 5667.2 |
| treatment | 8376 | 2249.0 | 1142.7 | 5601.8 | 7135.2 | 31630.8 |
| treatment,palier:1000 | 1908 | 5349.4 | 4219.0 | 9675.6 | 12820.4 | 31630.8 |
| treatment,palier:transition | 24 | 2955.7 | 2673.7 | 5858.9 | 6736.6 | 8114.7 |
| warmup | 11000 | 3516.8 | 640.1 | 11049.2 | 16937.9 | 59998.5 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-09T19:38:39.773000+00:00 → 2026-09-09T23:09:43.661000+00:00 (12664 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-*.csv`) | ⚠️ **absent** — hôte, k6 et conteneurs non mesurés (voir `tests/loadtest-k6/observe.sh`) |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-43468` | 0.53 | 11 | 20 | 0.026 | 12.16 |
| `DESKTOP-DEV-X2C-43560` | 0.54 | 9 | 24 | 0.026 | 22.78 |
| `DESKTOP-DEV-X2C-43980` | 0.52 | 8 | 20 | 0.026 | 16.35 |
| `DESKTOP-DEV-X2C-54152` | 0.49 | 14 | 21 | 0.025 | 17.58 |
| `DESKTOP-DEV-X2C-57164` | 0.56 | 5 | 31 | 0.026 | 44.55 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur

⚠️ **Échantillonneur absent de la fenêtre** — le CPU des conteneurs, celui de k6 et celui de l'hôte ne sont pas mesurés. Impossible, sur ce tir, d'écarter le tireur comme facteur limitant.

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 4210.5 | 2530 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 4747.9 | 2530 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 14531.0 | 2523 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 39000.0 | 2520 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 2791.7 | 2526 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 18647.1 | 2521 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 5536.5 | 2526 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 60000.0 | 2524 |
| `api/v{version:apiVersion}/Mail/sendmail` | 29750.0 | 2502 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 1125.0 | 2500 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 54785.7 | 2500 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 875.0 | 2500 |
| `api/v{version:apiVersion}/Search/semantic` | 56500.0 | 2506 |
| `api/v{version:apiVersion}/Settings` | 228.5 | 11 |
| `api/v{version:apiVersion}/Settings/getsettings` | 8.6 | 11 |
| `api/v{version:apiVersion}/Sync/coverage` | 1417.9 | 2526 |

- **p95 client global (k6)** : 11021.3 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -48978.7 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.58 |
| Documents CDA /s | 0.62 |
| Durée traitement CDA (s, p95) | 3.57 |
| Événements de session IMAP /s | 1.85 |
| Recherches (s, p95) | 56.500 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 3039.0 | 29000 | 12.5 (0.4 %), p95 725 | 2833.6 (93.2 %), p95 29000 | 192.8 (6.3 %), p95 2350 |
| `GetMail` | 11.4 | 1425.1 | 15867 | 104.9 (7.4 %), p95 3313 | 1300.1 (91.2 %), p95 9976 | 20.2 (1.4 %), p95 190 |
| `GetMailsByUids` | 14.8 | 12047.0 | 60000 | 0.4 (0.0 %), p95 5 | 1535.6 (12.7 %), p95 9254 | 10511.0 (87.3 %), p95 60000 |

- **`EnrichPersistMail`** — sur 3039.0 ms en moyenne (7.9 requête(s) SQL par appel) : 12.5 ms attente d'une connexion, 2833.6 ms exécution SQL, 192.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 1425.1 ms en moyenne (11.4 requête(s) SQL par appel) : 104.9 ms attente d'une connexion, 1300.1 ms exécution SQL, 20.2 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 12047.0 ms en moyenne (14.8 requête(s) SQL par appel) : 0.4 ms attente d'une connexion, 1535.6 ms exécution SQL, 10511.0 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.0 | 20.2 | 2005.6 | 0.9 | 1.3 | 0.9 | 2.5 | non relevé | 0.0 | 0.9 | 2.3 | 0.1 | 0.9 | non relevé | 0.2 |
| `GetMailsByUids` | 239.3 | 10511.0 | 43930.4 | 21.5 | 32.7 | 21.5 | 34.8 | 21.5 | 0.0 | 21.5 | 6.7 | 0.0 | 21.3 | 51.6 | 6.2 |

- **`GetMail`** — sur 20.2 ms de matérialisation, l'appel a construit 10.0 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.5 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.3 résultats de biologie, 0.1 éléments de synthèse, 0.9 corps de messages, 0.2 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **2005.6 µs**.

- **`GetMailsByUids`** — sur 10511.0 ms de matérialisation, l'appel a construit 239.3 objets, dont 21.5 messages, 32.7 étiquettes, 21.5 destinataires, 34.8 pièces jointes, 21.5 identifiants enrichis, 0.0 acquittements, 21.5 documents médicaux, 6.7 résultats de biologie, 0.0 éléments de synthèse, 21.3 corps de messages, 51.6 objets de fil, 6.2 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **43930.4 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **5.0 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.4 | 3838.6 | 29000 | 129.8 (3.4 %), p95 475 | 32.5 (0.8 %), p95 960 | 34.3 (0.9 %), p95 2350 | 3314.7 (86.4 %), p95 29000 | 327.3 (8.5 %), p95 6875 |

- **Enrichir un message** — sur 3838.6 ms en moyenne (5.4 message(s) par requête) : 129.8 ms fetch IMAP, 32.5 ms extraction XDM, 34.3 ms parsing CDA, 3314.7 ms écritures base, 327.3 ms le reste (DTO, notifications). **Poste dominant : écritures base.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 3836.5 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 2720.7 | 8913 | 0.0 (0.0 %), p95 5 | 2151.1 (79.1 %), p95 7647 | 189.6 (7.0 %), p95 628 | 343.3 (12.6 %), p95 488 | 445.0 (16.4 %), p95 1077 | 36.8 (1.4 %), p95 162 |

- **Envoyer un message** — sur 2720.7 ms en moyenne : 0.0 ms garde d'opposition, 2151.1 ms construction MIME, 189.6 ms obtention de session SMTP, 343.3 ms transmission + acquittement, 445.0 ms archivage Sent, 36.8 ms le reste. **Poste dominant : construction MIME.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.475 | 2.425 | 0.05 |
| `imap_session` | 0.532 | 2.386 | 32.51 |
| `in_process_fetch` | 0.005 | 2.425 | 0.05 |
| `smtp_session` | 0.055 | 4.234 | 3.42 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 2.369 | 4.594 | 2.125 | 3.49 |
| `EnrichEmails` | 0.005 | 1.150 | 2.425 | 0.812 | 0.93 |
| `GetAttachmentStream` | 1.525 | 16.000 | 29.000 | 16.000 | 0.64 |
| `GetEmailContent` | 0.005 | 3.475 | 2.425 | 3.475 | 2.29 |
| `GetFolders` | 0.377 | 28.000 | 58.500 | 2.667 | 3.29 |
| `ProcessEmailUid` | 0.005 | 2.425 | — | 2.425 | 0.05 |
| `ReadFolder` | 0.732 | 2.419 | 12.000 | 2.382 | 18.93 |
| `UpdateFlag` | 0.658 | 2.344 | 2.431 | 2.344 | 8.58 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.495** | 0.512 | 0.594 | 0.0 % |
| `EnrichEmails` | **0.444** | 0.637 | 0.812 | 0.0 % |
| `GetAttachmentStream` | **2.500** | 5.625 | 8.000 | 100.0 % |
| `GetEmailContent` | **0.812** | 0.978 | 1.731 | 0.0 % |
| `GetFolders` | **0.250** | 0.383 | 0.465 | 0.0 % |
| `ProcessEmailUid` | **0.487** | 0.487 | 0.738 | 0.0 % |
| `ReadFolder` | **0.517** | 0.604 | 0.710 | 0.0 % |
| `UpdateFlag` | **0.684** | 0.760 | 1.004 | 0.0 % |

- 🔴 **`GetAttachmentStream` : détention tenue en régime** — médiane 2.500 s et **100.0 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.

> ⚠️ **Pourquoi cette table existe** (task-276). La table qui la précède réduit chaque série à sa **pointe**. Au tir du 2026-08-29, `ReadFolder` y valait 11,871 s — lu comme « la fusion de task-270 a allongé la section critique », alors que sa médiane en régime valait 0,469 s, **sous** les 0,692 s de l'opération qu'elle remplace. La pointe était réelle ; la conclusion qu'on en tirait, non. Même famille de piège que les buckets en millisecondes (task-211), le plafond d'histogramme (task-245) et la saturation lue comme un timeout (task-271).
| Voie | Acquisitions /s |
|---|---|
| `read` | 32.51 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 1.525 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| file ThreadPool du réplica `DESKTOP-DEV-X2C-54152` | 14.00 éléments | 100 éléments | 14.0 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (file ThreadPool du réplica `DESKTOP-DEV-X2C-54152`) monte à 14.0 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## Vérification par base (propriété + complétude)

> ⚠️ La passe automatique de `report.sh` n'a trouvé aucune base (Postgres saturé par le drainage du spill au moment de l'appel). Rejouée à la main à 01h25, banc debout : **1000 bases, 122 736 mails stockés, 122 736 correctement attribués, 0 sujet étranger, 0 sans marqueur — verdict PASS** (`verify.sh`, `SUMMARY dbs=1000 mails=122736 owned=122736 foreign=0 unmarked=0 verdict=PASS`).

## Analyse Seq (findings) — MCP seq-local

> Comptages API Seq bornés `rangeStartUtc`/`rangeEndUtc` + `@Timestamp` (19:38Z → 23:30Z).

| Requête | Compte | Lecture |
|---|---|---|
| `@Level = 'Fatal'` / `LOST` | **0 / 0** | Aucune perte, aucun Critical du journal. |
| `[Audit] Channel full` | 102 231 | Canal plein de 23h40 à 01h09 (saturation), spill = régime normal. |
| `[Audit] Journal saturated` / `parked … refused` / `Spill buffer unreachable` | **0 / 0 / 0** | Borne 360 k jamais approchée (pic ~95 k) ; Redis a répondu. |
| `Failed to persist a batch` / `Failed to persist audit trace` | 36 090 / 46 165 | Timeouts de login Npgsql sous saturation ; **toutes re-spillées et persistées ensuite** (0 perte). Bruit de journal élevé : à requalifier en Warning une fois le re-spill prouvé (suivi). |
| `[Cache] Timeout getting key` | 10 773 | Le cache Redis sature seul (cf. rapport A/B) — finding cache. |
| `08P01` | 203 (log PgBouncer : 203 refus) | Plus bas que sans journal (270) : bruit de mesure du pooler, le journal ne pèse plus. |
| `HTTP … Status=500` / `503` | 173 / 0 | — |
| Error+Fatal / Warning | 86464 / 190453 | — |
| scratch `mss-ihe-xdm` | 0 (garde : 0 recréation) | — |

