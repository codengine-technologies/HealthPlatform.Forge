# todo-task-141.md — Sélection multiple + actions en masse sur mobile

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur l'inbox mobile la **sélection multiple** et les **opérations en
masse** de `client-angular` (`mail-list`) : marquer lu/non-lu, flag/unflag,
déplacer vers un dossier, supprimer — en un geste sur N messages. L'état de
sélection existe déjà dans `mail-state.service` mobile mais **aucune UI ne
l'exploite**.

Ergonomie mobile (pas de checkbox permanente comme sur desktop) :
- **Appui long** sur une ligne → entrée en « mode sélection » (haptique)
- En mode sélection : tap = coche/décoche, cases visibles, **barre d'actions
  contextuelle** en header (compteur « N sélectionnés », Tout sélectionner,
  Lu/Non-lu, Flag, Déplacer, Supprimer, Annuler)
- Déplacer → action sheet des dossiers (réutilise celle du swipe unitaire)
- Supprimer → confirmation (alerte cascade lien patient, cohérente avec l'unitaire)

US **frontend-only** : endpoints bulk existants (`bulkUpdateReadStatus`,
`bulkUpdateUnreadStatus`, `bulkUpdateFlagStatus`, `bulkUpdateUnflagStatus`,
`bulkMoveEmails`, `bulkDeleteEmails` — Angular `mss-api.service.ts:1448-1590`).
Aucun changement backend ni DTO.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Appui long → mode sélection ; tap → coche/décoche ; Annuler → sortie propre
- [ ] Barre contextuelle : compteur, Tout sélectionner, Lu/Non-lu, Flag, Déplacer, Supprimer
- [ ] `MssApiService` : 6 méthodes bulk + tests unitaires (succès + erreur + compte retourné)
- [ ] Mise à jour **optimiste** avec rollback sur échec (convention `mail-actions.service` existante)
- [ ] Compteurs non-lus des dossiers cohérents après chaque action en masse
- [ ] Suppression en masse avec confirmation ; sortie du mode sélection après action
- [ ] Tests : entrée/sortie du mode sélection, tout sélectionner, action bulk optimiste + rollback
- [ ] Libellés FR en dur ; `data-testid` sur barre contextuelle et actions
- [ ] Aucune donnée de santé dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; inbox avec ≥ 5 messages
- Appui long sur un message → mode sélection, ligne cochée, barre contextuelle visible
- Cocher 2 autres messages → compteur « 3 sélectionnés »
- « Marquer lu » → les 3 passent lus instantanément, compteur dossier décrémenté
- Re-sélectionner, « Déplacer » → choisir un dossier → messages retirés de la liste, présents dans le dossier cible
- Sélectionner, « Supprimer » → confirmation → messages en Corbeille
- Couper le réseau, tenter une action bulk → rollback visuel + toast d'erreur
- « Tout sélectionner » puis « Annuler » → sortie du mode, aucune action exécutée

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité d'une capacité web existante
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : opérations bulk journalisées côté `api-mail` (canal existant)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-141-mobile-bulk-actions — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-141-mobile-bulk-actions

## Develop log

- Repos touched : `client-mobile`
- DTOs published : no DTO change (US frontend-only, endpoints bulk existants)
- Interop published : no interop change
- Commits :
  - client-mobile : `5ee53a8` feat(mobile): sélection multiple + actions en masse sur l'inbox (task-141)
- Local build / test : ✓ `npm run build` (0 erreur) · `npm test … ChromeHeadless` (428 SUCCESS)
- Implémentation :
  - `MssApiService` : 6 méthodes bulk (`bulkUpdateReadStatus`, `bulkUpdateUnreadStatus`,
    `bulkUpdateFlagStatus`, `bulkUpdateUnflagStatus`, `bulkMoveEmails`, `bulkDeleteEmails`)
    alignées sur les endpoints `…/emails/bulk/*` de `api-mail`.
  - `MailStateService` : `enterSelectionMode`, `selectAllVisible`, `selectedCount`,
    `isAllSelected` (sélection déjà posée en task-099).
  - `MailActionsService` : orchestration en masse optimiste + rollback
    (`bulkMarkRead/Unread/Flag/Unflag/Delete/Move`), compteurs non-lus cohérents.
  - `mss-mail-header` : appui long (450 ms, haptique `@capacitor/haptics`) → `longPress`,
    case de sélection visuelle en mode sélection.
  - `mss-mail-list` : tap = coche/décoche en mode sélection, swipe désactivé.
  - `InboxPage` : barre d'actions contextuelle dans le header (compteur, Tout sélectionner,
    Lu/Non lu, Flag, Déplacer via action sheet, Supprimer avec confirmation cascade lien
    patient, Annuler) ; toast d'erreur au rollback.
- DOD self-check : build ✓, tests ✓, 6 méthodes bulk + tests (succès/erreur/compte) ✓,
  optimiste + rollback testé ✓, entrée/sortie sélection + tout sélectionner testés ✓,
  libellés FR + `data-testid` ✓. Ergonomie appui long / cohérence visuelle → test manuel (HAG).
- Next step : /forge-simplify task-141

## Simplify log

- Repos passed : `client-mobile`
- Applied & committed : client-mobile (3 fichiers, `cba85a4`)
  - Retrait du code mort `MailActionsService.bulkUnflag` (barre = Flag seul ;
    `bulkUpdateUnflagStatus` conservé côté API — parité contrat + DOD).
  - `toggleSelectAll` → `MailStateService.deselectAll()` (fin du poke direct du
    signal, cohérence des mutations d'état).
- No change : —
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Suivi noté (hors scope diff) : les prompts « Déplacer vers… » (action sheet)
  et confirmation de suppression sont désormais une 3e copie de
  `MailListComponent`/`MailDetailComponent`. Extraction d'un
  `MailPromptsService` partagé recommandée en task dédiée (toucherait 2
  composants pré-existants testés — hors périmètre d'une passe simplify).
- Build / tests : ✓ green (`npm run build`, 428 SUCCESS)
- Next step : /lint-mobile task-141 (api-mail & client-angular non touchés)

## Lint mobile log

- Repo : `client-mobile` (feat/task-141-mobile-bulk-actions)
- Baseline `ng lint` : **All files pass linting** — 0 error, 0 warning, 0 fixable
- Iterations : aucune nécessaire (code frais déjà conforme aux consignes
  `conventions/angular.md` : control-flow natif `@if`/`@for`, préfixes
  `mss-`/`app-`, libellés FR en dur, `data-testid`)
- Commit : aucun (rien à corriger)
- Best-effort : ✓ 0 error résiduelle
- Next step : /verify-visual task-141

## Visual verify log

- Écrans capturés : 2 / 2 — **aucun écran blanc, aucune erreur console** — commit `b70deb1`
- Smoke rendu ciblé : le header de l'inbox a été restructuré (`@if (isSelectionMode())`
  → barre contextuelle vs toolbar par défaut). `inbox.page.spec` teste la classe sans
  compiler le template ; cette capture confirme que le rendu par défaut de l'inbox n'a
  pas régressé (toolbar, filtres, chip bio, toggle vue, lignes, FAB, tabs tous présents).

| Écran | Route | Référence Stitch | Capture | Verdict fidélité |
|---|---|---|---|---|
| inbox | /tabs/messages | — (état d'interaction, pas d'écran Stitch dédié — E012 miroir) | [`task-141/inbox.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/b70deb1216eee7dfc334a6571a4ef532d06a5c4e/e2e/screenshots/task-141/inbox.png) | Rendu par défaut conforme ; barre de sélection masquée hors mode sélection (correct). |
| mail-list | /tabs/messages | — | [`task-141/mail-list.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/b70deb1216eee7dfc334a6571a4ef532d06a5c4e/e2e/screenshots/task-141/mail-list.png) | Liste + badges nominaux. |

- Note : le **mode sélection** (barre contextuelle + cases) est un état d'interaction
  atteint par appui long — non scripté par la capture headless (pas de référence Stitch
  à apparier). Vérification ergonomique = test manuel humain (HAG, cf. Manual Test Plan).
- Écrans non mappés (screens.json) : aucun
- APIs non mappées loguées : aucune
- Next step : /review task-141

### Fix post-HAG — mode sélection « affichage vide » (commit dc29dc4)

- **Signalé par le praticien** : en mode sélection, les lignes apparaissaient vides.
- **Cause** : `ion-checkbox` (display:block, label-placement par défaut) s'étirait à
  100 % de la largeur de la ligne (358 px mesurés), réduisant avatar + contenu à
  largeur nulle. Le contenu texte restait dans le DOM (clippé, pas absent) → le
  smoke `/verify-visual` (détection d'écran vide via `innerText.length`) ne l'avait
  pas vu.
- **Correctif** : `.mail-select-check { width: 26px; min-width: 26px }`. Build + 428
  tests ✓.
- **Prévention** : `capture.mjs` gagne une action `longPress` + écran mappé
  `inbox-selection` — l'état de sélection est désormais capturé à chaque cycle.
  Capture [`inbox-selection.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/dc29dc4b385965898037d3bd6d9f9f4b590ca5a5/e2e/screenshots/task-141/inbox-selection.png)
  vérifiée : lignes complètes + case + barre contextuelle.

## PRs

- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/45 — label `awaiting-human-merge`

## Code Review Summary

- Verdict : **APPROVED** — 0 blocking.
- Build ✓ · Tests ✓ (428 SUCCESS) · `ng lint` All files pass · Vérification visuelle : aucun écran blanc.
- Correctness (invariant mono-dossier `folderOf`, décrément non-lus ciblé, capture de la
  sélection avant `clearSelection`), Security (folderPath encodé, `ProblemDetails`, aucune
  donnée de santé loguée), Architecture (miroir du pattern optimiste unitaire), Test coverage
  (6 méthodes bulk succès/erreur/compte, optimiste+rollback, sélection, appui long) — tous ✓.
- DOD : tous les items vérifiables par commande ✓ ; ergonomie appui long / mode sélection
  déférée au test manuel humain (HAG).
- Qualité : /sonar skipped — api-mail non touché.

## Merged

- Merged (human-triggered `/merge --i-tested`) : 2026-07-10 12:24 +0200
- Squash-merged :
  - client-mobile : `2bf986e` feat(mobile): sélection multiple + actions en masse sur l'inbox (task-141) (#45) — PR #45 closed
- Remote branch deleted : `feat/task-141-mobile-bulk-actions` (local branch kept)
- Excluded / not applicable : dtos-mss (no DTO change), api-mail, client-blazor, client-angular (US frontend-only, client-mobile only)
- develop CI : run in-flight at archive time — https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/29086095075 (same commit passed CI green on PR #45 pre-merge : build-android ✓)
