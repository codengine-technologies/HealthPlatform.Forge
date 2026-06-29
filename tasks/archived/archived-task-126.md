# todo-task-126.md — Refonte Stitch composant `biology-ack-badge` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le badge d'état d'acquittement biologie
`biology-ack-badge` (`src/app/features/mail/components/biology-ack-badge/*`) pour
une fidélité parfaite à sa **référence Stitch** `biology-ack-badge`, sur la base
du socle `done-task-110`.

Badge indiquant l'état d'acquittement d'un résultat de biologie (acquitté /
en attente / patient contacté…). Travail **soigné**. `client-mobile` uniquement —
aucun changement fonctionnel.

## Référence Stitch
- **Réutiliser** l'écran Stitch `biology-ack-badge` (correspondance exacte).
- Étape design : `/stitch-design task-126`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (badge, variantes d'état, couleurs sémantiques
      issues du socle)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés
- [ ] Aucune régression (états affichés)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir des messages de biologie à différents états d'ack.
- Vérifier le rendu du badge pour chaque état au nouveau design (couleurs
  sémantiques cohérentes).
- Comparer à la maquette Stitch `biology-ack-badge`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : biologie médicale — restyling UI. **Vague** : hors Ségur (UX).
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable — restyling sans
  logique métier.

## Branches
- `client-mobile` (pushed) : feat/task-126-stitch-biology-ack-badge — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-126-stitch-biology-ack-badge

## Stitch design log
- Écran Stitch `biology-ack-badge` (id c8cfb02efffd48a09f8bee1096804c7a) **réutilisé**.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLulePc1MnLNR4RK_0tz7xPwoJ5MftKt6EuykC2CJPnIuoVAL96o5Dz6_3lKaLFhan4VcJlDVl63RlTc2ctztLBeiQX8xhl2BUBc7UzGW6mpB-oeVN__nejoByb8QUCW2paLUtuBxmvrwZvU_62fs_9EMG9sJeItwzZX1RQXnmzBh79K18pfIauTPQ_iBUTfA0UJsJaAbtmThV28Nm-_U7_HTHXWkNISUadBToKsFr-MRcLIUmzVuhaGQqIc
- Refonte : couleurs sémantiques du socle (critique → `danger`, en attente →
  `tertiary` #920d00, au lieu de `warning` amber hors-socle) ; typo/espacements
  token-driven (label-md, --app-space-xs). Logique de visibilité/compteur/critique inchangée.

## Develop log
- Repos touchés : `client-mobile` (poussé). Commit `7652da2`.
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓**.
- Next step : /forge-simplify task-126.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle inline (couleurs sémantiques + tokens), rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-126.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-126.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/29 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Couleurs sémantiques socle (critique→danger, en attente→tertiary) + tokens typo/espacement ; logique inchangée ; data-testid préservé. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `biology-ack-badge` réutilisé.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `88ce52d` (PR #29 fermée).
- CI develop : aucun workflow CI sur ce repo.
- Remote branch `feat/task-126-stitch-biology-ack-badge` supprimée ; branche locale conservée.
