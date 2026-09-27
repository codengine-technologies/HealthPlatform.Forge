# todo-task-336.md — Plusieurs serveurs, un seul comportement : conversations IA, notifications en temps réel et boîte suivie ne dépendent plus du serveur qui répond

**Repos**: api-mail, client-blazor, client-mobile
**Dependencies**: — (aucune)
**Epic**: E011
**Single frontend**: false
**Priorité**: **2** — avec plusieurs réplicas (4 dans le manifeste de production, 5 dans l'AppHost), l'assistant IA perd sa conversation ~3 fois sur 4, la plupart des tags d'urgence n'arrivent jamais à l'écran, un même mail peut être dupliqué, et après une bascule de boîte le praticien reçoit les notifications de la mauvaise boîte.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-18**, **AUD-19**, **AUD-21**). Cause commune :
> un état tenu **en mémoire d'un processus** alors que les requêtes d'un même praticien se répartissent
> entre réplicas (mémoire « api-mail = 5 réplicas, pool IMAP par processus »).

## Ce qui est établi (develop @ `14d58398`)

1. **Conversations IA (AUD-19)** — `AiConversationStateManager.cs:12` : `ConcurrentDictionary` en Singleton
   (`Api/DependencyInjection.cs:133`). Conversation créée sur le pod 1, message envoyé au pod 2 :
   `CONVERSATION_NOT_FOUND`. `DevOps/Prod/api.yaml:7` : 4 réplicas, Service sans affinité.
2. **Notifications (AUD-18 a)** — `SseNotificationBroker`, `SseMailEventBroker`, `SseSyncProgressBroker` :
   dictionnaires en mémoire ; `AddNewMailConsumer.cs:331` (`NotifyTagsUpdatedAsync`) ne publie que dans
   le broker local, or RabbitMQ livre le message à un réplica quelconque → ~(N−1)/N des tags d'urgence
   n'atteignent pas le flux SSE du praticien.
3. **Promotion concurrente (AUD-18 b)** — `MailClientSessionManager.cs:456-473` (verrou local),
   `MailRepository.UpdateExistingMailWithContentAsync:574-660`, `MailDataContext.cs:166` (index
   `MailContents.MailId` **non unique**) : deux appareils du même praticien, routés vers deux réplicas,
   promeuvent la même ligne « en-têtes seuls » → contenu, documents et biologie dupliqués.
4. **Boîte suivie par le flux SSE (AUD-21)** — `UserContextEnricherMiddleware.cs:596-605, 722-730`,
   `MailEventsController.cs:71, 93-95` : `EventSource` ne pose aucun en-tête ; le middleware sélectionne
   la boîte **par défaut** ; le contrôleur ne lit `?mailbox=` que si le contexte est vide (jamais). Aucun
   client n'envoie d'ailleurs `?mailbox=` (mobile `mail-events-stream.service.ts:66-69`, Blazor
   `MailSseService.cs:162-176`). Le repli brut du contrôleur (`:93-95`) serait non validé s'il devenait atteignable.

## Objective

Que le comportement vu par le praticien soit **identique quel que soit le réplica** qui traite chacune
de ses requêtes, et que le flux temps réel suive la **boîte affichée**.

### Périmètre

1. **Conversations IA** partagées entre réplicas (Redis, TTL 8 h) — ou affinité exigée et documentée si
   `/develop` établit que c'est la seule voie ; choix justifié.
2. **Backplane SSE** : une publication sur un réplica atteint les abonnés de tous les réplicas (Redis pub/sub) ;
   clés (boîte, dossier) de task-175 conservées.
3. **Promotion unique** : une seule ligne de contenu par mail, garantie par la base (contrainte unique sur
   `MailContents(MailId)` avec gestion du conflit) ou par un verrou distribué.
4. **SSE et boîte** : pour les routes SSE seulement, le middleware lit `?mailbox=` quand l'en-tête est
   absent et le **valide contre le registre** comme l'en-tête ; le repli brut du contrôleur est supprimé.
5. **Clients** : Blazor et mobile ouvrent le flux avec `?mailbox=` de la boîte affichée et le rouvrent à la bascule.

### Hors périmètre

- Le pool IMAP par processus et le fan-out des sessions (mémoire E011) — inchangés.
- L'isolation de l'assistant IA sur le Kernel partagé (task-328).

## Definition of Done

- [ ] Build passes (0 errors) sur les 3 repos ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] conversation créée par une instance du gestionnaire, lue par une autre instance → trouvée
  - [ ] publication d'un événement sur un broker, abonné sur une autre instance → reçu
  - [ ] deux promotions concurrentes de la même ligne → une seule ligne de contenu
  - [ ] flux SSE ouvert avec `?mailbox=B` sans en-tête → abonné à la boîte **B** ; `?mailbox=` d'une boîte non rattachée au compte → 403 `ProblemDetails`
- [ ] Migration éventuelle (contrainte unique) auditée selon la règle 7c ; doublons existants traités par la migration ou une reprise documentée
- [ ] Test d'intégration endpoint (règle 1b) : `GET` du flux SSE avec `?mailbox=` validé de bout en bout
- [ ] Clients : test de composant/service — le flux est rouvert avec la nouvelle boîte à la bascule (Blazor bUnit, mobile Jasmine)
- [ ] `data-testid` et libellés (FR mobile / Localizer Blazor) sur tout élément ajouté
- [ ] Aucune donnée de santé dans les messages du backplane au-delà de ce que le flux SSE porte déjà

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (5 réplicas de l'AppHost) ; mobile `cd Client/Mobile && npm start` ; Blazor en parallèle.
2. **IA** : ouvrir l'assistant, poser trois questions successives → la conversation continue à chaque fois. Avant : « conversation non trouvée » la plupart du temps.
3. **Tags** : recevoir cinq mails de test porteurs d'un compte rendu de biologie urgent → le tag « Urgent » apparaît en temps réel sur les cinq. Avant : sur une minorité.
4. **Deux appareils** : ouvrir le même mail non enrichi simultanément sur mobile et Blazor → un seul exemplaire des documents dans le dossier patient.
5. **Multi-boîtes** : praticien à deux boîtes, basculer sur B → les nouveaux mails de B arrivent en temps réel, aucun de A. Avant : l'inverse.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité de fonctionnalités existantes (notification temps réel, multi-boîtes E016)
- **INS** : non applicable — aucune INS ajoutée au backplane
- **Authentification PS** : PSC / e-CPS inchangée
- **Habilitations** : **au cœur pour le SSE** — la boîte suivie est validée contre le registre (compte × adresse), jamais crue telle quelle
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ouverture de flux sur une boîte non rattachée refusée et tracée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Redis dans le périmètre HDS ; conversations IA stockées avec TTL
- **AIPD / impact RGPD** : à mettre à jour — les conversations IA (contenant des éléments de mails) passent d'une mémoire de processus à un stockage partagé avec TTL 8 h
