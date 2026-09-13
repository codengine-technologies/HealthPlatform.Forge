# questions/merge-task-303.md — `/merge 303 --i-tested` refusé

**Date** : 2026-09-13
**Commande** : `/merge 303 --i-tested`
**Verdict** : **abort** — deux gates de sécurité en échec, aucune PR mergée.

## Gate 1 — label `awaiting-us-completion` (règle 11)

Les deux PRs de task-303 portent `awaiting-us-completion`, posé délibérément par
`/review` :

| Repo | PR | Label |
|---|---|---|
| `api-mail` | #236 | `awaiting-us-completion` |
| `dtos-mss` | #32 | `awaiting-us-completion` |

task-303 est la **vague 1/2** d'une US unique ; la vague 2 est **task-304**
(`tasks/todo-task-304.md`, non démarrée). La règle 11 exige que le test humain
porte sur la US **assemblée** et que les vagues intermédiaires attendent.
Merger 303 seul poserait sur `develop` un backend de sélection de boîte
qu'aucun front n'expose — la « fausse v1 » que la règle interdit.

`/merge` refuse explicitement sur ce label (gate 2 de sa spec).

## Gate 2 — PR api-mail #236 en conflit avec `develop`

`mergeable = CONFLICTING`. Indépendamment de la règle 11, cette PR ne peut pas
être squash-mergée en l'état. Résolution attendue par `git merge origin/develop`
sur la branche de feature (règle 4 — jamais de rebase).

## Ce qui n'a PAS été fait

Aucun `gh pr merge`, aucune suppression de branche, aucun `develop` touché,
`tasks/done-task-303.md` inchangé.

## Chemins possibles

1. **Nominal (recommandé)** : `/start 304` → chaîne autonome → PRs de 304
   ouvertes → test humain de la US assemblée → `/merge 303` puis `/merge 304`.
   Le conflit de #236 se résoudra au passage (`/review` de 304 ne touche pas
   api-mail ; la résolution reste à faire à la main sur la branche 303).
2. **Dérogation explicite** : si tu décides que 303 doit merger seul, c'est une
   dérogation à la règle 11 qui t'appartient — retire le label
   `awaiting-us-completion`, résous le conflit de #236, puis merge à la main via
   `gh pr merge --squash`. `/merge` ne portera pas cette décision.
