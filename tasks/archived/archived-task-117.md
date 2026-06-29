# todo-task-117.md — Refonte Stitch composant `mail-folder-item` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** l'item de dossier `mail-folder-item`
(`src/app/features/mail/components/mail-folder-item/*`) pour une fidélité
parfaite à sa **référence Stitch** `mail-folder-item`, sur la base du socle
`done-task-110`.

Ligne unitaire d'un répertoire : icône, nom du dossier, compteur non-lus, état
sélectionné/actif. Travail **soigné**. `client-mobile` uniquement — aucun
changement fonctionnel.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-folder-item` (correspondance exacte).
- Étape design : `/stitch-design task-117`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (icône, nom, compteur non-lus, état actif)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés
- [ ] Aucune régression (clic, sélection, compteur)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir le menu des dossiers.
- Vérifier le rendu d'un item (icône, nom, compteur, état actif) au nouveau design.
- Cliquer un item → sélection inchangée.
- Comparer à la maquette Stitch `mail-folder-item`.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — restyling UI.
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable — restyling sans
  logique métier.

## Branches
- `client-mobile` (pushed) : feat/task-117-refonte-stitch-mail-folder-item — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-117-refonte-stitch-mail-folder-item

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | mail-folder-item | mail-folder-item | 16124e44e18445249ab949869df222a8 | reused | (récupéré via get_screen, consigné en session) |
- ⚠ Rename needed in Stitch UI : none.
- Stitch reachable : ✓
- Constat : l'essentiel de `mail-folder-item` (icônes par type, badge sombre,
  arborescence/chevron, pastille de base) a déjà été aligné par **task-116**
  (le composant est la ligne du `mail-folder-list`). La maquette dédiée
  `mail-folder-item` révèle **un seul écart résiduel** : l'item **actif** est
  une **pilule bleu clair** (primary-container) avec icône + texte **bleus**,
  alors que task-116 utilisait un gris.

## Develop log

- Repos touched : client-mobile (seul repo de la task)
- DTOs / Interop : aucun changement de contrat
- Périmètre : reprise ciblée de l'**état sélectionné/actif** de
  `mail-folder-item` pour fidélité à la maquette dédiée. Le reste de la ligne
  (icônes par type, badge non-lus sombre, pastilles tag, arborescence) provient
  déjà de task-116 — non re-touché.
- Implémentation (token-driven) :
  - `mail-folder-item.component.scss` : `.folder-item--selected` →
    fond `rgba(var(--app-primary-container-rgb), 0.1)` (pilule bleu clair),
    `--color`/icône/nom = `--ion-color-primary`. Remplace le gris
    `--app-surface-container` posé par task-116.
- Nuance différée (hors « compteur non-lus » du DOD) : la maquette montre un
  compteur **total** grisé sur Brouillons (vs badge sombre des non-lus) ;
  non implémenté pour ne pas introduire d'affichage hors scope.
- Tests : inchangés (modification purement SCSS ; getters `isSelected`/icône/tag
  déjà couverts par les specs task-116).
- Local build / test : ✓ (npm run build OK ; **135/135** tests OK, headless).
- DOD self-check :
  - Build passe ✓ ; Tests passent (135/135) ✓
  - Structure alignée (icône, nom, compteur non-lus, **état actif bleu**) ✓
  - Tokens du socle réutilisés, aucune valeur de design en dur ✓
  - data-testid préservés (folder-item-*, folder-toggle-*, folder-unread-*, folder-tag-dot-*) ✓
  - Aucune régression (clic/sélection/compteur inchangés ; tests verts) ✓
  - Comparaison visuelle screenshot Stitch : ⏸ déferré (HAG) — test humain
- Next step : /forge-simplify task-117

## Simplify log

- Repo : client-mobile (seul repo touché)
- Verdict : **skip clean** — le diff est un unique bloc SCSS token-driven
  (`.folder-item--selected` en pilule bleue), sans duplication ni gain
  reuse/simplif/efficacité/altitude.
- dtos-mss / interop-cda : non touchés (hors scope simplify).
- Next step : /lint-mobile task-117 (api-mail non touché → /sonar skip ;
  client-angular non touché → /lint-angular skip).

## Lint mobile log

- Repo : client-mobile (Working dir Client/Mobile/)
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 erreur.
- Aucun fix (diff SCSS uniquement, non linté par ESLint).
- Next step : /review task-117

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/21 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (SCSS pur token-driven, 0 blocking).
- `mail-folder-item.component.scss` — ✅ `.folder-item--selected` en pilule bleu clair (`rgba(var(--app-primary-container-rgb), 0.1)`), icône/nom en `--ion-color-primary`.
- Contexte : l'essentiel de `mail-folder-item` provenait déjà de task-116 ; task-117 ne corrige que l'état actif (gris → bleu).
- Nuance différée : compteur total grisé Brouillons (hors scope « compteur non-lus »).
- Build ✓ | Tests 135/135 ✓ | Lint ✓.
- ⚠ DOD « comparaison visuelle » Stitch : déféré au test humain (HAG).

## Merged

- Date : 2026-06-24 (human-triggered `/merge task-117 --i-tested`, HAG validé).
- Squash-merge :
  - `client-mobile` : `9816802` (PR #21 closed) — branche distante
    `feat/task-117-refonte-stitch-mail-folder-item` supprimée, branche locale conservée.
- `develop` CI : aucun workflow configuré sur le repo `HealthPlatform.Mobile`
  (rien à vérifier — rule 5 N/A).
