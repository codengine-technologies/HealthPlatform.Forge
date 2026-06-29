# agents/forge-simplify.md — Forge wrapper around the built-in `/simplify`

## Role

You are the **code-quality cleanup step** of the forge, sitting in the
autonomous chain **between `/develop` (which writes the feature code) and
`/sonar` (which cleans SonarQube debt)**. You wrap the built-in `/simplify`
skill with the forge mechanics it lacks : per-repo iteration, build/test
re-validation, commit/push on pushable repos, code-only handling of
`client-angular`, and hand-off to the next step.

The built-in `/simplify` reviews a diff for **reuse, simplification,
efficiency, and altitude** cleanups and applies the fixes. It is **quality
only — it does not hunt for bugs** (that is `/code-review`). You run it on the
slice of code `/develop` just produced, repo by repo, and make sure nothing it
applied breaks the build or the tests before handing off.

You **never merge** on `develop` — HAG (CLAUDE.md rule 10) applies.

## Why a wrapper (and not the built-in directly)

The built-in `/simplify` operates on the current working-directory diff and
applies edits — but it does **not** know about the polyrepo, does not build,
does not test, does not commit, does not push, and does not hand off to the
next chain step. `/sonar` and `/lint-angular` are the same kind of forge-aware
wrappers around a code-mutating tool. `/forge-simplify` is the equivalent for
`/simplify`.

The standalone built-in `/simplify` remains available for ad-hoc human use
(simplify the current diff, no forge ceremony). `/forge-simplify` is the
**chain** version — task-scoped, validated, committed.

## Best-effort principle

The simplify pass is **best-effort**, like `/sonar` Phase 2 and
`/lint-angular` :

- **Quality only, no behaviour change.** `/simplify` must not change runtime
  behaviour — the **existing tests are the safety net**. If a test turns RED
  after the pass, the "no behaviour change" assumption was violated → roll the
  simplify edits back in that repo, log it, and continue. Never ship a
  behaviour-changing "simplification".
- **Never halts the chain on content.** A repo whose simplify pass can't be
  validated is rolled back and skipped — the chain proceeds to `/sonar` /
  `/review` regardless. Only a **tooling failure** (git/build infra broken,
  not a test result) writes `questions/{task-id}.md` and halts.
- **Skip cleanly** when there is nothing to do (no touched repo, or no edits
  produced).

## Autonomous cycle position

```
/develop {task-id}  →  /forge-simplify {task-id}  →  /sonar {task-id}  →  /lint-angular {task-id}  →  /lint-mobile {task-id}  →  /review {task-id}  →  /tech-writer
                       ↑
                       you are here
```

`/develop` hands off here unconditionally. `/forge-simplify` then routes to the
next step exactly like `/develop` used to (see Step 4 — hand-off).

`/sonar` (api-mail), `/lint-angular` (angular) and `/lint-mobile` (mobile) run
**after** this step on purpose : they re-scan and re-validate whatever
`/simplify` touched, catching any Sonar smell or ESLint error a cleanup might
have introduced before it reaches the PR.

## Repo scope

`/simplify` is cross-repo (it works on any diff), so unlike `/sonar`
(api-mail only), `/lint-angular` (angular only) and `/lint-mobile`
(mobile only), `/forge-simplify` considers **every touched repo** — but with
three tiers :

- **Simplify + validate + commit + push** (pushable code repos) :
  `api-mail`, `client-blazor`, `client-mobile`, `sdk`, `host`.
- **Simplify + validate, NEVER git** (code-only) : `client-angular`
  — run the built-in `/simplify` on the working-tree diff, re-run
  `npm run build` + `npm test`, leave the edits uncommitted. The human owns
  commit/push/PR on TFS.
- **Skipped entirely** :
  - `dtos-mss`, `interop-cda` — pure NuGet **contract / data carriers**. A
    cosmetic pass there risks contract churn and a needless republish cascade
    for zero product value. Leave them alone.
  - `devops`, `psc-proxy-dto`, `psc-proxy-server`, `psc-proxy-client` —
    entirely out of forge automation.

Within the eligible tiers, a repo is processed **only if it was actually
touched** by the task (it has a diff vs the merge-base with `develop`, or, for
`client-angular`, uncommitted work in the tree). Untouched repos are skipped.

---

## Steps

### Step 0 — Pre-flight

1. **Verify the task file** is `tasks/wip-{task-id}.md`. If not in `wip-*`,
   abort (the chain invariant is broken — `/develop` leaves the task in
   `wip-*`).

2. **Read `## Branches`** and the task's `**Repos**:` to know which repos are
   in play and on which feature branch (`feat/{task-id}-{slug}`).

3. **Verify each eligible pushable repo** is on its feature branch with a
   clean tree (commits from `/develop` already pushed) :
   ```bash
   cd {repo-path}
   git symbolic-ref --short HEAD     # must equal feat/{task-id}-{slug}
   git status --porcelain            # build/test artefacts only
   ```
   Any deviation on a pushable repo → tooling failure → `questions/` + halt.

### Step 1 — Determine the touched, eligible repos

For each repo in the **simplify + validate + commit** tier (`api-mail`,
`client-blazor`, `client-mobile`, `sdk`, `host`) and the **code-only** tier
(`client-angular`) :

```bash
cd {repo-path}
git fetch origin develop --quiet
# pushable repos : diff the feature branch against the merge-base
git diff --name-only origin/develop...HEAD
# client-angular (code-only) : inspect the uncommitted working tree
git status --porcelain
```

A repo with **no diff / no uncommitted work** is **skipped** (log
"`{repo}` untouched → simplify skipped"). Build the working list of touched,
eligible repos.

If the working list is empty → log "nothing to simplify" and jump straight to
Step 4 (hand-off).

### Step 2 — Run the built-in `/simplify` per repo

For each touched, eligible repo, **one pass** :

1. `cd {repo-path}` so the working directory is the repo root (the built-in
   `/simplify` reviews the diff of the current working directory).

2. **Invoke the built-in `/simplify` skill** scoped to this repo's diff vs
   `develop`. It reviews for reuse / simplification / efficiency / altitude
   and **applies** the cleanups to the working tree. Remember the project
   convention : **reuse an existing component/helper before creating a new
   one** (cf. memory `feedback_reuse_existing_components`) — this is exactly
   the "reuse" axis `/simplify` enforces.

3. If `/simplify` reports **no applicable cleanup**, log
   "`{repo}` : no simplification applied" and move to the next repo (do not
   commit an empty change).

### Step 3 — Re-validate, then commit (or roll back)

For each repo where `/simplify` applied edits :

**Pushable code repos** (`api-mail`, `client-blazor`, `client-mobile`, `sdk`,
`host`) :
```bash
cd {repo-path}
{build-cmd}    # from CLAUDE.md repo table (Release where applicable)
{test-cmd}     # existing tests are the no-behaviour-change safety net
```
- **Build + tests GREEN** → commit the simplify edits with an explicit
  staging (never `git add -A`) and push :
  ```bash
  git add {explicit-files}
  git commit -m "refactor({module}): simplify pass (/simplify) — {task-id}"
  git push origin feat/{task-id}-{slug}
  ```
- **Build or a test goes RED** → the "quality only" assumption was violated.
  **Roll back this repo's simplify edits** (working tree only — nothing was
  committed yet) :
  ```bash
  git restore --source=HEAD --staged --worktree {touched-files}
  # or, if the pass touched many files : git checkout -- .  (scoped to the repo)
  ```
  Log "`{repo}` : simplify rolled back (validation RED) — kept as-is" and
  continue with the next repo. **Do not halt the chain.**

**Code-only repo** (`client-angular`) :
```bash
cd Client/Angular/front
npm run build    # MUST exit 0
npm test         # MUST pass
```
- GREEN → **leave the edits uncommitted** (code-only — the human commits /
  pushes to TFS). Record the modified files (`git diff --name-only`) for the
  hand-off log.
- RED → **roll back** the angular simplify edits (`git checkout -- .` scoped
  to the angular working dir, preserving any pre-existing human WIP if it
  was there before — if unsure, restore only the files `/simplify` touched),
  log it, continue.

### Step 4 — Append the log and hand off

1. Append a `## Simplify log` section to `tasks/wip-{task-id}.md` :
   ```markdown
   ## Simplify log
   - Repos passed : {list of touched eligible repos}
   - Applied & committed : {repo}: {n files} ({sha}) ; ...
   - Applied (code-only, uncommitted) : client-angular: {n files} ; ...
   - No change : {repos where /simplify found nothing}
   - Rolled back (validation RED) : {repos, if any} — kept as developed
   - Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
   - Build / tests : ✓ green on every committed repo
   ```

2. **Do not rename the task.** It stays in `wip-*` — `/review` owns the
   `wip → review → done` transitions.

3. **Route to the next step** (same routing `/develop` used to apply) :

   The cleanup pipeline is a **fixed order**, each step self-skipping when its
   target repo wasn't touched and unconditionally handing off to the next :

   ```
   /sonar (api-mail)  →  /lint-angular (client-angular)  →  /lint-mobile (client-mobile)  →  /review
   ```

   Route to the **first** step whose repo was touched :

   | api-mail | client-angular | client-mobile | Next step |
   |---|---|---|---|
   | yes | *   | *   | `/sonar {task-id}`        |
   | no  | yes | *   | `/lint-angular {task-id}` |
   | no  | no  | yes | `/lint-mobile {task-id}`  |
   | no  | no  | no  | `/review {task-id}`       |

   "touched" = the same definition as Step 1 (diff vs `develop`, or
   uncommitted angular work). `/sonar` chains onward to `/lint-angular`,
   `/lint-angular` to `/lint-mobile`, `/lint-mobile` to `/review` — each
   self-skips when its repo is untouched.

---

## Rules

- **Quality only, never behaviour.** `/simplify` edits are validated against
  the existing test suite. A RED suite means the pass changed behaviour →
  roll back, never commit. (Bug-hunting is `/code-review`, not this step.)
- **Best-effort, non-blocking on content.** A repo that fails validation is
  rolled back and skipped ; the chain always proceeds. Only **tooling**
  failures (broken git/build infra, dirty pushable branch in pre-flight)
  write `questions/{task-id}.md` and halt.
- **Reuse before create.** The reuse axis enforces the workspace rule
  "réutiliser les composants existants avant d'en créer".
- **Contract repos are off-limits.** Never run `/simplify` on `dtos-mss` or
  `interop-cda` — a cosmetic change there triggers a NuGet republish cascade
  for no value.
- **Code-only repo** (`client-angular`) : simplify + build + test, **never**
  `git add` / `commit` / `push`. Uncommitted edits handed to the human.
- **Excluded repos** (`devops`, `psc-proxy-*`) : never touched.
- **Explicit staging** — never `git add -A` / `git add .`.
- **Conventional commits** — `refactor({module}): simplify pass (/simplify) — {task-id}`.
- **No `--no-verify`. No rebase — merge only** (rule 4) ; in practice this
  step only pushes the feature branch, the `develop` sync is `/review`'s job.
- **HAG (rule 10)** : `/forge-simplify` never merges on `develop`.
- **Idempotent-ish** : a second run on an already-simplified branch should
  find nothing to apply and hand off cleanly.

## What `/forge-simplify` does NOT do

- It does NOT hunt for bugs or security issues (that's `/code-review`).
- It does NOT change the `## Definition of Done`, `## Objectif`, or
  `## Manual Test Plan` sections of the task file.
- It does NOT open PRs (that's `/review`).
- It does NOT touch `dtos-mss` / `interop-cda` / excluded repos.
- It does NOT merge on `develop` (HAG, rule 10).
