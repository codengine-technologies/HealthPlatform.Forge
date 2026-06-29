# todo-task-102-mobile-refresh-session-jwt.md — Prévoir le refresh de session JWT sur client-mobile

**Repos**: client-mobile
**Dependencies**: task-100
**Epic**: E012

> **US mono-repo justifiée** : le défaut observé est côté client-mobile (gestion de session/auth et retry HTTP). L'API expose déjà une erreur explicite d'expiration de token ; la parité attendue est avec le comportement de client-angular.

## Objective

Aligner `client-mobile` sur `client-angular` pour la gestion de session expirée :
quand un appel API échoue car le JWT est expiré, le mobile doit **tenter un
refresh de session**, puis **rejouer la requête initiale** si le refresh réussit.

Si le refresh échoue (session réellement expirée / invalide), l'utilisateur doit
être redirigé proprement vers `/login` avec un message explicite, sans écran
vide ni boucle d'erreurs.

## Problème observé

- Sur `GET /api/v1/mail/folders/INBOX`, le backend peut retourner une erreur
  mappée :
  `Result-mapped 500 ... JWT token has expired. Please refresh your session.`
- `client-mobile` ne met pas en œuvre le même mécanisme de refresh/retry que
  `client-angular`.
- Résultat utilisateur : échec de chargement de la boîte, expérience dégradée.

## Comportement attendu

- Détection centralisée d'une session expirée (statut/problème reconnu)
- Tentative unique de refresh de token/session
- Rejeu transparent de la requête initiale après refresh réussi
- En cas d'échec du refresh : purge de session locale + redirection `/login`
  + message utilisateur clair
- Aucune boucle infinie de retry

## Scénarios d'acceptation

1. **Token expiré, refresh OK** — Étant donné une session expirée, quand
   j'ouvre l'inbox, alors le client refresh la session puis recharge
   automatiquement les dossiers sans action manuelle.
2. **Token expiré, refresh KO** — Quand le refresh échoue, alors je suis
   redirigé vers `/login` avec un message "session expirée" et sans écran vide.
3. **Requête concurrentes** — Quand plusieurs requêtes échouent en même temps
   sur token expiré, alors le client n'exécute qu'un refresh effectif et rejoue
   correctement les requêtes en attente.
4. **Pas de régression** — Les appels normaux (token valide) conservent le
   comportement actuel, sans latence notable ni double appel.

## Definition of Done

- [ ] Build passe (`cd Client/Mobile && npm run build`, 0 erreur)
- [ ] Tests passent (`cd Client/Mobile && npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Gestion centralisée de l'expiration JWT implémentée (interceptor/service auth)
- [ ] Refresh + replay automatique de la requête initiale implémentés
- [ ] Anti-boucle en place (max 1 retry par requête)
- [ ] En cas d'échec refresh : logout technique, redirection `/login`, message utilisateur explicite
- [ ] Tests unitaires couvrant :
  - refresh réussi + replay
  - refresh échoué + redirection login
  - appels concurrents (single refresh)
- [ ] Aucun log contenant de donnée de santé ou token en clair

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC avec un compte de test
- Forcer un token expiré (ou attendre expiration de session)
- Ouvrir la vue inbox :
  - Vérifier qu'un refresh est tenté automatiquement
  - Vérifier que les dossiers/emails se rechargent sans re-login si refresh OK
- Simuler un refresh invalide :
  - Vérifier la redirection vers `/login`
  - Vérifier le message "session expirée" clair
- Vérifier qu'aucune boucle d'appels API n'apparaît dans l'onglet Network
- Comparer le comportement avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR** : robustesse d'accès MSS en session authentifiée PSC
- **Authentification PS** : PSC/e-CPS inchangé, amélioration de continuité de session
- **Sécurité** : pas de persistance/log de token en clair ; gestion d'expiration centralisée
- **AIPD / RGPD** : inchangé (durcissement technique du cycle de session)

## Branches (attendues via /start)

- `client-mobile` : `feat/task-102-mobile-refresh-session-jwt`

## Branches
- `client-mobile` (pushed) : feat/task-102-mobile-refresh-session-jwt — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-102-mobile-refresh-session-jwt

> Single frontend (client-mobile only). Dépend de task-100 (mergé).

## Décision (humain, 2026-06-18)
- Contrat de refresh : **re-POST `/auth/token` (withCredentials, sans `code`)** → `TokenAggregate`. Le BFF mint un nouvel access token via le cookie de session. Pas de refresh_token envoyé par le client.

## Develop log
- Repos : client-mobile
- MssHeadersInterceptor : détection expiration + single-flight refresh + replay + file d'attente + anti-boucle (HttpContext) ; échec → logout + /login?expired=1
- AuthService.refreshSession : re-POST /auth/token (cookie, sans code) → rebuild+save session ; login bannière ?expired=1
- Injector lazy pour AuthService (évite cycle HttpClient↔interceptor)
- Build ✓ · Tests ✓ 77/77 (7 nouveaux) · Lint ✓
- Commit : client-mobile @850ef64

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/7 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 77/77 · Lint ✓
- refresh ok/ko + concurrence (single refresh) + anti-boucle testés ; aucun token/donnée santé loggé ; FR + data-testid

## Merged
- Merged : 2026-06-19 (squash) by human authorization
- client-mobile : develop @d646546 (PR #7 closed)
- Local feature branch conservée
