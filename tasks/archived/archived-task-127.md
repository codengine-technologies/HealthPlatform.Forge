# todo-task-127.md — Refonte Stitch composant `biology-ack-panel` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le panneau d'acquittement biologie
`biology-ack-panel` (`src/app/features/mail/components/biology-ack-panel/*`) pour
une fidélité parfaite à sa **référence Stitch** `biology-ack-panel`, sur la base
du socle `done-task-110`.

Panneau d'actions d'acquittement d'un résultat de biologie (les actions métier
existantes : acquitter, patient contacté, etc.). Travail **soigné**.
`client-mobile` uniquement — aucun changement des actions/logique.

## Référence Stitch
- **Réutiliser** l'écran Stitch `biology-ack-panel` (correspondance exacte).
- Étape design : `/stitch-design task-127`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (liste d'actions, hiérarchie, boutons primary/
      secondary du socle, touch ≥ 44px)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés sur chaque action
- [ ] Aucune régression (chaque action d'acquittement fonctionne comme avant)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir un résultat de biologie, ouvrir le panneau d'ack.
- Vérifier le rendu (actions, boutons, hiérarchie) au nouveau design.
- Déclencher chaque action → comportement inchangé.
- Comparer à la maquette Stitch `biology-ack-panel`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : biologie médicale (acquittement) — restyling UI sans logique
  métier. **Vague** : hors Ségur (UX).
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable au restyling
  (l'acquittement et sa traçabilité existants sont inchangés).

## Branches
- `client-mobile` (pushed) : feat/task-127-stitch-biology-ack-panel — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-127-stitch-biology-ack-panel

## Stitch design log
- Écran Stitch `biology-ack-panel` (id 617cba580ad548d7a439acb966184e4f) **réutilisé**.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLsVrnb6KdlzrkyBJld4EGFL0TQYW-6nF6TyGeKZydG6oba225FbzRV_rsYP9ChksMsVJPcPww-OpvtGqA0Lni4ZeLNwFF4mgmnauqHBe07nMe1nbAkKeEBYGQLUahGOvWgmUiX5O788wx5wUjmD0NpLMa_5niS1unMVBsxKQlrba3Q4U84cA9JGeXktn9GekuHjWjGA8DvgyFVig8dJsQIHSkWCEFJYqBN5YTGLG0FMgztCQcsftYudOjZy
- Refonte = migration SCSS 100 % token-driven (panneau, header, statut, actions).
  Statut aux couleurs sémantiques du socle : à traiter → tertiary, en cours →
  primary, résolu → secondary (le socle Clinical Precision n'a ni vert ni ambre →
  remplacement de `warning`/`success`). Panneau critique → `--app-error-container`.
  Boutons d'action `size="small"` (touch Ionic), `data-testid` par action préservés.
  Actions/logique d'acquittement (modale de confirmation, persistance) inchangées.

## Develop log
- Repos touchés : `client-mobile` (poussé). Commit `ef19c5e`.
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓**.
- Next step : /forge-simplify task-127.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven, rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-127.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-127.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/30 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle SCSS 100 % token-driven, statut aux couleurs sémantiques socle, logique d'acquittement inchangée, data-testid préservés. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `biology-ack-panel` réutilisé.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `6a90bb2` (PR #30 fermée).
- CI develop : aucun workflow CI sur ce repo.
- Remote branch `feat/task-127-stitch-biology-ack-panel` supprimée ; branche locale conservée.
