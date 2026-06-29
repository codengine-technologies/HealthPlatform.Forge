# todo-task-123.md — Refonte Stitch composant `medical-html-frame` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le cadre d'affichage HTML médical
`medical-html-frame` (`src/app/features/mail/components/medical-html-frame/*`)
pour une fidélité parfaite à sa **référence Stitch** `medical-html-frame`, sur la
base du socle `done-task-110`.

Conteneur d'affichage de documents HTML médicaux (cadre sandbox/sécurisé, états
chargement/erreur, responsive). Travail **soigné**. `client-mobile` uniquement —
**aucun** changement du mécanisme de sandbox/sécurité ni du contenu.

## Référence Stitch
- **Réutiliser** l'écran Stitch `medical-html-frame` (correspondance exacte).
- Étape design : `/stitch-design task-123`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure/cadre alignés sur Stitch (conteneur, états chargement/erreur,
      responsive)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] Mécanisme de sandbox/sécurité **inchangé**
- [ ] Aucune régression d'affichage des documents HTML médicaux
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir un message comportant un document HTML médical (CDA
  rendu).
- Vérifier le cadre (bords, états, responsive) au nouveau design ; le document
  reste correctement isolé/affiché.
- Comparer à la maquette Stitch `medical-html-frame`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : transverse (affichage documents) — restyling UI. **Vague** :
  hors Ségur (UX).
- **Interop CI-SIS** : le rendu CDA et son assainissement restent inchangés (via
  `interop-cda` / pipeline existant). **DSR / INS / Authentification /
  Habilitations / PGSSI-S / Consentement / Référentiels / HDS / RGPD** : non
  applicable. Sandbox de sécurité préservée.

## Branches
- `client-mobile` (pushed) : feat/task-123-stitch-medical-html-frame — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-123-stitch-medical-html-frame

## Stitch design log
- Écran Stitch `medical-html-frame` (id a79637193fbe4ff1847dfeb290c5efdf) **réutilisé**.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLs12znClIA3xUU8nkltUBU2lYM3I3vOywP57iJjuZ-c6QXw53BFeXmQtzwYjbKEPzbIUoI6LBPpNVDZEdOnCVgQvYIdIx5uUKwhMOD7WzjPEO-6UqBuWPv4SOkQeNQvHLtuqBYC6u4nYWUFJlYkmQ1BKQu_lZzK7ICP5oFVXDOWA1o7UqFG3GuKYtBcL-oxXNXS_GrR2gXtqzmsoKQQSLAm0tbhlS6N3D7K3B1i_rCGBBXuOCfaEwOtURee
- La maquette montre le CDA dans une **carte bordée arrondie** (`border-outline-variant rounded-lg overflow-hidden`), rendu en **Public Sans** / couleurs Clinical Precision (#1a1c1e, #00478d).
- Refonte : (1) iframe enveloppée dans un conteneur token-driven (bordure `--app-outline-variant`, `--app-radius-lg`, overflow hidden, surface `--app-surface-container-lowest`) ; (2) tokens par défaut injectés dans le document alignés sur la palette (#1a1c1e/#00478d) + pile Public Sans. **Mécanisme iframe/blob/sandbox strictement inchangé** ; contenu CDA inchangé.

## Develop log
- Repos touchés : `client-mobile` (poussé).
- Commit : client-mobile `f0f93b7` feat(mobile): Stitch restyle of medical-html-frame.
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓**.
- Sandbox/blob/iframe inchangé ; conteneur token-driven + tokens injectés alignés palette + Public Sans.
- Next step : /forge-simplify task-123.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle (conteneur token-driven + valeurs de tokens injectées), rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-123.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-123.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/26 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Conteneur token-driven (bordure/radius/surface E014) + tokens injectés alignés palette/Public Sans ; mécanisme iframe/blob/sandbox strictement inchangé ; contenu CDA inchangé. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `medical-html-frame` réutilisé.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `e279517` (PR #26 fermée).
- CI develop : aucun workflow CI sur ce repo.
- Remote branch `feat/task-123-stitch-medical-html-frame` supprimée ; branche locale conservée.
