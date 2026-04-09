# /review — Validate the human's implementation and open the PR(s)

Usage : `/review {task-id}` (e.g. `/review back-clinical-notifications-046`)

Purpose : the human finished implementing a task in WindSurf and pushed (or,
for `client-angular`, committed locally). The forge validates and, if
everything is GREEN, opens the pull request(s) and marks the task `done-*`.

**The forge does NOT fix code. If validation fails, the forge reports what is
wrong and the human goes back to WindSurf.**

## Steps

1. **Locate the task file** : accept `tasks/wip-{task-id}.md` or
   `tasks/review-{task-id}.md`. If missing → abort.

2. **Read the task** : `## Branches`, `## Definition of Done`, `## Manual Test Plan`.

3. **For each branch listed in `## Branches`** (both pushed and local-only) :
   ```bash
   cd {repo-path}
   git fetch origin                         # safe for both GitHub and TFS
   git checkout feat/{task-id}-{slug}
   # Pushed repos only :
   git pull --ff-only
   # Run repo's build + test from CLAUDE.md
   {build-cmd}
   {test-cmd}
   ```
   Any non-zero exit → validation FAILS. Stop, report the failing command and
   its output. Do NOT attempt a fix. Leave the task as-is.

4. **Check the Definition of Done** item by item. Command-verifiable items are
   run ; observational items are deferred to the Manual Test Plan in the PR
   body. Any DOD item that fails → validation FAILS with the reason.

5. **Sync each branch with develop** (merge, never rebase) :
   ```bash
   git fetch origin develop
   git merge origin/develop
   ```
   Conflicts → stop and report. The human resolves in WindSurf.

6. **If everything is GREEN**, for each branch :

   **Pushed repos** (GitHub) — open a PR :
   ```bash
   gh pr create \
     --base develop \
     --head feat/{task-id}-{slug} \
     --title "{type}({module}): {task-title}" \
     --body "{summary + link to task file + Manual Test Plan}"
   gh pr edit {num} --add-label awaiting-human-merge
   ```

   **Local-only repos** (`client-angular`, TFS remote) — no `gh` :
   - Do NOT push, do NOT attempt `gh pr create`
   - Write a line to the task file noting that the TFS PR must be opened
     manually by the human (commit hash + branch name + path)
   - Record the local commit SHA so the human can find the branch easily

7. **Rename the task** : `mv tasks/{wip|review}-{task-id}.md tasks/done-{task-id}.md`
   and append a `## PRs` section :

   ```markdown
   ## PRs
   - `api-mail` : https://github.com/.../pull/42 (awaiting-human-merge)
   - `client-blazor` : https://github.com/.../pull/43 (awaiting-human-merge)
   - `client-angular` : **TFS manual** — branch feat/X-001 at commit abc1234, push to TFS and open PR manually
   ```

8. **Report** to the human :
   ```
   {task-id} validated.
   
   GitHub PRs opened :
   - {repo} : {pr-url}
   - ...
   
   TFS (manual) :
   - client-angular : push feat/{task-id}-{slug} to tfs.weda.fr and open the PR
   
   Test manually, then merge the GitHub PRs yourself and open the TFS PR manually.
   ```

## Rules

- The forge never patches code — validation is read-only
- The forge never merges — HAG (CLAUDE.md rule 10)
- The forge never pushes a local-only repo
- The forge never attempts `gh` on a TFS remote
- Every DOD item must be checked or explicitly marked as deferred to manual test
- Build + test MUST pass on every target repo before any PR is opened
- Use `git merge`, never `git rebase` (CLAUDE.md rule 4)
