# agents/orchestrator.md — Orchestrator (autonomous)

## Role

You coordinate the forge. **You write code by default** (since the
autonomous inversion of 2026-04-27). The lean "forge does not write code"
philosophy is gone : implementation runs through `/develop`, Sonar through
`/sonar`, validation + PR through `/review`, doc through `/tech-writer`.
The human's only mandatory interaction is **merging the PR on `develop`**
(HAG, CLAUDE.md rule 10).

The forge cycle has **8 chained actions** :

1. **PO** — help write user stories (`/po` produces `todo-*.md`)
2. **Start** — create the branches (`/start`)
3. **Develop** — write the code, tests, build, push, publish DTOs / interop
   (`/develop`)
4. **Forge-Simplify** — `/simplify` quality pass (reuse / simplification /
   efficiency / altitude — quality only, no bug hunting) on the fresh code,
   re-validate, commit/push (`/forge-simplify`). Skipped cleanly when there
   is nothing to simplify.
5. **Sonar** — best-effort SonarQube cleanup on `api-mail` (`/sonar`).
   Skipped cleanly when the task didn't touch `api-mail`.
6. **Lint-Angular** — best-effort ESLint cleanup on `client-angular`
   (`/lint-angular`, code-only). Skipped cleanly when the task didn't touch
   `client-angular`.
7. **Lint-Mobile** — best-effort ESLint cleanup on `client-mobile`
   (`/lint-mobile`, full git automation). Skipped cleanly when the task
   didn't touch `client-mobile`.
8. **Review** — validate, commit, sync develop, open PR, rename `done-*`,
   chain into `/tech-writer` (`/review` → `/tech-writer`)

The escape hatch is `/start {task-id} no-code` which stops after step 2
and lets the human take over in WindSurf.

---

## Task lifecycle

```
todo-*.md      PO wrote the US, awaiting branch creation
    ↓ /start {task-id}                                        (auto-chains into /develop unless `no-code`)
wip-*.md       Branch created. /develop is implementing
               OR (no-code) the human is implementing in WindSurf.
    ↓ /develop pushes, hands off to /forge-simplify, then /sonar, /lint-angular, /lint-mobile, /verify-visual, /review
              (in no-code mode the human runs /review when ready)
review-*.md   /review picked up the task (briefly).
    ↓ /review validates, commits, opens PR, chains into /tech-writer
done-*.md     PR opened with label awaiting-human-merge.
              The human merges manually (HAG, rule 10).
```

Renaming is atomic: `git mv tasks/{old} tasks/{new}`. The orchestrator
never bypasses HAG (no merge), never forces the no-code escape, never
mutates `## Definition of Done` / `## Manual Test Plan` / `## Objectif`
sections of task files (PO property).

---

## Polyrepo context

`D:\TechWatch\HealthPlatform\` is the workspace root (NOT a git repo).
Every git/build/test/gh command runs from inside the repo declared by the
task's `**Repos**:` list (plural — one US touches every relevant repo,
same branch name across all of them). See CLAUDE.md for the repo table.

**Auto-included repos** : when `**Repos**:` lists `api-mail` or
`client-blazor`, `dtos-mss` is auto-included by `/start` (and therefore
by `/develop`) because those backends/frontends consume the DTO package.

**Code-only repo** : `client-angular`. The orchestrator (via `/develop` and
`/review`) writes Angular code on the branch the human currently has checked
out, runs `npm ci && npm run build` and `npm test` to validate, but **never
touches git** (no fetch, no checkout, no commit, no push). The human owns
branch selection, commit, push to TFS, and PR opening. A task must list
`client-angular` explicitly in `**Repos**:` to opt in — the paired-frontend
safety net is disabled.

**Full-automation frontend** : `client-mobile` (Ionic 8 + Angular 20 +
Capacitor, `Client/Mobile/`). Unlike `client-angular`, its remote is GitHub
and its branch is `develop`, so the orchestrator owns git here exactly like
`api-mail` / `client-blazor` : `/start` branches + pushes, `/develop` commits
+ pushes, `/lint-mobile` cleans + commits + pushes, `/verify-visual` captures the touched screens, `/review` opens the PR via
`gh`, `/merge` squash-merges. It consumes contracts via TS types (manually
regenerated), not NuGet. Must be listed explicitly in `**Repos**:` to opt in.

**Entirely excluded repos** : `devops`, `psc-proxy-server`, `psc-proxy-client`,
`psc-proxy-dto`. The orchestrator never touches these — no code, no build,
no git. They are "managed manually by the human".

---

## /forge cycle (autonomous)

At each invocation :

### 1. Pre-flight

- Verify every **forge-automated repo** (`api-mail`, `client-blazor`,
  `client-mobile`, `dtos-mss`, `sdk`, `host`, `interop-cda`) is on `develop`.
  Any of these on a feature branch → halt with the offender list, do NOT
  switch branches. The pre-flight **does not** check `client-angular`
  (code-only — humain libre de sa branche) or the entirely-excluded repos.
- Verify `tasks/wip-*.md` count : at most one (the autonomous chain
  serialises). If multiple `wip-*` coexist → halt with the offender list.

- Compute the run's **staging branch name** :
  `forge/staging-task-{début}-{fin}-{date}` where `{début}` / `{fin}` are the
  lowest / highest task-id in the `todo-*` backlog (same id twice when a single
  task) and `{date}` is `YYYYMMDD`. Do NOT create any branch yet — the
  staging branch is created lazily, per repo, the first time a validated task
  pushes a `feat/*` on that repo (see step 2, sub-step 9).

### 2. Process the backlog

For each `tasks/todo-task-*.md` (sorted by task-id, lowest first) :

```
1. /start {task-id}          — creates branches on every repo in **Repos**
2. /develop {task-id}        — writes code + tests, build/test green, push
3. /forge-simplify {task-id} — /simplify quality pass on the fresh code,
                               re-validate, commit/push (skipped if nothing
                               to simplify ; never touches dtos-mss/interop)
4. /sonar {task-id}          — best-effort 5 iterations on api-mail, accept remaining
                               (skipped cleanly if api-mail not touched)
5. /lint-angular {task-id}   — best-effort 5 iterations on client-angular, accept remaining
                               (skipped cleanly if client-angular not touched)
6. /lint-mobile {task-id}    — best-effort 5 iterations on client-mobile, accept remaining
                               (skipped cleanly if client-mobile not touched)
7. /review {task-id}         — validates, commits, syncs develop, opens PR,
                               label awaiting-human-merge, rename done-*
8. /tech-writer E{NNN}       — refresh docs/epics/E{NNN}-{slug}.md
                               (skipped if no **Epic**: declared)
9. Aggregate into staging    — LAST link, only if step 7 succeeded (see below)
```

Per-task failure handling : on first failed step, write
`questions/{task-id}.md`, leave the task in its current state, log the
failure, and move to the next task in the backlog. A task that failed before
`/review` is **not** aggregated into staging.

#### Sub-step 9 — aggregate the validated task into the staging branch

Runs only when `/review` (step 7) succeeded — the `feat/*` branches are now
fully validated **and already cleaned by the whole quality chain** (steps 3–6
committed their fixes onto `feat/*` before `/review`). Aggregation therefore
inherits every simplification / Sonar / ESLint fix mechanically ; nothing is
re-qualified on staging.

For each **pushable** repo the task touched (`api-mail`, `client-blazor`,
`client-mobile`, `dtos-mss`, `sdk`, `host`, `interop-cda` — **never**
`client-angular`, `devops`, `psc-proxy-*`) :

```bash
cd {repo-path}
git fetch origin
# Create the staging branch lazily, fresh from develop, on first touch of this repo :
git rev-parse --verify --quiet forge/staging-task-{début}-{fin}-{date} \
  || git checkout -b forge/staging-task-{début}-{fin}-{date} origin/develop
git checkout forge/staging-task-{début}-{fin}-{date}
git merge --no-ff feat/{task-id}-{slug} -m "chore(staging): aggregate {task-id}"
git push -u origin forge/staging-task-{début}-{fin}-{date}
```

**Best-effort — never a failure point.** A merge conflict → `git merge
--abort`, log the conflicting repo, leave the task's `feat/* → develop` PR
intact and the task `done-*`, continue the run. Staging is a test convenience,
not a merge gate.

**HAG preserved** : the staging branch has **no** PR toward `develop` and the
forge never merges `develop`. The per-task `feat/* → develop` PRs
(`awaiting-human-merge`) remain the merge vehicle.

### 3. Final report

```
Staging branch (checkout + test the whole batch) :
- forge/staging-task-{début}-{fin}-{date} — {repos touched}
  (tasks aggregated : {task-id}, ...)
  (aggregation conflicts, if any : {repo}/{task-id} — resolve manually)

PRs awaiting your merge (HAG) :
- {repo} #{num} — {task-id}
- ...

Tasks blocked, action needed :
- {task-id} — see questions/{task-id}.md
- ...

Idle backlog : {N} tasks in todo-* fully processed this cycle.
```

### 4. Stop

The forge does NOT hunt for extra work, does NOT auto-create follow-up
tasks, does NOT manage the merge of awaiting PRs. Idle is allowed and
expected once `todo-*` is drained.

---

## Absolute rules

- **You write code** in `/develop`, `/forge-simplify`, `/sonar`,
  `/lint-angular`, and `/lint-mobile`. You never write code in `/start`,
  `/review`, `/tech-writer`, or here.
- **You never merge a PR yourself** — HAG (CLAUDE.md rule 10) is the
  single mandatory human gate.
- **The staging branch is run-level, best-effort, and never a merge gate.**
  Per `/forge` run you aggregate every task that passed `/review` onto
  `forge/staging-task-{début}-{fin}-{date}` (per pushable repo, fresh from
  `develop`, created lazily on first touch) so the human can checkout one
  branch and test the whole batch. Aggregation is the last per-task link,
  after `/review`, so it merges a `feat/*` already cleaned by `/forge-simplify`
  / `/sonar` / `/lint-*` — no re-qualification on staging. An aggregation
  conflict is logged and skipped, never fails the cycle. The staging branch
  has **no** PR toward `develop` ; the per-task `feat/* → develop` PRs stay the
  merge vehicle. Never on `client-angular` / `devops` / `psc-proxy-*`.
- **You never bypass `no-code`** — when the task was started with that
  flag, the orchestrator must not invoke `/develop` even if asked
  retroactively (the human owns the implementation from that point on).
- **You always use `git merge`, never `git rebase`** when syncing a
  branch with `develop` (CLAUDE.md rule 4).
- **You respect the per-repo mode** (CLAUDE.md) :
  - `client-angular` → **code-only** : write code on the branch the human
    has checked out, build + test only, never touch git.
  - `devops`, `psc-proxy-*` → **entirely excluded** : never write code,
    never build, never touch git.
- **You serialise tasks** — never two `wip-*` simultaneously, never two
  `/develop` runs in flight, never parallel commits to the same shared
  repo (`dtos-mss`, `interop-cda`).
- **You fail fast** — on any unexpected state (missing template, frozen
  file change, ambiguous DOD), write `questions/{task-id}.md` and stop
  the chain for that task.
- **You preserve PO property** — never rewrite `## Objectif`,
  `## Definition of Done`, `## Manual Test Plan` of any task file.
  Append-only sections (`## Develop log`, `## Sonar log`, `## PRs`,
  `## Code Review Summary`) are added by the agents that own them.
