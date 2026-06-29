# todo-task-128.md — Refonte Stitch composant `biology-ack-confirm-dialog` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le dialog de confirmation d'acquittement biologie
`biology-ack-confirm-dialog`
(`src/app/features/mail/components/biology-ack-confirm-dialog/*`) pour une
fidélité parfaite à sa **référence Stitch** `biology-ack-confirm-dialog`, sur la
base du socle `done-task-110`.

Modale/feuille de confirmation (ex. « Patient contacté ») : titre, message,
champ(s) éventuel(s), boutons confirmer/annuler. Travail **soigné**.
`client-mobile` uniquement — aucun changement de logique.

## Référence Stitch
- **Réutiliser** l'écran Stitch `biology-ack-confirm-dialog` (correspondance
  exacte). NB : un écran orphelin `Confirmation : Patient contacté` existe aussi
  (doublon probable) — le **nettoyage** côté Stitch est un geste humain optionnel.
- Étape design : `/stitch-design task-128`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (modale/feuille, titre, message, boutons,
      arrondis cartes 8px / bottom-sheet 12px du socle)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés (confirmer / annuler)
- [ ] Aucune régression (confirmation/annulation déclenchent les mêmes effets)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, déclencher une action d'acquittement ouvrant le dialog.
- Vérifier le rendu (titre, message, boutons) au nouveau design.
- Confirmer puis (autre essai) annuler → effets inchangés.
- Comparer à la maquette Stitch `biology-ack-confirm-dialog`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : biologie médicale (acquittement) — restyling UI. **Vague** :
  hors Ségur (UX).
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable — restyling sans
  logique métier.

## Branches
- `client-mobile` (pushed) : feat/task-128-stitch-biology-ack-confirm-dialog — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-128-stitch-biology-ack-confirm-dialog

## Stitch design log
- Écran Stitch `biology-ack-confirm-dialog` (id 53bbca53f21b4ad99bd8ed355628cac8) **réutilisé**.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLscODUrMTZmMpgqb94d6YYPdKnc02tSon3UW5daDJcFGRGGZ8_jtDogxekSi1z4p2xJ8xHOSL2jgBhHkSTyL7toixAE8-hNfGrLatzHWc6VH6tdm4n1640IBT93sVeZK5T1LgWQv3g5ur2XZdL9FtK4xuYyj5ZNVqU3mzuYFh6ENncLWAOM4SVksPdcqrqsJwGxfeye0H57UwMdv94SFGyDP-hwIWOMJeEmGF5bQiGv2LmrPLzRBTln2DNO
- NB : un écran orphelin « Confirmation : Patient contacté » (id 529342a3493b4c559269f7b7676a2e56) coexiste — doublon probable ; nettoyage Stitch = geste humain optionnel (non bloquant).
- Refonte = migration SCSS 100 % token-driven (action, encart valeurs critiques → `--app-error-container`/`radius-lg`, LOINC, bouton). Logique (note optionnelle, confirm/cancel, valeurs critiques) inchangée.

## Develop log
- Repos touchés : `client-mobile` (poussé). Commit `a518c2c`.
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓**.
- Next step : /forge-simplify task-128.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven, rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-128.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-128.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/31 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle SCSS 100 % token-driven, encart critique en error-container, logique inchangée, data-testid préservés. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `biology-ack-confirm-dialog` réutilisé (doublon « Confirmation : Patient contacté » à nettoyer côté humain, optionnel).

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `03ce1b5` (PR #31 fermée).
- CI develop : aucun workflow CI sur ce repo.
- Remote branch `feat/task-128-stitch-biology-ack-confirm-dialog` supprimée ; branche locale conservée.
