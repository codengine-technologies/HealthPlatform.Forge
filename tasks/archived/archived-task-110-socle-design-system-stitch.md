# todo-task-110.md — Socle design system mobile (Stitch « Clinical Precision »)

**Repos**: client-mobile
**Dependencies**: none
**Single frontend**: true
**Epic**: E014
**EpicTitle**: Design system mobile (Stitch Clinical Precision)

## Branches
- `client-mobile` (pushed) : feat/task-110-socle-design-system-stitch — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-110-socle-design-system-stitch

## Objective
Aligner l'identité visuelle de l'app mobile (`client-mobile`, Ionic 8 + Angular
20) sur le **design system de référence Stitch « Clinical Precision »**, défini
dans le projet Stitch `client-mobile` (id `10088502293310567548`,
source de vérité du design mobile — cf. `agents/stitch-design.md`).

Cette US livre **le socle thème global uniquement** : les **design tokens**
(couleurs, typographie, espacements, formes, élévation) traduits en variables
CSS Ionic + SCSS, et la police **Public Sans** embarquée. Tous les écrans
existants **héritent** automatiquement de ce socle, sans refonte structurelle
écran par écran (celle-ci est le périmètre des US de suite — voir ci-dessous).

Périmètre volontairement cadré :
- **`client-mobile` uniquement** — aucun changement backend, dtos, ni autre
  frontend. Pas de logique métier touchée : restyling pur.
- **Socle thème global** : `src/theme/variables.scss` + `src/global.scss` +
  chargement de la police. Pas de réécriture des templates/structure des
  composants dans cette US.
- **Stitch = référence, pas du code** : on traduit les tokens du design system
  Stitch en variables Ionic ; on **ne colle jamais** le HTML/CSS Stitch.

## Source de design (Stitch)
- Projet Stitch : `client-mobile` (id `10088502293310567548`, device MOBILE).
- Design system : **« Clinical Precision Design System »** (embarqué dans le
  `designTheme` du projet Stitch). Tokens de référence :
  - **Couleurs** : primary `#005EB8` (bleu institutionnel), on-primary `#FFFFFF`,
    surface `#F9F9FC`, surface-container-lowest `#FFFFFF`, surface-alt /
    container `#EEEEF0`/`#F3F3F6`, on-surface `#1A1C1E`, on-surface-variant
    `#424752`, outline `#727783` / outline-variant `#C2C6D4`, error `#BA1A1A`,
    accent critique rouge réservé aux alertes.
  - **Typographie** : **Public Sans**, échelle display-lg 30/700, headline-md
    24/600, headline-sm 20/600, title-lg 18/600, body-lg 16/400, body-md 14/400,
    label-md 12/600 (letter-spacing .05em), caption 12/400.
  - **Formes (soft)** : boutons/inputs radius 4px (0.25rem), cartes/modales 8px
    (0.5rem), bottom-sheets 12px (0.75rem), avatars circulaires.
  - **Espacements** : échelle 8px (xs 4 / sm 8 / md 16 / lg 24 / xl 32), marge
    mobile 16px, gouttière 12px.
  - **Élévation** : couches tonales + outlines 1px discrets, **éviter les ombres
    lourdes** (popovers/overlays : ombre douce 0 4px 12px rgba(0,0,0,.08)).
  - **Composants** : boutons (primary plein, touch ≥ 44px), inputs (fond
    surface-alt, label toujours visible), chips (radius 4px, label-md), listes
    haute densité (lignes ≥ 56px, séparateurs 1px subtils).

## Mapping écrans ↔ Stitch (état au 2026-06-23)
Le mapping composants `client-mobile` ↔ écrans Stitch a été refait. État retenu
comme base des US de suite (refonte structurelle) :

- **Correspondance exacte (15)** : `authentication`, `home`, `login`,
  `mail-list`, `mail-detail`, `mail-compose`, `mail-search`, `mail-body`,
  `mail-folder-item`, `mail-folder-list`, `mail-attachment`,
  `medical-html-frame`, `html-editor`, `biology-ack-badge`,
  `biology-ack-confirm-dialog`, `biology-ack-panel`.
- **À renommer dans l'UI Stitch** (pas d'op rename côté MCP) : écran
  `BiologyComponent` → `biology`.
- **Écrans Stitch manquants** (à créer pour les US de suite, hors socle) :
  `inbox` (création MCP en échec — timeouts ; à recréer dans l'UI Stitch),
  `mail-header`, `inbox-biology-ack-chip`.

## Suite prévue (hors périmètre de cette US)
Refonte **structurelle écran par écran** (fidélité layout/hiérarchie/états aux
maquettes Stitch, via `/stitch-design`) en batch de follow-up sous E014, par
groupe : auth/home → liste/inbox → détail/biologie → compose. Ces US
s'appuieront sur le socle livré ici.

## Definition of Done
- [ ] Build passe : `cd Client/Mobile && npm ci && npm run build` (0 erreur)
- [ ] Tests passent : `npm test -- --watch=false --browsers=ChromeHeadless` (0 échec)
- [ ] `src/theme/variables.scss` : variables Ionic mappées sur les tokens
      « Clinical Precision » (`--ion-color-primary` = #005EB8 + contrastes/shades,
      `--ion-background-color`, `--ion-text-color`, couleurs surface/outline,
      `--ion-color-danger` = #BA1A1A)
- [ ] **Public Sans** embarquée (fichiers de police locaux, pas de CDN externe
      bloquant) et appliquée globalement (`--ion-font-family`)
- [ ] Tokens **espacement** (8/16/24/32, marge 16, gouttière 12) et **formes**
      (radius 4/8/12, avatars circulaires) exposés en variables CSS et utilisés
      par `global.scss`
- [ ] `global.scss` : lignes de liste haute densité (≥ 56px), séparateurs 1px
      discrets, boutons radius 4px + touch ≥ 44px, chips radius 4px, inputs fond
      surface-alt, élévation tonale (pas d'ombres lourdes)
- [ ] Mode **clair** canonique (le design system est LIGHT) ; vérifier qu'aucun
      écran ne casse si le dark mode système est actif (a minima lisible)
- [ ] Aucune régression fonctionnelle : tous les écrans existants se chargent et
      restent utilisables (héritage du thème, pas de refonte structurelle)
- [ ] Aucune chaîne en dur ajoutée ; aucun token codé en dur hors
      `variables.scss`/`global.scss` (couleurs via variables)
- [ ] Aucune donnée de santé en clair introduite dans l'UI/les logs

## Manual Test Plan
- Lancer le mobile : `cd Client/Mobile && npm start` (ou `ionic serve`).
- Parcourir les écrans clés et vérifier l'application du socle visuel :
  1. **login / authentication** : bleu primaire #005EB8 sur les boutons,
     typographie Public Sans, coins arrondis doux, inputs au nouveau style.
  2. **inbox / mail-list** : lignes de liste haute densité (≥ 56px),
     séparateurs fins, segments/chips au nouveau thème, FAB compose au bleu
     primaire.
  3. **mail-detail / mail-body / biology** : titres à l'échelle typographique,
     espacements 8px cohérents, badges/chips biologie lisibles.
  4. **mail-compose / html-editor** : champs et boutons au nouveau style.
- Vérifier la **cohérence inter-écrans** : même police, même palette, mêmes
  rayons, mêmes espacements partout.
- Basculer le thème système en sombre : vérifier qu'aucun écran ne devient
  illisible (le mode clair reste la cible ; pas d'exigence de dark mode complet).
- Comparer visuellement avec les captures de référence Stitch (projet
  `client-mobile`) : l'**ambiance** (couleur/typo/formes/densité) doit
  correspondre, même si la structure fine des écrans reste celle de l'existant
  (refonte structurelle = US de suite).

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : hors couloir — restyling UI, aucun usage métier de soin.
- **Vague Ségur** : hors Ségur — fonctionnalité de confort/UX (design system).
- **Exigences DSR honorées** : non applicable — aucune exigence DSR couverte.
- **INS** : non applicable — aucune manipulation de patient ni d'INS.
- **Authentification PS** : inchangée — aucun flux d'authentification modifié.
- **Habilitations** : non applicable — aucun contrôle d'accès touché.
- **Interop CI-SIS** : non applicable — aucun échange métier (pas de CDA/FHIR/HL7v2).
- **Tracé PGSSI-S** : non applicable — aucun évènement métier nouveau (restyling).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : inchangé — pas de nouvelle donnée stockée.
- **AIPD / impact RGPD** : inchangé — aucun traitement de données nouveau ;
  restyling purement visuel.

## Develop log

- Repos touched : client-mobile
- DTOs published : no DTO change
- Interop published : no interop change
- Implémentation :
  - `@fontsource/public-sans@^5` ajouté (police locale, poids 400/600/700) et
    câblé dans `angular.json` > styles (build + test)
  - `src/theme/variables.scss` : tokens « Clinical Precision » → variables Ionic
    (`--ion-color-primary` #005EB8 + shades/contrastes, `--ion-color-danger`
    #BA1A1A, surfaces, texte, `--ion-font-family`) + tokens `--app-*`
    (espacements 8px, formes 4/8/12px, élévation tonale, densité listes,
    échelle typo) + fallback `prefers-color-scheme: dark`
  - `src/global.scss` : application transverse (Public Sans, lignes ≥ 56px,
    boutons radius + touch 44px, chips, inputs surface-alt, overlays, avatars
    ronds, classes typo utilitaires)
- Commits :
  - client-mobile : 29ff95c feat(mobile): socle design system Stitch « Clinical Precision » (task-110)
- Local build / test : ✓ build OK (warning budget pré-existant `mail-header.scss`,
  hors socle) ; 108/108 tests verts
- DOD self-check : build ✓, tests ✓, variables Ionic mappées ✓, Public Sans
  embarquée + appliquée ✓, tokens espacement/formes exposés + utilisés ✓,
  global.scss densité/boutons/chips/inputs/élévation ✓, fallback dark ✓,
  zéro valeur de design en dur hors variables/global ✓. Items observables
  (rendu visuel par écran, comparaison Stitch) → déférés au test humain (HAG).
- Next step : /forge-simplify task-110

## Simplify log
- Repos passed : client-mobile (seul repo touché)
- Applied & committed : aucun
- No change : client-mobile — socle purement déclaratif (tokens centralisés
  dans variables.scss, réutilisés via var() dans global.scss, aucune
  duplication ni logique) → aucune simplification applicable (reuse/
  simplification/efficacité/altitude tous satisfaits par construction)
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ (inchangés depuis /develop — pas d'édition simplify)
- Next step : /lint-mobile task-110 (api-mail & client-angular non touchés)

## Lint mobile log

- Repo : client-mobile (Client/Mobile/, Ionic/Angular CLI)
- Commands : npm run lint
- Baseline : 0 errors / 0 warnings — « All files pass linting »
- Final : 0 errors / 0 warnings
- Iterations : 0 / 5 (lint clean → no work ; le socle ne touche que scss/json,
  non lintés)
- Commit : aucun (rien à corriger)
- Build / tests : ✓ (déjà verts en /develop)
- Next step : /review task-110

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/14 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 bloquant, 1 suggestion non bloquante)
- Repos validés : client-mobile (build ✓, 108/108 tests ✓, lint ✓)
- Diff : purement déclaratif (scss/json) — aucune logique, aucune donnée de santé
- Suggestion : `letter-spacing` répété entre `.app-text-label-md` et `ion-chip`
  (nécessaire vu le shorthand CSS `font:` qui n'inclut pas le letter-spacing)
- DOD : items command-verifiables ✓ ; rendu visuel par écran + comparaison Stitch
  déférés au test humain (HAG, Manual Test Plan recopié dans la PR)
- Séquencement E014 : socle préalable des US task-111..130 ; indépendamment
  mergeable (identité visuelle cohérente et testable en l'état)

## Addendum — mode clair canonique (post-review)
- Constat humain : « aucun changement visible ». Cause : en mode sombre OS, la
  palette `dark.system.css` d'Ionic écrasait les couleurs de marque (primary
  forcé à #4d8dff au lieu de #005EB8). De plus le défaut Ionic 8 (primary
  #0054e9) est déjà proche → écart discret.
- Décision humaine : forcer le mode clair partout (design canonique).
- Changements (commit c82125d, poussé sur PR #14) : retrait import
  `dark.system.css`, suppression du bloc `@media (prefers-color-scheme: dark)`,
  `color-scheme: light` (variables.scss + index.html). Build ✓, 108/108 tests ✓.
- Rappel : la vraie transformation visuelle viendra des refontes écran par
  écran (task-111..130).

## Merged
- Date : 2026-06-23
- Validation humaine : `--i-tested` (HAG, règle 10)
- `client-mobile` : squash `e225afa` — PR #14 mergée et fermée
- Remote branch `feat/task-110-socle-design-system-stitch` supprimée ; branche
  locale conservée
- CI `develop` : aucun workflow CI configuré sur le repo mobile (rien à vérifier)
