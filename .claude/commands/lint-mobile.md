# /lint-mobile — Automated ESLint cleanup on client-mobile

Usage :
- `/lint-mobile {task-id}` — **Mode A (chained)**. Called by `/lint-angular`
  (or upstream by `/sonar` / `/develop` when neither
  api-mail nor client-angular was touched) inside the autonomous cycle.
  Operates on the feature branch `feat/{task-id}-{slug}` checked out in
  `Client/Mobile/`, best-effort 5 iterations, commits/pushes the fixes,
  hands off to `/review`.
- `/lint-mobile` (no argument) — **Mode B (stand-alone)**. Manual
  housekeeping on the current `Client/Mobile/` branch. No task file, no
  hand-off — prints the final report and exits (no commit unless asked).

Purpose : the `client-mobile` counterpart of `/lint-angular` — the mobile
messaging client (Ionic 8 + Angular 20 + Capacitor, `Client/Mobile/`, plain
Angular CLI, **not** Nx). After `/develop` writes mobile code, `/lint-mobile`
runs the ESLint auto-fixer then manually cleans the residual errors (capped
at 5 iterations, best-effort). It is the **last cleanup step** before
`/review`.

**Key difference from `/lint-angular`** : `client-mobile` is a **pushable**
repo (GitHub remote, `develop` branch), so `/lint-mobile` is in **full git
automation** — it commits and pushes its fixes on the feature branch. It
never merges on `develop` (HAG, rule 10) and never opens the PR (`/review`'s
job).

The agent uses plain Angular CLI commands (no Nx) :

```bash
cd Client/Mobile
npm run lint           # ng lint — baseline
npm run lint -- --fix  # ESLint auto-fix (iteration 1)
npm run build          # ng build — anti-regression net
npm test -- --watch=false --browsers=ChromeHeadless   # anti-regression net
```

Read `agents/lint-mobile.md` and execute the full playbook :

1. Pre-flight (working dir exists, `node_modules` present, mode detection,
   skip-cleanly check when no mobile work was done, feature-branch sanity)
2. Baseline lint snapshot (errors, warnings, fixable count)
3. Iteration 1 : `npm run lint -- --fix`, then build + test, re-lint to
   measure progress (rollback + halt best-effort on regression)
4. Iterations 2..5 : group errors by rule (top-1, max 30 files / 100 errors
   per iteration), classify pure-refactor vs behavioural (test-first for
   behavioural — CLAUDE.md rule 1), apply fixes, build + test, re-lint
5. Stop when : zero errors, no progression, or 5 iterations done
6. Hand-off :
   - Mode A : append `## Lint mobile log` to `tasks/wip-{task-id}.md`,
     commit + push the fixes (explicit staging, never `git add -A`), invoke
     `/review {task-id}` (autonomous, no human prompt).
   - Mode B : print the final report and exit (no commit unless asked).

Best-effort acceptance : remaining lint errors after 5 iterations are
**not** a chain blocker. They are logged in `## Lint mobile log` and the
cycle proceeds to `/review`.

The human merges the PR (HAG rule 10).

## ⏱️ Instrumentation (obligatoire)

Borne l'étape et mesure chaque commande coûteuse — c'est ce qui rend le coût
du cycle **mesuré** au lieu d'estimé :

```bash
Tools/timing/step.sh start --task {task-id} --step lint-mobile
Tools/timing/measure.sh --task {task-id} --step lint-mobile --repo {repo} \
    --cwd {repo-path} --kind {kind} -- {commande}
Tools/timing/step.sh end --task {task-id} --step lint-mobile --status ok
```

- **Kinds de cette étape** : `lint` (`ng lint --fix`), `build`, `test`
- `step.sh end --iterations N` sur les 5 autorisées.
- `step.sh end` est appelé **aussi** quand l'étape skip proprement
  (`--status skipped --note "{raison}"`) ou fail-fast (`--status failed`) — un
  skip non mesuré est un trou dans le journal, pas une mesure à zéro.
- `measure.sh` est **transparent** : sortie et code retour inchangés, la
  commande est exécutée telle quelle (donc sûr autour du scanner Sonar et de
  `npm test -- --watch=false`). Une panne du harnais ne casse jamais l'étape.
- Protocole complet et vocabulaire des kinds : `Tools/timing/README.md`.

---
## Rules

- Scope : `client-mobile` only (working directory `Client/Mobile/`). Never
  touches other repos.
- **Full git automation** (GitHub remote) : commits + pushes the lint fixes
  on the feature branch. Never merges on `develop`, never opens the PR.
- Test-first on behavioural fixes (CLAUDE.md rule 1) — adjacent `.spec.ts`
  (Jasmine/Karma).
- Build + tests MUST pass after every iteration. If a fix breaks them,
  patch-based rollback then halt best-effort (the chain still proceeds to
  `/review` with the prior green state).
- Best-effort : 5 iterations max, residual errors accepted.
- Skip cleanly when the task didn't touch `client-mobile`.
- On any unexpected state (tooling crash, repo missing, working tree in an
  unrecognisable state), stop and write `questions/{task-id}.md` (Mode A) or
  print the error (Mode B). Do NOT hand off to `/review` on tooling failure.

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

`Skill(verify-visual, "{task-id}")` — c'est-à-dire
`/verify-visual {task-id}`.

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
