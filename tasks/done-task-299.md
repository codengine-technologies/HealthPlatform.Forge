# todo-task-299.md — Registre des tenants : un compte praticien → plusieurs messageries → un tenant (et sa base isolée) par couple, avec date de dernière connexion

**Repos**: sdk, api-mail
**Dependencies**: **task-305** (le SDK doit être redevenu un paquet backend — sans quoi tout
contrat publié ici part dans la charge utile WASM de `client-blazor` et impose un bump à un
consommateur qui n'en consomme rien). Préalable à task-300 et task-303.
**Epic**: E016
**EpicTitle**: Socle multi-tenant — registre des tenants, comptes multi-messageries et journal d'audit mutualisé
**Priorité**: **1** — préalable structurel. Trois chantiers sont aujourd'hui **impossibles**
faute d'annuaire : la purge de rétention globale, la migration de schéma des bases dormantes,
et tout inventaire transverse (cf. task-176). Aucun ne se débloque sans cette US.

## Objective

Doter la plateforme d'une **base de données commune** portant le registre du parc :
les **comptes** praticiens (identifiés par leur identité d'authentification), les **messageries**
MSSanté qui leur sont rattachées, et le **tenant** — le couple (compte, messagerie) qui **porte la
base isolée** — plus, par compte, la **date de dernière connexion** qui rend la dormance
observable.

> **Nommage — à ne pas confondre.** Dans ce produit, « annuaire » désigne déjà l'**Annuaire Santé
> de l'ANS** : `DirectoryController` (`api/v{version}/Directory`) sert `practitioners/search`,
> `specialties`, `professions` via `AnnuaireSanteService`. Le registre introduit ici n'a **rien**
> à voir. Tous ses identifiants de code portent donc **`TenantRegistry`**, jamais `Directory`, et
> il n'expose **aucune** route HTTP sous `/directory`.

Cette US ne déplace **aucune** donnée de santé et ne change **aucune** frontière d'isolation :
chaque messagerie garde sa base PostgreSQL dédiée, exactement comme aujourd'hui. Elle rend
seulement **explicite et interrogeable** un placement qui n'existe pour l'instant que sous
forme de fonction de hachage.

### Le problème, tel qu'il est dans le code aujourd'hui

Le nom de la base d'un praticien est une **fonction pure de (email, RPPS)** —
`UserContextInfo.BuildUserDatabaseName` produit `u_{rpps}_{slug}_{hash}`. Il n'existe donc
**aucune liste** des bases : elles ne sont connues qu'au moment où leur propriétaire se
connecte. Conséquences constatées, pas supposées :

| Conséquence | Preuve dans le dépôt |
|---|---|
| Aucune purge de rétention globale possible | `AuditRetentionOptions.PurgeInterval` : « no way to enumerate the practitioner databases, so a global nightly job would have nothing to iterate over » — la purge est **opportuniste**, déclenchée par l'activité du tenant lui-même |
| Un praticien qui cesse d'utiliser le produit **ne déclenche plus jamais de purge** ; ses traces (qui portent `PatientIns`, `PatientName`, `Subject`) sont conservées au-delà de la durée de rétention | conséquence directe de la ligne ci-dessus — **défaut de conformité RGPD art. 5.1.e** |
| Les migrations de schéma sont opportunistes (`MigrationHelper` + `MigrateUp` au premier contact) : une base dormante reste sur un schéma ancien sans que personne ne le sache | `UserContextInfo.ConnectionStringProvisioningServer` (task-200), `MigrationHelper.CreateDatabase` |
| Un inventaire à destination du DPO doit être lancé « base praticien par base praticien », manuellement | `Api/Mail/docs/task-176-inventaire-commingling.md` §2 |
| Le nom de base dépend de l'email **et** du RPPS : un changement d'adresse MSSanté ou une correction de RPPS crée une **base neuve vide** et rend l'ancienne invisible, silencieusement | `BuildUserDatabaseName(email, rpps)` — aucun état stocké ne rattrape la bascule |

### Modèle retenu

```
Compte (sub Keycloak, RPPS)  1 ──< N  Rattachement [base isolée]  N >── 1  Messagerie (adresse MSSanté)
```

- **Compte** — un praticien. Identifiant technique **stable** (`Guid` v7, cf. stratégie de PK
  de la plateforme). Deux clés naturelles : le **`sub` Keycloak** (identité d'authentification,
  **unique et obligatoire** — c'est par lui que le middleware résout le compte ; piège connu :
  `MapInboundClaims` non désactivé rend `FindFirstValue("sub")` null, lire
  `ClaimTypes.NameIdentifier`) et le **RPPS** (unique lorsqu'il est présent). Le compte porte
  aussi **`PscSubject`** (le `sub` du jeton PSC, unique, nullable). **Ni `Rpps` ni
  `PscSubject` ne sont lus des claims Keycloak `mssSub` / `mssRpps`** — ces claims disparaissent
  du modèle cible (task-303). Ils sont **ancrés** au premier rattachement de boîte réussi, depuis
  le jeton PSC que l'opérateur MSSanté vient de valider en XOAUTH2 ; jamais réécrits ensuite
  (règle « pas de re-binding silencieux » héritée de task-049). Cette US crée les colonnes et la
  règle d'unicité ; l'ancrage lui-même est livré par task-303 — en attendant, un compte peut
  exister **non ancré** (`PscSubject` et `Rpps` nuls).
- **Messagerie** — une adresse MSSanté (unique), son domaine d'opérateur.
- **Tenant** = le rattachement (compte × messagerie). **C'est le concept de premier rang de tout
  l'EPIC**, et c'est lui — pas la messagerie, pas le compte — **qui porte la base isolée**.
  Raison vérifiée dans le code : `BuildUserDatabaseName(email, rpps)` dépend du RPPS **et** de
  l'email ; deux PS partageant une adresse organisationnelle ont donc **deux bases** aujourd'hui.
  Un tenant est la *vue d'un PS sur une boîte* : ses liens patients, ses drapeaux, son journal.
  Le nom de base reste produit par `BuildUserDatabaseName`, inchangé : **aucune migration de
  données**, le registre ne fait qu'enregistrer ce que la fonction produit déjà. Le tenant porte
  aussi : `isDefault`, `state` (`Active` / `AuthFailing` / `Detached`), `attachedAt`,
  `detachedAt?`, `lastSuccessfulLoginAt?` — consommés par task-303.

  > ⚠️ **`TenantId` est l'identifiant du tenant, jamais celui du compte ni celui de la messagerie.**
  > Les trois lectures ne sont pas équivalentes, et deux d'entre elles sont des défauts graves :
  > l'id du **compte** fusionnerait les journaux des N boîtes d'un même PS ; l'id de la
  > **messagerie** ferait **voir à deux PS d'une même adresse organisationnelle les traces l'un de
  > l'autre** — une fuite de données de santé entre praticiens. Ce n'est pas théorique :
  > `MssAuditTrace.UserId` stocke l'**email**, donc deux PS sur une boîte organisationnelle ont le
  > **même** `UserId` et seul le tenant les distingue. task-300 (journal mutualisé) et task-303
  > (résolution de la boîte courante) consomment tous deux `TenantId` : il est défini **ici**,
  > une fois, pour que ces deux tâches n'aient pas à se coordonner.
- **Rattachement N:N** et non 1:N — décision de PO, justifiée : une **adresse MSSanté
  organisationnelle** appartient à une structure, pas à un PS, et plusieurs praticiens y ont
  légitimement accès. Un modèle 1:N obligerait à une migration dès le premier cas réel.
- **Dernière connexion** — deux horodatages distincts par compte, parce qu'ils ne répondent
  pas à la même question :
  - `LastAuthenticationAt` — dernière **authentification réussie** (PSC / Keycloak). C'est la
    grandeur qui définit la **dormance**.
  - `LastActivityAt` — dernière requête authentifiée, quelle qu'elle soit. Indicateur
    d'exploitation, **jamais** critère de purge.

### Décisions de PO prises ici (à contester maintenant, pas après)

1. **PK technique de substitution, RPPS en clé naturelle nullable.** Le RPPS n'est pas
   toujours présent (`UserContextInfo.NormalizeRpps` retombe sur `FallbackRpps`), et les
   professions à ADELI, les PSCo (secrétariat, sans RPPS) et les comptes de test existent.
   Un annuaire dont la PK serait le RPPS serait bloqué par le premier de ces cas.
2. **Le registre s'écrit sur le chemin de provisionnement**, au premier contact authentifié
   (là où `CREATE DATABASE` + `MigrateUp` ont déjà lieu) — en `upsert` idempotent. **Aucune
   énumération n'est requise pour le peupler** : c'est l'œuf et la poule, et on le résout par
   l'écriture au fil de l'eau, pas par un balayage impossible.

   > ⚠️ **Ce chemin est le comportement PRÉ-task-303, et lui seul.** Ici, la messagerie provient
   > du claim `mssEmail`, déjà validé par une sonde IMAP lors de l'onboarding task-037 : le
   > rattachement est donc légitime. **À partir de task-303, rattacher une boîte exige une sonde
   > IMAP côté serveur** — un rattachement sans sonde deviendrait un contournement du garde-fou
   > central. Ce code est donc écrit **dès maintenant dans une classe isolée et marquée**
   > `LegacyClaimsMigration` (`[Obsolete]`, compteur `mss_registry_legacy_claims_migrations_total`),
   > que task-303 **reprend telle quelle** et que le retrait des mappers Keycloak supprimera.
   > Aucun autre chemin d'écriture de rattachement n'existe dans cette US.
3. **`LastActivityAt` est throttlé** : au plus **une écriture par heure et par compte**,
   gardée par un marqueur Redis à TTL (le motif déjà utilisé pour les traitements
   opportunistes par tenant). Sans ce garde-fou, l'annuaire deviendrait un point d'écriture à
   chaque requête — exactement le défaut que E015 combat.
4. **Zéro DSCP dans l'annuaire.** Il porte un id, un RPPS, une adresse MSSanté, un nom de
   base, un état, une version de schéma, des horodatages. **Jamais** d'INS, de nom de patient,
   de sujet de message ni de contenu.
5. **La dormance ne supprime rien par elle-même.** Elle rend un compte *éligible* au passage
   de purge de rétention (qui, lui, applique les durées déjà définies). Elle ne crée **aucune**
   nouvelle règle de suppression, et surtout pas la suppression d'une base praticien : la
   conservation du dossier médical relève d'un autre arbitrage, hors de cette US.
6. **Contrat séparé de l'implémentation** (arbitrage humain 2026-09-13 : la base centrale aura
   à terme **son propre backend d'API sur le réseau privé**). La bascule future vers
   `HttpTenantRegistryClient` doit rester **un simple changement d'enregistrement DI** ;
   l'implémentation `PostgresTenantRegistryClient` (EF/Npgsql) est la seule à connaître le
   `DbContext`.

   > ⚠️ **Révisé le 2026-09-13, après `/review`, sur décision humaine.** La forme initialement
   > livrée plaçait `ITenantRegistryClient` et ses `record` dans `HealthPlatform.Host.Sdk`. Le
   > coût réel était un **cycle de publication à chaque évolution du modèle** — commit SDK,
   > attente de CI, publication NuGet, bump de consommateur — pour un modèle qui bougera à chaque
   > vague de l'EPIC (300, 301, 303). Les types sont rapatriés dans `api-mail`, isolés par leurs
   > espaces de noms. Voir « Révision post-review » en fin de fichier.

   **Conséquence de task-305 : le SDK n'a plus qu'un consommateur, `api-mail`.** Le cycle
   publish → CI → bump (`agents/develop.md` Step 3b) ne porte donc plus que sur lui.

### Contrat SDK — contraintes de migrabilité (non négociables dans le code)

Chaque contrainte prépare le saut réseau ; aucune ne coûte quoi que ce soit aujourd'hui.

- **Asynchrone, `CancellationToken` partout ; DTOs `record` immuables ; aucune entité EF ni
  `IQueryable` ne traverse l'interface.**
- **Opérations à gros grain** (`EnsureAccountAsync(sub)`, `GetAccountAsync(sub)`,
  **`ResolveTenantAsync(sub, mailboxEmail)`** → `TenantId` + état + nom de base,
  `ListMailboxesAsync(accountId)`, `ListTenantsAsync()` (reprise task-301),
  `TouchAuthenticationAsync`, `TouchActivityAsync`, `ListDormantAccountsAsync(since)`) ;
  **écritures idempotentes** (rejouables sur timeout).
- **Aucune transaction partagée** entre l'annuaire et une base praticien — un service distant ne
  peut pas rejoindre la transaction d'`api-mail`. Test qui échoue si un `TransactionScope` /
  `BeginTransaction` englobe un appel à `ITenantRegistryClient`.
- **Exceptions typées** (`NotFoundException`, `ConflictException`, `UnavailableException` — règle
  12) : même mapping `ProblemDetails` en local et en distant.
- **Cache-first** sur tout ce que le chemin de requête consulte (compte par `sub`, boîtes du
  compte), invalidation **explicite** à l'écriture, TTL borné. Le cache fait partie du contrat.
- **Dégradation définie par opération** sur `UnavailableException` : lectures ⇒ dernière valeur
  en cache ou refus explicite ; écritures d'horodatage ⇒ best-effort journalisé ; **jamais** de
  blocage d'une requête métier (déjà exigé par le DOD).
- **Identité en paramètre**, jamais lue du `HttpContext` dans l'implémentation ; propagation de
  `X-Correlation-Id` prévue dans la signature (paramètre ou contexte explicite).
- **Un seul point d'accès** : test d'architecture qui échoue si le `DbContext` de l'annuaire est
  référencé hors de `PostgresTenantRegistryClient`.
- ~~**Contrat versionné** : namespace `HealthPlatform.Host.Sdk.TenantRegistry.V1`, évolutions
  additives.~~ **Abandonné à la révision** : le versionnement par espace de noms protège un
  consommateur externe déjà livré. Sans paquet publié, le seul appelant est `api-mail`, qui
  recompile. Le jour où le service du réseau privé existera, c'est lui qui publiera son contrat
  versionné.

**Conséquence forge (réglée le 2026-09-13)** : le SDK est désormais un **porteur de contrat**
dans `agents/develop.md` (Step 3b : publish → CI → bump des deux consommateurs, exclu de la passe
`/simplify`, ordre dtos → interop → **sdk** → api-mail). Reste le déclencheur CI du repo SDK, traité
dans le DOD ci-dessous.

### Ce que ce n'est pas

Ni une messagerie unifiée (voir un seul écran pour N boîtes : hors périmètre, décision produit
séparée — le registre la rend *possible*, il ne la livre pas), ni le rattachement de plusieurs
boîtes par le praticien (**task-303**), ni les écrans (**task-304**), ni le banc multi-BAL
(**task-306**), ni le retrait du SDK côté Blazor (**task-305**, préalable), ni un déplacement de
données de santé, ni un écran d'administration (task-302), ni le journal d'audit mutualisé
(task-300).

## Definition of Done

- [ ] Build passes on `sdk` et `api-mail` (0 errors) ; tests pass (0 failures)
- [ ] `sdk` : workflow `Sdk/.github/workflows/dotnet.yml` déclenché sur **toutes** les branches
      (`branches: [ "**" ]`, comme `dtos-mss`) — aujourd'hui `master`/`develop` seulement, donc
      aucun paquet ne serait publié depuis `feat/*` ; premier commit de la branche
      (`ci(sdk): publish NuGet from every branch`)
- [x] ~~`sdk` : `ITenantRegistryClient` + DTOs `record` dans
      `HealthPlatform.Host.Sdk.TenantRegistry.V1`…~~ **remplacé à la révision du 2026-09-13** par :
      `ITenantRegistryClient` + `EnsureTenantRequest` dans
      `mss.mail.application.Services.Repository.TenantDb`, `record` de données dans
      `mss.mail.Domain.Entities.TenantDb`, pannes typées dans `mss.mail.application.Exceptions` ;
      **aucune entité de persistance ne franchit le contrat** (test de réflexion sur toute la
      surface de l'interface) ; `Directory.Packages.props` d'`api-mail` **ramené à `13.0.0`** —
      le registre n'a plus besoin d'un paquet publié, et task-305 a retiré la référence de
      `client-blazor` (vérifier qu'elle n'est pas revenue)
- [ ] `api-mail` : `PostgresTenantRegistryClient` seule implémentation ; test d'architecture — le
      `DbContext` de l'annuaire n'est référencé nulle part ailleurs
- [ ] Test : aucun appel à `ITenantRegistryClient` à l'intérieur d'une transaction ouverte sur une
      base praticien
- [ ] Test : `UnavailableException` sur chaque opération ⇒ dégradation définie (lecture : cache
      ou refus typé ; horodatage : best-effort journalisé) ; jamais de propagation brute
- [ ] Test : invalidation du cache à chaque écriture (écriture puis lecture ⇒ valeur neuve sans
      attendre le TTL)
- [ ] Une base commune (`TenantRegistry:ConnectionString`, variable d'environnement) portant trois
      tables — comptes, messageries, rattachements — créée et migrée par un chemin **distinct**
      des migrations par tenant, idempotent et concurrent-safe (motif `MigrationHelper`,
      SQLSTATE `42P04` bénin)
- [ ] Chaîne de connexion de l'annuaire portant `Application Name=mss-mail-registry`
      (convention task-298 : tout backend Postgres doit être attribuable sans deviner par l'IP)
- [ ] Test unitaire : `upsert` du compte + messagerie + rattachement au provisionnement,
      **idempotent** (deux appels consécutifs ⇒ une seule ligne de chaque)
- [ ] Test unitaire : le nom de base enregistré **sur le rattachement** est **exactement** celui
      que produit `UserContextInfo.BuildUserDatabaseName(email, rpps)` — l'annuaire n'invente pas
      de placement, il l'enregistre
- [ ] Test unitaire : le compte est résolu par le `sub` Keycloak — test qui **échoue** si
      `FindFirstValue("sub")` rend null (piège `MapInboundClaims`)
- [ ] Test unitaire : un compte sans RPPS est enregistré (PK technique, `sub` Keycloak) et
      n'entre pas en collision avec un autre compte sans RPPS
- [ ] Test unitaire : deux messageries distinctes du même compte ⇒ **un** compte, **deux**
      messageries, **deux** rattachements portant **deux** bases distinctes
- [ ] Test unitaire : une même adresse MSSanté rattachée à deux comptes (cas organisationnel) ⇒
      **une** messagerie, **deux** rattachements, **deux** bases (`rpps` différents) — le modèle
      N:N avec la base sur le rattachement est ce qui rend ce cas représentable
- [ ] Test unitaire : `LastAuthenticationAt` mis à jour à chaque authentification réussie ;
      `LastActivityAt` écrit **au plus une fois par heure et par compte** (marqueur Redis
      posé/respecté — vérifié par un compteur d'écritures sur 100 requêtes simulées)
- [ ] Test unitaire : la requête de dormance rend les comptes sans authentification depuis
      `TenantRegistry:DormancyDays` (défaut **365**), et **aucun** compte actif
- [ ] **Aucune route HTTP nouvelle** : le registre est une dépendance interne. La première route
      qui l'expose est `GET /account/mailboxes` (task-303), sur l'`AccountController` existant.
      Test : aucun contrôleur ne route sous `/directory` autre que le `DirectoryController` de
      l'Annuaire Santé ANS (grep + test de routage)
- [ ] Aucune DSCP dans les tables de l'annuaire : test de contrat sur le schéma (liste blanche
      de colonnes), et aucune donnée de santé dans les logs du chemin annuaire
- [ ] L'indisponibilité de la base commune **ne bloque pas** l'accès du praticien à sa propre
      base : l'écriture d'annuaire est best-effort et journalisée, jamais dans le chemin
      critique d'une requête métier (test : annuaire injoignable ⇒ la requête métier reste 200)
- [ ] Documentation : `Api/Mail/docs/ADR-2026-09-13-registre-tenants.md` (modèle, décisions
      1 à 6 ci-dessus, ce que l'annuaire n'autorise pas)

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`
- **Écran / URL** : `http://127.0.0.1:5052/scalar` (ou `curl` avec un jeton de dev)
- **Actions et vérifications** :
  1. Se connecter avec un praticien de test, puis
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "select rpps, last_authentication_at from accounts"`
     → **une** ligne, horodatage à la seconde près.
  2. Lire la jointure comptes / messageries / bases : le `database_name` doit être **identique**
     à celui qu'utilise l'application. Le vérifier avec
     `docker exec postgres-pgvector psql -U postgres -c "select datname from pg_database"`
     filtré sur le préfixe des bases praticien.
  3. Se reconnecter avec une **seconde adresse MSSanté du même RPPS** → **toujours un seul
     compte**, deux messageries, deux bases.
  4. Enchaîner 100 requêtes authentifiées en moins d'une heure, puis relire `last_activity_at` :
     il ne doit avoir été écrit **qu'une fois** (compteur : `pg_stat_user_tables.n_tup_upd`).
  5. Arrêter la base commune (`docker pause`) et rejouer une action métier (lecture d'une boîte)
     → **l'action réussit** (200), une ligne de log avertit que l'annuaire est indisponible.
  6. Compter les comptes sans authentification depuis 365 jours → la requête de dormance
     répond ; sur un parc neuf, `0`.
- **Données de test** : praticiens synthétiques du banc, aucune donnée réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — socle technique d'exploitation du service MSSanté
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur la cartographie
  interne du parc de bases ; l'US sert l'exploitabilité et la conformité RGPD du service
- **INS** : non applicable — **aucune donnée patient n'entre dans l'annuaire**, par construction
  (liste blanche de colonnes vérifiée par test)
- **Authentification PS** : inchangée — PSC / e-CPS, niveau eIDAS substantiel. L'US consomme
  l'authentification existante (elle horodate son succès), elle n'en crée ni n'en relâche aucune
- **Habilitations** : inchangées — le registre n'expose **aucune route HTTP** ; la première est
  `GET /account/mailboxes` (task-303), scopée au praticien appelant.
  **Aucun accès transverse n'est ouvert par cette US** (c'est task-302, et elle est
  conditionnée à la création d'un modèle de rôles qui n'existe pas aujourd'hui)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : l'annuaire n'est pas un journal. Les évènements déjà tracés le restent ;
  l'US **débloque** en revanche l'application effective des durées de rétention déjà décidées
  (3 653 j accès aux données de santé, 365 j technique) en rendant la dormance observable
- **Consentement patient** : non applicable — aucune donnée patient
- **Référentiels métier** : **RPPS** (11 chiffres, `NormalizeRpps`), adresses **MSSanté**
  (personnelle PS / organisationnelle — le modèle N:N existe pour la seconde)
- **Hébergement HDS** : oui — la base commune est hébergée dans le même environnement HDS que
  les bases praticien. Elle ne contient pas de DSCP, mais elle contient des données
  personnelles de professionnels (RPPS, adresse MSSanté) et relève du même niveau de protection
- **AIPD / impact RGPD** : **à mettre à jour** — nouveau traitement (cartographie du parc et
  horodatage de connexion des professionnels), finalité : exploitation du service et
  application des durées de conservation. Aucune donnée de santé, aucune donnée patient.
  L'US **corrige** un défaut RGPD existant (art. 5.1.e : purge inapplicable aux comptes dormants)

## Branches

- `sdk` (pushed) : `feat/task-299-registre-tenants` — base `origin/develop` @ 1fae0cc
  https://github.com/codengine-technologies/HealthPlatform.Host.Sdk/tree/feat/task-299-registre-tenants
- `api-mail` (pushed) : `feat/task-299-registre-tenants` — base `origin/develop` @ 560237ab
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-299-registre-tenants
- `dtos-mss` (pushed, auto-inclus par la regle CLAUDE.md) : `feat/task-299-registre-tenants` — base `origin/develop` @ f20f310
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-299-registre-tenants
  **Aucun changement de contrat attendu** : le registre n'expose aucune route HTTP et ses DTOs
  vivent dans le SDK. Branche probablement sans commit, donc sans PR.

> **Ordre de publication** impose par `agents/develop.md` (Step 1) :
> `dtos-mss` -> `sdk` -> `api-mail`. Le SDK est **porteur de contrat** depuis le 2026-09-13 :
> il se publie sur NuGet et `api-mail` doit etre bumpe avant de compiler contre
> `ITenantRegistryClient`. **`client-blazor` ne doit PAS etre rebumpe** — task-305 a retire sa
> reference au SDK, et `SdkReferenceGuardTests` echoue si elle revient.

> ⚠️ **Pre-requis CI, premier commit** (item 2 du DOD) : le workflow
> `Sdk/.github/workflows/dotnet.yml` ne se declenche que sur `master`/`develop`. Tel quel, aucun
> paquet ne serait publie depuis `feat/*` et l'attente `gh run watch` tournerait a vide.

## Sonar log

**Projet** : `healthplatform` (SonarQube 25.6.0 Community — pas d'analyse par
branche : le scan écrase la photo `main`, pratique en place sur ce dépôt).
**Itérations** : 4 (plafond 5). **4 analyses complètes** (build Release + suite
avec couverture OpenCover + scan).

### KPIs qualité (baseline → final)

| Métrique | Baseline (avant task-299) | Pic (task-299 brute) | **Final** | Δ vs baseline |
|---|---|---|---|---|
| **Quality Gate** | ERROR | ERROR | **ERROR** | inchangé |
| `new_violations` | 155 | 165 | **155** | **0** |
| `new_code_smells` | 151 | 161 | **151** | **0** |
| `new_bugs` | 2 | 2 | **2** | 0 |
| `new_vulnerabilities` | 2 | 2 | **2** | 0 |
| `new_coverage` | 89,1 % | 89,1 % | **89,1 %** | 0 |
| `code_smells` (projet) | 226 | 237 | **227** | +1 |
| `coverage` (projet) | 88,5 % | 88,6 % | **88,5 %** | 0 |
| Ratings (fiabilité / sécurité / maintenabilité) | 3 / 5 / 1 | 3 / 5 / 1 | **3 / 5 / 1** | inchangés |

**task-299 est neutre pour Sonar** : les 10 violations que la task avait
introduites ont toutes été traitées, et **0 issue ne subsiste sur les fichiers du
registre**.

### Ce qui a été corrigé, par itération

| # | Règle | Où | Nature |
|---|---|---|---|
| 1 | **S1854** (MAJOR) | `PostgresTenantRegistryClient` | affectation morte — introduite par la passe qualité `/simplify` elle-même |
| 1 | **S4457** (MAJOR) | `PostgresTenantRegistryClient` | validation d'arguments dans un corps `async` : l'erreur ne levait qu'au premier `await` de l'appelant |
| 1 | **CA1068** ×4 | client + synchroniseur | jeton d'annulation en dernier sur les helpers **privés** |
| 1 | **CA1859** ×2 | client | relais direct d'une tâche concrète |
| 2 | **CA1068** | client | le `…CoreAsync` créé en itération 1 avait hérité l'ordre du contrat public |
| 2 | **S2699** | tests du synchroniseur | test sans assertion — il serait passé si le synchroniseur devenait un no-op |
| 3 | **S103** ×2 | `GlobalExceptionHandler` | lignes de mapping > 150 caractères |
| 3 | **S138** | `AddApplication` | extraction de `AddTenantRegistry` (98 → 94 lignes) |
| 4 | **S103** | `GlobalExceptionHandler` | ligne `IsDatabaseUnavailable` — **dette préexistante**, repliée au passage |

### Findings acceptés (best-effort)

- **S138 sur `AddApplication`** — **non attribuable à task-299** : la méthode
  faisait déjà ~93 lignes avant les 2 lignes de cette US (seuil 80). L'extraction
  de l'itération 3 l'a réduite sans la ramener sous le seuil. La scinder est un
  refactor du code d'autrui, hors périmètre.
- **Quality Gate ERROR** — `new_violations` 155 (seuil 0) et
  `new_security_hotspots_reviewed` 83,3 % (seuil 100 %). **Aucun des deux n'est le
  fait de task-299** : la *new-code period* du projet est une baseline large qui
  inclut des tasks déjà mergées, et le QG était déjà ERROR avec exactement ces
  valeurs avant l'US. Le fait vérifiable est le Δ : **0**.

### Conventions apprises

`conventions/csharp.md` : **3 entrées créées** (S1854, S4457, CA1068) et
**1 compteur incrémenté** (CA1859, 3ᵉ récidive — variante « relais d'une tâche »).

> ⚠️ Le dernier commit (itération 4, repli de la ligne `IsDatabaseUnavailable`)
> est **postérieur au 4ᵉ scan**. Les chiffres du tableau sont donc ceux d'avant ce
> commit, qui ne peut que les améliorer d'une unité.

## Lint log

**`/lint-angular` : skip propre.** `client-angular` n'est pas dans les
`**Repos**:` de cette US (`sdk`, `api-mail`) et aucune ligne d'Angular n'a été
écrite. Aucune commande de lint, de build ou de test n'a été lancée sur
`Client/Angular/front/`.

> Les deux fichiers modifiés dans `Client/Angular/` au moment du cycle
> (`environment.ts` de `mss` et de `weda2`, bascule de `mssApiUrl` sur
> `localhost:7012`) appartiennent à l'humain, sur sa branche
> `feature/nova-rewriting-mss`. Le mode code-only interdit toute opération git
> sur ce dépôt : la forge ne les a ni lus comme siens, ni touchés.

**`/lint-mobile` : skip propre également** — `client-mobile` n'est pas davantage
dans les `**Repos**:`.

## Visual verify log

**Skip propre.** `client-mobile` n'est pas dans les `**Repos**:` de cette US, la
task ne déclare aucun `## Stitch design log`, et aucun écran n'a été touché —
task-299 est une US de socle (contrat SDK + base commune + crochet de
middleware), sans surface visible. Aucun serveur `ng serve` démarré, aucune
capture produite, `Docs/epics/img/screens/client-mobile/` inchangé.

## PRs

- `sdk` : https://github.com/codengine-technologies/HealthPlatform.Host.Sdk/pull/3
  — label `awaiting-human-merge`. Paquet publié **`14.0.0`** (run CI 14).
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/233
  — label `awaiting-human-merge`.
- `dtos-mss` : **aucune PR** — branche auto-incluse, **0 commit** (le registre n'expose aucune
  route et ses DTOs vivent dans le SDK, comme la section `## Branches` le prévoyait).
- `client-blazor` : **délibérément non rebumpé** — task-305 a retiré sa référence au SDK, et
  `SdkReferenceGuardTests` échoue si elle revient.

> **Ordre de merge** : le SDK **d'abord** (`api-mail` compile contre le paquet `14.0.0` déjà
> publié, mais `develop` d'`api-mail` référencera une version dont le code source n'est sur
> `develop` du SDK qu'après le merge de la PR #3).

## Code Review Summary

**APPROVED** — 0 bloquant, **2 suggestions**.

Build : `sdk` 0 erreur / 0 avertissement ; `api-mail` 0 erreur (1 avertissement `ASPIRE010`
préexistant sur l'AppHost) ; `dtos-mss` 0 erreur.
Tests : **sdk 23/23** ; **api-mail 4 393 / 0 échec** (16 ignorés), dont **26 dédiés au registre**.

### Les deux suggestions — et pourquoi elles ne bloquent pas

Toutes deux portent sur des méthodes **sans appelant en production aujourd'hui**. Plutôt que de
les laisser en remarque de PR, elles sont inscrites dans le **DOD de leurs consommateurs** :

1. **Curseur de pagination non prouvé traduisible en SQL** (`ListTenantsAsync`,
   `ListDormantAccountsAsync`) : `t.Id.CompareTo(cursor) > 0`. Les tests de cette US tournent sur
   le fournisseur EF **en mémoire**, qui évalue l'expression **côté client** — ils ne prouvent
   donc rien sur Postgres, où une expression non traduisible lève à l'exécution.
   → **DOD de task-301**, qui consomme la pagination.
2. **`EnsureTenantAsync` ne relit pas après `SaveIdempotentAsync`** : sur une course perdue
   (violation d'unicité, tracker vidé), la méthode rend le tenant **qu'elle a tenté d'insérer** —
   donc un `TenantId` qui n'existe pas en base, alors que c'est l'identifiant sur lequel le
   journal d'audit sera clé. `EnsureAccountAsync` fait la relecture correctement.
   → **DOD de task-303**, qui rattache les messageries.

### Autres axes revus

- **Sécurité** : aucune DSCP dans le registre (liste blanche de colonnes vérifiée par test) ;
  `CREATE DATABASE` interpolé — le nom vient de la configuration de déploiement, jamais d'une
  entrée utilisateur, et les guillemets sont échappés ; aucun secret ; aucune donnée de santé
  dans les journaux du chemin registre.
- **Architecture** : test garantissant que **seul** `PostgresTenantRegistryClient` connaît
  `TenantRegistryDbContext` ; le client reçoit une **fabrique** de contexte, ce qui interdit
  structurellement l'enrôlement dans une transaction de base praticien.
- **Performance** : lectures cache-first, budget de temps par appel, pool borné à 4, pagination
  obligatoire, horodatage d'activité bridé à 1/heure/compte.
- **Couverture** : 26 tests dédiés, dont trois qui existent parce que le défaut qu'ils couvrent
  serait **silencieux** (adresse organisationnelle, piège `MapInboundClaims`, bride d'écriture).

## Timings

*(généré par `tools/timing/report.sh --task task-299 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 50 s | — | — | — | — |
| /develop | ok | 32 min 12 s | 7 (1 min 30 s) | 13 (5 min 57 s) | — | sdk 1B/3T, api-mail 6B/10T |
| /sonar | ok | 57 min 24 s | 4 (1 min 01 s) | 5 (6 min 30 s) | — | 4 itération(s), api-mail 4B/5T |
| /lint-angular | skipped | 2.9 s | — | — | — | client-angular non touche par task-299 (Repos: sdk, api-mail) |
| /lint-mobile | skipped | 2.7 s | — | — | — | client-mobile non touche par task-299 (Repos: sdk, api-mail) |
| /verify-visual | skipped | 4.3 s | — | — | — | aucun ecran client-mobile touche (task backend + contrat SDK) |
| /review | ok | 7 min 27 s | 3 (26 s) | 2 (2 min 14 s) | — | sdk 1B/1T, api-mail 1B/1T, dtos-mss 1B/0T |
| /tech-writer | ok | 2 min 18 s | — | — | — | — |
| **Total cycle** | | **1 h 40 min** | **14 (2 min 58 s)** | **20 (14 min 42 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (1 min 24 s)

---

## Révision post-review — le contrat quitte le SDK (2026-09-13)

**Décision humaine, après l'ouverture des PRs et avant tout merge.**

> « l'utilisation du SDK pour contenir les entités ne me convient plus — je souhaite les rapatrier
> dans l'assembly `mss.mail.domain`, comme fait pour email, en séparant les entités de MailDb et de
> TenantDb, dans une optique de maintenabilité et éviter de bumper un package systématiquement
> lorsqu'il y a un changement. »

### Ce qui a été fait

| Rôle | Types | Emplacement |
|---|---|---|
| Données franchissant le contrat | `RegistryAccount`, `RegistryMailbox`, `RegistryTenant`, `TenantState` | `Domain/Entities/TenantDb` |
| Contrat | `ITenantRegistryClient`, `EnsureTenantRequest` | `Application/Services/Repository/TenantDb` |
| Pannes typées | `TenantRegistryUnavailableException`, `TenantRegistryConflictException` | `Application/Exceptions` |
| Persistance | les trois `…Row` | `Infrastructure/Persistance/TenantDb` *(inchangé)* |

Symétriquement, les **22 entités du courrier** passent de `mss.mail.Domain.Entities` à
`mss.mail.Domain.Entities.MailDb` : les deux domaines deviennent des espaces **frères**, comme
`Migrations/`, `Persistance/` et `Repositories/` l'étaient déjà depuis la restructuration
FluentMigrator. Renommage mécanique, 310 fichiers, aucun changement de comportement.

`Sdk/TenantRegistry/` est supprimé. Le changement de déclencheur CI (`branches: [ "**" ]`) **reste**
— il sert au cycle de la forge, pas à ce contrat.

### Ce que la révision ne change pas

La séparation `record` ↔ entité EF. Elle était garantie **gratuitement** par la frontière de paquet
— le SDK ne voyait pas l'infrastructure, exposer un `RegistryTenantRow` était impossible. Elle est
désormais garantie par `TenantRegistryContractTests.NoPersistenceType_CrossesTheContract`, qui
inspecte par réflexion toute la surface de l'interface (arguments, types rendus, génériques
dépliés). **C'est cette contrainte, et non l'assembly d'accueil, qui portait la promesse de
bascule vers un client HTTP.**

Un second garde-fou, `TheContract_DoesNotDependOnTheSdk`, épingle la décision : le SDK reste
référencé par l'assembly pour `IResilientCacheService`, donc une rechute compilerait sans un mot.

### Ce que la révision abandonne

Le versionnement par espace de noms (`.V1`) — sans consommateur externe, il ne protège personne.

### Impact sur les PRs ouvertes

- `sdk` — PR #3 ne porte plus que le déclencheur CI. Le paquet `14.0.0` publié reste accessible
  mais **n'est référencé par personne** ; `api-mail` repasse à `13.0.0`.
- `api-mail` — PR #233 mise à jour.
- **L'ordre de merge n'a plus d'objet** : `api-mail` ne compile plus contre un paquet dont le code
  source serait absent de `develop` du SDK. Les deux PRs sont indépendantes.

### Vérification

Build `sdk` 0 erreur / 0 avertissement, **16 tests** (23 − 7 tests de contrat, portés vers
`api-mail`). Build `api-mail` 0 erreur (1 avertissement `ASPIRE010` préexistant), **4 412 tests
verts, 0 échec, 16 ignorés** — dont **45 dédiés au registre** (26 au moment du
`/review`, + 11 nés de la restructuration FluentMigrator, + 8 portés ou créés à la révision).

Commits : `api-mail` `02967676`, `sdk` `3e79ab3`.
