# questions/task-021.md — fail-fast `/develop`

**Task** : `wip-task-021.md` — Authentification JWT par middleware (secure-by-default)
**Branche** : `feat/task-021-jwt-auth-middleware` sur `api-mail` (push) + `dtos-mss` (push, vide)
**Décision forge** : 🛑 **Fail-fast** après Pass 1. Le reste de la task dépasse la zone de confort autonome — handoff au humain dans WindSurf, ou re-lance `/develop task-021` dans une session fresh.

## Pass 1 — livrée et committée (`77688a5`)

Infrastructure JWT en place mais **non-active** :

- ✅ Package `Microsoft.AspNetCore.Authentication.JwtBearer 10.0.7` ajouté
- ✅ `AddAuthentication().AddJwtBearer()` configuré avec `Keycloak:Authority` + `Keycloak:Audience` lus depuis la config (vides en dev → désactive la validation issuer/audience pour ne pas casser le démarrage)
- ✅ `OnMessageReceived` accepte `?token=...` en query string (préparation SSE)
- ✅ `UserContextEnricherMiddleware` créé : peuple `UserContextInfo` depuis les claims JWT, retombe sur `TryExtractJwtToken` pour le test bypass
- ✅ Pipeline ordre : `UseAuthentication → UseAuthorization → UserContextEnricherMiddleware`
- ✅ Build green, 1587 tests verts (aucun changement de comportement, pas encore d'enforcement)

## Pass 2-5 — **NON livrée** (à exécuter ensuite)

### Pass 2 — Test bypass converti en authentication scheme

**Pourquoi c'est bloquant** : avec `FallbackPolicy = RequireAuthenticatedUser` activée, le middleware `UseAuthorization` rejette à 401 **avant** que mon `UserContextEnricherMiddleware` puisse appliquer le fallback test-bypass. Donc `/qa` (qui utilise `X-Test-Bypass`) casserait.

**Solution canonique ASP.NET Core** : créer une `AuthenticationHandler<TestBypassOptions>` qui lit `X-Test-Bypass`, valide la clé contre `TestMode:BypassKey`, et produit un `ClaimsPrincipal` valide AVANT que `UseAuthorization` se déclenche.

```csharp
// src/Api/Authentication/TestBypassAuthenticationHandler.cs
public sealed class TestBypassAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public const string SchemeName = "TestBypass";
    private readonly IConfiguration _configuration;

    public TestBypassAuthenticationHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder,
        IConfiguration configuration)
        : base(options, logger, encoder)
    {
        _configuration = configuration;
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        // Bloqué en Production
        var env = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT");
        if (string.Equals(env, "Production", StringComparison.OrdinalIgnoreCase))
            return Task.FromResult(AuthenticateResult.NoResult());

        if (!Request.Headers.TryGetValue("X-Test-Bypass", out var bypassKey))
            return Task.FromResult(AuthenticateResult.NoResult());

        var expectedKey = _configuration["TestMode:BypassKey"];
        if (string.IsNullOrEmpty(expectedKey) || bypassKey.ToString() != expectedKey)
            return Task.FromResult(AuthenticateResult.Fail("Invalid bypass key"));

        if (!Request.Headers.TryGetValue("Client-Email", out var email) || string.IsNullOrEmpty(email))
            return Task.FromResult(AuthenticateResult.Fail("Missing Client-Email"));

        var claims = new[]
        {
            new Claim(ClaimTypes.Email, email.ToString()),
            new Claim("preferred_username", email.ToString()),
            new Claim("sid", Guid.NewGuid().ToString("N")[..16])
        };
        var identity = new ClaimsIdentity(claims, SchemeName);
        var ticket = new AuthenticationTicket(new ClaimsPrincipal(identity), SchemeName);
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}
```

Câblage dans `Program.cs` :

```csharp
builder.Services.AddAuthentication(options =>
{
    options.DefaultScheme = "JwtOrTestBypass";
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(/* déjà fait */)
.AddScheme<AuthenticationSchemeOptions, TestBypassAuthenticationHandler>(
    TestBypassAuthenticationHandler.SchemeName, _ => { })
.AddPolicyScheme("JwtOrTestBypass", "JwtOrTestBypass", options =>
{
    options.ForwardDefaultSelector = ctx =>
        ctx.Request.Headers.ContainsKey("X-Test-Bypass")
            ? TestBypassAuthenticationHandler.SchemeName
            : JwtBearerDefaults.AuthenticationScheme;
});
```

Le `UserContextEnricherMiddleware` actuel n'a alors plus besoin du fallback `TryExtractJwtToken` — tout passe par les claims.

### Pass 3 — Activer FallbackPolicy + marquer infra `[AllowAnonymous]`

```csharp
builder.Services.AddAuthorization(options =>
{
    options.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();
});
```

Et marquer `[AllowAnonymous]` sur :
- Aspire `MapDefaultEndpoints` exposant `/health`, `/alive` — ils peuvent passer par `app.MapGroup(...).AllowAnonymous()` ou via `[AllowAnonymous]` si Health est un controller
- `app.UseSwagger() / UseSwaggerUI()` — dev seulement, ou `app.MapSwagger().AllowAnonymous()`
- `app.MapPrometheusScrapingEndpoint().AllowAnonymous()`
- Les **5 controllers métier actuellement anonymes** (cf. audit IDOR) :
  - `AiController` 4 endpoints
  - `DirectoryController` 3 endpoints
  - `FeatureFlagController` 2 endpoints
  - `MailEventsController` 1 endpoint SSE
  - `NotificationsController` 1 endpoint SSE
  → Tous taggés `[AllowAnonymous]` **temporairement**, task-022 décidera lesquels rester ouverts.

### Pass 4 — Bulk-remove `TryExtractJwtToken` des controllers

Pattern à supprimer (apparaît ~115 fois sur 23 controllers) :

```csharp
if (!RequestHelper.TryExtractJwtToken(Request, userContextInfo, out var errorMessage))
{
    return Unauthorized(errorMessage);
}
```

Approche pragmatique : sed Python qui supprime le bloc complet (4 lignes pattern-matched) puis re-build pour corriger les `var errorMessage` orphelins. Estimation : 30 min.

```python
import re
for f in glob.glob("src/Api/Controllers/V1/*.cs"):
    with open(f, 'r', encoding='utf-8') as fp: s = fp.read()
    s = re.sub(
        r'\s*if \(!RequestHelper\.TryExtractJwtToken\(Request, userContextInfo, out var errorMessage\)\)\s*\{\s*return Unauthorized\(errorMessage\);\s*\}',
        '',
        s, flags=re.MULTILINE
    )
    with open(f, 'w', encoding='utf-8') as fp: fp.write(s)
```

Marquer `RequestHelper.TryExtractJwtToken` `internal` ensuite (le middleware reste son seul caller).

### Pass 5 — Adapter `HttpContextFactory` des tests

`tests/mss.mail.application.tests/Fixtures/HttpContextFactory.cs` retourne aujourd'hui un `DefaultHttpContext` avec un header `Bearer valid-token`. Après le refactor, les controllers ne lisent plus de header — ils lisent `UserContextInfo` (déjà mocké via DI dans les tests) et/ou `context.User` (claim principal).

Si des tests vérifient `Unauthorized` quand l'auth manque, ils doivent désormais :
- Soit mocker `User.Identity.IsAuthenticated = false` (mais comme les tests appellent les méthodes du controller en direct, l'attribut `[Authorize]` n'est pas évalué — ces tests deviennent inutiles)
- Soit transformés en tests d'intégration (`WebApplicationFactory<>`) — plus coûteux

Recommandation : grep des tests qui font `Assert<UnauthorizedResult>` et les supprimer / re-écrire 1 par 1. Estimation : 1h.

### Pass 6 — Tests dédiés sécurité

Le DOD demande des tests de spoofing (`Client-Email` ignoré quand JWT valide), de token expiré (401), de token forgé (401), de SSE query string accepté. Nouvelle classe `JwtAuthenticationTests` utilisant `WebApplicationFactory<Program>` pour tester le pipeline HTTP complet. Estimation : 1h.

## Recommandation

**Option A — Continuer en autonomous** (`/develop task-021` dans une session fresh)

Le travail restant est mécanique et bien défini. Une session fresh sans le poids du contexte cumulé pourrait l'enchaîner. Pré-requis :
- Pass 1 déjà committée et poussée → la session fresh repart de `feat/task-021-jwt-auth-middleware` avec tout le scaffolding en place
- Le fichier wip-task-021.md reste tel quel, pas besoin de le modifier
- La task ressemble à une "phase 2" : il suffira de relancer `/develop task-021` qui détectera l'état wip-* et continuera

**Option B — Continuer en humain via WindSurf** (recommandée)

Le travail est tactique mais sensible (auth scheme custom, integration test des paths edge), c'est typiquement bien fait à la main avec WindSurf. Pré-requis :
- Renommer (manuellement) `tasks/wip-task-021.md` → tel quel, le humain bosse dessus
- Quand fini, lancer `/review task-021` qui validera et ouvrira la PR

**Option C — Désactiver Pass 1 et reporter complètement la task**

Revenir sur la branche, supprimer le commit `77688a5`, garder l'état actuel. Pas recommandé : Pass 1 est de l'infra propre qui ne casse rien et facilite la reprise.

## État courant — pour reprise sereine

- Branche `feat/task-021-jwt-auth-middleware` poussée sur api-mail + dtos-mss
- 1 commit Pass 1 sur api-mail (`77688a5`), 0 commits sur dtos-mss (DTOs non touchés, branche vide attendue)
- `tasks/wip-task-021.md` inchangé depuis `/start`
- Build vert, 1587 tests verts
- Aucun controller modifié, aucune fonction de RequestHelper modifiée

## Prochaine action

Choisir Option A / B / C et exécuter. Sans nouvelle action, la task reste en `wip-*` indéfiniment.
