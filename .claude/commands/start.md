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

0. **Pre-flight : all repos on `develop`**

   Before doing anything, iterate over every repo listed in CLAUDE.md (the
   full polyrepo, not just the task's targets) and verify each is on its
   `develop` branch :

   ```bash
   for each repo in CLAUDE.md table :
     cd {repo-path}
     current=$(git symbolic-ref --short HEAD)
     if [ "$current" != "develop" ] : record repo + current branch
   ```

   If **any** repo is not on `develop` → **abort** and print the list :

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
   - **Paired frontends safety net** : if the list contains `client-blazor`
     XOR `client-angular`, AND `Single frontend` is not `true`, add the missing
     one so both frontends get the branch
   - Deduplicate
   - Abort if any entry is unknown (not in the CLAUDE.md repo table)

4. **For each target repo**, look up its entry in CLAUDE.md and note whether
   it is a `local-only` repo (currently : `client-angular`, because its remote
   is TFS and `gh pr` is unusable).

5. **Create the branch** in each target repo from the latest `develop` :

   **Pushable repos** (default — origin is GitHub) :
   ```bash
   cd {repo-path}
   git fetch origin develop
   git checkout -b feat/{task-id}-{slug} origin/develop
   git push -u origin feat/{task-id}-{slug}
   ```

   **Local-only repos** (`client-angular`) :
   ```bash
   cd {repo-path}
   git fetch origin develop       # TFS remote — still fetches the ref
   git checkout -b feat/{task-id}-{slug} origin/develop
   # NO git push — the human pushes to TFS and opens the PR manually later
   ```

   Branch prefix : `feat/`, `fix/`, `wire/`, `chore/` — pick from the task type.
   Confirm with the human if ambiguous.

6. **Rename the task** : `mv tasks/todo-{task-id}.md tasks/wip-{task-id}.md`.

7. **Append a `## Branches` section** to the wip task file, listing every branch
   with its repo, mode (`pushed` or `local-only`) and (if pushed) URL :

   ```markdown
   ## Branches
   - `api-mail` (pushed) : feat/back-X-001-signalr — https://github.com/.../tree/feat/back-X-001-signalr
   - `client-blazor` (pushed) : feat/back-X-001-signalr — https://...
   - `client-angular` (local-only) : feat/back-X-001-signalr — TFS, human handles push/PR manually
   ```

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
   `/develop` takes over the implementation, then chains into `/sonar`
   (api-mail), then `/review`, then `/tech-writer`. The full autonomous
   loop runs end-to-end without human prompt — the only mandatory human
   action is **merging the resulting PR** (HAG, CLAUDE.md rule 10).

10. **Report** to the human :

    **Default mode** (chained into `/develop`) :
    ```
    Branch(es) created for {task-id} :
    - {repo} (pushed / local-only)
    - ...

    Chaining into /develop now → /sonar → /review → /tech-writer.
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

- **1 US = 1 task file = 1 branch name** on every repo the US touches.
  No split `todo-back-*` / `todo-front-*` — one unified task.
- Never create a branch on a repo not declared (directly or via pairing)
- Never skip dependencies
- Never branch from a stale local ref — always `git fetch origin develop` first
- Never push a `local-only` repo branch
- `/start` itself never writes code — it only creates branches. The
  `/develop` chaining (step 9) is what writes code, and only when the
  `no-code` flag is absent.
- The `no-code` flag is the **only** way to opt out of autonomous
  implementation. Once chosen, the task is the human's responsibility
  until they manually trigger `/review`.
