# CLAUDE.md — Forge Factory Rules

> Read automatically by all agents at startup. Non-negotiable rules.
> When in doubt about a rule → questions/, never improvise.

---

## Forge philosophy — lean

The forge is strictly limited to **4 actions** :

1. **PO** — help the human write user stories (.feature + `todo-*.md` task file)
2. **Start** — create ONE working branch in the target repo(s) (`/start`)
3. **Validate** — verify the human's implementation : build + tests + DOD (`/review`)
4. **PR** — open the pull request and mark the task `done-*` (still inside `/review`)

**Implementation is done by the human in WindSurf with AI pair programming.**
The forge does NOT dispatch dev agents, does NOT write code, does NOT run QA /
Designer reviews automatically, does NOT "find extra work" when idle. If there
is nothing to do, the forge stays idle.

Task lifecycle : `todo → wip → review → done`
- `todo-*.md` : PO wrote the US, awaiting branch creation
- `wip-*.md`  : branch created, human is implementing in WindSurf
- `review-*.md` : human finished, awaiting forge validation
- `done-*.md` : validated, PR opened, awaiting human merge (HAG, rule 10)

### 1 US = 1 task file = 1 branch name across every impacted repo

**A user story is a single, end-to-end slice of product value.** The PO produces
**one** `todo-*.md` task file per US, listing **every** repo the US touches in
a `**Repos**:` field (plural). A full-stack feature touches at minimum :

- `api-mail` (backend)
- `client-blazor` (new frontend)
- `client-angular` (legacy frontend)

and possibly `dtos-mss` or others.

**`/start` creates the SAME branch name `feat/{task-id}-{slug}` on each listed
repo** — one logical branch, multiple physical checkouts. The human implements
the US end-to-end on these branches in WindSurf (backend + blazor + angular in
lockstep). `/review` validates every repo and opens one PR per pushable repo,
linking them together in the task file.

**No more split `todo-back-*` / `todo-front-blazor-*` / `todo-front-angular-*`
files.** One US = one task = one branch name.

**Exception** : a US that is genuinely scoped to a single layer (e.g. pure
backend migration, pure Angular-only polish) may list fewer repos, but this
must be justified in the task body. The default is "all 3 frontends and
backend".

**Pre-flight for `/start`** : the forge refuses to create a new working branch
unless **every repo in the polyrepo is on `develop`**. If any repo is on a
feature branch (finished work not yet cleaned up, or in-flight manual work),
`/start` aborts and lists the offenders. The human finishes, stashes, or
checks out `develop` in the listed repos, then retries `/start`. The forge
never switches branches on the human's behalf.

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
| `client-angular` | `Client/Angular` | Angular, Node | `npm ci && npm run build` | `npm test` |
| `dtos-mss` | `Dtos` | .NET 10 class lib (NuGet) | `dotnet build HealthPlatform.Dtos.Mss.csproj` | n/a |
| `sdk` | `Sdk` | .NET 10 host SDK | `dotnet build HealthPlatform.Host.Sdk.csproj` | n/a |
| `host` | `Host/Modules` | .NET 10 modules | `dotnet build` | n/a |
| `interop-cda` | `interop/interop.cda.parser` | .NET 10 | `dotnet build interop.cda.parser.sln` | `dotnet test` |
| `psc-proxy-server` | `psc/proxy/psc.proxy.server` | .NET 10 DDD | `dotnet build psc.proxy.server.sln` | `dotnet test` |
| `psc-proxy-client` | `psc/proxy/psc.proxy.client` | .NET 10 client | `dotnet build psc.proxy.client.sln` | n/a |
| `psc-proxy-dto` | `psc/proxy/psc.proxy.dto` | .NET 10 DTOs | `dotnet build psc.proxy.dto.sln` | n/a |
| `devops` | `DevOps` | CI/CD configs | n/a | n/a |

### Excluded repos (managed manually)

The following repos are **entirely excluded from forge automation**. The human
manages them manually (branches, builds, tests, PRs). The forge ignores them
in pre-flight checks, `/start`, and `/review`.

**`client-angular`** — TFS remote, human manages branches/PRs manually.

**`devops`** — CI/CD configs, human manages independently.

**`psc-proxy-dto`** — human manages independently.

For both :
- `/start` does **NOT** create any branch
- `/review` does **NOT** build, test, or open PRs
- Pre-flight does **NOT** check their current branch
- If a task file lists them in `**Repos**:`, the forge acknowledges but skips
  all automation. A note is added : "managed manually by the human"

### Paired frontends safety net

`client-angular` is excluded from forge automation (see above). The paired
frontends safety net is **disabled** — `/start` does NOT auto-add
`client-angular` to any task. The human is responsible for creating the
Angular branch and implementing the Angular side manually.

### Auto-included repo : `dtos-mss`

`dtos-mss` is the shared DTO package consumed by `api-mail` and `client-blazor`.
**`/start` MUST always create a branch on `dtos-mss`** alongside `api-mail` and
`client-blazor`, even if the task file does not explicitly list it in `**Repos**:`.
Any US that touches `api-mail` or `client-blazor` may need DTO changes, so the
branch must exist proactively. If no DTO changes are needed, the branch will
simply have no commits and no PR will be opened for it.

### Cross-repo dependencies

- `api-mail`, `client-blazor` consume `dtos-mss` as a NuGet package.
  `client-angular` consumes the contracts via its own TypeScript types (regenerated manually).
  Any contract change → `/publish-dtos` first (publishes + bumps .NET consumers).
- `client-blazor` and `host` consume `sdk`.
- `psc-proxy-server` consumes `psc-proxy-dto`.
- All other links are independent.

### Task → Repos routing

Each `tasks/todo-*.md` MUST declare a `**Repos**:` field (plural) with the
comma-separated list of every repo key the US touches. For a full-stack US the
list is at minimum `api-mail, client-blazor, client-angular`. `/start` creates
the same branch name in every listed repo, and `/review` `cd`s into each path
to run the repo-specific build/test before opening one PR per pushable repo.

---

## Absolute rules

### 1. BDD-first mandatory

```
Step 0: PO writes .feature files BEFORE any implementation
Step 1: Human (in WindSurf) reads the existing .feature — never creates/modifies them
Step 2: Human writes step definitions → verify RED
Step 3: Human implements until GREEN
Step 4: Human runs /review → forge validates and opens the PR when all Gherkin scenarios are GREEN
```

`/review` refuses to open a PR with red tests.

### 1b. Endpoint coverage mandatory

Each endpoint MUST have at least 1 integration test. Empty scaffolds (endpoints that compile but return nothing meaningful) are bugs. If an endpoint exists, a test proves it works end-to-end through the DI pipeline. `/review` checks this as part of the DOD.

### 1a. Feature file purity

**.feature files are PO property.** Neither the forge nor WindSurf implementation sessions modify `.feature` files. If a `.feature` is missing or incomplete → stop and ask the PO (human, via `/po`).

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

### 2. Local verification mandatory BEFORE the PR

**No code leaves the machine without local verification.**

Build + test commands are **per-repo** (see the Repos table above). Run them from
the repo root, never from the workspace root. Example for `api-mail`:

```bash
cd Api/Mail
dotnet build HealthPlatform.Api.Mail.sln    # MUST return 0 errors
dotnet test  HealthPlatform.Api.Mail.sln    # MUST pass
```

`/review` re-runs these commands before opening the PR and refuses RED.

### 4. Merge-based sync, not rebase

**When a PR has conflicts with develop, use `git merge origin/develop` instead of `git rebase`.**

### 5. PR hygiene (polyrepo)

- **1 task = 1 branch = 1 PR per repo** towards `develop` — in the **repo declared by the
  task's `**Repos**:` field**. `/start` creates the same branch on every listed repo, `/review` opens one PR per pushable repo.
- A task that legitimately needs to touch N repos lists each repo — `/start` creates
  the SAME branch name `feat/{task-id}-{slug}` in each, and `/review` opens N PRs
  (one per repo) and links them in the task file.
- Max ~30 modified files per PR
- After each merge (by the human) → verify that repo's `develop` CI GREEN within 2 minutes
- The workspace root (`D:\TechWatch\HealthPlatform\`) is NEVER pushed — it has no remote.

### 6. Isolated scopes

A task only touches files in its module. If a cross-module need appears → stop, ask the PO.

### 7. Fail-fast mandatory

Stop and create `questions/{task-id}.md` if:
- Edge case not covered by Gherkin
- Business rule ambiguity
- Need to modify frozen files

### 7c. Schema migration audit

After generating any database migration (EF Core, Prisma, Alembic, Knex, etc.), the human (or `/review`) MUST:
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

Every task file (`todo-*.md`) MUST include a `## Definition of Done` section with concrete, verifiable criteria. No subjective criteria ("clean code") — only binary checks `/review` can verify.

The DOD is the contract between the human (implementing in WindSurf) and `/review`. If a criterion is not in the DOD, `/review` won't check it. If it IS in the DOD, `/review` WILL check it and REFUSE to open the PR if it's not met.

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

**Aucune PR n'est mergée sur `develop` par la forge. Jamais. Le merge est l'action exclusive du humain.**

`/review` ouvre la PR et pose le label `awaiting-human-merge`. Le humain teste, puis merge lui-même via `gh pr merge` ou l'UI GitHub. Pas d'exception — même les PRs triviales (CI fix, doc fix, version bump).

**Contrat task file** : chaque `todo-*.md` doit contenir une section `## Manual Test Plan` listant :
- la commande exacte pour lancer l'app localement
- l'écran/URL à ouvrir
- les actions à effectuer
- ce que le humain doit voir/vérifier
- les données de test si nécessaires

`/review` recopie ce bloc dans le body de la PR au moment de l'ouvrir.

**Pourquoi cette règle :** la forge a mergé sur `develop` sans validation humaine pendant plusieurs vagues. Inacceptable. Le humain doit rester man-in-the-middle, et depuis la bascule "implémentation en WindSurf", il l'est par construction — la forge ne pousse jamais de code, elle ouvre des PRs que le humain merge.

### 11. US-complete merge gate — non-négociable

**Aucune PR ne merge sur `develop` tant que la User Story complète n'est pas fonctionnellement opérationnelle ET validée humainement de bout en bout.**

Pas de "scaffold first, enrich later". Pas de plomberie nue mergée en attendant l'enrichissement. Pas de "fausse v1" sur develop.

**Conséquences :**
- Une US découpée en plusieurs waves (wave 1 plomberie + wave 2 enrichissement) reste **entièrement en attente** jusqu'à ce que toutes les waves soient en PR prête. Les PRs intermédiaires attendent.
- Le test humain (règle 10 HAG) se fait sur la **US assemblée**, pas sur chaque wave isolée. 1 validation humaine = la US entière, pas chaque morceau.
- `/review` marque les PRs intermédiaires `awaiting-us-completion` au lieu de `awaiting-human-merge` tant que toutes les waves d'une même US ne sont pas prêtes.
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
| `verify-before-push.sh` | Bash `git push` | Build + tests MUST pass |

---

## Commands

| Command | Effect |
|---|---|
| `/po` | Write a new US : `.feature` + `todo-*.md` task file. With `--from <doc.md>` : batch-extract US from a markdown document (one-by-one human validation) |
| `/start {task-id}` | Create the working branch in the target repo(s), move task to `wip-*` |
| `/review {task-id}` | Validate the human's implementation (build + tests + DOD), open the PR, move task to `done-*` |
| `/forge` | Lean cycle : report state, auto-run `/review` on any `review-*.md`, list PRs awaiting human merge |
| `/status` | Quick status in < 10 lines |
| `/publish-dtos` | Publish the DTO NuGet package and bump consumers |
| `/kickoff` | Bootstrap a new project (scaffold `.claude/`, agents, templates) |
