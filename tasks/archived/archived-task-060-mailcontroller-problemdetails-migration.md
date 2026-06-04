# todo-task-060-mailcontroller-problemdetails-migration.md — Migration MailController vers le GlobalExceptionHandler

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Migrer **`MailController`** (`src/Api/Controllers/V1/MailController.cs`) sur le
pattern de gestion d'erreurs RFC 7807 posé par task-055. C'est le plus gros
controller du module : **~1804 lignes, ~37 actions, ~71 blocs `catch`**. Il est
traité **seul** dans sa propre task pour respecter l'hygiène PR (CLAUDE.md
règle 5) et borner le risque.

Cible :
1. Retirer les `try/catch` boilerplate (`OperationCanceledException`→499,
   `catch (Exception)`→500 codés en dur, retours `"Internal server error."` /
   strings brutes). Les exceptions remontent au `GlobalExceptionHandler`.
2. Remplacer les not-found / validations manuelles par les **exceptions métier
   typées** de task-055 (`NotFoundException`, `ValidationException`,
   `ConflictException`, `UnavailableException`) — mapping par type.
3. Retirer `[ExcludeFromCodeCoverage]` du controller.
4. Couvrir chaque action par au moins 1 test unitaire (rule 1b). `MailControllerTests`
   existe déjà — l'étendre.

**Note de découpage** : si le volume de tests fait dépasser ~30 fichiers / la
revue raisonnable, `/develop` peut scinder en 2 PRs cohérentes (ex. actions
lecture/dossiers vs actions écriture/envoi/brouillon) — à documenter dans le
develop log. Une exception au « 1 task = 1 PR » justifiée par la taille.

api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] Tous les `try/catch` boilerplate retirés de `MailController`
- [ ] Not-found / input invalide → exceptions métier typées (mapping par type
      via `GlobalExceptionHandler`, pas de `StatusCode(500, "...")` codé en dur)
- [ ] `OperationCanceledException` non ré-attrapée par action (499 géré globalement)
- [ ] `[ExcludeFromCodeCoverage]` retiré de `MailController`
- [ ] ≥ 1 test unitaire par action (happy path + au moins 1 mode d'échec typé) —
      `MailControllerTests` étendu
- [ ] Aucune réponse d'erreur en string brute ou `ErrorResponse` ne subsiste
      dans `MailController` (audit grep)
- [ ] Aucune donnée de santé (INS/NIR/CDA/MSSanté) dans les `ProblemDetails`

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- Sur quelques endpoints `MailController` : provoquer un not-found
  (UID/dossier inexistant) → 404 `problem+json` ; couper IMAP → 5xx
  `problem+json` avec `traceId` ; annuler une requête longue → 499.
- Vérifier en UI MSS (Blazor/Angular) qu'aucune action mail courante ne régresse
  visuellement (toasts identiques).

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique d'un controller existant, iso-comportement
métier. Même posture que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair dans les `ProblemDetails`
- [ ] Détail technique réservé aux logs serveur, corrélé par `traceId`

## Branches
- `api-mail` (pushed) : chore/task-060-mailcontroller-problemdetails — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-060-mailcontroller-problemdetails
- `dtos-mss` (pushed, auto-included) : chore/task-060-mailcontroller-problemdetails — branche probablement vide (aucun changement de contrat attendu)

## Develop log

- Repos touched : api-mail (pushed, c60b36f). dtos-mss : aucun changement (branche vide). Pas de découpage en 2 PRs : 3 fichiers modifiés seulement (controller + service + tests), bien sous la limite des ~30.
- Migration des 37 actions de `MailController` (1805 → 1241 lignes) :
  - ~30 blocs try/catch boilerplate supprimés (OCE→499 et Exception→500 gérés par `GlobalExceptionHandler`)
  - Not-found / invalid → `NotFoundException` / `ValidationException` ; MDN déjà envoyé → `ConflictException` (**400→409 assumé**, sémantique RFC 8098, frontends status-first non régressés)
  - `MailCancelAndReplaceResult` enrichi d'un discriminant typé `MailCancelFailureReason` (None/OriginalNotFound/InvalidRequest/SendFailed) — l'heuristique `Contains("not found")` du controller est supprimée (règle 12) ; paramètre positionnel avec défaut, aucun appelant cassé
  - `GetEmailsByTag` : échec Result mappé par type via `ToActionResult` (**était un `NotFound(string brute)` aveugle** — un `Error` service sort désormais en 500, plus en 404)
  - `SendReadReceipt` : échec MDN via `ToActionResult` (était `StatusCode(500, raw)`)
  - **2 catch légitimes conservés, justifiés inline** : (1) enrichissement background fire-and-forget (`Task.Run` — le handler global ne peut pas l'observer) ; (2) streaming `GetMailsByTag` (réponse déjà commencée, status line partie — best-effort `!Response.HasStarted`) ; le parsing des UIDs y est désormais validé AVANT le stream (`ValidationException` → 400 problem+json)
  - `[ExcludeFromCodeCoverage]` retiré
- Tests : `MailControllerTests` 0 → **88 tests** (72 méthodes + theories) — ≥1 happy + ≥1 mode d'échec typé par action, y compris offline queuing, propagation OCE (preuve de non-ré-attrapage), cancel-and-replace par Reason. Note méthode : refactor iso-comportement adossé aux tests existants (rule 1 « pure refactors ») ; les nouveaux tests capturent le contrat cible (exceptions typées) — rouges par construction contre l'ancien controller.
- Audit grep DOD : `BadRequest("` / `NotFound("` / `StatusCode(500` / `StatusCode(499` / `ErrorResponse` → **0** dans MailController ; catch restants = les 2 justifiés.
- Build : ✓ 0 erreur / 0 warning. Suite complète : verte hors 1 pré-existant documenté (`UserContextEnricher…EventId3724`) + 2 flaky parallélisation vérifiés verts en isolation (`ImapConnection…Cancellation`, `MarkdownPdfRendererTests.RenderHeadingPreservesText` — famille PDF).
- no angular change → /lint-angular skippera
- Next step : **/sonar task-060**

## Sonar log (Mode A — chained, api-mail)

- 3 analyses complètes (Release + OpenCover). **Phase 1 (new code) : ✓ verte en 3 itérations**
  - Itér. 1 : `new_violations` 6 → 0 — 3× S125 (commentaires "task-060" au phrasé code-like → reformulés en prose) + 3× S103 (lignes >150 chars dans `MailCancellationService` → coupées) ; +35 tests (théorie 422 ModelState sur 30 actions, fallback drafts-at-top, lambda background rendue déterministe via `TaskCompletionSource` + stub `IServiceScopeFactory`)
  - Itér. 2 : +12 tests ciblés sur lignes non couvertes (queues offline ×4, cache-miss `GetEmail`, échec archive `AppendToSent`, callback `SendAndArchiveAsync` via stub invoquant le `Func<>`, catch streaming OCE→499 / Exception→500 pré-flush)
  - Itér. 3 : **seam d'interface** — `MailController` injecte `IEmailSummaryService` au lieu de la classe concrète (les 5 dernières lignes étaient intestables : classe concrète + `Kernel` réel ; DI déjà enregistrée pour l'interface) ; +2 tests (summary cache-miss + échec 503)
  - Final : `MailController.cs` **new_coverage 96.3 %** (cible 95 ✓), line_coverage 99.9 %, 0 ligne non couverte ; `new_bugs`/`new_vulnerabilities` 0, hotspots reviewed 100 %
- `new_coverage` projet 73.7 % = artefact de new-code period (~28k lignes legacy), identique tasks 055/059 — accepté best-effort, pas de halt.
- Projet : bugs 0, vulnérabilités 0, code smells 0, ratings A/A/A, duplication 0.6 %.
- Tests Release : verts hors le pré-existant documenté (`UserContextEnricher…EventId3724`) + 1 flaky parallélisation (`ImapConnection…Cancellation`, vert en isolation — vérifié plusieurs fois ce cycle).
- Commits sonar : e3f0436 (S125+S103+422+lambda), 11f1fde (couverture batch 2), 71f0399 (seam IEmailSummaryService).
- no angular change → skip /lint-angular
- Next step : **/review task-060**

## PRs

- **api-mail** (pushed) : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/80 — label `awaiting-human-merge`
- **dtos-mss** : aucun changement de contrat → branche vide, pas de PR.

## Code Review Summary

**Verdict : APPROVED** (0 bloquant).

- Build : ✓ 0 erreur / 0 warning
- Tests : ✓ `MailControllerTests` 137 verts (0 → 137 ; ≥1 happy + ≥1 échec typé par action) ; suite complète verte hors **1 pré-existant documenté** (`UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724`) et **1 flaky parallélisation** (`ImapConnectionServiceIntegrationTests.ConnectAsync…`, vérifié vert en isolation plusieurs fois ce cycle)
- DOD : 9/9 items ✓ (audit grep : 0 string brute / 0 `StatusCode(500` / 0 `ErrorResponse` ; 2 catches restants = justifiés inline ; `[ExcludeFromCodeCoverage]` retiré)
- Sonar new code : 0 violation / 0 bug / 0 vuln / hotspots 100 % ; `MailController.cs` new-coverage 96.3 %, lignes 99.9 %, 0 ligne non couverte
- Non bloquants : `AiDiagnosticsController` injecte encore la classe concrète `EmailSummaryService` (scope task-062) ; changement contractuel assumé 400→409 sur MDN déjà envoyé (`ConflictException`, RFC 8098)

**HAG (règle 10)** : dérouler le Manual Test Plan puis merger la PR (`/merge task-060 --i-tested`).

## Merged

- **Date** : 2026-06-04 (attestation humaine `--i-tested`, HAG règle 10)
- **api-mail** : PR [#80](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/80) squash-mergée → `01540f9` sur `develop` — CI ✓ [run 26960110153](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/26960110153)
- **dtos-mss** : aucun changement de contrat → pas de PR ; branche remote vide supprimée, clone resynchronisé sur `develop`
- Branche remote api-mail supprimée (`--delete-branch`) ; branche locale `chore/task-060-*` conservée pour inspection rétroactive
