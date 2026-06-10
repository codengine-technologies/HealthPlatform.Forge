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

## Branches
- `api-mail` (pushed) : refactor/task-062-ai-controllers-problemdetails — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/refactor/task-062-ai-controllers-problemdetails
- `dtos-mss` (pushed, auto-included) : refactor/task-062-ai-controllers-problemdetails — branche probablement vide (aucun changement de contrat), pas de PR si aucun commit.

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

## Develop log

- Repos touched : api-mail (pushed). dtos-mss : aucun changement (branche vide, pas de PR).
- Commits : api-mail f0e3416 refactor(api): migrate AI controllers to RFC 7807 (task-062)
- Changes :
  - `AiController`, `AiChatController`, `AiDiagnosticsController` : suppression des
    `try/catch` boilerplate + retours 500/499 codés en dur.
  - `AiDiagnosticsController` : les catches fuyaient `ex.Message` **et `ex.StackTrace`**
    dans le corps 500 — supprimés (amélioration sécurité, le handler renvoie un 500
    générique sans fuite).
  - Erreurs métier → exceptions typées (`NotFoundException` → 404, `ValidationException` → 400).
  - **Streaming** : `AiController.CorrectText` et `AiChatController.StreamMessage` —
    validation pré-flux déléguée au handler (problem+json avant 1er octet) ; gestion
    in-stream conservée (événement SSE terminal générique, aucun `ex.Message`/contexte
    IA échoé). `[ERROR] {ex.Message}` remplacé par message générique.
  - `[ExcludeFromCodeCoverage]` retiré des 3 controllers.
- Tests : 26 nouveaux tests (happy + échec typé + streaming + smoke contract pour les
  2 endpoints diagnostics qui downcastent `BaseRepository.DataContext`, non unit-testables).
- Build : ✓. Tests task-062 : ✓ 26/26.
- Next step : `/sonar task-062` → `/review` (skip `/lint-angular`, pas de change angular).

## Sonar log

- Mode A (chaîné), branche `refactor/task-062-...`, SonarQube `healthplatform`.
- **New code task-062 — zéro dette** : `new_violations`=0, `new_bugs`=0,
  `new_vulnerabilities`=0, `new_code_smells`=0, `new_security_hotspots_reviewed`=100%.
  - 2 findings introduits puis fixés : S125 (commentaire `//` d'en-tête converti en
    `///` XML doc) + S2302 (`nameof(request)` dans la validation pré-flux StreamMessage).
- Couverture des fichiers task-062 : `AiController` 88.7%, `AiChatController` 81.5%,
  `AiDiagnosticsController` 34.3%. Les non-couvertures restantes sont :
  - les blocs `catch` **in-stream** (déclenchés uniquement sur exception pendant le flux,
    non exercés par le happy path) ;
  - les 2 endpoints diagnostics `CheckEmbeddingsStatus` / `DebugVectorSearch` qui
    downcastent `IMailRepository` → `BaseRepository.DataContext` : **non unit-testables**
    sans harnais WebApplicationFactory + Testcontainer PostgreSQL (hors scope api-tests).
    Contrat (route/verbe) couvert par tests. C'était la raison du `[ExcludeFromCodeCoverage]`
    historique, désormais retiré (DOD) avec couverture mesurée et lacune documentée.
- Quality Gate projet RED uniquement sur `new_coverage` global (73.4% < 80%) — dette
  pré-existante baseline 2026-04-27 (30k+ lignes), hors périmètre task-062.
- Build Release ✓. 3 échecs de tests pré-existants documentés (middleware DB-name stale,
  IMAP flaky, MailExport PDF flaky) — non liés à task-062.
- Commits Sonar : api-mail 0f71f67 fix(sonar/new): clear task-062 new-code findings.
- Next step : skip `/lint-angular` (pas de change angular) → `/review task-062`.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/82 — label `awaiting-human-merge`
- `dtos-mss` : branche vide (aucun changement) — pas de PR.

## Code Review Summary
- Verdict : **APPROVED**. Correctness/Security (plus de fuite stack trace)/Architecture/Tests ✅.
- Sonar new-code : 0 violation ; couverture diagnostics limitée par les downcasts DataContext (documenté).
- 3 échecs pré-existants documentés (non liés à task-062).

## Merged

- Merged: 2026-06-09  UTC (squash, HAG human attestation via /merge --i-merged)
- api-mail :  (PR # squash-merged into develop, remote branch deleted)
- dtos-mss : no PR (branch empty — no contract change)
- develop CI run : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions?query=branch%3Adevelop
