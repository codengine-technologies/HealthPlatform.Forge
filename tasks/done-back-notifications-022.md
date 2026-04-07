# todo-back-notifications-022 — Backend : Préférences de notification

**Dependencies**: aucune
**Feature**: tests/Features/Mss/PreferencesNotification.feature
**Repo**: api-mail (path: `Api/Mail`)
**Touches**: dtos-mss (DTO contracts → run `/publish-dtos` first)
**Module**: Api/Mail

## Objectif

Étendre les UserSettings pour inclure les préférences de notification et les exposer via l'API.

## Travail à réaliser

### 1. Étendre UserSettingsDto
- Ajouter `NotificationPreferences` dans `UserSettingsDto` (stocké dans le JSON existant) :
  - `EnableNewMail` (bool, default true)
  - `EnableUrgentOnly` (bool, default false)
  - `EnableAbnormalBiology` (bool, default true)
  - `EnableSoundNotification` (bool, default false)
  - `EnableDesktopNotification` (bool, default true)

### 2. DTO
- Créer `NotificationPreferencesDto` dans `Dtos/Mss/`
- Intégrer comme propriété de `UserSettingsDto`

### 3. Service
- Le `SettingsController` existant gère déjà le save/get des UserSettings
- S'assurer que les nouvelles propriétés sont correctement sérialisées/désérialisées dans le JSON
- Valeurs par défaut si le JSON existant ne contient pas ces champs

### 4. SignalR (optionnel)
- Si `MailHubService` existe, filtrer les notifications push selon les préférences utilisateur
- Ne pas envoyer de notification si `EnableNewMail=false`
- Envoyer uniquement les urgents si `EnableUrgentOnly=true`

### 5. Tests
- Test unitaire : sérialisation/désérialisation avec les nouvelles propriétés
- Test unitaire : valeurs par défaut pour les settings existants sans notification prefs
- Test d'intégration : save et retrieve des préférences

## Definition of Done
- [x] Build passes (0 errors)
- [x] Tests unitaires passent
- [x] Tests d'intégration passent
- [x] Les préférences sont persistées dans UserSetting.SettingsJson
- [x] Les valeurs par défaut sont appliquées pour les users existants
- [x] Rétrocompatibilité avec les settings JSON existants
- [ ] Tous les scénarios Gherkin de PreferencesNotification.feature couverts côté backend — bloqué tant qu'aucun framework BDD n'est en place
