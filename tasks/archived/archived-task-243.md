# todo-task-243.md — Le premier poste de coût du parcours est une boîte noire de 3,3 secondes

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-240** (`archived`, mergée le 2026-08-08) — c'est elle qui
a rendu ce coût **attribuable à un appel**. Celle-ci rend attribuable ce qui se
passe **dans** cet appel. Coordination utile avec **task-242** (`todo`,
`cl_waiting` qui accélère) : l'un des trois candidats de cette US est
précisément la contention base que task-242 instruit — les deux US se répondent
et gagnent à être lues ensemble.
**Priorité**: **1** — c'est le dernier verrou technique du **NO-GO 500**. On ne
mesure pas à 500 praticiens sans savoir expliquer 200, et le premier poste de
coût du parcours est aujourd'hui une boîte noire.

## Objective

Qu'on puisse répondre à « **pourquoi** la page d'en-têtes de l'inbox coûte
5 676 ms de p95 ? » — pas « laquelle des requêtes coûte », ce que task-240 a
déjà réglé, mais **où part le temps à l'intérieur** de cette requête.

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus
rapide. Elle rend le prochain correctif décidable — et surtout, elle **empêche**
d'écrire ce correctif sur une intuition. Cette EPIC a déjà annulé une US
applicative bâtie sur une cause plausible et fausse (task-222) ; la règle qui en
est sortie s'applique ici mot pour mot.

## Ce qui est déjà établi — et qu'il ne faut pas re-mesurer

Instruction du 2026-08-08 (`instr-emails-ids-170900`, 100 médecins × 10 min,
attribution **reproduite à l'identique** sur deux tirs consécutifs, donc fiable) :

| Fait | Mesure |
|---|---|
| `emails` porte le coût de `read_list` | **97 %** du temps serveur de l'étape, p95 **5 676 ms**, p50 458 ms |
| Le temps est **dans l'action** | décomposition de trace : contexte résolu en **0,3 ms**, puis **3 278 ms** sur 3 297 — et **aucun événement** dans l'intervalle |
| **Ce n'est pas IMAP** | **214** `fetch_body_part` pour ~25 000 UIDs demandés — la page est servie depuis la **base** |
| **Ce n'est pas l'attente de verrou** | 5 ms p95, et `GetEmailsByIds` **ne prend pas** le verrou `imap_session` |

**Lecture du code, annoncée comme structurelle et non mesurée** :
`MailRepository.GetMailsByUidsAsync` enchaîne **6 à 8 requêtes groupées** —
génération du dossier, les mails, puis tags, destinataires, pièces jointes,
identifiants enrichis, acquittements biologie. **Ce n'est pas un N+1** : tout est
batché par `mailIds.Contains(...)`. C'est précisément ce qui rend la cause
non évidente — six à huit requêtes groupées ne font pas 3,3 s à elles seules.

## Les trois candidats, non séparables en l'état

C'est **le** problème que cette US existe pour résoudre. Aucun n'est privilégié :

1. **Contention base** — `cl_waiting` est non nul sur **21 %** des relevés dès
   100 médecins (et 29 % à 200 lors de la campagne). Le temps pourrait être
   passé à **attendre une connexion**, pas à exécuter du SQL.
2. **Concurrence CPU du pipeline CDA** — depuis task-239, l'enrichissement
   acquiert le verrou **11,26 fois par seconde** et son parsing tourne
   désormais hors verrou, donc en parallèle des requêtes du médecin.
3. **Coût de matérialisation** — construire 25 DTO avec leurs tags,
   destinataires, pièces jointes et acquittements est du travail CPU et des
   allocations, invisible de toute métrique actuelle.

## Ce que la US doit livrer

Une **décomposition chiffrée** du temps passé dans `GetMailsByUidsAsync`,
suffisante pour désigner le ou les postes dominants et écarter les autres. Au
minimum, savoir séparer :

- le temps d'**emprunt d'une connexion** à la base (l'attente du pooler) ;
- le temps d'**exécution** des requêtes, requête par requête (les 6 à 8 sont de
  natures très différentes — l'une d'elles peut porter le tout) ;
- le temps de **construction des DTO** (le reste).

La forme est un choix technique : histogrammes OpenTelemetry par phase,
activités/spans, ou les deux. Ce qui compte, c'est que le rapport de banc puisse
ensuite **nommer le poste dominant**, comme task-240 a appris à nommer l'appel.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est la base.** C'est l'hypothèse la plus séduisante
  (`cl_waiting` non nul), donc celle qui mérite le plus d'être vérifiée avant
  d'être codée. Un `cl_waiting` à valeur faible (max 3 mesuré) peut coexister
  avec un temps SQL négligeable.
- **Ne pas présumer que l'instrumentation est gratuite.** Chronométrer 6 à 8
  requêtes sur un chemin appelé ~1 000 fois par tir a un coût, et une étiquette
  mal bornée fait exploser la cardinalité. Mesurer par **phase**, pas par
  requête individuelle, si la phase suffit à trancher.
- **Ne pas présumer qu'il faut instrumenter ce seul chemin.** `GetMailsByUidsAsync`
  est un patron partagé (`LoadBulkMailLookupsAsync` sert plusieurs appelants) :
  regarder si l'instrumentation peut servir la famille sans la diluer.
- **Ne pas glisser vers l'optimisation.** Si une évidence saute aux yeux pendant
  le travail (une requête inutile pour un `Header`, par exemple), **la
  consigner** comme finding et la traiter dans une US suivante — mesurée. Une US
  d'instrument qui optimise en passant ne peut plus prouver son propre effet.

## Definition of Done

- [x] Build passes (0 erreur) — `dotnet build HealthPlatform.Api.Mail.sln`
- [x] Tests pass (0 failure) — `dotnet test HealthPlatform.Api.Mail.sln`
      (3 689 tests, 0 échec) + suite du harnais (224 tests Python, 0 échec)
- [x] **Zéro changement de comportement** : mêmes routes, mêmes réponses, mêmes
      requêtes SQL émises — l'instrumentation observe, elle ne réécrit pas
      (intercepteurs délégant à `base`, résultat rendu inchangé — test dédié)
- [x] La décomposition sépare au minimum **emprunt de connexion / exécution SQL /
      construction des DTO**, et le choix des phases est **justifié par écrit**
      (voir « Ce qui a été livré » ci-dessous et le commentaire de tête de
      `MailProcessingMetrics`, section task-243)
- [x] Cardinalité **bornée** : étiquettes littérales, aucune valeur dérivée de la
      donnée (ni UID, ni dossier, ni identifiant patient) — cf. la fuite évitée
      par task-213 sur le nom de pièce jointe. Deux tests la verrouillent, côté
      C# (étiquettes émises) et côté rapport (aucun `by` élargi dans les PromQL)
- [x] Unit tests : les phases sont chronométrées aux bons endroits (test d'ordre
      ou de comptage d'émissions), et une exception ne laisse pas une phase
      ouverte
- [x] Aucune donnée de santé dans les métriques ni dans les logs ajoutés
      (aucun log ajouté ; deux étiquettes, toutes deux littérales)
- [x] `report.py` publie la décomposition — ou, si l'US choisit de ne pas
      toucher au rapport, la requête PromQL qui la lit est **écrite dans le
      task file** pour être rejouable → **les deux** ont été faits
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir
      `journey` court (100 médecins, 10 min) et **une phrase attribuable** —
      « sur les ~3,3 s de la page d'en-têtes, X ms sont l'attente de connexion,
      Y ms l'exécution SQL, Z ms la construction des DTO ». Si les trois postes
      ne suffisent pas à expliquer le total, **le dire** : le reste inexpliqué
      est lui-même un résultat, et il désigne le prochain découpage.
      → **RESTE À FAIRE** : le banc n'était pas monté. Le rapport rend la phrase
      tout seul dès qu'un tir tourne sur ce binaire (section « Où part le temps
      d'une lecture servie par la base »).

## Ce qui a été livré (2026-08-08, directement sur `develop`)

> ⚠️ Développée **directement sur `develop`** à la demande humaine — pas de
> branche `feat/*`, pas de PR, donc pas de HAG sur cette task. La seule case
> restante est la contre-épreuve au banc, qui exige un banc monté.

**Le découpage, et pourquoi celui-là.** Trois phases, choisies pour trancher entre
les trois candidats de la US et rien de plus :

| Phase | Ce qu'elle mesure | Le candidat qu'elle désigne |
|---|---|---|
| `connection_open` | obtenir une connexion : pool Npgsql, PgBouncer, poignée de main | **contention base** à l'état pur |
| `sql_execute` | commande envoyée → serveur répondu | travail du serveur |
| `assemble` | **le reste, par différence** : streaming des lignes, matérialisation EF, LINQ, DTO | **coût de matérialisation** (et concurrence CPU) |

`connection_open` **ne pouvait pas se mesurer au point d'appel** :
`GetDataContextAsync` n'instancie qu'un `DbContext`, et Npgsql n'ouvre la
connexion que paresseusement, à l'exécution de chaque requête. D'où le passage par
des **intercepteurs EF Core**, seul endroit qui voie cette frontière. La durée est
lue dans les `eventData.Duration` d'EF, qu'il mesure déjà pour cet usage — la
re-chronométrer aurait exigé de corréler début et fin par `ConnectionId`, donc un
état partagé, pour une mesure moins fidèle.

`assemble` est **volontairement une soustraction** et non une mesure : le découper
(streaming vs matérialisation vs DTO) n'aurait aucun sens tant qu'on ne sait pas
s'il pèse. S'il domine, c'est lui que la prochaine US découpe.

**Un compteur à côté des durées** : `mssante_db_operation_queries_total`. Si
`sql_execute` domine, c'est ce chiffre qui distingue « une requête lente » de
« trente requêtes rapides » — deux remèdes sans rapport. Il vérifie du même coup
l'annonce « 6 à 8 requêtes groupées », jamais mesurée jusqu'ici.

**La famille, pas le seul chemin.** Deux points d'appel instrumentés :
`GetMailsByUidsAsync` (le sujet) et `GetMailAsync` (l'autre lecture servie par la
base, qui partage `PopulateMailContentAsync` et porte l'hydratation des documents
de la fiche patient). Le périmètre n'est **pas re-entrant** : un périmètre
imbriqué alimente le périmètre extérieur sans republier, pour que l'attribution
désigne le geste du médecin et non le détail d'implémentation.

**Hors périmètre, rien ne coûte.** Les intercepteurs sont branchés sur tout le
trafic SQL du service, mais sans `DbOperationScope` actif ils ne font rien : ni
allocation, ni série temporelle. Instrumenter les dizaines d'autres requêtes
(réglages, contacts, migrations) aurait produit une métrique illisible à un coût
payé partout.

Fichiers : `src/Application/Telemetry/DbOperationScope.cs` (nouveau),
`MailProcessingMetrics.cs` (section task-243),
`src/Infrastructure/Telemetry/DbOperationPhaseInterceptors.cs` (nouveau),
`BaseRepository.cs` (câblage), `MailRepository.cs` (deux périmètres),
`tests/loadtest-k6/report.py` (section publiée) + 3 fichiers de tests.

## Les requêtes PromQL — rejouables à la main

Le rapport les émet lui-même (`report.py`, `PROM_DB_*`), mais elles se rejouent
telles quelles dans Prometheus / Grafana. **Les parts se calculent sur les
MOYENNES, qui s'additionnent ; jamais sur les p95 — le p95 d'une somme n'est pas
la somme des p95.**

```promql
# Moyenne par phase, en ms — CE SONT CES TROIS VALEURS QUI SOMMENT AU TOTAL
1000 * sum by (operation, phase) (rate(mssante_db_operation_phase_duration_seconds_sum[1m]))
     / sum by (operation, phase) (rate(mssante_db_operation_phase_duration_seconds_count[1m]))

# p95 par phase, en ms — dit OÙ VIT LA QUEUE, ne se partage aucun total
1000 * histogram_quantile(0.95, sum by (le, operation, phase)
       (rate(mssante_db_operation_phase_duration_seconds_bucket[1m])))

# L'enveloppe : moyenne et p95 de l'opération complète (instrument SÉPARÉ des
# phases, pour qu'un `sum by (phase)` ne puisse pas compter le total en double)
1000 * sum by (operation) (rate(mssante_db_operation_duration_seconds_sum[1m]))
     / sum by (operation) (rate(mssante_db_operation_duration_seconds_count[1m]))
1000 * histogram_quantile(0.95, sum by (le, operation)
       (rate(mssante_db_operation_duration_seconds_bucket[1m])))

# Requêtes SQL PAR APPEL — « une requête lente » ou « trente rapides » ?
sum by (operation) (rate(mssante_db_operation_queries_total[1m]))
  / sum by (operation) (rate(mssante_db_operation_duration_seconds_count[1m]))
```

## Findings consignés — à NE PAS corriger ici

> La US l'exige : « si une évidence saute aux yeux pendant le travail, **la
> consigner** comme finding et la traiter dans une US suivante — mesurée. Une US
> d'instrument qui optimise en passant ne peut plus prouver son propre effet. »
> Aucun de ces points n'a été touché.

**F-243-1 — `ComputeThreadCountsAsync` lit TOUTE la table `Mails` du praticien, à
chaque page d'en-têtes.** Deux requêtes sans aucun filtre de dossier, de page ni
de génération, sur le chemin de `GetMailsByUidsAsync` :

- [MailRepository.cs:1301-1304](../Api/Mail/src/Infrastructure/Repository/MailRepository.cs#L1301-L1304)
  — tous les `MessageId` de la boîte, matérialisés en mémoire ;
- [MailRepository.cs:1307-1310](../Api/Mail/src/Infrastructure/Repository/MailRepository.cs#L1307-L1310)
  — tous les mails porteurs de `References` ou `InReplyTo`, avec trois colonnes.

Ce coût suit la **taille de la boîte**, pas celle de la page : c'est le profil
« plat en charge, croissant avec le corpus » que la certification a observé. À
247 messages par boîte au banc, c'est modeste ; à 50 000 messages pour un
praticien réel, c'est deux scans complets par ouverture d'inbox. **Candidat
sérieux pour les 3,3 s**, et l'instrument livré ici doit maintenant le confirmer
ou l'écarter (il apparaîtra dans `sql_execute` et dans `assemble`) — c'est
exactement l'ordre que la US impose : mesurer d'abord.

**F-243-2 — l'hydratation d'un document reste en N+1 sur `GetMailAsync`.** ~10 +
3·D requêtes séquentielles par message (D = nombre de documents CDA), là où le
chemin bulk sans N+1 existe déjà dans le dépôt (`LoadBulkMailLookupsAsync`) sans
route HTTP qui l'expose avec `WithContent`. Déjà identifié à l'analyse du
2026-08-06 ; la task-243 le rend désormais mesurable via l'opération `GetMail`.

## Manual Test Plan

```bash
cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test
```

- Monter le banc (skill `loadtest-skill`), seeder une population modeste
- Ouvrir l'inbox d'un praticien (`GET .../emails/{25 uids}`) et vérifier dans
  Seq / Prometheus que la décomposition apparaît pour cette requête
- Vérifier qu'aucune étiquette ne contient d'UID, de nom de dossier ni
  d'identifiant patient
- Tir court `journey` 100 médecins × 10 min : lire la décomposition et vérifier
  qu'elle **explique** l'ordre de grandeur du p95 observé (ou nomme ce qui reste)

Données de test synthétiques uniquement — aucune donnée de santé réelle,
aucun INS réel.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de mesure interne
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : non applicable — aucun traitement d'identité modifié. ⚠️ Les
  étiquettes de métrique ne doivent porter **aucun** identifiant patient : c'est
  à la fois une exigence de confidentialité et une garde de cardinalité
- **Authentification PS** : inchangée
- **Habilitations** : non applicable — le cloisonnement « une base par
  praticien » n'est pas touché
- **Interop CI-SIS** : non applicable
- **MSSanté** : non applicable — aucun échange modifié
- **Tracé PGSSI-S** : les mesures ajoutées sont des données **d'exploitation**,
  pas des évènements métier : ni contenu clinique, ni INS, seulement des durées
  et des libellés de phase
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — banc local, données synthétiques ;
  l'instrumentation livrée devra rester **acceptable en production HDS** (volume
  de métriques borné, aucune donnée de santé)
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données
  personnelles
