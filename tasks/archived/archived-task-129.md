# todo-task-129.md — Refonte Stitch composant `mail-compose` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** la composition/envoi de message `mail-compose`
(`src/app/features/mail/components/mail-compose/*`) pour une fidélité parfaite à
sa **référence Stitch** `mail-compose`, sur la base du socle `done-task-110`.

Écran de rédaction : destinataires (To/Cc/Cci), sujet, corps (html-editor),
pièces jointes, options (accusé de réception), action envoyer. Travail **soigné**.
`client-mobile` uniquement — aucun changement de la logique d'envoi.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-compose` (correspondance exacte).
- Étape design : `/stitch-design task-129`. Stitch = référence, pas du code.
- Coordination : compose intègre `html-editor` (task-130) — respecter la
  composition.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (champs To/Cc/Cci, sujet, corps, PJ, options
      accusé, bouton envoyer ; inputs au style socle, label visible)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés (champs, envoyer, ajouter PJ)
- [ ] Aucune régression (saisie, ajout PJ, Cc/Cci, accusé, envoi)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir la composition (FAB de l'inbox).
- Vérifier le rendu (champs, sujet, corps, PJ, options) au nouveau design ;
  inputs avec label visible, boutons primary, touch ≥ 44px.
- Rédiger, ajouter Cc/Cci + une PJ + accusé, envoyer → comportement inchangé.
- Comparer à la maquette Stitch `mail-compose`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : médecine de ville (envoi MSSanté) — restyling UI sans
  logique métier. **Vague** : hors Ségur (UX).
- **MSSanté** : flux d'envoi inchangé (certificat/en-têtes/routage existants).
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable au restyling. Jamais
  d'INS/RPPS dans les sujets/headers ; ne jamais exposer de contenu en clair hors UI.

## Branches
- `client-mobile` (pushed) : feat/task-129-stitch-mail-compose — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-129-stitch-mail-compose

## Stitch design log
- Écran Stitch `mail-compose` (id 340f18be9395435f8fc472e0c476f736) **réutilisé**.
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLtx3dNeWsvWfE8sqEWYUujJl5ZIYPoWNPoN93LLvLdTpW_2szovhfKp6zN_k0l6ytYSGOB5kLOm4ANgrFaKyPy-ih9uAS5-0LT2cCWZxyg6LURdt_oloQKGD_ve4XGazVZtWo1R-zvy0ZhXzCOaA9Sp9VIvUi6OTkKMwjwBOEkwaa3AQhL-yYzGpX752lKH8StQu_6VgIwruztjCCxbAZ1IBr7ZqZs6AmboFFsT2ykiqE53zx0PncTZViue
- Refonte = migration SCSS 100 % token-driven (corps, zone PJ, bouton « Ajouter
  une PJ »). Champs To/Cc/Cci/Objet = `ion-input` à label visible (inchangés,
  héritent du socle). `mss-html-editor` composé (task-130, non re-touché ici).
  Logique d'envoi (To/Cc/Cci, PJ, accusé, send) inchangée.

## Develop log
- Repos touchés : `client-mobile` (poussé). Commit `9c87c4e`.
- Vérifs : `npm run build` ✓ ; `npm test` headless **151 ✓**.
- Next step : /forge-simplify task-129.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — restyle SCSS token-driven, rien à simplifier.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-129.

## Lint mobile log (client-mobile)
- Baseline `npm run lint` : **All files pass linting** — 0 erreur. Skip clean.
- Next step : /review task-129.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/32 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle SCSS 100 % token-driven, logique d'envoi inchangée, data-testid préservés. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch `mail-compose` réutilisé.

## Merged
- Date : 2026-06-26 (human-tested, HAG rule 10)
- `client-mobile` : squash `3a25f791baf52aa4fc82864b5b367ddd44482156` (PR #32 closed, remote branch deleted, local branch kept)
- develop CI : no checks configured on mobile repo (GitHub) — fast-forward to develop OK
