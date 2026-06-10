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
