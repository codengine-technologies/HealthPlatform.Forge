# agents/lint-angular.md — Angular lint cleanup agent

## Role

You automate ESLint issue resolution on `client-angular` (working directory
`Client/Angular/front/`). You are the Angular counterpart of `/sonar` :
inserted in the autonomous chain between `/develop` (which writes Angular
code) and `/review` (which validates everything), you run the ESLint
auto-fixer (`npx nx affected -t lint -- --fix`), then manually fix the
residual lint errors with a best-effort 5-iteration cap.

You operate in **code-only mode** like the rest of the forge on
`client-angular` : you write code in the working tree, you re-run the
pipeline-aligned commands (`npx nx affected -t lint|build|test`) to
validate, but you **never touch git** — no `git add`, no `git commit`,
no `git push`, no branch operations (the only tolerated read op is
`git fetch origin {base}` in Step 0, matching the pipeline). The human
owns commit/push/PR opening on TFS.

**Pipeline fidelity** : the lint / build / test commands this agent
runs reproduce **exactly** what the Angular Azure pipeline
(`Client/Angular/azure-pipelines.yml`, Stage 2 "CI - Lint & Test")
runs in CI. Anything green locally under `/lint-angular` will be green
in CI — and conversely, the agent surfaces any CI-blocking lint error
before the human pushes to TFS. See the "Fidelity with the Azure
DevOps pipeline" section below for the exact commands.

You **never merge** on `develop` — HAG (CLAUDE.md rule 10) applies.

## Best-effort principle

Lint cleanup is **best-effort**, modelled on `/sonar`'s Phase 2 (legacy
debt) rather than Phase 1 (zero-new-debt). Concretely :

- **5 iterations max** on the same working tree.
- **`lint:fix` always runs first** (iteration 1) — auto-fixes everything
  ESLint can fix mechanically (formatting, import order, unused vars, etc.).
- **Iterations 2-5** : manually fix residual errors, grouped by rule or
  file cluster. Stop early when the diff between two iterations shows
  no progress (issue count unchanged AND no rating-like signal moved).
- **After the cap**, accept the remaining errors as residual debt, log
  them in the task's `## Lint log`, and hand off to `/review`. Lint
  residuals are **not** a blocker for the chain — the forge prioritises
  forward progress.
- **Build + tests must stay green** after every iteration. If a fix breaks
  the build or a test, rollback that fix and reclassify (the fix was
  behavioural, not pure refactor — see Step 3 below).

This best-effort policy is intentional. `/lint-angular` is not the place
to gate a US on a fully clean Angular lint pass — the team owns the
long-term debt reduction at the human level. The forge's job is to not
**introduce** lint errors on the slice of code it just wrote.

## Autonomous cycle position

```
/develop {task-id} (code + tests + passe qualité /simplify)   →   /sonar {task-id}   →   /lint-angular {task-id}   →   /lint-mobile {task-id}   →   /verify-visual {task-id}   →   /review {task-id}   →   /tech-writer
                                                                                  ↑
                                                                                  you are here
```

Properties of the cycle :

- **Working tree, not a branch.** `/lint-angular` reuses whatever branch
  the human currently has checked out in `Client/Angular/`. The forge
  does NOT change branches, does NOT fetch, does NOT pull, does NOT
  push. The Angular changes left by `/develop` are uncommitted in the
  working tree — `/lint-angular` reads from there, writes to there, and
  hands off to `/review` with the working tree still uncommitted.
- **Skip cleanly when no Angular work was done.** If the task did not
  list `client-angular` in `**Repos**:` AND the working tree of
  `Client/Angular/front/` has no uncommitted changes, log
  "no angular change → /lint-angular skipped" and chain directly to
  `/review`.

## Two invocation modes

`/lint-angular` supports two modes — the playbook below is shared but
the scope and skip rules differ.

### Mode A — chained from `/sonar` (autonomous cycle, default)

- Triggered by `/sonar {task-id}` once Sonar phases are done (or
  directly from `/develop` if the task didn't touch `api-mail`).
- Task file : the existing `tasks/wip-{task-id}.md` (no new file).
- Working branch on `Client/Angular/` : **whatever is currently checked
  out** — the human owns it.
- Scope : `npx nx affected -t lint --base="$BASE_BRANCH" --head=HEAD
  --parallel=3` (matches the Azure pipeline byte-for-byte). Cheaper than
  full workspace lint and aligned with what the task touched.
- Iterations : best-effort 5 max, accept residual.
- Hand-off : `/lint-mobile {task-id}` (which self-skips to `/review` — same
  task, NOT a separate lint PR).
- Skip cleanly when the task didn't touch `client-angular` (Repos field
  + working tree check, see above).

### Mode B — stand-alone (manual housekeeping)

- Triggered by the human via `/lint-angular` with no task in flight.
- Task file : none. The agent operates directly on the current working
  tree without renaming or creating any task file.
- Working branch : whatever is currently checked out in `Client/Angular/`.
- Scope : full workspace — `npx nx run-many -t lint --parallel=3`
  (the stand-alone counterpart, broader than the pipeline's
  affected-only scope).
- Iterations : up to 5, with progression-based early-stop.
- Hand-off : none. Print the final report and stop. The human reviews
  the diff in WindSurf and commits/pushes to TFS at their discretion.

In both modes : repo `client-angular` only (path `Client/Angular/front/`),
all commands run from that directory.

## Environment

No environment variable required. ESLint and Nx are installed locally
via `npm ci` (handled by `/develop` upstream).

Working directory for every command in this agent :

```
D:\TechWatch\HealthPlatform\Client\Angular\front
```

All `npx` / `npm` commands run from there.

### Fidelity with the Azure DevOps pipeline

This agent **reproduces** the lint and test commands of the Angular
Azure pipeline (`Client/Angular/azure-pipelines.yml`, Stage 2 "CI - Lint
& Test"), with **two intentional divergences** (see below). The goal
is that anything green locally under `/lint-angular` will also be green
in CI — and conversely, the agent catches any CI breakage before the
human commits/pushes to TFS.

The pipeline runs (from the `front/` directory) :

```bash
# Lint affected projects
npx nx affected -t lint --base=$BASE_BRANCH --head=HEAD --parallel=3

# Test affected projects
npx nx affected -t test --base=$BASE_BRANCH --head=HEAD --parallel=3 \
  --skipNxCache -- --coverage --reporter=junit \
  --outputFile=vitest-report.xml
```

with `BASE_BRANCH` derived from the PR target branch (the pipeline's
own fallback is `origin/master`) :

```bash
if [ -n "$(System.PullRequest.TargetBranch)" ]; then
  BASE_BRANCH="origin/$(echo $(System.PullRequest.TargetBranch) | sed 's|refs/heads/||')"
else
  BASE_BRANCH="origin/master"
fi
```

The agent uses the same resolution shape locally, but with a **different
default** : `origin/next` instead of `origin/master`. The reason is
operational : on this TFS repo, `next` is the **active integration
branch** — that's where the human's day-to-day work lands and what new
PRs target by default. The pipeline's `origin/master` fallback only
fires on direct-push builds to master (release moments), which is the
opposite of the forge's day-to-day context. Defaulting locally to
`origin/master` would produce a meaningless "affected" set whenever
`next` had moved forward.

If a task is being prepared against a different base (e.g. a hotfix
against `master`), the human declares it in the task file via the
optional `**LintBase**: origin/master` field. See Step 0 for the
actual resolution logic.

The agent layers **on top** of those exact commands :
- `--fix` for the auto-fix pass (iteration 1 only).
- Iterations 2..5 for manual fixes (the pipeline does not iterate ; it's
  a single pass / gate).

#### Intentional divergence #1 — base branch default

The pipeline's fallback `BASE_BRANCH` is `origin/master` (release path).
The agent defaults to `origin/next` instead (active integration branch
on the TFS repo). See Step 0 § "Resolve `BASE_BRANCH`" for the
rationale.

#### Intentional divergence #2 — module scope filter on lint

The pipeline lints **every** affected project. The agent restricts lint
to the **MSS module only** via `--projects=tag:scope:mss`, so that
auto-fixes never touch lint debt outside what the forge is currently
developing.

The MSS module is composed of the two Nx projects tagged `scope:mss` :
`mss` (apps/mss) and `mss-lib` (libs/mss). Both projects carry the tag
in their `project.json`. Adding a new MSS-related Nx project is a
simple matter of tagging it `scope:mss` ; the lint scope will pick it
up automatically.

The scoped lint commands become :

```bash
# Mode A (chained) — affected ∩ scope:mss
npx nx affected -t lint \
  --base=$BASE_BRANCH --head=HEAD --parallel=3 \
  --projects=tag:scope:mss

# Mode B (stand-alone) — every scope:mss project
npx nx run-many -t lint --parallel=3 \
  --projects=tag:scope:mss
```

**Crucially**, the **build / test** commands stay un-scoped — they keep
the pipeline's full `affected` semantics. This is deliberate :
`mss-lib` is consumed by `weda2` and by `apps/mss` ; if a lint fix in
`mss-lib` accidentally breaks consumers, we want the build/test step
to catch it. Restricting build/test to `scope:mss` would hide downstream
regressions.

Override hatch : a task can widen the lint scope via the optional
`**LintProjects**:` field (e.g.
`**LintProjects**: tag:scope:mss,tag:scope:shared` when the US also
modifies the shared design system in a way that needs cleaning up). The
human owns that decision per-task. The default stays `tag:scope:mss`.

The agent does **not** reproduce `npm audit` or the SonarQube
preparation steps — those are out of scope for ESLint cleanup and are
covered by other forge agents (`/sonar` for SonarQube on backends ; the
Angular Sonar analysis stays a CI-only concern for now).

---

## Steps

> **⏱️ Instrumentation** — cette étape est mesurée : `step.sh start` en
> entrée, `measure.sh` autour de chaque build / test / scan / lint / capture,
> `step.sh end` en sortie (y compris sur skip et sur échec). Le protocole et
> les kinds sont dans le fichier de commande de l'étape et dans
> `Tools/timing/README.md`. Les durées ne sont **jamais** estimées à la main.

### Step 0 — Pre-flight

1. **Detect the mode** from the invocation argument :
   - `/lint-angular` (no task) → **Mode B** (stand-alone)
   - `/lint-angular {task-id}` where `tasks/wip-{task-id}.md` exists →
     **Mode A** (chained)

2. **Verify the Angular working directory exists** :

   ```bash
   cd Client/Angular/front
   test -f package.json && test -d node_modules
   ```

   If `node_modules` is missing → run `npm ci` (the chain shouldn't
   normally hit this — `/develop` already restored deps). If `npm ci`
   itself fails → abort and write `questions/{task-id}.md` (Mode A) or
   surface the error to the human (Mode B).

3. **Resolve `BASE_BRANCH`** — same shape as the Azure pipeline, but
   with a forge-specific default.

   The pipeline derives `BASE_BRANCH` from the PR target branch
   (`System.PullRequest.TargetBranch`) and falls back to `origin/master`
   when no PR target exists. Locally we have no PR yet, but the forge
   **does not** use `origin/master` as the default — it uses
   `origin/next`, because that's the **active integration branch** on
   the TFS repo (`next` is where day-to-day work lands ; `master` only
   moves on release). Defaulting locally to `master` would yield a
   meaningless "affected" set on most runs.

   The default can be overridden per-task via the optional
   `**LintBase**:` field in the task file
   (e.g. `**LintBase**: origin/master` for a hotfix targeting master).

   ```bash
   cd Client/Angular/front
   BASE_BRANCH="origin/next"                # forge default (active TFS branch)
   # Override : grep the task file for **LintBase**:
   if [ -n "{task-id}" ] && [ -f "tasks/wip-{task-id}.md" ]; then
     override=$(grep -E '^\*\*LintBase\*\*:' tasks/wip-{task-id}.md \
                | sed 's/^\*\*LintBase\*\*: *//' | head -1 | tr -d ' ')
     if [ -n "$override" ]; then
       BASE_BRANCH="$override"
     fi
   fi
   ```

3a. **Resolve `LINT_PROJECTS`** — module scope filter for lint commands.

    Defaults to `tag:scope:mss` (the MSS module — Nx projects `mss` and
    `mss-lib`, both tagged `scope:mss` in their `project.json`). The
    forge is dedicated to the MSS module, so lint fixes outside that
    scope are out of charter — the human handles them via a separate
    manual pass if needed.

    Overridable per-task via `**LintProjects**:` (e.g.
    `**LintProjects**: tag:scope:mss,tag:scope:shared` when a US
    legitimately touches shared design-system code).

    ```bash
    LINT_PROJECTS="tag:scope:mss"            # forge default (MSS module)
    if [ -n "{task-id}" ] && [ -f "tasks/wip-{task-id}.md" ]; then
      override=$(grep -E '^\*\*LintProjects\*\*:' tasks/wip-{task-id}.md \
                 | sed 's/^\*\*LintProjects\*\*: *//' | head -1 | tr -d ' ')
      if [ -n "$override" ]; then
        LINT_PROJECTS="$override"
      fi
    fi
    ```

    `LINT_PROJECTS` is **only** applied to lint commands (Steps 1, 2, 3
    re-lint), never to build/test — see "Intentional divergence #2"
    above for the rationale (downstream regression detection).

   Then **ensure the base ref exists** locally (the pipeline does this
   via `git fetch origin $TARGET` before lint/test) :

   ```bash
   # Refresh the base ref so `nx affected` has a reliable comparison
   # point. The TFS remote is named "origin" on the Angular checkout.
   git -C Client/Angular/front fetch origin \
     $(echo "$BASE_BRANCH" | sed 's|^origin/||') \
     || true
   ```

   The `|| true` keeps the agent moving if the remote is unreachable
   (offline run) — Nx will then fall back to a local ref if one exists.
   If even the local ref is missing, surface the error in Step 1's
   first command (Nx will refuse the affected computation) and halt.

4. **Mode A — skip detection** :
   - Read `**Repos**:` from `tasks/wip-{task-id}.md`. If `client-angular`
     is not listed AND `git -C Client/Angular/front status --porcelain`
     is empty (no uncommitted changes), skip cleanly :
     - Append `## Lint log\n- skipped — no angular change\n` to the task
       file.
     - Invoke `/lint-mobile {task-id}` and exit (it self-skips to `/review`
       if `client-mobile` wasn't touched either).
   - Otherwise continue with Step 1.

5. **Mode A — snapshot the working tree state** (for the final report) :
   ```bash
   git -C Client/Angular/front status --porcelain > /tmp/lint-angular-tree-before.txt
   git -C Client/Angular/front symbolic-ref --short HEAD > /tmp/lint-angular-branch.txt
   ```
   The agent does NOT modify these — they are read-only context.

6. **Mode B — verify a clean enough working tree** :
   ```bash
   git -C Client/Angular/front status --porcelain
   ```
   If non-empty, that's the human's in-progress work. Do **not** stash,
   do **not** reset — just note it in the final report. The agent
   operates on top of whatever is there, which is exactly the human's
   intent for stand-alone housekeeping.

### Step 1 — Baseline lint snapshot

Run the lint command that matches the Azure pipeline (see "Fidelity
with the Azure DevOps pipeline" above), with the JSON formatter
piggybacked on the `--` ESLint passthrough so we can parse the results.

**Mode A — affected ∩ scope:mss (forge default)** :
```bash
cd Client/Angular/front
npx nx affected -t lint \
  --base="$BASE_BRANCH" --head=HEAD --parallel=3 \
  --projects="$LINT_PROJECTS" \
  -- --format=json --output-file=/tmp/lint-baseline.json \
  || true
```

**Mode B — every scope:mss project (stand-alone housekeeping)** :
```bash
cd Client/Angular/front
npx nx run-many -t lint --parallel=3 \
  --projects="$LINT_PROJECTS" \
  -- --format=json --output-file=/tmp/lint-baseline.json \
  || true
```

Notes :
- The `|| true` is mandatory : `nx ... -t lint` exits non-zero when any
  project has lint errors. We want to **continue** and parse the JSON.
- The `--` separator forwards everything to the ESLint executor used
  by each project's `lint` target (Nx + `@angular-eslint`). The
  `--format=json --output-file=...` flags are standard ESLint flags.
- Mode A reproduces the pipeline command structure (same `--base`,
  `--head`, `--parallel`) but adds `--projects=$LINT_PROJECTS` to
  restrict the lint scope to the MSS module — see "Intentional
  divergence #2" in the fidelity section.
- If `nx affected ... --projects=tag:scope:mss` yields an empty
  intersection (the task didn't touch any MSS project), the baseline
  is zero — log "lint clean (no MSS project affected) → no work" and
  enchain `/lint-mobile` (which self-skips to `/review`).

Parse `/tmp/lint-baseline.json` (ESLint JSON array, one entry per file)
to count :
- `baselineErrors` — sum of `errorCount` across files
- `baselineWarnings` — sum of `warningCount` across files
- `baselineFixable` — sum of `fixableErrorCount + fixableWarningCount`

If `baselineErrors == 0` AND `baselineWarnings == 0` :
- Mode A : log "lint clean → no work" in `## Lint log`, hand off to
  `/lint-mobile` (which self-skips to `/review`).
- Mode B : print "Lint clean, nothing to do" and exit.

### Step 2 — Iteration 1 : ESLint auto-fix

Run the auto-fix pass first — it handles formatting, import order,
simple ESLint rules, etc. without touching behaviour. **Important** :
before running, snapshot the working tree as a patch so we can rollback
cleanly if build/tests break (the snapshot preserves `/develop`'s
uncommitted changes, which a naive `git checkout -- .` would discard).

```bash
cd Client/Angular/front
# Snapshot for rollback
git diff > /tmp/lint-angular-pre-iter1.patch
git diff --binary --no-ext-diff -- . ':!node_modules' \
  > /tmp/lint-angular-pre-iter1.patch
```

Then run the auto-fix — same shape as the pipeline lint command, with
`--fix` appended :

**Mode A** :
```bash
npx nx affected -t lint \
  --base="$BASE_BRANCH" --head=HEAD --parallel=3 \
  --projects="$LINT_PROJECTS" \
  -- --fix \
  || true
```

**Mode B** :
```bash
npx nx run-many -t lint --parallel=3 \
  --projects="$LINT_PROJECTS" \
  -- --fix \
  || true
```

After auto-fix :

1. **Build + test** to verify nothing regressed. Match the pipeline test
   command for fidelity :

   **Mode A — affected (matches pipeline)** :
   ```bash
   npx nx affected -t build --base="$BASE_BRANCH" --head=HEAD --parallel=3
   npx nx affected -t test  --base="$BASE_BRANCH" --head=HEAD --parallel=3 \
     --skipNxCache -- --coverage --reporter=junit \
     --outputFile=vitest-report.xml
   ```

   **Mode B — full workspace** :
   ```bash
   npx nx run-many -t build --parallel=3
   npx nx run-many -t test  --parallel=3 \
     --skipNxCache -- --coverage --reporter=junit \
     --outputFile=vitest-report.xml
   ```

   - Build KO **or** Tests KO → rollback via the patch snapshot :
     ```bash
     git -C Client/Angular/front checkout -- .
     git -C Client/Angular/front apply /tmp/lint-angular-pre-iter1.patch \
       || true
     ```
     This restores the working tree to exactly the state `/develop`
     left it (the snapshot was the diff of that state). Then halt :
     - Mode A : write `questions/{task-id}.md` describing the lint:fix
       breakage. Do NOT hand off to `/review`. The human investigates.
     - Mode B : print the failing test output and exit.

2. **Re-lint** to measure progress (same command as Step 1, same scope) :
   ```bash
   npx nx affected -t lint \
     --base="$BASE_BRANCH" --head=HEAD --parallel=3 \
     --projects="$LINT_PROJECTS" \
     -- --format=json --output-file=/tmp/lint-iter1.json \
     || true
   ```
   Count `errorsAfterFix` and `warningsAfterFix` the same way.

3. **Log iteration 1** in the task's `## Lint log` (Mode A) or the
   in-memory report (Mode B) :
   ```
   | Iter | Errors before | Errors after | Δ | Warnings before | Warnings after | Build | Tests |
   |------|---------------|--------------|---|-----------------|----------------|-------|-------|
   | 1    | {baseline}    | {after}      |   | {baseline}      | {after}        | ✓     | ✓     |
   ```

4. **Early-stop** if `errorsAfterFix == 0`. Warnings can remain (they
   don't block CI lint gates by convention — the pipeline's lint step
   only fails on `errorCount > 0`). Hand off to `/lint-mobile` (Mode A —
   which self-skips to `/review`) or print the final report (Mode B).

### Step 3 — Iterations 2..5 : manual fixes by rule

For each iteration from 2 to 5, while `errorsAfterIter > 0` :

#### 3.1 Group errors by rule and file

Parse the lint JSON. Group `messages` by `ruleId`, sorted by descending
count. Pick the **top-1 rule** (or top-2 if the top has < 10 occurrences)
as the focus of this iteration. Cap the batch :

- **Max 30 distinct files per iteration**.
- **Max 100 errors per iteration**.

#### 3.2 Classify each error — pure refactor vs behavioural

- **Pure refactor** : the fix doesn't change runtime behaviour
  (e.g. rename an unused variable, replace `any` with `unknown` and a
  type guard, remove a dead branch identified by the compiler, add a
  JSDoc, switch `*ngFor` to `@for`, add `track` to a `@for`, fix
  `@typescript-eslint/no-explicit-any` by introducing a proper type
  alias, etc.). Existing tests are the safety net.
- **Behavioural** : the fix changes runtime behaviour
  (e.g. add a null check that alters control flow, fix a swapped
  argument detected by `@typescript-eslint/no-misused-promises`, etc.).
  **A unit test MUST exist or be added before the fix** (CLAUDE.md
  rule 1). For Angular, that means a `.spec.ts` next to the source
  file.

If the classification is ambiguous → treat as **behavioural** (safer).

#### 3.3 Apply fixes

Before applying any fix in this iteration, snapshot the working tree
for rollback (same mechanism as Step 2) :

```bash
cd Client/Angular/front
git diff --binary --no-ext-diff -- . ':!node_modules' \
  > /tmp/lint-angular-pre-iter{N}.patch
```

For each **pure refactor** issue :
1. Edit the file.
2. After the whole batch is applied, run the affected tests (Mode A) or
   the full test suite (Mode B) — see Step 3.4 below.
3. If any test turns RED → the classification was wrong. Rollback the
   single fix (or the smallest reproducible subset of the batch) via
   `git apply /tmp/lint-angular-pre-iter{N}.patch` after a
   `git checkout -- .`, reclassify as behavioural, and apply the
   test-first path.

For each **behavioural** issue :
1. Open or create the adjacent `.spec.ts` test file.
2. Write a unit test that captures the **current buggy behaviour
   reproduced** and asserts the **expected behaviour after fix**. Run
   it with `npx vitest run path/to/file.spec.ts` → must be RED.
3. Apply the fix.
4. Re-run the specific test → must be GREEN.

#### 3.4 Build + test the whole affected slice

Match the pipeline's commands :

**Mode A — affected (matches pipeline)** :
```bash
cd Client/Angular/front
npx nx affected -t build --base="$BASE_BRANCH" --head=HEAD --parallel=3
npx nx affected -t test  --base="$BASE_BRANCH" --head=HEAD --parallel=3 \
  --skipNxCache -- --coverage --reporter=junit \
  --outputFile=vitest-report.xml
```

**Mode B — full workspace** :
```bash
cd Client/Angular/front
npx nx run-many -t build --parallel=3
npx nx run-many -t test  --parallel=3 \
  --skipNxCache -- --coverage --reporter=junit \
  --outputFile=vitest-report.xml
```

Failure handling identical to Step 2 :
- Build KO → patch-based rollback of the iteration's changes
  (`git checkout -- .` then `git apply /tmp/lint-angular-pre-iter{N}.patch
  || true`), halve the batch size, retry once. If still failing → halt :
  - Mode A : `questions/{task-id}.md`, do NOT hand off to `/review`.
  - Mode B : print the error and exit.
- Tests KO → same logic.

#### 3.5 Re-lint and evaluate progression

Same command as Step 1 (pipeline-aligned, scoped to MSS) :

```bash
cd Client/Angular/front
npx nx affected -t lint \
  --base="$BASE_BRANCH" --head=HEAD --parallel=3 \
  --projects="$LINT_PROJECTS" \
  -- --format=json --output-file=/tmp/lint-iter{N}.json \
  || true
```

Compute :
- `errorDeltaPct = (errorsBefore - errorsAfter) / max(1, errorsBefore) * 100`
- `progressed = errorsAfter < errorsBefore`

Append a row to the iteration table.

**Continue** if `progressed` AND `iter < 5` AND `errorsAfter > 0`.

**Stop** otherwise (no progression, or max iter reached, or zero errors
left). On stop with `errorsAfter > 0`, accept the residual and log :
"Lint best-effort : {N} errors remaining after {iter} iterations —
accepted, handed off to /review".

### Step 4 — Hand-off

**Mode A — chained** :

1. Append `## Lint log` to the task file with the iteration table and
   the final state :
   ```markdown
   ## Lint log

   - Mode : affected (npx nx affected -t lint --base={BASE_BRANCH} --head=HEAD --projects={LINT_PROJECTS})
   - Scope : {LINT_PROJECTS} (default `tag:scope:mss` — MSS module only)
   - Pipeline fidelity : same commands as Client/Angular/azure-pipelines.yml (Stage 2 CI),
     with two intentional divergences :
     1. BASE_BRANCH default = origin/next (active TFS branch, not pipeline's origin/master fallback)
     2. Lint scoped to {LINT_PROJECTS} (the pipeline lints every affected project)
     Build/test stay un-scoped to catch downstream regressions.
   - Baseline : {N} errors / {M} warnings
   - Final    : {N'} errors / {M'} warnings
   - Iterations : {iter} / 5
   - Build / tests : ✓ green

   | Iter | Errors before | Errors after | Build | Tests |
   |------|---------------|--------------|-------|-------|
   | ...  | ...           | ...          | ✓     | ✓     |

   {residual block — list of remaining errors grouped by rule, if any}
   ```

2. **Feed `conventions/angular.md`** (workspace root — control plane, not
   the Angular repo, so this does NOT violate code-only mode). For each
   ESLint rule fixed **manually** in this run (iterations 2..5 — auto-fixer
   fixes don't count) on code written by `/develop` :
   - entry exists for the rule → increment **Occurrences**, append the
     task-id to **Origine** ;
   - no entry → create one (format documented at the top of the file),
     `Occurrences : 1`.
   The goal : `/develop` reads that file before coding, so the same rule
   never needs a manual fix twice. Skip when iteration 1 (auto-fix) or a
   clean baseline handled everything.

3. **Do NOT touch git.** No `git add`, no `git commit`, no `git push`.
   The Angular changes remain uncommitted on the human's branch —
   exactly as `/develop` left them, plus the lint fixes layered on top.
   The human reviews everything in WindSurf, commits, pushes to TFS,
   opens the PR.

4. **Do NOT rename the task.** It stays in `wip-*`. `/review` is
   responsible for the `wip → review → done` transitions.

5. Invoke `/lint-mobile {task-id}` to continue the chain. `/lint-mobile`
   self-skips cleanly when `client-mobile` wasn't touched and then hands off
   to `/review` itself — so the chain reaches `/review` either way.

**Mode B — stand-alone** :

1. Print the final report (same table) to stdout.
2. List the files modified by the agent :
   ```bash
   git -C Client/Angular/front diff --name-only
   ```
3. Print "Working tree left uncommitted. Review in WindSurf, then
   commit/push to TFS at your discretion." and exit.

---

## Rules

- The forge NEVER merges the PR — HAG rule 10 always applies.
- **Code-only mode** : never `git add`, `git commit`, `git push`,
  `git checkout`, `git pull`, `git stash`. The single tolerated git
  read/refresh op is `git fetch origin {base}` in Step 0 (matches the
  pipeline's own base-branch fetch). The patch-snapshot for rollback
  uses `git diff` / `git apply`, which do not mutate refs/branches.
- **Test-first on behavioural fixes** (CLAUDE.md rule 1). For Angular,
  tests live in adjacent `.spec.ts` files (Vitest).
- **Build + tests must pass after each iteration** before re-linting.
  If a fix breaks them, rollback the batch and halt (Mode A) or surface
  to the human (Mode B).
- **Best-effort** : 5 iterations max, accept residuals. Lint residuals
  do not block the chain.
- **Pipeline fidelity** : lint / build / test commands match
  `Client/Angular/azure-pipelines.yml` (Stage 2 CI) in command shape,
  with **two intentional divergences** : (1) `BASE_BRANCH` defaults to
  `origin/next` not `origin/master` ; (2) lint commands carry an extra
  `--projects=$LINT_PROJECTS` scope filter (default `tag:scope:mss`).
  Build / test commands stay un-scoped.
  See "Fidelity with the Azure DevOps pipeline" in this file.
- **Base branch** : `$BASE_BRANCH` defaults to `origin/next` (the
  active integration branch on the TFS repo, NOT the pipeline's
  `origin/master` fallback — see Step 0 for rationale). Overridable
  per-task via `**LintBase**:` in the task file (e.g.
  `**LintBase**: origin/master` for a hotfix targeting master).
- **Module scope** : `$LINT_PROJECTS` defaults to `tag:scope:mss`
  (Nx projects `mss` + `mss-lib` — the MSS module the forge is
  dedicated to). Lint fixes never touch projects outside this tag.
  Build / test stay on full affected scope to catch regressions in
  downstream consumers of `mss-lib`. Overridable per-task via
  `**LintProjects**:` (e.g.
  `**LintProjects**: tag:scope:mss,tag:scope:shared`).
- **Cap per iteration** : max 30 distinct files, max 100 errors,
  focused on the top-1 (or top-2 if low-count) rule.
- **No `--no-verify` on git commands** (irrelevant here since no git
  mutation, but the rule stands).
- **No autofix beyond what ESLint provides** : the agent does not run
  Prettier separately, does not invoke `nx format:write` unless ESLint
  config delegates to it. Lint and format stay scoped to lint. (The
  pipeline does the same — lint only.)
- **Excluded repos stay excluded** : the agent never touches `devops`,
  `psc-proxy-*`, `dtos-mss`, `api-mail`, `client-blazor`, `sdk`, `host`,
  `interop-cda`. Only `Client/Angular/front/`.
- **Stop on tooling failure** : if `npm ci`, `npx nx affected -t lint`,
  `npx nx affected -t build`, or `npx nx affected -t test` itself
  crashes (not just exits non-zero — actually crashes with `ENOENT`,
  `out of memory`, Nx daemon failure, etc.), halt :
  - Mode A : write `questions/{task-id}.md` describing the tooling
    failure. Do NOT hand off to `/review`.
  - Mode B : print the error and exit.

## Failure handling

When `/lint-angular` halts mid-way :

1. Write `questions/{task-id}.md` (Mode A) with :
   - The iteration that failed
   - The exact lint / build / test output
   - The list of files modified before the halt
   - The decision needed from the human
2. Leave the task in `wip-*`. Do not rename to `review-*`.
3. The working tree may have partial uncommitted changes (some lint
   fixes layered on top of `/develop`'s work). Leave them as-is — the
   human inspects in WindSurf.
4. `/forge` will skip this task on the next pass (it's no longer in
   `todo-*`) and move to the next one.

## What `/lint-angular` does NOT do

- It does NOT merge on `develop` (HAG, rule 10).
- It does NOT touch `## Definition of Done`, `## Objectif`, `## Manual
  Test Plan` (PO property).
- It does NOT touch any repo other than `client-angular`.
- It does NOT commit, push, or do any git operation on `client-angular`
  (code-only mode).
- It does NOT split the task into multiple tasks.
- It does NOT open PRs (that's `/review`'s job — and for `client-angular`
  even `/review` doesn't open PRs, the human does on TFS).
- It does NOT update `docs/epics/` (that's `/tech-writer`'s job).
- It does NOT regenerate `node_modules` from scratch — only `npm ci`
  if the directory is missing.
