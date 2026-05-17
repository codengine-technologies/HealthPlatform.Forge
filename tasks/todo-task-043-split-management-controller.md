# todo-task-043-split-management-controller.md — Split `ManagementController` (S6960)

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune (parallélisable avec task-040, 041, 042, 044, 045)
**Epic**: E010
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Éliminer **1 occurrence S6960** sur
`src/Api/Controllers/V1/ManagementController.cs`. Le contrôleur regroupe trop
de responsabilités hétérogènes (health, diagnostics, settings admin, ops,
etc.). Split en plusieurs contrôleurs cohérents avec mise à jour synchrone
des deux frontends.

Plan US-complete identique à task-042 (règle 11) : les 3 PRs (api-mail +
blazor + angular) sont prêtes ensemble avant merge.

## Plan de découpage proposé

À affiner par `/develop` après lecture du contrôleur. Découpage hypothétique :

| Nouveau contrôleur | Routes (proposition) | Responsabilité |
|---|---|---|
| `HealthController` ou `DiagnosticsController` | `/api/v1/health`, `/api/v1/diagnostics/*` | Liveness, readiness, diagnostics ops |
| `OperationsController` ou `MaintenanceController` | `/api/v1/ops/*` | Tâches d'administration (purge, reindex, etc.) |
| `SystemInfoController` | `/api/v1/system/info`, `/api/v1/system/version` | Méta-info applicative |

Découpage exact arbitré par `/develop` (lecture + éventuellement
`questions/task-043.md` si ambigu). Pas d'alias legacy (règle 11).

## Scope par repo

### `api-mail`
- Lire `src/Api/Controllers/V1/ManagementController.cs`
- Identifier les groupes de responsabilités
- Créer N nouveaux contrôleurs sous `src/Api/Controllers/V1/`
- Supprimer ou réduire `ManagementController.cs`
- Routes / Auth / OpenAPI tags mis à jour
- Tests unitaires par nouveau contrôleur, intégration par endpoint

### `client-blazor`
- Mettre à jour les services HTTP appelant les routes Management
- Aucun changement UI sauf si dashboards admin référencent ces routes
- Build + test verts

### `client-angular` (code-only mode)
- Mettre à jour les services HTTP TypeScript équivalents
- Build + test verts
- (Humain) branche commit/push/PR TFS

## Scope OUT

- Pas de nouveau endpoint, pas de nouveau besoin métier
- Pas de touchee à PatientsController (task-042) ou SettingsController (task-044)
- Pas de modification de la couche Application (services métier)
- Pas d'évolution des permissions

## Definition of Done

### Tous repos
- [ ] Build passes (0 errors)
- [ ] Tests passent (0 failures)

### `api-mail`
- [ ] **0 occurrence** restante de `csharpsquid:S6960` sur
      `ManagementController.cs`
- [ ] Chaque nouveau contrôleur a un nom révélant sa responsabilité
- [ ] Chaque endpoint a ≥ 1 test d'intégration (rule 1b)
- [ ] OpenAPI régénérée, tags propres
- [ ] Parité fonctionnelle complète

### `client-blazor` + `client-angular`
- [ ] Services HTTP mis à jour vers les nouvelles routes
- [ ] Aucun appel résiduel vers les anciennes routes (grep confirme)
- [ ] Tests verts

### Cross-repo
- [ ] 3 PRs cross-linkées dans cette task
- [ ] Label `awaiting-us-completion` puis `awaiting-human-merge` selon
      l'avancement des PRs

## Manual Test Plan

1. Démarrer backend + Blazor + Angular comme task-042
2. Tester end-to-end les écrans/flows admin qui consomment ces routes :
   - Health/diagnostics page (si exposée dans les UIs)
   - Pages admin/maintenance
   - Page system info / version
3. Vérifier console réseau : appels HTTP sur les **nouvelles** routes
4. Vérifier SonarQube : **0** occurrence S6960 sur ManagementController
5. Vérifier OpenAPI : nouveaux contrôleurs visibles, tags propres
