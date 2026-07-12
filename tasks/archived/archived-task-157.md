# todo-task-157.md — Refresh préventif du jeton sur mobile (parité stratégie Angular)

**Repos**: client-mobile
**Dependencies**: —
**Single frontend**: true

## Objective

Compléter la stratégie de rafraîchissement de session du client mobile avec le
**volet préventif** présent dans `client-angular` : avant d'envoyer une requête
vers l'API MSS, si l'access token est **connu expiré (ou expire imminemment)**,
rafraîchir la session **d'abord**, puis envoyer la requête avec le jeton frais.

### Pourquoi

- Le mobile est le client au **profil d'usage intermittent** : l'app revient
  du premier plan après des minutes/heures de veille. Aujourd'hui, chaque
  reprise paie systématiquement **trois allers-retours** (requête → 401 →
  refresh → rejeu) sur réseau mobile, là où un seul suffirait.
- Parité comportementale avec Angular, qui vérifie la validité du jeton avant
  chaque requête (horloge réactive) et ne subit le 401 qu'en dernier recours.

### Existant à conserver (ne pas régresser)

- Le **volet réactif** actuel de l'intercepteur MSS reste le filet de
  sécurité : 401 → un refresh mutualisé (anti-boucle, file d'attente des
  requêtes concurrentes) → rejeu ; échec du refresh → purge de session +
  redirection `/login?expired=1`.
- Architecture inchangée : pas de refresh token stocké côté mobile — le
  rafraîchissement passe par le cookie de session du proxy (BFF). La parité
  porte sur le comportement, pas sur le stockage des jetons.

### Comportement attendu

1. L'échéance de l'access token (portée par le jeton lui-même) est connue de
   la session locale.
2. Avant chaque requête API MSS : jeton encore valide (avec une petite marge
   de sécurité, de l'ordre de quelques dizaines de secondes) → envoi direct ;
   jeton expiré ou dans la marge → **refresh d'abord** (mutualisé avec le
   mécanisme existant — jamais deux refresh concurrents), puis envoi.
3. Si le refresh préventif échoue → même issue que le réactif : purge +
   `/login?expired=1`. Pas de nouveau chemin d'erreur.
4. Les endpoints hors API MSS (BFF d'authentification) restent exclus,
   comme aujourd'hui.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Jeton valide → la requête part immédiatement, sans appel de refresh (testé)
- [ ] Jeton expiré (ou dans la marge) → refresh **avant** l'envoi, puis requête avec le jeton frais ; un seul refresh pour N requêtes concurrentes (testé avec timers fake)
- [ ] Échec du refresh préventif → purge de session + redirection `/login?expired=1` (testé)
- [ ] Volet réactif inchangé : les tests existants de l'intercepteur restent verts (401 imprévu → refresh → rejeu)
- [ ] Endpoints du BFF d'authentification toujours exclus du mécanisme (testé)
- [ ] Aucun jeton ni donnée de santé dans les logs client
- [ ] Aucun changement d'UI (pas de nouvel élément interactif, pas de `data-testid` requis)

## Manual Test Plan

- `cd Client/Mobile && npm start` ; se connecter
- Laisser l'app inactive au-delà de la durée de vie de l'access token (ou
  raccourcir artificiellement l'échéance côté proxy pour accélérer le test)
- Revenir sur l'inbox et déclencher un rafraîchissement (pull-to-refresh) :
  - dans l'onglet Réseau des outils développeur, observer **un appel de
    refresh PUIS l'appel API** — aucun 401 ne doit apparaître
- Supprimer le cookie `proxy-session-id` puis refaire la manœuvre → arrivée
  sur `/login?expired=1` (comportement existant, non-régression)
- Usage nominal (jeton frais) : navigation fluide, aucun appel de refresh
  superflu dans l'onglet Réseau

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — optimisation d'un mécanisme d'authentification existant
- **Exigences DSR honorées** : non applicable — hygiène de session
- **INS** : non applicable
- **Authentification PS** : cœur de la US — continuité de session e-CPS/PSC sans friction ni fenêtre d'usage d'un jeton expiré ; le refresh reste porté par le cookie de session BFF (aucun secret durable côté app)
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refresh tracé côté proxy (canal existant) ; aucun jeton en log client
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-157-preventive-token-refresh — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-157-preventive-token-refresh

## Develop log

- Repos touched : `client-mobile` (US mono-repo, single frontend)
- DTOs published : no DTO change · Interop published : no interop change
- Commits :
  - client-mobile : `929f48e` feat(mobile): refresh préventif du jeton (parité stratégie Angular)
- Local build / test : ✓ `npm run build` (0 erreur) · `npm test … ChromeHeadless` (**438 SUCCESS**, +6 vs baseline 432)
- Implémentation :
  - `session.model.ts` : `AuthSession.accessTokenExpiresAt` (epoch ms) dérivé de la
    claim `exp` du JWT dans `sessionFromTokenAggregate` (« échéance portée par le
    jeton lui-même »). Absente → préventif désactivé (fallback sûr).
  - `mss-headers.interceptor.ts` :
    - **volet préventif** : avant l'envoi, `isAccessTokenExpired(session)` (marge
      30 s) → `refreshThenReplay` (refresh d'abord, puis envoi avec jeton frais) ;
    - **refresh mutualisé factorisé** (`refreshSessionShared`) partagé entre
      préventif et réactif → jamais deux refresh concurrents ; échec → purge
      (`authSession.logout()`) + `/login?expired=1` ;
    - **volet réactif inchangé** : 401 imprévu → `refreshThenReplay` (même méthode),
      marqueur `RETRIED` anti-boucle conservé ;
    - endpoints hors `session.mssApiUrl` (BFF auth) toujours exclus.
- DOD self-check : build ✓, tests ✓ ; jeton valide→envoi direct sans refresh ✓ ;
  expiré/marge→refresh avant envoi + jeton frais ✓ ; un seul refresh N concurrents ✓ ;
  échec préventif→purge+/login?expired=1 ✓ ; réactif inchangé (tests existants verts) ✓ ;
  BFF exclu ✓ ; aucun jeton/donnée santé en log ✓ ; aucun changement d'UI ✓.
- Next step : /forge-simplify task-157

## Simplify log

- Repos passed : `client-mobile`
- Applied & committed : — (aucune simplification appliquée)
- No change : `client-mobile` — le refactor `/develop` a déjà factorisé le refresh
  mutualisé (`refreshSessionShared`, partagé préventif + réactif = axe reuse/DRY
  appliqué d'emblée) ; `session.model` minimal ; tests avec factories. RAS.
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ verts (inchangés depuis /develop)
- Next step : /lint-mobile task-157 (api-mail & client-angular non touchés → /sonar & /lint-angular skip)

## Lint mobile log

- Repo : `client-mobile` (feat/task-157-preventive-token-refresh)
- Baseline `ng lint` : **All files pass linting** — 0 error, 0 warning, 0 fixable
- Iterations : aucune (code frais conforme à `conventions/angular.md` — TS pur, pas de template)
- Commit : aucun (rien à corriger)
- Next step : /verify-visual task-157

## Visual verify log

- **Skip clean** — aucun écran touché (diff = intercepteur HTTP + `session.model`,
  aucun template/SCSS/page). Rien à capturer. Aucun changement d'UI (DOD).
- Écrans capturés : 0 / 0
- Next step : /review task-157

## PRs

- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/47 — label `awaiting-human-merge`

## Code Review Summary

- Verdict : **APPROVED** — 0 bloquant.
- Build ✓ (`npm run build` 0 erreur) · Tests ✓ (**438 SUCCESS**, +6) · `ng lint` All files pass · Vérification visuelle : skip clean (aucun écran).
- **Correctness** : `isAccessTokenExpired` fallback sûr (échéance inconnue → préventif off) ;
  préventif + réactif partagent `refreshSessionShared` (mutualisé) ; comportement réactif
  préservé (tests existants verts).
- **Anti-boucle** : un seul refresh pour N concurrents (`isRefreshing`/`refreshed$`) ; rejeu unique (`RETRIED`).
- **Security** : aucun jeton/donnée de santé en log.
- **Test coverage** : 6 tests (valide→direct, expiré & marge→refresh-first, single-refresh N concurrents, échec→purge+login, BFF exclu).
- DOD : tous les items vérifiables par commande ✓ ; comportement réseau (un refresh puis appel, pas de 401) déféré au test manuel humain (HAG).
- Qualité : /sonar skipped — api-mail non touché.

## Merged

- Merged : 2026-07-11 (human-triggered `/merge --i-tested`)
- Squash commits :
  - client-mobile : `26d3bad` (PR #47 squash-merged & closed, remote branch deleted, local kept)
- develop CI : https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/29146101860 (in progress at merge time — see report)
