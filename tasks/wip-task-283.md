# todo-task-283.md — Le mobile perd l'accès à sa boîte ~3 min sur 5 : le refresh est piloté par la mauvaise horloge, et l'échec sort en 500 muet

**Repos**: client-mobile, api-mail
**Dependencies**: — aucune. Complémentaire de `todo-task-275` (dont le plan de test
manuel §2 « laisser l'app ouverte > 5 minutes puis ouvrir un mail avec PJ » est
**aujourd'hui non passant** à cause de ce défaut). Tactique vis-à-vis de
`tasks/onhold/todo-task-171` (ADR-2026-07-25 backend-pull), qui reste ON HOLD sur
l'infra `*.weda.fr` — voir « Articulation avec l'ADR ».
**Epic**: E012

> **Origine** : session de test `client-mobile` du 2026-08-30, analyse Seq
> (`seq-local`, `localhost:5341`). Symptôme rapporté par l'humain :
> « JWT token appears to be expired for user robert.specialiste0060694@… ».

> ### ✅ Re-vérification du 2026-08-30 — **valide**, après mise à jour de `develop`
>
> Rejouée sur `develop` @ `041cd91` (api-mail) et `46015b7` (client-mobile).
> Trois corrections, aucune remise en cause du fond :
>
> 1. **Renumérotée 276 → 281 → 283.** Deux collisions successives :
>    `archived-task-276` … `280` existaient déjà (mergées entre-temps), puis
>    `todo-task-281` a été créée **en parallèle sur une autre machine**
>    (`edc31a5`, contention archivage/lecture de dossier, E015) et poussée sur
>    `origin/develop` la première. La sienne est conservée telle quelle ;
>    celle-ci prend **283**.
> 2. **Le tableau des sites d'aplatissement passe de 10 à 23 sites**, re-dérivé
>    mécaniquement. `ImapService.cs` a été profondément remanié par
>    `archived-task-277` (+183 lignes, `DeadSessionPolicy`), donc les numéros de
>    ligne d'origine étaient périmés. Le DOD exige désormais **un seul point de
>    conversion**, pas 23 corrections copiées.
> 3. Toutes les autres citations vérifiées une à une et **inchangées** :
>    `UserContextInfo.cs:84` (alias `JwtToken` → `PscToken`),
>    `ImapConnectionService.cs:301` / `:304-307` (commentaire task-165) / `:315`,
>    `BackgroundSyncManager.cs:89`, `session.model.ts:35-56`,
>    `mss-headers.interceptor.ts:30` (marge 30 s) et `:233` (`isSessionExpired`).
>
> **`archived-task-277` ne recouvre pas cette US** : elle rejoue une session
> poolée coupée par le serveur, et son `DeadSessionPolicy` ne filtre que des
> **exceptions** (`SocketException`, `IOException`, `ProtocolException`…). Le
> jeton expiré remonte un `Result.Unauthorized`, jamais une exception — aucune
> interaction, aucun risque de boucle de rejeu.
>
> La durée de vie de 5 min du jeton Keycloak est désormais **prouvée** et non
> plus déduite : `exp − iat = 300 s` sur un jeton décodé le 2026-08-30.

## Objectif

Un praticien qui utilise l'app mobile perd l'accès à sa boîte MSSanté **par
tranches de 2 à 3 minutes, en boucle**, sans rien faire de particulier. L'app se
répare ensuite toute seule, puis retombe. Cette US supprime la panne et rétablit
le filet de sécurité qui aurait dû l'absorber.

### Ce qui se passe réellement

`api-mail` s'authentifie à l'IMAP/SMTP en **XOAUTH2 avec le jeton PSC**, pas avec
le bearer Keycloak : `UserContextInfo.JwtToken` est un **alias de `PscToken`**
(`Api/Mail/src/Domain/Entities/UserContextInfo.cs:84-88`, `get => PscToken`), et
c'est cette valeur que `ImapConnectionService.AuthenticateClientAsync` passe à
`SaslMechanismOAuth2` (`:315`) après l'avoir testée (`:301`).

Or les deux jetons n'ont pas la même durée de vie :

| Jeton | Durée de vie | Mesure du 2026-08-30 |
|---|---|---|
| Access token **Keycloak** (`Authorization: Bearer`) | **5 min** | intervalles de refresh 5 min 00,6 s |
| Access token **PSC** (`X-PSC-Token`) | **~1,98 min** | `[AutoTokenRefresh] new token valid for 1.9858… minutes` (6 relevés, tous ≈ 1,98) |

Et `client-mobile` calcule son échéance préventive **uniquement** sur l'`exp` du
jeton **Keycloak** : `sessionFromTokenAggregate` ne renseigne
`accessTokenExpiresAt` que depuis le payload de `accessToken`
(`Client/Mobile/src/app/core/auth/session.model.ts:35-56`). L'expiration du jeton
PSC n'est suivie **nulle part** côté client.

**Conséquence** : pendant ~3 minutes sur 5, le mobile envoie un bearer Keycloak
parfaitement valide accompagné d'un `X-PSC-Token` périmé. Tout endpoint qui
touche IMAP ou SMTP échoue.

### Le « rattrapage » observé n'est pas un mécanisme, c'est un effet de bord

L'humain a constaté que l'app se remet à fonctionner toute seule. C'est exact, et
c'est **accidentel** : quand l'horloge Keycloak franchit enfin son seuil
(`exp − 30 s`), le refresh préventif part, et le proxy re-frappe **les deux**
jetons — le jeton PSC est réparé **au passage**. D'où le dents-de-scie relevé
dans Seq :

```
16:07:12  REFRESH
16:10:26  PSC-EXPIRED          <- le jeton PSC est mort depuis ~16:09:12
16:10:29  PSC-EXPIRED
16:10:39  PSC-EXPIRED
16:12:12  REFRESH   (+301s)    <- « rattrapage » sur l'horloge Keycloak
16:16:56  REFRESH   (+284s)
16:20:32  PSC-EXPIRED          <- mort depuis ~16:18:55
16:20:34  PSC-EXPIRED
16:20:45  PSC-EXPIRED
16:21:03  PSC-EXPIRED
16:21:03  HTTP-500             <- GET /api/v1/mail/folders/INBOX
16:23:21  REFRESH   (+384s)    <- « rattrapage », 2 min 20 d'indispo
16:27:18  PSC-EXPIRED
16:29:12  REFRESH   (+352s)
```

Le motif se reproduit à **chaque** cycle, sans exception.

### Pourquoi le filet réactif ne rattrape pas

`ImapConnectionService` retourne bien un `Result.Unauthorized(...)` — le
commentaire task-165 (`:303-308`) dit explicitement que c'est « pour que le
refresh réactif des frontends, branchés sur 401, se déclenche correctement ».
Mais le statut est **aplati en `Error`** en remontant, par le motif
`Result<T>.Error(connectResult.Errors.FirstOrDefault() ?? …)` qui ne conserve que
le message :

| Fichier | Sites de retour (lignes, `develop` @ `041cd91`) |
|---|---|
| `ImapService.cs` | 231, 748, 3081, 3185, 3278, 3435, 3672, 4051, 4097, 4156, 4207, 4268 |
| `ImapFolderService.cs` | 110, 208, 278, 347, 413, 505, 611 |
| `FlagPropagationService.cs` | 294 |
| `MailExportService.cs` | 331 |
| `BackgroundImapService.cs` | 92, 144 (forme `string.Join`) |

**23 sites au total.** Le compte a été re-dérivé sur `develop` le 2026-08-30 ;
une première estimation à 10 sous-évaluait `ImapService` et `ImapFolderService`.
Trois formes cohabitent (`.FirstOrDefault() ?? ConnectionFailed`,
`ImapConnectionFailedPrefix + (…)`, `string.Join(", ", …)`), et
`ImapService:231` est la seule multi-lignes (elle ajoute un repli sur
`ValidationErrors`) — d'où l'intérêt d'**un seul point de conversion** plutôt
que 23 corrections copiées.

Trace du 2026-08-30 16:21:03 (`TraceId=367fc544f490a462546003604f400e50`) :

```
Result-mapped 500 on /api/v1/mail/folders/INBOX (ResultStatus=Error):
JWT token has expired. Please refresh your session.
HTTP GET /api/v1/mail/folders/INBOX - Status=500, ElapsedMs=333, Size=0
```

`ResultStatus=Error` → **500**, et `Size=0` → **corps vide**. Le
`isSessionExpired()` de `mss-headers.interceptor.ts` teste `status === 401` **ou**
un `detail` matchant `/expired|refresh your session/i` : sans 401 et sans corps,
aucune des deux branches ne matche. Task-165 est présente dans le code mais
**inerte en pratique**.

### Ce que fait cette US

1. **`client-mobile`** — le déclencheur préventif s'aligne sur la **plus proche
   des deux échéances**. Le jeton PSC est un JWT (`IsTokenExpired` côté api-mail
   le décode en splittant sur `.` et en lisant `exp`), donc `decodeJwtPayload`
   suffit : `AuthSession` porte un nouveau champ `pscAccessTokenExpiresAt`, et
   `isAccessTokenExpired()` raisonne sur `min(accessTokenExpiresAt,
   pscAccessTokenExpiresAt)` (échéance absente ⇒ ignorée, comme aujourd'hui).
2. **`api-mail`** — les sites listés ci-dessus **propagent le statut** du
   `Result` de connexion au lieu de l'aplatir en `Error`, pour qu'un jeton
   expiré ressorte en **401 + `ProblemDetails`** (règle 12) avec le `detail`
   « JWT token has expired. Please refresh your session. » — ce qui restaure le
   filet réactif comme garde-fou même si le préventif rate un cas.

Les deux moitiés sont indissociables (règle 11) : la première supprime la panne,
la seconde garantit qu'une panne du même genre ne redevienne pas silencieuse.

### Articulation avec l'ADR backend-pull (hors périmètre)

`ADR-2026-07-25` (`tasks/onhold/todo-task-171` / `172`) supprime la cause racine :
`api-mail` irait chercher le jeton PSC lui-même et l'en-tête `X-PSC-Token`
disparaîtrait. C'est **le bon fix**, mais il est **ON HOLD** sur un blocage
d'infra (api-mail doit être servi sous `*.weda.fr` pour le transport cookie). Ce
travail est donc **tactique et non concurrent** : il ne crée aucun mécanisme
nouveau, il aligne une horloge et rétablit un contrat d'erreur déjà voulu par
task-165. Quand 171/172 seront livrées, le champ `pscAccessTokenExpiresAt`
deviendra simplement sans objet et se retirera avec l'en-tête.

### Effet de bord à connaître

Aligner le refresh sur le jeton PSC fait passer la cadence de **~5 min à ~2 min**.
Or chaque refresh **rote la claim `sid`**, qui clé le pool IMAP/SMTP d'api-mail —
donc le nombre de reconnexions IMAP passerait d'environ 12/h à 30/h. Ce couplage
est traité par **`todo-task-282`**, qu'il faut livrer **dans le même lot et
*avant* celle-ci** — voir « Ordre de livraison » ci-dessous.

## Ordre de livraison — `282` d'abord, puis `283`

Les deux US forment un lot indissociable (règle 11), mais **l'ordre compte** :

1. **`todo-task-282`** découple la clé du pool IMAP de la claim `jti`, ce qui
   ramène le régime établi de ~10 sessions IMAP simultanées par praticien à ~5.
2. **`todo-task-283`** (celle-ci) fait ensuite passer la cadence de refresh de
   ~5 min à ~2 min. Livrée **en premier**, elle ferait franchir le plafond de
   10 connexions IMAP par utilisateur ; livrée **après `282`**, elle reste sous
   le plafond.

L'ordre numérique est donc aussi l'ordre d'exécution.

## Hors périmètre

- Tout changement du `psc-auth-proxy` (autre forge, `D:\Workspaces\psc-auth-proxy`).
- L'ADR backend-pull (`onhold/todo-task-171`, `172`).
- Le snapshot de jeton figé du sync de fond (`BackgroundSyncManager.StartSyncAsync:89`
  copie `jwtToken` dans un local rejoué pour toute la durée du sync) — **déjà dans
  le périmètre de `onhold/todo-task-171`** (« Background sync : stocker le session
  id, plus de snapshot de token »). Ne pas le dupliquer ici ; c'est lui qui produit
  les `PSC-EXPIRED` à `CorrelationId="-"`, hors requête.
- `client-angular` et `client-blazor` : le même défaut d'horloge existe
  probablement, mais il n'est ni mesuré ni reproduit ici. À instruire séparément.

## Definition of Done

**client-mobile**
- [ ] Build passes (`npm ci && npm run build`), tests pass
      (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `AuthSession` porte `pscAccessTokenExpiresAt?: number`, alimenté par
      `sessionFromTokenAggregate` depuis l'`exp` du `pscAccessToken`
- [ ] Test unitaire : un agrégat dont le `pscAccessToken` expire **avant** le
      `accessToken` produit une session dont l'échéance effective est celle du PSC
- [ ] Test unitaire : `pscAccessToken` absent ou non décodable ⇒
      `pscAccessTokenExpiresAt` vaut `undefined` et le comportement est
      **identique à aujourd'hui** (aucune régression sur les sessions token-only)
- [ ] Test unitaire (`mss-headers.interceptor`) : jeton Keycloak encore valide
      mais jeton PSC dans la marge ⇒ le refresh préventif **est** déclenché avant
      l'envoi, et la requête part avec les deux jetons frais
- [ ] Test unitaire : le refresh reste **single-flight** (N requêtes concurrentes
      ⇒ un seul `POST /auth/refresh`) — non-régression du `refreshed$` existant
- [ ] Aucun changement dans `src/environments/*`

**api-mail**
- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur),
      tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échec) — hors les
      3 rouges pré-existants connus (middleware DB-name stale, IMAP cancel,
      MailExport PDF)
- [ ] Les **23** sites listés dans le tableau propagent le `ResultStatus` du
      `Result` de connexion au lieu de l'aplatir en `Error`, via **un seul**
      point de conversion partagé (pas 23 copies du même `switch`)
- [ ] Test d'intégration : un `X-PSC-Token` expiré sur `GET /api/v1/mail/folders/INBOX`
      renvoie **401** (pas 500), en `application/problem+json`, avec un `detail`
      non vide contenant « refresh your session »
- [ ] Test d'intégration : le corps de cette réponse ne contient **ni** jeton,
      **ni** stack trace, **ni** donnée de santé (règle 12)
- [ ] Test unitaire : une panne de connexion IMAP **non** liée au jeton
      (socket, TLS) reste mappée comme aujourd'hui (503 / 500 selon le cas) —
      non-régression du mapping existant

**Bout en bout**
- [ ] Aucun `HTTP-500` sur un endpoint mail pendant 10 minutes d'usage continu
      (voir le plan de test manuel)

## Manual Test Plan

Pré-requis : `psc-auth-proxy` lancé (AppHost), `api-mail` lancé (AppHost Aspire),
app mobile `npm start` (http://localhost:8100), Seq sur http://localhost:5341.

1. Login e-CPS complet (RPPS de test, code d'appairage validé sur l'app e-CPS)
   → boîte de réception affichée.
2. **Laisser l'app ouverte et naviguer en continu pendant 10 minutes** : ouvrir
   la boîte de réception, ouvrir un mail, revenir, ouvrir un mail avec pièce
   jointe, changer de dossier. Faire une action toutes les ~30 s.
   **Attendu** — aucune erreur, aucun écran vide, aucun retour au login. La PJ
   s'ouvre à chaque tentative.
3. Dans Seq, filtrer `ApplicationName='mss.mail.api' and StatusCode = 500` sur la
   fenêtre du test : **attendu — 0 événement**.
4. Dans Seq, filtrer `@Message like '%appears to be expired%'` sur la même
   fenêtre : **attendu — 0 événement en contexte de requête** (`CorrelationId`
   renseigné). Les événements à `CorrelationId="-"` (sync de fond) sont
   **attendus et hors périmètre** — ils relèvent de `onhold/todo-task-171`.
5. Dans Seq, filtrer `ApplicationName='auth-proxy.Api' and @Message like
   '%Client requesting OAuth%'` : **attendu — un refresh toutes les ~2 min**
   (et non toutes les ~5 min), tous suivis d'un `✅ [Refresh] … re-minted`.
6. **Vérification du filet réactif** : arrêter le `psc-auth-proxy`, attendre
   3 minutes, puis naviguer. **Attendu** — l'app bascule proprement sur
   `/login?expired=1` (pas d'écran blanc, pas de boucle de requêtes, pas de 500
   affiché à l'utilisateur). Redémarrer le proxy, re-login e-CPS → OK.
7. Aucun jeton en clair dans Seq sur toute la session.

## Notes pour /develop

- Le décodage du jeton PSC réutilise `decodeJwtPayload` déjà exporté par
  `auth.service.ts` — ne pas écrire un second décodeur. Attention : cette
  fonction est tolérante (retourne `{}` sur échec), donc `pscAccessTokenExpiresAt`
  doit rester `undefined` quand `exp` est absent, jamais `NaN`.
- La marge `EXPIRY_MARGIN_MS` (30 s) est déjà définie dans
  `mss-headers.interceptor.ts` ; la réutiliser pour les deux échéances plutôt
  que d'en introduire une seconde. Avec un jeton PSC de ~119 s, cela donne une
  cadence de refresh d'environ 90 s — c'est attendu, ce n'est pas une tempête
  (cf. le single-flight, et task-161 pour le 429).
- Côté api-mail, `Ardalis.Result` conserve le statut si on **retourne le
  `Result` d'origine remappé** plutôt que d'en fabriquer un nouveau avec
  `.Error(...)`. Vérifier le helper existant avant d'en introduire un : le but
  est un seul point de conversion, pas 23 copies du même `switch`.
- `BackgroundImapService` utilise `string.Join(", ", …)` là où les autres
  utilisent `.FirstOrDefault()` — harmoniser au passage, mais sans élargir le
  périmètre à d'autres fichiers.
- Ne pas toucher `UserContextInfo.JwtToken` (l'alias vers `PscToken`) : le
  renommer est tentant mais c'est un changement transverse à ~20 sites, et l'ADR
  backend-pull va le supprimer. Se contenter d'un commentaire XML qui explicite
  que c'est le **jeton PSC**, pas le bearer Keycloak — c'est précisément
  l'ambiguïté qui a masqué ce bug.

## Branches

Créées par `/start` le 2026-08-30 depuis `origin/develop`, même nom sur les
trois repos : **`fix/task-283-psc-refresh-clock-and-401-propagation`**
(préfixe `fix/` — c'est un correctif de défaut, pas une fonctionnalité).

- `client-mobile` (pushed) : [`fix/task-283-psc-refresh-clock-and-401-propagation`](https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-283-psc-refresh-clock-and-401-propagation)
- `api-mail` (pushed) : [`fix/task-283-psc-refresh-clock-and-401-propagation`](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-283-psc-refresh-clock-and-401-propagation)
- `dtos-mss` (pushed, auto-inclus) : branche créée par précaution ; aucun
  changement de contrat attendu — si elle reste à 0 commit, pas de PR ni de
  publish NuGet.
- `client-angular`, `client-blazor`, `devops`, `psc-proxy-*` — non listés,
  hors périmètre.

### État de l'antécédent d'ordre

`task-282` est **mergée et archivée** le 2026-08-30 (`9edb6d8` api-mail,
`2daa61d` client-mobile) : la condition d'ordre posée par « Ordre de livraison »
est satisfaite côté code.

⚠️ **Réserve consignée** : les deux critères « bout en bout » de la DOD de 282
— une seule valeur de `ClientSessionId` sur 10 min, `🌱 New ImapClient` borné
aux 5 réplicas — **n'ont pas encore été mesurés au banc**. C'est cette mesure
qui prouve que le régime est bien retombé de ~10 à ~5 sessions IMAP par
praticien, donc que la cadence de refresh ramenée à ~2 min par la présente US
reste sous le plafond de 10 connexions. Le lancement de 283 a été décidé par
l'humain en connaissance de cette réserve. À lever au plan de test manuel.
