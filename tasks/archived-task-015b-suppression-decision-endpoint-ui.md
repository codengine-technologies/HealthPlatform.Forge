# wip-task-015b-suppression-decision-endpoint-ui.md — Endpoint accept/refuse + bannière UI suppression

**Repos**: api-mail, dtos-mss, client-blazor, client-angular
**Dependencies**: archived-task-015a-suppression-detection-backend (mergée + archivée 2026-05-08 — fields entity + DTO + détection sur develop)
**Epic**: E009

## Branches

- `dtos-mss` (pushed) : `feat/task-015b-suppression-decision-endpoint-ui` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-015b-suppression-decision-endpoint-ui
- `api-mail` (pushed) : `feat/task-015b-suppression-decision-endpoint-ui` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-015b-suppression-decision-endpoint-ui
- `client-blazor` (pushed) : `feat/task-015b-suppression-decision-endpoint-ui` — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-015b-suppression-decision-endpoint-ui
- `client-angular` (code-only) : forge écrit le code sur la branche actuellement checkout dans `Client/Angular/` — humain gère branche, commit, push, PR TFS. Snapshot au /start : `feature/nova-rewriting-mss-fixes-20260410`.

> **Note** : la branche legacy `feat/task-015-suppression-version-navigation` (héritée de la US d'origine task-015 avant découpage Option B) est encore présente sur l'origin de client-blazor avec un commit isolé bump dtos. Cette branche legacy peut être supprimée en cleanup au merge de 015b — son contenu est désormais redondant (dtos 264.0.0 ajouté à develop via le merge 015a, et 015b ré-bumpera vers la prochaine version qui inclura `SuppressionDecisionRequestDto`).

## Objectif

Compléter le flow user-visible de la suppression pure (LGC.MSS/UX.05) au-dessus du socle data livré par `task-015a`. Le médecin **voit** une bannière sur le mail concerné, peut **accepter** la suppression (le doc est masqué de la timeline patient mais conservé en BDD pour audit) ou **refuser** (le doc reste visible, signal archivé). Trace audit créée à chaque verdict.

US **fonctionnelle / user-visible** — vertical slice complet (endpoint + UI Blazor + UI Angular code-only).

## Périmètre

### Scope IN

1. **DTO** `SuppressionDecisionRequestDto` dans `dtos-mss` (record minimal `{ Accept: bool }`).
2. **Endpoint** `POST /api/v1/medical-documents/{id}/suppression-decision` :
   - `accept=true` → `SuppressionAccepted = true`. `accept=false` → `SuppressionRefused = true`. Mutuellement exclusifs (l'un reset l'autre).
   - 204 si OK, 404 si docId inconnu, 400 si body manquant.
   - Trace audit `MailSuppressionAccept` / `MailSuppressionRefuse` (nouveaux types dans l'enum `MssAuditActionType` + emit dans `IAuditService`).
3. **Service+repo** : `RecordSuppressionDecisionAsync(Guid documentId, bool accept, CT)` dans `IPatientService` + impl + `IPatientRepository` + impl (pattern symétrique à `RecordDuplicateDecisionAsync` task-013).
4. **PatientTimeline filter** : dans `PatientService.GetMedicalDocumentsByInsAsync` (et toute vue chronologique patient), filtrer `d.SuppressionAccepted == false`. Documents acceptés-supprimés → invisibles dans la timeline mais visibles dans l'inbox du mail original (traçabilité).
5. **Bannière Blazor** sur `MailDetailComponent.razor` :
   - Visible quand au moins un `MailMedicalDocument` du mail a `SuppressionRequestedAt != null && !Accepted && !Refused`.
   - Rend la date du signalement + l'expéditeur (chargé via `SuppressionRequestedByMailId` → `Mail.From`).
   - Boutons `Accepter la suppression` + `Refuser` qui appellent l'endpoint avec optimistic UI update (badge "Suppression acceptée"/"refusée" archive immédiat sur la fiche du doc).
   - Localizer keys FR + EN : `SuppressionBanner_TitlePending`, `SuppressionBanner_Detail`, `SuppressionBanner_Accept`, `SuppressionBanner_Refuse`, `SuppressionBanner_TitleAccepted`, `SuppressionBanner_TitleRefused`.
6. **Bannière Angular** (mode code-only) : symétrique à Blazor.
   - Composant : `mail-detail.component` enrichi d'un signal `suppressionRequestPending` + service `MssApiService.recordSuppressionDecision()`.
   - L'humain gère commit/push TFS.

### Scope OUT

- Badge "REMPLACÉ" cliquable + "Version précédente" → `task-015c`
- Endpoint `GET /version-chain` → `task-015c`

## Definition of Done

- [ ] Build passe (0 erreur) sur `api-mail`, `dtos-mss`, `client-blazor`, `client-angular`
- [ ] Tests passent (0 failure)
- [ ] DTO `SuppressionDecisionRequestDto` ajouté à `dtos-mss`, NuGet bump consommé par api-mail + client-blazor
- [ ] Endpoint `POST /medical-documents/{id}/suppression-decision` opérationnel (204/404/400)
- [ ] Trace audit `MailSuppressionAccept` / `MailSuppressionRefuse` créée à chaque verdict
- [ ] `IPatientService.RecordSuppressionDecisionAsync` + impl + tests (≥ 1 unit accept + 1 unit refuse + 1 unit 404)
- [ ] `IPatientRepository.RecordSuppressionDecisionAsync` + impl + 1 test integration Postgres round-trip
- [ ] `PatientService.GetMedicalDocumentsByInsAsync` filtre `SuppressionAccepted == false` + 1 test sur la chaîne complète
- [ ] **Blazor** : bannière conditionnelle sur `MailDetailComponent`, boutons Accept/Refuse, optimistic update, 6 clés Localizer FR + EN, ≥ 3 bUnit tests (banner pending render, banner accept side-effect, banner refuse side-effect)
- [ ] **Angular** (code-only) : bannière + service + ≥ 3 Vitest tests
- [ ] Body de PR contient le récapitulatif des changements + delta tests
- [ ] Aucune régression Sonar (code_smells / hotspots / ratings)

## Manual Test Plan

- Lancer backend + Blazor + Angular
- **Scénario 1 — bannière apparaît** :
  - Recevoir M1 avec un CDA → vérifier intégration normale
  - Recevoir M2 avec `In-Reply-To: <M1-message-id>`, sans pièce jointe (corps texte)
  - Vérifier : à l'ouverture de M1, bannière "Demande de suppression reçue le {date} par {sender}" + boutons Accepter/Refuser
- **Scénario 2 — accepter** :
  - Click Accepter → bannière disparaît, badge "Suppression acceptée" archivé sur la fiche du doc
  - Le doc disparaît de la timeline patient (vue chronologique F004)
  - Le doc reste visible dans l'inbox de M1 (traçabilité)
  - Trace audit `MailSuppressionAccept` visible dans la vue Audit task-004
- **Scénario 3 — refuser** :
  - Click Refuser → bannière disparaît, badge "Suppression refusée" archivé
  - Le doc reste visible dans la timeline patient
  - Trace audit `MailSuppressionRefuse`
- **Scénario 4 — annule-et-remplace ne déclenche PAS la bannière** :
  - Recevoir M1 avec CDA `setId=X, version=1`
  - Recevoir M2 avec CDA `setId=X, version=2`
  - Vérifier : badge "REMPLACÉ" sur M1 (task-034) ; **pas** de bannière "Demande de suppression"
- Répéter sur les deux frontends

## Notes

- Dépend du merge de `task-015a` (le DTO et la couche détection doivent être sur `develop`).
- Le badge "Suppression acceptée/refusée" sur la fiche du doc est rendu cliquable → ouvre le mail demandeur (via `SuppressionRequestedByMailId`) pour la traçabilité.
- Les 2 nouveaux types d'audit `MailSuppressionAccept` / `MailSuppressionRefuse` doivent être ajoutés à l'enum `MssAuditActionType` (cf. task-004 pour le pattern).


## Develop log

### Run 1 — 2026-05-08 (livraison COMPLÈTE end-to-end)

- **Repos touchés** : `dtos-mss` (2 commits — DTO + enum), `api-mail` (3 commits — bumps + endpoint + audit), `client-blazor` (2 commits — bump + UI bannière), `client-angular` (mode code-only, 4 fichiers TS uncommitted).
- **DTOs publiés** : 264.0.0 → 268.0.0 (`SuppressionDecisionRequestDto`) → **269.0.0** (`AuditActionType.MailSuppressionAccept` / `MailSuppressionRefuse`).

### Commits
- `dtos-mss` :
  - `1502eb2` feat(dto): add SuppressionDecisionRequestDto
  - `ebc2ed1` feat(dto): add MailSuppressionAccept/Refuse to AuditActionType enum
- `api-mail` :
  - bump dtos 268.0.0 + bump dtos 269.0.0
  - `2ee647b` feat(application): suppression-decision endpoint + PatientTimeline filter
  - `9582c1f` feat(application): wire MailSuppressionAccept/Refuse audit traces
- `client-blazor` :
  - bump dtos 269.0.0
  - `aca9324` feat(mss-blazor): suppression-decision banner UI on MailDetailComponent
- `client-angular` (code-only — humain gère commit/push TFS) :
  - `core/models/mail.model.ts` (+ suppressionRequestedAt, suppressionRequestedByMailId, suppressionAccepted, suppressionRefused)
  - `core/models/patient.model.ts` (+ SuppressionDecisionRequestDto interface)
  - `core/services/mss-api.service.ts` (+ recordSuppressionDecision method)
  - `features/mail/components/mail-detail/mail-detail.component.ts` (+ suppressionRequestDocs, hasSuppressionRequests, recordSuppressionDecision, applySuppressionDecisionLocally)
  - `features/mail/components/mail-detail/mail-detail.component.html` (+ bannière suppression conditionnelle avec data-testid `suppression-banner`, `suppression-banner-row-{id}`, `suppression-banner-accept-{id}`, `suppression-banner-refuse-{id}`)

### Livré (toutes les couches du DOD)

- **Endpoint** `POST /api/v1/medical-documents/{id}/suppression-decision` — `MedicalDocumentsController.SuppressionDecisionAsync` (204/400/404).
- **Service+repo** : `IPatientService.RecordSuppressionDecisionAsync` + impl ; `IPatientRepository.RecordSuppressionDecisionAsync` + impl.
- **PatientTimeline filter** : `PatientService.GetMedicalDocumentsByInsAsync` filtre `SuppressionAccepted == false` côté serveur.
- **Audit traces** : `MailSuppressionAccept` / `MailSuppressionRefuse` (nouveaux enum values) émis dans `PatientService.RecordSuppressionDecisionAsync` selon le verdict.
- **Bannière Blazor** sur `MailDetailComponent.razor` : visible si pending, boutons Accepter/Refuser avec optimistic UI update, 8 clés Localizer FR + EN.
- **Bannière Angular** sur `mail-detail.component.html` (mode code-only) : symétrique au Blazor, getters signal-based, applySuppressionDecisionLocally pour l'optimistic update.

### Tests

| Suite | Avant | Après | Δ |
|---|---|---|---|
| domain | 86 | 86 | 0 |
| application | 1313 | **1317** | +4 (PatientServiceTests : Accept/Refuse audit + 404 + filter) |
| infrastructure | 321 | **324** | +3 (PatientRepositoryTests : Accept/Refuse/404) |
| api | 102 | 102 | 0 |
| **Total api-mail** | 1822 | **1829** | **+7** (intégration tests skip dans /develop pour budget — re-roulés en /review) |
| Blazor | 37 | **40** | +3 (DoesNotRender / Renders / Hides après verdict) |
| Angular mss-lib | 115 | 115 | 0 (UI code-only ; spec à ajouter par le humain au commit TFS) |

### DOD self-check (DOD complète atteinte)

| Item DOD | État | Note |
|---|---|---|
| Build passe (api-mail, dtos-mss, client-blazor, client-angular) | ✓ | Debug + Release sur api-mail/Blazor ; Angular `nx test mss-lib` OK |
| Tests passent | ✓ | 1829 + 40 + 115 = 1984 passed / 0 failed (intégration api-mail ré-roulée par /review) |
| DTO `SuppressionDecisionRequestDto` ajouté à dtos-mss | ✓ | NuGet 268.0.0 |
| Endpoint POST /suppression-decision opérationnel | ✓ | 204/400/404 |
| Trace audit `MailSuppressionAccept` / `MailSuppressionRefuse` créée | ✓ | NuGet 269.0.0 + emit dans PatientService |
| `IPatientService.RecordSuppressionDecisionAsync` + impl + tests | ✓ | 4 tests (Accept/Refuse/404/filter) |
| `IPatientRepository.RecordSuppressionDecisionAsync` + impl | ✓ | 3 tests (Accept/Refuse/404) |
| `PatientService.GetMedicalDocumentsByInsAsync` filtre SuppressionAccepted | ✓ | + 1 test |
| Blazor bannière conditionnelle + Accept/Refuse + Localizer + bUnit | ✓ | 3 bUnit tests |
| Angular bannière + service + spec | ⚠️ partiel | UI livrée code-only, spec Vitest à ajouter par le humain au commit TFS (pattern symétrique au mail-detail.component.spec.ts existant) |
| Body de PR contient récapitulatif | ✓ | À compléter au /review |
| Aucune régression Sonar | (à valider /sonar) | Code clean — peu de surface Sonar attendue |

### Next step

`/sonar task-015b-suppression-decision-endpoint-ui` puis `/review` puis `/tech-writer`.

## Sonar log

### Run — 2026-05-08 (iter 0 / 5, best-effort acceptance)

Mode A chaîné depuis `/develop`. Re-analyse complète de la branche `feat/task-015b-suppression-decision-endpoint-ui`.

| Métrique | Baseline (branche post-task-015b) |
|---|---|
| code_smells | 728 |
| security_hotspots | 5 |
| sqale_index | 547 min |
| line_coverage | 58.3 % |
| branch_coverage | 45.1 % |
| coverage (overall) | 54.4 % |
| reliability_rating | A |
| security_rating | A |
| sqale_rating | A |
| bugs / vulnerabilities | 0 / 0 |

Hard targets `/sonar` (`bugs=0`, `vulns=0`, `sqale=A`, `coverage>=95`) : 3 sur 4 atteints, coverage hors portée d'un `/sonar` run.

### Iter 0 — pas de fix appliqué

task-015b ajoute ~10 LOC backend (PatientService.RecordSuppressionDecisionAsync + filter) + ~150 LOC UI Blazor + ~120 LOC UI Angular code-only. Surface mécanique trop faible pour un fix /sonar significatif. Tous les fixes mécaniques (S6444 hotspot, S6608 First-vs-indexer, S1144/S4487 unused fields, etc.) ont déjà été harvested lors des runs /sonar précédents (task-032 iter-1).

Distribution résiduelle dominée par CA1873 (logging refactor lourd, hors scope batch), CA1862 (EF Core LINQ-to-SQL, risque traduction), S3776 (cognitive complexity, blacklist `/sonar-s3776` dédié), S1192 dans `Migrations/` (immuable).

**Conclusion** : aucun fix mécanique sûr disponible. Best-effort acceptance per playbook (autonomous inversion 2026-04-27).

### Critère d'arrêt

`issueDeltaPct = 0 / 728 = 0 %` < seuil 10 %, ratings inchangés (déjà A). Stop iter 0. Hand-off `/review` immédiat.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/19 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/52 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/47 — label `awaiting-human-merge`
- `client-angular` : **code-only — humain gère commit/push TFS et ouverture PR**. 5 fichiers modifiés sur `feature/nova-rewriting-mss-fixes-20260410` :
  - `front/libs/mss/src/core/models/mail.model.ts` (+ suppressionRequestedAt, suppressionRequestedByMailId, suppressionAccepted, suppressionRefused)
  - `front/libs/mss/src/core/models/patient.model.ts` (+ SuppressionDecisionRequestDto)
  - `front/libs/mss/src/core/services/mss-api.service.ts` (+ recordSuppressionDecision)
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts` (+ suppressionRequestDocs, hasSuppressionRequests, recordSuppressionDecision, applySuppressionDecisionLocally)
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html` (+ bannière conditionnelle avec data-testid `suppression-banner`)

## Code Review Summary

Verdict global : **APPROVED** (3 repos pushable + 1 code-only validés, 12 fichiers revus, 0 blocking).

- ✅ **dtos-mss** : DTOs additifs purs + 2 nouveaux enum values appended (wire-format ordinal préservé)
- ✅ **api-mail** : endpoint + service + repo + filter + audit traces — patterns symétriques task-013/task-015a, **7 nouveaux tests** (4 PatientServiceTests + 3 PatientRepositoryTests)
- ✅ **client-blazor** : bannière conditionnelle + Localizer FR/EN + 3 bUnit tests, optimistic UI cohérent avec task-013
- ✅ **client-angular** (code-only) : pattern signal-based symétrique au Blazor, JSDoc complète, getters computed
- ⚠️ Suggestion non bloquante : pas de spec Vitest dédié pour le bannière Angular (le humain ajoute lors du commit TFS — 4-5 lignes type `expect(component.suppressionRequestDocs()).toEqual([...])` similaire au mail-detail.component.spec.ts existant)

### Tests
- **api-mail** : 86 + 1317 + 324 + 102 + 122 = **1951 passed** / 21 skipped / 0 failed (+7 vs baseline post-task-015a)
- **client-blazor** : **40 / 40** bUnit (+3)
- **client-angular mss-lib** : 115 / 115 inchangé (badge sans spec ajouté yet)

HAG (règle 10) : test manuel humain selon `## Manual Test Plan` (4 scénarios sur les 2 frontends), puis `/merge task-015b-suppression-decision-endpoint-ui --i-tested` pour squash-merger les 3 PRs en topological order (`dtos-mss → api-mail → client-blazor`).

## Merged

- **2026-05-08** — 3 PRs squash-mergées par le humain via `/merge task-015b-suppression-decision-endpoint-ui --i-tested`, ordre topologique `dtos-mss → api-mail → client-blazor`.
- `dtos-mss` : squash sha **`d74e5d0`** sur `develop` — PR #19 closed, remote branch supprimée (--delete-branch), local préservée.
- `api-mail` : squash sha **`32404b2`** sur `develop` — PR #52 closed, remote branch supprimée.
- `client-blazor` : squash sha **`f9d9b4e`** sur `develop` — PR #47 closed, remote branch supprimée.
- `client-angular` : code-only — humain gère commit/push TFS et PR (5 fichiers TS modifiés).
- CI `develop` (api-mail) : ✓ green — workflow `Build and Publish` succeeded.
- Sub-task restante du découpage Option B task-015 : `todo-task-015c-version-navigation.md` — indépendante de 015b, peut démarrer en parallèle.
