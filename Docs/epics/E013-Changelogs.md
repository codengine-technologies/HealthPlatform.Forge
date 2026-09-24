# E013 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Document frère (vue produit)** : [`E013-refonte-du-cycle-de-vie-du-token-psc.md`](./E013-refonte-du-cycle-de-vie-du-token-psc.md)
> **Dernière mise à jour** : 2026-09-24 (task-171)

Historique détaillé des changements de l'EPIC **E013 — Refonte du cycle de vie
du token PSC (backend pull via proxy)**. Une entrée par task ayant atteint
`done-*` ou `archived-*`. Append-only : une entrée existante n'est jamais réécrite.

Référence d'architecture : ADR-2026-07-25 « [PSC] Stratégie Refresh Token PSC
Backend Pull Via Proxy » (six chantiers) + addendum du 2026-09-23 (retour de
l'endpoint proxy dédié `GET /v1/internal/psc-context`, proxy task-016).

---

## Historique détaillé des changelogs

### v1.0 — task-171 : backend pull du jeton PSC, `X-PSC-Token` retiré partout (`api-mail`, `client-blazor`, `client-angular`, `client-mobile`)

> PRs : [api-mail #248](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/248),
> [client-blazor #82](https://github.com/codengine-technologies/HealthPlatform.Client/pull/82),
> [client-mobile #78](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/78) —
> label `awaiting-human-merge`. `client-angular` en code-only (branche
> `feature/nova-rewriting-mss`, non commité) — l'humain commite et ouvre la PR TFS.
> Aucun republish NuGet (`dtos-mss` intouché : `TokenInfoDto` garde ses champs `Psc*`).
> Dépendance : proxy task-016 (`done`, PR ouverte, pas encore sur `origin/next`).

Absorbe **task-172** (clients Angular + mobile, retirée, étendue à Blazor), le
**chantier 6** de l'ADR (retrait du fallback API, jamais tasqué) et **task-318**
(liaison compte ↔ professionnel, audit sécurité du registre du 2026-09-16, E016).

#### api-mail

Commits : `82940a62` (feature), `0e47900d` (passe `/simplify`), `ee4a11e3`
(`connection/status` sans boîte), `f2ed8712` (intégration), `710067ff` + `a8049fd0`
(Sonar new code), `1d5823ef` (bloquants de revue), `d74fb3f6` (clé interne dev).

- `IPscTokenProvider` / `PscTokenProvider` (`src/Application/Services/Psc/`) :
  `GET {proxy}/v1/internal/psc-context?keepAlive=` avec `Cookie: proxy_session_id`,
  `X-Internal-Api-Key`, `Authorization: Bearer`. Cache de mode (300 s ; négatifs
  60 s), cache de jeton jusqu'à `exp − 30 s` (repli 60 s sans échéance),
  single-flight `Lazy<Task>` alimentant les caches dans l'appel partagé. **Caches et
  single-flight indexés sur `(ProxySessionId, KcSub)`** (`ScopeOf`, revue).
  Mapping : 200 `hasPsc` → Online/NoPsc, 401 → SessionExpired, 403 →
  IdentityConflict, autre / exception → Unavailable (dégradé). RG-L1 défense en
  profondeur : `kcSub` de la projection vs `PscSessionKey.KcSub` (sub du bearer
  établi par le pipeline, plus de re-parse du jeton).
- Client HTTP nommé `PscProxy` (`Api/DependencyInjection.AddPscProxyClient`) :
  disjoncteur (30 s d'échantillonnage, 5 appels min., 50 %, 30 s ouvert) + timeout
  ≤ 5 s, sans retry ; base normalisée par `UriBuilder`.
- `UserContextInfo` : `PscToken` / `JwtToken` supprimés ; `ProxySessionId`,
  `KeepAliveProxySession` (jamais copié par `CopyIdentityTo` — RG-S),
  `SessionPscIdentity`, `IsOnlineMode` explicite, `OnlinePscIdentity`.
- `UserContextEnricherMiddleware` : mode = verdict du provider ; `X-PSC-Token`
  jamais lu ; IdentityConflict → 403 `problem+json` `PSC_IDENTITY_CONFLICT` +
  `TraceMailboxAttachRefused` sur l'endpoint `[MailboxAttachEndpoint]` ; bypass de
  test pose le mode depuis `mssSub` / `mssRpps` sans appel proxy (RG-5).
- Authentification IMAP / SMTP : jeton résolu à l'instant de l'authentification
  (`ImapConnectionService.AuthenticateClientAsync`, `BackgroundImapService`,
  `SmtpConnectionFactory`) ; `TokenValidationService` et la garde task-165
  supprimés. Exceptions typées `UnauthorizedException` (401),
  `PscIdentityConflictException` (403), `UnavailableException` (503) via
  `IErrorCoded` → extension `code` du `ProblemDetails` ; filtres d'exception sur
  les catch-alls IMAP et SMTP (revue).
- `AccountController` : attach avec `OnlinePscIdentity` + jeton du provider
  (RG-L2) ; sans session liée → 401 `PSC_SESSION_REQUIRED` (RG-L3) ; refus audités
  `MailboxAttached Success=false` (RG-L4, aucun nouveau `AuditActionType`).
- `ConnectionController.GetConnectionStatusAsync` `[MailboxNotRequired]` : mode de
  session sans boîte, pending / last sync à 0 / null.
- CORS `.AllowCredentials()` (origines exactes) ; `SyncController` sans
  `PscPreview` ; k6 `identity.js` / `config.js` sans `X-PSC-Token` ni `pscTokenFor`.
- Config : section `PscProxy` ; `InternalApiKey` par environnement uniquement
  (`PscProxy__InternalApiKey` ; AppHost `PSC_CONTEXT_API_KEY`, défaut dev
  `dev-psc-context-key-change-me` **aligné sur le proxy** — le premier défaut
  `local-dev-psc-context-key` faisait répondre `PROXY-API-9010` au proxy, constaté
  en test manuel Angular ; le flag `FeatureManagement__PscContextController` était
  bien `true`).
- Tests : `PscTokenProviderTests` (caches, single-flight, mapping, contrat —
  `refreshToken` / `pscRefreshToken` / `pscIdToken` jamais retenus, RG-L1
  inter-bearers ×3, branches Sonar ×10), `PscSessionContractTests`,
  `PscSessionResolutionTests` (8), `PscSessionIntegrationTests` (11, pipeline réel
  Bearer → middleware → `GlobalExceptionHandler` → `AccountController`),
  `ConnectionControllerTests`, CORS credentialed, `ImapConnectionServiceTests`
  (traversée des exceptions typées). Suites finales : domain 172, infrastructure
  492, api 840, application 2537, integration 527 (16 skippés) — 1 flaky
  pré-existant `ImapServiceIntegrationTests.GetEmailAsync_WithFullContent…`, vert
  au rejeu.

**Qualité (SonarQube 9.9.8, période new code 30 j)** — Quality Gate new code OK.

| Métrique | Baseline (2026-09-20) | Final | Δ |
|---|---|---|---|
| New coverage | 85,1 % | 86,9 % | +1,8 pt |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | = |
| Security hotspots | 3 | 3 | = |
| Code smells (projet) | 217 | 223 | +6 (0 sur les fichiers de 171) |
| Coverage (projet) | 87,9 % | 88,2 % | +0,3 pt |
| Duplication | 0,5 % | 0,5 % | = |
| Ratings R / S / M | A / A / A | A / A / A | = |

8 findings new code corrigés (S3925 ×2, S4457 ×2, S125 ×2, S1075, S1172) ; 2 S3925
résolus faux positif (constructeur de sérialisation binaire obsolète en .NET 10) ;
27 findings new code hors périmètre (E016, specs antérieures) laissés en l'état.
`conventions/csharp.md` : S125 (5e occurrence), S4457 (3e), S3925 / S1075 / S1172
créées.

#### client-blazor

Commits : `d3e1845` (feature), `5e24e7a` (passe `/simplify`).

- `X-PSC-Token` retiré (`HttpRequestService`, `MailboxAccountsService`) ;
  `SessionCookieCredentialsHandler` (`WebAssemblyFetchOptions` `credentials=include`)
  sur les clients typés `HttpRequestService`, `MailSseService`,
  `MailboxAccountsService`.
- `PscTokenRefreshService` → `SessionRefreshService` (interface unique
  `Module.Mss.Domain.Services.ISessionRefreshService`) : enveloppe single-flight sur
  `IAuthService.RefreshTokenAsync`, chemin 401 → refresh → rejeu (task-156) seul ;
  les 15 `EnsureValidPscTokenAsync` avant requête supprimés.
- `MailboxSessionService.IsOffline` = `GET connection/status` (via le registre,
  `Task.WhenAll` avec la liste, hors ligne tant qu'inconnu) ; `ConnectionStatusService`
  et `ConnectionStateService` délèguent. `OfflineStatusWidget` sans compte à rebours,
  `SyncProgressWidget` sur le statut backend, `Index` / `CallbackApi` sans refresh PSC.
- Tests : 272 verts (2 skippés) — `HttpRequestServiceCredentialsTests`, registre
  credentialed, décision d'entrée sur le statut backend, task-156 conservé.

#### client-angular (code-only)

- `mss-headers.interceptor` : plus d'en-tête PSC, `withCredentials: true` (+ spec
  neuve). Supprimés : `psc-token-guard.interceptor` (+ spec), `mss-psc-token.token`
  (`MSS_PSC_ACCESS_TOKEN`, `MSS_PSC_REFRESH_FN`), `jwt-expiration.utils` (+ spec),
  `MSS_PSC_TOKEN_PRESENT`.
- `MailboxSessionStore.offline` = `MailboxAccountsService.connectionStatus()`
  (`loadAccountsAndStatus`, `Promise.all`) ; `offline-status-widget` et
  `sync-progress-widget` sur ce signal ; `streamMessage` : `credentials: 'include'`,
  `Client-Session-Id` = `clientSessionId()` (plus `jwt.sid`, task-282) ;
  `EventSource` mail-events / notifications `withCredentials: true`.
- Validation : `nx build weda2` vert ; `nx run-many -t test` 2575 verts (14
  skippés) ; lint MSS 0 erreur (1 `prettier` auto-fixé, 56 warnings antérieurs).
- Pré-existant signalé : `mss:build:production` (démonstrateur `apps/mss`) casse —
  `environment.prod.ts` supprimé par `7de0cee3` sur `feature/nova-rewriting-mss`.

#### client-mobile

Commit : `2886781`.

- `MssHeadersInterceptor` : plus d'en-tête PSC, `withCredentials: true` sur les
  trois chemins d'envoi, préventif sur `accessTokenExpiresAt` seul
  (`earliestExpiry` et `psc-token-expiry.spec.ts` supprimés).
- `AuthSession` sans `pscAccessToken` / `pscAccessTokenExpiresAt` ;
  `AuthSessionService` purge les champs hérités (`LEGACY_PSC_SESSION_FIELDS`) à la
  relecture et au `save()` ; `hasPscToken` supprimé.
- `MailboxSessionService.offline` = `connectionStatus()` (modèle
  `ConnectionStatusDto`) ; fetch SSE IA et `EventSource` credentialed.
- 881 tests verts ; lint « All files pass » ; `/verify-visual` skippé (aucun écran).

#### Limites et suites

- Non exécuté par la forge : tir k6 court en profil loadtest ; test RG-S à horloge
  réelle (TTL 60 s) ; relevé des durées de vie du realm de production.
- Prérequis de mise en service : proxy task-016 et task-001 (garde anti-doublon
  `PROXY-KC-4012`, RG-L5) mergées et déployées ; même `PSC_CONTEXT_API_KEY` des deux
  côtés ; api-mail sous `*.weda.fr` hors dev ; audit SQL `FEDERATED_IDENTITY` à zéro
  doublon ; cookie `proxy_session_id` à valider dans la WebView Capacitor.
- Suggestions de revue non appliquées : format du cookie validé avant transmission ;
  `BelongsToBearer` fail-closed si `kcSub` vide ; bornes des TTL de cache ;
  `PscAccessTokenExpiresAtUtc` en `DateTimeOffset` ; `AuthenticationSubject` copié
  dans les scopes de fond ; code d'audit RG-L3 aligné sur `PSC_SESSION_REQUIRED` ;
  retrait de `TokenInfoDto.Psc*` côté `dtos-mss`.

### v1.0 — task-172 : clients Angular + mobile (fusionnée dans task-171, jamais démarrée)

Retirée le 2026-09-23 (décision humaine, règle 11 : une seule US complète).
Contenu repris intégralement au point 6 de task-171, étendu à Blazor. Aucun code
propre, aucune PR.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle dans E013 |
|---|---|
| `api-mail` `src/Application/Services/Psc/` | `IPscTokenProvider`, `PscTokenProvider`, `PscContextDto`, `PscProxyOptions`, `PscSessionErrorCodes`, `PscSessionKeyExtensions` |
| `api-mail` `src/Api/Middleware/UserContextEnricherMiddleware.cs` | Résolution du mode par session, refus RG-L1, bypass RG-5 |
| `api-mail` `src/Api/DependencyInjection.cs` | Client HTTP `PscProxy` (disjoncteur + timeout) |
| `api-mail` `src/Application/Exceptions/` | `UnauthorizedException`, `PscIdentityConflictException`, `IErrorCoded` |
| psc-auth-proxy `GET /v1/internal/psc-context` | Projection de session (task-016), clé `PSC_CONTEXT_API_KEY` |
| `client-blazor` `SessionCookieCredentials*`, `SessionRefreshService` | Cookie de session, refresh réactif |
| `client-angular` `mss-headers.interceptor`, `MailboxSessionStore` | Cookie de session, mode backend |
| `client-mobile` `MssHeadersInterceptor`, `AuthSessionService`, `MailboxSessionService` | Cookie de session, purge du jeton local, mode backend |

## Annexe B — Inventaire fonctionnel daté (2026-09-24)

- 4 repos touchés, 3 PRs GitHub ouvertes, 1 livraison code-only.
- 1 endpoint proxy consommé ; 1 endpoint api-mail élargi (`connection/status`).
- 0 écran modifié.

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | RGs |
|---|---|---|
| task-171 | Backend pull du jeton PSC via le proxy, liaison compte ↔ professionnel lue dans la session, retrait de `X-PSC-Token` des trois clients et de l'API, mode décidé par le backend | RG-E013-L1, L2, L3, L4, S, J |
| task-172 | Retirée — fusionnée dans task-171 | — |
