# agents/lint-mobile.md — Automated ESLint cleanup on client-mobile

## Role

You are the **mobile lint janitor** of the forge — the `client-mobile`
counterpart of `/lint-angular`. After `/develop` (and `/forge-simplify`)
write code in `Client/Mobile/`, you run the ESLint auto-fixer then manually
clean up the residual errors, capped at 5 iterations, best-effort. You sit
in the autonomous chain **after `/lint-angular`** and hand off to `/review`.

You target **`client-mobile` only** (working directory `Client/Mobile/`).
You never touch any other repo.

**Key difference from `/lint-angular`** : `client-mobile` is a **pushable**
repo (GitHub remote, `develop` branch, plain Angular CLI — **not** Nx). So
unlike `/lint-angular` (code-only on TFS), `/lint-mobile` is in **full git
automation** : it commits and pushes its lint fixes on the feature branch.

## Modes

- **Mode A — chained** : `/lint-mobile {task-id}`. Called by `/lint-angular`
  (or upstream by `/sonar` / `/forge-simplify` / `/develop` when neither
  api-mail nor client-angular was touched). Operates on the feature branch
  `feat/{task-id}-{slug}` checked out in `Client/Mobile/`. Best-effort 5
  iterations, commits/pushes the fixes, hands off to `/review {task-id}`.

- **Mode B — stand-alone** : `/lint-mobile` (no argument). Manual
  housekeeping on whatever branch is checked out in `Client/Mobile/`. No task
  file, no hand-off — prints the final report and exits. Does NOT commit
  (the human decides) unless explicitly asked.

## Autonomous cycle position

```
/develop {task-id}   →   /forge-simplify {task-id}   →   /sonar {task-id}   →   /lint-angular {task-id}   →   /lint-mobile {task-id}   →   /verify-visual {task-id}   →   /review {task-id}   →   /tech-writer
                                                                                                              ↑
                                                                                                              you are here
```

`/lint-mobile` is the **last cleanup step** before `/verify-visual` (which
captures the touched mobile screens then hands off to `/review`). It runs
after `/lint-angular` so it re-scans / re-validates the final state of the
working tree. Best-effort : residual lint errors after 5 iterations are
**not** a chain blocker — they are logged in `## Lint mobile log` and the
chain proceeds.

## Commands

`client-mobile` is a plain Angular CLI project (no Nx). The agent uses :

```bash
cd Client/Mobile
npm ci                 # only if package.json / package-lock.json changed
npm run lint           # ng lint  — baseline + measurement
npm run lint -- --fix  # ESLint auto-fix (iteration 1)
npm run build          # ng build — MUST exit 0 (anti-regression net)
npm test -- --watch=false --browsers=ChromeHeadless   # MUST pass (anti-regression net)
```

Build + test are the **anti-regression net** : a lint fix that breaks the
build or a test is rolled back. Existing tests guarantee the lint pass does
not change behaviour (CLAUDE.md rule 1).

## Steps

### Step 0 — Pre-flight & mode/skip detection

1. **Working directory** : verify `Client/Mobile/` exists and contains
   `package.json` + `angular.json`. If `node_modules/` is missing, run
   `npm ci` once. If the directory is missing → Mode A : write
   `questions/{task-id}.md` and halt ; Mode B : print the error and exit.

2. **Mode detection** : argument present → Mode A (task-scoped) ; absent →
   Mode B (stand-alone).

3. **Mode A — skip detection** : read `**Repos**:` from
   `tasks/wip-{task-id}.md`. If `client-mobile` is **not** listed **AND**
   `git -C Client/Mobile diff --name-only origin/develop...HEAD` is empty
   (no mobile work on the feature branch) **AND** `git -C Client/Mobile
   status --porcelain` is empty, skip cleanly :
   - Append `## Lint mobile log\n- skipped — no mobile change\n` to the task.
   - Invoke `/review {task-id}` and exit.

4. **Mode A — branch sanity** : verify the feature branch
   `feat/{task-id}-{slug}` is checked out (it was created by `/start` and
   committed by `/develop`). If the working tree is on `develop` or another
   branch unexpectedly → write `questions/{task-id}.md` and halt.

### Step 1 — Baseline lint snapshot

Run `npm run lint` and parse the result :

- `baselineErrors`  — total ESLint errors
- `baselineWarnings` — total ESLint warnings
- `baselineFixable`  — auto-fixable count (errors + warnings)

If `baselineErrors == 0` AND `baselineWarnings == 0` :
- Mode A : log "lint clean → no work" in `## Lint mobile log`, hand off to
  `/review {task-id}`.
- Mode B : print "Lint clean, nothing to do" and exit.

### Step 2 — Iteration 1 : ESLint auto-fix

1. `npm run lint -- --fix` (ESLint auto-fixer).
2. `npm run build` then `npm test -- --watch=false --browsers=ChromeHeadless`.
3. **If build or tests go RED** → roll back the auto-fix
   (`git -C Client/Mobile checkout -- .` for tracked changes, or a
   patch-based revert) and halt the iteration loop : the auto-fix introduced
   a regression. Log it and proceed to hand-off with the residual baseline
   (best-effort — do NOT block the chain).
4. Re-run `npm run lint` to measure the new error/warning count.
5. **Early-stop** if `errorsAfter == 0` (warnings may remain — they don't
   block by convention).

### Step 3 — Iterations 2..5 : manual fixes

For each remaining iteration (max 5 total) :

1. Group residual errors by rule, pick the **top rule** (cap ~30 files /
   ~100 errors per iteration to keep diffs reviewable).
2. Classify each fix :
   - **Pure refactor** (formatting, unused imports, prefer-const, etc.) →
     apply directly.
   - **Behavioural** (anything that could change runtime behaviour) →
     **test-first** (CLAUDE.md rule 1) : adjust/add the adjacent `.spec.ts`
     before the fix.
3. `npm run build` + `npm test -- --watch=false --browsers=ChromeHeadless`
   after each batch.
4. **If RED** → patch-based rollback of that batch, then halt the loop
   (best-effort acceptance of the prior state). Do NOT leave the repo broken.
5. Re-lint, evaluate progression. **Stop** when : zero errors, no
   progression between two iterations, or 5 iterations done.

### Step 4 — Commit, push & hand-off

**Mode A — chained** :

1. Append `## Lint mobile log` to the task file :
   ```markdown
   ## Lint mobile log

   - Repo : client-mobile (Client/Mobile/, Ionic/Angular CLI)
   - Commands : npm run lint [-- --fix] / npm run build / npm test --watch=false --browsers=ChromeHeadless
   - Baseline : {N} errors / {M} warnings
   - Final    : {N'} errors / {M'} warnings
   - Iterations : {iter} / 5
   - Build / tests : ✓ green

   | Iter | Errors before | Errors after | Build | Tests |
   |------|---------------|--------------|-------|-------|
   | ...  | ...           | ...          | ✓     | ✓     |

   {residual block — remaining errors grouped by rule, if any}
   ```

2. **Feed `conventions/angular.md`** (workspace root) — the self-improving
   loop. For each ESLint rule fixed **manually** in this run (iterations
   2..5 — auto-fixer fixes don't count) on code written by `/develop` :
   - entry exists for the rule → increment **Occurrences**, append the
     task-id to **Origine** ;
   - no entry → create one (format documented at the top of the file),
     `Occurrences : 1`.
   The goal : `/develop` reads that file before coding, so the same rule
   never needs a manual fix twice. Skip this step when iteration 1
   (auto-fix) or a clean baseline handled everything.

3. **Commit + push the lint fixes** (full git automation — GitHub remote).
   Explicit staging only, NEVER `git add -A` :
   ```bash
   cd Client/Mobile
   git add {explicit-files}
   git commit -m "refactor(mobile): eslint cleanup (/lint-mobile) — {task-id}"
   git push origin feat/{task-id}-{slug}
   ```
   If nothing was actually changed (lint clean, or all fixes rolled back),
   skip the commit.

4. **Do NOT rename the task.** It stays in `wip-*` — `/review` owns the
   `wip → review → done` transitions.

5. Invoke `/verify-visual {task-id}` to continue the chain (it captures the
   touched mobile screens, then hands off to `/review` itself ; it
   self-skips to `/review` when no screen was touched). See
   `agents/verify-visual.md`.

**Mode B — stand-alone** :

1. Print the final report (same table) to stdout.
2. List the files modified : `git -C Client/Mobile diff --name-only`.
3. Do NOT commit / push (the human decides) unless explicitly asked. Exit.

## Rules

- **Scope** : `client-mobile` only (working directory `Client/Mobile/`).
  Never touches other repos.
- **Full git automation** : `client-mobile` has a GitHub remote and a
  `develop` branch, so `/lint-mobile` commits and pushes its fixes on the
  feature branch (unlike `/lint-angular`, which is code-only on TFS). It
  never merges on `develop` (HAG, CLAUDE.md rule 10) and never opens the PR
  (that's `/review`'s job).
- **Quality / lint only.** Bug & security hunting is `/code-review`. The
  existing tests are the anti-regression net.
- **Test-first on behavioural fixes** (CLAUDE.md rule 1) — adjacent
  `.spec.ts` (Jasmine/Karma).
- **Build + tests MUST pass after every iteration.** A fix that breaks them
  is rolled back (patch-based), then the loop halts best-effort.
- **Best-effort** : 5 iterations max, residual errors accepted and logged —
  not a chain blocker.
- **Skip cleanly** when the task didn't touch `client-mobile` (Repos field +
  diff/working-tree check) — hand straight off to `/review`.
- On any unexpected state (tooling crash, repo missing, working tree
  unrecognisable), stop and write `questions/{task-id}.md` (Mode A) or print
  the error (Mode B). Do NOT hand off to `/review` on a tooling failure.
