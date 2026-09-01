# /lint-angular — Automated ESLint cleanup on client-angular

Usage :
- `/lint-angular {task-id}` — **Mode A (chained)**. Called by `/sonar` (or by
  `/develop` when `api-mail` wasn't touched) inside the autonomous cycle.
  Operates on the working tree of `Client/Angular/front/`, scope
  `npx nx affected -t lint --base=$BASE_BRANCH --head=HEAD --parallel=3`
  (matches the Azure pipeline), best-effort 5 iterations, hands off to
  `/review`.
- `/lint-angular` (no argument) — **Mode B (stand-alone)**. Manual
  housekeeping. Scope `npx nx run-many -t lint --parallel=3` (full
  workspace, broader than the pipeline), no task file, no hand-off —
  prints the final report and exits.

Purpose : the Angular counterpart of `/sonar`. After `/develop` writes
Angular code in `Client/Angular/front/`, `/lint-angular` runs the ESLint
auto-fixer then manually cleans up the residual errors (capped at 5
iterations, best-effort). The forge then hands off to `/review` which
validates everything and rebuilds.

The agent **reproduces** the lint / build / test commands of the
Angular Azure pipeline (`Client/Angular/azure-pipelines.yml`,
Stage 2 "CI - Lint & Test"), with two intentional divergences (default
base branch + lint scope filter — see below) :

```bash
cd Client/Angular/front
# Lint — scoped to the MSS module
npx nx affected -t lint  --base=$BASE_BRANCH --head=HEAD --parallel=3 \
  --projects=$LINT_PROJECTS
# Build + test — full affected scope (catch downstream regressions)
npx nx affected -t build --base=$BASE_BRANCH --head=HEAD --parallel=3
npx nx affected -t test  --base=$BASE_BRANCH --head=HEAD --parallel=3 \
  --skipNxCache -- --coverage --reporter=junit \
  --outputFile=vitest-report.xml
```

**Defaults & divergences vs the pipeline** :

- `$BASE_BRANCH` = **`origin/next`** (active TFS integration branch),
  NOT the pipeline's `origin/master` fallback (which only fires on
  release pushes). Overridable per-task via `**LintBase**: origin/master`.
- `$LINT_PROJECTS` = **`tag:scope:mss`** (Nx projects `mss` + `mss-lib`).
  The pipeline lints every affected project ; the forge restricts lint
  fixes to the MSS module so it never touches lint debt outside its
  charter. **Only the lint commands carry this scope** — build / test
  stay un-scoped to detect regressions in `weda2` and other downstream
  consumers of `mss-lib`. Overridable per-task via `**LintProjects**:
  tag:scope:mss,tag:scope:shared` (or similar).
- The agent layers `--fix` (auto-fix) and 5 iterations of manual fixes
  on top of these commands ; the pipeline itself runs a single
  gate-style pass.

Like every other forge step on `client-angular`, `/lint-angular` operates
in **code-only mode** : it modifies files in the working tree, runs the
pipeline-aligned commands above to validate, but **never** touches git
(the only tolerated git read op is the Step-0 `git fetch origin
{base}` so Nx affected has a reliable comparison ref). The human owns
commit/push to TFS and PR opening.

Read `agents/lint-angular.md` and execute the full playbook :

1. Pre-flight (working directory exists, `node_modules` present, mode
   detection, skip-cleanly check when no Angular work was done)
2. Baseline lint snapshot (errors, warnings, fixable count)
3. Iteration 1 : ESLint auto-fix via the pipeline-aligned command with
   `--fix` appended (`npx nx affected -t lint --base=$BASE_BRANCH
   --head=HEAD --parallel=3 -- --fix` in Mode A, or `npx nx run-many
   -t lint --parallel=3 -- --fix` in Mode B), then build + test (also
   pipeline-aligned), re-lint to measure progress
4. Iterations 2..5 : group errors by rule (top-1, max 30 files / 100 errors
   per iteration), classify pure-refactor vs behavioural (test-first
   for behavioural — CLAUDE.md rule 1), apply fixes, build + test, re-lint,
   evaluate progression
5. Stop when : zero errors, no progression, or 5 iterations done
6. Hand-off :
   - Mode A : append `## Lint log` to `tasks/wip-{task-id}.md`, invoke
     `/lint-mobile {task-id}` (autonomous, no human prompt — it self-skips
     to `/review` when `client-mobile` wasn't touched).
   - Mode B : print the final report and exit.

Best-effort acceptance : remaining lint errors after 5 iterations are
**not** a chain blocker. They are logged in `## Lint log` and the cycle
proceeds to `/lint-mobile` (which self-skips to `/review`).

The human merges the PR (HAG rule 10) ; for `client-angular` specifically
the human also owns commit/push/PR-opening on TFS.

## ⏱️ Instrumentation (obligatoire)

Borne l'étape et mesure chaque commande coûteuse — c'est ce qui rend le coût
du cycle **mesuré** au lieu d'estimé :

```bash
Tools/timing/step.sh start --task {task-id} --step lint-angular
Tools/timing/measure.sh --task {task-id} --step lint-angular --repo {repo} \
    --cwd {repo-path} --kind {kind} -- {commande}
Tools/timing/step.sh end --task {task-id} --step lint-angular --status ok
```

- **Kinds de cette étape** : `lint` (`nx affected -t lint`), `build`, `test`
- `step.sh end --iterations N` — le nombre d'itérations réellement consommées sur les 5 autorisées.
- `step.sh end` est appelé **aussi** quand l'étape skip proprement
  (`--status skipped --note "{raison}"`) ou fail-fast (`--status failed`) — un
  skip non mesuré est un trou dans le journal, pas une mesure à zéro.
- `measure.sh` est **transparent** : sortie et code retour inchangés, la
  commande est exécutée telle quelle (donc sûr autour du scanner Sonar et de
  `npm test -- --watch=false`). Une panne du harnais ne casse jamais l'étape.
- Protocole complet et vocabulaire des kinds : `Tools/timing/README.md`.

---
## Rules

- Scope : `client-angular` only (working directory
  `Client/Angular/front/`). Never touches other repos.
- **Pipeline fidelity** : lint / build / test commands match the
  Angular Azure pipeline (`Client/Angular/azure-pipelines.yml`)
  byte-for-byte (modulo the `--fix` flag in iter 1 and the JSON
  formatter `--` passthrough used for parsing).
- **Base branch** : default `origin/next` (active TFS integration
  branch). Diverges intentionally from the pipeline's `origin/master`
  fallback. Overridable per-task via `**LintBase**:` in the task file.
- **Module scope (lint only)** : default `tag:scope:mss` (Nx projects
  `mss` + `mss-lib`). The forge is dedicated to the MSS module — lint
  auto-fixes never touch projects outside this scope. Build / test
  stay on the full affected scope. Overridable per-task via
  `**LintProjects**:` in the task file.
- **Code-only mode** : never `git add`, `git commit`, `git push`, or any
  other git mutation on `client-angular`. The only tolerated git read
  op is `git fetch origin {base}` to refresh the comparison ref
  (matches the pipeline's own pre-lint fetch).
- Test-first on behavioural fixes (CLAUDE.md rule 1) — adjacent
  `.spec.ts` (Vitest).
- Build + tests MUST pass after every iteration. If a fix breaks them,
  patch-based rollback then halt (Mode A → `questions/{task-id}.md`,
  Mode B → surface to human).
- Best-effort : 5 iterations max, residual errors accepted.
- On any unexpected state (tooling crash, repo missing, working tree in
  an unrecognisable state), stop and write
  `questions/{task-id}.md` (Mode A) or print the error (Mode B).

---

## ⛓️ Chaînage — NE PAS INTERROMPRE

> Cette section est **opérationnelle**, pas descriptive. Elle a été ajoutée le
> 2026-08-04 parce que la chaîne s'arrêtait en pratique à chaque étape : les
> fichiers disaient « hand off to … » sans jamais ordonner d'appeler l'étape
> suivante, donc l'agent rédigeait un rapport et rendait la main. L'humain devait
> relancer « continue la chaîne » à chaque maillon — ce qui vide de son sens la
> boucle autonome.

**À la fin de cette étape, tu invoques immédiatement l'étape suivante via l'outil
`Skill`, dans le MÊME tour, sans rien demander et sans rapport intermédiaire.**

`Skill(lint-mobile, "{task-id}")` — c'est-à-dire
`/lint-mobile {task-id}`.

**Tu appelles l'outil `Skill` maintenant**, sans rapport intermédiaire. Le rapport
unique de fin de cycle est celui de `/review`.

### Les DEUX seuls arrêts légitimes

1. **Fail-fast** — un vrai blocage technique : `questions/{task-id}.md` est écrit,
   et tu t'arrêtes en le disant. Un plafond d'itérations atteint, un build
   irréparable, une ambiguïté métier. **Le budget de contexte conversationnel
   n'en est pas un.**
2. **Décision humaine explicitement requise** par le task file — un encadré
   « arbitrage humain requis » sur un point précis. Tu traites tout le reste,
   puis tu poses la question sur ce seul point.

### Ce qui n'est PAS un motif d'arrêt

- une étape qui **skippe** (repo non touché) : elle enchaîne quand même ;
- une étape **best-effort** dont il reste des findings : c'est son
  fonctionnement normal ;
- un flaky pré-existant identifié comme tel ;
- la longueur du travail déjà accompli dans le tour ;
- l'envie de faire valider une étape intermédiaire — **HAG (règle 10) est la
  seule barrière humaine, et elle est au merge de la PR, pas avant.**
