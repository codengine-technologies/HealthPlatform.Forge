# todo-task-136.md — Connexion mobile par CIBA e-CPS (RPPS + validation découplée)

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: —
**Epic**: E012

## Objective

Doter l'app `client-mobile` du **mode d'authentification CIBA** (Client-Initiated
Backchannel Authentication) destiné au mobile, canal **`MOBILE`**, déjà exposé
côté proxy d'authentification par l'endpoint `POST /v1/auth/connect`.

Aujourd'hui le mobile ne sait se connecter que par **redirection PSC web**
(`AuthService.loginPsc()` → redirection navigateur → callback `code` →
`/auth/token`). Le CIBA est le flux **découplé** : le PS saisit son **RPPS**
dans l'app, l'app déclenche la demande d'authentification, et le PS **valide sur
son application e-CPS** (notification reçue sur le même terminal). Pendant ce
temps le proxy interroge l'IdP en tâche de fond (polling serveur, jusqu'à 2 min)
puis, à la validation, pose le cookie de session BFF et renvoie la session.

**Décisions produit (validées 2026-06-29) :**

1. **CIBA devient le moyen de connexion principal** sur mobile : le bouton
   primaire de l'écran de connexion lance le flux e-CPS (saisie RPPS). La
   redirection PSC web existante passe en **moyen secondaire** (lien « Autre
   moyen de connexion » déjà présent dans la maquette, aujourd'hui inactif).
2. **Binding message généré par l'app** : l'app tire un **code aléatoire à
   2 chiffres** (`00`–`99`), l'affiche en grand pendant l'attente, et le PS
   vérifie qu'il **correspond** à celui montré dans son app e-CPS
   (anti-hameçonnage, esprit OIDC CIBA).
3. **RPPS pré-rempli** : le dernier RPPS saisi avec succès est mémorisé
   localement et **pré-rempli** (modifiable) à la connexion suivante.

**Hors scope** : le proxy d'authentification (`psc-proxy-*`) — l'endpoint
`/auth/connect` est **déjà implémenté** et ces repos sont gérés manuellement,
hors automation forge. Aucune modification backend n'est attendue. Le mode CARD
n'est pas câblé (mobile = canal `MOBILE` uniquement).

## Contrat d'échange (rappel, déjà fourni par le proxy)

- **Requête** `POST {authEndpoint}/auth/connect` (corps JSON, `withCredentials`) :
  - `nationalId` : RPPS — 12 chiffres, commence par `8` (regex proxy `^8\d{11}`)
  - `bindingMessage` : exactement 2 chiffres (`^\d{2}$`)
  - `clientId` : identifiant logiciel (issu de `environment.authClientId`, ex. `weda`)
  - `channel` : **`MOBILE`** (constante)
- La requête est **longue** : le proxy fait le polling serveur (≈ 2 min max)
  en attendant la validation e-CPS du PS. L'app affiche un écran d'attente.
- **Réponse 200** : `{ proxy_session_id, session_state }` + **cookie de session
  BFF posé**. L'app récupère alors le `TokenAggregate` via le cookie
  (`POST /auth/token` sans `code`, comme `AuthService.refreshSession()`), construit
  l'`AuthSession` et navigue vers `/home`.
- **Réponse d'erreur** : `application/problem+json` (RFC 7807). Cas connus du
  proxy à mapper en messages FR : payload invalide (400), client/RPPS inconnu
  (404), **session déjà en cours** / **conflit** (409), **IdP injoignable**
  (503), **timeout / non validé** (échec polling), erreur interne CIBA.

## Definition of Done

- [ ] Build passe : `cd Client/Mobile && npm run build` (0 erreur)
- [ ] Tests passent : `npm test -- --watch=false --browsers=ChromeHeadless` (0 échec)
- [ ] `AuthService.connectCiba(rpps)` (ou équivalent) implémenté : génère le
      binding message, POST `/auth/connect` `{ nationalId, bindingMessage, clientId, channel:'MOBILE' }`
      en `withCredentials`, puis récupère le `TokenAggregate` via le cookie de
      session et construit l'`AuthSession` (réutilise `sessionFromTokenAggregate`)
- [ ] Tests unitaires `connectCiba` : succès end-to-end, échec validation RPPS,
      timeout/échec polling, refus/erreur IdP, conflit session déjà en cours
      (≥ 1 test par branche)
- [ ] Générateur de binding message testé : renvoie toujours **2 chiffres**,
      bornes `00`–`99` incluses
- [ ] Validation RPPS **côté client avant POST** : 12 chiffres, commence par `8`
      (aligné sur la regex du DTO proxy) ; message d'erreur FR si invalide ; testé
- [ ] Écran de connexion CIBA implémenté (saisie RPPS) + **état d'attente**
      affichant le binding code en grand et un bouton **Annuler**
- [ ] CIBA est le bouton **principal** de l'écran de connexion ; la redirection
      PSC web reste accessible en moyen **secondaire** (lien « Autre moyen de connexion »)
- [ ] **Pré-remplissage RPPS** : RPPS mémorisé localement après succès, pré-rempli
      (modifiable) à la connexion suivante ; testé
- [ ] Erreurs `ProblemDetails` consommées (`title`/`detail`/`status`) et mappées
      en messages FR lisibles (timeout/non validé, RPPS/client inconnu, session déjà
      en cours, IdP injoignable, erreur générique)
- [ ] `data-testid` sur tous les éléments interactifs (champ RPPS, bouton connexion
      e-CPS, bouton annuler, lien moyen secondaire, zone binding code, zone erreur)
- [ ] Libellés **FR en dur** (pas de `ngx-translate` — cf. convention mobile/Angular MSS)
- [ ] **Aucun RPPS en clair** dans les logs console / messages d'erreur affichés /
      URL ; le RPPS ne transite que dans le corps du POST
- [ ] `channel` figé à `MOBILE`, `clientId` issu de `environment.authClientId`

## Manual Test Plan

**Pré-requis** : proxy d'authentification lancé en local (exposé sur
`environment.authEndpoint`, ex. `https://localhost:8081/v1`), un **RPPS de test**
valide et l'**application e-CPS** (bac à sable PSC) installée pour recevoir et
valider la demande.

1. Lancer le mobile : `cd Client/Mobile && npm start` (ou `ionic serve`).
2. Ouvrir l'écran de connexion → le bouton **principal** propose la connexion
   **e-CPS** (CIBA).
3. Le toucher, saisir le **RPPS** de test, valider.
4. L'app affiche un **code à 2 chiffres** (ex. « 58 ») et l'état « En attente de
   validation sur votre application e-CPS ».
5. Sur l'app e-CPS, recevoir la demande, **vérifier que le code affiché correspond**,
   valider.
6. **Attendu** : l'app bascule sur `/home`, session active (accès messagerie OK).
7. **Cas timeout** : relancer une connexion et **ne pas valider** sur e-CPS →
   après expiration, message FR « demande non validée / expirée », retour au
   formulaire RPPS.
8. **Cas RPPS invalide** : saisir un RPPS mal formé (ne commençant pas par 8, ou
   < 12 chiffres) → message d'erreur FR **sans appel réseau**.
9. **Pré-remplissage** : se déconnecter puis revenir sur l'écran de connexion →
   le **RPPS est pré-rempli** avec la dernière valeur utilisée (modifiable).
10. **Moyen secondaire** : vérifier que la **redirection PSC web** reste
    accessible et fonctionnelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie sécurisée de santé — socle
  d'authentification de l'app mobile)
- **Vague Ségur** : V2 (socle d'identification/authentification PSC / e-CPS)
- **Exigences DSR honorées** : authentification du PS via Pro Santé Connect /
  e-CPS, niveau eIDAS substantiel (PGSSI-S § authentification eIDAS) ; CIBA =
  flux d'authentification décrit par le service PSC pour le canal mobile
- **INS** : non applicable — la connexion authentifie un **professionnel** (RPPS),
  aucune manipulation d'identité patient
- **Authentification PS** : **e-CPS via CIBA** (canal `MOBILE`, validation
  découplée sur l'app e-CPS), niveau eIDAS **substantiel** ; le RPPS est fourni
  par le PS et contrôlé par l'IdP PSC en amont du proxy
- **Habilitations** : RPPS porté par le PS et vérifié par PSC ; `clientId`
  logiciel restreint à l'allowlist du proxy (déjà en place) ; aucune habilitation
  métier supplémentaire gérée par le mobile
- **Interop CI-SIS** : non applicable — pas d'échange de contenu métier (CDA/FHIR)
  dans ce flux
- **Tracé PGSSI-S** : journaliser (sans RPPS en clair) — initiation d'une demande
  CIBA, succès de connexion, échec/timeout/refus, déconnexion. La journalisation
  **probante longue durée (6 ans)** est assurée côté proxy/IdP ; le mobile se
  limite à des évènements UI non sensibles
- **Consentement patient** : non applicable — aucun traitement de donnée patient
- **Référentiels métier** : aucun (CIM-10/SNOMED/LOINC/CCAM/NABM/CIS-CIP non concernés)
- **Hébergement HDS** : non — le flux n'crée ni ne manipule de DSCP ; il établit
  une session authentifiée. Le token/session est conservé selon le mécanisme
  existant de l'app
- **AIPD / impact RGPD** : à signaler — nouveau **canal d'authentification** sur
  mobile (saisie + mémorisation locale du RPPS, identifiant professionnel) ;
  vérifier que la note RGPD/AIPD du périmètre mobile mentionne ce canal et le
  stockage local du RPPS

## DOD santé — items ajoutés

- [ ] Authentification PS via e-CPS (CIBA, canal MOBILE) testée bout-en-bout
      (manuel — Manual Test Plan)
- [ ] Aucune donnée sensible en clair dans les logs (RPPS notamment)
- [ ] Évènements journalisés côté mobile : initiation CIBA, succès, échec/timeout/refus
      (sans RPPS en clair)

## Branches
- `client-mobile` (pushed) : feat/task-136-mobile-ciba-ecps-login — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-136-mobile-ciba-ecps-login

## Stitch design log
- Projet : `client-mobile` (id `10088502293310567548`, MOBILE), design system « Clinical Precision ».
- Écran de référence réutilisé : **`login`** (id `84fe1a8c764344509857ef06a1696adc`) — base de marque conservée (logo disque + halo, titres, mention ANS).
- Génération d'un écran dédié `login-ecps` (form RPPS + état d'attente binding code) : **best-effort timeout** côté MCP Stitch (génération > 2 min). Non bloquant — l'intention a été traduite en Ionic à partir de l'écran `login` existant et des tokens du design system (Public Sans, primaire #005EB8, radii 4/8px, bouton primaire solide, input à label visible, code de liaison en `display-lg`). Renommage/refresh éventuel de l'écran Stitch = tâche humaine (le MCP n'a pas d'op rename).

## Develop log

- Repos touched : client-mobile (single frontend ; api-mail / client-angular / client-blazor non concernés)
- DTOs published : no DTO change (mobile consomme ses propres types TS ; proxy `/auth/connect` déjà livré, hors scope)
- Interop published : no interop change
- Commits :
  - client-mobile : 1da9212 feat(mobile): add CIBA e-CPS login (RPPS + decoupled validation)
- Local build / test : ✓ `npm run build` (0 erreur, warning budget scss non bloquant) ; ✓ `npm test --watch=false --browsers=ChromeHeadless` (263/263)
- DOD self-check (commandable) :
  - `AuthService.connectCiba(rpps)` → `src/app/core/auth/auth.service.ts` (binding message + POST `/auth/connect` MOBILE withCredentials + récup session via cookie + mémorisation RPPS) ✓
  - Helpers purs testés → `src/app/core/auth/ciba.util.ts` (+ `.spec`) : binding message (bornes 00–99), `isValidRpps` (`^8\d{11}$`), `mapCibaError` (400/404/408-504/409/503/0/générique, sans fuite) ✓
  - Tests `connectCiba` (succès e2e, RPPS invalide sans réseau, timeout 408, IdP 503, conflit 409, prefill) → `auth.service.spec.ts` ✓
  - Écran : form RPPS (prefill) + état d'attente binding code + bouton Annuler ; e-CPS = bouton principal, PSC = lien secondaire ; `data-testid` sur tous les interactifs ; libellés FR en dur → `login.page.{ts,html,scss}` (+ `login.page.spec.ts`) ✓
  - Aucun RPPS en clair dans logs/URL (transite uniquement dans le corps du POST ; mémorisé en localStorage pour prefill, jamais loggé) ✓
- Items déférés au test manuel (HAG) : validation e-CPS bout-en-bout réelle (sandbox PSC), comportement timeout réel du proxy, journalisation PGSSI-S côté proxy
- Next step : /forge-simplify task-136

## Simplify log
- Repos passed : client-mobile (seul repo touché ; api-mail / client-angular / client-blazor non concernés)
- Applied & committed : client-mobile : 3 fichiers (36aa64e)
  - `auth.service.ts` : extraction du pipeline partagé `/auth/token` → session (`mintSessionFromCookie`), mutualisé entre `refreshSession` et la connexion CIBA (axe reuse + altitude)
  - `login.page.ts` : suppression de l'état `submitting` write-only (la vue `form`/`waiting` pilote déjà l'UI) (axe simplification)
  - `login.page.scss` : fusion des règles dupliquées `.login-error` / `.session-expired` (axe simplification)
- No change : —
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-* (non touchés de toute façon)
- Conscious keeps (non appliqués) : refactor `authentication.page`/`$exchangeCodeForToken` (hors diff) ; déplacement persistance RPPS vers `AuthSessionService` (nit de couche marginal, ripple hors diff) ; `formatBindingMessage` (gagne ses tests de bornes 00–99 exigés par la DOD) ; branche défensive `RppsValidationError` côté page (fallback bon marché)
- Build / tests : ✓ green (263/263) sur client-mobile après la passe
- Next step : /lint-mobile task-136 (api-mail & client-angular non touchés → /sonar et /lint-angular skip)

## Lint mobile log

- Repo : client-mobile (Client/Mobile/, Ionic/Angular CLI)
- Commands : npm run lint
- Baseline : 0 errors / 0 warnings — « All files pass linting »
- Final    : 0 errors / 0 warnings
- Iterations : 0 / 5 (lint clean → no work, aucun commit nécessaire)
- Build / tests : ✓ green (vérifiés à l'étape /forge-simplify, 263/263)
- Next step : /review task-136

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/39 — label `awaiting-human-merge`
- Autres repos : non concernés (US single-frontend `client-mobile` ; pas de DTO/backend ; `psc-proxy-*` gérés manuellement)

## Code Review Summary
- Verdict : **APPROVED** (0 blocage)
- Build ✓ / Tests ✓ 263/263 (client-mobile)
- `channel` = `MOBILE`, `clientId` = `environment.authClientId` ✓
- Aucun RPPS en clair (logs/URL/messages) — corps du POST uniquement ; localStorage pour le pré-remplissage ✓
- ProblemDetails (RFC 7807) mappé en FR par status, sans fuite ✓
- Passe `/simplify` : extraction `mintSessionFromCookie`, suppression état `submitting` mort, fusion SCSS — ESLint clean
- Couverture : succès e2e, RPPS invalide sans réseau, timeout 408, IdP 503, conflit 409, prefill, bornes binding 00–99, mapping FR
- Items déférés au test manuel (HAG, rule 10) : validation e-CPS bout-en-bout réelle (sandbox PSC), comportement timeout réel du proxy, traçabilité PGSSI-S côté proxy

## Merged
- Date : 2026-06-29
- `client-mobile` : squash `021b51f` — PR #39 mergée (https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/39)
- Branche distante `feat/task-136-mobile-ciba-ecps-login` supprimée ; branche locale conservée
- Note : 8 commits de raffinement humains intégrés après /review (sélecteur de canal MOBILE/CARD, timeout client 5 min, endpoints proxy CIBA/Keycloak dédiés, bouton officiel Pro Santé Connect, reset d'écran à l'entrée)
- develop CI : aucun workflow configuré pour ce repo (rien à attendre)
