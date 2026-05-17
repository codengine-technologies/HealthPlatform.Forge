# wip-task-032bis-fhir-mock.md — Mock FhirClient HTTP pour tester les 7 stratégies AnnuaireSante

**Repos**: api-mail
**Dependencies**: done-task-032 (archivée 2026-05-07)
**Epic**: E009

## Branches

- `api-mail` (pushed) : `feat/task-032bis-test-harness` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-032bis-test-harness
- `dtos-mss` (pushed) : `feat/task-032bis-test-harness` — branche vide (0 commit), à supprimer en cleanup au merge

> **Note** : nom de branche `-test-harness` hérité de l'US d'origine (avant découpage Option B 2026-05-07). Le contenu déposé sur la branche est désormais réduit au seul Chantier 2 — la branche reste sous son ancien nom pour préserver l'historique des commits déjà poussés (`e30472e`, `3e147b6`).

## Objectif

**Scope réduit (Option B 2026-05-07)** : livrer le harness FhirClient HTTP qui permet de tester les paths FHIR `ExecuteAsync` des 7 stratégies AnnuaireSante + les paths `SearchAsync` d'`AnnuaireSanteService`, sans hitter l'API Annuaire Santé réelle. C'est l'un des 3 chantiers initialement scopés dans `todo-task-032bis-test-harness.md` ; les 2 autres (GreenMail Testcontainers, samples CDA) ont été extraits dans des sub-tasks dédiées :

- `todo-task-032ter-greenmail-fixture.md` — Mock IMAP server (Chantier 1, mode `no-code`)
- `todo-task-032quater-cda-samples.md` — Samples CDA zip files (Chantier 3, gated sur livraison métier)

Cette US livre une **valeur self-contained** : un harness FHIR réutilisable + 22 nouveaux tests sur les 7 stratégies. Pas de promesse de seuils 80/70 globaux ici — c'est un building block.

US **technique / dette / outillage qualité** — aucun nouveau comportement métier.

## Périmètre

### Refactor production (1 fichier, ~16 LOC)

Ajout d'un ctor `internal` à `AnnuaireSanteService` acceptant directement un `FhirClient` pré-configuré + `IDistributedCache` + `ILogger`. Les tests construisent un `FhirClient(uri, FhirClientSettings, HttpMessageHandler)` (overload natif Hl7.Fhir 6.1.1) avec un handler custom. Pas de package mock externe.

Le ctor production `IOptions<FhirOptions>` est inchangé, la DI runtime continue de l'utiliser.

### Test harness (4 nouveaux fichiers, ~600 LOC)

- `FhirMockHandler.cs` — `HttpMessageHandler` minimaliste qui hand-off chaque requête à un responder + record la liste pour assertion.
- `FhirBundleFactory.cs` — JSON FHIR R4 hand-crafted (4 shapes : empty Bundle, OperationOutcome, Practitioner seul, Practitioner + PractitionerRole).
- `AnnuaireSanteStrategyExecuteTests.cs` — happy + empty + erreur (FhirOperationException ou catch interne) sur **les 7 stratégies** (Rpps / Name / NameWithLocation / Specialty / Location / Organization / Combined). 14 tests.
- `AnnuaireSanteServiceSearchAsyncTests.cs` — end-to-end `SearchAsync` via le ctor `internal` : succès, vide, FhirError → `InvalidOperationException`, ArgumentException wrap, sanity mock + 3 ctor null. 8 tests.

### Hors scope (sub-tasks dédiées)

- **Mock IMAP server / GreenMail Testcontainers** — `task-032ter-greenmail-fixture` (mode `no-code` — `MailClientSessionManager` est concrete et demande extraction d'interface, décision structurante).
- **Samples CDA zip files** — `task-032quater-cda-samples` (gated sur livraison métier de 5 zips IHE-XDM anonymisés).
- **AiTextService** — non couvert (wrapper `Microsoft.SemanticKernel.Kernel`, mocking non-trivial). Reste exclu via `[ExcludeFromCodeCoverage]`.

## Cibles chiffrées

À l'issue de cette US (scope FhirClient seul) :

- **+22 tests** sur la suite api-mail (vs baseline post-task-032)
- **0 régression** sur les tests existants
- **0 nouveau warning** Sonar introduit
- **Build vert** Release sur `api-mail`
- **Aucune `[ExcludeFromCodeCoverage]` retirée** — la liste d'exclusions task-032 ciblait IMAP/X.509/AI/CDA/PDF, pas les stratégies AnnuaireSante. Cette US n'attaque pas les exclusions ; c'est le rôle de `task-032ter` + `task-032quater`.

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 failure)
- [ ] Suite api-mail compte +22 tests vs baseline post-task-032 (1896 → 1918)
- [ ] Ctor `internal AnnuaireSanteService(FhirClient, IDistributedCache, ILogger<AnnuaireSanteService>)` ajouté, validé par 3 ctor-null tests
- [ ] `FhirMockHandler` et `FhirBundleFactory` présents dans `tests/mss.mail.application.tests/Services/AnnuaireSante/`
- [ ] 7 stratégies AnnuaireSante × `ExecuteAsync` testées (au moins happy + empty path chacune)
- [ ] `AnnuaireSanteService.SearchAsync` testée pour : RPPS query happy, empty result, FhirError wrap, ArgumentException wrap (validation)
- [ ] Aucun test sans assertion (chaque test contient ≥ 1 `Assert.*`)
- [ ] Body de PR contient le récapitulatif des fichiers ajoutés + le delta de tests
- [ ] Aucune dégradation des KPIs Sonar (code_smells / hotspots / ratings)

## KPIs (à publier dans le body de PR — repris par `/tech-writer` pour E009)

```
### Mock FhirClient harness — task-032bis-fhir-mock

| Métrique                                | Avant (post-task-032) | Après (post-task-032bis-fhir-mock) |
|-----------------------------------------|-----------------------|------------------------------------|
| Tests api-mail (passed)                 |        1 896          |              1 918                 |
| Δ tests                                 |          —            |              +22                   |
| Tests AnnuaireSante stratégies          |       Mode/CanHandle  |     +14 ExecuteAsync               |
| Tests AnnuaireSanteService.SearchAsync  |        validation only|     +8 (incl. ctor null)           |
| [ExcludeFromCodeCoverage] retirées      |          —            |              0                     |
| Sonar code_smells (delta)               |          —            |          neutre attendu            |
| Sonar ratings A/A/A                     |        ✓              |              ✓                     |
```

## Manual Test Plan

Aucun comportement métier modifié — la validation est entièrement automatique :

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreur
3. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release` → 1918 passed / 21 skipped / 0 failed
4. Smoke run : `dotnet run --project src/mss.mail.api` puis `GET /api/health` → 200 (preuve que le ctor `internal` ajouté ne casse pas la résolution DI du ctor production).
5. Smoke recherche AnnuaireSante (si l'environnement local a la config `FhirOptions:BaseUrl + ApiKey`) : appeler `/api/v1/directory/search?lastName=Dupont` → 200 et résultats — preuve que le ctor production reste actif en runtime.

## Notes

- Cette US est issue du découpage **Option B (2026-05-07)** de la US d'origine `task-032bis-test-harness`. Voir le develop log ci-dessous pour le contexte initial 3-chantiers.
- `task-032ter` (GreenMail) et `task-032quater` (CDA samples) prennent le relais sur les 2 autres chantiers initialement scopés.
- `task-033` (cleanup Sonar massif) ne dépend plus strictement de cette US — task-033 peut démarrer avec le filet task-032 actuel + le harness FhirClient livré ici. La couverture IMAP/CDA arrivera plus tard via task-032ter / task-032quater.

## Develop log

### Run 1 — 2026-05-07 (livraison Chantier 2 — scope final post-Option-B)

- **Repos touchés** : `api-mail`. `dtos-mss` non utilisé (branche vide).
- **DTOs publiés** : aucun.
- **Interop publié** : aucun.
- **Commits** :
  - `e30472e` feat(application): expose internal AnnuaireSanteService ctor for FhirClient injection
  - `3e147b6` test(application): cover 7 AnnuaireSante strategies × ExecuteAsync via FhirMockHandler
- **Build / tests** : ✓ tous projets verts en Release. **Suite api-mail 1918 passed** (was 1896) / 21 skipped / 0 fail. **+22 nouveaux tests**.

### Livré

- Refactor production : ctor `internal` `AnnuaireSanteService(FhirClient, IDistributedCache, ILogger<AnnuaireSanteService>)`. Production ctor `IOptions<FhirOptions>` inchangé.
- Test infrastructure (4 fichiers, ~600 LOC) : `FhirMockHandler`, `FhirBundleFactory`, `AnnuaireSanteStrategyExecuteTests` (14 tests), `AnnuaireSanteServiceSearchAsyncTests` (8 tests).

### DOD self-check (scope final)

| Item | État | Note |
|---|---|---|
| Build passe | ✓ | 0 erreur, Release |
| Tests passent | ✓ | 1918 / 0 fail (+22 vs baseline) |
| Ctor `internal` présent | ✓ | + 3 ctor-null tests |
| `FhirMockHandler` + `FhirBundleFactory` | ✓ | sous `tests/.../AnnuaireSante/` |
| 7 stratégies × ExecuteAsync testées | ✓ | 14 tests AnnuaireSanteStrategyExecuteTests |
| `SearchAsync` paths testés | ✓ | 8 tests AnnuaireSanteServiceSearchAsyncTests |
| Pas de test sans assertion | ✓ | grep manuel — chaque test contient ≥ 1 Assert.* |
| Sonar pas dégradé | (à valider /sonar) | Chantier 2 produit du code clean — peu de surface Sonar |

DOD du scope final : **✓ atteinte**. Hand-off `/sonar` → `/review` autorisé.

### Historique — découpage Option B (2026-05-07)

US d'origine `task-032bis-test-harness` (3 chantiers : Mock IMAP / Mock FhirClient / Samples CDA) jugée trop large pour `/develop` autonome après tentative. Découpée en 3 :
- task-032bis-fhir-mock (cette US — Chantier 2 livré autonomement)
- task-032ter-greenmail-fixture (Chantier 1 — mode `no-code`)
- task-032quater-cda-samples (Chantier 3 — gated métier)

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/46 — label `awaiting-human-merge`
- `dtos-mss` : pas de PR (branche `feat/task-032bis-test-harness` créée par /start mais 0 commit — aucun changement DTO requis ; à supprimer en cleanup au merge)

## Code Review Summary

Verdict : **APPROVED** (6 fichiers revus, +566/-4 LOC, 1 suggestion non bloquante, 0 blocking).

- ✅ Refactor production minimal : ctor `internal` `AnnuaireSanteService(FhirClient, IDistributedCache, ILogger)` avec 3 null-checks `ArgumentNullException`. Le ctor production `IOptions<FhirOptions>` est inchangé — la DI runtime continue de l'utiliser.
- ✅ Disambiguation `(IOptions<FhirOptions>)null!` cast dans le test pré-existant `ConstructorWithNullOptionsShouldThrowArgumentNullException` (changement minimal pour préserver l'intent).
- ✅ Test infrastructure : `FhirMockHandler` + `FhirBundleFactory` (JSON hand-crafted, pas de dépendance au sérialiseur Hl7.Fhir → robuste aux churns d'API).
- ✅ 22 nouveaux tests AAA, naming `Method_Context_ExpectedResult`, ≥ 1 `Assert.*` par test (38 assertions au total).
- ⚠️ Suggestion non-bloquante : edge case OperationOutcome severity=warning avec status 200 OK non couvert ; à ajouter en follow-up si Sonar/coverage le réclament.

HAG (règle 10) : test manuel humain selon `## Manual Test Plan`, puis `gh pr merge 46 --squash` ou via UI GitHub.

## Merged

- **2026-05-07** — PR #46 squash-mergée par le humain via `/merge task-032bis-fhir-mock --i-tested`.
- `api-mail` : squash sha **`a863e39`** sur `develop` — PR #46 closed, remote branch `feat/task-032bis-test-harness` supprimée (--delete-branch), local préservée pour inspection rétroactive.
- `dtos-mss` : branche `feat/task-032bis-test-harness` (vide, 0 commit) supprimée du remote en cleanup.
- CI `develop` (api-mail) : workflow `Build and Publish` n'auto-trigger pas sur push develop (cf. dernier run 2026-04-15) — pas de régression visible. Si un run futur échoue, voir `gh run list --branch develop`.
- Sub-tasks restantes du découpage Option B :
  - `todo-task-032ter-greenmail-fixture.md` — Chantier 1 (Mock IMAP), mode `no-code` recommandé
  - `todo-task-032quater-cda-samples.md` — Chantier 3 (Samples CDA), gated sur livraison métier
