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
