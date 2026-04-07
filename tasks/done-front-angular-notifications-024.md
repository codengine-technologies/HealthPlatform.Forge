# todo-front-angular-notifications-024 — Angular : Préférences de notification

**Dependencies**: todo-back-notifications-022
**Feature**: tests/Features/Mss/PreferencesNotification.feature
**Repo**: client-angular (path: `Client/Angular`)
**Module**: Client/Angular/front/libs/mss

## Objectif

Implémenter l'interface de configuration des préférences de notification dans Angular.

## Travail à réaliser

### 1. Modèles
- Ajouter `NotificationPreferencesDto` dans les modèles MSS
  - enableNewMail, enableUrgentOnly, enableAbnormalBiology, enableSoundNotification, enableDesktopNotification
- Étendre `UserSettingsDto` avec `notificationPreferences?: NotificationPreferencesDto`

### 2. MssSettingsComponent
- Section "Notifications" :
  - Toggles pour chaque préférence (utiliser Toggle du design system)
  - Auto-save via le mécanisme de debounce existant
  - Demande de permission navigateur pour les notifications bureau

### 3. Intégration
- Respecter les préférences dans le système de notification existant (SnackbarService)

## Definition of Done
- [x] Build passes (0 errors) — Angular dev build clean
- [ ] Tests Vitest passent — à exécuter / écrire
- [x] Tous les toggles fonctionnent et sont persistés — 5 toggles in `mss-settings.component.html` (lines 345-393), wired via `onNotificationPrefChanged`
- [x] Préférences conservées entre les sessions — `notificationPreferences` in `UserSettingsDto`, persisted via existing settings auto-save
- [x] Standalone component, OnPush, Angular Signals — `mss-settings.component.ts` uses signals + computed
- [x] Demande de permission navigateur pour `enableDesktopNotification` — `onDesktopNotificationToggleChanged` calls `Notification.requestPermission()`
