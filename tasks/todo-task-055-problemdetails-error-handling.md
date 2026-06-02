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
