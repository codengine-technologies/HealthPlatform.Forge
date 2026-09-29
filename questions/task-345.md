# task-345 — /review CHANGES REQUESTED (2026-09-29, 2e passage)

Validation : build + tests verts (api-mail 5 849/5 849, mobile 947/947). Le blocage
précédent (démontage de `run.mjs`) est **levé**. Un bloquant reste :

## Bloquant — lu/non-lu et flag vérifiés sur l'état OPTIMISTE seulement

`E2E-MAIL-001`, `E2E-MAIL-002`, `E2E-MAIL-003` (`Client/Mobile/e2e/specs/functional.spec.ts`)
lisent la classe CSS de la ligne sans recharger. Or `MailActionsService.toggleRead`,
`markRead`, `toggleFlag` (et les variantes bulk) modifient la ligne AVANT l'appel API et
ne reviennent en arrière que sur erreur. Un `updateReadStatus` / `updateFlagStatus` qui
rend `of(true)` sans appeler le serveur laisse les trois parcours verts — la même
catégorie que BIO-001, déjà durci pour cette raison. Les 7 mutations de preuve ne
couvraient ni la lecture ni le flag.

Correctif attendu : attendre la réponse de l'appel, recharger l'inbox, re-vérifier l'état ;
prouver par une mutation no-op sur `updateReadStatus`/`updateUnreadStatus` et
`updateFlagStatus`/`updateUnflagStatus`.

## Suggestions (non bloquantes)

- `run.mjs` : l'instantané des conteneurs ignore le code retour de `docker ps -a` — une
  erreur Docker transitoire donnerait un instantané vide, donc un démontage trop large
  (doit échouer fermé).
- `run.mjs` : `suiteEnv` n'épingle pas `MOBILE_BASE_URL` sur l'app servie.
- `E2E-DASH-001` : en headless, un widget bloqué en chargement compte comme rendu.
- Signaux pendant les `spawnSync` longs (non traité : le démontage a lieu à la sortie de l'enfant).
