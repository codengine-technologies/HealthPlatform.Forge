# CLAUDE.md — Forge Factory Rules

> Read automatically by all agents at startup. Non-negotiable rules.
> When in doubt about a rule → questions/, never improvise.

---

## Workspace layout — POLYREPO

`D:\TechWatch\HealthPlatform\` is a **meta-workspace**, NOT a git repo. It contains
the forge control plane (CLAUDE.md, agents/, tasks/, questions/, .claude/) and 11
independent git repositories. Every code-touching action MUST happen inside one of
those repos — never at the workspace root.

### Repos

| Repo key | Path | Stack | Build cmd | Test cmd |
|---|---|---|---|---|
| `api-mail` | `Api/Mail` | .NET 10, xUnit, Reqnroll BDD | `dotnet build HealthPlatform.Api.Mail.sln` | `dotnet test HealthPlatform.Api.Mail.sln` |
| `client-blazor` | `Client/Blazor` | Blazor WASM, .NET 10, xUnit | `dotnet build HealthPlatform.Client.sln` | `dotnet test HealthPlatform.Client.sln` |
| `dtos-mss` | `Dtos` | .NET 10 class lib (NuGet) | `dotnet build HealthPlatform.Dtos.Mss.csproj` | n/a |
| `sdk` | `Sdk` | .NET 10 host SDK | `dotnet build HealthPlatform.Host.Sdk.csproj` | n/a |
| `host` | `Host/Modules` | .NET 10 modules | `dotnet build` | n/a |
| `interop-cda` | `interop/interop.cda.parser` | .NET 10 | `dotnet build interop.cda.parser.sln` | `dotnet test` |
| `psc-proxy-server` | `psc/proxy/psc.proxy.server` | .NET 10 DDD | `dotnet build psc.proxy.server.sln` | `dotnet test` |
| `psc-proxy-client` | `psc/proxy/psc.proxy.client` | .NET 10 client | `dotnet build psc.proxy.client.sln` | n/a |
| `psc-proxy-dto` | `psc/proxy/psc.proxy.dto` | .NET 10 DTOs | `dotnet build psc.proxy.dto.sln` | n/a |
| `devops` | `DevOps` | CI/CD configs | n/a | n/a |

### Repos EXCLUDED from the forge

The following repos exist under the workspace but the forge MUST NOT touch them.
No dev agents, no automated commits, no PR creation, no hook enforcement. All
git/build/test/PR operations for these repos are handled **manually** by the human.

| Repo | Path | Reason |
|---|---|---|
| `client-angular` | `Client/Angular` | Remote is TFS (`tfs.weda.fr`), not GitHub — `gh pr` unusable. All work done manually. |

**Rules for excluded repos:**
- No `**Repo: client-angular**` in task files — such tasks are forbidden
- The `verify-before-push.sh` hook short-circuits (exit 0) when invoked from inside an excluded repo
- The orchestrator skips anything under excluded repo paths
- If the human wants the forge to help edit code inside an excluded repo, they do it via plain `/dev` targeted at a non-forge prompt, never via `/forge`

### Cross-repo dependencies

- `api-mail`, `client-blazor`, `client-angular` consume `dtos-mss` as a NuGet package.
  Any contract change → `/publish-dtos` first (publishes + bumps consumers).
- `client-blazor` and `host` consume `sdk`.
- `psc-proxy-server` consumes `psc-proxy-dto`.
- All other links are independent.

### Task → Repo routing

Each `tasks/todo-*.md` MUST declare a `**Repo**:` field whose value is one of the
repo keys above. Agents `cd` into that path and execute ALL git/build/test/gh
commands from there. Tasks that genuinely span repos (e.g. backend + DTO publish)
list the primary repo and reference the secondary via the body — the orchestrator
splits these into ordered sub-steps (publish-dtos → backend/frontend).

---

## Absolute rules

### 1. BDD-first mandatory

```
Step 0: PO writes .feature files BEFORE any implementation
Step 1: Dev agent READS existing .feature — never creates/modifies them
Step 2: Write step definitions → verify RED
Step 3: Implement until GREEN
Step 4: PR only when all Gherkin scenarios are GREEN
```

An agent that opens a PR with red tests = PR rejected automatically.

### 1b. Endpoint coverage mandatory

Each endpoint MUST have at least 1 integration test. Empty scaffolds (endpoints that compile but return nothing meaningful) are bugs. If an endpoint exists, a test proves it works end-to-end through the DI pipeline.

### 1a. Feature file purity

**.feature files are PO property.** A dev agent never creates or modifies a .feature file.
If a .feature is missing or incomplete → agent blocks and writes to `questions/`.

**.feature files are purely functional — ZERO technical jargon:**

```gherkin
# CORRECT — natural language, user-observable
Given a user with an active account
When the user logs in with valid credentials
Then the user is authenticated

# FORBIDDEN — technical jargon
When I POST /api/v1/auth/login with:    # URL = technical
Then the response status is 200          # HTTP code = technical
And I receive a JWT access token         # JWT = technical
```

**Forbidden patterns** (enforced by `guard-feature.sh` hook):
- HTTP status codes: 200, 201, 400, 401, 403, 404, 409, 422, 500
- API paths: `/api/`, `POST /`, `GET /`
- Technical terms: JWT, token, database, query, SQL, endpoint, header, JSON, HTTP

### 2. Local verification mandatory BEFORE commit/push

**No code leaves the machine without local verification.**

Build + test commands are **per-repo** (see the Repos table above). Run them from
the repo root, never from the workspace root. Example for `api-mail`:

```bash
cd Api/Mail
dotnet build HealthPlatform.Api.Mail.sln    # MUST return 0 errors
dotnet test  HealthPlatform.Api.Mail.sln    # MUST pass
```

**If a test fails → fix BEFORE committing.**

### 3. Immediate commit after GREEN

**As soon as tests are GREEN → git add + git commit + git push IMMEDIATELY.**
A fix verified locally but not committed does not exist.

### 4. Merge-based sync, not rebase

**When a PR has conflicts with develop, use `git merge origin/develop` instead of `git rebase`.**

### 5. PR hygiene (polyrepo)

- **1 task = 1 branch = 1 PR towards `develop`** — in the **repo declared by the
  task's `**Repo**:` field**. Never push code from one task into another task's repo.
- A task that legitimately needs to touch N repos lists each repo and produces N
  PRs (one per repo), with the SAME branch name `feat/{task-id}-{slug}`. The
  orchestrator links the sibling PR URLs in the task file before merging any of them.
- Max ~30 modified files per PR
- Each worktree agent creates its OWN PR in its OWN repo
- After each merge → verify that repo's `develop` CI GREEN within 2 minutes
- The workspace root (`D:\TechWatch\HealthPlatform\`) is NEVER pushed — it has no
  remote. Forge control files (CLAUDE.md, agents/, tasks/, questions/) are tracked
  separately (see "Forge control" section below) or kept local.

### 6. Isolated scopes

Each agent only touches files in its module. If a cross-module need appears → create `questions/` and block.

### 7. Fail-fast mandatory

Block immediately and create `questions/{task-id}.md` if:
- Edge case not covered by Gherkin
- Business rule ambiguity
- Need to modify frozen files
- Two approaches have failed

### 7a. Circuit breaker — 3 attempts max

An agent debugging a problem has **3 maximum attempts** to resolve it.
After 3 consecutive failures on the same problem:
- **STOP immediately** — do not keep guessing
- Create `questions/{task-id}-debug-{timestamp}.md` documenting:
  - What was tried (the 3 approaches)
  - Results/errors of each attempt
  - Hypothesis on root cause
- Report status `FAILED` and wait for human/PO input

**Why:** an agent looping on a fix consumes context and budget without progressing.

### 7b. Subagent tool access fallback

Subagents in isolated worktrees may lose access to certain tools (e.g., Bash for git commands).
When blocked:
- Report status `BLOCKED` with **exact commands** to execute
- The orchestrator executes the commands on behalf of the agent
- Agent prompts should include: "If tool access is denied for git commands, list exact commands and report BLOCKED."

### 7c. Schema migration audit

After generating any database migration (EF Core, Prisma, Alembic, Knex, etc.), the agent MUST:
1. **Read the generated migration file** and verify it matches intent
2. **Check for phantom operations** (altering columns that were never created, dropping tables that shouldn't be dropped)
3. **Verify companion/metadata files exist** (e.g., `.Designer.cs` for EF Core, snapshot files)
4. **Run the framework's "has pending changes" command** to confirm no drift

**Why:** auto-generated migrations can produce phantom operations when the snapshot diverges from the actual schema.

### 8. Commit convention

```
feat(module): add feature description
fix(module): fix description
test(module): add test description
refactor(module): refactor description
```

### 9. Definition of Done (DOD) mandatory

Every task file (`todo-*.md`) MUST include a `## Definition of Done` section with concrete, verifiable criteria. No subjective criteria ("clean code") — only binary checks the Evaluator agent can verify.

The DOD is the contract between the dev agent and the evaluator. If a criterion is not in the DOD, the evaluator won't check it. If it IS in the DOD, the evaluator WILL check it and FAIL the evaluation if it's not met.

Template:
```
## Definition of Done
- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] New handlers have unit tests (>=1 test per handler)
- [ ] No hardcoded strings in UI (all through i18n)
- [ ] data-testid on all interactive elements
- [ ] DTO types match backend contracts
```

---

## Frozen files

Never modify without human arbitration:
- `src/core/`

---

## Hooks

| Hook | Trigger | Effect |
|---|---|---|
| `guard-shared.sh` | Write/Edit | Blocks modification of frozen files |
| `guard-feature.sh` | Write/Edit .feature | Blocks technical jargon |
| `guard-wip-features.sh` | Bash `git push` | Blocks push if @wip features have step definitions |
| `guard-merge-ci-green.sh` | Bash `gh pr merge` | Blocks merge if CI is RED on target branch |
| `guard-bdd-first.sh` | Write/Edit handler/service | Warns when creating handlers without test specs |
| `verify-before-push.sh` | Bash `git push` | Build + tests MUST pass |

---

## Commands

| Command | Effect |
|---|---|
| `/forge` | Full orchestrator cycle |
| `/loop 15m /forge` | Automatic cycle every 15 min |
| `/status` | Quick status in < 10 lines |
| `/dev tasks/todo-xxx.md` | Launch a dev agent on a task |
| `/po` | Handle pending business questions |
