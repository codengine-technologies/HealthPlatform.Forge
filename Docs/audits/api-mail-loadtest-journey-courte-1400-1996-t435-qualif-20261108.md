# Rapport de tir — journey-courte-1400-1996-20261108-t435-qualif

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261108-t435-qualif-174802.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 1 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** sur le chemin du médecin (`cl_waiting` non nul sur 21 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.012 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 762445 — **débit émergent global** : 337.1 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 54043 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 337.1 | **141.8** | 58.6 | **496.5** | — | 12989.3 | 0.01 | 100.0 | 0 | 0 | 248398/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214087 | 290.48 | 0.01 | 829.6 |
| **1996 médecins** | 1080 | 933 | 387100 | 414.90 | 0.01 | 1498.7 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 59 / 539 (n=64056) | 64 / 563 (n=114748) |
| 2 | Ouvrir / rafraîchir l'inbox | 40 / 93 (n=31988) | 50 / 137 (n=57390) |
| 3 | Ouvrir un message enrichi (servi base) | 33 / 63 (n=15992) | 45 / 107 (n=28696) |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 / 507 (n=6473) | 453 / 521 (n=11457) |
| 5 | Recherche | 327 / 641 (n=4821) | 348 / 632 (n=8679) |
| 6 | Envoi (acquittement UI) | 483 / 922 (n=4754) | 491 / 946 (n=8576) |
| 7 | Télécharger une PJ (~124 Ko) | 37 / 73 (n=6462) | 51 / 129 (n=11436) |
| 8 | Marquer lu | 34 / 82 (n=12764) | 53 / 108 (n=23001) |
| 9 | Rechercher un patient | 55 / 65 (n=4658) | 56 / 76 (n=8610) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 65 (n=7022) | 59 / 77 (n=12948) |
| 11 | Fiche patient complète (ressenti médecin) | 262 / 440 (n=3511) | 336 / 701 (n=6474) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.2 / 60 | 8052 | 440 |
| **1996 médecins** | 14.6 / 20 | 34.4 / 60 | 14422 | 701 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2235 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 657 ms en moyenne, 12989 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2255 / 3113 (magasin) | 2255 / 3113 (magasin) |
| Backends Postgres (moy/max) | 1240 / 1437 | 1988 / 2025 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 1 | 0 / 3 |
| PgBouncer `cl_waiting` — chemin du médecin (échant. non nuls) | 36/172 (21 %) | 52/148 (35 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 36/172 (21 %) | 52/148 (35 %) |
| …dont **registre** des comptes (échant. non nuls) | 0/172 (0 %) | 0/148 (0 %) |
| …dont **maintenance** (échant. non nuls) | 0/172 (0 %) | 0/148 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 46.0 | 152.9 |
| …dont bases **praticien** — chemin du médecin | 46.0 | 152.9 |
| …dont **registre** des comptes — chemin du médecin | 0.0 | 0.0 |
| …dont **maintenance** (`postgres`, `pgbouncer`) | 0.0 | 0.0 |
| Attente PgBouncer cumulée — chemin du médecin (s) | 728.5 | 1337.4 |
| …par transaction du médecin (ms) | 0.4 | 0.5 |
| …part du temps des transactions (attente comprise) | 18.3 % | 19.2 % |
| …part du temps des requêtes HTTP du palier (k6) | 3.4 % | 3.2 % |
| Attente PgBouncer cumulée — maintenance (s) | 0.0 | 0.0 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | 0.009 / 0.015 / 0.035 | 0.011 / 0.019 / 0.022 |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 120 / 361 | 99 / 284 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 102 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1406 | 1995 |
| Backends **directs** — audit + provisionnement (max) | 30 | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 96.0 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 | 0 / 1 |
| RSS par réplica api-mail, Mo (moy/max) | 753 / 1638 (8 réplicas) | 2023 / 2282 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1437.0 / 2500** (57.5 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2025.0 / 2500** (81.0 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15992)
- palier 1996 : cohorte 1996 chauffée à 99.5 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28696)

> ⓘ Chauffe : **302 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 59 (300) | 539 (1500) | 64056 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 40 (300) | 93 (1000) | 31988 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 33 (100) | 63 (500) | 15992 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 444 (800) | 507 (2500) | 6473 | ✅ |
| 5 | Recherche | 327 (500) | 641 (2000) | 4821 | ✅ |
| 6 | Envoi (acquittement UI) | 483 (1000) | 922 (3000) | 4754 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 37 (500) | 73 (2000) | 6462 | ✅ |
| 8 | Marquer lu | 34 (200) | 82 (1000) | 12764 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 65 (1500) | 4658 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 65 (2000) | 7022 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 262 (1500) | 440 (4000) | 3511 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 64 (300) | 563 (1500) | 114748 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 50 (300) | 137 (1000) | 57390 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 45 (100) | 107 (500) | 28696 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 453 (800) | 521 (2500) | 11457 | ✅ |
| 5 | Recherche | 348 (500) | 632 (2000) | 8679 | ✅ |
| 6 | Envoi (acquittement UI) | 491 (1000) | 946 (3000) | 8576 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 51 (500) | 129 (2000) | 11436 | ✅ |
| 8 | Marquer lu | 53 (200) | 108 (1000) | 23001 | ✅ |
| 9 | Rechercher un patient | 56 (300) | 76 (1500) | 8610 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 59 (500) | 77 (2000) | 12948 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 336 (1500) | 701 (4000) | 6474 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 114748 | 162 | 563 | 18617.9 | 44.8 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8576 | 633 | 946 | 5427.7 | 13.1 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11457 | 455 | 521 | 5214.9 | 12.6 % |
| 🟢 | Recherche (`search`) | 8679 | 398 | 632 | 3451.7 | 8.3 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 57390 | 58 | 137 | 3343.7 | 8.1 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28696 | 54 | 107 | 1540.1 | 3.7 % |
| 🟢 | Marquer lu (`mark_read`) | 23001 | 60 | 108 | 1386.4 | 3.3 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 11436 | 67 | 129 | 766.9 | 1.8 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7211 | 102 | 156 | 738.6 | 1.8 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8610 | 48 | 76 | 414.2 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6474 | 59 | 77 | 379.7 | 0.9 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6474 | 37 | 73 | 242.5 | 0.6 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 1 🟠 · 11 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 18617.9 s, 44.8 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 8.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 16014 | 391 | 978 | 6123.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 16014 | 59 | 496 | 2182.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 16014 | 20 | 164 | 722.0 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 16014 | 57 | 67 | 917.8 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15994 | 15 | 114 | 474.1 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15994 | 50 | 84 | 854.9 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28687 | 400 | 996 | 11298.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28687 | 63 | 503 | 3998.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28687 | 28 | 182 | 1586.3 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28687 | 60 | 82 | 1734.7 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28695 | 20 | 128 | 1090.0 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28695 | 69 | 143 | 2253.7 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (996 ms de p95, 400 ms de p50, n=28687), qui porte **aussi** le temps serveur de l'étape (11298.6 s, 61 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (143 ms de p95, 69 ms de p50, n=28695), qui porte **aussi** le temps serveur de l'étape (2253.7 s, 67 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21961 | 68.8 | 44.6 | 103.4 | 164.0 | 1437.8 |
| attachment,palier:1400 | 6462 | 41.6 | 36.9 | 60.0 | 73.2 | 396.2 |
| attachment,palier:1996 | 11436 | 67.1 | 51.1 | 102.3 | 128.7 | 1302.0 |
| attachment,palier:transition | 605 | 133.0 | 49.5 | 373.2 | 462.8 | 1091.5 |
| dashboard | 220616 | 166.2 | 62.6 | 470.1 | 611.1 | 1961.7 |
| dashboard,call:coverage,palier:1400 | 16014 | 57.3 | 56.6 | 63.6 | 67.2 | 135.7 |
| dashboard,call:coverage,palier:1996 | 28687 | 60.5 | 59.7 | 74.4 | 81.8 | 717.6 |
| dashboard,call:coverage,palier:transition | 1078 | 108.7 | 84.6 | 198.1 | 235.3 | 467.9 |
| dashboard,call:folder,palier:1400 | 16014 | 382.4 | 390.6 | 760.9 | 978.2 | 1519.1 |
| dashboard,call:folder,palier:1996 | 28687 | 393.9 | 399.8 | 775.2 | 996.5 | 1931.9 |
| dashboard,call:folder,palier:transition | 1078 | 460.3 | 464.1 | 741.0 | 865.2 | 1516.7 |
| dashboard,call:folders,palier:1400 | 16014 | 45.1 | 19.6 | 148.2 | 163.9 | 660.7 |
| dashboard,call:folders,palier:1996 | 28687 | 55.3 | 27.8 | 161.9 | 181.6 | 944.0 |
| dashboard,call:folders,palier:transition | 1078 | 106.0 | 89.0 | 223.2 | 296.9 | 474.6 |
| dashboard,call:today,palier:1400 | 16014 | 136.3 | 58.5 | 475.8 | 496.4 | 770.7 |
| dashboard,call:today,palier:1996 | 28687 | 139.4 | 62.7 | 479.6 | 502.8 | 1128.9 |
| dashboard,call:today,palier:transition | 1078 | 305.4 | 170.3 | 607.6 | 656.6 | 990.4 |
| dashboard,palier:1400 | 64056 | 155.3 | 58.7 | 456.7 | 539.3 | 1519.1 |
| dashboard,palier:1996 | 114748 | 162.3 | 63.5 | 463.4 | 563.1 | 1931.9 |
| dashboard,palier:transition | 4312 | 245.1 | 137.0 | 574.0 | 658.5 | 1516.7 |
| mark_read | 43981 | 62.8 | 48.3 | 95.7 | 125.1 | 1058.2 |
| mark_read,palier:1400 | 12764 | 46.2 | 34.1 | 75.7 | 82.2 | 333.4 |
| mark_read,palier:1996 | 23001 | 60.3 | 53.4 | 95.0 | 108.3 | 840.8 |
| mark_read,palier:transition | 1225 | 86.4 | 62.8 | 224.6 | 270.5 | 445.0 |
| patient_docs | 179255 | 69.5 | 51.3 | 123.7 | 172.0 | 1243.3 |
| patient_docs,palier:1400 | 51071 | 45.3 | 41.8 | 81.8 | 96.9 | 290.5 |
| patient_docs,palier:1996 | 94339 | 65.6 | 55.7 | 125.0 | 153.4 | 1223.4 |
| patient_docs,palier:transition | 5238 | 102.5 | 54.0 | 256.9 | 429.2 | 1170.0 |
| patient_dossier | 12283 | 39.3 | 27.9 | 59.9 | 89.2 | 851.7 |
| patient_dossier,palier:1400 | 3511 | 26.1 | 23.8 | 34.7 | 42.6 | 92.0 |
| patient_dossier,palier:1996 | 6474 | 37.5 | 31.5 | 59.7 | 73.1 | 181.6 |
| patient_dossier,palier:transition | 357 | 57.3 | 27.6 | 165.6 | 217.2 | 344.9 |
| patient_opposition | 12283 | 60.6 | 57.6 | 70.8 | 82.6 | 714.2 |
| patient_opposition,palier:1400 | 3511 | 56.6 | 56.0 | 61.8 | 65.5 | 132.4 |
| patient_opposition,palier:1996 | 6474 | 58.7 | 59.0 | 70.7 | 77.2 | 714.2 |
| patient_opposition,palier:transition | 356 | 68.7 | 57.7 | 97.9 | 144.1 | 248.0 |
| patient_search | 16311 | 49.5 | 55.6 | 69.7 | 81.0 | 719.8 |
| patient_search,palier:1400 | 4658 | 44.0 | 55.3 | 61.1 | 64.9 | 119.6 |
| patient_search,palier:1996 | 8610 | 48.1 | 55.8 | 69.5 | 75.8 | 719.8 |
| patient_search,palier:transition | 488 | 58.2 | 55.8 | 102.6 | 131.8 | 326.7 |
| read_content | 55154 | 56.4 | 39.2 | 86.7 | 125.8 | 1090.3 |
| read_content,palier:1400 | 15992 | 36.4 | 33.3 | 51.1 | 63.1 | 168.2 |
| read_content,palier:1996 | 28696 | 53.7 | 45.1 | 87.4 | 106.8 | 916.6 |
| read_content,palier:transition | 1371 | 102.4 | 43.6 | 298.0 | 366.2 | 636.4 |
| read_content_cold | 22148 | 455.2 | 450.2 | 506.6 | 528.2 | 1202.6 |
| read_content_cold,palier:1400 | 6473 | 445.5 | 443.7 | 492.8 | 506.9 | 859.2 |
| read_content_cold,palier:1996 | 11457 | 455.2 | 452.9 | 504.5 | 520.6 | 1202.6 |
| read_content_cold,palier:transition | 566 | 469.4 | 453.6 | 561.6 | 600.2 | 750.3 |
| read_list | 110308 | 61.6 | 45.7 | 113.6 | 157.0 | 1013.9 |
| read_list,call:emails,palier:1400 | 15994 | 53.5 | 49.5 | 71.1 | 84.0 | 182.4 |
| read_list,call:emails,palier:1996 | 28695 | 78.5 | 68.6 | 121.0 | 143.0 | 1013.9 |
| read_list,call:emails,palier:transition | 1280 | 175.7 | 75.4 | 450.8 | 528.2 | 780.8 |
| read_list,call:folder,palier:1400 | 15994 | 29.6 | 15.2 | 31.5 | 113.9 | 507.3 |
| read_list,call:folder,palier:1996 | 28695 | 38.0 | 20.4 | 60.8 | 127.7 | 794.5 |
| read_list,call:folder,palier:transition | 1280 | 62.1 | 23.3 | 152.5 | 197.4 | 552.3 |
| read_list,palier:1400 | 31988 | 41.5 | 39.6 | 67.2 | 92.7 | 507.3 |
| read_list,palier:1996 | 57390 | 58.3 | 50.2 | 111.2 | 136.7 | 1013.9 |
| read_list,palier:transition | 2560 | 118.9 | 59.1 | 362.9 | 456.4 | 780.8 |
| search | 16561 | 403.3 | 343.6 | 532.1 | 793.9 | 2075.4 |
| search,palier:1400 | 4821 | 378.8 | 327.5 | 475.2 | 641.5 | 1537.3 |
| search,palier:1996 | 8679 | 397.7 | 347.7 | 488.1 | 632.0 | 1597.4 |
| search,palier:transition | 458 | 457.0 | 360.3 | 723.7 | 931.7 | 1829.3 |
| send | 15742 | 647.5 | 514.4 | 918.2 | 951.1 | 1546.1 |
| send,palier:1400 | 4754 | 627.9 | 483.1 | 900.6 | 922.1 | 1095.8 |
| send,palier:1996 | 8576 | 632.9 | 490.8 | 918.3 | 946.4 | 1546.1 |
| send,palier:transition | 472 | 657.6 | 579.3 | 947.6 | 1010.4 | 1208.2 |
| treatment | 13872 | 100.6 | 83.7 | 131.4 | 184.0 | 3812.8 |
| treatment,palier:1400 | 4026 | 73.3 | 79.3 | 96.9 | 106.6 | 168.3 |
| treatment,palier:1996 | 7211 | 102.4 | 88.5 | 133.0 | 155.9 | 3721.4 |
| treatment,palier:transition | 352 | 156.4 | 88.2 | 366.6 | 480.0 | 1099.7 |
| warmup | 21956 | 657.4 | 336.2 | 758.5 | 3026.8 | 12989.3 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-08T16:10:20.946000+00:00 → 2026-11-08T16:48:02.522000+00:00 (2262 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-t435-qualif.csv`) | ✅ 80050 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-64552` | 0.90 | 10 | 27 | 0.030 | 4.64 |
| `DESKTOP-DEV-X2C-66840` | 0.96 | 22 | 36 | 0.034 | 4.65 |
| `DESKTOP-DEV-X2C-67760` | 1.02 | 5 | 36 | 0.034 | 4.84 |
| `DESKTOP-DEV-X2C-67980` | 0.95 | 5 | 44 | 0.022 | 4.98 |
| `DESKTOP-DEV-X2C-72864` | 0.99 | 12 | 29 | 0.035 | 5.02 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.20 | 4.17 | 2488 |
| `com.docker.backend#34124` | 0.01 | 0.16 | 39 |
| `dcp#33988` | 0.00 | 0.00 | 12 |
| `dcp#40084` | 0.00 | 0.00 | 12 |
| `dcp#41816` | 0.00 | 0.04 | 12 |
| `dcp#56500` | 0.00 | 0.00 | 12 |
| `dcp#60212` | 0.00 | 0.00 | 12 |
| `dcp#62420` | 0.00 | 0.00 | 12 |
| `dcp#66764` | 0.00 | 0.00 | 12 |
| `dcp#68768` | 0.00 | 0.00 | 12 |
| `dcp#69172` | 0.00 | 0.04 | 13 |
| `dcp#70368` | 0.00 | 0.12 | 13 |
| `dcp#70936` | 0.00 | 0.13 | 52 |
| `dcp#71128` | 0.73 | 2.45 | 3252 |
| `dcp#75032` | 0.00 | 0.08 | 13 |
| `dcp#79636` | 0.00 | 0.04 | 13 |
| `dcp#79704` | 0.00 | 0.04 | 12 |
| `k6#306387` | 0.86 | 1.83 | 2887 |
| `mss.mail.api#64552` | 0.65 | 1.93 | 2296 |
| `mss.mail.api#66840` | 0.64 | 2.25 | 2291 |
| `mss.mail.api#67760` | 0.61 | 3.21 | 2169 |
| `mss.mail.api#67980` | 0.63 | 2.20 | 2155 |
| `mss.mail.api#72864` | 0.64 | 3.52 | 2235 |
| `mss.mail.api.tests#44108` | 0.61 | 0.61 | 26 |
| `mss.mail.api.tests#50392` | 1.04 | 1.04 | 28 |
| `mss.mail.api.tests#56656` | 0.96 | 0.96 | 1 |
| `mss.mail.e2e#73964` | 0.00 | 0.13 | 33 |
| `vmmemWSL#36464` | 5.22 | 11.05 | 49480 |
| `loadtest-otel-collector-eawuhahd` | 0.02 | 0.15 | 113 |
| `loadtest-pgbouncer-msrutgem` | 0.42 | 0.86 | 48 |
| `mss-mail-flagsmith-app-b6152948` | 0.10 | 0.40 | 471 |
| `mss-mail-flagsmith-db-b6152948` | 0.00 | 0.13 | 178 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.05 | 161 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.06 | 197 |
| `mss-mail-rabbitmq-ybthvkzy` | 0.01 | 0.05 | 142 |
| `mss-mail-redis-b6152948` | 0.26 | 1.34 | 979 |
| `mss-mail-rediscommander-bbkqahgp` | 0.00 | 0.17 | 42 |
| `mss-mail-seq-b6152948` | 0.11 | 1.04 | 5346 |
| `postgres-pgvector` | 2.06 | 9.02 | 47534 |

- **Hôte** : CPU 62.9 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 43
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9480, cl_waiting max 26, cl_waiting_doctor_path max 26, cl_waiting_maintenance max 0, cl_waiting_practitioner max 26, cl_waiting_registry max 0, count max 1997, login_retry_delta max 0, maxwait_doctor_path_ms max 153, maxwait_maintenance_ms max 0, maxwait_ms max 153, maxwait_practitioner_ms max 153, maxwait_registry_ms max 0, query_delta_maintenance max 2, query_delta_practitioner max 41746, query_delta_registry max 0, sv_active max 148, sv_idle max 1586, sv_login max 3, wait_us_delta_maintenance max 0, wait_us_delta_practitioner max 80140580, wait_us_delta_registry max 0, xact_delta_maintenance max 2, xact_delta_practitioner max 41641, xact_delta_registry max 0, xact_us_delta_maintenance max 0, xact_us_delta_practitioner max 398751586, xact_us_delta_registry max 0
- **Backends Postgres** : audit max 5, cache_mb max 39424, direct max 30, idle_over_60s max 218, majfault_per_s max 1, pooler max 1995, practitioner_databases max 1988, provision max 5, rss_mb max 6173, seconds max 0, started_last_60s max 361, total max 2025, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 21759.8 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 4049.1 | 450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 688.1 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 833.5 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 920.8 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 684.7 | 443 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 488.0 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 729.4 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 1972.5 | 432 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 241.9 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 426.2 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 248.0 | 442 |
| `api/v{version:apiVersion}/Search/semantic` | 2125.0 | 442 |
| `api/v{version:apiVersion}/Sync/coverage` | 456.2 | 447 |

- **p95 client global (k6)** : 496.5 ms
- **p95 serveur le plus élevé** : 21759.8 ms
- **Écart** : -21263.4 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.84 |
| Documents CDA /s | 0.84 |
| Durée traitement CDA (s, p95) | 1.52 |
| Événements de session IMAP /s | 4.11 |
| Recherches (s, p95) | 2.125 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 71.4 | 650 | 0.0 (0.0 %), p95 5 | 44.5 (62.4 %), p95 650 | 26.7 (37.5 %), p95 446 |
| `GetMail` | 11.1 | 45.1 | 503 | 4.3 (9.5 %), p95 64 | 37.4 (82.9 %), p95 465 | 3.4 (7.5 %), p95 24 |
| `GetMailsByUids` | 14.7 | 67.5 | 510 | 0.1 (0.1 %), p95 5 | 57.0 (84.4 %), p95 482 | 10.4 (15.4 %), p95 80 |

- **`EnrichPersistMail`** — sur 71.4 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 44.5 ms exécution SQL, 26.7 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 45.1 ms en moyenne (11.1 requête(s) SQL par appel) : 4.3 ms attente d'une connexion, 37.4 ms exécution SQL, 3.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 67.5 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 57.0 ms exécution SQL, 10.4 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est l'attente du **pool Npgsql** seul ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **L'attente PgBouncer n'est pas dans `attente d'une connexion`** (task-435). En mode transaction, le pooler attribue un serveur à la première requête de chaque transaction : son attente est comptée dans `exécution SQL`. Son coût se lit dans « Coûts résidents » (« Attente PgBouncer cumulée — chemin du médecin »).

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.4 | 315.7 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.9 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 206.6 | 10.4 | 50.5 | 18.7 | 28.5 | 18.7 | 30.3 | 18.7 | 0.0 | 18.7 | 5.8 | 0.0 | 18.6 | 44.7 | 4.0 |

- **`GetMail`** — sur 3.4 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.9 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **315.7 µs**.

- **`GetMailsByUids`** — sur 10.4 ms de matérialisation, l'appel a construit 206.6 objets, dont 18.7 messages, 28.5 étiquettes, 18.7 destinataires, 30.3 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.8 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.7 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **50.5 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4381.9 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 369.3 | 2175 | 142.1 (38.5 %), p95 350 | 19.0 (5.1 %), p95 696 | 107.8 (29.2 %), p95 1600 | 54.5 (14.8 %), p95 650 | 45.9 (12.4 %), p95 696 |

- **Enrichir un message** — sur 369.3 ms en moyenne (3.8 message(s) par requête) : 142.1 ms fetch IMAP, 19.0 ms extraction XDM, 107.8 ms parsing CDA, 54.5 ms écritures base, 45.9 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **2.73 aller(s)-retour(s) IMAP par message enrichi** — 0.91 `fetch_whole_message`, 0.45 `fetch_bodystructure`, 0.45 `open_folder`, 0.45 `resolve_folder`, 0.45 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 233.9 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 638.0 | 979 | 0.0 (0.0 %), p95 5 | 17.8 (2.8 %), p95 58 | 221.8 (34.8 %), p95 478 | 398.2 (62.4 %), p95 489 | 422.6 (66.2 %), p95 974 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 638.0 ms en moyenne : 0.0 ms garde d'opposition, 17.8 ms construction MIME, 221.8 ms obtention de session SMTP, 398.2 ms transmission + acquittement, 422.6 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.444 | 2.425 | 96.15 |
| `smtp_session` | 0.005 | 0.988 | 10.06 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.387 | 2.339 | 0.490 | 10.07 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 1.25 |
| `GetAttachmentStream` | 0.481 | 2.200 | 2.425 | 0.638 | 0.85 |
| `GetEmailContent` | 0.005 | 0.547 | — | 0.547 | 13.76 |
| `GetFolders` | 0.005 | 1.515 | 1.515 | 0.243 | 7.87 |
| `ReadFolder` | 0.756 | 2.425 | 2.425 | 0.487 | 34.98 |
| `ReadToday` | 0.005 | 0.500 | — | 0.500 | 7.89 |
| `UpdateFlag` | 0.005 | 0.487 | — | 0.487 | 25.98 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `EnrichEmails` | **0.406** | 0.444 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.600 | 0.638 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.489 | 0.489 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.242 | 0.0 % |
| `ReadFolder` | **0.429** | 0.438 | 0.443 | 0.0 % |
| `ReadToday` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 96.15 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.756 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 26.00 clients | 0 clients | 100.0 % | 27.9 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 9.02 cœurs | 24 cœurs | 37.6 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-66840` | 22.00 éléments | 100 éléments | 22.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#72864` (CPU) | 3.52 cœurs | 24 cœurs | 14.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#67760` (CPU) | 3.21 cœurs | 24 cœurs | 13.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#66840` (CPU) | 2.25 cœurs | 24 cœurs | 9.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#67980` (CPU) | 2.20 cœurs | 24 cœurs | 9.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#64552` (CPU) | 1.93 cœurs | 24 cœurs | 8.0 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 27.9 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 320 171

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 3 923 |
| OpenAI | gpt-4o-mini | prompt | 316 248 |
| OpenAI | text-embedding-3-small | embedding | 481 500 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 176 | 0 (0.0 %) | 0 | 4.7 | 1.17 | 1.04 | 2.56 |
| étiquetage (chat) | OpenAI | 176 | 0 (0.0 %) | 0 | 4.7 | 1.10 | 0.95 | 2.56 |
| embedding | OpenAI | 176 | 0 (0.0 %) | 0 | 4.7 | 0.56 | 0.44 | 1.56 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 3 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.6 | 14.0 |
| GPU — VRAM occupée (Mo) | 2 011 | 2 308 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.8 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 603.5** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.30** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **4.0 ms** | sur 762 445 requêtes HTTP k6 |
| Taux de cache (blocs) | **98.29 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **6.84 Mo/s (876 blocs/s)** | attente disque : 8.3 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **277 912 / 29 688** | rapport 9.4 |
| Écritures de lignes / s (ins+upd+del) | **167.5** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.29 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 17 % |
| Sessions ouvertes / s | **3.19** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **56.2 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 569 / 2 025** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **10 / 18 / 35 ms** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **96 / 100 %** | fautes majeures/s max : 0.6 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Signaux de défaut (détecteurs prouvés sur le corpus)

> Chaque forme passe aux détecteurs de `report_signals.py`, sur **toutes** les formes et pas seulement le top 20. Chaque détecteur a été vu signaler un défaut réel sur le tir d'avant son correctif, et se taire sur le tir d'après (`fixtures/pgss-corpus/`). Un signal est une hypothèse : le code et le plan d'exécution tranchent.

| Temps SQL | Appels | Détecteurs | Constats | Émise par | Requête |
|---|---|---|---|---|---|
| 147.4 s | 168594 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Body, HtmlBody : 18.2 Go lus, 3.2 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 14.1 % du temps SQL, 52.3 % des lectures disque du tir | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 39.5 s | 15560 | `colonne-volumineuse`, `poids-dans-le-tir` | sélectionne Content : 3.0 Go lus, 1.8 Go sur disque — à garder seulement sur le chemin qui sert ce contenu · 3.8 % du temps SQL, 30.1 % des lectures disque du tir | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 37.5 s | 8523 | `pages-par-ligne` | 31.2 pages par ligne rendue, 624 par appel, 40.5 Go lus | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 33.8 s | 8600 | `pages-par-ligne` | 31.4 pages par ligne rendue, 628 par appel, 41.2 Go lus | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 22.2 s | 168607 | `colonne-volumineuse` | sélectionne Body, BodyHtml : 5.9 Go lus, 0.0 Go sur disque — à garder seulement sur le chemin qui sert ce contenu | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |

### Top 20 des requêtes par temps serveur cumulé

⚠️ **88 évictions `pg_stat_statements`** pendant le tir (96 637 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

136 formes de requête, 6 030 482 appels, **17.4 min** de temps serveur cumulé — soit **1.4 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Émise par | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **15.2 %** | 15 % | 8 543 | 0.01 | 18.53 | 50.7 | 339 | 0 % | 0 | 815 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **14.1 %** | 29 % | 168 594 | 0.22 | 0.87 | 1.0 | 14 | 17 % | 0 | 1 872 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 3 | **13.6 %** | 43 % | 8 554 | 0.01 | 16.65 | 50.8 | 392 | 0 % | 0 | 816 | — | `SemanticSearchRepository.ExecuteFullTextSearchAsync` ← `POST /api/v1/Search/semantic` | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **6.5 %** | 49 % | 88 823 | 0.12 | 0.77 | 18.0 | 100 | 0 % | 0 | 1 996 | — | `MailRepository.LoadBulkContentLookupsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **6.2 %** | 56 % | 762 355 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `PostgresTenantRegistryClient.GetMailboxAsync` ← `GET /api/v1/Mail/folders/{foldername}` | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 6 | **3.8 %** | 59 % | 15 560 | 0.02 | 2.54 | 1.0 | 25 | 61 % | 0 | 1 221 | **Code** — 61 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur | `MailRepository.GetAttachmentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 7 | **3.6 %** | 63 % | 8 523 | 0.01 | 4.40 | 20.0 | 624 | 0 % | 0 | 811 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchMedicalDocumentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 8 | **3.2 %** | 66 % | 8 600 | 0.01 | 3.93 | 20.0 | 628 | 0 % | 0 | 818 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SemanticSearchRepository.SearchEmailContentsByVectorAsync` ← `POST /api/v1/Search/semantic` | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 9 | **3.2 %** | 69 % | 138 622 | 0.18 | 0.24 | 1.0 | 15 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | — | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 10 | **2.6 %** | 72 % | 5 968 | 0.01 | 4.57 | 178.0 | 540 | 1 % | 0 | 1 029 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | — | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 11 | **2.1 %** | 74 % | 168 607 | 0.22 | 0.13 | 1.0 | 5 | 1 % | 0 | 1 872 | — | `MailRepository.PopulateMailContentAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}` | `SELECT m."Id", m."MailId", m."ContentType", m."Body", m."BodyHtml", m."Summary" FROM "MailContents" AS m WHERE m."MailI…` |
| 12 | **2.1 %** | 76 % | 283 356 | 0.37 | 0.08 | 1.3 | 16 | 0 % | 0 | 1 996 | — | `MailRepository.ResolveActiveDuplicateRefsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 13 | **1.9 %** | 78 % | 94 939 | 0.12 | 0.21 | 18.0 | 5 | 0 % | 0 | 1 832 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | site inconnu ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}`<br>`MailRepository.LoadMailsReferencingAnyRootAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 14 | **1.3 %** | 80 % | 283 353 | 0.37 | 0.05 | 2.0 | 4 | 0 % | 0 | 1 996 | — | `MailRepository.EnrichManyWithBiologyAcksAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 15 | **1.3 %** | 81 % | 88 817 | 0.12 | 0.15 | 18.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.GetMailsByUidsAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 16 | **1.2 %** | 82 % | 45 145 | 0.06 | 0.28 | 27.0 | 5 | 0 % | 0 | 1 401 | — | `MailRepository.GetLatestMessageIdsPerThreadAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/{ids}` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **1.0 %** | 83 % | 143 971 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **1.0 %** | 84 % | 189 159 | 0.25 | 0.05 | 1.5 | 6 | 0 % | 0 | 1 894 | — | `MailRepository.GetMailAsync` ← `GET /api/v1/Mail/folders/{foldername}/emails/content/{emailid}`, `GET /api/v1/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | `SELECT t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."UrgencyExplanat…` |
| 19 | **1.0 %** | 85 % | 143 969 | 0.19 | 0.07 | 14.0 | 5 | 0 % | 0 | 1 996 | — | `MailRepository.LoadThreadLinkBatchesAsync` ← `POST /api/v1/Mail/folders/{foldername}/emails/enrich/sync` | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 20 | **0.9 %** | 86 % | 35 930 | 0.05 | 0.27 | 1.0 | 9 | 3 % | 0 | 1 452 | — | `PendingActionRepository.AddAsync` ← `PUT /api/v1/Mail/folders/{foldername}/emails/{emailid}/status/read` | `INSERT INTO "PendingActions" ("Id", "ActionType", "ClaimedAt", "CreatedAt", "FolderPath", "LastError", "MailUid", "Payl…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune) ; **Émise par** = la méthode d'api-mail qui l'émet et les routes qui l'appellent, lues dans le commentaire `/* route=… site=… */` de chaque commande (task-432).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.7 % | 87.6 % |
| INSERT | 4.4 % | 2.9 % |
| UPDATE | 0.4 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.5 % | 7.6 % |
| bases : praticien (N bases) | 90.1 % | 82.1 % |
| bases : unique (1 base) | 9.9 % | 17.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **18.5** | 105 | 8 543 | 15.2 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **16.7** | 107 | 8 554 | 13.6 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **4.6** | 133 | 5 968 | 2.6 % | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have ty…` |
| **4.4** | 100 | 8 523 | 3.6 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **3.9** | 75 | 8 600 | 3.2 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailMedicalDocumentBiology` | 1 529 | 181 951 | 0 | 5 | 0.1 Mo |
| `Mails` | 774 | 97 906 | 686 | 26 | 0.1 Mo |
| `MailTags` | 224 | 55 552 | 86 | 43 | 0.1 Mo |
| `MailRecipients` | 205 | 31 980 | 62 | 26 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 112 | 29 232 | 212 | 43 | 30.0 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 187 | 28 447 | 1 338 | 157 | 8.0 Mo |
| `MailContents` ⚠️ index candidat | 47 | 7 332 | 2 529 | 156 | 1.9 Mo |
| `PendingActions` | 186 | 5 510 | 0 | 31 | 0.1 Mo |
| `Tags` | 161 | 2 898 | 88 | 0 | 0.0 Mo |
| `MailFolders` | 409 | 1 104 | 364 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (6.2 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 98.3 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Schéma | 🟠 | `MailAttachments` balayée 112 fois (29232 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 187 fois (28447 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 47 fois (7332 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°6 (3.8 % du temps SQL) — 61 % des blocs lus sur disque, mais la forme lit elle-même trop de pages : voir « Signaux de défaut », pas la mémoire du serveur |
| Infra | 🟡 | requête n°10 (2.6 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Schéma | 🟡 | requête n°7 (3.6 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°13 (1.9 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-174846.tsv`, `pgserver-journey-debut-171007.tsv`, `pgserver-journey-fin-174853.tsv`, `pgtables-journey-debut-171016.tsv`, `pgtables-journey-fin-174859.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 248398 — dont **248398** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261108-t435-qualif-174802.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._

## Qualification de l'attente PgBouncer — décision préparée (task-435)

> - **Tir** : `journey-courte-1400-1996-20261108-t435-qualif`, api-mail `develop` (`a7d8429f`), outillage de task-435
>   (`55c51ca5`).
> - **Conditions** : IA simulée, pool 1, tireur k6bench (75,6 Mo/s), banc mail cluster, `LATENCY_MS=96`, bases
>   hydratées du 2026-11-08 sans `reset-state`.
> - **Validité** : SMTP sain (220 ms pour une session), 0,012 % d'erreurs, chauffe aboutie.

### Qui attend

| Famille de base | Présence (`cl_waiting` non nul) 1400 / 1996 | Profondeur `maxwait` p95 / pire, 1400 / 1996 |
|---|---|---|
| **bases praticien** (chemin du médecin) | 21 % / 35 % | 11,2 / 46,0 ms — 11,6 / 152,9 ms |
| registre des comptes | 0 % / 0 % | 0 |
| maintenance (`postgres`, `pgbouncer`) | 0 % / 0 % | 0 |

- **Toute l'attente est sur les bases praticien, donc sur le chemin du médecin.** La lecture « sonde de readiness » des
  rapports d'avant était fausse : c'était le filtre de l'échantillonneur, pas le pooler.
- **La continuité tient.** La présence totale (21 % / 35 %) retombe dans l'ordre du tir `bilan-apres` (16 % / 34 %).
- Le registre ne passe par aucune file : ses 0 transactions via le pooler montrent qu'il est servi en direct.

### Ce qu'elle coûte

| Mesure (`SHOW STATS`, bases praticien + registre) | 1400 médecins | 1996 médecins |
|---|---|---|
| Attente cumulée sur le palier (1 060 s) | 728,5 s | 1 337,4 s |
| Clients en attente en moyenne (attente ÷ durée) | 0,7 | 1,3 |
| Transactions | 1 939 034 | 2 801 236 |
| Attente par transaction | 0,4 ms | 0,5 ms |
| Part du temps des transactions (attente comprise) | 18,3 % | 19,2 % |
| Part du temps des requêtes HTTP du palier (k6) | 3,4 % | 3,2 % |

- **Une requête HTTP du parcours ouvre 10 à 12 transactions.** Chacune attend en moyenne 0,4 à 0,5 ms qu'un serveur se
  libère, soit environ 5 ms par requête.
- **Où l'attente apparaît dans les phases SQL** : dans « exécution SQL », pas dans « attente d'une connexion ».
  - `GetMailsByUids` porte 0,1 ms d'« attente d'une connexion » pour 14,7 requêtes par appel. Avec 0,5 ms
    d'attente PgBouncer par transaction, c'est de l'ordre de 7 ms par appel, invisibles dans cette colonne.
  - En mode transaction, le pooler attribue un serveur à la **première requête** de chaque transaction.
  - La note de la table des phases est corrigée dans le rapport et dans `report.py`.
- **Phénomène distinct, à ne pas confondre** : `GetMail` porte 4,3 ms d'« attente d'une connexion », soit 9,5 % de
  l'appel, au p95 64 ms. C'est le **pool Npgsql** de la base, et non PgBouncer.
- **Attribution par étape impossible** avec cet instrument : `SHOW STATS` compte par base, pas par route.

### Confrontation au seuil de reprise de task-242

| Critère | Seuil | Mesure | Verdict |
|---|---|---|---|
| Attente praticien rapportée au temps serveur | > 1 % | 3,2 à 3,4 % du temps HTTP mesuré par k6 (le temps serveur, plus court, en ferait une part plus grande) | **franchi** |
| Profondeur p95 à un palier | > 100 ms | 11,2 / 11,6 ms | non franchi |

**Le seuil est franchi par le coût, pas par la profondeur.** La file est **fréquente et courte** : un médecin dont
plusieurs requêtes arrivent ensemble (plusieurs réplicas, rafales du dashboard) les voit se sérialiser derrière l'unique
connexion serveur de sa base (pool 1, task-422).

### Remèdes possibles — à décider, aucun n'est appliqué

| Remède | Effet attendu | Risque | Ce qui le départagerait |
|---|---|---|---|
| **A. Moins de transactions par requête** (grouper les lectures d'une requête : `GetMail` 11 requêtes, `GetMailsByUids` 14,7) | moins d'attributions de serveur, donc moins d'attentes ; gain de latence au-delà de l'attente (allers-retours) | code applicatif, par chemin ; une transaction longue tient le serveur plus longtemps (pool 1) | A/B du tir court sur `GetMailsByUids` seul : attente cumulée et p50 des étapes 2 et 3 |
| **B. `reserve_pool_size` = 1, `reserve_pool_timeout` court** | absorbe les rafales sans doubler les backends en régime | backends en pointe, donc retour vers le mur `max_connections` (~1 300 actifs à pool 2, task-422) | A/B : attente cumulée, backends au pic, `max_connections` |
| **C. Pool 2** (retour d'avant task-422) | supprime l'essentiel de la file | **écarté** : 1,9 backend par actif, mur à ~1 300 actifs (mesuré le 2026-11-05) | — |
| **D. Continuer à réduire la durée des transactions** (findings SQL : FND-007 `HtmlBody`, FND-010, FND-014) | moins de temps de serveur occupé, donc moins d'attente | nul, déjà la voie suivie | déjà mesuré par les A/B de chaque finding |

**Ma recommandation** : **A d'abord**, sur le chemin le plus fréquent (`GetMailsByUids`, la page d'en-têtes). Elle
attaque la cause, le nombre d'attributions, sans toucher au plafond de connexions que task-422 a levé. B vient
ensuite, si A ne suffit pas, avec un A/B qui surveille les backends au pic.

**Limite suivante désignée**, quel que soit le choix : l'appel IMAP `GET /mail/folders/{folder}`, qui pèse 61 % du
temps serveur de l'arrivée sur le dashboard (synthèse du bilan du lot, point 3).
