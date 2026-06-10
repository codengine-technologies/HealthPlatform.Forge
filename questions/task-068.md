# questions/task-068.md — /develop bloqué au pre-flight (Step 0.3 : wip multiples)

**Date** : 2026-06-10
**Étape en échec** : `/develop task-068` — Step 0 (pre-flight), point 3 « workspace clean : une seule task wip ».

## Blocker

Deux tasks `wip-*` coexistent :

- `tasks/wip-task-067-test-coverage-raise.md` — campagne de couverture de tests sur **api-mail** (Epic E009, chore, condition d'arrêt ≥ 95 % ou 5 itérations)
- `tasks/wip-task-068-imap-fetch-cible-streaming-pj.md` — la task courante (Epic E011, perf IMAP, **api-mail** aussi)

Le playbook `agents/develop.md` (Step 0.3) impose l'abort : « If multiple
`wip-*` files coexist, abort : the autonomous loop serialises tasks, parallel
`wip-*` is a sign something is off. » Les deux tasks ciblent le même repo
`api-mail` — risque réel de collision (la campagne de coverage ajoute des tests
sur les classes que task-068 va réécrire : `ImapService`, `BackgroundImapService`).

## État des repos (aucun code écrit, aucun commit)

- `api-mail` : sur `feat/task-068-imap-fetch-cible-streaming-pj` (créée et pushée par `/start`, 0 commit, working tree propre)
- `dtos-mss` : sur `feat/task-068-imap-fetch-cible-streaming-pj` (créée et pushée par `/start`, 0 commit, working tree propre)
- task-067 : aucune branche `chore/task-067-*` détectée sur `api-mail` (la campagne ne semble pas démarrée, ou a été menée hors branche)

## Décision attendue de l'humain

Choisir l'une des options :

1. **Suspendre task-067** : renommer `wip-task-067-*.md` en `todo-task-067-*.md`
   (elle redeviendra éligible plus tard), puis relancer `/develop task-068`.
2. **Terminer/archiver task-067 d'abord** : si la campagne est en réalité
   terminée ou abandonnée, la passer en `review-*`/`archived-*` selon son état
   réel, puis relancer `/develop task-068`.
3. **Forcer la poursuite** : confirmer explicitement que les deux wip peuvent
   coexister (dérogation ponctuelle à la règle) — la forge reprendra
   `/develop task-068` sur instruction.

La task-068 reste en `wip-*`, branches en place, prête à reprendre dès la
décision.

## Réponse de l'humain (2026-06-10)

**Option 3 retenue** — dérogation ponctuelle explicite : les deux tasks
`wip-*` (067 coverage, 068 perf IMAP) coexistent. `/develop task-068`
reprend. La règle « une seule wip » reste la norme pour les prochains cycles.
