# /forge-simplify — Forge-aware code simplification step

Usage : `/forge-simplify {task-id}` (e.g. `/forge-simplify task-018`)

Purpose : run the built-in `/simplify` quality pass (reuse / simplification /
efficiency / altitude — **quality only, no bug hunting**) on the code
`/develop` just produced, repo by repo, then re-validate, commit/push the
pushable repos, leave `client-angular` code-only, and hand off to the next
chain step. This is the forge-aware wrapper around the standalone built-in
`/simplify` — the chain version, task-scoped and validated.

It sits in the autonomous chain **between `/develop` and `/sonar`** :

```
/develop  →  /forge-simplify  →  /sonar  →  /lint-angular  →  /review  →  /tech-writer
```

`/sonar` and `/lint-angular` deliberately run after it so they re-scan /
re-validate whatever the simplify pass touched.

Read `agents/forge-simplify.md` and execute the full playbook :

1. Pre-flight (task in `wip-*`, pushable repos on their feature branch, clean)
2. Determine the touched, eligible repos (diff vs `develop`)
3. Run the built-in `/simplify` per touched repo (skip `dtos-mss`,
   `interop-cda`, and excluded repos)
4. Re-validate (build + existing tests) ; commit + push pushable repos on
   GREEN, roll back on RED (quality pass must not change behaviour),
   leave `client-angular` uncommitted
5. Append `## Simplify log` ; route to `/sonar` (if api-mail touched) →
   `/lint-angular` (if angular touched) → `/review` otherwise

## Rules

- **Quality only.** Bug/security hunting is `/code-review`, not this step.
- **Best-effort, non-blocking.** A repo that fails validation is rolled back
  and skipped ; the chain proceeds. Only tooling failures halt
  (`questions/{task-id}.md`).
- **Scope** : `api-mail`, `client-blazor`, `sdk`, `host` (commit + push) ;
  `client-angular` (code-only, never git). NEVER `dtos-mss` / `interop-cda`
  (contract carriers) or `devops` / `psc-proxy-*` (excluded).
- **Reuse before create** — the reuse axis enforces the workspace rule.
- Explicit staging only, conventional `refactor(module):` commits, no rebase.
- HAG (rule 10) : never merges on `develop`.

The standalone built-in `/simplify` stays available for ad-hoc human use
(simplify the current diff, no forge ceremony). `/forge-simplify` is the
chained, task-scoped version.
