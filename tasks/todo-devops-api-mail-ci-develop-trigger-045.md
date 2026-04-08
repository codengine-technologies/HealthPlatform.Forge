# todo-devops-api-mail-ci-develop-trigger-045 — Api/Mail : déclencher la CI sur les PRs vers develop

**Dependencies**: aucune sur le contenu, mais **NE PAS DISPATCHER tant que `wip-back-notifications-realtime-040` est en cours** (conflit de branche dans le même repo, pas de worktree isolé pour 040).
**Repo**: api-mail (path: `Api/Mail`)
**Module**: DevOps / CI

## Contexte

Le workflow `.github/workflows/dotnet.yml` du repo `api-mail` ne se déclenche que sur les PRs vers `master`. Toutes les PRs de feature branches vers `develop` ont donc `statusCheckRollup: []` et sont mergées **sans validation CI distante** — seul `verify-before-push.sh` (build+tests locaux) faisait foi.

Le repo `client-blazor` a déjà été corrigé par PR codengine-technologies/HealthPlatform.Client#20. Cette tâche applique le même fix côté `api-mail`.

## Travail à réaliser

Modifier `Api/Mail/.github/workflows/dotnet.yml` :

```yaml
on:
  push:
    branches: [ "master", "develop" ]
  pull_request:
    branches: [ "master", "develop" ]
```

(Remplacer `[ "master" ]` par `[ "master", "develop" ]` dans les deux triggers.)

Brancher : `ci/develop-trigger`. PR vers `develop`. Title : `ci: trigger workflow on develop branch`. Body : référencer le miroir Blazor #20 et expliquer le trou structurel.

## Definition of Done

- [ ] `.github/workflows/dotnet.yml` accepte `develop` dans `push` et `pull_request`
- [ ] PR ouverte vers `develop`
- [ ] Aucune autre modification dans le workflow (pas de refacto, juste la ligne de trigger)
- [ ] Une fois mergée : la prochaine PR vers `develop` doit montrer la CI en train de tourner

## Notes

- **Bloquant : 040 doit avoir merge avant qu'on touche `Api/Mail`**, pour ne pas créer de conflit de branche dans un repo non-worktree.
- Pas besoin de worktree pour cette tâche (modif d'1 ligne, scope ridicule).
- Si l'orchestrator dispatch automatiquement, vérifier d'abord que `tasks/wip-back-notifications-realtime-040.md` n'existe plus.
