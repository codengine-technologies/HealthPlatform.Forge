# todo-task-044-split-settings-controller.md — Split `SettingsController` (S6960)

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune (parallélisable avec task-040, 041, 042, 043, 045)
**Epic**: E010
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Éliminer **1 occurrence S6960** sur
`src/Api/Controllers/V1/SettingsController.cs`. Le contrôleur regroupe trop
de responsabilités hétérogènes (settings user, settings tenant/global, feature
flags, préférences UI, etc.). Split en plusieurs contrôleurs cohérents avec
mise à jour synchrone des frontends.

Plan US-complete identique à tasks 042 et 043 (règle 11).

## Plan de découpage proposé

À affiner par `/develop` après lecture du contrôleur. Découpage hypothétique :

| Nouveau contrôleur | Routes (proposition) | Responsabilité |
|---|---|---|
| `UserSettingsController` | `/api/v1/settings/user/*` | Préférences personnelles utilisateur |
| `TenantSettingsController` ou `OrganizationSettingsController` | `/api/v1/settings/organization/*` | Settings au niveau organisation/tenant |
| `FeatureFlagsController` | `/api/v1/settings/features/*` | Lecture des feature flags (souvent géré par un service à part type Flagsmith — peut-être pas nécessaire) |

Découpage exact arbitré par `/develop` après lecture. `questions/task-044.md`
si ambiguité (notamment pour l'éventuelle séparation feature flags : si déjà
delegué à Flagsmith via DI, le sortir du contrôleur n'a pas d'intérêt).

## Scope par repo

### `api-mail`
- Lire `src/Api/Controllers/V1/SettingsController.cs`
- Identifier les groupes de responsabilités
- Créer N nouveaux contrôleurs sous `src/Api/Controllers/V1/`
- Supprimer ou réduire `SettingsController.cs`
- Routes / Auth / OpenAPI tags mis à jour
- Tests unitaires + intégration

### `client-blazor`
- Mettre à jour les services HTTP appelant les routes Settings
- Pages settings adaptées si l'arborescence des routes change (URLs côté
  frontend)
- Build + test verts

### `client-angular` (code-only mode)
- Mettre à jour les services HTTP TypeScript équivalents
- Build + test verts
- (Humain) branche commit/push/PR TFS

## Scope OUT

- Pas de nouveau réglage métier, pas de nouvelle preference
- Pas de touchee aux autres controllers (Patients / Management)
- Pas de modification du modèle de stockage des settings
- Pas de migration de données

## Definition of Done

### Tous repos
- [ ] Build passes (0 errors)
- [ ] Tests passent (0 failures)

### `api-mail`
- [ ] **0 occurrence** restante de `csharpsquid:S6960` sur
      `SettingsController.cs`
- [ ] Chaque nouveau contrôleur a un nom révélant sa responsabilité
- [ ] Chaque endpoint a ≥ 1 test d'intégration (rule 1b)
- [ ] OpenAPI régénérée, tags propres
- [ ] Parité fonctionnelle complète

### `client-blazor` + `client-angular`
- [ ] Services HTTP mis à jour
- [ ] Aucun appel résiduel vers les anciennes routes
- [ ] Tests verts

### Cross-repo
- [ ] 3 PRs cross-linkées
- [ ] Label `awaiting-us-completion` puis `awaiting-human-merge`

## Manual Test Plan

1. Démarrer backend + Blazor + Angular
2. Tester end-to-end les écrans settings sur les deux frontends :
   - Page settings utilisateur (modifier une préférence, persistance)
   - Page settings organisation (si exposée)
   - Lecture / activation feature flag (si géré par cet endpoint)
3. Vérifier console réseau : appels HTTP sur les **nouvelles** routes
4. Vérifier SonarQube : **0** occurrence S6960 sur SettingsController
5. Vérifier OpenAPI : nouveaux contrôleurs visibles
