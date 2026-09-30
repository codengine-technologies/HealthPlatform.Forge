# todo-task-343.md — Plusieurs serveurs, un seul comportement : les notifications temps réel et les conversations de l'assistant ne dépendent plus du serveur qui répond

**Repos**: api-mail, client-mobile, client-angular *(clients ajoutés le 2026-09-30, extension humaine : parcours e2e temps réel et assistant)*
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


### Extension du périmètre (2026-09-30, demande humaine)

> **Pourquoi.** Au premier `/review`, les mécanismes étaient prouvés contre un vrai Redis, mais
> **aucun parcours du médecin** ne couvrait les notifications en temps réel ni l'assistant. Les
> 22 parcours e2e passaient déjà avant la task. L'humain demande de couvrir ces deux parcours
> **dans cette branche**. Arbitrages du 2026-09-30 :
> - faux fournisseur IA au protocole Ollama dans l'outillage e2e, avec des réponses scriptées : le banc cesse d'appeler OpenAI ;
> - les deux clients sont ajoutés aux `**Repos**` ;
> - des `data-testid` sont ajoutés dans weda2.
>
> Le banc e2e fait tourner l'API sur **5 réplicas** derrière un proxy qui répartit les requêtes.
> Ces parcours exercent donc exactement ce que la task corrige, et doivent être **rouges ou
> instables sur `develop`**, puis verts sur la branche.

- **E2E-LIVE-001 — Recevoir un nouveau message en temps réel, sans recharger** :
  - un compte rendu de biologie arrive pendant que la boîte est ouverte, et un autre appareil déclenche la synchronisation ;
  - la notification et la nouvelle ligne apparaissent sans rechargement, puis le signalement d'urgence posé par l'analyse automatique.
- **E2E-AI-001 — Interroger l'assistant sur des messages sélectionnés** :
  - la sélection de messages ouvre l'assistant, qui affiche un résumé initial ;
  - deux questions de suite reçoivent leur réponse ;
  - la conversation est relue du serveur avec ses quatre tours.
- **Outillage** (`api-mail`) :
  - faux fournisseur Ollama ;
  - préférences de notification dans le seed ;
  - dépôt d'un compte rendu de biologie à la demande ;
  - drapeaux IA forcés dans le profil e2e.

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
- [ ] Scénarios **E2E-LIVE-001** et **E2E-AI-001** ajoutés dans `Api/Mail/e2e/scenarios.yml` et implémentés dans chaque client où ils sont requis (mobile, angular)
- [ ] Les deux parcours sont **prouvés rouges ou instables sur `develop`** (5 réplicas) et verts sur la branche ; preuve par mutation sur les écouteurs SSE et sur la persistance des tours
- [ ] Le banc e2e ne contacte plus aucun fournisseur IA externe (faux fournisseur Ollama)

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

- `client-mobile` (pushed) : feat/task-343-backplane-sse-conversations-redis — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-343-backplane-sse-conversations-redis (depuis `origin/develop` @ `01933dd`, 2026-09-30)
- `client-angular` (code-only) : la forge écrit sur la branche courante `feature/nova-rewriting-mss` ; l'humain gère le commit, le push et la PR TFS (hors `environment.ts`)

## Timings

*(généré par `tools/timing/report.sh --task task-343 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 1 h 03 min | 22 (3 min 00 s) | 11 (18 min 22 s) | — | api-mail 20B/9T, client-mobile 1B/1T, client-angular 1B/1T, extension e2e LIVE-001 / AI-001 |
| /sonar | ok | 6 min 52 s | 7 (1 min 24 s) | 26 (25 min 54 s) | 10 (3 min 01 s) | 1 itération(s), api-mail 7B/26T, extension e2e |
| /lint-angular | ok | 1 min 50 s | — | — | — | 1 itération(s), 29 erreurs prettier (fichiers e2e neufs) corrigées par --fix |
| /lint-mobile | ok | 34 s | — | — | — | all files pass |
| /e2e | ok | 6 min 44 s | — | — | — | e2e ×12 (24 min 38 s), extension : 24/24 + 24/24 |
| /review | ok | 6 min 18 s | 1 (4.2 s) | 1 (2 min 23 s) | — | api-mail 1B/1T, APPROVED (4e passage), PR api-mail #263 + mobile #82 |
| /tech-writer | ok | 55 s | — | — | — | extension e2e |
| **Total cycle** | | **1 h 27 min** | **30 (4 min 28 s)** | **38 (46 min 40 s)** | **10 (3 min 01 s)** | |

Autres commandes mesurées : lint ×4 (54 s)

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

### Extension e2e (2026-09-30) — parcours temps réel et assistant

- **Outillage api-mail** (`0029505d`) :
  - `fake-ai` : faux fournisseur au protocole Ollama, avec des réponses scriptées (`FakeAiScript`) ;
  - `deliver` : remise du compte rendu `cr-bio-temps-reel` ;
  - préférences de notification dans le seed : sans elles, `NewMailNotifier` ignorait tout ;
  - profil e2e pointé sur le faux fournisseur : le banc n'appelle plus aucun fournisseur réel ;
  - `FeatureFlags:ForcedOn`, en liste blanche `Development` (`ForcedOnFeatureFlagService`) ;
  - catalogue : `E2E-LIVE-001` et `E2E-AI-001`, requis sur mobile et angular.
- **Protocole** : prouvé avec le **vrai** connecteur Ollama de l'API (`FakeAiTests` : réponse unique, diffusion, embeddings).
- **Mobile** (`24dce09`) : `specs/live-ai.spec.ts` et `support/e2e-backend.ts` (« un autre appareil »), avec les en-têtes du bypass factorisés dans `headless.ts`.
- **weda2** (code-only, à commiter sur TFS par l'humain, hors `environment.ts`) : `data-testid` ajoutés sur le bandeau d'urgence, le panneau de l'assistant, le bouton IA de la sélection et les cartes du volet de lecture. Plus `e2e/mss-e2e/specs/live-ai.e2e.ts` et `support/e2e-backend.ts`.
- **Vert sur la branche** : mobile 24/24 et weda2 24/24 (22 parcours existants + 2), contre les 5 réplicas.
- **Rouge sans le correctif** (backplane et stockage des conversations remis par processus, 5 réplicas, 3 runs) :
  - `E2E-AI-001` rouge **3/3** (« réponse à la question n°1 », deux fois ; « n°2 », une fois) ;
  - `E2E-LIVE-001` rouge **2/3** (« aucune notification » ; vert une fois, quand le hasard mettait la synchronisation sur le réplica du flux).
- **Preuve par mutation côté client** (chaque fois rouge sur l'assertion visée, puis restauré et vert) :
  - mobile M1, notification ignorée → « notification « Nouveau message » » ;
  - mobile M2, `TagsUpdated` ignoré → « le signalement d'urgence arrive en temps réel » ;
  - weda2 MA1 et MA2 : mêmes rouges.
- **Trois « verts qui mentent » trouvés en route, et corrigés** :
  - le tag d'urgence était déjà posé quand l'app chargeait la ligne : M2 restait verte. Le faux fournisseur retarde désormais ses réponses de classification de 5 s, et le parcours prouve **l'absence**, puis **l'arrivée**, du signalement ;
  - deux mutations n'avaient pas compilé (TS2339, TS6133), et le serveur de dev continuait de servir l'ancien bundle ;
  - un prédicat `waitForResponse` réécrit en ligne de commande était devenu un commentaire JavaScript, donc acceptait tout POST.
  - Consignés dans `conventions/e2e.md` : `temps-reel-deja-charge`, `mutation-non-servie`, `predicat-de-reponse`, `ligne-de-biologie`.
- **Passe qualité** (quatre angles, deux relectures) :
  - retiré : champ de manifeste et sortie de `deliver` morts, doublons du manifeste et des en-têtes du bypass (un `bypassHeaders()` par dépôt) ;
  - forçage des drapeaux en **liste blanche** `Development` via `IHostEnvironment`, et non plus un simple refus de Production ;
  - écartés : routage du faux fournisseur par nom de modèle (l'API n'en a qu'un pour tout Ollama), délai de classification limité au seul message du parcours (indiscernable du compte rendu seedé).
- **Validation** :
  - api-mail : 5 915 verts ;
  - mobile : build vert, 947/947, après un échec **instable** de `MailboxSwitcherComponent` (erreur interne Ionic `onAriaChanged`, aucun fichier `src/` modifié, vert deux fois de suite) ;
  - weda2 : build vert, 2 575 tests verts (11 projets) ;
  - types des deux projets e2e : OK.

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
- **Analyse 5**, extension e2e (`0029505d`) : ✓ **0 finding** sur la branche, QG **OK**, new_coverage 98,1 %, 10 smells (legacy). api 1 126 (+2 cas du forçage en liste blanche).
- Phase 2 (legacy) : 0 itération. Les mêmes 10 findings structurels (S107, S3604) restent, acceptés en best-effort.
- Tests sous OpenCover (analyse 3) : domain 190, application 3 277, infrastructure 665, api 1 107, integration 654 (+16 ignorés). Analyses 1 et 2 : domain 190, application 3 272, infrastructure 665, api 1 107, integration 653 (+16 ignorés). Les 3 rouges liés à l'heure du run (filtres « du jour », entre 00:00 et 02:00 à Paris) sont documentés dans le Develop log.

### KPIs qualité (baseline → final)

Baseline = dernière analyse avant la task (2026-09-29, task-347).

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98,3 % | 98,1 % | −0,2 pt |
| Bugs / Vulnerabilities / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | ±0 |
| Code smells | 10 | 10 | ±0 (3 introduits puis corrigés) |
| Coverage (projet) | 98,2 % | 98,2 % | ±0 pt |
| Duplication | 0,5 % | 0,4 % | −0,1 pt |

## Lint log

- Premier passage (backend seul) : `/lint-angular` et `/lint-mobile` sautés, clients non touchés.
- **Extension e2e** — `/lint-angular` (`nx affected -t lint --base=origin/next --projects=tag:scope:mss`) :
  - référence : 29 erreurs Prettier, toutes dans les deux fichiers e2e neufs du projet `mss-e2e` ;
  - itération 1, `nx run mss-e2e:lint --fix` : **0 erreur**, lint vert sur 12 projets. Seuls les deux fichiers neufs ont été réécrits ;
  - avertissements restants acceptés : `@example` vides (`jsdoc/require-example`), au même style que les utilitaires existants de la suite.
  - Code-only : aucune opération git.
- **Extension e2e** — `/lint-mobile` : `npm run lint` → « All files pass linting ». Les fichiers e2e sont hors du périmètre de lint du dépôt (`src/**`).

## E2E log

Run du 2026-09-30, après l'extension e2e : api-mail `0029505d`, mobile `24dce09`, weda2 sur la branche courante (code-only). C'est le code que `/review` valide.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et client-mobile touchés | ✅ verte | 24 verts (22 + LIVE-001 + AI-001), 0 flaky, 0 rouge, 0 quarantaine | 3 min 14 s |
| angular | api-mail et client-angular touchés | ✅ verte | 24 verts (22 + LIVE-001 + AI-001), 0 flaky, 0 rouge, 0 quarantaine | 3 min 00 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task, avec **E2E-LIVE-001** et **E2E-AI-001** ajoutés (v1, requis sur les deux clients).
- Banc : l'API tourne sur **5 réplicas** derrière un proxy qui répartit les requêtes, et le fournisseur IA est le faux fournisseur scripté (aucun appel externe).
- **Rouge sans le correctif** (état par processus, 3 runs) : AI-001 rouge 3/3, LIVE-001 rouge 2/3. **Preuve par mutation côté client** : notification ignorée, puis `TagsUpdated` ignoré, rouges sur l'assertion visée, sur les deux clients (voir le Develop log).
- Quarantaines : aucune. Divergences ouvertes : aucune.
- Flaky : aucun sur ce run. Au registre de `conventions/e2e.md` : `[angular] E2E-INBOX-001` (1 occurrence, run précédent de cette task) et `[angular] E2E-FOLDER-001` (task-347).
- Parcours touchés sans spec e2e modifié : aucun. Côté weda2, seuls des `data-testid` ont été ajoutés aux templates.
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143 et 11534 libres, aucun conteneur `e2e-*` résiduel).

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
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.
## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/263, branche `feat/task-343-backplane-sse-conversations-redis` (`0029505d`). Label `awaiting-human-merge`.
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/82, même branche (`24dce09`), label `awaiting-human-merge`. Parcours e2e seulement, aucun fichier `src/`.
- `client-angular` : **code-only**. L'humain commite, pousse sur TFS et ouvre la PR, sur la branche courante `feature/nova-rewriting-mss`, **sans** les deux `environment.ts`. Fichiers :
  - `front/libs/mss/src/features/mail/components/ai-chat-panel/ai-chat-panel.component.html` (`data-testid`)
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html` (`data-testid` du bandeau d'urgence)
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html` (`data-testid` du bouton IA)
  - `front/libs/mss/src/features/settings/mss-settings.component.html` (`data-testid` du volet de lecture)
  - `front/e2e/mss-e2e/specs/live-ai.e2e.ts` (nouveau)
  - `front/e2e/mss-e2e/support/e2e-backend.ts` (nouveau)
  - `front/e2e/mss-e2e/support/session.ts` (`bypassHeaders` factorisé)
  - `front/e2e/mss-e2e/run.mjs` (variables de l'outillage)
- `dtos-mss` : aucun contrat modifié, donc aucune branche.

## Code Review Summary

- Verdict : **APPROVED** au 4e passage (revue indépendante), le 2026-09-30.
- Passages 1 à 3 (backend), résumés dans la Reprise :
  - démarrage impossible sans Redis ;
  - tour de parole non enregistré signalé en `SERVER_ERROR` ;
  - files orphelines après un abonnement raté ;
  - puis APPROVED.
- 4e passage (extension e2e) : APPROVED.
  - Sécurité : `FeatureFlags:ForcedOn` est refusé en Staging et en Production, dont les configmaps posent `ASPNETCORE_ENVIRONMENT=Staging`. Faux fournisseur et forçage n'existent que dans le profil e2e. Aucun secret ni aucune donnée de santé dans les arguments de processus.
  - Parcours : AI-001 prouve bien la relecture d'un tour par un autre réplica. Pour LIVE-001, la notification est la preuve entre réplicas, et la mutation MA2 montre que le rafraîchissement de weda2 (30 s) ne ramène pas le tag.
  - Protocole du faux fournisseur : correct, prouvé avec le vrai connecteur.
- Suggestions non traitées, dans `questions/task-343.md` :
  - « tag absent à l'arrivée de la ligne » exposé à une synchronisation de plus de 5 s ;
  - message remis non nettoyé si `waitForNewUid` échoue ;
  - `finally` weda2 qui peut masquer l'erreur d'origine ;
  - délai de classification appliqué à tous les mails ;
  - notifications du seed pendant COMPOSE-001 ;
  - `content` lu par `GetValue<string>` ;
  - `DistinctQuestions`.
- Validation finale :
  - api-mail : 5 917 verts, QG OK, 0 finding sur la branche ;
  - mobile : build vert, 947/947 ;
  - weda2 : build vert, 2 575 verts, lint MSS 0 erreur ;
  - `/e2e` : mobile 24/24 et weda2 24/24, 0 flaky, parité verte.

## Amélioration continue (règle d'or)

- **Récidive S3604** (×3, code frais) : `conventions/csharp.md` avait été lu par ses titres seulement. Compteur à 2, variante consignée.
- **Nouvelle consigne C#** `memoire-vers-redis-chemins-faillibles` : démarrage, flux en streaming, file orpheline de StackExchange.Redis, message d'une `JsonException`.
- **Quatre consignes e2e** (`conventions/e2e.md`) :
  - `temps-reel-deja-charge` : un tag déjà posé au chargement ne prouve pas le temps réel ;
  - `mutation-non-servie` : une mutation qui ne compile pas laisse servir l'ancien bundle ;
  - `predicat-de-reponse` : une regex réécrite en ligne de commande est devenue un commentaire ;
  - `ligne-de-biologie` ;
  - et `preuve-par-mutation` passe à 4 occurrences.
- **Le banc e2e ne contacte plus aucun fournisseur IA externe** : une dépendance et un coût retirés, conformément au principe « aucun service externe » du filet.
- **Deux tests instables par construction** rendus déterministes : bornes de concurrence, et délai de classification du faux fournisseur.
- **Garde de convention qui ne voit que les fichiers suivis** (`MetricCaptureSerialisationScanTests`) : piège signalé, garde rejouée après staging.
- **Tasks à ouvrir** : tests dépendants de l'horloge du poste, et suites de la revue (`questions/task-343.md`).
