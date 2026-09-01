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

## ⏱️ Instrumentation (obligatoire)

Borne l'étape et mesure chaque commande coûteuse — c'est ce qui rend le coût
du cycle **mesuré** au lieu d'estimé :

```bash
Tools/timing/step.sh start --task {task-id} --step sonar
Tools/timing/measure.sh --task {task-id} --step sonar --repo {repo} \
    --cwd {repo-path} --kind {kind} -- {commande}
Tools/timing/step.sh end --task {task-id} --step sonar --status ok
```

- **Kinds de cette étape** : `scan` (`sonarscanner begin`/`end` + attente de traitement serveur), `build`, `test` (ajouter `--label coverage` sur les passes OpenCover)
- Reporter le nombre d'itérations : `step.sh end --iterations N`. C'est la métrique qui dira si Phase 2 mérite de rester dans le chemin critique.
- Envelopper le scanner est sûr : `measure.sh` exécute la commande directement, donc `MSYS_NO_PATHCONV` / `MSYS2_ARG_CONV_EXCL` exportés avant l'appel s'appliquent à l'identique.
- `step.sh end` est appelé **aussi** quand l'étape skip proprement
  (`--status skipped --note "{raison}"`) ou fail-fast (`--status failed`) — un
  skip non mesuré est un trou dans le journal, pas une mesure à zéro.
- `measure.sh` est **transparent** : sortie et code retour inchangés, la
  commande est exécutée telle quelle (donc sûr autour du scanner Sonar et de
  `npm test -- --watch=false`). Une panne du harnais ne casse jamais l'étape.
- Protocole complet et vocabulaire des kinds : `Tools/timing/README.md`.

---
## Rules

- Scope : `api-mail` only. Other repos are out of scope for this command.
- Test-first on every behavioural fix (rule 1).
- Blacklisted rules (`agents/sonar-blacklist.yml`) are NEVER fixed here.
  S3776 uses the dedicated `/sonar-s3776` command.
- Token read from `$SONAR_TOKEN`, never hardcoded.
- On any unexpected state, stop and write `questions/sonar-api-mail-{YYYYMMDD}.md`.

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

`Skill(lint-angular, "{task-id}")` — c'est-à-dire
`/lint-angular {task-id}`.

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
