# todo-front-blazor-notifications-realtime-041 — Blazor : affichage temps-réel des notifications

**Dependencies**: todo-back-notifications-realtime-040
**Feature**: tests/Features/Mss/PreferencesNotification.feature
**Repo**: client-blazor (path: `Client/Blazor`)
**Module**: Client/Blazor/Src/Modules/Mss

## Contexte

La tâche `done-front-blazor-notifications-023` a livré les toggles dans `SettingsComponent.razor` et la demande de permission navigateur, mais **aucun code ne déclenche ni toast ni notification desktop** lors de la réception d'un nouveau mail. Test manuel confirmé : rien n'apparaît.

Cette tâche branche la réception SignalR sur les services d'affichage (Radzen toast + JS interop desktop + JS interop son) pour rendre la feature réellement visible.

## Objectif

Quand le backend émet un événement SignalR `"NotificationReceived"` (cf. tâche 040), afficher une notification à l'utilisateur selon ses préférences, sur n'importe quelle page de l'application.

## Travail à réaliser

### 1. Souscription SignalR dans `MailHubService`

Étendre `Src/Modules/Mss/Plugin/Services/MailHubService.cs` :

```csharp
public event Func<NotificationPayloadDto, Task>? OnNotificationReceived;

// Dans le constructeur :
_hubConnection.On<NotificationPayloadDto>("NotificationReceived", async payload =>
{
    _logger.LogDebug("[MailHubService] Received notification {Kind}: {Title}", payload.Kind, payload.Title);
    if (OnNotificationReceived != null)
        await OnNotificationReceived.Invoke(payload);
});
```

Ajouter aussi un appel `JoinUserGroupAsync(userEmail)` au démarrage (existant côté `MailHub.cs` mais pas encore invoqué par le client). Le user email vient de `TokenService` ou du claim JWT.

### 2. Service `NotificationDispatcher`

Créer `Src/Modules/Mss/Plugin/Services/NotificationDispatcher.cs` :

```csharp
public class NotificationDispatcher : INotificationDispatcher, IAsyncDisposable
{
    // Souscrit à IMailHubService.OnNotificationReceived au démarrage
    // Pour chaque payload reçu :
    //   1. Radzen NotificationService.Notify(...) si payload.Kind correspond à un toggle activé
    //   2. IJSRuntime.InvokeVoidAsync("healthplatform.notifications.showDesktop", ...) si payload.ShowDesktop
    //   3. IJSRuntime.InvokeVoidAsync("healthplatform.notifications.playSound") si payload.PlaySound
}
```

Enregistré comme singleton dans `ServiceCollectionExtensions.cs` et **démarré via un HostedService ou au premier load de l'app shell** pour s'assurer qu'il est actif dès l'ouverture de l'application (pas seulement quand la page Mail est visible).

### 3. JS interop — `wwwroot/js/notifications.js`

Nouveau fichier :
```javascript
window.healthplatform = window.healthplatform || {};
window.healthplatform.notifications = {
    showDesktop: function(title, body, iconUrl) {
        if (!("Notification" in window)) return false;
        if (Notification.permission !== "granted") return false;
        const n = new Notification(title, { body: body, icon: iconUrl || "/favicon.ico" });
        setTimeout(() => n.close(), 8000);
        return true;
    },
    playSound: function() {
        try {
            const audio = new Audio("/sounds/notification.mp3");
            audio.volume = 0.6;
            audio.play();
        } catch (e) {
            console.warn("notification sound failed", e);
        }
    }
};
```

Référencer le fichier dans `wwwroot/index.html` (ou équivalent Shell.Wasm).

Ajouter un fichier audio `wwwroot/sounds/notification.mp3` (court, ~500 ms, libre de droits ou fourni par le PO).

### 4. Titre/corps de la notification

Le payload backend contient déjà `Title` et `Body`. Le dispatcher n'a rien à composer — il affiche tel quel. Les libellés "Nouveau message" vs "Résultat biologique anormal" sont gérés côté backend pour rester cohérents Blazor/Angular.

Si besoin d'une action "Cliquer pour ouvrir le mail" sur la notification desktop : ajouter `data-mail-uid` au payload et gérer `n.onclick = () => navigate(...)`. **Scope optionnel** — si le dev agent en a le temps, sinon à reporter.

### 5. Intégration dans le Shell

Le `NotificationDispatcher` doit être actif dès qu'un user est authentifié, peu importe la page courante. Deux options :

**Option A (recommandée)** : Ajouter un composant invisible `<NotificationHost />` dans `MainLayout.razor` (ou l'équivalent dans Shell/Shell.Wasm) qui s'injecte `NotificationDispatcher` dans `OnInitializedAsync` et appelle `dispatcher.StartAsync()`.

**Option B** : HostedService Blazor — possible mais plus complexe à débrancher en mode WASM. Préférer A.

### 6. i18n

Aucune chaîne à ajouter côté Blazor — les titres/bodies viennent du backend. Vérifier néanmoins que `SettingsComponent.razor` n'a pas de chaîne hardcodée sur les toggles (devrait déjà être OK depuis la tâche 023).

### 7. Tests

**Unitaires** :
- `NotificationDispatcher` avec mocks de `IMailHubService`, `NotificationService` Radzen, et `IJSRuntime` :
  - Payload avec `ShowDesktop=true` → appel JS interop
  - Payload avec `ShowDesktop=false` → pas d'appel JS interop
  - Payload avec `PlaySound=true` → appel JS interop son
  - Toast Radzen appelé à chaque payload (le filtrage par Enable* est fait backend, le frontend affiche tout ce qu'il reçoit)

**Manuel** (à documenter dans le fichier de test du PR) :
- Ouvrir 2 onglets du Blazor, activer desktop dans Settings sur l'un
- Envoyer un mail au user de test depuis un autre client MSS
- Vérifier : toast Radzen apparaît, notification desktop apparaît (si permission accordée), son joué

**BDD** : les step definitions `PreferencesNotificationStepDefinitions.cs` côté backend (tâche 040) couvrent la logique de décision. Pas de BDD Blazor pour cette tâche (pas de runner Gherkin Blazor dans le projet).

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Client.sln`
- [ ] `MailHubService` souscrit à `"NotificationReceived"` et expose `OnNotificationReceived`
- [ ] `JoinUserGroupAsync` invoqué au démarrage avec l'email du user authentifié
- [ ] `NotificationDispatcher` implémenté, testé unitairement, enregistré en DI
- [ ] `NotificationDispatcher` démarré automatiquement via `NotificationHost` dans le layout principal
- [ ] Fichier `wwwroot/js/notifications.js` créé et référencé
- [ ] Fichier audio `wwwroot/sounds/notification.mp3` présent (PO à fournir ou libre de droits)
- [ ] Desktop notification fonctionne en test manuel : permission déjà accordée → Notification visible
- [ ] Son joué en test manuel si `EnableSoundNotification=true` dans les préférences du user
- [ ] Toast Radzen visible en test manuel sur toutes les pages (Mail, Settings, autre page du shell)
- [ ] data-testid sur le composant `NotificationHost` : `notification-host`
- [ ] Aucune régression sur les fonctionnalités déjà livrées (drafts, folders, signature) — lancer les tests existants
- [ ] Pas d'appel `new Notification(...)` direct dans du code C# (tout passe par JS interop)

## Notes

- Le filtrage par préférences est fait **côté backend** (tâche 040). Le frontend n'a pas à lire `UserSettings` pour décider d'afficher ou non — il affiche tout ce qui arrive via le hub. Simplifie le code Blazor et évite la duplication.
- Si la permission desktop n'a jamais été demandée, le `NotificationDispatcher` ne demande PAS la permission automatiquement — la demande reste attachée au toggle dans `SettingsComponent` (comportement existant). Le user doit explicitement cocher le toggle pour déclencher la demande.
- Penser à gérer le cas "MailHub déconnecté" gracieusement : en cas de perte de connexion, pas de notification — le hub se reconnecte automatiquement (`WithAutomaticReconnect()` déjà en place).
