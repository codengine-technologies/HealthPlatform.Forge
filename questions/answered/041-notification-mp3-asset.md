# Question PO — fichier audio de notification (Blazor + Angular)

**Tâche d'origine** : `done-front-blazor-notifications-realtime-041` (PR codengine-technologies/HealthPlatform.Client#19)
**Date posée** : 2026-04-08
**Date résolue** : 2026-04-08
**Statut** : RÉSOLUE — feature abandonnée

## Décision PO

**La feature "notification sonore" est ABANDONNÉE.** Pas d'asset à fournir, pas de toggle à conserver, pas de code à garder.

### Rationale
- Bloquer 041/042 sur le sourcing d'un asset audio est disproportionné.
- La valeur clinique des notifications est portée par le visuel (toast + desktop notif), pas par le son.
- Maintenir une feature inactive (toggle visible mais no-op) crée de la dette UX et de la confusion utilisateur.
- Suppression complète plutôt que report : pas de "fausse v1" (cf. règle 11 US-complete merge gate).

## Périmètre de suppression (dispatché en tâches dev)

| Couche | Tâche dev créée | Repo |
|---|---|---|
| DTO contract | `todo-back-remove-sound-notification-dto-051` | dtos-mss (puis `/publish-dtos`) |
| Backend filtering + tests | `todo-back-remove-sound-notification-052` | api-mail |
| Frontend Blazor (UI + JS + dispatcher + tests) | `todo-front-blazor-remove-sound-notification-053` | client-blazor |
| Frontend Angular spec (042) | spec amendée — section "son" supprimée | client-angular (manuel) |

Les `.feature` partagés et bdd ont déjà été nettoyés (PO direct, scénario "Activer le son des notifications" supprimé).

## Notes
- Aucun asset audio à sourcer.
- Le placeholder `wwwroot/sounds/notification.mp3.README` doit être supprimé par la tâche dev Blazor.
- Migration DB : si `EnableSoundNotification` est persisté en BDD, prévoir migration de drop colonne dans la tâche back 052.
