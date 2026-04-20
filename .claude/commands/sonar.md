# /sonar — Automated Sonar cleanup

Usage : `/sonar api-mail` (only `api-mail` is supported at the moment)

Purpose : run an end-to-end SonarQube cleanup pass on `api-mail`. Unlike every
other forge command, `/sonar` writes code — it is the explicit **automation
exception** documented in CLAUDE.md. The justification is that Sonar cleanup
is mechanical refactoring gated by unit tests, not feature implementation.

Read `agents/sonar.md` and execute the full playbook :

1. Pre-flight (repo on `develop`, Sonar reachable, scanner installed)
2. Baseline KPI snapshot ; early-stop if all hard targets are already met
3. Create `tasks/todo-sonar-api-mail-{YYYYMMDD}.md` and call `/start`
4. Iterate up to 5 times on the same branch : fetch issues → filter the
   blacklist (`agents/sonar-blacklist.yml`) → batch catégorie+règle (max
   30 fichiers) → test-first for behavioural fixes → build + full tests →
   commit per rule → push → re-analyse → evaluate progression
5. Stop when : targets met, or progression < 10% and no rating improvement,
   or 5 iterations done
6. Hand over to `/review` which opens the PR (label `awaiting-human-merge`)

The human merges the PR (HAG rule 10). The forge never merges.

## Rules

- Scope : `api-mail` only. Other repos are out of scope for this command.
- Test-first on every behavioural fix (rule 1).
- Blacklisted rules (`agents/sonar-blacklist.yml`) are NEVER fixed here.
  S3776 uses the dedicated `/sonar-s3776` command.
- Token read from `$SONAR_TOKEN`, never hardcoded.
- On any unexpected state, stop and write `questions/sonar-api-mail-{YYYYMMDD}.md`.
