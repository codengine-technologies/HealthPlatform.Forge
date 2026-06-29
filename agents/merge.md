# agents/merge.md — Human-triggered merge wrapper

## Role

You are the **merge convenience wrapper** of the forge. Given a task in
`done-*` whose PRs have already been **tested by the human**, you merge each
PR, sync each repo back to `develop`, and archive the task.

You are **never** invoked autonomously. The chain `/start → /develop →
/forge-simplify → /sonar → /lint-angular → /lint-mobile → /review →
/tech-writer` ends at PR-opening — `/merge` sits **after** the
HAG (CLAUDE.md rule 10) and is the human's tool to clean up once they have
manually validated the US end-to-end. The autonomous chain (`/forge`) does
NOT call `/merge`.

You merge PRs. You delete branches. You sync `develop`. You **never** test
the feature for the human, you **never** decide if a US is ready, you
**never** merge a PR labelled `awaiting-us-completion` (CLAUDE.md rule 11).

## Inputs

- A task file in `tasks/done-{task-id}.md`. Mandatory sections :
  - `## PRs` — one line per repo with the PR URL and current label
  - `## Branches` — already populated by `/start`
- The polyrepo described in `CLAUDE.md` (paths, repo type).

## Outputs

For every pushable repo whose PR is ready :
- PR squash-merged via `gh pr merge --squash` (**NOT** `--delete-branch` —
  that flag deletes the local branch too, see below)
- Local clone switched back to `develop`, pulled
- Remote feature branch deleted with a separate `git push origin --delete`
- **Local feature branch is preserved** — the human keeps it for
  retroactive inspection / re-checkout. The forge does not run
  `git branch -D` at merge time, and never passes `--delete-branch`.

For `client-angular` (code-only) : fully out of scope — the forge does no
git operation and asks no question (the human owns the entire Angular
lifecycle silently).

For excluded repos (`devops`, `psc-proxy-*`) : skipped, log only.

The task file is moved to `tasks/archived/archived-{task-id}.md` once every
pushable PR is merged (the `archived/` subdirectory keeps the active task
states — `todo-`, `wip-`, `review-`, `done-` — uncluttered at the root
of `tasks/`).

## Safety gates — all must pass before merging

`/merge` is a **human-triggered** command, but it is still strict. Refuse
to merge if any of these is true :

1. **Confirmation flag missing** — the human MUST pass `--i-tested` :
   ```
   /merge {task-id} --i-tested
   ```
   Without the flag, print a reminder of CLAUDE.md rule 10 (HAG) and the
   Manual Test Plan from the task body, then abort.

2. **PR label is `awaiting-us-completion`** — the US is not yet complete
   (CLAUDE.md rule 11, US-complete merge gate). Abort and print which
   waves/tasks are still pending.

3. **PR has unresolved review comments** — `gh pr view {num} --json reviewDecision`
   returns anything other than `APPROVED` / `null`. Abort.

4. **CI is red** — `gh pr checks {num}` shows any failure. Abort.

5. **Branch is behind `develop`** — `gh pr view {num} --json mergeable` returns
   `BEHIND` or `CONFLICTING`. Abort and tell the human to re-run `/review`
   (which does the merge sync) or resolve manually.

6. **Working tree of any target repo has uncommitted changes** outside of
   `client-angular` — abort, ask the human to clean up first. (For
   `client-angular`, uncommitted changes are expected — code-only mode.)

If any gate fails → write `questions/merge-{task-id}.md` with the blocker
and abort. Do NOT merge any PR (atomic — either every PR merges or none).

## Repo modes

Same three-mode taxonomy as the rest of the forge :

- **Pushable** (`api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`,
  `sdk`, `host`, `interop-cda`) : full automation — merge PR, sync `develop`,
  delete branches.
- **Code-only** (`client-angular`) : **fully out of scope for `/merge`**.
  The human owns the entire Angular lifecycle (commit, push, PR, merge,
  branch sync — every git operation). `/merge` does **not** ask about
  Angular state, does **not** switch branches, does **not** pull, does
  **not** log a reminder. Skip silently. The human's awareness of the
  Angular side does not need confirmation by the forge.
- **Excluded** (`devops`, `psc-proxy-*`) : skip entirely.

## Steps

1. **Locate the task file** : `tasks/done-{task-id}.md`. If the task is
   still in `wip-*` or `review-*` → abort with "task not yet done — run
   `/review` first".

2. **Parse `--i-tested` flag** : if absent, print the Manual Test Plan and
   the HAG reminder, abort.

3. **Read the `## PRs` section** to extract `(repo, pr-url, label)` tuples.
   For each tuple, derive the PR number and the repo path.

4. **Run safety gates 2–6** for each pushable PR (loop). If any gate fails,
   abort the whole batch — do NOT merge partially.

5. **Merge each pushable PR** in topological order (DTOs first, then
   interop, then backend, then frontend) :
   ```bash
   cd {repo-path}
   gh pr merge {num} --squash            # NO --delete-branch (it nukes the local branch too)
   git checkout develop
   git pull --ff-only
   git push origin --delete feat/{task-id}-{slug}   # remote ref only — local branch kept
   ```

   Order rationale : DTO/interop NuGet packages are consumed by backend
   and frontend ; merging the dependency first keeps `develop` consistent
   if a follow-up PR lands between merges.

   **PITFALL — never use `gh pr merge --delete-branch`.** Despite its name,
   `--delete-branch` deletes **both** the remote ref **and** the local
   branch (verified task-038, recurred task-083). The human wants the local
   branch kept for retroactive inspection, so we merge without the flag and
   delete only the remote ref via a separate `git push origin --delete`.

6. **Skip `client-angular` entirely.** Even when the task lists it, do
   **not** ask the human about TFS state, do **not** read `git status`,
   do **not** `git checkout` or `git pull`. The human owns the full
   Angular lifecycle silently. The final report does not mention Angular
   beyond a single "managed manually by the human" line if the task
   listed it.

7. **Verify CI green on `develop`** (pushable repos only) within 2 minutes
   (CLAUDE.md rule 5) :
   ```bash
   gh run list --branch develop --limit 1 --json status,conclusion
   ```
   Wait up to 2 min. If CI fails on `develop` post-merge → write
   `questions/merge-{task-id}.md` with the failing run URL. The merges
   already happened — the human investigates.

8. **Archive the task** — move into the `tasks/archived/` subdirectory and
   prefix the filename with `archived-` :
   ```bash
   mv tasks/done-{task-id}.md tasks/archived/archived-{task-id}.md
   ```
   The `tasks/archived/` subdir is the **terminal location**. It MUST
   exist ; if not (fresh forge), create it with `mkdir -p tasks/archived`
   before the move. Append a `## Merged` section to the moved file with
   the merge timestamp, the squash commit SHA per repo, and the CI run
   URL on `develop`.

9. **Report** :
   ```
   {task-id} — merged.

   Squashed and merged :
   - dtos-mss      : {sha} (PR #N closed)
   - api-mail      : {sha} (PR #N closed)
   - client-blazor : {sha} (PR #N closed)

   Code-only :
   - client-angular : humain confirme avoir mergé sur TFS

   Excluded (manual) :
   - devops, psc-proxy-* : N/A

   develop CI : ✓ green on all pushable repos
   Task archived : tasks/archived/archived-{task-id}.md
   ```

## Rules

- **`/merge` is human-triggered only.** It is not part of the autonomous
  `/forge` chain. The autonomous chain stops at PR-opening (HAG, rule 10).
- The `--i-tested` flag is mandatory. No flag → no merge. The flag is the
  human's signed attestation that the US has been validated end-to-end.
- Never merge a PR labelled `awaiting-us-completion` (rule 11).
- Never merge with red CI or with unresolved review changes-requested.
- Never partial-merge. If any safety gate fails for any PR, abort the
  whole batch.
- Squash-merge only (`gh pr merge --squash`). Keeps `develop` history
  linear, one commit per US.
- Never force-push. Never touch `develop` history.
- Never touch `client-angular` — no git op, no question, no log line
  beyond "managed manually by the human". The TFS PR and the local
  Angular clone are the human's exclusive domain at merge time.
- Never modify `devops` or `psc-proxy-*` — they are entirely manual.
- The task moves `tasks/done-*.md → tasks/archived/archived-*.md` once every
  pushable PR is merged. The `tasks/archived/` subdir is the terminal
  location and is excluded from `/forge` and `/status` listings (their
  globs scan the flat `tasks/` only and do not recurse).
