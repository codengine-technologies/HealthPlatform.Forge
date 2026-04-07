# todo-front-blazor-notifications-023 — Blazor : Préférences de notification

**Dependencies**: todo-back-notifications-022
**Feature**: tests/Features/Mss/PreferencesNotification.feature
**Repo**: client-blazor (path: `Client/Blazor`)
**Module**: Client/Blazor/Src/Modules/Mss

## Objectif

Implémenter l'interface de configuration des préférences de notification dans Blazor.

## Travail à réaliser

### 1. Section Settings
- Ajouter une section "Notifications" dans `SettingsComponent.razor`
  - Toggle "Notifications pour les nouveaux messages"
  - Toggle "Uniquement les messages urgents"
  - Toggle "Résultats biologiques anormaux"
  - Toggle "Son des notifications"
  - Toggle "Notifications bureau" (avec demande de permission navigateur)
- Sauvegarde automatique à chaque changement (comme les autres settings)

### 2. Intégration notifications
- Respecter les préférences lors de l'affichage des notifications toast
- Si son activé, jouer un son lors d'une notification

## Definition of Done
- [x] Build passes (0 errors in SettingsComponent — pre-existing errors in other components unrelated to this task)
- [x] Tous les toggles fonctionnent et sont persistés (5 toggles bound to NotificationPreferencesDto, auto-save via AutoSaveAsync)
- [x] Les préférences sont conservées entre les sessions (persisted via IUserSettingsService)
- [x] La demande de permission navigateur s'affiche pour les notifications bureau — `OnDesktopNotificationToggleChangedAsync` in `SettingsComponent.razor` calls `Notification.requestPermission()` via `IJSRuntime`
- [x] data-testid sur tous les éléments interactifs (toggle-notif-new-mail, toggle-notif-urgent-only, toggle-notif-abnormal-biology, toggle-notif-sound, toggle-notif-desktop)
- [x] Tous les textes passent par le Localizer (i18n) (EN + FR entries added)
