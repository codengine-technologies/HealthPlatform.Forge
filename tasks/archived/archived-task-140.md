# todo-task-140.md — Écran Paramètres mobile réel (fin du placeholder)

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Remplacer le placeholder « Bientôt disponible » de l'onglet **Paramètres** par
un écran de préférences réel, adapté du `mss-settings` Angular aux usages
mobiles. Les réglages spécifiques desktop (position du volet, config serveur
IMAP/SMTP, full-sync) sont **exclus** ; le mobile expose :

- **Identité expéditeur** (nom affiché à l'envoi) — lecture/édition
- **Organisation** : dossier par défaut à l'ouverture, filtre inbox par défaut
  (Tous/Non lus), **mode conversation** par défaut (Liste/Conversation)
- **Recherche** : sensibilité (`minSimilarity` — le `SearchSettingsService`
  mobile existe déjà mais n'a aucune UI)
- **Notifications in-app** : toggles (nouveaux mails, biologie anormale)
- **Lecture** : taille max PJ affichée (lecture seule, valeur serveur)
- **Compte** : adresse MSSanté (lecture seule), bouton **Déconnexion** (existant, conservé)
- **À propos** : version de l'app

US **frontend-only** : `getUserSettings` / `saveUserSettings` existent
(Angular `mss-api.service.ts:624/638`) avec sauvegarde auto debouncée (300 ms).
Aucun changement backend ni DTO. Les préférences déjà persistées côté serveur
(mode conversation, dossier par défaut…) sont **partagées** avec le client web —
un réglage posé sur mobile s'applique au web et réciproquement (même DTO).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Placeholder remplacé : sections Identité / Organisation / Recherche / Notifications / Compte / À propos
- [ ] `MssApiService` : `getUserSettings` + `saveUserSettings` + tests (succès + erreur)
- [ ] Sauvegarde auto debouncée (300 ms) — testée avec timers fake ; toast discret de confirmation
- [ ] Le mode conversation par défaut et le filtre inbox par défaut sont **appliqués** à l'ouverture de l'inbox
- [ ] La sensibilité de recherche alimente `SearchSettingsService` (branchement effectif)
- [ ] Les toggles notifications pilotent réellement les toasts SSE in-app
- [ ] Déconnexion conservée avec confirmation
- [ ] Libellés FR en dur ; `data-testid` sur chaque contrôle
- [ ] Aucune donnée de santé dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; ouvrir l'onglet **Paramètres**
- Modifier l'identité expéditeur → envoyer un mail → le libellé expéditeur reflète le réglage
- Passer le mode par défaut en « Conversation » → tuer/relancer l'app → l'inbox s'ouvre en Conversation
- Régler le filtre par défaut sur « Non lus » → l'inbox s'ouvre filtrée
- Désactiver les notifications nouveaux mails → recevoir un mail de test → pas de toast ; réactiver → toast
- Vérifier sur le client web Angular qu'un réglage partagé (mode conversation) a bien suivi
- Déconnexion → confirmation → retour `/login`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — écran de préférences, parité partielle web
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : session existante ; la déconnexion purge les tokens locaux (comportement existant conservé)
- **Habilitations** : inchangées — settings cloisonnés par praticien (backend task-023)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : sauvegarde des préférences via l'endpoint existant ; déconnexion déjà tracée côté serveur
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — préférences stockées côté serveur ; pas de donnée de santé persistée sur l'appareil
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-140-mobile-settings — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-140-mobile-settings

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | settings (page Paramètres réelle) | settings | 34d145c4e04d48ebab80ff05afb709af | **created** (timeout MCP attendu, matérialisé au diff get_project ~4 min) | https://lh3.googleusercontent.com/aida/AP1WRLv8dvW9zDlnXtt0Bppb1fZp9tdBRlaiOtEFd18upLJzy0dk8ys6sUOPlNELjNDavwEWjVNQT1HBPEHzI17cpHvTwJZyDN-JAYx-f8kNu-WuKYv2g5Cw3ss26I64Poagj3tue9-x1yMQnzD7WKHeh5V91aYBUNKLREA3ddwQK0TK9728ys85uK1TFwW_HG5g5ulRVfys9MvKhoZdk3J2cVP03Du_Y_9DKM1HQyBhzYOFJGNcpk9ODTwsTuI |
- Structure de référence (HTML téléchargé, scratchpad `stitch-settings.html`) : header titre « Paramètres » ; profil (avatar + nom + sous-titre session) ; sections sur cartes blanches `rounded-xl` bord `outline-variant`, en-têtes `label-md` MAJUSCULES : IDENTITÉ (input « Nom affiché à l'envoi ») / ORGANISATION (ligne « Dossier à l'ouverture » + segmentés « Filtre par défaut » Tous·Non lus et « Affichage par défaut » Liste·Conversation) / RECHERCHE (slider + valeur % en primary bold) / NOTIFICATIONS (toggles « Nouveaux messages », « Biologie anormale ») / LECTURE (ligne lecture seule « Taille max des pièces jointes — 10 Mo ») / COMPTE (adresse MSSanté + bouton Déconnexion rouge outline pleine largeur) / À PROPOS (caption « Version x.y.z ») ; rangées min 56 px, séparateurs 1 px ; tab bar Messages/Patients/Paramètres (actif).
- ⚠ Rename / labelliser in Stitch UI : none — titre exact `settings` obtenu ; labelliser l'instance 34d145c4e04d48ebab80ff05afb709af est un plus.
- 📌 Bonus : la génération `mail-draft-list` de task-139 (réputée « non matérialisée ») a fini par atterrir — écran f9001616b2064b4a837a61e37a053345, titre exact `mail-draft-list`. Le run manuel noté dans archived-task-139 n'est plus nécessaire ; labelliser l'instance dans l'UI.
- ⚠ Doublons suspectés à nettoyer dans l'UI : inchangé (instances hidden de task-137 déjà signalées)
- Stitch reachable : ✓

## Develop log

- Repos touched : client-mobile (US frontend-only)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - client-mobile : 5678615 feat(mobile): écran Paramètres réel — préférences partagées, auto-save 300 ms, défauts inbox, gating notifications (task-140)
- Local build / test : ✓ `npm run build` 0 erreur ; `npm test -- --watch=false --browsers=ChromeHeadless` 399/399 SUCCESS (+32)
- DOD self-check : 11/11 items vérifiables vérifiés
  - build ✓, tests ✓ ; placeholder remplacé par les 7 sections (Identité / Organisation / Recherche / Notifications / Lecture / Compte / À propos) ✓ ; `MssApiService.saveUserSettings` ajouté (POST /api/v1/Settings, miroir Angular) + tests succès/erreur pour get et save ✓ ; auto-save debouncée 300 ms dans le nouveau `UserSettingsService` (store racine signals) testée fakeAsync (tick 299/1, POST unique, statuts saving→saved→idle) + toast discret « Préférences enregistrées » ✓ ; mode conversation + filtre par défaut APPLIQUÉS à l'ouverture de l'inbox (consommés une fois par session, testés) et dossier d'ouverture préféré (repli INBOX, testé) ✓ ; sensibilité → `SearchSettingsService` (slider + hydratation au load serveur, testés) ✓ ; toggles notifications gardent `handleNotification` (toast + insertion coupés, testés) ✓ ; déconnexion conservée verbatim (confirmation AlertController, testée) ✓ ; FR en dur + data-testid sur chaque contrôle (display-name, default-folder, default-filter, default-viewmode, search-similarity, notif-newmail, notif-biology, max-attachment, account-address, logout-btn, about-version, load-error/retry) ✓ ; aucun contenu santé loggé (0 console.*) ✓
  - validation visuelle end-to-end : deferred to manual test (HAG)
- Choix documentés :
  - **DTO partagé préservé** : le mobile ne type qu'un sous-ensemble de `UserSettingsDto`, mais toute mutation repart de l'objet chargé (spread) → les champs desktop non typés (thème, densité, volet, IMAP/SMTP, full-sync…) transitent tels quels au POST (testé). Aucune sauvegarde tant que le GET n'a pas réussi (un POST from scratch écraserait les réglages web) → état d'erreur + Réessayer sur l'écran.
  - **Nom affiché** : champ unique (réf. Stitch) mappé sur `senderIdentity.firstName/lastName` (split au 1er espace, type Personnel) — même DTO que le web ; appliqué à l'envoi via `from.name` (`OutgoingMailDto`). Limite connue : le chemin `sendDraft` (SaveDraftDto sans `from`) ne transporte pas le nom — gap contrat existant, noté pour un éventuel follow-up backend.
  - **Enums serveur ≠ enums mobiles** : `SettingsInboxFilter`/`SettingsMailViewMode` (int serveur) distincts des enums string locaux ; mapping aux frontières (`inboxFilterFromSettings`, « Lus » sans équivalent mobile → Tous).
  - **Préférence de notification absente = toasts actifs** (comportement historique conservé, pas de coupure silencieuse) ; défauts appliqués une seule fois par session (les bascules manuelles priment aux retours d'onglet).
  - `mail-compose` migré sur le store partagé (suppression du GET settings dupliqué) ; version app via `environment.appVersion` (aligné package.json).
- Next step : /forge-simplify task-140

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 7 files (bb73937)
  - efficiency : GET /Settings et GET /folders parallélisés à l'entrée de l'inbox (prefetch passé à `loadFolders` — 2 RTT séquentiels → 1 à la première entrée de session)
  - simplification : machine d'états `saveStatus` (4 états + timer de reset) remplacée par l'émission one-shot `saved$` (seule transition observée — le toast) ; alias `as prefs` inutilisé supprimé ; les 2 handlers de toggles notifications fusionnés en `onNotificationToggle(key, event)`
  - reuse : `maxAttachmentLabel` passe par l'util partagé `formatFileSize` (même formatteur que la jauge du compose — « 10.0 Mo » homogène)
  - altitude : transformations nom affiché ↔ `SenderIdentityDto` extraites en utils purs de modèle (`senderIdentityFromDisplayName` / `getSenderDisplayName` dans user-settings.model.ts, précédent patient.model.ts) — le store n'orchestre plus que le cycle load/mutate/save
- No change (skips motivés) : `ensureFoldersLoaded` partagé (alt — MailStateService reste un state container sans IO, parité Angular ; abstraction à consommateur unique, notée si un 3e appelant apparaît) ; parallélisation settings/folders côté page Paramètres (eff — fetch gaspillé en cas d'échec, gain 1 RTT rare) ; logout dupliqué inbox/settings (préexistant, hors diff — bon candidat de hoisting futur) ; prédicat `shouldNotify(kind)` (2 ifs lisibles) ; helpers segments (gain nul)
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ `npm run build` 0 erreur ; 399/399 tests SUCCESS

## Lint mobile log
- Baseline : 5 errors / 0 warning — `@angular-eslint/template/prefer-control-flow` (settings.page.html, *ngIf/*ngFor introduits par la task)
- Iteration 1 : `npm run lint -- --fix` — 0 fix (règle sans fixer)
- Iteration 2 : conversion manuelle en control flow natif `@if` / `@for (… ; track folder.path) @empty` — pur refactor de template
- Final : 0 error / 0 warning — « All files pass linting »
- Fixes committed : settings.page.html (1 file)
- Residual : none
- Build / tests : ✓ `npm run build` 0 erreur ; 399/399 tests SUCCESS

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/44 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 blocking)
- Review indépendante « second développeur », diff complet vs origin/develop (tous fichiers lus + code adjacent)
- Points validés : passthrough des champs desktop non typés au POST (chaque mutation spread l'objet chargé, refus tant que null → le POST est toujours un superset de l'objet serveur) ; `ensureLoaded` once-guard avec retry sur échec ; debounce 300 ms + `switchMap` corrects pour un remplacement whole-object (annulation sans perte, `saved$` sur le POST gagnant) ; gating notifications `?? true` (absent = actifs) ; parallélisation settings/folders sans course sur le dossier préféré ; garde d'édition sur échec de chargement (pas de POST from scratch) ; déconnexion conservée verbatim ; specs jugées signifiantes (frontière 299/1 ms, préservation champs non typés, once-per-session, gating on/off, split du nom, garde from-scratch)
- Suggestions non bloquantes : (1) asymétrie dossier (ré-appliqué à chaque entrée, parité comportement antérieur) vs filtre/mode (une fois par session) — choix défendable, à éyeballer au HAG ; (2) surbrillance `ion-segment` à valeurs numériques à confirmer sur device ; (3) cache settings non purgé au logout (neutralisé par le full reload du login, pattern MailStateService identique)
- Validation finale : build ✓ (0 erreur), 399/399 tests ✓, lint ✓ (0 erreur)
- Commits : 5678615 (feat), bb73937 (refactor /simplify), 294bda2 (refactor lint)

## Visual verify log
- Run rétroactif (première mise en service de /verify-visual, montée pendant task-140) — commit captures : 432cb5b (liens pinnés au SHA)
- Écrans capturés : 2 / 2 — aucun écran blanc, 0 erreur console
| Écran | Route | Référence Stitch | Capture | Verdict fidélité |
|---|---|---|---|---|
| settings | /tabs/settings | [référence](https://lh3.googleusercontent.com/aida/AP1WRLv8dvW9zDlnXtt0Bppb1fZp9tdBRlaiOtEFd18upLJzy0dk8ys6sUOPlNELjNDavwEWjVNQT1HBPEHzI17cpHvTwJZyDN-JAYx-f8kNu-WuKYv2g5Cw3ss26I64Poagj3tue9-x1yMQnzD7WKHeh5V91aYBUNKLREA3ddwQK0TK9728ys85uK1TFwW_HG5g5ulRVfys9MvKhoZdk3J2cVP03Du_Y_9DKM1HQyBhzYOFJGNcpk9ODTwsTuI) | [`task-140/settings.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/432cb5bd25a7d75e159e08cf2ce7e095ce65f91f/e2e/screenshots/task-140/settings.png) | Fidèle à la référence : sections sur cartes blanches arrondies, en-têtes label-md majuscules, segments Tous/Non lus et Liste/Conversation **avec surbrillance primaire fonctionnelle** (lève le doute n°2 de la code review), slider avec % en bleu gras, toggles, tab bar active. Écarts connus et assumés : pas de bloc profil/avatar, déconnexion en section Compte uniquement (sous le fold de la capture avec Lecture/À propos). |
| inbox | /tabs/messages | — (écran antérieur, non re-généré) | [`task-140/inbox.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/432cb5bd25a7d75e159e08cf2ce7e095ce65f91f/e2e/screenshots/task-140/inbox.png) | Rendu sain : filtres, bascule Liste/Conversation, chip bio, badges Document médical/Biologie (rouge), pastille non-lu, flag, trombone, FAB, fin de liste — cohérent Clinical Precision. |
- Écrans non mappés (screens.json) : aucun
- APIs non mappées loguées : flux SSE (corrigé dans capture.mjs — servis en event-stream vide)

## Merged
- Date : 2026-07-07
- `client-mobile` : squash `3f88474` — PR #44 closed (https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/44)
  - CI fix folded in : `d25f379` (add `appVersion` to `environment.local.ts` — unblocked `build-android` on the `local` config used by CI)
- Remote branch `feat/task-140-mobile-settings` deleted ; local branch kept.
- develop CI run : https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/28899705308
