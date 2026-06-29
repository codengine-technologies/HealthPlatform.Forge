# todo-task-111.md — Refonte Stitch écran `login` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Branches
- `client-mobile` (pushed) : feat/task-111-refonte-login-stitch — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-111-refonte-login-stitch

## Objective
Refondre **structurellement** l'écran de connexion mobile `login`
(`src/app/login/login.page.*`) pour une fidélité parfaite à sa **référence
Stitch** `login` (projet `client-mobile`, id `10088502293310567548`), en
s'appuyant sur le socle design system livré par `done-task-110`.

Travail **soigné, pixel-conscient** : hiérarchie visuelle, espacements,
composants, états (chargement, erreur d'identifiants) doivent correspondre à la
maquette Stitch. `client-mobile` uniquement, restyling/restructuration UI — aucun
changement de logique d'authentification.

## Référence Stitch
- **Réutiliser** l'écran Stitch `login` (correspondance exacte) comme référence.
- Étape design préalable : `/stitch-design task-111` récupère screenshot +
  HTML/CSS de référence. **Stitch = référence, jamais coller le HTML** — traduire
  en Ionic.

## Definition of Done
- [ ] Build passe : `cd Client/Mobile && npm ci && npm run build` (0 erreur)
- [ ] Tests passent : `npm test -- --watch=false --browsers=ChromeHeadless` (0 échec)
- [ ] Structure de l'écran alignée sur la référence Stitch `login` (layout,
      hiérarchie, logo, champs identifiant/mot de passe, bouton(s) de connexion,
      états chargement + erreur)
- [ ] Tokens du socle (couleurs/typo/espacements/formes) **réutilisés** — aucune
      valeur de design en dur dans le composant
- [ ] `data-testid` préservés/complétés sur tous les éléments interactifs
- [ ] Aucune régression fonctionnelle (connexion + gestion d'erreur identiques)
- [ ] Aucune chaîne en dur ajoutée hors libellés FR existants
- [ ] Comparaison visuelle avec le screenshot Stitch consignée (capture avant/après)

## Manual Test Plan
- Lancer : `cd Client/Mobile && npm start` (ou `ionic serve`).
- Ouvrir l'écran `login` (déconnecté).
- Vérifier : logo, champs, bouton(s) au nouveau design ; typo Public Sans ;
  bleu primaire #005EB8 ; arrondis doux ; espacements 8px cohérents.
- Saisir des identifiants invalides → message d'erreur lisible, au bon style.
- Se connecter avec des identifiants valides → navigation inchangée.
- Comparer visuellement à la maquette Stitch `login`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : hors couloir — restyling UI. **Vague Ségur** : hors Ségur.
- **Exigences DSR** : non applicable. **INS** : non applicable.
- **Authentification PS** : inchangée (aucun flux d'auth modifié).
- **Habilitations / Interop CI-SIS / Tracé PGSSI-S / Consentement / Référentiels
  métier** : non applicable — restyling sans logique métier.
- **Hébergement HDS** : inchangé. **AIPD / RGPD** : inchangé (UI pure).

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Référence |
  |---|---|---|---|---|
  | login | login | 84fe1a8c764344509857ef06a1696adc | reused | screenshot + HTML/CSS récupérés |
- ⚠ Rename needed in Stitch UI : none
- Stitch reachable : ✓
- Intent traduit en Ionic (jamais collé) : header de marque « lock MSSanté », fond
  clair, logo en disque blanc + halo, titres centrés, bouton PSC primaire ancré bas,
  mention ANS, bannière session-expirée en rouge doux.
- Écart assumé vs maquette : le lien « Autre moyen de connexion » de la maquette est
  **omis** (aucun autre moyen d'auth câblé dans l'app → éviter un lien mort/fausse
  fonctionnalité). Logo : icône Ionic `mail` dans le disque (pas d'asset WEDA importé).

## Develop log

- Repos touched : client-mobile
- DTOs/Interop : aucun
- Implémentation : refonte structurelle de `src/app/login/login.page.{html,scss}`
  d'après la référence Stitch `login`, 100% tokens du socle (task-110), `data-testid`
  ajouté sur le bouton PSC (`login-psc-btn`). Logique inchangée (`loginWithPsc`,
  `sessionExpired`).
- Commits :
  - client-mobile : 98f32d2 feat(mobile): refonte écran login d'après la référence Stitch (task-111)
- Local build / test : ✓ build OK (warning budget pré-existant `mail-header.scss`,
  hors scope) ; 108/108 tests verts
- DOD self-check : build ✓, tests ✓, structure alignée Stitch ✓, tokens socle (zéro
  valeur en dur) ✓, data-testid ✓, aucune régression fonctionnelle ✓. Comparaison
  visuelle screenshot Stitch → test humain (HAG).
- Next step : /forge-simplify task-111

## Simplify log
- Repos passed : client-mobile (seul repo touché)
- Applied & committed : aucun
- No change : client-mobile — refonte d'écran propre et token-based (aucune
  duplication, HTML sémantique, pas de helper à factoriser pour un écran unique)
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ (inchangés depuis /develop)
- Next step : /lint-mobile task-111 (api-mail & client-angular non touchés)

## Lint mobile log
- Repo : client-mobile (Client/Mobile/)
- Commands : npm run lint
- Baseline : 0 errors / 0 warnings — « All files pass linting »
- Final : 0 errors / 0 warnings — Iterations : 0 / 5
- Commit : aucun (rien à corriger)
- Build / tests : ✓ (déjà verts en /develop)
- Next step : /review task-111

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/15 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 bloquant)
- client-mobile : build ✓, 108/108 tests ✓, lint ✓
- Logique login inchangée ; template token-based ; data-testid (banner + bouton PSC) ;
  aucun lien mort (lien « Autre moyen de connexion » de la maquette volontairement omis)
- DOD command-verifiable ✓ ; comparaison visuelle Stitch déférée au test humain (HAG)

## Addendum — fidélité à l'export Stitch (post-review, sur retour humain)
- Constat humain : « pas le même résultat que la page HTML exportée de Stitch »
  (`Downloads/stitch_client_mobile/code.html` + DESIGN.md).
- Causes identifiées via l'export :
  1. **Primary** : token Stitch `primary = #00478d` (l'export `bg-primary`), `#005eb8`
     = `primary-container`. Mon socle (task-110) avait pris `#005eb8` comme primary.
  2. **Rayons** : l'export `code.html` rend `rounded-full = 0.75rem` (carré arrondi,
     pas un cercle), `rounded-xl = 0.5rem` (bouton), `rounded-lg = 0.25rem` (bannière).
- Correctifs (commit ce8eebe, poussé sur PR #15) :
  - socle : `--ion-color-primary` = #00478d (+ shade/tint recalculés) ; ajout
    `--app-primary-container` = #005eb8 (amende le socle task-110, bénéficie à tous
    les écrans).
  - login : logo en carré arrondi 0.75rem, bouton 0.5rem, bannière 0.25rem ; halo +
    hover bouton en primary-container. Build ✓, 108/108 tests ✓.
- **Assets intégrés** (fournis par l'humain, commit 60e5e8c) :
  - logo **WEDA** `src/assets/weda-logo.png` dans le disque (remplace l'icône mail)
  - **bouton officiel PSC** `src/assets/psc-connect-button.svg` (SVG ANS auto-porté
    #000091) utilisé tel quel sur fond clair ; handler `loginWithPsc` + `data-testid`
    conservés via le `<button>` englobant
- **Lien « Autre moyen de connexion »** ajouté (commit fbb7e62) — placeholder visuel
  inactif (pas de 2e moyen d'auth câblé), `data-testid` login-alt-link
- État : parité maquette Stitch login complète (commits 98f32d2 → 48e12fe sur PR #15)
- Logo WEDA finalement **vectorisé en SVG** (`weda-logo.svg`, repro ~91% du
  bitmap, navy #064475), PNG supprimé (commit 48e12fe).

## Merged
- Date : 2026-06-23
- Validation humaine : `--i-tested` (HAG, règle 10)
- `client-mobile` : squash `9a88a01` — PR #15 mergée et fermée
- Remote branch `feat/task-111-refonte-login-stitch` supprimée ; branche locale conservée
- CI `develop` : aucun workflow CI configuré sur le repo mobile (rien à vérifier)
