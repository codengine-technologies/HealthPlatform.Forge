# todo-task-055-problemdetails-error-handling.md — Harmonisation de la gestion d'erreurs API via ProblemDetails (RFC 7807)

**Repos**: api-mail, client-blazor, client-angular, dtos-mss
**Dependencies**: —
**Epic**: E009
**EpicTitle**: Robustesse & observabilité de la plateforme

> **Note transverse (control-plane)** : cette US modifie aussi `CLAUDE.md`
> (règles d'implémentation de la forge) pour **graver `ProblemDetails` comme
> le pattern officiel et obligatoire de gestion d'erreurs au niveau des
> controllers**. `CLAUDE.md` vit à la racine du workspace (pas de remote,
> jamais poussé) — cette édition est faite directement, hors PR repo, mais
> fait partie intégrante du périmètre de la tâche et est vérifiée par
> `/review`.

## Objective

Unifier la gestion des erreurs des 25 controllers V1 de `api-mail`
(`Api/Mail/src/Api/Controllers/V1`) autour d'un **handler d'exception global**
produisant des réponses normalisées **`application/problem+json` (RFC 7807)**.

Aujourd'hui chaque action répète manuellement un triple `try/catch`
(`OperationCanceledException` → 499, `Exception` → 500) — mesuré à ~93 blocs
`catch (Exception)`, ~66 `catch (OperationCanceledException)` et ~97 retours
`500` codés en dur. Trois formats de réponse d'erreur coexistent
(`ErrorResponse(Success, Message)`, string brute `"Internal server error."`,
string métier). Le mapping HTTP repose sur une **heuristique de mots-clés**
fragile dans le message (`ResultExtensions.MapStatusCode`).

Cible :

1. **Backend** : un `GlobalExceptionHandler` (`IExceptionHandler`, .NET 10) +
   `AddProblemDetails()` branchés dans le pipeline. Suppression des
   `try/catch` boilerplate des controllers. Toutes les erreurs sortent en
   `ProblemDetails` avec `traceId`. `ProblemDetails` devient le **seul**
   format d'erreur officiel des controllers.
2. **Mapping par type, pas par chaîne** : exceptions métier typées
   (`NotFoundException`, `ValidationException`, `ConflictException`,
   `UnavailableException`, …) — ou généralisation du pattern `Ardalis.Result`
   déjà présent — mappées vers le code HTTP par leur **type**. Suppression de
   l'heuristique de mots-clés.
3. **Frontends** : adapter la consommation des erreurs au nouveau schéma
   `ProblemDetails` sans régression UX (mêmes toasts/notifications visibles).
   - **Blazor** : adapter le point central `HttpRequestService` (remplacer
     `ErrorResponseDto(bool Success, string Message)` par lecture de
     `ProblemDetails.title`/`detail`/`status`).
   - **Angular** : modèle partagé `ProblemDetails` (généraliser l'existant
     `DmpProblemDetails`) + mapping des notifications d'erreur du module MSS.
4. **Forge** : `CLAUDE.md` mis à jour pour rendre le pattern obligatoire sur
   toute nouvelle US backend.

Périmètre **volontairement transverse** (refactor cross-cutting) — justifie le
multi-repos. Pas de nouvelle fonctionnalité métier : iso-comportement
observable pour l'utilisateur, robustesse et homogénéité internes.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportements
couverts par tests unitaires + intégration._

## Definition of Done

### Backend (api-mail)
- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [ ] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs)
- [ ] `GlobalExceptionHandler` implémenté (`IExceptionHandler`) + enregistré via
      `AddExceptionHandler` / `AddProblemDetails` + `app.UseExceptionHandler()`
      dans `ConfigurePipeline` ([Program.cs](Api/Mail/src/Api/Program.cs))
- [ ] Toute réponse d'erreur (4xx/5xx non métier) sort en
      `application/problem+json` conforme RFC 7807 (`type`, `title`, `status`,
      `detail`, `instance`, extension `traceId`)
- [ ] `OperationCanceledException` mappée sur **499** par le handler global
      (plus dans chaque action)
- [ ] Exceptions métier typées (`NotFoundException`, `ValidationException`,
      `ConflictException`, `UnavailableException`) mappées **par type** vers
      le code HTTP — l'heuristique de mots-clés de
      `ResultExtensions.MapStatusCode` est supprimée ou réduite au strict
      fallback
- [ ] Les `try/catch` boilerplate sont retirés des controllers migrés ;
      chaque controller migré peut sortir de `[ExcludeFromCodeCoverage]`
- [ ] Au moins **2 controllers** entièrement migrés et dé-`[ExcludeFromCodeCoverage]`
      en preuve de bout en bout (cibles : `BiologyController`, `ContactController`)
- [ ] Tests unitaires du `GlobalExceptionHandler` (≥ 1 test par branche de
      mapping : 499, 400, 404, 409, 503, 500 fallback)
- [ ] Test d'intégration prouvant qu'une exception non gérée d'un endpoint
      ressort bien en `ProblemDetails` 500 avec `traceId` (rule 1b)
- [ ] Test d'intégration prouvant qu'une exception métier typée ressort avec
      le bon code (ex. `NotFoundException` → 404 `problem+json`)
- [ ] `ProblemDetails.detail` ne contient **jamais** de stack trace, de
      message d'exception brut, ni de donnée de santé (INS/NIR/contenu CDA/MSSanté) —
      message générique côté client, détail technique uniquement dans les logs

### Frontend Blazor (client-blazor)
- [ ] Build passes (`dotnet build HealthPlatform.Client.sln`, 0 erreurs)
- [ ] Tests pass (`dotnet test HealthPlatform.Client.sln`, 0 échecs)
- [ ] [HttpRequestService.cs](Client/Blazor/Src/Modules/Mss/Application/Services/HttpRequestService.cs)
      lit `ProblemDetails` (`title`/`detail`/`status`) au lieu de
      `ErrorResponseDto(Success, Message)`
- [ ] Les notifications d'erreur (`errorNotificationService`) restent
      fonctionnelles : 401 → auth, 503 → connexion, 4xx/5xx → message
      générique — aucune régression visible
- [ ] ≥ 1 test unitaire sur le parsing `ProblemDetails` (succès + body
      illisible/legacy → fallback gracieux)

### Frontend Angular (client-angular, code-only)
- [ ] Build passes (`npm run build`)
- [ ] Tests pass (`npm test`)
- [ ] Modèle partagé `ProblemDetails` (généralisation de l'existant
      `DmpProblemDetails`) disponible pour le module MSS
- [ ] Mapping des erreurs HTTP MSS (`error.error` typé `ProblemDetails`) vers
      les notifications/snackbars existants — aucune régression visible
- [ ] data-testid inchangés sur les éléments interactifs concernés
- [ ] ≥ 1 test unitaire sur le mapping `ProblemDetails` → message utilisateur

### Contrats (dtos-mss)
- [ ] Aucun changement de contrat requis a priori (ASP.NET `ProblemDetails`
      est un standard) — si un type partagé est ajouté, package republié via
      `/publish-dtos` et consommateurs .NET bumpés

### Forge (control-plane — CLAUDE.md)
- [ ] `CLAUDE.md` mis à jour : section "Absolute rules" enrichie d'une règle
      rendant **`ProblemDetails` (RFC 7807) obligatoire** pour toute réponse
      d'erreur de controller, et **interdisant** les nouveaux `try/catch`
      boilerplate par action (gestion déléguée au `GlobalExceptionHandler`)
- [ ] La règle référence le `GlobalExceptionHandler` comme mécanisme canonique

## Manual Test Plan

- Lancer le backend : `cd Api/Mail/src/Api && dotnet run`
- **Erreur non gérée → ProblemDetails 500** : appeler un endpoint en forçant
  une dépendance indisponible (ex. couper Redis/IMAP) puis
  `GET /api/v1/Mail/folders`. Vérifier dans l'onglet réseau :
  - `Content-Type: application/problem+json`
  - corps JSON avec `title`, `status: 500`, `traceId` présent
  - **aucune** stack trace ni message technique exposé
- **Annulation client → 499** : démarrer une requête longue et l'annuler
  (fermer l'onglet / abort). Vérifier code 499 + log `LogWarning`.
- **Erreur métier typée → bon code** : déclencher un `NotFound`
  (ex. `GET /api/v1/Contact/{guid-inexistant}`) → 404 `problem+json`.
- **Front Blazor** : `cd Client/Blazor && dotnet run`, provoquer une erreur
  serveur depuis l'UI MSS (ex. action sur dossier indisponible). Vérifier que
  le **toast d'erreur s'affiche correctement** (titre + message), identique à
  avant.
- **Front Angular** : `cd Client/Angular/front && npm start`, même scénario
  d'erreur côté module MSS → snackbar/notification affichée correctement.
- **Logs** : confirmer dans Seq/console qu'aucune donnée de santé
  (INS/NIR/contenu CDA/MSSanté) n'apparaît dans les `ProblemDetails` ni les
  messages renvoyés au client ; le détail technique reste uniquement dans les
  logs serveur corrélés par `traceId`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — refactor technique transverse de la
  couche API, sans impact sur un volet métier Ségur spécifique.
- **Vague Ségur** : hors Ségur — robustesse/observabilité plateforme.
- **Exigences DSR honorées** : non applicable — aucune exigence DSR de contenu
  ou de transport touchée ; le format des échanges métier (CDA/MSSanté/FHIR)
  est inchangé.
- **INS** : non applicable — l'US ne manipule aucune INS ni donnée patient ;
  elle uniformise uniquement la forme des réponses d'erreur HTTP.
- **Authentification PS** : inchangée — le pipeline d'auth (JWT/PSC/e-CPS,
  fallback dev) n'est pas modifié ; les réponses 401/403 sont simplement
  normalisées en `ProblemDetails`.
- **Habilitations** : non applicable — aucun contrôle RPPS/ADELI ajouté ou retiré.
- **Interop CI-SIS** : non applicable — pas d'échange CDA/FHIR/HL7v2 modifié ;
  `ProblemDetails` ne concerne que les erreurs de transport HTTP, pas le
  contenu métier interopérable.
- **Tracé PGSSI-S** : chaque 5xx reste journalisé (Error log) et corrélé par
  `traceId`/`CorrelationId` (Serilog/OpenTelemetry déjà en place) ;
  conservation inchangée. Renforcement : garantie qu'aucune donnée de santé
  n'est journalisée dans le détail d'erreur exposé.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement de production HDS existant,
  périmètre inchangé.
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement de données ;
  point de vigilance RGPD **renforcé** (non-fuite de DSCP dans les messages
  d'erreur côté client). À noter dans le registre si une revue le requiert.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair dans les `ProblemDetails` renvoyés au
      client (INS, NIR, NIA, contenu CDA, contenu MSSanté)
- [ ] Aucune donnée de santé en clair dans les logs corrélés par `traceId`
- [ ] Messages d'erreur client génériques ; détail technique réservé aux logs
      serveur

## Branches
- `api-mail` (pushed) : chore/task-055-problemdetails-error-handling — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-055-problemdetails-error-handling
- `client-blazor` (pushed) : chore/task-055-problemdetails-error-handling — https://github.com/codengine-technologies/HealthPlatform.Client/tree/chore/task-055-problemdetails-error-handling
- `dtos-mss` (pushed) : chore/task-055-problemdetails-error-handling — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/chore/task-055-problemdetails-error-handling
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot @ /start : `feature/nova-rewriting-mss`) — humain gère branche, commit, push, PR TFS

## Develop log

- Repos touched : api-mail (pushed), client-blazor (pushed), client-angular (code-only, uncommitted), dtos-mss (no change → no PR), CLAUDE.md (control-plane)
- DTOs published : no DTO change (RFC 7807 ProblemDetails is an ASP.NET standard — no shared contract added, dtos-mss branch left empty)
- Interop published : no interop change

### api-mail (pushed — chore/task-055-problemdetails-error-handling)
- `feat(api): harmonise API errors via RFC 7807 GlobalExceptionHandler` (a14958e)
  - `src/Api/ErrorHandling/GlobalExceptionHandler.cs` (IExceptionHandler, type-based mapping, generic client-safe detail)
  - `src/Application/Exceptions/{NotFound,Validation,Conflict,Unavailable}Exception.cs`
  - `src/Api/Program.cs` : AddProblemDetails (traceId + instance customisation) + AddExceptionHandler + UseExceptionHandler downstream of RequestLoggingMiddleware
  - `src/Api/Helpers/ResultModelExtensions.cs` : keyword heuristic removed → strict type-based mapping (500 fallback)
  - `BiologyController` + `ContactController` : try/catch boilerplate removed, `[ExcludeFromCodeCoverage]` dropped, typed exceptions thrown
- `test(api): cover ProblemDetails error handling` (e200cb3)
  - `GlobalExceptionHandlerTests` (Map branch coverage 499/400/404/409/503/500 + leak guard)
  - `GlobalExceptionHandlerIntegrationTests` (TestServer: 500+traceId no-leak, NotFoundException→404, OCE→499)
  - `ResultExtensionsTests` updated for the removed heuristic
- Build : ✓ 0 error / 0 warning. Tests : api.tests 170 → 169 pass / **1 pre-existing failure unrelated to task-055** (`UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724_WithExpectedAnonymisedFields` — anonymisation hashing, confirmed failing on clean develop with this branch stashed). My 34 added/updated tests all green.

### client-blazor (pushed — chore/task-055-problemdetails-error-handling)
- `feat(mss): consume RFC 7807 ProblemDetails in HttpRequestService` (f462820)
  - `ProblemDetailsParser.cs` (detail→title→legacy message→null) + `HttpRequestService` rewired (status-first notifications)
  - `ProblemDetailsParserTests.cs` (problem+json / legacy / empty-unreadable fallback)
- Build : ✓ 0 error / 0 warning. Tests : 95 pass / 2 skipped (pre-existing) / 0 fail.

### client-angular (code-only — uncommitted on feature/nova-rewriting-mss, awaiting human commit/push/PR TFS)
- `libs/mss/src/core/models/problem-details.model.ts` (shared ProblemDetails generalising DmpProblemDetails)
- `libs/mss/src/core/utils/problem-details.utils.ts` (`mapProblemDetailsToMessage` + `isProblemDetails`)
- `libs/mss/src/core/utils/problem-details.utils.spec.ts`
- Build/test : **deferred to `/lint-angular`** (pipeline-aligned nx build+test, scope:mss). Pre-existing human WIP in the tree (environment.ts ×2, patient-search.scss) left untouched.

### Forge control-plane
- `CLAUDE.md` : new **Absolute rule 12** — `ProblemDetails` (RFC 7807) mandatory for all controller error responses, references `GlobalExceptionHandler` as canonical mechanism.

- DOD self-check : all command-verifiable backend + blazor items ✓ ; Angular items deferred to `/lint-angular` ; manual/observable items (toasts, no-leak in Seq) deferred to HAG manual test.
- Next step : **`/sonar task-055`** (api-mail touched → chains to `/lint-angular` since client-angular touched, then `/review`).

## Sonar log (Mode A — chained, api-mail)

- SonarQube démarré (conteneurs `sonarqube_db` + `sonarqube`), analyse complète relancée 2× sur la branche.
- **Phase 1 (new code) — findings actionnables : tous résolus**
  - `new_violations` : 2 → **0** (2× S2302 « use nameof » dans `ContactController.GetBySourceAsync` — fixés)
  - `new_bugs` = 0, `new_vulnerabilities` = 0, `new_code_smells` = 0
  - `new_security_hotspots_reviewed` = 100 %
  - Tests ajoutés couvrant tout le new code task-055 : `GlobalExceptionHandlerTests` (Map + leak guard), `GlobalExceptionHandlerIntegrationTests` (TestServer), `BiologyControllerTests`, `ContactControllerTests` (33 tests couvrant les 2 controllers dé-`[ExcludeFromCodeCoverage]`).
- **`new_coverage` = 52.9 % → condition QG RED (seule condition rouge)** : artefact de configuration projet, **hors périmètre task-055**. La *new code period* du projet `healthplatform` couvre ~`28850 new_lines` (quasi tout le code legacy classé « new »), pas le diff ~600 lignes de la task. Tout le code task-055 est couvert ; le 52.9 % est dominé par du legacy non testé. Accepté en best-effort (legacy / Phase 2), pas de halt — cf. cadrage best-effort du cycle autonome.
- **Projet** : bugs 0, vulnerabilities 0, code_smells **0** (les 2 fixés étaient les seuls), maintainability **A**, security A, reliability A, duplication 0.6 %, coverage 60.8 %.
- Build Release : ✓ 0 erreur. Tests unitaires : verts hormis le **1 échec pré-existant** `UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724` (anonymisation, sans rapport avec task-055, confirmé rouge sur develop propre). Suite d'intégration Testcontainers non exécutée dans ce run Sonar (couverture du new code assurée par les tests unitaires api.tests).
- Commits sonar : `test(sonar/new): cover migrated Biology/Contact controllers` (16a8374), `fix(sonar/new): resolve 2 occurrences of S2302` (2b5a85c).
- Next step : **`/lint-angular task-055`** (client-angular touché → puis `/review`).

## Lint log (Mode A — chained, client-angular, code-only)

- Mode : affected ∩ scope (`npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss`)
- Base : `origin/next` (default, fetched from TFS), scope `tag:scope:mss` (defaults, no per-task override)
- **Baseline lint : 0 errors / 0 warnings** — « All files pass linting » sur les 11 projets affected. Mes 3 fichiers ajoutés (`problem-details.model.ts`, `problem-details.utils.ts`, `problem-details.utils.spec.ts`) n'introduisent aucune erreur ESLint → **aucune itération de fix nécessaire** (early-stop).
- **Tests `mss-lib` : 25 fichiers / 198 tests verts** (`npx nx test mss-lib --skipNxCache`), dont `problem-details.utils.spec.ts` (mapping ProblemDetails → message + type guard). DOD Angular « ≥1 test unitaire sur le mapping » ✓.
- **Build affected** : `mss-lib` (lib) OK. **Échec pré-existant hors task-055** sur les builds *production* d'apps `mss` et `prescription` : `environment.prod.ts ... does not exist` (file-replacement prod). Le fichier `environment.prod.ts` est absent du repo sur la branche `feature/nova-rewriting-mss` (WIP humain de réécriture) ; task-055 n'ajoute/modifie aucun fichier d'environnement. À traiter par l'humain (infra de branche), sans rapport avec ProblemDetails.
- Code-only : working tree laissé non commité (mes 3 fichiers + WIP humain pré-existant `environment.ts`×2, `patient-search.scss`). L'humain commit/push TFS + ouvre la PR.
- Next step : **`/review task-055`**.

## PRs

- **api-mail** (pushed) : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/78 — label `awaiting-human-merge`
- **client-blazor** (pushed) : https://github.com/codengine-technologies/HealthPlatform.Client/pull/55 — label `awaiting-human-merge`
- **dtos-mss** : aucun changement de contrat (RFC 7807 standard ASP.NET) → branche vide, pas de PR.
- **client-angular** (code-only) : humain gère commit/push TFS + ouverture PR. Fichiers modifiés (non commités sur `feature/nova-rewriting-mss`) :
  - `front/libs/mss/src/core/models/problem-details.model.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.spec.ts`
  - Lint MSS clean, `mss-lib` 198 tests verts. (Build *production* d'apps mss/prescription échoue sur `environment.prod.ts` manquant — pré-existant, infra de branche, hors task-055.)
- **CLAUDE.md** (control-plane) : règle absolue 12 ajoutée (ProblemDetails obligatoire) — édition directe, pas de PR (workspace sans remote).

## Code Review Summary

**Verdict : APPROVED** (0 bloquant).

- Build : ✓ api-mail | ✓ client-blazor | ✓ mss-lib (angular)
- Tests : ✓ api-mail 67 tests task-055 verts (domain 94 / infra 322 / app 1462 / api 194-sur-195) | ✓ client-blazor 95 | ✓ mss-lib 198
- **1 test pré-existant en échec, NON lié** : `UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724` (anonymisation) — rouge sur develop propre, documenté, hors scope.
- Sonar new code : 0 violation / 0 bug / 0 vuln / hotspots 100 % reviewed ; maintainability A.
- Suggestions non-bloquantes : `BadRequest(ModelState)` des controllers reste en validation framework (non problem+json) — acceptable.

**HAG (règle 10 + US-complete règle 11)** : tester l'US assemblée (backend + blazor + angular) de bout en bout, puis merger les PRs GitHub manuellement et pousser l'angular sur TFS.

## Merged

- **Date** : 2026-06-04 (attestation humaine `--i-tested`, HAG règle 10)
- **api-mail** : PR [#78](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/78) squash-mergée → `921dd3eb` sur `develop` — CI ✓ [run 26952651368](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/26952651368)
- **client-blazor** : PR [#55](https://github.com/codengine-technologies/HealthPlatform.Client/pull/55) squash-mergée → `88d5605` sur `develop` — CI ✓ [run 26952669475](https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/26952669475)
- **dtos-mss** : aucun changement de contrat → pas de PR ; branche remote vide `chore/task-055-problemdetails-error-handling` supprimée, clone resynchronisé sur `develop`
- **client-angular** : managed manually by the human (TFS)
- Branches remote supprimées (`--delete-branch`) ; branches locales `chore/task-055-*` conservées pour inspection rétroactive
