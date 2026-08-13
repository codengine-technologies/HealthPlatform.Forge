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
