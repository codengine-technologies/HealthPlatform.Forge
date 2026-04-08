# todo-back-notifications-realtime-040 — Backend : déclenchement réel des notifications

**Dependencies**: aucune (les DTOs et préférences existent déjà depuis done-back-notifications-022)
**Feature**: tests/Features/Mss/PreferencesNotification.feature
**Repo**: api-mail (path: `Api/Mail`)
**Touches**: dtos (nouveau `NotificationPayloadDto`)
**Module**: Api/Mail

## Contexte

La tâche `done-back-notifications-022` a livré la persistance des `NotificationPreferences` dans `UserSettings` mais **aucun code ne lit ces préférences pour déclencher une notification**. Les toggles sont des valeurs mortes. Un test manuel a confirmé : aucune notification n'apparaît lors de la réception d'un nouveau mail.

Cette tâche comble le trou : brancher les préférences sur le pipeline de sync IMAP et émettre des événements temps-réel vers les frontends via **deux canaux** (SignalR pour Blazor, SSE pour Angular).

## Objectif

Lorsqu'un nouveau mail arrive lors d'une synchronisation IMAP, émettre un événement "notification" vers le frontend du user **uniquement si ses préférences l'autorisent**.

## Travail à réaliser

### 1. DTO partagé (repo `dtos`)

Créer `NotificationPayloadDto` :
```
Kind: enum { NewMail, AbnormalBiology }
Title: string       // "Nouveau message de Dr X" ou "Résultat biologique anormal"
Body: string        // subject du mail ou résumé
MailUid: uint
FolderPath: string
ReceivedAt: DateTimeOffset
Urgency: UrgencyLevel    // réutilise l'enum existant
PlaySound: bool     // reflète EnableSoundNotification
ShowDesktop: bool   // reflète EnableDesktopNotification
```

→ Publier via `/publish-dtos` **avant** de démarrer le reste.

### 2. Service `NewMailNotifier` (application layer)

Créer `src/Application/Services/Interfaces/INewMailNotifier.cs` et son implémentation `src/Application/Services/Implementation/NewMailNotifier.cs` :

```csharp
public interface INewMailNotifier
{
    Task HandleNewMailAsync(string userEmail, MailDto mail, CancellationToken ct);
    Task HandleAbnormalBiologyAsync(string userEmail, MailDto mail, CancellationToken ct);
}
```

**Règles métier** (testables unitairement, sans I/O) :
- Si `NotificationPreferences == null` → rien (valeurs par défaut = false pour tout)
- Si `EnableNewMail == false` **et** `Kind == NewMail` → rien
- Si `EnableUrgentOnly == true` **et** `mail.Urgency != Urgent` → rien
- Si `EnableAbnormalBiology == false` **et** `Kind == AbnormalBiology` → rien
- Sinon : construire `NotificationPayloadDto` avec `PlaySound = prefs.EnableSoundNotification`, `ShowDesktop = prefs.EnableDesktopNotification`

Le service dispatche vers les 2 canaux en parallèle (SignalR + SSE broadcaster — voir points 3 et 4).

### 3. Canal SignalR (existant)

Étendre `MailEnrichmentNotifier` ou créer un nouveau `NotificationHubNotifier` qui expose :
```csharp
public async Task NotifyUserAsync(string userEmail, NotificationPayloadDto payload, CancellationToken ct)
    => await hubContext.Clients.Group(userEmail).SendAsync("NotificationReceived", payload, ct);
```

Événement SignalR émis : `"NotificationReceived"` sur le group `userEmail`. Le client Blazor s'abonne via le user group déjà existant (`MailHub.JoinUserGroup`).

### 4. Canal SSE (nouveau)

Créer un endpoint `GET /api/v1/mail/notifications/stream` qui :
- Content-Type: `text/event-stream`
- Long-lived connection (async loop)
- Authentifie le user (JWT ou mécanisme actuel)
- S'abonne à un `Channel<NotificationPayloadDto>` scoppé par `userEmail` (singleton `ISseNotificationBroker`)
- Écrit chaque payload au format SSE :
  ```
  event: notification
  data: {"Kind":"NewMail","Title":"...","Body":"...",...}
  
  ```
- Heartbeat toutes les 15 secondes (`: heartbeat\n\n`) pour éviter les timeouts proxy
- Cleanup de l'abonnement en cas de `HttpContext.RequestAborted`

`ISseNotificationBroker` : singleton avec un `ConcurrentDictionary<string, List<Channel<NotificationPayloadDto>>>` keyed par userEmail. `NewMailNotifier` appelle `broker.Publish(userEmail, payload)` qui pousse dans tous les channels du user (un par connexion Angular ouverte).

### 5. Hook dans le pipeline de sync

Identifier l'endroit où la sync IMAP détecte un nouveau mail (très probablement `ImapSyncService` ou `PendingActionService.ProcessActionAsync` selon l'architecture PendingActions livrée dans drafts). Ajouter l'appel :
```csharp
await newMailNotifier.HandleNewMailAsync(userEmail, mailDto, cancellationToken);
```

**Attention** : ne pas déclencher de notification pour les mails chargés lors d'une sync initiale massive (par exemple les 500 premiers mails d'une boîte). Règle : uniquement pour les mails dont `ReceivedAt > dernierSync.CompletedAt`. Lire le `LastSyncAt` depuis `UserSettings` ou équivalent.

### 6. Tests

**Unitaires** (`NewMailNotifier`) :
- EnableNewMail=false → aucun dispatch
- EnableNewMail=true + Urgency=Normal → dispatch
- EnableUrgentOnly=true + Urgency=Normal → aucun dispatch
- EnableUrgentOnly=true + Urgency=Urgent → dispatch
- EnableAbnormalBiology=false → dispatch refusé pour Kind=AbnormalBiology
- NotificationPreferences=null → aucun dispatch
- PlaySound et ShowDesktop propagés correctement dans le payload

**Intégration** (`mss.mail.integration.tests`) :
- Endpoint SSE `/api/v1/mail/notifications/stream` retourne 200, Content-Type `text/event-stream`
- Un événement publié via le broker est reçu par le client de test dans les 2 secondes
- Le heartbeat arrive toutes les ~15 secondes
- La déconnexion client nettoie bien le channel

**BDD** (`mss.mail.bdd.tests/StepDefinitions/PreferencesNotificationStepDefinitions.cs`) :
- Étendre les step definitions pour couvrir les scénarios 1, 2, 4 de `PreferencesNotification.feature` avec un vrai dispatch simulé via un `INewMailNotifier` instancié + mock du broker SignalR/SSE. Vérifier que le payload part (ou ne part pas) selon les prefs.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tous les tests passent — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] `NotificationPayloadDto` ajouté dans le repo `dtos` et publié via `/publish-dtos`
- [ ] `INewMailNotifier` + implémentation livrés, 100 % de la logique de décision testée unitairement
- [ ] Endpoint SignalR : événement `"NotificationReceived"` émis sur le user group quand les prefs l'autorisent
- [ ] Endpoint SSE : `GET /api/v1/mail/notifications/stream` répond `text/event-stream`, broadcast fonctionnel, heartbeat présent, cleanup au disconnect
- [ ] `ISseNotificationBroker` singleton thread-safe, testé en intégration (2 clients simultanés pour le même user reçoivent tous deux)
- [ ] Hook dans le pipeline de sync : le `NewMailNotifier.HandleNewMailAsync` est appelé pour les mails reçus après `LastSyncAt`, **pas** pour la sync initiale massive
- [ ] Scénarios Gherkin 1, 2, 4 de `PreferencesNotification.feature` GREEN dans `mss.mail.bdd.tests`
- [ ] Logs structurés sur chaque décision `NewMailNotifier` (fired / skipped with reason) pour le debug
- [ ] Aucune modification des 4 toggles existants dans `SettingsComponent` backend (persistance inchangée)

## Notes

- **Ne pas traiter `EnableAbnormalBiology` dans cette tâche si la détection de résultats anormaux n'est pas encore connectée au pipeline de sync.** Laisser le `HandleAbnormalBiologyAsync` en place mais ne pas le câbler. Un commentaire `// TODO(notifications-abnormal-biology-043)` suffit. Créer une tâche follow-up si nécessaire.
- Le heartbeat SSE (15 s) est important pour les proxies / reverse-proxies qui ferment les connexions idle.
- Si l'authentification du stream SSE pose problème (pas de header possible avec EventSource natif), utiliser un query param `?token=...` — documenter dans le README du endpoint.
