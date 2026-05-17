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

## Closed — no-op (2026-05-17)

**Décision** : task fermée sans implémentation, option C.2 après inspection préalable au `/start`.

**Pourquoi** :

1. **`csharpsquid:S6960` = 0 occurrence** dans le Sonar actuel. La règle n'est pas dans le profile `Weda way` actif depuis 2026-05-14.

2. **Analyse design data-driven** :
   - **75 LOC, 4 endpoints** (`getsettings`, `[HttpPost]`, `settings`, `autoconfig`).
   - Ratio ~19 LOC/endpoint — c'est un controller **petit** pour les standards .NET.
   - Pas de mixed-responsibilities flagrant à cette taille.

3. **Coût/bénéfice nettement défavorable** :
   - Splitter un contrôleur de 75 LOC en N micro-controllers ajoute du boilerplate (déclaration classe + ctor DI + attributs `[Route]` + `[Authorize]`) pour un bénéfice nul. Le résultat serait moins lisible que l'original.
   - Refactor toucherait 3 repos (api-mail + client-blazor + client-angular) avec US-complete merge gate. Coût ~3-5 j·p pour **dégrader** la lisibilité.

**À reconsidérer si** :
- L'admin Sonar décide de réactiver `csharpsquid:S6960` dans `Weda way`.
- `SettingsController` croît significativement (> 300 LOC ou > 10 endpoints).
- Note tangentielle : les attributs L40-41 affichent une incohérence de route (`[HttpPost]` sans nom + `[HttpGet("settings")]` dans une class déjà routée `/settings` → produit `GET /settings/settings`). À nettoyer dans une future task ciblée si cette URL pose problème en pratique, mais hors scope S6960.

**Aucune branche créée** sur aucun repo. Aucun commit, aucun PR. État repos identique à pré-`/start`.
