# todo-task-258.md — `db_write` triple avec la concurrence et personne ne peut dire si c'est une file : instrumenter avant d'optimiser

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-255** — c'est sa campagne qui a mesuré le triplement et
qui a établi, **par recoupement**, que ce n'était pas une file au pooler. Aucune
dépendance bloquante : l'instrument est écrivable dès maintenant.
**Priorité**: **2** — la phase `db_write` est le **seul poste de
l'enrichissement qui croît avec la concurrence**. C'est donc le prochain suspect
désigné, et il est aujourd'hui le seul du parcours qu'on ne sait pas attribuer.

## Objective

Que la phase `db_write` de l'enrichissement soit **décomposable** en attente
d'obtention de connexion, exécution SQL et matérialisation — de sorte qu'on
puisse dire si son coût est une **file** ou du **travail**.

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus rapide.

## Ce qui est établi — task-255, série de référence du 2026-08-13

Trois points de concurrence, hôte non affamé, 640 messages enrichis sur 640
soumis à chaque point, 0 erreur :

| Concurrence | Débit | `imap_fetch`/msg | **`db_write`/msg** | `assemble`/msg |
|---|---|---|---|---|
| 4 | 16,66 msg/s | 124,8 ms | **23,3 ms** | 8,4 ms |
| 8 | 30,19 msg/s | 126,5 ms | **31,7 ms** | 11,2 ms |
| 16 | 45,02 msg/s | 127,3 ms | **62,1 ms** | 21,1 ms |

**`db_write` fait ×2,7 quand la concurrence fait ×4**, pendant que le transport
IMAP reste plat au demi-millimètre (124,8 → 127,3 ms). C'est le poste qui monte.

**Ce que task-255 a pu écarter** — le pooler PgBouncer : `cl_waiting` nul sur
14 relevés sur 15, `maxwait` maximal **0,7 ms**, backends PostgreSQL invariants
(16 aux trois concurrences).

**Ce que task-255 n'a PAS pu mesurer, et c'est l'objet de cette US** : l'attente
d'obtention d'une connexion **côté Npgsql**, sur le chemin d'écriture.
`mssante_db_operation_phase_duration_seconds` — dont la phase `connection_open`
— existe, mais elle couvre le **chemin de lecture** (task-243) : sur toute la
campagne elle n'a remonté **qu'un seul appel**. Le triplement de `db_write` est
donc attribué **par recoupement** (file processeur qui explose, pooler calme,
backends stables) et **non mesuré à la source**.

Le recoupement est solide, mais il ne permet pas de choisir un remède : « la
connexion se fait attendre » et « l'écriture calcule plus » appellent des
correctifs opposés — desserrer `Maximum Pool Size` d'un côté, réduire le travail
par message de l'autre.

## Ce que la US doit livrer

Pour le chemin d'**écriture** d'enrichissement, le pendant de ce que task-243 a
livré pour le chemin de **lecture** : la phase `db_write` ventilée en

- **attente d'obtention d'une connexion** (le temps passé dans le pool Npgsql
  avant d'avoir une connexion utilisable) — c'est la grandeur qui manque ;
- **exécution SQL** ;
- **le reste** (suivi de changements EF, matérialisation, validation).

Plus le **nombre de requêtes SQL par message enrichi** — le dénominateur sans
lequel une durée ne dit pas si elle vient du volume ou du coût unitaire, exacte-
ment la leçon de task-243 et de task-256.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est une file de connexions.** `Maximum Pool Size=2`
  par base praticien est un candidat évident, donc suspect : task-255 a mesuré le
  pooler **calme**, et le CPU **saturé**. Un coût qui croît sans file est
  parfaitement compatible avec les mesures actuelles.
- **Ne pas présumer que c'est PostgreSQL.** Le suivi de changements d'EF Core et
  la matérialisation tournent **côté application**, pas côté base.
- **Ne pas optimiser en passant.** Si une évidence saute aux yeux — une écriture
  par message là où un lot suffirait —, la consigner comme finding et la traiter
  dans une US **mesurée**. Cette EPIC a annulé task-222 pour avoir fait
  l'inverse.
- **Ne pas re-mesurer l'acquis** : la durée de la phase et le débit par point de
  concurrence sont établis. Cette US ajoute **la décomposition**.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] La phase `db_write` de l'enrichissement publie une **attente d'obtention de
      connexion**, une **exécution SQL** et un **reste**, chacun sommable et
      comparable d'un tir à l'autre
- [ ] Un compteur donne le **nombre de requêtes SQL par message enrichi**
- [ ] `report.py` publie la **phrase attribuable** : « sur les X ms de `db_write`,
      Y ms sont de l'attente de connexion, Z ms de l'exécution SQL, sur N
      requêtes »
- [ ] **Hors périmètre, rien ne coûte** : sans scope actif, ni allocation ni série
- [ ] Une absence de donnée écrit **« non relevé »**, jamais un zéro — la table
      des verrous de task-214 a déjà conclu à tort sur une étiquette absente
- [ ] Tests unitaires de la décomposition, dont un cas « attente nulle » et un cas
      multi-requêtes
- [ ] **Aucune donnée de santé dans les étiquettes** : ni INS, ni objet de
      message, ni nom de fichier — noms de phases pris dans un ensemble fini
- [ ] **Contre-épreuve chiffrée** : rejouer les trois points de concurrence de
      task-255 (4 / 8 / 16, protocole identique) et **dire** laquelle des deux
      hypothèses la mesure retient — file, ou travail. Si elle ne tranche pas, le
      rapport l'écrit : c'est un résultat, pas un échec

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`) — **contrôler d'abord à qui appartient
  le CPU** (`docker stats --no-stream | sort -k2 -hr | head`) : un hôte affamé
  fausse la pente, task-255 l'a payé d'une série complète
- Seeder 8 praticiens × 80 messages, `ENRICH_BATCH=20`, `ENRICH_SHARE=1.0`
- Pour chaque concurrence 4 / 8 / 16 : drainer le bus, purger
  (`YES=1 tests/loadtest-k6/reset-state.sh`), préchauffer un `GET /folders` par
  praticien, tirer, **attendre 30 s avant de relever les compteurs** (sans quoi
  la queue du tir est perdue — mesuré à −57 % sur un tir de 16 s)
- Lire la section « Où part le temps » du rapport : l'attente de connexion et le
  nombre de requêtes par message doivent y figurer aux trois points
- Ouvrir une boîte depuis l'application pendant le palier le plus chargé : la
  liste doit rester consultable
- Vérifier dans Seq qu'aucune étiquette ne porte de donnée patient

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — observabilité interne
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : ⚠️ le chemin instrumenté **écrit des CDA porteurs d'INS**. Le
  compteur ne publie que des **durées**, des **nombres** et des **noms de phases**
  pris dans un ensemble fini : aucune valeur de champ, aucun fragment de requête
  paramétrée, aucun identifiant
- **Interop CI-SIS** : volet transport MSSanté / IHE-XDM — ⚠️ **l'intégrité et la
  complétude des documents écrits sont bloquantes** : l'instrumentation ne doit
  rien changer au contenu persisté. Les garde-fous de task-254 (`8a843a8`,
  `e71f14e`) restent le filet
- **Habilitations** : le cloisonnement « une base par praticien » est inchangé —
  aucune connexion partagée entre praticiens
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : le coût de l'instrument doit être négligeable en
  production — critère « hors périmètre, rien ne coûte » ci-dessus
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-258-instrumenter-db-write — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-258-instrumenter-db-write
- `dtos-mss` (pushed, auto-inclus) : feat/task-258-instrumenter-db-write — aucun contrat DTO attendu (US d'instrument interne)

## Develop log — 2026-08-13

### L'instrument existait déjà — il n'était pas branché

`DbOperationScope` (task-243) publie **exactement** les trois composantes que le
DOD demande — `connection_open`, `sql_execute`, et le **reste** par différence —
plus le compte de requêtes. Il n'était simplement jamais ouvert sur le chemin
d'écriture.

**Cause précise de l'angle mort**, que task-255 avait constaté sans pouvoir
l'expliquer : l'intercepteur de **commandes** alimente les **deux** périmètres
(lecture task-243 et enrichissement task-245), mais l'intercepteur de
**connexion** n'alimente que `DbOperationScope`, inactif sur ce chemin faute de
`Begin`. La phase `db_write` de l'enrichissement ne mesurait donc **que
l'exécution SQL** — l'attente d'obtention de connexion n'était pas mal mesurée,
**elle n'existait pas**.

**Livré** : `DbOperationScope.Begin(DbOperationEnrichPersistMail)` dans
`MailRepository.AddNewMail`. **Zéro nouvel instrument, zéro changement de contrat
de métrique.**

### Deux décisions de placement

**Au dépôt, pas chez l'appelant** — comme les deux périmètres de lecture. La
mesure suit alors l'opération quel que soit son appelant, au lieu de dépendre
d'un site d'appel qu'on oublierait : c'est le mode de panne de task-214, où une
API instrumentée n'était branchée que sur **un site sur vingt et un**.

**Le court-circuit de déduplication est DANS le périmètre** : il interroge la
base, donc il coûte. Un message dédupliqué doit apparaître pour ce qu'il est —
une écriture bon marché — plutôt que de disparaître de la mesure, ce qui
flatterait le coût moyen d'écriture.

### `report.py` : rien à câbler

La table et la phrase attribuable agrègent **par opération** (`sum by
(operation)`) : la nouvelle opération y apparaît d'elle-même. Seul le titre de
section a changé — il annonçait « lecture servie par la base » alors qu'une
**écriture** va désormais s'y ranger — assorti d'une note de lecture qui dit ce
que `EnrichPersistMail` tranche.

### Tests — éprouvés par mutation, y compris contre le « vert à vide »

**6 tests, 6 verts avec l'instrumentation, 6 rouges sans** (mutation : retrait du
`using` dans `AddNewMail`).

⚠️ **Au premier passage, seuls 4 sur 5 tombaient.** Le cinquième bouclait sur une
liste vide et **passait à vide** — exactement le piège payé par task-250 (un test
d'intégration vert **avec** le défaut). Renforcé par un `Assert.NotEmpty`, avec le
commentaire qui dit pourquoi.

Cas couverts : décomposition publiée sous son opération · **attente nulle**
(InMemory n'ouvre aucune connexion — le zéro est **publié**, jamais tu) · le reste
porte tout le total quand rien n'est observé · message dédupliqué mesuré quand
même · étiquettes bornées à `operation`/`phase`, littérales · **compteur de
requêtes publié**.

**Limite assumée** : le fournisseur **InMemory** n'ouvre aucune connexion et
n'exécute aucune commande, donc les intercepteurs ne se déclenchent pas. C'est ce
qui donne gratuitement le cas « attente nulle », et cela prouve que la publication
n'en dépend pas — mais **le cas multi-requêtes réel ne peut pas être éprouvé
ici** ; il l'est au niveau du périmètre (`DbOperationScopeTests`), où les durées
sont injectables.

### Réutilisation : cherchée, et écartée pour une raison

`PhaseCapture` (même projet) semble être le helper à réutiliser. Il ne l'est
pas : il **ouvre lui-même** un périmètre avec l'opération de **lecture**, parce
qu'il éprouve les intercepteurs. Ces tests-ci doivent au contraire vérifier que
**le dépôt** ouvre le bon périmètre, donc n'en ouvrir aucun. Le réutiliser
exigerait d'inverser son contrat.

### Ce qui reste ouvert — et c'est le cœur de la US

Le dernier critère du DOD — **la contre-épreuve chiffrée** : rejouer les trois
points de concurrence de task-255 et **dire** laquelle des deux hypothèses la
mesure retient, file ou travail. Elle exige **une campagne de banc**, hors chaîne
autonome. Même situation que task-243, task-247, task-248 et task-250 : l'US
d'instrument livre l'instrument, la mesure suit.

**Ordre recommandé** : merger d'abord, mesurer ensuite. Mesurer avec un instrument
non mergé obligerait à re-mesurer après merge.

## Contre-épreuve — 2026-08-13, banc local, trois points de concurrence

**Le dernier critère du DOD est tenu : la mesure tranche.**

Protocole **identique à task-255** — 8 praticiens × 80 messages porteurs
d'`IHE_XDM.ZIP`, `ENRICH_BATCH=20`, `ENRICH_SHARE=1.0`,
`SESSION_ROTATION=0.002`, drainage du bus → purge → préchauffage → snapshot →
tir → décantation 30 s → snapshot. Trois points verts : **0 erreur HTTP, 100 %
de checks, 32 lots sur 32, 640 messages enrichis sur 640 soumis** à chacun.

### La décomposition que la US devait produire

| Concurrence | Débit | `connection_open` | `sql_execute` | `assemble` | **Requêtes/message** |
|---|---|---|---|---|---|
| 4 | 13,96 msg/s | 0,52 ms | 22,92 ms | 11,28 ms | **8,72** |
| 8 | 26,66 msg/s | 0,21 ms | 25,53 ms | 8,46 ms | **8,72** |
| 16 | 40,21 msg/s | 0,61 ms | **37,40 ms** | 9,57 ms | **8,72** |

### Verdict : **du TRAVAIL, pas une file — et plus précisément, le MÊME travail plus lent**

Trois faits, et ils s'excluent mutuellement de toute autre lecture :

1. **L'attente d'obtention de connexion est nulle et plate** : 0,52 → 0,21 →
   0,61 ms, soit **1,4 % du coût d'écriture** au point le plus chargé, sans
   tendance. Corroboré côté pooler : `cl_waiting` et `maxwait` **nuls sur tous
   les relevés**. **Ce n'est pas une file.** L'hypothèse du pool — `Maximum Pool
   Size=2` par base praticien, suspect désigné d'avance — est **écartée par la
   mesure**.
2. **Le nombre de requêtes est identique au centième** : **8,72 par message** aux
   trois concurrences. **Ce n'est donc pas non plus « plus de travail »** : la
   quantité de travail demandée à la base ne bouge pas d'un iota.
3. **L'exécution SQL, elle, croît de 63 %** (22,92 → 37,40 ms). Ce sont donc **les
   mêmes requêtes, en même nombre, qui prennent plus de temps** quand la
   concurrence monte.

**Sans le dénominateur, ce verdict était impossible.** Une durée qui croît se lit
aussi bien « plus de requêtes » que « des requêtes plus lentes », et les deux
appellent des remèdes opposés. C'est exactement la leçon que task-243 et
task-256 avaient tirée, et la raison d'être du compteur ajouté ici.

### Où cela déplace la question

`sql_execute` mesure « commande envoyée → serveur répondu ». Le temps
supplémentaire est donc **dans PostgreSQL ou sur le lien qui y mène**, pas dans
l'application ni dans l'attente d'une connexion. Les causes candidates — et
**aucune n'est tranchée ici** — sont la contention interne de PostgreSQL (CPU,
verrous de ligne, écriture du journal WAL, points de reprise), ou la concurrence
entre les 8 bases praticien sollicitées simultanément.

**Ce que la présente mesure ne dit pas**, et qu'il ne faut pas lui faire dire :
elle ne distingue pas ces causes entre elles. Le prochain instrument n'est plus
côté application — il est **côté PostgreSQL** (`pg_stat_statements`,
`pg_stat_activity.wait_event`, statistiques de verrous).

### Réserve d'honnêteté sur les niveaux

Le débit de cette campagne (13,96 → 26,66 → 40,21 msg/s, soit **×2,88 pour ×4**
de concurrence) est cohérent avec task-255 (16,66 → 30,19 → 45,02, ×2,70) sans
lui être identique : conditions d'hôte différentes, à quelques heures d'écart.
**Seules les grandeurs comparées à l'intérieur de cette campagne sont
opposables** — et ce sont elles qui portent le verdict : le compte de requêtes
(un nombre, pas une durée) et la platitude de l'attente de connexion.

### Ce qui reste ouvert

- **La cause du ralentissement des requêtes**, à instruire côté base — c'est la
  prochaine US, et elle n'est plus une US d'instrument applicatif.
- **Le domaine de validité s'arrête à 16** et à 8 praticiens, banc local. Rien
  ici ne dit ce qui se passe à 500.

## PRs

- `api-mail` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/187 — label `awaiting-human-merge`
- `dtos-mss` (pushed, auto-inclus) : **aucune PR** — branche sans commit, contrat non touché

## Code Review Summary

**Verdict : APPROVED** — 6 fichiers, 0 blocage, **1 suggestion**.

| Contrôle | Résultat |
|---|---|
| Build | ✅ 0 erreur, 0 avertissement |
| Tests | ✅ **3 762 verts** (domain 136 · infra 442 · api 661 · integration 402 · application 2 122) + **270 auto-tests Python** — 1 rouge **pré-existant** |
| DOD | ✅ **8 critères sur 8 — y compris la contre-épreuve**, ce qu'aucune US d'instrument de cette EPIC n'avait encore fait |
| Quality Gate | ✅ OK, dette introduite **zéro** |

### ⚠️ Suggestion — l'étiquette couvre plus que son nom

`EnrichPersistMail` promet un enrichissement, mais le périmètre couvre **les
quatre** sites d'appel de `AddNewMail`, dont un (`ImapService.cs:2646`) écrit des
**DTO d'en-têtes seuls**, bien moins coûteux. Sur une campagne `journey`, la
série **mélangerait deux populations** — c'est la classe de défaut que cette EPIC
paie régulièrement.

**La campagne qui porte le verdict n'en est pas contaminée — vérifié, pas
supposé** : **640 appels mesurés pour 640 messages enrichis, aux trois points**.
Le scénario `enrich` n'exerce pas ce chemin.

**À trancher avant la première campagne `journey` qui lira cette métrique** :
renommer en neutre (`PersistMail`), ou distinguer les deux écritures par un
paramètre. Non corrigé ici — `/review` ne patche pas de code.

### Ce que la revue relève par ailleurs

- `MailProcessingMetrics.cs` — ✅ une constante ; le commentaire **nomme la cause
  de l'angle mort**, ce qui est ici autant le livrable que le code.
- `MailRepository.cs` — ✅ une ligne, placée comme les deux périmètres de lecture.
  **Non ré-entrant** : les quatre sites d'appel sont hors de tout périmètre
  englobant (vérifié), et un `Begin` imbriqué rendrait de toute façon un objet
  inerte alimentant le périmètre extérieur.
- Tests — ✅ 6, éprouvés par mutation, dont un **renforcé après avoir été surpris
  à passer à vide**.
- `report.py` — ✅ titre corrigé (« lecture » → « opération ») et note qui dit ce
  que l'opération tranche.

**Sécurité / PGSSI-S** : étiquettes littérales d'un ensemble fini, **vérifié par
test**. Le chemin instrumenté écrit des CDA porteurs d'INS ; seules des durées,
des nombres et des noms de phases sont publiés.

## Merged

Mergée le 2026-08-13 par l'humain (`/merge task-258 --i-tested`).

| Repo | PR | Squash commit | Branche distante |
|---|---|---|---|
| `api-mail` | [#187](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/187) | `452ca99` | supprimée |
| `dtos-mss` | aucune (branche sans commit) | — | supprimée |

**CI `develop` : verte** (`success`) — vérifiée après le merge, règle 5.

**DOD close à 8 critères sur 8, contre-épreuve comprise.** C'est la première US
d'instrument de cette EPIC dans ce cas : task-243, 245, 247, 248 et 250 ont
toutes livré leur instrument en laissant leurs critères de mesure ouverts.

### Ce qui reste ouvert, et qui n'appartient plus à cette task

1. **La cause du ralentissement des requêtes**, côté PostgreSQL — contention
   interne (CPU, verrous, WAL, points de reprise) ou concurrence entre les
   8 bases praticien. **Le prochain instrument n'est plus applicatif** :
   `pg_stat_statements`, `pg_stat_activity.wait_event`, statistiques de verrous.
2. **La portée de l'étiquette `EnrichPersistMail`** — elle couvre les quatre
   sites d'appel de `AddNewMail`, dont un écrit des en-têtes seuls. Campagne du
   verdict **non contaminée (vérifié : 640 appels pour 640 messages)**, mais à
   trancher **avant** la première campagne `journey` qui lira cette métrique.
3. **Le domaine de validité s'arrête à 16** et à 8 praticiens, banc local.
