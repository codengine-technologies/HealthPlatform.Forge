# E020 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E020-boite-partagee-une-base-par-boite-tout.md](E020-boite-partagee-une-base-par-boite-tout.md).
> **Dernière mise à jour** : 2026-10-30 (v1.11)

---

## Historique détaillé des changelogs

### v1.11 — Changement de boîte : rien de la boîte précédente ne reste — task-417

- **Task** : task-417, statut `done`. Run `/forge` 412-418, empilée sur task-412. PRs `client-mobile`
  #120 et `api-mail` #333 (catalogue), label `awaiting-human-merge`. `client-angular` : code non commité
  sur `feature/nova-mss-weda-integration`.
- **Défauts** (audit du 2026-10-30, m5 et m7, vérifiés sur le code) :
  - à la bascule, seuls quatre porteurs d'état étaient purgés côté mobile. La conversation IA, l'onglet
    Patients, les réglages, l'identité d'expéditeur et les widgets de l'accueil survivaient ;
  - un refus d'accès sur une requête épinglée à une autre boîte suspendait la boîte ouverte ;
  - le dossier « envoyés » était reconnu par la sous-chaîne `sent` (« Consent » compris).
- **Livré (mobile)** :
  - `UserSettingsService` rejoint `MAILBOX_SCOPED_STATES` (purge et garde d'`epoch`) ;
  - `DashboardRefreshService` recharge l'accueil au changement de génération, et
    `forCurrentMailbox()` ignore les réponses tardives des widgets ;
  - l'assistant se ferme et l'onglet Patients se recharge ;
  - l'identité d'expéditeur ignore la réponse d'une boîte quittée ;
  - l'intercepteur ne suspend plus sur une requête épinglée à une autre boîte ;
  - `isSentMail` passe par `FolderType.Sent`.
- **Livré (weda2)** :
  - intercepteur (requête épinglée) ;
  - `isSentFolder` (accusé de lecture, annule-et-remplace, en-tête) ;
  - flux de notifications rouvert après « Réessayer ».
- **Scénario** : **E2E-MAILBOX-007** v1 (mobile et angular requis), vu rouge sur mobile (attendu 0,
  reçu 1). weda2 recrée l'écran Patients à la navigation, et le test y est vert.
- **Qualité** :
  - Sonar non rejoué (catalogue YAML seul) ;
  - api-mail : 7264 tests, 0 échec ;
  - mobile : 1399/1399 ;
  - E2E vert : mobile 57 et Angular 67, parité verte.
- **Prévention** :
  - un test vide de sens trouvé en revue, maintenant vu rouge par mutation ;
  - le flaky Karma du sélecteur (`onAriaChanged`, défaut préexistant de la spec) est consigné en
    3ᵉ occurrence dans `conventions/angular.md`, et sa task de stabilisation est due ;
  - E2E-AI-001 en est à sa 3ᵉ occurrence.

### v1.10 — Poste partagé : la déconnexion ferme la boîte, l'assistant agit sur la boîte ouverte — task-412

- **Task** : task-412, statut `done`. Run `/forge` 412-418. PRs `client-mobile` #119 et `api-mail` #332
  (catalogue), label `awaiting-human-merge`. `client-angular` : specs e2e non commités sur
  `feature/nova-mss-weda-integration`.
- **Défauts** (audit du 2026-10-30, M1, M8 et m6, vérifiés sur le code) :
  - la déconnexion mobile laissait la boîte ouverte en mémoire : la personne suivante, connectée par
    e-CPS sans recharger la page, arrivait dans la boîte de la précédente ;
  - le flux de l'assistant mobile envoyait l'adresse du compte ;
  - la rédaction et l'assistant restaient au-dessus de « accès suspendu ».
- **Livré (mobile)** :
  - `LogoutService` vide `MailboxSessionService` et ferme les fenêtres ;
  - un `403 MAILBOX_NOT_ATTACHED` sur la boîte ouverte la vide et ramène au choix de boîte (second
    filet) ;
  - `Client-Email` = boîte ouverte sur le flux de l'assistant ;
  - `MailEventService.closeMailboxOverlays$`.
- **Scénarios** : **E2E-SESSION-004** et **E2E-AI-002** (mobile et angular requis), vus rouges sur le
  mobile sans correctif. weda2 est vert : il recharge toute l'application quand l'identité change
  (task-052).
- **Qualité** : Sonar non rejoué (catalogue YAML seul sur api-mail). Lint mobile vert. E2E vert, mobile
  56/56 et Angular 67/67, après correction d'un flaky propre au nouveau test weda2.
- **Prévention** : deux lignes « Trous du filet » (M1, M8) et une ligne au registre des flaky dans
  `conventions/e2e.md`.

### v1.9 — Le nom PSC du délégataire est lu sur la bonne route du proxy — task-416

- **Task** : task-416, statut `done`. `/review` APPROVED le 2026-10-30. PR `api-mail` #331
  (`awaiting-human-merge`).
- **Défaut** (constat humain du 2026-10-30) : un délégataire connecté avec Pro Santé Connect ne pouvait
  rien envoyer depuis la boîte déléguée (« Identité du délégataire indisponible »).
  - `PersonNameResolver` appelait `v1/auth/userinfo` sous une `BaseUrl` qui finit déjà par `/v1`, soit
    `/v1/v1/auth/userinfo` : un 404 de routage.
  - Le défaut venait de task-405. Il était masqué par les faux proxys des tests, qui répondaient sur
    tout chemin.
- **Livré** :
  - la route `auth/userinfo` ;
  - des faux proxys réalistes (`/v1` dans la `BaseUrl`, réponse uniquement sur le vrai chemin) ;
  - la preuve rouge par mutation : 6 tests d'intégration et 1 test unitaire.
- **Qualité** : SonarQube QG OK, 0 issue. E2E vert : mobile 54/54, Angular 65/65 au rejeu, après un arrêt
  du backend e2e inscrit au registre d'outillage.
- **Prévention** : `conventions/csharp.md` § `route-relative-sans-prefixe-de-base` et
  § `identifiant-aleatoire-sous-index-unique` (flaky `SeededThreadsAreCountableTests` corrigé au passage).

### v1.8 — Le cache patient par INS est cloisonné par boîte (audit C1) — task-410

- **Task** : task-410, statut `done`. `/review` APPROVED le 2026-10-30. PR `api-mail` #330
  (`awaiting-human-merge`). Sonar et e2e : bypass humain (`/start --no-sonar --no-e2e`), annoncé en
  tête de PR.
- **Défaut corrigé** (audit du 2026-10-30, finding critique C1) : la clé `patient:ins:{condensat}` ne
  nommait pas la boîte. Deux boîtes (deux bases) connaissant le même INS partageaient une entrée
  Redis. La seconde recevait, pendant le TTL de 5 min, la fiche de l'autre cabinet.
- **Livré** :
  - `RedisKeys.Patient.ByIns(adresse, ins)` → `patient:{adresse normalisée}:ins:{SHA-256}` ;
  - `PatientRepository` : pas de boîte connue → pas de cache ; invalidation de l'opposition sur la clé
    de la boîte.
- **Preuve** : `PatientCacheAcrossMailboxesEndToEndTests` (3), deux bases et le **vrai** cache sur Redis,
  vus rouges par mutation : clé sans la boîte, invalidation retirée.
- **Revue des clés Redis** : `patient:ins` était la seule clé de données de boîte sans la boîte (table
  dans le task file).
- **Prévention** : `conventions/csharp.md` § `cle-de-cache-de-boite`.

### v1.7 — Charge d'une boîte partagée mesurée — task-406

- **Task** : task-406, statut `done`. `/review` APPROVED le 2026-10-30. PR `api-mail` #329
  (`awaiting-human-merge`), qui ne contient que du code de test et le harnais.
- **Livré** :
  - `LoadTestRegistryProvisioner.ProvisionSharedBoxesAsync` ;
  - seed `--shared-box N` ;
  - k6 `SHARED_BOX=N`, où chaque personne garde son identité et son nom PSC.
- **Campagne** du 2026-10-30, `mixed`, N = 2, 5 et 10, référence contre boîte partagée, banc mail
  sur le cluster. Rapport : `Docs/audits/boite-partagee-charge-2026-10-30.md`.
  - Pool Postgres : à garder. Attente de connexion ≈ 0,1 ms, aucun pool épuisé.
  - CDA et IA : 1 par message quel que soit N (~124 contre N × ~122).
  - Sessions et verrous de la boîte : ouverture et envoi ×2 dès 5 personnes. L'acquisition SMTP
    passe de 52 à 380 ms, et l'attente des verrous de récupération atteint 520 s cumulées à 10.
- **Suites proposées** :
  - `MaxSessionsPerMailbox` par personne, déjà dans task-411 ;
  - lecture concurrente d'un même message, à instrumenter d'abord.
- **Outillage corrigé** : depuis task-404, `reset-state.sh`, `verify.sh` et `pg-*.sh` ne voyaient plus
  aucune base. Les noms sont désormais recalculés depuis les identités du banc.

### v1.6 — Le délégataire écrit pour le compte de la boîte (`Sender`) — task-407

- **Task** : task-407, statut `done`. `/review` APPROVED le 2026-10-30 (cycle `/start` manuel).
- **PRs** (label `awaiting-human-merge`, à merger dans cet ordre) : `dtos-mss` #56, `api-mail` #328,
  `client-mobile` #118. `client-angular` est en code-only, non commité sur
  `feature/nova-mss-weda-integration`.
- **dtos-mss** : `MailDto.Sender` (`MailAddressDto?`), publié en 571.0.0.
- **api-mail** :
  - `OnBehalfSenderResolver` et `OnBehalfSenderPolicy` (`Services/Mailboxes/OnBehalfSender.cs`). Les
    règles du référentiel draft vivent à un seul endroit ;
  - `SmtpService` : le `From` est contrôlé, le `Sender` posé, l'enveloppe `MAIL FROM` est la boîte et
    `RCPT TO` = To+Cc+Bcc. Le refus est tracé ;
  - `MdnService` suit la même règle ;
  - `GlobalExceptionHandler` : `OnBehalfSendRefusedException` → 400 (`MAIL_FROM_NOT_MAILBOX`,
    `DELEGATE_IDENTITY_UNAVAILABLE`) ;
  - réception : `EmailAddressHelper.ExtractSenderAddress`, colonnes `Mails.SenderAddress` et
    `SenderName` (migration MailDb `20261029140000_AddMailSenderColumns`), relues dans 4 projections.
- **Fronts** (mobile et weda2) : mention `mail-on-behalf-of`, `replyRecipient()` (`Reply-To`, sinon
  `From`, jamais `Sender`).
  - Mobile : le `From` et l'adresse « à soi » prennent la boîte ouverte, plus le compte. Défaut
    trouvé par E2E-SHARED-002 ;
  - mobile : un « Répondre » simple ignorait le `Reply-To`, corrigé.
- **Règle 1b** : `OnBehalfSendEndToEndTests` (11 tests, pile réelle, GreenMail et Dovecot). Les
  mutations M1 à M11 sont vues rouges.
- **Sonar** : CA2016 et CA1859 corrigées, S3925 en faux positif. Quality Gate OK, 0 issue, new
  coverage 96,4 %.
- **e2e** : E2E-SHARED-002 v1. Mobile 54 et weda2 65, verts. E2E-SETTINGS-003 a été stabilisé (la
  version est relue au serveur).
- **Dette** : 4 copies de la projection `Mail → MailDto`, à unifier dans une task dédiée.
- **À arbitrer** : AIPD (le nom et la BAL du délégataire sont communiqués aux destinataires), et le
  référentiel draft à revérifier sur la version finale.

### v1.5 — Rattachement : identité du praticien préremplie — task-409

- **Task** : task-409, statut `done`. `/review` APPROVED le 2026-10-29, run `/forge` `forge-20261029-408-409`.
  **Empilée sur task-408** : merger task-408 d'abord.
- **PRs** (label `awaiting-human-merge`) : `api-mail` #327, `client-mobile` #117 ; `client-angular` code-only,
  non commité sur `feature/nova-mss-weda-integration`.
- **api-mail** :
  - registre : migration `TenantDb/AddPractitionerProfile` (civilité, profession, spécialité, structure,
    adresse, `profile_fetched_at`, `prefill_done_at`) ;
  - annuaire : `GetPractitionerProfileAsync` (BAL + identité en une lecture), FHIR et LDAP ;
  - `MailboxPrefillService`, appelé par le middleware à la première requête sur une boîte : identité
    d'expéditeur (titulaire, ou membre sans titulaire) et « Signature annuaire », une seule fois, sans
    écrasement, tracées au nom de la personne ; `DirectorySignature` encode les valeurs de l'annuaire ;
  - requalification : identité enregistrée rafraîchie pour tous les rôles ;
  - seeds e2e et banc : rattachements posés « déjà préremplis ».
- **Fronts** (mobile, weda2) : accueil en un geste (BAL précochées, issue par ligne, « Réessayer »),
  confirmation lue sur la boîte rattachée (identifiant de session neuf), aperçu de signature assaini.
- **Règle 1b** : `MailboxPrefillIntegrationTests` (6, pile réelle), mutations P1 à P7 vues rouges ;
  `AttachInOneGesture_…` ; profil LDAP sur vrai OpenLDAP.
- **Sonar** : S3776 corrigée (`ApplyAttachmentAsync` extrait) ; QG OK, 0 issue, new coverage 96,9 % → 96,5 %.
- **e2e** : E2E-MAILBOX-003 v2 et E2E-MAILBOX-006 v1 ; verts pendant `/develop` (mobile 53, weda2 63 + 1 flaky)
  et rouges sous mutation ; `/e2e` **bypassé par l'humain** (2026-10-29).
- **À arbitrer** : attente de l'annuaire à la première requête (≤ 10 s) ; AIPD à compléter (données
  professionnelles publiques conservées au registre).

### v1.4 — Annuaire : source FHIR ou LDAP choisie dans appsettings.json — task-408

- **Task** : task-408, statut `done`. `/review` APPROVED le 2026-10-29, run `/forge` `forge-20261029-408-409`.
- **PRs** (label `awaiting-human-merge`) : `api-mail` #326, `client-mobile` #116 ; `client-angular` code-only,
  non commité sur `feature/nova-mss-weda-integration`.
- **api-mail** :
  - `AnnuaireOptions` (section `Annuaire`) : `Source` = `Fhir` | `Ldap`, validée au démarrage
    (`AnnuaireOptionsValidator`, `ValidateOnStart`) : source absente, inconnue ou section LDAP incomplète
    refusent le démarrage, la clé dans le message ;
  - `LdapAnnuaireSanteService` : décorateur qui ne remplace que `GetPractitionerMailboxesAsync`
    (filtre `(psidnat=8{RPPS})` échappé RFC 4515, lecture anonyme bornée). Recherche, spécialités et
    professions restent sur FHIR. Injoignable → `DIRECTORY_UNAVAILABLE`, comme FHIR ;
  - `DirectoryMailboxes` : traduction PER / ORG / CAB / APP / absent, partagée par FHIR et LDAP ;
  - `AnnuaireSourceStartupLogger` : source active journalisée au démarrage ;
  - `appsettings.json` : `Source = Fhir`, LDAP `partenaires.annuaire.sante.fr:389`, `ou=bal,o=mssante,c=fr` ;
    AppHost : `Ldap` sur le poste local, `Fhir` pour les profils e2e et loadtest ;
  - bibliothèque `Novell.Directory.Ldap.NETStandard` 4.0.0 (managée, aucune `libldap` dans l'image).
- **Fronts** (mobile, weda2) : spinner et texte pendant la lecture de « Mes boîtes » ; spinner dans le seul
  bouton cliqué, actions désactivées, un seul rattachement à la fois.
- **Règle 1b** : 4 tests d'intégration sur un vrai OpenLDAP (`OpenLdapFixture`), mutations M1 à M4 vues rouges.
- **Validation** : api-mail 202 / 699 / 1 306 / 3 865 / 1 059 (16 ignorés) ; mobile 1 348 ; weda2 12 projets verts.
- **Sonar** : QG OK, 0 issue, new coverage 96,8 % → 96,9 %.
- **e2e** : mobile 52 verts, weda2 62 verts + 1 flaky (E2E-COMPOSE-001, 7e occurrence), parité verte.
- **À arbitrer** : `appsettings.Development.json` exclu du dépôt (task-045, secrets locaux) : l'activation
  locale passe par l'AppHost. weda-dev : configmap `Annuaire__Source=Ldap` et port 389 sortant (`devops`).

### v1.3 — Tout acte imputé à son auteur réel — task-405

- **Task** : task-405, statut `done`. `/review` APPROVED le 2026-10-29, run `/forge` `forge-20261029-403-405`.
  **Empilée sur task-404**, elle-même sur task-403 : merger dans cet ordre.
- **PRs** (label `awaiting-human-merge`) : `dtos-mss` #55, `api-mail` #325, `client-mobile` #115 ;
  `client-angular` code-only, non commité sur `feature/nova-mss-weda-integration`.
- **dtos-mss** : 560.0.0 puis **561.0.0**.
  - `ActorDto` ;
  - `AuditActionType` 44 à 69, à valeurs explicites ;
  - `MssAuditTraceDto.Actor` / `IsSystemAct` / `MailboxAddress`, `AuditTraceFilterDto.ActorRpps` ;
  - `BiologyAckDto.CreatedBy`, `MailMedicalDocumentDto.ManualAttachedBy`.
- **api-mail** :
  - **Imputation** : `AuditService.Impute` remplit le compte, le RPPS, le nom, le prénom, le rôle et la
    boîte. Sans compte, la trace est un acte système (`is_system_act`).
  - **Nom** : `PersonNameResolver` lit la route `GET v1/auth/userinfo` du proxy PSC, une fois par
    session. Le nom est enregistré sur le rattachement (`person_first_name` / `person_last_name`),
    ce qui impute le titulaire hors ligne. Au banc, les en-têtes `Client-First-Name` /
    `Client-Last-Name` en tiennent lieu.
  - **Lecture par boîte** : migration `TenantDb/AddAuditActor`.
    - La RLS `audit_traces_mailbox_read` porte sur `mss.mailbox_id`, posé côté serveur.
    - Un déclencheur `SECURITY DEFINER` déduit la boîte d'une trace émise avant sa résolution.
    - Les traces existantes sont reprises par rattachement.
  - **Filtres serveur** : `ActionType`, `Search` (`ILIKE` échappé sur huit colonnes) et `ActorRpps`.
  - **Tout acte** : chacune des 158 actions porte `[Audited]` (filtre d'action), `[TracedInCode]` ou
    `[TraceExempt("raison")]`. `EveryControllerActionIsTracedTests` l'impose.
  - **Auteur réel** : migration `MailDb/AddActorColumns`, avec `BiologyAcks.CreatedBy*` et
    `MailMedicalDocuments.ManualAttachedBy*`.
- **client-mobile** (c354540) : auteur de l'acquittement et du rattachement, E2E-BIO-001 v2.
- **client-angular** (weda2, code-only) :
  - miroir `AuditActionType` 44 à 69 ;
  - colonne « Qui » et filtre par personne de l'écran Audit ;
  - auteurs de l'acquittement et du rattachement ;
  - `getAuditTraces` envoie `actorRpps` (défaut attrapé par E2E-AUDIT-001) ;
  - E2E-AUDIT-001 v1, E2E-BIO-001 v2.
- **Règle 1b** : `AuditImputationIntegrationTests` (6 tests, vrai journal) et deux cas d'usage
  Dovecot (suppression, étiquette, acquittement, rattachement par le délégataire, lus par le
  titulaire). Mutations M1 à M10 vues rouges.
- **Changement de règle** : `BLOQUANT_Deux_PS_sur_la_meme_adresse_…` est inversé. Toute personne
  rattachée lit tous les actes de la boîte (décision humaine du 2026-10-28).
- **Validation** : api-mail 202 / 3 831 (+ 9) / 699 / 1 306 / 1 055 (16 ignorés) ; mobile 1 343 ;
  weda2 1 369 + 2 653.
- **Sonar** : QG OK ; new coverage 97,0 % → 96,8 % ; 10 issues ramenées à 0 (S3776, S3604 ×3,
  S3459/S1144 ×4, SYSLIB1045, CA1859).
- **e2e** : mobile 52 verts, weda2 63 verts, parité verte.
- **À arbitrer** :
  - la civilité « Dr » n'est pas portée par `ActorDto` ;
  - relire un message déjà lu n'est pas retracé (exemption avec raison) ;
  - le filtre par personne est une saisie du RPPS ;
  - `Search` n'a pas d'index trigramme ;
  - l'AIPD est à mettre à jour.

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
| Imputation des actes | `Api/Mail/src/Application/Services/Implementation/AuditService.cs` | Personne réelle, acte système (task-405) |
| Nom de la personne | `Api/Mail/src/Application/Services/Psc/PersonNameResolver.cs` | `userinfo` du proxy PSC (task-405) |
| Marques d'audit | `Api/Mail/src/Api/Audit/AuditAttributes.cs` | `[Audited]`, `[TracedInCode]`, `[TraceExempt]` (task-405) |
| Source de l'annuaire | `Api/Mail/src/Application/Services/Implementation/AnnuaireSante/AnnuaireOptions.cs` | `Fhir` ou `Ldap`, validée au démarrage (task-408) |
| Annuaire MSSanté LDAP | `Api/Mail/src/Application/Services/Implementation/AnnuaireSante/LdapAnnuaireSanteService.cs` | BAL d'un RPPS, annuaire de test « partenaires » (task-408) |
| Préremplissage de la boîte | `Api/Mail/src/Application/Services/Mailboxes/MailboxPrefillService.cs` | Identité d'expéditeur et « Signature annuaire », une fois (task-409) |
| Confirmation du rattachement | `Client/Mobile/src/app/mailbox/shared/attach-confirmation.component.*`, `Client/Angular/front/libs/mss/src/ui/attach-confirmation/` | Lue sur la boîte rattachée (task-409) |
| Sender du délégataire | `Api/Mail/src/Application/Services/Mailboxes/OnBehalfSender.cs` | Règles ECO.1.2.9, adresse `no-reply-…` (task-407) |
| Mention « pour le compte de » | `mail-detail.component.*` (mobile et weda2) | `mail-on-behalf-of` (task-407) |

---

## Annexe B — Inventaire fonctionnel (2026-10-30)

- Routes ajoutées : 3 (`GET /api/v1/account/mailboxes/directory` ; `POST|DELETE /api/v1/testing/operator-refusals`, banc seulement ; `GET|PUT /api/v1/account/mailboxes/current/sender-identity`).
- Migrations du registre : 3 (`AddMailboxRole`, `AddMailboxes`, `AddAuditActor`) ; base de boîte : 3 (`AddUserAuthenticationSubject`, `AddActorColumns`, `AddMailSenderColumns`).
- Scénarios e2e : 9 ajoutés (E2E-MAILBOX-003, E2E-MAILBOX-004, E2E-MAILBOX-005, E2E-MAILBOX-007, E2E-SHARED-001, E2E-SHARED-002, E2E-AUDIT-001, E2E-SESSION-004, E2E-AI-002), 2 versionnés (E2E-WEDA-001 v2, E2E-BIO-001 v2).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | Règles |
|---|---|---|---|
| task-402 | archivée (mergée) | Rattachement guidé par l'Annuaire Santé ; rôle titulaire, membre, délégataire ou « à requalifier » | RG-E020-03 ; RG-E020-06 (partiel) |
| task-403 | archivée (mergée le 2026-10-29) | Accès à la base subordonné au verdict de l'opérateur ; hors-ligne du titulaire seul | RG-E020-04, RG-E020-05 ; RG-E020-06 (partiel) |
| task-404 | archivée (mergée le 2026-10-29) | Une base par boîte ; données de la personne séparées ; identité d'expéditeur de la boîte | RG-E020-01, RG-E020-02 |
| task-405 | archivée (mergée le 2026-10-29) | Tout acte imputé à son auteur réel ; journal lisible de toute la boîte | RG-E020-06, RG-E020-07 |
| task-406 | archivée (mergée le 2026-10-30) | Mesure de charge d'une boîte partagée : bornes du pool gardées, 1 traitement par message, sessions par boîte à corriger | RG-E020-01 |
| task-407 | archivée (mergée le 2026-10-30) | Le délégataire écrit pour le compte de la boîte (`Sender`, ECO.1.2.9 à 1.2.11) | RG-E020-08, RG-E020-06 |
| task-408 | archivée (mergée le 2026-10-29) | Source de l'annuaire FHIR ou LDAP choisie dans appsettings ; attente visible au rattachement | RG-E020-03 |
| task-409 | archivée (mergée le 2026-10-29) | Rattachement : identité du praticien préremplie, accueil en un geste | RG-E020-03, RG-E020-06 |
| task-410 | archivée (mergée le 2026-10-30) | Correctif d'audit C1 : le cache patient par INS nomme la boîte | RG-E020-01 |
| task-412 | done (PRs mobile #119, api-mail #332 en attente de merge) | Poste partagé : la déconnexion ferme la boîte ; l'assistant agit sur la boîte ouverte ; fenêtres fermées à la suspension | RG-E020-04, RG-E020-06 |
| task-417 | done (PRs mobile #120, api-mail #333 en attente de merge, empilées sur task-412) | Changement de boîte : rien de la précédente ne reste (assistant, patients, accueil, réglages, identité) ; requête épinglée sans suspension ; envoyés par type | RG-E020-01, RG-E020-04 |
| task-416 | archivée (mergée le 2026-10-30) | Le nom PSC du délégataire est lu sur la bonne route du proxy : l'envoi pour le compte de la boîte fonctionne | RG-E020-06, RG-E020-08 |
