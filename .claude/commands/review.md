# /review — Validate the implementation and open the PR(s)

Usage : `/review {task-id}` (e.g. `/review back-clinical-notifications-046`)

Purpose : the implementation phase is complete (either by `/develop` in the
autonomous chain, or by the human in WindSurf in `no-code` mode). The forge
validates (build, tests, DOD), performs a **code review** equivalent to a
second developer reviewing the implementation, and if everything is GREEN
commits any uncommitted changes, opens the pull request(s), labels them
`awaiting-human-merge`, marks the task `done-*`, and chains into
`/tech-writer` to refresh the EPIC doc.

**Since the autonomous inversion of 2026-04-27, `/review` no longer prompts
the human for approval before committing / opening PRs.** The chain runs
end-to-end. The only mandatory human interaction remains the **merge of the
final PR** (HAG, CLAUDE.md rule 10).

**The forge does NOT fix code.** If validation or code review fails, the
forge writes `questions/{task-id}.md` with the blocker details and stops.
In autonomous mode (`/develop` upstream) this halts the chain ; in
`no-code` mode the human goes back to WindSurf.

## Steps

1. **Locate the task file** : accept `tasks/wip-{task-id}.md` or
   `tasks/review-{task-id}.md`. If missing → abort.

2. **Read the task** : `## Branches`, `## Definition of Done`, `## Manual Test Plan`,
   `## Objectif` (to understand the intent of the US).

3. **For each repo listed in `## Branches`**, branch validation depends on
   the mode :

   **Pushed repos** (`api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`,
   `sdk`, `host`, `interop-cda`) :
   ```bash
   cd {repo-path}
   git fetch origin
   git checkout feat/{task-id}-{slug}
   git pull --ff-only
   {build-cmd}
   {test-cmd}
   ```
   `client-mobile` is a pushed repo even though it's an Ionic/Angular
   frontend — its `{build-cmd}` / `{test-cmd}` (npm, from the CLAUDE.md table:
   `npm run build` / `npm test -- --watch=false --browsers=ChromeHeadless`)
   are run the same way, and its PR is opened via `gh` in step 9.

   **Code-only repos** (`client-angular`) — humain owns git, forge only
   re-validates :
   ```bash
   cd Client/Angular
   git symbolic-ref --short HEAD     # capture current branch (whatever it is)
   git status --porcelain            # snapshot the working tree state
   npm ci && npm run build           # MUST exit 0
   npm test                          # MUST pass
   # Do NOT git fetch, git checkout, git pull — humain owns the branch
   ```

   **Entirely excluded repos** (`devops`, `psc-proxy-*`) :
   - Skip entirely. Log "managed manually by the human".

   Any non-zero exit on build/test → validation FAILS. Stop, report the
   failing command and its output. Do NOT attempt a fix. Leave the task as-is.

4. **Check the Definition of Done** item by item. Command-verifiable items are
   run ; observational items are deferred to the Manual Test Plan in the PR
   body. Any DOD item that fails → validation FAILS with the reason.

5. **Code Review** — review the diff on each repo like a second developer :

   ```bash
   cd {repo-path}
   git diff origin/develop...HEAD
   ```

   Read all changed files and evaluate against these criteria :

   ### 5.1 Correctness
   - Does the implementation match the US objective and Gherkin scenarios?
   - Are there logic errors, off-by-one, null reference risks?
   - Are edge cases handled (empty strings, nulls, missing data)?

   ### 5.2 Security
   - No injection risks (SQL, XSS, command injection)
   - No secrets or credentials in the code
   - Input validation at system boundaries
   - Authentication/authorization respected

   ### 5.3 Architecture & Design
   - Follows existing patterns in the codebase (Clean Architecture, DDD, etc.)
   - No unnecessary coupling between layers
   - DTOs used for cross-boundary communication
   - No business logic in controllers or UI components

   ### 5.4 Code Quality
   - Readable, clear naming
   - No dead code, commented-out blocks, or TODO left behind
   - No code duplication that should be factored
   - Appropriate error handling (not over-engineered, not missing)

   ### 5.5 Performance
   - No N+1 queries, unnecessary allocations, or blocking calls in async code
   - Appropriate use of async/await
   - No unbounded collections or missing pagination

   ### 5.6 Test Coverage
   - New code has tests (unit and/or integration)
   - Tests are meaningful (not just asserting true)
   - Step definitions match the Gherkin scenarios

   ### Verdict

   For each file or area reviewed, note :
   - ✅ **Approve** — code is good, no issues
   - ⚠️ **Suggestion** — non-blocking improvement (nice-to-have, not required)
   - ❌ **Request changes** — blocking issue that must be fixed before merge

   The overall code review verdict is :
   - **APPROVED** — no blocking issues (may have suggestions)
   - **CHANGES REQUESTED** — at least one blocking issue → validation FAILS

6. **Print the validation report** (autonomous — no prompt) :

   ```
   Validation report for {task-id} :

   Build       : ✓ api-mail | ✓ client-blazor | ...
   Tests       : ✓ api-mail (X passed, 0 failed)
   DOD         : ✓ all items checked
   Code Review : ✓ APPROVED (or ✗ CHANGES REQUESTED)

   ## Code Review Details

   ### api-mail
   - `src/Application/Helpers/XdmSubjectHelper.cs` — ✅ clean implementation
   - `src/Api/Controllers/MailController.cs` — ⚠️ suggestion: consider caching
   - ...

   ### client-blazor
   - `Components/MailHeader.razor` — ✅ correct usage of helper
   - ...

   ## Suggestions (non-blocking)
   - ...

   ## Blocking Issues (if any)
   - ...
   ```

   **If CHANGES REQUESTED** : write `questions/{task-id}.md` with the
   blocking issues, leave the task in `review-*` (or `wip-*` in autonomous
   mode, since `/develop` left it there), and **halt the chain**. Do not
   commit, do not open PRs. The human (or a future re-run after fixes)
   restarts the cycle from the failure point.

   **If APPROVED** : continue to step 7 immediately — no human prompt, no
   waiting. The autonomous chain has no manual approval gate ; HAG (rule 10)
   is the single barrier and it sits at PR-merge time, not before.

7. **Commit uncommitted changes** on each **pushable** repo (autonomous — no
   prompt) :
   ```bash
   cd {repo-path}
   git add -A
   git status
   # If there are changes to commit :
   git commit -m "feat({module}): {task-title}"
   git push
   ```
   Skip pushable repos with no uncommitted changes.

   **Skip `client-angular` entirely** — code-only mode means uncommitted
   Angular changes are intentional ; the human owns commit/push to TFS. Do
   NOT `git add`, do NOT `git commit`, do NOT `git push`.

8. **Sync each branch with develop** (merge, never rebase) :
   ```bash
   git fetch origin develop
   git merge origin/develop
   ```
   Conflicts → stop and report. The human resolves in WindSurf.

9. **Open PRs** for each pushed repo :

   **Pushed repos** (GitHub) :
   ```bash
   gh pr create \
     --base develop \
     --head feat/{task-id}-{slug} \
     --title "{type}({module}): {task-title}" \
     --body "{summary + code review summary + Manual Test Plan}"
   gh pr edit {num} --add-label awaiting-human-merge
   ```

   Include the code review summary in the PR body under a `## Code Review`
   section so the human can see the review when merging.

   **Code-only repo** (`client-angular`) :
   - Do **NOT** push, do **NOT** attempt `gh pr create` (TFS remote, manual).
   - Write a note in the task's `## PRs` section : "code-only — humain gère
     commit/push TFS et ouverture PR. Liste des fichiers modifiés ci-dessous :"
     followed by the output of `git diff --name-only` in `Client/Angular/`.
   - The forge has already validated build + test in step 3 ; the human
     reviews the diff in WindSurf before pushing to TFS.

   **Entirely excluded repos** (`devops`, `psc-proxy-*`) :
   - Skip entirely. Write the note "managed manually by the human" in the
     task's `## PRs` section.

10. **Rename the task** : `mv tasks/{wip|review}-{task-id}.md tasks/done-{task-id}.md`
    and append `## PRs` and `## Code Review Summary` sections.

11. **Update the EPIC documentation** — if the task file declares `**Epic**: E{NNN}`,
    invoke `/tech-writer E{NNN}` to refresh `docs/epics/E{NNN}-{slug}.md`. If no
    `**Epic**:` field is present, skip with the note "no EPIC linked — skipped
    tech-writer" in the final report. The tech-writer runs read-only on tasks
    and only writes to `docs/epics/`.

12. **Report** to the human :
    ```
    {task-id} — autonomous cycle complete.

    Code review : APPROVED (X files reviewed, Y suggestions, 0 blocking)

    Commits pushed, GitHub PRs opened :
    - {repo} : {pr-url}    [label: awaiting-human-merge]
    - ...

    Code-only repo (humain gère git + PR) :
    - client-angular : N fichier(s) modifié(s), uncommitted sur branche `{branch}` —
      review le diff puis commit/push TFS + ouvre la PR

    Excluded repos (manual) :
    - devops, psc-proxy-* : managed manually by the human

    EPIC doc : docs/epics/E{NNN}-{slug}.md updated
               (or : no EPIC linked — skipped tech-writer)

    HAG (rule 10) : test manually, then merge the GitHub PRs yourself.
    ```

## Rules

- The forge never patches code in `/review` — validation and review are
  read-only on the existing code (`/develop` is the agent that writes code)
- The forge never merges PRs — HAG (CLAUDE.md rule 10)
- The forge never commits or pushes `client-angular` (code-only mode —
  humain gère git + PR TFS) ; build + test are still run
- The forge never builds, tests, commits, pushes, or opens PRs for
  `devops` or `psc-proxy-*` (entièrement hors automation)
- **`/review` is autonomous** : no "yes/no" prompt before commit / PR
  creation. The human's only manual intervention is merging the PR
  (HAG, rule 10).
- If code review is **CHANGES REQUESTED** → write `questions/{task-id}.md`
  and halt the chain. Do not commit, do not open PRs.
- Every DOD item must be checked or explicitly marked as deferred to manual
  test (Manual Test Plan items become PR-body checkboxes for the human).
- Build + test MUST pass on every target repo before code review
- Use `git merge`, never `git rebase` (CLAUDE.md rule 4)
- The code review is honest and rigorous — it flags real issues, not cosmetic
  nitpicks. The goal is to catch bugs, security issues, and design problems
  that `/develop` (or the human in `no-code` mode) might have missed.
- The tech-writer is invoked **after** the PRs are opened and the task is
  renamed `done-*`. A failure in `/tech-writer` does NOT revert the review —
  the doc can be rebuilt later with `/tech-writer E{NNN} --refresh`.
