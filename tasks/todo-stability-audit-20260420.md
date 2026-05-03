# todo-stability-audit-20260420.md — Plan de stabilisation polyrepo (master)

**Repos**: api-mail, client-blazor, client-angular, dtos-mss
**Dependencies**: aucune
**Type**: chore (→ /start MUST use `chore/` branch prefix)
**Révisé** : 2026-05-03 après clôture du chantier sécurité E009 (tasks 018-024) — voir section « Progrès au 2026-05-03 » ci-dessous.

> **Note sur `client-angular`** : ce repo est exclu de l'automation forge (CLAUDE.md).
> Le `/start` ne créera pas de branche Angular ; le humain gère manuellement la branche
> et les PR TFS côté Angular. Les items Angular de ce plan sont listés pour information
> et exécution manuelle, pas pour `/review` automatique.

> **Note sur `dtos-mss`** : inclus car plusieurs findings concernent la dérive de
> contrat (fields manquants, types inconsistants). Les modifications DTO passent
> par `/publish-dtos` selon la procédure existante.

---

## Objectif

Produire un **plan de développement** vers une version ultra-stable de la plate-forme,
sur la base d'un audit profond conduit le 2026-04-20 par 4 agents spécialisés
(`api-mail`, `client-blazor`, `client-angular`, cross-cutting). **176 risques
distincts identifiés** sur les 3 stacks et les seams inter-stacks, classés par
sévérité et regroupés en **5 phases exécutables**.

Ce fichier fait autorité : chaque phase peut donner lieu à un `/start` ultérieur
(créer un task file fils spécialisé et faire merger l'audit dans le carnet de
bord), ou être attaquée directement. Le task file master reste consultable
jusqu'à complétion de toutes les phases.

---

## Synthèse chiffrée

| Stack | Critical | High | Medium | Low | Total |
|---|---|---|---|---|---|
| `api-mail` (.NET 10) | 5 | 12 | 25 | 10 | 52 |
| `client-blazor` (Blazor WASM) | 1 | 15 | 28 | 16 | 60 |
| `client-angular` (Angular 21, zoneless, signals) | 3 | 7 | 10 | 5 | 25 |
| Cross-cutting (seams, CI, forge, secrets) | 3 | 13 | 15 | 8 | 39 |
| **Total** | **12** | **47** | **78** | **39** | **176** |

**Les 12 findings Critical sont concentrés sur 4 thèmes** :
1. Secrets exposés dans le repo (OpenAI, DB Postgres, FHIR, Flagsmith, NuGet token)
2. CORS wildcard + HTTPS non forcé
3. XSS via HTML email non sanitisé (Blazor + Angular)
4. Blocking sync-over-async dans callbacks TLS (deadlock IMAP/SMTP sous charge)

Le détail par-finding (ID, file:line, impact, fix, effort) est archivé dans les
rapports d'audit (agents `audit-api-mail`, `audit-blazor`, `audit-angular`,
`audit-cross`). Ce plan master restitue le ranking et la roadmap.

---

## Progrès au 2026-05-03 — chantier sécurité E009 (tasks 018-024)

Entre le 2026-04-20 (audit initial) et le 2026-05-03, **7 tasks** du
chantier sécurité E009 ont été livrées et mergées sur `develop`. Plusieurs
findings de cet audit sont **partiellement ou totalement clos**.

### Couches de défense ajoutées (pas explicitement dans l'audit initial)

| Couche | Tasks | Effet sur l'audit |
|---|---|---|
| **1. Identifiants opaques (Guid v7)** | 018 + 019 + 020 | 100% des PK Postgres en `uuid` v7 (RFC 9562, .NET-side). 0 routes `{*:int}`, 0 hack `BitConverter.ToInt32` (`ContactDto.GetIntId` supprimé). Anti-énumération URL totale. Crée le besoin de la couche 3. |
| **2. Authentification cryptographique JWT** | 021 | `AddJwtBearer` Keycloak (signature + issuer + audience + lifetime). `PolicyScheme JwtOrTestBypass` (TestBypassAuthenticationHandler dédié, hard-block en Production). `FallbackPolicy = RequireAuthenticatedUser` secure-by-default. `UserContextEnricherMiddleware` peuple `UserContextInfo` depuis claims JWT validés. **Ferme X-AUTH-01 et API-DI-01.** |
| **2bis. Endpoints anonymes + flux SSE refermés** | 022 | Retrait du `[AllowAnonymous]` temporaire sur 5 controllers (Ai/Directory/FeatureFlag/MailEvents/Notifications). SSE résolu exclusivement depuis claim JWT (ignore `?email=`). `RequestLoggingMiddleware.ScrubQueryStringToken` masque `?token=...` AVANT `LogContext.Push` → JWT propagé en query SSE n'apparaît jamais en clair en Seq. **Ferme partiellement BLZ-SECURITY-05, NG-SEC-03 et API-LOG-01/05/06 (volet SSE).** |
| **3. Ownership scoping repositories** | 023 | 5 dépôts (Contact, MailSignature, MailTemplate, MssAuditTrace, PendingAction) filtrent cumulativement `Id == X && UserId == currentUserId`. `BaseRepository.GetCurrentUserIdAsync` factorisé. Convention 404 (jamais 403) sur ownership KO pour ne pas leaker l'existence des Guids. **Anti cross-tenant après leak Guid** — vecteur IDOR résiduel post-tasks 018-022. **+21 tests cross-tenant** (`CrossTenantOwnershipTests.cs`). |
| **(observabilité)** | 024 | Instrumentation lock IMAP : `MailClientSession` carry `(operation, acquiredAt)`, `MailClientSessionManager.GetCurrentLockHolder` exposé, `ImapLockScope.AcquireAsync` enrichit cancel/timeout warnings avec `HolderOperation` + `HolderHeldMs`, success log Debug → Information. **Ferme partiellement API-LOG-02** (structured logging) sur le périmètre lock IMAP. Fix log-level race `MailRepository.AddNewMail` (Error → Information sur le succès du fallback duplicate-key). |

### Findings audit clos / partiellement clos

| Finding ID | État | Tasks | Note |
|---|---|---|---|
| `X-AUTH-01` Auth unifiée Bearer + retirer Client-Email/Client-Session-Id | ✅ **DONE** | 021 | `AddJwtBearer` + `UserContextEnricherMiddleware`. `RequestHelper.TryExtractJwtToken` désormais `internal` (legacy, conservé pour les tests existants seulement). Headers `Client-Email`/`Client-Session-Id` plus jamais lus côté backend. |
| `API-DI-01` Décoder JWT middleware, claims via HttpContext.User | ✅ **DONE** | 021 | Pipeline AuthN/AuthZ ASP.NET Core en place. Claims accessibles via `User.FindFirstValue(ClaimTypes.Email)` etc. Plus aucun controller ne fait l'extraction de claims à la main. |
| `BLZ-SECURITY-05` / `NG-SEC-03` Tokens hors URL SSE | ⏳ **PARTIEL** | 021 + 022 | Le token reste en query string (`?token=...`) car EventSource native API ne supporte pas le header `Authorization`. **Mais** : (1) la validation crypto JWT (task-021) empêche tout forgeage même si le token est exfiltré, (2) `ScrubQueryStringToken` (task-022) masque `?token=***` AVANT que les logs n'atteignent Seq. Le risque résiduel est maintenant : exfiltration via `Referer` header HTTP cross-origin → mitigé par CORS Phase 1. |
| `BLZ-SECURITY-03` `[Authorize]` sur pages Blazor | ⏳ **PARTIEL** | 021 | Côté **backend**, `FallbackPolicy = RequireAuthenticatedUser` rend toute route `[Authorize]` implicitement. **Côté Blazor client (route guard SPA)**, l'attribut reste à poser sur les pages pour éviter de rendre la page côté navigateur avant le 401 du backend (UX). |
| `API-LOG-01` / `API-SEC-05` / `API-SEC-06` Redaction logs token preview | ⏳ **PARTIEL** | 022 | `?token=...` query string scrubbed dans `RequestLoggingMiddleware`. Restent à auditer : `SmtpConnectionFactory` et `RequestHelper` (token preview en clair dans logs serveur si activé). |
| `API-LOG-02` Structured logging (LogError($"...{ex.Message}") → templates) | ⏳ **PARTIEL** | 024 + 022 | Cas spécifiques fixés (`MailRepository.AddNewMail` Error → Information, `MailClientSessionManager.LockImapClientAsync` enrichi `HolderOperation`/`HolderHeldMs`/`WaitTimeMs`). **Audit grep complet sur `LogError\(\$"` reste à faire** sur le reste du codebase. |

### Findings audit confirmés inchangés (à attaquer en Phase 1+)

Tous les autres findings Critical / High de l'audit restent ouverts. **9 des 12 Critical** sont toujours actifs :
- Secrets en clair dans le repo (5 trouvés)
- CORS wildcard
- HTTPS non forcé / pas de HSTS
- XXE dans `AutoconfigService.cs`
- HtmlSanitizer manquant côté Blazor + bypassSecurityTrustHtml côté Angular
- Blocking sync-over-async dans callbacks TLS (deadlock IMAP/SMTP sous charge)

### Nouveau finding révélé par le chantier (à intégrer)

| ID | Nature | Tasks |
|---|---|---|
| **X-LOG-04** (nouveau) | **Audit grep `LogError($"...")` exhaustif sur le codebase** : task-024 a fixé un cas isolé, mais le pattern est utilisé dans d'autres services (à recenser). Liste à produire avec `grep -rn 'LogError(\$"' src/`. | À ouvrir |

---

## Phasage (5 phases)

### Phase 1 — Urgences sécurité (1-3 jours)

**Objectif** : sortir du risque immédiat. Rien en Phase 1 ne peut attendre.

| Item | Où | Finding IDs | Effort |
|---|---|---|---|
| **Révoquer immédiatement la clé OpenAI** exposée dans `src/Api/appsettings.json:59` et régénérer via `https://platform.openai.com/account/api-keys`. Toute personne ayant accès au repo (ou à un clone) a la clé. | api-mail | API-SEC-01, X-CFG-02 | S |
| **Révoquer/régénérer les creds AppHost** : `flagsmith_pwd_2026!`, `FhirOptions__ApiKey`, `FLAGSMITH_ENVIRONMENT_KEY`, token NuGet dans `nuget.config`. | api-mail | API-SEC-02, X-CFG-03 | S |
| **Purger git history** des secrets révoqués (BFG ou `git filter-repo`), force-push coordonnée (tous les repos impactés). À faire APRÈS rotation, avec coordination humaine. | api-mail | API-SEC-01, API-SEC-02 | M |
| **Ajouter `appsettings.Development.json` à `.gitignore`** et injecter les secrets via env vars / .NET User Secrets / dotnet-env. | api-mail | API-SEC-01/02 | S |
| **Pre-commit hook secrets** (detect-secrets / gitleaks) bloquant `sk-proj-`, `ghp_`, mots de passe en clair, clés API communes. | workspace | X-WF-02 | S |
| **CORS explicite** : remplacer `.AllowAnyOrigin()` par `WithOrigins("http://localhost:4200", "http://localhost:5213", "https://<prod-domain>")`. Paramétrer via `ALLOWED_ORIGINS` env var. | api-mail | API-SEC, X-SEC-01, X-HTTP-02 | S |
| **Forcer HTTPS** en production : activer `UseHttpsRedirection()` et ajouter header HSTS (`Strict-Transport-Security: max-age=31536000; includeSubDomains`). | api-mail, client-blazor | BLZ-SECURITY-04, X-SEC-02 | S |
| **Fix XXE dans `AutoconfigService.cs:135`** : remplacer `XDocument.Parse(xml)` par `XmlReader.Create(stream, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null })`. | api-mail | API-SEC-03 | S |
| **Sanitiser HTML email Blazor** : installer `HtmlSanitizer`, passer `SelectedMail.Content.BodyHtml` à travers `new HtmlSanitizer().Sanitize(html)` avant tout `MarkupString` ou `loadHtmlInShadowDom`. | client-blazor | BLZ-SECURITY-01, BLZ-SECURITY-02, BLZ-JSINTEROP-03 | M |
| **Sanitiser HTML email Angular** : retirer tous les `bypassSecurityTrustHtml()` sur `bodyHtml` (mail-body, medical-document-modal). Laisser Angular sanitizer faire son travail (innerHTML seul est sanitisé par défaut). Si besoin d'HTML complexe médical, sanitiser côté backend (HtmlSanitizer.NET) avant de pousser. | client-angular | NG-SEC-01, NG-SEC-02 | M |
| ⏳ **PARTIEL (task-021 + task-022)** — **Sortir les tokens des URLs SSE/EventSource** : côté Blazor `MailSseService.cs:168`, côté Angular `notification-stream.service.ts:54`. **État 2026-05-03** : (1) le token est désormais validé crypto par `AddJwtBearer` (task-021) → impossible à forger même si exfiltré ; (2) `RequestLoggingMiddleware.ScrubQueryStringToken` (task-022) masque `?token=...` avant que les logs n'atteignent Seq. **Reste à faire** : décider si on bascule de `EventSource` vers `fetch()` stream pour pouvoir poser `Authorization: Bearer` en header (alternative : durcir CORS Phase 1 pour empêcher l'exfiltration via `Referer` cross-origin). | client-blazor, client-angular | BLZ-SECURITY-05, NG-SEC-03 | M |
| ⏳ **PARTIEL (task-021)** — **`@attribute [Authorize]`** sur toutes les pages Blazor authentifiées (`Patient.razor`, `Mail.razor`, `Contacts.razor`…). **État 2026-05-03** : côté **backend**, `FallbackPolicy = RequireAuthenticatedUser` rend toutes les routes `[Authorize]` implicitement → l'API est bétonnée. **Reste à faire** : poser l'attribut côté Blazor SPA pour éviter de rendre la page client avant le 401 (UX, pas sécurité). | client-blazor | BLZ-SECURITY-03 | S |

**Sortie Phase 1** : plus aucun secret dans le repo, CORS/HTTPS bétonné, XSS bouchées, tokens hors URL.

---

### Phase 2 — Stabilité concurrence & fuites mémoire (1-2 semaines)

**Objectif** : éliminer les sources de deadlock, OOM, leaks d'abonnements et de ressources.

#### 2a. Backend — async & resources

| Item | Finding IDs | Effort |
|---|---|---|
| **Éliminer les `GetAwaiter().GetResult()` dans les callbacks TLS** (`BackgroundImapService.cs:375`, `ImapConnectionService.cs:304`, `ImapConnectionManager.cs:102`). Revoir le design : valider le certificat en amont de la connexion, ou rendre le `ICertificateValidator` synchrone. | API-ASYNC-01/02/03 | M |
| **Corriger les autres `GetAwaiter().GetResult()`** dans `BackgroundSyncManager.cs:113, 138`. | API-ASYNC-04/05 | M |
| **Traquer les `_ = Task.Run(...)` fire-and-forget** et les remplacer par des tâches observées (try/catch + logger, ou background worker dédié). Cas connus : `MailController`, `BackgroundSyncManager.cs:55`. | API-ASYNC-06/07 | M |
| **`ConfigureAwait(false)` sur toute la couche Application/Infrastructure** (library code). Pas besoin sur Api endpoints. Peut être automatisé avec l'analyzer `CA2007`. | API-ASYNC-08 | L |
| **Propager `CancellationToken`** dans toutes les chaînes async (du controller vers l'infra). | API-ASYNC | M |
| **`HttpClient` via `IHttpClientFactory`** partout. Cas `SemanticKernelExtensions.cs:66, 74` créent un `new HttpClient()` → passer en injection. | API-RES-01 | M |
| **Cleanup temp files** après extraction XDM dans `BackgroundImapService.cs:427`. Try/finally + Delete. | API-RES-03 | S |
| **Disposal ImapClient** : try/finally autour des création/remplacement dans `BackgroundImapService.cs:292-293`. | API-RES-02 | S |

#### 2b. Blazor — subscriptions, lifecycle, state

| Item | Finding IDs | Effort |
|---|---|---|
| **Éliminer `async void` dans les timers** : `FolderComponent.OnTimerElapsed`, `MailListComponent.OnRefreshTimerElapsed`, `SyncProgressBar.OnHideTimerElapsed`. Retourner `Task`, wrap en try/catch, annuler le timer dans `Dispose`. | BLZ-LIFECYCLE-01/02/03, BLZ-ASYNC-03 | M |
| **`CancellationTokenSource` annulé dans `Dispose`** : `MailListComponent.cs:229` et partout où `_cts` est créé. | BLZ-STATE-03 | S |
| **Audit des souscriptions event-service** (`RefreshService`, `MailEventService`, `FolderEventService`, `SyncProgressService`) : implémenter `IAsyncDisposable` sur `BaseComponent` et toutes les subclasses ; unsubscribe exhaustif dans `Dispose`. | BLZ-SUBSCRIPTIONS-01/02/03/04/05 | M |
| **Pattern `ShouldRender` + `@key`** sur les gros `@foreach` (`MailListComponent.razor:122`, timeline, listes patient). | BLZ-PERF-01/03 | M |
| **`firstRender` guard** sur `LoadImagePreviewsAsync` (`AttachmentComponent.razor:138`) et autres `OnAfterRenderAsync` lourds. | BLZ-PERF-02 | S |
| **ConfigureAwait(false)** dans `HttpRequestService` et services Blazor non-UI. | BLZ-ASYNC-04 | M |
| **IJSObjectReference / DotNetObjectReference Dispose** vérifié sur tous les composants JSInterop. | BLZ-JSINTEROP-02/04 | M |
| **ErrorBoundary** autour de `MailBodyComponent`, `MailDetailComponent`, `AttachmentComponent`. | BLZ-ERROR-03 | S |

#### 2c. Angular — RxJS leaks, zones, effects

| Item | Finding IDs | Effort |
|---|---|---|
| **Fuite de polling `sync-progress-widget.component.ts:174-193`** : `interval(1000)` sans `takeUntilDestroyed()` sur le stream externe. Ajouter et retirer le `pollingActive` flag. | NG-RXJS-01 | S |
| **Garde destroy sur `setTimeout` recursif** `notification-dispatcher.component.ts:67-71`. | NG-RXJS-02 | S |
| **Uniformiser `takeUntilDestroyed()`** : retirer les `autoSaveSubscription` manuels (mail-compose). Un seul mécanisme par stream. | NG-RXJS-03 | S |
| **Completer les `Subject` / `ReplaySubject`** dans `mail-event.service.ts` via `ngOnDestroy`. | NG-RXJS-05 | M |
| **Debounce sur `effect()` de patient-resolution** (`mail-compose.component.ts:68-79`) pour éviter les rafales d'appels. | NG-SIGNAL-01 | S |
| **Retirer le `setInterval` manuel + `tick` signal** dans `offline-status-widget` : utiliser `toSignal(interval(1000).pipe(...))`. | NG-CD-02, NG-SIGNAL-02 | S |
| **Consolidation `MailEventService`** : tout en signals OU tout en Subjects, pas un mix. Préférer signals. | NG-ARCH-01 | M |

**Sortie Phase 2** : plus de deadlock IMAP/SMTP, plus de fuites d'abonnements ni de timers, gestion des ressources propre sur les 3 stacks.

---

### Phase 3 — Contrats cohérents & gestion d'erreurs unifiée (1-2 semaines)

**Objectif** : rendre les seams inter-stacks déterministes et réduire les "surprises" côté consommateurs.

| Item | Finding IDs | Effort |
|---|---|---|
| **Middleware `UseExceptionHandler` + ProblemDetails RFC 7807** globalisé sur `api-mail`. Remplacer tous les `StatusCode(500, "string")` par `Problem(...)` ou `Result<T>.Error().ToActionResult()`. | X-ERR-01 | M |
| **Code d'erreur standardisé** (enum `TokenExpired=1001`, `ValidationFailed=1003`…) inclus dans ProblemDetails.Extensions. Mapping côté Angular + Blazor vers messages utilisateur. | X-ERR-02 | M |
| **Convention status codes** : 200 + tableau vide pour les listes (jamais 204). Ban `499`. Lint rule possible. | X-ERR-03, X-HTTP-04 | S |
| **DTO drift — ajouts Angular manquants** : `inReplyTo`, `references`, `isPartOfThread`, `threadCount`, `isThreadRoot`, `readReceiptTo`, `readReceiptSentAt` sur `MailDto`. Régénérer via `/publish-dtos` + codegen Angular. | X-DTO-02 | S |
| **DTO drift — types** : documenter `Guid-as-string` sur `ContactDto.id` (X-DTO-01), convention ISO-8601 UTC pour `DateTimeOffset` (X-DTO-03), `uint` UID côté C# ↔ convertir en `string` côté TS si risque précision (X-DTO-04). | X-DTO-01/03/04 | M |
| ✅ **DONE (task-021)** — **Auth unifiée** : `Authorization: Bearer {jwt}` + `X-PSC-Token` (optionnel). Retirer `Client-Email` et `Client-Session-Id` (extraire depuis claims JWT). Aligner Blazor et Angular sur le même pattern. **État 2026-05-03** : `AddJwtBearer` Keycloak + `UserContextEnricherMiddleware` qui peuple `UserContextInfo` depuis claims (`Email = email \|\| preferred_username`, `ClientSessionId = sid \|\| jti`, `KeycloakToken` via `SaveToken=true`, `X-PSC-Token` lu inconditionnellement). `RequestHelper.TryExtractJwtToken` désormais `internal` (legacy, conservé pour les tests existants seulement). ~120 appels supprimés dans 23 controllers. | X-AUTH-01 | L |
| **Token refresh margin harmonisée** à 60s sur les 2 frontends. | X-AUTH-02 | M |
| **Correlation ID propagation** : interceptor Angular + Blazor qui capture `X-Correlation-Id` en réponse et le renvoie sur les requêtes suivantes. | X-OBS-01 | S |
| **Versioning API consistent** : tous les controllers utilisent `[Route("api/v{version:apiVersion}/[controller]")]`. Fix `DraftController` qui a un path hardcodé. | X-HTTP-03 | S |
| **CSRF anti-forgery middleware** côté backend si les clients envoient déjà `X-CSRF-TOKEN`. Sinon retirer le code mort Blazor. | X-SEC-03 | M |
| **Alignement version DTOs** : le .csproj est à `165.0.0` mais les consumers pinnent `196.0.0`. Reconcilier + documenter. | X-VER-01 | S |
| **Codegen TypeScript automatisé** dans `/publish-dtos` : après publish NuGet, régénérer les models Angular (OpenAPI generator ou équivalent) et commit. | X-VER-02 | M |
| **`ProblemDetails` parsé côté Blazor** dans `HttpRequestService` (aujourd'hui seul `ErrorResponseDto` est parsé). | BLZ-HTTP-02 | M |
| **Retry policy Polly** sur `HttpRequestService` (Blazor) et interceptor Angular. Exponential backoff sur 5xx. | BLZ-HTTP-03 | M |
| **Timeout explicite** sur `HttpClient` Blazor (`30s` par défaut, override configurable). | BLZ-HTTP-04 | S |
| **Gestion erreurs user-facing Angular** : `mail-detail.component.ts:94-105` et `patient-timeline.component.ts:148-155` catchent silencieusement. Surface l'erreur via snackbar / error state. | NG-HTTP-01/02/03 | M |

**Sortie Phase 3** : un client qui reçoit une erreur sait exactement ce que c'est, les DTOs sont alignés, l'auth est uniforme, les corrélations tracent de bout en bout.

---

### Phase 4 — Qualité code, tests & maintenabilité (2-3 semaines)

**Objectif** : rattraper la dette de test, renforcer la safety à la compilation, préparer les refactors.

#### 4a. Tests

| Item | Finding IDs | Effort |
|---|---|---|
| **Intégration tests api-mail** : couverture ≥1 test (happy + 1 failure) par endpoint. 20+ controllers, seulement 3 fichiers de tests aujourd'hui (DraftController, NotificationsController). Viser la couverture règle 1b CLAUDE.md. | API-HTTP-01, API-TEST-01 | L |
| **Unit tests Domain** : invariants sur `Mail`, `MailMedicalDocument`, `MailPatient`. | API-TEST-02 | M |
| **Integration tests isolés** : remplacer PostgreSQL/IMAP externes par Testcontainers ou mocks. | API-TEST-03 | M |
| **Projet de tests Blazor** (`HealthPlatform.Client.Tests` avec bUnit). Cibler `MailBodyComponent`, `MailListComponent`, `NewMailComponent`. | BLZ-TESTING-01/02 | L |
| **Specs Angular** : `app.component.spec.ts`, `app.routes.spec.ts`, guards, route transitions (app shell 0 spec aujourd'hui). | NG-TEST-04 | M |
| **`data-testid` coverage** : audit de tous les éléments interactifs sur les 3 frontends. Règle à enforcer via linter custom (CLAUDE.md DOD standard). | NG-TEST-01/02/03, BLZ-TESTID-01/02/03 | M |

#### 4b. Compile-time safety & design

| Item | Finding IDs | Effort |
|---|---|---|
| **`#nullable enable` sur toutes les entités Domain** (`src/Domain/Entities/*.cs`). Annoter proprement les `?`. | API-NULL-01, API-ARCH-01 | M |
| **Non-null assertions** sur `BackgroundImapService.cs:65`, `EmailBuildingService.cs:104-106` → null-guards explicites. | API-NULL-02/03 | S |
| **N+1 Patient dans `MailRepository`** (`:98-99, 148-149, 230-233`) : batch lookup par `Contains(insList)`. | API-EF-01 | M |
| **`AsNoTracking()`** systématique sur les queries read-only. | API-EF-02 | M |
| **`SaveChangesAsync` unique** par use-case (atomicité). `AddNewMail` actuel en fait plusieurs. | API-EF-03 | M |
| **ConcurrencyToken** (`[Timestamp] public byte[] RowVersion`) sur `Mail` et entités éditables. | API-EF-04 | M |
| **Rate limiting** via `Microsoft.AspNetCore.RateLimiting` sur endpoints sensibles (sync, enrichment, search). | API-HTTP-03 | M |
| **`IValidateOptions<T>` + `ValidateOnStart`** sur toutes les configs critiques (OpenAi, SMTP, IMAP, Keycloak, PSC). | API-CFG-02 | M |
| **Structured logging** : remplacer les `LogError($"...{ex.Message}")` par `LogError(ex, "message template {Prop}", prop)`. | API-LOG-02 | M |
| **Redaction logs** : ne plus logger de token preview (SmtpConnectionFactory, RequestHelper). | API-LOG-01, API-SEC-05/06 | S |
| **Kernel en Singleton** (pas Transient) dans `SemanticKernelExtensions`. | API-DI-02 | S |
| **Décoder JWT dans middleware**, exposer les claims via `HttpContext.User` (plus besoin d'extraire via headers custom). | API-DI-01 (lié à X-AUTH-01) | M |

#### 4c. i18n, a11y, UX

| Item | Finding IDs | Effort |
|---|---|---|
| **Audit i18n Blazor** : toutes les strings françaises en dur (`MailDetailComponent.razor:428`, `BiologyComponent.razor:13`, …) passées à `IStringLocalizer<>`. | BLZ-I18N-01/02 | M |
| **`DateTime.ToString()` → `CultureInfo.InvariantCulture`** partout où l'affichage est machine-lisible. | BLZ-I18N-03 | S |
| **Culture fixée à startup** Blazor WASM (fr-FR par défaut, override utilisateur possible). | BLZ-WASM-01 | S |
| **a11y Angular** : `role="tab"`, `aria-selected`, `aria-label` sur boutons icône-only (patient-timeline, mail-body tabs, downloads). | NG-A11Y-01/02/03 | S |
| **a11y Blazor** : keyboard handlers sur tabs, focus management modales (Radzen à vérifier). | BLZ-A11Y-01/03 | M |
| **Validations forms Blazor** : `<DataAnnotationsValidator>`, disable submit pendant envoi, validation email, `accept` sur `InputFile`. | BLZ-FORMS-01/02/03/04 | S |
| **Error handling send mail Angular** (`mail-compose.component.ts:378-457`) : arrêt du `try/catch` silencieux. | NG-ERR-01 | M |

#### 4d. Performance & bundle

| Item | Finding IDs | Effort |
|---|---|---|
| **Pipeline Markdown en singleton** (`MarkdownService.cs:15` → `static readonly`). | BLZ-WASM-02 | S |
| **Tiptap en `@defer`** dans Angular (chargé à l'ouverture du compose). | NG-PERF-01 | M |
| **Bornes sur `ConcurrentQueue` enrichissement** `MailListComponent.cs:234`. | BLZ-PERF-04 | M |
| **`StringBuilder` dans `BackgroundImapService.cs:484`** (concat en boucle). | API-PERF-02 | S |
| **Retirer `Task.Run` inutile** sur code CPU synchrone (`EmailBuildingService.cs:33-42`). | API-PERF-01 | S |

#### 4e. Architecture

| Item | Finding IDs | Effort |
|---|---|---|
| **Refactor `MailListComponent.razor`** (>500 lignes) en sous-composants : pagination, toolbar, table. | BLZ-ARCH-01/02 | L |
| **Extract PDF state** (5 Maps dans `mail-body.component.ts`) en service ou signal state unique. | NG-ARCH-03 | M |
| **Constructor → `ngOnInit`** : déplacer le setup de souscriptions (mail-detail). | NG-ARCH-02 | S |
| **Logique hors Component Blazor** : `MailListComponent` filtre/pagine/sélectionne dans le composant, déplacer dans `IMailListService`. | BLZ-ARCH-02 | L |
| **Anaemic domain** : injecter du comportement dans les entités (`Mail.SetRead()`, etc.). | API-ARCH-02 | L |
| **`MailFactory`** dans Application pour isoler la construction d'entités (`MailRepository` les crée aujourd'hui). | API-ARCH-03 | M |

**Sortie Phase 4** : tests en place (rule 1b respectée), null-safety bétonnée, EF sain, i18n/a11y propres, perfs correctes, architecture plus lisible.

---

### Phase 5 — Outillage forge, CI & qualité continue (1-2 semaines)

**Objectif** : ancrer la stabilité via des garde-fous automatiques, pour que les régressions soient bloquées à la source.

| Item | Finding IDs | Effort |
|---|---|---|
| **GitHub Actions par stack** : `.github/workflows/api-mail.yml`, `.github/workflows/client-blazor.yml`, `.github/workflows/client-angular.yml`. Chaque workflow : checkout → setup → restore/install → build → test → lint → Sonar. Déclencheur : PR vers develop. | X-CI-01 | M |
| **Coverage threshold** : ≥90% (rule 1c CLAUDE.md). Upload via dotnet sonarscanner / codecov. Bloquer si <80%. | X-CI-02 | M |
| **Intégrer `/sonar`** dans la boucle qualité : scheduler régulier ou déclenchement manuel après merge. Réutilise l'agent créé en 2026-04-20 (`agents/sonar.md`). | — | S |
| **`verify-before-push.sh` enrichi** : ajouter `dotnet test` et `npm test` (aujourd'hui seulement build). | X-WF-01 | S |
| **Task file linter** : script qui valide `**Repos**:`, `**Type**:`, sections DOD, Manual Test Plan. Appelé en pré-`/start`. | X-WF-03 | S |
| **Pre-commit hook secrets** (déjà en Phase 1) intégré dans `.claude/hooks/`. | X-WF-02 | S |
| **`.editorconfig` workspace root** avec overrides par langage. | X-SHARED-01 | S |
| **Issue templates GitHub** (`bug`, `feature`, `chore`) sous `.github/ISSUE_TEMPLATE/`. | X-SHARED-03 | S |
| **CI pre-flight DTO** : vérifier que les versions pinnées dans `Directory.Packages.props` existent réellement sur le feed NuGet. | X-SHARED-02, X-VER-01 | S |
| **Guard git pre-commit sur `src/core/`** (pas seulement forge hook). | X-FROZEN-01 | M |
| **Clarification Angular core models** : auto-générés ou hand-written ? Si auto : retirer du périmètre "frozen". | X-FROZEN-02 | S |
| **OTel frontend** (Angular + éventuellement Blazor) : `@opentelemetry/web` avec `traceparent` propagé vers api-mail. Fermeture du trace end-to-end. | X-OBS-02/03 | L |
| **Décision Angular ↔ forge automation** : migrer vers GitHub (et intégrer au forge) OU acter définitivement la gestion manuelle dans CLAUDE.md avec checklist explicite pour les PRs paires. | X-CI-03 | L (décision d'abord, exécution ensuite) |

**Sortie Phase 5** : pipeline CI complet, Sonar récurrent, hooks préventifs, documentation d'invariants. La dette ne se recrée plus en silence.

---

## Definition of Done

Ce task file est considéré "done" lorsque **les 12 findings Critical et les 47 High sont clos**.
Les Medium et Low sont portés par les phases suivantes (rubriques "qualité continue"
dans Sonar / backlog forge).

### Phase 1 — Urgences sécurité
- [ ] Clé OpenAI révoquée et régénérée via nouveau secret provider
- [ ] Secrets AppHost (DB, FHIR, Flagsmith, NuGet) tous révoqués/régénérés
- [ ] Git history purgée des secrets (BFG ou `git filter-repo`)
- [ ] `appsettings.Development.json` dans `.gitignore`, secrets injectés via User Secrets / env
- [ ] Pre-commit hook secrets actif (bloque `sk-proj-`, `ghp_`, etc.)
- [ ] CORS explicite (plus de wildcard) sur `api-mail`
- [ ] HSTS + HTTPS redirect actifs en prod
- [ ] XXE fixé dans `AutoconfigService`
- [ ] HtmlSanitizer en place côté Blazor (MarkupString email body)
- [ ] Angular sans `bypassSecurityTrustHtml` sur `bodyHtml`
- [ ] Tokens hors URL (SSE / EventSource → headers)
- [ ] `[Authorize]` sur pages Blazor authentifiées

### Phase 2 — Stabilité concurrence & fuites
- [ ] 0 `GetAwaiter().GetResult()` dans les callbacks TLS
- [ ] 0 `_ = Task.Run(...)` non observé en production (audit complet)
- [ ] `ConfigureAwait(false)` systématique en couche library backend
- [ ] `HttpClient` uniquement via `IHttpClientFactory`
- [ ] Temp files XDM cleanup OK
- [ ] Timers Blazor : 0 `async void`, `CancellationToken` propagé, `Dispose` annule
- [ ] `BaseComponent` Blazor `IAsyncDisposable` + unsubscribe exhaustif
- [ ] `takeUntilDestroyed()` systématique côté Angular (0 `.subscribe()` non-protégé)
- [ ] Polling `sync-progress-widget` borné et propre

### Phase 3 — Contrats cohérents
- [ ] `ProblemDetails` RFC 7807 sur 100% des endpoints
- [ ] Codes d'erreur enum + mapping frontend
- [ ] MailDto TypeScript aligné (champs threading, read-receipt)
- [ ] DTO dates et UID documentés / typés correctement côté TS
- [ ] Auth unifiée `Authorization: Bearer` partout (headers custom retirés)
- [ ] Correlation ID end-to-end (frontend → backend → logs)
- [ ] Versioning API consistent sur 100% des controllers
- [ ] `Directory.Packages.props` aligné avec `.csproj` Dtos
- [ ] `/publish-dtos` régénère les types Angular automatiquement

### Phase 4 — Qualité code, tests
- [ ] ≥1 test d'intégration par endpoint api-mail (règle 1b CLAUDE.md)
- [ ] Projet `HealthPlatform.Client.Tests` (bUnit) créé, couvre les composants clés
- [ ] Specs Angular app shell + guards ajoutées
- [ ] `data-testid` audit complet — règle enforcée
- [ ] `#nullable enable` sur toutes les entités Domain
- [ ] N+1 patient lookup fixé, `AsNoTracking` systématique
- [ ] `ConcurrencyToken` sur Mail + entités éditables
- [ ] Rate limiting en place
- [ ] i18n Blazor : 0 string française en dur (audit grep)
- [ ] a11y : `aria-*` sur tabs, focus trap modales

### Phase 5 — CI / outillage
- [ ] GitHub Actions pour les 3 stacks (build + test + lint + Sonar)
- [ ] Coverage ≥ 80% bloquant sur PR
- [ ] `/sonar` planifié (manuel ou cron)
- [ ] `verify-before-push.sh` exécute les tests
- [ ] Task file linter actif
- [ ] Décision formalisée Angular ↔ forge automation
- [ ] Pre-commit secrets + frozen-files (git pre-commit, pas seulement forge)

---

## Manual Test Plan

**Attention** : ce plan couvre 5 phases. Le MTP liste **le test de smoke global** à exécuter
après **chaque phase** (pas seulement à la fin). Chaque phase devrait idéalement faire
l'objet d'un `/start` distinct ou d'un commit group validé indépendamment.

### Smoke test global (après chaque phase)

1. **Build local** des 3 stacks :
   ```bash
   cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln --configuration Release
   cd Client/Blazor && dotnet build HealthPlatform.Client.sln --configuration Release
   cd Client/Angular && npm ci && npm run build
   ```
2. **Tests** :
   ```bash
   cd Api/Mail && dotnet test HealthPlatform.Api.Mail.sln --configuration Release
   cd Client/Blazor && dotnet test HealthPlatform.Client.sln --configuration Release
   cd Client/Angular && npm test -- --watch=false
   ```
3. **AppHost Aspire** : `cd Api/Mail && dotnet run --project src/AppHost`. Dashboard doit démarrer, tous les services UP.
4. **Flux fumée métier** :
   - Ouvrir Angular (`npm start` ou prod build servie)
   - Se connecter (PSC ou Keycloak selon env)
   - Lister les mails d'une boîte
   - Ouvrir un mail avec PJ → vérifier affichage correct, pas de XSS (check console navigateur)
   - Composer et envoyer un mail de test
   - Idem sur Blazor (même flux)
5. **Vérif Sonar** : le Quality Gate n'a pas régressé après la phase.
6. **Vérif observabilité** : un `X-Correlation-Id` est présent en réponse et propagé dans les logs Seq/Serilog.

### Vérifications spécifiques Phase 1 (sécurité)

- `git log -p --all | grep -E "(sk-proj-|ghp_|flagsmith_pwd)"` → **vide** après purge
- `curl -H "Origin: https://evil.example.com" http://localhost:7012/api/v1/...` → rejeté (CORS)
- `http://localhost:...` (HTTP) en prod → redirige 301 vers HTTPS
- Envoyer un mail test avec `<script>alert(1)</script>` en body → non exécuté côté Blazor et Angular
- EventSource / SSE : `X-Correlation-Id` visible, token dans header `Authorization` seulement (pas en query)

### Vérifications spécifiques Phase 2 (concurrence)

- Lancer 10 connexions IMAP en parallèle → aucun deadlock, aucun thread pool starvation
- Ouvrir 20 mails successivement en Blazor → pas de fuite mémoire (DevTools memory profiler)
- Naviguer rapidement entre patients en Angular → pas d'intervals résiduels (`performance.getEntriesByType('resource')`)

### Vérifications spécifiques Phase 3 (contrats)

- Forcer une erreur backend (ex. payload invalide) → réponse JSON au format RFC 7807 avec `type`, `title`, `status`, `detail`, `instance`, `code`
- Tracer une requête end-to-end : `X-Correlation-Id` identique entre requête Angular, logs api-mail, audit trace

### Vérifications spécifiques Phase 5 (CI)

- Ouvrir une PR factice → workflows se déclenchent sur les 3 stacks
- Descendre artificiellement la coverage sous 80% → PR bloquée
- Tenter de commit un secret → pre-commit hook bloque

---

## Références audits

Les 176 findings détaillés (ID, file:line, evidence code, impact précis, fix suggéré, effort chiffré) sont archivés dans les rapports produits le 2026-04-20 par les 4 agents d'audit :
- `audit-api-mail` — .NET 10 backend
- `audit-blazor` — Blazor WASM frontend
- `audit-angular` — Angular 21 frontend (zoneless, signals)
- `audit-cross` — seams inter-stacks + CI + forge

Un finding mentionné dans ce plan master renvoie toujours à son `ID` dans le rapport d'origine (ex. `API-ASYNC-01`, `BLZ-SECURITY-01`, `NG-RXJS-01`, `X-CFG-02`). Conserver ces rapports comme archives lors du traitement des phases — ils contiennent les extraits de code exacts qui ne sont pas recopiés ici par souci de taille.
