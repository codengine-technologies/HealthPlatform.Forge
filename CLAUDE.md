# CLAUDE.md — Forge Factory Rules

> Read automatically by all agents at startup. Non-negotiable rules.
> When in doubt about a rule → questions/, never improvise.

---

## Forge philosophy — autonomous (since 2026-04-27)

> **Inversion** — la philosophie historique « la forge n'écrit pas de code,
> WindSurf le fait » a été inversée le 2026-04-27. Par défaut **la forge
> développe** ; l'humain n'intervient que pour **merger la PR finale** (HAG,
> règle 10). L'échappatoire est `/start {task-id} no-code` qui rebascule
> l'implémentation côté WindSurf.

### Cycle autonome par défaut

```
/po                                 (humain rédige la US)
    ↓
/start {NNN}                        (crée les branches)
    ↓ (auto)
/develop {NNN}                      (écrit code + tests, build + tests verts,
                                     publie DTOs/interop NuGet, push)
    ↓ (auto)
/sonar {NNN}                        (cleanup SonarQube best-effort 5 itérations,
                                     api-mail uniquement)
    ↓ (auto)
/review {NNN}                       (build + test + DOD + code review,
                                     commit/push/sync develop, ouvre la PR,
                                     label awaiting-human-merge,
                                     rename done-*)
    ↓ (auto)
/tech-writer E{NNN}                 (refresh docs/epics/E{NNN}-{slug}.md)
    ↓
fin de cycle                        (PR en attente de merge humain — HAG)
```

`/forge` répète ce cycle séquentiellement sur tous les `tasks/todo-task-*.md`.
Si une étape échoue, la chaîne s'arrête, écrit `questions/{task-id}.md`,
laisse la task dans son état actuel, et `/forge` passe à la task suivante.

**Objectif** : minimiser les interactions humaines. La forge est autonome
de bout en bout, sauf merge final.

### Échappatoire — mode `no-code`

```
/start {task-id} no-code
```

Casse la chaîne après création des branches. La task reste en `wip-*`,
l'humain implémente dans WindSurf, puis lance `/review {task-id}` lui-même
(qui reste autonome — plus de prompt d'approbation côté forge).

À utiliser quand :
- L'US est exploratoire / heavy-design / hors zone de confort de `/develop`
- Le humain veut piloter à la main pour des raisons spécifiques
- `/develop` ou `/sonar` ont mishandled un cas similaire récemment

### Étapes du cycle — ownership

| Étape | Agent / commande | Écrit du code ? | Notes |
|---|---|---|---|
| Rédaction US | `/po` (humain) | non | Pas de `.feature`, juste `todo-*.md` |
| Création branches | `/start` | non | Pre-flight : tous les repos sur `develop` |
| **Implémentation** | **`/develop`** | **oui** | Test-first, cross-repo dans l'ordre dtos→interop→backend→frontend, publie NuGet pour DTOs/interop. Pour `client-angular` : mode **code-only** (écrit le code sur la branche actuellement checked out, build + test, mais ne touche pas à git — humain gère branche, commit, push, PR TFS). |
| Cleanup Sonar | `/sonar` (api-mail) | oui | Best-effort 5 itérations, accepte les issues restantes |
| Validation + PR | `/review` | non (lecture seule sur le code) | Plus de prompt humain — autonome |
| Doc EPIC | `/tech-writer` | non (écrit dans `docs/epics/` uniquement) | Idempotent |
| **Merge develop** | **humain** | — | **HAG, règle 10 — non négociable** |

### Sonar — étape standard du cycle

`/sonar` n'est plus une « exception d'automation » — c'est une étape
intégrée du cycle autonome, après `/develop` et avant `/review`. Best-effort :
5 itérations max, accepte les issues restantes après ça, hand-off à `/review`
quoi qu'il arrive (sauf erreur de tooling).

`/sonar-s3776` (cognitive complexity, 1 méthode = 1 PR) **reste manuel** —
hors chaîne autonome, sinon on se retrouve avec N PRs par task.

Task lifecycle : `todo → wip → review → done`
- `todo-*.md` : PO a rédigé la US, en attente de `/start`
- `wip-*.md`  : branche créée, `/develop` en cours **OU** mode `no-code` (humain code dans WindSurf)
- `review-*.md` : implémentation finie (par `/develop` ou par l'humain en `no-code`), en attente de `/review`
- `done-*.md` : validée, PR ouverte, en attente du merge humain (HAG, règle 10)

### Epic linkage (optional)

Each `todo-*.md` MAY declare `**Epic**: E{NNN}` to associate the US with a
broader EPIC. The first task that introduces a new EPIC also declares
`**EpicTitle**:` so the technical writer can derive the slug. The EPIC
documentation lives in `docs/epics/E{NNN}-{slug}.md` — **one file per EPIC**,
rebuilt idempotently by `/tech-writer` at the tail of every `/review` cycle.
Tasks without `**Epic**:` are simply ignored by the tech-writer.

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
unless **every forge-automated repo is on `develop`**. The check covers
`api-mail`, `client-blazor`, `dtos-mss`, `sdk`, `host`, `interop-cda` ; it
**explicitly skips** `client-angular` (code-only mode — humain libre de sa
branche), `devops`, `psc-proxy-server`, `psc-proxy-client`, `psc-proxy-dto`
(entièrement hors automation). If any in-scope repo is on a feature branch
(finished work not yet cleaned up, or in-flight manual work), `/start`
aborts and lists the offenders. The human finishes, stashes, or checks out
`develop` in the listed repos, then retries `/start`. The forge never
switches branches on the human's behalf.

---

## Workspace layout — POLYREPO

`D:\TechWatch\HealthPlatform\` is a **meta-workspace**, NOT a git repo. It contains
the forge control plane (CLAUDE.md, agents/, tasks/, questions/, .claude/) and 11
independent git repositories. Every code-touching action MUST happen inside one of
those repos — never at the workspace root.

### Repos

| Repo key | Path | Stack | Build cmd | Test cmd |
|---|---|---|---|---|
| `api-mail` | `Api/Mail` | .NET 10, xUnit | `dotnet build HealthPlatform.Api.Mail.sln` | `dotnet test HealthPlatform.Api.Mail.sln` |
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

### Code-only repo : `client-angular`

`client-angular` is in **code-only mode** — the forge writes Angular code, but
**never touches git**. The remote is TFS (`gh pr` unusable), and the human
keeps full control of branching, commits, push, and PR opening.

Concretely :
- **`/start`** : does **NOT** create a branch on `client-angular`. The human
  is responsible for checking out the right branch in `Client/Angular/` before
  invoking `/start`. Pre-flight does **NOT** check the Angular branch.
- **`/develop`** : writes code on whatever branch is currently checked out in
  `Client/Angular/`. Runs `npm ci && npm run build` and `npm test` to validate.
  Does **NOT** commit, does **NOT** push.
- **`/review`** : re-runs build + test on the current Angular branch.
  Does **NOT** push, does **NOT** open a PR.
- **Human owns** : branch selection, commit, push to TFS, opening the PR.
- A task file MUST list `client-angular` in `**Repos**:` to opt into Angular
  code generation by the forge. The paired-frontend safety net is disabled
  (see below) — Angular is never auto-added.

### Excluded repos (entirely manual)

The following repos are **entirely excluded from forge automation**. The
forge writes no code, runs no build/test, and never touches git for them. If
a task file lists any of them in `**Repos**:`, the forge acknowledges and
adds the note : "managed manually by the human".

**`devops`** — CI/CD configs, human manages independently.

**`psc-proxy-dto`** — human manages independently.

**`psc-proxy-server`** — convention de branche `master` (pas de `develop`), human manages independently.

**`psc-proxy-client`** — convention de branche `master` (pas de `develop`), human manages independently.

For all four :
- `/start` does **NOT** create any branch
- `/develop` does **NOT** write code
- `/review` does **NOT** build, test, or open PRs
- Pre-flight does **NOT** check their current branch

### Paired frontends safety net

The paired frontends safety net is **disabled**. `/start` does NOT auto-add
`client-angular` when a task lists `client-blazor` (or vice-versa). The PO
must explicitly list `client-angular` in `**Repos**:` whenever the forge
should generate Angular code. Without an explicit listing, the human keeps
the Angular implementation as a manual task.

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

### 1. Unit-test-first mandatory

```
Step 0: PO writes the todo-*.md task (Objectif + DOD + Manual Test Plan) — NO .feature file
Step 1: Human (in WindSurf) writes unit tests for the new behavior → verify RED
Step 2: Human implements until GREEN
Step 3: Human runs /review → forge validates (build + tests + DOD) and opens the PR
```

`/review` refuses to open a PR with red tests.

**Test style — unit tests only (xUnit/NUnit/Jest/etc.):**
- Arrange / Act / Assert
- Small, focused, fast
- Mock external collaborators via NSubstitute/Moq/Jest mocks
- One behavior per test, descriptive name (`Method_Context_ExpectedResult`)
- No Reqnroll/SpecFlow, no Gherkin `.feature` files, no step definitions

**BDD (Reqnroll/SpecFlow) is deprecated across this workspace.** The
`mss.mail.bdd.tests` project has been removed (chore bundled with task-008).
Future tasks MUST cover behavior via unit + integration tests. Do not
resurrect `.feature` files.

### 1b. Endpoint coverage mandatory

Each endpoint MUST have at least 1 integration test. Empty scaffolds (endpoints that compile but return nothing meaningful) are bugs. If an endpoint exists, a test proves it works end-to-end through the DI pipeline. `/review` checks this as part of the DOD.

### 1c. Test coverage expectation per task

Every `todo-*.md` MUST list in its DOD the concrete test artifacts the task
will produce. Examples:
- `[ ] Unit tests for {ServiceName} (>= 1 test per public method / branch)`
- `[ ] Integration test for {Endpoint} (happy path + 1 failure mode)`
- `[ ] UI component test for {Component} (render + primary interaction)`

`/review` verifies these items before opening the PR.

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
- Edge case not covered by the task DOD / Manual Test Plan
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

The DOD is the contract entre la forge (`/develop` qui implémente, `/sonar` qui nettoie, `/review` qui valide) et l'humain. If a criterion is not in the DOD, `/review` won't check it. If it IS in the DOD, `/review` WILL check it and REFUSE to open the PR if it's not met. En mode `no-code`, c'est l'humain qui implémente dans WindSurf, mais le contrat DOD/`/review` reste identique.

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

**Pourquoi cette règle :** la forge a mergé sur `develop` sans validation humaine pendant plusieurs vagues. Inacceptable. Le humain doit rester man-in-the-middle. Avec la bascule autonome (2026-04-27), la forge écrit du code et ouvre des PRs end-to-end — HAG est désormais **la seule** barrière humaine du cycle, et c'est précisément pour ça qu'elle est non-négociable.

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
| `verify-before-push.sh` | Bash `git push` | Build + tests MUST pass |

---

## Commands

| Command | Effect |
|---|---|
| `/po` | Write a new US : `todo-*.md` task file only (no .feature). With `--from <doc.md>` : batch-extract US from a markdown document (one-by-one human validation) |
| `/start {task-id}` | Create the working branches in the target repo(s) and **chain into `/develop`** by default. The full cycle then runs autonomously : `/develop` → `/sonar` → `/review` → `/tech-writer`. |
| `/start {task-id} no-code` | Create the working branches and **stop**. Task stays in `wip-*` ; the human implements in WindSurf and runs `/review {task-id}` manually when ready. Escape hatch when `/develop` is unsuitable. |
| `/develop {task-id}` | **Autonomous implementation** : write code + tests, build, test, publish DTOs / interop NuGet packages when contracts change, bump consumers, push, hand off to `/sonar`. See `agents/develop.md`. |
| `/sonar {task-id}` | Best-effort SonarQube cleanup on `api-mail` (5 iterations max, accepts remaining issues). Standard step in the autonomous chain. See `agents/sonar.md`. |
| `/sonar-s3776 api-mail` | **[Manual]** Reduce cognitive complexity of ONE method (S3776). One method = one PR. Characterisation tests written first. Out of the autonomous chain. See `.claude/commands/sonar-s3776.md`. |
| `/review {task-id}` | Validate the implementation (build + tests + DOD + code review), commit/push/sync develop, open the PR (label `awaiting-human-merge`), rename `done-*`, chain into `/tech-writer`. Autonomous — no human prompt. |
| `/merge {task-id} --i-tested` | **[Human only]** After the human has tested the US end-to-end on the open PRs, squash-merge each pushable PR, sync `develop`, delete the branches, archive the task `archived-*`. Refuses without `--i-tested`, on `awaiting-us-completion` label, or red CI. Never invoked by `/forge` — HAG (rule 10) stays. See `agents/merge.md`. |
| `/tech-writer E{NNN}` | Refresh `docs/epics/E{NNN}-{slug}.md` from all tasks that declare `**Epic**: E{NNN}`. Called automatically at the tail of `/review` ; can be run manually for retro-generation or `--refresh`. See `agents/technical-writer.md`. |
| `/forge` | Loop autonome : pour chaque `tasks/todo-task-*.md`, déclenche `/start` → `/develop` → `/sonar` → `/review` → `/tech-writer`. Séquentiel (pas de parallélisme). Stop sur la première task qui échoue (écrit `questions/`, passe à la suivante). **Ne déclenche jamais `/merge`** — HAG, règle 10. |
| `/status` | Quick status in < 10 lines |
| `/publish-dtos` | Publish the DTO NuGet package and bump consumers (manual command — `/develop` does the equivalent inline as part of the autonomous cycle). |
| `/kickoff` | Bootstrap a new project (scaffold `.claude/`, agents, templates) |
