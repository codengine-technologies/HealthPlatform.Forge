# Rapport de tir — terrain-1000-20260926-develop

> Banc de charge api-mail (EPIC E015). Source k6 : `terrain-1000-20260926-develop-024619.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- 3 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 1000 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 1 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.006 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : terrain
- **Utilisateurs** : 1000 — **VUs** : 1000 — **Durée** : 10830s — **Latence** : mssante
- **Requêtes** : 228793 — **débit émergent global** : 21.0 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 1807 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 1000 / 1000 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | terrain | — | 21.0 | **115.4** | 32.2 | **484.4** | — | 6379.3 | 0.01 | 100.0 | 0 | 0 | 129351/247 |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **1000 praticiens inscrits** | 10800 | 10555 | 216466 | 20.51 | 0.00 | 778.6 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 1000 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 18 / 792 (n=64228) |
| 2 | Ouvrir / rafraîchir l'inbox | 31 / 64 (n=32100) |
| 3 | Ouvrir un message enrichi (servi base) | 29 / 45 (n=16050) |
| 4 | Ouvrir un message froid (fetch IMAP) | 435 / 503 (n=6442) |
| 5 | Recherche | 265 / 360 (n=4761) |
| 6 | Envoi (acquittement UI) | 844 / 944 (n=4707) |
| 7 | Télécharger une PJ (~124 Ko) | 28 / 361 (n=6382) |
| 8 | Marquer lu | 24 / 33 (n=12838) |
| 9 | Rechercher un patient | 14 / 19 (n=4694) |
| 10 | Ouvrir la page d'un dossier patient | 38 / 69 (n=7028) |
| 11 | Fiche patient complète (ressenti médecin) | 217 / 342 (n=3514) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Terrain — praticiens inscrits, concurrence active

> **N désigne des praticiens INSCRITS.** Le modèle de session (task-321) fait s'absenter chaque praticien entre deux sessions de messagerie : la concurrence réelle **émerge** au lieu d'être fixée à 100 %. La grille SLO par geste est celle de `journey`, inchangée ; ce qui change est qui frappe à la porte, et quand. **Une ligne terrain ne se compare jamais à une ligne journey.**

**Profils** (journée de 8 h — hypothèses construites par cohérence, à remplacer par les distributions observées dans `audit_traces` dès que le journal tourne en production) :

| Profil | Part | Sessions / journée | Session moyenne |
|---|---|---|---|
| `occasionnel` | 30 % | 2 | 3 min |
| `regulier` | 50 % | 5 | 6 min |
| `intensif` | 20 % | 10 | 12 min |

| Palier | Régime (s) | Sessions | **Actifs en moyenne** (attendu) | Sessions / praticien / h (attendu) | Passages / praticien / h (attendu) | Passages / session | Absence moyenne (attendu) |
|---|---|---|---|---|---|---|---|
| **1000 inscrits** | 10555 | 1801 | **95** (85) | 0.61 (0.58) | 5.3 (4.5) | 8.7 | 97 min (135) |

> **Lecture.** « Actifs en moyenne » = Σ secondes de session ÷ fenêtre de régime : c'est le nombre de praticiens réellement dans la messagerie à un instant quelconque, et l'unité du verdict SLO ci-dessous. Le modèle est **fermé** : un serveur lent allonge les sessions (le praticien attend), donc **augmente** les actifs et **réduit** les passages par heure — un écart obtenu/attendu dans ce sens est la signature d'un serveur qui freine ses utilisateurs, pas d'un modèle faux.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **1000 médecins** | 15.2 / 20 | 37.9 / 74 | 7966 | 342 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 685 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 11000 appels d'analyse, ~1078000 messages analysés, 313 ms en moyenne, 6379 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 1000 médecins |
|---|---|
| Sessions IMAP (moy/max) | 222 / 1021 (magasin) |
| Backends Postgres (moy/max) | 231 / 667 |
| PgBouncer `sv_login` — backends en login (moy/max) | 0 / 2 |
| PgBouncer `cl_waiting` (échant. non nuls) | 17/2144 (1 %) |
| …dont bases **praticien** (échant. non nuls) | 15/2144 (1 %) |
| …dont pool de **maintenance** (échant. non nuls) | 2/2144 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 1925.8 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 6.9 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 1925.8 |
| PgBouncer refus `server_login_retry` (total du palier) | 0 |
| Login PostgreSQL depuis le conteneur, s (p50 / p95 / max) | 0.006 / 0.007 / 0.024 |
| Backends Postgres créés depuis < 60 s — `started_last_60s` (moy/max) | 53 / 344 |
| Backends Postgres inactifs > 60 s — `idle_over_60s` (min ; 0 soutenu = churn total) | 0 |
| Backends venant du **pooler** (`application_name` hors `mss-mail-*`, max) | 636 |
| Backends **directs** — audit + provisionnement (max) | 30 |
| … dont **journal d'audit** — `mss-mail-audit` (max) | 5 |
| … dont **provisionnement** — `mss-mail-provision` (max) | 5 |
| Mémoire du conteneur Postgres — usage du cgroup (max, %) | 65.7 |
| Fautes majeures du cgroup Postgres — `majfault_per_s` (moy/max) | 0 / 0 |
| RSS par réplica api-mail, Mo (moy/max) | 825 / 1230 (5 réplicas) |

- à 1000 médecins : Backends Postgres au pic : **667.0 / 2500** (26.7 % de `max_connections`)

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 100.0 %** des 1000 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⓘ Chauffe : **200 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 10800 s, soit **2 %** — sous le plafond de 50 % : le régime occupe le reste de la fenêtre.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 1000 : chauffe [+30 s..+275 s] (2 % de la fenêtre) ; **régime [+275 s..+10830 s]** porte le verdict

### 1000 praticiens inscrits — 95 actifs en moyenne — ✅ SLO tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 18 (300) | 792 (1500) | 64228 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 31 (300) | 64 (1000) | 32100 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 29 (100) | 45 (500) | 16050 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 435 (800) | 503 (2500) | 6442 | ✅ |
| 5 | Recherche | 265 (500) | 360 (2000) | 4761 | ✅ |
| 6 | Envoi (acquittement UI) | 844 (1000) | 944 (3000) | 4707 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 28 (500) | 361 (2000) | 6382 | ✅ |
| 8 | Marquer lu | 24 (200) | 33 (1000) | 12838 | ✅ |
| 9 | Rechercher un patient | 14 (300) | 19 (1500) | 4694 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 38 (500) | 69 (2000) | 7028 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 217 (1500) | 342 (4000) | 3514 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **1000**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 64228 | 163 | 792 | 10493.9 | 52.2 % |
| 🟠 | Envoi (acquittement UI) (`send`) | 4707 | 701 | 944 | 3299.1 | 16.4 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 6442 | 313 | 503 | 2015.0 | 10.0 % |
| 🟢 | Recherche (`search`) | 4761 | 277 | 360 | 1317.6 | 6.5 % |
| 🟢 | Ouvrir / rafraîchir l'inbox (`read_list`) | 32100 | 37 | 64 | 1203.4 | 6.0 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 16050 | 35 | 45 | 560.3 | 2.8 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 6382 | 61 | 361 | 392.1 | 1.9 % |
| 🟢 | Marquer lu (`mark_read`) | 12838 | 25 | 33 | 323.3 | 1.6 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 3983 | 64 | 51 | 253.1 | 1.3 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 3514 | 39 | 69 | 138.6 | 0.7 % |
| 🟢 | Rechercher un patient (`patient_search`) | 4694 | 14 | 19 | 67.8 | 0.3 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 3514 | 15 | 20 | 53.1 | 0.3 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 3 🟠 · 9 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 10493.9 s, 52.2 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 43.9×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Envoi (acquittement UI)** (`send`, 3299.1 s, 16.4 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
- **Télécharger une PJ (~124 Ko)** (`attachment`, 392.1 s, 1.9 %)
  - **dispersion p95/p50 = 12.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation

> Ce tir est un **A/B de non-régression** de `develop` à `dff07dce` contre
> `terrain-1000-20260921-task323` (branche task-323 à `c98f38f9`). Facteurs qui ont
> changé entre les deux jambes : `6e482d7e` (le tableau de bord ne fait plus de
> `SEARCH SINCE` : il remonte la fin de la boîte en séquences sous le verrou),
> task-171 (jeton PSC récupéré par api-mail auprès du proxy — **non exercé ici**,
> le banc s'authentifie à IMAP par mot de passe), le nettoyage Sonar `e1b10dbd`
> (89 fichiers, dont `ImapConnectionService`, `BackgroundSyncManager`, SMTP), et des
> tests seuls (`07e45229`, `dff07dce`). Iso-conditions : même population de 1 000
> boîtes non purgées, mêmes paramètres, banc mail cluster à 96 ms, tireur k6 sur le
> poste, Postgres recréé juste avant le tir (cache froid, comme la référence).

**Verdict de l'A/B : aucune régression, et le goulet n'a pas changé.**

| Grandeur | Référence 21/09 | Ce tir | Lecture |
|---|---|---|---|
| SLO | 11/11 | **11/11** | — |
| Latence moy. / p95 globales | 131,4 / 561,7 ms | **115,4 / 484,4 ms** | −12 % / −14 % |
| Arrivée dashboard p50 / p95 | 17 / 877 ms | 18 / **792** ms | −10 % au p95 |
| Appel `today` p50 / p95 (temps total) | 15 / 522 ms (1 950 s) | 15 / 475 ms (1 869 s) | **neutre** — `6e482d7e` ne coûte rien sur Dovecot |
| Appel `folder` de l'arrivée p50 / p95 | 463 / 1 330 ms | 434 / 1 170 ms | même population lente |
| Recherche p50 / p95 | 418 / 651 ms | 265 / 360 ms | **externe** (OpenAI), voir le finding n° 3 |
| Envoi p50 / p95 | 883 / 1 131 ms | 844 / 944 ms | −4 % / −17 % |
| Coût SQL par requête HTTP | 4,3 ms | 4,4 ms | iso |
| cgroup Postgres moy / max | 51 / 65 % | 51 / 66 % | iso |
| 5xx en régime | 17 | 14 (dont 13 task-324) | voir « Analyse Seq » |

**1. Arrivée dashboard — 52,2 % du temps serveur — l'attente du verrou `imap_session` (cause MESURÉE, inchangée).**
- *Mesuré dans ce tir* : `GET /mail/folders/INBOX` a toujours **deux populations** — sur 22:30-23:30, 7 657 appels à 50 ms en moyenne et **3 611 (32 %) à 674 ms** (21/09 : 31 % à 773 ms). Décomposition d'une requête de la population lente (trace `0b1dbcf1…`, 579 ms) : **450 ms d'attente du verrou** `ReadFolder:INBOX` (`WaitTimeMs=450`), 115 ms de revalidation IMAP, le reste < 15 ms — la même forme que le 21/09 (442 ms sur 585).
- *Qui retient le verrou* : `GetFolders` à **6,56 s de détention p95 en établissement de session** (21/09 : 7,02 s) ; les 23 `Lock released (long)` de Seq sont **tous** des `GetFolders` (max 6,27 s).
- *Nouveau* : l'étiquette `ReadToday` apparaît (1,56 acquisition/s, détention p95 1,83 s dont 0,85 s d'exploitation). Elle matérialise la voie de `6e482d7e` ; les acquisitions `ReadFolder` passent de 2,95 à 2,38/s. Le décompte d'avant `6e482d7e` n'isolait pas le `SEARCH` du jour : **pas de comparaison acquisition par acquisition possible**. En latence, la voie est neutre (ligne `today` ci-dessus).
- *Remède, gain, risque* : inchangés depuis le 21/09 — sortir l'établissement de session de la section critique, ~20 % du temps serveur attendu ; risque sérieux (task-270 : ×19 chez les voisins). **A/B au banc obligatoire, juge = la table de détention par opération.**

**2. Envoi — 16,4 % — pas de cause établie par ce tir.** Plus rapide qu'en référence (p95 −17 %) sans facteur ciblé ; renvoi à task-281 (archivage Sent, 4 allers-retours). Pas un finding.

**3. Recherche — n'est plus candidate, mais son gain n'est PAS attribuable au code.** Moyenne 764 → 277 ms : la référence avait une queue (moyenne > p95) caractéristique des appels OpenAI lents ; ici 0 échec d'embedding, 0 `ClientResultException`. Aucun commit de la fenêtre ne touche la recherche. **Ne pas créditer `develop`.**

**4. task-171 : coût inconnu, hors de portée du banc.** `ImapConnectionService.AuthenticateClientAsync` ne passe par `IPscTokenProvider` que si `UseAuth2` ; le banc est en mot de passe, donc **l'appel au proxy PSC n'a jamais eu lieu**. Or il s'exécute pendant l'établissement de session, c'est-à-dire **dans la section critique qui fait le finding n° 1** : en production, chaque aller-retour au proxy (délai 5 s au pire) allonge la détention. *Backlog d'instrumentation* : un proxy PSC simulé dans l'AppHost du banc, à latence réglable, et `UseAuth2` sur les boîtes de banc.

**Proposition à l'humain (non créée d'office)** : une task `/po` sur le finding n° 1, qui pèse > 15 % du temps serveur, en y intégrant la réserve n° 4 : la sortie de l'établissement de session hors du verrou protège aussi du coût du proxy PSC.

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 16057 | 434 | 1170 | 7604.5 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 16057 | 15 | 475 | 1868.5 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 16057 | 19 | 177 | 792.6 |
| 1000 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 16057 | 13 | 20 | 228.4 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 16050 | 15 | 118 | 427.6 |
| 1000 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 16050 | 38 | 58 | 775.8 |

### Qui porte le coût — palier 1000 médecins

- **Arrivée dashboard** (`dashboard`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (1170 ms de p95, 434 ms de p50, n=16057), qui porte **aussi** le temps serveur de l'étape (7604.5 s, 72 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 1000) — le p95 de l'étape est porté par l'appel **`folder`** (118 ms de p95, 15 ms de p50, n=16050) ; le temps serveur total, lui, est porté par **`emails`** (775.8 s, 64 % du temps ventilé). Les deux porteurs diffèrent : la queue et le volume ne se corrigent pas de la même façon.

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 6417 | 61.6 | 28.4 | 40.6 | 362.6 | 1179.3 |
| attachment,palier:1000 | 6382 | 61.4 | 28.4 | 40.6 | 360.9 | 1179.3 |
| attachment,palier:transition | 16 | 95.7 | 27.8 | 48.3 | 318.9 | 1086.7 |
| dashboard | 64619 | 163.4 | 18.1 | 475.1 | 791.3 | 4212.2 |
| dashboard,call:coverage,palier:1000 | 16057 | 14.2 | 13.4 | 18.4 | 20.4 | 257.8 |
| dashboard,call:coverage,palier:transition | 28 | 14.0 | 12.2 | 15.9 | 21.4 | 43.7 |
| dashboard,call:folder,palier:1000 | 16057 | 473.6 | 434.5 | 1117.5 | 1169.7 | 4212.2 |
| dashboard,call:folder,palier:transition | 30 | 469.5 | 439.4 | 1136.3 | 1191.6 | 1224.0 |
| dashboard,call:folders,palier:1000 | 16057 | 49.4 | 18.8 | 156.1 | 176.7 | 544.1 |
| dashboard,call:folders,palier:transition | 28 | 35.4 | 17.5 | 112.9 | 146.4 | 181.8 |
| dashboard,call:today,palier:1000 | 16057 | 116.4 | 15.3 | 457.8 | 475.5 | 1205.0 |
| dashboard,call:today,palier:transition | 29 | 105.2 | 14.5 | 455.8 | 475.6 | 511.2 |
| dashboard,palier:1000 | 64228 | 163.4 | 18.0 | 475.0 | 791.9 | 4212.2 |
| dashboard,palier:transition | 115 | 161.0 | 16.9 | 469.1 | 774.3 | 1224.0 |
| mark_read | 12911 | 25.3 | 23.8 | 30.8 | 33.5 | 340.5 |
| mark_read,palier:1000 | 12838 | 25.2 | 23.8 | 30.8 | 33.4 | 340.5 |
| mark_read,palier:transition | 29 | 26.0 | 23.5 | 30.0 | 34.8 | 60.0 |
| patient_docs | 53599 | 50.4 | 38.4 | 58.1 | 68.4 | 2126.2 |
| patient_docs,palier:1000 | 53253 | 50.3 | 38.3 | 57.9 | 67.9 | 2126.2 |
| patient_docs,palier:transition | 74 | 41.6 | 43.8 | 59.8 | 63.5 | 96.4 |
| patient_dossier | 3538 | 39.6 | 37.6 | 61.6 | 70.0 | 257.8 |
| patient_dossier,palier:1000 | 3514 | 39.5 | 37.6 | 61.4 | 69.5 | 257.8 |
| patient_dossier,palier:transition | 8 | 35.8 | 27.6 | 61.9 | 65.1 | 68.2 |
| patient_opposition | 3538 | 15.2 | 14.3 | 18.7 | 20.5 | 61.4 |
| patient_opposition,palier:1000 | 3514 | 15.1 | 14.3 | 18.7 | 20.4 | 61.4 |
| patient_opposition,palier:transition | 8 | 15.8 | 15.1 | 19.3 | 22.5 | 25.7 |
| patient_search | 4723 | 14.5 | 13.8 | 17.8 | 19.5 | 155.2 |
| patient_search,palier:1000 | 4694 | 14.4 | 13.8 | 17.8 | 19.4 | 155.2 |
| patient_search,palier:transition | 8 | 14.8 | 14.9 | 16.6 | 16.6 | 16.6 |
| read_content | 16149 | 35.0 | 29.0 | 39.1 | 44.7 | 784.2 |
| read_content,palier:1000 | 16050 | 34.9 | 29.0 | 39.0 | 44.6 | 784.2 |
| read_content,palier:transition | 40 | 35.6 | 27.2 | 44.1 | 61.1 | 228.5 |
| read_content_cold | 6474 | 313.4 | 435.4 | 491.1 | 503.9 | 1496.1 |
| read_content_cold,palier:1000 | 6442 | 312.8 | 435.3 | 490.6 | 503.5 | 1496.1 |
| read_content_cold,palier:transition | 11 | 382.2 | 456.8 | 500.6 | 502.5 | 504.4 |
| read_list | 32304 | 37.5 | 30.5 | 48.5 | 64.4 | 735.4 |
| read_list,call:emails,palier:1000 | 16050 | 48.3 | 38.2 | 50.9 | 58.1 | 735.4 |
| read_list,call:emails,palier:transition | 39 | 49.1 | 35.6 | 48.1 | 62.8 | 429.1 |
| read_list,call:folder,palier:1000 | 16050 | 26.6 | 14.9 | 21.9 | 117.9 | 539.6 |
| read_list,call:folder,palier:transition | 39 | 15.9 | 15.4 | 19.0 | 21.0 | 26.8 |
| read_list,palier:1000 | 32100 | 37.5 | 30.5 | 48.5 | 63.8 | 735.4 |
| read_list,palier:transition | 78 | 32.5 | 27.6 | 43.7 | 48.0 | 429.1 |
| search | 4784 | 277.9 | 265.1 | 321.8 | 362.4 | 3551.8 |
| search,palier:1000 | 4761 | 276.7 | 264.9 | 321.1 | 359.8 | 1173.2 |
| search,palier:transition | 11 | 281.9 | 277.0 | 319.3 | 353.0 | 386.6 |
| send | 4721 | 701.5 | 843.9 | 926.0 | 944.5 | 1133.2 |
| send,palier:1000 | 4707 | 700.9 | 843.6 | 925.9 | 943.8 | 1133.2 |
| send,palier:transition | 7 | 827.4 | 886.4 | 925.7 | 939.3 | 952.8 |
| treatment | 4002 | 64.0 | 30.8 | 41.2 | 51.3 | 2546.0 |
| treatment,palier:1000 | 3983 | 63.6 | 30.8 | 41.1 | 51.0 | 2546.0 |
| treatment,palier:transition | 8 | 311.6 | 34.8 | 817.0 | 846.2 | 875.4 |
| warmup | 11000 | 313.1 | 96.6 | 235.1 | 2199.0 | 6379.3 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-26T21:45:08.105000+00:00 → 2026-09-27T00:46:19.649000+00:00 (10872 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-234458.csv`) | ✅ 279523 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-26392` | 0.48 | 2 | 18 | 0.008 | 0.91 |
| `DESKTOP-DEV-X2C-31108` | 0.45 | 2 | 15 | 0.009 | 1.04 |
| `DESKTOP-DEV-X2C-40620` | 0.45 | 3 | 14 | 0.009 | 1.49 |
| `DESKTOP-DEV-X2C-42640` | 0.34 | 1 | 12 | 0.007 | 1.20 |
| `DESKTOP-DEV-X2C-56044` | 0.43 | 2 | 15 | 0.007 | 0.89 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#21392` | 0.01 | 0.31 | 43 |
| `com.docker.backend#33900` | 0.30 | 3.32 | 1128 |
| `dcp#10988` | 0.00 | 0.00 | 12 |
| `dcp#14712` | 0.00 | 0.10 | 14 |
| `dcp#17148` | 0.00 | 0.20 | 42 |
| `dcp#31604` | 0.00 | 0.10 | 14 |
| `dcp#3600` | 0.00 | 0.10 | 12 |
| `dcp#42572` | 0.08 | 1.18 | 425 |
| `dcp#42792` | 0.00 | 0.05 | 14 |
| `dcp#43344` | 0.00 | 0.15 | 14 |
| `dcp#45284` | 0.00 | 0.05 | 12 |
| `dcp#46640` | 0.00 | 0.21 | 12 |
| `dcp#48244` | 0.00 | 0.10 | 12 |
| `dcp#54512` | 0.00 | 0.10 | 12 |
| `dcp#55408` | 0.00 | 0.05 | 12 |
| `dcp#55588` | 0.00 | 0.15 | 12 |
| `k6#4696` | 0.02 | 2.18 | 1344 |
| `mss.mail.api#26392` | 0.08 | 1.84 | 990 |
| `mss.mail.api#31108` | 0.08 | 1.92 | 952 |
| `mss.mail.api#40620` | 0.08 | 2.08 | 1230 |
| `mss.mail.api#42640` | 0.08 | 1.67 | 1052 |
| `mss.mail.api#56044` | 0.08 | 1.74 | 961 |
| `vmmemWSL#32776` | 2.33 | 10.57 | 51132 |
| `loadtest-otel-collector-cypdfsfs` | 0.02 | 0.11 | 113 |
| `loadtest-pgbouncer-wcfqgnmw` | 0.03 | 0.70 | 15 |
| `mss-mail-grafana-b6152948` | 0.00 | 0.11 | 117 |
| `mss-mail-prometheus-b6152948` | 0.01 | 0.07 | 198 |
| `mss-mail-rabbitmq-qqgzyyec` | 0.00 | 0.02 | 129 |
| `mss-mail-redis-b6152948` | 0.02 | 0.25 | 45 |
| `mss-mail-seq-b6152948` | 0.00 | 0.03 | 166 |
| `postgres-pgvector` | 0.23 | 8.02 | 14182 |

- **Hôte** : CPU 20.7 % moy / 100.0 % max sur 24 cœurs logiques, file processeur max 33
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 1274, cl_waiting max 4, cl_waiting_maintenance max 2, cl_waiting_practitioner max 4, count max 1001, login_retry_delta max 0, maxwait_maintenance_ms max 1926, maxwait_ms max 1926, maxwait_practitioner_ms max 10, sv_active max 13, sv_idle max 233, sv_login max 2
- **Backends Postgres** : audit max 5, cache_mb max 31443, direct max 30, idle_over_60s max 322, majfault_per_s max 0, pooler max 636, practitioner_databases max 626, provision max 5, rss_mb max 1664, seconds max 0, started_last_60s max 344, total max 667, usage_pct max 66

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 6833.9 | 2171 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2425.0 | 2170 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 897.3 | 2162 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 2500.0 | 2170 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 695.1 | 2154 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 1750.0 | 2142 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 178.6 | 2147 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 406.2 | 2153 |
| `api/v{version:apiVersion}/Mail/sendmail` | 1750.0 | 2132 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 178.8 | 2138 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 300.0 | 2138 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 55.0 | 2138 |
| `api/v{version:apiVersion}/Search/semantic` | 3560.1 | 2139 |
| `api/v{version:apiVersion}/Sync/coverage` | 75.9 | 2154 |

- **p95 client global (k6)** : 484.4 ms
- **p95 serveur le plus élevé** : 6833.9 ms
- **Écart** : -6349.4 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 0.25 |
| Documents CDA /s | 0.25 |
| Durée traitement CDA (s, p95) | 0.45 |
| Événements de session IMAP /s | 3.85 |
| Recherches (s, p95) | 3.560 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 2.2 | 5.3 | 123 | 0.0 (0.1 %), p95 5 | 4.3 (80.2 %), p95 123 | 1.0 (19.7 %), p95 123 |
| `GetMail` | 11.3 | 20.3 | 192 | 1.6 (8.0 %), p95 39 | 15.9 (78.4 %), p95 97 | 2.8 (13.6 %), p95 91 |
| `GetMailsByUids` | 14.3 | 21.1 | 218 | 0.0 (0.1 %), p95 5 | 16.6 (78.6 %), p95 179 | 4.5 (21.2 %), p95 25 |

- **`EnrichPersistMail`** — sur 5.3 ms en moyenne (2.2 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 4.3 ms exécution SQL, 1.0 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 20.3 ms en moyenne (11.3 requête(s) SQL par appel) : 1.6 ms attente d'une connexion, 15.9 ms exécution SQL, 2.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 21.1 ms en moyenne (14.3 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 16.6 ms exécution SQL, 4.5 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.1 | 2.8 | 271.8 | 0.9 | 1.2 | 0.9 | 2.7 | non relevé | 0.0 | 0.9 | 2.4 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 213.7 | 4.5 | 20.9 | 19.6 | 26.1 | 19.6 | 32.1 | 19.6 | 0.0 | 19.6 | 6.1 | 0.0 | 19.5 | 46.7 | 4.7 |

- **`GetMail`** — sur 2.8 ms de matérialisation, l'appel a construit 10.1 objets, dont 0.9 messages, 1.2 étiquettes, 0.9 destinataires, 2.7 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.4 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **271.8 µs**.

- **`GetMailsByUids`** — sur 4.5 ms de matérialisation, l'appel a construit 213.7 objets, dont 19.6 messages, 26.1 étiquettes, 19.6 destinataires, 32.1 pièces jointes, 19.6 identifiants enrichis, 0.0 acquittements, 19.6 documents médicaux, 6.1 résultats de biologie, 0.0 éléments de synthèse, 19.5 corps de messages, 46.7 objets de fil, 4.7 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **20.9 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **10559.3 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 2.2 | 217.4 | 975 | 152.0 (69.9 %), p95 488 | 18.4 (8.4 %), p95 235 | 17.3 (8.0 %), p95 475 | 22.0 (10.1 %), p95 235 | 7.8 (3.6 %), p95 49 |

- **Enrichir un message** — sur 217.4 ms en moyenne (2.2 message(s) par requête) : 152.0 ms fetch IMAP, 18.4 ms extraction XDM, 17.3 ms parsing CDA, 22.0 ms écritures base, 7.8 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`, 0.50 `close_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 222.1 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 690.6 | 983 | 0.0 (0.0 %), p95 5 | 7.0 (1.0 %), p95 19 | 272.1 (39.4 %), p95 505 | 411.3 (59.6 %), p95 489 | 444.9 (64.4 %), p95 1377 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 690.6 ms en moyenne : 0.0 ms garde d'opposition, 7.0 ms construction MIME, 272.1 ms obtention de session SMTP, 411.3 ms transmission + acquittement, 444.9 ms archivage Sent, 0.1 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | 0.005 | 0.725 | 0.18 |
| `imap_session` | 0.494 | 6.534 | 7.42 |
| `in_process_fetch` | 0.005 | 0.725 | 0.18 |
| `smtp_session` | 0.080 | 1.750 | 0.76 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.077 | 2.351 | 2.425 | 1.300 | 0.75 |
| `EnrichEmails` | 0.005 | 0.487 | — | 0.487 | 0.38 |
| `GetAttachmentStream` | 0.488 | 2.425 | 2.425 | 0.738 | 0.15 |
| `GetEmailContent` | 1.600 | 1.990 | 2.425 | 1.675 | 1.47 |
| `GetFolders` | 0.089 | 6.558 | 6.558 | 0.638 | 3.65 |
| `ProcessEmailUid` | 0.073 | 0.725 | — | 0.725 | 0.18 |
| `ReadFolder` | 1.525 | 2.425 | 2.750 | 0.506 | 2.38 |
| `ReadToday` | 0.082 | 1.825 | 2.425 | 0.850 | 1.56 |
| `UpdateFlag` | 0.032 | 0.713 | — | 0.713 | 1.91 |

#### Détention en exploitation, **fenêtre de régime** — palier 1000

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 1.300 | 0.0 % |
| `EnrichEmails` | **0.444** | 0.475 | 0.487 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.488 | 0.738 | 0.0 % |
| `GetEmailContent` | **0.488** | 0.575 | 1.675 | 0.0 % |
| `GetFolders` | **0.241** | 0.242 | 0.638 | 0.0 % |
| `ProcessEmailUid` | **0.487** | 0.488 | 0.725 | 0.0 % |
| `ReadFolder` | **0.399** | 0.432 | 0.506 | 0.0 % |
| `ReadToday` | **0.487** | 0.525 | 0.850 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.488 | 0.713 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 7.42 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.077 s au p95, contre 1.600 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

> ⓘ **PgBouncer — transitoire d'attente, écarté du verdict.** 18 échantillon(s) sur 2162 portent une attente cliente non nulle (0.8 %, pointe à 4), sous le seuil de présence soutenue de 25 %. Ce profil est celui d'une **ouverture de palier**, pas d'un pooler qui n'absorbe plus — il ne désigne donc pas de facteur limitant. À surveiller tout de même : sur la campagne du 2026-07-29, cette pointe croît avec la charge.

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| conteneur `postgres-pgvector` (CPU) | 8.02 cœurs | 24 cœurs | 33.4 % | 0.0 % — transitoire |
| processus `k6#4696` (CPU) | 2.18 cœurs | 24 cœurs | 9.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#40620` (CPU) | 2.08 cœurs | 24 cœurs | 8.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#31108` (CPU) | 1.92 cœurs | 24 cœurs | 8.0 % | 0.0 % — transitoire |
| processus `mss.mail.api#26392` (CPU) | 1.84 cœurs | 24 cœurs | 7.7 % | 0.0 % — transitoire |
| processus `mss.mail.api#56044` (CPU) | 1.74 cœurs | 24 cœurs | 7.2 % | 0.0 % — transitoire |
| processus `mss.mail.api#42640` (CPU) | 1.67 cœurs | 24 cœurs | 7.0 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-40620` | 3.00 éléments | 100 éléments | 3.0 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (conteneur `postgres-pgvector` (CPU)) monte à 33.4 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **181.3 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **479.6** | annulées : 0.0 % |
| Backends actifs (équivalent) | **0.09** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **4.4 ms** | sur 228 793 requêtes HTTP k6 |
| Taux de cache (blocs) | **97.88 %** | ⚠️ < 99 % : jeu de travail hors `shared_buffers` ou cache froid |
| Lecture disque | **1.41 Mo/s (180 blocs/s)** | attente disque : 18.2 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **81 347 / 4 895** | rapport 16.6 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **16.3** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.03 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **36 / 0** | blocs écrits par les backends eux-mêmes : 27 % |
| Sessions ouvertes / s | **1.57** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **291.9 Mo** | 1 000 bases |
| Backends (échantillonneur, moy / max) | **231 / 667** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **6 / 7 / 24 ms** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **51 / 66 %** | fautes majeures/s max : 0.0 |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

137 formes de requête, 5 184 781 appels, **11.9 min** de temps serveur cumulé — soit **3.1 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **19.6 %** | 20 % | 14 352 | 0.06 | 9.72 | 34.3 | 343 | 1 % | 0 | 843 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m0."Uid"::bigint AS "Uid", m0."FolderPath", m."Body" FROM "MailMedicalDocuments" AS m INNER JOIN "Ma…` |
| 2 | **19.3 %** | 39 % | 14 352 | 0.06 | 9.57 | 34.3 | 285 | 0 % | 0 | 843 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."MailId", m0."Uid"::bigint AS "Uid", m0."FolderPath", m."Body" FROM "MailContents" AS m INNER JOIN "Mails" AS …` |
| 3 | **12.0 %** | 51 % | 63 977 | 0.28 | 1.33 | 1.0 | 41 | 27 % | 0 | 933 | **Postgres** — 27 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Body", m."Category", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateConfirmed", m."DuplicateOfI…` |
| 4 | **6.1 %** | 57 % | 3 538 | 0.02 | 12.27 | 30.4 | 535 | 21 % | 0 | 799 | **Postgres** — 21 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 5 | **4.0 %** | 61 % | 29 463 | 0.13 | 0.96 | 16.9 | 208 | 0 % | 0 | 998 | — | `SELECT m."Id", m."MailId", m."PatientId", m."DocumentId", m."SetId", m."Version", m."Date", m."Title", m."Loinc", m."Ca…` |
| 6 | **3.4 %** | 64 % | 17 150 | 0.07 | 1.42 | 8.4 | 518 | 0 % | 0 | 1 000 | **Schéma** — ~62 blocs lus par ligne rendue : balayage probable — index sur le prédicat `WHERE`/`ORDER BY` (confirmer par `explain (analyze, buffers)`) | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 INNER JOIN "Mails" AS m2 ON m1."…` |
| 7 | **3.4 %** | 68 % | 4 784 | 0.02 | 5.02 | 19.8 | 682 | 3 % | 0 | 843 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m0."Uid"::bigint AS "Uid", m0."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 8 | **3.3 %** | 71 % | 5 810 | 0.03 | 4.04 | 178.0 | 537 | 1 % | 0 | 1 001 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `SELECT ns.nspname, t.oid, t.typname, t.typtype, t.typnotnull, t.elemtypoid FROM ( -- Arrays have typtype=b - this subqu…` |
| 9 | **2.9 %** | 74 % | 684 121 | 2.99 | 0.03 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 10 | **2.5 %** | 76 % | 2 061 | 0.01 | 8.64 | 1.0 | 0 | — | 0 | 1 | **Code** — verrou consultatif : sérialise les appelants — mesurer la détention avant d'élargir | `SELECT pg_advisory_xact_lock($1)` |
| 11 | **2.5 %** | 79 % | 684 121 | 2.99 | 0.03 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 12 | **2.1 %** | 81 % | 1 643 206 | 7.18 | 0.01 | 0.0 | 0 | — | 0 | 2 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 13 | **1.8 %** | 83 % | 4 784 | 0.02 | 2.74 | 19.8 | 691 | 2 % | 0 | 843 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m0."Uid"::bigint AS "Uid", m0."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 14 | **1.6 %** | 84 % | 8 244 | 0.04 | 1.39 | 1.0 | 31 | 3 % | 0 | 999 | **Infra** — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) | `select * from information_schema.columns where table_schema = $1 and table_name = $2 and column_name = $3` |
| 15 | **1.6 %** | 86 % | 63 651 | 0.28 | 0.18 | 1.0 | 8 | 3 % | 0 | 933 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."MailId", m."Summary" FROM "MailContents" AS m…` |
| 16 | **1.1 %** | 87 % | 228 789 | 1.00 | 0.03 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successful_login_at, m.m…` |
| 17 | **0.9 %** | 88 % | 6 754 | 0.03 | 0.96 | 1.0 | 27 | 41 % | 0 | 889 | **Postgres** — 41 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 18 | **0.9 %** | 89 % | 39 169 | 0.17 | 0.16 | 1.0 | 13 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 19 | **0.7 %** | 90 % | 99 279 | 0.43 | 0.05 | 1.8 | 9 | 0 % | 0 | 998 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 20 | **0.7 %** | 90 % | 99 279 | 0.43 | 0.05 | 1.3 | 15 | 0 % | 0 | 998 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 95.6 % | 63.4 % |
| INSERT | 1.7 % | 1.1 % |
| UPDATE | 0.4 % | 0.7 % |
| DELETE | 0.0 % | 0.2 % |
| AUTRE | 2.3 % | 34.6 % |
| bases : praticien (N bases) | 90.0 % | 67.4 % |
| bases : unique (1 base) | 10.0 % | 32.6 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **12.3** | 80 | 3 538 | 6.1 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **9.7** | 36 | 14 352 | 19.6 % | `SELECT m."MailId", m0."Uid"::bigint AS "Uid", m0."FolderPath", m."Body" FROM "MailMedicalDocuments"…` |
| **9.6** | 28 | 14 352 | 19.3 % | `SELECT m."MailId", m0."Uid"::bigint AS "Uid", m0."FolderPath", m."Body" FROM "MailContents" AS m IN…` |
| **8.6** | 3 209 | 2 061 | 2.5 % | `SELECT pg_advisory_xact_lock($1)` |
| **5.0** | 61 | 4 784 | 3.4 % | `SELECT m0."Uid"::bigint AS "Uid", m0."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |

### Tables et index de la base échantillon

Base `u_90000000002_l2l_cf8dc87f69ca70e04e966cfb8e1f8721` (la plus volumineuse du banc), compteurs fin − début.

| Table balayée (seq scan) | Balayages | Lignes lues | Lectures par index | Lignes vivantes | Taille |
|---|---|---|---|---|---|
| `MailTags` | 6 060 | 1 222 280 | 78 | 0 | 0.1 Mo |
| `Mails` | 562 | 72 491 | 361 | 0 | 0.1 Mo |
| `MailMedicalDocumentBiology` | 541 | 53 559 | 0 | 0 | 0.1 Mo |
| `MailRecipients` | 74 | 10 656 | 0 | 0 | 0.1 Mo |
| `MailAttachments` ⚠️ index candidat | 38 | 9 234 | 78 | 0 | 34.8 Mo |
| `MailMedicalDocuments` ⚠️ index candidat | 71 | 7 867 | 616 | 0 | 31.6 Mo |
| `MailContents` ⚠️ index candidat | 37 | 5 328 | 897 | 0 | 1.7 Mo |
| `Tags` | 44 | 792 | 154 | 0 | 0.0 Mo |
| `MailFolders` | 116 | 218 | 100 | 0 | 0.1 Mo |
| `VersionInfo` | 8 | 80 | 0 | 0 | 0.0 Mo |

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Postgres | 🟠 | taux de cache 97.9 % (< 99 %) : le jeu de travail déborde `shared_buffers` — cache froid (redémarrage) ou population trop large pour la mémoire allouée |
| Postgres | 🟠 | requête n°3 (12.0 % du temps SQL) — 27 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Postgres | 🟠 | requête n°4 (6.1 % du temps SQL) — 21 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟠 | 17 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | requête n°1 (19.6 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |
| Schéma | 🟠 | `MailAttachments` balayée 38 fois (9234 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailMedicalDocuments` balayée 71 fois (7867 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Schéma | 🟠 | `MailContents` balayée 37 fois (5328 lignes lues, 0 vivantes) pendant le tir sur la base échantillon : index candidat sur le prédicat de la requête qui la lit |
| Code | 🟡 | requête n°10 (2.5 % du temps SQL) — verrou consultatif : sérialise les appelants — mesurer la détention avant d'élargir |
| Infra | 🟡 | requête n°8 (3.3 % du temps SQL) — provisionnement / migration : ne doit pas apparaître en régime (sinon une base est recréée ou re-migrée pendant le tir) |
| Infra | 🟡 | requête n°9 (2.9 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°12 (2.1 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Schéma | 🟡 | requête n°6 (3.4 % du temps SQL) — ~62 blocs lus par ligne rendue : balayage probable — index sur le prédicat `WHERE`/`ORDER BY` (confirmer par `explain (analyze, buffers)`) |
| Schéma | 🟡 | requête n°7 (3.4 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-terrain-024621.tsv`, `pgserver-terrain-debut-234504.tsv`, `pgserver-terrain-fin-024623.tsv`, `pgtables-terrain-debut-234507.tsv`, `pgtables-terrain-fin-024626.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 129351 — dont **129351** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Attendu par boîte** : 247 (complétude relative au périmètre du scénario)
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-terrain-1000-20260926-develop-024619.jsonl` — **45 événements `Error`/`Fatal`, dump complet** (le compte agrégé Seq sur la fenêtre vaut exactement 45). Fenêtre : 2026-09-26 21:45:00Z → 2026-09-27 00:46:30Z. Aucun `Fatal`.

### Erreurs — 16 requêtes HTTP en 5xx sur 228 793 (0,007 %)

| Route | 5xx | Famille | Lecture |
|---|---|---|---|
| `/api/v1/mail/folders/INBOX` | **9** | `ObjectDisposedException: … 'ImapClient'` levée dans `ImapConnectionService.AuthenticateClientAsync` (`ImapConnectionService.cs:299`, voie mot de passe), mappée en 500 « Erreur inattendue lors de la connexion » | **Famille résiduelle connue**, instruite en `todo-task-324`, qui n'est pas mergée. Même famille que les 17 du 21/09 : **pas une régression** |
| `/api/v1/mail/folders` | **4 + 1** | 4 × même `ObjectDisposedException` (les 4 `warmup ko`, toutes à 21:45:27, pendant la rafale d'ouverture de sessions) ; 1 × `Request cancelled.` | Le `Request cancelled.` tombe à **00:46:19**, la seconde où k6 coupe : artefact de fin de tir |
| `/api/v1/mail/folders/INBOX/emails/today` | 1 | `Request cancelled.` | Même seconde (00:46:19) : artefact de fin de tir |
| `/api/v1/mail/folders/INBOX/emails/content/396` | 1 | `InvalidOperationException` (stratégie de reprise EF) ← `NpgsqlException: Exception while writing to stream` ← `SocketException 10053` | Une connexion Postgres coupée côté hôte, **isolée** (1 sur 3 h) ; à surveiller si elle se répète d'un tir à l'autre |

Les 13 `ObjectDisposedException` s'étalent sur tout le tir (4 à 21:45:27, puis 9 entre 22:12 et 00:00), comme le 21/09. **2 des 16 échecs ne relèvent pas du régime.**

**Constat secondaire (règle 12)** : une annulation `OperationCanceledException` sort ici en **500** et non en **499**. `ImapConnectionService.cs:135` et `ImapFolderService.cs:148` la convertissent en `Result.Error("Request cancelled.")` ; le code date de mars 2026, rien de neuf. C'est sans effet en régime, mais contraire à la règle 12 (« `OperationCanceledException` → 499 gérée centralement »).

### Marqueurs de régression — tous à zéro

| Marqueur | Attendu | Mesuré |
|---|---|---|
| `Failed to parse entity headers` (retour de GreenMail côté IMAP) | 0 | **0** ✅ |
| Échecs d'embedding (`maximum input length`, task-196) | 0 | **0** ✅ |
| `ClientResultException` / `insufficient_quota` (OpenAI) | 0 | **0** ✅ |
| HTTP 429 (limiteur) | 0 | **0** ✅ |
| `PostgresException 08P01 … server_login_retry` | 0 | **0** ✅ |

### Parsings CDA

**326** `[CdaParsingService] Parsing completed` (264 le 21/09). Chiffre attendu bas : la chauffe tourne en mode population hydratée (`JOURNEY_WARMUP_HYDRATED=1`) ; seuls les messages tirés par le geste « traitement » sont analysés en régime (3 983 traitements contre 3 898).

### Warnings — RAS hors bruit connu

| Contexte / modèle | n | Lecture |
|---|---|---|
| `[TlsCertificateValidationSession] Allowing untrusted certificate` | 7 450 | Certificat auto-signé du banc, voulu |
| `[MailClientSession] ♻️ Session expired` | 4 453 | Recyclage nominal après inactivité |
| `[CdaParsingService] Missing values` | 655 | Section vide dans le document de test : le parseur descend bien dans le CDA |
| `[ImapLock] 🔓⚠️ Lock released (long)` | 23 | **Tous `GetFolders`**, max 6 274 ms — voir le finding n° 1 |
| `[ImapSessionLock] Verrou de session disposé pendant l'opération` | 13 | Pendant exact des 13 `ObjectDisposedException` (task-324) |
| `[PractitionerContactPublisher] SKIPPED - Invalid RPPS` | 13 | Donnée du corpus |
| `[PractitionerContactService] SKIPPED - Empty FullName` | 5 | Donnée du corpus |
| `[MailRepository] biology results skipped (missing Name)` | 2 | Donnée du corpus |

### Hors de portée de ce tir

- **task-171 (jeton PSC récupéré auprès du proxy)** : jamais exercé, puisque le banc s'authentifie à IMAP par mot de passe (`UseAuth2=false`). Seq ne montre aucun appel au proxy. Voir le finding n° 4.
