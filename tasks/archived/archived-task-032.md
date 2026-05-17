# wip-task-032.md — Augmenter la couverture TU api-mail (filet de sécurité avant cleanup Sonar)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009

## Branches

- `api-mail` (pushed) : `feat/task-032-coverage-tu-api-mail` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-032-coverage-tu-api-mail
- `dtos-mss` (pushed) : `feat/task-032-coverage-tu-api-mail` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-032-coverage-tu-api-mail

> **Note initiale** : la branche `api-mail` embarque dès le `/start` **6 fichiers WIP non-task** (~300 LOC : `MailEventsController`, `NotificationsController`, `RequestHelper`, `UserContextEnricherMiddleware`, + 2 fichiers de tests associés) qui traînaient sur `develop` en working-tree dirty. Choix humain au /start ("conserve et continu") — la PR finale contiendra donc à la fois cette WIP préexistante et le travail coverage de task-032.

## Objectif

Augmenter de manière significative la couverture des tests unitaires du
backend `api-mail` afin de constituer un **filet de sécurité** robuste
**avant** d'engager la US sœur de cleanup Sonar massif (`task-033`). Sans
cette couverture, on ne peut pas affirmer "0 régression" sur 20 itérations
de refactor automatisé.

US purement **technique / dette** — aucun nouveau comportement métier,
uniquement augmentation de coverage. Rattachée à E009 via une nouvelle
section "KPIs Sonar & Qualité" maintenue par `/tech-writer`.

## Périmètre

Couverture mesurée via :

```bash
dotnet test HealthPlatform.Api.Mail.sln \
  --collect:"XPlat Code Coverage" \
  --settings:codecoverage.runsettings
```

Le périmètre est **déjà figé** dans `codecoverage.runsettings` (lignes 19-24)
et porte sur les assemblies de production :

- `mss.mail.application`
- `mss.mail.infrastructure`
- `mss.mail.api`
- `mss.mail.domain`

Sont exclus (déjà configurés) : projets de tests, `Migrations/`, code décoré
`[ExcludeFromCodeCoverage]`, code généré (`*.Designer.cs`).

## Cibles chiffrées (binaires — vérifiées par `/review`)

- **Line coverage ≥ 70 %** (toutes assemblies du périmètre cumulées, pondéré par LOC, **post-exclusions**)
- **Branch coverage ≥ 55 %** (toutes assemblies du périmètre cumulées, pondéré par LOC, **post-exclusions**)

> **Cibles ajustées par décision PO 2026-05-06 — Option A4** suite au fork
> report (cf. `questions/task-032.md`). Les seuils initiaux 80 % / 70 %
> seront atteints après livraison de `task-032bis-test-harness` qui retirera
> les 9 exclusions posées ici.

## Stratégie d'implémentation

### Conventions de tests

- xUnit + NSubstitute, **un comportement par test**, nom
  `Method_Context_ExpectedResult`.
- Chaque test contient **≥ 1 `Assert.*`** non trivial. Pas de test
  "tautologique" qui se contente d'instancier sans vérifier.
- Pour les repositories dépendant de Postgres → utiliser
  `PostgreSqlFixture` / Testcontainers (déjà en place dans
  `mss.mail.integration.tests`) plutôt que de mocker `DbContext`.

### Mesure initiale (avant la boucle)

1. Lancer la suite tests avec coverage cobertura, parser le rapport, sauvegarder :
   - Line + branch coverage globaux et par assembly (snapshot "avant")
   - Liste des classes < 50 % de couverture, triées par LOC produit (poids
     pondéré dans le total)

### Boucle d'exécution — 30 itérations max

À chaque itération :

1. Sélectionner la classe sous-couverte avec le **plus gros impact pondéré**
   sur le total (priorité : handlers MediatR, services applicatifs, services
   domaine, validators, mappers, parsers — CDA, LOINC, …).
2. Ajouter un batch de tests xUnit + NSubstitute couvrant les branches
   manquantes (cf. conventions ci-dessus).
3. Si la classe nécessite un refactor de testabilité (passer une dépendance
   par DI, extraire une méthode privée en `internal` / `protected internal`) :
   appliquer dans la limite **5 fichiers production cumulés sur l'US**. Au-delà,
   écrire `questions/task-032.md` et stopper la boucle.
4. Si la classe est matériellement non testable (dépendance statique non
   injectable, classe `sealed` sans abstraction, IO réseau sans harness) : annoter
   `[ExcludeFromCodeCoverage]` avec `// reason: ...`. Limite cumulée
   **10 classes** (relâché de 5 → 10 par décision PO 2026-05-06, Option A
   du fork report — cf. section "Exclusions pré-approuvées"). Au-delà, idem `questions/`.
5. `dotnet build` → si rouge, rollback le batch et investiguer.
6. `dotnet test` → si rouge, rollback le batch et investiguer.
7. Re-mesurer la coverage. Commit `test(coverage): batch N — line XX % → YY %`.

### Critères d'arrêt (premier vrai gagne)

- ✅ **Succès** : `line ≥ 70 %` ET `branch ≥ 55 %` sur le total pondéré
  post-exclusions (seuils ajustés Option A4 — cf. ## Cibles chiffrées).
  Boucle terminée, on passe à l'ouverture de PR.
- ❌ **Échec — plafond itérations** : 30 atteintes sans avoir franchi les
  seuils → écrire `questions/task-032.md` avec snapshot des KPIs (avant /
  après) et liste des classes restantes problématiques (couverture %, LOC,
  pourquoi pas testées). **Ne pas ouvrir de PR partielle** — la US-sœur
  task-033 dépend du seuil atteint.
- ❌ **Échec — plafond exclusions** : > 10 classes `[ExcludeFromCodeCoverage]`
  cumulées (cap relâché par décision PO Option A) OU > 5 fichiers production
  modifiés cumulés → idem `questions/`, pas de PR.
- ❌ **Échec — tooling** : coverlet / cobertura / scanner KO pendant la
  boucle → idem `questions/`, pas de PR.

## Exclusions pré-approuvées (décision PO 2026-05-06 — Option A)

Suite au fork report `/develop` du 2026-05-06 (3 itérations livrées : 59.3 % →
62.4 % line, 46.5 % → 49.1 % branch), le PO a relâché le cap d'exclusions
de 5 → 10 et pré-approuvé l'annotation `[ExcludeFromCodeCoverage]` sur les
9 classes ci-dessous. Elles sont **intractables sans harness manquant**, qui
fait l'objet de la US-suivante `task-032bis-test-harness`.

Annoter `[ExcludeFromCodeCoverage]` (avec `// reason: …`) sur :

1. `application.Services.Implementation.ImapService` — IMAP IO sans serveur mock (1 233 LOC)
2. `application.Services.Implementation.BackgroundImapService` — hosted IMAP, idem (415 LOC)
3. `application.Services.Implementation.ImapFolderService` — IMAP IO (390 LOC)
4. `application.Services.Implementation.ImapConnectionService` — IMAP IO (232 LOC)
5. `application.Services.Implementation.OcspValidationService` — X.509 chain validation (158 LOC)
6. `application.Services.Implementation.CrlValidationService` — X.509 chain validation (152 LOC)
7. `application.Services.Implementation.AiTextService` — wrapper OpenAI HTTP (142 LOC)
8. `application.Services.Implementation.CdaParsingService` — XML/zip parsing sans samples (382 LOC)
9. `application.Services.Implementation.MarkdownPdfRenderer` — PdfPig output (339 LOC)

Total : ~3 443 LOC retirés du dénominateur ; sur 17 437 - 3 443 = 13 994 lignes
restantes, on est à ~78 % avec les 10 881 lignes déjà couvertes. Il faut
ensuite **ajouter ~310 lignes couvertes via 2-3 itérations de tests EF Core repos**
(`MailRepository`, `PatientRepository`, `SemanticSearchRepository`, `BiologyRepository`,
`BaseRepository`) pour franchir 80 %.

`task-032bis-test-harness` (US suivante) retirera ces exclusions une fois
le harness disponible (GreenMail + FhirClient HTTP mock + samples CDA).

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 failure)
- [ ] Line coverage globale ≥ 70 % (cobertura, pondérée par LOC, post-exclusions) — seuil ajusté Option A4
- [ ] Branch coverage globale ≥ 55 % (cobertura, pondérée par LOC, post-exclusions) — seuil ajusté Option A4
- [ ] Boucle exécutée jusqu'à atteinte des seuils (≤ 30 itérations) ; si
      plafond atteint sans succès, US en `questions/task-032.md` et **pas de PR**
- [ ] Critère d'arrêt documenté dans le body PR (succès | plafond itérations |
      plafond exclusions | tooling)
- [ ] Aucun test sans assertion (chaque test contient ≥ 1 `Assert.*`)
- [ ] Classes annotées `[ExcludeFromCodeCoverage]` ≤ **10** (cap relâché PO
      Option A), chacune avec commentaire `// reason: ...`
- [ ] Les 9 classes pré-approuvées (cf. ## Exclusions pré-approuvées) sont
      effectivement annotées
- [ ] Fichiers de production modifiés pour testabilité ≤ 5, listés dans le body PR
- [ ] Body de PR contient le bloc KPIs (cf. ci-dessous)

## KPIs (à publier dans le body de PR — repris par `/tech-writer` pour E009)

```
### Couverture TU api-mail — task-032

| Assembly                | Line avant | Line après | Branch avant | Branch après |
|-------------------------|------------|------------|--------------|--------------|
| mss.mail.application    |    XX %    |    XX %    |     XX %     |     XX %     |
| mss.mail.infrastructure |    XX %    |    XX %    |     XX %     |     XX %     |
| mss.mail.api            |    XX %    |    XX %    |     XX %     |     XX %     |
| mss.mail.domain         |    XX %    |    XX %    |     XX %     |     XX %     |
| **Total pondéré (LOC)** |    XX %    |  ≥ 70 %    |     XX %     |   ≥ 55 %     |

- Tests ajoutés : NN
- Classes annotées `[ExcludeFromCodeCoverage]` (avec raison) : NN / 10
- Fichiers production modifiés (testabilité) : NN / 5
- Durée totale de la suite tests (post) : NNs
```

## Manual Test Plan

Aucun comportement métier modifié — la validation est entièrement automatique :

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreur
3. `dotnet test HealthPlatform.Api.Mail.sln --collect:"XPlat Code Coverage" --settings:codecoverage.runsettings`
4. Vérifier le rapport `TestResults/*/coverage.cobertura.xml` (ou via
   `reportgenerator`) : `line-rate ≥ 0.70` et `branch-rate ≥ 0.55` sur le
   total pondéré post-exclusions (seuils Option A4).
5. Smoke run : `dotnet run --project src/mss.mail.api` puis `GET /api/health`
   doit répondre 200 — preuve que les modifs testabilité n'ont rien cassé.

## Notes

- US-sœur **`task-033`** (cleanup Sonar massif) dépend explicitement de
  `done-task-032` car elle utilise cette suite de tests étendue comme
  **oracle de non-régression** pendant 20 itérations de refactor
  automatisé.
- S3776 (cognitive complexity) **n'est pas traité ici** — il reste réservé
  à `/sonar-s3776` (1 méthode = 1 PR avec characterization tests).

## Develop log

### Run 1 — 2026-05-06 (3 batches initiaux)

- Repos touchés : `api-mail`
- Tests ajoutés : 106
- Commits :
  - `ee4ada5` test(coverage): batch 1 — EmailActionsPlugin + AnnuaireSante strategies (Mode/CanHandle) + DraftCacheRepository (71 tests)
  - `b1de02d` test(coverage): batch 2 — FhirBundleParser additional + EmailEmbeddingService functional (24 tests)
  - `5824e3c` test(coverage): batch 3 — AnnuaireSanteService cache + validation paths (11 tests)
- Coverage : line 59.3 % → 62.4 %, branch 46.5 % → 49.1 %
- Stoppé volontairement avant les seuils 80/70 — fork report écrit dans `questions/task-032.md`

### Run 2 — 2026-05-06 (Option A appliquée puis A4)

- Décision PO 2026-05-06 :
  - **Option A** : relâcher cap exclusions 5 → 10, annoter 9 classes pré-approuvées (cf. ## Exclusions pré-approuvées)
  - **Option A4** : abaisser seuils DOD 80/70 → 70/55 vu que post-exclusions on retire aussi des lignes couvertes
- Commits :
  - `6e19ca5` chore(coverage): exclude 9 IO/IMAP/X.509/AI/CDA/PDF classes (line 62.4 % → 69.6 %, branch 49.1 % → 57.2 % sur denom réduit 13 994 lignes / 4 674 branches)
  - `b278953` test(coverage): batch 4 — FolderRepository (DeleteByPath, Reconcile, Rename) + AuditTraceRepository complet (Add, GetById, GetTraces avec tous filtres + sort + pagination + truncate) — 25 tests pour franchir le seuil
- Coverage finale : **line 70.2 %, branch 58.0 %** (post-exclusions, denom 13 994 / 4 674)
- Caps utilisés : **9 / 10** `[ExcludeFromCodeCoverage]`, **0 / 5** fichiers production modifiés pour testabilité
- Build / tests verts : ✓ tous projets
- DOD self-check : line ≥ 70 % ✓, branch ≥ 55 % ✓, 9 exclusions documentées ✓, body PR à compléter au /review
- Next step : `/sonar` (api-mail), puis `/review`, puis `/tech-writer`. `task-032bis-test-harness` (créée en `todo-`) reprendra le harness pour viser 80/70 vrais sans exclusions.

## Sonar log

### Run — 2026-05-07 (iter 1 / 5, best-effort acceptance)

Mode A chaîné depuis `/develop`. Branche `feat/task-032-coverage-tu-api-mail`
réutilisée (pas de chore branch). Baseline Sonar capturée par re-analyse de la
branche avant fixes (sha `b278953`), pas l'état `develop`.

| Métrique | Baseline branche | Après iter 1 | Δ |
|---|---|---|---|
| code_smells | 798 | **790** | -8 |
| security_hotspots | 10 | **6** | -4 (-40 %) |
| sqale_index | 644 min | 626 min | -18 min |
| line_coverage | 69.3 % | 69.3 % | 0 |
| branch_coverage | 57.4 % | 57.4 % | 0 |
| coverage (overall) | 65.9 % | 65.9 % | 0 |
| reliability_rating | A | A | — |
| security_rating | A | A | — |
| sqale_rating | A | A | — |
| bugs / vulnerabilities | 0 / 0 | 0 / 0 | — |

Cibles long terme du playbook (`bugs=0`, `vulnerabilities=0`, `sqale_rating=A`,
`coverage>=95`) : trois sur quatre déjà atteints, coverage hors portée d'un
run `/sonar` (et hors scope — c'est le rôle de task-032 / task-032bis).

### Iter 1 — 6 règles, 9 issues fixées, 7 fichiers

| Règle | # | Fichiers | Type |
|---|---|---|---|
| S6444 (Regex sans timeout) | 4 | AnnuaireSanteService, MailExportService, MailCancellationService | hotspot MEDIUM |
| S4136 (overloads adjacents) | 1 (couvre 2 issues) | MailCancellationService | refactor pur |
| S6608 (indexer vs First) | 1 | MailController | refactor pur |
| S1144 (champ privé inutilisé) | 1 | ManagementController | suppression |
| S4487 (champ privé non lu) | 1 | SearchController | suppression |
| S1192 (constante littérale) | 1 | UserContextEnricherMiddleware | refactor pur |

Commits (push origin `feat/task-032-coverage-tu-api-mail`) :
- `69464b2` fix(sonar): resolve iter-1 batch — S6444 (4) + S4136 (1)
- `e57f55e` fix(sonar): resolve 1 occurrence of S6608 — use indexer instead of First()
- `0d76c45` fix(sonar): resolve 1 occurrence of S1144 — remove unused private field
- `3eb599b` fix(sonar): resolve 1 occurrence of S4487 — remove unread private field
- `c74a4d8` fix(sonar): resolve 1 occurrence of S1192 — extract repeated literal

### Règles écartées de ce run (justification)

- **csharpsquid:S3776** (38) — blacklist (`/sonar-s3776` dédié, 1 méthode = 1 PR)
- **external_roslyn:CA1873** (623) — refactor structurel (LoggerMessage source generator)
  trop lourd pour un batch ; touche 87 fichiers dont plusieurs `[ExcludeFromCodeCoverage]`.
  À blacklister par décision humaine ou à traiter en US dédiée.
- **external_roslyn:CA1862** (30) — toutes dans `MailRepository` / `PatientRepository`
  EF Core LINQ-to-SQL. Remplacer `.ToLower().Contains(s)` par
  `.Contains(s, StringComparison.OrdinalIgnoreCase)` casse la traduction
  PostgreSQL — risque haut sans tests d'intégration ciblés.
- **csharpsquid:S125** (3) — false positives : commentaires `task-XXX` /
  défense-en-profondeur, pas du code commenté.
- **csharpsquid:S6960** (3) — découpage de controller, décision de design.
- **csharpsquid:S107** (9) — trop de paramètres, signatures publiques (risque API).
- **csharpsquid:S1192** (Migrations) — fichier `20240101_SetupMigration.cs` ne se
  modifie pas après-coup (historique EF Core).
- **csharpsquid:S6664 / external_roslyn:SYSLIB1045** — refactors lourds
  (LoggerMessage / regex source generator).

### Critère d'arrêt

`issueDeltaPct = 12 / 808 = 1.5 %` < seuil 10 %, ratings inchangés (déjà A).
Stop iter 1 par règle progression 3.9 + best-effort acceptance (autonomous
inversion 2026-04-27). Restent **790 smells + 6 hotspots** acceptés en l'état,
hand-off à `/review`. Un futur `/sonar-s3776` ciblé sur les 38 S3776 traitera
la dette de complexité cognitive, et la blacklist mérite un ticket pour
ajouter CA1873 (623 occurrences sans valeur sans refactor LoggerMessage).

- Build / tests verts ✓ (1896 passés / 21 skipped / 0 fail, mêmes chiffres
  que post-`/develop` — aucune régression introduite par les 9 fixes).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/44 — label `awaiting-human-merge`
- `dtos-mss` : pas de PR (branche `feat/task-032-coverage-tu-api-mail` créée par /start mais 0 commit — aucun changement DTO requis par la US)

## Code Review Summary

Verdict : **APPROVED** (29 fichiers revus, 1 suggestion non bloquante, 0 blocking).

- ✅ Test additions (~2000 LOC, 106 tests) : conventions xUnit + NSubstitute, AAA, naming `Method_Context_ExpectedResult`, ≥ 1 `Assert.*` par test
- ✅ 9 annotations `[ExcludeFromCodeCoverage]` (sha `6e19ca5`) — chaque classe avec `// reason: ...`, scope intractable sans harness (cf. task-032bis)
- ✅ WIP pre-existante préservée au /start (mssEmail unique source pour SSE/notifications + defense-in-depth Client-Email check dans RequestHelper) — security hardening cohérent
- ✅ Sonar iter-1 (5 commits, 9 issues, 6 règles) — pure refactor mécanique, build + tests verts maintenus à 1896/0 fail
- ⚠️ Suggestion non bloquante : la WIP pre-existante (~300 LOC : controllers SSE + RequestHelper + middleware + tests associés) sort du scope strict task-032. L'humain peut la juger lors du test manuel ; si elle nécessite un découplage, le faire post-merge avec un commit séparé sur develop.

HAG (règle 10) : test manuel humain selon ## Manual Test Plan, puis `gh pr merge 44 --squash` ou via UI GitHub.

## Merged

- **2026-05-07** — PR #44 squash-mergée par le humain via `/merge task-032 --i-tested`.
- `api-mail` : squash sha **`21ce9b0`** sur `develop` — PR #44 closed, remote branch `feat/task-032-coverage-tu-api-mail` supprimée (--delete-branch), local préservée pour inspection rétroactive.
- `dtos-mss` : branche `feat/task-032-coverage-tu-api-mail` (vide, 0 commit) supprimée du remote en cleanup. Pas de PR fusionnée car aucun changement DTO requis.
- CI `develop` (api-mail) : ✓ green — run `Build and Publish` https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/24478732670
- Tasks suivantes débloquées : `task-032bis-test-harness` (todo), `task-033` (todo, dépend de cette task mergée comme oracle de non-régression).
