# todo-task-143.md — Dossiers personnalisés + quota mailbox sur mobile

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur `client-mobile` la **gestion des dossiers personnalisés** et
l'**affichage du quota** de la boîte MSSanté, présents dans `client-angular`
(`mail-folder-list` / `mail-folder-item` + `mailbox-quota-widget`, task-087) :

1. **CRUD dossiers personnalisés** — uniquement sur les dossiers de type
   `Custom` (les dossiers système Inbox/Sent/Drafts/Trash/Junk/Important
   restent sans menu) :
   - Créer un dossier (racine ou sous-dossier d'un Custom)
   - Renommer un dossier Custom
   - Supprimer un dossier Custom (confirmation)
   - Ergonomie mobile : bouton « + » en tête de section Dossiers + menu
     contextuel par appui long (ou bouton « ⋯ ») sur un dossier Custom
2. **Quota mailbox** — jauge en pied du volet dossiers :
   `Utilisé X Go / Y Go · Z %`, **ambre ≥ 80 %**, **rouge ≥ 90 %** ; si
   l'opérateur n'annonce pas de quota → « Quota non disponible » sans erreur.

US **frontend-only** : endpoints existants (`createFolder`, `renameFolder`,
`deleteFolder`, `getMailboxQuota` — Angular `mss-api.service.ts:246-292/187`).
Aucun changement backend ni DTO.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `MssApiService` : 4 méthodes + tests unitaires (succès + erreur)
- [ ] Création de dossier (racine + sous-dossier) → apparaît dans l'arbre sans rechargement complet
- [ ] Renommage + suppression **réservés aux dossiers Custom** ; aucun menu sur les dossiers système (testé)
- [ ] Suppression avec confirmation ; dossier non vide → comportement identique à Angular (message d'erreur serveur relayé proprement)
- [ ] Jauge quota en pied de volet : valeurs, seuils 80 % (ambre) / 90 % (rouge), cas « Quota non disponible »
- [ ] Tests de rendu : menu contextuel Custom vs système, jauge aux 3 états
- [ ] Libellés FR en dur ; `data-testid` sur bouton +, items de menu, jauge
- [ ] Aucune donnée de santé dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; ouvrir le volet dossiers
- Créer un dossier « Suivi » → visible dans l'arbre ; créer un sous-dossier sous « Suivi »
- Renommer « Suivi » → « Suivi 2026 » → l'arbre reflète le nom
- Déplacer un mail vers « Suivi 2026 » (action existante) → compteur OK
- Supprimer le sous-dossier → confirmation → disparu
- Vérifier qu'aucun menu contextuel n'apparaît sur Inbox/Envoyés/Corbeille
- Pied de volet : jauge quota affichée avec % ; comparer la valeur au client web

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité web (task-087)
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées — dossiers de la boîte du titulaire uniquement
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : opérations de dossier journalisées côté `api-mail` (canal existant)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-143-custom-folders-mailbox-quota — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-143-custom-folders-mailbox-quota

## Stitch design log

- Projet `client-mobile` (id `10088502293310567548`, MOBILE) — écran de référence
  **`mail-folder-list`** existant (id `8dfbb9fc7b7c49318ce15b77a660ac3b`, label
  `mail-folder-list`), réutilisé comme référence. Aucun nouvel écran généré
  (évite le piège doublon MCP). La jauge de quota est un sous-élément du volet
  dossiers, pas un écran autonome.
- Intent traduit en Ionic (pas de HTML collé) : section « Dossiers » + bouton « + »,
  menu contextuel par dossier Custom, jauge de quota en pied de volet.

## Develop log

- Repos touched : `client-mobile` (US mono-repo, frontend-only)
- DTOs published : no DTO change · Interop published : no interop change
- Commits :
  - client-mobile : `cfaf0bc` feat(mobile): dossiers personnalisés (CRUD) + jauge de quota (task-143)
- Local build / test : ✓ `npm run build` (0 erreur) · `npm test … ChromeHeadless` (**469 SUCCESS**, +31 vs baseline 438)
- Implémentation :
  - `mailbox-quota.model.ts` : miroir TS de `MailboxQuotaDto` (task-087).
  - `MssApiService` : `createFolder` (POST /folders), `renameFolder`
    (PUT /folders/{path}/rename), `deleteFolder` (DELETE /folders/{path}),
    `getMailboxQuota` (GET /account/quota). Endpoints backend existants, aucun
    changement contrat.
  - `mail-folder-item` : getter `isCustom`, output `folderMenu`, bouton `⋯`
    (rendu `@if (isCustom)`) + appui long (pointer + timer 450 ms + Haptics)
    **actif uniquement sur Custom** ; propagation récursive `onChildMenu`.
    Dossiers système/tags : aucun menu.
  - `mail-folder-list` : bouton « + » (création racine) en tête de section,
    `openFolderMenu` → ActionSheet (Nouveau sous-dossier / Renommer / Supprimer),
    saisie via AlertController, suppression avec confirmation, refresh de l'arbre
    via `getFolders` (pas de rechargement complet), erreurs serveur relayées en
    toast (`extractProblemDetail` — ex. dossier non vide) ; bascule sur Inbox si
    le dossier supprimé était sélectionné. Jauge `mss-mailbox-quota-widget`
    épinglée en pied (flex + margin-top:auto).
  - `mailbox-quota-widget` : jauge linéaire, seuils 80 % (ambre `#f59e0b` /
    texte `#b45309`) / 90 % (rouge `--ion-color-danger`), format FR (Go/Mo),
    borne 100 %, état « Quota non disponible » sur `available=false` **et** sur
    échec réseau (dégradation sans erreur).
- DOD self-check : build ✓ · tests ✓ · 4 méthodes API + tests succès/erreur ✓ ·
  création racine + sous-dossier ✓ · rename/delete réservés Custom (aucun menu
  système, testé) ✓ · suppression avec confirmation + erreur serveur relayée ✓ ·
  jauge 3 états + « non disponible » ✓ · libellés FR en dur + `data-testid`
  (new-folder-btn, folder-menu-*, mailbox-quota-*) ✓ · aucun jeton/donnée santé
  en log ✓. Comportement réseau (arbre MAJ sans reload) déféré au test manuel (HAG).
- Next step : /forge-simplify task-143

## Simplify log

- Repos passed : `client-mobile`
- Applied & committed : — (aucune simplification appliquée)
- No change : `client-mobile` — code frais déjà aligné sur les patterns existants
  (reuse appliqué d'emblée par /develop : `extractProblemDetail`, récursion
  `mail-folder-item`, pattern d'appui long emprunté à `mail-header`, jauge
  miroir du `mailbox-quota-widget` Angular). `formatFileSize.util` écarté à
  dessein (plafonne à Mo + décimale anglaise ; le quota exige Go + `fr-FR`,
  d'où le formateur privé — parité Angular task-087). Facto d'un directive
  d'appui long partagé (mail-header + mail-folder-item) = hors scope isolé de
  la task (règle 6) et risque de régression → non appliqué (quality-only,
  best-effort).
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ verts (inchangés depuis /develop — 469 SUCCESS)
- Next step : /lint-mobile task-143 (api-mail & client-angular non touchés → /sonar & /lint-angular skip)

## Lint mobile log

- Repo : `client-mobile` (feat/task-143-custom-folders-mailbox-quota)
- Baseline `ng lint` : **All files pass linting** — 0 error, 0 warning, 0 fixable
- Iterations : aucune (code frais conforme à `conventions/angular.md` — control
  flow natif `@if`/`@for`, sélecteurs `mss-`, libellés FR en dur, `data-testid`)
- Commit : aucun (rien à corriger)
- Next step : /review task-143

## Visual verify log

- Écrans capturés : 1 / 1 — aucun écran blanc, aucune erreur console — commit `3b3d0ba`

| Écran | Route | Référence Stitch | Capture | Verdict fidélité |
|---|---|---|---|---|
| mail-folder-list | /tabs/messages (menu Dossiers) | Stitch `mail-folder-list` (id `8dfbb9fc…`) | [`task-143/mail-folder-list.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/3b3d0ba72c45f8cd37b18ba6f677dcbb58861e91/e2e/screenshots/task-143/mail-folder-list.png) | Conforme « Clinical Precision » : en-tête « Dossiers » + bouton « + » bleu, dossiers système sans menu, dossier Custom « Suivi » avec chevron + menu ⋯, jauge de quota en pied (27,5 % niveau normal, « Utilisé 2,8 Go / 10 Go », format FR). Public Sans + primaire #005EB8, lignes 56 px. RAS. |

- Écrans non mappés (screens.json) : aucun
- APIs non mappées loguées : aucune (fixture quota `/api/v1/account/quota` + dossier Custom ajoutés à `folders.json`)
- Note outillage : `tools/visual-verify/capture.mjs` (route quota) + `fixtures/folders.json` (dossier Custom « Suivi » + sous-dossier) enrichis pour matérialiser le menu Custom et la jauge dans la capture.
- Next step : /review task-143

## PRs

- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/48 — label `awaiting-human-merge`

## Code Review Summary

- Verdict : **APPROVED** — 0 bloquant.
- Build ✓ (`npm run build` 0 erreur) · Tests ✓ (**469 SUCCESS**, +31 vs baseline 438) · `ng lint` All files pass · `/verify-visual` 1/1 (aucun écran blanc).
- **Correctness** : parité fidèle avec client-angular task-087 ; `encodeURIComponent` sur les chemins de dossier ; `takeUntilDestroyed(destroyRef)` correct hors contexte d'injection ; jauge borne le pourcentage à 100 % et dégrade en « non disponible » sur échec réseau.
- **Contrainte métier** : CRUD réservé aux dossiers `Custom` — aucun menu sur les dossiers système ni les tags (testé rendu + logique + appui long).
- **Security** : aucun secret, aucune donnée de santé en log ; toasts d'erreur via `extractProblemDetail` (RFC 7807).
- **Test coverage** : 31 tests (4 méthodes API succès/erreur, jauge 3 états + non disponible + échec réseau, menu Custom vs système, appui long Custom-only, orchestration create/rename/delete + refresh + fallback Inbox).
- **DOD** : tous items vérifiables par commande ✓ ; comportement réseau (arbre MAJ sans reload complet) déféré au test manuel humain (HAG).
- Qualité : /sonar skipped — api-mail non touché (US frontend-only).

## Merged

- Merged : 2026-07-11 (human-triggered `/merge --i-tested`)
- Squash commits :
  - client-mobile : `e9dea11` (PR #48 squash-merged & closed, remote branch deleted, local kept)
- develop CI : voir run ci-dessous (build-android ~3m30s, hors fenêtre 2 min — voir rapport)
