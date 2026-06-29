# todo-task-121.md — Refonte Stitch écran `mail-detail` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le détail d'un message `mail-detail`
(`src/app/mail-detail/mail-detail.page.*` **et**
`src/app/features/mail/components/mail-detail/*`) pour une fidélité parfaite à sa
**référence Stitch** `mail-detail`, sur la base du socle `done-task-110`.

Écran de lecture d'un message : en-tête (mail-header), corps (mail-body), pièces
jointes, bloc biologie, barre d'actions (répondre, transférer, lu/non-lu, flag,
supprimer, déplacer). Travail **soigné** exigé. `client-mobile` uniquement —
aucun changement fonctionnel.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-detail` (correspondance exacte).
- Étape design : `/stitch-design task-121`. Stitch = référence, pas du code.
- Coordination : cet écran compose `mail-header` (task-118), `mail-body`
  (task-122), `mail-attachment` (task-124), `biology` (task-125). Respecter la
  composition lors de la refonte.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (en-tête, corps, PJ, biologie, barre d'actions)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés sur toutes les actions
- [ ] Aucune régression (lecture, actions, navigation retour)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir un message depuis l'inbox.
- Vérifier le rendu (en-tête, corps, PJ, biologie, actions) au nouveau design ;
  typo Public Sans, espacements 8px, arrondis doux.
- Tester chaque action (répondre/transférer/lu/flag/supprimer/déplacer) → inchangé.
- Comparer à la maquette Stitch `mail-detail`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : médecine de ville / biologie (lecture message) — restyling
  UI sans logique métier. **Vague Ségur** : hors Ségur (UX).
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable. Ne jamais exposer
  d'INS/contenu CDA/MSSanté en clair au-delà de l'affichage métier existant.

## Branches
- `client-mobile` (pushed) : feat/task-121-stitch-mail-detail — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-121-stitch-mail-detail

## Stitch design log
- Projet Stitch `client-mobile` (id 10088502293310567548) ; design system « Clinical Precision ».
- Écran **réutilisé** : `mail-detail` (id 2ca2f78af2244d46a0f1c00cf6a1fe61).
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLuSqr-H_lflwayCwjvKK1jqwWbg2GN7X9vVITbUavjVNP4TJDeZZX7DzrafSb-LVmEUUpEw2lHUNBLWG8fSg_UGrOBxJqeDNX3aXf5wus3OlYXX98MexaolRAX3WSkmJpWojEGJnXdHC-7LdMKZU9f3Yz1xeArgR4LvW4fTtluDDv1YkQLzo_WBraWubO7vbDhzDWPHJLeIP47Jn6rmyedweEIlCDeOO7-JA9QKDbYYWkGtdDJNNtI2bQQ
- Structure de la maquette (sujet → identité patient + INS → De/À/Date → barre
  d'actions → bandeau accusé → corps → pièces jointes) **déjà alignée** avec le
  composant existant. Refonte = migration 100 % token-driven du SCSS du
  `mail-meta-card` (couleurs/typo/espacements/formes → tokens E014), sans
  changement de structure ni de comportement. `mail-body`, `mail-attachment`,
  `biology` restent du ressort de leurs tasks dédiées (122/124/125).

## Develop log
- Repos touchés : `client-mobile` (poussé). Aucun DTO/interop/backend.
- Commit poussé : client-mobile `8b8c9c8` feat(mobile): Stitch restyle of mail-detail (token-driven meta card).
- Vérifs locales : `npm run build` ✓ (0 erreur ; seul warning budget pré-existant home.page.scss) ; `npm test` headless **151 ✓** (restyle SCSS pur, pas de delta de tests).
- Stitch : écran `mail-detail` réutilisé ; structure déjà alignée → migration token-driven du SCSS uniquement. Cf. ## Stitch design log.
- DOD : structure alignée (en-tête/corps/PJ/biologie/actions), tokens réutilisés (aucune valeur en dur), data-testid préservés, pas de régression (SCSS pur). Comparaison Stitch consignée.
- Next step : /forge-simplify task-121.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven (+ 1 bind template), rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-121 (api-mail & client-angular non touchés ; client-mobile touché).

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Aucun fix, aucun commit. Skip clean.
- Next step : /review task-121.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/24 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle SCSS 100 % token-driven (typo/espacements/formes/couleurs E014), structure & comportement inchangés, data-testid préservés ; chip de tag par token (drop du `#6b7280` en dur). Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `mail-detail` réutilisé, comparaison visuelle consignée.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `3d703f0` (PR #24 fermée).
- CI develop : aucun workflow CI sur ce repo (rien à attendre).
- Remote branch `feat/task-121-stitch-mail-detail` supprimée ; branche locale conservée.
