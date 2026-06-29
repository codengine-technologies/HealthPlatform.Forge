# todo-task-130.md — Refonte Stitch composant `html-editor` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** l'éditeur de contenu `html-editor`
(`src/app/features/mail/components/html-editor/*`) pour une fidélité parfaite à
sa **référence Stitch** `html-editor`, sur la base du socle `done-task-110`.

Zone d'édition du corps de message : barre d'outils (formatage), zone de saisie,
états focus/placeholder. Travail **soigné**. `client-mobile` uniquement — aucun
changement des capacités d'édition.

## Référence Stitch
- **Réutiliser** l'écran Stitch `html-editor` (correspondance exacte).
- Étape design : `/stitch-design task-130`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (barre d'outils, zone de saisie, états focus/
      placeholder ; boutons d'outils au style socle, touch ≥ 44px)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés sur les boutons d'outils
- [ ] Aucune régression (formatage, saisie, focus)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir la composition affichant `html-editor`.
- Vérifier le rendu (barre d'outils, zone, focus, placeholder) au nouveau design.
- Tester le formatage et la saisie → comportement inchangé.
- Comparer à la maquette Stitch `html-editor`.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — restyling UI.
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable — restyling sans
  logique métier.

## Branches
- `client-mobile` (pushed) : feat/task-130-stitch-html-editor — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-130-stitch-html-editor

## Stitch design log
- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | html-editor | html-editor | c944b34bc4fb4e8d891c97fd30719b92 | reused | https://lh3.googleusercontent.com/aida/AP1WRLv4RER8hAc-aaCrGfOXXxvtgTyU3k7ANjeEneqcOLGQVHrTN1VRFL2-gdDoaCZJM17xnoBr5XU551eCBkxIScFbkCdiCLmCtF3IeAZu0aqSLug1sEwaX_ED2oo1N4AxoFzsJh4fdo8TKsc-lK-9z34LKb5J9LL-9b-3uGyOBrPNNf_1wXwpjojnzcweBbyzkYS60WxdBkI94pS1YjfL-sebARVjK7pbkDaAa4BRk10IhhNGUaRyImuZJN1b |
- ⚠ Rename needed in Stitch UI : none (title already `html-editor`).
- Stitch reachable : ✓
- Intent retenu : barre d'outils plate `--app-surface-container-low` + bordure basse `--app-outline-variant`, boutons d'outils 44px (`--app-touch-target`) en `--app-on-surface-variant`, radius `--app-radius-sm` ; zone d'édition `--app-type-body-lg`, placeholder « Écrivez votre message sécurisé ici… » en `--app-outline`.

## Develop log
- Repos touched : `client-mobile` (poussé). Commit `ab6e9ed`.
- DTOs published : no DTO change. Interop published : no interop change.
- Stitch : écran `html-editor` réutilisé (id c944b34bc4fb4e8d891c97fd30719b92).
- Vérifs : `npm run build` ✓ (0 erreur) ; `npm test` headless **151 ✓**.
- DOD self-check : build ✓, tests ✓, SCSS 100 % token-driven (aucune valeur en dur),
  data-testid d'outils préservés (bold/italic/list/link), boutons 44px. Comparaison
  visuelle Stitch consignée (Stitch design log).
- Next step : /forge-simplify task-130.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven déjà minimal (aucune duplication, pas de règle redondante), rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-130 (api-mail & client-angular non touchés → /sonar & /lint-angular skip).

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-130.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/33 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Refonte SCSS/HTML 100 % token-driven du composant `html-editor`, alignée sur sa référence Stitch (id c944b34bc4fb4e8d891c97fd30719b92). Logique d'édition (gras/italique/liste/lien) inchangée, `data-testid` préservés, boutons d'outils ≥ 44px. Build ✓, 151 tests ✓, lint 0 erreur.

## Merged
- Date : 2026-06-26 (human-tested, HAG rule 10)
- `client-mobile` : squash `0fffcd705751e38649bb034b6258b6f2d427580d` (PR #33 closed, remote branch deleted, local branch kept)
- develop CI : no checks configured on mobile repo (GitHub) — fast-forward to develop OK
