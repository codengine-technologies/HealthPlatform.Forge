# todo-task-343.md — Plusieurs serveurs, un seul comportement : les notifications temps réel et les conversations de l'assistant ne dépendent plus du serveur qui répond

**Repos**: api-mail
**Dependencies**: — (aucune ; complémentaire de task-336 — voir « Hors périmètre »)
**Epic**: E011
**Single frontend**: true
**Priorité**: **2** — avec plusieurs réplicas (4 dans le manifeste de production, 5 dans l'AppHost), **la plupart des tags d'urgence n'arrivent jamais à l'écran** en temps réel, et l'assistant IA perd sa conversation environ 3 fois sur 4.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-18 a** et **AUD-19**). Issue du découpage de
> l'ancienne task-336, validé par l'humain le 2026-09-27 (task-336 : boîte suivie par le flux ; task-343 :
> ce fichier ; task-344 : promotion unique). Cause commune : un état tenu **en mémoire d'un processus** alors
> que les requêtes d'un même praticien se répartissent entre réplicas (mémoire « api-mail = 5 réplicas, pool
> IMAP par processus »).

## Ce qui est établi (develop @ `14d58398`)

1. **Notifications (AUD-18 a)** — `SseNotificationBroker`, `SseMailEventBroker`, `SseSyncProgressBroker`
   (`src/Application/Services/Implementation/`) : abonnements tenus dans un `ConcurrentDictionary` du processus.
   `AddNewMailConsumer.cs:331` (`NotifyTagsUpdatedAsync`) publie dans le broker **local** ; or RabbitMQ livre le
   message à un réplica quelconque → environ (N−1)/N des tags d'urgence n'atteignent pas le flux SSE du praticien,
   même avec une affinité HTTP. Même effet pour les enrichissements et la progression de synchronisation publiés
   par un travail de fond.
2. **Conversations IA (AUD-19)** — `AiConversationStateManager.cs:12` : `ConcurrentDictionary` en Singleton
   (`Api/DependencyInjection.cs:133`), expiration 8 h par un `Timer` du processus. Conversation créée sur le pod 1,
   message envoyé au pod 2 → `CONVERSATION_NOT_FOUND` ; le résumé initial payé au fournisseur est perdu, et tout
   redémarrage efface les conversations. `DevOps/Prod/api.yaml:7` : 4 réplicas, Service NodePort sans affinité.
3. **Le mécanisme de diffusion existe déjà** : task-285 diffuse les ordres de synchronisation et de déconnexion
   entre instances par un canal Redis (`RedisSyncStateStore.cs:204-249` — `PublishAsync` / `SubscribeAsync` sur
   `mss:sync:cmd`), avec un service hébergé qui pose l'abonnement **au démarrage** (`SyncCommandSubscriptionService`,
   leçon task-285 : un abonnement posé à la première requête laisse une instance sourde).

## Objective

Qu'un événement temps réel publié par **n'importe quel réplica** atteigne le praticien **sur le réplica qui tient
son flux**, et qu'une conversation de l'assistant soit **retrouvée par n'importe quel réplica** et survive au
redémarrage d'un pod.

### Périmètre

1. **Backplane SSE (Redis pub/sub)** — sur le modèle de `mss:sync:cmd` :
   - chaque publication des trois brokers passe par un canal Redis ; chaque réplica s'y abonne **au démarrage**
     (service hébergé) et relaie vers ses abonnés locaux ;
   - **une seule voie de livraison** : le réplica émetteur publie dans Redis **sans** livrer lui-même en local ;
     tous les réplicas, lui compris, livrent depuis leur abonnement — aucun doublon, aucune perte selon le réplica ;
   - clés conservées : (boîte, dossier) pour les mails (task-175), e-mail de la boîte pour notifications et progression ;
   - **contrat SSE vu par les clients inchangé** (format des événements identique) ;
   - **Choix retenu par défaut** : le message diffusé porte le **DTO complet** déjà envoyé au client (Redis est dans
     le périmètre HDS et porte déjà des caches de contenu). Alternative notée : n'émettre que (boîte, dossier, UIDs)
     et relire en base sur chaque réplica — plus léger sur Redis, plus coûteux en base. L'humain peut inverser ce
     choix avant `/start` ;
   - panne Redis : la publication **ne fait pas échouer** l'opération métier (journalisée, comptée) ; la reprise
     de l'abonnement après coupure est automatique et testée.
2. **Conversations IA dans Redis** :
   - état de conversation (historique, résumé initial, UIDs, dossier, titre) stocké sous une clé
     **e-mail de la boîte + identifiant de conversation**, expiration **glissante de 8 h** (remplace le `Timer`) ;
   - écritures concurrentes sur une même conversation (deux onglets) protégées par un **numéro de version**
     (concurrence optimiste) : un tour de parole n'est jamais écrasé ; conflit → nouvel essai ou 409 explicite ;
   - `GetUserConversations` et `ActiveConversationCount` conservent leur sens (index par boîte) ;
   - **Choix retenu par défaut** : Redis. Alternative écartée : affinité de session sur `/api/v1/ai/*` — dépend de
     l'infrastructure (Service sans `sessionAffinity`, proxy amont inconnu) et ne résout pas le redémarrage d'un pod.

### Hors périmètre

- La **boîte** suivie par le flux SSE (task-336) : cette US garantit que l'événement atteint le bon réplica ;
  task-336 garantit que le flux suit la bonne boîte. Les deux sont nécessaires, indépendantes, dans n'importe quel ordre.
- La promotion concurrente d'un mail (task-344).
- L'isolation de l'assistant sur le Kernel partagé (task-328).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] deux instances de broker (deux « réplicas ») reliées au même Redis : publication sur l'une, abonné sur l'autre → **reçu**
  - [ ] conversation créée par une instance du gestionnaire, lue par une autre instance → **trouvée**
- [ ] Test : publication et abonné sur le **même** réplica → reçu **une seule fois**
- [ ] Test : Redis indisponible pendant une publication → l'opération métier aboutit, l'échec est journalisé et compté
- [ ] Test : l'abonnement est posé au **démarrage** de l'hôte (service hébergé), pas à la première requête
- [ ] Test : deux écritures concurrentes sur la même conversation → aucune perte de tour de parole
- [ ] Test : une conversation inactive expire après 8 h ; une conversation active voit son expiration prolongée
- [ ] Test d'intégration (Redis Testcontainers) : bout en bout des deux mécanismes
- [ ] Non-régression : tests existants des brokers SSE (task-175) et de l'assistant verts
- [ ] Aucune donnée de santé ajoutée dans les **logs** (le contenu diffusé vit dans Redis, jamais dans Seq/OTLP)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (5 réplicas de l'AppHost) ; mobile `cd Client/Mobile && npm start`.
2. **Tags** : recevoir cinq mails de test porteurs d'un compte rendu de biologie urgent → le tag « Urgent » apparaît en temps réel sur les cinq. Avant : sur une minorité.
3. **Progression** : lancer une synchronisation complète → la progression s'affiche du début à la fin sans saut.
4. **IA** : ouvrir l'assistant, poser trois questions successives → la conversation continue à chaque fois. Avant : « conversation non trouvée » la plupart du temps.
5. **Redémarrage** : pendant une conversation, redémarrer un réplica de l'AppHost → la conversation se poursuit.
6. **Panne Redis** : arrêter Redis quelques secondes pendant la réception de mails → les mails sont bien reçus et enregistrés ; les notifications reprennent au retour de Redis.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité de fonctionnalités existantes (notification temps réel, assistant)
- **INS** : non applicable — aucune INS ajoutée au backplane ni aux conversations
- **Authentification PS** : PSC / e-CPS inchangée
- **Habilitations** : inchangées — conversations et événements clés par la boîte du praticien, jamais partagés entre praticiens
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; échecs de publication sur le backplane journalisés sans contenu
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Redis dans le périmètre HDS ; conversations stockées avec expiration de 8 h
- **AIPD / impact RGPD** : **à mettre à jour** — les conversations de l'assistant (qui contiennent des extraits de mails) passent d'une mémoire de processus à un stockage partagé avec expiration de 8 h ; les événements temps réel transitent par Redis

## Branches

- `api-mail` (pushed) : feat/task-343-backplane-sse-conversations-redis — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-343-backplane-sse-conversations-redis (depuis `origin/develop` @ `f8e3bef0`)
- `dtos-mss` : aucune branche (création paresseuse par `/develop` si un contrat bouge)
- Choix par défaut conservés (aucune inversion humaine avant `/start`) : backplane portant le DTO complet ; conversations dans Redis.

## Timings

*(généré par `tools/timing/report.sh --task task-343 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 48 min 05 s | 14 (1 min 29 s) | 8 (14 min 41 s) | — | api-mail 14B/8T |
| /sonar | ok | 5 min 48 s | 6 (1 min 05 s) | 21 (20 min 34 s) | 8 (2 min 22 s) | 1 itération(s), api-mail 6B/21T, re-analyse revue 2 |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | 6 min 03 s | — | — | — | e2e ×9 (18 min 15 s), rejoué après revue 2 |
| /review | ok | 50 min 05 s | 1 (4.2 s) | 1 (2 min 23 s) | — | api-mail 1B/1T, APPROVED (3e passage), PR api-mail #263 |
| **Total cycle** | | **1 h 50 min** | **21 (2 min 39 s)** | **30 (37 min 39 s)** | **8 (2 min 22 s)** | |

## Develop log

- **Conventions lues avant le code** : `conventions/csharp.md` (CA1859, CA1869, S4457, CA1068, xUnit1051, S2699 en particulier). Choix par défaut conservés : le backplane porte le **DTO complet**, et les conversations vivent dans **Redis**.
- **Backplane SSE (AUD-18 a)** :
  - `ISseBackplane` et `RedisSseBackplane` : canal `mss:sse:events` ; lecture par `ChannelMessageQueue`, donc dans l'ordre d'arrivée (une souscription par callback est servie en parallèle et la progression pourrait reculer à l'écran).
  - `InProcessSseBackplane` : repli pour un hôte sans Redis ; l'API enregistre toujours Redis.
  - Les trois brokers publient **uniquement** vers le backplane. Chaque réplica, l'émetteur compris, livre depuis son abonnement (`ISseBackplaneListener.Deliver`) : une seule voie de livraison.
  - Clés conservées : (boîte, dossier) pour les mails (task-175), e-mail de la boîte pour les notifications et la progression. Contrat SSE inchangé, prouvé en comparant la sérialisation `SseHelper.JsonOptions` avant et après le transit par Redis.
  - `SseBackplaneSubscriptionService` : service hébergé qui s'abonne **au démarrage** (leçon task-285) et route chaque topic vers son broker.
  - `AddRealtimeBackplane()` : chaque broker est **un** singleton exposé sous deux contrats.
  - Panne Redis : la publication ne lève jamais d'exception. L'échec est journalisé sans contenu et compté dans `mssante_sse_backplane_publish_failures_total{topic}`. Un multiplexeur déconnecté n'est pas attendu. La reprise après coupure est assurée par le multiplexeur, et testée.
- **Conversations IA (AUD-19)** :
  - `IAiConversationStorage` et `RedisAiConversationStorage` :
    - hash `mss:ai:conv:{boîte}:{id}` (`v` version, `d` document) et index `mss:ai:conv-index:{boîte}` ;
    - écriture compare-and-set en **un script Lua** ;
    - TTL glissant de 8 h (`AiConversationOptions.IdleTimeout`) renouvelé à chaque lecture et écriture ; il remplace le `Timer` du processus.
  - `InMemoryAiConversationStorage` : même contrat, pour un hôte sans Redis et pour les tests.
  - `AiConversationStateManager` :
    - devient asynchrone et sans état ;
    - `UpdateConversationAsync(change)` relit la dernière version, applique le changement et écrit à version égale, sinon rejoue (10 essais), puis lève un `ConflictException`, donc un 409 explicite ;
    - `CountActiveConversationsAsync(boîte)` remplace le compteur global ;
    - la boîte est normalisée (casse, espaces).
  - `AiConversationService` : le tour (question + réponse), les jetons et le résumé courant sont **ajoutés** à la dernière version stockée, jamais écrasés.
- **Tests rouges d'abord** (run du 2026-09-29) : brokers au constructeur final mais publication encore **locale** (comportement actuel) ; gestionnaire actuel, un par réplica. **9 rouges, exactement les tests visés** :
  - `AiConversationAcrossReplicasTests.Conversation_CreatedByOneReplica_IsFoundByAnother` (`Assert.NotNull() Failure: Value is null`) ;
  - `SseBackplaneTests` : `TagsUpdated_…`, `Notification_…` et `SyncProgress_PublishedOnAnotherReplica_ReachesTheSubscriber`, `MailEvent_OfAnotherMailboxOrFolder_…`, `EmailsEnriched_ComesOutOfTheBackplaneAsItWentIn`, `Publish_WithoutAnyBackplaneSubscription_DeliversNothingLocally`, `Publish_WhenRedisThrows_…`, `Publish_WhenRedisIsDisconnected_…` ;
  - « même réplica → reçu une seule fois » était déjà vert : c'est attendu, la livraison locale ne sert qu'une fois.
- **Un défaut trouvé par le test de concurrence** : le premier `InMemoryAiConversationStorage` comparait l'entrée entière (`TryUpdate` sur un record), échéance comprise. Une simple lecture, qui renouvelle l'échéance, faisait donc échouer l'écriture de l'autre onglet, et deux onglets s'épuisaient mutuellement (`ConflictException` au 10e essai). Réécrit avec un verrou, la **version** étant seule juge, comme le script Redis.
- **Intégration (Redis Testcontainers)** : `MultiReplicaRedisIntegrationTests`, 12 tests, sur deux « réplicas » composés par les registrations de production et chacun son multiplexeur :
  - livraison entre réplicas des trois topics ; une seule livraison ; contrat SSE à l'octet près ; ordre de 40 progressions ;
  - abonnement posé par le seul démarrage de l'hôte (`PUBSUB NUMSUB`) ; reprise après `CLIENT KILL TYPE pubsub` ; Redis en pause pendant une publication → l'appelant aboutit ;
  - conversation retrouvée par un autre réplica et après redémarrage de son créateur ; tours concurrents de deux onglets (`MaxWriteAttempts / 2` chacun), tous conservés ; TTL de 8 h renouvelé par une lecture ; expiration réelle (TTL de 1 s) et sortie de la liste ; clôture vue par tous.
- **Preuve par mutation** (intégration), chaque mutation annulée ensuite :
  - M1, écriture sans contrôle de version → `TurnsWrittenConcurrentlyByTwoReplicas_AreAllKept` rouge ;
  - M2, lecture sans renouvellement du TTL → `Conversation_LivesForTheIdleTimeout_AndEveryReadRenewsIt` rouge ;
  - M3, sans service d'abonnement au démarrage → 6 tests de backplane rouges.
- Aucune donnée de santé dans les logs : les nouveaux messages ne portent que topic, identifiant de conversation et chemin JSON. L'exception de désérialisation n'est pas journalisée, car elle peut citer le document.
- **Suite complète** (run du 2026-09-30 à 00:07, heure locale) : domain 190/190, infrastructure 665/665, api 1 107/1 107, application 3 272/3 272. Intégration : 652 verts et 16 ignorés (préexistants), **3 rouges hors périmètre, liés à l'heure du run** :
  - `EmailReadingUseCaseTests.FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync`, `ImapFolderServiceIntegrationTests.GetFolderTodayAsync_…` et `GetFolderNotSeenTodayAsync_…` ;
  - cause : entre 00:00 et 02:00 à Paris, la date locale (30/09) et la date UTC (29/09) diffèrent, et « le message du jour » tombe hors du filtre. Le rejeu isolé les donne rouges à l'identique ; ils ne touchent ni le SSE ni l'assistant ;
  - **à ouvrir** : une task de correction, parce que ces tests dépendent de l'horloge du poste (règle d'or).
- **Passe qualité `/simplify`** (§Q : quatre relectures en parallèle — réutilisation, simplification, efficacité, altitude). Appliqué :
  - **Montage** : les implémentations en processus sont des **défauts** (`TryAdd`), et l'API enregistre Redis **explicitement** (`AddRedisRealtimeState()`, à côté de `ISyncStateStore`). Choisir Redis selon la simple présence d'un multiplexeur laissait un hôte mal composé démarrer proprement et reproduire AUD-18 a / AUD-19 en silence. Garde : `SyncControlPlaneIntegrationTests.L_api_partage_le_backplane_sse_et_les_conversations_par_redis` compose le vrai `AddApi`.
  - **Efficacité** : un réplica sans abonné local pour la boîte ne désérialise plus le message (4 réplicas sur 5 reconstruisaient pour rien une liste de `MailDto` enrichis).
  - **Réutilisation** :
    - une seule instance d'options JSON (`SseBackplaneSerializer`, avec `Pack`/`Unpack`) ;
    - `TaggedMetricCounter` extrait de `RefreshStatusCounter` vers `testing.shared`, et reconnu comme marqueur par `MetricCaptureSerialisationScanTests` ;
    - un seul `SseLoopback` dans `testing.shared` ;
    - `AiConversationTesting.Storage/InMemoryManager` pour la mise en place des tests.
  - **Piège évité** : `SseBackplaneTests` capture une métrique sans collection sérialisante. Le test de convention passait parce que le fichier n'était pas encore suivi par Git ; il aurait tourné au rouge après le commit. Classe rattachée à `MailMetricsCaptureCollection`, puis garde rejouée avec les fichiers suivis : 23/23.
  - **Hygiène** : deux journalisations transmettaient un `JsonException`, dont le message peut citer un mail ; elles ne portent plus que le type ou le chemin JSON. Entrée en mémoire fondée sur `StoredConversation`, constantes de champs trompeuses retirées, suppression Redis en parallèle.
  - **Écarté, noté comme piste** : enveloppe binaire sans double échappement JSON (change le format sur le fil) ; classe de base générique pour les trois brokers (duplication antérieure à la task) ; helper pub/sub commun avec `RedisSyncStateStore`.
  - Re-validation : build 0 erreur. Suite complète identique au run précédent (intégration 653 verts, les 3 rouges liés à l'heure du run).
  - Feature et passe qualité sont dans le **même commit** (`3d226f69`) : les nettoyages étaient entremêlés dans l'arbre de travail.
- 42 fichiers au commit, au-dessus du repère d'environ 30 de la règle 5 : le surplus est l'ajustement mécanique des tests existants au nouveau constructeur des brokers et à l'API asynchrone du gestionnaire.

### Reprise après /review (2026-09-30, CHANGES REQUESTED)

Revue indépendante (APPROVED avec suggestions), durcie par `/review` sur deux points. Voir `questions/task-343.md`.

- **Tests rouges d'abord**, sur `eef21c49` : **4 rouges, exactement les tests visés** :
  - `AiConversationTurnPersistenceTests` : conflit à l'enregistrement du tour, panne Redis à l'enregistrement du tour, conversation fermée pendant sa création ;
  - `SseBackplaneTests.SubscriptionService_WhenRedisIsDownAtStartup_DoesNotFailTheHost_AndSubscribesOnceItIsBack`.
- **Démarrage sans Redis** : `SseBackplaneSubscriptionService.StartAsync` ne lève plus jamais d'exception. En cas d'échec, l'abonnement est retenté en arrière-plan toutes les secondes jusqu'à réussite, ou jusqu'à l'arrêt de l'hôte ; `StopAsync` l'annule et l'attend. Sans cela, une panne Redis au déploiement faisait redémarrer les pods en boucle.
  - Intégration : `Replica_StartedWhileRedisDoesNotAnswer_StartsAnyway_AndSubscribesOnceRedisIsBack`, avec Redis en pause au démarrage, puis `NUMSUB` + 1 au retour.
- **Tour non enregistré → erreur explicite** :
  - conflit épuisé → `CONVERSATION_CONFLICT` ;
  - Redis indisponible ou délai dépassé → `CONVERSATION_NOT_SAVED` ;
  - dans les deux cas, pas d'événement `final` : le praticien sait que la réponse lue n'a pas été conservée.
- **Création** : une conversation fermée pendant la génération de son résumé lève `NotFoundException` (404), au lieu de renvoyer un identifiant mort.
- **Résumé courant** : en fire-and-forget, il s'indexe sur `state.UserEmail`, plus sur le contexte d'une requête terminée.
- **Test qui stubait sa prémisse** : le message illisible n'était jamais désérialisé (aucun abonné). Il vit désormais dans `SubscriptionService_AfterAnUnreadableMessage_KeepsDeliveringTheNextOnes`, avec un abonné, et il est **prouvé rouge par mutation** (sans le `try/catch` de `Dispatch`, la `JsonException` remonte). Son message cite le contenu, ce qui confirme qu'on ne journalise que le type.
- **Notées comme suites, non traitées ici** : un Redis figé fait attendre chaque publication `asyncTimeout` ; un résumé tardif peut écraser un plus récent (défaut antérieur à la task) ; il manque une métrique de taille des charges diffusées (limite `client-output-buffer-limit pubsub`).
- **Règle d'or** : nouvelle consigne `memoire-vers-redis-chemins-faillibles` dans `conventions/csharp.md`.

### Reprise après /review, 2e passage (2026-09-30, CHANGES REQUESTED)

- **Bloquant** : chaque `SubscribeAsync` raté laissait une **file orpheline** attachée au multiplexeur.
  - Dans StackExchange.Redis 2.7.27, la `ChannelMessageQueue` est rattachée à l'abonnement suivi **avant** le contact avec le serveur. En cas d'échec, elle reste attachée, et l'appelant ne la reçoit jamais.
  - Effet : chaque réessai du démarrage en créait une. Redis revenu, chacune aurait accumulé **sans borne** une copie de chaque message du backplane (mails enrichis compris) pendant toute la vie du pod.
  - Le test `NUMSUB` ne le voyait pas : le serveur ne compte qu'un abonné.
- **Rouge d'abord** : `FailedSubscriptionAttempts_LeaveNoOrphanQueueBehind` (Redis en pause, 3 échecs, puis 1 succès) → **4 files attachées au lieu de 1**. Correctif : la file est détachée (`UnsubscribeAsync`, fire-and-forget) avant de rendre l'échec ; le test passe à 1.
- **Suggestion retenue** : si l'achèvement de la création échoue (résumé, Redis), la conversation déjà créée est fermée au mieux, au lieu de rester listée 8 h sans résumé ni digests.
  - Rouge d'abord : `CreateConversation_WhenItsCompletionCannotBeStored_LeavesNoStubBehind` (`Assert.Empty` en échec), puis vert.
- Suite complète : application 3 278, api 1 107, infrastructure 665, domain 190. Intégration : 655 verts et les 3 rouges préexistants liés à l'heure.
- Commit `112c5241`.

## Sonar log

Mode A, serveur SonarQube 9.9.8, projet `healthplatform-api-mail`. Deux analyses complètes (begin, build Release, 5 passes OpenCover, end).

- **Analyse 1** (`3d226f69`) : QG OK, mais **3 findings sur les lignes de la branche**, tous `csharpsquid:S3604`, dans `InMemoryAiConversationStorage` : `_gate = new()`, `_entries = []`, et `Stored { get; } = stored` du type interne `Entry`.
  - C'est une **récidive** : `conventions/csharp.md` porte deux entrées S3604, et seuls leurs titres avaient été lus avant le code.
  - Variante nouvelle, consignée : même un initialiseur qui ne dérive d'**aucun** paramètre est signalé dans une classe à constructeur primaire.
- **Correction** (`eef21c49`) : constructeur explicite ; `Entry` devient un record positionnel.
  - Au passage, le test « deux onglets » est rendu **déterministe** : 10 tours d'affilée par onglet laissaient un onglet gagner 10 fois de suite et l'autre épuiser ses 10 essais (1 rouge sur 3 rejoués). Il fait désormais `MaxWriteAttempts / 2` tours par onglet, puisqu'un essai perdu est une écriture gagnée par l'autre. 30/30 verts rejoués.
- **Analyse 2** (`eef21c49`) : ✓ **0 finding** sur les fichiers de la branche, QG **OK**.
- **Analyse 3**, après la reprise de revue (`a403200f`) : ✓ **0 finding** sur la branche, QG **OK**, new_coverage 98,1 %.
- **Analyse 4**, après le 2e passage (`112c5241`) : ✓ **0 finding** sur la branche, QG **OK**, new_coverage 98,0 %, 10 smells (legacy).
- Phase 2 (legacy) : 0 itération. Les mêmes 10 findings structurels (S107, S3604) restent, acceptés en best-effort.
- Tests sous OpenCover (analyse 3) : domain 190, application 3 277, infrastructure 665, api 1 107, integration 654 (+16 ignorés). Analyses 1 et 2 : domain 190, application 3 272, infrastructure 665, api 1 107, integration 653 (+16 ignorés). Les 3 rouges liés à l'heure du run (filtres « du jour », entre 00:00 et 02:00 à Paris) sont documentés dans le Develop log.

### KPIs qualité (baseline → final)

Baseline = dernière analyse avant la task (2026-09-29, task-347).

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98,3 % | 98,0 % | −0,3 pt |
| Bugs / Vulnerabilities / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | ±0 |
| Code smells | 10 | 10 | ±0 (3 introduits puis corrigés) |
| Coverage (projet) | 98,2 % | 98,2 % | ±0 pt |
| Duplication | 0,5 % | 0,4 % | −0,1 pt |

## Lint log

- `/lint-angular` : skipped — client-angular non touché par task-343.
- `/lint-mobile` : skipped — client-mobile non touché par task-343.

## E2E log

Run du 2026-09-30, rejoué après le 2e passage de revue, sur `112c5241` : le code que `/review` valide. Il avait déjà été vert sur `eef21c49` et `a403200f`.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 22 verts, 0 flaky, 0 rouge, 0 quarantaine | 2 min 56 s |
| angular | api-mail touché | ✅ verte | 22 verts, 0 flaky, 0 rouge, 0 quarantaine | 2 min 27 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `feat/task-343-backplane-sse-conversations-redis` (inchangé par la task).
- Quarantaines : aucune. Divergences ouvertes : aucune.
- Flaky : aucun sur ce run. Le run précédent (`eef21c49`) avait relevé `[angular] E2E-INBOX-001` vert au 2e essai ; il est inscrit au registre de `conventions/e2e.md` (1re occurrence).
- Les brokers SSE passent par le backplane Redis, y compris sur le banc e2e : l'API y est composée par `AddApi`, et l'AppHost fournit Redis. Aucun parcours n'a régressé.
- Parcours touchés sans spec e2e modifié : aucun (aucun fichier client touché).
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143 libres, aucun conteneur `e2e-*` résiduel).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/263, label `awaiting-human-merge`, branche `feat/task-343-backplane-sse-conversations-redis` (`112c5241`).
- `dtos-mss` : aucun contrat modifié, donc aucune branche.

## Code Review Summary

- Verdict : **APPROVED** au 3e passage (revue indépendante), le 2026-09-30.
- 1er passage : APPROVED avec suggestions, **durci en CHANGES REQUESTED par `/review`**. Corrigé dans `a403200f` :
  - démarrage impossible si Redis est indisponible (les pods auraient redémarré en boucle) ;
  - tour de parole non enregistré signalé en `SERVER_ERROR` générique, au lieu d'une erreur explicite.
- 2e passage : CHANGES REQUESTED. Corrigé dans `112c5241` :
  - chaque `SubscribeAsync` raté laissait une file orpheline sur le multiplexeur ;
  - une ébauche de conversation restait listée si sa création échouait.
- Suites non traitées (Redis figé, résumé tardif, taille des charges pub/sub, AIPD) : `questions/task-343.md`.
- Validation finale sur `112c5241` :
  - tests : domain 190, application 3 278, infrastructure 665, api 1 107, integration 655, plus les 3 rouges préexistants liés à l'heure, prouvés sur `develop` ;
  - Sonar : QG OK, 0 finding sur la branche ;
  - `/e2e` : 22/22 sur les deux voies.

## Amélioration continue (règle d'or)

- **Récidive S3604** sur du code frais (×3) : `conventions/csharp.md` avait été lu par ses seuls titres. Compteur à 2, variante consignée (tout initialiseur d'instance, dès qu'il y a un constructeur primaire). La leçon porte sur la **lecture** : lire les consignes en entier, pas les titres.
- **Nouvelle consigne** `memoire-vers-redis-chemins-faillibles` (`conventions/csharp.md`) :
  - un état qui quitte la mémoire rend faillibles le démarrage et les flux en streaming ;
  - un `SubscribeAsync` raté laisse une file orpheline dans StackExchange.Redis ;
  - le message d'une `JsonException` cite le document.
- **Test instable par construction** (deux onglets × 10 tours, borne à 10 essais) : borne rendue explicite (`MaxWriteAttempts / 2`), justification écrite dans le test.
- **Test qui supposait sa prémisse** (message illisible jamais désérialisé) : réécrit et prouvé rouge par mutation.
- **Garde de convention qui ne voit que les fichiers suivis** : `MetricCaptureSerialisationScanTests` passait parce que `SseBackplaneTests` n'était pas encore suivi par Git ; il aurait tourné au rouge après le commit. Le marqueur `TaggedMetricCounter` y est ajouté, et la garde a été rejouée après staging.
- **Registre des flaky** : `[angular] E2E-INBOX-001`, 1re occurrence (`conventions/e2e.md`).
- **Task à ouvrir** : les tests dépendants de l'horloge du poste (`questions/task-343.md`).
