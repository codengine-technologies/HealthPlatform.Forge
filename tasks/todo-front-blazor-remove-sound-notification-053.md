# todo-front-blazor-remove-sound-notification-053 — Purger la logique son côté Blazor

**Dependencies**: todo-back-remove-sound-notification-dto-051 (DTO republié) — peut être dispatché en parallèle de 052
**Feature**: tests/Features/Mss/PreferencesNotification.feature (scénario "Activer le son" déjà supprimé par PO)
**Repo**: client-blazor (path: `Client/Blazor`)
**Module**: Client/Blazor/Src/Modules/Mss

## Contexte

Décision PO 2026-04-08 : feature "notification sonore" ABANDONNÉE. Cette tâche purge toute trace côté client Blazor (UI, JS interop, dispatcher, tests, asset placeholder).

## Périmètre — fichiers identifiés

- `Client/Blazor/Src/Modules/Mss/Plugin/Components/SettingsComponent.razor` — supprimer le toggle "son" et toute liaison au champ `EnableSoundNotification`.
- `Client/Blazor/Src/Modules/Mss/Plugin/Services/NotificationDispatcher.cs` — supprimer la branche "play sound" et l'appel à `playSound` JS interop.
- `Client/Blazor/Src/Component/Shared/wwwroot/js/notifications.js` — supprimer la fonction `playSound` (et la création du `new Audio(...)`).
- `Client/Blazor/Src/Component/Shared/wwwroot/sounds/notification.mp3.README` — **supprimer** ce placeholder.
- `Client/Blazor/Src/Component/Shared/wwwroot/sounds/` — supprimer le dossier s'il devient vide.
- `Client/Blazor/tests/HealthPlatform.Module.Mss.Plugin.Tests/NotificationDispatcherTests.cs` — supprimer les tests qui couvrent la branche son.

## Travail à réaliser

1. **Audit** : `grep -r "EnableSoundNotification\|playSound\|SoundNotification\|notification\.mp3" Client/Blazor/`
2. **UI** : supprimer le toggle dans `SettingsComponent.razor` + i18n associée si présente.
3. **Code** : supprimer la branche son du dispatcher, supprimer le JS interop.
4. **Asset** : supprimer le placeholder README et le dossier `wwwroot/sounds/` s'il est vide.
5. **Tests** : supprimer les tests orphelins, conserver les autres tests GREEN.
6. **Build + tests** : `cd Client/Blazor && dotnet build HealthPlatform.Client.sln && dotnet test HealthPlatform.Client.sln`
7. Commit + PR sur `develop`.

## Definition of Done

- [ ] Aucune occurrence de `EnableSoundNotification` / `playSound` / `notification.mp3` dans `Client/Blazor/`
- [ ] Toggle "son des notifications" absent de l'UI Settings
- [ ] Dossier `wwwroot/sounds/` supprimé (ou vide)
- [ ] `dotnet build HealthPlatform.Client.sln` → 0 erreur
- [ ] `dotnet test HealthPlatform.Client.sln` → 0 failure
- [ ] DTO consommé est la version republiée par 051
- [ ] data-testid : aucune référence à un testid sound-toggle restante
- [ ] PR ouverte sur `develop` (repo client-blazor)

## Manual Test Plan

- Lancer Blazor : `cd Client/Blazor && dotnet run --project Src/Host`
- Ouvrir l'écran Préférences MSS → vérifier que **aucun** toggle "son" n'apparaît, seuls les toggles "nouveaux mails", "urgents", "biologie anormale", "notifications bureau" subsistent.
- Envoyer un mail au compte de test depuis api-mail : vérifier que **aucun son** n'est joué (et aucune erreur console JS du type "playSound is not defined").
- DevTools → Network → Static : aucune requête vers `/sounds/notification.mp3`.

## Notes

- Coordonner avec 052 : tant que le payload SSE backend contient encore `playSound`, le code front l'ignore silencieusement (pas de crash). Une fois 052 mergée, le champ disparaît côté wire — aucune adaptation supplémentaire nécessaire ici si le code l'ignore proprement.
- Côté Angular (042) : le scope son est déjà retiré de la spec PO. Aucune action forge nécessaire (repo exclu).
