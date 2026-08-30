# todo-task-276.md — Le mobile perd l'accès à sa boîte ~3 min sur 5 : le refresh est piloté par la mauvaise horloge, et l'échec sort en 500 muet

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

| Fichier | Lignes |
|---|---|
| `ImapService.cs` | 218-224, 641-643, 1421-1425 |
| `ImapFolderService.cs` | 109-110, 207-208, 277-278 |
| `MailExportService.cs` | 328-331 |
| `FlagPropagationService.cs` | 288-294 |
| `BackgroundImapService.cs` | 90-92, 142-144, 204-… (`string.Join`) |

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
est traité par **`todo-task-277`**, à livrer de préférence dans le même lot.

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
- [ ] Les 10 sites listés dans le tableau propagent le `ResultStatus` du
      `Result` de connexion au lieu de l'aplatir en `Error`
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
  est un seul point de conversion, pas 10 copies du même `switch`.
- `BackgroundImapService` utilise `string.Join(", ", …)` là où les autres
  utilisent `.FirstOrDefault()` — harmoniser au passage, mais sans élargir le
  périmètre à d'autres fichiers.
- Ne pas toucher `UserContextInfo.JwtToken` (l'alias vers `PscToken`) : le
  renommer est tentant mais c'est un changement transverse à ~20 sites, et l'ADR
  backend-pull va le supprimer. Se contenter d'un commentaire XML qui explicite
  que c'est le **jeton PSC**, pas le bearer Keycloak — c'est précisément
  l'ambiguïté qui a masqué ce bug.
