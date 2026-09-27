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
