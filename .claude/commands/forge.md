# /forge — Autonomous forge loop

Read `agents/orchestrator.md` and execute the autonomous loop on the current
backlog.

## Behaviour

For each `tasks/todo-task-*.md` (lowest task-id first), run the full
autonomous chain :

```
/start {task-id}    → /develop {task-id}    → /sonar {task-id}    → /lint-angular {task-id}    → /review {task-id}    → /tech-writer E{NNN}
```

`/sonar` and `/lint-angular` skip cleanly when their target repo wasn't
touched (no api-mail change → `/sonar` is a no-op ; no client-angular
change → `/lint-angular` is a no-op). Both are best-effort 5-iteration
loops that hand off to the next step even if residual issues remain.

Sequentially, not in parallel. Cross-task interference on shared repos
(branches, package versions, `Directory.Packages.props`) makes parallel
execution unsafe.

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

Task task-018 — feat(mail) ...
  /start        : ✓ branches created on api-mail, client-blazor, dtos-mss
  /develop      : ✓ commits pushed (api-mail @abc1234, client-blazor @def5678, dtos-mss @9876543)
  /sonar        : ✓ 3 iterations, 12 issues fixed, 4 remaining (best-effort)
  /lint-angular : ⤍ skipped — no angular change
  /review       : ✓ APPROVED, 3 PRs opened (#42, #43, #44, label awaiting-human-merge)
  /tech-w.      : ✓ docs/epics/E009-... updated

Task task-019 — fix(audit) ...
  /start    : ✓
  /develop  : ✗ blocker — questions/task-019.md created
  → skipping to next task

...

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
- **HAG (rule 10) is preserved.** The forge never merges a PR. Each
  task ends with a PR labelled `awaiting-human-merge`.
- **No retry.** A failed task moves to `questions/` and is skipped — the
  human triages and re-runs the chain (or fixes manually) when ready.
- **No backlog hunting beyond `todo-*`.** The forge does not invent work,
  does not "find extra effort", does not auto-create chore tasks. If
  `todo-*` is empty, output "nothing to do" and exit.
- **No-code escape** : if a task needs `/start {task-id} no-code`, the
  human is expected to invoke `/start` directly with that flag. `/forge`
  does not infer when to use `no-code`.
