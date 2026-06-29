# todo-task-125.md — Refonte Stitch composant `biology` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le tableau de résultats de biologie `biology`
(`src/app/features/mail/components/biology/*`) pour une fidélité parfaite à sa
**référence Stitch**, sur la base du socle `done-task-110`.

Affichage structuré des résultats de biologie médicale (analytes, valeurs,
unités, valeurs de référence, indicateurs d'anormalité/alerte). Lisibilité
clinique **critique** — travail **soigné** exigé (densité, alignement colonnes,
mise en évidence des valeurs hors normes). `client-mobile` uniquement — aucun
changement de la logique métier biologie.

## Référence Stitch
- **Réutiliser** l'écran Stitch existant **titré `BiologyComponent`** comme
  référence. ⚠ **À renommer en `biology`** dans l'UI Stitch (le MCP n'a pas
  d'opération rename — geste humain). `/stitch-design task-125` consigne le
  mismatch. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure du tableau alignée sur Stitch (colonnes analyte/valeur/unité/
      référence, indicateurs d'anormalité, densité, alignement)
- [ ] Valeurs hors normes mises en évidence (accent rouge réservé aux alertes)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés
- [ ] Aucune régression de la logique d'affichage biologie
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir un message de biologie (CR-BIO).
- Vérifier le tableau (colonnes, densité, alignement, mise en évidence des
  valeurs anormales) au nouveau design ; lisibilité clinique préservée.
- Comparer à la maquette Stitch `biology` (ex-`BiologyComponent`).

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : biologie médicale (affichage CR-BIO) — restyling UI sans
  logique métier. **Vague Ségur** : hors Ségur (UX).
- **Interop CI-SIS** : affichage du volet CR-BIO inchangé (parsing/validation via
  pipeline existant). **DSR / INS / Authentification / Habilitations / PGSSI-S /
  Consentement / Référentiels (LOINC) / HDS / RGPD** : non applicable au restyling.
  Ne jamais exposer d'INS/contenu CDA en clair hors affichage métier existant.

## Branches
- `client-mobile` (pushed) : feat/task-125-stitch-biology — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-125-stitch-biology

## Stitch design log
- Écran Stitch de référence **titré `BiologyComponent`** (id 625b517626294bd7bee428a974be3155) — réutilisé comme référence du tableau de biologie.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLtfDuX6QK-i5w0PDru_H5YUDctRswr963oWSjehWCcC3OfAfFlVL_uPx3iRU7Ekc3W3MoZDaGkGgRkiaRC66Y54TzBH6j_p-jjlwMiM7IWn17_Q2WTOs1Y0jN8IdjNL7kcmnuHml1eXut0jSvQlNLDz1QQBWxWQaPrA09jdSs3Xe4VV2kofeQm6AE_YIcT1JzsEZFwmJA36khVkI_Cw1c7dxpz2j8vhYSJFt94G3RqcMzpbeClcJaTXLgWr
- ⚠ **Mismatch de nommage** : l'écran est titré `BiologyComponent` (PascalCase) ; convention E012/E014 = kebab `biology` (= sélecteur `mss-biology`). Le MCP Stitch n'a **pas** d'opération de rename → **renommer `BiologyComponent` → `biology` dans l'UI Stitch est un geste humain** (consigné ici, non bloquant).
- Refonte = migration SCSS 100 % token-driven (colonnes analyte/valeur/unité/référence, densité, badges). Mise en évidence hors normes : conteneur d'erreur `--app-error-container` (rouge doux) ; critique = même fond + liseré danger gauche + valeur en `--ion-color-danger`. Accent rouge réservé aux alertes. Logique métier biologie inchangée.

## Develop log
- Repos touchés : `client-mobile` (poussé). Commit `6cf1583`.
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓** (restyle SCSS pur).
- Next step : /forge-simplify task-125.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven, rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-125.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-125.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/28 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle SCSS 100 % token-driven, hors-normes en `--app-error-container` + accent danger pour le critique, logique biologie inchangée, data-testid préservés. Build ✓, 151 tests ✓, lint 0 erreur. ⚠ Rename Stitch `BiologyComponent`→`biology` = geste humain (MCP sans rename).

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `3c420c8` (PR #28 fermée).
- CI develop : aucun workflow CI sur ce repo.
- Remote branch `feat/task-125-stitch-biology` supprimée ; branche locale conservée.
- ⚠ Reste à faire (humain) : renommer l'écran Stitch `BiologyComponent` → `biology`.
