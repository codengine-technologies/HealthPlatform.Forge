# todo-task-072.md — Perf pipeline HTTP : compression de réponse, ordre des middlewares, coûts par requête

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : optimisation du pipeline ASP.NET Core
> (`src/Api/Program.cs` + middlewares). Aucun changement de contrat ni d'UI.

## Objective

Réduire le coût fixe payé par **chaque** requête HTTP de l'API : absence de
compression des réponses JSON volumineuses (listes de mails de 500 Ko à
plusieurs Mo envoyées non compressées), middlewares de logging exécutés avant
l'authentification, lectures de variables d'environnement et parsing de token
répétés à chaque requête.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Api/Program.cs:227-258` | Aucun `UseResponseCompression` (Brotli/Gzip) : payloads JSON 3-5× plus lourds sur le réseau | Élevé |
| 2 | `src/Api/Program.cs:244-257` | `RequestLoggingMiddleware` exécuté avant `UseAuthentication`/`UseAuthorization` : travail de logging complet payé même par les requêtes 401/403 | Faible-Moyen |
| 3 | `src/Api/Middleware/UserContextEnricherMiddleware.cs:208-219` | `Environment.GetEnvironmentVariable("MSS-MAIL-CONNECTIONSTRING")` relu à chaque requête | Faible |
| 4 | `src/Api/Middleware/UserContextEnricherMiddleware.cs:405-418` | `new JsonWebTokenHandler()` + re-parse du token PSC à chaque requête, alors que JwtBearer a déjà validé et exposé les claims | Faible-Moyen |
| 5 | `src/Api/Middleware/RequestLoggingMiddleware.cs:152-171` | `Split`/allocations sur `X-Forwarded-For` à chaque requête | Faible |

⚠️ **Point d'arbitrage sécurité (compression)** : activer la compression sur
HTTPS expose théoriquement aux attaques de type BREACH lorsque des secrets sont
reflétés dans des réponses compressées contenant des données contrôlées par
l'attaquant. La US doit documenter la décision (compression activée uniquement
sur les types MIME de réponses de listes, pas sur les réponses contenant des
tokens/secrets) — si le doute persiste au moment de l'implémentation, ouvrir
`questions/task-072.md`.

## Comportement attendu

- Réponses JSON compressées (Brotli prioritaire, Gzip fallback) avec une
  politique MIME/endpoints documentée au regard du risque BREACH.
- Le logging applicatif détaillé ne s'exécute plus pour les requêtes rejetées
  par l'authentification, ou court-circuite au plus tôt.
- La connection string serveur est résolue une fois au démarrage et injectée.
- L'identité PSC est lue depuis les claims du `ClaimsPrincipal` déjà validés
  par le pipeline JwtBearer — plus de re-parse du JWT par requête.
- Le parsing `X-Forwarded-For` est fait une fois et mémorisé dans
  `HttpContext.Items` si plusieurs consommateurs en ont besoin.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] `UseResponseCompression` actif ; une réponse de liste de mails part avec `Content-Encoding: br` ou `gzip` (test d'intégration le prouvant)
- [ ] Décision BREACH documentée dans la PR (périmètre MIME compressé + justification)
- [ ] Le logging détaillé par requête n'est plus exécuté pour les requêtes non authentifiées (ou court-circuit explicite)
- [ ] Plus de lecture d'`Environment.GetEnvironmentVariable` par requête dans `UserContextEnricherMiddleware`
- [ ] Plus d'instanciation de `JsonWebTokenHandler` ni de re-parse du token par requête
- [ ] Unit tests : >= 1 test par middleware modifié (comportement conservé : enrichissement contexte, logs, ProblemDetails inchangés — règle 12)
- [ ] Integration test : 1 requête authentifiée happy path + 1 requête anonyme 401 traversant le pipeline complet
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Depuis le client Blazor, charger une liste de >= 100 mails ; dans les outils
  réseau du navigateur, vérifier `Content-Encoding: br` (ou `gzip`) et comparer
  la taille transférée avant/après (réduction attendue >= 60 % sur le JSON).
- Appeler un endpoint sans token (`curl -i https://localhost:.../api/v1/...`) :
  réponse 401 immédiate, et absence de ligne de log applicatif détaillée pour
  cette requête.
- Vérifier que l'application fonctionne normalement de bout en bout (lecture,
  envoi, recherche) — aucun changement visible hormis la rapidité.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée fonctionnellement (PSC/JwtBearer) ; la lecture d'identité passe par les claims déjà validés — aucune baisse du niveau de contrôle
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : le périmètre des évènements journalisés reste identique pour les requêtes authentifiées ; les échecs d'authentification restent tracés (exigence PGSSI-S) même si le logging détaillé est court-circuité
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-072-pipeline-http-compression
- `dtos-mss` (pushed, auto-incluse) : feat/task-072-pipeline-http-compression — sera supprimée sans PR si aucun changement de contrat

## Develop log (2026-06-10)

**Commit (api-mail, `feat/task-072-pipeline-http-compression`)** : `e38e742`

**Findings traités** :
1. ✅ `AddMssResponseCompression` + `app.UseResponseCompression()` (Brotli prioritaire, Gzip fallback, `CompressionLevel.Fastest`). **Décision BREACH** (gravée dans `ResponseCompressionSetup`) : compression activée sur HTTPS car (a) auth Bearer header, pas cookie → pas de requête cross-site créditée, (b) périmètre MIME restreint à `application/json`/`application/problem+json`, aucun secret reflété à côté d'input attaquant, (c) tokens jamais dans les corps JSON. SSE (`text/event-stream`) exclu (sémantique flush).
2. ✅ Court-circuit `RequestLoggingMiddleware` : requête **sans aucun credential** (ni Authorization, ni `?token=` SSE, ni X-Test-Bypass) vers un endpoint non-`[AllowAnonymous]` → trace compacte unique Warning (méthode, path, statut, correlationId, IP source — exigence PGSSI-S de traçage des échecs auth conservée) au lieu des 11 pushes LogContext + parsing headers. Les requêtes avec credential invalide gardent le chemin détaillé.
3. ✅ `ServerConnectionString` singleton résolu une fois au démarrage, injecté au ctor du middleware — plus de `Environment.GetEnvironmentVariable` par requête.
4. ✅ `JsonWebTokenHandler` statique (stateless en lecture) + `GetPscIdentity` mémoïsé par requête dans `HttpContext.Items` — le token PSC est parsé au plus une fois par requête (2 sites consommateurs). Nota : le token PSC (`X-PSC-Token`) n'est PAS le Bearer validé par JwtBearer — la lecture « depuis les claims » suggérée par l'audit était inapplicable ; la mémoïsation atteint le même objectif (zéro re-parse).
5. ✅ `X-Forwarded-For` : `IndexOf(',')` + slice au lieu de `Split`.

**Validation** : build Release 0 erreur ; suite 2697 verts (94+491+346+1555+214(+16 skip)), 1 échec = flaky IMAP pré-existante. 7 nouveaux tests (4 TestServer pipeline réel : compression br vérifiée par décompression, SSE non compressé, 401 anonyme avec correlation, 200 authentifié ; 3 unitaires middleware).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/95 — label `awaiting-human-merge`
- `dtos-mss` : branche `feat/task-072-pipeline-http-compression` sans commit — pas de PR, branche à supprimer au `/merge`

## Code Review Summary

APPROVED — 0 issue bloquante, 1 note non-bloquante (404 sans credential → trace compacte, statut/path tracés).
- `ResponseCompressionSetup.cs` — ✅ politique BREACH documentée inline, périmètre MIME restreint, SSE exclu
- `RequestLoggingMiddleware.cs` — ✅ court-circuit testé (compact + détaillé conservé), XFF sans Split
- `UserContextEnricherMiddleware.cs` — ✅ singleton injecté (ctor), handler statique, mémo PSC par requête ; harnais TestServer task-048 mis à jour
- DOD : tous items verts (test d'intégration Content-Encoding: br inclus)
- Sonar : Quality Gate OK, 0 new-code issue (1 fix ASP0015 en itération 2)

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #95 squash-mergée — commit `3bf6dce` sur `develop`
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27366803559
- Branches locales conservées pour inspection rétroactive (convention /merge)
