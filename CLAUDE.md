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

### 10. Human Acceptance Gate (HAG) — non-négociable

**Aucune PR n'est mergée sur `develop` sans validation humaine explicite, même si toutes les gates automatiques (CI distante, Evaluator, Copilot, QA, Designer) sont vertes.**

L'orchestrator n'a JAMAIS le droit de merger une PR de son propre chef. Le merge a lieu uniquement :
- sur instruction explicite du humain dans la conversation ("merge #X"), OU
- via la pose du label `human-approved` sur la PR (que seul le humain peut poser), OU
- par le humain lui-même via `gh pr merge` ou l'UI GitHub

**Pas d'exception.** Même les PRs triviales (CI fix, doc fix, version bump) attendent une validation humaine. La règle vaut pour les 11 repos de la forge.

**Contrat dev agent enrichi** : chaque dev agent DOIT inclure dans son rapport final une section `## Manual Test Plan` listant :
- la commande exacte pour lancer l'app localement
- l'écran/URL à ouvrir
- les actions à effectuer
- ce que le humain doit voir/vérifier
- les données de test si nécessaires (user, mot de passe, mail à envoyer, etc.)

**Contrat orchestrator** :
1. Quand toutes les gates automatiques sont vertes, l'orchestrator NE merge PAS.
2. Il poste le `Manual Test Plan` du dev agent comme commentaire de PR (`gh pr comment`).
3. Il pose le label `awaiting-human-test` (`gh pr edit --add-label`).
4. Il reporte au humain dans la conversation : "PR #X attend ta validation — teste puis dis 'merge #X' ou pose le label `human-approved`."
5. Il passe à autre chose et NE relance PAS le merge automatiquement.

**Nouveau statut agent** : `DONE_AWAITING_HUMAN_TEST` — utilisé par le dev agent quand il considère le travail technique terminé et que toutes les gates automatiques peuvent être vertes. Remplace `DONE` dès que cette règle est en vigueur.

**Pourquoi cette règle :** la forge a mergé sur `develop` sans aucune validation humaine pendant plusieurs vagues (drafts, folders, signature, notifications-022/023). Combiné au trou structurel CI (workflows triggered uniquement sur `master` jusqu'au fix de PR codengine-technologies/HealthPlatform.Client#20), des features ont atterri sur `develop` sans validation distante NI humaine. Inacceptable. Le humain doit rester man-in-the-middle.

### 11. US-complete merge gate — non-négociable

**Aucune PR ne merge sur `develop` tant que la User Story complète n'est pas fonctionnellement opérationnelle ET validée humainement de bout en bout.**

Pas de "scaffold first, enrich later". Pas de plomberie nue mergée en attendant l'enrichissement. Pas de "fausse v1" sur develop.

**Conséquences :**
- Une US découpée en plusieurs waves (wave 1 plomberie + wave 2 enrichissement) reste **entièrement en attente** jusqu'à ce que toutes les waves soient en PR prête. Les PRs intermédiaires attendent.
- Le test humain (règle 10 HAG) se fait sur la **US assemblée**, pas sur chaque wave isolée. 1 validation humaine = la US entière, pas chaque morceau.
- L'orchestrator marque les PRs intermédiaires `awaiting-us-completion` et NE propose PAS de merge tant que toutes les waves d'une même US ne sont pas prêtes.
- Les PRs vraiment orthogonales à toute US en cours (CI/devops indépendant, hotfix sécurité, bump deps non lié) peuvent merger indépendamment. **En cas de doute, demander au humain.**

**Pourquoi :** une wave 1 "plomberie SSE/SignalR + toast générique" mergée sans la wave 2 enrichissement clinique CDA aurait posé une "fausse v1 notifications" sur develop avec aucune valeur médicale (pas de patient, pas de findings, pas de sévérité réelle). Inacceptable. Le médecin doit voir la valeur du premier coup, pas attendre une wave suivante.

Cette règle compose avec la règle 10 HAG : HAG dit "pas de merge sans validation humaine", US-complete dit "pas de validation humaine sur des morceaux".

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
