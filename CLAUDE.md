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
/forge-simplify {NNN}               (passe qualité /simplify : reuse/simplif/
                                     efficacité/altitude — quality only, pas de
                                     chasse aux bugs ; re-valide + commit/push ;
                                     skip si rien à simplifier ; jamais
                                     dtos-mss/interop)
    ↓ (auto)
/sonar {NNN}                        (cleanup SonarQube best-effort 5 itérations,
                                     api-mail uniquement — skip si non touché)
    ↓ (auto)
/lint-angular {NNN}                 (cleanup ESLint best-effort 5 itérations,
                                     client-angular uniquement — skip si non touché)
    ↓ (auto)
/lint-mobile {NNN}                  (cleanup ESLint best-effort 5 itérations,
                                     client-mobile uniquement — skip si non touché)
    ↓ (auto)
/verify-visual {NNN}                (captures Playwright des écrans mobiles
                                     touchés, pairées à la référence Stitch —
                                     bloquant uniquement sur écran blanc/crash ;
                                     skip si aucun écran touché)
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

### Branche staging par run `/forge`

Chaque run `/forge` **agrège le travail validé de toutes ses tasks sur une
branche staging par repo pushable**, pour que l'humain puisse `git checkout`
**une** branche et tester le lot complet de bout en bout au lieu de jongler
entre N branches `feat/*`.

- **Nom** : `forge/staging-task-{début}-{fin}-{date}` (`{début}`/`{fin}` =
  plus petit / plus grand task-id du backlog du run, même id deux fois si une
  seule task ; `{date}` = `YYYYMMDD`). Même nom sur tous les repos.
- **Fraîche depuis `develop`** : créée paresseusement depuis `origin/develop`
  à la première task validée qui pousse un `feat/*` sur ce repo. Jamais
  réutilisée d'un run à l'autre, jamais périmée, jamais de branche vide.
- **Scope** : repos pushables uniquement (`api-mail`, `client-blazor`,
  `client-mobile`, `dtos-mss`, `sdk`, `host`, `interop-cda`). **Jamais**
  `client-angular` (code-only), `devops`, `psc-proxy-*`.
- **Dernier maillon par task, après `/review`** : `git merge --no-ff
  feat/{task}` d'une branche **déjà nettoyée par toute la chaîne qualité**
  (`/forge-simplify`, `/sonar`, `/lint-angular`, `/lint-mobile` ont committé
  leurs fixes sur `feat/*` **avant** `/review`). Staging hérite mécaniquement
  de tous les fixes qualité ; aucune re-qualification sur staging.
- **Best-effort, jamais un point d'échec** : un conflit d'agrégation →
  `git merge --abort`, log, la PR `feat/* → develop` de la task reste intacte,
  la task reste `done-*`, le run continue.
- **HAG préservé, pas de PR staging** : les PRs `feat/* → develop` par task
  (label `awaiting-human-merge`) restent inchangées et sont le véhicule de
  merge. La branche staging n'a **aucune** PR vers `develop` et la forge ne
  merge **jamais** `develop` (règle 10). Seules les tasks passées par `/review`
  (build + tests + DOD + code review verts) rejoignent staging.

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
| Cleanup Simplify | `/forge-simplify` | oui | Wrapper forge autour du built-in `/simplify` : passe qualité (reuse/simplif/efficacité/altitude) **quality-only** sur le code frais, par repo, re-valide (build + tests = filet anti-régression), commit/push pushables, `client-angular` code-only. Best-effort, non bloquant : rollback du repo si une régression apparaît. **Jamais** `dtos-mss`/`interop-cda` (porteurs de contrat). Skip clean si rien à simplifier. |
| Cleanup Sonar | `/sonar` (api-mail) | oui | Best-effort 5 itérations, accepte les issues restantes. Skip clean si api-mail non touché. |
| Cleanup Lint Angular | `/lint-angular` (client-angular) | oui | Best-effort 5 itérations (`lint:fix` + fix manuels), accepte les erreurs restantes. Code-only — ne touche jamais à git. Skip clean si client-angular non touché. |
| Cleanup Lint Mobile | `/lint-mobile` (client-mobile) | oui | Best-effort 5 itérations (`ng lint --fix` + fix manuels), accepte les erreurs restantes. **Automation git complète** (remote GitHub) : commit/push des fixes. Skip clean si client-mobile non touché. |
| Vérification visuelle | `/verify-visual` (client-mobile) | non (captures uniquement, commit des PNG) | Playwright headless : session factice + API mockée (fixtures), capture 390×844 de chaque écran touché, pairée à la référence Stitch dans la PR. **Bloquant uniquement sur écran blanc/crash** ; écart design = best-effort (juge = humain au HAG). Skip clean si aucun écran touché. |
| Validation + PR | `/review` | non (lecture seule sur le code) | Plus de prompt humain — autonome. Recopie KPIs Sonar + table de vérification visuelle dans le body des PRs. |
| Doc EPIC | `/tech-writer` | non (écrit dans `docs/epics/` uniquement) | Idempotent |
| **Merge develop** | **humain** | — | **HAG, règle 10 — non négociable** |

### Simplify + Sonar + Lint Angular + Lint Mobile — étapes standard du cycle

`/forge-simplify` (tous repos code), `/sonar` (api-mail), `/lint-angular`
(client-angular) et `/lint-mobile` (client-mobile) ne sont pas des
« exceptions d'automation » — ce sont **des étapes intégrées du cycle
autonome**, insérées entre `/develop` et `/review`, dans cet ordre
(`/forge-simplify` en premier, juste après `/develop`, pour que `/sonar`,
`/lint-angular` et `/lint-mobile` re-scannent et re-valident derrière ce que la
passe qualité a touché). Toutes sont best-effort : acceptation des findings
restants, hand-off à l'étape suivante quoi qu'il arrive (sauf erreur de
tooling). Toutes skip cleanly quand leur repo cible n'a pas été touché
par la task — la chaîne saute simplement à l'étape suivante.

`/lint-mobile` est le pendant de `/lint-angular` pour `client-mobile` (app
Ionic/Angular). Différence clé : `client-mobile` a un remote **GitHub** (pas
TFS), donc `/lint-mobile` est en **automation git complète** — il commit et
push ses fixes, contrairement à `/lint-angular` qui reste code-only.

`/forge-simplify` est **quality-only** (reuse / simplification / efficacité /
altitude) : il ne chasse jamais les bugs (c'est `/code-review`), les tests
existants sont son filet anti-régression, et il **ne touche jamais**
`dtos-mss`/`interop-cda` (porteurs de contrat → éviter un republish NuGet
cosmétique). Le built-in `/simplify` standalone reste dispo pour l'usage
ad-hoc humain (simplifier le diff courant, sans cérémonie forge).

`/sonar-s3776` (cognitive complexity, 1 méthode = 1 PR) **reste manuel** —
hors chaîne autonome, sinon on se retrouve avec N PRs par task.

### Conventions apprises — boucle d'auto-amélioration

Deux fichiers de conventions vivent à la racine du workspace et ferment la
boucle « le nettoyage d'aujourd'hui devient la prévention de demain » :

| Fichier | Alimenté par | Lu par |
|---|---|---|
| `conventions/angular.md` | `/lint-angular`, `/lint-mobile` (règles ESLint corrigées **manuellement**) | `/develop` avant tout code Angular/Ionic |
| `conventions/csharp.md` | `/sonar` (règles corrigées manuellement, new-code en priorité) | `/develop` avant tout code C# |

Protocole : première correction manuelle d'une règle → entrée créée ;
récidive → compteur incrémenté. `/develop` applique les « Consignes »
d'emblée — une récidive lint/Sonar sur du code frais signale que le fichier
n'a pas été lu. Les fixes de l'auto-fixer ESLint ne comptent pas (gratuits).
Format d'entrée et protocole détaillés en tête de chaque fichier.

Task lifecycle : `todo → wip → review → done → archived`
- `tasks/todo-*.md` : PO a rédigé la US, en attente de `/start`
- `tasks/wip-*.md`  : branche créée, `/develop` en cours **OU** mode `no-code` (humain code dans WindSurf)
- `tasks/review-*.md` : implémentation finie (par `/develop` ou par l'humain en `no-code`), en attente de `/review`
- `tasks/done-*.md` : validée, PR ouverte, en attente du merge humain (HAG, règle 10)
- `tasks/archived/archived-*.md` : **état terminal**, post-merge. Le fichier est déplacé dans le sous-répertoire `tasks/archived/` par `/merge` une fois la PR mergée par l'humain. Les globs `/forge` et `/status` ne recursent pas — ce sous-dir reste invisible des cycles actifs. Seul `/tech-writer` le scanne pour le changelog historique.

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

and, when the mobile messaging client is impacted, `client-mobile`
(Ionic/Angular mobile frontend), plus possibly `dtos-mss` or others.

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
`api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk`, `host`,
`interop-cda` ; it **explicitly skips** `client-angular` (code-only mode —
humain libre de sa branche), `devops`, `psc-proxy-server`,
`psc-proxy-client`, `psc-proxy-dto` (entièrement hors automation). If any in-scope repo is on a feature branch
(finished work not yet cleaned up, or in-flight manual work), `/start`
aborts and lists the offenders. The human finishes, stashes, or checks out
`develop` in the listed repos, then retries `/start`. The forge never
switches branches on the human's behalf.

---

## Workspace layout — POLYREPO

`D:\TechWatch\HealthPlatform\` is the **forge control plane** — CLAUDE.md,
agents/, tasks/, questions/, Docs/, .claude/ — and it contains the code
repositories as sibling directories. Every code-touching action MUST happen
inside one of those repos, never at the workspace root.

> ⚠️ **Corrigé le 2026-08-02 (task-219).** Ce paragraphe affirmait que la racine
> n'est **pas** un dépôt git, et la règle 5 qu'elle **n'a pas de remote**. Les
> deux étaient faux : la racine est le dépôt **`HealthPlatform.Forge`**, sur
> `develop`, avec un remote GitHub. Le plan de contrôle est donc **versionné et
> poussé** — les task files, la doc d'EPIC et les skills se commitent comme le
> reste. Découvert en constatant que `git -C Host/Modules status` remontait des
> fichiers de la racine.

> ⚠️ **`Host/Modules` n'est pas un dépôt** — il ne contient aucun `.git` et
> `git ls-files Host/` renvoie 0 fichier. Toute commande git qui le cible
> remonte donc jusqu'au dépôt de la forge et répond pour lui. **Conséquence
> pratique : le pré-flight de `/start` ne mesure rien sur `host`** ; il lit la
> branche du plan de contrôle. Ne pas s'y fier, et ne pas accuser `host` quand
> le pré-flight le signale.

### Repos

| Repo key | Path | Stack | Build cmd | Test cmd |
|---|---|---|---|---|
| `api-mail` | `Api/Mail` | .NET 10, xUnit | `dotnet build HealthPlatform.Api.Mail.sln` | `dotnet test HealthPlatform.Api.Mail.sln` |
| `client-blazor` | `Client/Blazor` | Blazor WASM, .NET 10, xUnit | `dotnet build HealthPlatform.Client.sln` | `dotnet test HealthPlatform.Client.sln` |
| `client-angular` | `Client/Angular` | Angular, Node | `npm ci && npm run build` | `npm test` |
| `client-mobile` | `Client/Mobile` | Ionic 8 + Angular 20 + Capacitor, Node | `npm ci && npm run build` | `npm test -- --watch=false --browsers=ChromeHeadless` |
| `dtos-mss` | `Dtos` | .NET 10 class lib (NuGet) | `dotnet build HealthPlatform.Dtos.Mss.csproj` | n/a |
| `sdk` | `Sdk` | .NET 10 host SDK | `dotnet build HealthPlatform.Host.Sdk.csproj` | n/a |
| `host` | `Host/Modules` | .NET 10 modules | `dotnet build` | n/a — ⚠️ **pas de `.git`**, cf. l'avertissement ci-dessus |
| `interop-cda` | `interop` | .NET 10 | `dotnet build interop.cda.parser.sln` | `dotnet test` |
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

### Full-automation frontend : `client-mobile`

`client-mobile` (`Client/Mobile`) is the **mobile messaging client** — an
Ionic 8 + Angular 20 + Capacitor app (plain Angular CLI, **not** Nx). Unlike
`client-angular`, its remote is **GitHub** (`gh pr` usable) and its
integration branch is **`develop`**, so it is a **fully-automated, pushable
repo** : the forge writes code **and owns git** (branch, commit, push, PR,
merge) exactly like `api-mail` / `client-blazor`.

Concretely :
- **`/start`** : creates the branch `feat/{task-id}-{slug}` from `origin/develop`
  and pushes it (pushable repo). Pre-flight **checks** that `client-mobile` is
  on `develop`.
- **`/develop`** : writes code on the feature branch, runs `npm ci && npm run
  build` and `npm test -- --watch=false --browsers=ChromeHeadless`, commits and
  pushes. Before coding each mobile screen it invokes **`/stitch-design`**
  (Step 5c sub-step) to get the design reference (see below).
- **`/stitch-design`** : the **design sub-step** of `/develop` for mobile
  screens. Stitch is the **single source of truth for the `client-mobile` UI
  design** (Stitch project `client-mobile`, id `10088502293310567548`,
  MOBILE). Convention : **Stitch screen title = component/page kebab-case name**
  — le nom de fichier/sélecteur (`inbox`, `mail-list`, `mail-folder-list`, …),
  pas le nom de classe PascalCase. For each target screen it **reuses**
  the matching Stitch screen if present, else **creates** it
  (`generate_screen_from_text`), and logs the screenshot + HTML/CSS reference in
  the task file. Stitch output is a **reference, not applied code** : `/develop`
  translates the visual/structural intent into Ionic, never pastes the HTML.
  Best-effort & non-blocking (a Stitch/MCP outage doesn't kill the task). The
  Stitch MCP has **no rename** op, so renaming existing screens to match
  component names is the **human's job in the Stitch UI**. Deux pièges connus
  du connecteur MCP : un **timeout de `generate_screen_from_text` = succès
  probable côté Stitch** (jamais de re-génération — source de doublons ;
  détection du nouvel écran par **diff des `screenInstances` de
  `get_project`**), et **`list_screens` est périmé** pendant des heures sur
  les créations récentes (`get_project` fait foi). See
  `agents/stitch-design.md`.
- **`/forge-simplify`** : eligible (frontend code repo, pushable) — quality
  pass, re-validate, commit/push. Not a contract carrier.
- **`/lint-mobile`** : its dedicated ESLint cleanup step (`ng lint --fix` +
  manual fixes, best-effort 5 iterations), inserted after `/lint-angular`.
  Commits/pushes its fixes (git automation, unlike `/lint-angular`).
- **`/review`** : build + test on the feature branch, opens the PR via `gh`,
  label `awaiting-human-merge`.
- **`/merge`** : squash-merges the PR, syncs `develop`, deletes the remote
  branch (human-triggered, HAG).

Like `client-angular`, `client-mobile` consumes the backend contracts via its
own **TypeScript types** (regenerated manually) — it is **not** a NuGet
consumer, so a `dtos-mss` contract change never auto-bumps it. A task MUST list
`client-mobile` explicitly in `**Repos**:` to opt into mobile code generation
(the paired-frontend safety net is disabled — see below).

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
`client-angular` (or `client-mobile`) when a task lists `client-blazor` (or
vice-versa). The PO must explicitly list `client-angular` and/or
`client-mobile` in `**Repos**:` whenever the forge should generate Angular
or mobile code. Without an explicit listing, the human keeps that frontend's
implementation as a manual task.

### Auto-included repo : `dtos-mss`

`dtos-mss` is the shared DTO package consumed by `api-mail` and `client-blazor`.
**`/start` MUST always create a branch on `dtos-mss`** alongside `api-mail` and
`client-blazor`, even if the task file does not explicitly list it in `**Repos**:`.
Any US that touches `api-mail` or `client-blazor` may need DTO changes, so the
branch must exist proactively. If no DTO changes are needed, the branch will
simply have no commits and no PR will be opened for it.

### Cross-repo dependencies

- `api-mail`, `client-blazor` consume `dtos-mss` as a NuGet package.
  `client-angular` and `client-mobile` consume the contracts via their own
  TypeScript types (regenerated manually).
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
- Le **plan de contrôle** (racine du workspace, dépôt `HealthPlatform.Forge`)
  est versionné et poussé sur `develop`, **sans PR** : c'est le journal de la
  forge, pas du code applicatif. Il ne suit donc pas la règle 1 US = 1 PR.
  (Corrigé le 2026-08-02 — cette ligne affirmait qu'il n'avait pas de remote.)

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

### 12. Gestion d'erreurs API — `ProblemDetails` (RFC 7807) obligatoire — non-négociable

**Toute réponse d'erreur d'un controller backend (4xx/5xx) DOIT sortir en
`application/problem+json` conforme RFC 7807, produite par le
`GlobalExceptionHandler` (`IExceptionHandler`), jamais par du code ad hoc dans
l'action.** (Gravé par task-055.)

Concrètement, pour toute nouvelle US backend (`api-mail` et tout futur service
.NET de la plateforme) :

- **Interdit** : les `try/catch` boilerplate par action qui retournent
  `StatusCode(500, "...")`, `ErrorResponse(Success, Message)`, ou une string
  brute. La gestion des exceptions est **déléguée au `GlobalExceptionHandler`**
  branché via `AddProblemDetails()` + `AddExceptionHandler<GlobalExceptionHandler>()`
  + `app.UseExceptionHandler()`.
- **Mapping par type, pas par chaîne** : lever une exception métier typée
  (`NotFoundException` → 404, `ValidationException` → 400,
  `ConflictException` → 409, `UnavailableException` → 503) ou retourner le
  `ResultStatus` Ardalis correspondant. Aucune heuristique de mots-clés sur le
  message.
- **`OperationCanceledException` → 499** est gérée centralement, jamais
  ré-attrapée dans chaque action.
- **Zéro fuite** : le `detail` exposé au client ne contient jamais de stack
  trace, de message d'exception système brut, ni de donnée de santé
  (INS/NIR/contenu CDA/MSSanté). Le détail technique reste dans les logs
  serveur, corrélé par `traceId`.
- **Frontends** : consommer le schéma `ProblemDetails` (`title`/`detail`/`status`)
  — `HttpRequestService` (Blazor) et le mapping d'erreurs MSS (Angular) lisent
  `ProblemDetails`, pas l'ancien `ErrorResponse`.

`GlobalExceptionHandler` (`Api/Mail/src/Api/ErrorHandling/GlobalExceptionHandler.cs`)
est le mécanisme canonique de référence.

**Pourquoi :** avant task-055, ~93 `catch (Exception)`, ~97 retours `500`
codés en dur et trois formats d'erreur incohérents coexistaient, avec un
mapping HTTP par heuristique de mots-clés fragile. Un format d'erreur unique et
typé est une exigence de robustesse, d'observabilité et de non-fuite de données
de santé.

---

### 13. La chaîne autonome ne s'interrompt pas — non-négociable

**Chaque étape de la chaîne invoque l'étape suivante via l'outil `Skill`, dans le
même tour, sans rapport intermédiaire et sans rien demander à l'humain.**

```
/start → /develop → /forge-simplify → /sonar → /lint-angular → /lint-mobile
       → /verify-visual → /review → /tech-writer
```

**Pourquoi cette règle existe** (posée le 2026-08-04, sur constat humain) : les
fichiers de commande décrivaient le chaînage en prose — « hand off to
`/forge-simplify` » — sans jamais **ordonner** d'appeler l'étape suivante.
L'agent lisait « passe la main », rédigeait un rapport de fin d'étape, et rendait
la main. L'humain devait relancer « continue la chaîne » à chaque maillon, ce qui
vide de son sens la boucle autonome et transforme un cycle en huit interactions.

**Les DEUX seuls arrêts légitimes** :

1. **Fail-fast** sur un vrai blocage technique → `questions/{task-id}.md` écrit,
   arrêt annoncé. Plafond d'itérations, build irréparable, ambiguïté métier.
2. **Décision humaine explicitement requise** par le task file (encadré
   « arbitrage humain requis »). Tout le reste est traité d'abord ; la question
   ne porte que sur ce point.

**Ce qui n'est PAS un motif d'arrêt** : une étape qui skippe proprement, une
étape best-effort avec des findings restants, un flaky pré-existant identifié,
la longueur du travail déjà fait dans le tour, ou l'envie de faire valider une
étape intermédiaire. **HAG (règle 10) est la seule barrière humaine du cycle, et
elle se situe au merge de la PR — jamais avant.**

Un rapport intermédiaire entre deux étapes n'est pas une faute de style : il
**termine le tour**, donc il casse la chaîne. Le rapport unique de fin de cycle
est celui produit après `/tech-writer`.

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

> **⛓️ Chaînage** — les étapes `/develop` → `/forge-simplify` → `/sonar` →
> `/lint-angular` → `/lint-mobile` → `/verify-visual` → `/review` →
> `/tech-writer` s'appellent **les unes les autres via l'outil `Skill`, sans
> rapport intermédiaire ni retour à l'humain** (règle 13). Une étape qui rend la
> main au milieu de la chaîne est un défaut, pas une politesse.

| Command | Effect |
|---|---|
| `/po` | Write a new US : `todo-*.md` task file only (no .feature). With `--from <doc.md>` : batch-extract US from a markdown document (one-by-one human validation) |
| `/start {task-id}` | Create the working branches in the target repo(s) and **chain into `/develop`** by default. The full cycle then runs autonomously : `/develop` → `/forge-simplify` → `/sonar` → `/lint-angular` → `/lint-mobile` → `/verify-visual` → `/review` → `/tech-writer`. |
| `/start {task-id} no-code` | Create the working branches and **stop**. Task stays in `wip-*` ; the human implements in WindSurf and runs `/review {task-id}` manually when ready. Escape hatch when `/develop` is unsuitable. |
| `/develop {task-id}` | **Autonomous implementation** : write code + tests, build, test, publish DTOs / interop NuGet packages when contracts change, bump consumers, push, hand off to `/forge-simplify`. Frontends covered : `client-blazor`, `client-angular` (code-only), `client-mobile` (full git automation). For mobile screens, calls `/stitch-design` first to get the design reference. See `agents/develop.md`. |
| `/stitch-design {task-id}` | **Design sub-step of `/develop`** (mobile only). Ensures each `client-mobile` screen has a matching design in the Stitch project `client-mobile` (id `10088502293310567548`) — reuse if present, **create** via the Stitch MCP if missing (convention : screen title = component kebab-case name, e.g. `mail-list`). Logs the screenshot + HTML/CSS reference so `/develop` codes the Ionic screen against it. Stitch = design source of truth ; output is a **reference, not code**. Best-effort & non-blocking. Stand-alone form `/stitch-design {screen-name}` for manual design create/refresh. See `agents/stitch-design.md`. |
| `/forge-simplify {task-id}` | Forge wrapper around the built-in `/simplify` : **quality-only** cleanup pass (reuse / simplification / efficiency / altitude — no bug hunting) on the code `/develop` just produced, per repo, re-validate (build + existing tests), commit/push pushable repos, `client-angular` code-only. Best-effort & non-blocking (rollback a repo on regression). **Never** touches `dtos-mss`/`interop-cda` (contract carriers) or excluded repos. Standard step in the autonomous chain, between `/develop` and `/sonar` ; skip clean if nothing to simplify. The standalone built-in `/simplify` stays available for ad-hoc human use. See `agents/forge-simplify.md`. |
| `/sonar {task-id}` | Best-effort SonarQube cleanup on `api-mail` (5 iterations max, accepts remaining issues). Standard step in the autonomous chain. Consigne un tableau de **KPIs qualité (baseline → final + Quality Gate)** dans le `## Sonar log` de la task — restitué par `/review` dans le body de la PR api-mail et dans le rapport de fin de cycle (on monitore toujours la qualité, jamais de fin de cycle silencieuse sur ce plan). See `agents/sonar.md`. |
| `/lint-mobile {task-id}` | Best-effort ESLint cleanup on `client-mobile` (Working dir `Client/Mobile/`). Plain Angular CLI : `ng lint --fix` then manual fixes, build (`npm run build`) + test (`npm test -- --watch=false --browsers=ChromeHeadless`) as the anti-regression net, 5 iterations max, accepts remaining errors. **Full git automation** (GitHub remote) : commits/pushes its fixes, unlike `/lint-angular`. Standard step in the autonomous chain, after `/lint-angular`, skip clean if client-mobile non touché. Hands off to `/verify-visual`. See `agents/lint-mobile.md`. |
| `/verify-visual {task-id}` | **Vérification visuelle** des écrans `client-mobile` touchés, entre `/lint-mobile` et `/review`. Playwright headless (`tools/visual-verify/`) : session factice, API mockée par fixtures (aucun backend, aucune donnée de santé), capture 390×844 par écran, **pairée à la référence Stitch** dans le `## Visual verify log` (recopié par `/review` dans la PR). Captures rangées par task (`e2e/screenshots/{task-id}/`, liens SHA-pinnés) **et copiées dans `Docs/epics/img/screens/client-mobile/{écran}.png`** (sous-répertoire par app) — l'**état visuel global de l'application**, intégré par `/tech-writer` dans la galerie « État visuel » du doc produit de l'EPIC. Bloquant **uniquement** sur écran blanc/crash de navigation (`questions/` + halt) ; écarts design/outillage = best-effort. Skip clean si aucun écran touché. Forme stand-alone `/verify-visual {screen-name}`. See `agents/verify-visual.md`. |
| `/lint-angular {task-id}` | Best-effort ESLint cleanup on `client-angular` (Working dir `Client/Angular/front/`). Reproduit la forme des commandes lint/build/test du pipeline Azure `Client/Angular/azure-pipelines.yml` (Stage 2 CI), avec deux divergences intentionnelles : (1) default `$BASE_BRANCH = origin/next` (branche d'intégration vivante du repo TFS, pas l'`origin/master` du pipeline) ; (2) lint scopé via `--projects=tag:scope:mss` (le forge ne fixe que le module MSS — `mss` + `mss-lib`). Build/test restent en scope complet pour détecter les régressions downstream. Auto-fix puis fix manuels 5 itérations max, accepte les errors restantes. Code-only — ne touche jamais à git. Standard step in the autonomous chain, skip clean si client-angular non touché. See `agents/lint-angular.md`. |
| `/sonar-s3776 api-mail` | **[Manual]** Reduce cognitive complexity of ONE method (S3776). One method = one PR. Characterisation tests written first. Out of the autonomous chain. See `.claude/commands/sonar-s3776.md`. |
| `/review {task-id}` | Validate the implementation (build + tests + DOD + code review), commit/push/sync develop, open the PR (label `awaiting-human-merge`), rename `done-*`, chain into `/tech-writer`. Autonomous — no human prompt. |
| `/merge {task-id} --i-tested` | **[Human only]** After the human has tested the US end-to-end on the open PRs, squash-merge each pushable PR, sync `develop`, delete the branches, move the task into `tasks/archived/archived-{task-id}.md`. Refuses without `--i-tested`, on `awaiting-us-completion` label, or red CI. Never invoked by `/forge` — HAG (rule 10) stays. See `agents/merge.md`. |
| `/tech-writer E{NNN}` | Refresh `docs/epics/E{NNN}-{slug}.md` from all tasks that declare `**Epic**: E{NNN}` — y compris la galerie **« État visuel de l'application »** (copies d'écran de `Docs/epics/img/screens/{app}/` appartenant à l'EPIC, embeds relatifs, libellés produit). Called automatically at the tail of `/review` ; can be run manually for retro-generation or `--refresh`. See `agents/technical-writer.md`. |
| `/forge` | Loop autonome : pour chaque `tasks/todo-task-*.md`, déclenche `/start` → `/develop` → `/forge-simplify` → `/sonar` → `/lint-angular` → `/lint-mobile` → `/verify-visual` → `/review` → `/tech-writer`. Séquentiel (pas de parallélisme). Stop sur la première task qui échoue (écrit `questions/`, passe à la suivante). Agrège chaque task validée sur une **branche staging par run** `forge/staging-task-{début}-{fin}-{date}` (fraîche depuis `develop`, par repo pushable, best-effort) pour test du lot complet — voir « Branche staging par run `/forge` ». **Ne déclenche jamais `/merge`**, n'ouvre **aucune** PR staging → develop — HAG, règle 10. |
| `/status` | Quick status in < 10 lines |
| `/publish-dtos` | Publish the DTO NuGet package and bump consumers (manual command — `/develop` does the equivalent inline as part of the autonomous cycle). |
| `/kickoff` | Bootstrap a new project (scaffold `.claude/`, agents, templates) |
