# todo-task-124.md — Refonte Stitch composant `mail-attachment` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** l'élément pièce jointe `mail-attachment`
(`src/app/features/mail/components/mail-attachment/*`) pour une fidélité parfaite
à sa **référence Stitch** `mail-attachment`, sur la base du socle `done-task-110`.

Carte/ligne PJ : icône de type (PDF, image, CDA…), nom, taille, action
télécharger, état (chargement/erreur). Travail **soigné**. `client-mobile`
uniquement — aucun changement fonctionnel.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-attachment` (correspondance exacte).
- Étape design : `/stitch-design task-124`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (icône type, nom, taille, action télécharger,
      états)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés (bouton télécharger)
- [ ] Aucune régression (téléchargement, états)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir un message avec pièces jointes.
- Vérifier le rendu (icône type, nom, taille, bouton) au nouveau design.
- Télécharger une PJ → comportement inchangé.
- Comparer à la maquette Stitch `mail-attachment`.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — restyling UI.
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable. Ne jamais exposer
  de contenu de PJ santé en clair dans l'UI/les logs au-delà de l'existant.

## Branches
- `client-mobile` (pushed) : feat/task-124-stitch-mail-attachment — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-124-stitch-mail-attachment

## Stitch design log
- Écran Stitch `mail-attachment` (id ed9c3a7e0a524b0bb6db3794b4e51df5) **réutilisé**.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLss-YG8RVVsHuVMQxiEKeceBjZrxfL7W43V0JJfkEBIgHXXlVaeG0WbpyhfMc8QP3qwiVMvKVjRw7jt_mS3fGu_JQTnBctlHrTh-jDh2QrLvYAtqtfu8nrkDIVB2Xk0ZHMBVGa4bYRByNh5htugcQ-iW5RkRZ-7DbLfs7Nz_ckgW957vaGwwRHE0YsUCnObpn83gt0KKCEnnzO1OGR-L-b72XF_0QkwccpyYTHs5cX3lTR43ZoHeADmn78k
- Refonte = migration SCSS 100 % token-driven (en-tête PJ, lignes, nom/taille,
  badge document médical, bouton ZIP). HTML/TS (icônes, téléchargement, ZIP,
  prévisualisation) inchangés.

## Develop log
- Repos touchés : `client-mobile` (poussé). Commit `b7785c3`.
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓** (restyle SCSS pur).
- Next step : /forge-simplify task-124.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven, rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-124.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-124.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/27 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle SCSS 100 % token-driven, structure & comportement inchangés, data-testid préservés. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `mail-attachment` réutilisé.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `03e6d63` (PR #27 fermée).
- CI develop : aucun workflow CI sur ce repo.
- Remote branch `feat/task-124-stitch-mail-attachment` supprimée ; branche locale conservée.
