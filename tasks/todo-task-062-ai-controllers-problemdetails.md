# todo-task-062-ai-controllers-problemdetails.md — Migration controllers IA vers le GlobalExceptionHandler

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Migrer le **cluster IA** sur le pattern RFC 7807 de task-055 :

- `AiController` (~115 lignes, ~4 actions, ~2 `catch`)
- `AiChatController` (~229 lignes, ~5 actions, ~7 `catch`)
- `AiDiagnosticsController` (~421 lignes, ~4 actions, ~4 `catch`)

Pour chaque controller : retirer les `try/catch` boilerplate, lever les
exceptions métier typées pour les erreurs métier (un service IA indisponible →
`UnavailableException`→503 ; entrée invalide → `ValidationException`→400),
retirer `[ExcludeFromCodeCoverage]`, couvrir chaque action par ≥ 1 test unitaire.
`AiDiagnosticsControllerTests` existe déjà — l'étendre.

**Spécificité streaming** : `AiChatController` et certaines actions IA peuvent
exposer des flux (SSE / streaming). Pour une réponse **déjà commencée**, le
`GlobalExceptionHandler` ne peut plus écrire de `problem+json` (headers envoyés) —
conserver/poser une gestion d'erreur in-stream propre pour ces actions (documenter
le choix), et ne déléguer au handler global que les erreurs **avant** le premier
octet. Ne pas casser le contrat de streaming.

api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] `try/catch` boilerplate retiré des 3 controllers (hors gestion in-stream
      légitime, documentée)
- [ ] Erreurs métier → exceptions typées (mapping par type) ; IA indisponible → 503
- [ ] `OperationCanceledException` non ré-attrapée par action (hors annulation de flux)
- [ ] `[ExcludeFromCodeCoverage]` retiré des 3 controllers
- [ ] ≥ 1 test unitaire par action (happy path + ≥ 1 mode d'échec typé)
- [ ] Le contrat de streaming SSE des actions concernées reste fonctionnel
      (aucune régression sur le flux)
- [ ] Aucune donnée de santé dans les `ProblemDetails`

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- Appeler une action IA non-stream avec une entrée invalide → 400 `problem+json`.
- Couper le backend IA (clé/endpoint) puis appeler une action IA → 503
  `problem+json` avec `traceId`.
- Lancer un chat IA streaming et vérifier que le flux fonctionne toujours
  (pas de régression), et qu'une erreur avant le premier octet sort en `problem+json`.

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique de controllers existants. Vigilance :
les prompts/contextes IA peuvent contenir des données patient → s'assurer
qu'aucun écho de contexte IA n'apparaît dans les `ProblemDetails`. Même posture
que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé / contexte IA en clair dans les `ProblemDetails`
- [ ] Détail technique réservé aux logs serveur, corrélé par `traceId`
