# todo-task-404 — Une base par boîte

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-403 (le verrou d'accès doit précéder le partage)
**Epic**: E020

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 — « une boîte = une base ». Analyse
> d'origine : le nom `u_{rpps}_{slug}_{hash(adresse)}` (`UserContextInfo.BuildUserDatabaseName`)
> donne au délégataire qui ouvre la boîte de son délégant **une seconde base**, copie complète des
> données de santé, qui survit à la révocation et diverge de l'original.
>
> **Repos clients** : `client-mobile` et `client-angular` sont listés pour le scénario E2E-SHARED-001
> (règle 1c) et, depuis l'amendement du 2026-10-29, pour l'**identité d'expéditeur** : elle quitte
> les réglages de la personne pour devenir une donnée de la boîte (contrat `dtos-mss`, écran des
> réglages mobile et weda2 — `user-settings.model.ts`, `mss-settings.component.ts`). Aucun autre
> contrat ni écran ne change.
>
> **Aucune reprise** (humain, 2026-10-28) : rien n'est en production. Le registre et les bases
> praticien de dev sont supprimés au déploiement.

## Ce qui est établi

- **Nommage** : `u_{rpps}_{slug}_{hash}` où le hash ne porte que l'adresse — le RPPS est le seul
  discriminant entre deux personnes sur une même boîte. Le nom est calculé une fois au rattachement
  (`MailboxManagementService.cs:108`, `UserContextInfo.ProposeDatabaseName`) puis enregistré dans
  `mss_accounts.database_name` ; les requêtes relisent le nom enregistré.
- **Registre** : clé unique `(account_id, mailbox_address)` ; deux comptes peuvent rattacher la même
  adresse, chacun avec son nom de base.
- **Personne dans la base** : `Users` est indexé par `UserContextInfo.Email`, c'est-à-dire l'adresse
  de la **boîte** (`BaseRepository.GetCurrentUserIdAsync`, `:150-199`). Filtrés par `UserId` :
  `UserSettings`, `MailSignatures`, `MailTemplates`, `Contacts` (`ContactRepository`),
  `BiologyAck` (`BiologyAckRepository:52,171,302`), `PendingActions`.
- **Redis** : `user:id:{email}` (`BaseRepository.cs:135`) n'inclut **pas** la base — sur deux bases
  d'une même adresse, la seconde personne relit l'identifiant de la première. Les autres clés
  (`RedisKeys` : contacts, métadonnées, UIDs, `background-sync`, brouillons) sont indexées par
  adresse, donc déjà au niveau de la boîte.
- **Code du banc et tests qui fixent le format** : `E2eReset.cs:36-45`, `E2eSeed.cs:93`,
  `LoadTestRegistryProvisioner.cs:165`, `UserContextInfoDatabaseNameCoverageTests`,
  `E2eResetTests`, `LoadTestRegistryProvisionerTests`, `UserContextEnricherMiddlewareTests`,
  intégrations `E2eRegistryProvisioning`, `LoadTestBenchProvisioning`, `AuditJournal`,
  `ProxySessionPoolKey`, `MailboxReauthentication`. Commentaires `u_{rpps}_…` : `AppHost.cs:457`,
  `pgbouncer.ini:23`, `UserContextEnricherMiddleware.cs:100,774`, `RequestHelper.cs:85`.

## Objective

Toutes les personnes rattachées à une adresse travaillent dans **la même base** : ce que l'une fait
(rattachement patient, étiquette, acquittement, classement) est vu des autres. Seuls les réglages et
les signatures restent propres à chacun. La copie par personne disparaît, et avec elle le double coût
de synchronisation et d'IA.

## Règles

1. **Nom de base = fonction de l'adresse seule** : `u_{slug}_{hash(adresse)}`, sans RPPS. Calculé
   une fois, au premier rattachement de l'adresse.
2. **Une adresse, une base — garanti par la base de données.** Une table des boîtes du registre
   (adresse unique, nom de base, type d'adresse) est référencée par les rattachements ; le type
   d'adresse posé par la task-402 y migre. Deux premiers rattachements simultanés aboutissent à
   **une** base.
3. **Partage des données** :

   | À la boîte (vu de tous) | À la personne |
   |---|---|
   | messages, dossiers, documents, patients, biologie **et son état d'acquittement**, étiquettes, contacts, modèles, brouillons (déjà dans le dossier IMAP Brouillons), **identité d'expéditeur** (nom affiché dans le `From`) | réglages, signatures, **actions IMAP en attente** |

   Les actions en attente restent à la personne : elles s'exécutent **avec son jeton**, et
   l'opérateur doit voir agir la bonne personne (règle 14).

   **Identité d'expéditeur** *(amendement du 2026-10-29, conformité ANS ECO.1.2.9, voir task-407)* :
   elle quitte les réglages de la personne (`UserSettingsDto.SenderIdentity`, lue par
   `SmtpService.ResolveSenderDisplayNameAsync`). L'ANS exige que le `From` porte le nom **du
   titulaire de la boîte**. Restée réglage personnel, elle aurait fait envoyer au délégataire
   `From: <son propre nom> <adresse du délégant>`. Elle est modifiable par le **titulaire** ; sans
   titulaire rattaché (adresse organisationnelle, ou titulaire qui n'utilise pas l'application),
   par toute personne rattachée. Chaque modification est imputée à son auteur (task-405).
4. **La personne dans la base** est identifiée par son compte (`sub` Keycloak, présent en ligne
   comme hors ligne), plus par l'adresse de la boîte. RPPS et nom d'affichage : task-405.
5. **Redis** : la clé de l'identifiant de la personne porte la base **et** la personne. Les clés
   indexées par adresse restent au niveau de la boîte.
6. **Consommateurs du bus et tâches de fond** : sans personne, ils n'écrivent **aucune** donnée
   personnelle (actes système, règle 14).
7. **Aucune compatibilité** : pas de repli sur l'ancien nom, pas d'ancienne forme dans les resets.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : l'identité d'expéditeur sort de `UserSettingsDto` et devient une donnée de
      la boîte — package publié, consommateurs .NET bumpés, types TypeScript mobile et Angular
      régénérés ; écran des réglages mobile et weda2 : l'identité est présentée comme celle de la
      boîte, en lecture seule pour un délégataire quand le titulaire est rattaché
- [ ] Migration du registre (table des boîtes, référence depuis le rattachement) auditée (règle 7c)
- [ ] Migration de la base praticien (clé personne, filtres boîte / personne) auditée (règle 7c)
- [ ] Unit tests du nommage (sans RPPS, stabilité, longueur ≤ 63) et de la clé Redis de la personne
- [ ] Test d'intégration de bout en bout : deux comptes rattachent la même adresse → **une seule**
      base au registre ; deux rattachements simultanés → une seule base — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : un patient rattaché, une étiquette posée et un résultat
      acquitté par le titulaire sont lus dans la réponse réelle du délégataire — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : contacts et modèles créés par l'un sont lus par l'autre —
      vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : réglages et signature du délégataire **absents** de la
      réponse du titulaire, et inversement — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : l'identité d'expéditeur réglée par le titulaire est lue
      dans la réponse réelle du délégataire ; le délégataire qui tente de la modifier, le titulaire
      étant rattaché, est refusé (problem+json 403) et l'identité est inchangée — vu rouge (règle 1b)
- [ ] Test d'intégration : une action en attente du délégataire s'exécute avec **son** identité —
      vu rouge (règle 1b)
- [ ] **Banc** : `E2eReset` et `E2eSeed` sur les nouveaux noms (seconde personne au seed),
      `LoadTestRegistryProvisioner` aligné, tests qui fixent le format corrigés, commentaires
      `u_{rpps}_…` mis à jour (liste dans « Ce qui est établi »)
- [ ] Scénario E2E-SHARED-001 (v1 : le titulaire rattache un patient, le délégataire le voit ; le
      délégataire change sa signature, celle du titulaire est intacte) ajouté dans
      Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté)

## Manual Test Plan

- **Avant tout test** : registre et bases praticien de dev supprimés (local, e2e, banc de charge ;
  le cluster weda-dev est appliqué par l'humain).
- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`) ; mobile
  `cd Client/Mobile && npm start` ; weda2 via le faux hôte.
- Le titulaire rattache un patient à un document, pose une étiquette, acquitte un résultat de
  biologie → le délégataire voit les trois.
- Le délégataire crée un contact et un modèle → le titulaire les voit. Il change sa signature →
  celle du titulaire ne bouge pas.
- `psql -c '\l'` : **une** base `u_…` pour `boite-praticien`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du stockage, sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable
- **INS** : inchangé — les patients restent ceux de la boîte, sans duplication
- **Authentification PS** : inchangée (PSC / e-CPS ; verrou de la task-403)
- **Habilitations** : inchangées (rôle de la task-402, verdict de la task-403)
- **Interop CI-SIS** : inchangé — IHE-XDM, CDA r2 via `interop-cda`, HPRIM
- **Tracé PGSSI-S** : inchangé ici ; l'imputation complète vient avec la task-405
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — effet positif : plus de copie des données de santé par personne
- **AIPD / impact RGPD** : à mettre à jour — une base par boîte, partagée entre titulaire,
  délégataires et membres

## Branches

> **Empilée sur task-403** : les branches partent de `origin/develop` et fusionnent `feat/task-403-l-acces-a-la-base-d-une-boite-est-ouvert` (dépendance non encore mergée). Les PRs le disent : à merger **après** celles de task-403.

- `api-mail` (pushed) : feat/task-404-une-base-par-boite — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-404-une-base-par-boite
- `client-mobile` (pushed) : feat/task-404-une-base-par-boite — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-404-une-base-par-boite
- `dtos-mss` (lazy) : aucune branche au /start — `/develop` la crée au premier contrat touché (depuis la branche de task-403)
- `client-angular` (code-only) : branche courante `feature/nova-mss-weda-integration` (porte déjà les fichiers non commités de task-403) — humain gère branche, commit, push, PR TFS

## Develop log

### Conception

- **Le nom de base ne dépend plus que de l'adresse** : `u_{slug}_{hash}`, sans RPPS
  (`UserContextInfo.ProposeDatabaseName`). Deux personnes qui rattachent la même adresse proposent
  donc le même nom.
- **Le registre grave une boîte par adresse** : table `mss_mailboxes` (adresse unique, base unique),
  référencée par `mss_accounts.mailbox_id`. Une clé étrangère composite (id, adresse, base) interdit
  qu'un rattachement désigne une autre base que celle de sa boîte. `EnsureMailboxAsync` crée la ligne
  par `INSERT … ON CONFLICT DO NOTHING`, puis la relit : deux rattachements simultanés retombent
  sur la même base.
- **Dans la base de la boîte, la personne est une ligne de `Users`** (`AuthenticationSubject` = sub
  Keycloak). La ligne « boîte » garde un sujet nul.
  - **À la boîte** (`GetMailboxUserIdAsync`) : contacts, modèles, acquittements de biologie, et
    l'identité d'expéditeur, rangée dans les réglages de la ligne « boîte ».
  - **À la personne** (`GetCurrentUserIdAsync`) : réglages, signatures, actions en attente.
  - Patients, documents, rattachements et étiquettes sont des lignes de la base sans clé de
    personne : ils sont partagés dès que la base l'est.
- **Clé Redis de l'identifiant** : `user:id:{base}:{mailbox|person:{sub}}`.
- **Identité d'expéditeur** : route `GET|PUT api/v1/account/mailboxes/current/sender-identity`
  (`MailboxSenderIdentityController`). Le titulaire seul la modifie. Sans titulaire rattaché, toute
  personne rattachée le peut. Sinon : 403 problem+json `MAILBOX_SENDER_IDENTITY_HOLDER_ONLY`. Le
  `From` de l'envoi (`SmtpService`) la lit.
- **Contrat** : `dtos-mss` 557.0.0. `UserSettingsDto.SenderIdentity` est retiré, et arrivent
  `MailboxSenderIdentityDto` et le nouveau code d'erreur.
- **Clients** : un service dédié à l'identité de la boîte, sur mobile (`MailboxSenderIdentityService`)
  comme dans weda2 (signal `canEditSenderIdentity`, placeholders `Sender…` de la rédaction). Les
  champs passent en lecture seule, avec le texte « Seul son titulaire la modifie », quand la
  personne n'a pas le droit.

### Commits

| Repo | Commit | Contenu |
|---|---|---|
| dtos-mss | 7db45ab | contrat de l'identité d'expéditeur de la boîte, publié en 557.0.0 |
| api-mail | ba0dec75 | fusion de la branche task-403 (empilement) |
| api-mail | 03ed3eb6 | nommage sans RPPS ; reset e2e et bancs alignés |
| api-mail | 249c480c | bump `HealthPlatform.Dtos.Mss` 557.0.0 |
| api-mail | b85a420d | cœur : registre des boîtes, personne dans la base, dépôts boîte / personne, identité d'expéditeur |
| api-mail | d3a07362 | tests d'intégration du partage (M1 à M6) |
| api-mail | a5548808 | patient rattaché vu du délégataire (M9), scénario E2E-SHARED-001 au catalogue |
| api-mail | 4c7bd487 | registre de la suite partagée sans pool (53300) |
| client-mobile | a7f877c | fusion de la branche task-403 (empilement) |
| client-mobile | 42f4fec | identité de la boîte, lecture seule du délégataire, E2E-SHARED-001 |

### Règle 1b — comportement → test d'intégration → preuve rouge

Suite : `tests/mss.mail.integration.tests/Api/SharedMailboxIntegrationTests.cs`. Elle utilise le
vrai registre PostgreSQL, la vraie résolution de base (provisionnée et migrée à la requête), les
vrais contrôleurs et les vrais dépôts. Seuls le proxy PSC et le verrou d'accès de task-403 sont
simulés. Chaque mutation a été réinjectée, vue rouge, puis restaurée.

| Comportement | Test | Mutation vue rouge |
|---|---|---|
| une adresse = une base, même en 8 rattachements simultanés | `TwoAccountsAttachingTheSameAddress_ShareOneDatabase_EvenWhenAttachingTogether` | **M1** : le rattachement garde la base proposée au lieu de celle de la boîte |
| contacts et modèles de l'un lus par l'autre | `ContactsAndTemplates_CreatedByOnePerson_AreReadByTheOther` | **M2** : `ContactRepository` sur `GetCurrentUserIdAsync` |
| réglages et signatures restent à la personne | `SettingsAndSignatures_StayWithThePerson` | **M3** : `UserSettingsRepository` sur `GetMailboxUserIdAsync` |
| identité réglée par le titulaire, lue du délégataire, qui ne la modifie pas (403 problem+json, identité inchangée) | `TheSenderIdentity_SetByTheHolder_IsReadByTheDelegate_WhoCannotChangeIt` | **M4** : garde `CanEditAsync` neutralisée |
| résultat de biologie acquitté par le titulaire, acquitté pour le délégataire | `ABiologyResultAcknowledgedByTheHolder_IsAcknowledgedForTheDelegate` | **M5** : `BiologyAckRepository` sur `GetCurrentUserIdAsync` |
| action en attente du délégataire, rejouée pour lui seul | `APendingActionOfTheDelegate_IsQueuedAndReplayedForHimAlone` | **M6** : `PendingActionRepository` sur `GetMailboxUserIdAsync` |
| patient rattaché par le titulaire, lu dans le dossier du délégataire | `APatientAttachedByTheHolder_IsReadInTheDelegatesPatientRecord` | **M9** : la base résolue à la requête diffère pour le délégataire. Résultat : fiche introuvable (404). Une première mutation, au rattachement, a été bloquée par la clé étrangère composite avant l'assertion : c'est le garde-fou du registre, pas la preuve, d'où la seconde mutation. |

> **Étiquettes — écart levé à la revue** : `/review` a relevé le manque de DoD (aucune étiquette lue par le délégataire), et `/develop` a été rouvert pour ce seul test. Le test `FolderOperationsEndToEndTests.ATagSetByTheHolder_IsReadByAnotherPersonOfTheSameMailbox` (`f93609c1`) passe par le vrai `MailController`, le vrai `ImapService` et la base PostgreSQL du harnais. Le titulaire pose l'étiquette (`POST …/tags`), puis une autre personne de la même adresse (autre RPPS) la lit dans la réponse de son propre hôte. **M10** : la base redevient fonction du RPPS de la personne, comme avant task-404 ; vu rouge (« collection vide »), restauré.

Clients (preuve par mutation, Vitest weda2) :
- **M7** : la rédaction ignore l'identité de la boîte → rouge « remplit les placeholders Sender… ».
- **M8** : la garde `canEditSenderIdentity` est neutralisée → rouge « un délégataire lit l'identité
  sans pouvoir la modifier ».
- Côté mobile, les specs `MailboxSenderIdentityService` (4 tests) et `settings.page` (lecture seule,
  enregistrement sur la route de la boîte) sont vertes.

### Migrations (règle 7c)

- `MailDb/20261029120000_AddUserAuthenticationSubject` : ajoute la colonne nullable et remplace
  l'index unique `IX_Users_Email` (créé par `20240101_SetupMigration`) par deux index partiels
  (`Email` si sujet nul, `AuthenticationSubject` si non nul). Le Down est symétrique : il supprime
  d'abord les lignes de personne, ce qui échoue si des signatures ou des réglages les référencent
  encore (limite assumée d'un retour arrière). FluentMigrator n'a ni snapshot ni Designer, et aucune
  opération fantôme n'a été trouvée.
- `TenantDb/20261029120000_AddMailboxes` :
  - crée `mss_mailboxes` ;
  - reprend les données par adresse : la plus ancienne base rattachée devient celle de la boîte, et
    les autres rattachements y sont réalignés ;
  - passe `mailbox_id` en NOT NULL, puis pose la clé étrangère composite.

  Une base qu'un délégataire avait seul, sous l'ancien nommage, devient orpheline : elle n'est pas
  supprimée, mais n'est plus désignée.

### Banc

- `E2eReset` / `E2eSeed` / `LoadTestRegistryProvisioner` utilisent les nouveaux noms.
- La seconde personne du seed est le délégataire du manifeste (task-402/403). Il rattache la boîte
  du praticien par délégation à l'exécution du scénario.

### Passe qualité (§Q)

- Contrôles mécaniques sur le diff : seul le code commenté (S125) a été cherché, et rien n'a été trouvé. **Le contrôle §Q 2b (S4457) n'a pas été joué**, contrairement à ce qu'annonçait la première version de ce log. Sonar a vu `SaveMailboxSenderIdentityAsync`, corrigé par `/sonar`.
- La factorisation de `OpenMailboxBaseAsync` dans la suite partagée a été faite au fil de l'eau.
- dtos-mss : jamais (porteur de contrat).

### Validation

- **api-mail** : build vert. Unitaires : domain 202, application 3 830, infrastructure 698, api
  1 302 verts. Intégration : la suite partagée a 7 verts. Suite complète après le dernier commit :
  1 045 verts, 16 ignorés sur 1 061. Un premier passage a donné 13 rouges `53300 too many clients`, tous verts une fois isolés : la connexion au registre de la suite partagée était poolée. Elle passe en `Pooling=false` (4c7bd487), conformément à la consigne de task-331.
- **client-mobile** : build vert, 1 336 specs vertes.
- **client-angular** (code-only, non commité) : `nx build weda2` vert, tests `mss`/`mss-lib`/`weda2`
  1 355 + 2 653 verts. Typecheck e2e propre.

### client-angular — fichiers task-404 (non commités, à reprendre par l'humain sur TFS)

- `libs/mss/src/core/models/user-settings.model.ts`
- `libs/mss/src/core/services/mss-api.service.ts`
- `libs/mss/src/features/settings/mss-settings.component.{ts,html,spec.ts}`
- `libs/mss/src/features/mail/components/mail-compose/mail-compose.component.{ts,spec.ts}` et les 7
  specs sœurs (mock de la nouvelle route)
- `e2e/mss-e2e/support/e2e-backend.ts` (`ActorInMailbox`)
- `e2e/mss-e2e/specs/functional.e2e.ts` (E2E-SHARED-001)

## Sonar log

- Serveur SonarQube 9.9.8 (`sonar.login`). Branche `feat/task-404-une-base-par-boite`. Baseline : la dernière analyse, celle de task-403 en fin de cycle.
- **Itération 1** (`4c7bd487`) : QG OK, couverture du code neuf à 96,9 %, **1 issue** sur le code neuf.
  - `csharpsquid:S4457` dans `UserSettingsRepository.SaveMailboxSenderIdentityAsync` : `ThrowIfNull` en tête d'une méthode `async`. C'est une récidive, et le contrôle §Q 2b n'avait pas été joué par `/develop`.
  - Le même contrôle, joué ici tel qu'écrit, trouve aussi un **S125** : une prose avec « ; » dans `UserContextIdentityCopyTests`.
  - Trois branches neuves de la task ne sont pas couvertes : le corps nul du PUT d'identité, le type de boîte gravé au rattachement d'une boîte existante, et le repli du nom d'expéditeur sans `From`.
- **Corrections** :
  - `05b2055a` : S4457, enveloppe synchrone + `SaveMailboxSenderIdentityCoreAsync` ;
  - `a8bbf9cd` : tests du PUT sans corps (400 problem+json, identité inchangée, test d'intégration), du type de boîte gravé au rattachement du titulaire (registre), et du repli sans `From` ;
  - `a4b2e833` : S125.
- **Itération 2** (`a4b2e833`) : **QG OK, 0 issue, 0 hotspot**, couverture du code neuf à 97,0 %.
  - `MailboxSenderIdentityController` et `PostgresTenantRegistryClient` sont à 100 % de lignes neuves couvertes.
  - Reste accepté (best-effort) : `UserSettingsRepository` (2 lignes, 3 conditions), `MailboxSenderIdentityService` (2 conditions), `BaseRepository` (1 condition).
  - Tests : 202 + 3 831 + 699 + 1 302 + 1 046 verts (16 ignorés).
- Phase 2 (legacy) : sans objet, 0 bug, 0 vulnérabilité, 0 code smell.
- Conventions : **S4457** passe à 8 occurrences, **S125** à 21.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,1 % | 97,0 % | −0,1 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 pt |
| Duplication | 0,4 % | 0,4 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode : chaîné, comme pour task-403. `npx eslint -f json` tourne sur les 16 fichiers `.ts`/`.html` de task-404 (suite e2e comprise), base `origin/next` rafraîchie.
- **Baseline** : **5 erreurs**, toutes sur du code touché par la task :
  - 3 `prettier/prettier` (spec e2e, rédaction) ;
  - 1 `@typescript-eslint/consistent-type-imports` (`mss-api.service.ts`) ;
  - 1 `jsdoc/require-jsdoc` (`setupAutoSave`).
- **Itération 1** : `eslint --fix` laisse 3 erreurs `prettier`. L'auto-fixer a posé un squelette de JSDoc vide en LF dans un fichier CRLF, et prettier a tourné en rond (« Circular fixes »).
- **Itération 2 (manuelle)** : la cause est l'insertion de `setupSenderIdentity`, ancrée sur la signature de `setupAutoSave`. Le JSDoc d'origine de `setupAutoSave` était resté orphelin au-dessus du bloc neuf. Le bloc orphelin est retiré, `setupAutoSave` reçoit une vraie doc, et les fins de ligne du fichier sont uniformisées en CRLF. Résultat : **0 erreur**, 39 avertissements, autant qu'à la baseline (`jsdoc/require-example` antérieurs, `max-lines`, `complexity` sur `replacePlaceholders`, avis « fichier ignoré »).
- Build / tests : `nx build weda2` vert ; `mss`/`mss-lib`/`weda2` 1 355 + 2 653 verts ; typecheck e2e propre.
- Conventions : `jsdoc/require-jsdoc` passe à **14 occurrences** dans `conventions/angular.md` (ancrage sur la signature de la méthode suivante, récidive de task-378).
- Code-only : aucune opération git sur `client-angular` (seul `git fetch origin next`).

## Lint mobile log

- Mode : chaîné, branche `feat/task-404-une-base-par-boite` (`42f4fec`), arbre propre.
- Baseline `npm run lint` : **0 erreur, 0 warning** (« All files pass linting »). Aucune itération, aucun commit.
- Build et tests non rejoués : rien n'a changé depuis la validation de `/develop` (build vert, 1 336 specs).

## E2E log

| Voie | Jouée | Résultat | Durée |
|---|---|---|---|
| mobile (`npm run e2e:headless`) | oui : `api-mail`, `client-mobile` et `dtos-mss` touchés | 52 verts, 0 flaky, 0 rouge | rejouée (empreinte changée) |
| angular (`npm run e2e:mss`) | oui : `api-mail`, `client-angular` et `dtos-mss` touchés | 60 verts, 2 flaky, 0 rouge (+1 en quarantaine) | rejouée (empreinte changée) |

- Démontage vérifié : aucun conteneur e2e résiduel.
- Écrans modifiés (Paramètres, rédaction) : les specs e2e des deux clients sont modifiées (E2E-SHARED-001).
- Flaky ajoutés au registre de `conventions/e2e.md` : E2E-PATIENT-004 et E2E-COMPOSE-004, même signature « corps de réponse libéré » que trois autres tests déjà enregistrés.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (2) :

- [angular] « patients — la vue « Mails du patient » reste ouverte et ses pages viennent du serveur » (E2E-PATIENT-004)
- [angular] « rédaction — écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut » (E2E-COMPOSE-004)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ⚠️ flaky | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ⚠️ flaky | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-MAILBOX-003 | 1 | headless | Rattacher ses boîtes depuis « Mes boîtes » — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

> Empilées sur task-403 : merger d'abord dtos #53, api-mail #323, mobile #113.

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/54 — `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/324 — `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/114 — `awaiting-human-merge`
- `client-angular` : code-only. L'humain gère le commit, le push sur TFS et l'ouverture de la PR. La branche `feature/nova-mss-weda-integration` porte aussi, non commités, les fichiers de task-403. Fichiers modifiés par task-404 :
  - `libs/mss/src/core/models/user-settings.model.ts`
  - `libs/mss/src/core/services/mss-api.service.ts`
  - `libs/mss/src/features/settings/mss-settings.component.{ts,html,spec.ts}`
  - `libs/mss/src/features/mail/components/mail-compose/mail-compose.component.{ts,spec.ts}`
  - `libs/mss/src/features/mail/components/mail-compose/mail-compose-{draft,intent,recipients,safety,spelling,suggestions,toolbar}.component.spec.ts`
  - `e2e/mss-e2e/support/e2e-backend.ts`, `e2e/mss-e2e/specs/functional.e2e.ts`

## Code Review Summary

**APPROVED** — 0 point bloquant, 2 suggestions.

- **Validation** :
  - api-mail : build vert. Tests : 202 + 3 831 + 699 + 1 302 + 1 046 verts, 16 ignorés. Un rouge isolé, `AnnuaireQuotaSharedRedisIntegrationTests` (quota temporel, hors task), vert rejoué seul.
  - client-mobile : build vert, 1 336 specs. 1 à 4 rouges sporadiques sur deux passages sur cinq, verts rejoués ; le spec instable n'est pas identifié.
  - client-angular : `nx build weda2` vert, 1 355 + 2 653 verts.
  - dtos-mss : inchangé depuis la publication de 557.0.0.
- **DoD** : tous les points sont vérifiés.
  - Le point « étiquette lue par le délégataire » manquait. `/develop` a été rouvert pour ce seul test (`f93609c1`, mutation M10 vue rouge).
  - Banc : la seconde personne est le délégataire du manifeste, rattaché à l'exécution.
  - Logs : aucune donnée de santé dans les traces ajoutées (scopes d'opération seulement).
- **Règle 1b** (comportement → test → preuve rouge) :

| Comportement | Test d'intégration | Preuve |
|---|---|---|
| une adresse = une base, même en course | `SharedMailboxIntegrationTests.TwoAccountsAttachingTheSameAddress_…` | M1 |
| contacts et modèles partagés | `ContactsAndTemplates_CreatedByOnePerson_AreReadByTheOther` | M2 |
| réglages et signatures à la personne | `SettingsAndSignatures_StayWithThePerson` | M3 |
| identité d'expéditeur de la boîte, 403 au délégataire | `TheSenderIdentity_SetByTheHolder_…` | M4 |
| acquittement de biologie partagé | `ABiologyResultAcknowledgedByTheHolder_…` | M5 |
| action en attente à la personne | `APendingActionOfTheDelegate_…` | M6 |
| patient rattaché vu du délégataire | `APatientAttachedByTheHolder_IsReadInTheDelegatesPatientRecord` | M9 |
| étiquette vue par une autre personne de la boîte | `FolderOperationsEndToEndTests.ATagSetByTheHolder_…` | M10 |
| PUT sans corps → 400 problem+json, identité inchangée | `ASenderIdentityWithoutBody_IsRefusedWith400_…` | branche de validation, couverte depuis `/sonar` |

- **Règle 14** : une base par boîte (aucune base par personne). Le rôle de titulaire, qui seul modifie l'identité, vient du registre qualifié par l'Annuaire.
- **Suggestions** :
  - quelques conditions restent non couvertes (`UserSettingsRepository`, `MailboxSenderIdentityService`, `BaseRepository`) ;
  - le spec mobile instable est à identifier (`--reporters=progress` sur plusieurs passages).
- **Données existantes** : aucune reprise, sur arbitrage humain du 2026-10-28.

## Timings

*(généré par `tools/timing/report.sh --task task-404 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 57 min 07 s | 3 (30 s) | 10 (10 min 57 s) | — | api-mail 1B/4T, client-mobile 1B/2T, client-angular 1B/4T |
| /sonar | ok | 24 min 27 s | 3 (49 s) | 14 (17 min 45 s) | 4 (1 min 41 s) | 2 itération(s), api-mail 3B/14T |
| /lint-angular | ok | 3 min 06 s | 1 (13 s) | 2 (39 s) | — | 2 itération(s), client-angular 1B/2T |
| /lint-mobile | ok | 16 s | — | — | — | — |
| /e2e | ok | 18 min 42 s | — | — | — | e2e ×5 (35 min 08 s) |
| /review | ok | 10 min 12 s | 3 (24 s) | 4 (5 min 34 s) | — | api-mail 2B/2T, client-mobile 1B/2T |
| **Total cycle** | | **1 h 54 min** | **10 (1 min 57 s)** | **30 (34 min 57 s)** | **4 (1 min 41 s)** | |

Autres commandes mesurées : lint ×5 (30 s), nuget-wait ×1 (6.5 s), restore ×1 (22 s)
