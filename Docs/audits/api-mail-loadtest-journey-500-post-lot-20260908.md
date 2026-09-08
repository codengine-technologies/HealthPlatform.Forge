# Rapport de tir — journey-500-lot288-194-20260908

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-500-lot288-194-20260908-225405.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- à 500 médecins, 1 étape(s) dépassent le temps de réponse attendu : « Recherche »
- 4 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)
- à 500 médecins, des demandes ont **attendu une connexion à la base** (`cl_waiting` non nul sur 5 % des relevés) — le contrat exige zéro : le multiplexeur est sous-dimensionné
- 0.002 % des demandes ont échoué (sous le plafond, mais non nul)

## Contexte

- **Scénario** : journey
- **Utilisateurs** : 500 — **VUs** : 500 — **Durée** : 7230s — **Latence** : mssante
- **Requêtes** : 470669 — **débit émergent global** : 64.8 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 39289 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 500 / 500 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | 500 | journey | — | 64.8 | **116.5** | 28.8 | **474.9** | — | 31085.5 | 0.00 | 100.0 | 0 | 0 | 114768/247 |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre stabilisée (s) | Requêtes | Débit émergent (req/s) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|
| **500 médecins** | 7200 | 196821 | 27.34 | 0.00 | 844.0 |

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 500 médecins |
|---|---|---|
| 1 | Arrivée dashboard | 13 / 467 (n=66696) |
| 2 | Ouvrir / rafraîchir l'inbox | 118 / 483 (n=33374) |
| 3 | Ouvrir un message enrichi (servi base) | 39 / 110 (n=16694) |
| 4 | Ouvrir un message froid (fetch IMAP) | 409 / 469 (n=3231) |
| 5 | Recherche | 567 / 906 (n=4964) |
| 6 | Envoi (acquittement UI) | 440 / 890 (n=5068) |
| 7 | Télécharger une PJ (~124 Ko) | 344 / 715 (n=6705) |
| 8 | Marquer lu | 29 / 75 (n=13406) |
| 9 | Rechercher un patient | 6 / 30 (n=3956) |
| 10 | Ouvrir la page d'un dossier patient | 78 / 235 (n=4864) |
| 11 | Fiche patient complète (ressenti médecin) | 229 / 732 (n=2432) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **500 médecins** | 14.9 / 20 | 34.8 / 60 | 3138 | 732 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 1630 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 5500 appels d'analyse, ~539000 messages analysés, 363 ms en moyenne, 3963 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

| Coût résident | 500 médecins |
|---|---|
| Sessions IMAP (moy/max) | 437 / 729 (magasin) |
| Backends Postgres (moy/max) | 544 / 882 |
| PgBouncer `cl_waiting` (échant. non nuls) | 65/1427 (5 %) |
| …dont bases **praticien** (échant. non nuls) | 65/1427 (5 %) |
| …dont pool de **maintenance** (échant. non nuls) | 0/1427 (0 %) |
| PgBouncer `maxwait` (ms, pire relevé du palier) | 72.8 |
| …dont bases **praticien** (`u_9…`) — chemin de données du médecin | 72.8 |
| …dont pool de **maintenance** (`postgres`) — sonde de readiness | 0.0 |
| RSS par réplica api-mail, Mo (moy/max) | 1871 / 2485 (5 réplicas) |

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

✅ **Chauffe aboutie pour 100.0 %** des 500 médecins (plancher 90 %) : la base servant les étapes 2, 3, 10, 11 est peuplée, leurs verdicts sont opposables.

> ⚠️ Chauffe : **4871 s** au p95 (attente de vague incluse) sur une fenêtre de palier de 7200 s, soit **68 %** — au-delà du plafond de 50 %. Le palier mesure alors surtout sa propre préparation : allonger la fenêtre, ou réduire la réserve analysée. Le plafond de débit d'enrichissement du serveur (~9,5 messages/s, task-245) borne ce qu'on peut y gagner côté harnais — c'est **task-254** qui le relève.

> ⓘ **Fenêtres de verdict (task-264)** — la chauffe de chaque palier est allouée d'avance (cohorte nouvelle × réserve analysée ÷ débit plafond), taguée `chauffe`, et **exclue du verdict** : chaque verdict de palier est porté par sa seule fenêtre de régime. Un tir antérieur, qui incluait la chauffe dans la fenêtre, n'est pas directement comparable.
>   palier 500 : chauffe [+30 s..+5229 s] (72 % de la fenêtre) ; **régime [+5229 s..+7230 s]** porte le verdict

### 500 médecins — ❌ SLO non tenu

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 13 (300) | 467 (1500) | 66696 | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 118 (300) | 483 (1000) | 33374 | ✅ |
| 3 | Ouvrir un message enrichi (servi base) | 39 (100) | 110 (500) | 16694 | ✅ |
| 4 | Ouvrir un message froid (fetch IMAP) | 409 (800) | 469 (2500) | 3231 | ✅ |
| 5 | Recherche | 567 (500) | 906 (2000) | 4964 | ❌ |
| 6 | Envoi (acquittement UI) | 440 (1000) | 890 (3000) | 5068 | ✅ |
| 7 | Télécharger une PJ (~124 Ko) | 344 (500) | 715 (2000) | 6705 | ✅ |
| 8 | Marquer lu | 29 (200) | 75 (1000) | 13406 | ✅ |
| 9 | Rechercher un patient | 6 (300) | 30 (1500) | 3956 | ✅ |
| 10 | Ouvrir la page d'un dossier patient | 78 (500) | 235 (2000) | 4864 | ✅ |
| 11 | Fiche patient complète (ressenti médecin) | 229 (1500) | 732 (4000) | 2432 | ✅ |

> Le verdict ne se lit qu'accompagné des gardes système (erreurs < 0,1 %, `cl_waiting` = 0 soutenu, file ThreadPool < 100, sessions IMAP stables, RSS plate) — voir « Coûts résidents » et « Ressources & télémétrie ».

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **500**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 66696 | 107 | 467 | 7121.9 | 30.4 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 33374 | 161 | 483 | 5373.0 | 23.0 % |
| 🟠 | Recherche (`search`) | 4964 | 635 | 906 | 3149.8 | 13.5 % |
| 🟢 | Envoi (acquittement UI) (`send`) | 5068 | 552 | 890 | 2796.7 | 11.9 % |
| 🟢 | Télécharger une PJ (~124 Ko) (`attachment`) | 6705 | 284 | 715 | 1905.5 | 8.1 % |
| 🟢 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 3231 | 410 | 469 | 1324.6 | 5.7 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 16694 | 48 | 110 | 799.9 | 3.4 % |
| 🟢 | Marquer lu (`mark_read`) | 13406 | 35 | 75 | 469.1 | 2.0 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 2432 | 96 | 235 | 233.4 | 1.0 % |
| 🟠 | Traitement (plateforme) (`treatment`) | 1569 | 111 | 664 | 173.9 | 0.7 % |
| 🟢 | Rechercher un patient (`patient_search`) | 3956 | 10 | 30 | 38.9 | 0.2 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 2432 | 7 | 18 | 16.9 | 0.1 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 4 🟠 · 8 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 7121.9 s, 30.4 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 35.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 5373.0 s, 23.0 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 4.1×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Recherche** (`search`, 3149.8 s, 13.5 %)
  - **hors grille** — le médecin attend trop
- **Traitement (plateforme)** (`treatment`, 173.9 s, 0.7 %)
  - **dispersion p95/p50 = 11.2×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation

> Tir du lot **288-285-289-184-186-291-193-183-194** (9 PR mergées entre le 2026-09-01 et le 2026-09-08), code
> sous test `develop` `9bd8a72`. Référence : `report-journey-500-lot281283-20260831-004458` (code `b85f409`,
> 11/11 vertes). Conditions reproduites : 500 médecins, journey K=1, 7 230 s, réserves 365..462 / 463..536 /
> 537..611, probabilités traitement 0,095 / lecture froide 0,19, corpus fileté 0,3 sur le cluster, RTT p50
> **18,4 ms** → latence injectée **83 ms** (référence : 5,3 / 96, total apparié ~101 ms), bases **non purgées**
> entre le tir 1000 et celui-ci (protocole du 26/08 → 01/09 reproduit dans sa forme).
>
> **Écarts d'iso-conditions déclarés :**
> 1. **Âge de la base.** La référence tournait sur une base hydratée le 26/08 et exercée par quatre tirs
>    (30/08, 31/08…) : ses caches « à la première demande » étaient pleins. Ici la base a été **purgée le matin**
>    (A/B task-194) et ré-hydratée par un tir 1000 lui-même dégradé (F-08P01-1 du rapport 1000). Conséquence
>    mesurée sur l'étape 7 (F-AGE-1) et, très probablement, sur une partie des +10 à +60 % des étapes servies
>    par la base. **Règle à retenir : l'iso-condition inclut l'âge de la base, pas seulement son hydratation.**
> 2. **Contamination de la chauffe par l'analyse du tir 1000** : des requêtes Seq lourdes (comptages sur 3,5 h
>    d'événements) ont tourné sur l'hôte entre 21h05 et 21h50, **pendant la chauffe** (20h53 → 22h20). La
>    fenêtre de régime (22h20 → 22h53), seule à porter le verdict, n'a reçu que des sondes légères.
> 3. Neuf HTTP 500 dans les 10 premières minutes de chauffe : résidu du cache d'échec PgBouncer du tir 1000
>    (`08P01` cached, 23 refus jusqu'à 21h02), 0 ensuite. Sans effet sur le verdict.

#### F-500-1 — Verdict : 10/11 vertes, 0,002 % d'erreurs, la Recherche seule sort de la grille (au p50)

| Étape | 01/09 p50 / p95 | 08/09 p50 / p95 | Écart | Verdict |
|---|---|---|---|---|
| 1 Arrivée dashboard | 9 / 521 | 13 / **467** | p95 −10 % | ✅ |
| 2 Inbox | 105 / 304 | 118 / 483 | p95 +59 % | ✅ |
| 3 Message enrichi (base) | 27 / 71 | 39 / 110 | +55 % | ✅ |
| 4 Message froid (IMAP) | 455 / 512 | **409 / 469** | −9 % | ✅ |
| 5 Recherche | 404 / 560 | **567 / 906** | +40 % / +62 % | ❌ (p50 567 pour 500) |
| 6 Envoi | 470 / 963 | **440 / 890** | −6 % / −8 % | ✅ |
| 7 PJ | 9 / 423 | 344 / 715 | p50 ×38 | ✅ (F-AGE-1) |
| 8 Marquer lu | 20 / 48 | 29 / 75 | +56 % | ✅ |
| 9 Rechercher un patient | 5 / 18 | 6 / 30 | +67 % (sur 30 ms) | ✅ |
| 10 Page dossier patient | 51 / 147 | 78 / 235 | +60 % | ✅ |
| 11 Fiche patient complète | 157 / 463 | 229 / 732 | +58 % | ✅ |
| Latence moyenne / p95 global | 102,5 / 471,7 | 116,5 / 474,9 | +14 % / +0,7 % | — |
| Erreurs | 0,000 % | 0,002 % (9, chauffe) | — | — |
| `cl_waiting` praticien | 2 en régime | 5 % des relevés, pointe 5, `maxwait` 73 ms | — | 🟠 |

**Lecture.** Le p95 global est **inchangé** (+0,7 %) et le chemin messagerie (froid, envoi) **s'améliore** ;
ce sont les étapes **servies par la base** qui montent de 50 à 60 % au p95, sur des valeurs qui restent 2 à 5
fois sous leur cible. Trois causes candidates, dont une seule mesurée à ce stade : (a) l'âge de la base
(F-AGE-1, mesuré sur l'étape 7) ; (b) la charge d'écriture du journal d'audit (F-AUDIT-2, mesurée en volume,
pas en coût) ; (c) le coût par objet de la page d'en-têtes (F-194-2). Le tir ne permet **pas** de les séparer :
l'A/B qui tranche est un rejeu de ce même tir sur cette même base **sans purge**, dans quelques jours, qui
isolera (a).

#### F-AGE-1 — L'étape 7 (PJ) ne mesure pas la même chose qu'au 01/09 : le contenu se remplit à la première demande

Mesuré en base (praticien 500) : sur 116 archives `IHE_XDM.ZIP`, **68 ont un `Content` NULL et 48 un contenu**,
et la présence du contenu coïncide avec l'existence d'une trace d'audit `AttachmentDownload` pour le même UID
(47 sur 48 ; 68 sur 68 des NULL n'ont jamais été téléchargées). Le code confirme : `ImapService` →
`UpdateAttachmentAsync` **après** le premier téléchargement IMAP (lignes 3228 et 3417) ; à l'enrichissement, seul
le contenu des documents extraits est stocké, pas l'archive. Une PJ jamais demandée coûte donc un aller-retour
IMAP (trace : `GetAttachmentStream` sous `imap_session`, `WaitTimeMs=0`, 366 ms pour 25 Ko) ; une PJ déjà demandée
est servie par la base (9 ms le 01/09). **Le p50 de 9 ms du 01/09 mesurait un cache plein après quatre tirs ; le
p50 de 344 ms d'aujourd'hui mesure le premier passage.** Aucune régression : les deux chiffres décrivent deux
états de base. Finding d'instrument : la grille SLO devrait nommer l'étape « PJ, première demande » et
« PJ, déjà demandée », ou le rapport publier la part de téléchargements servis par la base (le compteur
`AttachmentDownload` du journal d'audit le permet désormais).

#### F-SEARCH-1 — La Recherche est hors grille au p50, et 67 % de son temps est chez OpenAI

Décomposition d'une recherche à 584 ms (médiane 567), trace `fa769dfb…` : démarrage 51,668 s → appel
`POST https://api.openai.com/v1/embeddings` (Polly, tentative 0) **391,6 ms** → requête vectorielle pgvector
**~18 ms** (échantillons de distance à 52,078) → hydratation des 10 résultats et réponse **~171 ms** (52,249).
Soit **67 % embedding externe, 3 % SQL vectoriel, 29 % hydratation des résultats**. La dérive constatée depuis
trois campagnes (331 → 425 → 567 ms de moyenne, « non attribuée » au 01/09) porte donc d'abord sur une latence
**réseau externe** que le banc ne contrôle pas ; elle n'est imputable ni au lot ni à Postgres. Deux leviers
applicatifs : mise en cache de l'embedding des requêtes récurrentes (la même requête revient d'un médecin à
l'autre dans le parcours), et allègement de l'hydratation (171 ms pour 10 documents = 17 ms/document, à comparer
aux 4,2 ms/objet de la page d'en-têtes). Gain attendu : p50 sous 300 ms sur requête en cache ; risque : nul sur
la pertinence si la clé de cache est le texte exact.

#### F-194-2 — La page d'en-têtes à 500 : +38 % par rapport au 01/09, malgré task-194

| `GetMailsByUids` | 01/09 | 08/09 |
|---|---|---|
| Moyenne totale / p95 | 112,0 / 471 ms | **154,2 / 809 ms** |
| exécution SQL | 34,3 ms | 47,7 ms |
| matérialisation | 77,6 ms | 106,5 ms |
| Objets / appel | 231,5 | 236,2 |
| Coût par objet | 335 µs | **451 µs** |
| Appel `emails` p50 / p95 (client) | 159 / 340 | 255 / 571 |

À 1000, la même opération coûte 5,6 fois **moins** qu'au 26/08 (F-194-1 du rapport 1000) ; à 500, elle coûte
38 % **plus** qu'au 01/09. Les deux ne se contredisent pas : le gain de task-194 est un gain de **mémoire**
(allocations ÷13, gen2 ÷8 à l'A/B du matin, médiane quasi inchangée), qui ne se voit qu'une fois le serveur
contraint par le GC et le CPU — c'est le cas à 1000, pas à 500 (0,4 à 0,5 cœur par réplica). À 500, la hausse
du coût par objet (+35 %) est du même ordre que celle de toutes les étapes servies par la base : elle relève
des causes (a)/(b) de F-500-1, pas de task-194. Le levier Postgres reste le scan `References LIKE`
(inchangé, mémoire A/B).

#### F-AUDIT-2 — task-186 : 86 888 traces d'audit écrites en 2 h sur 500 bases, 0 perdue

| Grandeur | Valeur |
|---|---|
| Traces écrites (fenêtre du tir, 500 bases) | **86 888** — MailRead 31 675, AttachmentDownload 15 914, MailSend 11 661, MailArchiveSent 11 661, SmtpConnect 4 212, MailReceive 4 120, MedicalDocumentProcess 4 115, ImapConnect 3 530 |
| Rapport aux requêtes HTTP (470 978) | **0,18 insertion par requête** |
| `Failed to persist audit trace` / `Channel full` / `LOST` (Fatal) | **0 / 0 / 0** |

À 500, le journal est **exhaustif et gratuit en erreurs** ; son coût en latence n'est pas isolable dans ce tir
(les écritures sont asynchrones, hors chemin du médecin, mais partagent le pooler et Postgres). C'est la
contre-épreuve de F-AUDIT-1 du rapport 1000 : la perte de traces est un phénomène de **saturation**, pas un
défaut de fonctionnement nominal. La question ouverte reste le coût Postgres de ces insertions à 1000 — la
mesure qui le tranche est un tir 1000 avec le journal désactivé (variable d'environnement), à protocole égal.

#### F-SEND-1 — L'envoi tient et s'améliore légèrement (task-216/269 confirmées, rien de neuf du lot)

Envoi synchrone 631 → **556 ms** de moyenne, p95 1 008 → 966 ; `acquire_session` 195 → 164 ms, `transmit`
416 → 363, `archive_sent` (hors chemin) 425 → 378, MIME 20 → 30 ms. `AppendToSent` détention médiane 0,487 s en
régime, 0 % > 2 s. `SmtpCommandException` 4 455 sur le tir (NOOP du serveur SMTP du banc, connu). Les
allers-retours d'archivage restent à ~4 par message (F-281-1) : le regroupement de commandes proposé le 01/09
n'a pas encore été fait.

#### F-LOCK-2 — `imap_session` en régime : aucune détention tenue au-dessus de 2 s

Médianes 0,24 à 0,50 s sur toutes les opérations, **0 %** des relevés au-dessus de 2 s (à 1000 : 16,6 % sur
`GetAttachmentStream`, 28,4 % sur `ProcessEmailUid`). `ReadFolder` attend 0,756 s au p95 sur tout le tir
(chauffe comprise), 12,9 acquisitions/s. Rien à instruire à 500.

**Propositions de tasks `/po` (à arbitrer par le PO)** : (1) F-SEARCH-1 — cache d'embedding de requête +
allègement de l'hydratation des résultats ; (2) F-AGE-1 — instrument : part des PJ servies par la base dans le
rapport, ou scission de l'étape 7 dans la grille SLO ; (3) rejeu **iso** de ce tir sur cette base non purgée
dans quelques jours pour séparer l'âge de la base de la charge d'audit (pas une US produit : un tir).
Les propositions du rapport 1000 (F-AUDIT-1, F-SCRATCH-1, F-08P01-1) restent prioritaires.

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 500 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 16674 | 132 | 761 | 4902.1 |
| 500 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 16674 | 6 | 420 | 1333.7 |
| 500 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 16674 | 19 | 175 | 783.5 |
| 500 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 16674 | 3 | 20 | 102.6 |
| 500 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 16687 | 7 | 130 | 633.5 |
| 500 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 16687 | 255 | 571 | 4739.5 |

### Qui porte le coût — palier 500 médecins

- **Arrivée dashboard** (`dashboard`, palier 500) — le p95 de l'étape est porté par l'appel **`folder`** (761 ms de p95, 132 ms de p50, n=16674), qui porte **aussi** le temps serveur de l'étape (4902.1 s, 69 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 500) — le p95 de l'étape est porté par l'appel **`emails`** (571 ms de p95, 255 ms de p50, n=16687), qui porte **aussi** le temps serveur de l'étape (4739.5 s, 88 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 15914 | 225.4 | 83.0 | 467.5 | 622.3 | 1429.8 |
| attachment,palier:500 | 6705 | 284.2 | 344.3 | 523.3 | 714.9 | 1347.8 |
| attachment,palier:transition | 91 | 253.3 | 318.6 | 504.7 | 630.5 | 1190.5 |
| dashboard | 158296 | 103.7 | 10.5 | 400.2 | 462.4 | 2601.3 |
| dashboard,call:coverage,palier:500 | 16674 | 6.2 | 3.3 | 13.0 | 20.5 | 129.5 |
| dashboard,call:coverage,palier:transition | 9 | 8.4 | 7.1 | 12.6 | 16.6 | 20.6 |
| dashboard,call:folder,palier:500 | 16674 | 294.0 | 131.7 | 698.6 | 761.5 | 1682.6 |
| dashboard,call:folder,palier:transition | 9 | 451.5 | 407.7 | 980.4 | 989.5 | 998.6 |
| dashboard,call:folders,palier:500 | 16674 | 47.0 | 19.2 | 154.3 | 175.3 | 498.8 |
| dashboard,call:folders,palier:transition | 9 | 43.6 | 13.9 | 146.2 | 155.6 | 164.9 |
| dashboard,call:today,palier:500 | 16674 | 80.0 | 5.9 | 389.6 | 420.0 | 941.8 |
| dashboard,call:today,palier:transition | 9 | 350.8 | 396.5 | 415.5 | 421.7 | 427.8 |
| dashboard,palier:500 | 66696 | 106.8 | 13.3 | 404.2 | 467.4 | 1682.6 |
| dashboard,palier:transition | 36 | 213.6 | 71.4 | 423.3 | 564.8 | 998.6 |
| mark_read | 31675 | 28.4 | 21.9 | 51.0 | 64.4 | 416.2 |
| mark_read,palier:500 | 13406 | 35.0 | 28.8 | 61.8 | 74.9 | 214.9 |
| mark_read,palier:transition | 153 | 21.4 | 18.1 | 33.7 | 41.1 | 76.0 |
| patient_docs | 85134 | 38.3 | 27.0 | 86.6 | 115.0 | 489.1 |
| patient_docs,palier:500 | 36294 | 46.2 | 31.0 | 108.6 | 139.3 | 459.0 |
| patient_docs,palier:transition | 324 | 31.3 | 16.7 | 77.1 | 98.1 | 179.2 |
| patient_dossier | 5693 | 71.6 | 52.4 | 148.9 | 194.4 | 649.8 |
| patient_dossier,palier:500 | 2432 | 96.0 | 78.5 | 188.2 | 234.7 | 649.8 |
| patient_dossier,palier:transition | 21 | 70.5 | 50.6 | 177.9 | 181.0 | 222.1 |
| patient_opposition | 5693 | 5.9 | 4.3 | 10.2 | 14.0 | 83.5 |
| patient_opposition,palier:500 | 2432 | 7.0 | 5.0 | 12.2 | 18.1 | 53.4 |
| patient_opposition,palier:transition | 21 | 4.1 | 3.3 | 6.8 | 6.8 | 9.2 |
| patient_search | 9272 | 7.2 | 4.7 | 15.1 | 22.4 | 184.7 |
| patient_search,palier:500 | 3956 | 9.8 | 6.0 | 21.7 | 30.3 | 184.7 |
| patient_search,palier:transition | 37 | 5.7 | 4.3 | 8.0 | 15.5 | 34.8 |
| read_content | 39574 | 38.8 | 29.5 | 73.4 | 94.3 | 438.9 |
| read_content,palier:500 | 16694 | 47.9 | 39.3 | 89.1 | 109.6 | 432.5 |
| read_content,palier:transition | 92 | 29.5 | 25.0 | 51.0 | 64.8 | 88.0 |
| read_content_cold | 7598 | 407.3 | 405.7 | 451.0 | 465.4 | 1408.3 |
| read_content_cold,palier:500 | 3231 | 410.0 | 409.2 | 454.7 | 469.3 | 886.0 |
| read_content_cold,palier:transition | 47 | 401.9 | 404.5 | 442.9 | 462.2 | 470.9 |
| read_list | 79148 | 126.0 | 99.8 | 317.4 | 406.9 | 1931.0 |
| read_list,call:emails,palier:500 | 16687 | 284.0 | 254.9 | 482.6 | 571.3 | 1483.7 |
| read_list,call:emails,palier:transition | 57 | 248.1 | 263.4 | 356.3 | 395.9 | 600.1 |
| read_list,call:folder,palier:500 | 16687 | 38.0 | 7.3 | 115.2 | 129.9 | 572.3 |
| read_list,call:folder,palier:transition | 57 | 39.1 | 6.4 | 112.6 | 126.9 | 415.9 |
| read_list,palier:500 | 33374 | 161.0 | 118.1 | 396.1 | 482.8 | 1483.7 |
| read_list,palier:transition | 114 | 143.6 | 112.7 | 345.4 | 363.3 | 600.1 |
| search | 11811 | 582.7 | 493.9 | 730.4 | 850.4 | 31085.5 |
| search,palier:500 | 4964 | 634.5 | 567.3 | 789.5 | 906.5 | 21450.3 |
| search,palier:transition | 56 | 487.5 | 443.1 | 660.8 | 805.7 | 1081.5 |
| send | 11661 | 548.0 | 429.7 | 837.7 | 871.0 | 2385.9 |
| send,palier:500 | 5068 | 551.8 | 439.6 | 853.6 | 890.5 | 1229.4 |
| send,palier:transition | 66 | 537.8 | 430.1 | 804.8 | 809.0 | 872.8 |
| treatment | 3691 | 75.0 | 42.2 | 109.4 | 154.4 | 1556.6 |
| treatment,palier:500 | 1569 | 110.8 | 59.2 | 148.7 | 663.9 | 1476.8 |
| treatment,palier:transition | 7 | 50.8 | 52.7 | 70.8 | 73.9 | 77.0 |
| warmup | 5500 | 363.3 | 132.6 | 809.0 | 2201.2 | 3962.8 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-09-08T18:53:02.572000+00:00 → 2026-09-08T20:54:05.549000+00:00 (7263 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-201927.csv`) | ✅ 195770 points |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-10448` | 0.42 | 3 | 12 | 0.011 | 3.09 |
| `DESKTOP-DEV-X2C-43044` | 0.48 | 3 | 12 | 0.011 | 2.60 |
| `DESKTOP-DEV-X2C-49216` | 0.41 | 4 | 19 | 0.012 | 4.35 |
| `DESKTOP-DEV-X2C-50208` | 0.46 | 2 | 11 | 0.008 | 2.93 |
| `DESKTOP-DEV-X2C-7276` | 0.50 | 6 | 13 | 0.009 | 3.65 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur (échantillonneur)

| Cible | CPU moy (cœurs) | CPU max (cœurs) | Mém max (Mo) |
|---|---|---|---|
| `com.docker.backend#34056` | 1.38 | 4.42 | 1393 |
| `com.docker.backend#35624` | 0.00 | 0.30 | 39 |
| `dcp#12760` | 0.00 | 0.00 | 12 |
| `dcp#18040` | 0.00 | 0.05 | 12 |
| `dcp#20636` | 0.00 | 0.00 | 12 |
| `dcp#30600` | 0.00 | 0.00 | 12 |
| `dcp#33096` | 0.00 | 0.00 | 12 |
| `dcp#46432` | 0.00 | 0.33 | 42 |
| `dcp#47052` | 0.00 | 0.10 | 11 |
| `dcp#47728` | 0.00 | 0.00 | 12 |
| `dcp#48432` | 0.00 | 0.05 | 12 |
| `dcp#6680` | 0.53 | 2.22 | 1208 |
| `k6#38736` | 0.14 | 2.36 | 1131 |
| `mss.mail.api#10448` | 0.21 | 2.26 | 2436 |
| `mss.mail.api#43044` | 0.23 | 2.01 | 2460 |
| `mss.mail.api#49216` | 0.22 | 2.49 | 2646 |
| `mss.mail.api#50208` | 0.20 | 2.59 | 2417 |
| `mss.mail.api#7276` | 0.22 | 2.11 | 2408 |
| `vmmemWSL#33512` | 4.52 | 12.60 | 38246 |
| `loadtest-otel-collector-erfrwjkp` | 0.03 | 0.20 | 127 |
| `loadtest-pgbouncer-bywthhgq` | 0.31 | 0.93 | 29 |
| `mss-mail-grafana-b6152948` | 0.01 | 0.20 | 173 |
| `mss-mail-prometheus-b6152948` | 0.02 | 0.18 | 406 |
| `mss-mail-rabbitmq-bqnqhrzh` | 0.01 | 0.20 | 180 |
| `mss-mail-redis-b6152948` | 0.13 | 1.11 | 2029 |
| `mss-mail-seq-b6152948` | 0.01 | 0.17 | 164 |
| `postgres-pgvector` | 1.25 | 6.50 | 11438 |

- **Hôte** : CPU 45.9 % moy / 99.0 % max sur 24 cœurs logiques, file processeur max 46
  > ⚠️ Ce compteur `_Total` est **contaminé** sur le poste de banc (SonarQube, Ollama, Keycloak, SQL Server, Mongo tournent en permanence). Il borne le reste ; il ne désigne jamais une cause. Seuls le **par processus** et le **par conteneur** sont opposables.
- **PgBouncer** : cl_active max 4284, cl_waiting max 5, cl_waiting_maintenance max 0, cl_waiting_practitioner max 5, count max 1002, maxwait_maintenance_ms max 0, maxwait_ms max 73, maxwait_practitioner_ms max 73, sv_active max 16, sv_idle max 706
- **Backends Postgres** : practitioner_databases max 876, total max 882

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 980.0 | 1450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2312.5 | 1450 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 450.0 | 1448 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 4278.8 | 1445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 579.2 | 1449 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 1450.0 | 1445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 400.0 | 1445 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 885.2 | 1449 |
| `api/v{version:apiVersion}/Mail/sendmail` | 1862.5 | 1431 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 70.6 | 1442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 431.2 | 1442 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 39.0 | 1442 |
| `api/v{version:apiVersion}/Search/semantic` | 3375.0 | 1439 |
| `api/v{version:apiVersion}/Sync/coverage` | 28.1 | 1449 |

- **p95 client global (k6)** : 474.9 ms
- **p95 serveur le plus élevé** : 4278.8 ms
- **Écart** : -3803.9 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Mails traités /s | 7.49 |
| Documents CDA /s | 7.47 |
| Durée traitement CDA (s, p95) | 0.40 |
| Événements de session IMAP /s | 13.35 |
| Recherches (s, p95) | 3.375 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `EnrichPersistMail` | 8.2 | 60.6 | 475 | 0.1 (0.2 %), p95 10 | 51.7 (85.4 %), p95 475 | 8.8 (14.5 %), p95 48 |
| `GetMail` | 11.3 | 33.7 | 216 | 2.1 (6.1 %), p95 45 | 28.4 (84.3 %), p95 200 | 3.2 (9.5 %), p95 10 |
| `GetMailsByUids` | 14.7 | 154.2 | 809 | 0.1 (0.0 %), p95 5 | 47.7 (30.9 %), p95 248 | 106.5 (69.1 %), p95 674 |

- **`EnrichPersistMail`** — sur 60.6 ms en moyenne (8.2 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 51.7 ms exécution SQL, 8.8 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMail`** — sur 33.7 ms en moyenne (11.3 requête(s) SQL par appel) : 2.1 ms attente d'une connexion, 28.4 ms exécution SQL, 3.2 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 154.2 ms en moyenne (14.7 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 47.7 ms exécution SQL, 106.5 ms le reste (matérialisation, DTO). **Poste dominant : le reste (matérialisation, DTO).**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 10.0 | 3.2 | 320.8 | 0.9 | 1.3 | 0.9 | 2.4 | non relevé | 0.0 | 0.9 | 2.3 | 0.1 | 0.9 | non relevé | 0.2 |
| `GetMailsByUids` | 236.2 | 106.5 | 450.8 | 21.2 | 32.3 | 21.2 | 34.4 | 21.2 | 0.0 | 21.2 | 6.7 | 0.0 | 21.1 | 51.0 | 6.0 |

- **`GetMail`** — sur 3.2 ms de matérialisation, l'appel a construit 10.0 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.4 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 2.3 résultats de biologie, 0.1 éléments de synthèse, 0.9 corps de messages, 0.2 références de doublon. **Famille dominante : pièces jointes.**
  - Coût par objet : **320.8 µs**.

- **`GetMailsByUids`** — sur 106.5 ms de matérialisation, l'appel a construit 236.2 objets, dont 21.2 messages, 32.3 étiquettes, 21.2 destinataires, 34.4 pièces jointes, 21.2 identifiants enrichis, 0.0 acquittements, 21.2 documents médicaux, 6.7 résultats de biologie, 0.0 éléments de synthèse, 21.1 corps de messages, 51.0 objets de fil, 6.0 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **450.8 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **490.7 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

| Messages/requête | Moy. par message (ms) | p95 (ms) | fetch IMAP | extraction XDM | parsing CDA | écritures base | le reste (DTO, notifications) |
|---|---|---|---|---|---|---|---|
| 5.1 | 243.8 | 2350 | 135.0 (55.4 %), p95 475 | 22.1 (9.0 %), p95 235 | 13.8 (5.7 %), p95 235 | 59.4 (24.4 %), p95 475 | 13.4 (5.5 %), p95 73 |

- **Enrichir un message** — sur 243.8 ms en moyenne (5.1 message(s) par requête) : 135.0 ms fetch IMAP, 22.1 ms extraction XDM, 13.8 ms parsing CDA, 59.4 ms écritures base, 13.4 ms le reste (DTO, notifications). **Poste dominant : fetch IMAP.**
  - 🔁 **inf aller(s)-retour(s) IMAP par message enrichi** — inf `close_folder`, inf `fetch_bodystructure`, inf `fetch_whole_message`, inf `open_folder`, inf `resolve_folder`. Un `fetch_body_part` est emis **par partie** (texte, HTML, archive) ; `fetch_body_structure` couvre tout le sous-lot. **C'est ce nombre, et non une duree, qui decide de regrouper les commandes** : multiplie par la latence aller-retour du lien, il dit quelle part du fetch est de la latence — et donc ce qu'un regroupement peut esperer gagner.
  - ℹ️ **Empreinte sémantique : 645.2 ms** — **hors du chemin synchrone**, donc **non comptée** ci-dessus. Elle s'exécute dans un consommateur déclenché par un `Publish` que le producteur n'attend pas : `enrich/sync` ne paie pas cette latence, mais la plateforme la paie en ressources.

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total. `le reste` est ce que le total ne doit à aucune phase nommée : mapping DTO, assainissement HTML, notifications, audit — s'il domine, c'est **lui** que la prochaine US découpe.

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 556.3 | 966 | 0.0 (0.0 %), p95 5 | 29.6 (5.3 %), p95 80 | 163.9 (29.5 %), p95 472 | 362.6 (65.2 %), p95 491 | 377.6 (67.9 %), p95 814 | 0.2 (0.0 %), p95 5 |

- **Envoyer un message** — sur 556.3 ms en moyenne : 0.0 ms garde d'opposition, 29.6 ms construction MIME, 163.9 ms obtention de session SMTP, 362.6 ms transmission + acquittement, 377.6 ms archivage Sent, 0.2 ms le reste. **Poste dominant : archivage Sent.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `distributed_fetch` | — | — | 0.00 |
| `imap_session` | 0.453 | 2.012 | 28.13 |
| `in_process_fetch` | — | — | 0.00 |
| `smtp_session` | 0.054 | 1.862 | 3.04 |

ⓘ **Non exercé sur la fenêtre : `distributed_fetch`, `in_process_fetch`** — 0 acquisition/s. Cellules de latence vides faute d'observation, non faute d'instrumentation.

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.005 | 1.225 | 2.350 | 0.688 | 3.02 |
| `EnrichEmails` | 0.016 | 0.475 | — | 0.475 | 8.26 |
| `GetAttachmentStream` | 0.487 | 1.975 | 2.425 | 0.825 | 2.22 |
| `GetEmailContent` | 0.079 | 0.863 | — | 0.863 | 2.09 |
| `GetFolders` | 0.005 | 0.983 | 0.988 | 0.362 | 1.78 |
| `ProcessEmailUid` | — | — | — | — | 0.00 |
| `ReadFolder` | 0.756 | 2.312 | 2.425 | 0.487 | 12.93 |
| `UpdateFlag` | 0.450 | 0.494 | — | 0.494 | 7.45 |

ⓘ **Non exercé sur la fenêtre : `ProcessEmailUid`** — 0 acquisition/s. Cellules de latence vides faute d'observation, non faute d'instrumentation.

#### Détention en exploitation, **fenêtre de régime** — palier 500

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.492 | 0.0 % |
| `EnrichEmails` | **0.275** | 0.437 | 0.475 | 0.0 % |
| `GetAttachmentStream` | **0.496** | 0.545 | 0.642 | 0.0 % |
| `GetEmailContent` | **0.487** | 0.490 | 0.497 | 0.0 % |
| `GetFolders` | **0.241** | 0.241 | 0.242 | 0.0 % |
| `ReadFolder` | **0.451** | 0.456 | 0.461 | 0.0 % |
| `UpdateFlag` | **0.486** | 0.487 | 0.489 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 28.13 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.005 s au p95, contre 0.756 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

> ⓘ **PgBouncer — transitoire d'attente, écarté du verdict.** 66 échantillon(s) sur 1444 portent une attente cliente non nulle (4.6 %, pointe à 5), sous le seuil de présence soutenue de 25 %. Ce profil est celui d'une **ouverture de palier**, pas d'un pooler qui n'absorbe plus — il ne désigne donc pas de facteur limitant. À surveiller tout de même : sur la campagne du 2026-07-29, cette pointe croît avec la charge.

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| conteneur `postgres-pgvector` (CPU) | 6.50 cœurs | 24 cœurs | 27.1 % | 0.0 % — transitoire |
| processus `mss.mail.api#50208` (CPU) | 2.59 cœurs | 24 cœurs | 10.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#49216` (CPU) | 2.49 cœurs | 24 cœurs | 10.4 % | 0.0 % — transitoire |
| processus `k6#38736` (CPU) | 2.36 cœurs | 24 cœurs | 9.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#10448` (CPU) | 2.26 cœurs | 24 cœurs | 9.4 % | 0.0 % — transitoire |
| processus `mss.mail.api#7276` (CPU) | 2.11 cœurs | 24 cœurs | 8.8 % | 0.0 % — transitoire |
| processus `mss.mail.api#43044` (CPU) | 2.01 cœurs | 24 cœurs | 8.4 % | 0.0 % — transitoire |
| file ThreadPool du réplica `DESKTOP-DEV-X2C-7276` | 6.00 éléments | 100 éléments | 6.0 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (conteneur `postgres-pgvector` (CPU)) monte à 27.1 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 114768 — dont **114768** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Attendu par boîte** : 247 (complétude relative au périmètre du scénario)
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-500-lot288-194-20260908-225405.jsonl` (tous les `Error`/`Fatal`
> hors middleware HTTP, + 500 `Warning`). Comptages exhaustifs sur la fenêtre 18:53:00Z → 20:54:06Z par l'API Seq.

| Requête | Résultat | Lecture |
|---|---|---|
| `@Level in ['Error','Fatal']` | **33** (0 Fatal) | 9 × `08P01` résiduels en chauffe (×3 lignes : middleware, `Result-mapped`, `Unexpected error getting folders`), 6 × `CONFLIT METIER` contact (apport perdu) |
| `@Level = 'Warning'` | 18 236 | certificat non approuvé 7 742 (banc), `Missing values` 7 132 (bénin), `Session expired` 2 925 (nominal), RPPS invalide 311 (corpus), biologie sans nom 52, CDA invalide 25, conflit contact rejoué 6 |
| `Failed to parse entity headers` | **0** | pas de régression IMAP |
| `[CdaParsingService] Parsing completed` | **4 120** | = 4 115 traces `MedicalDocumentProcess` ; la réserve analysée était déjà hydratée par le tir 1000 (chauffe 100 % en quelques minutes) |
| `maximum input length is 8192 tokens` | **0** | task-196 tenue |
| `StatusCode = 429` | **0** | limiteur jamais atteint |
| `StatusCode = 500` | 9 | tous avant 21h03, résidu du tir 1000 |
| `keep-alive NOOP failed` | 2 222 | serveur SMTP du banc, connu |
| `Failed to persist audit trace` / `Channel full` / `LOST` | **0 / 0 / 0** | F-AUDIT-2 |
| `Error extracting IHE-XDM` | 0 | garde scratch : aucune disparition datée |
| `Embedding failed` / `[Tagging] Failed` | 0 / 0 | les 5 366 / 2 715 du tir 1000 étaient donc bien des effets de la saturation (08P01 sur la lecture), pas une famille propre |

**Findings Seq.** (1) RAS hors bruit de banc : un tir à 33 erreurs pour 470 978 requêtes. (2) Les deux
familles « à instruire » du rapport 1000 (`Embedding failed`, `[Tagging] Failed`) sont à **0** ici : elles
appartiennent à la saturation, ce qui clôt leur instruction. (3) Les 6 conflits de contact pour 11 661 envois
(0,05 %) sont dans l'ordre de grandeur du 23/08 (0,1 %).
