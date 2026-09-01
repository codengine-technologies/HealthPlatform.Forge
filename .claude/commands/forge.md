# /forge — Autonomous forge loop

Read `agents/orchestrator.md` and execute the autonomous loop on the current
backlog.

## Behaviour

For each `tasks/todo-task-*.md` (lowest task-id first), run the full
autonomous chain :

```
/start {task-id}    → /develop {task-id}    → /sonar {task-id}    → /lint-angular {task-id}    → /lint-mobile {task-id}    → /review {task-id}    → /tech-writer E{NNN}
```

`/develop` now carries the `/simplify` quality pass itself (reuse /
simplification / efficiency / altitude — quality only, no bug hunting), applied
per repo right after the feature code is green and before the push : the former
`/forge-simplify` chain step was merged into it on 2026-08-31 to stop paying a
second full build + test per repo. `/sonar`, `/lint-angular` and `/lint-mobile` skip
cleanly when their target repo wasn't touched (no api-mail change → `/sonar`
is a no-op ; no client-angular change → `/lint-angular` is a no-op ; no
client-mobile change → `/lint-mobile` is a no-op). All are best-effort
and hand off to the next step even if residual issues remain.

Sequentially, not in parallel. Cross-task interference on shared repos
(branches, package versions, `Directory.Packages.props`) makes parallel
execution unsafe.

## ⏱️ Instrumentation du run (obligatoire)

Un run `/forge` regroupe ses mesures sous un **run id**. Les variables
d'environnement ne survivent pas d'un appel Bash à l'autre, donc le run id vit
dans un fichier — écrit au démarrage, supprimé à la fin :

```bash
# au tout début du run, une fois le backlog connu
mkdir -p metrics/.state
echo "forge-{YYYYMMDD}-{début}-{fin}" > metrics/.state/run_id

# ... les tasks s'exécutent, chaque étape mesure ...

# à la toute fin du run, avant le rapport
rm -f metrics/.state/run_id
```

Chaque étape de la chaîne borne et mesure elle-même (voir la section
« Instrumentation » de son fichier de commande) ; `/forge` n'a que le run id à
gérer, plus deux lignes de restitution dans le rapport final :

```bash
Tools/timing/report.sh --last {N}    # une ligne par task du run
Tools/timing/report.sh --by-kind     # combien de builds / tests / scans par task
```

**Le rapport de run n'est jamais silencieux sur le coût** — comme il ne l'est
jamais sur la qualité Sonar. C'est cette restitution qui permet de comparer un
run au précédent et de valider (ou d'invalider) chaque optimisation de la
chaîne.

---

## Staging branch (per run)

Each `/forge` run aggregates the fully-validated work of all its tasks onto a
single **staging branch per pushable repo**, so the human can `git checkout`
**one** branch and test the whole batch end-to-end instead of juggling N
feature branches.

- **Naming** : `forge/staging-task-{début}-{fin}-{date}` where `{début}` /
  `{fin}` are the lowest / highest task-id in the run's `todo-*` backlog
  (collapse to the same id when a single task, e.g.
  `forge/staging-task-159-159-20260716`) and `{date}` is `YYYYMMDD`. The
  same branch name is used across every repo.
- **Fresh from `develop`** : created lazily from `origin/develop` the first
  time a successful task pushes a `feat/*` on that repo — never reused across
  runs, never stale. Repos a run never touches get no staging branch (no
  empty branches).
- **Scope** : pushable repos only — `api-mail`, `client-blazor`,
  `client-mobile`, `dtos-mss`, `sdk`, `host`, `interop-cda`. **Never**
  `client-angular` (code-only, no git), `devops`, `psc-proxy-*` (excluded).
- **Aggregation is the last per-task link, after `/review`** : it merges
  (`git merge --no-ff feat/{task}-{slug}`) the feature branch **already
  cleaned by the full quality chain** — `/develop`'s `/simplify` pass,
  `/sonar`, `/lint-angular`, `/lint-mobile` all committed their fixes onto `feat/*`
  *before* `/review`. Staging inherits every quality fix mechanically ;
  nothing is re-qualified on staging (redundant, and staging has no PR).
- **Best-effort, never a failure point** : an aggregation merge conflict →
  abort that merge, log it, leave the task's `feat/* → develop` PR intact and
  the task `done-*`. Staging is a test convenience, never blocks the cycle.
- **HAG preserved, no staging PR** : the per-task `feat/* → develop` PRs
  (label `awaiting-human-merge`) are unchanged and remain the merge vehicle.
  The staging branch has **no** PR toward `develop` — you check it out, test
  the batch, then merge the per-task PRs you're happy with. The forge never
  merges `develop` (HAG, CLAUDE.md rule 10).
- **Only validated tasks are aggregated** : a task enters staging only once it
  passes `/review` (build + tests + DOD + code review green). `/sonar` and the
  lint steps are best-effort and never block aggregation ; a red build/test or
  CHANGES_REQUESTED keeps the task out of staging (no unvalidated code in the
  test branch).

## Per-task halt conditions

If any step fails (`/develop` blocker, Sonar tooling failure, `/review`
CHANGES_REQUESTED, build/test red on `develop` after merge), the chain
halts for that task :

- A `questions/{task-id}.md` is written by the failing step
- The task stays in whatever state the failing step left it
  (`wip-*` if `/develop` or `/sonar` halted, `review-*` if `/review` halted)
- `/forge` logs the failure and **moves to the next task** in `todo-*`

Hard halt of the loop only happens if pre-flight on the workspace itself
fails (e.g. some repo isn't on `develop` and the human hasn't cleaned up).

## Per-cycle output

```
/forge — autonomous loop
========================

Backlog : N tasks in todo-*
Staging : forge/staging-task-018-019-20260716 (fresh from develop, per repo)

Task task-018 — feat(mail) ...
  /start        : ✓ branches created on api-mail, client-blazor, dtos-mss
  /develop      : ✓ commits pushed (api-mail @abc1234, client-blazor @def5678, dtos-mss @9876543)
                  passe qualité : api-mail @bcd2345 (3 files simplified), client-blazor no change
  /sonar        : ✓ 3 iterations, 12 issues fixed, 4 remaining (best-effort)
  /lint-angular : ⤍ skipped — no angular change
  /lint-mobile  : ⤍ skipped — no mobile change
  /review       : ✓ APPROVED, 3 PRs opened (#42, #43, #44, label awaiting-human-merge)
  staging       : ✓ feat/task-018-... merged into forge/staging-... (api-mail, client-blazor, dtos-mss)
  /tech-w.      : ✓ docs/epics/E009-... updated
  coût          : 34 min (11 builds, 9 suites, 3 scans) — cf. ## Timings du task file

Task task-019 — fix(audit) ...
  /start    : ✓
  /develop  : ✗ blocker — questions/task-019.md created
  → skipping to next task (not aggregated into staging)

...

Staging branch (checkout + test the whole batch) :
- forge/staging-task-018-019-20260716 — api-mail, client-blazor, dtos-mss
  (tasks aggregated : task-018)

Coût du run (Tools/timing/report.sh --by-kind) :
- 2 tasks mesurées — 1 h 12 min cumulées
- build ×19 (2 min médiane) | test ×14 (4 min médiane) | scan ×5
- poste le plus lourd : /sonar (42 % du temps mesuré)

PRs awaiting your merge (HAG, rule 10) :
- api-mail #42, client-blazor #43, dtos-mss #44 (task-018)
- api-mail #38 (task-014, from previous run)

Tasks blocked, action needed :
- task-019 — see questions/task-019.md
```

## Stop conditions

- All `todo-*` processed → loop ends, summary printed
- Workspace pre-flight fails (some repo not on `develop`) → loop refuses
  to start, prints the offending repos
- Genuine emergency stop : the user interrupts manually

## Rules

- **Sequential only.** Never two tasks in flight at once.
- **HAG (rule 10) is preserved.** The forge never merges a PR onto `develop`.
  Each task ends with a `feat/* → develop` PR labelled `awaiting-human-merge`.
  The staging branch is an aggregation of `feat/*` branches for testing — it
  has no PR toward `develop` and never merges `develop`.
- **Staging is best-effort and run-level.** It aggregates only tasks that
  passed `/review`, after the full quality chain (`/develop`'s `/simplify`
  pass, `/sonar`, `/lint-*`) has already baked its fixes into `feat/*`. An aggregation merge
  conflict is logged and skipped — it never fails the cycle nor touches the
  per-task PR.
- **No retry.** A failed task moves to `questions/` and is skipped — the
  human triages and re-runs the chain (or fixes manually) when ready.
- **No backlog hunting beyond `todo-*`.** The forge does not invent work,
  does not "find extra effort", does not auto-create chore tasks. If
  `todo-*` is empty, output "nothing to do" and exit.
- **No-code escape** : if a task needs `/start {task-id} no-code`, the
  human is expected to invoke `/start` directly with that flag. `/forge`
  does not infer when to use `no-code`.
