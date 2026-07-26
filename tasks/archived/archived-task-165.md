# todo-task-165.md — Mobile : le refresh de session ne récupère pas après expiration du jeton

**Repos**: api-mail, client-mobile
**Dependencies**: —

> **Re-scopé 2026-07-17 (`api-mail` ajouté)** — vérification du code : le vrai
> fix est **backend**. `ImapConnectionService` renvoie `Result.Error(...)` sur
> jeton expiré → mappé **500**, et pour un 500 `ResultModelExtensions` renvoie un
> `detail` **générique** (« An unexpected error occurred ») — le message « expired »
> est droppé. D'où le réactif mobile (regex sur `detail`) **aveugle**. Le mapper
> gère déjà `ResultStatus.Unauthorized → 401` : il suffit de renvoyer
> **`Result.Unauthorized`** (→ 401) pour que le réactif mobile (déjà branché sur
> 401) fonctionne. **client-angular et client-blazor sont vérifiés robustes**
> (préventif + réactif sur 401) → aucun changement, le 401 est une amélioration
> transparente pour eux. Le mobile n'a besoin que d'un **durcissement du préventif**.

## Objective

Rétablir la **récupération automatique de session** sur l'app mobile : après
expiration de l'access token, l'app doit rafraîchir et rejouer de façon
transparente, sans que l'utilisateur soit éjecté ni que les écrans échouent en
boucle. Aujourd'hui, en test, l'app **continue d'envoyer un jeton expiré** à
`api-mail` alors même que le proxy sait le rafraîchir.

## Cause racine (analyse Seq 2026-07-17)

Timeline session mobile `n2ngms5T23n8dNv-a-Xcifoh` (user `robert.specialiste…`) :

- **09:45:05** — proxy `POST /v1/auth/refresh` : **SUCCÈS** (nouveau jeton
  Keycloak minté). → le refresh **fonctionne** côté serveur.
- **09:48:02 → 09:49:20** — `api-mail` logue de façon répétée
  `JWT token appears to be expired` (GetFolderToday, GetFolderNotSeenToday,
  GetFolders, `account/quota`), **~3 min après** le refresh réussi.
- **Aucun** `/api/v1/* StatusCode=401` sur la période → `api-mail` **ne renvoie
  pas 401** sur jeton expiré (mappé en 500, cf. `Result-mapped 500 … JWT token
  has expired` du 2026-07-12).

Deux défauts **côté mobile**, combinés :

1. **Détection réactive aveugle au 500** —
   [mss-headers.interceptor.ts](../../Client/Mobile/src/app/core/http/mss-headers.interceptor.ts)
   `isSessionExpired()` ne reconnaît l'expiration que sur `status === 401` ou un
   `detail` contenant `expired|refresh your session`. Derrière un **500 au
   `detail` assaini** (RFC 7807 sans fuite), la regex échoue → `refreshThenReplay`
   ne part **jamais** → la requête échoue sans refresh ni rejeu.
2. **Refresh préventif non fiable après un premier refresh** — le préventif
   (`isAccessTokenExpired`, exp-based via `accessTokenExpiresAt` lu du JWT dans
   [session.model.ts](../../Client/Mobile/src/app/core/auth/session.model.ts))
   devrait empêcher tout envoi expiré. Or des requêtes partent expirées 3 min
   après un refresh OK → à investiguer : la session fraîche est-elle bien
   **persistée et réappliquée** (`authSession.save`), `accessTokenExpiresAt`
   est-il **re-décodé** du nouveau jeton, et le préventif couvre-t-il **toutes**
   les requêtes API (y compris celles qui ne matchent pas `startsWith(mssApiUrl)`
   ou les jetons capturés en `?token=` des flux SSE) ?

## Comportement attendu

1. **Récupération transparente** : quand l'access token expire, la prochaine
   requête API déclenche un refresh (préventif si l'échéance est connue,
   réactif sinon) puis est rejouée avec le **jeton frais** ; l'utilisateur ne
   voit ni erreur ni déconnexion tant que le refresh token proxy est valide.
2. **Détection d'expiration robuste** : l'intercepteur reconnaît l'expiration
   **indépendamment du code HTTP** renvoyé par `api-mail` (401 idéalement, mais
   aussi le cas 500 actuel), sans boucler.
3. **Jeton frais réellement propagé** : après un refresh réussi, toutes les
   requêtes suivantes (et les flux SSE re-ouverts) portent le nouveau jeton ;
   `accessTokenExpiresAt` reflète le nouveau `exp`.
4. **Déconnexion propre en dernier recours** : si (et seulement si) le refresh
   token proxy est réellement invalide, purge + `/login?expired=1` (comportement
   actuel conservé).

## Definition of Done

- [ ] Build passe (`npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Le refresh préventif est fiable : après un refresh, `accessTokenExpiresAt` est re-décodé et la session fraîche persistée/réappliquée (test unitaire : 2 requêtes successives autour de l'échéance → 1 seul refresh, 2e requête avec le jeton frais)
- [ ] La détection d'expiration ne dépend plus du seul 401 : une réponse d'`api-mail` signalant l'expiration (401 **ou** le 500 actuel) déclenche un unique refresh + rejeu (test unitaire sur l'intercepteur)
- [ ] Anti-boucle préservé : au plus 1 refresh + 1 rejeu par requête (jetons `RETRIED`), pas de tempête
- [ ] Après refresh, un flux SSE ré-ouvert utilise le nouveau `?token=` (pas de jeton figé expiré)
- [ ] Déconnexion + `/login?expired=1` uniquement si le refresh proxy échoue réellement (test unitaire)
- [ ] Aucune donnée de santé en clair dans les logs client
- [ ] (Recommandé, hors ce repo) task api-mail : JWT expiré → **401** `ProblemDetails` au lieu de 500 — tracée à part

## Manual Test Plan

- Lancer `api-mail` + proxy PSC + mobile (`cd Client/Mobile && npm start`), session e-CPS valide
- Se connecter, laisser l'app ouverte jusqu'à expiration de l'access token (ou réduire sa durée de vie en env de test)
- Naviguer (onglet Accueil, ouvrir un mail, quota) : attendu → les écrans se chargent, l'app rafraîchit en silence, **aucune** éjection vers login
- Vérifier les logs Seq : plus de rafales `JWT token appears to be expired` sur la session mobile ; le proxy montre les refresh à la demande
- Forcer un refresh token proxy invalide (logout serveur) → l'app bascule proprement sur `/login?expired=1`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : socle — robustesse d'authentification, pas de nouvelle exigence DSR
- **Exigences DSR honorées** : PGSSI-S (gestion de session/expiration) — fiabilisation
- **INS** : non applicable — flux d'authentification, aucune donnée patient
- **Authentification PS** : e-CPS / PSC (eIDAS substantiel) — cœur du sujet ; le refresh conserve la session sans re-challenge tant que le refresh token est valide
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refresh/échec de refresh journalisés (proxy + client best-effort) ; pas de jeton en clair dans les logs
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — client
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement

## Branches
- `api-mail` (pushed) : feat/task-165-session-refresh-recovery — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-165-session-refresh-recovery
- `client-mobile` (pushed) : feat/task-165-session-refresh-recovery — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-165-session-refresh-recovery
- `client-angular` / `client-blazor` : hors scope (vérifiés robustes — gèrent déjà le 401)

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/118 — label `awaiting-human-merge`
- `client-mobile` : **aucun changement** (vérifié : réactif gère déjà le 401 + préventif re-décode `accessTokenExpiresAt` au refresh) → branche supprimée, pas de PR
- `client-angular` / `client-blazor` : hors scope (robustes, gèrent déjà le 401)

## Develop log
- 2026-07-17 — cœur du fix = api-mail : jeton expiré `Result.Error`(500) → `Result.Unauthorized`(401), message surfacé au `detail`. Commit 5eccc73.
- Vérification frontends : mobile/Angular/Blazor gèrent déjà le 401 → aucun changement client (le mobile « durcissement préventif » envisagé s'est avéré inutile, le code re-décode déjà l'exp). 
- Build ✓ 0/0 ; ResultExtensions 31 ✓ (dont test Unauthorized+message) ; ImapConnection 14 ✓. PR #118 en attente merge humain (HAG).

## Merged
- 2026-07-17 — squash-merge sur `develop` (`--i-tested`)
- `api-mail` : 6c5a476 (PR #118 fermée) — jeton expiré → 401
- `client-mobile`/`angular`/`blazor` : aucun changement (gèrent déjà le 401)
