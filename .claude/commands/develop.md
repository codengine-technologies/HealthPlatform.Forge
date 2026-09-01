# /develop — Autonomous implementation of a task

Usage : `/develop {task-id}` (e.g. `/develop task-018`)

Purpose : write the code, the tests, build, run the suite, run the **integrated
quality pass** (built-in `/simplify`) on the fresh code, commit, push, and hand
off to the cleanup chain (`/sonar` → `/lint-angular` → `/lint-mobile` →
`/verify-visual` → `/review`). This is the **default implementation path** of
the forge — the only escape hatch is `/start {task-id} no-code`, which leaves
the task in `wip-*` for the human to implement in WindSurf.

> **Fusion (2026-08-31)** — l'ancienne étape `/forge-simplify` est **absorbée
> par `/develop`**. Elle refaisait tout ce que `/develop` venait de faire
> (pré-flight, détection du diff, **build + tests complets par repo**, commit,
> push) pour appliquer une passe cosmétique. C'est désormais la **sous-étape
> « passe qualité » (§Q de `agents/develop.md`)**, exécutée par repo juste
> après le vert de la feature et **avant le push** : un seul cycle build+test
> par repo au lieu de deux, un seul tour d'agent au lieu de deux. Le built-in
> `/simplify` reste dispo pour l'usage ad-hoc humain.

Read `agents/develop.md` and execute the full playbook :

1. Pre-flight (task in `wip-*`, branches exist on every listed repo, working
   trees clean)
2. Compute the cross-repo build order : `dtos-mss` → `interop-cda` →
   backends → frontends
3. For shared-contract repos (`dtos-mss`, `interop-cda`) : code, build,
   commit, push, `gh run watch` until the GitHub Actions CI publishes the
   NuGet package, bump consumers' `Directory.Packages.props`, commit the
   bump in each consumer (push later)
4. For backends and frontends : test-first for behavioural changes, build +
   test green before each commit, conventional messages
5. **Passe qualité intégrée (§Q)** par repo éligible, une seule fois, **avant
   le push** : built-in `/simplify` sur le diff vs `develop` (reuse /
   simplification / efficacité / altitude — **quality only, jamais de chasse
   aux bugs**), re-validation build+test **seulement si des cleanups ont été
   appliqués**, commit `refactor(module): simplify pass (/simplify) —
   {task-id}` au vert, `git restore` au rouge (best-effort, jamais bloquant).
   **Jamais** sur `dtos-mss` / `interop-cda` (porteurs de contrat) ; jamais
   d'opération git sur `client-angular` (code-only). Puis **un seul push** par
   repo, portant feature + passe qualité
6. Final verification : DOD self-check, et **pas de re-build** d'un repo déjà
   vert depuis sa dernière validation
7. Hand off unconditionally to the fixed cleanup pipeline
   `/sonar → /lint-angular → /lint-mobile → /verify-visual → /review` (each step self-skips
   when its repo wasn't touched) :
   - api-mail touched → `/sonar {task-id}`
   - else client-angular touched → `/lint-angular {task-id}`
   - else client-mobile touched → `/lint-mobile {task-id}`
   - none touched → `/review {task-id}` directly

`/develop` writes code by design — this is the post-lean philosophy. The
human's only mandatory interaction is **merging the PR on `develop`** at
the end of the chain (HAG, CLAUDE.md rule 10).

## ⏱️ Instrumentation (obligatoire)

Borne l'étape et mesure chaque commande coûteuse — c'est ce qui rend le coût
du cycle **mesuré** au lieu d'estimé :

```bash
Tools/timing/step.sh start --task {task-id} --step develop
Tools/timing/measure.sh --task {task-id} --step develop --repo {repo} \
    --cwd {repo-path} --kind {kind} -- {commande}
Tools/timing/step.sh end --task {task-id} --step develop --status ok
```

- **Kinds de cette étape** : `restore` (`dotnet restore`, `npm ci`), `build`, `test`, `nuget-wait` (`gh run watch` sur la CI DTO/interop)
- Mesurer le `gh run watch` a un intérêt propre : c'est du **temps mort série** au milieu de l'implémentation, et le premier candidat au feed NuGet local.
- La passe qualité §Q se mesure avec le même `--step develop` : ses build/test de re-validation apparaissent dans le compte du repo concerné.
- `step.sh end` est appelé **aussi** quand l'étape skip proprement
  (`--status skipped --note "{raison}"`) ou fail-fast (`--status failed`) — un
  skip non mesuré est un trou dans le journal, pas une mesure à zéro.
- `measure.sh` est **transparent** : sortie et code retour inchangés, la
  commande est exécutée telle quelle (donc sûr autour du scanner Sonar et de
  `npm test -- --watch=false`). Une panne du harnais ne casse jamais l'étape.
- Protocole complet et vocabulaire des kinds : `Tools/timing/README.md`.

---
## Rules

- 5 iterations cap on the same RED test or broken build → fail-fast into
  `questions/{task-id}.md`
- Cross-repo order is mandatory : DTOs and interop must be published to
  NuGet before consumers can compile against the new contract
- Never `git add -A` / `git add .` — explicit staging only
- Excluded repos (`client-angular`, `devops`, `psc-proxy-*`) are never
  touched ; logged as "managed manually by the human"
- HAG is preserved : `/develop` never merges on `develop`
- On any unexpected state, stop and write `questions/{task-id}.md`

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

L'étape suivante dépend des repos touchés :

| api-mail | client-angular | client-mobile | Invoquer |
|---|---|---|---|
| oui | * | * | `Skill(sonar, "{task-id}")` |
| non | oui | * | `Skill(lint-angular, "{task-id}")` |
| non | non | oui | `Skill(lint-mobile, "{task-id}")` |
| non | non | non | `Skill(review, "{task-id}")` |

La passe qualité **n'est plus un maillon de la chaîne** : elle est déjà faite,
dans cette étape, repo par repo. Il n'y a rien à invoquer pour elle.

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
