# todo-back-remove-sound-notification-dto-051 — Supprimer `EnableSoundNotification` du DTO partagé

**Dependencies**: aucune (point d'entrée de la purge sonore)
**Feature**: tests/Features/Mss/PreferencesNotification.feature (scénario "Activer le son" supprimé)
**Repo**: dtos-mss (path: `Dtos`)
**Module**: Dtos

## Contexte

Décision PO 2026-04-08 : la feature "notification sonore" est ABANDONNÉE (cf. `questions/answered/041-notification-mp3-asset.md`). Suppression complète, pas de toggle dormant.

Cette tâche est le **point d'entrée** de la purge : elle modifie le contrat DTO partagé. Elle DOIT être livrée + republiée via `/publish-dtos` AVANT que les tâches consommatrices (052 back, 053 front-blazor) soient dispatchées.

## Travail à réaliser

1. Éditer `Dtos/NotificationPreferencesDto.cs` :
   - Supprimer la propriété `public bool EnableSoundNotification { get; set; } = false;`
2. Bumper la version du package (patch ou minor selon convention du repo).
3. Build : `dotnet build HealthPlatform.Dtos.Mss.csproj`
4. Commit + PR sur `develop`.
5. **Après merge** : exécuter `/publish-dtos` pour publier le NuGet et bumper les consommateurs (`api-mail`, `client-blazor`, `client-angular` — Angular sera mis à jour manuellement par le humain).

## Definition of Done

- [ ] `EnableSoundNotification` n'apparaît plus dans `NotificationPreferencesDto.cs`
- [ ] Build dtos-mss passe (0 erreur)
- [ ] PR créée sur `develop` (repo dtos-mss)
- [ ] Note dans la PR : "Bloc 1/3 de la purge son. À faire suivre par /publish-dtos puis dispatch des tâches 052 (api-mail) et 053 (client-blazor)."

## Manual Test Plan

- Pas d'app à lancer — modification de contrat pure.
- Vérifier que le NuGet republié est consommable par `api-mail` et `client-blazor` (la commande `/publish-dtos` s'en charge).

## Notes

- Cette tâche NE touche PAS l'implémentation back/front : elle ne fait que casser le contrat. La compilation des consommateurs cassera tant que 052 et 053 ne sont pas livrées — c'est le comportement attendu, géré par le séquencement orchestrator.
