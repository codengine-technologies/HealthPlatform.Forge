# todo-task-299.md — Annuaire commun : un compte praticien (RPPS) → plusieurs messageries → une base isolée par messagerie, avec date de dernière connexion

**Repos**: sdk, api-mail
**Dependencies**: — (aucune ; US autonome, préalable à task-300 et task-303)
**Epic**: E016
**EpicTitle**: Socle multi-tenant — annuaire et journal d'audit mutualisé
**Single frontend**: true
**Priorité**: **1** — préalable structurel. Trois chantiers sont aujourd'hui **impossibles**
faute d'annuaire : la purge de rétention globale, la migration de schéma des bases dormantes,
et tout inventaire transverse (cf. task-176). Aucun ne se débloque sans cette US.

## Objective

Doter la plateforme d'une **base de données commune** portant l'annuaire du parc :
les **comptes** praticiens (identifiés par RPPS), les **messageries** MSSanté qui leur sont
rattachées, et la **base isolée** associée à chaque messagerie — plus, par compte, la **date de
dernière connexion** qui rend la dormance observable.

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
- **Rattachement** (compte × messagerie) — **c'est lui qui porte la base isolée**, pas la
  messagerie. Raison vérifiée dans le code : `BuildUserDatabaseName(email, rpps)` dépend du RPPS
  **et** de l'email ; deux PS partageant une adresse organisationnelle ont donc **deux bases**
  aujourd'hui. La base est la *vue de ce PS sur cette boîte* (ses liens patients, ses drapeaux,
  son journal). Le nom de base reste produit par `BuildUserDatabaseName`, inchangé : **aucune
  migration de données**, l'annuaire ne fait qu'enregistrer ce que la fonction produit déjà.
  Le rattachement porte aussi : `isDefault`, `state` (`Active` / `AuthFailing` / `Detached`),
  `attachedAt`, `detachedAt?`, `lastSuccessfulLoginAt?` — consommés par task-303.
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
2. **L'annuaire s'écrit sur le chemin de provisionnement**, au premier contact authentifié
   (là où `CREATE DATABASE` + `MigrateUp` ont déjà lieu) — en `upsert` idempotent. **Aucune
   énumération n'est requise pour le peupler** : c'est l'œuf et la poule, et on le résout par
   l'écriture au fil de l'eau, pas par un balayage impossible.
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
6. **Contrat dans le SDK, implémentation dans `api-mail`** (arbitrage humain 2026-09-13 : la
   base centrale aura à terme **son propre backend d'API sur le réseau privé**). L'interface
   `IDirectoryClient` et ses DTOs vivent dans `HealthPlatform.Host.Sdk` ; l'implémentation
   `PostgresDirectoryClient` (EF/Npgsql) vit dans `api-mail/Infrastructure`. **Jamais**
   d'implémentation Postgres dans le SDK : il est chargé dans Blazor WASM. La bascule future vers
   `HttpDirectoryClient` doit être **un changement d'enregistrement DI**, rien d'autre — voir la
   section « Contrat SDK — contraintes de migrabilité ».

### Contrat SDK — contraintes de migrabilité (non négociables dans le code)

Chaque contrainte prépare le saut réseau ; aucune ne coûte quoi que ce soit aujourd'hui.

- **Asynchrone, `CancellationToken` partout ; DTOs `record` immuables ; aucune entité EF ni
  `IQueryable` ne traverse l'interface.**
- **Opérations à gros grain** (`EnsureAccountAsync(sub)`, `GetAccountAsync(sub)`,
  `ListMailboxesAsync(accountId)`, `TouchAuthenticationAsync`, `TouchActivityAsync`,
  `ListDormantAccountsAsync(since)`) ; **écritures idempotentes** (rejouables sur timeout).
- **Aucune transaction partagée** entre l'annuaire et une base praticien — un service distant ne
  peut pas rejoindre la transaction d'`api-mail`. Test qui échoue si un `TransactionScope` /
  `BeginTransaction` englobe un appel à `IDirectoryClient`.
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
  référencé hors de `PostgresDirectoryClient`.
- **Contrat versionné** : namespace `HealthPlatform.Host.Sdk.Directory.V1`, évolutions additives.

**Conséquence forge (réglée le 2026-09-13)** : le SDK est désormais un **porteur de contrat**
dans `agents/develop.md` (Step 3b : publish → CI → bump des deux consommateurs, exclu de la passe
`/simplify`, ordre dtos → interop → **sdk** → api-mail). Reste le déclencheur CI du repo SDK, traité
dans le DOD ci-dessous.

### Ce que ce n'est pas

Ni une messagerie unifiée (voir un seul écran pour N boîtes : hors périmètre, décision produit
séparée — l'annuaire la rend *possible*, il ne la livre pas), ni le rattachement de plusieurs
boîtes par le praticien et le sélecteur de boîte (**task-303** — qui consomme ce modèle), ni un
déplacement de données de santé, ni un écran d'administration (task-302), ni le journal d'audit
mutualisé (task-300).

## Definition of Done

- [ ] Build passes on `sdk` et `api-mail` (0 errors) ; tests pass (0 failures)
- [ ] `sdk` : workflow `Sdk/.github/workflows/dotnet.yml` déclenché sur **toutes** les branches
      (`branches: [ "**" ]`, comme `dtos-mss`) — aujourd'hui `master`/`develop` seulement, donc
      aucun paquet ne serait publié depuis `feat/*` ; premier commit de la branche
      (`ci(sdk): publish NuGet from every branch`)
- [ ] `sdk` : `IDirectoryClient` + DTOs `record` dans `HealthPlatform.Host.Sdk.Directory.V1`,
      **aucune** dépendance Npgsql/EF ajoutée au SDK (test : le `.csproj` du SDK ne référence ni
      `Npgsql` ni `Microsoft.EntityFrameworkCore`) ; NuGet publié, `Directory.Packages.props`
      d'`api-mail` **et** de `client-blazor` bumpés à la même version (fin de la dérive 13/12)
- [ ] `api-mail` : `PostgresDirectoryClient` seule implémentation ; test d'architecture — le
      `DbContext` de l'annuaire n'est référencé nulle part ailleurs
- [ ] Test : aucun appel à `IDirectoryClient` à l'intérieur d'une transaction ouverte sur une
      base praticien
- [ ] Test : `UnavailableException` sur chaque opération ⇒ dégradation définie (lecture : cache
      ou refus typé ; horodatage : best-effort journalisé) ; jamais de propagation brute
- [ ] Test : invalidation du cache à chaque écriture (écriture puis lecture ⇒ valeur neuve sans
      attendre le TTL)
- [ ] Une base commune (`Directory:ConnectionString`, variable d'environnement) portant trois
      tables — comptes, messageries, rattachements — créée et migrée par un chemin **distinct**
      des migrations par tenant, idempotent et concurrent-safe (motif `MigrationHelper`,
      SQLSTATE `42P04` bénin)
- [ ] Chaîne de connexion de l'annuaire portant `Application Name=mss-mail-directory`
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
      `Directory:DormancyDays` (défaut **365**), et **aucun** compte actif
- [ ] Test d'intégration : `GET /v1/directory/self` (le praticien voit **ses** comptes,
      messageries et états — jamais ceux d'un autre) ; extension de
      `CrossTenantOwnershipTests` à ce nouveau chemin
- [ ] Aucune DSCP dans les tables de l'annuaire : test de contrat sur le schéma (liste blanche
      de colonnes), et aucune donnée de santé dans les logs du chemin annuaire
- [ ] L'indisponibilité de la base commune **ne bloque pas** l'accès du praticien à sa propre
      base : l'écriture d'annuaire est best-effort et journalisée, jamais dans le chemin
      critique d'une requête métier (test : annuaire injoignable ⇒ la requête métier reste 200)
- [ ] Documentation : `Api/Mail/docs/ADR-2026-09-13-annuaire-multi-tenant.md` (modèle, décisions
      1 à 6 ci-dessus, ce que l'annuaire n'autorise pas)

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`
- **Écran / URL** : `http://127.0.0.1:5052/scalar` (ou `curl` avec un jeton de dev)
- **Actions et vérifications** :
  1. Se connecter avec un praticien de test, puis
     `docker exec postgres-pgvector psql -U postgres -d mss_directory -c "select rpps, last_authentication_at from accounts"`
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
- **Habilitations** : inchangées — `GET /v1/directory/self` est scopé au praticien appelant.
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
