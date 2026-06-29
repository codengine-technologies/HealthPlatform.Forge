# /develop — Autonomous implementation of a task

Usage : `/develop {task-id}` (e.g. `/develop task-018`)

Purpose : write the code, the tests, build, run the suite, commit, push, and
hand off to `/forge-simplify` (which runs the `/simplify` quality pass, then
chains `/sonar` → `/lint-angular` → `/lint-mobile` → `/review`). This is the **default
implementation path** of the
forge — the only escape hatch is `/start {task-id} no-code`, which leaves the
task in `wip-*` for the human to implement in WindSurf.

Read `agents/develop.md` and execute the full playbook :

1. Pre-flight (task in `wip-*`, branches exist on every listed repo, working
   trees clean)
2. Compute the cross-repo build order : `dtos-mss` → `interop-cda` →
   backends → frontends
3. For shared-contract repos (`dtos-mss`, `interop-cda`) : code, build,
   commit, push, `gh run watch` until the GitHub Actions CI publishes the
   NuGet package, bump consumers' `Directory.Packages.props`, commit the
   bump in each consumer (push later)
4. For backends and frontends : test-first for behavioural changes, build +
   test green before each commit, conventional messages, push at the end
5. Final verification : every repo green, DOD self-check
6. Hand off unconditionally to `/forge-simplify {task-id}` — it runs the
   `/simplify` quality pass on the fresh code, re-validates, commits/pushes
   pushable repos, then routes onward along the fixed pipeline
   `/sonar → /lint-angular → /lint-mobile → /review` (each step self-skips
   when its repo wasn't touched) :
   - api-mail touched → `/sonar {task-id}`
   - else client-angular touched → `/lint-angular {task-id}`
   - else client-mobile touched → `/lint-mobile {task-id}`
   - none touched → `/review {task-id}` directly

`/develop` writes code by design — this is the post-lean philosophy. The
human's only mandatory interaction is **merging the PR on `develop`** at
the end of the chain (HAG, CLAUDE.md rule 10).

## Rules

- 5 iterations cap on the same RED test or broken build → fail-fast into
  `questions/{task-id}.md`
- Cross-repo order is mandatory : DTOs and interop must be published to
  NuGet before consumers can compile against the new contract
- Never `git add -A` / `git add .` — explicit staging only
- Excluded repos (`client-angular`, `devops`, `psc-proxy-*`) are never
  touched ; logged as "managed manually by the human"
- HAG is preserved : `/develop` never merges on `develop`
- On any unexpected state, stop and write `questions/{task-id}.md`
