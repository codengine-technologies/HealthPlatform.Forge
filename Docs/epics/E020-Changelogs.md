# E020 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E020-boite-partagee-une-base-par-boite-tout.md](E020-boite-partagee-une-base-par-boite-tout.md).
> **Dernière mise à jour** : 2026-10-29 (v1.2)

---

## Historique détaillé des changelogs

### v1.2 — Une base par boîte — task-404

- **Task** : task-404, statut `done`. `/review` APPROVED le 2026-10-29. La revue a relevé un manque
  de DoD (l'étiquette lue par le délégataire), comblé en rouvrant `/develop` pour ce seul test
  (`f93609c1`). Run `/forge` `forge-20261029-403-405`. **Empilée sur task-403** : merger 403 d'abord.
- **PRs** (label `awaiting-human-merge`) : `dtos-mss` #54, `api-mail` #324, `client-mobile` #114 ;
  `client-angular` code-only, non commité sur `feature/nova-mss-weda-integration`.
- **dtos-mss** : `HealthPlatform.Dtos.Mss` **557.0.0** (7db45ab).
  - `UserSettingsDto.SenderIdentity` retiré.
  - Ajouts : `MailboxSenderIdentityDto { Identity, CanEdit }` et le code
    `MAILBOX_SENDER_IDENTITY_HOLDER_ONLY` (403).
- **api-mail** (03ed3eb6, 249c480c, b85a420d, d3a07362, a5548808, 4c7bd487, 05b2055a, a8bbf9cd,
  a4b2e833, f93609c1) :
  - **Nommage** : `UserContextInfo.ProposeDatabaseName(email)` → `u_{slug}_{hash}`, sans RPPS ;
  - **Registre** : table `mss_mailboxes` (adresse unique, base unique), `mss_accounts.mailbox_id`,
    clé étrangère composite (id, adresse, base). `EnsureMailboxAsync` fait un
    `INSERT … ON CONFLICT DO NOTHING` puis relit la ligne. Le type d'adresse connu est gravé sur la
    boîte. `HasActiveHolderAsync` est ajouté ;
  - **Base de la boîte** : `Users.AuthenticationSubject` (sub Keycloak), avec deux index partiels
    (`Email` pour la ligne « boîte », le sujet pour la ligne « personne ») ;
    - `GetMailboxUserIdAsync` (boîte) : contacts, modèles, acquittements de biologie ;
    - `GetCurrentUserIdAsync` (personne, ou boîte pour un acte système) : réglages, signatures,
      actions en attente ;
    - clé Redis `user:id:{base}:{mailbox|person:{sub}}` ;
  - **Identité d'expéditeur** : `MailboxSenderIdentityService` et
    `GET|PUT api/v1/account/mailboxes/current/sender-identity`. L'identité est rangée dans les
    réglages de la ligne « boîte ». Le titulaire seul la modifie, et sans titulaire rattaché toute
    personne rattachée le peut. Sinon : 403 problem+json. `SmtpService` lit le `From` de la boîte ;
  - **Migrations** : `MailDb/20261029120000_AddUserAuthenticationSubject`,
    `TenantDb/20261029120000_AddMailboxes`. Aucune reprise des données existantes, sur arbitrage
    humain : rien n'est en production ;
  - **Bancs** : `E2eReset`, `E2eSeed` et `LoadTestRegistryProvisioner` passent aux nouveaux noms ;
  - **Catalogue** : E2E-SHARED-001 v1.
- **client-mobile** (42f4fec) : `MailboxSenderIdentityService`. Paramètres en lecture seule pour qui
  ne peut pas modifier l'identité. `From` de la boîte. E2E-SHARED-001 (`ActorInMailbox`).
- **client-angular** (weda2, code-only) : `getMailboxSenderIdentity` / `saveMailboxSenderIdentity`,
  Paramètres en lecture seule, placeholders `Sender…` de la rédaction tirés de la boîte,
  E2E-SHARED-001.
- **Règle 1b** : `SharedMailboxIntegrationTests` (8 tests, vrai registre, vraie résolution de base)
  et `FolderOperationsEndToEndTests.ATagSetByTheHolder_…`. Mutations M1 à M6, M9 et M10 vues rouges.
- **Validation** : api-mail domain 202, infrastructure 699, api 1 302, application 3 831,
  integration 1 046 (16 ignorés) ; mobile 1 336 ; weda2 1 355 + 2 653.
- **Sonar** : Quality Gate OK ; new coverage 97,1 % → 97,0 % ; 0 bug, 0 vulnérabilité, 0 smell.
  Une S4457 et une S125 corrigées, toutes deux récidives du contrôle §Q 2b non joué.
- **e2e** : mobile 52 verts, weda2 60 verts dont 2 flaky (E2E-PATIENT-004, E2E-COMPOSE-004, corps de
  réponse libéré), parité verte.
- **Limites et dette** :
  - au retour arrière, la migration de la base de boîte échoue si des lignes de personne sont encore
    référencées ;
  - une base qu'un délégataire avait seul sous l'ancien nommage devient orpheline (sans objet tant
    que les bases de dev sont supprimées au déploiement) ;
  - un spec mobile instable reste à identifier ;
  - le délégataire voit le patient, mais l'**imputation** des actes à leur auteur reste à faire
    (task-405).

### v1.1 — Accès à la base d'une boîte ouvert par l'opérateur MSSanté — task-403

- **Task** : task-403, statut `done` (`/review` APPROVED le 2026-10-29 au second passage : le premier
  a exigé que les traces de refus soient relues dans le vrai journal, corrigé par `8ee621a6`). Run
  `/forge` `forge-20261029-403-405`.
- **PRs** (label `awaiting-human-merge`) : `dtos-mss` #53, `api-mail` #323, `client-mobile` #113 ;
  `client-angular` code-only, non commité sur `feature/nova-mss-weda-integration`.
- **dtos-mss** : `HealthPlatform.Dtos.Mss` 551.0.0 → **554.0.0** (40e44e2) — codes
  `MAILBOX_ACCESS_REFUSED` (403), `MAILBOX_PSC_SESSION_REQUIRED` (403), `MAILBOX_ACCESS_UNVERIFIED`
  (503) ; `AuditActionType.MailboxAccessRefused = 42`, `MailboxAccessSuspended = 43`.
- **api-mail** (1962a5f7, 22ce37df, b6e16a17, e7f3bcbf, 8ee621a6) :
  - **Domaine** : `MailboxAccessPolicy.Evaluate(role, online)` — titulaire ouvert, autres rôles :
    verdict de l'opérateur de moins de 5 min en ligne, session PSC requise hors ligne ;
  - **Verrou** : `MailboxAccessGate`, appelé par `MailboxSelectionService` sur la boîte demandée et
    sur la boîte par défaut, donc avant toute lecture et tout cache. `AuthFailing` → refusé par
    l'opérateur ;
  - **Verdicts** : `RedisOperatorVerdictStore`, clé `mailbox-access:verdict:{empreinte}`, TTL 5 min,
    échec fermé ;
  - **Renouvellement** : `ImapOperatorAccessProbe` (sonde du rattachement, jeton PSC ou mot de passe
    de banc). Refus → `AuthFailing`, verdict retiré, `StopSyncStartedByAsync` (nouvelle commande
    ciblée `SyncControlCommand.StartedBy`), traces ; injoignable → 503 sans suspension ;
  - **Usage** : `MailServerTokenRetry` (IMAP et SMTP) enregistre l'acceptation comme verdict et le
    refus définitif comme `AuthFailing` (`IOperatorVerdictRecorder`) ;
  - **Temps réel** : `SseHelper.AccessWatchAsync` revérifie toutes les
    `MailboxAccess:StreamRecheckInterval` (30 s) ; évènement final `MailboxAccessSuspended` ;
  - **Banc e2e** : `BenchOperatorRefusals` + `BenchOperatorAccessProbe`,
    `POST|DELETE /api/v1/testing/operator-refusals?mailbox=` (Development/Testing et bypass seuls) ;
  - **Composition** : enregistré dans `AddApi` ; paramètre facultatif sur `ImapServerAccess` et
    `SmtpConnectionFactory` ;
  - **Catalogue** : E2E-MAILBOX-005 v1.
- **client-mobile** (d37c55d) : `MailboxAccessSuspensionService` (intercepteur + deux flux SSE),
  `MailboxSessionService.purgeMailboxData`, écran `/access-suspended`, E2E-MAILBOX-005.
- **client-angular** (weda2, code-only) : même service dans la lib MSS, intercepteur weda2, composant
  `mss-mailbox-access-suspended`, miroir `AuditActionType` 42/43, E2E-MAILBOX-005.
- **Règle 1b** : `MailboxAccessLockIntegrationTests` (5 tests, vrai registre, vrai Redis, vrai journal
  d'audit, vraie liste en cache) et `MailServerTokenRefusalEndpointIntegrationTests` (refus en cours
  d'usage SMTP/IMAP → `AuthFailing` au registre réel). Mutations M1 à M6 vues rouges.
- **Validation** : api-mail domain 204, infrastructure 697, api 1 302, application 3 830,
  integration 1 037 (16 ignorés) ; mobile 1 332 ; weda2 build OK, 12 projets de tests verts.
- **Sonar** : Quality Gate OK ; new coverage 96,8 % → 97,1 % ; 0 bug, 0 vulnérabilité, 0 smell ;
  2 × S927 corrigées (nouvelle consigne `conventions/csharp.md`) ; S4457 récidive (compteur 7).
- **e2e** : mobile 51 verts, weda2 61 verts, parité verte ; divergence E2E-MAILBOX-002 [angular]
  toujours « à retirer » (task-395).
- **Limites et dette** (suggestions de revue) :
  - renouvellement non mutualisé : N requêtes simultanées à l'expiration → N sondes ;
  - une route de gestion portant `Client-Email` renouvelle aussi le verdict ;
  - une trace `MailboxAccessRefused` par requête refusée ;
  - Redis injoignable → sonde à chaque requête d'un non-titulaire ;
  - AIPD à mettre à jour (coupure des données synchronisées à la révocation).

### v1.0 — Rattachement guidé par l'Annuaire Santé : rôle titulaire, membre ou délégataire — task-402

- **Task** : task-402, statut `done` (`/review` APPROVED le 2026-10-28, après une pause demandée par
  l'humain au milieu de l'étape). Chaîne complète : `/develop` → `/sonar` → `/lint-angular` →
  `/lint-mobile` → `/e2e` → `/review`.
- **PRs** (label `awaiting-human-merge`) :
  - `dtos-mss` #52 ;
  - `api-mail` #321 ;
  - `client-mobile` #111 ;
  - `client-angular` : code-only, **non commité** sur `feature/nova-mss-weda-integration` (17
    fichiers, dont un nouveau spec). Commit, push et PR TFS par l'humain.
- **dtos-mss** : `HealthPlatform.Dtos.Mss` 548.0.0 → **551.0.0** (commit 6719eeb). Contenu :
  - `MailboxDto.Role` (défaut `Delegate`) et `MailboxDto.AddressType` ;
  - classes de constantes `MailboxRoles`, `MailboxAddressTypes`, `MailboxAttachModes` ;
  - `DirectoryMailboxDto` (`Email`, `AddressType`, `AlreadyAttached`) ;
  - `AttachMailboxRequest.Mode` (défaut `Delegation`) ;
  - codes `MAILBOX_NOT_IN_DIRECTORY` et `MAILBOX_LISTED_USE_DIRECTORY`.
- **api-mail** (7494367e, 437f8d3f, a5cf9187, f4719f4d, ca4db22e, 593bd96b, 7746a0f1) :
  - **Domaine** : `MailboxRole` (`Delegate=0, Holder=1, Member=2, ToRequalify=3`),
    `MailboxAddressType`, `MailboxQualification` et `DirectoryMailbox` ; `RegistryTenant` porte
    `Role` et `AddressType` ;
  - **Registre** : migration `20261028120000_AddMailboxRole`, relue (règle 7c, aucune opération
    fantôme) :
    - `role` int NOT NULL, défaut 0 ;
    - `address_type` int nullable ;
    - `Down` symétrique ;
  - **Client du registre** : `AttachMailboxAsync(…, MailboxQualification?)` et nouveau
    `RequalifyMailboxAsync`, qui rend `null` si l'adresse est inconnue ou détachée ;
  - **Annuaire** : `FhirBundleParser.TelecomOf` / `MssMailboxes` / `ReadMssMailbox` lisent la
    sous-extension `type` de `as-ext-mailbox-mss-metadata` (TRE_R257) :
    - `PER` → Personal ;
    - `ORG`/`CAB` → Organizational ;
    - `APP` → écartée ;
    - métadonnée absente → Organizational ;
    - à adresse égale, `PER` l'emporte ;
  - `DirectorySearchEngine.MailboxesOfAsync(rpps)` traite toute réponse incomplète en
    `UnavailableException` (`DIRECTORY_UNAVAILABLE`, 503) ;
    `IAnnuaireSanteService.GetPractitionerMailboxesAsync` ;
  - **Service des boîtes** (`MailboxManagementService`) :
    - `AttachAsync` reçoit le mode ; `QualifyAsync` fixe le rôle **avant** la sonde ;
    - `Directory` : revérification dans la liste du RPPS de la session ;
    - `Delegation` : refus d'une adresse de sa propre liste ; Annuaire indisponible → délégation
      acceptée sans contrôle ;
    - `RequalifyFromDirectoryAsync` requalifie une adresse déjà rattachée en délégation ou « à
      requalifier » ;
    - `RequalifyOnReauthenticationAsync` : titulaire ou membre non publié → `ToRequalify` ;
      Annuaire indisponible → rôle gardé ;
    - `ListDirectoryMailboxesAsync` : `AlreadyAttached` seulement pour titulaire ou membre ;
  - garde de rattachement réduite à `sessionIdentity is null` : le jeton relève de la sonde ;
  - `AttachMailboxStatus.RoleRefused = 5` ;
  - **Audit** : `TraceMailboxAttachRefused(errorCode, detail)`. Détail
    `mailbox-attach mode=… role=… actor-rpps=…` dans `ServerRequest`, sur le rattachement, le refus
    de rôle et la ré-authentification (colonnes dédiées à la personne : task-405) ;
  - **API** : `GET /api/v1/account/mailboxes/directory` :
    - 401 `PSC_SESSION_REQUIRED` sans session ;
    - 503 si l'Annuaire est incomplet ;
    - refus de rôle en 400 codé ;
  - `ResolvePscTokenAsync` ne demande plus de jeton au proxy sans session proxy, ni sous la claim
    `test_bypass` (`TestBypassAuthenticationHandler.BypassClaim`, réutilisée par
    `UserContextEnricherMiddleware`) ;
  - **Sonde** : `MssAccountOnboardingService` s'authentifie par mot de passe sur un serveur sans
    OAuth2 (bancs Dovecot). Ce chemin est absent de la production ;
  - **Banc e2e** :
    - faux Annuaire FHIR `FakeAnnuaireServer`, sous-commande `fake-annuaire`, port 11535,
      `FhirOptions__BaseUrl` ;
    - identités `Newcomer` (9002) et `Delegate` (9003), boîte `praticien.autre-operateur@e2e.test` ;
    - cabinet qualifié membre ;
    - `RegistryComposition.SeedCallTimeout` rétabli à 30 s (retiré par le revert de task-401) ;
  - **Catalogue** : E2E-MAILBOX-003 v1, E2E-MAILBOX-004 v1, E2E-WEDA-001 v2.
- **client-mobile** (eea646a, 0e1c008) :
  - formulaire de rattachement à deux voies : « Mes boîtes » (avec indisponibilité et Réessayer) et
    « Ajouter une BAL déléguée » ;
  - lecture de la liste par `effect` au passage en ligne ;
  - badge `mailbox-badge-role-{id}`, bandeau `mailbox-requalify-{id}`, `attachModeOf` au
    re-rattachement ;
  - e2e : `openAs`, `mailboxRow`, E2E-MAILBOX-003/004.
- **client-angular** (weda2, code-only) : mêmes deux voies, présélection de l'adresse désignée par
  Weda (`data-preselected`), badge et bandeau, e2e WEDA-001 v2 et MAILBOX-003/004.
- **Règle 1b** : `MailboxAttachRoleIntegrationTests`, 11 tests sur le vrai pipeline HTTP, le vrai
  registre PostgreSQL, le vrai `AnnuaireSanteService` (sur `FakeAnnuaireSante`) et le vrai
  `AuditService`. Mutations M1 à M12, toutes vues rouges puis restaurées.
- **Validation** :
  - api-mail, au `/review` : domain 195, infrastructure 697, application 3 783, api 1 295,
    integration 1 022 verts (16 ignorés), 0 échec ;
  - client-mobile : 1 317 verts ;
  - weda2 : build OK, `mss-lib` 119 fichiers de tests verts ;
  - dtos-mss : build OK.
- **Sonar** :
  - new coverage 97,3 % → 98,1 % ; coverage projet 97,5 % → 98,0 % ;
  - code smells 79 → 72 ;
  - Quality Gate ERROR sur des conditions héritées : 0 finding sur une ligne de la task.
- **e2e** : voie mobile 49 verts ; voie weda2 57 verts et 1 flaky (E2E-SEARCH-001, 14ᵉ occurrence) ;
  parité verte.
- **Limites et dette** :
  - AIPD à mettre à jour par l'humain (Annuaire Santé comme source, rôle de délégataire) ;
  - le nom de base dérive encore du RPPS (`UserContextInfo.ProposeDatabaseName`) : une base par
    boîte, c'est task-404 ;
  - aucun accès n'est encore subordonné au rôle : c'est task-403 ;
  - divergence E2E-MAILBOX-002 [angular] signalée « à retirer » par la porte (task-395).

---

## Annexe A — Cartographie des briques applicatives

| Brique | Emplacement | Apport E020 |
|---|---|---|
| Qualification de rôle | `Api/Mail/src/Domain/Entities/TenantDb/MailboxQualification.cs` | Rôle et type d'adresse (task-402) |
| Registre des rattachements | `Api/Mail/src/Infrastructure/Repositories/TenantDb/PostgresTenantRegistryClient.cs` | Colonnes `role` et `address_type`, requalification (task-402) |
| Service des boîtes | `Api/Mail/src/Application/Services/Mailboxes/MailboxManagementService.cs` | Rôle au rattachement, « Mes boîtes », requalification (task-402) |
| Annuaire Santé | `Api/Mail/src/Application/Services/Implementation/AnnuaireSante/` | BAL MSSanté d'un RPPS (task-402) |
| Verrou d'accès | `Api/Mail/src/Application/Services/Mailboxes/MailboxAccessGate.cs` | Verdict de l'opérateur, suspension (task-403) |
| Verdicts de l'opérateur | `Api/Mail/src/Application/Services/Mailboxes/OperatorVerdicts.cs` | Redis, 5 min, échec fermé (task-403) |
| Opérateur simulé du banc | `Api/Mail/src/Api/Testing/BenchOperatorRefusals.cs` | Révocation simulée (task-403) |
| Écran « accès suspendu » (mobile) | `Client/Mobile/src/app/mailbox/access-suspended/` | task-403 |
| Écran « accès suspendu » (weda2) | `Client/Angular/front/libs/mss/src/features/mailbox-access-suspended/` | task-403 |
| Faux Annuaire du banc | `Api/Mail/tests/mss.mail.e2e/FakeAnnuaire/` | Profil e2e (task-402) |
| Formulaire de rattachement (mobile) | `Client/Mobile/src/app/mailbox/shared/attach-mailbox-form.component.*` | Deux voies (task-402) |
| Formulaire de rattachement (weda2) | `Client/Angular/front/libs/mss/src/ui/attach-mailbox-form/` | Deux voies, présélection Weda (task-402) |
| Registre des boîtes | `Api/Mail/src/Infrastructure/Migrations/TenantDb/20261029120000_AddMailboxes.cs` | Une adresse, une base (task-404) |
| Personne dans la base de boîte | `Api/Mail/src/Infrastructure/Repositories/MailDb/BaseRepository.cs` | Boîte / personne (task-404) |
| Identité d'expéditeur de la boîte | `Api/Mail/src/Application/Services/Mailboxes/MailboxSenderIdentityService.cs` | Titulaire seul (task-404) |

---

## Annexe B — Inventaire fonctionnel (2026-10-29)

- Routes ajoutées : 3 (`GET /api/v1/account/mailboxes/directory` ; `POST|DELETE /api/v1/testing/operator-refusals`, banc seulement ; `GET|PUT /api/v1/account/mailboxes/current/sender-identity`).
- Migrations du registre : 2 (`AddMailboxRole`, `AddMailboxes`) ; base de boîte : 1 (`AddUserAuthenticationSubject`).
- Scénarios e2e : 4 ajoutés (E2E-MAILBOX-003, E2E-MAILBOX-004, E2E-MAILBOX-005, E2E-SHARED-001), 1 versionné (E2E-WEDA-001 v2).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | Règles |
|---|---|---|---|
| task-402 | done (PR en attente de merge) | Rattachement guidé par l'Annuaire Santé ; rôle titulaire, membre, délégataire ou « à requalifier » | RG-E020-03 ; RG-E020-06 (partiel) |
| task-403 | done (PR en attente de merge) | Accès à la base subordonné au verdict de l'opérateur ; hors-ligne du titulaire seul | RG-E020-04, RG-E020-05 ; RG-E020-06 (partiel) |
| task-404 | done (PR en attente de merge) | Une base par boîte ; données de la personne séparées ; identité d'expéditeur de la boîte | RG-E020-01, RG-E020-02 |
| task-405 | todo | Tout acte imputé à son auteur réel ; journal lisible de toute la boîte | RG-E020-06, RG-E020-07 |
| task-406 | todo | Mesure de charge d'une boîte partagée | — |
