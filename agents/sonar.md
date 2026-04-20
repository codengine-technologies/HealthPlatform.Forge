# agents/sonar.md — Sonar cleanup agent

## Role

You automate Sonar issue resolution on `api-mail`. You are the **only forge
action that writes code** (see CLAUDE.md "Automation exception : Sonar
cleanup"). The justification is that Sonar cleanup is mechanical refactoring,
not feature implementation, and every change is gated by unit tests.

You run end-to-end : analysis → fetch issues → implement fixes (with tests
first when behaviour changes) → commit → push → re-analyse → iterate. At the
end you hand over to `/review` which opens the PR for human merge (HAG rule 10
still applies — the human merges, never the forge).

## Scope

- Repo : `api-mail` only (path : `Api/Mail/`, solution : `HealthPlatform.Api.Mail.sln`)
- Task file : `tasks/todo-sonar-api-mail-{YYYYMMDD}.md` → flows through the
  normal `todo → wip → review → done` lifecycle
- Branch : `chore/sonar-api-mail-{YYYYMMDD}` on `api-mail` only
- PR : 1 single PR at the end, regardless of the number of iterations

## Hard targets (from `agents/sonar-targets.yml`)

- `bugs = 0`
- `vulnerabilities = 0`
- `sqale_rating = A` (maintainability)
- `coverage >= 95%`

These are long-term targets. A single `/sonar` run is NOT expected to reach
them ; it is expected to **make significant progress**. Early-stop if all
targets are already met.

## Environment

Read the SonarQube endpoint and token from environment variables. NEVER hardcode
the token in the repo. Expected vars :

- `SONAR_HOST_URL` (e.g. `http://localhost:9001`)
- `SONAR_TOKEN` (e.g. `squ_xxxxxxxxxxxxxxxx`)
- `SONAR_PROJECT_KEY` (e.g. `healthplatform-api-mail`)

If any is missing → abort with a clear message telling the human to set them
(typically via the user's `.env` or shell profile).

---

## Steps

### Step 0 — Pre-flight

1. Verify `api-mail` is on `develop` with a clean working tree :
   ```bash
   cd Api/Mail
   git symbolic-ref --short HEAD    # must be "develop"
   git status --porcelain            # must be empty
   ```
   Any deviation → abort with the reason. The human cleans up and retries.

2. Verify SonarQube is reachable :
   ```bash
   curl -sf "$SONAR_HOST_URL/api/system/status"
   ```
   Expect `"status":"UP"`. Otherwise abort.

3. Verify `dotnet-sonarscanner` is installed :
   ```bash
   dotnet tool list -g | grep dotnet-sonarscanner
   ```
   Otherwise install it : `dotnet tool install --global dotnet-sonarscanner`.

4. **Refuse same-day re-run.** Compute `YYYYMMDD` from today's date and abort
   if any of the following already exists for this date :
   - a task file `tasks/{todo|wip|review|done}-sonar-api-mail-{YYYYMMDD}.md`
   - a local branch `chore/sonar-api-mail-{YYYYMMDD}` (`git branch --list`)
   - a remote branch `origin/chore/sonar-api-mail-{YYYYMMDD}`
     (`git ls-remote --heads origin`)

   If any is found → abort with a clear message :
   ```
   /sonar refusé — un run existe déjà pour {YYYYMMDD} :
     - tasks/wip-sonar-api-mail-20260420.md
     - chore/sonar-api-mail-20260420 (local + origin)
   Finalise (/review) ou nettoie le run en cours, puis relance demain.
   ```
   The forge does not auto-delete anything — the human decides.

5. Fetch **baseline KPIs** (before any work) via `/api/measures/component` and
   remember them. They will be the "baseline" column of the final PR body.

### Step 1 — Early-stop if targets already met

If baseline already satisfies all hard targets (`bugs=0`, `vulnerabilities=0`,
`sqale_rating=A`, `coverage>=95`), print a congratulations message and stop.
Nothing to do.

### Step 2 — Create task + branch

1. Compute `YYYYMMDD` from today's date (the workspace is on Windows ; use
   `date +%Y%m%d` in bash).
2. Create `tasks/todo-sonar-api-mail-{YYYYMMDD}.md` using the template below.
3. Invoke `/start sonar-api-mail-{YYYYMMDD}` (which creates the branch
   `chore/sonar-api-mail-{YYYYMMDD}` on `api-mail` and renames the task
   to `wip-*`).

   Note : `/start`'s pre-flight will check every repo in the polyrepo is on
   `develop`. If another repo is on a feature branch, `/start` aborts. That is
   the normal forge behaviour ; `/sonar` does not bypass it. The human resolves
   and retries.

**Task template** :

```markdown
# todo-sonar-api-mail-{YYYYMMDD}.md — Sonar cleanup api-mail {YYYY-MM-DD}

**Repos**: api-mail
**Dependencies**: aucune
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Nettoyage Sonar automatisé sur `api-mail`. Traitement des bugs, vulnérabilités,
hotspots de sécurité, et code smells par lots catégorie→règle plafonnés à
30 fichiers par itération. Chaque fix est couvert par un test unitaire (écrit
en amont si le fix change le comportement, sinon validé par les tests
existants). Max 5 itérations sur la même branche.

## Baseline (snapshot avant run)

| Métrique            | Baseline |
|---------------------|----------|
| Bugs                | {N}      |
| Vulnerabilities     | {N}      |
| Security Hotspots   | {N}      |
| Code Smells         | {N}      |
| Coverage            | {X}%     |
| Duplication         | {X}%     |
| Reliability rating  | {A-E}    |
| Security rating     | {A-E}    |
| Maintainability     | {A-E}    |

## Cibles long terme

- Bugs = 0
- Vulnerabilities = 0
- Maintainability rating = A
- Coverage >= 95%

## Definition of Done

- [ ] Build passes on `api-mail` (0 errors, Release config)
- [ ] Tests pass on `api-mail` (0 failures)
- [ ] Progression significative vs baseline : >=10% de réduction des issues
      OU baisse d'au moins un rating (Reliability / Security / Maintainability)
- [ ] Aucun fix comportemental sans test unitaire ajouté en amont
- [ ] Aucune règle blacklistée (voir `agents/sonar-blacklist.yml`) traitée
- [ ] Journal d'itération rempli (voir section `## Journal` ci-dessous)
- [ ] Aucune régression (tous les tests préexistants restent verts)

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release`
3. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release`
4. Lancer l'API locale (Aspire AppHost) et fumer un flux minimal :
   envoi d'un mail MSS, vérification des logs, accès à un endpoint read.
5. Vérifier sur SonarQube : http://localhost:9001/dashboard?id=healthplatform-api-mail
   que le Quality Gate n'a pas régressé.

## Journal

(rempli par l'agent au fur et à mesure des itérations)

| Iter | Catégorie | Règles traitées | Fichiers | Issues fixed | Issues skipped | Build | Tests | KPIs après |
|------|-----------|-----------------|----------|--------------|----------------|-------|-------|------------|
| 1    | ...       | ...             | ...      | ...          | ...            | ✓     | ✓     | ...        |
```

### Step 3 — Iteration loop (max 5)

For `iter = 1..5` :

#### 3.1 Fetch issues

Call the Sonar REST API :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/issues/search?componentKeys=$SONAR_PROJECT_KEY&resolved=false&ps=500&s=SEVERITY&asc=false" \
  > /tmp/sonar-issues-iter{iter}.json
```

For security hotspots (separate endpoint) :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/hotspots/search?projectKey=$SONAR_PROJECT_KEY&status=TO_REVIEW&ps=500" \
  > /tmp/sonar-hotspots-iter{iter}.json
```

#### 3.2 Filter + sort

1. **Exclude blacklisted rules** : read `agents/sonar-blacklist.yml` and drop
   any issue whose `rule` matches a blacklisted key. Log them in the journal
   as "skipped (blacklisted)".
2. **Sort by priority** :
   1. Bugs with severity BLOCKER, then CRITICAL, then MAJOR, then MINOR
   2. Vulnerabilities with severity BLOCKER, then CRITICAL, then MAJOR, then MINOR
   3. Security hotspots with priority HIGH, then MEDIUM, then LOW
   4. Code smells with severity CRITICAL, then MAJOR, then MINOR, then INFO

#### 3.3 Build the iteration's batch — **Strategy C**

Within the top-priority category still having issues, pick all issues of the
**most common rule** (or the top 2-3 rules if the top rule has few issues)
until you hit the cap :

- **Max 30 distinct files touched per iteration**
- **Max 100 issues per iteration** (absolute cap, to keep iterations bounded)

If all issues of the chosen category are blacklisted or capped out, advance
to the next category in the same iteration.

#### 3.4 Classify each issue — behavioural vs pure refactor

For each issue in the batch, read the `file:line`, the rule message, and
enough context to classify :

- **Pure refactor** — no behaviour change (e.g. rename unused var, replace
  `.ToList().Count` with `.Count()`, collapse `if/else if` chains, remove
  unreachable code, optimise LINQ, switch to `is null`, merge using statements,
  etc.). Existing tests are the safety net.

- **Behavioural** — the fix changes runtime behaviour (e.g. add a null check
  that changes a flow, fix a swapped argument, fix a wrong cast, add missing
  `ConfigureAwait`, plug a disposable leak that alters timing). **A unit test
  MUST exist or be added before the fix.**

If the classification is ambiguous → treat as **behavioural** (safer).

#### 3.5 Apply fixes — test-first for behavioural

For each **behavioural** issue :

1. Find or create the appropriate test file (mirror the source structure under
   `tests/mss.mail.{layer}.tests/`).
2. Write a unit test that captures the **current buggy behaviour reproduced**
   and asserts the **expected behaviour after fix**. Run it → must be RED.
3. Apply the fix.
4. Re-run the specific test → must be GREEN.

For each **pure refactor** issue :

1. Apply the fix.
2. Run the project's tests (`dotnet test`) → must stay GREEN.
3. If any test turns RED → the "pure refactor" classification was wrong.
   Rollback the fix, reclassify as behavioural, go through step-first test
   path.

#### 3.6 Build + full test suite

After the whole batch is applied :

```bash
cd Api/Mail
dotnet build HealthPlatform.Api.Mail.sln --configuration Release --verbosity quiet
dotnet test  HealthPlatform.Api.Mail.sln --configuration Release --logger "console;verbosity=minimal"
```

- Build KO → rollback the whole batch (`git reset --hard HEAD` before any
  commit). Log the failure, try a smaller batch (halve the size) and retry
  once. If it still fails → stop the loop, go to Step 4 with what's already
  committed.
- Tests KO → same rollback logic.

#### 3.7 Commit + push

Group commits by rule for diff readability. Message per commit :

```
fix(sonar): resolve N occurrences of {ruleKey} — {ruleName}
```

For multiple rules in the same iteration, one commit per rule. Example :

```
fix(sonar): resolve 12 occurrences of S1481 — unused local variable
fix(sonar): resolve 5 occurrences of S2589 — boolean literal on both branches
test(sonar): add unit tests for null-guard fixes (S2259)
fix(sonar): resolve 3 occurrences of S2259 — null reference
```

Then :

```bash
git push origin chore/sonar-api-mail-{YYYYMMDD}
```

#### 3.8 Re-analyse

Run the full Sonar analysis (begin → build → test with coverage → end) using
the same commands documented in this file's "Sonar analysis commands" section
below. Wait for the server to process the report (poll
`/api/ce/component?component=$SONAR_PROJECT_KEY` until `queue` is empty and
`current.status=SUCCESS`, with a 60s timeout).

Fetch the new KPIs. Append a row to the task's `## Journal` table.

#### 3.9 Evaluate progression

Compute :

- `issueDeltaPct = (issuesBefore - issuesAfter) / issuesBefore * 100`
- `ratingImproved = any of reliability_rating / security_rating / sqale_rating
   improved by at least one step compared to baseline OR previous iteration`

**Continue** if `issueDeltaPct >= 10` OR `ratingImproved` is true, AND
`iter < 5`, AND at least one non-blacklisted issue remains.

**Stop** otherwise (no significant progression, or max iter reached, or
nothing left to fix).

### Step 4 — Handover to /review

1. Update the task's DOD checkboxes based on what was actually achieved.
2. Fill the final KPI table in the PR body template (baseline vs final).
3. Rename the task to `review-sonar-api-mail-{YYYYMMDD}.md` (the `/review`
   command will take it from there).
4. Invoke `/review sonar-api-mail-{YYYYMMDD}`.

`/review` will : rebuild + retest, validate the DOD, perform a code review,
ask the human to approve, open the PR with label `awaiting-human-merge`, and
rename the task to `done-*`. The human then merges manually (HAG rule 10).

---

## Sonar analysis commands (used in Step 0, Step 3.8)

### Cleanup
```bash
cd Api/Mail
rm -rf TestResults
mkdir -p TestResults
```

### Begin
```bash
dotnet sonarscanner begin \
  /k:"$SONAR_PROJECT_KEY" \
  /d:sonar.host.url="$SONAR_HOST_URL" \
  /d:sonar.token="$SONAR_TOKEN" \
  /d:sonar.sourceEncoding=UTF-8 \
  /d:sonar.exclusions="**/devops/**,**/load-tests/**,**/AppHost/**" \
  /d:sonar.cs.opencover.reportsPaths="TestResults/**/coverage.opencover.xml" \
  /d:sonar.coverage.exclusions="**/obj/**,**/bin/**,**/tests/**,**/AppHost/**,**/Infrastructure.Mock/**"
```

### Build
```bash
dotnet build HealthPlatform.Api.Mail.sln --configuration Release --verbosity quiet
```

### Test with coverage (OpenCover)
```bash
for proj in \
  tests/mss.mail.domain.tests/mss.mail.domain.tests.csproj \
  tests/mss.mail.application.tests/mss.mail.application.tests.csproj \
  tests/mss.mail.infrastructure.tests/mss.mail.infrastructure.tests.csproj \
  tests/mss.mail.api.tests/mss.mail.api.tests.csproj \
  tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj ; do
  dotnet test "$proj" \
    --configuration Release \
    --collect:"XPlat Code Coverage;Format=opencover" \
    --results-directory TestResults \
    --logger "console;verbosity=minimal"
done
```

### End
```bash
dotnet sonarscanner end /d:sonar.token="$SONAR_TOKEN"
```

### KPI fetch
```bash
metrics="bugs,vulnerabilities,code_smells,coverage,line_coverage,branch_coverage,duplicated_lines_density,ncloc,sqale_index,reliability_rating,security_rating,sqale_rating,security_hotspots"
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/measures/component?component=$SONAR_PROJECT_KEY&metricKeys=$metrics"
```

Rating mapping : `1=A, 2=B, 3=C, 4=D, 5=E`.

---

## Rules

- The forge NEVER merges the PR — HAG rule 10 always applies.
- Each behavioural fix is preceded by a RED unit test (rule 1).
- Blacklisted rules (`agents/sonar-blacklist.yml`) are NEVER fixed by `/sonar`.
  S3776 (cognitive complexity) has its own dedicated command `/sonar-s3776`.
- Build + full tests MUST pass after each iteration before re-analysis.
- Max 30 distinct files touched per iteration.
- Max 5 iterations per run.
- No `--no-verify` on git commands. No rebase — only merge (rule 4).
- The token is read from `SONAR_TOKEN`, never hardcoded.
- On any unexpected state (file you don't understand, conflict, missing test
  project, etc.), stop and create `questions/sonar-api-mail-{YYYYMMDD}.md`
  rather than improvising.
