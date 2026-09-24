# todo-task-171.md — Le jeton PSC ne transite plus par le client : api-mail le résout auprès du proxy, les clients cessent de le transporter, l'en-tête `X-PSC-Token` disparaît

> ▶️ **RÉACTIVÉE le 2026-09-23 (décision humaine)** — après deux mois on hold
> (2026-07-25, attente de la bascule d'api-mail sous `*.weda.fr`). La réactivation
> vaut décision de **construire et valider la US en local dès maintenant** ; le
> transport cookie hors dev reste conditionné au domaine (section « Prérequis de
> déploiement »).
>
> ✏️ **Refondue le 2026-09-23 en une seule US complète** (décision humaine) : elle
> réunit le backend pull d'origine (chantiers 1–4 de l'ADR), le **retrait du volet PSC
> dans les trois clients** (ex-task-172, chantier 5 — étendu à Blazor, qui manquait), et
> le **retrait du fallback `X-PSC-Token` côté API** (chantier 6, qui n'avait jamais eu
> de task). Plus de transition, plus de réglage temporaire : à la fin de cette US,
> **aucun composant ne lit ni n'écrit `X-PSC-Token`**. Règle 11 : la US se valide
> assemblée, pas par morceaux.
>
> ✏️ **Absorbe task-318** (remédiation n°1 de l'audit sécurité du registre du
> 2026-09-16). La liaison compte ↔ professionnel que 318 tentait de reconstruire à
> partir de deux jetons fournis par le client est ici **lue dans la session du proxy**,
> où elle a été établie au login. Voir « Liaison compte ↔ professionnel » et l'encadré
> « Remplace task-318 ».

**Repos**: api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: **proxy `task-016`** (`D:\Workspaces\psc-auth-proxy\tasks\todo-task-016-contexte-psc-pour-api-mail.md`) — mergée **et déployée** sur l'environnement testé : elle porte l'endpoint `GET /v1/internal/psc-context` que cette US consomme. Sans elle, le backend pull n'a pas de point d'entrée sûr (voir « Référence », addendum ADR).
**Epic**: E013
**EpicTitle**: Refonte du cycle de vie du token PSC (backend pull via proxy)

> **Référence** : ADR-2026-07-25 « [PSC] Stratégie Refresh Token PSC Backend Pull Via Proxy »
> (OneDrive · 03-Technical-Architecture · Architecture Decision Record). Cette US
> couvre les **six chantiers** de l'ADR. Elle porte aussi la **règle de liaison compte
> ↔ professionnel** issue de task-318 (Epic E016, audit du registre).
>
> `client-angular` est en mode **code-only** : l'humain choisit la branche dans
> `Client/Angular/` avant `/start`, la forge écrit le code, l'humain commit/push/PR TFS.
> Aucun écran n'est modifié : pas de passage `/stitch-design` ni `/verify-visual`.
>
> **Addendum ADR-2026-07-25 (2026-09-23) — l'endpoint dédié revient.** L'ADR écartait
> tout endpoint proxy dédié au profit de `POST /v1/session/token`. Il l'écrivait avant
> le passage au JWT Authorization Grant (proxy task-014/015, bordereau Keycloak 1.15.0)
> et avant la lecture du code du 2026-09-23. Trois faits l'invalident : (1)
> `/v1/session/token` ne rafraîchit que sur l'échéance **Keycloak**, jamais sur celle du
> jeton **PSC** dont `api-mail` a besoin ; (2) sa branche de refresh est **sans verrou**
> alors que le refresh token PSC **tourne** (usage unique) — un second rafraîchisseur
> côté serveur crée une course qui déconnecte le praticien ; (3) chaque refresh
> **prolonge la session de 30 min**, ce qui ferait du sync de fond un keep-alive sans
> présence humaine. Le proxy reçoit donc `GET /v1/internal/psc-context` (task-016 du
> proxy) : refresh sur échéance PSC, sous verrou partagé, sans prolongation par défaut,
> projection sans refresh token. C'est la seule modification du proxy que cette US
> requiert, et elle est **prérequise**.

## Objective

Aujourd'hui les trois clients rafraîchissent l'access token PSC (~2 min de TTL) pour le
pousser à `api-mail` dans l'en-tête `X-PSC-Token` à chaque requête, alors que le
backend ne le consomme qu'à l'ouverture/ré-authentification des sessions IMAP/SMTP
MSSanté (XOAUTH2). Et `api-mail` **croit ce jeton sur parole** : il le décode sans
vérifier sa signature, et plus rien ne le relie au compte Keycloak qui fait la requête
(audit du 2026-09-16, écart critique n°1).

Cette US inverse le flux et ferme l'écart en une fois :

1. **`api-mail` résout lui-même l'access token PSC auprès du psc-auth-proxy**, au
   moment où il en a besoin, en rejouant le cookie `proxy_session_id` reçu du
   navigateur — et le bearer du praticien — sur l'endpoint **dédié**
   `GET {proxy}/v1/internal/psc-context` (proxy task-016 : lecture de l'agrégat en
   Redis, refresh **si le PSC l'exige**, sous verrou, projection sans refresh token) ;
2. **il vérifie que cette session appartient au porteur du bearer** — la liaison
   compte ↔ professionnel est *lue* dans l'agrégat, pas reconstruite ;
3. **les trois clients cessent de rafraîchir et de transporter le jeton PSC**, et
   envoient le cookie à `api-mail` ;
4. **`api-mail` ne lit plus `X-PSC-Token`** — l'en-tête est ignoré s'il arrive encore.

**Pourquoi une seule US, pas trois.** Le plan de juillet (171 backend avec fallback →
172 clients → « chantier 6 » de nettoyage) laissait l'en-tête vivant pendant toute la
transition, donc l'attaque de l'audit ouverte — et le chantier 6 n'avait pas de task.
Une US découpée n'atteint la sécurité visée qu'au troisième merge ; celle-ci l'atteint
au premier. Le coût est un **déploiement coordonné** des quatre repos (voir
« Prérequis de déploiement ») ; aucun ordre ne casse quoi que ce soit, chaque
composant non encore déployé dégrade en mode hors ligne.

### Contenu

**Backend `api-mail` — chantiers 1 à 4 de l'ADR**

1. **`IPscTokenProvider`** (nouveau service + client HTTP dédié) :
   - config URL du proxy dans `appsettings.json` (dev : `https://localhost:8081/v1`),
     timeout court (≤ 5 s) ;
   - appel `GET /v1/internal/psc-context` en forwardant le cookie
     (`Cookie: proxy_session_id=...`), le bearer du praticien
     (`Authorization: Bearer …`, pour la liaison RG-L1 côté proxy) et la clé
     interne `X-Internal-Api-Key` (variable `PscProxy:InternalApiKey`, jamais en
     clair dans `appsettings.json` versionné) ; `?keepAlive=true` sur une requête
     portée par un praticien, **rien** depuis un travail de fond (RG-S) ;
   - reçoit la **projection** `PscContextDto` — `hasPsc`, `pscAccessToken` +
     échéance, `pscSub`, `subjectNameId`, `kcSub`, `sessionExpiresAtUtc` — et rien
     d'autre : **aucun refresh token ne transite jamais**, il n'y a donc rien à
     « jeter » ;
   - mapping des réponses : `401` (session absente) → hors ligne ; `200 hasPsc:false`
     (session Keycloak-only) → hors ligne ; `403 PscIdentityConflict` → RG-L1,
     jamais hors ligne ; `503` (refresh en échec, proxy indisponible, timeout) →
     hors ligne à l'évaluation du mode, `UnavailableException` sur une
     authentification IMAP/SMTP déjà engagée ;
   - vérifie **aussi** `kcSub == sub du bearer` sur la projection reçue (deux lignes,
     défense en profondeur : le proxy l'a déjà fait, `api-mail` ne fait pas confiance
     à un seul contrôle) ;
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
       `/v1/internal/psc-context` alimente les deux caches (jamais d'introspection
       séparée). Rythme cible en régime établi : ~1 appel mode / 5 min / session
       active + 1 appel par (ré)ouverture de connexion IMAP/SMTP ;
   - **verdicts négatifs du cache mode** (protection du proxy — sans eux, les cas
     sans token martèleraient le proxy à chaque requête) : session sans PSC
     (`PscAccessToken` vide, cas Keycloak-only) → « offline » caché ~5 min par
     session id (stable par construction : un login PSC crée une nouvelle session,
     donc un nouveau session id → réévaluation immédiate) ; session
     expirée/invalide → « offline » caché ~60 s ; session **non liée au porteur**
     (RG-L1) → refus caché ~60 s, jamais « offline » ;
   - **circuit breaker** (Polly) sur le client HTTP proxy : après N échecs,
     circuit ouvert ~30 s → toute évaluation de mode bascule offline
     instantanément (le timeout de 5 s ne se paie qu'aux transitions, jamais en
     rafale), reprise via half-open ;
   - **évaluation paresseuse** : le middleware pose un résolveur lazy, la
     résolution n'a lieu qu'au premier accès effectif au mode ou au token dans la
     requête ;
   - erreurs typées (règle 12 ProblemDetails) : session absente/expirée →
     `UnauthorizedException` (401), session non liée au porteur →
     `ForbiddenException` (403, code `PscIdentityConflict`), proxy indisponible →
     `UnavailableException` (503).
2. **Résolution middleware + mode online/offline** :
   `UserContextEnricherMiddleware` lit le cookie `proxy_session_id` entrant — **et
   rien d'autre** : `X-PSC-Token` n'est plus lu (chantier 6 ci-dessous).
   **Attention — la présence du cookie ne suffit PAS à déclarer le mode online** :
   le proxy accepte des sessions Keycloak-only (login mot de passe, sans PSC), et
   le cookie peut survivre à la session Redis. La règle :
   *online ⇔ un token PSC est effectivement obtenable* — résolution non bloquante
   via `IPscTokenProvider.TryGet` (cache par session ; `PscAccessToken`
   vide/session expirée/proxy injoignable → **offline** : lecture cache DB, actions
   en attente, aucune 5xx sur les lectures, cause tracée). Le middleware pose un
   **indicateur de mode explicite** dans `UserContextInfo` ; `ConnectionModeService`
   (dont `CanSendEmail`, qui lit aujourd'hui la string `PscToken`) consomme cet
   indicateur et non plus la présence du token brut. La propriété
   `UserContextInfo.PscToken` disparaît au profit du résolveur.
   ⚠️ *La version de juillet écrivait ici que « le cross-check identité PSC↔Keycloak
   existant s'applique au token résolu ». Ce cross-check n'existe plus : task-308 l'a
   retiré quand les claims `mssSub`/`mssRpps` ont disparu du realm. La liaison est
   spécifiée à part — section « Liaison compte ↔ professionnel ».*
3. **Points de consommation** : `ImapConnectionService`, `SmtpConnectionFactory`,
   `BackgroundImapService` obtiennent le token via `IPscTokenProvider` juste avant
   chaque `AuthenticateAsync`, au lieu de lire un token figé dans `UserContextInfo`.
   La garde « token expiré → 401 » (contrat task-165) est **supprimée** : elle est
   remplacée par la résolution d'un token frais ; le 401 ne subsiste que si la
   session proxy elle-même est expirée.
4. **Background sync** : `BackgroundSyncManager` et `BackgroundEnrichmentProcessor`
   mémorisent le **session id** (plus de snapshot de token — `target.PscToken =
   source.PscToken` disparaît) et résolvent un token frais à chaque
   (ré)authentification — le sync long survit aux expirations tant que la session
   proxy vit (30 min glissants).

   **RG-S — Le sync de fond lit, il n'entretient pas la session.** Sans cette règle,
   le backend pull crée un keep-alive : chaque résolution qui déclenche un refresh
   prolonge la session proxy de 30 min, et un sync périodique maintient vivante la
   session d'un praticien parti depuis des heures — l'expiration par inactivité
   (PGSSI-S) serait contournée par le serveur lui-même. Donc : les appels du sync de
   fond sont émis **sans** `keepAlive` ; si le proxy doit rafraîchir pour servir, il le
   fait **sans prolonger** (task-016 RG-4) ; et si la session a expiré, le sync
   **s'arrête** et reprendra à la prochaine requête du praticien. Seules les requêtes
   HTTP portées par un praticien prolongent la session — via le refresh Keycloak que
   les clients continuent de faire, et via `keepAlive=true` sur leurs résolutions.
5. **CORS api-mail — passage en mode credentialed** : la policy actuelle
   (`CorsPolicySetup.cs`, task-092) n'appelle **pas** `.AllowCredentials()` — son
   commentaire dit explicitement « Bearer tokens (no cookies) ». Sans cela, le
   navigateur n'enverra jamais le cookie `proxy_session_id` en cross-origin.
   Ajouter `.AllowCredentials()` (whitelist d'origines exactes uniquement —
   jamais de wildcard avec credentials), mettre à jour le commentaire de la
   classe et les tests d'intégration CORS existants. Les flux SSE
   (`MailEventsController`, `NotificationsController`) sont concernés si leurs
   endpoints consultent le mode : côté client, `EventSource`/fetch en
   `withCredentials`.

**Clients — chantier 5 de l'ADR (ex-task-172, étendu à Blazor)**

6. **Retrait du volet PSC dans les trois clients.** Le refresh du token **Keycloak**
   (`Authorization: Bearer`, qui authentifie les requêtes API et prolonge la session
   proxy) reste strictement inchangé partout.
   - **client-angular** (`Client/Angular/front`, code-only) : supprimer
     `psc-token-guard.interceptor.ts` (libs/mss), son enregistrement dans
     `app.config.ts`, le token d'injection `MSS_PSC_REFRESH_FN` et son câblage ;
     `mss-headers.interceptor.ts` ne pose plus `X-PSC-Token` et garantit
     `withCredentials: true` sur les appels vers `MSS_API_URL` ; purger
     `pscAccessToken` du state (`AuthenticationStore` / `ITokenAggregate`) là où il
     n'est plus consommé (le proxy peut continuer de le renvoyer — le client l'ignore).
   - **client-mobile** (`Client/Mobile`, automation complète) :
     `mss-headers.interceptor.ts` retire le volet PSC (pose de l'en-tête, raisonnement
     `min(Keycloak, PSC)`) et conserve la logique de refresh Keycloak (préventif 30 s +
     filet 401 + 429) ; `mss-api.service.ts:766` idem ; `withCredentials: true` vers
     `mssApiUrl` ; `auth-session.service.ts` / `session.model.ts` ne persistent plus
     `pscAccessToken` dans `localStorage` (`mobile_mss_session`) — une donnée
     d'authentification santé de moins sur le device.
     **Point de vigilance WebView Capacitor** : valider sur émulateur que le cookie
     `proxy_session_id` (`SameSite=None`, WebView servie en `https://app.weda.fr`)
     part bien vers api-mail. S'il ne passe pas : **ne pas improviser** — ouvrir
     `questions/task-171.md` ; le plan B de l'ADR (transmission du `ProxySessionId`
     renvoyé par le flux CIBA dans un en-tête explicite) est une décision
     d'architecture, pas un contournement silencieux.
   - **client-blazor** (`Client/Blazor`, pushable) : `HttpRequestService.cs`
     (`SetHeader`/`RemoveHeader("X-PSC-Token")`, l. 87 et 92) et
     `MailboxAccountsService.cs:162` ne posent plus l'en-tête ; toutes les requêtes
     vers `api-mail` passent en `BrowserRequestCredentials.Include` (`HttpRequestMessage
     .SetBrowserRequestCredentials`) pour que le cookie parte ; purger `PscAccessToken`
     de l'état des tokens là où il n'est plus consommé ; `IMailExportService.cs:16`
     (doc) mis à jour.
   - **Mode online/offline — le statut backend, partout, y compris pour la décision
     d'entrée dans la boîte.** Le mode est déterminé par le backend (« un token PSC
     est-il obtenable pour cette session ? ») et exposé par `GET /api/v1/connection/status`
     — modèle déjà suivi par `sync-progress-widget` (Angular) et `ConnectionStateService`
     (Blazor). Revue du 2026-09-23 : **quatre** dérivations locales à remplacer, et ce
     ne sont pas des détails — trois d'entre elles décident `PscRequired` vs
     `Onboarding`, c'est-à-dire si le praticien peut rattacher une boîte :
     - mobile `mailbox-session.service.ts:106` — `offline = computed(() => !session.pscAccessToken)` ;
     - Angular `app.config.ts:270` — `MSS_PSC_TOKEN_PRESENT` ;
     - Blazor `MailboxSessionService.IsOffline` et `ConnectionStatusService.IsOfflineMode`.
     Conséquence : la page « PSC requis » dépend désormais d'une réponse réseau au
     démarrage, pas d'un champ local — prévoir l'état de chargement.
   - **Les widgets « compte à rebours PSC » n'ont plus d'objet** : `offline-status-widget`
     (Angular, `pscSessionStatus` / `pscTimeRemaining`) et `OfflineStatusWidget.razor`
     (Blazor, `GetPscSessionStatus`) affichent l'échéance d'un jeton que le client ne
     voit plus. Les remplacer par le `mode` du statut backend ; aucun nouvel écran.
   - **Stratégie de refresh client — un seul jeton, une seule échéance.** Mobile :
     `isAccessTokenExpired` cesse de raisonner sur `min(Keycloak, PSC)` (task-283) et ne
     garde que `accessTokenExpiresAt` ; `earliestExpiry()` et ses tests disparaissent.
     Angular : `pscTokenGuardInterceptor` disparaît, `authInterceptorFn` reste le seul
     déclencheur (expiration KC + 401). Blazor : `TokenService` (moniteur KC) inchangé ;
     **`PscTokenRefreshService` ne se supprime pas** — `HttpRequestService.
     HandleUnauthorizedAndRetryAsync` s'appuie sur `ForceRefreshPscTokenAsync` pour le
     chemin 401 → refresh → rejeu de task-156 ; il se **renomme** en refresh de session
     et perd sa logique d'échéance PSC (`IsPscTokenExpiringSoon`,
     `EnsureValidPscTokenAsync`, appel avant chaque requête). Chaque `/auth/refresh`
     continue de rafraîchir PSC côté proxy et de prolonger la session : c'est ainsi que
     le **client reste le seul gardien de la session** (RG-S).
   - **Angular `mss-api.service.ts:2101`** — le `fetch` SSE IA dérive `Client-Session-Id`
     de `jwt.sid`, qui n'existe pas (task-282) : aligner sur
     `mailboxSession.clientSessionId()` dans le même geste que le retrait de l'en-tête.

**Backend `api-mail` — chantier 6, retrait du fallback**

7. **`X-PSC-Token` n'est plus lu nulle part dans `api-mail`** : `RequestHelper.cs`
   (l. 73–78), `UserContextEnricherMiddleware.ResolvePscToken` / `TryParsePscIdentity`,
   et tout consommateur de `UserContextInfo.PscToken`. Un en-tête `X-PSC-Token` qui
   arriverait encore (client pas encore redéployé) est **ignoré, pas rejeté** : la
   requête est traitée comme sans cookie → mode hors ligne, aucune erreur. Le contrat
   « 401 → refresh réactif » de task-165 est retiré avec la garde qui le portait.
   **Le banc de charge — RG-5 telle qu'écrite dans 318 était fausse.** Revue du
   2026-09-23 : `tests/loadtest-k6/lib/identity.js:112` envoie
   `X-PSC-Token: pscTokenFor(user)`, un JWT forgé, **et c'est lui qui met le banc en
   mode online** (`IsOnlineMode = PscToken non vide`) — task-206 l'avait même durci
   pour exercer le vrai chemin de parse. Ignorer l'en-tête ferait tomber tout le banc
   en hors ligne, sans IMAP. Donc : `TestBypassAuthenticationHandler` **pose lui-même
   l'indicateur de mode « online »** et l'identité PSC (`Client-Psc-Sub`, `Client-Rpps`,
   déjà envoyés) dans le contexte, sans jamais appeler le proxy ; k6 **retire**
   `X-PSC-Token` et `pscTokenFor` ; la référence de capacité E015 se déplace (comme
   task-303 l'avait déplacée) — à noter dans le rapport du premier tir post-171.
   **`SyncController.cs:47-55`** journalise aujourd'hui 50 caractères du jeton PSC
   (`PscPreview`) : ce log disparaît avec la propriété — c'était déjà une fuite.

### Liaison compte ↔ professionnel (reprise de task-318)

**Pourquoi c'est ici.** L'audit sécurité du registre du 2026-09-16 (écart critique
n°1) a établi qu'`api-mail` croit sur parole le jeton PSC présenté dans `X-PSC-Token`
et que **plus aucune ligne** ne rapproche l'identité PSC du compte Keycloak qui fait
la requête. Un compte Keycloak muni du jeton PSC d'un autre professionnel peut
rattacher la messagerie de ce professionnel sur son propre compte et **verrouiller la
victime** (le registre refuse qu'un RPPS soit rattaché deux fois). Task-318 voulait
fermer l'écart en vérifiant la signature du jeton et en comparant son `sub` à un claim
Keycloak ajouté par mapper — c'est-à-dire **reconstruire** une liaison à partir de
deux jetons indépendants fournis par le client.

Le backend pull rend cette reconstruction inutile : l'agrégat de session du proxy
(`TokenInfoDto`) contient **ensemble** le jeton Keycloak et les jetons PSC d'un même
login, et le jeton Keycloak y a été émis par le grant RFC 7523 pour le seul compte
**lié** au `sub` de l'assertion PSC. La liaison est un fait établi côté serveur au
moment du login. Il suffit de la **lire**.

Mais le cookie est, lui aussi, un artefact détenu par le client. Sans le contrôle
ci-dessous, « mon bearer + le cookie de la victime » reproduit exactement l'attaque
de l'audit avec un artefact différent. D'où les règles.

**RG-L1 — Appartenance de la session au porteur du bearer.** À chaque résolution via
cookie, `api-mail` compare le `sub` du jeton Keycloak contenu dans l'agrégat
(`TokenInfoDto.AccessToken`) au `sub` du bearer de la requête. Inégalité → **403**
`application/problem+json`, code `PscIdentityConflict` (déjà connu des trois fronts),
**rien de résolu** : aucun cache token alimenté, aucune connexion IMAP/SMTP ouverte,
rien de persisté. La comparaison porte sur `sub`, jamais sur le jeton lui-même — il est
re-frappé à chaque refresh (`jti` neuf). Un agrégat sans jeton Keycloak (session
PSC-only non encore échangée) ne satisfait **pas** la règle : refus, pas de repli.

**RG-L2 — L'identité professionnelle est celle de la session.** `sub` PSC et
`SubjectNameID` (RPPS) sont lus dans le `PscAccessToken` / `PscIdToken` de l'agrégat
rendu par le proxy — que le proxy a obtenu **directement** auprès de PSC — et jamais
dans un en-tête client. `AttachAsync` (`ValidatedByPscSubject`, `ValidatedByRpps`) et
`MailboxCompatibility` consomment cette identité. **Aucune vérification de signature
côté `api-mail` n'est requise** : la confiance repose sur le canal serveur-à-serveur
(TLS + clé interne `X-Internal-Api-Key` + liaison au bearer, task-016 du proxy) et
sur l'origine du jeton. La conserver en défense en profondeur
est permis ; elle n'est pas porteuse. Facultatif, même statut : si le bearer porte
un claim `psc_sub` (mappers du bordereau Keycloak 1.17.0), le confronter au `sub` PSC
de l'agrégat et journaliser l'écart — jamais refuser sur ce seul critère.

**RG-L3 — Le chemin cookie est le seul chemin ; le rattachement l'exige.** Il n'y a
plus de fallback, donc plus de réglage de transition. `POST /api/v1/account/mailboxes`
et l'évaluation de compatibilité (`MailboxCompatibility`) **exigent** une session
proxy liée au porteur (RG-L1 satisfaite) et porteuse d'une identité PSC (RG-L2). Sans
cookie, cookie invalide, session Keycloak-only ou non liée → **401**
`application/problem+json`, code dédié, rien de persisté. La **lecture** des boîtes
déjà rattachées reste servie en mode hors ligne dans tous ces cas : le compte se
résout par le bearer, et aucune donnée d'un autre praticien n'est atteignable.

**RG-L4 — Trace d'audit.** Un rattachement refusé pour RG-L1 ou RG-L3 produit une
trace `MailboxAttached` avec `Success = false` et le code de refus en `ErrorMessage`.
**Aucun nouveau membre `AuditActionType`** : le type est miroité à la main côté
Angular et Blazor (mémoire `auditactiontype-ordinal-wire-mirrored-ts`). Les journaux
techniques portent des identifiants tronqués, jamais un jeton, jamais un cookie.

**RG-L5 — Prérequis d'intégrité : la liaison fédérée doit être injective.** RG-L1 ne
prouve la non-usurpation que si un `sub` PSC n'est lié qu'à **un** compte Keycloak.
Keycloak ne l'impose pas : sa seule contrainte d'unicité est
`(IDENTITY_PROVIDER, USER_ID)`, l'index sur l'identifiant côté fournisseur n'est pas
unique, et un `POST federated-identity` sur un `sub` déjà lié répond `204` (mesuré
le 2026-09-22 sur 26.7.2). Deux dispositifs, **hors DOD de cette US** mais
prérequis de mise en service :
- la garde anti-doublon dans `CreateIdentityProviderLinkAsync` du proxy — seule voie
  de création d'une liaison hors du flow navigateur. Livrée le 2026-09-22 sur
  `feature/task-001-support-espace-communautaire-psc` (commit `3651bef`, code de refus
  dédié `PROXY-KC-4012`) ; elle clôt la task-013 du proxy. **Prérequis : la PR de
  task-001 mergée sur `next` et déployée** ;
- l'audit SQL des liaisons du realm avant mise en service :
  `SELECT FEDERATED_USER_ID, COUNT(*) FROM FEDERATED_IDENTITY WHERE
  IDENTITY_PROVIDER='oidc' GROUP BY FEDERATED_USER_ID HAVING COUNT(*) > 1`
  doit rendre **zéro ligne** (bordereau Keycloak).

> **Remplace task-318** (retirée le 2026-09-23, conservée dans `tasks/archived/`
> pour son constat d'audit, toujours exact).
>
> | Règle de 318 | Devenir dans 171 |
> |---|---|
> | RG-1 vérification cryptographique du jeton PSC | **Sans objet** — le jeton ne vient plus du client (RG-L2) |
> | RG-2 jeton forgé → 401 | **Sans objet** — plus aucun jeton client n'est lu ; un en-tête qui arrive encore est ignoré |
> | RG-3 égalité claim Keycloak = `sub` PSC | **Remplacée par RG-L1** — liaison lue dans la session, pas reconstruite ; `psc_sub` devient une contre-vérification facultative |
> | RG-4 mode observation `Enforce` | **Supprimé** — pas de transition, le rattachement exige la session liée dès la livraison (RG-L3) |
> | RG-5 banc de charge non concerné | **Réécrite** — elle était fausse : le banc tenait son mode online de l'en-tête forgé. Le bypass pose désormais le mode lui-même, k6 retire l'en-tête (point 7) |
> | RG-6 trace `MailboxAttached` en échec | **Conservée telle quelle** (RG-L4) |
> | Arbitrage « nom du claim », « émetteurs PSC + JWKS », « durée d'observation » | **Caducs** — aucun claim porteur, aucune vérification de signature, aucune durée |

> **Absorbe task-172 et le « chantier 6 »** (2026-09-23). Task-172 (clients Angular +
> mobile) est retirée dans `tasks/archived/` ; son contenu est repris intégralement au
> point 6, **étendu à Blazor** — qui pose `X-PSC-Token` à deux endroits et n'était
> couvert par aucune task. Le chantier 6 (retrait du fallback API, contrat task-165)
> n'avait jamais eu de task : c'est le point 7. Les deux clauses « Hors scope » de la
> version de juillet qui les renvoyaient à plus tard sont supprimées.

### Prérequis de déploiement

**Domaine d'api-mail (BLOQUANT hors dev).** Le transport par cookie exige qu'api-mail
soit servi sous un hôte du domaine `.weda.fr` (portée du cookie proxy :
`Domain=.weda.fr`, `HttpOnly`, `Secure`, `SameSite=None`). Or les environnements
actuels pointent vers `https://mss-api.xsd2code.com` (`environment.prod.ts` Angular
**et** mobile) — **le cookie ne partira jamais vers ce domaine**. En dev local, aucun
problème (cookie host-only `localhost`, les ports sont ignorés). Décision humaine du
2026-07-25 (`questions/answered/task-171.md`) : bascule vers `*.weda.fr`, pas de
plan B par en-tête. La liste des origines à whitelister dans `Cors:AllowedOrigins`
par environnement reste à fournir à la mise en service. L'implémentation et les tests
de la US sont entièrement réalisables en local.

**Durées de vie mesurées sur le realm de production — avant d'écrire une ligne.**
Les commentaires du code (task-283, mobile et backend) affirment « Keycloak ~5 min,
PSC ~2 min ». Mesuré le 2026-09-23 sur le realm local : **les deux valent 120 s**
(`accessTokenLifespan: 120`), les deux refresh tokens **1 800 s**. La stratégie de
refresh dépend de cette réponse : si Keycloak = PSC, la cadence client ne change pas
en retirant PSC ; si Keycloak = 300 s, le PSC stocké en session est périmé ~3 min sur
5 entre deux refresh client, et c'est le proxy (task-016, refresh sur échéance PSC)
qui doit combler — d'où la dépendance. À relever et consigner dans le task file :

```bash
curl -sk -H "Authorization: Bearer $ADMIN_TOKEN" "$KC/admin/realms/weda-realm" \
  | grep -oE '"(accessTokenLifespan|ssoSessionIdleTimeout|ssoSessionMaxLifespan)":[0-9]+'
# et la vie d'un jeton PSC émis par l'émetteur de production : exp − iat de sa charge utile
```

**Proxy task-016 déployée**, avec `PSC_CONTEXT_API_KEY` posée côté proxy et
`PscProxy:InternalApiKey` côté `api-mail` (secret, jamais versionné) ; et **PR de
task-001 du proxy mergée** (garde anti-doublon, RG-L5).

**Déploiement coordonné des quatre repos.** La US se valide assemblée (règle 11, HAG
sur les quatre PR). En déploiement, aucun ordre ne casse : un client déjà migré face à
un backend pas encore migré n'envoie plus l'en-tête → hors ligne jusqu'au déploiement
backend ; un backend déjà migré face à un client pas encore migré ignore l'en-tête et
ne reçoit pas de cookie → hors ligne jusqu'au déploiement client. Jamais d'erreur,
jamais de fuite, mais **une fenêtre hors ligne** à planifier hors heures d'usage.

### Hors scope

- Toute modification du workspace `psc-auth-proxy` **autre que task-016** (endpoint
  `/v1/internal/psc-context` + service de refresh unique), portée par la forge du
  proxy et prérequise de cette US — voir l'addendum ADR en « Référence ». La version
  de juillet écrivait ici « `POST /v1/session/token` existe et suffit » : ce n'est
  plus vrai, et la raison est documentée.
- `dtos-mss` : `TokenInfoDto` **garde** ses champs `Psc*`. Le proxy continue de
  renvoyer l'agrégat complet aux clients ; ceux-ci ignorent ces champs. Aucun
  republish NuGet.
- TTL de l'access token Keycloak (levier realm `weda-realm`, hors périmètre ADR).
- Vérification de la signature du jeton PSC dans `api-mail` (RG-1 de l'ex-318) :
  sans objet ; permise en défense en profondeur, jamais exigée.
- Les mappers `psc_sub` du realm (bordereau Keycloak 1.17.0) : défense en profondeur,
  hors chemin critique ; leur pose n'est pas un prérequis de cette US.
- La garde anti-doublon du proxy et l'audit SQL des liaisons (RG-L5) : prérequis de
  mise en service, portés par le proxy et le bordereau Keycloak, pas par cette DOD.
- Le refresh Keycloak et ses interceptors clients (`authInterceptorFn`,
  `SharedRefreshTokenService`, refresh mobile préventif/401/429) — intouchés.

## Definition of Done

**Backend `api-mail`**

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors 3 flaky pré-existants documentés) — `dotnet test`
- [ ] Unit tests `IPscTokenProvider` : cache token (hit / miss / expiration à
      `exp − 30 s`) / cache mode découplé (verdict valable ~5 min même quand
      l'access token caché est expiré — pas de réévaluation au rythme du token) /
      dédup d'appels concurrents / session expirée → 401 typé /
      proxy indisponible → 503 typé (≥ 1 test par branche)
- [ ] Unit tests middleware / mode : online avec cookie + session PSC valide et liée ;
      **offline** avec cookie + session Keycloak-only (sans PSC) ; **offline** avec
      cookie invalide/session expirée ; **offline** (dégradé, tracé) avec proxy
      injoignable à l'évaluation du mode ; offline sans cookie ; **offline** avec
      `X-PSC-Token` seul (en-tête ignoré, aucune lecture)
- [ ] `ConnectionModeService` (`CanSendEmail` inclus) basé sur l'indicateur de mode
      posé par le middleware ; la propriété `UserContextInfo.PscToken` n'existe plus ;
      comportement offline existant (cache DB, pending actions) non régressé
      (tests `MailDataProviderFactory`/`PendingActionService` verts)
- [ ] Integration test endpoint (règle 1b) : requête avec cookie `proxy_session_id`
      → le token est résolu via le provider (proxy mocké) et l'authentification IMAP
      reçoit ce token
- [ ] Integration test : proxy indisponible à l'**évaluation du mode** → bascule
      offline tracée, lecture des dossiers servie depuis le cache (pas de 5xx) ;
      proxy indisponible au moment d'une **authentification IMAP/SMTP déjà engagée
      en mode online** → `application/problem+json` 503 (règle 12), aucun
      try/catch ad hoc dans les controllers
- [ ] `BackgroundSyncManager` / `BackgroundEnrichmentProcessor` ne stockent plus de
      token (grep : plus de snapshot capturé au démarrage) — test unitaire sur la
      résolution à la ré-authentification
- [ ] **Chantier 6** — `grep -rn "X-PSC-Token" Api/Mail/src` = 0 hit hors
      commentaires historiques ; `TryParsePscIdentity` et `ResolvePscToken` supprimés ;
      la garde « token expiré → 401 » de task-165 supprimée ; un en-tête `X-PSC-Token`
      reçu ne provoque **ni erreur ni lecture** (test d'intégration : requête avec
      l'en-tête seul → 200 en mode offline)
- [ ] Aucun token (PSC/Keycloak/refresh), aucun `TokenInfoDto` sérialisé, aucun
      session id en clair dans les logs (revue des appels logger sur le code neuf)
- [ ] Timeout de l'appel proxy ≤ 5 s, configuré et testé
- [ ] Charge proxy bornée : unit tests prouvant qu'une série de requêtes sur une
      même session ne produit qu'**un** appel proxy par fenêtre de cache mode
      (~5 min) — y compris dans les cas négatifs (session Keycloak-only, session
      expirée, session non liée, circuit ouvert) ; l'access token n'est demandé
      qu'aux instants d'authentification IMAP/SMTP ; jamais d'appel proxy par
      requête HTTP ; aucun timer/refresh périodique dans api-mail (pull pur)
- [ ] Circuit breaker testé : N échecs → circuit ouvert → évaluations de mode
      offline sans appel réseau ni timeout ; reprise en half-open
- [ ] CORS : `.AllowCredentials()` actif avec whitelist d'origines exactes (jamais
      de wildcard) ; tests d'intégration `CorsPolicySetup` mis à jour (preflight
      credentialed accepté depuis une origine whitelistée, refusé sinon)
- [ ] RG-5 (ex-318) — le chemin `X-Test-Bypass` (hors Production) n'appelle jamais le
      proxy ; le banc de charge (`aspire run` profil loadtest, tir k6 court) passe
      sans changement ni 401/403 nouveau

**Liaison compte ↔ professionnel (ex-318)**

- [ ] RG-L1 — unit tests : `sub` égaux → identité résolue ; `sub` différents → 403
      typé `PscIdentityConflict`, **aucun** cache token alimenté, **aucune** tentative
      IMAP/SMTP ; agrégat sans jeton Keycloak → refus ; bearer sans `sub` → refus
      (≥ 1 test par branche)
- [ ] RG-L2 — unit test : `ValidatedByPscSubject` / `ValidatedByRpps` proviennent de
      l'agrégat ; aucune autre source possible (la propriété d'en-tête n'existe plus)
- [ ] RG-L1 — integration test (règle 1b) : `POST /api/v1/account/mailboxes` avec le
      bearer du compte A et le cookie d'une session du compte B (proxy mocké) →
      403 `application/problem+json`, **zéro** ligne créée dans `mss_accounts`, trace
      `MailboxAttached` `Success = false`
- [ ] RG-L3 — integration tests : rattachement sans cookie → 401 typé, rien de
      persisté ; avec cookie de session Keycloak-only → 401 typé ; **lecture** d'une
      boîte déjà rattachée sans cookie → servie en mode offline
- [ ] RG-L4 — aucun nouveau membre `AuditActionType` (diff sur l'enum vide) ; revue
      des appels logger : ni jeton, ni cookie, ni session id en clair, identifiants
      tronqués

**Clients (ex-172, + Blazor)**

- [ ] client-angular : build passes — `npm ci && npm run build` (0 errors) ; tests
      pass — `npm test` (0 failures)
- [ ] client-mobile : build passes — `npm ci && npm run build` (0 errors) ; tests
      pass — `npm test -- --watch=false --browsers=ChromeHeadless`
- [ ] client-blazor : build passes — `dotnet build HealthPlatform.Client.sln`
      (0 errors) ; tests pass — `dotnet test HealthPlatform.Client.sln`
- [ ] **Plus aucune occurrence de `X-PSC-Token` dans le code des trois clients**
      (grep = 0 hit hors commentaires/changelog)
- [ ] client-angular : `psc-token-guard.interceptor` supprimé (fichier +
      enregistrement + token DI) ; tests associés supprimés ou adaptés
- [ ] `withCredentials: true` (Angular, mobile) / `BrowserRequestCredentials.Include`
      (Blazor) effectif sur **tous** les appels api-mail, SSE compris — test unitaire
      d'interceptor / de `HttpRequestService` le vérifiant
- [ ] client-mobile : `pscAccessToken` absent de `localStorage` après login (test
      unitaire sur `AuthSessionService` + vérification manuelle)
- [ ] Refresh Keycloak inchangé sur les trois clients : tests existants des
      interceptors/services Keycloak verts sans modification de comportement
- [ ] Aucun code client ne dérive l'état online/offline de la présence locale d'un
      `pscAccessToken` (l'état vient du statut de connexion backend)
- [ ] Aucun libellé/log client contenant token ou session id en clair

**Revue du 2026-09-23 — cohérence clients, refresh, banc**

- [ ] `IPscTokenProvider` consomme `PscContextDto` et **ne désérialise aucun champ**
      `refreshToken` / `pscRefreshToken` / `idToken` (test de contrat sur la
      désérialisation : un JSON qui les porterait est ignoré, jamais stocké)
- [ ] Mapping des réponses proxy testé : `401` → hors ligne ; `200 hasPsc:false` →
      hors ligne ; `403` → `PscIdentityConflict` **jamais** hors ligne ; `503` →
      hors ligne à l'évaluation du mode, 503 typé sur authentification engagée
- [ ] `kcSub` de la projection comparé au `sub` du bearer côté `api-mail` (défense en
      profondeur — test : projection avec un autre `kcSub` → refus)
- [ ] RG-S — les appels du sync de fond n'envoient pas `keepAlive` (test sur la
      requête émise) ; **test d'intégration** : session proxy mockée à TTL 60 s, sync
      actif, aucune requête cliente → après 60 s le sync s'est arrêté, aucun appel avec
      `keepAlive=true` n'a été émis
- [ ] Mobile : `isAccessTokenExpired` ne lit que `accessTokenExpiresAt` ;
      `earliestExpiry` supprimée avec ses tests ; `mailbox-session.service.offline`
      lit le statut backend (test : statut `offline` → `PscRequired`, statut
      `online` → `Onboarding`, indépendamment de tout champ local)
- [ ] Angular : `MSS_PSC_TOKEN_PRESENT` supprimé ou branché sur le statut backend ;
      `offline-status-widget` sans `MSS_PSC_ACCESS_TOKEN` ; `mss-api.service` fetch SSE
      : `Client-Session-Id` = `clientSessionId()` (test)
- [ ] Blazor : `PscTokenRefreshService` renommé (refresh de session), sans
      `IsPscTokenExpiringSoon` ni appel avant chaque requête ; le chemin 401 →
      `ForceRefresh…` → rejeu (task-156) **toujours couvert par ses tests** ;
      `MailboxSessionService.IsOffline` et `ConnectionStatusService.IsOfflineMode`
      lisent le statut backend ; `OfflineStatusWidget` sans compte à rebours PSC
- [ ] Banc : `TestBypassAuthenticationHandler` pose le mode online et l'identité PSC
      sans appel proxy (test unitaire) ; `identity.js` sans `X-PSC-Token` ni
      `pscTokenFor` ; un tir k6 court en profil loadtest atteint IMAP (compteurs
      `mail_server_solicitations` non nuls)
- [ ] `SyncController` : plus aucun extrait de jeton dans les logs (grep `PscPreview` = 0)
- [ ] Durées de vie du realm de production relevées et consignées dans ce fichier
      (section « Prérequis de déploiement »), avec la date

**Transverse**

- [ ] `grep -rn "X-PSC-Token"` sur les quatre repos = 0 hit hors commentaires
      historiques, changelogs et task files
- [ ] Doc EPIC E013 (`/tech-writer`) : le nouveau cycle de vie du jeton PSC et la
      garantie de liaison expliqués en langage produit, avec renvoi vers l'audit du
      2026-09-16 (E016)
- [ ] AIPD : note ajoutée — le jeton PSC ne transite plus par le client ni par le
      stockage local du device ; le rattachement d'une messagerie exige une identité
      PSC issue de la session d'authentification et liée au compte

## Manual Test Plan

Prérequis : psc-auth-proxy lancé (workspace `D:\Workspaces\psc-auth-proxy`, AppHost
Aspire), `api-mail` lancé (`cd Api/Mail && aspire run --project src/AppHost`), deux
comptes PS de test A et B avec boîtes MSSanté de test.

**Backend, en `curl`**

1. **Chemin nominal (pull via cookie)** — se connecter via PSC sur un client pour
   obtenir une session proxy. Récupérer le cookie `proxy_session_id` (DevTools →
   Application → Cookies) et le token Keycloak. Appeler `api-mail` :
   `curl -H "Authorization: Bearer {kc}" -H "Client-Email: {mss}" --cookie "proxy_session_id={sid}" https://localhost:{port}/api/...folders`
   → la liste des dossiers IMAP se charge (le backend a résolu le token via le proxy).
2. **Fraîcheur** — attendre > 2 min (expiration de l'access token PSC), rejouer le
   même curl → toujours 200, sans intervention client (le proxy a rafraîchi).
3. **En-tête ignoré (chantier 6)** — rejouer le curl du point 1 **sans cookie, avec**
   `-H "X-PSC-Token: {jeton PSC valide}"` → `200` en **mode offline**
   (`GET .../connection/status` → `mode: "offline"`), aucune erreur, aucune lecture du
   jeton dans les logs Seq.
4. **Session expirée / cookie invalide** — cookie invalide → `200` en mode offline,
   dossiers servis depuis le cache DB, aucun 5xx ; logs Seq sans token ni session id.
5. **Proxy éteint** — arrêter le proxy, rejouer le point 1 → lecture en mode offline
   (dégradé, cause tracée dans Seq). Relancer le proxy, session valide, puis l'arrêter
   **après** chargement (mode online, cache token chaud) et forcer une reconnexion IMAP
   après expiration du cache → `application/problem+json` 503.
6. **Session Keycloak-only (sans PSC)** — login/mot de passe sans broker PSC :
   `connection/status` → `mode: "offline"`, lecture cache OK.
7. **Sync background** — déclencher un sync, laisser tourner > 5 min → le sync ne
   meurt plus sur expiration de token (logs Seq : pas d'`AuthenticationException`
   XOAUTH2).

7 bis. **Le sync n'entretient pas la session (RG-S)** — se connecter, déclencher un
   sync, **fermer le client** (aucune requête praticien). Observer côté proxy :
   `docker exec psc-auth-proxy-redis redis-cli -a … TTL session:{sid}` **décroît**
   pendant que le sync tourne ; à 0 la session disparaît et les logs `api-mail`
   montrent l'arrêt propre du sync (pas d'`AuthenticationException`, pas de tentative
   de refresh). Contre-épreuve : même scénario avec le client ouvert et actif → la TTL
   remonte à ~1800 à chaque refresh Keycloak du client.
7 ter. **Course fermée** — client Angular ouvert et actif (refresh toutes les ~90 s)
   pendant qu'un sync de fond tire des jetons ; 15 min. **Attendu** : aucune
   déconnexion, zéro `PscTokenRefreshFailed` / `invalid_grant` dans Seq du proxy,
   des lignes `lock held, waiting` présentes.

**Liaison compte ↔ professionnel (ex-318) — le test de sécurité central de la US**

8. **Usurpation par cookie (RG-L1)** — rattachement avec le **bearer de A** et le
   **cookie de B** :
   ```bash
   curl -sk -X POST https://localhost:{port}/api/v1/account/mailboxes \
     -H "Authorization: Bearer {bearer de A}" -H "Client-Email: {mss de A}" \
     --cookie "proxy_session_id={sid de B}" \
     -H "Content-Type: application/json" -d '{"email":"{adresse mssante de B}"}' -i
   ```
   **Attendu** : `403`, corps `application/problem+json`, code `PscIdentityConflict`,
   **aucune ligne** créée (`docker exec postgres-pgvector psql -U postgres -d
   mss_registry -c "select count(*) from mss_accounts;"` inchangé), trace
   `MailboxAttached` en échec dans l'écran d'audit de A, journaux Seq à identifiants
   tronqués — **jamais** le cookie ni un jeton.
9. **Rattachement sans liaison (RG-L3)** — même appel **sans cookie**, avec
   `X-PSC-Token` de B : `401`, code dédié, rien de persisté — le jeton volé ne sert
   plus à rien. La **lecture** des dossiers d'une boîte déjà rattachée à A, sans
   cookie, fonctionne en mode offline.
10. **Chemin nominal** — bearer de A + cookie de A : rattachement accepté, boîte
    ouverte, `ValidatedByPscSubject` égal au `sub` PSC de la session de A (contrôler
    en base ou via l'écran de compatibilité).

**Clients**

11. **Web Angular** — `cd Client/Angular/front && npm start`, login PSC. DevTools →
    Network sur les appels api-mail : **absence** de `X-PSC-Token`, **présence** du
    cookie `proxy_session_id` (Request Cookies). Dossiers, lecture, envoi d'un mail de
    test → tout fonctionne. Session > 5 min avec activité intermittente → aucune
    déconnexion ni « token expiré ».
12. **Web Blazor** — même parcours sur le client Blazor : absence de l'en-tête,
    présence du cookie, messagerie fonctionnelle, écran de rattachement opérationnel.
13. **Mobile** — `cd Client/Mobile && npm start` ou émulateur Android (AVD Pixel,
    config 4096M). Login e-CPS (flux CIBA). Inspecteur réseau : absence de
    `X-PSC-Token`, cookie envoyé vers api-mail. Inbox, lecture, envoi. `localStorage`
    (`mobile_mss_session`) : plus de champ `pscAccessToken`. App ouverte > 5 min →
    inbox toujours fonctionnelle.
14. **Maintien de session longue** (web) — messagerie par intermittence pendant
    > 35 min (une action toutes les ~10 min) → jamais déconnecté (chaque refresh
    Keycloak prolonge cookie + session proxy). Puis inactivité totale > 30 min → à la
    prochaine action, redirection login propre.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — refactoring d'architecture sécurité, aucune
  exigence DSR nouvelle ; conforme à la trajectoire ANS token-secure du proxy
  (US-PROXY-2026-001)
- **Exigences DSR honorées** : non applicable — pas de nouvelle exigence ;
  renforce PGSSI-S : le token PSC ne transite plus par le navigateur ni la WebView,
  ni par le stockage local du device
- **INS** : non applicable — aucune manipulation de données patient
- **Authentification PS** : PSC / e-CPS via psc-auth-proxy, niveau eIDAS
  substantiel — flux de login inchangés (PSC web + CIBA mobile) ; seule la mécanique
  de distribution de l'access token change
- **Habilitations** : **resserrées**. L'identité professionnelle qui autorise le
  rattachement (`sub` PSC, RPPS) est celle de la session d'authentification du
  proxy, liée au compte au login par le grant RFC 7523 sur la liaison fédérée ;
  `api-mail` vérifie que la session appartient au porteur du bearer (RG-L1) et
  n'accepte plus aucune identité déclarée par le client. Exigence PGSSI-S de
  non-usurpation (référentiel d'authentification)
- **Interop CI-SIS** : non applicable — aucun échange métier modifié
- **Tracé PGSSI-S** : journaliser (Seq, corrélés par traceId) : échec de résolution
  de token (session expirée, proxy indisponible), échec d'authentification
  IMAP/SMTP — sans token, refresh token, ni session id en clair ; conservation
  identique à l'existant (6 mois logs techniques). Rattachement refusé pour session
  non liée au porteur (RG-L1) ou sans session liée (RG-L3) → trace d'audit métier
  `MailboxAttached` en échec, visible du praticien. Côté clients, aucun évènement
  nouveau
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant d'api-mail, inchangé ;
  bénéfice côté device : suppression d'un token d'accès à des DSCP du `localStorage`
  mobile
- **AIPD / impact RGPD** : **à mettre à jour** — aucun traitement nouveau, mais une
  **mesure de sécurité nouvelle sur le rattachement** (identité issue de la session
  d'authentification et liée au compte) à porter au registre des mesures, et une
  **réduction de surface** : le token PSC ne transite plus par le client ni par son
  stockage local

## Branches

Créées le 2026-09-24 par `/start 171`, depuis `origin/develop` de chaque repo. Un seul nom partout : `feat/task-171-backend-pull-token-psc`.

- `api-mail` (pushed) : `feat/task-171-backend-pull-token-psc`
- `client-blazor` (pushed) : `feat/task-171-backend-pull-token-psc`
- `client-mobile` (pushed) : `feat/task-171-backend-pull-token-psc`
- `client-angular` (code-only) : la forge écrit sur la branche actuellement checked out dans `Client/Angular/` — humain gère branche, commit, push, PR TFS

> **Dépendance proxy task-016 — état au `/start`** : `done-task-016` dans la forge du
> proxy (PR ouverte, branche `feature/task-016-contexte-psc-pour-un-appelant-serveur`,
> HAG en attente), **pas encore sur `origin/next`**. Contrat vérifié sur la branche :
> `PscContextDto { HasPsc, PscAccessToken, PscAccessTokenExpiresAtUtc, PscSub,
> SubjectNameId, KcSub, SessionExpiresAtUtc }`, `GET v1/internal/psc-context?keepAlive`,
> en-tête `X-Internal-Api-Key`, variable `PSC_CONTEXT_API_KEY`. `/develop` code et
> teste contre ce contrat (proxy mocké) ; **le test manuel de bout en bout et le
> merge de 171 supposent la PR de task-016 mergée et le proxy redéployé.**

## Develop log

*`/develop 171` — 2026-09-24, forge autonome. Une branche `feat/task-171-backend-pull-token-psc` sur `api-mail`, `client-blazor`, `client-mobile` (poussées) ; `client-angular` en code-only sur `feature/nova-rewriting-mss` (rien de commité, l'humain gère).*

### Ce qui a été livré

**api-mail** (3 commits : feature, passe qualité, statut sans boîte)
- `IPscTokenProvider` / `PscTokenProvider` : pull-only vers `GET {proxy}/v1/internal/psc-context?keepAlive=` (cookie `proxy_session_id`, `X-Internal-Api-Key`, bearer transmis), cache mode ~5 min / négatifs 60 s, cache token jusqu'à `exp − 30 s`, single-flight par session (`Lazy<Task>`, caches alimentés dans l'appel partagé), disjoncteur + timeout 5 s sans retry (`AddPscProxyClient`), mapping 200 `hasPsc` → online/offline, 401 → session expirée, 403 → `PscIdentityConflict`, autre → indisponible (dégradé). RG-L1 en défense en profondeur : `kcSub` de la projection comparé au `sub` du bearer **déjà établi par le pipeline** (`PscSessionKey.KcSub`), plus de re-parse du jeton.
- `UserContextInfo` : `PscToken`/`JwtToken` retirés ; `ProxySessionId`, `KeepAliveProxySession` (jamais copié vers les scopes de fond — RG-S), `SessionPscIdentity`, `IsOnlineMode` explicite, `OnlinePscIdentity`.
- `UserContextEnricherMiddleware` : le mode est le verdict du proxy, plus aucune lecture d'en-tête ; `X-PSC-Token` reçu = ignoré ; conflit d'identité → 403 `problem+json` + trace `MailboxAttached Success=false` sur la route marquée `[MailboxAttachEndpoint]` (métadonnée d'endpoint, plus de suffixe de chemin) ; bypass de test pose lui-même le mode depuis `mssSub`/`mssRpps` (RG-5, le banc n'appelle jamais le proxy).
- Authentification IMAP/SMTP : jeton résolu **à l'instant** de l'authentification via le provider (`ImapConnectionService`, `BackgroundImapService`, `SmtpConnectionFactory`) ; exceptions typées `UnauthorizedException` (401), `PscIdentityConflictException` (403), `UnavailableException` (503) portées par `IErrorCoded` → `code` dans le `ProblemDetails` (règle 12). `TokenValidationService` supprimé ; garde task-165 « token expiré → 401 » supprimée avec le snapshot.
- `AccountController` : attach avec identité de session + jeton du proxy (RG-L2) ; sans session PSC liée → 401 `PSC_SESSION_REQUIRED` (RG-L3) ; refus audités par `TraceMailboxAttachRefused` (RG-L4, aucun nouveau `AuditActionType`).
- **`GET /api/v1/connection/status` passe `[MailboxNotRequired]`** : les trois clients y lisent le mode de la *session* pour décider « PSC requis » vs « onboarding » sur un compte sans boîte (actions en attente / dernière synchro à 0 / null dans ce cas). Décision prise en cours de `/develop` : sans elle, aucun client ne peut prendre cette décision une fois le jeton PSC local disparu.
- CORS `.AllowCredentials()` (origines exactes, tests preflight) ; `SyncController` sans extrait de jeton ; k6 `identity.js`/`config.js` sans `X-PSC-Token` ni `pscTokenFor`.
- Config : section `PscProxy` (`BaseUrl`, `TimeoutSeconds`, `ModeCacheSeconds`, `NegativeCacheSeconds`, `TokenRefreshMarginSeconds`) ; `InternalApiKey` **uniquement par variable d'environnement** (`PscProxy__InternalApiKey`, AppHost : `PSC_CONTEXT_API_KEY`, défaut local `dev-psc-context-key-change-me` — la valeur dev du proxy, alignée le 2026-09-24 (`d74fb3f6`) après constat en test manuel : le premier défaut `local-dev-psc-context-key` était rejeté par le proxy en `PROXY-API-9010`, toute session lue hors ligne ; le feature flag `PscContextController` était bien à `true`), jamais dans un appsettings versionné.
- Tests : `PscTokenProviderTests` (caches, single-flight, mapping, contrat — champs `refreshToken`/`pscRefreshToken`/`pscIdToken` ignorés), `PscSessionResolutionTests` (middleware, 8 cas), `PscSessionIntegrationTests` (11 cas de bout en bout : pipeline réel Bearer → middleware → `GlobalExceptionHandler` → vrai `AccountController`, proxy scripté : online/offline/dégradé, en-tête ignoré, 403 + trace + registre jamais atteint, 401 typé sur attach sans session, 503/401 typés sur authentification engagée), `ConnectionControllerTests` (statut sans boîte), CORS credentialed, `AccountControllerTests`, `MailboxManagementServiceTests`, `UserContextInfoTests`, `ImapConnectionServiceTests`, `ConnectionModeServiceTests`, `GlobalExceptionHandlerTests`.

**client-blazor** (2 commits : feature, passe qualité)
- Plus de `X-PSC-Token` (`HttpRequestService`, `MailboxAccountsService`). `SessionCookieCredentialsHandler` sur les clients typés `HttpRequestService`, `MailSseService`, `MailboxAccountsService` → toute requête api-mail (SSE compris) porte `credentials: include`.
- `PscTokenRefreshService` → `SessionRefreshService` (une seule interface, Domain) : plus de pré-refresh PSC avant chaque requête ; seul le chemin 401 → refresh → rejeu (task-156) reste, en tâche partagée sur `IAuthService.RefreshTokenAsync`.
- `MailboxSessionService.IsOffline` = verdict backend (`GET connection/status` via le registre, liste + statut en parallèle, hors ligne tant que le statut n'est pas connu) ; `ConnectionStatusService.IsOfflineMode` et `ConnectionStateService.IsOnline` délèguent à cette source unique ; `OfflineStatusWidget` sans compte à rebours PSC ; `SyncProgressWidget` sur le statut backend ; `Index`/`CallbackApi` sans refresh PSC au démarrage.
- `TokenInfoDto` (dtos-mss) garde ses champs `Psc*` — hors scope, le client ne les consomme plus pour décider du mode.

**client-angular** (code-only — **rien de commité**, branche `feature/nova-rewriting-mss`)
- `mss-headers.interceptor.ts` : plus d'en-tête PSC, `withCredentials: true` vers `MSS_API_URL` (+ spec neuve). `psc-token-guard.interceptor` + spec, `mss-psc-token.token` (`MSS_PSC_ACCESS_TOKEN`, `MSS_PSC_REFRESH_FN`), `jwt-expiration.utils` + spec **supprimés** ; `app.config.ts` nettoyé ; `MSS_PSC_TOKEN_PRESENT` supprimé.
- `MailboxSessionStore.offline` = statut backend (`MailboxAccountsService.connectionStatus()`, `Promise.all` avec la liste) ; `offline-status-widget` et `sync-progress-widget` lisent ce signal ; `mss-api.service` : fetch SSE IA sans en-tête PSC, `credentials: 'include'`, `Client-Session-Id` = `MailboxSessionStore.clientSessionId()` (plus `jwt.sid`) ; `EventSource` des flux mail-events / notifications en `withCredentials: true`.
- `ITokenAggregate` garde `pscAccessToken` (forme de la réponse `/auth/token` du proxy, ignorée par le client).
- Build `nx build weda2` OK, tests `nx run-many -t test` : 2575 passés, 14 skippés. **À la charge de l'humain** : commit, push TFS, PR. Deux `environment.ts` (`apps/mss`, `apps/weda2`) sont modifiés localement par l'humain (`mssApiUrl` local) — non touchés par la forge.

**client-mobile** (1 commit, passe qualité incluse)
- `MssHeadersInterceptor` : plus d'en-tête PSC, `withCredentials: true`, préventif sur la seule échéance Keycloak (`earliestExpiry` et `psc-token-expiry.spec.ts` supprimés ; filet 401 + 429 inchangés, tests existants verts).
- `AuthSession` sans `pscAccessToken`/`pscAccessTokenExpiresAt` ; `AuthSessionService` purge les champs hérités de `localStorage` et ne les persiste jamais (tests) ; `hasPscToken` supprimé.
- `MailboxSessionService.offline` = statut backend (`MailboxAccountsService.connectionStatus()`, modèle `ConnectionStatusDto` ajouté) ; fetch SSE IA et `EventSource` credentialed.
- Aucun écran modifié → `/stitch-design` et `/verify-visual` sans objet.

### Passe qualité `/simplify` (par repo, avant push)
- api-mail : single-flight `Lazy<Task>` + caches alimentés dans l'appel partagé, `KcSub` dans la clé (plus de re-parse du bearer), `IErrorCoded`, `TraceMailboxAttachRefused`, `OpaqueIdentifierMask`, métadonnée `[MailboxAttachEndpoint]`, `OnlinePscIdentity`, filtre d'exception SMTP, garde hors-ligne sans exception dans la sync de fond, section `PscProxy` liée une fois. Écartés (conception, pas qualité) : cache de mode sur Redis, gestionnaire de résilience standard, unification `PSC_SESSION_REQUIRED`/`PscMismatch`.
- client-blazor : interface unique, tâche partagée sur `IAuthService`, client typé + handler pour le registre, source unique du mode, refresh parallèle, clés Localizer mortes retirées. Écartés : TTL sur le statut par écran, timer du widget (pré-existant).
- client-angular / client-mobile : `EventSource` credentialed (trou relevé par la revue altitude), sync-progress-widget sur le store, `loadAccountsAndStatus()` factorisé, `MailboxSessionStore` injecté directement (plus d'`Injector`), CSS mort. Écarté : remplacer `MailboxAccountsService.connectionStatus()` par `MssApiService.getConnectionStatus()` (symétrie des trois clients : le registre est la surface sans boîte).

### DOD — auto-contrôle
- Vérifié vert : builds et tests des quatre repos (api-mail 172/492/840/2511/527 ; Blazor 272 ; Angular 2575 ; mobile 881) ; `X-PSC-Token` = 0 hit hors commentaires et assertions d'absence dans les specs ; `PscPreview` = 0 ; aucun nouveau `AuditActionType` ; timeout ≤ 5 s ; CORS credentialed ; mapping proxy ; `kcSub` ; RG-L1..L4 (unit + intégration) ; RG-S (clé sans `keepAlive` sur les scopes de fond, `CopyIdentityTo` ne copie pas le drapeau) ; bypass sans appel proxy ; `withCredentials` testé sur les trois clients (SSE compris) ; `localStorage` mobile sans jeton PSC (test) ; `isAccessTokenExpired` Keycloak seul (test) ; `MSS_PSC_TOKEN_PRESENT` supprimé ; Blazor `SessionRefreshService` + tests 401 de task-156 verts.
- **Non couvert par la forge — reste à l'humain** :
  - « test d'intégration RG-S : session proxy mockée à TTL 60 s, sync actif → arrêt après 60 s » : couvert au niveau unitaire (aucune clé `keepAlive=true` émise par les scopes de fond), pas de test à horloge réelle de 60 s.
  - « tir k6 court en profil loadtest atteint IMAP » : non exécuté (AppHost + Dovecot requis) — à faire au HAG.
  - « durées de vie du realm de production relevées » : hors de portée de la forge (accès prod) ; les valeurs locales (KC 120 s, PSC 120 s, refresh 1800 s) sont dans « Prérequis de déploiement ».
  - Doc EPIC E013 et note AIPD : `/tech-writer` en fin de cycle ; l'AIPD est une décision humaine.
  - **Prérequis d'exploitation** : PR task-016 du proxy mergée et redéployée ; `PSC_CONTEXT_API_KEY` posée côté api-mail et proxy **avec la même valeur** ; cookie `proxy_session_id` en `Domain=.weda.fr` ; à valider sur émulateur que la WebView Capacitor envoie le cookie (plan B de l'ADR sinon — ne pas improviser).

## Sonar log

*`/sonar 171` — 2026-09-24, Mode A (chaîné), SonarQube 9.9.8 (`sonar.login`), clé `healthplatform-api-mail`, période new code = 30 jours (donc plus large que la task).*

- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 86,9 % (seuil du gate 80 %)
- Phase 1 — Issues fixées : 8 (0 bug / 0 vuln / 8 smells / 0 hotspot) — S3925 ×2 (triplet de constructeurs), S4457 ×2 (validation hors `async`), S125 ×2, S1075, S1172, toutes sur les fichiers de la task
- Phase 1 — Résolues « faux positif » avec justification : 2 (S3925 sur `UnauthorizedException` / `PscIdentityConflictException` — la règle réclame le constructeur de sérialisation binaire, obsolète en .NET 10 (SYSLIB0051) ; même convention que les exceptions existantes du dépôt)
- Phase 1 — Tests ajoutés : 21 (`PscTokenProviderTests` +10 : annulation, section incomplète, bearer absent, projection sans identité / sans compte / sans jeton / sans échéance, corps vide, clé nulle ; `PscSessionContractTests` : exceptions, `IsConfigured`, `OpaqueIdentifierMask`)
- Phase 1 — Itérations : 2 (analyse → fixes + tests → ré-analyse)
- Phase 1 — Findings new code **hors périmètre de la task** (27, non traités, inchangés) : E016 (`ITenantRegistryClient` CA1068 ×13, `PostgresTenantRegistryClient` S3776 + 2, `TenantRegistryExceptions` S3925 ×2), AV0011 ×4 et CA1822 sur des specs d'intégration antérieures, CA1859 ×3 sur des specs Imap d'une autre task — fichiers non touchés par 171 (règle 6, périmètre isolé). La cible de couverture 95 % de `agents/sonar-targets.yml` n'est pas atteinte sur la période (467 lignes neuves non couvertes, dont ~10 sur les fichiers de 171 : branche défensive `catch (Exception)` de `GetModeCoreAsync`, `SmtpConnectionFactory.AuthenticateAsync` OAuth2 non testable sans `SmtpClient` réel).
- Phase 2 (legacy) : non lancée — cibles projet déjà tenues (bugs 0, vuln 0, A/A/A), couverture projet 88,2 % < 95 % relève de la dette historique, hors chemin critique de la task
- Build / tests : ✓ green (172 / 2532 / 492 / 840 / 527). Un test d'intégration est tombé une fois pendant la 2e passe OpenCover (526/527, nom non capturé par le harnais de scan) et repasse vert au rejeu immédiat en Release : transitoire sous instrumentation, non attribuable à la task.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-09-20) | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 85,1 % | 86,9 % | +1,8 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 3 | 3 | 0 |
| Code smells (projet) | 217 | 223 | +6 (aucun sur les fichiers de 171 ; +4 new code hors périmètre, cf. ci-dessus) |
| Code smells (new code) | 23 | 27 | +4 (0 sur la task après fixes) |
| Coverage (projet) | 87,9 % | 88,2 % | +0,3 pt |
| Duplication | 0,5 % | 0,5 % | → |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

*`/lint-angular 171` — 2026-09-24, Mode A (chaîné), code-only, base `origin/next`, scope lint `tag:scope:mss` (`mss` + `mss-lib`), branche de travail `feature/nova-rewriting-mss`.*

- Baseline : 1 erreur, 56 warnings (`jsdoc/require-example` 35, `max-lines` 17, `complexity` 4)
- Itération 1 (auto-fix `--fix`) : l'erreur unique — `prettier/prettier` « Delete `␍⏎` », un CRLF résiduel dans `libs/mss/src/core/services/mss-api.service.ts` — corrigée par l'auto-fixer. **0 erreur restante**, warnings inchangés (56).
- Itérations 2..5 : non consommées (plus d'erreur).
- Warnings restants : tous sur des méthodes antérieures à la task (`@example` vides laissés par d'anciens squelettes d'auto-fix : `purge()`, `loadCoverage()`, `querySyncStatus()`, `startCountdown()`, `getSyncCoverage()` ; `max-lines` sur `mss-api.service.ts` 2293 lignes ; `complexity` hors périmètre). Acceptés best-effort — hors des hunks de 171, laissés au diff minimal pour le commit humain.
- Build `nx affected -t build` : ✓ pour `weda2` et toutes les libs (`mss-lib`, `design-system`, `dmp-lib`, `shared`, …) ; **✗ `mss:build:production`** (l'application de démonstration `apps/mss`) — `fileReplacements` référence `apps/mss/src/environments/environment.prod.ts`, **supprimé par le commit `7de0cee3` « First MSS implementation » de la branche `feature/nova-rewriting-mss`**, bien avant 171 (le fichier existe sur `origin/next`). Défaut pré-existant de la branche, hors périmètre de la task, **à signaler à l'humain** (recréer le fichier ou retirer le `fileReplacements`). Tests `nx affected -t test --skipNxCache` : ✓ (34 + 457 + 2575 + 15 passés, 14 skippés).
- `conventions/angular.md` : aucune correction manuelle → rien à alimenter
- Git : aucune opération (code-only) — l'humain commit/push sur TFS et ouvre la PR ; deux `environment.ts` modifiés localement par l'humain restent hors du périmètre de la forge.

## Lint mobile log

*`/lint-mobile 171` — 2026-09-24, Mode A (chaîné), branche `feat/task-171-backend-pull-token-psc`, arbre propre.*

- Baseline `npm run lint` : **All files pass linting** — 0 erreur, 0 warning
- Itérations : 0 consommée (rien à corriger) ; build et tests déjà verts en sortie de `/develop` (881/881)
- `conventions/angular.md` : aucune correction manuelle → rien à alimenter
- Git : aucun commit nécessaire

## Visual verify log

*`/verify-visual 171` — 2026-09-24 : **skip propre**. Aucun écran `client-mobile` touché par la task (services d'authentification, intercepteur HTTP, modèles et specs uniquement — aucun template ni style modifié), aucun `## Stitch design log`. Rien à capturer, l'état visuel global de l'application est inchangé.*

## PRs

*Ouvertes le 2026-09-24 par `/review 171`, label `awaiting-human-merge` — HAG (règle 10) : test manuel puis merge par l'humain.*

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/248
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/82
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/78
- `client-angular` : **code-only — humain gère commit/push TFS et ouverture PR.** Travail non commité sur la branche `feature/nova-rewriting-mss` (`Client/Angular/front`). Build `nx build weda2` et tests `nx run-many -t test` verts au `/review`. Fichiers modifiés :
  - `M apps/weda2/src/app/app.config.ts`
  - `M apps/weda2/src/app/core/interceptors/mss-headers.interceptor.ts`
  - `?? apps/weda2/src/app/core/interceptors/mss-headers.interceptor.spec.ts` (nouveau)
  - `M apps/weda2/src/lib/auth/models/mail-session-closer.model.ts`
  - `M libs/mss/src/core/index.ts`
  - `D libs/mss/src/core/interceptors/psc-token-guard.interceptor.ts` + `.spec.ts`
  - `D libs/mss/src/core/tokens/mss-psc-token.token.ts`
  - `D libs/mss/src/core/utils/jwt-expiration.utils.ts` + `.spec.ts`
  - `M libs/mss/src/core/services/mail-events-stream.service.ts`
  - `M libs/mss/src/core/services/mailbox-accounts.service.ts`
  - `M libs/mss/src/core/services/mss-api.service.ts` + `.spec.ts`
  - `M libs/mss/src/core/services/mss-api.vcard.service.spec.ts`
  - `M libs/mss/src/core/services/notification-stream.service.ts`
  - `M libs/mss/src/core/stores/mailbox-session.store.ts` + `.spec.ts`
  - `M libs/mss/src/core/tokens/mss-psc-sign-in.token.ts`
  - `M libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `M libs/mss/src/ui/offline-status-widget/offline-status-widget.component.{ts,html,scss}`
  - `M libs/mss/src/ui/sync-progress-widget/sync-progress-widget.component.ts`
  - (hors forge, modifications locales de l'humain : `apps/mss/src/environments/environment.ts`, `apps/weda2/src/environments/environment.ts`)
  - ⚠️ Deux incidents d'outillage à connaître avant de committer : (1) le `npm ci` du `/review` a échoué (binaires natifs verrouillés par un `nx serve weda2` que l'humain avait laissé tourner) et a été rattrapé par `npm install` — `package-lock.json` restauré à l'identique, mais **relancer `npm ci` une fois le dev server arrêté** pour remettre `node_modules` strictement au lockfile ; (2) la forge a arrêté un processus `esbuild.exe` orphelin issu de ce `node_modules` — le dev server peut nécessiter un redémarrage. (3) `apps/mss` (démonstrateur) ne build pas en production sur cette branche : `environment.prod.ts` supprimé par le commit `7de0cee3`, antérieur à 171.
- `devops`, `psc-proxy-*` : managed manually by the human (task-016 côté proxy déjà `done`, PR en attente de merge).

## Code Review Summary

- **api-mail** : CHANGES REQUESTED → **2 bloquants corrigés dans le cycle** (`1d5823ef`) puis APPROVED après re-validation (172 / 2537 / 492 / 840 / 527 verts ; 1 flaky pré-existant `ImapServiceIntegrationTests.GetEmailAsync_WithFullContent…`, vert au rejeu) : caches et single-flight du fournisseur PSC indexés sur (session, sub du bearer) — RG-L1 tenait uniquement à froid ; exceptions typées 503/403 traversant les catch-alls IMAP (règle 12). 6 suggestions non bloquantes consignées dans la PR.
- **client-blazor** : APPROVED (0 bloquant, 6 suggestions — test devenu sans objet, `RefreshAsync` et statut sur échec de liste, relais `OnChanged`, double registration, `TokenInfoDto.PscAccessToken` à retirer côté dtos-mss).
- **client-angular** (code-only) et **client-mobile** : APPROVED (0 bloquant, 6 suggestions — spec `connectionStatus()`, réécriture immédiate de la session assainie, type `mode`, commentaire task-283 périmé, `getConnectionStatus()` sans appelant).
- Écart de process assumé : `/review` a corrigé les deux bloquants api-mail au lieu de halter (règle 13 — les défauts étaient ceux de la forge, dans le même cycle) ; Sonar rejoué sur le code final.

## Timings

*(généré par `tools/timing/report.sh --task task-171 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 56 s | — | — | — | — |
| /develop | ok | 1 h 54 min | 28 (3 min 53 s) | 17 (13 min 00 s) | — | api-mail 19B/11T, client-blazor 4B/2T, client-angular 2B/2T, client-mobile 3B/2T |
| /sonar | ok | 23 min 05 s | 5 (1 min 09 s) | 18 (13 min 56 s) | 6 (1 min 46 s) | 2 itération(s), api-mail 5B/18T |
| /lint-angular | ok | 5 min 12 s | 1 (24 s) | 1 (45 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 35 s | — | — | — | — |
| /verify-visual | skipped | 0.5 s | — | — | — | aucun écran client-mobile touché (services, intercepteur, modèles, specs uniquement) ; pas de Stitch design log |
| /review | ok | 2 h 53 min | 8 (1 min 00 s) | 8 (5 min 35 s) | — | api-mail 4B/3T, client-mobile 1B/2T, client-angular 2B/2T, client-blazor 1B/1T, 2 bloquants api-mail corrigés dans le cycle ; clé interne proxy alignée après test manuel |
| /tech-writer | ok | 2 min 11 s | — | — | — | — |
| **Total cycle** | | **5 h 19 min** | **42 (6 min 27 s)** | **44 (33 min 18 s)** | **6 (1 min 46 s)** | |

Autres commandes mesurées : lint ×4 (1 min 43 s), restore ×3 (53 s)
