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
/develop  →  /forge-simplify  →  /sonar  →  /lint-angular  →  /lint-mobile  →  /review  →  /tech-writer
```

`/sonar`, `/lint-angular` and `/lint-mobile` deliberately run after it so they
re-scan / re-validate whatever the simplify pass touched.

Read `agents/forge-simplify.md` and execute the full playbook :

1. Pre-flight (task in `wip-*`, pushable repos on their feature branch, clean)
2. Determine the touched, eligible repos (diff vs `develop`)
3. Run the built-in `/simplify` per touched repo (skip `dtos-mss`,
   `interop-cda`, and excluded repos)
4. Re-validate (build + existing tests) ; commit + push pushable repos on
   GREEN, roll back on RED (quality pass must not change behaviour),
   leave `client-angular` uncommitted
5. Append `## Simplify log` ; route to the first touched step in the fixed
   pipeline `/sonar` (api-mail) → `/lint-angular` (client-angular) →
   `/lint-mobile` (client-mobile) → `/review` (each self-skips when untouched)

## Rules

- **Quality only.** Bug/security hunting is `/code-review`, not this step.
- **Best-effort, non-blocking.** A repo that fails validation is rolled back
  and skipped ; the chain proceeds. Only tooling failures halt
  (`questions/{task-id}.md`).
- **Scope** : `api-mail`, `client-blazor`, `client-mobile`, `sdk`, `host`
  (commit + push) ; `client-angular` (code-only, never git). NEVER `dtos-mss`
  / `interop-cda` (contract carriers) or `devops` / `psc-proxy-*` (excluded).
- **Reuse before create** — the reuse axis enforces the workspace rule.
- Explicit staging only, conventional `refactor(module):` commits, no rebase.
- HAG (rule 10) : never merges on `develop`.

The standalone built-in `/simplify` stays available for ad-hoc human use
(simplify the current diff, no forge ceremony). `/forge-simplify` is the
chained, task-scoped version.

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

L'étape suivante dépend des repos touchés (table de routage ci-dessus) :

| api-mail | client-angular | client-mobile | Invoquer |
|---|---|---|---|
| oui | * | * | `Skill(sonar, "{task-id}")` |
| non | oui | * | `Skill(lint-angular, "{task-id}")` |
| non | non | oui | `Skill(lint-mobile, "{task-id}")` |
| non | non | non | `Skill(review, "{task-id}")` |

**Tu appelles l'outil `Skill` maintenant.** Tu ne dis pas « je vais enchaîner »,
tu ne résumes pas ce que tu viens de faire : le `## Simplify log` du task file
porte déjà la trace, et le rapport unique de fin de cycle est celui de `/review`.

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
