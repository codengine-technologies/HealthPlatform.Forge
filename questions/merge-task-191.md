# merge-task-191 — CI `develop` rouge après le merge : échec du push Docker (502 du registre)

**Date** : 2026-09-30
**Repo** : `api-mail`
**Merge** : PR #261 squash-mergée → `2d5109936b584ea4f0eec13ddc1d555035a6b42a` (déjà sur `develop`, task archivée)
**Run** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/36747271257

## Constat

- Job `build` : **succès** (compilation et tests).
- Job `publish`, étape « Push Docker image » (`docker push ***/healthplatform-api-mail:develop`) :
  **échec**. Plusieurs couches ont été poussées (`Pushed`), puis le registre a répondu
  `received unexpected HTTP status: 502 Bad Gateway` → exit code 1.
- Les 8 runs précédents sur `develop` (2026-09-15 → 2026-09-19) ont tous réussi leur `publish`.

## Lecture

Une **panne passagère du registre d'images**, pas une régression du code : le 502 vient du
serveur, après le début de l'envoi. Conséquence : l'image `healthplatform-api-mail:develop` du
registre **ne contient pas encore** task-191, et elle a peut-être été laissée partielle.

## Action attendue (humain)

Relancer le job en échec, puis vérifier qu'il passe :

```bash
cd Api/Mail
gh run rerun 36747271257 --failed
gh run watch 36747271257 --exit-status
```

Si le 502 persiste : état du registre à vérifier (disponibilité, quota, limite de taille).
