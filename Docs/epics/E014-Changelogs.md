# E014 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Vue produit** : [E014-design-system-mobile-stitch.md](E014-design-system-mobile-stitch.md)
> **Dernière mise à jour** : 2026-06-26

---

## Historique détaillé des changelogs

### v1.0 — Socle design system « Clinical Precision » (task-110)

- **Repo** : `client-mobile` (`Client/Mobile/`, Ionic 8 + Angular 20, plain Angular CLI)
- **Branche** : `feat/task-110-socle-design-system-stitch`
- **PR** : [#14](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/14) — **mergée** (squash `e225afa`) sur `develop` le 2026-06-23 (validation humaine `--i-tested`)
- **Commits** :
  - `29ff95c` feat(mobile): socle design system Stitch « Clinical Precision » (task-110)
  - `c82125d` feat(mobile): force light-canonical theme — apply brand colors regardless of OS dark mode (task-110)
- **Mode clair canonique** : suite au constat « aucun changement visible » (les couleurs
  de marque étaient écrasées par la palette `dark.system.css` d'Ionic quand l'OS est en
  sombre — primary forcé à #4d8dff), l'import `dark.system.css` a été retiré, le bloc
  `@media (prefers-color-scheme: dark)` supprimé, et `color-scheme: light` posé (variables.scss
  + index.html). L'identité de marque s'applique désormais quel que soit le thème OS.
  Rappel : le défaut Ionic 8 (primary #0054e9) est déjà proche → l'écart visuel du socle
  reste discret ; la transformation visible viendra des refontes écran par écran (task-111..130).
- **Dépendance ajoutée** : `@fontsource/public-sans@^5` (poids 400/600/700, woff2 locaux)
- **Fichiers** :
  - `angular.json` — ajout des CSS `@fontsource/public-sans/{400,600,700}.css` aux
    tableaux `styles` des cibles build + test (bundle local, url() résolus, pas de CDN)
  - `src/theme/variables.scss` — tokens « Clinical Precision » → variables Ionic
    (`--ion-color-primary` #005EB8 + `-rgb`/`-contrast`/`-shade` #0052a2 /`-tint` #1a6ebf,
    `--ion-color-danger` #BA1A1A, `--ion-color-secondary` #5a5f62, `--ion-color-tertiary`
    #920d00, `--ion-background-color` #f9f9fc, `--ion-text-color` #1a1c1e,
    `--ion-font-family` Public Sans) + tokens applicatifs `--app-*` (espacements 8px,
    formes `--app-radius` 4/8/12px, `--app-elevation-overlay`, `--app-list-row-min-height`
    56px, `--app-touch-target` 44px, échelle typo `--app-type-*`) + bloc
    `@media (prefers-color-scheme: dark)` remappant les surfaces `--app-*`
  - `src/global.scss` — application transverse : `body` Public Sans, classes
    utilitaires `.app-text-*`, `ion-item --min-height` 56px + séparateurs
    `--app-outline-variant`, `ion-button` radius + min-height 44px, `ion-chip`
    radius + typo label, `ion-card` radius 8px, `ion-input/ion-textarea/ion-searchbar`
    fond `--app-surface-alt`, `ion-modal/ion-popover` élévation `--app-elevation-overlay`,
    `ion-avatar` rond
  - `package.json` / `package-lock.json` — dépendance fontsource
- **Validation** :
  - `npm run build` : ✓ (warning budget pré-existant `mail-header.component.scss`
    2.14 kB > 2 kB — hors socle, non introduit par cette task)
  - `npm test -- --watch=false --browsers=ChromeHeadless` : ✓ 108/108
  - `npm run lint` : ✓ « All files pass linting » (le diff ne touche que scss/json,
    non lintés par ESLint)
- **Code review** : APPROVED — 0 bloquant, 1 suggestion (`letter-spacing` répété entre
  `.app-text-label-md` et `ion-chip`, nécessaire vu le shorthand CSS `font:`)
- **Forge-simplify** : aucune édition — socle purement déclaratif (tokens centralisés,
  réutilisés via `var()`, aucune duplication ni logique)
- **Portée** : socle thème uniquement ; la refonte structurelle écran par écran est
  déléguée aux task-111..130. Aucune logique ni donnée de santé touchée.

---

### v1.1 — Refonte écran login (task-111)

- **Repo** : `client-mobile` · **Branche** : `feat/task-111-refonte-login-stitch`
- **PR** : [#15](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/15) — **mergée** (squash `9a88a01`) sur `develop` le 2026-06-23 (`--i-tested`)
- **Commits** (branche) : `98f32d2` refonte login → `ce8eebe` align primary/rayons export →
  `fbb7e62` lien alt → `60e5e8c` assets WEDA+PSC → `48e12fe` logo WEDA vectorisé SVG
- **Fidélité export Stitch** : sur retour humain, alignement sur `code.html`/`DESIGN.md` —
  primary `#00478d` (+ `--app-primary-container #005eb8`, amende le socle task-110), rayons
  (logo carré arrondi 0.75rem, bouton 0.5rem, bannière 0.25rem), logo WEDA reproduit en
  **SVG vectoriel** (`weda-logo.svg`, ~91% du bitmap, navy #064475), bouton officiel ANS
  `psc-connect-button.svg` (fond #000091) utilisé tel quel, lien « Autre moyen de connexion ».
- **Fichiers** : `src/app/login/login.page.html`, `src/app/login/login.page.scss`
- **Référence Stitch** : écran `login` (id 84fe1a8c764344509857ef06a1696adc) réutilisé
- **Changements** : header de marque « lock MSSanté », fond clair, logo en disque + halo,
  titres centrés, bouton PSC primaire ancré bas + mention ANS, bannière session-expirée
  en rouge doux (token danger). 100% tokens du socle, `data-testid` sur le bouton PSC.
- **Écart assumé** : lien « Autre moyen de connexion » omis (pas d'autre moyen d'auth câblé) ;
  icône Ionic `mail` dans le disque (pas d'asset WEDA importé).
- **Validation** : build ✓, 108/108 tests ✓, lint ✓. Code review APPROVED (0 bloquant).

---

### v1.2 — Refonte écran authentication (task-112)

- **Repo** : `client-mobile` · **Branche** : `feat/task-112-refonte-authentication-stitch`
- **PR** : [#16](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/16) — **mergée** (squash `f6f1170`) sur `develop` le 2026-06-23 (`--i-tested`)
- **Commit** : `e78d09f`
- **Stitch** : écran `authentication` synchronisé via `edit_screens` (« HIPAA »→« ANS »)
- **Fichiers** : `authentication.page.{html,scss,ts}` (ajout `styleUrls`)
- **Référence Stitch** : écran `authentication` (id 87324d3e550b41debfeef8a162f1b56e) réutilisé
- **Changements** : header marque centré, état chargement (spinner + textes), état erreur
  (icône + titre + message dynamique + Réessayer/Annuler), footer réassurance sécurité.
  Logique de callback PSC inchangée. Adaptation « HIPAA »→« ANS » (conformité FR).
- **Validation** : build ✓, 108/108 tests ✓, lint ✓. Code review APPROVED.

---

### v1.3 — Tableau de bord d'accueil `home` (task-113)

- **Repo** : `client-mobile` · **Branche** : `feat/task-113-refonte-home-stitch`
- **PR** : [#17](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/17) — **mergée** (squash `cfffcc1`) sur `develop` le 2026-06-23 (validation humaine `--i-tested`)
- **Commit** (branche) : `feat(mobile): dashboard d'accueil home miroir Angular MSS (task-113)`
- **Stitch** : écran `home` → « Dashboard Accueil » (id 83399bfa940a4e36ba56d66e3b210e76) créé via `edit_screens`. Housekeeping Stitch restant (UI humaine, MCP sans rename/delete) : renommer en `home`, supprimer l'ancien écran générique (id 8c3d240e346f42f8a4bbd55c57f98a70).
- **Objet** : transformation de l'écran `home` (placeholder orphelin du starter Ionic, non routé) en tableau de bord d'accueil **landing post-login**, miroir colonne unique du dashboard Angular MSS (`mss-dashboard`). Agrégation **client-side** de l'état mail INBOX, aucun changement backend/dtos.
- **Fichiers** :
  - `src/app/home/home.page.ts` — agrégation : résolution dossier INBOX (`getFolders`/`getFolder`), counts Total/Non lus, échantillon des 30 UID les plus récents (`getEmails`) pour le résumé « du jour » (filtre `!isRead && isToday(sentDate)`, top 5) + agrégats bio d'affichage (`hasCriticalPendingBiologyAck`, `hasAbnormalBiology`), count d'acquittement exact via `getBiologyAckPendingMailUids` (best-effort, non bloquant). Helpers `senderName`/`initials`/`isToday`/`sentTime`. Chargement sur `ionViewWillEnter`, pull-to-refresh.
  - `src/app/home/home.page.html` — header marque « lock MSSanté », section Messagerie (3 stat cards + CTA `goToInbox`), résumé non lus du jour (`@for`/`@if`, état vide), section Biologie (2 tuiles → `/inbox`). `data-testid` sur tous les interactifs.
  - `src/app/home/home.page.scss` — 100% tokens du socle (task-110). Réduit pour respecter le budget anyComponentStyle 4 kB (suppression de déclarations redondantes `cursor:pointer`/`text-align` sur boutons) ; reste un warning budget 2 kB (sous le seuil error 4 kB).
  - `src/app/home/home.page.spec.ts` — 8 tests (agrégation stats + résumé, rendu DOM sections, état vide sans appel `getEmails`, nav inbox/détail, erreur réseau + reset, résilience panne count bio, initiales/expéditeur).
  - `src/app/app-routing.module.ts` — route `home` (lazy `HomePageModule`).
  - `src/app/login/login.page.ts` — `loginPsc('psc', '/home')` (landing dashboard).
  - `src/app/core/auth/auth.service.ts` — défaut `loginPsc` + fallback `consumeReturnUrl` → `/home`.
- **Hors périmètre (assumé)** : widget « Patients avec mails non lus » (identité patient non en liste, garde-fou INS) → US backend ultérieure ; nav latérale Angular (écrans inexistants côté mobile) ; tag cloud.
- **Limite résiduelle** : compteurs bio critiques/anormaux dérivés de l'échantillon récent (30 derniers UID), pas de l'inbox entière — approximation d'affichage ; comptage exact = endpoint dashboard backend (différé).
- **Validation** : `npm run build` ✓ (warning budget scss home 2 kB, sous le seuil error 4 kB), `npm test` ✓ **116/116**, `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean (rien de matériel ; `MailStateService` non réutilisable pour une landing — signals vides tant que l'inbox n'a pas été ouvert).
- **Code review** : APPROVED — 0 bloquant, 1 suggestion (approximation bio sample-based, documentée). Aucune INS / donnée de santé en clair.

---

### v1.4 — Refonte écran inbox (task-114)

- **Repo** : `client-mobile` · **Branche** : `feat/task-114-refonte-stitch-inbox`
- **PR** : [#18](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/18) — **mergée** (squash `a06157f`) sur `develop` le 2026-06-24 (validation humaine `--i-tested`)
- **Commit** (branche initiale) : `9aa3ae5` feat(mobile): refonte structurelle de l'écran inbox (Stitch Clinical Precision)
- **Objet** : refonte **structurelle** de l'écran central `inbox` (page hôte mince). Refactor HTML/SCSS, complété en session par une mise en conformité Stitch haute-fidélité (cf. extension ci-dessous).
- **Extension session 2026-06-24** (MCP Stitch rétabli — maquettes `inbox-updated-nav` + `inbox-biology-abnormal`) : commits `0f8e433` / `07c95e4` / `d6d57bc` / `e095338` ajoutent : (1) **valeurs de biologie inline** dans `mss-mail-header` (résultats flaggés `Nom : valeur unité (code)`, gravité critique LL/HH/AA → `--ion-color-tertiary`, anormale L/H/A → danger, bandeau urgence ; helpers `isCriticalBio`/`isAbnormalBio`/`getBioIcon`/`getBioLevel` transposés de client-angular) ; (2) **regroupement de liste** `mss-mail-list` « BIOLOGIE À VALIDER (HORS NORMES) » + « AUTRES MESSAGES » (computed OnPush sur `hasAbnormalBiology`/`hasCriticalPendingBiologyAck`, ligne factorisée `ngTemplateOutlet`) ; (3) **barre de navigation `ion-tabs`** Messages/Patients/Paramètres (`src/app/tabs/` + placeholders `src/app/patients/`, `src/app/settings/` ; restructure routing : parent `tabs` + `authGuard`, redirect `/inbox → /tabs/messages`, mail-detail plein écran hors onglets) ; (4) **filtres + toggle vue en pilule iOS** (`mode="ios"`, filtre pleine largeur visible + toggle compact à droite de Bio à acquitter) ; (5) tokens `--app-error-container`/`--app-on-error-container`. Tests **128/128** après extension.
- **Fichiers** :
  - `src/app/inbox/inbox.page.html` — toolbar épurée (déconnexion `ion-button fill="clear"` + `ion-icon log-out-outline`, `aria-label` préservé) ; nouvelle **zone de contrôles épinglée** `.inbox-controls` regroupant `mss-mail-search` + `.inbox-controls-row` (segment filtre `inbox-filter` Tous/Non lus/Flaggés + segment `inbox-viewmode` liste/conversation avec `aria-label`) + `mss-inbox-biology-ack-chip` conditionnel ; bloc erreur relocalisé sous les contrôles ; FAB `compose-new` classé `.inbox-compose-fab`. Tous les `data-testid` préservés (folders-menu-btn, logout-btn, inbox-filter, inbox-viewmode, compose-new, inbox-infinite, inbox-end, inbox-error, inbox-retry).
  - `src/app/inbox/inbox.page.scss` — 100 % token-driven (`theme/variables.scss`) : `.inbox-toolbar` (surface, séparateur `--app-outline-variant`, titre `--app-type-title-lg`), `.inbox-controls` (`position: sticky`, fond `--app-surface`, gap/padding via `--app-space-*`/`--app-margin`), segments fond `--app-surface-container`, `.inbox-error` radius `--app-radius-lg`, `.inbox-end` `--app-type-caption`, `.inbox-compose-fab` plein `--ion-color-primary` + élévation `--app-elevation-overlay`. Aucune valeur de design en dur.
- **Référence Stitch** : ⚠ **non créée** — le **MCP Stitch n'est pas connecté** dans la session forge (seul l'outil claude.ai DesignSync, hors périmètre, est exposé). La création MCP de l'écran `inbox` avait déjà échoué en timeout le 2026-06-23. La refonte a donc été codée contre les **tokens du socle** (task-110) + la spec structurelle de la task. Fallback restant côté humain : créer `inbox` dans l'UI Stitch puis consigner la comparaison visuelle (items DOD différés HAG).
- **Validation** : `npm run build` ✓ (warnings budget scss pré-existants home/login/mail-header, hors scope), `npm test -- --watch=false --browsers=ChromeHeadless` ✓ **116/116**, `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean — diff déjà token-driven, `.inbox-toolbar` réutilisée sur les deux toolbars, composants enfants réutilisés (search/list/bio-chip/folder-list), aucun gain reuse/simplif/efficacité/altitude matériel.
- **Lint-mobile** : skip clean — baseline `ng lint` 0 erreur (diff HTML/SCSS uniquement).
- **Code review** : APPROVED — 0 bloquant. Refactor pur, bindings/handlers tous préservés, error/bio-chip conditionnels intacts, a11y améliorée (aria-labels). Aucune INS / donnée de santé en clair.

---

### v1.5 — Refonte menu des répertoires `mail-folder-list` (task-116)

- **Repo** : `client-mobile` · **Branche** : `feat/task-116-refonte-stitch-mail-folder-list`
- **PR** : [#19](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/19) — **mergée** (squash `71aedf5`) sur `develop` le 2026-06-24 (validation humaine `--i-tested`)
- **Commit** (branche) : `735d25d` feat(mobile): refonte Stitch du menu des répertoires (mail-folder-list)
- **Objet** : refonte structurelle du menu latéral des répertoires (`mss-mail-folder-list` / `mss-mail-folder-item`) d'après la maquette Stitch `mail-folder-list`. Refactor HTML/SCSS/TS — aucun changement de flux fonctionnel.
- **Fichiers** :
  - `mail-folder-item.component.ts` — getters `iconName` (switch sur `FolderType` : Inbox→`file-tray-outline`, Sent→`paper-plane-outline`, Drafts→`document-outline`, Trash→`trash-outline`, Junk→`warning-outline`, Important→`star-outline`, défaut `folder-outline`/`archive-outline` sur heuristique nom), `isTag` (`FolderSource.Tag`), `tagColor` (repli `#6b7280`).
  - `mail-folder-item.component.html` — 3 branches slot start (chevron si enfants / pastille tag colorée / icône type), classe `.folder-item--selected` (pilule), badge non-lus `.folder-unread-badge`. `data-testid` complétés (`folder-tag-dot-*`).
  - `mail-folder-item.component.scss` — pilule sélectionnée (`--app-surface-container`), icône/pastille/badge sombre (`--app-on-surface`), 100 % tokens.
  - `mail-folder-list.component.{ts,html,scss}` — exposition `tagFolders` (`MailStateService.tagFolders`), sections « Répertoires » (IMAP) + « TAGS » (pastilles colorées), en-têtes de section `.folder-section-header` ; passage `ion-list` → `div` (pilule mieux rendue hors `ion-list`).
  - `src/app/inbox/inbox.page.html` — en-tête du menu latéral « Répertoires » → brand « MSSanté ».
  - `mail-folder-item.component.spec.ts` — +6 specs (mapping icônes par type, heuristique archive, détection tag + couleur + repli, rendu pastille).
- **Référence Stitch** : écran `mail-folder-list` (id 84138523de2c40c1aa866c64bb5ef84d) **réutilisé** (MCP Stitch joignable).
- **Validation** : `npm run build` ✓, `npm test` ✓ **133/133**, `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean — diff token-driven, réutilise la récursion `mss-mail-folder-item` et `tagFolders`, `switch` propre ; factoriser les deux `@for` (IMAP/TAGS) via `ngTemplateOutlet` jugé sans gain matériel (altitude).
- **Lint-mobile** : skip clean — baseline `ng lint` 0 erreur.
- **Code review** : APPROVED — 0 bloquant. ⚠ 1 suggestion : sélection d'un dossier **tag** via le même flux `folderChanged$ → loadEmailsForFolder` que les IMAP (cohérent miroir client-angular) — à confirmer au test manuel. Aucune INS / donnée de santé en clair.

---

### v1.6 — Refonte liste des emails `mail-list` (task-115)

- **Repo** : `client-mobile` · **Branche** : `feat/task-115-refonte-stitch-mail-list`
- **PR** : [#20](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/20) — **mergée** (squash `7e27bd0`) sur `develop` le 2026-06-24 (validation humaine `--i-tested`)
- **Commit** (branche) : `25d9608` feat(mobile): refonte Stitch de la liste des emails (mail-list)
- **Objet** : reprise structurelle/visuelle de la ligne `mail-list` (rendue par `mss-mail-header`) + conteneur `mss-mail-list` d'après la maquette Stitch `mail-list`. Refactor présentation — logique TS inchangée, acquis task-114 (valeurs biologie inline, regroupement) préservés. Les internes profonds de `mail-header` (API @Input/@Output) restent du ressort de task-118.
- **Fichiers** :
  - `mail-header.component.scss` — **réécriture 100 % token-driven** : avatar **carré arrondi** (`--app-radius-lg`, `background --app-on-surface-variant`, `font --app-type-title-lg`), séparateur `--app-outline-variant`, fonds d'état (`--app-surface-container-low`/`--app-surface-container`), typographies `--app-type-body-md`/`-caption`/`-label-md`, hauteur `--app-list-row-min-height`, accent critique `.mail-row--critical` (`border-left --ion-color-tertiary`). Constantes dimensionnelles (40px avatar, 10px dot) + 1 teinte `rgba(146,13,0,0.08)` du chip bio-critical conservées.
  - `mail-header.component.ts` — getter `biologyChipLabel` (« Biologie CRITIQUE » si `hasCriticalPendingBiologyAck`, sinon « Biologie »).
  - `mail-header.component.html` — classe `mail-row--critical` (`hasCriticalBiology`), libellé chip = `biologyChipLabel`.
  - `mail-list.component.scss` — réponses de fil indentées plus claires (`--app-surface-container-low`, `--app-on-surface-variant`) + état vide, token-driven.
  - `mail-header.component.spec.ts` — +2 specs (label « Biologie CRITIQUE » critique vs normal, classe `mail-row--critical`).
- **Référence Stitch** : écran `mail-list` (id 09bc742258d14caabd40dc311ee04c24) **réutilisé**.
- **Validation** : `npm run build` ✓, `npm test` ✓ **135/135**, `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean — réécriture token-driven sans duplication, getter trivial, aucun gain matériel.
- **Lint-mobile** : skip clean — baseline `ng lint` 0 erreur.
- **Code review** : APPROVED — 0 bloquant. Présentation pure ; acquis biologie/regroupement task-114 intacts. Aucune INS / donnée de santé en clair.

---

### v1.7 — Item de répertoire actif `mail-folder-item` (task-117)

- **Repo** : `client-mobile` · **Branche** : `feat/task-117-refonte-stitch-mail-folder-item`
- **PR** : [#21](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/21) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `0a22c6b` feat(mobile): item de dossier actif en pilule bleue (mail-folder-item)
- **Objet** : reprise ciblée de l'**état sélectionné/actif** de `mail-folder-item` d'après la maquette Stitch dédiée. L'essentiel du composant (icônes par type, badge non-lus sombre, pastilles tag, arborescence/chevron) provenait déjà de **task-116** (le composant est la ligne du `mail-folder-list`) — non re-touché.
- **Fichier** :
  - `mail-folder-item.component.scss` — `.folder-item--selected` : fond `rgba(var(--app-primary-container-rgb), 0.1)` (pilule bleu clair), `--color` + `.folder-icon`/`.folder-name` = `--ion-color-primary`. Remplace le gris `--app-surface-container` posé par task-116.
- **Référence Stitch** : écran `mail-folder-item` (id 16124e44e18445249ab949869df222a8) **réutilisé**.
- **Nuance différée** (hors scope DOD « compteur non-lus ») : la maquette montre un compteur **total** grisé sur Brouillons (vs badge sombre des non-lus) — non implémenté pour éviter un affichage hors périmètre.
- **Validation** : `npm run build` ✓ (`rgba(var(...))` compile), `npm test` ✓ **135/135** (inchangé — diff SCSS pur), `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean — bloc SCSS unique token-driven, aucun gain.
- **Lint-mobile** : skip clean — diff SCSS, non linté ESLint.
- **Code review** : APPROVED — 0 bloquant. Aucune INS / donnée de santé en clair.

### v1.8 — Recherche avancée `mail-search` + historique de recherche (task-119)

- **Repos** : `dtos-mss`, `api-mail`, `client-mobile` (poussés) · `client-angular` (code-only) · Branche `feat/task-119-mail-search-history`
- **PRs** : dtos-mss [#25](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/25) · api-mail [#112](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/112) · client-mobile [#22](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/22) — toutes **ouvertes**, label `awaiting-human-merge` (HAG rule 10). client-angular : code-only, l'humain commit/push/PR TFS.
- **Commits** (branches) : dtos `7ff425e` · api-mail `eb3d707` · client-mobile `260a201`.
- **Objet** : changement **fonctionnel assumé** (l'ancien périmètre « restyling UI sans changement fonctionnel » est caduc). Recherche refondue en page dédiée + historique de recherche partagé, persisté côté backend.
- **dtos-mss** : `SearchHistoryEntryDto` (id Guid v7 + `SearchedAt` + `SearchRequestDto` rejouable), `SearchHistoryResponseDto`. Publié NuGet `337.0.0` ; consommateur `api-mail` bumpé (`335.0.0 → 337.0.0`).
- **api-mail** :
  - `ISearchHistoryService`/`SearchHistoryService` (`src/Application/Services/{Interfaces,Implementation}`) — clé Redis `mss:search-history:{email}` (email praticien lowercased/trimmed dans la clé → isolation RGPD), TTL **7 jours** posé sur `absolute` **et** `sliding` (le `CacheService` du Sdk force sinon un sliding 30 min qui éviterait l'historique), dédup par empreinte JSON, cap 20, **INS strippé** (minimisation), résilience cache via `SafeGet`/`SafeRemove` + `Set` gardé (task-074).
  - `SearchController` — enregistrement après recherche sémantique réussie ; `GET /api/v1/search/history` ; `DELETE /api/v1/search/history`. Aucun try/catch ad hoc → RFC 7807 via `GlobalExceptionHandler` (règle 12).
  - Tests : `SearchHistoryServiceTests` (14, in-memory `ICacheService` + capture TTL), `SearchControllerTests` (+4), `SearchHistoryServiceIntegrationTests` (3, `CacheService` réel sur `MemoryDistributedCache` — round-trip JSON, happy + clear-empty + isolation).
- **client-mobile** :
  - Page dédiée `src/app/mail-search/` (route `/mail-search` poussée au-dessus des onglets) hébergeant `mss-mail-search` + `mss-mail-search-history` + `mss-mail-list` (réutilisé).
  - `mss-mail-search` reconstruit (parité 100 % Angular) : Importants, type de doc (14), plage de dates (1/7/30/90 j → `sentDateFrom`), De/À/Objet ; `minSimilarity` lu de `SearchSettingsService` (localStorage, défaut 0.1) ; `replay()` restaure les critères + `inferDateRange`.
  - `mss-mail-search-history` (nouveau, nom aligné Angular) ; `inbox` : recherche inline retirée, icône loupe ajoutée ; `MssApiService.getSearchHistory`/`clearSearchHistory`.
  - Tests : 148 verts (mail-search 10, mail-search-history 6, mail-search.page 3 + existants). Lint ESLint 0 erreur.
- **client-angular** (code-only) : `search.model.ts` (DTOs), `mss-api.service.ts` (2 endpoints), `mail-search.component.ts` (`replay()` + `inferDateRange`), `mail-search-history/` (nouveau `mss-mail-search-history`), `mail-list` (viewChild + `onReplaySearch` + stub spec). AOT dev build `nx build mss` ✓ ; `nx lint mss-lib --fix` → 0 erreur ; `nx test mss-lib` 299 verts. **2 échecs PRÉ-EXISTANTS** hors scope dans `mail-list.component.spec` (bloc task-036) : `new MailListComponent()` lève `NG0201 MailDestinationRefreshService` (provider manquant **déjà au HEAD** de `feature/nova-rewriting-mss`).
- **Référence Stitch** : écran `mail-search` (id fd767eca895f41b1b30a8bc932cf40cf) **réutilisé** (section « Recherches récentes » + « Effacer » + lignes historique avec rejeu).
- **Forge-simplify** : skip clean — code déjà reuse-clean (`mail-list`, `SafeCacheExtensions`, `extractProblemDetail`, tokens E014).
- **Sonar** : skip best-effort — infra non provisionnée (`SONAR_TOKEN` absent, `localhost:9000` injoignable).
- **Code review** : APPROVED — 0 bloquant. Scope praticien isolé, minimisation INS, pas de fuite donnée de santé en clair.

### v1.9 — Refonte `inbox-biology-ack-chip` + compteur (task-120)

- **Repo** : `client-mobile` · **Branche** : `feat/task-120-stitch-inbox-biology-ack-chip`
- **PR** : [#23](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/23) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `fc012d5` feat(mobile): Stitch restyle of inbox-biology-ack-chip + pending counter
- **Objet** : refonte « Clinical Precision » du chip de filtre acquittement biologie + ajout du **compteur** (parité client-angular `InboxBiologyAckChipComponent`, qui affiche le compte dans son libellé).
- **Fichiers** :
  - `inbox-biology-ack-chip.component.ts` — pilule token-driven (`--app-radius` 4px, `--app-type-label-md`, `--app-surface-alt` au repos, `--ion-color-tertiary` actif) ; `count` signal + `Bio à acquitter (N)` ; fetch déplacé en `ngOnChanges` (recharge par dossier) + cache `pendingUids` ; `toggle()` émet le cache ; `data-testid` complétés + `aria-pressed`.
  - `inbox-biology-ack-chip.component.spec.ts` — 5 tests (chargement compte, émission active/inactive, refetch sur changement de dossier, resync à chaud).
- **Correctif de régression évité** : l'ancien fetch lazy sur `toggle()` portait toujours sur le dossier courant ; en passant le fetch en `ngOnChanges`, le refetch sur changement de dossier garantit que le filtre rejoué reste scopé au bon dossier (sinon `toggle()` aurait émis le cache d'un dossier précédent).
- **Référence Stitch** : écran `inbox-biology-ack-chip` **créé** (id `e6222381e2204ccd9d45bd785fa15d93`) — les appels MCP ont timeouté côté client mais la génération a abouti côté serveur (confirmé au 2ᵉ essai). Implémenté d'après la spec design system (« Chips : 4px radius, Surface Alt, label-md ») ; comparaison visuelle conforme (deux états empilés, pilule 4px, accent tertiaire). Écart mineur assumé : la maquette n'affiche le compteur qu'à l'état actif, l'implémentation l'affiche aux deux états par parité client-angular.
- **Validation** : `npm run build` ✓ (warning budget pré-existant `home.page.scss` uniquement), `npm test` ✓ **151/151** (+3), `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean — composant unique token-driven, aucun gain.
- **Code review** : APPROVED — 0 bloquant. Aucune INS / donnée de santé en clair (compteur d'entiers uniquement).

### v1.10 — Refonte `mail-detail` (token-driven) (task-121)

- **Repo** : `client-mobile` · **Branche** : `feat/task-121-stitch-mail-detail`
- **PR** : [#24](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/24) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `8b8c9c8` feat(mobile): Stitch restyle of mail-detail (token-driven meta card)
- **Objet** : refonte « Clinical Precision » de la carte méta du visualiseur d'email. Structure de la maquette Stitch `mail-detail` (sujet → identité patient + INS → De/À/Date → barre d'actions → bandeau accusé → corps → PJ) **déjà alignée** avec le composant — la refonte est une migration SCSS pure.
- **Fichiers** :
  - `mail-detail.component.scss` — migration **100 % tokens E014** : `--app-type-title-lg/body-md/label-md/caption`, espacements `--app-space-*` (8px), `--app-radius-full`, surfaces `--app-surface-container-lowest`/`--app-surface-alt`, outlines `--app-outline-variant`, identité patient `--ion-color-primary`. Suppression des littéraux (`16/17/13/12/10px`, `#6b7280`, `var(--ion-color-step-100)`, `--ion-color-success-shade`).
  - `mail-detail.component.html` — chip de tag : fallback `tag.colorCode || null` (le défaut vient du token `--ion-color-medium` dans le SCSS) au lieu du `#6b7280` en dur.
- **Périmètre** : carte méta + barre d'actions + bandeau accusé uniquement. `mail-body`, `mail-attachment`, `biology` (composés par cet écran) restent du ressort de task-122/124/125.
- **Référence Stitch** : écran `mail-detail` (id 2ca2f78af2244d46a0f1c00cf6a1fe61) **réutilisé**.
- **Validation** : `npm run build` ✓ (warning budget pré-existant `home.page.scss` uniquement), `npm test` ✓ **151/151** (restyle SCSS pur, pas de delta), `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean — restyle SCSS, aucun gain.
- **Code review** : APPROVED — 0 bloquant. Structure & comportement inchangés ; aucune INS / donnée de santé en clair au-delà de l'affichage métier existant.

### v1.11 — Refonte `mail-body` (token-driven) (task-122)

- **Repo** : `client-mobile` · **Branche** : `feat/task-122-stitch-mail-body`
- **PR** : [#25](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/25) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `50028b6` feat(mobile): Stitch restyle of mail-body (token-driven)
- **Objet** : refonte « Clinical Precision » du corps de message — migration SCSS pure.
- **Fichier** : `mail-body.component.scss` — migration **100 % tokens E014** : `--app-type-body-md/caption`, espacements `--app-space-*`/`--app-gutter`, `--app-radius-lg`, surfaces `--app-surface-alt`, outlines `--app-outline-variant` ; `line-height: 1.6` pour les notes cliniques longues. Suppression des littéraux (`16/14/13/12px`, `8px radius`, `var(--ion-color-step-100)`, `var(--ion-color-light)`, `var(--ion-color-medium-shade)`).
- **Sécurité** : pipeline d'assainissement (`blockRemoteContent` + `mss-medical-html-frame`) **strictement inchangé** ; bannière images distantes restylée mais comportement de blocage identique.
- **Référence Stitch** : écran `mail-body` (id c9f8d3d5941e4fa097a6be64ace4a549) **réutilisé**.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151** (restyle SCSS pur, pas de delta), `npm run lint` ✓ « All files pass linting ».
- **Forge-simplify** : skip clean — restyle SCSS, aucun gain.
- **Code review** : APPROVED — 0 bloquant. Assainissement HTML intact ; aucune fuite de contenu MSSanté.

### v1.12 — Refonte `medical-html-frame` (token-driven) (task-123)

- **Repo** : `client-mobile` · **Branche** : `feat/task-123-stitch-medical-html-frame`
- **PR** : [#26](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/26) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `f0f93b7` feat(mobile): Stitch restyle of medical-html-frame (token-driven)
- **Objet** : refonte « Clinical Precision » du cadre d'affichage CDA.
- **Fichier** : `medical-html-frame.component.ts` (template + styles + tokens injectés inline) :
  - Template : iframe enveloppée dans un `.medical-html-frame` (carte bordée arrondie).
  - Styles : conteneur token-driven (`--app-outline-variant`, `--app-radius-lg`, `overflow: hidden`, `--app-surface-container-lowest`) ; iframe background tokenisé.
  - `wrapWithDesignTokens` : valeurs hex alignées Clinical Precision (`--mss-text-color #1a1c1e`, `--mss-primary-color #00478d`, surfaces `#f3f3f6/#eeeef0/#c2c6d4`) + pile **Public Sans** (les `--app-*` de l'hôte ne traversent pas le blob → valeurs auto-portées).
- **Sécurité** : `sandbox="allow-same-origin"`, `referrerpolicy="no-referrer"`, rendu via Blob + `bypassSecurityTrustResourceUrl`, isolation no-script et height-sync **strictement inchangés**. Contenu CDA inchangé.
- **Référence Stitch** : écran `medical-html-frame` (id a79637193fbe4ff1847dfeb290c5efdf) **réutilisé**.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151** (specs blob/url couverts), `npm run lint` ✓.
- **Forge-simplify** : skip clean — restyle, aucun gain.
- **Code review** : APPROVED — 0 bloquant. Mécanisme d'isolation préservé ; aucune fuite de contenu MSSanté.

### v1.13 — Refonte `mail-attachment` (token-driven) (task-124)

- **Repo** : `client-mobile` · **Branche** : `feat/task-124-stitch-mail-attachment`
- **PR** : [#27](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/27) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `b7785c3` feat(mobile): Stitch restyle of mail-attachment (token-driven)
- **Objet** : refonte « Clinical Precision » des lignes de pièces jointes — migration SCSS pure.
- **Fichier** : `mail-attachment.component.scss` — migration **100 % tokens E014** : `--app-type-label-md/body-md/caption`, espacements `--app-space-*`, surfaces/outline (`--app-outline-variant`, `--app-on-surface`/`-variant`). Suppression des littéraux (`8/16/6/4px`, `0.85/0.75/0.7/0.6rem`, `var(--ion-color-step-100)`, `var(--ion-color-medium-shade)`, `var(--ion-color-medium)`).
- **Périmètre** : HTML/TS (icônes par type, téléchargement par fichier, ZIP, prévisualisation inline) inchangés.
- **Référence Stitch** : écran `mail-attachment` (id ed9c3a7e0a524b0bb6db3794b4e51df5) **réutilisé**.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151** (restyle SCSS pur), `npm run lint` ✓.
- **Forge-simplify** : skip clean. **Code review** : APPROVED — 0 bloquant. Aucune donnée de PJ santé en clair hors affichage existant.

### v1.14 — Refonte `biology` (table token-driven) (task-125)

- **Repo** : `client-mobile` · **Branche** : `feat/task-125-stitch-biology`
- **PR** : [#28](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/28) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `6cf1583` feat(mobile): Stitch restyle of biology results table (token-driven)
- **Objet** : refonte « Clinical Precision » du tableau de résultats de biologie — migration SCSS pure.
- **Fichier** : `biology.component.scss` — migration **100 % tokens E014** ; mise en évidence hors-normes via `--app-error-container` + texte `--app-on-error-container`, critique = même fond + `border-left 3px var(--ion-color-danger)` + valeur `--ion-color-danger`, badges code en `--ion-color-tertiary`/`--ion-color-danger`. Suppression des littéraux (`rgba(245,158,11,…)`, `rgba(239,68,68,…)`, `#fff`, px/rem, `var(--ion-color-step-100)`, `--ion-color-warning-shade`, `--ion-color-medium*`).
- **Périmètre** : logique d'affichage (groupes par document, filtre hors-norme, `level()`/`arrow()`/codes d'interprétation) inchangée.
- **Référence Stitch** : écran titré **`BiologyComponent`** (id 625b517626294bd7bee428a974be3155) **réutilisé comme référence**. ⚠ Mismatch de nommage : convention kebab = `biology` (sélecteur `mss-biology`) ; le MCP Stitch n'a pas d'op de rename → **rename `BiologyComponent` → `biology` à faire dans l'UI Stitch (geste humain)**, consigné dans le `## Stitch design log` de la task.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151** (restyle SCSS pur), `npm run lint` ✓.
- **Forge-simplify** : skip clean. **Code review** : APPROVED — 0 bloquant. Aucune INS/contenu CDA en clair hors affichage existant.

### v1.15 — Refonte `biology-ack-badge` (token-driven) (task-126)

- **Repo** : `client-mobile` · **Branche** : `feat/task-126-stitch-biology-ack-badge`
- **PR** : [#29](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/29) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `7652da2` feat(mobile): Stitch restyle of biology-ack-badge (token-driven)
- **Objet** : refonte « Clinical Precision » du badge d'acquittement.
- **Fichier** : `biology-ack-badge.component.ts` (template + styles inline) — couleur `[color]="isCritical() ? 'danger' : 'tertiary'"` (remplace le `'warning'` amber hors-socle) ; styles `font: var(--app-type-label-md)`, `gap: var(--app-space-xs)`, icône `1em` (suppression `0.65rem`/`0.8rem`/`2px`).
- **Périmètre** : logique (visibilité, compteur `pendingBiologyAcksCount`, flag critique, tooltip) inchangée.
- **Référence Stitch** : écran `biology-ack-badge` (id c8cfb02efffd48a09f8bee1096804c7a) **réutilisé**.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151**, `npm run lint` ✓.
- **Forge-simplify** : skip clean. **Code review** : APPROVED — 0 bloquant.

### v1.16 — Refonte `biology-ack-panel` (token-driven) (task-127)

- **Repo** : `client-mobile` · **Branche** : `feat/task-127-stitch-biology-ack-panel`
- **PR** : [#30](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/30) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `ef19c5e` feat(mobile): Stitch restyle of biology-ack-panel (token-driven)
- **Objet** : refonte « Clinical Precision » du panneau d'acquittement — migration SCSS pure.
- **Fichier** : `biology-ack-panel.component.scss` — migration **100 % tokens E014** ; statut `à traiter`→`--ion-color-tertiary`, `en cours`→`--ion-color-primary`, `résolu`→`--ion-color-secondary` (remplace `warning`/`success` hors-socle, palette sans vert/ambre) ; panneau critique → `--app-error-container`. Suppression des littéraux (`12/10/8/6/4px`, `rgba(239,68,68,…)`, `#fff`, `var(--ion-color-step-*)`, `--ion-color-warning/success`).
- **Périmètre** : 5 actions, modale de confirmation, persistance `recordBiologyAck` inchangées.
- **Référence Stitch** : écran `biology-ack-panel` (id 617cba580ad548d7a439acb966184e4f) **réutilisé**.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151**, `npm run lint` ✓.
- **Forge-simplify** : skip clean. **Code review** : APPROVED — 0 bloquant.

### v1.17 — Refonte `biology-ack-confirm-dialog` (token-driven) (task-128)

- **Repo** : `client-mobile` · **Branche** : `feat/task-128-stitch-biology-ack-confirm-dialog`
- **PR** : [#31](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/31) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `a518c2c` feat(mobile): Stitch restyle of biology-ack-confirm-dialog (token-driven)
- **Objet** : refonte « Clinical Precision » de la modale de confirmation — migration SCSS pure.
- **Fichier** : `biology-ack-confirm-dialog.component.scss` — migration **100 % tokens E014** ; encart valeurs critiques → `--app-error-container`/`--app-on-error-container`, `--app-radius-lg`. Suppression des littéraux (`0.95/0.85/0.8rem`, `8/10/12/16/4/18px`, `rgba(239,68,68,0.12)`, `--ion-color-medium`).
- **Périmètre** : logique (note optionnelle, `confirm`/`cancel`, valeurs critiques LL/HH/AA) inchangée.
- **Référence Stitch** : écran `biology-ack-confirm-dialog` (id 53bbca53f21b4ad99bd8ed355628cac8) **réutilisé**. NB : écran orphelin « Confirmation : Patient contacté » (id 529342a3493b4c559269f7b7676a2e56) = doublon probable, nettoyage Stitch optionnel côté humain.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151**, `npm run lint` ✓.
- **Forge-simplify** : skip clean. **Code review** : APPROVED — 0 bloquant.

### v1.18 — Refonte `mail-compose` (token-driven) (task-129)

- **Repo** : `client-mobile` · **Branche** : `feat/task-129-stitch-mail-compose`
- **PR** : [#32](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/32) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `9c87c4e` feat(mobile): Stitch restyle of mail-compose (token-driven)
- **Objet** : refonte « Clinical Precision » de la composition — migration SCSS pure.
- **Fichier** : `mail-compose.component.scss` — migration **100 % tokens E014** (`--app-gutter`/`--app-space-*`, `--app-type-body-md`, `--app-radius`, bouton PJ en bordure pointillée `--app-outline-variant`). Suppression des littéraux (`12/6/4px`, `0.8rem`, `4px 8px`, `8px radius`, `var(--ion-color-step-200)`).
- **Périmètre** : champs To/Cc/Cci/Objet (`ion-input` label visible), `mss-html-editor` composé (task-130), logique d'envoi (PJ, accusé, send) inchangés.
- **Référence Stitch** : écran `mail-compose` (id 340f18be9395435f8fc472e0c476f736) **réutilisé**.
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151**, `npm run lint` ✓.
- **Forge-simplify** : skip clean. **Code review** : APPROVED — 0 bloquant. Jamais d'INS/RPPS dans sujets/headers.

### v1.19 — Refonte `html-editor` (token-driven) (task-130)

- **Repo** : `client-mobile` · **Branche** : `feat/task-130-stitch-html-editor`
- **PR** : [#33](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/33) — **ouverte**, label `awaiting-human-merge` (HAG rule 10)
- **Commit** (branche) : `ab6e9ed` feat(mobile): refonte Stitch token-driven du composant html-editor
- **Objet** : refonte « Clinical Precision » de l'éditeur de contenu — migration SCSS + ajustement HTML.
- **Fichiers** : `html-editor.component.scss` — migration **100 % tokens E014** (barre d'outils plate `--app-surface-container-low` + bordure `--app-outline-variant`, boutons d'outils `--app-touch-target` (44px) en `--app-on-surface-variant`/`--app-radius-sm`, zone `--app-type-body-lg`/`--app-on-surface`, placeholder `--app-outline`). Suppression des littéraux (`8px radius`, `2px gap`, `160px`, `10px 12px`, `14px`, `1.5`, `var(--ion-color-step-*)`, `var(--ion-color-medium)`). `html-editor.component.html` — retrait de `size="small"` sur les 4 `ion-button` (cible tactile 44px gouvernée par le SCSS), `data-testid` préservés (bold/italic/list/link).
- **Périmètre** : capacités d'édition (`document.execCommand` gras/italique/liste/lien, contenteditable, `@Input html` / `@Output htmlChange`) inchangées.
- **Référence Stitch** : écran `html-editor` (id c944b34bc4fb4e8d891c97fd30719b92) **réutilisé** — aucun rename requis (titre déjà conforme).
- **Validation** : `npm run build` ✓, `npm test` ✓ **151/151**, `npm run lint` ✓.
- **Forge-simplify** : skip clean (diff déjà minimal/token-driven). **Code review** : APPROVED — 0 bloquant. Restyle UI sans logique métier.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Chemin | Rôle |
|--------|--------|------|
| Variables de thème | `Client/Mobile/src/theme/variables.scss` | Tokens « Clinical Precision » → variables Ionic + `--app-*` |
| Styles globaux | `Client/Mobile/src/global.scss` | Application transverse des tokens aux composants Ionic |
| Config build | `Client/Mobile/angular.json` | Câblage des CSS Public Sans (fontsource) dans `styles` |
| Police | `@fontsource/public-sans` (node_modules, woff2 locaux) | Public Sans 400/600/700 embarquée |
| Dashboard d'accueil | `Client/Mobile/src/app/home/home.page.{ts,html,scss}` | Landing post-login, agrégation client-side de l'état mail (Messagerie / non lus du jour / Biologie) |
| Boîte de réception | `Client/Mobile/src/app/inbox/inbox.page.{html,scss}` | Page hôte mince ; zone de contrôles épinglée (recherche + filtres + toggle vue + chip bio), liste/infinite-scroll, FAB compose ; refonte structurelle token-driven |
| Coquille à onglets | `Client/Mobile/src/app/tabs/` + `patients/` + `settings/` | Barre de navigation basse `ion-tabs` (Messages/Patients/Paramètres) ; Patients & Paramètres = placeholders ; redirect `/inbox → /tabs/messages` |
| Menu des répertoires | `Client/Mobile/src/app/features/mail/components/mail-folder-list` + `mail-folder-item` | Liste latérale des dossiers : sections Répertoires (icônes par type) + TAGS (pastilles colorées), sélection en pilule, badge non-lus sombre |
| Ligne d'email | `Client/Mobile/src/app/features/mail/components/mail-header` (+ conteneur `mail-list`) | Ligne haute densité token-driven : avatar carré, nom gras, sujet/extrait, horodatage, pastille non-lu, chips statut, accent critique, valeurs biologie inline |
| Recherche (mobile) | `Client/Mobile/src/app/mail-search/` + `features/mail/components/mail-search` + `mail-search-history` | Page dédiée `/mail-search` : critères (parité Angular), historique rejouable, résultats via `mail-list` réutilisé ; `SearchSettingsService` (minSimilarity) |
| Historique de recherche (backend) | `Api/Mail/src/Application/Services/{Interfaces,Implementation}/*SearchHistoryService*` + `Api/Controllers/V1/SearchController` | Persistance Redis scope praticien (clé email), TTL 7 j, dédup/cap/minimisation INS ; endpoints GET/DELETE `/api/v1/search/history` |

## Annexe B — Inventaire fonctionnel daté (2026-06-26)

- Tasks de l'EPIC : 20 (1 socle + 19 reprises d'écran ; task-118 `mail-header` supprimée le 2026-06-24 — composant déjà couvert par task-114/115, en-tête détaillé relevant de task-121 `mail-detail`)
- Tasks mergées : 19 (task-110 … task-129, hors task-118 supprimée)
- Tasks en PR ouverte : 1 (task-130 `html-editor` — client-mobile)
- Tasks à faire : 0
- Tests client-mobile : 151 (verts) — inchangé vs task-129 (task-130 = restyle SCSS/HTML pur)
- Endpoints backend ajoutés : `GET`/`DELETE /api/v1/search/history` (historique Redis, TTL 7 j, scope praticien)
- DTO publié : `HealthPlatform.Dtos.Mss 337.0.0` (SearchHistory*)
- Dépendance de police ajoutée : `@fontsource/public-sans@^5`

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | RG fermées |
|------|--------------|------------|
| task-110 | Socle design system mobile « Clinical Precision » : Public Sans embarquée, tokens couleur/typo/espacement/formes mappés sur Ionic + `--app-*`, application transverse (densité listes, boutons, chips, inputs, overlays), fallback mode sombre | aucune (restyling UI) |
| task-111 | Refonte écran `login` d'après l'export Stitch (logo WEDA SVG, bouton PSC officiel ANS, bannière session-expirée) | aucune (UI) |
| task-112 | Refonte écran `authentication` (callback PSC) : états chargement/erreur, footer réassurance, « HIPAA »→« ANS » | aucune (UI) |
| task-113 | Tableau de bord d'accueil `home` miroir du dashboard Angular MSS : landing post-login, agrégation client-side (Messagerie / non lus du jour / Biologie), route `/home`, redirection login/callback | aucune (UI + agrégation d'affichage) |
| task-114 | Refonte structurelle écran `inbox` (toolbar, zone de contrôles épinglée, FAB primaire) **+ mise en conformité Stitch haute-fidélité** : valeurs de biologie inline, regroupement « Biologie à valider (hors normes) », barre de navigation `ion-tabs` (+ placeholders Patients/Paramètres), filtres/toggle en pilule iOS, tokens error-container | aucune (UI) |
| task-116 | Refonte du menu des répertoires `mail-folder-list`/`mail-folder-item` : icônes par type de dossier, état sélectionné en pilule, badge non-lus sombre, section TAGS (pastilles colorées), en-tête menu « MSSanté » | aucune (UI) |
| task-115 | Refonte de la liste des emails `mail-list`/`mail-header` : ligne haute densité 100 % token-driven (avatar carré, séparateurs/fonds/typo socle), accent rouge + libellé « Biologie CRITIQUE » sur résultat critique, réponses de fil indentées ; acquis biologie/regroupement task-114 préservés | aucune (UI) |
| task-117 | Item de répertoire `mail-folder-item` : état actif en pilule bleu clair (`primary-container`) + icône/nom primaires (le reste du composant provenait déjà de task-116) | aucune (UI) |
| task-119 | Recherche avancée `mail-search` + historique de recherche : DTOs partagés (337.0.0), service+endpoints backend (Redis scope praticien, TTL 7 j, minimisation INS, RFC 7807), page mobile dédiée + composant `mail-search-history` + parité filtres 100 % + `minSimilarity` réglages, mêmes apports historique côté Angular (code-only) | aucune (RGPD/PGSSI-S : minimisation, scope praticien, TTL borné — pas de RG Ségur formelle) |
| task-120 | Refonte Stitch du chip `inbox-biology-ack-chip` (pilule 4px/label-md token-driven, accent tertiaire actif) + compteur de bios non acquittées par dossier (libellé « Bio à acquitter (N) ») ; fetch en `ngOnChanges` (refetch par dossier, anti-régression du scope de filtre) | aucune (UI + compteur d'affichage) |
| task-121 | Refonte Stitch de la carte méta du `mail-detail` : SCSS migré 100 % tokens E014 (typo/espacements/formes/surfaces), suppression des valeurs en dur, fallback chip de tag par token ; structure & comportement inchangés | aucune (UI) |
| task-122 | Refonte Stitch du corps `mail-body` : SCSS migré 100 % tokens E014 (onglets, corps HTML/texte, bannière images distantes), interlignage 1.6 ; pipeline d'assainissement HTML inchangé | aucune (UI) |
| task-123 | Refonte Stitch du cadre `medical-html-frame` : carte bordée arrondie token-driven, tokens injectés alignés palette Clinical Precision + Public Sans ; mécanisme iframe/blob/sandbox inchangé | aucune (UI) |
| task-124 | Refonte Stitch de la pièce jointe `mail-attachment` : SCSS migré 100 % tokens E014 (icône type, nom, taille, badge, télécharger/ZIP) ; HTML/TS inchangés | aucune (UI) |
| task-125 | Refonte Stitch du tableau `biology` : SCSS migré 100 % tokens E014, hors-normes en `--app-error-container` + accent danger pour le critique ; logique biologie inchangée. ⚠ Rename Stitch `BiologyComponent`→`biology` = geste humain | aucune (UI) |
| task-126 | Refonte Stitch du badge `biology-ack-badge` : couleurs sémantiques socle (critique→danger, en attente→tertiary, fin du `warning` amber hors-socle), tokens typo/espacement ; logique inchangée | aucune (UI) |
| task-127 | Refonte Stitch du panneau `biology-ack-panel` : SCSS migré 100 % tokens E014, statut aux couleurs sémantiques socle (à traiter/en cours/résolu → tertiary/primary/secondary), panneau critique en error-container ; 5 actions + confirmation inchangées | aucune (UI) |
| task-128 | Refonte Stitch de la modale `biology-ack-confirm-dialog` : SCSS migré 100 % tokens E014, encart valeurs critiques en error-container/radius-lg ; note + confirm/cancel inchangés | aucune (UI) |
| task-129 | Refonte Stitch de la composition `mail-compose` : SCSS migré 100 % tokens E014 (corps, zone PJ, bouton PJ pointillé) ; champs label visible, logique d'envoi inchangée | aucune (UI) |
| task-130 | Refonte Stitch de l'éditeur `html-editor` : SCSS migré 100 % tokens E014 (barre d'outils plate, boutons d'outils 44px `--app-touch-target`, zone `--app-type-body-lg`, placeholder `--app-outline`), retrait `size="small"` des `ion-button` ; capacités d'édition (gras/italique/liste/lien, contenteditable) inchangées | aucune (UI) |
