# todo-task-061-patient-clinical-controllers-problemdetails.md — Migration controllers patient/clinique vers le GlobalExceptionHandler

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Migrer le **cluster patient / clinique** sur le pattern RFC 7807 de task-055 :

- `PatientsController` (~372 lignes, ~10 actions, ~19 `catch`)
- `MedicalDocumentsController` (~281 lignes, ~5 actions, ~10 `catch`)
- `BiologyAcksController` (~177 lignes, ~3 actions, ~9 `catch`)

Pour chaque controller : retirer les `try/catch` boilerplate, lever les
exceptions métier typées (`NotFoundException`/`ValidationException`/
`ConflictException`/`UnavailableException`) pour les erreurs métier, retirer
`[ExcludeFromCodeCoverage]`, couvrir chaque action par ≥ 1 test unitaire.

**Vigilance données de santé** : ces controllers manipulent des INS, des
documents médicaux et des acquittements biologiques. Le `detail` exposé au
client doit rester **générique** sur les 5xx (jamais d'INS/NIR/contenu CDA dans
le message). Les exceptions typées ne doivent pas embarquer de donnée patient
dans leur message.

api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Branches
- `api-mail` (pushed) : refactor/task-061-patient-clinical-controllers-problemdetails — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/refactor/task-061-patient-clinical-controllers-problemdetails
- `dtos-mss` (pushed, auto-included) : refactor/task-061-patient-clinical-controllers-problemdetails — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/refactor/task-061-patient-clinical-controllers-problemdetails (aucun changement de contrat attendu — branche probablement vide, pas de PR si aucun commit)

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] `try/catch` boilerplate retiré des 3 controllers
- [ ] Not-found / input invalide → exceptions métier typées (mapping par type)
- [ ] `OperationCanceledException` non ré-attrapée par action
- [ ] `[ExcludeFromCodeCoverage]` retiré des 3 controllers
- [ ] ≥ 1 test unitaire par action (happy path + ≥ 1 mode d'échec typé) pour
      chacun des 3 controllers
- [ ] Aucune string brute / `ErrorResponse` ne subsiste dans ces controllers
- [ ] **Aucune INS / NIR / contenu CDA / donnée patient** dans les `ProblemDetails`
      (vérification explicite sur le path 5xx et sur les messages d'exceptions typées)

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- `GET /api/v1/Patients/...` avec un INS inconnu → 404 `problem+json` sans INS dans le corps.
- `GET /api/v1/MedicalDocuments/{guid-inexistant}` → 404 `problem+json`.
- Forcer une erreur sur un acquittement biologie (`BiologyAcks`) → 5xx
  `problem+json` avec `traceId`, **aucun** détail clinique exposé.
- Vérifier en UI MSS que la vue patient / biologie / documents ne régresse pas.

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique de controllers existants, iso-comportement
métier. **Point de vigilance RGPD renforcé** : non-fuite de DSCP (INS, contenu
CDA, valeurs biologiques) dans les messages d'erreur. Même posture que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair (INS, NIR, contenu CDA, valeurs bio) dans les `ProblemDetails`
- [ ] Aucune donnée de santé en clair dans les logs corrélés par `traceId`
- [ ] Détail technique réservé aux logs serveur ; message client générique

## Develop log

- Repos touched : api-mail (pushed). dtos-mss : aucun changement de contrat (branche vide, pas de PR).
- DTOs published : no DTO change.
- Interop published : no interop change.
- Commits :
  - api-mail : 7ae9ef1 refactor(api): migrate patient/clinical controllers to RFC 7807 (task-061)
- Changes :
  - `PatientsController`, `MedicalDocumentsController`, `BiologyAcksController` :
    suppression des `try/catch` boilerplate + retours `500`/`499` codés en dur ;
    not-found / input invalide → exceptions métier typées (`NotFoundException` → 404,
    `ValidationException` → 400) mappées par type via le `GlobalExceptionHandler`.
  - `[ExcludeFromCodeCoverage]` retiré des 3 controllers.
  - `BiologyAckNotFoundException` / `BiologyAckBadRequestException` reparentées sur
    `NotFoundException` / `ValidationException` (mapping par type, plus aucun catch
    par action). Les deux exceptions de base ont été dé-`sealed` pour permettre la
    spécialisation. Tests `BiologyAckServiceTests` inchangés (le type concret levé
    par le service ne change pas).
  - Vigilance santé : les détails 404 n'exposent jamais l'INS (messages génériques
    "Patient not found" / "Medical document not found").
- Tests : 38 nouveaux tests unitaires (happy path + échec typé par action) pour les
  3 controllers — tous verts. `ModelState` invalide couvert (SuppressModelStateInvalidFilter=true).
- Local build : ✓ api-mail (0 warning, 0 error).
- Local test : ✓ api.tests 38/38 + suite complète verte SAUF
  `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync`
  — **échec pré-existant / flaky** (timing d'annulation IMAP sous charge parallèle de
  la suite intégration ; **passe en isolation**). Sans rapport avec task-061 (aucune
  modification IMAP).
- DOD self-check : build ✓, tests ✓, try/catch retirés ✓, exceptions typées ✓,
  OperationCanceledException centralisée ✓, [ExcludeFromCodeCoverage] retiré ✓,
  ≥1 test/action ✓, aucune string brute/ErrorResponse résiduelle ✓, non-fuite INS ✓.
- Next step : `/sonar task-061` (api-mail touché) → chaîne vers `/review`
  (`/lint-angular` skip : pas de changement angular).

## Sonar log

- Mode A (chaîné depuis /develop), branche `refactor/task-061-...`, SonarQube `healthplatform`.
- **New code introduit par task-061 — zéro dette** :
  - `new_violations` = **0** (les 6 findings introduits ont été fixés :
    S2302 ×3 → `nameof()` dans les messages `ValidationException` ;
    xUnit2032 ×3 → `Assert.IsType<T>(x, exactMatch:false)`).
  - `new_bugs` = 0, `new_vulnerabilities` = 0, `new_code_smells` = 0.
  - `new_security_hotspots_reviewed` = 100%.
  - **Couverture des fichiers task-061 = 100%** :
    `PatientsController.cs`, `MedicalDocumentsController.cs`, `BiologyAcksController.cs`
    (54 tests unitaires sur la surface task-061).
- **Quality Gate projet = ERROR** sur une **seule** condition : `new_coverage`
  = 74.6% < 80%. ⚠️ **Dette pré-existante projet, hors périmètre task-061** :
  le *new code period* SonarQube est fixé à `PREVIOUS_VERSION` (baseline du
  2026-04-27) et couvre **30 976 lignes** de tout le projet depuis avril, pas
  le diff de la task. task-061 a *amélioré* la couverture (74.2% → 74.6%) et
  ses propres fichiers sont à 100%. Cette condition ne peut pas être ramenée
  à ≥80% par une seule task de refactor de controllers — c'est de la dette
  legacy (Phase 2 best-effort, acceptée). Réf. mémoire forge :
  « new-code-period projet = baseline large ».
- Phase 2 (legacy) : non itérée (best-effort, acceptée) — le run a priorisé
  le zéro-dette sur le new code, atteint.
- Build Release : ✓. Tests : ✓ (hors 2 échecs pré-existants documentés ci-dessous).
- Échecs pré-existants (confirmés présents sur `origin/develop`, intouchés par task-061) :
  1. `UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724_WithExpectedAnonymisedFields`
     — assertion obsolète sur l'ancien schéma de nom de base (`mss_mail_user_...`)
     vs le nommage hash actuel de `UserContextInfo` (`u_..._<hash>`). Release-only.
  2. `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync`
     — flaky (timing d'annulation sous charge parallèle ; passe en isolation).
- Commits Sonar :
  - api-mail : 5b6fab5 fix(sonar/new): clear task-061 new-code findings (S2302, xUnit2032)
  - api-mail : a0415da test(sonar/new): raise task-061 new-code coverage
- Next step : pas de changement `client-angular` → skip `/lint-angular` → `/review task-061`.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/81 — label `awaiting-human-merge`
- `dtos-mss` : branche `refactor/task-061-...` vide (aucun changement de contrat) — pas de PR.

## Code Review Summary

- Verdict : **APPROVED** (autonome, pas de blocage).
- Correctness ✅ / Security & santé ✅ (aucun INS dans les ProblemDetails) /
  Architecture ✅ (pattern task-055) / Tests ✅ 54 tests / Sonar new-code ✅
  0 violation + controllers à 100% de couverture.
- Quality Gate projet RED uniquement sur `new_coverage` global (74.6%) — dette
  pré-existante baseline 2026-04-27, hors périmètre, améliorée par la PR.
- 3 échecs de tests pré-existants (middleware DB-name stale, IMAP flaky,
  MailExport PDF flaky) — confirmés sur `develop`, non liés à task-061.

## Merged

- Merged: 2026-06-09  UTC (squash, HAG human attestation via /merge --i-merged)
- api-mail :  (PR # squash-merged into develop, remote branch deleted)
- dtos-mss : no PR (branch empty — no contract change)
- develop CI run : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions?query=branch%3Adevelop
