# todo-task-116.md — Refonte Stitch composant `mail-folder-list` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** la liste des dossiers/répertoires
`mail-folder-list` (`src/app/features/mail/components/mail-folder-list/*`) pour
une fidélité parfaite à sa **référence Stitch** `mail-folder-list`, sur la base
du socle `done-task-110`.

Menu latéral des répertoires MSSanté (arborescence, compteurs non-lus, dossier
sélectionné). Travail **soigné**. `client-mobile` uniquement — aucun changement
fonctionnel.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-folder-list` (correspondance exacte).
- Étape design : `/stitch-design task-116`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure alignée sur Stitch (arborescence dossiers, compteurs non-lus,
      état sélectionné, en-tête du menu)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés
- [ ] Aucune régression (sélection de dossier, navigation, compteurs)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir le menu latéral des dossiers depuis l'inbox.
- Vérifier rendu (densité, compteurs, dossier actif) au nouveau design.
- Sélectionner un dossier → la liste se met à jour, comportement inchangé.
- Comparer à la maquette Stitch `mail-folder-list`.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — restyling UI.
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable — restyling sans
  logique métier.

## Branches
- `client-mobile` (pushed) : feat/task-116-refonte-stitch-mail-folder-list — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-116-refonte-stitch-mail-folder-list

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | mail-folder-list | mail-folder-list | 84138523de2c40c1aa866c64bb5ef84d | reused | (récupéré via get_screen, consigné en session) |
- ⚠ Rename needed in Stitch UI : none (titre = nom kebab-case).
- Stitch reachable : ✓
- Intention reprise : en-tête brand « MSSanté » + section « Répertoires »,
  icônes par type (INBOX=bac, Envoyés=avion, Brouillons=document, Archive=boîte,
  Corbeille=poubelle), état sélectionné en pilule gris clair + gras, badge
  non-lus en pastille sombre, section « TAGS » (pastille colorée + nom).

## Develop log

- Repos touched : client-mobile (seul repo de la task)
- DTOs published : aucun changement de contrat
- Interop published : aucun changement
- Implémentation (Stitch = référence, pas du code — traduit en Ionic + tokens socle) :
  - `mail-folder-item` : icônes ionicon par `FolderType` (`iconName`), détection
    tag (`isTag`/`tagColor` → pastille colorée), pilule sélectionnée, badge
    non-lus sombre — tout token-driven (`theme/variables.scss`).
  - `mail-folder-list` : sections « Répertoires » (IMAP) + « TAGS »
    (`tagFolders` depuis `MailStateService`), en-têtes de section discrètes.
  - `inbox.page.html` : en-tête du menu latéral « Répertoires » → brand « MSSanté »
    (la liste porte sa propre section « Répertoires »).
- Tests : +6 specs `mail-folder-item` (mapping icônes, archive, tag/couleur, dot rendu).
- Local build / test : ✓ (npm run build OK ; 133/133 tests OK, headless).
- DOD self-check :
  - Build passe ✓ ; Tests passent (133/133) ✓
  - Structure alignée (en-tête menu, arborescence, icônes type, compteurs, sélection, TAGS) ✓
  - Tokens du socle réutilisés, aucune valeur de design en dur ✓
  - data-testid préservés/complétés (folder-item-*, folder-toggle-*, folder-unread-*,
    + folder-tag-dot-*, folder-section-repertoires, folder-section-tags) ✓
  - Aucune régression fonctionnelle (sélection/navigation/compteurs inchangés ; tests verts) ✓
  - Comparaison visuelle screenshot Stitch : ⏸ déferré (HAG) — test humain sur l'app lancée
- Next step : /forge-simplify task-116

## Simplify log

- Repo : client-mobile (seul repo touché)
- Verdict : **skip clean** — rien à simplifier. Le diff (mail-folder-item +
  mail-folder-list + en-tête menu) est déjà token-driven, réutilise la
  récursion `mss-mail-folder-item` existante et `MailStateService.tagFolders`,
  `iconName` est un `switch` propre, l'en-tête de section est paramétré. Les
  deux `@for` (IMAP / TAGS) ne diffèrent que par la source ; les factoriser
  via `ngTemplateOutlet` ajouterait de l'indirection sans gain matériel
  (altitude → garder deux boucles lisibles).
- dtos-mss / interop-cda : non touchés (et hors scope simplify).
- Next step : /lint-mobile task-116 (api-mail non touché → /sonar skip ;
  client-angular non touché → /lint-angular skip).

## Lint mobile log

- Repo : client-mobile (Working dir Client/Mobile/)
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 erreur, 0 warning.
- Aucun fix nécessaire, aucune itération, aucun commit (le diff folder-list/
  folder-item + en-tête menu est ESLint-clean).
- Next step : /review task-116

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/19 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (refactor HTML/SCSS/TS, 0 blocking).
- `mail-folder-item.ts` — ✅ `iconName` switch exhaustif (default folder/archive), `isTag`/`tagColor` corrects.
- `mail-folder-item.html` — ✅ 3 branches (chevron / pastille tag / icône type), pilule sélectionnée, badge sombre, data-testid complétés.
- `mail-folder-list.*` — ✅ sections Répertoires + TAGS (`MailStateService.tagFolders`), en-têtes discrètes.
- `inbox.page.html` — ✅ en-tête menu « Répertoires » → « MSSanté ».
- ⚠️ Suggestion (non bloquant) : sélection d'un dossier tag via le même flux que les IMAP (cohérent miroir client-angular) — à confirmer au test manuel.
- Build ✓ | Tests 133/133 ✓ | Lint ✓.
- ⚠ DOD « comparaison visuelle » Stitch : déféré au test humain (HAG) sur l'app lancée.

## Merged

- Date : 2026-06-24 (human-triggered `/merge task-116 --i-tested`, HAG validé).
- Squash-merge :
  - `client-mobile` : `71aedf5` (PR #19 closed) — branche distante
    `feat/task-116-refonte-stitch-mail-folder-list` supprimée, branche locale conservée.
- `develop` CI : aucun workflow configuré sur le repo `HealthPlatform.Mobile`
  (rien à vérifier — rule 5 N/A).
