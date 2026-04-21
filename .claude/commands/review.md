# /review — Validate the human's implementation and open the PR(s)

Usage : `/review {task-id}` (e.g. `/review back-clinical-notifications-046`)

Purpose : the human finished implementing a task in WindSurf and pushed (or,
for excluded repos, committed locally). The forge validates (build, tests,
DOD), performs a **code review** equivalent to a second developer reviewing
the implementation, and if everything is GREEN **and the human approves**,
commits any uncommitted changes, opens the pull request(s), and marks the
task `done-*`.

**The forge does NOT fix code. If validation or code review fails, the forge
reports what is wrong and the human goes back to WindSurf.**

## Steps

1. **Locate the task file** : accept `tasks/wip-{task-id}.md` or
   `tasks/review-{task-id}.md`. If missing → abort.

2. **Read the task** : `## Branches`, `## Definition of Done`, `## Manual Test Plan`,
   `## Objectif` (to understand the intent of the US).

3. **For each branch listed in `## Branches`** (pushed repos only, skip excluded) :
   ```bash
   cd {repo-path}
   git fetch origin
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

6. **Present the validation report to the human** :

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

   Approve to commit and create PRs? (yes / no)
   ```

   **If CHANGES REQUESTED** : do NOT ask for approval. Report the blocking
   issues and stop. The human fixes in WindSurf and re-runs `/review`.

   **If APPROVED** : wait for human approval. Do NOT proceed without explicit
   "yes". If the human says "no" → stop, leave the task as-is.

7. **After human approval — Commit uncommitted changes** on each repo :
   ```bash
   cd {repo-path}
   git add -A
   git status
   # If there are changes to commit :
   git commit -m "feat({module}): {task-title}"
   git push
   ```
   Skip repos with no uncommitted changes.

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

   **Excluded repos** (`client-angular`, `devops`, `psc-proxy-dto`) :
   - Do NOT push, do NOT attempt `gh pr create`
   - Write a note to the task file : "managed manually by the human"

10. **Rename the task** : `mv tasks/{wip|review}-{task-id}.md tasks/done-{task-id}.md`
    and append `## PRs` and `## Code Review Summary` sections.

11. **Update the EPIC documentation** — if the task file declares `**Epic**: E{NNN}`,
    invoke `/tech-writer E{NNN}` to refresh `docs/epics/E{NNN}-{slug}.md`. If no
    `**Epic**:` field is present, skip with the note "no EPIC linked — skipped
    tech-writer" in the final report. The tech-writer runs read-only on tasks
    and only writes to `docs/epics/`.

12. **Report** to the human :
    ```
    {task-id} validated, reviewed, and approved.

    Code review : APPROVED (X files reviewed, Y suggestions, 0 blocking)

    Commits pushed, GitHub PRs opened :
    - {repo} : {pr-url}
    - ...

    Excluded repos (manual) :
    - client-angular : human manages branch, push, and PR

    EPIC doc : docs/epics/E{NNN}-{slug}.md updated
               (or : no EPIC linked — skipped tech-writer)

    Test manually, then merge the GitHub PRs yourself.
    ```

## Rules

- The forge never patches code — validation and review are read-only
- The forge never merges PRs — HAG (CLAUDE.md rule 10)
- The forge never pushes an excluded repo
- The forge never commits or creates PRs without **explicit human approval**
- The forge never commits or creates PRs if code review is **CHANGES REQUESTED**
- Every DOD item must be checked or explicitly marked as deferred to manual test
- Build + test MUST pass on every target repo before code review
- Code review MUST be APPROVED before presenting for human approval
- Use `git merge`, never `git rebase` (CLAUDE.md rule 4)
- The code review is honest and rigorous — it flags real issues, not cosmetic
  nitpicks. The goal is to catch bugs, security issues, and design problems
  that the implementing developer might have missed.
- The tech-writer is invoked **after** the PRs are opened and the task is
  renamed `done-*`. A failure in `/tech-writer` does NOT revert the review —
  the doc can be rebuilt later with `/tech-writer E{NNN} --refresh`.
