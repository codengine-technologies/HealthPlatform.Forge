# todo-task-122.md — Refonte Stitch composant `mail-body` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le rendu du corps de message `mail-body`
(`src/app/features/mail/components/mail-body/*`) pour une fidélité parfaite à sa
**référence Stitch** `mail-body`, sur la base du socle `done-task-110`.

Affichage du corps (texte/HTML sécurisé via medical-html-frame), typographie
lisible, espacements, citations/réponses. Travail **soigné**. `client-mobile`
uniquement — aucun changement fonctionnel ni du pipeline d'assainissement HTML.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-body` (correspondance exacte).
- Étape design : `/stitch-design task-122`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure/typographie alignées sur Stitch (lisibilité corps, espacements,
      citations)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] Assainissement HTML inchangé (aucune modification du pipeline de sécurité)
- [ ] Aucune régression d'affichage du corps
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir un message texte et un message HTML.
- Vérifier la lisibilité (typo Public Sans, interlignage, espacements) au nouveau
  design ; le contenu reste correctement assaini.
- Comparer à la maquette Stitch `mail-body`.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — restyling UI.
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable. Assainissement HTML
  (sécurité) inchangé ; ne jamais exposer de contenu MSSanté en clair hors rendu.

## Branches
- `client-mobile` (pushed) : feat/task-122-stitch-mail-body — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-122-stitch-mail-body

## Stitch design log
- Écran Stitch `mail-body` (id c9f8d3d5941e4fa097a6be64ace4a549) **réutilisé**.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLsmgUri6wMmZj7dE4qxyNvnLlzYd5K4SMpuYjz8QzXiJYhQoZtbHoWueO-IHR2M4oaHbHAKn4zKhFXnPFbFHe9Cd6m-MOaE6d4d-SqbxhRbvVavGoKwzsL4cq1c1G1L7M4mrz8M-IKZqtkfBlQMCmIU7BTLFF23-9AXSl7mmj-ghhM-A62oUpdtYx16KPl3ik_6VhSU8LOl0Dpq-a-fYZpW4dIHmIO1aa3apFfZhgE1MdL6r8T5haTn64I
- Refonte = migration SCSS 100 % token-driven (onglets, pane, bannière images
  distantes, corps HTML/texte, vide) ; typo Public Sans + interlignage 1.6 pour
  les notes cliniques longues. Pipeline d'assainissement HTML **inchangé**.

## Develop log
- Repos touchés : `client-mobile` (poussé).
- Commit poussé : client-mobile `50028b6` feat(mobile): Stitch restyle of mail-body (token-driven).
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓** (restyle SCSS pur).
- Stitch : écran `mail-body` réutilisé ; migration SCSS token-driven, pipeline d'assainissement HTML inchangé.
- Next step : /forge-simplify task-122.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven, rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-122.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-122.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/25 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle SCSS 100 % token-driven (typo/espacements/formes/surfaces, interlignage 1.6), pipeline d'assainissement HTML inchangé, comportement/structure inchangés. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `mail-body` réutilisé.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `977f84b` (PR #25 fermée).
- CI develop : aucun workflow CI sur ce repo.
- Remote branch `feat/task-122-stitch-mail-body` supprimée ; branche locale conservée.
