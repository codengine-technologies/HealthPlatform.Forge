# todo-task-255.md — Doubler la concurrence ne rend que 4 % de débit d'enrichissement : nommer ce qui sérialise

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-254** — c'est sa campagne qui a mesuré ce plateau, et
c'est elle qui a **écarté le fetch IMAP** comme cause. Son instrument
(`mssante_mail_server_solicitations_total`) et sa décomposition de phases sont
les outils de départ de celle-ci. La US n'attend rien d'autre : la première
moitié (établir la cause) est faisable dès maintenant.
**Priorité**: **2** — le coût **par message** a baissé de 43 % (task-254) sans
que le **débit** bouge. Tant que ce plateau tient, ajouter des praticiens
n'ajoute pas de capacité, et c'est la grandeur qui décide du dimensionnement.

## Objective

Nommer la ressource qui **sérialise** l'enrichissement — celle qui fait qu'un
doublement de concurrence ne rend que 4 % de débit — puis seulement décider du
remède.

⚠️ **US en deux temps, et l'ordre n'est pas négociable** : mesurer, puis
corriger. Cette EPIC a annulé une US applicative écrite sur une cause plausible
et fausse (task-222), et task-254 vient de **disculper** le suspect qu'on aurait
corrigé d'abord.

## Ce qui est établi

**Le plateau, mesuré au banc local le 2026-08-10** (8 praticiens, latence
Toxiproxy, groupement de fetch actif, pools Postgres préchauffés, 6 lots
aboutis sur 8 aux deux points) :

| Concurrence | Débit | `imap_fetch` par message | Sollicitations serveur/message |
|---|---|---|---|
| 4 | **2,66 msg/s** | 131,4 ms | 1,50 |
| 8 | **2,77 msg/s** | 130,1 ms | 1,80 |

**Doubler la concurrence rend +4 %.**

**Ce qui est déjà écarté — et c'est le principal apport de task-254** : ce n'est
**pas** le fetch IMAP. Deux raisons indépendantes :

1. Le coût de fetch par message **ne se dégrade pas** avec la concurrence
   (131 → 130 ms). Une ressource qui sature fait monter le coût de ceux qui
   l'attendent ; celui-ci est plat.
2. task-254 a **retiré un aller-retour sur deux** (3,00 → 1,50 sollicitation par
   message) et fait baisser `imap_fetch` de **43 %** — sans que le débit bouge.
   Si le fetch avait été le facteur limitant, ce gain se serait vu au débit.

**L'état du verrou de session après task-254** : détention **178,7 ms par
acquisition** (contre 269,3 ms avant), **1,10 acquisition par message**. Pour
mémoire, task-239 avait déjà ramené la détention p95 de **7,44 s à 0,49 s** en
prenant le verrou **par message** au lieu du sous-lot.

**Trois plafonds du banc qui contaminent toute mesure d'enrichissement** — à
neutraliser avant de conclure, pas à découvrir en route :

- **Pools Postgres froids** : l'ouverture d'une connexion neuve expire à **15 s**
  (`NpgsqlConnector.ConnectAsync` → `TimeoutException`, remontée en 500 par
  `GetEnrichedUidsAsync`, **avant tout fetch**). Un préchauffage d'une requête
  par praticien suffit à passer de 5 lots aboutis sur 8 à **8 sur 8**. Mesuré le
  2026-08-10.
- **`mail_max_userip_connections=10`** (Dovecot) — monter en charge par nombre de
  praticiens, pas par VU par praticien.
- **Limiteur de débit 100 req/10 s par identité.**

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est le verrou `imap_session`.** C'est le candidat
  historique de cette EPIC, il a déjà été écarté une fois sur un autre chemin,
  et task-254 vient d'écarter le suspect voisin. 178,7 ms de détention pour
  1,10 acquisition par message **ne suffisent pas** à expliquer un plafond à
  2,7 msg/s : il faut montrer **quelle file** se forme, et derrière quoi.
- **Ne pas présumer que le niveau absolu de 2,7 msg/s est comparable aux
  9,5 msg/s documentés.** Ces derniers viennent d'un autre montage (task-253).
  Le résultat de task-254 est la **platitude relative**, pas le chiffre. Toute
  conclusion sur un niveau absolu exige le **banc distant** (au-delà de
  ~500 praticiens, un chiffre mesuré en local est un artefact connu : Dovecot
  vole 2,6 cœurs au SUT).
- **Ne pas présumer que plus de concurrence est le remède.** task-253 a mesuré
  qu'un facteur 5 sur la concurrence ne rend que **+40 %** de débit — le coût
  unitaire absorbe presque tout.
- **Ne pas présumer que c'est Postgres** sur la base du timeout ci-dessus : il
  disparaît au préchauffage, donc il décrit un **démarrage à froid**, pas un
  plafond de régime.

## Definition of Done

- [ ] La ressource qui sérialise est **nommée et chiffrée** par la télémétrie,
      pas supposée : la mesure montre **une file** (attente non nulle et
      soutenue) sur une ressource identifiée, avec les requêtes qui l'établissent
- [ ] Le **débit est mesuré sur au moins trois points de concurrence**
      (par exemple 4 / 8 / 16) — deux points ne distinguent pas un plateau d'une
      pente faible
- [ ] Il est dit explicitement si la ressource est **dans api-mail** (verrou,
      pool, sérialisation applicative) ou **hors de lui** (serveur mail, base,
      pooler) — les deux remèdes n'ont rien à voir
- [ ] Les **trois plafonds de banc** ci-dessus sont neutralisés et le rapport le
      **dit** (préchauffage effectué, sessions par praticien sous le plafond
      Dovecot, débit par identité sous le limiteur) — sans quoi la mesure n'est
      pas opposable
- [ ] Si un correctif est livré : **A/B iso-conditions**, un seul facteur,
      binaires vérifiés, et le débit **croît** avec la concurrence sur les trois
      points
- [ ] Si aucun correctif n'est livré : le **dire**, écrire pourquoi, et poser le
      seuil qui rouvrirait le sujet
- [ ] Ce que la télémétrie n'a **pas** pu dire est écrit — backlog
      d'instrumentation de la US suivante

## Manual Test Plan

- Monter le banc, **précharger les pools** (une requête `GET /api/v1/mail/folders`
  par praticien) avant toute mesure
- Lancer l'enrichissement à **trois concurrences** (4 / 8 / 16), corpus et
  population identiques, base purgée entre chaque point
  (`YES=1 tests/loadtest-k6/reset-state.sh` — sans quoi les `MailContents` du
  point précédent court-circuitent l'analyse et le débit mesuré est faux)
- Relever, **pendant** chaque tir (une `rate` évaluée après coup rend une série
  vide) : le débit d'enrichissement, la détention et l'**attente** du verrou
  `imap_session`, la file du pooler (`cl_waiting`), les sessions Dovecot
- Ouvrir une boîte depuis l'application pendant le palier le plus chargé : la
  liste doit rester consultable (c'est ce que task-239 protège, et qu'un remède
  au plateau ne doit pas défaire)

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance / exploitation
- **Exigences DSR honorées** : aucune exigence nouvelle
- **INS** : ⚠️ l'enrichissement manipule des CDA porteurs d'INS — aucune étiquette
  de métrique ni message de journal ne doit porter d'INS, de contenu de document,
  d'objet de message ou de nom de fichier (la fuite qu'a évitée task-213). Les
  étiquettes restent des **littéraux** d'un ensemble fini
- **Interop CI-SIS** : volet transport MSSanté / IHE-XDM — ⚠️ **l'intégrité et la
  complétude des documents extraits sont bloquantes** : un remède qui gagnerait
  du débit en perdant, tronquant ou dupliquant un document clinique est refusé.
  Les garde-fous de task-254 (`8a843a8`, `e71f14e`) sont le filet à ne pas
  contourner
- **Habilitations** : le cloisonnement « une base par praticien » ne doit pas
  être affaibli pour gagner du débit — notamment aucun partage de connexion
  entre praticiens
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : le verdict et le remède doivent être transposables à la
  cible (le banc local n'est pas opposable sur un niveau absolu)
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-255-serialisation-enrichissement — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-255-serialisation-enrichissement
- `dtos-mss` (pushed, auto-inclus) : feat/task-255-serialisation-enrichissement — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-255-serialisation-enrichissement

## Campagne log — 2026-08-13, banc local, trois points de concurrence

### Résultat

**Le plateau ne se reproduit pas.** Sous protocole corrigé, le débit
d'enrichissement **croît** avec la concurrence.

| Concurrence | Fenêtre | Messages enrichis | Débit | Enveloppe/msg | `imap_fetch` | `db_write` | `assemble` | Attente `imap_session` |
|---|---|---|---|---|---|---|---|---|
| 4 | 42,0 s | 640 / 640 | **15,22 msg/s** | 209,1 ms | 125,5 ms | 31,8 ms | 10,8 ms | 0,0 ms/acq |
| 8 | 24,3 s | 640 / 640 | **26,38 msg/s** | 237,0 ms | 127,2 ms | 47,3 ms | 15,4 ms | 0,0 ms/acq |
| 16 | 18,5 s | 640 / 640 | **34,59 msg/s** | 325,2 ms | 127,8 ms | 112,9 ms | 32,0 ms | 10,5 ms/acq |

×1,73 puis ×1,31, soit **×2,27 de débit pour ×4 de concurrence**. À comparer
au **+4 %** que task-254 avait mesuré pour un doublement — et qui motivait cette
US. Les trois points sont verts : 0 erreur HTTP, 100 % de checks,
`enrich_short_circuited = 0`, 32 lots sur 32, **640 messages enrichis sur 640
soumis** aux trois points.

### La ressource qui borne la montée : le CPU disponible pour le système sous test

Ce n'est **ni** le verrou `imap_session`, **ni** le pooler, **ni** le serveur
mail, **ni** la base.

| Concurrence | CPU hôte | File d'exécution (24 cœurs) | `cl_waiting` praticien | `maxwait` | Backends Postgres | Sessions Dovecot |
|---|---|---|---|---|---|---|
| 4 | 69,8 % | 0,1 (max 1) | 0 / 8 relevés | 0 ms | 16 | 26 |
| 8 | 85,2 % | 3,2 (max 15) | 0 / 5 relevés | 0 ms | 16 | 41 |
| 16 | **91,2 %** (max 100) | **8,5 (max 24)** | 2 / 4 relevés | 63,8 ms | 16 | 46 |

Deux preuves indépendantes et concordantes :

1. **Par les ressources** — la file d'exécution du processeur passe de 0,1 à 8,5
   et touche 24 sur une machine à 24 cœurs, pendant que le pooler reste calme
   (`cl_waiting` nul sur 13 relevés sur 17, `maxwait` <= 64 ms) et que les
   backends Postgres ne bougent pas d'un point (16 aux trois concurrences).
2. **Par la décomposition interne** — la phase **bornée par la latence injectée**
   (`imap_fetch`, 100 ms Toxiproxy) est **plate au demi-millimètre**
   (125,5 -> 127,2 -> 127,8 ms), tandis que **toutes** les phases bornées par le
   calcul enflent ensemble (`db_write` x3,5, `assemble` x3,0, `xdm_extract`
   x1,3). Une file sur une ressource nommée ferait monter le coût de ceux qui
   l'attendent ; ici c'est tout ce qui calcule qui ralentit.

**Dans api-mail ou hors de lui ?** -> **Hors**. Et pas seulement hors de
l'application : **hors du banc**. Attribution du CPU pendant le point 16 —

| Poste | Cœurs |
|---|---|
| Hôte occupé (91,2 % de 24) | ~21,9 |
| api-mail (5 réplicas) | ~3,0 |
| Tous les conteneurs du banc (Postgres, PgBouncer, RabbitMQ, Dovecot, Toxiproxy, Seq…) | **1,62** |
| **Reste, étranger à la mesure** | **~17** |

Dont un coupable identifié et mesuré : le conteneur **`sql-server`**, qui n'a
aucun rapport avec le banc, consomme **~11 cœurs en continu** (1 087 à 1 164 %
sur trois relevés espacés de 5 s), sans interruption **depuis le 2026-08-12**,
et plafonne sa mémoire à 1,34 GiB sur 2 GiB.

**Conséquence sur l'opposabilité** : la pente mesurée est un **plancher**, pas un
plafond applicatif. Sur un hôte non affamé elle serait au moins aussi bonne.
Aucun niveau absolu n'est opposable — conforme à ce que le task file exigeait
déjà.

### Les trois plafonds de banc, neutralisés et vérifiés

| Plafond | Neutralisation | Preuve |
|---|---|---|
| Pools Postgres froids (timeout 15 s) | Préchauffage d'un `GET /folders` par praticien avant chaque point | 8/8 en 200 aux trois points ; 0 `TimeoutException` sur la série |
| `mail_max_userip_connections=10` (Dovecot) | Montée en concurrence à population constante (8 praticiens) | 46 sessions au maximum, soit **5,8 par praticien** — sous le plafond de 10 |
| Limiteur 100 req/10 s par identité | 32 requêtes par tir réparties sur 8 identités | **0 HTTP 429** aux trois points |

### Trois défauts de banc trouvés en route — deux campagnes jetées

**F-255-1 — `08P01 server_login_retry` : l'alias `pgupstream` ne protège plus.**
`--add-host=pgupstream:host-gateway` injecte aujourd'hui **deux** entrées dans
`/etc/hosts` du conteneur, une IPv4 (`192.168.65.254`) **et** une IPv6
(`fdc4:f303:9324::254`). PgBouncer retient l'AAAA, échoue en « Network
unreachable », met l'échec en cache pour `server_login_retry`, et **tout** client
du pool prend alors un 500 en quelques millisecondes. C'est la régression exacte
que task-200 croyait fermée : son garde-fou
(`BenchUpstream_DoesNotRelyOnHostDockerInternal`) teste le **nom**, pas la
**famille d'adresses résolue**. Coût mesuré : 13 % des lots au premier tir.
Retirer l'entrée IPv6 de `/etc/hosts` **ne suffit pas** (PgBouncer garde sa
propre résolution) — il restait 2,6 % d'échecs. **Correctif retenu** : sortir
complètement du `host-gateway` en rattachant PgBouncer au réseau du conteneur
PostgreSQL et en l'adressant par son nom (`postgres-pgvector`, DNS Docker,
IPv4 seul). Écrit dans `src/AppHost/pgbouncer/pgbouncer.ini`. ⚠️ Le
`docker network connect` reste **manuel** : à porter dans `AppHost.cs`.

**F-255-2 — la télémétrie fabriquait le plateau qu'on cherchait à expliquer.**
L'application exporte ses métriques toutes les 5 s et Prometheus scrute toutes
les 5 s. Un snapshot pris à la seconde où k6 s'arrête **perd la queue du tir** —
et d'autant plus que le tir est court, or un tir se raccourcit précisément quand
la concurrence monte. Mesure : sur un tir de 16 s, **275 messages comptés pour
640 réellement enrichis**, soit un débit sous-estimé de 57 %. Avec 30 s de
décantation, le comptage devient exact (640/640 aux trois points). **Sans ce
correctif, cette campagne aurait « confirmé » une décroissance du débit avec la
concurrence.** C'est le pendant, sur les compteurs cumulés, du piège des
`rate()` évaluées après coup déjà documenté dans le skill.

**F-255-3 — purger pendant que le bus travaille re-remplit les tables.**
Un `reset-state.sh` lancé alors qu'il reste des `AddNewMailMessage` en vol laisse
les consommateurs **réécrire des `MailContents` après le TRUNCATE**. Le point
suivant court-circuite alors son enrichissement (**22 lots sur 32** constatés) et
rend un débit faux, d'apparence excellente — 1,5 s de tir. Le filet du harnais
(`enrich_short_circuited count==0`) l'a attrapé. **Remède** : attendre le
drainage des files RabbitMQ **avant** de purger. Il a servi dès le point suivant
(un message encore en vol).

### Un défaut applicatif, sans rapport avec le débit

**F-255-4 — `ContactRepository.UpdateAsync` casse sous concurrence.**
`InvalidOperationException: Collection was modified; enumeration operation may
not execute` dans `RemoveRange`, quatre occurrences sur la campagne, sur le
chemin asynchrone des contacts praticien (`ContactRepository.cs:206`). Sans
effet sur l'enrichissement mesuré (aucune erreur sur les 1 920 messages
enrichis de la série), mais c'est un vrai bug de concurrence : la collection est
modifiée pendant qu'on l'énumère.

### Ce que la télémétrie n'a PAS pu dire — backlog d'instrumentation

1. **L'attente d'obtention d'une connexion base sur le chemin d'enrichissement
   n'est pas instrumentée.** `mssante_db_operation_phase_duration_seconds`
   (dont `connection_open`) ne remonte **qu'un seul appel** sur toute la
   campagne : elle couvre le chemin de lecture (task-243), pas l'écriture
   d'enrichissement. Le triplement de `db_write` (31,8 -> 112,9 ms) est donc
   **attribué par recoupement** — file d'exécution du processeur qui explose,
   pooler calme, backends stables — et **non mesuré à la source**. C'est le
   premier compteur à ajouter avant toute optimisation de cette phase.
2. **Le CPU n'est pas attribuable par phase.** On sait que les phases de calcul
   enflent ensemble, pas laquelle paie quoi.
3. **L'échantillonneur est trop lâche pour les tirs courts** : 4 relevés sur la
   fenêtre du point 16 (cadence 5 s). Suffisant pour une tendance monotone,
   insuffisant pour un percentile.
4. **`ConcurrentMessageLimit = 10`** sur `add-new-mail-queue` n'a pas été
   éprouvé : la phase `embedding` (189 ms/message, la plus coûteuse de toutes)
   est **hors du chemin synchrone** — le code le dit et la mesure le confirme
   (les phases synchrones bouclent exactement sur l'enveloppe). Elle n'entre donc
   pas dans la latence que paie `enrich/sync`, mais elle consomme du CPU en
   concurrence. Son plafond deviendra le facteur limitant dès que le CPU cessera
   de l'être.

### Aucun correctif de débit livré — et pourquoi

Le task file prévoyait les deux issues. **Aucun correctif applicatif n'est
livré**, parce que **la prémisse de la US n'est pas vérifiée** : il n'y a pas de
plateau à franchir entre 4 et 16 sur ce banc. Corriger quelque chose ici
reviendrait à traiter une cause supposée — exactement ce que cette EPIC a déjà
payé avec task-222.

**Seuil qui rouvrirait le sujet** : un tir sur **hôte non affamé** (file
d'exécution du processeur < 2, CPU étranger à la mesure < 4 cœurs) ou sur le
**banc distant**, montrant un rapport de débit **inférieur à x1,3 pour un
doublement** de concurrence sur deux paliers consécutifs. En dessous de ce
seuil, le suspect suivant est nommé d'avance par la présente mesure :
la phase `db_write` et son attente d'obtention de connexion — à **instrumenter
d'abord** (point 1 du backlog ci-dessus), à optimiser ensuite.

### Livrables

- Rapport de tir : `Api/Mail/tests/loadtest-k6/reports/2026-08-13/report-enrich-255-conc16-095739.md`
  (KPI, vérification par base **PASS** — 640/640 stockés, 0 mélange —, analyse
  Seq remplie, et l'annexe des trois points)
- Ligne d'INDEX ajoutée
- Résumés k6 des trois points : `enrich-255-conc4-094744.json`,
  `enrich-255-conc8-095241.json`, `enrich-255-conc16-095739.json`
- Échantillonneur de ressources : `observe-090235.csv`
- Correctif de banc : `src/AppHost/pgbouncer/pgbouncer.ini`

### Conditions de la mesure

Banc **local** (les serveurs mail ne sont pas sur le cluster), 8 praticiens x
80 messages porteurs d'`IHE_XDM.ZIP`, maildir vierge, `ENRICH_BATCH=20`,
`ENRICH_SHARE=1.0`, `SESSION_ROTATION=0.002`, `DURATION=15m` (plafond non
atteint), latence Toxiproxy `mssante` (100 ms), 5 réplicas api-mail, PgBouncer
en mode transaction. Protocole par point : **drainage du bus -> purge
(`reset-state.sh`) -> préchauffage -> snapshot -> tir -> décantation 30 s ->
snapshot**. Compteurs cumulés et deltas, jamais de `rate()`.

⚠️ **Écart assumé avec task-254** : 80 messages par praticien au lieu de 30. Il
en fallait au moins 16 lots pour que VUS=16 soit exécutable (un
`shared-iterations` refuse moins d'itérations que de VUs). Les niveaux absolus
ne sont donc pas comparables entre les deux campagnes — seule la **pente** l'est,
et c'est elle que la US demandait.

---

## ⚠️ Série de référence — hôte non affamé (2026-08-13, 14:22–14:34)

**Cette série remplace celle de 09:42–09:58 comme résultat de la US.** Cette
dernière est conservée ci-dessus comme **contre-épreuve** : elle diffère par un
seul facteur, un conteneur `sql-server` étranger au banc qui consommait ~11 des
24 cœurs (F-255-5), arrêté depuis.

| Concurrence | Fenêtre | Messages enrichis | Débit | Enveloppe/msg | `imap_fetch` | `db_write` | `assemble` | Attente `imap_session` |
|---|---|---|---|---|---|---|---|---|
| 4 | 38,4 s | 640 / 640 | **16,66 msg/s** | 188,0 ms | 124,8 ms | 23,3 ms | 8,4 ms | 0,0 ms/acq |
| 8 | 21,2 s | 640 / 640 | **30,19 msg/s** | 207,3 ms | 126,5 ms | 31,7 ms | 11,2 ms | 0,0 ms/acq |
| 16 | 14,2 s | 640 / 640 | **45,02 msg/s** | 258,9 ms | 127,3 ms | 62,1 ms | 21,1 ms | 8,7 ms/acq |

**×1,81 puis ×1,49, soit ×2,70 de débit pour ×4 de concurrence.** Le plateau à
+4 % pour un doublement, qui motivait cette US, **ne se reproduit pas**.

### La contre-épreuve, et ce qu'elle prouve

| Concurrence | Hôte affamé | Hôte calme | Écart |
|---|---|---|---|
| 4 | 15,22 msg/s | 16,66 msg/s | **+9 %** |
| 8 | 26,38 msg/s | 30,19 msg/s | **+14 %** |
| 16 | 34,59 msg/s | 45,02 msg/s | **+30 %** |
| **Pente (×4 de concurrence)** | ×2,27 | **×2,70** | — |

**Le gain croît avec la concurrence.** C'est la signature d'une contention de
calcul : plus on demande de travail simultané, plus la privation de CPU coûte.
Et c'est une preuve **indépendante** de la décomposition par phase — une file
sur une ressource applicative nommée n'aurait pas été desserrée en arrêtant un
conteneur tiers.

### Ressources pendant les trois tirs de référence

| Concurrence | CPU hôte | File d'exécution (24 cœurs) | `cl_waiting` praticien | `maxwait` | Backends Postgres | Sessions Dovecot |
|---|---|---|---|---|---|---|
| 4 | 48,6 % | 0,6 (max 2) | 0 / 7 relevés | 0 ms | 16 | 22 |
| 8 | 36,2 % | 2,6 (max 12) | 1 / 5 relevés | 0,7 ms | 16 | 32 |
| 16 | 68,7 % (max 98) | **13,0 (max 30)** | 0 / 3 relevés | 0 ms | 16 | 42 |

### Verdict — la ressource qui borne la montée est le CPU

Quatre constats indépendants et concordants :

1. **Le pooler ne fait pas la queue** — `cl_waiting` nul sur 14 relevés sur 15,
   `maxwait` maximal **0,7 ms**, backends Postgres invariants (16 aux trois
   concurrences).
2. **Le verrou `imap_session` est exonéré** — attente **strictement nulle** sur
   704 acquisitions à 4 comme à 8 ; à 16 elle apparaît mais vaut 9,6 ms par
   message sur une enveloppe de 258,9 ms, soit **3,7 %**. Le suspect historique
   de cette EPIC n'est pas le facteur limitant, et la US avait raison d'interdire
   de le présumer.
3. **La décomposition interne tranche** — la phase **bornée par la latence
   injectée** (`imap_fetch`, 100 ms Toxiproxy) est **plate au demi-millimètre**
   (124,8 → 126,5 → 127,3 ms), tandis que **toutes** les phases bornées par le
   calcul enflent ensemble (`db_write` ×2,7, `assemble` ×2,5, `xdm_extract`
   ×1,5). Une file ferait monter le coût de ceux qui l'attendent ; ici c'est
   tout ce qui calcule qui ralentit.
4. **La file d'exécution du processeur atteint 30 sur 24 cœurs** à VUS=16, contre
   0,6 à VUS=4.

**Dans api-mail ou hors de lui ?** → **Hors**. Le facteur limitant est le CPU de
l'hôte, partagé entre le SUT (~5,8 cœurs à VUS=16) et l'infrastructure du banc
(~4 cœurs). **Aucune ressource applicative ne sature avant lui.**

**Ce que ça implique pour le dimensionnement** : à 8 praticiens et 16 requêtes
simultanées, api-mail n'a **pas** de plafond interne d'enrichissement. Ajouter
de la concurrence ajoute du débit tant qu'il reste du CPU — c'est exactement la
propriété que la US voulait vérifier, et la réponse est positive.

### F-255-5 — le conteneur qui volait la moitié de la machine

Le premier verdict de cette campagne attribuait la sous-linéarité à « un CPU
hôte saturé ». L'analyse de la cause a montré qu'il ne s'agissait pas d'une
charge légitime : le conteneur **`sql-server`**, sans aucun rapport avec le banc,
était **en boucle d'échec** — `Error 17300, Failed to start system task` —
réémise en continu.

| Grandeur | Valeur |
|---|---|
| `memory.current` / `memory.max` (cgroup) | 2 147 344 384 / 2 147 483 648 — **99,994 % du plafond** |
| Échecs d'allocation (`failcnt`) | **50 997** |
| CPU | ~11 cœurs, `NanoCpus=0` — **aucune limite** |
| Première occurrence de l'erreur | **2025-10-03** (dix mois) |
| Journal | 9,1 M lignes, **5,0 Go** sur disque |
| Service rendu | **aucun** — `sqlcmd` sur `localhost` échoue avant login |

Le port 1433 était en écoute (proxy Docker) mais l'instance ne répondait pas :
même faux positif que le relais IPv6 déjà documenté — TCP accepté, service mort.
Cause racine : plafond mémoire de 2 GiB, c'est-à-dire le minimum que SQL Server
demande **pour lui seul**, tout compris. Il ne pouvait donc jamais atteindre sa
cible, échouait à allouer ses tâches système, et brûlait du CPU à réessayer.

**Leçon de banc, au-delà de cette US** : avant toute campagne, vérifier **à qui
appartient le CPU**. Un `docker stats --no-stream | sort -k2 -hr | head` de
cinq secondes aurait épargné une série complète. Consigné dans le skill.

### Récapitulatif du DOD

| Critère | État |
|---|---|
| Ressource nommée **et chiffrée** par la télémétrie, avec la file qui l'établit | ✅ CPU de l'hôte — file d'exécution 0,6 → 13,0 (max 30 sur 24 cœurs), et exonération chiffrée des trois autres candidats |
| Débit mesuré sur **au moins trois** points de concurrence | ✅ 4 / 8 / 16, deux séries complètes (référence + contre-épreuve) |
| Dire si la ressource est **dans** api-mail ou **hors** de lui | ✅ **Hors** — CPU hôte, aucune ressource applicative ne sature avant |
| Les **trois plafonds de banc** neutralisés, et le rapport le dit | ✅ préchauffage 8/8, 5,3 sessions/praticien (plafond 10), 0 HTTP 429 |
| Si correctif livré : A/B iso-conditions, débit croissant sur trois points | ✅ **sans objet côté applicatif**, mais l'A/B de banc est fourni (hôte affamé vs calme, un seul facteur) et le débit **croît** sur les trois points |
| Si aucun correctif : le dire, pourquoi, et poser le seuil de réouverture | ✅ ci-dessous |
| Ce que la télémétrie n'a **pas** pu dire | ✅ backlog d'instrumentation ci-dessus |

### Aucun correctif de débit livré — et pourquoi

**La prémisse de la US n'est pas vérifiée** : il n'y a pas de plateau à franchir
entre 4 et 16. Livrer un correctif ici reviendrait à traiter une cause supposée,
exactement ce que cette EPIC a déjà payé avec task-222.

**Seuil qui rouvrirait le sujet** : un tir montrant un rapport de débit
**inférieur à ×1,3 pour un doublement** de concurrence sur deux paliers
consécutifs, **avec la file d'exécution du processeur sous 2** (donc sans
famine CPU). En dessous de ce seuil, le suspect suivant est nommé d'avance par
la présente mesure : la phase `db_write` — à **instrumenter d'abord** (son
attente d'obtention de connexion n'existe pas comme métrique), à optimiser
ensuite.

**Deux réserves d'honnêteté** :

- **Le niveau absolu (45 msg/s) n'est pas opposable** : banc local, 8 praticiens,
  latence Toxiproxy, et une infrastructure de banc qui partage le CPU du SUT.
  Seule la **pente** est le résultat.
- **Le domaine de validité s'arrête à 16.** Rien ici ne dit ce qui se passe à
  32 ou à 500 praticiens, où le CPU cesserait d'être le premier plafond et où
  `ConcurrentMessageLimit = 10` deviendrait candidat.

### Livrables (série de référence)

- Rapport de tir : `Api/Mail/tests/loadtest-k6/reports/2026-08-13/report-enrich-255-conc16-143401.md`
  (KPI, vérification par base, analyse Seq remplie, annexe des trois points et
  contre-épreuve)
- Résumés k6 : `enrich-255-conc4-142614.json`, `enrich-255-conc8-143010.json`,
  `enrich-255-conc16-143401.json`
- Échantillonneur : `observe-142219.csv`
- Rapport de la contre-épreuve : `report-enrich-255-conc16-095739.md`
  (+ `observe-090235.csv`)
- Correctif de banc : `src/AppHost/pgbouncer/pgbouncer.ini`
- Pièges consignés dans `.claude/skills/loadtest-skill/SKILL.md`

## PRs

- `api-mail` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/185 — label `awaiting-human-merge`
- `dtos-mss` (pushed, auto-inclus) : **aucune PR** — branche sans commit, aucun contrat DTO touché

## Code Review Summary

**Verdict : APPROVED** — 1 fichier, +10 lignes de Markdown, 0 blocage, 0 suggestion.

Cette US est une US **de mesure** : elle ne produit aucun code applicatif. Le
correctif de banc `pgbouncer.ini`, éprouvé pendant la campagne, a été **retiré de
la branche** sur arbitrage humain du 2026-08-13 (`questions/task-255.md`, option
A) — il faisait tomber le garde-fou `BenchUpstream_DoesNotRelyOnHostDockerInternal`
et n'est pas complet sans son pendant `AppHost.cs`. Il part **entier** dans
task-257, reproduit en annexe de cette US.

### Validation

| Contrôle | Résultat |
|---|---|
| Build `api-mail` | ✅ 0 erreur, 0 avertissement |
| Tests `mss.mail.integration.tests` | ✅ 401 passés, 16 ignorés, **0 échec** — dont le garde-fou PgBouncer, redevenu vert après retrait du correctif |
| Tests `mss.mail.application.tests` | ⚠️ **1 échec pré-existant sur `develop`** — voir ci-dessous |
| DOD | ✅ tous les critères de mesure tenus (tableau récapitulatif plus haut) |

### ⚠️ `develop` est rouge, et ce n'est pas cette task

`AiPromptHelperTests.GetPromptShouldContainDocumentIntroduction` échoue, 2 fois
sur 2, de façon déterministe. **Cause établie** : le commit `411b289` « Fix
prompt », sur `develop` depuis le 2026-08-10, a modifié le texte du prompt sans
mettre à jour son test — la chaîne `"Voici le document à analyser"` n'existe plus
dans `AiPromptHelper.cs`.

**Preuve que task-255 n'y est pour rien** : le diff de la branche face à
`origin/develop` est de **10 lignes de Markdown**, aucun code compilé ne diffère —
le résultat du test est donc identique sur `develop`. Un second échec observé sur
la suite complète ne s'est pas reproduit à l'unité : flaky, non caractérisé.

**Ce n'est pas traité ici** (hors périmètre, et la forge ne corrige pas de code en
`/review`) mais cela mérite une US : un test qui garde un texte de prompt et qu'on
laisse rouge trois jours ne garde plus rien.
