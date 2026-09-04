# questions/merge-task-289.md — `/merge` refusé

Invoqué le 2026-09-04 : `/merge 289 --i-tested`. **Aucune PR n'a été mergée,
aucune branche supprimée, aucun fichier déplacé.** Le refus intervient avant
toute action, comme le prévoit la section « Safety » du playbook.

## Motif : il n'y a rien à merger

| Contrôle | Attendu | Constaté |
|---|---|---|
| Attestation `--i-tested` | présente | ✅ présente |
| Task file | `tasks/done-task-289.md` | ❌ `tasks/wip-task-289.md` |
| Section `## PRs` du task file | présente | ❌ absente |
| PR sur `api-mail` | ouverte, label `awaiting-human-merge` | ❌ **aucune PR, jamais ouverte** (`gh pr list --state all` : vide) |
| `questions/{task-id}.md` bloquant | absent | ❌ `questions/task-289.md` ouvert |

C'est le cas nommé par le playbook lui-même dans « When NOT to use `/merge` » :
*« If the task is still in `wip-*` or `review-*`. Run `/review` first. »*

## Pourquoi la PR n'existe pas

`/review` a tourné et a rendu **CHANGES REQUESTED**. Conformément à son
playbook (« the forge does NOT fix code … writes `questions/{task-id}.md` and
stops »), il a arrêté la chaîne **avant** l'ouverture de la PR. Le travail est
sur la branche poussée `fix/task-289-flag-absent-isole-du-snapshot`
(`api-mail`, 4 commits, `be1ba41`), build vert, 4023 tests verts, Quality Gate
SonarQube OK — mais trois défauts bloquants restent, dont deux établis **par
mutation du code** :

1. `FeatureFlagsConventionTests.cs:41` reste vert avec `FailClosedAtColdStart`
   vidée, c'est-à-dire quand le log de panne cesse de nommer `ai_pipeline` ;
2. `FlagsmithMissingFlagIsolationTests.cs:147` reste vert **avec le correctif
   annulé** ;
3. `FeatureFlagWarmUpService.cs:56` journalise « Startup flag state loaded »
   alors que rien n'a été chargé quand Flagsmith est injoignable.

Détail et correctifs : `questions/task-289.md`.

## Note sur l'attestation

`--i-tested` atteste que le `## Manual Test Plan` a été joué. Ici il ne peut pas
l'avoir été **par le chemin prévu** : aucune PR n'a été ouverte, donc rien n'a
été proposé au test dans les conditions du HAG. Ce n'est pas un reproche — c'est
la raison pour laquelle le garde-fou existe : il empêche qu'une attestation
porte sur un artefact inexistant.

## Reprise

```
/develop 289      # applique les 3 correctifs + le test manquant
```

La chaîne reprend ensuite son cours (`/sonar` → … → `/review`), et c'est
`/review` qui ouvrira la PR avec le label `awaiting-human-merge`. `/merge`
redeviendra alors applicable. Les sections `## Sonar log` et `## Develop log`
du task file sont à jour et n'ont pas à être refaites.
