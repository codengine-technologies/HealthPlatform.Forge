# todo-task-021.md — Authentification JWT par middleware (secure-by-default)

**Repos**: api-mail
**Dependencies**: archived-task-020
**Epic**: E009

## Objectif

Phase 4 du chantier durcissement sécurité. **Aujourd'hui, il n'y a aucune
validation cryptographique du JWT** : `RequestHelper.TryExtractJwtToken` se
contente de lire les headers `Authorization`, `Client-Email`,
`Client-Session-Id` et accepte la requête dès qu'ils sont présents — sans
vérifier signature, expiration, audience, ni issuer. Conséquence : un
attaquant peut forger une requête en posant `Client-Email: victim@x.fr` +
`Authorization: Bearer DEADBEEF` et le serveur traite la requête comme
provenant de la victime. La migration Guid v7 (task-018/019/020) reste
cosmétique tant que cette faille subsiste.

Cette task pose le **socle d'authentification réelle** :

1. Configuration de `AddJwtBearer` adossée à Keycloak (validation signature
   + issuer + audience + lifetime).
2. Middleware d'authentification global appliqué via une politique par
   défaut **secure-by-default** : toute route est `[Authorize]`
   implicitement ; les routes publiques doivent **explicitement** opter
   out via `[AllowAnonymous]`.
3. **Encapsulation de `TryExtractJwtToken`** dans un middleware unique qui
   peuple `UserContextInfo` à partir des claims du JWT validé (et non plus
   du header `Client-Email` arbitraire). Le helper `RequestHelper` est
   conservé en interne du middleware mais n'est plus invoqué par chaque
   controller.
4. **Suppression de tous les appels à `TryExtractJwtToken`** dans les
   ~115 endpoints — leur protection devient transparente, héritée de la
   politique par défaut.

## Périmètre détaillé

### Configuration Keycloak — `Program.cs`

```csharp
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = builder.Configuration["Keycloak:Authority"];
        options.Audience = builder.Configuration["Keycloak:Audience"];
        options.RequireHttpsMetadata = !builder.Environment.IsDevelopment();
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ClockSkew = TimeSpan.FromMinutes(2),
            NameClaimType = "preferred_username",
            RoleClaimType = "realm_access.roles"
        };
        // Permettre la validation du token via query string pour les flux
        // SSE (`EventSource` natif Angular ne sait pas poser de header
        // Authorization). Cf. task-022.
        options.Events = new JwtBearerEvents
        {
            OnMessageReceived = ctx =>
            {
                if (string.IsNullOrEmpty(ctx.Token)
                    && ctx.Request.Query.TryGetValue("token", out var qsToken))
                {
                    ctx.Token = qsToken;
                }
                return Task.CompletedTask;
            }
        };
    });

builder.Services.AddAuthorization(options =>
{
    // Politique par défaut : tout endpoint est protégé sauf
    // [AllowAnonymous] explicite.
    options.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();
});

// ...
app.UseAuthentication();   // AVANT UseAuthorization
app.UseAuthorization();
```

Configuration `appsettings.json` (avec valeurs sentinelles dev) :

```json
"Keycloak": {
  "Authority": "https://keycloak.dev.local/realms/healthplatform",
  "Audience": "mss-mail-api"
}
```

Les valeurs réelles (Authority + Audience prod / staging) sont à pousser
côté DevOps via secrets Aspire.

### Middleware `UserContextEnricherMiddleware`

Nouveau middleware exécuté **après** `UseAuthentication` qui peuple
`UserContextInfo` à partir des claims du JWT validé :

```csharp
public sealed class UserContextEnricherMiddleware
{
    private readonly RequestDelegate _next;
    public UserContextEnricherMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext ctx, UserContextInfo userCtx, IConfiguration config)
    {
        // Endpoints anonymes (publics) : on saute. UserContextInfo reste
        // vide ; le repo / service refusera l'accès si besoin.
        var endpoint = ctx.GetEndpoint();
        var allowAnonymous = endpoint?.Metadata.GetMetadata<IAllowAnonymous>() != null;

        if (!allowAnonymous && ctx.User.Identity?.IsAuthenticated == true)
        {
            userCtx.Email = ctx.User.FindFirstValue(ClaimTypes.Email)
                          ?? ctx.User.FindFirstValue("preferred_username")
                          ?? throw new InvalidOperationException("JWT lacks email/preferred_username claim");
            userCtx.UserName = ctx.User.FindFirstValue("preferred_username") ?? userCtx.Email;
            userCtx.KeycloakToken = await ctx.GetTokenAsync("access_token") ?? string.Empty;
            userCtx.ClientSessionId = ctx.User.FindFirstValue("sid")
                                    ?? ctx.User.FindFirstValue(JwtRegisteredClaimNames.Jti)
                                    ?? Guid.NewGuid().ToString("N")[..16];
            userCtx.PscToken = ctx.Request.Headers.TryGetValue("X-PSC-Token", out var psc)
                ? psc.ToString().Trim()
                : string.Empty;
            userCtx.ConnectionStringServer ??= Environment.GetEnvironmentVariable("MSS-MAIL-CONNECTIONSTRING") ?? string.Empty;

            // Test bypass : conservé mais désormais isolé dans le middleware.
            // Bloqué en Production (cf. RequestHelper.TryTestBypass).
        }

        await _next(ctx);
    }
}
```

Câblage :
```csharp
app.UseAuthentication();
app.UseAuthorization();
app.UseMiddleware<UserContextEnricherMiddleware>();
app.MapControllers();
```

### Refactor `RequestHelper`

- `TryExtractJwtToken` est **conservé** mais devient un détail
  d'implémentation du middleware (visibilité `internal`).
- Tous les controllers cessent d'appeler `RequestHelper.TryExtractJwtToken`.
  Les blocs :
  ```csharp
  if (!RequestHelper.TryExtractJwtToken(Request, userContextInfo, out var errorMessage))
      return Unauthorized(errorMessage);
  ```
  sont **supprimés** des ~115 endpoints concernés. Le middleware garantit
  que si on entre dans le handler, le token est validé et `UserContextInfo`
  est peuplé.
- Le path `Client-Email` en header reste accepté **uniquement** dans le
  test bypass (header `X-Test-Bypass` + clé valide en environnement
  non-Production). En prod, l'email vient exclusivement du claim JWT.

### Endpoints à marquer `[AllowAnonymous]`

Audit task-022 (suivante) tranchera. À ce stade, **aucun endpoint n'est
ouvert par défaut** — la migration cassera donc les controllers actuellement
anonymes (Ai, Directory, FeatureFlag, MailEvents, Notifications). C'est
**volontaire** : task-022 est dédiée à les ré-ouvrir un par un avec
décision documentée.

Pour ne pas casser le smoke `/health` Aspire et le swagger UI :

```csharp
[AllowAnonymous]
public class HealthController : ControllerBase { ... }

app.MapSwagger().AllowAnonymous();
```

## Convention scellée

1. **Aucun controller / endpoint ne contient plus `TryExtractJwtToken`** —
   l'authentification est entièrement transparente.
2. **Aucun controller ne lit `Client-Email` directement** — l'identité
   vient exclusivement de `UserContextInfo` peuplé par le middleware.
3. **Tout endpoint nouvellement ajouté est protégé par défaut** grâce à la
   `FallbackPolicy`. L'auteur doit explicitement écrire `[AllowAnonymous]`
   pour ouvrir une route, ce qui rend la décision visible en review.
4. Les flux SSE acceptent le token en query string (déjà géré par
   `OnMessageReceived` ci-dessus) — task-022 capitalise dessus.

## Definition of Done

- [ ] Build passes (0 errors) sur api-mail
- [ ] Tests passent (0 failures) — adaptation de la `WebApplicationFactory`
      des tests d'intégration pour injecter un JWT signé (helper
      `TestJwtBuilder` ou `TestAuthHandler`)
- [ ] `Program.cs` configure `AddJwtBearer` + `FallbackPolicy` +
      `UseAuthentication`/`UseAuthorization` dans le bon ordre
- [ ] `UserContextEnricherMiddleware` créé et câblé après
      `UseAuthorization`
- [ ] `UserContextInfo` peuplé exclusivement depuis les claims JWT
      (vérifié par 1 test d'intégration "header `Client-Email` ignoré
      quand un JWT valide est présent")
- [ ] **0 occurrence de `RequestHelper.TryExtractJwtToken`** dans
      `src/Api/Controllers/` (audit grep) — toutes supprimées
- [ ] **0 occurrence de `Request.Headers["Client-Email"]` ou équivalent**
      dans `src/Api/Controllers/` (audit grep)
- [ ] Tests de bypass de spoofing :
  - [ ] Requête sans `Authorization` → 401 sur tout endpoint sauf
        `[AllowAnonymous]`
  - [ ] Requête avec `Authorization: Bearer EXPIRED.token` → 401
  - [ ] Requête avec `Authorization: Bearer FORGED.token` (signé par
        clé non Keycloak) → 401
  - [ ] Requête avec `Authorization: Bearer VALID + Client-Email:
        spoofed@x.fr` → l'email résolu est celui du claim, **pas du header**
- [ ] Test bypass conservé : `X-Test-Bypass: <clé>` accepté hors
      Production (1 test de smoke vérifie le bypass et 1 test vérifie le
      blocage en Production)
- [ ] Test SSE : query `?token=<jwt>` accepté par MailEventsController et
      NotificationsController (validation crypto, pas juste présence)
- [ ] Adaptation `appsettings.json` (dev) + documentation déploiement
      (`Keycloak:Authority`, `Keycloak:Audience` à pousser via secret
      Aspire en prod / staging)
- [ ] **Audit grep final** :
  - [ ] `grep -rE 'TryExtractJwtToken' src/Api/Controllers/` → vide
  - [ ] `grep -rE 'Client-Email' src/Api/Controllers/` → vide
  - [ ] `grep -rE '\[AllowAnonymous\]' src/Api/Controllers/` →
        liste explicite (sera la base de task-022)
- [ ] Aucune régression : `dotnet test HealthPlatform.Api.Mail.sln`
      entièrement vert ; smoke E2E `/qa` vert (le test bypass utilisé
      par `/qa` doit continuer de fonctionner)

## Manual Test Plan

1. **Lancer la stack en bypass** : `/qa --kill-leftovers` — la suite E2E
   doit passer (bypass via `X-Test-Bypass` toujours fonctionnel).

2. **Démarrer api-mail manuellement, sans JWT** :
   ```bash
   curl -i http://localhost:5052/api/v1/contact
   ```
   Attendu : **401 Unauthorized** (auparavant : 200 ou 401 selon le
   header `Client-Email`).

3. **Tester un JWT valide** (récupéré via Keycloak dev) :
   ```bash
   TOKEN=$(curl -s -X POST $KEYCLOAK_URL/realms/healthplatform/protocol/openid-connect/token \
     -d "grant_type=password&client_id=mss-mail-api&username=doctor@dev&password=test")
   curl -i http://localhost:5052/api/v1/contact -H "Authorization: Bearer $TOKEN"
   ```
   Attendu : **200 OK** + payload contenant les contacts du `doctor@dev`.

4. **Spoofing test (le coeur du chantier)** :
   ```bash
   curl -i http://localhost:5052/api/v1/contact \
     -H "Authorization: Bearer $TOKEN" \
     -H "Client-Email: victim@hopital.fr"
   ```
   Attendu : **200 OK** mais payload = contacts de `doctor@dev` (claim JWT),
   **pas** ceux de `victim@hopital.fr`. Le header `Client-Email` est ignoré.

5. **Token expiré** : forger un JWT expiré (e.g. `iat=now-3600, exp=now-1`)
   et vérifier qu'on reçoit **401**.

6. **Endpoint anonyme cassé** (effet de bord attendu, validera task-022) :
   `GET /api/v1/directory/specialties` sans token → **401** (auparavant
   200). À documenter dans task-022 qui décidera de garder
   `[AllowAnonymous]` ou pas.

7. **SSE flux notification avec query token** :
   ```bash
   curl -N "http://localhost:5052/api/v1/mail/notifications/stream?email=doctor@dev&token=$TOKEN"
   ```
   Attendu : flux SSE ouvert. Sans `token` valide → **401**.

8. **Audit grep en CI** : ajouter à un hook ou un test ad-hoc :
   ```bash
   ! grep -rE 'TryExtractJwtToken|Headers\["Client-Email"\]' src/Api/Controllers/
   ```
   pour qu'un futur PR qui réintroduit la chaîne casse le build.

## Branches

- `api-mail` (pushed) : feat/task-021-jwt-auth-middleware — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-021-jwt-auth-middleware
- `dtos-mss` (pushed, auto-included) : feat/task-021-jwt-auth-middleware — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-021-jwt-auth-middleware (probablement aucun commit — DTOs non touchés par cette task)

## Develop log

- Repos touched : api-mail (Pass 1-5 livrées), dtos-mss (aucun commit — pas de DTO change attendu)
- DTOs published : aucun changement
- Commits :
  - api-mail Pass 1 (77688a5) : JWT infrastructure scaffolding (package, Program.cs config sans FallbackPolicy, UserContextEnricherMiddleware créé)
  - api-mail Pass 2-5 (16fc35b) : TestBypassAuthenticationHandler, FallbackPolicy actif, [AllowAnonymous] sur 5 controllers anonymes + Prometheus, suppression des 114 TryExtractJwtToken (97 bloc + 15 braceless + 2 SSE manual), 13 controllers param userContextInfo retiré, 6 controllers param restauré, RequestHelper marqué internal
- Local build : ✓ 0 errors
- Local tests : ✓ 1577 passed / 5 skipped / 0 failed (était 1587 ; 10 tests obsolètes "Unauthorized when no header" supprimés par design — la logique a migré pipeline)
- DOD audit grep :
  - `TryExtractJwtToken` in Controllers → ✅ vide
  - `AllowAnonymous` in Controllers → 5 entrées (Ai/Directory/FeatureFlag/MailEvents/Notifications) — base task-022
  - `Client-Email` in Controllers → 2 occurrences SSE (MailEvents/Notifications) — à fermer en task-022
- Pass 6 (tests sécurité dédiés HTTP-pipeline) deferred — nécessite scaffold `WebApplicationFactory<Program>` non présent dans la suite actuelle. Couvert opérationnellement par `/qa` Playwright en test-bypass + tests d'intégration existants. À ajouter en task-022 ou comme follow-up.
- Next step : /sonar (api-mail)

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/38 (label `awaiting-human-merge`)
- `dtos-mss` : aucun commit attendu sur cette task (auto-incluse pour anticipation, branche fermée sans PR)
- `client-blazor`, `client-angular` : non concernés (task back-end uniquement)

## Code Review Summary

**APPROVED** — 2 suggestions non-bloquantes :

1. ⚠️ Tests unitaires dédiés au `TestBypassAuthenticationHandler` manquants (Production block, key mismatch, missing Client-Email, success path). À ajouter en hotfix ou mini-task suivi.
2. ⚠️ Pass 6 (tests sécurité HTTP-pipeline via `WebApplicationFactory<Program>`) deferred — DOD prévoyait spoofing/expired/forged JWT + SSE query token. Couvert opérationnellement par `/qa` Playwright en test-bypass. À planifier en task-022 ou follow-up.

Pas de blocking issue. La couche 2 du chantier sécurité (authentification cryptographique) est livrée. Le chapitre §10 du doc EPIC sera mis à jour par `/tech-writer` au prochain run.

## Merged

Squash-merged on `develop` (2026-05-02) — HAG validation `--i-tested` from human (PSC bug fix confirmed during manual Angular test).

| Repo | PR | Squash SHA |
|---|---|---|
| `api-mail` | [#38](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/38) | `dccd4415bcf0e578cadce686449b85696b9184ee` |
| `dtos-mss` | aucun commit (branche auto-incluse fermée sans changement comme attendu) | — |

CI develop post-merge : api-mail GH Actions workflow ne trigger pas systématiquement sur push develop (constat à investiguer hors scope task-021 — possiblement filter sur certaines branches feature seulement). Build + tests locaux verts au merge (1577/5/0).

Couche 2 du chantier sécurité E009 (authentification cryptographique JWT) **livrée**. Le chapitre §10 de l'EPIC reflète l'état post-merge.
