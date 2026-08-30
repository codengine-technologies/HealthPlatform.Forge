# todo-task-277.md — Chaque refresh de jeton jette le pool IMAP : la clé de session suit une claim `sid` qui tourne

**Repos**: client-mobile, api-mail
**Dependencies**: — aucune techniquement, mais **à livrer dans le même lot que
`todo-task-276`** : celle-ci fait passer la cadence de refresh de ~5 min à ~2 min,
ce qui multiplie par ~2,5 le churn décrit ici. Livrer 276 seule dégrade cet axe.
**Epic**: E012

> **Origine** : session de test `client-mobile` du 2026-08-30, analyse Seq
> (`seq-local`, `localhost:5341`), en marge de l'investigation `todo-task-276`.

## Objectif

`api-mail` recrée un pool IMAP+SMTP complet (connexion TCP + TLS + validation de
certificat IGC-Santé + authentification XOAUTH2) **à chaque refresh de jeton**,
alors que rien dans la session du praticien n'a changé. Le pool précédent est
abandonné et meurt sur son timeout d'inactivité. Cette US découple la clé de
session du cycle de vie des jetons.

### Ce qui se passe

`MailClientSessionManager` clé son pool sur
`$"{userContext.Email}_{userContext.ClientSessionId}"`
(`Api/Mail/src/Application/Session/MailClientSessionManager.cs`,
lignes 101, 138, 182, 254, 267, 279, 288, 485, 491, 508, 534).

Et `UserContextEnricherMiddleware:610-616` (`PopulateIdentityFromClaims`) remplit
`ClientSessionId` par un **triple repli** :

```csharp
userContext.ClientSessionId = context.User.FindFirstValue("sid")
                              ?? context.User.FindFirstValue(JwtRegisteredClaimNames.Jti)
                              ?? Guid.NewGuid().ToString("N")[..16];
```

**C'est le deuxième repli — `jti` — qui est effectivement emprunté**, établi par
recoupement de deux observations indépendantes :

1. `client-mobile` ne pose l'en-tête `Client-Session-Id` que si `session.sessionId`
   existe, et `sessionId = jwtPayload['sid']` (`session.model.ts`). Or il ne le
   pose **jamais** : 1420 requêtes à `ClientSessionId=unknown` côté
   `RequestLoggingMiddleware` sur la fenêtre 16:00–16:30. ⟹ **le jeton Keycloak
   ne porte pas de claim `sid`.**
2. Sans `sid`, le repli suivant est `jti`. Ce qui est cohérent avec le modèle du
   proxy : l'échange est un **JWT Authorization Grant RFC 7523**
   (`grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`,
   `KeycloakTokenExchangeService`), rejoué **intégralement** à chaque
   `/auth/refresh` — le jeton n'est pas rafraîchi, il est **re-frappé**. Aucune
   session Keycloak n'est créée (cf. `todo-task-275` : « aucune session pour le
   client `weda` — session transiente »), donc pas de `sid`.

**Ce qui déclenche donc la rotation : chaque nouveau jeton d'accès**, c'est-à-dire
chaque `POST /auth/refresh` et chaque login. Et c'est **structurel** : la RFC 7519
impose que `jti` soit unique par jeton. Aucun réglage côté Keycloak ni côté proxy
ne peut stabiliser cette valeur — **seul un identifiant fourni par le client peut
l'être**, ce qui est exactement l'objet de cette US.

Corrélation relevée le 2026-08-30, **1:1 sans exception** (valeurs de la forme
`trrtag:{guid}`, absentes de tout dépôt : elles viennent du jeton) :

| Refresh (auth-proxy) | Nouveau `sid` vu côté api-mail | Écart |
|---|---|---|
| mint 16:01:53 | `7293a19f…` | +9 s |
| 16:07:12 | `c9dc8720…` | +4 s |
| 16:12:12 | `f257f578…` | +11 s |
| 16:16:56 | `9fd48000…` | +1 s |

### Ce que ça produit

- Une **reconnexion IMAP + SMTP complète toutes les ~5 min** (et ~2 min après
  `todo-task-276`), re-authentification XOAUTH2 comprise.
- Le cache d'UIDs attaché à la clé de session est jeté à chaque rotation →
  `[ListFolder] UIDs cache present but status expired — re-validating INBOX
  against IMAP`, à répétition.
- Des warnings en boucle sur les pools orphelins, réapés au bout de 5 min
  d'inactivité :
  `[MailClientSession] ♻️ Session expired … ImapIdle=00:05:49 (timeout 00:05:00)`
  — relevés à 16:14:20, 16:15:20 (×2), 16:16:20, 16:18:20.
- Des courses sur une clé qui vient d'être remplacée :
  `[RefreshSession] session not found for Session=…_trrtag:f257f578-…`
  (16:12:29, 16:13:08).
- Une consommation de connexions IMAP qui pousse contre le **plafond de 10
  connexions par utilisateur** — voir l'arithmétique ci-dessous, qui est le
  vrai enjeu de cette US.

### Le multiplicateur oublié : le pool est **par processus**, et il y a 5 réplicas

`MailClientSessionManager` est un **singleton** (`ServiceCollectionExtensions.cs:80`),
donc son dictionnaire `_sessions` est **local au processus**. Or `api-mail` tourne
en **5 réplicas** (`src/AppHost/AppHost.cs:350`, `.WithReplicas(5)`), derrière un
proxy DCP qui répartit les requêtes. Vérifié le 2026-08-30 : 5 processus
`mss.mail.api.exe` (PID 51772, 51860, 52096, 51464, 44056) lancés par un seul
AppHost.

**Conséquence** : pour une même clé `{email}_{sid}`, chaque réplica qui sert au
moins une requête construit **sa propre** session IMAP. Preuve dans Seq — quatre
`MailClientSession` d'identifiants distincts, portant une clé **rigoureusement
identique**, vivant simultanément et expirant dans le même balayage :

```
16:10:20.321  sess=8d5feeec  imapIdle=00:05:00  CID=…_trrtag:7293a19f-63d9-…
16:10:20.367  sess=32beb210  imapIdle=00:05:00  CID=…_trrtag:7293a19f-63d9-…
16:11:20.273  sess=8089f725  imapIdle=00:05:26  CID=…_trrtag:7293a19f-63d9-…
16:11:20.288  sess=85135a69  imapIdle=00:05:48  CID=…_trrtag:7293a19f-63d9-…
```

Les deux multiplicateurs se composent. Relevé sur 34 minutes, **un seul
praticien** : **27 sessions IMAP créées**, soit 7 clés (rotations de `sid`) × 3 à
5 réplicas touchés.

**L'arithmétique qui rend cette US nécessaire** : 5 réplicas × 2 générations
(l'ancienne qui draine pendant 5 min + la nouvelle) = **10 sessions IMAP
simultanées pour un praticien**, soit exactement le **plafond de 10 connexions
par utilisateur**. On est à la limite aujourd'hui. Après `todo-task-276` (refresh
toutes les ~2 min au lieu de ~5), l'ancienne génération n'a plus le temps de
mourir avant que la suivante arrive : **on dépasse**. C'est la raison pour
laquelle les deux US doivent partir ensemble.

Supprimer la rotation de clé ramène le régime établi à **1 session par réplica**,
soit 5 au lieu de 10, quelle que soit la cadence de refresh.

### Deux pièges à connaître avant de coder

**1. Le chemin nominal d'api-mail ne lit pas du tout l'en-tête.**
`PopulateIdentityFromClaims` (appelé en `:323`) écrase `ClientSessionId` depuis
les seules claims. L'en-tête `Client-Session-Id` n'est lu que par
`RequestHelper.TryExtractJwtToken` (`:285`), invoqué uniquement dans la branche
**test-bypass** (`:182`, suite `/qa` Playwright). Il ne s'agit donc pas de
« prioriser » l'en-tête : il faut **commencer à le lire** dans le chemin
authentifié normal.

**2. Le troisième repli est une bombe à retardement.** Si un jeton arrivait sans
`sid` **ni** `jti`, `ClientSessionId` vaudrait `Guid.NewGuid()` — donc une valeur
**différente à chaque requête**, donc **une session IMAP par requête**. Rien
aujourd'hui ne garantit la présence de `jti`. Ce repli doit disparaître au profit
d'une valeur déterministe (l'en-tête client, ou à défaut une constante par
utilisateur), et un test doit épingler qu'aucun chemin ne peut produire une clé
par requête.

### Ce que fait cette US

Donner au pool IMAP une clé **stable pour la durée de vie de la session
applicative**, insensible aux rotations de jeton :

1. **`client-mobile`** — tirer un identifiant de session applicatif (GUID) **au
   login**, le persister avec la session dans `localStorage`, et l'envoyer
   systématiquement en `Client-Session-Id`. Il survit aux refresh et ne change
   qu'au login ou au logout.
2. **`api-mail`** — privilégier l'en-tête `Client-Session-Id` quand il est
   présent ; ne retomber sur la claim `sid` que s'il est absent (compatibilité
   avec `client-angular` / `client-blazor`, non modifiés ici).

## Hors périmètre

- `client-angular` et `client-blazor` : ils continuent de fonctionner par le
  repli sur `sid`. Leur alignement est une US séparée.
- Le timeout d'inactivité de 5 min des sessions IMAP/SMTP (`ImapTimeout`,
  `SmtpTimeout`) : non touché.
- Le plafond de 10 connexions IMAP par utilisateur : non touché.
- Toute optimisation du pool elle-même (pré-chauffage, partage entre onglets).

## Definition of Done

**client-mobile**
- [ ] Build passes (`npm ci && npm run build`), tests pass
      (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `AuthSession` porte un identifiant de session applicatif stable, généré au
      login et persisté dans `localStorage` avec le reste de la session
- [ ] Test unitaire : deux `refreshSession()` successifs **conservent** cet
      identifiant (alors que `accessToken` et la claim `sid` changent)
- [ ] Test unitaire : `logout()` puis un nouveau login produisent un identifiant
      **différent**
- [ ] Test unitaire : une session restaurée depuis `localStorage` sans cet
      identifiant (session écrite par une version antérieure) en obtient un
      nouveau sans planter et sans forcer un retour au login
- [ ] Test unitaire (`mss-headers.interceptor`) : l'en-tête `Client-Session-Id`
      est posé sur **toute** requête MSS, avec cette valeur stable

**api-mail**
- [ ] Build passes (0 erreur), tests pass (0 échec — hors les 3 rouges
      pré-existants connus)
- [ ] `PopulateIdentityFromClaims` lit l'en-tête `Client-Session-Id` **dans le
      chemin authentifié nominal** (aujourd'hui il ne le lit pas du tout) et ne
      retombe sur les claims que s'il est absent
- [ ] Test unitaire : en-tête présent ⇒ `UserContextInfo.ClientSessionId` vaut
      l'en-tête, quelles que soient les claims `sid`/`jti` du jeton
- [ ] Test unitaire : en-tête absent ⇒ repli sur `sid` puis `jti`
      (non-régression Angular/Blazor)
- [ ] Le repli `Guid.NewGuid()` par requête a disparu ; test unitaire : **aucun**
      chemin ne produit deux `ClientSessionId` différents pour deux requêtes
      successives du même utilisateur avec le même jeton
- [ ] Test d'intégration : deux requêtes portant le **même** `Client-Session-Id`
      mais des jetons dont le `sid` diffère résolvent la **même** clé de session
      de pool

**Bout en bout**
- [ ] Sur 10 minutes d'usage continu couvrant au moins 3 refresh : **une seule**
      valeur de `ClientSessionId` dans les logs, et **aucun**
      `[MailClientSession] Session expired` déclenché par une rotation
- [ ] Sur la même fenêtre, le nombre de `[MailClientSession] 🌱 New ImapClient`
      est **borné par le nombre de réplicas** (≤ 5), au lieu des ~27 relevés le
      2026-08-30 — c'est la mesure qui prouve que le plafond de 10 connexions
      IMAP par praticien n'est plus menacé

## Manual Test Plan

Pré-requis : `psc-auth-proxy` lancé, `api-mail` lancé (AppHost Aspire), app
mobile `npm start` (http://localhost:8100), Seq sur http://localhost:5341.

1. Login e-CPS complet → boîte de réception affichée.
2. Naviguer en continu pendant **10 minutes** (une action toutes les ~30 s),
   de façon à traverser au moins 3 refresh.
3. Dans Seq, requête :
   `select ClientSessionId, count(*) from stream where ApplicationName='mss.mail.api' group by ClientSessionId`
   sur la fenêtre du test.
   **Attendu** — **une seule** valeur non-`unknown`, et plus aucune requête à
   `unknown` (le mobile pose désormais l'en-tête partout).
4. Dans Seq, filtrer `@Message like '%MailClientSession%Session expired%'` :
   **attendu** — aucun événement corrélé à un refresh. (Un pool réapé après une
   vraie inactivité de plus de 5 min reste normal.)
5. Dans Seq, filtrer `@Message like '%UIDs cache present but status expired%'` :
   **attendu** — nettement moins fréquent qu'avant (le cache n'est plus jeté à
   chaque rotation). Ce point est **indicatif**, pas bloquant.
6. Se déconnecter, se reconnecter : **attendu** — un `ClientSessionId`
   **différent** apparaît, et la boîte se charge normalement.
7. **Non-régression Angular** : ouvrir `client-angular` sur la même stack,
   charger la boîte de réception → fonctionne (repli sur `sid` intact).

## Notes pour /develop

- Ne pas réutiliser la claim `sid` ni dériver l'identifiant d'un jeton :
  c'est précisément ce qui crée le couplage. Un `crypto.randomUUID()` tiré au
  login et persisté suffit.
- `AuthSessionService.readFromStorage()` doit rester tolérant : une session
  persistée par une version antérieure n'a pas le champ. Lui en attribuer un à
  la volée, **sans** invalider la session (ne pas ajouter de condition qui
  retourne `null` — cela déconnecterait tous les utilisateurs à la mise à jour).
- Le mobile envoie déjà `Client-Session-Id` conditionnellement dans `addHeaders`
  (`if (session.sessionId)`) — rendre la pose inconditionnelle plutôt que
  d'ajouter un second en-tête.
- Côté api-mail, ne pas modifier `MailClientSessionManager` : il consomme
  `userContext.ClientSessionId`, il suffit que le middleware le remplisse mieux.
  Cela garde le diff petit et le repli Angular/Blazor gratuit.
- `Client-Session-Id` figure déjà dans la liste des en-têtes lus
  (`RequestHelper.cs:285`, `RequestLoggingMiddleware.cs:18`) — vérifier qu'aucun
  des deux chemins ne diverge après le changement, sinon les logs et le pool
  raconteront deux histoires différentes (c'est ce qui rendait ce bug difficile
  à lire : `unknown` côté logging, `trrtag:…` côté pool).
