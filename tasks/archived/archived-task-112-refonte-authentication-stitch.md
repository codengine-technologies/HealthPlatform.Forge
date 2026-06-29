# todo-task-112.md — Refonte Stitch écran `authentication` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Branches
- `client-mobile` (pushed) : feat/task-112-refonte-authentication-stitch — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-112-refonte-authentication-stitch

## Objective
Refondre **structurellement** l'écran `authentication`
(`src/app/authentication/authentication.page.*`) pour une fidélité parfaite à sa
**référence Stitch** `authentication` (projet `client-mobile`, id
`10088502293310567548`), sur la base du socle `done-task-110`.

Travail **soigné** : l'écran d'authentification (parcours PSC / redirection /
callback) doit correspondre visuellement à la maquette. `client-mobile`
uniquement — aucun changement de la logique d'authentification.

## Référence Stitch
- **Réutiliser** l'écran Stitch `authentication` (correspondance exacte).
- Étape design : `/stitch-design task-112`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur la référence Stitch `authentication` (layout, états
      chargement / redirection / erreur)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés sur les interactifs
- [ ] Aucune régression fonctionnelle du parcours d'authentification
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, déclencher le parcours d'authentification.
- Vérifier le rendu (typo Public Sans, bleu #005EB8, arrondis, espacements) et
  les états transitoires (chargement / redirection / erreur) au nouveau style.
- Vérifier que le parcours aboutit comme avant (aucune régression).
- Comparer à la maquette Stitch `authentication`.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — restyling UI.
- **DSR / INS / Habilitations / Interop / PGSSI-S / Consentement / Référentiels /
  HDS / RGPD** : non applicable — restyling sans logique métier.
- **Authentification PS** : inchangée (aucun flux d'auth modifié).

## Stitch design log
- Project : client-mobile (id 10088502293310567548)
- Screen : authentication (id 87324d3e550b41debfeef8a162f1b56e) — reused ✓
- Intent traduit en Ionic : header marque centré, état chargement (spinner +
  « Connexion en cours… » + sous-titre), état erreur (icône + titre + message +
  Réessayer/Annuler), footer réassurance sécurité.
- Adaptation : « Certifié HIPAA & RGPD » de la maquette → « Certifié ANS & RGPD »
  (HIPAA = US, hors champ MSSanté France ; ANS = autorité française pertinente).

## Develop log
- Repos touched : client-mobile
- Implémentation : `authentication.page.{html,scss,ts}` (ajout styleUrls), refonte
  d'après Stitch, 100% tokens socle, data-testid (auth-loading/error/retry/cancel).
  Logique de callback PSC (`ngOnInit`, `$exchangeCodeForToken`) inchangée.
- Commit : client-mobile e78d09f
- Build / test : ✓ build OK, 108/108 tests verts
- Next step : /forge-simplify task-112

## Simplify log
- client-mobile touché ; refonte d'écran propre et token-based → aucune
  simplification applicable. Aucun commit. dtos-mss/interop-cda non touchés.
- Next : /lint-mobile

## Lint mobile log
- npm run lint → 0 errors / 0 warnings (« All files pass linting »). Aucun fix.
- Next : /review task-112

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/16 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 bloquant)
- build ✓, 108/108 tests ✓, lint ✓
- Logique callback PSC inchangée ; template token-based ; data-testid sur états/actions
- Adaptation « HIPAA »→« ANS » justifiée (conformité MSSanté France)
- Comparaison visuelle Stitch déférée au test humain (HAG)

## Merged
- Date : 2026-06-23 · Validation humaine : `--i-tested` (HAG, règle 10)
- `client-mobile` : squash `f6f1170` — PR #16 mergée et fermée
- Remote branch supprimée ; branche locale conservée
- CI `develop` : aucun workflow CI configuré sur le repo mobile
- Stitch : écran `authentication` synchronisé (« HIPAA »→« ANS ») via edit_screens
