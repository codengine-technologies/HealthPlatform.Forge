# todo-task-054-userdb-routing-diagnostic.md — Diagnostic Seq sur l'aiguillage DB par utilisateur

**Repos**: api-mail
**Epic**: E009
**Dependencies**: task-048 (cross-check PSC/KC mergé `1acbd47`)

> ⚠ **SÉCURITÉ — incident persistant après task-048** (2026-05-21) :
> malgré le déploiement de task-048 avec `MSS_ENFORCE_PSC_IDENTITY=true`
> (`configmap.yaml` prod), un praticien authentifié via Pro Santé Connect
> avec la carte CPS de Virginie continue de voir la boîte aux lettres de
> Robert. Aucun event Seq 3721/3722/3723 n'a été observé sur la fenêtre
> du test → la barrière task-048 ne tire pas pour ces requêtes, **mais
> on ne sait pas pourquoi**.
>
> Hypothèse de travail : le claim `mssEmail` du JWT Keycloak (qui
> détermine le `UserDatabaseName` via `UserContextInfo.UserDatabaseName
> => GetUserDatabaseName(Email)`) reste figé sur l'identité historique
> de l'opt-in MSS, indépendamment de la carte CPS courante. La requête
> ouvre alors la DB historique (`mss_mail_user_robert…`) et sert ses
> rows. Pour le confirmer formellement il faut **observer** quelle DB
> est sélectionnée par requête, quelle identité PSC est portée par le
> token, et si le cross-check task-048 s'exécute bien ou est shunté
> silencieusement.

## Objectif

Phase **diagnostic-only**. Ajouter deux LoggerMessage structurés pour
rendre traçable dans Seq, à chaque requête authentifiée :

1. **Quelle DB Postgres** est sur le point d'être ouverte
   (`UserDatabaseName`).
2. **Quelle identité PSC** est portée par le `X-PSC-Token` reçu (sub
   tronqué + RPPS).
3. **Quel état** a le flag `PscIdentityOptions.Enforce` au runtime
   (pour vérifier que `MSS_ENFORCE_PSC_IDENTITY=true` est bien appliqué).
4. **Combien de NpgsqlDataSource** distinctes existent dans le cache
   process, et **pour quelle DB** une nouvelle DataSource est créée.

Ces logs permettent de produire, en 5 minutes après redéploiement, le
verdict définitif sur le mécanisme du leak. Aucune modification de
logique d'aiguillage : juste de l'observabilité.

**Hors scope** (suivra dans une task-055 séparée, conditionnée par les
constats Seq) : le fix racine du choix de la DB (option a/b/c discutées
le 2026-05-21).

## Scope

### `api-mail` — modifications

1. **`UserContextEnricherMiddleware`** :
   - Nouveau `LoggerMessage` EventId **3724** Information :
     `[UserContext] resolved.`
     Champs structurés :
     - `KcSub` (6 derniers chars du claim `sub` Keycloak = identité du
       compte KC, immutable per-session)
     - `MssEmail` (anonymisé via `AnonymiseEmail` existante — 3 chars +
       `…` + domaine)
     - `UserDatabaseName` (valeur **exacte** — c'est un nom de DB, pas
       un secret)
     - `HasPscToken` (bool)
     - `PscSub` (6 derniers chars, via `TruncateSub` existante)
     - `PscRpps` (= `SubjectNameID` du PSC token, entier non sensible)
     - `Enforce` (bool — `PscIdentityOptions.Enforce` au runtime)
     - `Path`
     - `CorrelationId`
   - Emis **une fois par requête authentifiée**, en fin de pipeline
     middleware (juste avant `await _next(context)`), uniquement si la
     requête n'a pas été rejetée par task-048 et si elle n'est pas sur
     un path exclu.
   - Réutilise `AnonymiseEmail` et `TruncateSub` déjà privées (made
     `internal` par task-048) — pas de duplication.

2. **`BaseRepository.GetOrCreateDataSource`** :
   - Le log existant `"Creating new NpgsqlDataSource for connection
     string"` (sans propriétés structurées) est remplacé par un log
     structuré `[BaseRepository] DataSource created` avec :
     - `DatabaseName` (extrait via `NpgsqlConnectionStringBuilder` —
       **jamais** la chaîne complète qui contient le password)
     - `DataSourceCacheCount` (taille de `_dataSources` après création)
   - EventId **3725** Information. (Pas de `LoggerMessage` source-gen
     car `BaseRepository` n'est pas `partial` ; un log structuré
     ordinaire suffit — fréquence très basse, 1 fois par DB par
     process.)

3. **Pas de modification** de `UserContextInfo`, `BaseRepository.CreateDbContextAsync`,
   ni du pipeline auth. Aucun changement de comportement utilisateur.

### Tests

#### `tests/mss.mail.api.tests/Middleware/UserContextEnricherMiddlewareTests.cs`

Ajouter un test :

- `AuthenticatedUserResolved_EmitsEventId3724_WithExpectedAnonymisedFields`
  — captures les logs via `FakeLogger<UserContextEnricherMiddleware>`,
  vérifie qu'exactement un EventId 3724 est émis avec `MssEmail` ==
  `"doc…@a.fr"`, `UserDatabaseName` == `"mss_mail_user_doc@a.fr"`,
  `HasPscToken` == `false`, `Enforce` == `false`.

(Les tests existants utilisent `NullLogger` — pas de régression
attendue. La présence d'un log Information additionnel ne casse rien.)

## Definition of Done

- [ ] LoggerMessage EventId 3724 ajouté dans `UserContextEnricherMiddleware`
      avec les champs listés
- [ ] Log structuré EventId 3725 dans `BaseRepository.GetOrCreateDataSource`
      (DatabaseName + DataSourceCacheCount, jamais la connection string
      complète)
- [ ] Extraction `DatabaseName` via `NpgsqlConnectionStringBuilder`
      (vérifiée par lecture du code — connection string contenant
      password → log ne contient pas le password)
- [ ] Test unitaire `AuthenticatedUserResolved_EmitsEventId3724_WithExpectedAnonymisedFields`
      passe et asserte sur les valeurs anonymisées
- [ ] Build `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreur
- [ ] Tests `dotnet test HealthPlatform.Api.Mail.sln` → 0 failure
- [ ] Aucune régression sur les tests existants
- [ ] PR ouverte sur `feat/task-054-userdb-routing-diagnostic`,
      labelée `awaiting-human-merge`
- [ ] PR description rappelle : « Diagnostic-only. Phase 2 (fix racine
      du routing DB) en task-055 conditionnée par les constats Seq des
      EventId 3724/3725 après redéploiement. »

## Branches

- `api-mail` : `feat/task-054-userdb-routing-diagnostic`

## Manual Test Plan

### Setup

- Image `api-mail` issue de `feat/task-054-…` déployée sur prod
  (Kubernetes `healthplatform-api-mail-dep`, `:develop` mutable tag).
- `MSS_ENFORCE_PSC_IDENTITY=true` (déjà en place via configmap).

### Reproduction du leak avec logs

1. Se connecter via PSC avec la carte CPS de Virginie.
2. Ouvrir la messagerie → si la boîte de Robert apparaît, le bug est
   reproduit.
3. Aller dans **Seq** et filtrer :
   - `EventId = 3724 and UserEmail like '%virginie%'` (UserEmail est
     posé par `RequestLoggingMiddleware` upstream)
   - Une ligne par requête `/api/v1/mail/folders` doit apparaître.
4. **Vérifier dans la même ligne** :
   - `UserDatabaseName` — la VRAIE valeur attendue. Si c'est
     `mss_mail_user_robert.specialiste0060694…`, le routing DB est
     bien le coupable.
   - `MssEmail` — anonymisé (doit correspondre à la DB).
   - `PscRpps` — doit être l'RPPS de la carte CPS Virginie courante.
   - `Enforce` — doit être `true` (confirme que le flag prod est lu).
   - `HasPscToken` — doit être `true` (confirme que le front envoie le
     header).
5. Vérifier aussi `EventId 3725` au démarrage du pod :
   - Un événement par DB ouverte. Si on voit
     `DatabaseName=mss_mail_user_robert…` alors qu'on attendait
     Virginie, c'est qu'on a écrit dans la DB de Robert.

### Résultat attendu du diagnostic

Une des deux conclusions Seq doit ressortir :

- **(A)** `UserDatabaseName = mss_mail_user_robert…` + `MssEmail =
  rob…@…` → le claim `mssEmail` du JWT KC est faux pour la session
  courante. Task-055 : refaire le routing DB sur `KcSub` immutable
  OU re-dériver l'email du PSC token.
- **(B)** `UserDatabaseName = mss_mail_user_virginie…` + on voit quand
  même les mails de Robert → le leak est **dans la DB de Virginie
  elle-même** (cross-contamination par le pool ou par sync IMAP qui a
  écrit sous une mauvaise identité). Task-055 différente.

Dans les deux cas, task-054 livre la donnée nécessaire pour qualifier
proprement la suite.

### Vérification de non-fuite

Inspecter manuellement 5 entrées Seq `EventId in [3724, 3725]` :
- Aucun champ ne doit contenir de **password** (la connection string
  prod contient `Password=changeme`).
- Aucun champ ne doit contenir le PSC token complet.
- `KcSub` et `PscSub` doivent faire 6 chars max.
