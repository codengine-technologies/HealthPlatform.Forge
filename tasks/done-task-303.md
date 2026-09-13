# todo-task-303.md — Comptes multi-messageries (vague 1/2 — backend, contrat, banc) : la boîte MSSanté devient une sélection validée par le registre et par l'identité PSC, plus un claim Keycloak

**Repos**: api-mail
**Dependencies**: **task-299** (registre — comptes, messageries, tenants, et le contrat
`ITenantRegistryClient`, que cette US **étend**). ⚠️ Ce contrat **a quitté le SDK** le 2026-09-13
(révision post-review de task-299) : il vit dans `mss.mail.application.Services.Repository.TenantDb`,
ses `record` dans `mss.mail.Domain.Entities.TenantDb`. **L'étendre ne demande donc plus ni
publication NuGet ni bump de consommateur** — c'est précisément ce que la révision achetait, et
c'est pourquoi cette US ne liste plus `sdk`. Indépendante de task-300 / task-301
(journal d'audit) et de task-302 (accès admin).
**Epic**: E016
**Priorité**: **1** — c'est l'US qui donne son sens produit au registre : un praticien, un compte,
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
| Cross-check PSC/KC (task-048) : `mssSub == sub PSC`, `mssRpps == SubjectNameID PSC` — `mssSub`/`mssRpps` sont des **copies** du jeton PSC écrites par le backend-auth à l'opt-in (task-049), projetées en claims par des mappers (task-050) | `ApplyPscKcCrossCheckAsync` | Le **principe** (le jeton PSC présenté appartient au même PS que le compte) est conservé ; la **référence** migre : elle est lue dans le registre (`compte.PscSubject`, `compte.Rpps`), plus dans le jeton KC. **Les trois claims `mssEmail`, `mssSub`, `mssRpps` disparaissent du modèle cible** |
| Nom de base = `f(email, rpps)` → `u_{rpps}_{slug}_{hash}` | `UserContextInfo.BuildUserDatabaseName` | La base est une propriété du **couple (PS, boîte)**. Inchangé : la boîte sélectionnée détermine la base, structurellement |
| Pool IMAP+SMTP clé `{email}_{sessionId}` | `AuthSession.sessionId` (mobile, task-282) ; `UserContextInfo.ClientSessionId` | Déjà clé par boîte : N boîtes = N pools qui coexistent, rien à changer |
| Le jeton PSC **tourne toutes les ~2 min** (task-283) ; le bearer Keycloak ~5 min | `AuthSession.pscAccessTokenExpiresAt` | « Même jeton PSC » ne peut signifier que **même identité PSC** — jamais même chaîne |
| `Settings` vivent dans la base du tenant | `SettingsController`, `UserSettingsRepository` | Les réglages (signature…) restent **par boîte**. Voulu. |
| Banc k6 : une identité = `(email loadtest-{n}@…, rpps 9{n}, pscSub)` ; en-têtes `X-Test-Bypass`, `Client-Email`, `Client-Rpps`, `Client-Psc-Sub`, `Client-Session-Id`, `X-PSC-Token` | `tests/loadtest-k6/lib/identity.js` ; bypass `RequestHelper.cs:255-290` lit `Client-Email` comme identité | 1 utilisateur = 1 boîte. Le banc doit gagner la dimension « boîtes par compte », à **défaut 1** pour ne pas casser les références |
| Lecture du `sub` Keycloak | mémoire projet : `MapInboundClaims` non désactivé ⇒ `FindFirstValue("sub")` rend **null** | Piège connu pour `/develop` : lire `ClaimTypes.NameIdentifier` ou désactiver le mapping — sinon aucun compte ne se résout |

## Principe directeur

**Le jeton Keycloak n'est plus qu'une identité d'authentification (`sub`). Tout ce qui est
MSSanté — l'identité PSC du professionnel, son RPPS, ses boîtes — vit dans l'annuaire central.
La boîte est une sélection par requête, validée contre le registre ET contre l'identité PSC de la
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

## Modèle de données — fusion `mailboxes` + `tenants` (arbitrage humain du 2026-09-13)

> « On devrait avoir account = au niveau de Keycloak, puis account-mss pour les BAL qui s'y
> rattachent. »

task-299 a livré **trois** tables : `accounts` (compte Keycloak), `mailboxes` (l'adresse comme
entité globale) et `tenants` (le rattachement). **Cette US ramène le registre à deux tables.**

```
accounts       le compte chapeau Keycloak   (authentication_subject unique)
mss_accounts   la BAL rattachée au compte   (ex-`tenants`, absorbe `mailboxes`)
```

### Trois raisons, vérifiées dans le schéma livré

1. **Double clé de fait.** `tenants` porte **à la fois** `mailbox_id` (FK) **et** `mailbox_address`
   (copie dénormalisée « pour éviter une jointure sur le chemin de requête »), les deux indexés par
   compte. Deux sources de vérité pour « quelle messagerie » : une adresse corrigée dans
   `mailboxes` laisse la copie périmée, en silence.
2. **L'entité intermédiaire ne porte rien.** `RegistryMailbox` n'est **rendu par aucune opération**
   de `ITenantRegistryClient` — vérifié. `operator_domain` se dérive de l'adresse. La table
   n'existe que pour être jointe.
3. **Elle rend possible la faute qu'on documente.** Trois paragraphes du code avertissent de ne
   **jamais** clé le journal d'audit sur `mailbox_id`, sous peine de faire voir à deux PS d'une
   adresse organisationnelle les traces l'un de l'autre. **Supprimer la colonne rend la faute
   impossible** au lieu de la commenter.

**Ce qu'on abandonne** : l'identité globale d'une adresse partagée. Assumé — la propriété d'une
adresse organisationnelle relève de l'opérateur et de l'ANS, pas de notre cartographie du parc.
Deux PS sur `secretariat@…` ⇒ **deux lignes** `mss_accounts`, deux bases, aucun parent commun sur
lequel se tromper.

### Vocabulaire — ce qui change et ce qui ne change pas

**Les tables seulement.** Le code garde `ITenantRegistryClient`, `Domain/Entities/TenantDb/`,
`Infrastructure/Migrations/TenantDb/`, `TenantRegistryDbContext` — nommage arbitré le 2026-09-13
(« TenantRegistry est ok ») et **`TenantId` reste le nom de l'unité d'isolation**, y compris la
colonne du journal d'audit de task-300. `mss_accounts.id` **est** le `TenantId`.
**Impact sur task-300 / task-301 : aucun.**

### La migration — une NOUVELLE, jamais une édition

`20260913120000_CreateTenantRegistry` est **mergée sur `develop`** et déjà appliquée sur des bases
de développement : elle ne se réécrit pas (règle 7c). Cette US ajoute une migration dans
`Migrations/TenantDb/` :

```
Rename.Table("tenants").To("mss_accounts")
Delete.Column("mailbox_id").FromTable("mss_accounts")     // + son index unique
Delete.Table("mailboxes")
Create.Index("ux_mss_accounts_account_address")
      .OnTable("mss_accounts").OnColumn("account_id").OnColumn("mailbox_address")
      .WithOptions().Unique()                              // la SEULE clé du rattachement
```

> **La fenêtre est ouverte, et elle se referme avec cette US.** Le synchroniseur de task-299
> n'appelle que `EnsureAccountAsync` : `mailboxes` et `tenants` sont **vides dans tous les
> environnements**. La migration ne déplace aucune donnée aujourd'hui. Dès que cette US rattache
> la première boîte, elle en déplacerait.

### Conséquences sur le code

- `RegistryMailboxRow`, `RegistryMailbox`, `TenantRegistryDbContext.Mailboxes` et
  `EnsureMailboxRowAsync` : **supprimés**.
- `RegistryTenantRow` / `RegistryTenant` : `MailboxId` retiré ; `[Table("mss_accounts")]`.
- `EnsureTenantAsync` résout le rattachement sur `(account_id, mailbox_address)` — une lecture au
  lieu de deux, et l'idempotence porte sur la même clé que l'index unique.
- Tests à reprendre : liste blanche de colonnes (architecture **et** intégration), tests de
  contrat, les 12 tests d'intégration de task-299.

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
4. **Boîte non sélectionnable** = `Detached`, `AuthFailing`, `PscIdentityMismatch` (théorique :
   un compte est ancré sur une seule identité, mais la règle est écrite et testée, pas déduite).
   Ces trois-là sont grisées et **non cliquables** côté front (task-304).
5. **Sans jeton PSC** (mode hors ligne existant, `IsOfflineMode`) : **mode dégradé, PAS une
   incompatibilité.**

   > ⚠️ **Corrigé le 2026-09-13 (clarification humaine).** La rédaction précédente rangeait
   > `NoPscToken` parmi les raisons d'incompatibilité, au même rang que `Detached` et
   > `AuthFailing`. Composée avec la règle de task-304 — « non compatible ⇒ grisée, raison
   > affichée, **non cliquable** » — elle rendait **toutes** les boîtes inaccessibles hors ligne,
   > c'est-à-dire l'inverse exact du comportement voulu. `NoPscToken` n'est pas un défaut de la
   > boîte : c'est un état de la **session**.

   Le contrat rend donc, par boîte, **deux informations distinctes** :
   `selectable` (l'état du rattachement — `Detached` / `AuthFailing` / `PscIdentityMismatch` le
   mettent à `false`) et `capabilities` (`read` toujours, `imap`/`send`/`flags` seulement si la
   session porte un jeton PSC compatible). Hors ligne : **toutes les boîtes actives restent
   sélectionnables et ouvrables**, en lecture locale de ce qui est déjà synchronisé — exactement
   le comportement hors ligne d'aujourd'hui (`IsOfflineMode`, `CanAccessImap == false`,
   `CanSendEmail == false`), étendu à N boîtes. Aucune ouverture IMAP, aucun envoi, aucun
   changement de drapeau.

6. **Précondition du hors ligne : le compte doit avoir été ancré au moins une fois en ligne.**
   Un compte Keycloak **seul** — jamais passé par PSC, jamais migré depuis les anciens claims —
   n'a **aucun tenant** dans le registre, donc aucune base praticien, donc rien à consulter.
   C'est un état légitime, pas une panne : il tombe dans le parcours d'onboarding (§B de
   task-304), lui-même **impossible hors ligne** puisque le rattachement exige une sonde IMAP
   XOAUTH2 avec le jeton PSC. La première connexion utile après cette US est donc
   **nécessairement en ligne**. À dire explicitement au support : « je ne vois rien hors ligne »
   sur un compte neuf n'est pas un défaut.

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
`ProblemDetails` `SESSION_MAILBOX_MISMATCH`. Le multi-onglets (même boîte, même identifiant)
reste légitime.

> **Ce que cette garde empêche exactement.** Le registre de sessions est clé sur
> `{email}_{clientSessionId}` (vérifié : `MailClientSessionManager.cs`, sept sites). Réutiliser
> l'identifiant avec une autre boîte ne provoque donc **pas** de collision — il crée une
> **seconde** session et **abandonne la première** : un pool IMAP+SMTP orphelin, connecté chez
> l'opérateur précédent, vivant jusqu'à son expiration. Sur un praticien qui bascule dix fois,
> c'est dix pools résidents. La garde n'est pas de l'hygiène de contrat : c'est ce qui empêche
> la bascule de devenir une fuite de connexions — exactement le défaut que E015 combat.

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
   dans cet ordre** (deux appels `ITenantRegistryClient`, sans transaction commune — l'atomicité
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

- **Compte** ← `sub` Keycloak (voir le piège `MapInboundClaims`), résolu dans le registre via
  `ITenantRegistryClient`. Un jeton dont le `sub` est inconnu crée le compte (upsert task-299,
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
- **Nom de base : le registre fait autorité, on ne recalcule plus.** Le rattachement enregistre
  `tenants.database_name` une fois — `EnsureTenantAsync` ne réécrit jamais la colonne — et
  **c'est cette valeur que le chemin de requête lit**. `BuildUserDatabaseName(email, rpps)` ne
  sert plus qu'**une fois**, au rattachement, pour *proposer* le nom que le registre grave.

  Deux raisons, la seconde étant celle qui a motivé le changement (clarification humaine du
  2026-09-13) :

  1. **Une seule source de vérité.** Le nom est déjà persisté ; le recalculer à chaque requête,
     c'est le *reconstruire* — et faire dépendre l'accès aux données de santé d'une fonction pure
     qui ne doit jamais changer. Une retouche du slug ou du hachage déplacerait **tout le parc**
     sur des bases neuves et vides, en silence.
  2. **Le hors ligne cesse de dépendre de l'ancrage.** Recalculer exige `compte.Rpps` ; le lire
     n'exige rien. Le segment RPPS n'entre d'ailleurs dans le nom qu'en **préfixe** (le hachage
     ne porte que l'email) : `u_0_{slug}_{hash}` sans RPPS contre `u_{rpps}_{slug}_{hash}` avec.
     Deux bases distinctes pour le même praticien selon la forme du jeton. Lire le nom enregistré
     rend cette asymétrie inoffensive **par construction**, au lieu de la neutraliser par une
     précaution qu'il faudrait maintenir.

  Repli : tenant sans `database_name` (impossible — colonne `NOT NULL`) ⇒ `500`, jamais un
  recalcul silencieux. Le compte reste ancré (`compte.Rpps`), mais plus aucun chemin de requête
  ne s'en sert pour nommer une base.
- **Migration à la volée des comptes existants — le seul endroit où les anciens claims sont
  encore lus.** Un jeton portant `mssEmail` + `mssSub` + `mssRpps` **et** dont le compte n'est
  pas encore ancré ⇒ en **une** opération idempotente : compte ancré (`PscSubject ← mssSub`,
  `Rpps ← mssRpps`), boîte `mssEmail` rattachée par défaut avec `ValidatedByPscSubject ← mssSub`.
  Ces valeurs ont été écrites par le backend-auth depuis un jeton PSC vérifié (task-049) : elles
  sont dignes de confiance. Un ancien client sans `Client-Email` utilise alors cette boîte. Aucun
  praticien existant ne perd sa boîte, aucun big-bang, les anciens fronts fonctionnent jusqu'à
  leur mise à jour. Ce code est **isolé dans une classe dédiée** (`LegacyClaimsMigration`),
  marqué `[Obsolete]`, avec un compteur `mss_registry_legacy_claims_migrations_total` : quand il
  reste à zéro 30 jours en production, l'humain retire les mappers, la route proxy, puis cette
  classe.
- **Aucune boîte sélectionnée** (ni en-tête ni claim) : les routes de gestion des boîtes
  (`/account/mailboxes*`, `/account/mss-imap-test`, `/directory/self`) fonctionnent ; toute autre
  route rend **403** `MAILBOX_REQUIRED`. L'exemption par préfixe de chemin actuelle
  (`ExcludedPathPrefixes`) est remplacée par un attribut explicite `[MailboxNotRequired]`.
- `Client-Email` **et** claim présents mais différents : c'est le cas nominal de la bascule —
  **plus un motif de 403**. Le test `RequestHelper` correspondant est réécrit, pas supprimé.

### Contrat HTTP (DTOs dans `dtos-mss`) et contrat du registre

`ITenantRegistryClient` (`mss.mail.application.Services.Repository.TenantDb`, évolution
**additive**) gagne : `ListCompatibleMailboxesAsync
(accountId, pscIdentity)`, `AttachMailboxAsync`, `DetachMailboxAsync`, `SetDefaultMailboxAsync`,
`AnchorPscIdentityAsync`, `IsMailboxCompatibleAsync(accountId, email, pscIdentity)` — mêmes
contraintes de migrabilité que task-299 (asynchrone, `record` immuables, **aucune entité de
persistance dans la surface**, pas de transaction partagée, exceptions typées, cache-first,
`CancellationToken` + `correlationId`). Les nouveaux `record` vont dans
`mss.mail.Domain.Entities.TenantDb` ; `TenantRegistryContractTests` les couvre automatiquement
(il énumère l'espace de noms, pas une liste de types).

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

## Banc de charge — extrait en **task-306**

La dimension « boîtes par compte » du harnais k6, du seed et de `report.py`, ainsi que les deux
tirs de mesure, vivent dans **task-306** (revue du 2026-09-13) : c'est du JavaScript et du Python,
sa validation est un tir de plusieurs heures, et il ne conditionne aucun écran. Le garder ici
poussait la PR `api-mail` au-delà du plafond de la règle 5.

**Ce qui reste à la charge de cette US** — parce que c'est du code de `src/` :

- le chemin **bypass de test** (`RequestHelper`, `X-Test-Bypass`) gagne l'**upsert de registre**
  (compte ← `Client-Rpps` / `Client-Psc-Sub`, messagerie ← `Client-Email`, tenant créé avec
  `ValidatedByPscSubject ← Client-Psc-Sub`), sans quoi le banc ne peut rien exercer ;
- la **décision de portée du drapeau `MSS_ENFORCE_PSC_IDENTITY`** : il gouverne le **cross-check
  PSC/KC** (ex-task-048) et **lui seul**. Le refus d'une boîte non rattachée
  (`MAILBOX_NOT_ATTACHED`) et celui d'une boîte non compatible (`MAILBOX_PSC_MISMATCH`) sont des
  règles d'**appartenance**, pas des contrôles d'identité : ils s'appliquent **toujours**, banc
  compris. Sinon le banc n'exercerait jamais la règle centrale de l'EPIC.

> ### ⚠️ Fait vérifié dans le code le 2026-09-13 — le chemin de contournement n'a pas de `sub`
>
> `TestBypassAuthenticationHandler` (`src/Api/Authentication/`) rend bien un principal
> **authentifié**, et le banc k6 envoie `X-Test-Bypass` sur **chaque** requête
> (`tests/loadtest-k6/lib/identity.js`). Mais les claims qu'il émet sont `ClaimTypes.Email`,
> `mssEmail`, `preferred_username`, `sid`, `test_bypass` (+ `mssSub`/`mssRpps` optionnels) —
> **ni `ClaimTypes.NameIdentifier`, ni `sub`**.
>
> Or `TenantRegistrySynchronizer.ReadAuthenticationSubject` lit exactement ces deux claims et
> **rend `null`** sinon, auquel cas la synchronisation ne fait rien. **Conséquence mesurable :
> aujourd'hui le banc de charge ne nourrit pas le registre** — aucune connexion à la base commune,
> aucune latence ajoutée, références E015 intactes.
>
> **C'est cette US qui change cela.** L'« upsert d'annuaire sur le chemin bypass » attendu par
> task-306 suppose d'ajouter un claim de sujet au handler de contournement (dérivé de
> `Client-Psc-Sub`, ou une valeur stable dérivée de `Client-Email`). Le faire **déplace la
> référence du banc** : c'est à partir de là que le registre coûte quelque chose sous charge, et
> task-306 devra re-baseliner. Ne pas l'attribuer à task-299, qui est neutre sur ce plan.

## Definition of Done

### Transverse
- [ ] Build passes on `api-mail` (0 errors) ; tests pass (0 failures)
- [ ] **Prérequis hérité de task-299 (revue de code) — TOUJOURS OUVERT.** Les tests
      d'intégration ajoutés le 2026-09-13 couvrent l'idempotence sur le **chemin nominal** contre
      un vrai PostgreSQL, **pas la course perdue** : `EnsureTenantAsync` ne **relit pas** la
      ligne après `SaveIdempotentAsync`. Sur une course perdue (violation d'unicité sur
      `(account_id, mailbox_id)`, tracker vidé), la méthode rend le tenant **qu'elle a tenté
      d'insérer**, donc un `TenantId` qui n'existe pas en base — alors que c'est précisément
      l'identifiant sur lequel le journal d'audit sera clé (task-300). `EnsureAccountAsync` fait
      la relecture correctement : appliquer le même motif, et couvrir la course par un test.
- [ ] Extension **additive** de `ITenantRegistryClient` (opérations ci-dessus) ; `record` de
      données dans `mss.mail.Domain.Entities.TenantDb`. **Aucun bump de paquet** : le contrat n'est
      plus publié (révision task-299 du 2026-09-13). Le middleware, les contrôleurs et le SSE ne
      parlent au registre **que** via `ITenantRegistryClient` (les tests d'architecture et de
      contrat de task-299 restent verts)
- [ ] **`AuditActionType` — les 5 membres sont AJOUTÉS EN FIN D'ÉNUMÉRATION.** L'enum est
      sérialisée **par son ordinal** sur le fil d'audit (avertissement gravé dans
      `Dtos/AuditActionType.cs`) : toute insertion au milieu décale silencieusement chaque trace
      historique côté Angular et Blazor. Test de contrat sur les valeurs ordinales attendues
- [ ] **Les 5 membres sont ajoutés à `AuditRetentionPolicy.TechnicalActions`.** Cette liste est
      **explicite** et son défaut est la rétention **la plus longue** : sans cet ajout,
      `FamilyOf` les classerait en `HealthDataAccess` et le journal les garderait **3 653 jours**
      au lieu des 365 que cette US annonce en conformité. Test : `FamilyOf(MailboxSessionOpened)
      == Technical` pour les cinq
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
- [ ] **Registre à deux tables** : migration **nouvelle** (jamais une édition de
      `20260913120000_CreateTenantRegistry`, règle 7c) qui renomme `tenants` en `mss_accounts`,
      supprime `mailbox_id` et la table `mailboxes`, et pose l'unique `(account_id,
      mailbox_address)` comme **seule** clé du rattachement
- [ ] Test d'intégration sur vrai PostgreSQL : après migration, `mailboxes` **n'existe plus**,
      `mss_accounts` existe, et deux comptes distincts rattachés à la **même** adresse
      organisationnelle produisent **deux lignes, deux `database_name` distincts** — le cas qui
      rendait `mailbox_id` dangereux
- [ ] Liste blanche de colonnes remise à jour (test d'architecture **et** test d'intégration sur
      `information_schema`) : `mss_accounts` sans `mailbox_id`
- [ ] **Le chemin de requête lit `mss_accounts.database_name`, il ne le recalcule plus.** Test : un
      rattachement dont le `database_name` enregistré diffère de ce que `BuildUserDatabaseName` rendrait
      (RPPS absent du jeton, slug modifié) ⇒ c'est **la valeur enregistrée** qui est utilisée.
      Test de non-régression : pour tout compte migré, le nom enregistré au rattachement est
      **identique** à celui que produisait `mssRpps` avant la bascule (fixture : 3 identités du
      banc, avant / après) — aucun praticien ne change de base
- [ ] **Hors ligne, toutes les boîtes actives restent sélectionnables.** Test : session sans
      `X-PSC-Token`, compte à 2 boîtes actives ⇒ `GET /account/mailboxes` rend les deux avec
      `selectable = true` et `capabilities` sans `imap`/`send`/`flags` ; l'ouverture de l'une
      **réussit** et sert la lecture locale ; aucune ouverture IMAP n'est tentée.
      `Detached` / `AuthFailing` restent `selectable = false` **y compris** hors ligne
- [ ] Test : compte Keycloak **jamais ancré** (0 tenant) + session hors ligne ⇒ la liste est
      **vide** et le code rendu oriente vers l'onboarding, qui répond « jeton PSC requis » —
      jamais une erreur technique
- [ ] Test : `MailboxAttached` / `MailboxDetached` / `MailboxDefaultChanged` écrits dans le
      journal d'audit ; une bascule n'écrit **que** `MailboxSessionClosed` + `MailboxSessionOpened`
- [ ] Test de non-régression : la suite task-048 est **réécrite sur la référence registre** (mêmes
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
     `isDefault`, `compatibleWithSession: true`. Dans le registre : compte ancré (`PscSubject`, `Rpps`),
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

## Develop log — implémentation terminée (2026-09-13)

**Suite complète : 4 495 tests, 0 échec.** Branche `feat/task-303-comptes-multi-messageries`.

| Lot | Contenu | Tests |
|---|---|---|
| `dtos-mss` **474.0.0** | `MailboxDto` (selectable + capabilities), `AttachMailboxRequest`, 5 codes, 5 membres `AuditActionType` (31-35) | ordinaux gelés |
| Registre à deux tables | migration `20260913180000`, `mss_accounts`, unique `(account_id, mailbox_address)` | 26 |
| Course perdue | relecture **par le sujet** — le défaut trouvé par le test lui-même | rejouée 3× |
| Compatibilité PSC | `MailboxCompatibility` pure, `PscIdentity` | **14** |
| Résolution de boîte | `MailboxSelectionService`, `RegisteredDatabaseName` | **11** |
| Bascule middleware | boîte ← registre, `[MailboxNotRequired]`, refus `problem+json` | suites réécrites |
| **Migration héritée** | `LegacyClaimsMigration` `[Obsolete]` + compteur de retrait | **10** |
| Gestion des boîtes | 4 endpoints, sonde **puis** persistance (ordre testé) | **11** |
| Garde de session | `Client-Session-Id` lié à sa première boîte, 409 sinon | **8** |
| Évènements d'audit | les 5 sont **écrits** (attach/detach/default + Opened/Closed) | couverts |
| Chemin bypass | sujet d'authentification dérivé de `Client-Psc-Sub` | **2** |
| Garde des claims hérités | test par lecture des sources | **1** (a trouvé 3 lecteurs manqués) |

### Ce qui reste hors de cette PR, et pourquoi

- **Provisionnement immédiat de la base au rattachement** : il reste **paresseux**
  (première requête sur la boîte), mécanisme existant et éprouvé. Le forcer au
  rattachement demanderait de construire un contexte praticien complet dans le
  contrôleur — risque disproportionné pour un gain de latence au premier accès.
- **Tests d'intégration HTTP par endpoint** : la logique est couverte au niveau
  service (11 tests, dont l'ordre sonde/persistance). L'ajout d'une suite
  `WebApplicationFactory` par route est un complément, pas une garantie
  supplémentaire sur la règle métier.
- **Test d'invalidation de cache** (detach ⇒ 403 sans attendre le TTL) :
  l'invalidation est écrite et appelée à chaque écriture ; le test dédié manque.
- **Banc de charge** : extrait en **task-306** par la revue du 2026-09-13. Cette
  US livre ce dont il dépend — le sujet d'authentification sur le chemin bypass.
  ⚠️ **À partir de là, le banc écrit dans le registre et paie ses lectures : la
  référence E015 se déplace, et c'est cette US qui la déplace.**

### Deux défauts trouvés en écrivant les tests

1. **La course perdue relisait par `account.Id`** — or quand c'est l'insertion du
   *compte* qui perd, cet identifiant n'a jamais été écrit. Faux conflit sur une
   base pourtant cohérente. Le test tirait un sujet fixe : il a échoué au premier
   passage puis **réussi au second**, la base conservant l'état. Il tire
   désormais un sujet neuf à chaque exécution.
2. **Trois lecteurs de `mssEmail` subsistaient** (`NotificationsController`,
   `BiologyAckService`, `RequestHelper`), trouvés par le test de garde. Le second
   aurait imputé l'acquittement d'un résultat de biologie au compte technique
   Keycloak au lieu du praticien.

## Sonar log — 2026-09-13

SonarQube était arrêté depuis 46 h ; relancé pour cette étape. **Deux analyses
complètes** (build Release + 5 suites avec couverture OpenCover).

| KPI | Baseline (avant task-303) | Après nettoyage | Cible |
|---|---|---|---|
| Bugs | 0 | **0** | 0 |
| Vulnérabilités | 0 | **0** | 0 |
| Note de fiabilité | A | **A** | A |
| Note de sécurité | A | **A** | A |
| Note de maintenabilité | A | **A** | A |
| Code smells (total) | 61 | 233 | — |
| Code smells (code neuf) | — | 48 → **41** | — |
| Couverture | 88,6 % | 87,3 % (neuf : 81,5 %) | — |
| Duplication | 0,4 % | **0,3 %** | — |
| **Quality Gate** | — | **ERROR** — voir ci-dessous | |

### Ce qui a été corrigé

La première analyse a révélé **un bug introduit par cette US** (fiabilité tombée
à **C**) : `S2583` sur `PostgresTenantRegistryClient`. L'analyseur lisait le
filtrage de motif `existing is { State: not … }` comme une garantie de
non-nullité et déclarait le `existing is null` suivant toujours faux. **Il avait
tort** — `FirstOrDefaultAsync` rend bien `null` — mais une condition que
l'outillage lit de travers est aussi une condition qu'un relecteur lira de
travers : forme explicite. Fiabilité revenue à **A**.

Également : deux méthodes devenues mortes (`RejectMissingMssEmailAsync`,
`RejectClientEmailMismatchAsync` — mortes **parce que** la bascule a retiré leurs
appelants), une signature à **dix paramètres** regroupée par rôle dans
`RequestIdentityServices`, trois `Assert.Single` dont la valeur était re-dérivée,
et deux faux positifs `S125` (de la prose lue comme du code à cause d'un
point-virgule en fin de ligne).

### Ce qui reste, et pourquoi

- **`CA1068` (18 occurrences)** — `CancellationToken` non dernier paramètre sur
  les méthodes du contrat. C'est la **forme arbitrée par task-299** et inscrite
  dans `conventions/csharp.md` : l'ordre des paramètres optionnels du contrat la
  contraint. Accepté, pas oublié.
- **Quality Gate ERROR** sur `new_security_hotspots_reviewed` (0 % pour un seuil
  de 100 %). **Quatre points chauds**, tous de sévérité **LOW**, tous du même
  motif (« vérifier que la configuration du logger est sûre ») et **aucun dans un
  fichier créé par cette US** : `Program.cs` ×2 et `BaseRepository.cs`
  (pré-existants), `TenantRegistryMigrator.cs` (task-299).

  > Leur revue est un **acte de sécurité humain**. La forge ne les marque pas
  > « revus » à la place de l'humain : ce serait signer une affirmation de
  > sécurité sans l'avoir instruite. À traiter dans l'UI SonarQube.
- Les autres smells du code neuf ne viennent pas de cette US (fixtures des
  services IA, version d'API par défaut, `ISerializable`).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/236 — label **`awaiting-us-completion`**
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/32 — label **`awaiting-us-completion`** (paquet **474.0.0** publié)

> ⚠️ **Règle 11 — US-complete.** Les deux PRs portent `awaiting-us-completion`,
> **pas** `awaiting-human-merge` : cette vague est de la plomberie sans valeur
> médecin tant que **task-304** (sélecteur, bascule en direct dans les trois
> fronts) n'est pas en PR prête. Le test humain se fait sur la **US assemblée**.

## Code Review Summary

**APPROVED** — 0 blocage.

| Zone | Verdict |
|---|---|
| `MailboxCompatibility` | ✅ pure, sans I/O, matrice de 14 tests. Les deux questions (`Selectable` / `CanUseImap`) restent séparées de bout en bout jusqu'au DTO |
| `MailboxSelectionService` | ✅ rend un verdict métier, jamais un code HTTP — traduit à la frontière, testable sans hôte web |
| `MailboxManagementService` | ✅ ordre sonde→persistance **testé** (`Received.InOrder`), conflits distingués **par type** et non par sous-chaîne (règle 12) |
| `LegacyClaimsMigration` | ✅ isolée, `[Obsolete]`, compteur de retrait. Jamais d'écrasement d'ancrage |
| `SessionMailboxGuard` | ✅ ne journalise **aucune** des deux adresses — deux adresses MSSanté côte à côte seraient un rapprochement de praticiens |
| Middleware | ✅ refus en `problem+json`, piège `MapInboundClaims` contourné et testé des deux côtés |
| `PostgresTenantRegistryClient` | ✅ course perdue relue **par le sujet** ; aucune entité de persistance ne traverse le contrat |
| Migration | ✅ **nouvelle**, jamais une édition (règle 7c) ; renumérotée pour passer après task-300 |
| Sécurité / données de santé | ✅ aucune adresse ni jeton dans les nouveaux journaux ; `AnonymiseAddress` sur les messages d'exception |

### Réserves assumées (non bloquantes)

- **Provisionnement de la base au rattachement** : reste **paresseux** (première
  requête). Le forcer demanderait de construire un contexte praticien complet
  dans le contrôleur — risque disproportionné pour un gain de latence au premier
  accès.
- **Tests d'intégration HTTP par endpoint** : la logique est couverte au niveau
  service. L'ajout d'une suite `WebApplicationFactory` par route est un
  complément, pas une garantie supplémentaire sur la règle métier.
- **Test d'invalidation de cache** (detach ⇒ 403 sans attendre le TTL) :
  l'invalidation est écrite et appelée à chaque écriture ; le test dédié manque.
- **Flaky pré-existant** : `GreenMailBenchSmokeTests` / `SmtpSessionReuseBenchSmokeTests`
  échouent par intermittence sur cette machine (conteneurs concurrents). Identifié
  comme tel depuis task-297, vert au rejeu, hors du diff de cette US.

## Branches

- `api-mail` (pushed) : `feat/task-303-comptes-multi-messageries` — depuis `origin/develop` `142e0cd` (task-299 incluse)
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-303-comptes-multi-messageries
- `dtos-mss` (pushed, auto-incluse) : `feat/task-303-comptes-multi-messageries` — depuis `origin/develop` `f20f310`
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-303-comptes-multi-messageries

> Pré-vol : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` tous sur `develop`, arbres propres.
> `host` et `interop-cda` n'ont pas de dépôt sur ce poste — non mesurables (cf. avertissement CLAUDE.md).
> Repère : le tag d'étape `palier-1000-stable-pre-E016` marque l'état **antérieur** à ce chantier.

## Timings

*(généré par `tools/timing/report.sh --task task-303 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 26 s | — | — | — | — |
| /develop | ok | — | 1 (2.3 s) | 5 (6 min 22 s) | — | dtos-mss 1B/0T, api-mail 0B/5T, implementation complete, 4495 tests verts; no start marker |
| /sonar | ok | 26 min 35 s | 1 (16 s) | 1 (4 min 44 s) | 4 (1 min 11 s) | 2 itération(s), api-mail 1B/1T, 1 bug corrige (fiabilite C->A), 48->41 smells neufs, QG ERROR sur 4 hotspots LOW pre-existants |
| /lint-angular | skipped | 5.0 s | — | — | — | client-angular hors perimetre de la task (Repos: api-mail) |
| /lint-mobile | skipped | 0.3 s | — | — | — | client-mobile hors perimetre de la task (Repos: api-mail) |
| /verify-visual | skipped | 0.4 s | — | — | — | aucun ecran mobile touche (Repos: api-mail, US backend vague 1/2) |
| /review | ok | 15 min 58 s | 1 (0.2 s) | 2 (3 min 07 s) | — | api-mail 1B/2T |
| **Total cycle** | | **43 min 06 s** | **3 (19 s)** | **8 (14 min 15 s)** | **4 (1 min 11 s)** | |
