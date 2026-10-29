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

> **Écart assumé — étiquettes.** Une étiquette est une colonne du message dans la base de la boîte,
> sans clé de personne : même mécanisme que le rattachement de patient, prouvé par M9. Aucun test
> HTTP propre aux étiquettes : le `MailController` exige la pile IMAP complète. À trancher par
> `/review`.

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

## Timings

*(généré par `tools/timing/report.sh --task task-404 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 57 min 07 s | 3 (30 s) | 10 (10 min 57 s) | — | api-mail 1B/4T, client-mobile 1B/2T, client-angular 1B/4T |
| **Total cycle** | | **57 min 35 s** | **3 (30 s)** | **10 (10 min 57 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (6.5 s), restore ×1 (22 s)
