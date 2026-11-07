# Rapport de tir — journey-courte-1400-1996-20261106-apres

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-courte-1400-1996-20261106-apres-193002.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 3 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1400 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 23 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.013 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 1996 — **Durée** : 2220s — **Latence** : mssante
- **Requêtes** : 760903 — **débit émergent global** : 336.9 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 53721 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1996 / 1996 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 1996 | journey | — | 336.9 | **149.8** | 63.4 | **518.7** | — | 9775.3 | 0.01 | 100.0 | 0 | 0 | 244792/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1400 médecins** | 1080 | 737 | 214441 | 290.96 | 0.01 | 800.4 |
| **1996 médecins** | 1080 | 933 | 385095 | 412.75 | 0.01 | 1493.5 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1400 médecins | 1996 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 59 / 541 (n=63624) | 69 / 649 (n=113772) |
| 2 | Ouvrir / rafraîchir l'inbox | 41 / 97 (n=31830) | 57 / 174 (n=56860) |
| 3 | Ouvrir un message enrichi (servi base) | 35 / 66 (n=15901) | 57 / 147 (n=28433) |
| 4 | Ouvrir un message froid (fetch IMAP) | 446 / 510 (n=6375) | 460 / 534 (n=11440) |
| 5 | Recherche | 328 / 593 (n=4891) | 368 / 707 (n=8498) |
| 6 | Envoi (acquittement UI) | 489 / 925 (n=4717) | 499 / 964 (n=8586) |
| 7 | Télécharger une PJ (~124 Ko) | 37 / 79 (n=6302) | 66 / 443 (n=11348) |
| 8 | Marquer lu | 36 / 86 (n=12770) | 68 / 136 (n=22734) |
| 9 | Rechercher un patient | 55 / 67 (n=4810) | 58 / 87 (n=8676) |
| 10 | Ouvrir la page d'un dossier patient | 56 / 110 (n=7155) | 85 / 239 (n=13044) |
| 11 | Fiche patient complète (ressenti médecin) | 302 / 510 (n=3578) | 442 / 1044 (n=6522) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1400 médecins** | 14.5 / 20 | 34.5 / 65 | 7990 | 510 |
| **1996 médecins** | 14.5 / 20 | 34.1 / 65 | 14342 | 1044 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 2223 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 21956 appels d'analyse, ~2151688 messages analysés, 592 ms en moyenne, 9775 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1400 médecins | 1996 médecins |
|---|---|---|
| Sessions IMAP (moy/max) | 2257 / 3105 (magasin) | 2257 / 3105 (magasin) |
| Backends Postgres (moy/max) | 1246 / 1437 | 1990 / 2026 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 2 | 0 / 2 |
| PgBouncer `cl_waiting` (échant. non nuls) | 43/190 (23 %) | 58/160 (36 %) ⚠️ soutenu |
| …dont bases **praticien** (échant. non nuls) | 0/190 (0 %) | 0/160 (0 %) |
| …dont pool de **maintenance** (échant. non nuls) | 43/190 (23 %) | 58/160 (36 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 50.6 | 1717.9 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 0.0 | 0.0 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 50.6 | 1717.9 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | non relevé | non relevé |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 119 / 410 | 97 / 282 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 | 98 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 1406 | 1995 |
| Backends **directs** — audit + provisionnement (max) | 30 | 29 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 | 4 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 99.1 | 100.0 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 1 | 1 / 16 |
| RSS par réplica api-mail, Mo (moy/max) | 1160 / 1597 (5 réplicas) | 2079 / 2323 (5 réplicas) |

- à 1400 médecins : Backends Postgres au pic : **1437.0 / 2500** (57.5 % de `max_connections`)
- à 1996 médecins : Backends Postgres au pic : **2026.0 / 2500** (81.0 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 1400 : cohorte 1400 chauffée à 100.0 % (sur 1400) ; étape 3 servie par la base à 99.4 % (sur 15901)
- palier 1996 : cohorte 1996 chauffée à 99.7 % (sur 596) ; étape 3 servie par la base à 99.4 % (sur 28433)

> ⓘ Chauffe : **301 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 1080 s, soit **28 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1400 : chauffe [+30 s..+373 s] (32 % de la fenêtre) ; **régime [+373 s..+1110 s]** porte le verdict
>   palier 1996 : chauffe [+1140 s..+1287 s] (14 % de la fenêtre) ; **régime [+1287 s..+2220 s]** porte le verdict

### 1400 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 59 (300) | 541 (1500) | 63624 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 41 (300) | 97 (1000) | 31830 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 35 (100) | 66 (500) | 15901 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 446 (800) | 510 (2500) | 6375 | ✅ |
| 5 | Recherche | 328 (500) | 593 (2000) | 4891 | ✅ |
| 6 | Envoi (acquittement UI) | 489 (1000) | 925 (3000) | 4717 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 37 (500) | 79 (2000) | 6302 | ✅ |
| 8 | Marquer lu | 36 (200) | 86 (1000) | 12770 | ✅ |
| 9 | Rechercher un patient | 55 (300) | 67 (1500) | 4810 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 56 (500) | 110 (2000) | 7155 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 302 (1500) | 510 (4000) | 3578 | ✅ |

### 1996 médecins — ❌ SLO non tenu

> ⚠️ fenêtre de 1080 s < 1800 s : la grille exige ≥ 30 min de plateau — verdict **indicatif**, pas opposable.

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 69 (300) | 649 (1500) | 113772 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 57 (300) | 174 (1000) | 56860 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 57 (100) | 147 (500) | 28433 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 460 (800) | 534 (2500) | 11440 | ✅ |
| 5 | Recherche | 368 (500) | 707 (2000) | 8498 | ✅ |
| 6 | Envoi (acquittement UI) | 499 (1000) | 964 (3000) | 8586 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 66 (500) | 443 (2000) | 11348 | ✅ |
| 8 | Marquer lu | 68 (200) | 136 (1000) | 22734 | ✅ |
| 9 | Rechercher un patient | 58 (300) | 87 (1500) | 8676 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 85 (500) | 239 (2000) | 13044 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 442 (1500) | 1044 (4000) | 6522 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1996**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 113772 | 169 | 649 | 19219.6 | 42.7 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 8586 | 637 | 964 | 5472.5 | 12.1 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 11440 | 463 | 534 | 5299.2 | 11.8 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 56860 | 71 | 174 | 4063.5 | 9.0 % |
| 🟢 | Recherche (`search`) | 8498 | 422 | 707 | 3585.6 | 8.0 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 28433 | 70 | 147 | 1977.2 | 4.4 % |
| 🟢 | Marquer lu (`mark_read`) | 22734 | 71 | 136 | 1618.5 | 3.6 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 11348 | 113 | 443 | 1276.8 | 2.8 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 7171 | 139 | 258 | 994.6 | 2.2 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 6522 | 104 | 239 | 679.4 | 1.5 % |
| 🟢 | Rechercher un patient (`patient_search`) | 8676 | 53 | 87 | 459.1 | 1.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 6522 | 63 | 92 | 409.9 | 0.9 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 3 🟠 · 9 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 19219.6 s, 42.7 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 9.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 4063.5 s, 9.0 %)
  - **dispersion p95/p50 = 3.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 1276.8 s, 2.8 %)
  - **dispersion p95/p50 = 6.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 15906 | 392 | 932 | 6082.2 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 15906 | 59 | 496 | 2180.8 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 15906 | 22 | 162 | 748.1 |
| 1400 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 15906 | 57 | 69 | 920.5 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 15915 | 16 | 115 | 477.6 |
| 1400 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 15915 | 51 | 88 | 888.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 28443 | 403 | 1011 | 11387.6 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 28443 | 67 | 510 | 4129.7 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 28443 | 38 | 195 | 1867.5 |
| 1996 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 28443 | 62 | 95 | 1834.8 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 28430 | 25 | 135 | 1257.5 |
| 1996 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 28430 | 84 | 194 | 2805.9 |

### Qui porte le coût — palier 1996 médecins

- **Arrivée dashboard** (`dashboard`, palier 1996) — le p95 de l'étape est porté par l'appel **`folder`** (1011 ms de p95, 403 ms de p50, n=28443), qui porte **aussi** le temps serveur de l'étape (11387.6 s, 59 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1996) — le p95 de l'étape est porté par l'appel **`emails`** (194 ms de p95, 84 ms de p50, n=28430), qui porte **aussi** le temps serveur de l'étape (2805.9 s, 69 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 21749 | 101.7 | 51.1 | 175.1 | 443.5 | 1784.9 |
| attachment,palier:1400 | 6302 | 48.7 | 37.2 | 63.0 | 78.5 | 1120.1 |
| attachment,palier:1996 | 11348 | 112.5 | 66.2 | 172.5 | 442.6 | 1333.0 |
| attachment,palier:transition | 607 | 230.7 | 63.7 | 680.1 | 745.3 | 1544.8 |
| dashboard | 219524 | 171.0 | 66.1 | 472.7 | 634.4 | 1711.0 |
| dashboard,call:coverage,palier:1400 | 15906 | 57.9 | 56.9 | 64.6 | 69.3 | 149.3 |
| dashboard,call:coverage,palier:1996 | 28443 | 64.5 | 62.0 | 84.1 | 95.1 | 585.4 |
| dashboard,call:coverage,palier:transition | 1037 | 135.2 | 104.4 | 270.0 | 320.1 | 508.8 |
| dashboard,call:folder,palier:1400 | 15906 | 382.4 | 391.6 | 757.5 | 932.0 | 1503.7 |
| dashboard,call:folder,palier:1996 | 28443 | 400.4 | 402.7 | 778.6 | 1011.1 | 1711.0 |
| dashboard,call:folder,palier:transition | 1037 | 487.0 | 474.2 | 766.5 | 889.8 | 1584.8 |
| dashboard,call:folders,palier:1400 | 15906 | 47.0 | 22.0 | 147.3 | 162.5 | 385.3 |
| dashboard,call:folders,palier:1996 | 28443 | 65.7 | 37.9 | 171.0 | 194.8 | 685.8 |
| dashboard,call:folders,palier:transition | 1037 | 155.7 | 123.2 | 332.8 | 442.1 | 787.7 |
| dashboard,call:today,palier:1400 | 15906 | 137.1 | 59.0 | 475.6 | 495.9 | 1106.2 |
| dashboard,call:today,palier:1996 | 28443 | 145.2 | 66.7 | 486.4 | 509.7 | 1125.2 |
| dashboard,call:today,palier:transition | 1037 | 344.9 | 385.3 | 635.2 | 716.7 | 1057.3 |
| dashboard,palier:1400 | 63624 | 156.1 | 59.2 | 456.1 | 541.1 | 1503.7 |
| dashboard,palier:1996 | 113772 | 168.9 | 69.0 | 468.1 | 649.4 | 1711.0 |
| dashboard,palier:transition | 4148 | 280.7 | 186.7 | 600.9 | 711.7 | 1584.8 |
| mark_read | 43717 | 69.9 | 59.5 | 111.2 | 149.6 | 711.6 |
| mark_read,palier:1400 | 12770 | 47.6 | 36.0 | 77.6 | 86.1 | 214.6 |
| mark_read,palier:1996 | 22734 | 71.2 | 67.6 | 114.0 | 135.6 | 670.2 |
| mark_read,palier:transition | 1167 | 130.0 | 67.3 | 380.1 | 480.6 | 711.6 |
| patient_docs | 179920 | 82.2 | 56.4 | 155.1 | 214.8 | 2263.2 |
| patient_docs,palier:1400 | 52071 | 46.9 | 43.2 | 83.9 | 99.4 | 347.3 |
| patient_docs,palier:1996 | 94513 | 84.1 | 67.9 | 165.0 | 205.5 | 965.0 |
| patient_docs,palier:transition | 5374 | 211.1 | 70.3 | 715.4 | 1027.3 | 2263.2 |
| patient_dossier | 12387 | 106.1 | 68.7 | 176.9 | 264.7 | 4147.5 |
| patient_dossier,palier:1400 | 3578 | 56.3 | 50.9 | 92.9 | 110.4 | 312.9 |
| patient_dossier,palier:1996 | 6522 | 104.2 | 85.1 | 186.3 | 239.3 | 830.9 |
| patient_dossier,palier:transition | 354 | 367.2 | 88.6 | 1266.5 | 1737.9 | 4147.5 |
| patient_opposition | 12387 | 63.4 | 58.9 | 80.5 | 95.2 | 542.9 |
| patient_opposition,palier:1400 | 3577 | 57.4 | 56.5 | 63.9 | 68.6 | 139.4 |
| patient_opposition,palier:1996 | 6522 | 62.8 | 61.6 | 81.7 | 91.9 | 542.9 |
| patient_opposition,palier:transition | 356 | 88.2 | 61.5 | 178.0 | 227.8 | 411.2 |
| patient_search | 16584 | 52.6 | 55.8 | 76.5 | 91.1 | 515.8 |
| patient_search,palier:1400 | 4810 | 45.0 | 55.4 | 63.1 | 66.8 | 155.6 |
| patient_search,palier:1996 | 8676 | 52.9 | 58.2 | 78.7 | 87.3 | 515.8 |
| patient_search,palier:transition | 484 | 75.9 | 59.5 | 163.9 | 216.2 | 373.4 |
| read_content | 54881 | 67.4 | 44.7 | 115.0 | 165.2 | 1055.3 |
| read_content,palier:1400 | 15901 | 38.2 | 34.6 | 55.0 | 65.7 | 232.3 |
| read_content,palier:1996 | 28433 | 69.5 | 57.1 | 119.6 | 147.1 | 838.9 |
| read_content,palier:transition | 1342 | 156.3 | 55.1 | 530.4 | 616.7 | 1055.3 |
| read_content_cold | 22041 | 460.8 | 455.4 | 514.7 | 539.7 | 1081.1 |
| read_content_cold,palier:1400 | 6375 | 447.7 | 446.1 | 495.7 | 509.8 | 635.8 |
| read_content_cold,palier:1996 | 11440 | 463.2 | 460.0 | 516.0 | 534.3 | 935.2 |
| read_content_cold,palier:transition | 595 | 498.9 | 470.5 | 643.6 | 697.6 | 871.8 |
| read_list | 109762 | 70.2 | 48.2 | 135.4 | 192.1 | 1179.8 |
| read_list,call:emails,palier:1400 | 15915 | 55.8 | 51.4 | 75.9 | 87.9 | 245.9 |
| read_list,call:emails,palier:1996 | 28430 | 98.7 | 84.5 | 160.6 | 193.9 | 741.5 |
| read_list,call:emails,palier:transition | 1248 | 262.7 | 81.6 | 800.7 | 883.4 | 1179.8 |
| read_list,call:folder,palier:1400 | 15915 | 30.0 | 15.6 | 37.6 | 115.4 | 509.4 |
| read_list,call:folder,palier:1996 | 28430 | 44.2 | 25.2 | 83.9 | 134.6 | 689.8 |
| read_list,call:folder,palier:transition | 1248 | 85.6 | 26.1 | 239.3 | 326.2 | 721.7 |
| read_list,palier:1400 | 31830 | 42.9 | 40.7 | 71.8 | 96.6 | 509.4 |
| read_list,palier:1996 | 56860 | 71.5 | 56.8 | 139.9 | 174.2 | 741.5 |
| read_list,palier:transition | 2496 | 174.1 | 63.2 | 625.6 | 800.6 | 1179.8 |
| search | 16462 | 418.1 | 354.7 | 559.0 | 868.3 | 2112.0 |
| search,palier:1400 | 4891 | 378.7 | 327.7 | 459.6 | 593.1 | 1541.9 |
| search,palier:1996 | 8498 | 421.9 | 368.3 | 531.0 | 706.5 | 1848.5 |
| search,palier:transition | 440 | 521.0 | 370.0 | 1117.3 | 1305.9 | 1637.8 |
| send | 15774 | 651.7 | 519.2 | 927.8 | 964.6 | 1561.9 |
| send,palier:1400 | 4717 | 629.5 | 489.0 | 903.9 | 925.2 | 1037.2 |
| send,palier:1996 | 8586 | 637.4 | 498.9 | 933.2 | 963.7 | 1512.7 |
| send,palier:transition | 461 | 687.2 | 619.7 | 987.6 | 1136.2 | 1561.9 |
| treatment | 13745 | 122.8 | 87.9 | 170.0 | 298.8 | 3982.3 |
| treatment,palier:1400 | 3995 | 75.5 | 79.7 | 101.1 | 112.9 | 269.4 |
| treatment,palier:1996 | 7171 | 138.7 | 99.5 | 179.2 | 257.7 | 3982.3 |
| treatment,palier:transition | 311 | 236.2 | 98.4 | 690.9 | 799.5 | 994.1 |
| warmup | 21956 | 591.7 | 403.0 | 824.3 | 1774.0 | 9775.3 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-06T17:52:23.866000+00:00 → 2026-11-06T18:30:02.650000+00:00 (2259 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-apres.csv`) | ✅ 75252 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-49256` | 0.94 | 14 | 33 | 0.034 | 5.29 |
| `DESKTOP-DEV-X2C-53164` | 0.92 | 6 | 41 | 0.039 | 4.73 |
| `DESKTOP-DEV-X2C-56604` | 0.99 | 32 | 31 | 0.038 | 4.95 |
| `DESKTOP-DEV-X2C-66012` | 1.01 | 10 | 24 | 0.026 | 5.04 |
| `DESKTOP-DEV-X2C-66152` | 0.99 | 11 | 33 | 0.035 | 4.65 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#30028` | 1.42 | 3.88 | 1948 |
| `com.docker.backend#34124` | 0.00 | 0.19 | 40 |
| `dcp#14132` | 0.00 | 0.14 | 54 |
| `dcp#14512` | 0.86 | 2.21 | 3208 |
| `dcp#2588` | 0.00 | 0.00 | 12 |
| `dcp#35480` | 0.00 | 0.00 | 12 |
| `dcp#36536` | 0.00 | 0.04 | 13 |
| `dcp#43636` | 0.00 | 0.09 | 13 |
| `dcp#45588` | 0.00 | 0.00 | 12 |
| `dcp#54796` | 0.00 | 0.04 | 12 |
| `dcp#56324` | 0.00 | 0.00 | 12 |
| `dcp#56880` | 0.00 | 0.00 | 12 |
| `dcp#58160` | 0.00 | 0.00 | 12 |
| `dcp#58436` | 0.00 | 0.04 | 13 |
| `dcp#60848` | 0.00 | 0.00 | 12 |
| `dcp#61832` | 0.00 | 0.09 | 14 |
| `dcp#65836` | 0.00 | 0.00 | 12 |
| `k6#111106` | 0.87 | 1.83 | 2913 |
| `mss.mail.api#49256` | 0.65 | 2.18 | 2211 |
| `mss.mail.api#53164` | 0.66 | 2.87 | 2236 |
| `mss.mail.api#56604` | 0.68 | 2.90 | 2323 |
| `mss.mail.api#66012` | 0.68 | 2.02 | 2313 |
| `mss.mail.api#66152` | 0.70 | 2.74 | 2247 |
| `mss.mail.e2e#59168` | 0.01 | 0.33 | 34 |
| `vmmemWSL#36464` | 5.70 | 12.02 | 69460 |
| `loadtest-otel-collector-qyetaxke` | 0.02 | 0.16 | 136 |
| `loadtest-pgbouncer-tstmpcut` | 0.51 | 0.96 | 53 |
| `mss-mail-flagsmith-app-b6152948` | 0.11 | 0.41 | 490 |
| `mss-mail-flagsmith-db-b6152948` | 0.01 | 0.27 | 195 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.06 | 156 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.08 | 218 |
| `mss-mail-rabbitmq-zbkbpqku` | 0.01 | 0.05 | 154 |
| `mss-mail-redis-b6152948` | 0.28 | 1.40 | 957 |
| `mss-mail-rediscommander-emzbtrdt` | 0.00 | 0.20 | 47 |
| `mss-mail-seq-b6152948` | 0.13 | 4.86 | 11653 |
| `postgres-pgvector` | 2.20 | 8.89 | 46991 |

- **Hôte** : CPU 66.8 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 31
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 9384, cl_waiting max 39, cl_waiting_maintenance max 39, cl_waiting_practitioner max 0, count max 1997, login_retry_delta max 0, maxwait_maintenance_ms max 1718, maxwait_ms max 1718, maxwait_practitioner_ms max 0, sv_active max 100, sv_idle max 1616, sv_login max 2
- **Backends Postgres** : audit max 5, cache_mb max 40966, direct max 30, idle_over_60s max 222, majfault_per_s max 16, pooler max 1995, practitioner_databases max 1985, provision max 5, rss_mb max 6230, started_last_60s max 410, total max 2026, usage_pct max 100

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 8631.9 | 448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2425.0 | 449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 962.7 | 446 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 941.1 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 734.1 | 447 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 771.7 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 491.0 | 444 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 917.9 | 446 |
| `api/v{version:apiVersion}/Mail/sendmail` | 2143.8 | 433 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 227.3 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 2231.3 | 442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 237.0 | 442 |
| `api/v{version:apiVersion}/Search/semantic` | 2040.5 | 443 |
| `api/v{version:apiVersion}/Sync/coverage` | 325.7 | 447 |

- **p95 client global (k6)** : 518.7 ms
- **p95 serveur le plus élevé** : 8631.9 ms
- **Écart** : -8113.1 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 2.07 |
| Documents CDA /s | 2.02 |
| Durée traitement CDA (s, p95) | 1.09 |
| Événements de session IMAP /s | 4.05 |
| Recherches (s, p95) | 1.821 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 7.9 | 64.8 | 378 | 0.0 (0.0 %), p95 5 | 42.2 (65.1 %), p95 225 | 22.6 (34.9 %), p95 177 |
| `GetMail` | 11.1 | 52.4 | 853 | 4.6 (8.7 %), p95 80 | 44.2 (84.4 %), p95 739 | 3.6 (6.9 %), p95 127 |
| `GetMailsByUids` | 14.7 | 78.6 | 696 | 0.1 (0.1 %), p95 5 | 67.3 (85.6 %), p95 682 | 11.2 (14.2 %), p95 86 |

- **`EnrichPersistMail`** — sur 64.8 ms en moyenne (7.9 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 42.2 ms exécution SQL, 22.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 52.4 ms en moyenne (11.1 requête(s) SQL par appel) : 4.6 ms attente d'une connexion, 44.2 ms exécution SQL, 3.6 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 78.6 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 67.3 ms exécution SQL, 11.2 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.7 | 3.6 | 335.6 | 0.9 | 1.4 | 0.9 | 2.8 | non relevé | 0.0 | 0.9 | 2.8 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 207.5 | 11.2 | 53.9 | 18.7 | 28.6 | 18.7 | 30.5 | 18.7 | 0.0 | 18.7 | 5.9 | 0.0 | 18.6 | 44.9 | 4.0 |

- **`GetMail`** — sur 3.6 ms de matérialisation, l'appel a construit 10.7 objets, dont 0.9 messages, 1.4 étiquettes, 0.9 destinataires, 2.8 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.8 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **335.6 µs**.

- **`GetMailsByUids`** — sur 11.2 ms de matérialisation, l'appel a construit 207.5 objets, dont 18.7 messages, 28.6 étiquettes, 18.7 destinataires, 30.5 pièces jointes, 18.7 identifiants enrichis, 0.0 acquittements, 18.7 documents médicaux, 5.9 résultats de biologie, 0.0 éléments de synthèse, 18.6 corps de messages, 44.9 objets de fil, 4.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **53.9 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **4101.7 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 3.8 | 273.9 | 3777 | 134.1 (48.9 %), p95 275 | 9.1 (3.3 %), p95 628 | 37.1 (13.6 %), p95 1766 | 54.0 (19.7 %), p95 312 | 39.6 (14.4 %), p95 378 |

- **Enrichir un message** — sur 273.9 ms en moyenne (3.8 message(s) par requête) : 134.1 ms fetch IMAP, 9.1 ms extraction XDM, 37.1 ms parsing CDA, 54.0 ms écritures base, 39.6 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **2.99 aller(s)-retour(s) IMAP par message enrichi** — 1.00 `fetch_whole_message`, 0.50 `resolve_folder`, 0.50 `fetch_bodystructure`, 0.50 `close_folder`, 0.50 `open_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 252.2 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 637.4 | 990 | 0.0 (0.0 %), p95 5 | 20.9 (3.3 %), p95 70 | 220.1 (34.5 %), p95 477 | 396.3 (62.2 %), p95 488 | 416.3 (65.3 %), p95 962 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 637.4 ms en moyenne : 0.0 ms garde d'opposition, 20.9 ms construction MIME, 220.1 ms obtention de session SMTP, 396.3 ms transmission + acquittement, 416.3 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.442 | 2.350 | 99.86 |
| `smtp_session` | 0.005 | 0.995 | 10.07 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.368 | 2.326 | 0.489 | 10.07 |
| `EnrichEmails` | 0.005 | 0.463 | — | 0.463 | 3.13 |
| `GetAttachmentStream` | 0.479 | 2.387 | 2.425 | 0.725 | 2.36 |
| `GetEmailContent` | 0.005 | 0.491 | — | 0.491 | 13.46 |
| `GetFolders` | 0.005 | 0.991 | 0.991 | 0.243 | 7.91 |
| `ReadFolder` | 0.499 | 2.350 | 2.350 | 0.487 | 34.95 |
| `ReadToday` | 0.005 | 0.496 | 2.425 | 0.496 | 7.87 |
| `UpdateFlag` | 0.005 | 0.488 | — | 0.488 | 26.06 |

#### Détention en exploitation, **fenêtre de régime** — palier 1996

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.489 | 0.0 % |
| `EnrichEmails` | **0.408** | 0.432 | 0.463 | 0.0 % |
| `GetAttachmentStream` | **0.488** | 0.550 | 0.688 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.489 | 0.490 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.243 | 0.0 % |
| `ReadFolder` | **0.430** | 0.440 | 0.448 | 0.0 % |
| `ReadToday` | **0.487** | 0.489 | 0.489 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.488 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 99.86 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.499 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| PgBouncer — clients en attente (`cl_waiting`) | 39.00 clients | 0 clients | 100.0 % | 28.3 % des échantillons |
| conteneur `postgres-pgvector` (CPU) | 8.89 cœurs | 24 cœurs | 37.0 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-56604` | 32.00 éléments | 100 éléments | 32.0 % | 0.0 % — transitoire |
| conteneur `mss-mail-seq-b6152948` (CPU) | 4.86 cœurs | 24 cœurs | 20.3 % | 0.0 % — transitoire |
| processus `mss.mail.api#56604` (CPU) | 2.90 cœurs | 24 cœurs | 12.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#53164` (CPU) | 2.87 cœurs | 24 cœurs | 12.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#66152` (CPU) | 2.74 cœurs | 24 cœurs | 11.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#49256` (CPU) | 2.18 cœurs | 24 cœurs | 9.1 % | 0.0 % — transitoire |

**Ressource épinglée : PgBouncer — clients en attente (`cl_waiting`)** — 100.0 % de sa borne au débit maximal atteint, sur 28.3 % des échantillons de la fenêtre.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : OpenAI (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 1 020 572

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | gpt-4o-mini | completion | 12 698 |
| OpenAI | gpt-4o-mini | prompt | 1 007 874 |
| OpenAI | text-embedding-3-small | embedding | 1 515 072 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

| Étape | Fournisseur | Exécutions | Erreurs | Ignorées | Débit (/min) | Moy. (s) | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|---|---|
| pipeline complet | OpenAI | 540 | 0 (0.0 %) | 0 | 14.3 | 1.16 | 0.99 | 2.49 |
| étiquetage (chat) | OpenAI | 540 | 0 (0.0 %) | 0 | 14.3 | 1.10 | 0.94 | 2.49 |
| embedding | OpenAI | 540 | 0 (0.0 %) | 0 | 14.3 | 0.55 | 0.45 | 1.50 |

> Un « ≥ » signale un quantile tombé au-delà de la dernière borne finie de l'histogramme (60 s) : la valeur est un minorant. Les erreurs d'étiquetage ne lèvent plus (task-344) : le mail reste en attente et la reprise (`[TaggingRecovery]`, à compter dans Seq) le reprend plus tard.

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

| Messages prêts : début | max | fin | Non acquittés max |
|---|---|---|---|
| 0 | 0 | 0 | 5 |

La file ne grossit pas sur la fenêtre : le pipeline IA suit le rythme d'arrivée.

### GPU et conteneur Ollama (échantillonneur)

| Grandeur | moy. | max |
|---|---|---|
| GPU — utilisation (%) | 0.0 | 1.0 |
| GPU — VRAM occupée (Mo) | 1 813 | 1 818 |

> Le GPU est celui du poste : il ne prend pas de cœurs au système sous test, mais le CPU et la mémoire du conteneur s'ajoutent à ceux du banc.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **38.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **2 603.3** | annulées : 0.0 % |
| Backends actifs (équivalent) | **1.41** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **4.3 ms** | sur 760 903 requêtes HTTP k6 |
| Taux de cache (blocs) | **95.92 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **20.70 Mo/s (2 649 blocs/s)** | attente disque : 9.8 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **758 516 / 35 489** | rapport 21.4 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **204.5** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.38 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **8 / 0** | blocs écrits par les backends eux-mêmes : 44 % |
| Sessions ouvertes / s | **2.87** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **219.3 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **1 567 / 2 026** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **98 / 100 %** | fautes majeures/s max : 16.2 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

⚠️ **88 évictions `pg_stat_statements`** pendant le tir (95 228 entrées pour un plafond de 100 000) : les formes rares sont sous-comptées, le top reste fiable pour les formes fréquentes. Monter `pg_stat_statements.max` (≈ bases × formes par base).

132 formes de requête, 6 001 994 appels, **21.3 min** de temps serveur cumulé — soit **1.7 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **13.1 %** | 13 % | 8 717 | 0.01 | 19.25 | 50.4 | 336 | 1 % | 0 | 815 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **13.0 %** | 26 % | 168 700 | 0.22 | 0.98 | 1.0 | 18 | 24 % | 0 | 1 885 | **Postgres** — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 3 | **12.0 %** | 38 % | 8 682 | 0.01 | 17.67 | 50.4 | 389 | 2 % | 0 | 815 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 4 | **8.9 %** | 47 % | 88 248 | 0.12 | 1.29 | 18.1 | 213 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 5 | **5.3 %** | 52 % | 760 820 | 1.00 | 0.09 | 1.0 | 9 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT s.id, s.account_id, s.address_type, s.attached_at, s.database_name, s.detached_at, s.is_default, s.last_successf…` |
| 6 | **5.3 %** | 58 % | 3 862 | 0.01 | 17.51 | 30.5 | 468 | 37 % | 0 | 435 | **Postgres** — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 7 | **4.9 %** | 63 % | 47 024 | 0.06 | 1.34 | 10.2 | 248 | 0 % | 0 | 1 433 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 8 | **3.4 %** | 66 % | 8 666 | 0.01 | 4.97 | 20.0 | 617 | 4 % | 0 | 810 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 9 | **3.3 %** | 69 % | 168 138 | 0.22 | 0.25 | 1.0 | 8 | 3 % | 0 | 1 874 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 10 | **2.9 %** | 72 % | 8 736 | 0.01 | 4.24 | 20.0 | 620 | 3 % | 0 | 817 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 11 | **2.6 %** | 75 % | 137 170 | 0.18 | 0.24 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 12 | **1.9 %** | 77 % | 282 018 | 0.37 | 0.09 | 2.0 | 8 | 0 % | 0 | 1 996 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 13 | **1.8 %** | 78 % | 15 798 | 0.02 | 1.45 | 1.0 | 23 | 53 % | 0 | 1 227 | **Postgres** — 53 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 14 | **1.7 %** | 80 % | 281 974 | 0.37 | 0.08 | 1.3 | 16 | 0 % | 0 | 1 995 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 15 | **1.6 %** | 82 % | 94 392 | 0.12 | 0.22 | 18.0 | 5 | 0 % | 0 | 1 793 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 16 | **1.4 %** | 83 % | 4 316 | 0.01 | 4.22 | 178.0 | 540 | 2 % | 0 | 758 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 17 | **1.1 %** | 84 % | 88 251 | 0.12 | 0.15 | 18.1 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 18 | **1.0 %** | 85 % | 44 917 | 0.06 | 0.29 | 27.0 | 5 | 0 % | 0 | 1 400 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 19 | **1.0 %** | 86 % | 188 164 | 0.25 | 0.07 | 3.2 | 8 | 0 % | 0 | 1 886 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |
| 20 | **0.8 %** | 87 % | 143 131 | 0.19 | 0.07 | 20.8 | 5 | 0 % | 0 | 1 996 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 95.6 % | 87.7 % |
| INSERT | 3.6 % | 3.0 % |
| UPDATE | 0.3 % | 1.2 % |
| DELETE | 0.1 % | 0.6 % |
| AUTRE | 0.4 % | 7.5 % |
| bases : praticien (N bases) | 91.7 % | 82.1 % |
| bases : unique (1 base) | 8.3 % | 17.9 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **19.3** | 202 | 8 717 | 13.1 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **17.7** | 232 | 8 682 | 12.0 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **17.5** | 1 033 | 3 862 | 5.3 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **5.0** | 144 | 8 666 | 3.4 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **4.2** | 178 | 8 736 | 2.9 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 877 | 217 496 | 198 | 43 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 1 157 | 137 683 | 0 | 5 | 0.1 Mo |
| `Mails` | 733 | 101 208 | 681 | 26 | 0.1 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 165 | 24 385 | 953 | 157 | 8.0 Mo |
| `MailAttachments` ⚠️ index candidat | 93 | 24 273 | 115 | 43 | 30.0 Mo |
| `MailRecipients` | 129 | 20 124 | 0 | 26 | 0.1 Mo |
| `MailContents` ⚠️ index candidat | 67 | 10 452 | 2 008 | 156 | 1.9 Mo |
| `PendingActions` | 150 | 4 489 | 0 | 31 | 0.1 Mo |
| `Tags` | 97 | 1 746 | 83 | 0 | 0.0 Mo |
| `MailFolders` | 299 | 812 | 302 | 4 | 0.1 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°5 (5.3 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Postgres | 🟠 | taux de cache 95.9 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°2 (13.0 % du temps SQL) — 24 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Postgres | 🟠 | requête n°6 (5.3 % du temps SQL) — 37 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 21 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 165 fois (24385 lignes lues, 157 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailAttachments` balayée 93 fois (24273 lignes lues, 43 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 67 fois (10452 lignes lues, 156 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Infra | 🟡 | requête n°16 (1.4 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Postgres | 🟡 | 44 % des blocs écrits le sont par les backends eux-mêmes : bgwriter/checkpointer en retard — `bgwriter_lru_maxpages`, `checkpoint_completion_target` |
| Postgres | 🟡 | requête n°13 (1.8 % du temps SQL) — 53 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°8 (3.4 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°15 (1.6 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-193047.tsv`, `pgserver-journey-debut-185214.tsv`, `pgserver-journey-fin-193051.tsv`, `pgtables-journey-debut-185218.tsv`, `pgtables-journey-fin-193055.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 2000
- **Mails stockés (total)** : 244792 — dont **244792** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **2000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-courte-1400-1996-20261106-apres-193002.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._

## Findings — analyse de code

> **Rejeu de preuve de task-433**, joué le 2026-11-07 par `/loadtest-findings` en **mode complet** (`--full` : le
> registre est ignoré, chaque candidat est ré-exploré). Sans `--full`, les findings réglés au registre ne sont plus
> que remesurés.
>
> - **Tir** : `journey-courte-1400-1996-20261106-apres`. **Code** : api-mail `f50f2ae5`. **Mesures** :
>   `pgstats-journey-193047.tsv`, 760 903 requêtes HTTP.
> - **Mode dégradé pour le site** : le tir précède task-432, ses formes ne portent pas de commentaire `site=`. Chaque
>   site est retrouvé par `git grep` au commit du tir, avec la recherche citée.
> - **Plans** : `Docs/audits/findings/plans/20261106-apres/`, joués sur la base de banc la plus volumineuse
>   (`u_l9l_b27c2b6f659b50f6240b3481927d0381`), paramètres tirés de la base et jamais recopiés (plan générique,
>   `$1`). Un index ajouté après le tir est retiré dans une transaction annulée pour retrouver le schéma du tir.
> - **Contrôle de non-confabulation** : `python Tools/loadtest-findings/findings.py check` — **101 éléments, 0 écart**.
>   Chaque mesure, chaque `fichier:ligne` et chaque ligne de plan citée sont retrouvés dans leur source.

**Candidats** : 8 sur 8.
- Six formes signalées par les détecteurs de task-431, par temps SQL.
- Deux formes non signalées, les plus coûteuses : la recherche plein texte et le registre.
- Une forme signalée est restée hors budget : le téléchargement d'une pièce jointe (`4c9c73a7…`, 22.9 s). Elle sert
  `Content` sur la route qui le rend, c'est le faux positif connu de D2.

| Finding | Verdict | Classe | Temps SQL | Lu sur disque | Gain borné |
|---|---|---|---|---|---|
| FND-007 Document médical chargé entier à l'ouverture d'un message | **confirmé — récidive** | `colonne-volumineuse` | 165.7 s | 5.4 Go | ≈ 13 % de la forme, à mesurer par A/B |
| FND-004 Comptage de biologie par sous-requête sans index | **confirmé** | `sous-requete-correlee` | 113.7 s | 0.1 Go | pages de la sous-requête |
| FND-003 Pièces jointes du dossier patient lues avec leur contenu | **confirmé** | `colonne-volumineuse` | 67.6 s | 5.1 Go | ≈ toute la forme |
| FND-005 Comptages d'étiquettes calculés trois fois | **confirmé** | `sous-requete-correlee` | 62.9 s | 0.0 Go | ≈ deux tiers de la forme |
| FND-010 Recherche vectorielle exacte, sans index | **plausible** | `pages-par-ligne` | 43.1 s | 1.5 Go | dépend de la taille des boîtes |
| FND-009 Contenu du message chargé avec son vecteur | **confirmé — récidive** | `colonne-volumineuse` | 42.4 s | 0.3 Go | ≈ 68 % de la forme, à mesurer par A/B |
| FND-002 Recherche plein texte, forme d'après task-427 | **écarté** | `hors-détecteur` | 167.8 s | 0.2 Go | — |
| FND-006 Registre : la boîte de la personne, une fois par requête | **écarté** | `hors-détecteur` | 67.9 s | 0.0 Go | — |

Les trois findings confirmés à la main le 2026-11-06 sont retrouvés (FND-003, FND-004, FND-005), et le registre est
écarté (FND-006). Le rejeu en ajoute deux qui avaient échappé à la lecture manuelle (FND-007, FND-009), tous deux
**récidives** d'une classe déjà corrigée.

#### FND-007 — Le document médical est chargé entier, vecteur compris, à l'ouverture d'un message

- **Verdict** : **confirmé — récidive**. La classe `colonne-volumineuse` a déjà été corrigée sur ce même chemin
  (task-322, task-323) et sur le dossier patient (FND-003, task-429).
- **Forme** : `9a63b74fac8c0708f158bb2588df9b57`
- **Détecteurs** : `colonne-volumineuse` (Body, Embedding, HtmlBody, MetadataJson) et `poids-dans-le-tir`.
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1263`, `PopulateMailContentAsync`, branche
  `WithContent`. Retrouvé par `git grep -n "MailMedicalDocuments.Where(a => a.MailId"` au commit du tir.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 168 700 |
| Temps SQL | 165.7 s |
| Part du temps SQL | 13.0 % |
| ms par appel | 0.98 |
| Pages par appel | 18 |
| Pages lues | 22.8 Go |
| Lu sur disque | 5.4 Go |
| Part des lectures disque | 33.1 % |

- **Cause** : en mode `WithContent`, l'entité `MailMedicalDocument` est matérialisée entière. `BuildMedicalDocumentDto`
  (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:1355`) ne lit que `Body` et `HtmlBody`. `Embedding` et
  `MetadataJson` sont lus, détoastés, transférés, puis jetés. Le chemin groupé les écarte déjà (task-322,
  `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1928`), le chemin d'un message seul non.
- **Preuve** : sous PostgreSQL 16, `EXPLAIN ANALYZE` ne détoaste pas. Le plan (`FND-007.txt`) montre 2 pages, là où
  le tir en a lu 18 par appel. La preuve est donc le poids de chaque colonne.
  **Plan** : `FND-007-colonnes.txt`

```text
| lignes | Body (octets/ligne) | HtmlBody (octets/ligne) | Embedding (octets/ligne) | MetadataJson (octets/ligne) |
| 157 | 2482 | 37860 | 6148 |  |
```

- **Gain borné** : `Embedding` pèse 6 148 octets sur 46 490 par ligne, soit 13 % des octets détoastés de la forme.
  `MetadataJson` est vide au banc et n'y pèse rien. Le gain est au plus ≈ 13 % de 165.7 s et de 22.8 Go, à mesurer
  par A/B. Il ne se reporte pas sur le temps de réponse sans mesure.
- **Correctif proposé** : projeter `MailMedicalDocument` sans `Embedding` ni `MetadataJson` en `WithContent`, comme
  `MedicalDocumentHeaderProjection` le fait en mode en-tête.
- **Test qui le prouverait** : un test d'intégration sur `GET /api/v1/Mail/folders/{folderName}/emails/{emailId}`
  ouvrant un message à document. Le SQL relevé par `NpgsqlQueryCapture` ne doit sélectionner ni `"Embedding"` ni
  `"MetadataJson"`. Il doit être vu rouge sur le code d'avant.
- **Prévention manquante** : la consigne `groupby-final-materialise-l-entite` de `conventions/csharp.md` interdit déjà
  de matérialiser une colonne volumineuse hors du chemin qui la sert. Mais sa garde
  (`AttachmentBytesReadEndToEndTests`) ne couvre que `Content` des pièces jointes. La garde qui manque : « aucune route
  de lecture du parcours ne sélectionne `Embedding` ni `MetadataJson`, hors recherche vectorielle ».

#### FND-004 — Le comptage de biologie parcourt la table par document

- **Verdict** : **confirmé**.
- **Forme** : `ac42e9c32aa51dc548795bf6a9692db0`
- **Détecteurs** : `pages-par-ligne` et `sous-requete-correlee`.
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1967`
  (`BiologyCount = d.MailMedicalDocumentBiologies.Count`), dans `LoadBulkMailLookupsAsync`. Retrouvé par
  `git grep -n BiologyCount`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 88 248 |
| Temps SQL | 113.7 s |
| Part du temps SQL | 8.9 % |
| Lignes par appel | 18.1 |
| Pages par appel | 213 |
| Pages par ligne | 11.8 |
| Pages lues | 143.2 Go |

- **Cause** : le compteur est une sous-requête corrélée par document, sur une table sans index sur
  `MedicalDocumentId` au commit du tir. Chaque document balaie la table de biologie.
- **Preuve** : plan au schéma du tir, avec l'index de task-430 retiré dans une transaction annulée.
  **Plan** : `FND-004.txt`

```text
SubPlan 1
->  Aggregate (actual time=0.010..0.010 rows=1 loops=20)
->  Seq Scan on "MailMedicalDocumentBiology" m0 (actual time=0.009..0.010 rows=1 loops=20)
Filter: (m."Id" = "MedicalDocumentId")
Rows Removed by Filter: 118
```

  À la taille de la base de banc (118 lignes rejetées par document), le planificateur garde le balayage même avec
  l'index (`FND-004-schema-courant.txt`). Le coût croît avec la table, et le tir l'a payé à 213 pages par appel.
- **Gain borné** : les pages de la sous-requête, au plus 143.2 Go et 113.7 s.
- **Correctif** : index sur `MailMedicalDocumentBiology.MedicalDocumentId` — task-430.
- **Registre** : déjà corrigé et mesuré (task-430 : −43 % de pages).

#### FND-003 — Les pièces jointes du dossier patient sont lues avec leur contenu

- **Verdict** : **confirmé**.
- **Forme** : `e25db356be94a82ee5c4619e7473f2ff`
- **Détecteurs** : `pages-par-ligne`, `colonne-volumineuse` (Content) et `poids-dans-le-tir`.
- **Site** : `src/Infrastructure/Repositories/MailDb/PatientRepository.cs:700` (`.GroupBy(a => a.MailId)`), dans
  `LoadMailsWithAttachmentsAsync` (`src/Infrastructure/Repositories/MailDb/PatientRepository.cs:651`). Retrouvé par
  `git grep -n "GroupBy(a => a.MailId"`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 3 862 |
| Temps SQL | 67.6 s |
| Lignes par appel | 30.5 |
| Pages par appel | 468 |
| Pages lues | 13.8 Go |
| Lu sur disque | 5.1 Go |
| Part des lectures disque | 30.9 % |

- **Cause** : un `GroupBy` final matérialise l'entité `MailAttachment` entière, `Content` compris, pour n'en projeter
  que les métadonnées.
- **Preuve** : `Content` pèse quatre ordres de grandeur de plus que les métadonnées projetées.
  **Plan** : `FND-003-colonnes.txt`

```text
| lignes | Content (octets/ligne) | FileName (octets/ligne) | ContentType (octets/ligne) |
| 261 | 184586 | 12 | 16 |
```

- **Gain borné** : la quasi-totalité de la forme, au plus 13.8 Go lus et 5.1 Go sur disque.
- **Correctif** : projeter avant de regrouper — task-429.
- **Registre** : déjà corrigé et mesuré (task-429 : lectures disque du tir −60 %).

#### FND-005 — Les comptages d'étiquettes sont calculés trois fois

- **Verdict** : **confirmé**.
- **Forme** : `2a14c9daf0b3eeb161b438a62f3eac73`
- **Détecteurs** : `pages-par-ligne` et `sous-requete-correlee`.
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:3461` et
  `src/Infrastructure/Repositories/MailDb/MailRepository.cs:3462` (`Count` et `UnreadCount`, deux expressions
  identiques), sous le filtre `Any` de `src/Infrastructure/Repositories/MailDb/MailRepository.cs:3451`, dans
  `GetTagFoldersAsync`. Retrouvé par `git grep -n "db.Tags"`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 47 024 |
| Temps SQL | 62.9 s |
| Pages par appel | 248 |
| Pages par ligne | 24.4 |
| Pages lues | 89.0 Go |

- **Cause** : la même sous-requête corrélée est écrite trois fois. Le filtre `Any` et deux compteurs identiques
  (`Count` = `UnreadCount`) balaient chacun `MailTags`, par étiquette.
- **Preuve** : **Plan** : `FND-005.txt`

```text
SubPlan 1
->  Seq Scan on "MailTags" m1 (actual time=0.001..0.012 rows=21 loops=11)
Filter: ("TagId" = t."Id")
SubPlan 2
->  Seq Scan on "MailTags" m3 (actual time=0.001..0.011 rows=21 loops=11)
```

- **Gain borné** : environ deux tiers des pages de la forme (deux balayages sur trois), au plus 89.0 Go et 62.9 s.
- **Correctif** : un seul comptage groupé par étiquette — task-430.
- **Registre** : déjà corrigé et mesuré (task-430 : −96 % de pages).

#### FND-010 — La recherche vectorielle calcule la distance de chaque document de la boîte

- **Verdict** : **plausible**.
- **Forme** : `9b0276b995554c73320b5caa00935e87`. Variante : `90fed31c06a6aff57d1fb5c7c8d25a5d`, la même recherche
  sur `MailContents`.
- **Détecteurs** : `pages-par-ligne`.
- **Site** : `src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs:295` (`CosineDistance`, jointure par
  dossier, seuil, tri, limite). Retrouvé par `git grep -n CosineDistance`. Site probable : la forme n'a pas de filtre
  patient, que la méthode n'émet que s'il est fourni.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 8 666 |
| Temps SQL | 43.1 s |
| ms par appel | 4.97 |
| Pages par appel | 617 |
| Lu sur disque | 1.5 Go |

- **Cause probable** : aucun index vectoriel. Chaque recherche détoaste le vecteur de tous les documents du dossier
  pour calculer la distance, puis trie.
- **Preuve** : **Plan** : `FND-010.txt`

```text
->  Seq Scan on "MailMedicalDocuments" m (actual time=0.032..9.297 rows=2 loops=1)
Rows Removed by Filter: 155
Buffers: shared hit=575 read=1
```

- **Pourquoi plausible et pas confirmé** : une recherche exacte est le bon plan à 157 documents par boîte. Un index
  HNSW est approché et post-filtre par dossier et par seuil. Le défaut n'existe que si les boîtes grossissent.
- **Gain borné** : au plus 43.1 s pour cette forme, plus 37.1 s pour sa variante. Pour trancher, il faut un tir sur
  des boîtes à 10 fois plus de documents.
- **Test qui le prouverait** : un plan sur une base de 2 000 documents, avec et sans index HNSW, rappel mesuré.

#### FND-009 — Le contenu du message est chargé avec son vecteur

- **Verdict** : **confirmé — récidive**. Même classe et même chemin que FND-007.
- **Forme** : `4b9380ddd1837d2bc365a5afbc833f85`
- **Détecteurs** : `colonne-volumineuse` (Body, BodyHtml, Embedding).
- **Site** : `src/Infrastructure/Repositories/MailDb/MailRepository.cs:1326` (`PopulateMailContentAsync`, branche
  `WithContent`). Le DTO ne recopie que `Body`, `BodyHtml`, `ContentType` et `Summary`
  (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:1337`). Retrouvé par
  `git grep -n "MailContents.Where(c => c.MailId"`.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 168 138 |
| Temps SQL | 42.4 s |
| Pages par appel | 8 |
| Pages lues | 10.7 Go |
| Lu sur disque | 0.3 Go |

- **Cause** : en `WithContent`, l'entité `MailContent` est matérialisée entière, `Embedding` compris, que rien
  n'affiche.
- **Preuve** : **Plan** : `FND-009-colonnes.txt`

```text
| lignes | Body (octets/ligne) | BodyHtml (octets/ligne) | Summary (octets/ligne) | Embedding (octets/ligne) |
| 156 | 2842 |  |  | 6148 |
```

- **Gain borné** : `Embedding` pèse 6 148 octets sur 8 990 par ligne, soit 68 %. Le gain est au plus ≈ 68 % de
  10.7 Go et de 42.4 s, à mesurer par A/B.
- **Correctif proposé** : le même que FND-007, sur `MailContent` (`ContentHeaderProjection` sans le vecteur).
- **Test qui le prouverait** : le même que FND-007.

#### FND-002 — Recherche plein texte : la forme d'après task-427

- **Verdict** : **écarté**. C'est la forme déjà corrigée de FND-002.
- **Forme** : `840774b6aad35df6f93d47d8d971aca0`. Variante : `28e9d819261554f956f0ee69032938d7`.
- **Détecteurs** : aucun. Elle est candidate par son coût (13.1 % du temps SQL).
- **Site** : `src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs:666` (`WITH terms AS`).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 8 717 |
| Temps SQL | 167.8 s |
| Part du temps SQL | 13.1 % |
| ms par appel | 19.25 |

- **Raison** : le corps n'est mis en minuscules qu'une fois par contenu candidat, ce qui était le correctif de
  task-427. Le coût restant est la lecture des corps à comparer, proportionnelle aux candidats du filtre.
  **Plan** : `FND-002.txt`

```text
->  Memoize (actual time=0.005..0.005 rows=1 loops=50)
Cache Key: (lower(d_1."Body"))
Execution Time: 4.471 ms
```

#### FND-006 — Registre : la boîte de la personne, lue une fois par requête

- **Verdict** : **écarté**. C'est le coût normal d'une recherche indexée d'une ligne.
- **Forme** : `8b53e22fb9e5951d2a2cd7da49917075`
- **Détecteurs** : aucun. Elle est candidate par son coût ; c'est le faux positif connu de D1.
- **Site** : `src/Infrastructure/Repositories/TenantDb/PostgresTenantRegistryClient.cs:390` (`GetMailboxAsync`).
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| Appels | 760 820 |
| Temps SQL | 67.9 s |
| Pages par appel | 9 |
| Lignes par appel | 1.0 |
| Bases | 1 |

- **Raison** : deux recherches par index unique, 12 pages et 0,3 ms. Le poids vient de la fréquence (une lecture par
  requête HTTP), pas du plan. S'il gêne un jour, la réponse est un cache, pas une requête.
  **Plan** : `FND-006.txt`

```text
->  Index Scan using ux_mss_accounts_account_address on mss_accounts m (actual time=0.068..0.068 rows=1 loops=1)
Buffers: shared hit=12
Execution Time: 0.342 ms
```

### Connus du registre — remesurés

Le mode complet ré-explore tout, il n'y a donc rien à remesurer à part. En mode normal, FND-002 à FND-006 seraient
seulement remesurés.

### Ce que l'humain décide

La forge ne rédige aucune task d'elle-même. Propositions, par gain borné décroissant :

1. FND-007 + FND-009 : projeter les documents et le contenu sans vecteur à l'ouverture d'un message, et ajouter la
   garde « aucune route de lecture ne sélectionne `Embedding` ». Une seule task.
2. FND-010 : un tir sur des boîtes à 10 fois plus de documents, pour trancher le besoin d'un index vectoriel.
