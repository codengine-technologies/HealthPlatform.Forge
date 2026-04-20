# /sonar-s3776 — Cognitive-complexity cleanup, one method at a time

Usage : `/sonar-s3776 api-mail` (only `api-mail` is supported)

Purpose : S3776 (cognitive complexity of methods too high) is blacklisted from
the batch `/sonar` command because each occurrence requires a real design
decision (extract method, strategy, polymorphism). This command handles S3776
**one method at a time, one PR per method**, so that each refactor is
reviewed in isolation by the human.

Like `/sonar`, this command writes code (same automation exception — see
CLAUDE.md).

## Scope per invocation

- Repo : `api-mail` only
- **One S3776 issue = one task = one branch = one PR**
- No iteration loop. One method, one pass.

## Steps

1. **Pre-flight** (same as `/sonar` Step 0) : `api-mail` on `develop`, Sonar
   reachable, `dotnet-sonarscanner` installed, env vars set.

   **Refuse collision on the method slug** : abort if any of the following
   exists for the chosen `{method-slug}-{YYYYMMDD}` combination :
   - a task file `tasks/{todo|wip|review|done}-sonar-s3776-{method-slug}-{YYYYMMDD}.md`
   - local or remote branch `chore/sonar-s3776-{method-slug}-{YYYYMMDD}`

   Same-method re-run within the same day is blocked ; finalise or clean up
   the existing run first. A different method on the same day is fine (the
   slug differs).

2. **Fetch S3776 issues** via
   `/api/issues/search?componentKeys=$SONAR_PROJECT_KEY&rules=csharpsquid:S3776&resolved=false&ps=100`.
   If empty → nothing to do, stop.

3. **Pick the top offender** : the issue with the highest complexity value
   (parse the message : "cognitive complexity of N (limit M)"). Ties broken
   by severity then file path. If the human passed an explicit issue key as
   argument (e.g. `/sonar-s3776 api-mail <issue-key>`), use that instead.

4. **Verify test coverage of the target method** :
   - Read the method (`file:line` from the issue).
   - Locate the relevant test project under `tests/mss.mail.{layer}.tests/`.
   - Confirm at least one existing unit test exercises the method's main
     branches.
   - If coverage is weak or absent → **write the missing characterisation
     tests FIRST** (red then green on the current implementation). This locks
     behaviour before the refactor. Commit them as
     `test(sonar-s3776): characterisation tests for {MethodName}`.

5. **Create task + branch** :
   - Task : `tasks/todo-sonar-s3776-{method-slug}-{YYYYMMDD}.md` (slug derived
     from the fully-qualified method name, kebab-cased, truncated to ~40 chars)
   - Invoke `/start sonar-s3776-{method-slug}-{YYYYMMDD}` → branch
     `chore/sonar-s3776-{method-slug}-{YYYYMMDD}` on `api-mail`.

6. **Refactor** the one method until its cognitive complexity falls under the
   Sonar limit. Techniques allowed, in order of preference :
   - Extract Method (pull sub-blocks into well-named private methods)
   - Early returns / guard clauses (reduce nesting)
   - Replace nested conditionals by a dispatch table or strategy
   - Extract a small helper class if the method mixes several concerns

   After each edit, run the full test suite. Every test (including the
   characterisation tests from step 4) must stay GREEN.

7. **Re-analyse** with Sonar (same begin/build/test/end sequence as `/sonar`).
   Verify the S3776 occurrence on that method is gone. If not → the refactor
   didn't reduce complexity enough ; iterate on the method until it does.

8. **Hand over to `/review`** : rename to `review-*`, invoke
   `/review sonar-s3776-{method-slug}-{YYYYMMDD}`. Normal review → PR →
   `awaiting-human-merge`. Human merges.

## Task template

```markdown
# todo-sonar-s3776-{method-slug}-{YYYYMMDD}.md — Reduce cognitive complexity of {MethodName}

**Repos**: api-mail
**Dependencies**: aucune
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Réduire la complexité cognitive de `{FullyQualifiedMethodName}` sous la limite
Sonar (actuellement {N}, limite {M}). Refactor uniquement, aucun changement de
comportement. Comportement verrouillé par les tests de caractérisation écrits
en amont.

## Issue Sonar

- Rule : `csharpsquid:S3776`
- Fichier : `{file}:{line}`
- Complexité actuelle : {N} (limite : {M})
- Issue key : `{sonar-issue-key}`

## Definition of Done

- [ ] Tests de caractérisation écrits avant le refactor (verts sur le code
      original) — commit séparé `test(sonar-s3776): ...`
- [ ] Build passes (0 errors, Release)
- [ ] Tests pass (0 failures, y compris les caractérisation tests)
- [ ] Complexité cognitive de la méthode cible < limite Sonar
- [ ] L'occurrence S3776 sur cette méthode n'apparaît plus dans le rapport
      Sonar post-refactor
- [ ] Aucune régression sur les autres tests

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release`
3. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release`
4. Vérifier sur SonarQube que l'issue {sonar-issue-key} est bien résolue.
5. Fumer manuellement un flux qui exerce la méthode (à déterminer selon la
   méthode choisie — à documenter ici au moment du /start).
```

## Rules

- **One method per run.** Never batch multiple S3776 in the same PR.
- **Characterisation tests FIRST.** No refactor without a green safety net.
- **Refactor only.** Zero behaviour change. If a behaviour bug surfaces during
  the refactor, stop and create `questions/sonar-s3776-{slug}.md` — do not fix
  it in the same PR.
- HAG rule 10 applies : the human merges.
- Rule 11 (US-complete) : S3776 PRs are orthogonal to USes and mergeable
  independently.
