# todo-back-remove-sound-notification-052 — Purger la logique son côté api-mail

**Dependencies**: todo-back-remove-sound-notification-dto-051 (le DTO doit être republié AVANT)
**Feature**: Api/Mail/tests/mss.mail.bdd.tests/Features/Mss/PreferencesNotification.feature (scénario "Activer le son" déjà supprimé par PO)
**Repo**: api-mail (path: `Api/Mail`)
**Module**: Api/Mail

## Contexte

Décision PO 2026-04-08 : feature "notification sonore" ABANDONNÉE. Cette tâche purge toute trace de `EnableSoundNotification` côté backend api-mail après que le DTO partagé ait été republié (tâche 051).

## Périmètre — fichiers identifiés

- `Api/Mail/src/Application/Services/Implementation/NewMailNotifier.cs` — supprimer toute lecture/propagation de `EnableSoundNotification` et le champ `playSound` éventuellement émis dans le payload SSE.
- `Api/Mail/tests/mss.mail.application.tests/Services/NewMailNotifierTests.cs` — supprimer les tests qui couvrent le filtrage son.
- `Api/Mail/tests/mss.mail.application.tests/Services/UserSettingsNotificationTests.cs` — idem.
- `Api/Mail/tests/mss.mail.domain.tests/Entities/NotificationPreferencesTests.cs` — supprimer les tests d'entité liés au son.
- `Api/Mail/tests/mss.mail.bdd.tests/StepDefinitions/PreferencesNotificationStepDefinitions.cs` — supprimer les steps "il active le son des notifications" / "les notifications sont accompagnées d'un signal sonore" (le scénario `.feature` est déjà supprimé).

## Travail à réaliser

1. **Audit** : `grep -r "EnableSoundNotification\|playSound\|SoundNotification" Api/Mail/` pour s'assurer qu'aucune occurrence n'est oubliée (tests inclus).
2. **Schéma** : si `EnableSoundNotification` est persisté en BDD (table préférences), générer une migration EF Core de **drop column**. Suivre la règle 7c (audit migration : vérifier le fichier généré, pas d'opération phantôme, snapshot à jour).
3. **Code** : supprimer le champ du domaine, du mapper, du notifier, du payload SSE.
4. **Tests** : supprimer / amender les tests référencés ci-dessus. Les tests restants doivent rester GREEN.
5. **BDD steps** : supprimer les steps orphelins (le scénario .feature est déjà parti — sans purge des steps, build BDD échouera).
6. **Build + tests** : `dotnet build HealthPlatform.Api.Mail.sln && dotnet test HealthPlatform.Api.Mail.sln` — 0 erreur, 0 failure.
7. Commit + PR sur `develop`.

## Definition of Done

- [ ] Aucune occurrence de `EnableSoundNotification` / `playSound` / `SoundNotification` dans `Api/Mail/`
- [ ] Migration EF Core générée + vérifiée si le champ était persisté (sinon, ignorer)
- [ ] `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreur
- [ ] `dotnet test HealthPlatform.Api.Mail.sln` → 0 failure
- [ ] Aucun step Reqnroll orphelin
- [ ] PR ouverte sur `develop` (repo api-mail)
- [ ] DTO consommé est la version republiée par la tâche 051

## Manual Test Plan

- Lancer api-mail localement : `cd Api/Mail && dotnet run --project src/Api`
- Endpoint `/api/v1/mail/notifications/preferences` :
  - GET : la réponse JSON ne contient PAS de champ `enableSoundNotification`
  - PUT : envoyer un body sans le champ → 200, persisté correctement
  - PUT : envoyer un body avec un ancien champ `enableSoundNotification: true` → soit ignoré silencieusement, soit 400 (au choix du dev, à documenter dans la PR)
- Stream SSE `/api/v1/mail/notifications/stream` : le payload émis ne contient PAS de champ `playSound`

## Notes

- Si la BDD prod contient déjà la colonne, la migration drop doit être réversible (down → re-add nullable). Documenter dans la PR.
- Cette tâche bloque techniquement 053 (front-blazor) à cause du contrat SSE (le payload ne doit plus contenir `playSound`). Ordre : 051 → publish-dtos → 052 + 053 en parallèle.
