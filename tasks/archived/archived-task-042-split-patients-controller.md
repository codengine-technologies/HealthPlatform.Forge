# todo-task-042-split-patients-controller.md — Split `PatientsController` (S6960)

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune (parallélisable avec task-040, 041, 043, 044, 045)
**Epic**: E010
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Éliminer **1 occurrence S6960** (`csharpsquid:S6960` — controllers should have
mixed responsibilities) sur `src/Api/Controllers/V1/PatientsController.cs`.

Le contrôleur regroupe aujourd'hui trop de responsabilités hétérogènes
(recherche, CRUD patient, ressources liées, etc.). Split en plusieurs
contrôleurs cohérents, et **mise à jour synchronisée des deux frontends**
(Blazor + Angular) car les routes changent.

## Pourquoi US-complete (règle 11)

Le split casse les routes HTTP exposées. Pour respecter la **règle 11
US-complete merge gate**, les 3 PRs (api-mail + blazor + angular) doivent
être prêtes ensemble avant tout merge :

- `api-mail` : nouveaux contrôleurs, anciennes routes supprimées
- `client-blazor` : services HTTP mis à jour vers les nouvelles routes
- `client-angular` : services HTTP TypeScript mis à jour (code-only mode,
  human owns git push + PR TFS)

`/review` posera le label `awaiting-us-completion` sur chaque PR
intermédiaire jusqu'à ce que les 3 soient prêtes.

## Plan de découpage proposé

À affiner pendant le `/develop` (lecture du contrôleur). Hypothèses initiales
basées sur les responsabilités typiques :

| Nouveau contrôleur | Routes (proposition) | Responsabilité |
|---|---|---|
| `PatientsController` (réduit) | `/api/v1/patients` + `/api/v1/patients/{id}` | CRUD pur du patient (GET/POST/PUT/DELETE) |
| `PatientSearchController` | `/api/v1/patients/search` + facets/autocomplete | Recherche, filtres, autocomplete |
| `PatientResourcesController` ou équivalent | `/api/v1/patients/{id}/{resource}` | Resources liées (documents, contacts, etc.) |

Le découpage exact est fixé par `/develop` après lecture du contrôleur
existant et discussion avec l'humain en cas d'ambiguïté (création de
`questions/task-042.md`).

### Alias de transition (NON retenu — règle 11)

Pas d'alias `[Route("/api/v1/old-route")]` sur les nouveaux contrôleurs.
La règle 11 impose que la US (split + frontends) soit complète et testée
end-to-end avant merge. Pas de "fausse v1" avec routes legacy en parallèle.

## Scope par repo

### `api-mail`

- Lire `src/Api/Controllers/V1/PatientsController.cs`
- Identifier les groupes de responsabilités (≥ 2 distincts)
- Créer N nouveaux contrôleurs sous `src/Api/Controllers/V1/`
- Supprimer `PatientsController.cs` original (ou le réduire au CRUD pur)
- Mettre à jour les attributs `[Route(...)]`, `[Authorize]`, OpenAPI tags
- Tests unitaires : 1 fixture par nouveau contrôleur, ≥ 1 test par endpoint
- Tests d'intégration : couvrir les routes nouvelles (rule 1b — chaque
  endpoint a ≥ 1 test d'intégration)

### `client-blazor`

- Identifier le service HTTP qui consomme les routes patient (probablement
  `PatientService.cs` ou équivalent sous `Services/Api/`)
- Mettre à jour les URLs vers les nouvelles routes
- Aucun changement UI (Blazor pages restent identiques côté UX)
- Build + test passent

### `client-angular` (code-only mode)

- Identifier le service HTTP TypeScript équivalent
- Mettre à jour les URLs vers les nouvelles routes
- Aucun changement UI
- `npm run build` + `npm test` passent
- **L'humain gère** : checkout branche, commit, push, ouverture PR TFS

## Scope OUT

- Pas de modification du schema patient (DB, DTO, models)
- Pas de modification de la couche Application (services métier)
- Pas de touchee aux autres controllers (Management, Settings — voir tasks
  043 et 044)
- Pas de nouveau endpoint, pas de nouveau besoin métier — refacto pur
- Pas d'évolution des permissions / authz (mêmes `[Authorize]` reportés)

## Definition of Done

### Tous repos
- [ ] Build passes (0 errors)
- [ ] Tests passent (0 failures)

### `api-mail`
- [ ] **0 occurrence** restante de `csharpsquid:S6960` sur
      `src/Api/Controllers/V1/PatientsController.cs` (le fichier peut
      avoir été supprimé et remplacé)
- [ ] Chaque nouveau contrôleur a un nom révélant sa responsabilité
- [ ] Chaque endpoint a ≥ 1 test d'intégration (rule 1b)
- [ ] OpenAPI/Swagger doc régénérée et cohérente (tags propres)
- [ ] Aucune route HTTP perdue (parité fonctionnelle complète)

### `client-blazor`
- [ ] Services HTTP mis à jour vers les nouvelles routes
- [ ] Aucun appel résiduel vers les anciennes routes (`grep` confirme)
- [ ] Tests Blazor verts

### `client-angular`
- [ ] Services HTTP TypeScript mis à jour
- [ ] `npm run build` + `npm test` verts
- [ ] (Humain) branche commit/push/PR TFS gérés manuellement

### Cross-repo
- [ ] Les 3 PRs (api-mail, blazor, angular) référencent mutuellement leurs
      liens (cross-link dans cette task)
- [ ] Label `awaiting-us-completion` sur chaque PR tant que les 3 ne sont
      pas prêtes ; passage à `awaiting-human-merge` une fois alignées

## Manual Test Plan

1. **Backend** : `cd Api/Mail && dotnet run` (ou Aspire AppHost)
2. **Blazor** : `cd Client/Blazor && dotnet run`
3. **Angular** : `cd Client/Angular && npm start`
4. Ouvrir la page Patients sur chaque frontend
5. Tester end-to-end :
   - Recherche patient par nom (autocomplete + résultats)
   - Ouverture fiche patient (GET /{id})
   - Création d'un nouveau patient
   - Modification d'une fiche patient
   - Suppression d'un patient
   - Accès aux ressources liées (documents, contacts) si pertinent
6. Vérifier dans la console réseau du navigateur : appels HTTP vers les
   **nouvelles** routes uniquement (pas de fallback / pas de 404)
7. Vérifier sur SonarQube : **0** occurrence S6960 sur PatientsController
8. Vérifier OpenAPI : `http://localhost:5000/swagger` (ou équivalent),
   les nouveaux contrôleurs apparaissent avec leurs tags propres

## Closed — no-op (2026-05-17)

**Décision** : task fermée sans implémentation, option C.2 après inspection préalable au `/start`.

**Pourquoi** :

1. **`csharpsquid:S6960` = 0 occurrence** dans le Sonar actuel. La règle n'est pas dans le profile `Weda way` actif depuis 2026-05-14 — le PatientsController n'est plus flaggé. DOD littérale "0 occurrence restante de S6960" trivialement satisfaite sans action.

2. **Analyse design data-driven** :
   - **368 LOC, 10 endpoints**, 4 groupes de responsabilités (lookup INS × 3, search × 3, opposition × 2, dashboard × 2).
   - Le ratio responsabilités/LOC est défavorable (4 groupes mélangés) mais la taille absolue (368 LOC) reste modérée — pas un code smell critique.

3. **Coût/bénéfice défavorable** :
   - Refactor toucherait 3 repos (api-mail + client-blazor + client-angular) → US-complete merge gate (CLAUDE.md règle 11) → 3 PRs alignées, 2 frontends à mettre à jour, Angular en code-only (humain owns PR TFS).
   - Estimation : ~5-7 j·p pour un bénéfice purement cosmétique (4 mini-controllers de ~80-90 LOC chacun).
   - Aucun gain technique mesurable (perfs, sécurité, observabilité).

4. **Précédent task-041** : même pattern (règle Sonar cible absente du profile, option C "refactor seulement les vrais cas design"). Cohérence avec la décision déjà prise.

**À reconsidérer si** :
- L'admin Sonar décide de réactiver `csharpsquid:S6960` dans `Weda way`.
- `PatientsController` croît significativement (> 600 LOC ou > 15 endpoints) → re-évaluation.
- Un besoin métier amène à ajouter un 5ᵉ groupe de responsabilités.

**Aucune branche créée** sur aucun repo. Aucun commit, aucun PR. État repos identique à pré-`/start`.
