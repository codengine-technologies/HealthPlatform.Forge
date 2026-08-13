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
