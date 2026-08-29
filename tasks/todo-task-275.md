# todo-task-275.md — Le mobile garde sa session tant que le refresh PSC vit : validation du modèle « token Keycloak jetable »

**Repos**: client-mobile
**Dependencies**: psc-auth-proxy/task-015 (refresh PSC-primaire par re-échange — autre forge, dépôt `D:\Workspaces\psc-auth-proxy`)
**Epic**: E012

## Objectif

Côté proxy (psc-auth-proxy/task-015), le refresh de session mobile change de
modèle : **le seul refresh token consommé est celui de PSC** ; le jeton Keycloak
n'est plus rafraîchi mais **re-frappé** à chaque `/auth/refresh` (re-échange JWT
Authorization Grant), porteur des claims `mssEmail`/`mssRpps` à jour. Il n'existe
plus ni session Keycloak ni refresh token Keycloak — l'agrégat rendu au mobile a
un champ `refreshToken` **vide**, et son `refreshTokenExpirationDateUtc` vaut
l'échéance du refresh token **PSC**.

L'analyse du code mobile (étude psc-auth-proxy
`questions/task-014-session-persistante.md` §7.6, 2026-08-29) conclut que
`client-mobile` est **déjà compatible** : le refresh est cookie-based sur
`authEndpoint` (`/auth/refresh`, single-flight dans `mss-headers.interceptor`),
l'échéance préventive est lue de l'`exp` du JWT lui-même, et le champ
`refreshToken` de l'agrégat n'est jamais lu (`AuthSession` ne le porte pas).

Cette US **verrouille** cette compatibilité au lieu de la supposer : tests qui
épinglent les invariants, et validation E2E du parcours complet sur le nouveau
modèle. Elle n'introduit **aucun changement de comportement**.

**Endpoints — aucune bascule.** Le refresh reste sur `authEndpoint`
(`/auth/refresh` du proxy Keycloak, :8081 en local) : c'est l'instance qui
détient les credentials Keycloak du re-échange (le déploiement PSC les exclut
volontairement — bordereau psc-auth-proxy). Fonctionnellement, ce refresh ne
consomme QUE le refresh token PSC ; le CIBA (`/auth/connect`, cookie BFF) reste
sur `cibaEndpoint` (:7129). Toute bascule du refresh vers `cibaEndpoint` est
**hors périmètre** et exigerait un arbitrage bordereau (credentials Keycloak sur
le déploiement PSC).

**Hors périmètre** : tout changement du proxy (porté par psc-auth-proxy/task-015) ;
toute modification des endpoints d'environnement ; tout nouveau traitement du code
d'erreur de re-échange (RG-3 côté proxy : l'échec de refresh conserve le
comportement actuel — purge locale + `/login?expired=1`).

## Definition of Done

- [ ] Build passes (`npm ci && npm run build`), tests pass
      (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Test unitaire : la construction d'`AuthSession` depuis un agrégat dont
      `refreshToken` est **vide** produit une session valide (accessToken,
      `mssEmail`, `accessTokenExpiresAt` lus normalement)
- [ ] Test unitaire : `refreshSession()` avec une réponse `/auth/refresh` au
      nouveau format (refreshToken vide, accessToken re-frappé avec un `exp`
      neuf) met à jour `accessTokenExpiresAt` ET `mssEmail` (claims re-dérivés)
- [ ] Test unitaire : l'intercepteur déclenche le refresh préventif sur
      l'échéance du jeton re-frappé (pas de dépendance à
      `refreshTokenExpirationDateUtc`)
- [ ] Test unitaire : un échec de `/auth/refresh` (ProblemDetails, code proxy
      de re-échange) suit le chemin existant purge + `/login?expired=1` —
      aucun traitement spécial du nouveau code
- [ ] Aucun changement dans `src/environments/*` ni dans les URL d'auth
- [ ] Aucune régression sur les specs existantes d'`auth.service` /
      `mss-headers.interceptor` / `auth-session.service`

## Manual Test Plan

Pré-requis : psc-auth-proxy sur la branche portant task-015 (les deux AppHost
lancés), api-mail lancé, app mobile `npm start` (http://localhost:8100).

1. Login e-CPS complet (RPPS de test, code d'appairage validé dans l'appli) →
   boîte de réception affichée (`mssEmail` résolu, pas d'onboarding).
2. Laisser l'app ouverte **> 5 minutes** (expiration de l'access token
   Keycloak), puis ouvrir un dossier et un mail avec pièce jointe :
   **attendu** — navigation fluide, aucun retour au login, la PJ s'ouvre
   (chemin IMAP complet re-validé après refresh).
3. Répéter l'attente et la navigation une seconde fois (2 refresh successifs =
   la rotation PSC est bien re-persistée par le proxy à chaque tour).
4. Dans Seq (seq-local) : événements de refresh PSC-primaire visibles, aucun
   jeton en clair.
5. Console Keycloak (realm weda-realm) : **aucune session** pour le client
   `weda` — comportement attendu du modèle (session transiente), ne pas
   instruire comme un défaut.
6. Mode dégradé : arrêter le conteneur Keycloak, attendre l'expiration du
   jeton, naviguer → retour `/login?expired=1` propre (pas d'écran blanc, pas
   de boucle) ; redémarrer Keycloak, re-login e-CPS → OK.

## Notes pour /develop

- Les invariants à épingler vivent dans `src/app/core/auth/`
  (`session.model.ts`, `auth.service.ts`, `auth-session.service.ts`) et
  `src/app/core/http/mss-headers.interceptor.ts`. **Aucun code de production ne
  devrait changer** — si un test révèle une dépendance réelle au refreshToken de
  l'agrégat ou à `refreshTokenExpirationDateUtc`, la corriger fait partie de
  l'US (et la consigner).
- Le champ `refreshToken` reste déclaré dans `TokenAggregate` (contrat de
  réponse proxy inchangé, RG-6 de task-015) — ne pas le supprimer du type.
