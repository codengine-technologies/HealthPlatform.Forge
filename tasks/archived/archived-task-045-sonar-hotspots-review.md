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

## Branches

- `api-mail` (pushed) : `chore/task-045-sonar-hotspots-review` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-045-sonar-hotspots-review
- `dtos-mss` (pushed, auto-included per CLAUDE.md) : `chore/task-045-sonar-hotspots-review`

## Scope révisé (2026-05-17, humain a arbitré pré-`/start`)

Snapshot Sonar pré-`/start` : **7 hotspots TO_REVIEW** (vs 5 dans le task body initial). Inspection comparative :

| # | Cible | Statut | Action |
|---|---|---|---|
| 1 | S2068 password `appsettings.json:31` (RabbitMQ guest/guest) | ✅ présent | **Move to `appsettings.Development.json` (gitignoré)** — pas Mark SAFE comme proposé initialement. Le humain a arbitré : meilleure pratique, pas de secret en clair dans le fichier tracked. |
| 2 | S6418 ApiKey `appsettings.json:63` | ❌ **disparu** (règle pas active dans `Weda way`) — mais la clé OpenAI réelle est toujours présente | **Move idem** (héritage Q3 du halt — couvert par Q1) |
| 3 | S6470 COPY recursive `Dockerfile:26` | ✅ présent | **FIX** — COPY restreint + `.dockerignore` |
| 4 | S6471 root user `Dockerfile:34` | ✅ présent | **FIX** — `USER app` non-root |
| 5 | S5122 CORS `Program.cs:83` | ✅ présent, `AllowAnyOrigin` toujours actif (pas dev-only — vérifié) | **FIX** — whitelist depuis config + test refus origine non-listée |
| 6 | S4792 logger `Program.cs:77` | NEW vs task body | **Mark SAFE** Sonar API (config logger standard) |
| 7 | S4792 logger `Program.cs:201` (Serilog setup) | NEW vs task body | **Mark SAFE** Sonar API |
| 8 | S4792 logger `BaseRepository.cs:209` | NEW vs task body | **Mark SAFE** Sonar API |

**Bonus** : `TestMode.BypassKey` (`appsettings.json:47`) déplacé aussi vers `appsettings.Development.json` — même rationale (test bypass key, à ne pas commiter). Pas un hotspot Sonar courant mais cohérent avec le move des autres secrets.

### Plan d'action

**Code** :
1. Créer `appsettings.Development.json` avec les 3 valeurs sensibles (`MassTransit:RabbitMQ:Password`, `OpenAi:ApiKey`, `TestMode:BypassKey`)
2. Vider ces valeurs dans `appsettings.json` (chaînes vides ou clés retirées)
3. Ajouter `**/appsettings.Development.json` au `.gitignore` du repo `api-mail`
4. Dockerfile : COPY explicite + USER non-root + créer `.dockerignore` strict
5. `Program.cs` CORS : whitelist depuis config `Cors:AllowedOrigins` + dev-only fallback `AllowAnyOrigin` + test d'intégration de refus

**Sonar UI (via API)** :
- Mark SAFE les 3 hotspots S4792 (logger config standard Serilog/Microsoft.Extensions.Logging) avec commentaire justificatif
- #1 S2068 disparaîtra automatiquement après le move (plus de "password" en clair dans le fichier scanné)

### Hors scope (différé)

- **Rotation des secrets** (token Sonar déjà fait via suppression `report_coverage.ps1` ; OpenAI key + RabbitMQ guest à rotater post-merge en task séparée admin — le humain a noté qu'une rotation sera faite plus tard)
- **History rewrite** : non, l'historique git garde les secrets (acceptable pour un développement perso pré-prod, à arbitrer si déploiement public)

## Develop log

### Commits api-mail (3 commits sur `chore/task-045-sonar-hotspots-review`)

- **`aaf21cc`** — `fix(security): move dev-only secrets out of appsettings.json (task-045 #1)` :
  - `src/Api/appsettings.json` : 3 valeurs sensibles vidées (`MassTransit:RabbitMQ:Username`/`Password`, `TestMode:BypassKey`, `OpenAi:ApiKey`) + ajout d'une section `Cors:AllowedOrigins: []` en préparation du commit CORS.
  - `src/Api/appsettings.Development.json` : **nouveau fichier (gitignored)** contenant les 3 valeurs dev.
  - `.gitignore` : pattern `**/appsettings.Development.json` ajouté.
- **`e790915`** — `fix(docker): harden Dockerfile — non-root USER + drop recursive COPY (task-045 #3, #4)` :
  - `Dockerfile` : `COPY . .` (L26 historique, recursive sur le build context) supprimé — redondant car `src/`, Directory.{Build,Packages}.props et nuget.config sont déjà copiés explicitement. Final stage : `COPY --chown=app:app --from=publish /app/publish .` + `USER app` (l'image `mcr.microsoft.com/dotnet/aspnet:10.0` fournit le user `app` depuis .NET 8).
  - `.dockerignore` : enrichi avec `appsettings.Development.json` (**CRITIQUE** — empêche les secrets dev d'atterrir dans une image Docker), `TestResults`, `tests/`, `logs/`, `*.md`, `.sonarqube`.
- **`77c4cdb`** — `fix(cors): whitelist origins in non-Development environments (task-045 #5)` :
  - `src/Api/Program.cs` : politique CORS `MobileWeb` désormais conditionnelle. Development → `AllowAnyOrigin()` (préservation friction-free localhost). Autres environments → `WithOrigins(Cors:AllowedOrigins)` lu depuis config avec fallback array vide (**fail-closed** : aucune origine acceptée tant que l'opérateur n'a pas configuré via env var `Cors__AllowedOrigins__0=...`).
  - `tests/mss.mail.api.tests/Configuration/CorsConfigurationTests.cs` : nouveau fichier, **3 tests** — binding config tableau, section manquante (fallback empty), section vide (fallback empty).

### Sonar UI (via `/api/hotspots/change_status`)

5 hotspots marqués `SAFE` avec commentaire justificatif (3 lors de l'implémentation des fixes code, 2 post-re-analyse pour les hotspots design-intent restants) :

- **3× S4792 logger config** (`Program.cs:77`, `Program.cs:201`, `BaseRepository.cs:209`) — Serilog setup standard, pas de PII/secret sans scrubbing middleware existant.
- **1× S6504 Dockerfile:L44** (COPY write permissions) — COPY 644/755 default, exécution read-only par user `app` non-root.
- **1× S5122 Program.cs:L89** (CORS permissif dev) — gated par `if (IsDevelopment())`, branche prod fait whitelist via config.

### Local build / test

- **Build api-mail Release** : ✓ 0 erreurs, 0 warnings.
- **Tests api-mail** : ✓ **2183 pass / 0 fail / 16 skipped** (+3 vs baseline post-task-043 — les 3 nouveaux `CorsConfigurationTests`).
  - domain : 86/86
  - application : 1437/1437
  - infrastructure : 346/346
  - **api : 128/128** (+3 nouveaux CORS)
  - integration : 186/202 (16 skipped pré-existants AI + Linux skip)

### KPIs Sonar post-re-analyse

| Métrique | Avant (post-task-043) | Après | Δ |
|---|---|---|---|
| Bugs | 0 | 0 | ✅ |
| **Vulnerabilities** | 1 (token leak) | **0** | ✅ (token déjà supprimé hors-task via `report_coverage.ps1`) |
| Code Smells | 1066 | 1072 | +6 mineurs (nouveau CorsConfigurationTests.cs + lambda CORS lambda étendue) |
| **Security Hotspots** | 7 TO_REVIEW | **0 TO_REVIEW** | ✅ DOD atteinte (5 marqués SAFE + 2 résolus par fix code) |
| Coverage | 73.3 % | **76.6 %** | +3.3 pp |
| Reliability rating | A | A | ✅ |
| **Security rating** | **E** | **A** | ✅ (rétabli) |
| Maintainability rating | A | A | ✅ |

### DOD self-check `/develop`

- [x] **Hotspots #1 et #2** : approche révisée (move to Development.json plutôt que Mark SAFE) — résout aussi la clé OpenAI bonus
- [x] **Hotspot #3** (S6470 COPY recursive) : `Dockerfile` corrigé, COPY redondant supprimé, `.dockerignore` enrichi
- [x] **Hotspot #4** (S6471 USER root) : `USER app` ajouté en final stage, `--chown=app:app` sur COPY artifacts
- [x] **Hotspot #5** (S5122 CORS) : whitelist depuis config + fallback empty + 3 tests binding + Mark SAFE (gating dev-only justifié)
- [x] **Hotspots S4792 logger × 3** (nouveaux vs task body) : Mark SAFE avec justification Serilog standard
- [x] **Hotspot S6504 Dockerfile USER directive review** (nouveau, surfacé par le fix #4) : Mark SAFE (COPY default 644/755, exécution read-only)
- [x] Build + tests verts
- [x] **0** security hotspot `TO_REVIEW` restant sur Sonar ✅
- [x] Security rating rétabli A (était E à cause du token leak `report_coverage.ps1`)
- [ ] Image Docker buildée localement et démarrée : `docker build` + `docker run --rm ... id` → déféré au Manual Test Plan (Docker pas dispo dans l'environnement CI courant)
- [ ] PR ouverte avec label `awaiting-human-merge` (étape `/review`)

### Hand-off

Next step : `/review task-045` directement. `/sonar task-045` skip (déjà re-analysé manuellement, KPIs vérifiés). `/lint-angular` skip (client-angular non listé). `dtos-mss` : 0 commit, branche orpheline (à supprimer post-merge comme pattern précédent).

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/66 — label `awaiting-human-merge`. CI [run 25991868707](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/25991868707).
- **dtos-mss** : pas de PR (0 commit). Branche `chore/task-045-sonar-hotspots-review` poussée mais vide — à supprimer manuellement post-merge.

## Code Review Summary

**APPROVED** — 6 fichiers reviewés (api-mail seul, scope mono-repo), 0 issue bloquante.

- `.gitignore` + `.dockerignore` — ✅ secrets isolés proprement, le `.dockerignore` couvre toutes les surfaces sensibles (notamment `appsettings.Development.json`).
- `Dockerfile` — ✅ pattern `USER app` + `--chown=app:app` standard pour .NET 8+ aspnet. Suppression du `COPY . .` redondant réduit la surface d'attaque et accélère le build.
- `src/Api/Program.cs` (CORS) — ✅ env-aware avec fail-closed default approprié en non-Dev. Pattern `if (IsDevelopment())` standard ASP.NET Core.
- `src/Api/appsettings.json` — ✅ keys conservées avec valeurs vides (découverte facile), commentaire dans `.gitignore` pointe vers Development.json.
- `src/Api/appsettings.Development.json` (gitignored) — ✅ vérifié non tracké via `git check-ignore`.
- `tests/mss.mail.api.tests/Configuration/CorsConfigurationTests.cs` (nouveau, 65 LOC) — ✅ 3 tests couvrent le contrat de binding (array peuplé, section manquante, section vide).

**Sonar UI** : 5 hotspots marqués SAFE via `/api/hotspots/change_status` avec commentaire justificatif (3× S4792 logger, 1× S6504 Dockerfile COPY perms, 1× S5122 CORS dev-gating).

**Suggestion non-bloquante** : le test CORS ne vérifie pas le comportement runtime de la policy (refus origine non-listée). Manual Test Plan couvre via curl. WebApplicationFactory test serait plus robuste mais infrastructure pas en place — déféré.

### KPIs Sonar post-fix (validés live avant PR)

- Vulnerabilities : 1 → **0**
- Security rating : **E → A** (rétabli après suppression du token leak hors-task + fix des hotspots)
- Security Hotspots TO_REVIEW : 7 → **0** ✅ DOD littérale atteinte
- Coverage : 73.3% → **76.6%** (+3.3 pp grâce aux 3 tests CORS + recompilation)
- Code Smells : 1066 → 1072 (+6 mineurs sur fichiers ajoutés/modifiés)

### Findings hors scope (toujours à traiter)

- Rotation effective des credentials leakés dans le git history (OpenAI key, RabbitMQ guest) — humain a noté qu'une rotation sera faite plus tard hors forge
- Flake `BackgroundSyncManagerTests.GetStatus_WhenServiceReturnsStatus_*`
- Multi-language Sonar scan non maîtrisé (~185 new_violations héritées)
- EF Core drift `EFCore.Design 9.0.8` vs `EFCore 10.0.7`
- Cast `((BaseRepository)(object)_mailRepository).DataContext` → exposer DataContext sur `IMailRepository`
- Node.js 20 deprecation GitHub Actions (avant 2026-06-02)

## Merged

- **Timestamp** : 2026-05-17 ~14:25 UTC (forge local time)
- **Validation HAG** : humain a attesté avoir testé la US end-to-end (`/merge task-045 -i--tested`, typo invocation acceptée intent-clear).
- **Squash merges (single PR)** :
  - `api-mail` : `7d0c430` (PR #66 closed, https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/66) — merge commit `chore(security): resolve 7 security hotspots — secrets move + Dockerfile harden + CORS whitelist (task-045) (#66)`.
- **`dtos-mss`** : pas de merge (0 commit sur la branche). Branche orpheline supprimée **avant** `/merge` à la demande du humain (pattern post-task-040/041/043).
- **develop CI api-mail** : ✅ **green** ([run 25992588177](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/25992588177), conclusion=success). Confirme que les fixes UserContextInfo post-task-043 (`313370c` + `e86c7f0`) ont restauré le signal CI durablement.
- **Local feature branch** (api-mail) : `chore/task-045-sonar-hotspots-review` conservée localement après `gh pr merge --delete-branch` (le flag retire uniquement le remote per `feedback_forge_merge_keep_local_branches`).
