# todo-task-063-realtime-connection-controllers-problemdetails.md — Migration controllers temps réel / connexion / annuaire

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Migrer sur le pattern RFC 7807 de task-055 :

- `MailEventsController` (~203 lignes, 1 action SSE, ~4 `catch`)
- `NotificationsController` (~140 lignes, 1 action SSE, ~2 `catch`)
- `ConnectionController` (~82 lignes, ~2 actions, ~3 `catch`)
- `DirectoryController` (~73 lignes, ~3 actions, ~3 `catch`)

Pour chaque controller : retirer les `try/catch` boilerplate, lever les
exceptions métier typées pour les erreurs métier, retirer
`[ExcludeFromCodeCoverage]`, couvrir chaque action par ≥ 1 test unitaire.

**Spécificité SSE** : `MailEventsController.Stream` et
`NotificationsController.Stream` produisent des flux Server-Sent Events. Comme
pour task-062, le `GlobalExceptionHandler` ne peut pas réécrire une réponse
déjà commencée — conserver une gestion d'erreur in-stream pour ce qui survient
après le premier octet, et ne déléguer au handler que les échecs **avant**
l'ouverture du flux (résolution claim email manquant → 400 `problem+json`,
etc., comportement task-022 préservé). Ne pas réintroduire de lecture
`?email=` (sécurité task-022).

api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] `try/catch` boilerplate retiré des 4 controllers (hors gestion in-stream
      légitime, documentée)
- [ ] Erreurs métier → exceptions typées (mapping par type)
- [ ] `[ExcludeFromCodeCoverage]` retiré des 4 controllers
- [ ] ≥ 1 test unitaire par action (happy path + ≥ 1 mode d'échec typé)
- [ ] Les flux SSE (`MailEvents`, `Notifications`) restent fonctionnels ;
      l'email reste résolu **exclusivement** depuis le claim JWT (sécurité task-022
      non régressée — `?email=` ignoré)
- [ ] Aucune donnée de santé dans les `ProblemDetails`

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- `ConnectionController` / `DirectoryController` : provoquer une erreur (annuaire
  indisponible, paramètre invalide) → `problem+json` avec le bon code.
- Ouvrir le flux SSE `MailEvents` / `Notifications` côté UI MSS → vérifier que
  les notifications temps réel arrivent toujours (pas de régression).
- Tenter `?email=victim@x.fr` sur le stream avec son propre JWT → le flux
  s'ouvre sur SON email (sécurité task-022 préservée).

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique de controllers existants, iso-comportement.
La sécurité SSE (résolution email par claim, scrub token en query) de task-022
ne doit pas régresser. Même posture que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair dans les `ProblemDetails`
- [ ] Détail technique réservé aux logs serveur, corrélé par `traceId`
- [ ] Sécurité SSE task-022 préservée (email depuis claim, `?email=` ignoré)
