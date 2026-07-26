# todo-task-171.md — Backend pull du token PSC : api-mail va chercher le token auprès du psc-auth-proxy

> ⏸️ **ON HOLD (décision humaine 2026-07-25)** — à réactiver lorsque api-mail sera
> servi sous `*.weda.fr` (prérequis du transport cookie, cf. `questions/answered/task-171.md`).
> Pour réactiver : redéplacer ce fichier dans `tasks/` puis `/start 171`.

**Repos**: api-mail
**Dependencies**: —
**Epic**: E013
**EpicTitle**: Refonte du cycle de vie du token PSC (backend pull via proxy)
**Single frontend**: true

> **Référence** : ADR-2026-07-25 « [PSC] Stratégie Refresh Token PSC Backend Pull Via Proxy »
> (OneDrive · 03-Technical-Architecture · Architecture Decision Record).
> Cette US couvre les chantiers 1 à 4 de l'ADR. Le chantier 5 (clients) est task-172.

## Objective

Aujourd'hui les clients rafraîchissent l'access token PSC (~2 min de TTL) pour le
pousser à `api-mail` dans le header `X-PSC-Token` à chaque requête, alors que le
backend ne le consomme qu'à l'ouverture/ré-authentification des sessions IMAP/SMTP
MSSanté (XOAUTH2). Cette US inverse le flux : **`api-mail` résout lui-même l'access
token PSC auprès du psc-auth-proxy, au moment où il en a besoin**, en rejouant le
cookie `proxy_session_id` reçu du navigateur sur l'endpoint **existant**
`POST {proxy}/v1/session/token` (le proxy introspecte, rafraîchit si besoin, renvoie
les tokens — aucune modification côté proxy).

**US backend uniquement (justification)** : le header `X-PSC-Token` reste accepté en
fallback (header présent → prioritaire ; absent → résolution via cookie), donc les
clients existants fonctionnent sans changement. La US est fonctionnellement complète
et testable de bout en bout à elle seule (règle 11 respectée). L'arrêt du push côté
clients est la task-172, dépendante de celle-ci.

### Contenu (chantiers 1–4 de l'ADR)

1. **`IPscTokenProvider`** (nouveau service + client HTTP dédié) :
   - config URL du proxy dans `appsettings.json` (dev : `https://localhost:8081/v1`),
     timeout court (≤ 5 s) ;
   - appel `POST /v1/session/token` en forwardant le cookie
     (`Cookie: proxy_session_id=...`) + header `X-Caller: api-mail` ;
   - ne conserve du `TokenInfoDto` que `PscAccessToken` + date d'expiration —
     les refresh tokens sont jetés immédiatement, jamais stockés, jamais loggés ;
   - **deux caches par session, découplés** (pas de refresh cadencé — pull pur) :
     - *cache token* : access token PSC gardé jusqu'à `expiration − 30 s`,
       consulté **uniquement aux instants d'authentification** IMAP/SMTP
       (première connexion, reconnexion après idle, envoi). Entre deux
       connexions, l'access token peut expirer sans conséquence : le proxy en
       re-mint un à la demande (refresh token 30 min) ;
     - *cache mode* : verdict « PSC obtenable » (propriété de la session, pas de
       l'access token), TTL ~5 min, positif comme négatif. Rafraîchi
       opportunément par tout appel token. **Ne jamais indexer le mode sur
       l'expiration de l'access token** — sinon on recrée le rythme ~2 min du
       client pendant la navigation active ;
     - dédup des appels concurrents (single-flight) ; un appel
       `/v1/session/token` alimente les deux caches (jamais d'introspection
       séparée). Rythme cible en régime établi : ~1 appel mode / 5 min / session
       active + 1 appel par (ré)ouverture de connexion IMAP/SMTP ;
   - **verdicts négatifs du cache mode** (protection du proxy — sans eux, les cas
     sans token martèleraient le proxy à chaque requête) : session sans PSC
     (`PscAccessToken` vide, cas Keycloak-only) → « offline » caché ~5 min par
     session id (stable par construction : un login PSC crée une nouvelle session,
     donc un nouveau session id → réévaluation immédiate) ; session
     expirée/invalide → « offline » caché ~60 s ;
   - **circuit breaker** (Polly) sur le client HTTP proxy : après N échecs,
     circuit ouvert ~30 s → toute évaluation de mode bascule offline
     instantanément (le timeout de 5 s ne se paie qu'aux transitions, jamais en
     rafale), reprise via half-open ;
   - **évaluation paresseuse** : le middleware pose un résolveur lazy, la
     résolution n'a lieu qu'au premier accès effectif au mode ou au token dans la
     requête ;
   - erreurs typées (règle 12 ProblemDetails) : session absente/expirée →
     `UnauthorizedException` (401), proxy indisponible → `UnavailableException` (503).
2. **Résolution middleware + fallback + mode online/offline** :
   `UserContextEnricherMiddleware` lit le cookie `proxy_session_id` entrant ;
   `X-PSC-Token` reste prioritaire s'il est présent (transition).
   **Attention — la présence du cookie ne suffit PAS à déclarer le mode online** :
   le proxy accepte des sessions Keycloak-only (login mot de passe, sans PSC), et
   le cookie peut survivre à la session Redis. La règle devient :
   *online ⇔ un token PSC est effectivement obtenable* — header présent, OU
   résolution non bloquante via `IPscTokenProvider.TryGet` (cache par session ;
   `PscAccessToken` vide/session expirée/proxy injoignable → **offline**, comme un
   header absent aujourd'hui : lecture cache DB, actions en attente, aucune 5xx
   sur les lectures, cause tracée). Le middleware pose un **indicateur de mode
   explicite** dans `UserContextInfo` ; `ConnectionModeService` (dont
   `CanSendEmail`, qui lit aujourd'hui la string `PscToken`) consomme cet
   indicateur et non plus la présence du token brut. Le cross-check identité
   PSC↔Keycloak existant s'applique au token résolu (via proxy ou header).
3. **Points de consommation** : `ImapConnectionService`, `SmtpConnectionFactory`,
   `BackgroundImapService` obtiennent le token via `IPscTokenProvider` juste avant
   chaque `AuthenticateAsync`, au lieu de lire un token figé dans `UserContextInfo`.
   La garde « token expiré → 401 » est remplacée par la résolution d'un token frais
   (le 401 ne subsiste que si la session proxy elle-même est expirée).
4. **Background sync** : `BackgroundSyncManager` mémorise le **session id** (plus de
   snapshot de token) et résout un token frais à chaque (ré)authentification — le
   sync long survit aux expirations tant que la session proxy vit (30 min glissants).

5. **CORS api-mail — passage en mode credentialed** : la policy actuelle
   (`CorsPolicySetup.cs`, task-092) n'appelle **pas** `.AllowCredentials()` — son
   commentaire dit explicitement « Bearer tokens (no cookies) ». Sans cela, le
   navigateur n'enverra jamais le cookie `proxy_session_id` en cross-origin.
   Ajouter `.AllowCredentials()` (whitelist d'origines exactes uniquement —
   jamais de wildcard avec credentials), mettre à jour le commentaire de la
   classe et les tests d'intégration CORS existants. Vérifier aussi les flux
   SSE (`MailEventsController`, `NotificationsController`) : côté client,
   `EventSource`/fetch devront être `withCredentials` si ces endpoints
   consultent le mode (à couvrir en task-172).

### Prérequis de déploiement — domaine d'api-mail (BLOQUANT hors dev)

Le transport par cookie exige qu'api-mail soit servi sous un hôte du domaine
`.weda.fr` (portée du cookie proxy). Or les environnements actuels pointent vers
`https://mss-api.xsd2code.com` (`environment.prod.ts` Angular **et** mobile) —
**le cookie ne partira jamais vers ce domaine**. En dev local, aucun problème
(cookie host-only `localhost`, les ports sont ignorés). Question ouverte à
l'humain : `questions/task-171.md` (bascule DNS vers `mss-api.weda.fr` ou
équivalent, vs plan B transport par header). L'implémentation et les tests de la
US restent entièrement réalisables en local sans attendre cette réponse.

### Hors scope

- Toute modification du workspace `psc-auth-proxy` (décision ADR : endpoint dédié
  écarté, triggers de réouverture documentés).
- Toute modification des clients (task-172).
- Retrait du fallback `X-PSC-Token` et du contrat 401-refresh task-165 (chantier 6,
  task de nettoyage en fin de transition).
- TTL de l'access token Keycloak (levier realm `weda-realm`, hors périmètre ADR).

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors 3 flaky pré-existants documentés) — `dotnet test`
- [ ] Unit tests `IPscTokenProvider` : cache token (hit / miss / expiration à
      `exp − 30 s`) / cache mode découplé (verdict valable ~5 min même quand
      l'access token caché est expiré — pas de réévaluation au rythme du token) /
      dédup d'appels concurrents / session expirée → 401 typé /
      proxy indisponible → 503 typé (≥ 1 test par branche)
- [ ] Unit tests middleware / mode : fallback header prioritaire ; online avec
      cookie + session PSC valide ; **offline** avec cookie + session Keycloak-only
      (sans PSC) ; **offline** avec cookie invalide/session expirée ; **offline**
      (dégradé, tracé) avec proxy injoignable à l'évaluation du mode ; offline
      sans header ni cookie
- [ ] `ConnectionModeService` (`CanSendEmail` inclus) basé sur l'indicateur de mode
      posé par le middleware, plus sur la présence de la string `PscToken` ;
      comportement offline existant (cache DB, pending actions) non régressé
      (tests `MailDataProviderFactory`/`PendingActionService` verts)
- [ ] Integration test endpoint (règle 1b) : requête avec cookie `proxy_session_id`
      **sans** `X-PSC-Token` → le token est résolu via le provider (proxy mocké) et
      l'authentification IMAP reçoit ce token ; requête avec header seul → chemin
      legacy inchangé
- [ ] Integration test : proxy indisponible à l'**évaluation du mode** → bascule
      offline tracée, lecture des dossiers servie depuis le cache (pas de 5xx) ;
      proxy indisponible au moment d'une **authentification IMAP/SMTP déjà engagée
      en mode online** → `application/problem+json` 503 (règle 12), aucun
      try/catch ad hoc dans les controllers
- [ ] `BackgroundSyncManager` ne stocke plus de token (grep : plus de snapshot
      `JwtToken` capturé au démarrage du sync) — test unitaire sur la résolution
      à la ré-authentification
- [ ] Aucun token (PSC/Keycloak/refresh), aucun `TokenInfoDto` sérialisé, aucun
      session id en clair dans les logs (revue des appels logger sur le code neuf)
- [ ] Timeout de l'appel proxy ≤ 5 s, configuré et testé
- [ ] Charge proxy bornée : unit tests prouvant qu'une série de requêtes sur une
      même session ne produit qu'**un** appel proxy par fenêtre de cache mode
      (~5 min) — y compris dans les cas négatifs (session Keycloak-only, session
      expirée, circuit ouvert) ; l'access token n'est demandé qu'aux instants
      d'authentification IMAP/SMTP ; jamais d'appel proxy par requête HTTP ;
      aucun timer/refresh périodique dans api-mail (pull pur)
- [ ] Circuit breaker testé : N échecs → circuit ouvert → évaluations de mode
      offline sans appel réseau ni timeout ; reprise en half-open
- [ ] `X-PSC-Token` toujours fonctionnel (aucune régression pour les clients actuels)
- [ ] CORS : `.AllowCredentials()` actif avec whitelist d'origines exactes (jamais
      de wildcard) ; tests d'intégration `CorsPolicySetup` mis à jour (preflight
      credentialed accepté depuis une origine whitelistée, refusé sinon)

## Manual Test Plan

Prérequis : psc-auth-proxy lancé (workspace `D:\Workspaces\psc-auth-proxy`, AppHost
Aspire), `api-mail` lancé (`cd Api/Mail && dotnet run` ou AppHost), un compte PS de
test avec boîte MSSanté de test.

1. **Chemin nominal (pull via cookie)** — se connecter via PSC sur le client Angular
   (`https://localhost:4200`) pour obtenir une session proxy. Récupérer le cookie
   `proxy_session_id` (DevTools → Application → Cookies) et le token Keycloak.
   Appeler `api-mail` en curl **sans** header `X-PSC-Token` :
   `curl -H "Authorization: Bearer {kc}" -H "Client-Email: {mss}" --cookie "proxy_session_id={sid}" https://localhost:7012/api/...folders`
   → la liste des dossiers IMAP se charge (le backend a résolu le token via le proxy).
2. **Fraîcheur** — attendre > 2 min (expiration de l'access token PSC), rejouer le
   même curl → toujours 200, sans intervention client (le proxy a rafraîchi).
3. **Fallback préservé** — utiliser le client Angular normalement (il pousse encore
   `X-PSC-Token`) : messagerie fonctionnelle, aucune régression visible.
4. **Session expirée / cookie invalide** — rejouer le curl du point 1 avec un
   cookie invalide → réponse 200 en **mode offline** (`GET .../connection/status`
   → `mode: "offline"`, dossiers servis depuis le cache DB), aucun 5xx ; logs Seq
   sans token ni session id en clair.
5. **Proxy éteint** — arrêter le proxy, rejouer le curl du point 1 → lecture en
   mode offline (dégradé, cause tracée dans Seq). Relancer le proxy, session
   valide, puis l'arrêter **après** chargement (mode online, cache token chaud) et
   forcer une reconnexion IMAP après expiration du cache → `application/problem+json` 503.
6. **Session Keycloak-only (sans PSC)** — se connecter en login/mot de passe (sans
   broker PSC) : `connection/status` → `mode: "offline"`, lecture cache OK,
   comportement identique à aujourd'hui sans `X-PSC-Token`.
7. **Sync background** — déclencher un sync, laisser tourner > 5 min → le sync ne
   meurt plus sur expiration de token (vérifier les logs Seq : pas d'
   `AuthenticationException` XOAUTH2).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — refactoring d'architecture sécurité, aucune
  exigence DSR nouvelle ; conforme à la trajectoire ANS token-secure du proxy
  (US-PROXY-2026-001)
- **Exigences DSR honorées** : non applicable — pas de nouvelle exigence ;
  renforce PGSSI-S (le token PSC ne transite plus par le navigateur à terme)
- **INS** : non applicable — aucune manipulation de données patient
- **Authentification PS** : PSC via psc-auth-proxy, niveau eIDAS substantiel —
  inchangée ; seule la mécanique de distribution de l'access token change
- **Habilitations** : inchangées — cross-check identité PSC↔Keycloak (sub/RPPS)
  conservé côté api-mail, appliqué au token résolu via le proxy
- **Interop CI-SIS** : non applicable — aucun échange métier modifié
- **Tracé PGSSI-S** : journaliser (Seq, corrélés par traceId) : échec de résolution
  de token (session expirée, proxy indisponible), échec d'authentification
  IMAP/SMTP — sans token, refresh token, ni session id en clair ; conservation
  identique à l'existant (6 mois logs techniques)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant d'api-mail, inchangé
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau ; réduction de
  l'exposition des tokens (défense en profondeur)
