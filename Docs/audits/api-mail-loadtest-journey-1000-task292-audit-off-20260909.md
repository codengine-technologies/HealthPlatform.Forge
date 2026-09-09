# Rapport de tir — journey-1000-task292-audit-off-20260909

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-1000-task292-audit-off-20260909-173951.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 1000 médecins, 8 étape(s) dépassent le temps de réponse attendu : « Ouvrir / rafraîchir l'inbox », « Ouvrir un message enrichi (servi base) », « Recherche »
- 10 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 45 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.158 % des demandes ont échoué (sous le plafond, mais non nul)

## 🎯 Objet du tir — A/B « journal d'audit DÉSACTIVÉ » (point 5 de task-292)

Code sous test : `feat/task-292-audit-trail-decoupled` @ `2354b44` avec `MSS_LOADTEST_AUDIT_DISABLED=true` (`Audit:Disabled`,
`NoOpAuditService` — Seq : « Journal DISABLED by configuration », 0 événement `[Audit]`, compteurs `mss_audit_*` à 0, base témoin
figée à 24 778 traces). Jambe A = tir du matin `report-journey-1000-task292-audit-20260909-123235.md` (journal actif, `c2c108b`).
Même protocole, mêmes 1000 bases hydratées (non purgées), même cluster, RTT 23 ms → latence injectée 78 ms (81 le matin).
Fenêtre 14h08 → 17h39, régime 17h01 → 17h39.

| Grandeur | A — journal actif (matin) | **B — journal désactivé** | Lecture |
|---|---|---|---|
| Postgres CPU moy. régime / max (cœurs) | 11,30 / 14,63 | **11,47 / 14,28** | **identique** : le coût Postgres du journal (0,18 INSERT/requête par la route directe) est nul à la mesure |
| PgBouncer CPU régime / `cl_waiting` (échant. non nuls) | 0,82 / 47 % | 0,87 / 45 % | identique — le pooler sature par le chemin de données, pas par l'audit |
| Refus `08P01 server_login_retry` | 646 | **270** | ÷2,4 |
| HTTP 500 / 503 (Seq) | 724 / 11 | **340 / 0** | ÷2,1 ; les 503 étaient la contre-pression audit |
| Erreurs k6 / p95 client / latence moy. | 0,44 % / 10 526 ms / 2 311 ms | **0,16 % / 9 418 ms / 2 103 ms** | −64 % d'erreurs, −10 % au p95 |
| `[Cache] Timeout getting key` / `Best-effort Set failed` | 21 835 / 287 | **6 568 / 25** | ÷3,3 — mais **non nul sans aucun spill** : le cache a son propre problème |
| Redis CPU moy. / pic (cœurs) | 0,21 / 1,18 | 0,21 / **1,15** | Redis pointe à 1 cœur **sans écriture d'audit** : `HMSET mail:email:*` (corps de message, jusqu'à 1,5 Mo) |
| Error+Fatal / Warning (Seq) | 2 454 / 185 105 | 1 301 / 40 286 | le Fatal unique = `Kestrel: application never completed` (16h54, hors audit) |
| Chauffe aboutie | 86,5 % (étapes 2/3/10/11 ⛔) | **93,7 %** (toutes opposables) | ⚠️ biais : 3e tir sur ces bases, plus hydratées — les étapes servies base ne se comparent pas strictement au matin |
| Incident scratch | 0 | 1 disparition de `%TEMP%\mss-ihe-xdm` à 14h41:02, recréé en 2 s par la garde, 0 `DirectoryNotFoundException` | F-SCRATCH-1 (task-293, PR #226) confirmée récurrente |

**Verdict du point 5 : le journal ne coûte rien à Postgres.** Son coût mesurable était ailleurs : dans les erreurs (×2,7), les refus du
pooler (×2,4) et ~10 % de p95 — c'est-à-dire dans le comportement du **drain** de la jambe A (un login direct par groupe, contre-pression
en fin de tir), pas dans les INSERT. Le re-tir de la branche corrigée (F-292-1/2/4, `2354b44`, journal actif) est le tir qui doit
ramener la jambe A sur la jambe B. Pas d'US « écriture par lot » à ouvrir pour Postgres.

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 12630s — **Latence** : mssante
- **Requêtes** : 1110076 — **débit émergent global** : 87.6 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 92882 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | journey | — | 87.6 | **2102.8** | 166.3 | **9418.5** | — | 186964.6 | 0.16 | 99.9 | 0 | 0 | 121403/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **1000 médecins** | 12600 | 248470 | 19.72 | 0.31 | 1065.6 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 235 / 1142 (n=83704) |
| 2 | Ouvrir / rafraîchir l'inbox | 1300 / 50797 (n=41828) |
| 3 | Ouvrir un message enrichi (servi base) | 2283 / 4640 (n=20985) |
| 4 | Ouvrir un message froid (fetch IMAP) | 756 / 1297 (n=3982) |
| 5 | Recherche | 8518 / 35612 (n=6195) |
| 6 | Envoi (acquittement UI) | 2240 / 12244 (n=6275) |
| 7 | Télécharger une PJ (~124 Ko) | 3231 / 7340 (n=8311) |
| 8 | Marquer lu | 1024 / 1810 (n=16726) |
| 9 | Rechercher un patient | 149 / 534 (n=5090) |
| 10 | Ouvrir la page d'un dossier patient | 12371 / 29981 (n=6220) |
| 11 | Fiche patient complète (ressenti médecin) | 26393 / 55371 (n=3106) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 15.1 / 20 | 35.3 / 60 | 4066 | 55371 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 3926 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 4123 ms en moyenne, 60009 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 756 / 1478 (magasin) |
| Backends Postgres (moy/max) | 910 / 1594 |
| PgBouncer `cl_waiting` (échant. non nuls) | 1076/2411 (45 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 1076/2411 (45 %) |
| …dont pool de **maintenance** (échant. non nuls) | 247/2411 (10 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 64596.2 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 40084.7 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 64596.2 |
| RSS par réplica api-mail, Mo (moy/max) | 1770 / 3972 (5 réplicas) |

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 93.7 %** des 1000 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⚠️ Chauffe : **10023 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 12600 s, soit **80 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+10346 s] (82 % de la fenêtre) ; **régime [+10346 s..+12630 s]** porte le verdict

### 1000 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 235 (300) | 1142 (1500) | 83704 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 1300 (300) | 50797 (1000) | 41828 | ❌ |
| 3 | Ouvrir un message enrichi (servi base) | 2283 (100) | 4640 (500) | 20985 | ❌ |
| 4 | Ouvrir un message froid (fetch IMAP) | 756 (800) | 1297 (2500) | 3982 | ✅ |
| 5 | Recherche | 8518 (500) | 35612 (2000) | 6195 | ❌ |
| 6 | Envoi (acquittement UI) | 2240 (1000) | 12244 (3000) | 6275 | ❌ |
| 7 | Télécharger une PJ (~124 Ko) | 3231 (500) | 7340 (2000) | 8311 | ❌ |
| 8 | Marquer lu | 1024 (200) | 1810 (1000) | 16726 | ❌ |
| 9 | Rechercher un patient | 149 (300) | 534 (1500) | 5090 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 12371 (500) | 29981 (2000) | 6220 | ❌ |
| 11 | Fiche patient complète (ressenti médecin) | 26393 (1500) | 55371 (4000) | 3106 | ❌ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🔴 | Ouvrir / rafraîchir l'inbox (`read_list`) | 41828 | 17600 | 50797 | 736182.9 | 72.0 % |
| 🔴 | Recherche (`search`) | 6195 | 11115 | 35612 | 68855.8 | 6.7 % |
| 🔴 | Ouvrir un message enrichi (servi base) (`read_content`) | 20985 | 2540 | 4640 | 53297.4 | 5.2 % |
| 🔴 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 3106 | 13266 | 29981 | 41203.3 | 4.0 % |
| 🔴 | Télécharger une PJ (~124 Ko) (`attachment`) | 8311 | 3776 | 7340 | 31381.6 | 3.1 % |
| 🟠 | Arrivée dashboard (`dashboard`) | 83704 | 361 | 1142 | 30175.9 | 3.0 % |
| 🔴 | Envoi (acquittement UI) (`send`) | 6275 | 4229 | 12244 | 26534.5 | 2.6 % |
| 🔴 | Marquer lu (`mark_read`) | 16726 | 1127 | 1810 | 18845.7 | 1.8 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 2033 | 5150 | 11239 | 10469.6 | 1.0 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 3982 | 832 | 1297 | 3314.1 | 0.3 % |
| 🟠 | Rechercher un patient (`patient_search`) | 5090 | 217 | 534 | 1102.1 | 0.1 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 3114 | 291 | 489 | 905.3 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 7 🔴 · 3 🟠 · 2 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Ouvrir / rafraîchir l'inbox** (`read_list`, 736182.9 s, 72.0 %)
  - **gros consommateur**
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (17600 ms)
  - **dispersion p95/p50 = 39.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 68855.8 s, 6.7 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (11115 ms)
  - **dispersion p95/p50 = 4.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message enrichi (servi base)** (`read_content`, 53297.4 s, 5.2 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (2540 ms)
- **Ouvrir la page d'un dossier patient** (`patient_dossier`, 41203.3 s, 4.0 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (13266 ms)
- **Télécharger une PJ (~124 Ko)** (`attachment`, 31381.6 s, 3.1 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (3776 ms)
- **Arrivée dashboard** (`dashboard`, 30175.9 s, 3.0 %)
  - **dispersion p95/p50 = 4.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Envoi (acquittement UI)** (`send`, 26534.5 s, 2.6 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (4229 ms)
  - **dispersion p95/p50 = 5.5×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Marquer lu** (`mark_read`, 18845.7 s, 1.8 %)
  - **hors grille** — le médecin attend trop
  - **coût par appel élevé** (1127 ms)
- **Traitement (plateforme)** (`treatment`, 10469.6 s, 1.0 %)
  - **coût par appel élevé** (5150 ms)
- **Rechercher un patient** (`patient_search`, 1102.1 s, 0.1 %)
  - **dispersion p95/p50 = 3.6×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation

> Tir A/B (point 5 de task-292). Les candidats mécaniques ci-dessus sont ceux du palier 1000 sur base hydratée (référence 26/08, E015) et ne sont pas re-décomposés ici.

- **F-292-3 tranché — les timeouts du cache Redis ne sont pas causés par le spill, il les aggrave.** 6 568 timeouts sans aucune écriture d'audit, Redis à 1,15 cœur en pointe sur des `HMSET mail:email:*` de corps de message (jusqu'à 1,5 Mo par entrée, 15 ms au slowlog). Remède côté cache, hors task-292 : ne pas mettre en cache le corps complet (ou le compresser / le borner), et mesurer la taille moyenne des entrées `mail:email:*`. Gain attendu : disparition des timeouts et du cœur Redis. Finding à proposer en `/po`.
- **Le coût Postgres du journal est nul à la mesure (point 5 de l'US)** : CPU régime 11,47 vs 11,30 cœurs, `cl_waiting` 45 vs 47 %. Aucune US d'écriture par lot à ouvrir pour Postgres.
- **Le coût visible du journal (jambe A) est celui du drain** : erreurs ×2,7, refus 08P01 ×2,4, p95 +10 %. C'est F-292-2 (login direct par groupe, contre-pression en fin de tir), corrigé dans `2354b44` — vérification par le re-tir journal actif.


## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 20926 | 398 | 1085 | 9496.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 20926 | 34 | 579 | 3539.1 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 20926 | 449 | 1608 | 13519.2 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 20926 | 22 | 645 | 3620.9 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 20914 | 52 | 377 | 2231.7 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 20914 | 34722 | 54963 | 733951.2 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folders`** (1608 ms de p95, 449 ms de p50, n=20926), qui porte **aussi** le temps serveur de l'étape (13519.2 s, 45 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`emails`** (54963 ms de p95, 34722 ms de p50, n=20914), qui porte **aussi** le temps serveur de l'étape (733951.2 s, 100 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 37382 | 1599.6 | 799.2 | 3854.5 | 4796.6 | 83862.0 |
| attachment,palier:1000 | 8311 | 3775.9 | 3230.6 | 5416.7 | 7339.7 | 38208.6 |
| attachment,palier:transition | 111 | 2737.5 | 2345.2 | 4156.1 | 5810.3 | 15225.7 |
| dashboard | 374360 | 245.8 | 100.0 | 676.8 | 921.7 | 60004.6 |
| dashboard,call:coverage,palier:1000 | 20926 | 173.0 | 21.5 | 528.9 | 644.9 | 4033.7 |
| dashboard,call:coverage,palier:transition | 9 | 24.1 | 31.0 | 41.9 | 43.8 | 45.7 |
| dashboard,call:folder,palier:1000 | 20926 | 453.8 | 397.5 | 884.7 | 1084.7 | 14373.7 |
| dashboard,call:folder,palier:transition | 9 | 829.4 | 390.1 | 2667.3 | 2689.6 | 2711.9 |
| dashboard,call:folders,palier:1000 | 20926 | 646.0 | 449.1 | 1309.2 | 1608.3 | 14033.9 |
| dashboard,call:folders,palier:transition | 9 | 16.3 | 16.2 | 21.2 | 25.1 | 29.0 |
| dashboard,call:today,palier:1000 | 20926 | 169.1 | 33.8 | 475.4 | 578.6 | 2481.1 |
| dashboard,call:today,palier:transition | 9 | 1040.0 | 390.4 | 2469.1 | 2599.3 | 2729.4 |
| dashboard,palier:1000 | 83704 | 360.5 | 234.6 | 886.8 | 1142.0 | 14373.7 |
| dashboard,palier:transition | 36 | 477.5 | 40.3 | 2371.0 | 2670.1 | 2729.4 |
| mark_read | 74379 | 524.6 | 405.7 | 1203.3 | 1435.2 | 59999.9 |
| mark_read,palier:1000 | 16726 | 1126.7 | 1024.4 | 1563.4 | 1809.9 | 11852.7 |
| mark_read,palier:transition | 229 | 849.3 | 801.0 | 1259.4 | 1430.3 | 1980.5 |
| patient_docs | 200696 | 1560.9 | 121.3 | 4831.9 | 6632.5 | 60013.8 |
| patient_docs,palier:1000 | 46949 | 3554.1 | 3472.3 | 7840.1 | 8964.1 | 32727.9 |
| patient_docs,palier:transition | 741 | 1682.4 | 1109.6 | 4292.0 | 5492.6 | 9323.6 |
| patient_dossier | 13609 | 5353.4 | 1000.5 | 17632.6 | 23144.4 | 52996.3 |
| patient_dossier,palier:1000 | 3106 | 13265.7 | 12370.6 | 27058.3 | 29980.7 | 52996.3 |
| patient_dossier,palier:transition | 44 | 6829.4 | 6550.6 | 15376.5 | 16135.2 | 22196.6 |
| patient_opposition | 13609 | 123.0 | 54.5 | 287.5 | 341.3 | 5812.1 |
| patient_opposition,palier:1000 | 3114 | 290.7 | 261.4 | 387.2 | 489.1 | 5812.1 |
| patient_opposition,palier:transition | 57 | 157.7 | 165.3 | 232.3 | 263.3 | 493.7 |
| patient_search | 22147 | 96.5 | 44.5 | 217.2 | 336.4 | 22857.6 |
| patient_search,palier:1000 | 5090 | 216.5 | 148.6 | 388.7 | 534.3 | 5493.5 |
| patient_search,palier:transition | 79 | 159.8 | 109.9 | 280.1 | 360.7 | 2335.2 |
| read_content | 93480 | 1066.6 | 447.1 | 2613.2 | 3151.3 | 59998.6 |
| read_content,palier:1000 | 20985 | 2539.8 | 2282.8 | 3524.8 | 4640.2 | 29570.2 |
| read_content,palier:transition | 334 | 1669.8 | 1635.3 | 2442.3 | 2767.1 | 7732.2 |
| read_content_cold | 17628 | 621.1 | 561.1 | 924.7 | 1123.4 | 59995.2 |
| read_content_cold,palier:1000 | 3982 | 832.3 | 756.2 | 1106.8 | 1296.9 | 7979.3 |
| read_content_cold,palier:transition | 61 | 898.7 | 776.5 | 1325.3 | 1674.1 | 1993.9 |
| read_list | 187180 | 7121.5 | 169.2 | 29926.6 | 39999.8 | 60020.6 |
| read_list,call:emails,palier:1000 | 20914 | 35093.8 | 34721.8 | 50797.0 | 54963.2 | 60020.6 |
| read_list,call:emails,palier:transition | 71 | 19343.5 | 22277.0 | 25941.5 | 26725.4 | 27773.4 |
| read_list,call:folder,palier:1000 | 20914 | 106.7 | 52.0 | 251.3 | 376.8 | 3200.6 |
| read_list,call:folder,palier:transition | 71 | 71.8 | 34.3 | 152.8 | 251.7 | 381.2 |
| read_list,palier:1000 | 41828 | 17600.2 | 1299.9 | 45705.7 | 50797.0 | 60020.6 |
| read_list,palier:transition | 142 | 9707.6 | 187.7 | 23868.7 | 25899.0 | 27773.4 |
| search | 27819 | 6845.3 | 4026.4 | 16543.6 | 32410.4 | 59761.9 |
| search,palier:1000 | 6195 | 11114.7 | 8518.3 | 19916.9 | 35611.8 | 59761.9 |
| search,palier:transition | 46 | 6231.6 | 5630.3 | 8168.7 | 9814.3 | 44250.7 |
| send | 27789 | 2000.1 | 817.3 | 5489.3 | 8180.2 | 120000.5 |
| send,palier:1000 | 6275 | 4228.6 | 2239.6 | 10174.4 | 12244.1 | 38767.1 |
| send,palier:transition | 73 | 2150.4 | 1316.4 | 6078.0 | 6586.6 | 7667.5 |
| treatment | 8989 | 2056.8 | 772.1 | 5334.3 | 7008.0 | 186964.6 |
| treatment,palier:1000 | 2033 | 5149.8 | 4204.5 | 8990.8 | 11238.7 | 41820.8 |
| treatment,palier:transition | 28 | 2939.8 | 2534.8 | 5292.6 | 6429.7 | 8071.4 |
| warmup | 11000 | 4122.6 | 409.9 | 9648.3 | 18485.9 | 60008.8 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-09T12:08:45.420000+00:00 → 2026-09-09T15:39:51.297000+00:00 (12666 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-140844.csv`) | ✅ 256951 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-20856` | 0.50 | 6 | 19 | 0.027 | 17.69 |
| `DESKTOP-DEV-X2C-46028` | 0.57 | 6 | 18 | 0.028 | 22.20 |
| `DESKTOP-DEV-X2C-56996` | 0.55 | 5 | 18 | 0.030 | 22.29 |
| `DESKTOP-DEV-X2C-61220` | 0.58 | 5 | 19 | 0.028 | 19.67 |
| `DESKTOP-DEV-X2C-7864` | 0.63 | 9 | 20 | 0.039 | 16.09 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#32776` | 0.00 | 0.29 | 40 |
| `com.docker.backend#34112` | 1.74 | 5.09 | 1461 |
| `dcp#12704` | 0.00 | 0.04 | 12 |
| `dcp#22408` | 0.81 | 2.49 | 1347 |
| `dcp#34496` | 0.00 | 0.24 | 40 |
| `dcp#44288` | 0.00 | 0.09 | 12 |
| `dcp#45352` | 0.00 | 0.00 | 12 |
| `dcp#49228` | 0.00 | 0.19 | 12 |
| `dcp#52100` | 0.00 | 0.19 | 12 |
| `dcp#53856` | 0.00 | 0.04 | 12 |
| `dcp#59140` | 0.00 | 0.09 | 12 |
| `dcp#59952` | 0.00 | 0.04 | 12 |
| `k6#61464` | 0.17 | 3.19 | 2002 |
| `mss.mail.api#20856` | 0.31 | 1.84 | 3432 |
| `mss.mail.api#46028` | 0.30 | 1.60 | 3398 |
| `mss.mail.api#56996` | 0.31 | 1.74 | 3259 |
| `mss.mail.api#61220` | 0.32 | 1.71 | 3674 |
| `mss.mail.api#7864` | 0.34 | 1.55 | 3972 |
| `vmmemWSL#35744` | 8.02 | 16.70 | 32905 |
| `loadtest-otel-collector-ewjuffvz` | 0.02 | 0.24 | 119 |
| `loadtest-pgbouncer-afebvakb` | 0.56 | 1.02 | 30 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.19 | 177 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.30 | 301 |
| `mss-mail-rabbitmq-smjhmwej` | 0.01 | 0.06 | 156 |
| `mss-mail-redis-b6152948` | 0.21 | 1.15 | 2737 |
| `mss-mail-seq-b6152948` | 0.01 | 0.31 | 178 |
| `postgres-pgvector` | 5.93 | 15.07 | 11489 |

- **Hôte** : CPU 66.5 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 75
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 4264, cl_waiting max 132, cl_waiting_maintenance max 4, cl_waiting_practitioner max 132, count max 1002, maxwait_maintenance_ms max 64596, maxwait_ms max 64596, maxwait_practitioner_ms max 40085, sv_active max 589, sv_idle max 1019
- **Backends Postgres** : practitioner_databases max 1577, total max 1594

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 60000.0 | 2529 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 3939.3 | 2530 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 60000.0 | 2526 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 60000.0 | 2522 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 2463.9 | 2525 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 13750.0 | 2505 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 4645.8 | 2522 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 60000.0 | 2527 |
| `api/v{version:apiVersion}/Mail/sendmail` | 48133.8 | 2491 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 2264.3 | 2511 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 54500.0 | 2508 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 2068.8 | 2508 |
| `api/v{version:apiVersion}/Search/semantic` | 55329.5 | 2506 |
| `api/v{version:apiVersion}/Settings` | 226.8 | 6 |
| `api/v{version:apiVersion}/Settings/getsettings` | 8.1 | 6 |
| `api/v{version:apiVersion}/Sync/coverage` | 1105.6 | 2525 |

- **p95 client global (k6)** : 9418.5 ms
- **p95 serveur le plus élevé** : 60000.0 ms
- **Écart** : -50581.5 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 2.93 |
| Documents CDA /s | 2.93 |
| Durée traitement CDA (s, p95) | 1.07 |
| Événements de session IMAP /s | 2.36 |
| Recherches (s, p95) | 55.295 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.1 | 2033.4 | 26500 | 26.3 (1.3 %), p95 3125 | 1881.5 (92.5 %), p95 26500 | 125.5 (6.2 %), p95 1075 |
| `GetMail` | 11.4 | 1498.6 | 60000 | 84.9 (5.7 %), p95 4418 | 1079.1 (72.0 %), p95 15383 | 334.5 (22.3 %), p95 60000 |
| `GetMailsByUids` | 14.8 | 10049.7 | 60000 | 2.4 (0.0 %), p95 788 | 1250.8 (12.4 %), p95 18625 | 8796.5 (87.5 %), p95 60000 |

- **`EnrichPersistMail`** — sur 2033.4 ms en moyenne (8.1 requête(s) SQL par appel) : 26.3 ms attente d'une connexion, 1881.5 ms exécution SQL, 125.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 1498.6 ms en moyenne (11.4 requête(s) SQL par appel) : 84.9 ms attente d'une connexion, 1079.1 ms exécution SQL, 334.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 10049.7 ms en moyenne (14.8 requête(s) SQL par appel) : 2.4 ms attente d'une connexion, 1250.8 ms exécution SQL, 8796.5 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.0 | 334.5 | 33333.1 | 0.9 | 1.3 | 0.9 | 2.5 | non relevé | 0.0 | 0.9 | 2.3 | 0.1 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 239.7 | 8796.5 | 36703.2 | 21.5 | 32.8 | 21.5 | 34.9 | 21.5 | 0.0 | 21.5 | 6.7 | 0.0 | 21.4 | 51.7 | 6.2 |

- **`GetMail`** — sur 334.5 ms de matérialisation, l'appel a construit 10.0 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.5 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.3 résultats de biologie, 0.1 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **33333.1 µs**.

- **`GetMailsByUids`** — sur 8796.5 ms de matérialisation, l'appel a construit 239.7 objets, dont 21.5 messages, 32.8 étiquettes, 21.5 destinataires, 34.9 pièces jointes, 21.5 identifiants enrichis, 0.0 acquittements, 21.5 documents médicaux, 6.7 résultats de biologie, 0.0 éléments de synthèse, 21.4 corps de messages, 51.7 objets de fil, 6.2 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **36703.2 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **6.0 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.3 | 2587.8 | 26500 | 131.3 (5.1 %), p95 537 | 29.0 (1.1 %), p95 388 | 29.8 (1.2 %), p95 1825 | 2218.2 (85.7 %), p95 26500 | 179.5 (6.9 %), p95 4208 |

- **Enrichir un message** — sur 2587.8 ms en moyenne (5.3 message(s) par requête) : 131.3 ms fetch IMAP, 29.0 ms extraction XDM, 29.8 ms parsing CDA, 2218.2 ms écritures base, 179.5 ms le reste (DTO, notifications). **Poste dominant : écritures base.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 3833.0 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 1835.9 | 4987 | 0.0 (0.0 %), p95 5 | 1119.2 (61.0 %), p95 3977 | 166.3 (9.1 %), p95 523 | 342.8 (18.7 %), p95 488 | 406.7 (22.2 %), p95 954 | 206.9 (11.3 %), p95 218 |

- **Envoyer un message** — sur 1835.9 ms en moyenne : 0.0 ms garde d'opposition, 1119.2 ms construction MIME, 166.3 ms obtention de session SMTP, 342.8 ms transmission + acquittement, 406.7 ms archivage Sent, 206.9 ms le reste. **Poste dominant : construction MIME.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.738 | 2.425 | 0.05 |
| `imap_session` | 0.499 | 2.425 | 35.71 |
| `in_process_fetch` | 0.005 | 2.425 | 0.05 |
| `smtp_session` | 0.005 | 2.209 | 3.87 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 2.380 | 4.125 | 2.316 | 3.87 |
| `EnrichEmails` | 0.068 | 4.250 | 2.425 | 4.250 | 3.78 |
| `GetAttachmentStream` | 0.338 | 7.750 | 9.500 | 8.000 | 1.55 |
| `GetEmailContent` | 0.012 | 2.208 | 2.425 | 2.208 | 2.45 |
| `GetFolders` | 0.371 | ≥ 60 ⚠️ | ≥ 60 ⚠️ | 2.448 | 3.44 |
| `ProcessEmailUid` | 0.074 | 2.425 | — | 2.425 | 0.05 |
| `ReadFolder` | 0.812 | 2.425 | ≥ 60 ⚠️ | 2.138 | 17.84 |
| `UpdateFlag` | 1.370 | 2.488 | 2.425 | 2.488 | 9.55 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.500** | 0.665 | 0.813 | 0.0 % |
| `EnrichEmails` | **0.454** | 0.571 | 0.831 | 0.0 % |
| `GetAttachmentStream` | **3.200** | 5.250 | 8.000 | 100.0 % |
| `GetEmailContent` | **0.796** | 0.925 | 1.475 | 0.0 % |
| `GetFolders` | **0.300** | 0.414 | 0.583 | 0.0 % |
| `ProcessEmailUid` | **0.487** | 0.487 | 2.425 | 3.2 % |
| `ReadFolder` | **0.545** | 0.644 | 0.735 | 0.0 % |
| `UpdateFlag` | **0.646** | 0.745 | 0.879 | 0.0 % |

- 🔴 **`GetAttachmentStream` : détention tenue en régime** — médiane 3.200 s et **100.0 %** des relevés au-dessus de 2 s. Ce n'est plus une pointe : `imap_session` sérialise toutes les opérations IMAP du praticien, donc les voisins la paient.
- 🟠 **`ProcessEmailUid` : pointe non représentative.** Médiane **0.487 s**, p90 0.487 s, mais une pointe à 2.425 s sur 3.2 % des relevés. **Citer la pointe comme valeur d'exploitation serait une faute de lecture** — c'est la médiane qui décrit le médecin.

> ⚠️ **Pourquoi cette table existe** (task-276). La table qui la précède réduit chaque série à sa **pointe**. Au tir du 2026-08-29, `ReadFolder` y valait 11,871 s — lu comme « la fusion de task-270 a allongé la section critique », alors que sa médiane en régime valait 0,469 s, **sous** les 0,692 s de l'opération qu'elle remplace. La pointe était réelle ; la conclusion qu'on en tirait, non. Même famille de piège que les buckets en millisecondes (task-211), le plafond d'histogramme (task-245) et la saturation lue comme un timeout (task-271).
| Voie | Acquisitions /s |
|---|---|
| `read` | 35.71 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

✅ **Lecture rétablie** pour `GetFolders` : l'agrégat est saturé (« ≥ 60 s », c'est-à-dire *non mesuré* — `histogram_quantile` rend la dernière borne finie quand le quantile tombe dans `+Inf`), mais l'exploitation, elle, tient dans l'instrument. La queue appartient à la chauffe, pas au régime établi.

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 1.370 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 132.00 clients | 0 clients | 100.0 % | 44.7 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 15.07 cœurs | 24 cœurs | 62.8 % | 0.0 % — transitoire |
| processus `k6#61464` (CPU) | 3.19 cœurs | 24 cœurs | 13.3 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-7864` | 9.00 éléments | 100 éléments | 9.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#20856` (CPU) | 1.84 cœurs | 24 cœurs | 7.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#56996` (CPU) | 1.74 cœurs | 24 cœurs | 7.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#61220` (CPU) | 1.71 cœurs | 24 cœurs | 7.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#46028` (CPU) | 1.60 cœurs | 24 cœurs | 6.7 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 44.7 % des échantillons de la fenêtre.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 121403 — dont **121403** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump : `seq-journey-1000-task292-audit-off-20260909-173951.jsonl` (Error+Fatal, timeouts cache). Comptages API Seq bornés `rangeStartUtc`/`rangeEndUtc` + `@Timestamp` (12:08Z → 15:45Z).

| Requête | Compte | Lecture |
|---|---|---|
| `[Audit]%` (hors « DISABLED ») | **0** | Interrupteur de banc effectif ; base témoin 24 778 → 24 778 traces. |
| `@Level = 'Fatal'` | 1 | `Microsoft.AspNetCore.Server.Kestrel` « Connection id … application never completed » à 14:54:26Z — connexion abandonnée par k6 sur une requête longue, hors audit. |
| `[Cache] Timeout getting key` / `Best-effort Set failed` | **6 568** / 25 | 21 835 / 287 avec le journal. Sans spill, un tiers des timeouts subsiste, et Redis pointe à 1,15 cœur sur des `HMSET mail:email:*` de corps de message (slowlog 16h10 et 17h13). Le spill **aggrave** (×3,3) un problème que le cache a déjà seul. |
| `08P01` | **270** | 646 avec le journal, 85 787 le 08/09. |
| `HTTP … Status=500` / `503` | 340 / **0** | 724 / 11 avec le journal. |
| `Parsing completed` | 2 264 | 7 377 le matin : chauffe aboutie à 93,7 % (moins de lots à rejouer), bases plus hydratées. |
| scratch `mss-ihe-xdm` / `Failed to parse entity headers` | 0 / 0 | La garde a recréé le répertoire en 2 s (14h41:02) avant qu'une requête ne le manque. |
| Error+Fatal / Warning | 1 301 / 40 286 | 2 454 / 185 105 avec le journal (dont 111 678 `Channel full`). |

