# /merge — Merge the PRs of a done task and sync `develop`

Usage : `/merge {task-id} --i-tested` (e.g. `/merge task-017 --i-tested`)

Purpose : once the human has manually validated the US end-to-end (HAG,
CLAUDE.md rule 10) on the PRs opened by `/review`, `/merge` automates the
clean-up : squash-merge each PR, delete the feature branches, sync each
local clone back to `develop`, verify CI is green, and archive the task
file. This shaves the per-task ceremony when a US touches 3+ repos.

**`/merge` is human-triggered only.** It is **not** invoked by the
autonomous chain (`/forge` stops at PR-opening). The forge never merges
on its own — HAG (rule 10) is non-negotiable.

The `--i-tested` flag is mandatory : it is the human's explicit
attestation that they have run the Manual Test Plan and validated the
US. Without it, `/merge` refuses and prints the test plan as a reminder.

See `agents/merge.md` for the agent specification.

## Quick reference

```
/merge task-017 --i-tested
```

Steps (high-level — see the agent file for the full spec) :

1. Read `tasks/done-{task-id}.md` and parse `## PRs`.
2. Verify safety gates : `--i-tested` present, no `awaiting-us-completion`
   label, CI green, no `CHANGES_REQUESTED` review, branch up-to-date with
   `develop`, no uncommitted changes.
3. Squash-merge each pushable PR in topological order
   (`dtos-mss → interop-cda → api-mail → client-blazor`) with `gh pr merge
   --squash` (never `--delete-branch`), then delete the **remote** ref only
   via `git push origin --delete` — the **local** branch is kept.
4. Ask whether the human merged the `client-angular` TFS PR ; if yes,
   switch the local Angular clone back to `develop`.
5. Wait up to 2 min for CI green on `develop` (rule 5).
6. Move `tasks/done-{task-id}.md → tasks/archived/archived-{task-id}.md`
   (creates the `tasks/archived/` subdir if missing) and append a
   `## Merged` section with the squash commit SHAs.
7. Report.

## When NOT to use `/merge`

- If the US is not yet end-to-end testable (rule 11 — wait for all waves
  to be in PR-ready state, then test the assembled US, then `/merge`).
- If you want to merge only some repos and leave others open. `/merge` is
  all-or-nothing per task — partial merges create inconsistent `develop`.
  Merge by hand via `gh pr merge` for that case.
- If the task is still in `wip-*` or `review-*`. Run `/review` first.

## Safety

- `/merge` aborts on the first failing gate and writes
  `questions/merge-{task-id}.md`. No PR is merged unless **all** gates
  pass for **all** pushable PRs.
- Squash-merge only (linear history on `develop`).
- Never force-push, never touch `develop` history.
