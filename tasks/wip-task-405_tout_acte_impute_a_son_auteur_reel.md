# todo-task-405 — Tout acte est imputé à son auteur réel

**Repos**: dtos-mss, api-mail, client-angular, client-mobile
**Dependencies**: task-404 (la base partagée)
**Epic**: E020

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 — « tout acte est imputé à son auteur réel :
> règle d'or de la traçabilité ». Mots de l'humain : « tout, absolument tout doit être tracé par celui
> qui le fait. Si Cyril supprime un email de la BAL du titulaire, on écrit que Cyril a supprimé. » et
> « on doit savoir nominativement qui a fait quoi ».
>
> Reprend, sur le modèle « une base par boîte », l'objectif de la task-400 (abandonnée avec le
> retrait de `shared/`).

## Ce qui est établi

- **Qui, aujourd'hui** : `AuditService` écrit `UserId = _userContextInfo.Email` (`AuditService.cs:90`),
  c'est-à-dire l'**adresse de la boîte**, pas la personne. `TransportMssRpps` est le RPPS du
  rattachement. Aucun nom.
- **Lecture** : `audit_traces` sous RLS `tenant_id = mss.tenant_id`
  (`20260913120000_CreateTenantRegistry.cs:388-405`), `tenant_id` = rattachement (personne × boîte) :
  le titulaire ne voit pas les actes d'une autre personne sur sa boîte.
- **Nom** : la route `GET /v1/auth/userinfo` du proxy PSC rend prénom et nom ; api-mail appelle déjà
  le proxy avec le cookie de session et sa clé interne (`PscTokenProvider.cs:270-280`) — aucune
  évolution du proxy n'est requise (constat de la task-400).
- **Types d'actes** (`Dtos/AuditActionType.cs`, 41 membres) : connexions IMAP/SMTP, lecture, envoi,
  réponse, suppression, déplacement, drapeaux, brouillons, impression, exports, pièces jointes,
  acquittements biologie, rattachement / détachement de document patient, boîtes, refus de jeton.
  **Non tracés** : étiquettes, contacts et groupes, modèles, signatures, réglages, recherche,
  consultation d'une fiche patient, assistant IA.
- **Miroir TypeScript** : `AuditActionType` est un ordinal sur le fil, recopié à la main dans weda2 ;
  il a déjà divergé une fois.
- **weda2** (`libs/mss/src/features/audit`) : liste, filtres, détail, chronologie par `Message-ID`,
  export CSV. `PostgresAuditReader.ApplyFilters` ignore les filtres `ActionType` et `Search` envoyés.

## Décisions actées (humain, 2026-10-28)

1. **Tout acte** est tracé au nom de la personne qui le fait — jamais au nom de la boîte ni du
   titulaire.
2. **Nominatif** : la trace porte le **RPPS**, le **nom** et le **prénom** (quand ils sont
   disponibles) de la personne.
3. **Lecture** : toute personne rattachée à la boîte lit **tous** les actes de la boîte, **détails
   techniques compris** (adresse IP, navigateur, session, requête et réponse du serveur).
4. Conservation inchangée : 3 653 jours pour la famille `HealthDataAccess`.

## Objective

Sur une boîte où plusieurs personnes agissent, chaque acte est tracé **nominativement** au nom de
celui qui le fait : qui (RPPS, nom, prénom, rôle), quand, quoi, sur quel objet, dans quelle boîte.
Toute personne rattachée lit tout le journal de la boîte.

## Règles

1. **Qui.** La trace porte la personne réelle :
   - son compte (`sub` Keycloak) ;
   - son **RPPS**, son **nom** et son **prénom** — RPPS du jeton PSC, nom et prénom de la route
     `userinfo` du proxy, lus une fois par session ;
   - son **rôle** (titulaire, membre, délégataire — task-402).

   Le titulaire **hors ligne** (sans session PSC) est imputé avec le RPPS, le nom et le prénom
   **enregistrés à son rattachement**. Nom ou prénom indisponibles : le champ est vide, le RPPS
   suffit à l'imputation. Un acte sans personne (tâche de fond, consommateur du bus, purge) est tracé
   **acte système**, explicitement. La boîte n'est jamais l'auteur.
2. **Quoi : tout.** Toute route qui lit une donnée de santé ou modifie quoi que ce soit dans une
   boîte émet une trace.
   - Nouveaux types d'actes : étiquette posée / retirée, contact et groupe (création, modification,
     suppression), modèle, signature, réglage, recherche, consultation d'une fiche patient, question
     à l'assistant IA.
   - Un **test d'architecture** échoue si une action de contrôleur n'est ni tracée, ni explicitement
     exemptée avec sa raison (santé du service, référentiels publics…). La règle « tout » est tenue
     par le code, pas par la relecture.
3. **Quand et où** : horodatage serveur, boîte, objet de l'acte — UID et `Message-ID`, document,
   patient (identifiant interne ; l'INS reste dans le journal d'audit en base, **jamais** dans les
   journaux applicatifs).
4. **Lecture** : toute personne rattachée à la boîte lit **tous** les actes de la boîte, détails
   techniques compris. Le cloisonnement passe du rattachement à la **boîte**, toujours par RLS, avec
   un réglage de session posé **côté serveur**. Un tiers non rattaché ne lit rien.
5. **Filtres** : `ActionType` et `Search` sont appliqués côté serveur ; un filtre **par personne**
   s'y ajoute.
6. **Sur l'objet** : là où l'écran montre déjà un auteur, il montre la **personne réelle** —
   acquittement de biologie, rattachement de document patient (« Acquitté par Dr Prénom Nom,
   délégataire, le … »). Les autres actes se lisent dans le journal.
7. **`AuditActionType`** : chaque nouveau membre a une **valeur explicite**, reportée à la main dans
   le miroir TypeScript de weda2.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-angular` (code-only), `client-mobile`
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : nouveaux types d'actes à valeurs explicites ; trace et DTO portant compte,
      RPPS, nom, prénom, rôle, acte système — package publié, consommateurs .NET bumpés, miroir
      TypeScript weda2 et types mobile mis à jour
- [ ] Migration `audit_traces` (colonnes de la personne et de la boîte) et politique RLS par boîte,
      auditées (règle 7c)
- [ ] Test d'architecture « toute action de contrôleur est tracée ou exemptée avec sa raison », vu
      rouge sur une action non tracée
- [ ] Test d'intégration de bout en bout : le délégataire supprime un message de la boîte du
      titulaire → la trace lue par le **titulaire** dans `GET /audit/traces` porte le RPPS, le nom, le
      prénom et le rôle du délégataire, et ses détails techniques — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : un tiers non rattaché ne lit aucune trace de la boîte
      (liste vide, 404 sur le détail) — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : chaque nouveau type d'acte lu dans le journal réel après
      sa route (étiquette, contact, groupe, modèle, signature, réglage, recherche, fiche patient,
      assistant IA) — vu rouge (règle 1b)
- [ ] Test d'intégration : acte d'un consommateur du bus → trace « système », sans personne — vu
      rouge (règle 1b)
- [ ] Test d'intégration : titulaire hors ligne → trace avec RPPS, nom et prénom enregistrés — vu
      rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : filtres `ActionType`, `Search` et par personne appliqués,
      lus dans la réponse réelle — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : acquittement par le délégataire → auteur réel (RPPS, nom,
      prénom, rôle) lu dans la réponse de la biologie côté titulaire — vu rouge (règle 1b)
- [ ] weda2 : écran Audit avec colonne « Qui » (Dr Prénom Nom, RPPS, rôle) et filtre par personne ;
      mobile et weda2 : auteur réel sur l'acquittement et le rattachement de document ;
      `data-testid` sur tous les éléments interactifs
- [ ] UI component tests : colonne « Qui », filtre par personne, auteur réel sur l'acquittement
- [ ] Scénario E2E-AUDIT-00N (v1 : le délégataire supprime un message ; le titulaire lit dans le
      journal « supprimé par Dr Prénom Nom, délégataire, RPPS … ») ajouté dans
      Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (angular ; mobile
      non applicable — l'application mobile n'a pas d'écran Audit)
- [ ] Scénario de l'acquittement de biologie existant versionné (auteur réel affiché) dans
      Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) ; l'INS
      reste réservé au journal d'audit en base
- [ ] Évènements PGSSI-S journalisés : tous les actes, avec la personne (RPPS, nom, prénom), le rôle
      et la boîte

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`) ; mobile
  `cd Client/Mobile && npm start` ; weda2 via le faux hôte.
- Titulaire e2e et délégataire e2e sur `boite-praticien`.
- Le délégataire supprime un message, pose une étiquette, acquitte un résultat, crée un contact,
  pose une question à l'assistant IA.
- Le titulaire ouvre le journal dans weda2 : les cinq actes sont au nom du délégataire (Dr Prénom
  Nom, RPPS, délégataire), détails techniques visibles. Le filtre « par personne » ne garde que lui.
- Sur le résultat de biologie, côté titulaire (mobile et weda2) : « Acquitté par Dr Prénom Nom
  (délégataire) ».
- Une troisième identité non rattachée : journal vide.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : à confirmer par l'humain — traçabilité et imputabilité (PGSSI-S,
  référentiel Imputabilité). La DoD n'en dépend pas
- **INS** : jamais dans les journaux applicatifs ; conservé dans le journal d'audit en base, comme
  aujourd'hui (arbitrage task-186)
- **Authentification PS** : PSC / e-CPS ; l'identité imputée vient du jeton PSC et de la route
  `userinfo` du proxy
- **Habilitations** : lecture du journal ouverte à toute personne rattachée à la boîte (task-402)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : tout acte — qui (RPPS, nom, prénom, rôle), quand, quoi, objet, boîte.
  Conservation inchangée (3 653 jours pour `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : à mettre à jour — les actes nominatifs d'un PS, détails techniques
  compris (adresse IP, navigateur), deviennent visibles des autres personnes de la boîte

## Branches

> **Empilée sur task-404** (elle-même sur task-403) : les branches partent de `origin/develop` et fusionnent `feat/task-404-une-base-par-boite`. Les PRs le disent : à merger **après** celles de task-403 puis de task-404.

- `api-mail` (pushed) : feat/task-405-tout-acte-impute-a-son-auteur-reel — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-405-tout-acte-impute-a-son-auteur-reel
- `client-mobile` (pushed) : feat/task-405-tout-acte-impute-a-son-auteur-reel — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-405-tout-acte-impute-a-son-auteur-reel
- `dtos-mss` (lazy) : aucune branche au /start ; `/develop` la crée au premier contrat touché, depuis la branche de task-404
- `client-angular` (code-only) : branche courante `feature/nova-mss-weda-integration`, qui porte déjà les fichiers non commités de task-403 et task-404. L'humain gère la branche, le commit, le push et la PR TFS

## Develop log

### Conception

- **Qui** — `AuditService.Impute` complète chaque trace avec la personne qui agit, et la boîte n'est jamais l'auteur :
  - compte (`sub` Keycloak) ;
  - RPPS : celui de la session PSC, sinon celui du rattachement ;
  - nom et prénom ;
  - rôle sur la boîte ;
  - boîte (`mailbox_id`, adresse).

  Sans compte (consommateur du bus, tâche de fond sans personne, purge), la trace est un **acte système** explicite (`is_system_act`).
- **Nom et prénom** — `PersonNameResolver` :
  - en ligne, il lit la route `GET v1/auth/userinfo` du proxy PSC une fois par session (cache par session, 12 h) ;
  - il enregistre le nom sur le rattachement (`mss_accounts.person_first_name` / `person_last_name`) quand il change ;
  - hors ligne, il rend le nom enregistré : c'est l'imputation du titulaire hors ligne ;
  - au banc, les en-têtes `Client-First-Name` / `Client-Last-Name` du contournement tiennent lieu de `userinfo`.

  Jamais bloquant : sans nom, le RPPS suffit.
- **Middleware** : la boîte (`MailboxId`) et le rôle viennent du rattachement retenu ; le nom vient du résolveur. `CopyIdentityTo` les transmet aux tâches de fond. Un message du bus ne les transmet pas, d'où l'acte système.
- **Lecture par boîte** :
  - migration `TenantDb/20261029130000_AddAuditActor` : la politique `audit_traces_mailbox_read` remplace `audit_traces_tenant_read` (`mailbox_id = mss.mailbox_id`, posé côté serveur depuis la boîte résolue) ;
  - un déclencheur `BEFORE INSERT` (`SECURITY DEFINER`) déduit la boîte du rattachement pour les traces émises avant sa résolution (rattachement, refus d'accès) ;
  - les traces existantes sont reprises par rattachement ;
  - toute personne rattachée lit tout le journal de la boîte, et un tiers ne lit rien.
- **Filtres côté serveur** : `ActionType` et `Search` (envoyés par weda2 et jusqu'ici ignorés) ; nouveau filtre par personne (`ActorRpps`). `Search` porte sur l'objet, l'expéditeur, les destinataires, le dossier, le `Message-ID`, le nom et le RPPS de la personne, avec échappement de `%` et `_`.
- **Tout acte** — chaque action de contrôleur (158) porte exactement une marque :
  - `[Audited(type)]` : un filtre d'action trace l'acte à son issue, avec le dossier, l'UID et la route assainie ;
  - `[TracedInCode(types)]` : l'action ou son service émet la trace ;
  - `[TraceExempt("raison")]` : aucune donnée de santé lue ni rien modifié, ou lecture tracée par un autre acte.

  Un test d'architecture l'impose, et vérifie que chaque type déclaré « tracé dans le code » apparaît dans les sources. Il a trouvé dès sa première exécution une action oubliée (`SyncController.StartSyncAsync`).
- **Contrat** : `dtos-mss` 560.0.0 puis **561.0.0**.
  - `ActorDto` ; types d'actes 44 à 62 (étiquette, contact, groupe, modèle, signature, réglage, recherche, fiche patient, question à l'IA, identité d'expéditeur) ;
  - 63 à 69 (dossiers créés, renommés ou supprimés, export du carnet, envoi en attente annulé, opposition du patient, décision sur un doublon), ajoutés au classement des 158 actions pour tenir la règle « tout » ;
  - `MssAuditTraceDto.Actor` / `IsSystemAct` / `MailboxAddress`, `AuditTraceFilterDto.ActorRpps`, `BiologyAckDto.CreatedBy`, `MailMedicalDocumentDto.ManualAttachedBy`.
- **Auteur réel sur l'objet** : migration `MailDb/20261029130000_AddActorColumns`. `BiologyAcks.CreatedBy*` et `MailMedicalDocuments.ManualAttachedBy*` (RPPS, prénom, nom, rôle) sont écrits à l'acquittement et au rattachement, effacés au détachement, et projetés dans tous les DTO de document.
- **Conservation** : les nouveaux types tombent dans `HealthDataAccess` (3 653 jours), par défaut d'`AuditRetentionPolicy`.

### Commits

| Repo | Commit | Contenu |
|---|---|---|
| dtos-mss | b864228 | ActorDto, types 44 à 62, auteur et boîte sur la trace, filtre par personne, auteurs → 560.0.0 |
| dtos-mss | 06dbada | types 63 à 69 → 561.0.0 |
| api-mail | 0c654a48 | fusion de la branche task-404 (empilement) |
| api-mail | b36dec76, 1bbe417d | bump `HealthPlatform.Dtos.Mss` 560.0.0 puis 561.0.0 |
| api-mail | 36df6617 | imputation, lecture par boîte, filtres, marques d'audit, auteurs, migrations |
| api-mail | 32378f35 | test d'architecture, tests d'intégration (M1 à M10), tests du journal passés à la lecture par boîte |
| api-mail | cc766680 | catalogue E2E-AUDIT-001 v1 et E2E-BIO-001 v2, nom de session au manifeste de seed |
| client-mobile | e2a9d49 | fusion de la branche task-404 (empilement) |
| client-mobile | c354540 | auteur réel de l'acquittement et du rattachement, E2E-BIO-001 v2 |

### Règle 1b — comportement → test d'intégration → preuve rouge

Chaque mutation a été réinjectée, vue rouge, puis restaurée.

| Comportement | Test | Mutation vue rouge |
|---|---|---|
| un acte du délégataire est lu par le titulaire avec RPPS, nom, prénom, rôle et détails techniques (navigateur) | `AuditImputationIntegrationTests.AnActOfTheDelegate_IsReadByTheHolder_WithTheDelegatesIdentityAndTechnicalDetails` | **M1** : `Impute` retiré |
| le délégataire supprime un message ; le titulaire lit au journal que c'est le délégataire (vrai IMAP, vrai `MailController`) | `FolderOperationsEndToEndTests.TheDelegateDeletesAMessage_TheHolderReadsInTheJournalThatTheDelegateDidIt` | **M1** |
| un tiers non rattaché ne lit rien de la boîte (liste, et 404 sur le détail) | `AThirdPartyNotAttached_ReadsNoTraceOfTheMailbox` | **M2** : politique RLS `USING (true)` |
| chaque nouveau type d'acte est lu au journal après sa route (contact, groupe, modèle, signature, réglage, identité d'expéditeur, fiche patient, recherche, question à l'IA) | `EveryNewKindOfAct_IsReadInTheJournalAfterItsRoute` | **M6** : filtre `[Audited]` muet |
| étiquette posée par le délégataire, lue au journal par le titulaire | `FolderOperationsEndToEndTests.TheDelegatesTagAndAcknowledgement_…` | **M1** |
| filtres `ActionType`, `Search` et par personne appliqués par le serveur | `TheFilters_ActionTypeSearchAndPerson_AreAppliedByTheServer` | **M3** : filtre `ActionType` retiré |
| acte d'un consommateur du bus → trace système sans personne (et boîte déduite par le déclencheur) | `AnActWithoutPerson_IsTracedAsASystemAct` | **M4** : `IsSystemAct` toujours faux |
| titulaire hors ligne → RPPS, nom et prénom enregistrés à son rattachement | `TheHolderOffline_IsImputedWithTheNameRecordedAtHisAttachment` | **M5** : nom enregistré ignoré |
| acquittement par le délégataire → auteur réel lu dans la réponse de la boîte côté titulaire | `FolderOperationsEndToEndTests.TheDelegatesTagAndAcknowledgement_…` | **M7** : `CreatedByRpps` non écrit |
| rattachement manuel par le délégataire → auteur réel lu côté titulaire | idem | **M9** : `ManualAttachedByRpps` non écrit |
| toute action est tracée ou exemptée avec sa raison | `EveryControllerActionIsTracedTests` (4 tests) | **M8** : `[Audited(TagAdded)]` retiré |

Défaut trouvé par ces tests et corrigé : la projection `MedicalDocumentTagListProjection` (vue par étiquette) omettait l'auteur du rattachement.

Clients :
- weda2 : N1 à N5 vues rouges (acte système, filtre par personne envoyé, auteur de l'acquittement, auteur du rattachement, rôle traduit) ;
- mobile : M1 à M3 vues rouges (auteur de l'acquittement, auteur du rattachement, rôle traduit).

### Tests existants changés par la règle 14 (lecture par boîte)

- `AuditJournalIntegrationTests.BLOQUANT_Deux_PS_sur_la_meme_adresse_organisationnelle_ne_se_voient_pas` est **inversé** en `BLOQUANT_Deux_PS_sur_la_meme_adresse_lisent_tous_les_actes_de_la_boite_et_eux_seuls`. C'est la décision humaine n°3 de task-405 (toute personne rattachée lit tous les actes de la boîte) ; l'isolation entre boîtes reste exigée.
- `MailboxAccessLockIntegrationTests` (task-403) affirmait que le titulaire ne lit pas la suspension de son délégataire : il la lit désormais.
- Lecteur, tri et journal : les traces de test portent la boîte de même identifiant que leur rattachement ; le helper RLS pose `mss.mailbox_id`.
- Listes blanches des colonnes du registre (+ `person_first_name`, `person_last_name`), contrat figé de l'enum (71 membres).

### Migrations (règle 7c)

- `TenantDb/20261029130000_AddAuditActor` :
  - `mss_accounts` : deux colonnes nullables ;
  - `audit_traces` : huit colonnes (`ADD COLUMN IF NOT EXISTS`, propagées aux partitions) ;
  - index `(mailbox_id, timestamp)`, reprise par rattachement, fonction et déclencheur, remplacement de la politique de lecture.

  Le Down est symétrique et rétablit la politique par rattachement. Pas d'opération fantôme. FluentMigrator n'a ni snapshot ni Designer.
- `MailDb/20261029130000_AddActorColumns` : huit colonnes nullables, Down symétrique.

### Passe qualité (§Q)

- Contrôles mécaniques §Q 2b joués **tels qu'écrits** sur le diff de la task : un S125 attrapé avant le commit (commentaire du lecteur), corrigé ; aucun S4457, xUnit1045 ni xUnit2032. Compteur S125 à 22 dans `conventions/csharp.md`.
- dtos-mss : aucune passe (porteur de contrat).

### Validation

- **api-mail** : build vert ; domain 202, infrastructure 699, api 1 306, application 3 831, intégration 1 055 verts (16 ignorés).
- **client-mobile** : build vert, 1 343 specs, lint 0 erreur, typecheck e2e propre.
- **client-angular** (code-only) : `nx build weda2` vert, 1 367 + 2 653 verts, ESLint 0 erreur sur les fichiers touchés, typecheck e2e propre.

### Écarts assumés

- La civilité (« Dr ») n'est pas affichée. Le contrat `ActorDto` ne la porte pas, alors que la route `userinfo` la rend à part (`civilityCode`).
- Le filtre par personne de weda2 est une saisie du RPPS, pas une liste des personnes de la boîte.
- Les lectures de listes d'en-têtes, du contenu d'un message et du carnet sont exemptées, raison donnée. La lecture d'un message est tracée à son passage à « lu » (`MailRead`), et chaque modification est tracée.

### client-angular — fichiers task-405 (non commités, à reprendre par l'humain sur TFS)

- `libs/mss/src/core/models/audit.model.ts` (+ spec), `biology-ack.model.ts`, `mail.model.ts`, `libs/mss/src/core/index.ts`, `utils/actor.util.ts` (+ spec)
- `libs/mss/src/features/audit/components/audit-list|audit-filter|audit-detail` (ts, html, specs nouvelles)
- `libs/mss/src/features/mail/components/biology-ack-panel` et `manual-attachment-panel` (ts, html, spec)
- `e2e/mss-e2e/support/session.ts`, `support/e2e-backend.ts`, `specs/functional.e2e.ts`

## Sonar log

- Serveur SonarQube 9.9.8 (`sonar.login`), branche `feat/task-405-tout-acte-impute-a-son-auteur-reel`. Baseline : la dernière analyse, celle de task-404 en fin de cycle.
- **Itération 1** (`cc766680`) : QG OK, couverture du code neuf à 96,8 %, **10 issues** sur le code neuf.
  - `S3776` : `TestBypassAuthenticationHandler.HandleAuthenticateAsync` passe de 15 à 18 avec les deux en-têtes de nom. Ce n'est pas du code ancien : les claims facultatifs sont extraits dans `AddOptionalClaim`.
  - `S3604` ×3 : initialiseurs sur les attributs d'audit à constructeur primaire.
  - `S3459`/`S1144` ×4 : DTO privé de désérialisation de `userinfo`.
  - `SYSLIB1045`, `CA1859` dans le test d'architecture.
- **Corrections** :
  - `a60169ae` (S3776, S3604, S3459/S1144) ;
  - `f857e9ea` (SYSLIB1045, CA1859) ;
  - `01f5cb35` : tests unitaires de `PersonNameResolver` (proxy en erreur, injoignable, non configuré, hors ligne, cache, registre indisponible), le fichier neuf le moins couvert (83 %).
- **Itération 2** (`f857e9ea`) : **QG OK, 0 issue, 0 hotspot**, couverture du code neuf à 96,8 %.
  - Reste accepté (best-effort) : `PersonNameResolver` 83 % (ses 9 tests unitaires ont été ajoutés après cette analyse, non remesurés), `ActorNames` 88,9 %, `AuditAttributes` 92 %.
  - Tests : 202 + 3 831 + 699 + 1 306 + 1 055 verts (16 ignorés).
- Phase 2 (legacy) : sans objet, 0 bug, 0 vulnérabilité, 0 code smell.
- Conventions :
  - **S3604** (3), **CA1859** (13) et **SYSLIB1045** (2) sont des récidives sur du code frais : leurs consignes existaient et n'ont pas été relues avant d'écrire ;
  - **S3459-S1144** est une nouvelle entrée.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,0 % | 96,8 % | −0,2 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 pt |
| Duplication | 0,4 % | 0,4 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Timings

*(généré par `tools/timing/report.sh --task task-405 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 28 s | — | — | — | — |
| /develop | ok | 55 min 54 s | 28 (1 min 52 s) | 14 (13 min 43 s) | — | dtos-mss 1B/0T, api-mail 23B/10T, client-mobile 3B/2T, client-angular 1B/2T |
| /sonar | ok | 23 min 27 s | 6 (53 s) | 10 (15 min 25 s) | 4 (1 min 26 s) | 2 itération(s), api-mail 6B/10T |
| **Total cycle** | | **1 h 19 min** | **34 (2 min 45 s)** | **24 (29 min 08 s)** | **4 (1 min 26 s)** | |

Autres commandes mesurées : lint ×1 (5.7 s), nuget-wait ×2 (17 s), restore ×3 (26 s)
