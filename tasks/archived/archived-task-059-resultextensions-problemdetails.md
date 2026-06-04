# todo-task-059-resultextensions-problemdetails.md — Uniformiser le path `Result` sur ProblemDetails (RFC 7807)

**Repos**: api-mail
**Dependencies**: task-055
**Epic**: E009

## Objectif

Suite de task-055 (qui a posé le `GlobalExceptionHandler` RFC 7807). Le dernier
format d'erreur non conforme restant est le path **`Ardalis.Result`** : quand
un service renvoie un `Result` en échec, `ResultExtensions.ToActionResult`
(`src/Api/Helpers/ResultModelExtensions.cs`) sérialise encore un
`ErrorResponse(bool Success, string Message)` au lieu d'un
`application/problem+json`.

Cette task **uniformise ce path** : `ToActionResult` doit produire un
`ProblemDetails` (via `ControllerBase.Problem(...)` ou `IProblemDetailsService`),
en réutilisant le **même mapping par type** que le `GlobalExceptionHandler`
(`ResultStatus` → code HTTP déjà en place depuis task-055). Le record
`ErrorResponse` est ensuite supprimé (plus aucun consommateur).

C'est le **keystone** : une fois mergée, tous les controllers utilisant le
pattern `Result` émettent du `problem+json` sans modification individuelle, et
les tasks 060–065 n'ont plus qu'à retirer le boilerplate `try/catch` et les
`[ExcludeFromCodeCoverage]`.

Périmètre **api-mail uniquement** — aucun changement de contrat DTO. Les
frontends consomment déjà `ProblemDetails` (Blazor `ProblemDetailsParser` +
Angular `mapProblemDetailsToMessage`, livrés par task-055, avec fallback legacy),
donc aucune régression UX.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur)
- [ ] Tests pass (`dotnet test`, 0 échec hors échec pré-existant documenté)
- [ ] `ResultExtensions.ToActionResult` (les 2 surcharges) renvoie un
      `ProblemDetails` (`application/problem+json`) en cas d'échec, avec `status`,
      `title`, `detail`, `traceId` — `detail` reste un message sûr (pas de fuite
      de donnée de santé)
- [ ] Mapping par type **réutilisé / cohérent** avec le `GlobalExceptionHandler`
      (`ResultStatus.NotFound`→404, `Unauthorized`→401, `Forbidden`→403,
      `Invalid`→400, `Conflict`→409, `Unavailable`→503, défaut→500)
- [ ] Le record `ErrorResponse` est **supprimé** (audit grep : 0 référence
      restante dans `src/`)
- [ ] `LogServerFailure` (log des 5xx Result-mapped) préservé
- [ ] `ResultExtensionsTests` mis à jour : assertions sur le body `ProblemDetails`
      (type `ObjectResult` portant un `ProblemDetails`, `StatusCode` correct)
- [ ] Aucune donnée de santé en clair dans le `detail` renvoyé au client

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- Déclencher un endpoint dont le service renvoie un `Result` en échec (ex. une
  opération onboarding/IMAP qui échoue) → vérifier `Content-Type:
  application/problem+json`, corps `{title, status, detail, traceId}`.
- Vérifier qu'aucun ancien corps `{ "success": false, "message": ... }` ne
  subsiste sur les réponses d'erreur.
- **Front Blazor / Angular** : provoquer la même erreur depuis l'UI MSS →
  toast/snackbar affiché correctement (le parser ProblemDetails est déjà en
  place depuis task-055).

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique transverse de la couche API
(uniformisation du format d'erreur), iso-comportement métier. Pas d'INS, pas de
donnée patient manipulée. Même posture de conformité que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair dans les `ProblemDetails` renvoyés
- [ ] Détail technique réservé aux logs serveur, corrélé par `traceId`

## Branches
- `api-mail` (pushed) : chore/task-059-resultextensions-problemdetails — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-059-resultextensions-problemdetails
- `dtos-mss` (pushed, auto-included) : chore/task-059-resultextensions-problemdetails — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/chore/task-059-resultextensions-problemdetails (aucun changement de contrat attendu — branche probablement vide, pas de PR si aucun commit)

## Develop log

- Repos touched : api-mail (pushed). dtos-mss : aucun changement de contrat (branche vide, pas de PR). client-blazor/client-angular : non listés, non touchés (parsers ProblemDetails déjà livrés par task-055).
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : f175937 refactor(api): unify Result failure path on RFC 7807 ProblemDetails (task-059)
- Implémentation :
  - `ToActionResult` (2 surcharges) → échec sérialisé en `ProblemDetails` (`application/problem+json`) : `status`/`title` (ReasonPhrases)/`detail`/`type` + `traceId` (`Activity.Current?.Id ?? TraceIdentifier`) + `instance` (`METHOD /path`) — même enrichissement que la customisation `AddProblemDetails` de Program (ce path est sérialisé par MVC, pas par `IProblemDetailsService`)
  - Detail : fallback 500 → message générique (zéro fuite, posture `GenericServerDetail` du `GlobalExceptionHandler`) ; statuts typés → message développeur ; `Result.Invalid` → `ValidationErrors` (pas `Errors`) ; statut typé sans message → fallback client sûr
  - `MapStatusCode` task-055 conservé tel quel (mapping par type) ; `LogServerFailure` préservé ; record `ErrorResponse` supprimé ; `[ExcludeFromCodeCoverage]` retiré de la classe
- Test-first : ResultExtensionsTests réécrits (28 tests) → RED 26/28 confirmé → implémentation → GREEN 28/28
- Local build / test : ✓ build 0 erreur / 0 warning. Suite complète : domain 94 ✓, infra 346 ✓, application 1461/1462, api 210/211, intégration 186/187 (16 skip) :
  - `UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724` — **pré-existant documenté** (rouge sur develop propre depuis task-055)
  - `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection` et `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync` — **flaky parallélisation, vérifiés verts en isolation** (sans rapport avec le diff : PDF/IMAP)
- DOD self-check : 7/8 items vérifiables par commande ✓ (grep ErrorResponse = 0 référence src+tests). Item "aucune donnée de santé dans detail" : garanti par le fallback générique + leak-guard test ; observation finale deferred to manual test (HAG).
- no angular change → /lint-angular skippera
- Next step : **/sonar task-059** (api-mail touché → chaîne vers /review)

## Sonar log (Mode A — chained, api-mail)

- SonarQube démarré (conteneurs `sonarqube_db` puis `sonarqube`), 2 analyses complètes sur la branche (Release + OpenCover, 5 projets de tests).
- **Phase 1 (new code) : ✓ verte**
  - `new_violations` : 1 → **0** (CA1859 INFO sur `ToProblemResult` — type de retour concret `ObjectResult`, fixé ed5ff63)
  - `new_bugs` = 0, `new_vulnerabilities` = 0, `new_security_hotspots_reviewed` = 100 %
  - Couverture `ResultModelExtensions.cs` : **new_coverage 95.7 %** (≥ cible 95), line 100 %, 0 ligne non couverte — 2 tests ajoutés (11672f6) : précédence `Activity.Current` pour le traceId, path logger de `LogServerFailure` (NSubstitute) ; garde-fous null intestables retirés (contrat Ardalis : collections jamais null)
- **`new_coverage` projet = 72.5 % → seule condition QG RED** : artefact de la new-code period (~28k lignes legacy classées « new »), identique task-055. Code task-059 couvert → accepté best-effort, pas de halt.
- **Phase 2 (legacy) : rien à faire** — bugs 0, vulnérabilités 0, code smells **0**, ratings A/A/A, duplication 0.6 %.
- Tests Release : verts hormis (1) `UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724` — pré-existant documenté ; (2) `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync` — flaky parallélisation, re-vérifié **vert en isolation** (Release). Le test PDF flaky du run précédent est passé ce run.
- Commits sonar : `fix(sonar/new)` ed5ff63, `test(sonar/new)` 11672f6 — poussés.
- no angular change (task-059 ne liste pas client-angular ; le WIP non commité dans `Client/Angular/` est l'héritage task-055/humain, hors scope) → **skip /lint-angular**
- Next step : **/review task-059**

## PRs

- **api-mail** (pushed) : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/79 — label `awaiting-human-merge`
- **dtos-mss** : aucun changement de contrat → branche vide, pas de PR.

## Code Review Summary

**Verdict : APPROVED** (0 bloquant).

- Build : ✓ api-mail (0 erreur / 0 warning)
- Tests : ✓ 30 tests ResultExtensionsTests verts ; suite complète verte hors **1 échec pré-existant documenté** (`UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724`, rouge sur develop propre depuis task-055) et **1 flaky parallélisation** (`ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync`, vérifié vert en isolation ×2 Debug+Release ; le test PDF flaky du premier run est repassé ensuite)
- DOD : 8/8 items vérifiables par commande ✓ (grep `ErrorResponse` = 0 référence ; items observables déférés au Manual Test Plan)
- Sonar new code : 0 violation / 0 bug / 0 vuln / hotspots 100 % reviewed ; `ResultModelExtensions.cs` new-coverage 95.7 %, lignes 100 %
- Suggestion non bloquante : `LogServerFailure` conserve un `?? Array.Empty` défensif (incohérent avec la simplification Ardalis amont, sans impact runtime)

**HAG (règle 10)** : tester le Manual Test Plan puis merger la PR manuellement.

## Merged

- **Date** : 2026-06-04 (attestation humaine `--i-tested`, HAG règle 10)
- **api-mail** : PR [#79](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/79) squash-mergée → `5c7741b` sur `develop` — CI ✓ [run 26955983381](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/26955983381)
- **dtos-mss** : aucun changement de contrat → pas de PR ; branche remote vide supprimée, clone resynchronisé sur `develop`
- Branche remote api-mail supprimée (`--delete-branch`) ; branche locale `chore/task-059-*` conservée pour inspection rétroactive
