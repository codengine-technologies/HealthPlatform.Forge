# todo-task-303.md — Comptes multi-messageries (vague 1/2 — backend, contrat, banc) : la boîte MSSanté devient une sélection validée par l'annuaire et par l'identité PSC, plus un claim Keycloak

**Repos**: sdk, api-mail
**Dependencies**: **task-299** (annuaire — comptes, messageries, rattachements, et le contrat
`IDirectoryClient` dans le SDK que cette US **étend**). Indépendante de task-300 / task-301
(journal d'audit) et de task-302 (accès admin).
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — c'est l'US qui donne son sens produit à l'annuaire : un praticien, un compte,
plusieurs boîtes MSSanté, sans jamais se déconnecter pour en changer.

> **Vague 1 d'une US en deux vagues.** La vague 2 est **task-304** (gestion des comptes dans les
> trois fronts : sélecteur, bascule en direct, cohérence PSC). Règle 11 : les PRs de cette vague
> portent `awaiting-us-completion` tant que task-304 n'est pas en PR prête — un backend
> multi-boîtes sans sélecteur est de la plomberie, pas une valeur pour le médecin. Le test humain
> se fait sur la US assemblée (plan de test de task-304).
>
> `dtos-mss` est auto-inclus par `/start` — des changements de contrat **sont** attendus
> (DTOs boîtes + `AuditActionType`). Les repos `psc-proxy-*` sont **hors automation** : voir
> « Proxy Keycloak ».

## Objective

Qu'un praticien authentifié une seule fois (Pro Santé Connect via le proxy / Keycloak) puisse
**rattacher plusieurs boîtes MSSanté à son compte**, chacune avec sa base isolée, et que le
backend expose **la liste des boîtes compatibles avec l'identité PSC de la session** — celles
entre lesquelles les fronts (task-304) pourront basculer **en direct**, sans ré-authentification,
sans nouveau jeton.

Le fondement est exact et vérifié dans le code : l'authentification IMAP/SMTP se fait en
**XOAUTH2 avec le jeton PSC** (`ImapConnectionService` → `SaslMechanismOAuth2`), et le jeton PSC
identifie le **professionnel** (RPPS en `SubjectNameID`), pas une boîte. Un même jeton ouvre donc
légitimement toute boîte que **l'opérateur MSSanté** a rattachée à ce PS — chez un ou plusieurs
opérateurs. **Un médecin = N BAL MSSanté, une seule connexion PSC.** C'est l'opérateur, pas
nous, qui est l'autorité de ce rattachement.

### Ce qui existe aujourd'hui — vérifié, avec les fichiers

| Mécanisme | Où | Ce que ça impose |
|---|---|---|
| La boîte est un **claim du JWT Keycloak** : `mssEmail` (+ `mssSub`, `mssRpps`) | `UserContextEnricherMiddleware.cs` — `userContext.Email = claim mssEmail` | **1 utilisateur Keycloak = 1 boîte = 1 base**. Changer de boîte = changer de jeton |
| L'en-tête `Client-Email` doit être **égal** au claim, sinon 403 | `UserContextEnricherMiddleware.RejectClientEmailMismatchAsync` ; `RequestHelper.cs:94-106` | L'en-tête existe déjà sur les trois fronts et sur k6 — il ne porte aujourd'hui **aucune** information, il fait écho au claim |
| L'onboarding (task-037) : **A.** sonde IMAP `POST /api/v1/account/mss-imap-test` `{email}` puis **B.** `PUT {proxy}/v1/admin/mss-profile` qui écrit l'attribut Keycloak, puis **C.** « déconnectez-vous et reconnectez-vous » | `MssAccountOnboardingService.TestImapConnectionAsync(email, pscToken)` ; fronts : `MssOnboardingService` ×3 | La persistance est **orchestrée par le client** (A puis B) et le nouveau jeton n'arrive qu'après une **déconnexion** — c'est ce parcours qui est refondu |
| Le flux SSE lit l'identité **uniquement dans le claim** (`User.FindFirstValue("mssEmail")`) | `MailEventsController.cs:65-83` | Un `EventSource` ne pose pas d'en-tête : la boîte doit être passée **en paramètre de requête** et validée |
| Cross-check PSC/KC (task-048) : `mssSub == sub PSC`, `mssRpps == SubjectNameID PSC` — `mssSub`/`mssRpps` sont des **copies** du jeton PSC écrites par le backend-auth à l'opt-in (task-049), projetées en claims par des mappers (task-050) | `ApplyPscKcCrossCheckAsync` | Le **principe** (le jeton PSC présenté appartient au même PS que le compte) est conservé ; la **référence** migre : elle est lue dans l'annuaire (`compte.PscSubject`, `compte.Rpps`), plus dans le jeton KC. **Les trois claims `mssEmail`, `mssSub`, `mssRpps` disparaissent du modèle cible** |
| Nom de base = `f(email, rpps)` → `u_{rpps}_{slug}_{hash}` | `UserContextInfo.BuildUserDatabaseName` | La base est une propriété du **couple (PS, boîte)**. Inchangé : la boîte sélectionnée détermine la base, structurellement |
| Pool IMAP+SMTP clé `{email}_{sessionId}` | `AuthSession.sessionId` (mobile, task-282) ; `UserContextInfo.ClientSessionId` | Déjà clé par boîte : N boîtes = N pools qui coexistent, rien à changer |
| Le jeton PSC **tourne toutes les ~2 min** (task-283) ; le bearer Keycloak ~5 min | `AuthSession.pscAccessTokenExpiresAt` | « Même jeton PSC » ne peut signifier que **même identité PSC** — jamais même chaîne |
| `Settings` vivent dans la base du tenant | `SettingsController`, `UserSettingsRepository` | Les réglages (signature…) restent **par boîte**. Voulu. |
| Banc k6 : une identité = `(email loadtest-{n}@…, rpps 9{n}, pscSub)` ; en-têtes `X-Test-Bypass`, `Client-Email`, `Client-Rpps`, `Client-Psc-Sub`, `Client-Session-Id`, `X-PSC-Token` | `tests/loadtest-k6/lib/identity.js` ; bypass `RequestHelper.cs:255-290` lit `Client-Email` comme identité | 1 utilisateur = 1 boîte. Le banc doit gagner la dimension « boîtes par compte », à **défaut 1** pour ne pas casser les références |
| Lecture du `sub` Keycloak | mémoire projet : `MapInboundClaims` non désactivé ⇒ `FindFirstValue("sub")` rend **null** | Piège connu pour `/develop` : lire `ClaimTypes.NameIdentifier` ou désactiver le mapping — sinon aucun compte ne se résout |

## Principe directeur

**Le jeton Keycloak n'est plus qu'une identité d'authentification (`sub`). Tout ce qui est
MSSanté — l'identité PSC du professionnel, son RPPS, ses boîtes — vit dans l'annuaire central.
La boîte est une sélection par requête, validée contre l'annuaire ET contre l'identité PSC de la
session.**

État cible, sans ambiguïté :
- **aucun** claim `mssEmail`, `mssSub`, `mssRpps` dans le jeton Keycloak — ni lu, ni attendu ;
- **aucun** appel à `PUT /v1/admin/mss-profile` — la route et les mappers deviennent sans objet ;
- un praticien dont le jeton ne porte **que** `sub` doit pouvoir s'onboarder, rattacher deux
  boîtes, basculer et travailler de bout en bout. **C'est le test d'acceptation de l'US.**

Concrètement, l'en-tête `Client-Email` **garde son nom et sa place** sur les trois fronts et sur
k6 ; seule sa **sémantique** côté serveur change :

- aujourd'hui : `Client-Email` **==** claim `mssEmail`, sinon 403 ;
- demain : `Client-Email` **∈** boîtes du compte **compatibles avec l'identité PSC présentée**,
  sinon 403.

C'est ce qui rend l'US **transverse mais petite** sur le protocole : aucun nouvel en-tête, aucun
changement de route, aucun changement de forme des appels métier.

## Règle métier centrale — compatibilité PSC (demande humaine du 2026-09-13)

> **Un médecin peut basculer en direct entre deux boîtes TANT QUE ces deux boîtes sont issues de
> la même identité PSC.** Le backend doit **lister les boîtes compatibles** avec le jeton PSC de
> la session.

Formalisation :

1. **Identité PSC de la session** = `(sub, SubjectNameID)` du `X-PSC-Token` courant. C'est une
   **identité**, stable pour le PS ; le jeton lui-même tourne toutes les ~2 min.
2. **Boîte compatible** = rattachement `Active` dont `ValidatedByPscSubject` (l'identité PSC dont
   la sonde XOAUTH2 a réussi au rattachement) **==** identité PSC de la session, et dont le
   compte est **ancré** sur cette même identité (`compte.PscSubject`, `compte.Rpps`).
3. **Bascule en direct** = changer la valeur de `Client-Email` (et le paramètre `mailbox` du
   SSE) pour une boîte compatible, **sans** ré-authentification, **sans** nouveau jeton PSC,
   **sans** nouveau bearer : le **même** `X-PSC-Token` ouvre la nouvelle boîte en XOAUTH2 chez
   son opérateur. **Mais côté backend, la bascule est une fin de session suivie d'une nouvelle
   session** (demande humaine du 2026-09-13) — voir la section dédiée ci-dessous : l'ancienne
   session de boîte est **fermée explicitement** (IMAP/SMTP, synchro de fond, contexte), jamais
   laissée expirer.
4. **Boîte non compatible** = tout le reste, avec une raison explicite : `Detached`,
   `AuthFailing`, `PscIdentityMismatch` (théorique : un compte est ancré sur une seule identité,
   mais la règle est écrite et testée, pas déduite), `NoPscToken`.
5. **Sans jeton PSC** (mode hors ligne existant, `IsOfflineMode`) : la compatibilité n'est pas
   évaluable ; la liste est rendue avec `NoPscToken`, la bascule reste possible **en lecture
   locale** de ce qui est déjà synchronisé — exactement le comportement hors ligne d'aujourd'hui,
   étendu à N boîtes. Aucune ouverture IMAP.

## Bascule = fin de session + nouvelle session (demande humaine du 2026-09-13)

> « Le switch doit imposer comme un logout sur le backend, le nettoyage des sessions IMAP par
> exemple. Puis l'utilisateur bascule sur une autre session avec le backend. »

**Ce qui existe déjà, vérifié** : `POST /api/v1/sync/logout` (`SyncController.LogoutCleanupAsync`
→ `BackgroundSyncManager.CleanupUserAsync(email, clientSessionId)`, task-285) ferme la session de
boîte `{email}_{sessionId}` **localement puis sur tous les pods** (diffusion Redis, best-effort),
arrête la synchro de fond si c'était la dernière session de cette boîte, et vide le contexte
utilisateur (`resetUserContext: true`). Les trois fronts l'appellent déjà à la déconnexion
(`SyncProgressService.LogoutCleanupAsync`, `mss-api.service.ts` Angular et mobile). **La bascule
réutilise exactement ce mécanisme** — pas un second chemin de fermeture.

**Protocole de bascule, vu du backend :**

1. **Fin de session** — `POST /api/v1/sync/logout` avec les en-têtes de la session **sortante**
   (`Client-Email` = ancienne boîte, `Client-Session-Id` = ancien identifiant). Effets : pool
   IMAP+SMTP de `{ancienne}_{ancien id}` fermé sur tous les pods, synchro de fond arrêtée si
   dernière session, contexte vidé, flux SSE de l'ancienne boîte clos côté serveur.
2. **Nouvelle session** — le front tire un **nouveau** `Client-Session-Id` (UUID, comme au
   login — `newClientSessionId()` côté mobile) et envoie `Client-Email` = nouvelle boîte. Le
   premier appel ouvre un pool neuf `{nouvelle}_{nouvel id}`, démarre la synchro de fond de cette
   boîte comme aujourd'hui au premier contact, et le SSE est réabonné avec `?mailbox=`.

**Garde serveur — la nouvelle session est imposée, pas conseillée.** Un `Client-Session-Id` est
**lié à la première boîte qu'il a ouverte** (marqueur Redis `{sessionId} → email`, TTL = durée
de vie de session). Le même identifiant présenté avec une **autre** `Client-Email` ⇒ **409**
`ProblemDetails` `SESSION_MAILBOX_MISMATCH` — un front qui « changerait juste l'en-tête » sans
clore la session est refusé. Le multi-onglets (même boîte, même identifiant) reste légitime.

**Ce que la bascule n'est pas** : ni une déconnexion Keycloak / PSC (le bearer et le
`X-PSC-Token` sont conservés), ni un `forceLoad` du front. Le médecin ne se ré-authentifie pas ;
c'est sa **session de boîte** qui change, pas son identité.

**Journalisation PGSSI-S** : la session de boîte est une frontière d'imputabilité. Deux
évènements supplémentaires dans `AuditActionType` : `MailboxSessionOpened` (première requête
d'un couple `(email, sessionId)`) et `MailboxSessionClosed` (`/sync/logout`, ou expiration côté
serveur avec la raison). Une bascule produit donc un `Closed` sur l'ancienne boîte et un `Opened`
sur la nouvelle — c'est ainsi qu'elle est tracée, pas par un évènement « switch ». La trace
`Information` actuelle de task-285 (« Logout close order received ») devient redondante avec le
journal et reste en `Debug`.

## Modèle de sécurité — le point qui ne se négocie pas

Le claim `mssEmail` était **signé par Keycloak**. L'appartenance à l'annuaire est un **état
serveur écrit par le compte lui-même**. Pour que le remplacement ne soit pas un affaiblissement :

1. **L'opérateur MSSanté est l'autorité.** Une boîte n'est rattachée que si la sonde IMAP
   **réussit, côté serveur, avec le jeton PSC de l'appelant** — jamais sur la foi d'un client
   qui affirme que l'étape A a réussi. Rattacher = **sonder puis persister, dans le même appel,
   dans cet ordre** (deux appels `IDirectoryClient`, sans transaction commune — l'atomicité
   « rien persisté si la sonde échoue » vient de l'ordre, pas d'une transaction). Un PS ne peut
   rattacher que ce que son opérateur lui ouvre : sa boîte personnelle, et les boîtes
   organisationnelles où sa structure l'a habilité.
2. **L'isolation reste structurelle.** Même si l'appartenance était contournée, la base atteinte
   serait `f(email, rpps_de_l'appelant)` — **jamais** la base d'un autre PS. Le multi-boîtes ne
   crée aucun chemin de lecture inter-praticiens.
3. **Re-validation continue.** Chaque login IMAP réussi re-valide de fait le rattachement. Une
   boîte dont l'authentification échoue durablement est marquée `AuthFailing` (donc non
   compatible) — jamais détachée silencieusement, remise `Active` au premier succès.
4. **Détacher ne supprime rien.** Le rattachement est marqué `Detached` (date) ; la base est
   conservée ; la purge suit les règles de dormance de task-299 (décision 5). Détacher est
   journalisé.
5. **Cinq évènements journalisés** : configuration d'accès — `MailboxAttached`,
   `MailboxDetached`, `MailboxDefaultChanged` ; frontières de session — `MailboxSessionOpened`,
   `MailboxSessionClosed`. Une bascule est tracée par le couple `Closed`/`Opened`, jamais par un
   évènement « switch » ; les lectures restent tracées par boîte comme aujourd'hui.

## Backend — `api-mail`

### Résolution du compte, de l'identité PSC et de la boîte (middleware)

- **Compte** ← `sub` Keycloak (voir le piège `MapInboundClaims`), résolu dans l'annuaire via
  `IDirectoryClient`. Un jeton dont le `sub` est inconnu crée le compte (upsert task-299,
  décision 2), **sans identité PSC ni RPPS** tant qu'aucune boîte n'a été rattachée.
- **Identité PSC du compte — ancrage** (reprend le contrat de task-049, côté `api-mail`) :
  au **premier rattachement réussi**, le `sub` et le `SubjectNameID` du jeton PSC qui vient de
  passer la sonde IMAP sont écrits sur le compte (`PscSubject`, `Rpps`) **et** sur le
  rattachement (`ValidatedByPscSubject`). Ce jeton est le seul dont on sait qu'il est
  authentique : **l'opérateur MSSanté en a validé la signature** en acceptant le XOAUTH2 —
  `api-mail`, lui, ne la vérifie pas (commentaire de `ApplyPscKcCrossCheckAsync`). Jamais
  d'ancrage sur un simple passage de requête.
- **Cross-check PSC (ex-task-048), référence annuaire** : sur toute requête portant
  `X-PSC-Token`, `sub == compte.PscSubject` et `SubjectNameID == compte.Rpps`, comparaison
  `Ordinal` stricte ; compte **non ancré** ⇒ seules les routes `[MailboxNotRequired]` passent.
  Les claims `mssSub` / `mssRpps` ne sont **plus lus**. `PscIdentityOptions.Enforce`
  (`MSS_ENFORCE_PSC_IDENTITY`) garde son rôle observation / enforcement.
- **Boîte** ← `Client-Email` si présent, validé **∈ boîtes compatibles** (cache mémoire court +
  Redis, invalidé à chaque changement de rattachement). Absente du compte ⇒ **403**
  `ProblemDetails` `MAILBOX_NOT_ATTACHED` ; présente mais **non compatible** avec l'identité PSC
  de la session ⇒ **403** `MAILBOX_PSC_MISMATCH` (règle 12, toujours `problem+json`).
- **Jamais de re-binding silencieux** : un rattachement présenté avec un jeton PSC dont
  `(sub, SubjectNameID)` ≠ `(PscSubject, Rpps)` du compte ⇒ **409** `PSC_IDENTITY_CONFLICT`,
  warning sécurité journalisé. La ré-association (changement de RPPS, rarissime) est un acte
  administratif, hors produit — exactement la règle 3 de task-049.
- **RPPS du nom de base** : `BuildUserDatabaseName(email, rpps)` reçoit désormais `compte.Rpps`
  (annuaire), plus le claim `mssRpps`. Même valeur pour tout compte existant — le nom de base
  ne change pas.
- **Migration à la volée des comptes existants — le seul endroit où les anciens claims sont
  encore lus.** Un jeton portant `mssEmail` + `mssSub` + `mssRpps` **et** dont le compte n'est
  pas encore ancré ⇒ en **une** opération idempotente : compte ancré (`PscSubject ← mssSub`,
  `Rpps ← mssRpps`), boîte `mssEmail` rattachée par défaut avec `ValidatedByPscSubject ← mssSub`.
  Ces valeurs ont été écrites par le backend-auth depuis un jeton PSC vérifié (task-049) : elles
  sont dignes de confiance. Un ancien client sans `Client-Email` utilise alors cette boîte. Aucun
  praticien existant ne perd sa boîte, aucun big-bang, les anciens fronts fonctionnent jusqu'à
  leur mise à jour. Ce code est **isolé dans une classe dédiée** (`LegacyClaimsMigration`),
  marqué `[Obsolete]`, avec un compteur `mss_directory_legacy_claims_migrations_total` : quand il
  reste à zéro 30 jours en production, l'humain retire les mappers, la route proxy, puis cette
  classe.
- **Aucune boîte sélectionnée** (ni en-tête ni claim) : les routes de gestion des boîtes
  (`/account/mailboxes*`, `/account/mss-imap-test`, `/directory/self`) fonctionnent ; toute autre
  route rend **403** `MAILBOX_REQUIRED`. L'exemption par préfixe de chemin actuelle
  (`ExcludedPathPrefixes`) est remplacée par un attribut explicite `[MailboxNotRequired]`.
- `Client-Email` **et** claim présents mais différents : c'est le cas nominal de la bascule —
  **plus un motif de 403**. Le test `RequestHelper` correspondant est réécrit, pas supprimé.

### Contrat HTTP (DTOs dans `dtos-mss`) et contrat SDK

`IDirectoryClient` (SDK, `V1`, évolution **additive**) gagne : `ListCompatibleMailboxesAsync
(accountId, pscIdentity)`, `AttachMailboxAsync`, `DetachMailboxAsync`, `SetDefaultMailboxAsync`,
`AnchorPscIdentityAsync`, `IsMailboxCompatibleAsync(accountId, email, pscIdentity)` — mêmes
contraintes de migrabilité que task-299 (asynchrone, `record`, pas d'EF, pas de transaction
partagée, exceptions typées, cache-first).

| Route | Corps / réponse | Règles |
|---|---|---|
| `GET /api/v1/account/mailboxes` | `MailboxDto[]` : `id`, `email`, `displayName?`, `operatorDomain`, `isDefault`, `state` (`Active` / `AuthFailing` / `Detached`), **`compatibleWithSession: bool`**, **`incompatibilityReason?`** (`Detached` / `AuthFailing` / `PscIdentityMismatch` / `NoPscToken`), `attachedAt`, `lastSuccessfulLoginAt?` | Toutes les boîtes du compte, `Detached` exclues par défaut (`?includeDetached=true`). **La compatibilité est calculée contre le `X-PSC-Token` de la requête** — c'est la liste que le sélecteur affiche |
| `POST /api/v1/account/mailboxes` | `AttachMailboxRequest { email }` → `201 MailboxDto` | **Sonde IMAP avec le jeton PSC de l'appelant puis persiste**. Échec de sonde ⇒ `4xx ProblemDetails` avec les codes existants (`AUTH_FAILED`, `HOST_UNREACHABLE`, `MAILBOX_NOT_FOUND`, `INVALID_EMAIL`), **rien persisté**. Déjà rattachée ⇒ `409`. Identité PSC ≠ compte ancré ⇒ `409 PSC_IDENTITY_CONFLICT`. Première boîte du compte ⇒ `isDefault = true` + ancrage. **Provisionne la base du tenant immédiatement** |
| `DELETE /api/v1/account/mailboxes/{id}` | `204` | Marque `Detached`, conserve la base. Si c'était la boîte par défaut, la plus ancienne active devient défaut. Le compte peut tomber à 0 boîte |
| `PUT /api/v1/account/mailboxes/{id}/default` | `204` | Change la boîte par défaut |
| `POST /api/v1/account/mss-imap-test` | inchangé | Conservé pour la validation « à blanc » depuis le formulaire ; **plus obligatoire** dans le flux |
| `GET /api/v1/mail/events?mailbox={email}` (SSE) | inchangé sinon | Le paramètre remplace la lecture du claim ; validé **compatible**, sinon 403. Absent ⇒ boîte par défaut du compte (compatibilité) |
| `POST /api/v1/sync/logout` | inchangé (task-285) | **Fin de session de boîte** — appelé par le front avec les en-têtes de la session **sortante** avant toute bascule, comme à la déconnexion. Écrit `MailboxSessionClosed` |
| En-tête `Client-Session-Id` | inchangé de forme | **Lié à la première boîte ouverte** (Redis, TTL session) ; réutilisé avec une autre `Client-Email` ⇒ **409** `SESSION_MAILBOX_MISMATCH`. Première requête d'un couple `(email, sessionId)` ⇒ `MailboxSessionOpened` |

### Ce qui ne change pas — et doit être prouvé par test

`BuildUserDatabaseName` (même nom de base pour tout compte existant), clé du pool IMAP,
`Settings` par boîte, en-tête `X-PSC-Token`, chemin bypass de test (il gagne seulement l'upsert
d'annuaire, voir « Banc »). Le cross-check PSC **change de référence, pas de règle** : même
comparaison, même `Enforce`, mêmes évènements de log (3721/3722/3723) — mais lus dans l'annuaire.

## Proxy Keycloak et mappers — ce qui disparaît, et dans quel ordre

Le backend-auth / proxy (`PUT /v1/admin/mss-profile`, task-037 ; écriture de `mssSub` /
`mssRpps`, task-049 ; Protocol Mappers, task-050) est **hors workspace et géré manuellement**.
Cette US **retire toute dépendance du produit à ces trois attributs et à cette route** :

| Élément | Après cette US | Retrait définitif (acte humain) |
|---|---|---|
| Appels fronts à `PUT /v1/admin/mss-profile` | **supprimés** (task-304, trois fronts) | route proxy retirable dès la mise à jour des fronts |
| Claim `mssEmail` | plus lu, sauf par `LegacyClaimsMigration` | mapper retiré quand le compteur de migrations reste à 0 sur 30 j |
| Claims `mssSub`, `mssRpps` | plus lus, sauf par `LegacyClaimsMigration` — la référence du cross-check est `compte.PscSubject` / `compte.Rpps` | mappers + écriture backend-auth (task-049) retirés au même moment |
| Attribut utilisateur Keycloak | inerte | nettoyage du realm, humain |

Le jeton Keycloak cible ne porte que `sub` (et les claims standard). **Le produit ne demande
plus rien à Keycloak à propos de MSSanté.**

## Banc de charge — `tests/loadtest-k6` et `tests/mss.mail.loadtest.seed`

- **`MAILBOXES_PER_USER`** (k6) et **`--mailboxes-per-user`** (seed), **défaut 1** : à défaut, le
  tir est **iso** aux références E015 (mêmes identités `loadtest-{n}@…`, mêmes bases) — la
  non-régression des baselines est un critère du DOD.
- `identity(n)` rend un **compte** (rpps, pscSub — **une seule identité PSC** pour toutes ses
  boîtes, conformément à la règle) et ses boîtes `loadtest-{n}-{k}@{domain}` pour `k ≥ 2` (la
  boîte 1 garde son nom actuel). `headersFor(user, sessionId, mailboxIndex)` pose `Client-Email`
  de la boîte choisie ; les autres en-têtes sont inchangés.
- **`JOURNEY_P_SWITCH`** (défaut **0**) : probabilité qu'un passage du parcours change de boîte
  — ce qui mesure le **coût d'une bascule** (pool IMAP froid de l'autre boîte, base différente).
  Le rapport gagne une ligne « boîtes par compte / part de bascules » et une phase « bascule ».
- **Chemin bypass** : `RequestHelper` lit déjà `Client-Email` / `Client-Rpps` / `Client-Psc-Sub`
  comme identité ; il gagne l'**upsert d'annuaire** (compte ← `Client-Rpps`/`Client-Psc-Sub`,
  boîte ← `Client-Email`, `ValidatedByPscSubject ← Client-Psc-Sub`) pour que la vérification de
  compatibilité passe sans pré-enregistrement. Le seed pré-enregistre néanmoins les rattachements
  (idempotent) pour ne pas mesurer l'upsert dans le premier passage.
- Le seed provisionne `users × mailboxes` boîtes sur Dovecot/GreenMail.

## Definition of Done

### Transverse
- [ ] Build passes on `sdk`, `api-mail` (0 errors) ; tests pass (0 failures)
- [ ] `sdk` : extension additive de `IDirectoryClient` (opérations ci-dessus), DTOs `record`,
      aucune dépendance Npgsql/EF ; NuGet publié, `api-mail` et `client-blazor` bumpés à la même
      version. Le middleware, les contrôleurs et le SSE ne parlent à l'annuaire **que** via
      `IDirectoryClient` (le test d'architecture de task-299 reste vert)
- [ ] `dtos-mss` : `MailboxDto` (avec `compatibleWithSession`, `incompatibilityReason`),
      `AttachMailboxRequest`, codes `MAILBOX_NOT_ATTACHED` / `MAILBOX_REQUIRED` /
      `MAILBOX_PSC_MISMATCH` / `PSC_IDENTITY_CONFLICT` / `SESSION_MAILBOX_MISMATCH`,
      `AuditActionType` + 5 membres (`MailboxAttached`, `MailboxDetached`,
      `MailboxDefaultChanged`, `MailboxSessionOpened`, `MailboxSessionClosed`) — NuGet publié,
      consommateurs .NET bumpés. Le miroir TS de `AuditActionType` est livré par task-304

### `api-mail` — compatibilité PSC (la règle demandée)
- [ ] **Test d'acceptation** : jeton Keycloak portant **uniquement** `sub` (aucun claim MSS) +
      `X-PSC-Token` d'une identité ⇒ rattachement de deux boîtes (sonde OK), `GET
      /account/mailboxes` rend **les deux compatibles**, bascule (`Client-Email` de l'une puis de
      l'autre) ⇒ 200 sur les deux, **sans** changement de jeton. Aucune lecture de `mssEmail` /
      `mssSub` / `mssRpps` en dehors de `LegacyClaimsMigration` (test par grep sur `src/`)
- [ ] Test : « même jeton PSC » = même **identité** — deux `X-PSC-Token` **différents** portant le
      même `(sub, SubjectNameID)` (rotation simulée) rendent la **même** liste compatible et
      ouvrent la **même** boîte ; un jeton d'une autre identité rend `PscIdentityMismatch` sur
      toutes les boîtes et 403 `MAILBOX_PSC_MISMATCH` à la sélection
- [ ] Test : sans `X-PSC-Token` ⇒ liste rendue avec `NoPscToken`, sélection acceptée en lecture
      locale, **aucune** ouverture IMAP tentée
- [ ] Test : boîte `AuthFailing` ⇒ `compatibleWithSession = false`, raison `AuthFailing`, sélection
      refusée 403 ; remise `Active` au premier succès XOAUTH2 ⇒ compatible à nouveau
- [ ] Test : ancrage `PscSubject` / `Rpps` / `ValidatedByPscSubject` **uniquement** au premier
      rattachement réussi — un passage de requête n'ancre rien ; une sonde échouée n'ancre rien
- [ ] Test : rattachement avec un jeton PSC d'un **autre** PS que celui ancré ⇒ **409**
      `PSC_IDENTITY_CONFLICT`, rien persisté, warning sécurité (règle 3 de task-049)

### `api-mail` — bascule = fin de session + nouvelle session
- [ ] Test d'intégration : `POST /sync/logout` avec `(boîte1, S1)` puis première requête avec
      `(boîte2, S2)` ⇒ le registre de sessions ne contient **plus** `boîte1_S1`, contient
      `boîte2_S2`, la synchro de fond de boîte1 est arrêtée (si dernière session) et celle de boîte2
      démarrée ; le pool IMAP de boîte1 est **fermé** (compteur de sessions du
      `IMailClientSessionManager`), pas seulement orphelin
- [ ] Test : diffusion inter-pods conservée — l'ordre de clôture émis sur un pod est reçu par un
      second (suite task-285 verte, étendue au cas « bascule »)
- [ ] Test : garde `Client-Session-Id` — `S1` vu avec `boîte1` puis présenté avec `boîte2` ⇒ 409
      `SESSION_MAILBOX_MISMATCH` en `problem+json`, aucune ouverture IMAP ; `S1` avec `boîte1`
      depuis un second onglet ⇒ 200 ; après `/sync/logout` de `(boîte1, S1)`, `S1` avec `boîte2`
      ⇒ **toujours** 409 (un identifiant ne se recycle pas — le front doit en tirer un neuf)
- [ ] Test : `MailboxSessionOpened` écrit une fois par couple `(email, sessionId)` (pas à chaque
      requête) ; `MailboxSessionClosed` écrit sur `/sync/logout` et sur expiration serveur avec la
      raison ; une bascule ⇒ exactement un `Closed` (boîte1) + un `Opened` (boîte2)
- [ ] Test : la bascule ne touche ni au bearer ni au `X-PSC-Token` — aucun appel sortant vers
      Keycloak / PSC, mêmes valeurs acceptées avant/après
- [ ] Test : SSE — le flux de `boîte1` est clos côté serveur à `/sync/logout` ; un flux
      `?mailbox=boîte2` s'ouvre avec `S2`

### `api-mail` — reste du contrat
- [ ] Test middleware : `Client-Email ∈ compatibles` ⇒ passe ; `∉ compte` ⇒ 403
      `MAILBOX_NOT_ATTACHED` ; claim et en-tête **différents mais tous deux compatibles** ⇒ passe
      (le test « mismatch ⇒ 403 » actuel est **réécrit**, pas supprimé)
- [ ] Test middleware : ni en-tête ni claim ⇒ routes `[MailboxNotRequired]` passent, les autres
      403 `MAILBOX_REQUIRED`
- [ ] Test : résolution du compte par `sub` Keycloak **effective** (test qui échoue si
      `FindFirstValue("sub")` rend null — le piège `MapInboundClaims`)
- [ ] Test unitaire : `POST /account/mailboxes` — sonde échouée ⇒ **rien persisté**, code
      d'erreur exact ; sonde réussie ⇒ rattachement `Active`, première boîte `isDefault`,
      provisionnement de la base déclenché ; doublon ⇒ 409
- [ ] Test unitaire : `DELETE` ⇒ `Detached` + date, base **non** supprimée, transfert du défaut ;
      `PUT default` ⇒ un seul défaut par compte
- [ ] Test d'intégration (1 par endpoint, happy path + 1 échec) : `GET/POST/DELETE
      /account/mailboxes`, `PUT …/default`, SSE `?mailbox=` (compatible ⇒ flux ouvert ; non ⇒ 403)
- [ ] Test `LegacyClaimsMigration` : jeton hérité `mssEmail` + `mssSub` + `mssRpps`, compte non
      ancré ⇒ compte ancré + boîte rattachée par défaut (`ValidatedByPscSubject = mssSub`), **une
      seule fois** (idempotent), compteur incrémenté ; compte **déjà ancré** avec des claims
      différents ⇒ **aucune** écriture, warning
- [ ] Test : `BuildUserDatabaseName` reçoit `compte.Rpps` et rend le **même** nom que depuis
      `mssRpps` pour tout compte migré (fixture : 3 identités du banc, avant / après)
- [ ] Test : `MailboxAttached` / `MailboxDetached` / `MailboxDefaultChanged` écrits dans le
      journal d'audit ; une bascule n'écrit **que** `MailboxSessionClosed` + `MailboxSessionOpened`
- [ ] Test de non-régression : la suite task-048 est **réécrite sur la référence annuaire** (mêmes
      cas, mêmes verdicts, mêmes EventIds) ; clé du pool IMAP inchangée
- [ ] Cache de compatibilité invalidé sur attach / detach / changement d'état (test : detach puis
      requête ⇒ 403 sans attendre le TTL)
- [ ] Aucune donnée de santé ni jeton dans les nouveaux logs (adresses MSSanté anonymisées comme
      aujourd'hui : `AnonymiseEmail`)

### Banc
- [ ] `MAILBOXES_PER_USER=1` / `--mailboxes-per-user 1` : identités, en-têtes et bases
      **identiques bit à bit** à aujourd'hui (test k6 `selftest.sh` + test seed) — non-régression
      des références E015
- [ ] `MAILBOXES_PER_USER=3`, `JOURNEY_P_SWITCH=0.1` : le tir tourne, `report.py` affiche
      « boîtes par compte » et la phase « bascule » (fixture + test `test_report_*.py`)
- [ ] Chemin bypass : upsert d'annuaire couvert par test ; seed pré-enregistre les rattachements
      (idempotent)

## Manual Test Plan

> Le test humain de la US **assemblée** (sélecteur, bascule, écrans) est dans **task-304**. Ce
> plan ne vérifie que le contrat backend, par `curl` / Scalar, et le banc.

- **Pré-requis** : un PS de test disposant de **deux boîtes MSSanté** ouvertes à son RPPS chez
  l'opérateur de test (idéalement chez **deux** opérateurs — c'est l'argument de l'US). À défaut,
  le banc : `--users 2 --mailboxes-per-user 2` sur Dovecot, en-têtes bypass.
- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost` ; `http://127.0.0.1:5052/scalar`.
- **Vérifications** (bearer Keycloak **sans** claim MSS + `X-PSC-Token` du PS) :
  1. `GET /account/mailboxes` → `[]`. `POST /account/mailboxes {email: boîte1}` → 201,
     `isDefault`, `compatibleWithSession: true`. En annuaire : compte ancré (`PscSubject`, `Rpps`),
     rattachement `ValidatedByPscSubject` = `sub` du jeton PSC.
  2. `POST` boîte2 → 201. `GET` → deux boîtes, **toutes deux compatibles**.
  3. `GET /mail/folders` avec `Client-Email: boîte1`, `Client-Session-Id: S1` → 200. **Bascule** :
     `POST /sync/logout` (mêmes en-têtes) → 200 ; puis `GET /mail/folders` avec `boîte2`, **`S2`**
     → 200, contenus différents, **même** `X-PSC-Token`. Dans Seq : fermeture de `boîte1_S1`
     diffusée, ouverture de `boîte2_S2` ; `pg_stat_activity` : deux bases `u_…` distinctes.
     Contre-épreuve : `GET /mail/folders` avec `boîte2` mais **`S1`** → **409**
     `SESSION_MAILBOX_MISMATCH`.
  4. Rejouer 3 avec un `X-PSC-Token` **rafraîchi** (autre chaîne, même identité) → identique.
  5. `X-PSC-Token` d'un **autre** PS de test → `GET /account/mailboxes` : les deux boîtes
     `compatibleWithSession: false`, `PscIdentityMismatch` ; `Client-Email: boîte1` → 403
     `MAILBOX_PSC_MISMATCH` ; `POST` d'une boîte avec ce jeton → 409 `PSC_IDENTITY_CONFLICT`.
  6. Sans `X-PSC-Token` → liste avec `NoPscToken`, `GET /mail/folders` → 200 depuis la base, aucun
     login IMAP dans les logs.
  7. `DELETE` boîte2 → 204 ; `GET` → boîte1 seule ; la base de boîte2 **existe toujours**.
  8. Écran d'audit (par `GET /audit/traces`) : `MailboxAttached` ×2, `MailboxDetached` ×1 ;
     pour la bascule de l'étape 3 : `MailboxSessionClosed` (boîte1, S1) puis `MailboxSessionOpened`
     (boîte2, S2) — rien d'autre.
  9. Jeton hérité (trois claims) → premier appel : compte ancré + boîte rattachée, compteur de
     migration = 1, puis stable.
- **Banc** : tir court `USERS=20 MAILBOXES_PER_USER=3 JOURNEY_P_SWITCH=0.2` → rapport avec la
  phase « bascule » ; puis `MAILBOXES_PER_USER=1` → rapport **identique en forme** à la
  référence E015.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — ergonomie et exploitabilité de la messagerie ; aucune exigence DSR
  nouvelle. L'US **respecte** le modèle MSSanté de rattachement PS ↔ boîte : c'est l'opérateur
  qui décide, le produit ne fait que refléter
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient manipulée par l'US. Les dossiers patients
  restent **par boîte** (par base) ; l'US ne les rapproche pas entre boîtes (hors périmètre,
  décision produit séparée)
- **Authentification PS** : inchangée — Pro Santé Connect via le proxy / Keycloak, eIDAS
  substantiel ; jeton PSC présenté en XOAUTH2 à chaque opérateur. **Aucune** boîte n'est ouverte
  avec un autre moyen que le jeton PSC du PS authentifié, et **aucune bascule n'est possible
  hors de l'identité PSC de la session** — c'est la règle centrale de l'US
- **Habilitations** : le rattachement d'une boîte est **délégué à l'opérateur MSSanté** (sonde
  XOAUTH2 obligatoire, côté serveur, avec le jeton de l'appelant). Le produit n'accorde rien de
  lui-même. **Lien compte ↔ PS** : l'identité PSC (`sub`, RPPS) est ancrée sur le compte au
  premier rattachement réussi et vérifiée à chaque requête en ligne ; jamais de ré-association
  silencieuse (409)
- **Interop CI-SIS** : non applicable
- **MSSanté** : types d'adresses concernés — personnelle PS et organisationnelle ; un compte peut
  rattacher les deux, chez un ou plusieurs opérateurs. L'`AutoconfigService` existant résout
  l'opérateur par domaine, par boîte
- **Tracé PGSSI-S** : `MailboxAttached`, `MailboxDetached`, `MailboxDefaultChanged` (configuration
  d'accès) et `MailboxSessionOpened` / `MailboxSessionClosed` (frontières de session — la
  bascule est tracée comme une clôture puis une ouverture), famille technique, rétention 365 j ;
  les accès aux données restent tracés par boîte comme aujourd'hui (3 653 j). Le détachement ne
  supprime aucune trace
- **Consentement patient** : non applicable
- **Sécurité / confidentialité** : remplacement d'un claim signé par une appartenance serveur —
  compensé par la sonde serveur atomique, l'isolation structurelle `f(email, rpps)`, la
  compatibilité PSC vérifiée à chaque requête, la re-validation continue et le cache invalidé à
  l'écriture. Jetons jamais journalisés ; adresses anonymisées dans les logs
- **Référentiels métier** : RPPS ; adresses MSSanté
- **Hébergement HDS** : oui — inchangé ; l'annuaire (task-299) porte des données de PS, pas de
  patients
- **AIPD / impact RGPD** : **à mettre à jour** dans la continuité de task-299 — le compte peut
  désormais référencer plusieurs boîtes ; finalité inchangée ; les événements de rattachement /
  détachement sont journalisés ; le détachement n'entraîne aucune suppression immédiate
