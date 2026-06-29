# /lint-mobile — Automated ESLint cleanup on client-mobile

Usage :
- `/lint-mobile {task-id}` — **Mode A (chained)**. Called by `/lint-angular`
  (or upstream by `/sonar` / `/forge-simplify` / `/develop` when neither
  api-mail nor client-angular was touched) inside the autonomous cycle.
  Operates on the feature branch `feat/{task-id}-{slug}` checked out in
  `Client/Mobile/`, best-effort 5 iterations, commits/pushes the fixes,
  hands off to `/review`.
- `/lint-mobile` (no argument) — **Mode B (stand-alone)**. Manual
  housekeeping on the current `Client/Mobile/` branch. No task file, no
  hand-off — prints the final report and exits (no commit unless asked).

Purpose : the `client-mobile` counterpart of `/lint-angular` — the mobile
messaging client (Ionic 8 + Angular 20 + Capacitor, `Client/Mobile/`, plain
Angular CLI, **not** Nx). After `/develop` writes mobile code, `/lint-mobile`
runs the ESLint auto-fixer then manually cleans the residual errors (capped
at 5 iterations, best-effort). It is the **last cleanup step** before
`/review`.

**Key difference from `/lint-angular`** : `client-mobile` is a **pushable**
repo (GitHub remote, `develop` branch), so `/lint-mobile` is in **full git
automation** — it commits and pushes its fixes on the feature branch. It
never merges on `develop` (HAG, rule 10) and never opens the PR (`/review`'s
job).

The agent uses plain Angular CLI commands (no Nx) :

```bash
cd Client/Mobile
npm run lint           # ng lint — baseline
npm run lint -- --fix  # ESLint auto-fix (iteration 1)
npm run build          # ng build — anti-regression net
npm test -- --watch=false --browsers=ChromeHeadless   # anti-regression net
```

Read `agents/lint-mobile.md` and execute the full playbook :

1. Pre-flight (working dir exists, `node_modules` present, mode detection,
   skip-cleanly check when no mobile work was done, feature-branch sanity)
2. Baseline lint snapshot (errors, warnings, fixable count)
3. Iteration 1 : `npm run lint -- --fix`, then build + test, re-lint to
   measure progress (rollback + halt best-effort on regression)
4. Iterations 2..5 : group errors by rule (top-1, max 30 files / 100 errors
   per iteration), classify pure-refactor vs behavioural (test-first for
   behavioural — CLAUDE.md rule 1), apply fixes, build + test, re-lint
5. Stop when : zero errors, no progression, or 5 iterations done
6. Hand-off :
   - Mode A : append `## Lint mobile log` to `tasks/wip-{task-id}.md`,
     commit + push the fixes (explicit staging, never `git add -A`), invoke
     `/review {task-id}` (autonomous, no human prompt).
   - Mode B : print the final report and exit (no commit unless asked).

Best-effort acceptance : remaining lint errors after 5 iterations are
**not** a chain blocker. They are logged in `## Lint mobile log` and the
cycle proceeds to `/review`.

The human merges the PR (HAG rule 10).

## Rules

- Scope : `client-mobile` only (working directory `Client/Mobile/`). Never
  touches other repos.
- **Full git automation** (GitHub remote) : commits + pushes the lint fixes
  on the feature branch. Never merges on `develop`, never opens the PR.
- Test-first on behavioural fixes (CLAUDE.md rule 1) — adjacent `.spec.ts`
  (Jasmine/Karma).
- Build + tests MUST pass after every iteration. If a fix breaks them,
  patch-based rollback then halt best-effort (the chain still proceeds to
  `/review` with the prior green state).
- Best-effort : 5 iterations max, residual errors accepted.
- Skip cleanly when the task didn't touch `client-mobile`.
- On any unexpected state (tooling crash, repo missing, working tree in an
  unrecognisable state), stop and write `questions/{task-id}.md` (Mode A) or
  print the error (Mode B). Do NOT hand off to `/review` on tooling failure.
