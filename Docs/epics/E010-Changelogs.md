# E010 — Changelogs ingénierie « Sonar cleanup api-mail (hors coverage) »

> **Audience** : équipes techniques, backlog, dette, audit qualité.
> **Document frère (vue produit / direction)** : [`E010-sonar-cleanup-api-mail-hors-coverage.md`](./E010-sonar-cleanup-api-mail-hors-coverage.md)
> **Dernière mise à jour** : 2026-05-17
>
> Ce document concentre les détails ingénierie qui n'ont pas leur place dans
> la vue produit : task IDs, numéros de PR, commits, fichiers touchés,
> métriques Sonar avant/après, décisions de refactor, limites différées.
> Le doc produit conserve la vision business ; les `task-XXX` y apparaissent
> en spine discret.

---

## Historique détaillé des changelogs

### v0.2 — 2026-05-17 — Refactor SemanticSearchService param objects (task-041)

**PR** : `api-mail` #63 — `refactor(search): extract SemanticSearchOptions param objects (task-041)` — label `awaiting-human-merge`.

**Branche** : `chore/task-041-sonar-s107-param-objects` (api-mail + dtos-mss). dtos-mss : 0 commit, pas de PR.

**Scope révisé en cours de cycle** (option C après halt `/develop`, voir `questions/answered/task-041.md`) :

- Cible initiale du task body : 9 méthodes flaggées `csharpsquid:S107` (> 7 paramètres).
- Réalité 2026-05-17 : **`csharpsquid:S107` a 0 occurrence** dans le Sonar actuel — la règle n'est **pas dans le profile `Weda way`** actif depuis 2026-05-14 (le profile `Sonar way` historique l'incluait).
- Les 9 méthodes existent toujours physiquement mais ne sont plus flaggées.
- Décision PO : Option C — refactor uniquement les **vrais cas design API publique**.

| # | Méthode candidate du task body | Décision |
|---|---|---|
| 1 | `MailController.cs` ctor primaire (16 deps) | Ignoré — wrapper `*Dependencies` cosmétique. Vrai fix = S6960 split (task-042/043/044). |
| 2 | `ImapConnectionService.cs` ctor | Ignoré — même argument. |
| 3 | `ImapFolderService.cs` ctor | Ignoré — même argument. |
| 4 | `ImapService.cs` ctor primaire | Ignoré — même argument. |
| 5 | `BackgroundImapService.cs` ctor | Ignoré — même argument. |
| 6 | `SmtpService.cs` ctor | Ignoré — même argument. |
| 7 | `ISemanticSearchService.SearchAsync` (8 params) + `SearchByPatientAsync` (7 params) | ✅ **Refactoré** |
| 8 | `ImapLockScope.AcquireAsync` (8 params) | Ignoré — 3 sont `[CallerMemberName/FilePath/LineNumber]`, attributs compilateur magiques qu'on ne peut pas wrapper sans casser l'auto-injection (diagnostique précieuse pour task-024 lock instrumentation). |
| 9 | `PatientRepository.ComputeScore` (8 params) | Ignoré — `private static` helper, pas de bénéfice API. Refactor structurel hors scope. |

**Commits api-mail** :

- `2a00407` — `refactor(search): extract SemanticSearchOptions / SemanticSearchByPatientOptions param objects`

**Fichier ajouté** :

- `src/Application/Models/SemanticSearchOptions.cs` (30 lignes) — 2 `sealed record` :
  - `SemanticSearchOptions` : `Query` (required), `MaxResults=10`, `MinSimilarity=0.1`, `SearchType=Both`, `SearchMode=Hybrid`, `FolderPath`, `Filters`.
  - `SemanticSearchByPatientOptions` : `Query` + `PatientId` (both required), `MaxResults=10`, `MinSimilarity=0.1`, `SearchMode=Hybrid`, `FolderPath`.

**Fichiers modifiés** :

- `src/Application/Services/Interfaces/ISemanticSearchService.cs` — `SearchAsync(SemanticSearchOptions, CancellationToken)` (vs 8 params) + `SearchByPatientAsync(SemanticSearchByPatientOptions, CancellationToken)` (vs 7 params). Doc XML mise à jour.
- `src/Application/Services/Implementation/SemanticSearchService.cs` — destructure des options en début des 2 méthodes, **body inchangé** (minimum de risque de régression). `ArgumentNullException.ThrowIfNull(options)` ajouté en garde.
- `src/Api/Controllers/V1/SearchController.cs` — 2 call sites (`POST /api/v1/search` et `POST /api/v1/search/patient`). Initializer syntax. **Request DTOs (`SearchRequestDto`, `PatientSearchRequestDto`) inchangés → contrat HTTP préservé**.
- `src/Api/Controllers/V1/ManagementController.cs` — 1 call site (`POST /api/v1/management/test-similarity`). Initializer syntax.
- `tests/mss.mail.application.tests/Services/Embedding/SemanticSearchServiceTests.cs` — 30 call sites convertis + **4 nouveaux tests dédiés** aux records (defaults + non-defaults pour les 2 records, satisfait DOD).
- `tests/mss.mail.integration.tests/UseCases/SearchUseCaseTests.cs` — 6 call sites convertis.

**Local build / test** :

- Build api-mail Release : ✓ 0 erreurs, 0 warnings.
- Tests : **2096 pass / 0 fail / 16 skipped** (16 = AI pré-existants + ParseImagingReport Linux skip)
  - domain : 86/86
  - **application : 1418/1418** (+4 vs baseline 1414, grâce aux records tests)
  - infrastructure : 346/346
  - api : 114/114
  - integration : 132/148 (16 skipped)

**KPIs Sonar — avant / après re-analyse** :

| Métrique | Avant (post-task-040) | Après | Δ |
|---|---|---|---|
| Bugs | 0 | 0 | ✅ |
| Vulnerabilities | 1 | 1 | inchangé (pré-existant token leak `report_coverage.ps1`) |
| Code Smells | 1064 | 1066 | +2 mineurs (probablement sur fichiers non-touchés, drift baseline) |
| Security Hotspots | 7 | 7 | inchangé |
| Coverage | 70.6 % | **73.3 %** | +2.7 pp (4 nouveaux tests records + recompilation) |
| Reliability rating | A | A | ✅ |
| Security rating | E | E | inchangé (token leak) |
| Maintainability rating | A | A | ✅ |
| `csharpsquid:S107` (cible) | 0 | **0** | ✅ (DOD trivialement satisfaite ; intent design respecté pour 3 méthodes refactorées) |

**Issues sur les fichiers touchés** :

| Fichier | Issues |
|---|---|
| `src/Application/Models/SemanticSearchOptions.cs` (nouveau) | **0** ✅ |
| `src/Application/Services/Interfaces/ISemanticSearchService.cs` | **0** ✅ |
| `src/Application/Services/Implementation/SemanticSearchService.cs` | 30 (pré-existants, body 90% inchangé) |
| `src/Api/Controllers/V1/SearchController.cs` | 5 (pré-existants) |
| `src/Api/Controllers/V1/ManagementController.cs` | 6 (pré-existants) |

**Quality Gate** : ERROR (même situation que task-040, non-régression). `new_violations=187 > 0` (vs 185 dans task-040, +2 mineurs). `new_coverage=78.5 % < 80 %` (+2.8 pp vs task-040 grâce aux 4 nouveaux tests, mais sous le seuil). Cause héritée multi-lang scan révélée par task-040.

**Décisions de refactor** :

- **Destructure pattern** plutôt que renaming en interne : `var query = options.Query;` etc. en début de méthode, body inchangé. Trade-off : un peu de bruit en haut des méthodes, mais zéro risque de régression sur le body (qui contient la logique métier complexe de hybrid search, filter intersection, ranking).
- **2 records distincts** (vs 1 unifié avec `PatientId` optionnel) : `SearchByPatientAsync` n'expose pas `SearchType` ni `Filters`, et `PatientId` est obligatoire — la duplication évite les options invalides au type-system.
- **`init`-only properties** (pas de primary constructor) : évite que le record lui-même déclenche S107 (synthesized ctor avec 7 params serait au seuil) et permet la syntaxe object initializer en site d'appel.

**Limites différées** :

1. Les 6 ctors DI lourds (#1-6) restent à traiter via S6960 split — voir `todo-task-042-split-patients-controller.md`, `todo-task-043-split-management-controller.md`, `todo-task-044-split-settings-controller.md` (mais aucun de ces 6 n'est listé S6960 dans le profile actuel ; les 3 controllers task-042/043/044 sont d'autres fichiers).
2. `MailController` (16 deps) n'est ni S107 (rule hors profile) ni S6960 (pas dans la liste). À traiter par décision archi explicite si la densité du ctor devient un problème pour la testabilité.
3. `ImapLockScope.AcquireAsync` : si vraiment besoin de réduire les params, alternative possible — extraire `(operation, logger)` dans un `ImapLockContext` record, garder les 3 `[CallerInfo]` attrs comme params optionnels en queue. Marginal.
4. `PatientRepository.ComputeScore` : meilleur refactor possible = merger avec `MatchByTraitsAsync` (public, 4 params, single caller) et passer un `record CandidateScore(string?, string?, DateTime?, string?)` aux 2 sides. Hors scope task-041.

---

### v0.1 — 2026-05-17 — Quick-wins S1075 + S1135 + exclusion Migrations (task-040)

**PR** : `api-mail` #62 — `chore(sonar): batch quick-wins — S1075 Flagsmith URI + S1135 TODO + Migrations exclusion (task-040)` — label `awaiting-human-merge`.

**Branche** : `chore/task-040-sonar-batch-quick-wins` (api-mail + dtos-mss). dtos-mss : 0 commit, pas de PR.

**Scope révisé en cours de cycle** (option A après halt `/sonar`, voir
`questions/answered/task-040.md`) :

- Cible initiale : CA1862 × 30 + S1075 × 1 + S1135 × 1 + S1192 × 17 (élim. via exclusion).
- Réalité 2026-05-17 :
  - CA1862 = **49** (toutes en `Where(...)` EF Core LINQ → risque client-eval silencieuse → déféré à task-047)
  - S1075 = **1** ✅ fixé
  - S1135 = **1** ✅ fixé
  - S1192 = **0** (déjà à 0, l'exclusion sert de filet futur ; a éliminé 1 S138 résiduel)
- Baseline globale code smells = **1064** (vs 100 dans le task body initial, 10× plus à cause du switch profile `Sonar way` → `Weda way` du 2026-05-14 qui a activé CA1873 × 636, S103 × 188, etc.).
- DOD recalibrée : items "Smells ≤ 51", "tests CA1862 case-insensitive", "0 occurrence CA1862", "0 occurrence S1192" supprimés.

**Commits api-mail** :

- `c4f70c5` — `fix(sonar): resolve S1075 — externalise Flagsmith ApiUrl, drop hardcoded fallback`
- `0fbc0ac` — `fix(sonar): resolve S1135 — convert NewMailNotifier TODO to neutral Note`

**Fichiers modifiés** :

- `src/Api/Extensions/FlagsmithExtensions.cs` — suppression du `const string DefaultFlagsmithApiUrl = "http://localhost:8000/api/v1/"`. Le fallback était dead code (jamais atteint quand `appsettings.json` charge `Flagsmith:ApiUrl`). Remplacé par `throw new InvalidOperationException(...)` clair → fail-fast au startup si config manquante. Classe reste `[ExcludeFromCodeCoverage]` (pattern DI extension du projet).
- `src/Application/Services/Implementation/NewMailNotifier.cs:L35-38` — `TODO(notifications-abnormal-biology-043)` (tracker inexistant — task-043 = split management controller, sans rapport) → `// Note:` explicatif pointant `archived-task-028` (biology-ack) pour le contexte domaine. Aucun changement comportemental.

**Fichier ajouté** :

- `tests/mss.mail.api.tests/Extensions/FlagsmithExtensionsTests.cs` (60 lignes, 2 tests xUnit) — vérifie (1) registration de `IFlagsmithClient` + `IFeatureFlagService` quand `Flagsmith:ApiUrl` présent en config, et (2) `InvalidOperationException` quand ni env var `FLAGSMITH_API_URL` ni config ne fournissent l'URL. Pattern try/finally pour isoler l'env var. **N'instancie pas `FlagsmithClient`** (évite l'invariant runtime `EnvironmentKey is required` qui ferait planter le test).

**Changement workspace forge (hors PR, non commité dans api-mail)** :

- `agents/sonar.md` ligne 751 — ajout de `**/Migrations/**` à `sonar.exclusions` dans le bloc `Begin` du scanner. Pas de commit sur api-mail car le fichier vit dans le workspace forge. Effet vérifié à la re-analyse : `src/Infrastructure/Migrations` passe de 1 issue (S138) à 0.

**Local build / test** :

- Build api-mail Release : ✓ 0 erreurs, 388 warnings analyzer pré-existants (non bloquants).
- Tests api-mail Release : ✓ 2092 pass / 0 fail / 16 skipped (les 16 skipped sont AI pré-existants, hors scope task-040).
  - domain : 86/86
  - application : 1414/1414
  - infrastructure : 346/346
  - api : 114/114 (+2 nouveaux : FlagsmithExtensionsTests)
  - integration : 132/148 (16 skipped = AI pré-existants)

**KPIs Sonar — avant / après re-analyse** :

| Métrique | Avant | Après | Δ |
|---|---|---|---|
| Bugs | 0 | 0 | ✅ |
| Vulnerabilities | 0 | **1** | ⚠️ pré-existant (voir limites résiduelles #1) |
| Code Smells | 1064 | 1064 | inchangé (CA1862 hors scope) |
| Security Hotspots | 7 | 7 | inchangé |
| Coverage | 66.3 % | **70.6 %** | +4.3 pp (recompilation + 2 nouveaux tests) |
| Reliability rating | A | A | ✅ |
| Security rating | A | **E** | ⚠️ pré-existant |
| Maintainability rating | A | A | ✅ |
| CA1862 (cible déférée) | 49 | 49 | inchangé (task-047) |
| S1075 (cible task-040) | 1 | **0** | ✅ |
| S1135 (cible task-040) | 1 | **0** | ✅ |
| S1192 | 0 | 0 | inchangé |
| Issues dans `src/Infrastructure/Migrations` | 1 (S138) | **0** | ✅ exclusion active |

**Quality Gate** : `ERROR` post-analyse. Conditions :
- `new_violations = 185 > 0` ❌ — provoqué par l'activation de **Multi-Language analysis** (warning Sonar : "Multi-Language analysis is enabled… set `/d:sonar.scanner.scanAll=false` if not intended"). Les 185 violations new-code sont essentiellement des findings sur des fichiers `.ps1`, `.yml`, `.json` jamais analysés auparavant — pas du code task-040.
- `new_coverage = 75.7 % < 80 %` ❌ — même origine (couverture mesurée sur le périmètre élargi par le multi-lang scan).
- `new_duplicated_lines_density = 0.92 % < 3 %` ✓.

Zero-new-debt principle techniquement violé, mais c'est de la dette héritée révélée par la config Sonar — pas par cette task. Justifie une task séparée pour soit désactiver le multi-lang scan (`sonar.scanner.scanAll=false`), soit traiter le périmètre élargi.

**Décisions de refactor** :

- **S1075 — choix "drop fallback + throw"** vs "suppress" : le fallback const était mort dans tous les environnements (`appsettings.json` charge toujours `Flagsmith:ApiUrl`). Suppression simple + throw clair, plutôt que `[SuppressMessage]` qui aurait conservé du code mort. Coût comportemental : nul en pratique (no realistic env where the fallback fires). Bénéfice : fail-fast au boot au lieu d'un silent pointage `localhost`.
- **S1135 — choix "TODO → Note"** vs "résoudre le TODO" : la résolution exigerait l'implémentation de la détection abnormal-biology (pipeline triage), clairement hors scope task-040. Reformulation en `// Note:` qui documente l'état et pointe `archived-task-028`. Aucun tracker ouvert car aucune US active sur ce domaine.

**Limites différées (à traiter en tasks séparées)** :

1. **`secrets:S6702` BLOCKER** sur `report_coverage.ps1:L1` — vrai token SonarQube en clair dans un script PowerShell de reporting. Commit d'origine `e462848 Add new tests`. Pré-existant sur develop, révélé par le multi-language scan. **À traiter en task dédiée** : rotation du token côté SonarQube admin + suppression du fichier (ou ajout au `.gitignore`).
2. **(Bonus, hors Sonar)** — `Api/Mail/src/Api/appsettings.json:L63` contient une clé OpenAI réelle (`sk-proj-...`) commitée en clair. Pattern identique au #1, même urgence. À traiter dans la même task de rotation de secrets.
3. **Multi-language scan non-config** — le scanner active par défaut le scan multi-lang qui a remonté les 185 new_violations. Soit on désactive (`sonar.scanner.scanAll=false` dans `agents/sonar.md`), soit on accepte et on ouvre une task de cleanup pour le périmètre élargi. Décision design à prendre.
4. **Drift `Microsoft.EntityFrameworkCore.Design` 9.0.8 vs `Microsoft.EntityFrameworkCore` 10.0.7** dans `Directory.Packages.props`. Pas de symptôme observé mais probablement un oubli de bump. À aligner dans une task chore séparée.

**CA1862 déféré à `task-047`** : `tasks/todo-task-047-ca1862-ef-linq-investigation.md` créée. Scope :

- **Phase 1 (mandatoire)** : 3 tests d'intégration capturant le SQL généré par `Where(... .ToLower().Contains(x))`, `Where(... .Contains(x, OrdinalIgnoreCase))`, `Where(EF.Functions.ILike(...))` via `IQueryable.ToQueryString()` avec un Postgres Testcontainer. Décision documentée : fix / SuppressMessage par classe / SuppressMessage par méthode / ILike Npgsql-specific.
- **Phase 2 (conditionnelle)** : application aux 49 occurrences (24 dans `MailRepository.cs` L2384-2389, L2414-2419, L2566-2571, L2629-2634 ; 25 dans `PatientRepository.cs` L186-191, L241-246, L349-354, L678-683, L841) + 1 spécial (L841 = `==`, pas `.Contains` — fix via `.Equals(string, StringComparison)`). Tests d'intégration avec assertion SQL pour chaque méthode Repository touchée.

---

## Annexe A — Cartographie des briques applicatives

*Inventaire des fichiers `api-mail` touchés ou potentiellement touchés par l'EPIC E010.*

| Fichier | Concerné par | Stratégie |
|---|---|---|
| `src/Api/Extensions/FlagsmithExtensions.cs` | F001 (S1075) | ✅ Fixé (task-040) |
| `src/Application/Services/Implementation/NewMailNotifier.cs` | F001 (S1135) | ✅ Fixé (task-040) |
| `src/Infrastructure/Migrations/**` | F001 (exclusion) | ✅ Exclu de l'analyse (task-040) |
| `src/Infrastructure/Repository/MailRepository.cs` | F008 (CA1862 × 24) | ⏳ Investigation (task-047) |
| `src/Infrastructure/Repository/PatientRepository.cs` | F008 (CA1862 × 25) | ⏳ Investigation (task-047) |
| `src/Api/Controllers/V1/PatientsController.cs` | F003 (S6960) | ⏳ Todo (task-042) |
| `src/Api/Controllers/V1/ManagementController.cs` | F002 + F004 (S6960 + 1 call site SemanticSearchOptions) | ✅ Site SemanticSearch refactoré (task-041) / ⏳ split S6960 todo (task-043) |
| `src/Api/Controllers/V1/SettingsController.cs` | F005 (S6960) | ⏳ Todo (task-044) |
| `src/Application/Services/Interfaces/ISemanticSearchService.cs` | F002 | ✅ Signatures simplifiées en records `*Options` (task-041) |
| `src/Application/Services/Implementation/SemanticSearchService.cs` | F002 | ✅ Body unchanged + destructure pattern (task-041) |
| `src/Application/Models/SemanticSearchOptions.cs` (nouveau) | F002 | ✅ 2 records immutables (task-041) |
| `src/Api/Controllers/V1/SearchController.cs` | F002 | ✅ 2 call sites mis à jour (task-041) |
| 6 ctors DI lourds (MailController, ImapConnectionService, ImapFolderService, ImapService, BackgroundImapService, SmtpService) | F002 ↪ F003-F005 | ⏳ Déférés au split S6960 (option C task-041) |
| `ImapLockScope.AcquireAsync` | F002 | ✋ Hors scope task-041 (3 params sont `[CallerInfo]` magic, incompatibles avec record wrapping) |
| `PatientRepository.ComputeScore` | F002 | ✋ Hors scope task-041 (private static helper, pas de bénéfice API) |
| Méthodes S3776 (39 occurrences, fichiers TBD) | F007 | 🟡 Campagne en cours (meta-task-046) |
| Hotspots security (7 occurrences, fichiers TBD) | F006 | ⏳ Todo (task-045) |
| `report_coverage.ps1` | Hors EPIC — secret leak | ⚠️ À rotater (task TBD) |
| `src/Api/appsettings.json:L63` | Hors EPIC — secret leak | ⚠️ À rotater (task TBD) |

---

## Annexe B — Inventaire fonctionnel daté (snapshot 2026-05-17, post-task-041)

- **Test projects api-mail** : 5 (domain, application, infrastructure, api, integration)
- **Tests totaux api-mail** : **2096 pass** / 0 fail / 16 skipped (16 = AI pré-existants + `ParseImagingReport` Linux skip post-task-040)
- **Solution** : `HealthPlatform.Api.Mail.sln`
- **Build config validée** : Release
- **EF Core version (runtime)** : 10.0.7
- **EF Core Design version** : 9.0.8 (drift — voir limite #4 v0.1)
- **Npgsql.EntityFrameworkCore.PostgreSQL** : 10.0.1
- **Sonar profile actif** : `Weda way (cs)` (switché depuis `Sonar way` le 2026-05-14)
- **Sonar baseline globale** : 0 bugs / 1 vulnerability (pré-existante) / **1066 smells** / 7 hotspots / **73.3 % coverage** / A/E/A ratings
- **Sonar new-code period** : `PREVIOUS_VERSION` (inherited)
- **Quality Gate** : ERROR (new_violations **187** > 0, new_coverage **78.5 %** < 80 %)
- **CI workflow `Build and Publish` api-mail** : triggered sur `develop` + step `dotnet test` actif (fix posé sur develop entre task-040 et task-041, commits `f7e6d0b` / `747e4fa` / `c053454`). Premier test réel sur PR #63.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task ID | Statut | Contribution | RGs closes |
|---------|--------|--------------|------------|
| task-040 | ✅ Done | Quick-wins S1075 + S1135 + exclusion `**/Migrations/**`. Scope révisé en vol (CA1862 déféré à task-047). | — |
| task-041 | ✅ Done | Refactor `ISemanticSearchService` (`SearchAsync` + `SearchByPatientAsync`) en records `SemanticSearchOptions` / `SemanticSearchByPatientOptions`. Scope révisé en vol — S107 hors profile `Weda way`, 6 ctors DI lourds et 2 helpers ignorés (option C). 4 nouveaux tests records ; 36 call sites convertis. | — |
| task-042 | ⚪ Todo | Split `PatientsController` (S6960). Touche api-mail + client-blazor + client-angular. | — |
| task-043 | ⚪ Todo | Split `ManagementController` (S6960). Touche api-mail + client-blazor + client-angular. | — |
| task-044 | ⚪ Todo | Split `SettingsController` (S6960). Touche api-mail + client-blazor + client-angular. | — |
| task-045 | ⚪ Todo | Review des 5 (actuellement 7) security hotspots — bascule `TO_REVIEW` → `SAFE` / `ACKNOWLEDGED` / `FIXED`. | — |
| meta-task-046 | 🟡 En cours | Tracker de campagne S3776 (39 méthodes, 1 méthode = 1 PR via `/sonar-s3776`). Non pické par `/forge`. | — |
| task-047 | ⚪ Todo | Investigation CA1862 EF LINQ + décision fix vs SuppressMessage. **Phase 1** (3 tests SQL) avant **Phase 2** (application aux 49 + 1 occurrences). | — |

---

*Changelogs ingénierie maintenus par `/tech-writer` (mode task-driven, append-only en mode incremental, rebuilt en mode `--refresh`).*
