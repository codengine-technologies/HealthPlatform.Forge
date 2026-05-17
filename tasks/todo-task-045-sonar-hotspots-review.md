# todo-task-045-sonar-hotspots-review.md — Review + traitement des 5 security hotspots

**Repos**: api-mail
**Dependencies**: aucune (parallélisable avec task-040 à 044)
**Epic**: E010
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Passer les **5 security hotspots** de `TO_REVIEW` à un statut résolu
(`SAFE`, `ACKNOWLEDGED` ou `FIXED`). Sonar ne les auto-fixe pas : ils
nécessitent une décision humaine (Safe vs. Fix). Cette task **combine** :

1. Une **partie review-only** : 2 hotspots marqués `SAFE` directement dans
   l'UI Sonar (sans toucher au code).
2. Une **partie code** : Dockerfile durci (USER non-root + COPY explicite),
   et arbitrage CORS sur `Program.cs`.

## Liste des 5 hotspots (Sonar snapshot 2026-05-17)

| # | Fichier | Ligne | Règle | Prob. | Sujet | Action proposée |
|---|---|---|---|---|---|---|
| 1 | `src/Api/appsettings.json` | 31 | S2068 | HIGH | "password" détecté dans la config | **Mark SAFE** (config dev, secrets prod via Key Vault / env) |
| 2 | `src/Api/appsettings.json` | 63 | S6418 | HIGH | "ApiKey" détectée dans la config | **Mark SAFE** (idem, config dev) |
| 3 | `Dockerfile` | 26 | S6470 | MED | `COPY` récursif sur build context | **FIX** — restreindre le `COPY` à des paths explicites (whitelist) ou ajouter `.dockerignore` strict |
| 4 | `Dockerfile` | 34 | S6471 | MED | Image tourne potentiellement en `root` | **FIX** — ajouter `USER app` (ou équivalent non-root) avant `ENTRYPOINT`, créer l'utilisateur si absent |
| 5 | `src/Api/Program.cs` | 83 | S5122 | LOW | Politique CORS permissive | **ARBITRAGE** — soit `SAFE` si dev-only / API publique assumée, soit `FIX` (whitelist d'origines) |

## Préalable — décision humaine pour les hotspots #1, #2 et #5

Le `/develop` qui exécute cette task doit s'assurer que ces 3 décisions
sont prises **avant** d'écrire du code. Si elles ne le sont pas, écrire
`questions/task-045.md` listant les 3 questions ouvertes.

**Hypothèses du plan** (à confirmer humainement) :

- **#1, #2** : `appsettings.json` contient des valeurs de dev (pas de
  secret production). Les vrais secrets sont injectés en prod via Key
  Vault ou variables d'environnement. → `SAFE` justifié.
- **#5** : La politique CORS actuelle (`AllowAnyOrigin()` ou équivalent)
  est-elle dev-only (entourée d'un `if (env.IsDevelopment())`) ou
  toujours active ? → Si toujours active : `FIX` avec whitelist
  `AllowedOrigins` lu depuis config. Si déjà dev-only : `SAFE`.

## Partie review-only (Sonar UI, pas de PR code)

Faite par l'humain (ou par `/develop` via l'API Sonar
`/api/hotspots/change_status`) :

```bash
# Exemple : marquer un hotspot comme SAFE avec commentaire
curl -X POST -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/hotspots/change_status" \
  -d "hotspot=dd9e0366-5c73-459b-b0e1-b7c796aef4d1" \
  -d "status=REVIEWED" \
  -d "resolution=SAFE" \
  -d "comment=Dev config; production secrets injected via Key Vault / env vars."
```

Hotspots à marquer SAFE (sous réserve de la décision préalable) :
- `dd9e0366-5c73-459b-b0e1-b7c796aef4d1` (appsettings password)
- `37572945-0e4b-4290-b587-3eca83ddd1e0` (appsettings ApiKey)

Hotspot #5 (CORS) : à marquer SAFE **uniquement si** déjà dev-only.
Sinon → FIX (partie code ci-dessous).

## Partie code — Dockerfile

### `Dockerfile` ligne 26 — COPY recursive (S6470)

Avant (probable) :
```dockerfile
COPY . /app
```

Après :
```dockerfile
# Whitelist explicite : on ne copie que ce qui est nécessaire au runtime
COPY src/Api/bin/Release/net10.0/publish/ /app/
COPY src/Api/Certs/ /app/Certs/
# ... autres paths nécessaires identifiés au build
```

ET / OU enrichir `.dockerignore` à la racine de `Api/Mail/` :

```
**/bin
**/obj
**/.vs
**/.idea
**/TestResults
**/tests/
*.md
.env*
```

### `Dockerfile` ligne 34 — USER non-root (S6471)

Avant :
```dockerfile
# (pas de USER → tourne en root par défaut)
ENTRYPOINT ["dotnet", "HealthPlatform.Api.Mail.dll"]
```

Après :
```dockerfile
# Créer un utilisateur applicatif (si pas déjà fait par l'image de base)
RUN groupadd -r app && useradd -r -g app -s /sbin/nologin app \
 && chown -R app:app /app
USER app
ENTRYPOINT ["dotnet", "HealthPlatform.Api.Mail.dll"]
```

Note : si l'image de base `mcr.microsoft.com/dotnet/aspnet:10.0` fournit
déjà un utilisateur `app` (vérifier la doc Microsoft .NET 10), `USER app`
suffit sans le `RUN groupadd`.

Compatibilité à vérifier :
- Le binding sur port < 1024 nécessite root. Si l'app écoute sur 80/443,
  configurer `ASPNETCORE_HTTP_PORTS=8080` (ou équivalent .NET 10) pour
  un port > 1024.
- Les chemins write (logs, temp files) doivent être accessibles à `app`.
- L'étape IGC-Santé de task-039 (`update-ca-certificates`) impose `USER
  root` temporairement ; replacer `USER app` **après** cette étape (déjà
  prévu dans le scope task-039).

## Partie code — CORS (conditionnelle)

Si décision arbitrée = FIX :

`src/Api/Program.cs` ligne 83, avant :
```csharp
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader()));
```

Après :
```csharp
var allowedOrigins = builder.Configuration
    .GetSection("Cors:AllowedOrigins").Get<string[]>() ?? [];
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
{
    if (builder.Environment.IsDevelopment())
        p.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader();
    else
        p.WithOrigins(allowedOrigins).AllowAnyMethod().AllowAnyHeader();
}));
```

Avec test unitaire / intégration vérifiant qu'en `Production`, une origine
non whitelistée est refusée.

## Scope OUT

- Pas de migration vers Azure Key Vault / AWS Secrets Manager (hors scope
  task — c'est une décision opérationnelle séparée)
- Pas de refacto code applicatif au-delà du CORS
- Pas de touchee aux contrôleurs ou aux migrations
- Pas de toucher à `.env` files

## Definition of Done

- [ ] **Hotspots #1 et #2** marqués `SAFE` dans Sonar UI avec commentaire
      justificatif
- [ ] **Hotspot #3** corrigé : Dockerfile COPY explicite + `.dockerignore`
      strict, et `0` occurrence S6470 post-analyse
- [ ] **Hotspot #4** corrigé : `USER app` (non-root) dans Dockerfile, et
      `0` occurrence S6471 post-analyse
- [ ] **Hotspot #5** : soit `SAFE` (justifié dans le commentaire Sonar),
      soit FIX (Whitelist CORS depuis config + test de refus origine
      non-listée)
- [ ] Build `api-mail` passes en Release
- [ ] Tests `api-mail` passent
- [ ] Image Docker buildée localement et démarrée : healthcheck OK,
      l'API répond, container ne tourne **pas** en root (`docker exec`
      → `id` retourne `uid != 0`)
- [ ] Compatibilité IGC-Santé (task-039) vérifiée : si task-039 est
      mergée, `update-ca-certificates` fonctionne toujours dans le
      nouveau Dockerfile
- [ ] **0** security hotspot `TO_REVIEW` restant sur Sonar
- [ ] PR ouverte sur `api-mail` avec label `awaiting-human-merge`

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreurs
3. `dotnet test  HealthPlatform.Api.Mail.sln --configuration Release` → 0 failures
4. **Build Docker** :
   ```bash
   docker build -t healthplatform-api-mail:test -f src/Api/Dockerfile .
   ```
5. **Vérifier l'utilisateur runtime** :
   ```bash
   docker run --rm healthplatform-api-mail:test id
   # → attendu : uid=<non-zero>(app) gid=<non-zero>(app)
   ```
6. **Démarrer et smoke-test** :
   ```bash
   docker run -d -p 8080:8080 --name api-mail-test healthplatform-api-mail:test
   curl http://localhost:8080/health   # → 200 OK
   docker stop api-mail-test && docker rm api-mail-test
   ```
7. **CORS** (si FIX appliqué) : depuis un origin non whitelisté, vérifier
   que la réponse pré-vol OPTIONS échoue (status 403 ou pas de header
   `Access-Control-Allow-Origin`).
8. Vérifier sur SonarQube :
   - **0** hotspot `TO_REVIEW` sur `healthplatform`
   - Security rating toujours A
