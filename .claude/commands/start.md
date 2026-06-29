# /start — Create the working branch(es) for a task

Usage :
- `/start {task-id}` — create the branches and **chain into `/develop`**
  (default — autonomous implementation by the forge).
- `/start {task-id} no-code` — create the branches and **stop**. The task
  stays in `wip-*` and the human implements in WindSurf manually. No
  `/develop` invocation.

Purpose : create the working branch(es) in the repo(s) declared by the task
file. By default the forge then writes the code itself (`/develop`) ; the
`no-code` flag is the escape hatch when the human wants to handle the
implementation in WindSurf (e.g. exploratory work, design-heavy changes,
or anything Sonar / `/develop` would mishandle).

**The forge writes code by default.** The lean "forge does not write code"
philosophy was inverted on 2026-04-27 — see CLAUDE.md "Forge philosophy".

## Steps

0. **Pre-flight : forge-automated repos on `develop`**

   Iterate **only over the forge-automated repos** in CLAUDE.md and verify
   each is on its `develop` branch. The set is :

   - `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk`, `host`, `interop-cda`

   **Explicitly skipped** (do NOT check their branch) :

   - `client-angular` — code-only mode, humain libre de sa branche
   - `devops`, `psc-proxy-server`, `psc-proxy-client`, `psc-proxy-dto` —
     entièrement hors automation

   ```bash
   for each forge-automated repo :
     cd {repo-path}
     current=$(git symbolic-ref --short HEAD)
     if [ "$current" != "develop" ] : record repo + current branch
   ```

   If **any** in-scope repo is not on `develop` → **abort** and print the list :

   ```
   /start refusé — les repos suivants ne sont pas sur develop :
   - api-mail      : feat/back-old-task-012
   - client-blazor : fix/some-hotfix

   Finis, stash ou checkout develop dans ces repos, puis relance /start.
   ```

   The forge does NOT switch branches itself — it only reports. The human
   handles the cleanup in WindSurf or the terminal.

1. **Locate the task file** : `tasks/todo-{task-id}.md`. If missing → abort.

2. **Read the task** and extract :
   - `**Repos**:` → comma-separated list of repo keys (plural, mandatory).
     A full-stack US lists at minimum `api-mail, client-blazor, client-angular`.
   - `**Single frontend**:` (optional, default `false`) → if `true`, skip the
     paired-frontend safety net below
   - `**Dependencies**:` → if any dep is not in `done-*`, abort and name it
   - The task body (for the branch slug)

3. **Resolve the target repos** :
   - Start with the list from `**Repos**:`
   - **Paired frontends safety net** : **disabled**. `/start` never
     auto-adds `client-angular` when `client-blazor` is listed (or
     vice-versa). The PO opts into Angular code generation by listing
     `client-angular` explicitly. Without an explicit listing, Angular
     stays a manual implementation by the human.
   - Auto-include `dtos-mss` whenever `api-mail` or `client-blazor` is
     listed (see CLAUDE.md "Auto-included repo : `dtos-mss`")
   - Deduplicate
   - Abort if any entry is unknown (not in the CLAUDE.md repo table)

4. **For each target repo**, look up its mode :
   - `client-angular` → **code-only**. The forge will write code on the
     branch currently checked out by the human (no branch creation in this
     command, no fetch, no checkout).
   - `devops`, `psc-proxy-*` → **entirely excluded**. Skip with the note
     "managed manually by the human".
   - All other repos → **pushable** (origin is GitHub).

5. **Create the branch** in each target repo from the latest `develop` :

   **Pushable repos** (default — origin is GitHub) :
   ```bash
   cd {repo-path}
   git fetch origin develop
   git checkout -b feat/{task-id}-{slug} origin/develop
   git push -u origin feat/{task-id}-{slug}
   ```

   **Code-only repos** (`client-angular`) :
   - **Do nothing.** Do NOT `git fetch`, do NOT `git checkout`, do NOT create
     a branch. The forge will operate on whatever branch is currently checked
     out in `Client/Angular/` when `/develop` runs. The human is responsible
     for the branch selection.

   **Excluded repos** (`devops`, `psc-proxy-*`) :
   - Skip entirely. Add the note "managed manually by the human" to the
     `## Branches` section.

   Branch prefix : `feat/`, `fix/`, `wire/`, `chore/` — pick from the task type.
   Confirm with the human if ambiguous.

6. **Rename the task** : `mv tasks/todo-{task-id}.md tasks/wip-{task-id}.md`.

7. **Append a `## Branches` section** to the wip task file, listing every repo
   with its mode (`pushed`, `code-only`, or `manual`) and the relevant info :

   ```markdown
   ## Branches
   - `api-mail` (pushed) : feat/back-X-001-signalr — https://github.com/.../tree/feat/back-X-001-signalr
   - `client-blazor` (pushed) : feat/back-X-001-signalr — https://...
   - `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` — humain gère branche, commit, push, PR TFS
   - `devops` (manual) : managed manually by the human
   ```

   For `client-angular`, capture the current branch at the time of `/start`
   so the report has a snapshot, but understand the human may switch branches
   before `/develop` runs — that's fine, `/develop` reads the current branch
   at execution time.

8. **Parse the optional `no-code` argument** :

   - If the second argument is `no-code` (or `--no-code` / `nocode` —
     accept any of these forms) → **skip step 9**. Annotate the
     `## Branches` section with a leading note :

     ```markdown
     > **Mode** : no-code — l'humain implémente dans WindSurf, pas de chaînage automatique vers /develop.
     ```

   - Otherwise → continue to step 9.

9. **Chain into `/develop`** (default behaviour) :

   Invoke `/develop {task-id}` immediately. The task stays in `wip-*` and
   `/develop` takes over the implementation, then chains into
   `/forge-simplify` (the `/simplify` quality pass), then `/sonar`
   (api-mail), then `/lint-angular` (client-angular), then `/lint-mobile`
   (client-mobile), then `/review`, then `/tech-writer`. `/forge-simplify`,
   `/sonar`, `/lint-angular` and `/lint-mobile` skip cleanly when there's
   nothing to do. The full autonomous loop runs
   end-to-end without human prompt — the only mandatory human action is
   **merging the resulting PR** (HAG, CLAUDE.md rule 10).

10. **Report** to the human :

    **Default mode** (chained into `/develop`) :
    ```
    Branch(es) created for {task-id} :
    - {repo} (pushed / local-only)
    - ...

    Chaining into /develop now → /forge-simplify → /sonar → /lint-angular → /lint-mobile → /review → /tech-writer.
    (/forge-simplify, /sonar, /lint-angular et /lint-mobile skip clean si leur repo n'a pas été touché.)
    The PR(s) will land with label awaiting-human-merge — you merge
    when ready (HAG rule 10).
    ```

    **`no-code` mode** :
    ```
    Branch(es) created for {task-id} (no-code mode) :
    - {repo} (pushed / local-only)
    - ...

    The task is now WIP. Go implement in WindSurf on those branches.
    When you are done, run /review {task-id}.
    ```

## Rules

- **1 US = 1 task file = 1 branch name** on every pushable repo the US touches.
  `client-angular` is **code-only** : no branch creation, the human owns the
  branch. No split `todo-back-*` / `todo-front-*` — one unified task.
- Never create a branch on a repo not declared in `**Repos**:` (auto-include
  `dtos-mss` is the only exception)
- Never create a branch on `client-angular` — code-only mode
- Never create a branch on `devops` or `psc-proxy-*` — entirely manual
- Never skip dependencies
- Never branch from a stale local ref — always `git fetch origin develop` first
  (pushable repos only — `client-angular` not concerned)
- `/start` itself never writes code — it only creates branches. The
  `/develop` chaining (step 9) is what writes code, and only when the
  `no-code` flag is absent.
- The `no-code` flag is the **only** way to opt out of autonomous
  implementation. Once chosen, the task is the human's responsibility
  until they manually trigger `/review`.
