# Audit de détection de bugs — `api-mail` (2026-09-27)

> **Périmètre** : `Api/Mail/src` (Api, Application, Infrastructure, Domain — ~77 000 lignes hors migrations), plus les manifestes `DevOps/` quand un défaut en dépend.
> **Version auditée** : `develop` @ **`14d58398`** (le commit « FetchSingleEmail ne sert plus d'en-tête seule… », poussé pendant l'audit, est inclus).
> **Méthode** : analyse statique approfondie, en lecture seule, découpée en 7 zones (sessions IMAP/SMTP, opérations mail, persistance, ingestion/enrichissement, surface HTTP/identité, recherche/IA/flags, envoi/exports/contacts), plus une vérification dédiée des tasks 189, 191, 192 et 290. Chaque constat a été tracé dans le code (appelants et appelés). Les constats marqués **✔** ont en outre été **contre-vérifiés** ligne à ligne pendant la consolidation.
> **Ce que l'audit n'est pas** : aucun code n'a été exécuté, aucun tir, aucun test ajouté. Un constat « Probable » repose sur une hypothèse explicitée. Les défauts déjà suivis (tasks 189/191/192/290/319/320/325, audit sécurité E016 du 2026-09-16, suites de task-324) sont exclus, sauf mention contraire.
> **Suite prévue** : création des tasks dans un second temps — une proposition de regroupement figure en fin de document.

---

## 1. Synthèse

**66 constats** après dédoublonnage (plusieurs zones ont trouvé indépendamment les mêmes défauts — c'est signalé en « origine ») :

| Sévérité | Nombre | Dont contre-vérifiés ✔ |
|---|---|---|
| 🔴 Critique | 8 | 6 |
| 🟠 Majeur | 36 | 2 |
| 🟡 Mineur | 22 | — |

**Les dix à traiter d'abord**, par ordre de priorité proposé :

1. **AUD-01 ✔** — Le manifeste « Prod » désactive la validation des jetons : n'importe quel JWT non signé ouvre la boîte d'un praticien.
2. **AUD-02 ✔ / AUD-03** — La validation TLS MSSanté n'examine ni la chaîne ni le nom d'hôte, et la révocation n'est pas authentifiée : une interception réseau récupère le jeton PSC.
3. **AUD-04 ✔** — L'assistant IA peut livrer à un médecin l'action (nom et téléphone d'un patient) d'un autre médecin.
4. **AUD-06 ✔ / AUD-07** — Des pièces jointes partent silencieusement absentes (envoi depuis un brouillon, transfert mobile) avec un « envoyé » affiché.
5. **AUD-08 ✔** — Un envoi hors ligne qui échoue une fois est perdu sans avertissement ; les drapeaux et suppressions rejoués en échec sont effacés comme réussis.
6. **AUD-05 ✔** — Un document rattaché à la main à un patient n'apparaît dans aucun dossier.
7. **AUD-10 ✔** — Chaque message RabbitMQ transporte la chaîne de connexion Postgres, le jeton Keycloak et la session PSC du praticien.
8. **AUD-09** — Le correctif `14d58398` ouvre un chemin qui pose le marqueur « enrichi » sans garde d'échec technique : perte définitive de contenu clinique possible.
9. **AUD-20** — Les envois par brouillon et les envois hors ligne rejoués ne sont jamais archivés dans « Envoyés ».
10. **AUD-11 ✔ / AUD-16** — Archives IHE-XDM (CDA en clair) jamais supprimées par la synchro de fond ; panne hôte pendant l'extraction = documents perdus définitivement.

**Trois familles de causes** reviennent dans plus de la moitié des constats — elles méritent d'être traitées comme telles plutôt que constat par constat :

- **Deux chemins pour la même opération, qui ont divergé.** Envoi `sendmail` vs envoi de brouillon vs rejeu hors ligne (AUD-06, 07, 20, 63) ; ingestion de premier plan vs synchro de fond (AUD-11, 12, 13, 14, 15). Le chemin secondaire a manqué chaque correctif du principal.
- **Un état en mémoire de processus alors que l'API tourne en plusieurs réplicas** (AUD-18, 19) : conversations IA, brokers SSE, verrous de promotion.
- **Des échecs rendus comme des succès ou en 500 indistincts** (AUD-08, 23, 31, 38, 46) — contraire à la règle 12 et à « jamais de silence ».

---

## 2. Statut des tasks 189, 191, 192 et 290

Toutes ont été rejouées contre `develop` @ `14d58398`. **Point commun** : leurs chemins de fichiers sont périmés depuis task-299 (`142e0cd7`, 2026-09-13) — `src/Infrastructure/Repository/*` → `src/Infrastructure/Repositories/MailDb/*`, `Migrations/*` → `Migrations/MailDb/*`.

| Task | Verdict | Détail |
|---|---|---|
| **task-189** — surface HTTP | 🟡 **Partiellement d'actualité** | ✅ Toujours présents : purge destructive non gardée (`MailMaintenanceController.cs:115-128`), corps invalide → 500 (`Program.cs:66`, 12 actions listées plus bas), `GET` qui écrit (`SettingsController.cs:53-55`), `list-emails` non borné (`:41`/`:55`). ❌ **Corrigé** : les trois refus 403 hors RFC 7807 (tasks 303 et 308 — `WriteMailboxProblemAsync`). ⚠️ **Fait périmé** : les deux sites `embeddings/*` de la preuve 4 sont bornés depuis task-196 (`MedicalDocumentRepository.cs:80`). |
| **task-191** — intégrité de l'ingestion | 🟢 **Toujours d'actualité** | Code d'ingestion inchangé depuis task-183. Ordre d'écriture invalide (`MailRepository.cs:125/128/131`, `DetectSuppressionRequestAsync` `:4282-4329`) et dossiers patients dupliqués (`:334`, `:398`, `:471-482`, index `Ins` non unique) toujours présents. |
| **task-192** — recherche | 🟢 **Toujours d'actualité, périmètre sous-estimé** | Dédup sur l'UID (`SemanticSearchRepository.cs:579-580`), fenêtre ordonnée sur l'UID, jokers non échappés, pas de signal de troncature : présents. **Omis par la task** : la couche service déduplique aussi sur l'UID (`SemanticSearchService.cs:68`, `:396-413`, **`:583-584` `ToDictionary(r => r.Uid)` → 500 si on ne corrige que le dépôt**) ; le contrat `SearchResponseDto.Uids` ne porte que des UID — **la task doit lister `dtos-mss` et les fronts consommateurs**. Casse : `ApplyFieldFilters` utilise déjà `ILike` pour les noms patients — la phrase « le seul ILike porte sur le corps » est fausse. |
| **task-290** — flags éteints | 🟢 **Toujours d'actualité** | Saut silencieux (`AddNewMailConsumer.cs:43-48`), aucun compteur global, couverture mensongère (`MailRepository.cs:3587-3606`). **À signaler** : un rejeu partiel existe déjà (`EmbeddingReindexService`, task-196) mais ne couvre que les documents, ne vérifie pas `ai_pipeline` ; distinguer « enrichi IMAP » / « enrichi IA » dans la couverture **change `SyncCoverageDto` (dtos-mss)**. |

**Corrections à apporter aux task files avant `/start`** (ancres actuelles) :

- **task-189** : `Program.cs:66` (et non 57/65), fallback policy `:132-135` ; purge `:115-128` ; retirer les sites `:145`/`:185` de la preuve 4 ; `PatientsController` `Math.Clamp` `:375` ; **MTP étape 3** : la route `PUT …/patients/ins/{ins}/opposition` n'existe plus (`754a194f`) → `PUT /api/v1/patients/{patientId:guid}/opposition` ; preuve 5, DOD et MTP étape 6 à retirer (déjà corrigé) ou à réduire à un test de non-régression. Actions à corps nul (ancres) : `AiController.cs:49,102,124,148` ; `AiDiagnosticsController.cs:64,376` ; `SearchController.cs:71,139` ; `AiChatController.cs:62` ; `PatientsController.cs:300` **et `:145` (SearchPatients, non listée)** ; `MailController.cs:440,556` ; `SignatureController.cs:83` **et `:122` (UpdateAsync, non listée)** ; `MailTemplateController.cs:95,127`.
- **task-191** : `DetectSuppressionRequestAsync` `:4282-4329` (`CreateVersion7` `:4302`, requête `:4306`, estampille `:4327`) ; catch `PersistNewMailAsync` `:532` ; `BackgroundEnrichmentProcessor.cs:100` (catch par mail `:167`) ; `ImapService.cs:2209` (appel `AddNewMail` `:2170`).
- **task-192** : `:579-580` ; appelants `:455-519` ; `ApplyFieldFilters` `:666-707` ; ajouter la couche service et `dtos-mss` au périmètre.
- **task-290** : préciser que c'est `ProcessMedicalDocumentEmbeddingAsync` qui publie les contacts, et seulement si le mail porte des documents ; ajouter `dtos-mss` si la couverture doit distinguer l'IA.

---

## 3. Constats critiques 🔴

### AUD-01 ✔ — Le déploiement « Prod » du dépôt accepte des JWT non signés
- **Origine** : zone HTTP (A-1). **Catégorie** : sécurité. **Confiance** : Confirmé (code + manifeste) ; hypothèse : `DevOps/Prod` est déployé tel quel.
- **Où** : `src/Api/Program.cs:166-196` ; `DevOps/Prod/configmap.yaml:10` (idem Staging) ; `DevOps/Prod/api.yaml:20-21` (seule source d'environnement : le configmap) ; `src/Api/Authentication/TestBypassAuthenticationHandler.cs:41-45`.
- **Mécanisme** : `devPermissive = !hasKeycloak && !builder.Environment.IsProduction()`. En mode permissif : `ValidateLifetime`, `ValidateIssuerSigningKey`, `RequireSignedTokens` à `false`, `ValidateIssuer = false`, et `SignatureValidator` rend le jeton parsé tel quel. Or **`Keycloak:Authority` n'est défini nulle part** (appsettings, AppHost, `DevOps/**`) et le configmap « Prod » pose **`ASPNETCORE_ENVIRONMENT: "Staging"`** → `IsProduction()` est faux → mode permissif actif.
- **Scénario** : un JWT forgé, non signé, portant le `sub` Keycloak d'un praticien est accepté ; le middleware résout son compte au registre puis ses boîtes. Lecture de ses mails, patients, documents, journal d'audit. Aggravants : le blocage « Production » du bypass de test lit la variable brute, pas `IHostEnvironment` ; le limiteur de débit, partitionné par `sub`, se contourne en changeant de `sub`.
- **Direction** : mode permissif **opt-in explicite** (Development **et** drapeau de config) ; refus de démarrer sans Authority hors Development ; bypass aligné sur `IHostEnvironment` ; corriger l'environnement du configmap. **À vérifier en premier sur le cluster réel.**

### AUD-02 ✔ — La validation TLS MSSanté ignore la chaîne et le nom d'hôte
- **Origine** : zone sessions (S-1). **Catégorie** : sécurité. **Confiance** : Confirmé.
- **Où** : `src/Application/Helpers/TlsCertificateValidationSession.cs:78-107` ; `CertificateValidator.cs:27-41, 165-190` ; appelants `ImapClientTlsConfigurer.cs:38`, `SmtpConnectionFactory.cs:292`, `BackgroundImapService.cs:434`.
- **Mécanisme** : pour les domaines OAuth2 (`acceptWhenNoPolicyErrors: false`), le paramètre `SslPolicyErrors errors` n'est jamais refusé — `RemoteCertificateChainErrors` et `RemoteCertificateNameMismatch` passent. `ValidatePreHandshake` se limite à `IssuerName.Name?.ToUpper().Contains("IGC-SANTE")` et `NotAfter < UtcNow` (`NotBefore` non vérifié). Aucun `X509Chain`, aucun `.Verify(`, aucune vérification de nom d'hôte dans le dépôt.
- **Scénario** : sur un chemin réseau hostile (DNS, Wi-Fi de cabinet, proxy), un certificat auto-signé dont le DN émetteur contient « IGC-SANTE », ou un vrai certificat IGC-Santé d'un autre hôte, est accepté ; `AuthenticateAsync` envoie alors le **jeton PSC XOAUTH2** à l'attaquant, qui le rejoue sur le vrai serveur.
- **Direction** : refuser dès que `errors != None` avec une chaîne construite contre les ancres IGC-Santé embarquées (`CustomTrustStore`, `CustomRootTrust`) et le nom d'hôte vérifié.

### AUD-03 — Révocation OCSP/CRL non authentifiée ; cache OCSP clé sur le seul numéro de série
- **Origine** : zone sessions (S-2). **Catégorie** : sécurité. **Confiance** : Confirmé.
- **Où** : `OcspValidationService.cs:88-96, 149-172, 352-374` ; `CrlValidationService.cs:88-114, 247-254`.
- **Mécanisme** : la signature de la réponse OCSP (`BasicOcspResp`) n'est jamais vérifiée, ni celle de la CRL (`crl.Verify` absent) ; les URL OCSP/CRL et même l'émetteur (AIA) sont lus **dans le certificat présenté par le pair**. Le cache Redis `ocsp:validation:v2:{SerialNumber}` ne porte pas l'émetteur.
- **Scénario** : une réponse OCSP « good » forgée (HTTP en clair) fait accepter un certificat révoqué ; une CRL vide servie après blocage de l'OCSP contourne le fail-close ; combiné à AUD-02, un certificat forgé reprenant le numéro de série public du vrai serveur hérite de son « good » en cache — sans même toucher au réseau.
- **Direction** : vérifier les signatures contre l'émetteur de confiance (ou répondeur délégué EKU OCSPSigning) ; clé de cache = (hash émetteur, numéro de série).

### AUD-04 ✔ — L'assistant IA fuit l'action d'un praticien vers un autre
- **Origine** : zone recherche/IA (R-1). **Catégorie** : isolation / fuite de données de santé. **Confiance** : Confirmé.
- **Où** : `AiConversationService.cs:29` (`_actionFilter = new()`), `:79-87`, `:216-222` ; `Application/Filters/AiActionFunctionFilter.cs` ; `Api/Extensions/SemanticKernelExtensions.cs:81,133` (`AddSingleton<Kernel>`).
- **Mécanisme** : le service est Scoped, le `Kernel` Singleton. Chaque requête ajoute **son** filtre au Kernel partagé (`Contains` compare par référence → toujours faux) et ne le retire jamais. Semantic Kernel exécute tous les filtres à chaque appel de fonction : chacun écrit `_lastAction`. La requête A lit donc l'action produite par la fonction de B.
- **Scénario** : le médecin B demande « appelle le patient » ; le médecin A, dont le flux se termine au même moment sur le même pod, reçoit un événement `Action` avec le **nom et le téléphone du patient de B** (idem `compose_email` : objet et corps rédigés d'après les mails de B). Effets secondaires : liste de filtres qui grossit sans fin, mutation concurrente non protégée, `ArgumentException` (plugin en double) au premier appel concurrent sur un pod neuf.
- **Direction** : ne jamais muter le Kernel singleton — `kernel.Clone()` par requête, ou plugin + filtre enregistrés une fois et action capturée dans un état propre à la requête.

### AUD-05 ✔ — Un document rattaché à la main n'apparaît dans aucun dossier patient
- **Origine** : zone persistance (D-1). **Catégorie** : données. **Confiance** : Confirmé.
- **Où** : `PatientRepository.cs:851-866` (`AttachDocumentToPatientAsync`) et `:548-564` (`ActiveDocumentsForPatient`) ; `PatientsController.cs:215-238` ; `Api/Helpers/PatientHandleResolver.cs:37-48`.
- **Mécanisme** : le rattachement ne pose que `doc.PatientId` ; le dossier résout l'identifiant en INS puis filtre `md.Ins == ins`. Un CDA arrivé sans INS (cas nominal depuis task-176) garde `Ins = null`.
- **Scénario** : le praticien rattache le document « à intégrer » au patient X : il disparaît de la file (qui compte `PatientId == null`) **sans entrer dans la chronologie de X**. Tout le flux de rattachement manuel est sans effet visible ; le test existant ne vérifie que `PatientId`.
- **Direction** : filtrer le dossier par `PatientId` (préférable), ou recopier `Ins`/`PatientOid` au rattachement.

### AUD-06 ✔ — L'envoi d'un brouillon perd les pièces jointes, l'accusé de lecture, l'acquittement d'opposition et « annule et remplace »
- **Origine** : zones envoi (E-1, E-6). **Catégorie** : perte / conformité MSSanté. **Confiance** : Confirmé.
- **Où** : `DraftService.cs:319-341` (`BuildMailDto`), `:257-262` ; `Dtos/SaveDraftDto.cs` ; Blazor `NewMailComponent.razor:390, 461-468, 688-694, 1060-1065` ; mobile `mail-compose.component.ts:873-899`.
- **Mécanisme** : `BuildMailDto` ne copie ni `Attachments`, ni `RequestReadReceipt`, ni `OppositionAcknowledged`, ni le mode annule-et-remplace. Or l'autosave (30 s) crée un brouillon dans tous les cas, et « Envoyer » passe alors par `POST drafts/{id}/send`.
- **Scénario** : le médecin joint un compte rendu PDF et rédige plus de 30 s : **le confrère reçoit le message sans la pièce jointe**, l'interface affiche « envoyé ». Un destinataire patient sous opposition, acquitté par le médecin : 409 systématique, et le brouillon reste bloqué en `Sending`. Hors ligne : 502 au lieu de la mise en file.
- **Direction** : un seul chemin d'envoi — faire converger `SendDraftAsync` vers celui de `sendmail` (file hors ligne, archivage, annule-et-remplace, garde d'opposition), `SaveDraftDto` complété ; en attendant, refuser en 400 un brouillon à pièces jointes.

### AUD-07 — Le transfert mobile écarte en silence les pièces jointes reprises par référence
- **Origine** : zone envoi (E-2). **Catégorie** : perte. **Confiance** : Confirmé.
- **Où** : `SmtpService.cs:306-312` (`.Where(a => a?.Content != null …)`), `:396` ; mobile `mail-compose.component.ts:305-316, 1173-1180`.
- **Scénario** : transfert mobile d'un mail porteur d'un résultat PDF ou d'un `IHE_XDM.ZIP` : les pièces sont reprises « par référence » (`carriedOver: true`, sans contenu) ; le serveur les filtre, **le mail part sans elles** (et sans les en-têtes X-MSS-CODECDA / X-MSS-INS), réponse 200. Aucun chemin d'envoi ne résout `AttachmentDto.Guid`.
- **Direction** : résoudre le guid vers le contenu (base ou IMAP), ou refuser en 400 — jamais d'écart silencieux.

### AUD-08 ✔ — Actions hors ligne : un premier échec les perd, et les échecs de rejeu sont effacés comme des succès
- **Origine** : trois zones indépendamment (M-2, E-4, P-9). **Catégorie** : perte / gestion d'erreur. **Confiance** : Confirmé.
- **Où** : `PendingActionService.cs:150-184, 211-235, 367-390` ; `PendingActionRepository.cs:43-51, 162-176, 245-259` ; `MailController.cs:1341-1357`.
- **Mécanisme** : (1) `MarkAsFailedAsync` passe l'action à `Failed` ; `GetPendingActionsAsync` ne lit que `Pending` → **jamais rejouée** ; `RetryCount >= 3` est inatteignable ; `GetPendingEmailsAsync` la retire de la liste du praticien, `CleanupOldFailedActionsAsync` finit par la supprimer. (2) Pour drapeaux et suppressions, le `Result` en échec est ignoré puis l'action est supprimée comme réussie. (3) Une `OperationCanceledException` (arrêt de synchro, arrêt du pod) compte comme un échec. (4) Une ligne `Processing` interrompue par un crash reste bloquée à vie. (5) La mise en file n'exécute pas `CheckMailDtoForSending`.
- **Scénario** : un courrier médical mis en file hors ligne (« sera envoyé à la reconnexion ») rencontre un 503 SMTP au rejeu : **perdu, sans aucune notification**. Un acquittement biologique rejoué en échec : perdu.
- **Direction** : `ReleaseClaimAsync` (existe déjà) pour revenir à `Pending` avec compteur ; tester `Result.IsSuccess` dans chaque branche ; relancer sur annulation ; récupérer les `Processing` anciens ; exposer les envois en échec au praticien. **⚠️ Ne pas rejouer naïvement un `SendMail`** : `SmtpService` réduit aussi les échecs post-DATA à `Result.Error` (AUD-23) — il faut propager le stade de l'échec pour ne pas créer de doublon.

---

## 4. Constats majeurs 🟠

### Sécurité, confidentialité, isolation

**AUD-10 ✔ — Les messages RabbitMQ transportent les secrets du praticien et de la plateforme.** `Messages/AddNewMailMessage.cs:14`, `CreatePatientContactMessage.cs`, `CreatePractitionerContactMessage.cs` sérialisent le `UserContextInfo` complet (aucun `[JsonIgnore]`) : `ConnectionStringServer` et chaînes calculées (mot de passe Postgres), `KeycloakToken`, `Password` IMAP, `ProxySessionId` (permet d'obtenir un jeton PSC). Stockés dans des files durables, visibles en console d'admin, conservés dans les files `_error`. Le corps du mail y voyage aussi. Au passage, le spill d'audit Redis (`RedisAuditSpillStore.cs:75`) sérialise encore des chaînes de transport devenues inutiles (task-312). *Direction* : DTO de message minimal (email, RPPS, tenant, nom de base enregistré). *Confirmé.*

**AUD-14 — Le HTML ingéré par la synchro de fond est stocké sans assainissement** (`BackgroundEnrichmentProcessor.cs:258-266` vs `EmailBuildingService.cs:69`). Seule la lecture `GetEmailContentInternalAsync` ré-assainit ; le mode hors ligne (`OfflineMailDataProvider.cs:120-131`) et `FetchSingleEmailAsync` (export, résumés, IA) servent le brut → XSS stocké selon le rendu des fronts. *Confirmé côté serveur, exploitabilité Probable.*

**AUD-37 — La réponse brute du LLM de tagging (constats cliniques) part en Warning dans Seq/OTLP** (`EmailTaggingService.cs:296`). Sur JSON invalide, la réponse entière — qui cite par construction valeurs biologiques et diagnostics — est journalisée. Contraire à PGSSI-S et à task-265. *Direction* : longueur + type d'exception seulement. *Confirmé.*

**AUD-42 — SSRF par serveur IMAP/SMTP choisi par l'utilisateur** (`SettingsController.cs:53-66`, `MailServerDiscovery` — `FromUserConfig` prioritaire, `SmtpConnectionFactory.cs:60-61`, `ImapConnectionService.cs:87`). Tout utilisateur authentifié peut désigner `Host: "redis"` ou une IP interne ; api-mail s'y connecte à chaque synchro ou envoi, et y présente le jeton PSC en OAuth2. *Direction* : allowlist exploitant, refus des IP privées/loopback. *Probable* (vérifier que la fonction « serveur personnalisé » est bien exposée).

**AUD-21 — Le flux SSE ignore `?mailbox=` et suit toujours la boîte par défaut** (origine A-2, P-3 ; `UserContextEnricherMiddleware.cs:596-605, 722-730`, `MailEventsController.cs:71, 93-95`). `EventSource` ne pose pas d'en-tête ; le middleware sélectionne la boîte par défaut ; le contrôleur ne lit `?mailbox=` que si le contexte est vide (jamais). Après bascule vers la boîte B : notifications, progression et nouveaux mails de A, rien de B. Aucun client n'envoie d'ailleurs `?mailbox=`. *Confirmé.*

**AUD-34 — Dossier patient, opposition et messages patient clés sur le matricule seul** (origine D-5, P-12 ; `PatientRepository.cs:548-552, 644-651, 667-671`, `MailRepository.cs:471`, `PatientHandleResolver.cs:42-47`). task-183 crée deux fiches pour un même matricule dans deux domaines (NIA/NIR, OID test/production) ; l'affichage les fusionne, et `GetOppositionAsync` lit une fiche arbitraire (sans `ORDER BY`) — `PatientOppositionGuard` peut lire la fiche non opposée et laisser partir un envoi sans acquittement. Distinct de task-191 (doublons). *Confirmé, fréquence dépendante des données.*

**AUD-35 — La vue « tag » renvoie des mails d'autres dossiers qui partagent l'UID** (`MailRepository.cs:3161-3187` vs `:3125-3139`). La jointure `MailTags × Mails` filtre `uids.Contains(m.Uid)` sans `FolderPath == INBOX` ni génération ; les UID recommencent à 1 par dossier. Mails en trop, risque d'afficher le mauvais pour un UID, et contexte de l'assistant IA pouvant inclure le mail d'un autre patient. *Confirmé.*

### Perte ou corruption de données

**AUD-09 — Le repli IMAP de `FetchSingleEmailAsync` (introduit par `14d58398`) pose le marqueur d'enrichissement sans garde d'échec technique ni verrou** (`ImapService.cs:3253-3292, 4573-4576, 4613-4621`). Toute lecture `WithContent` d'un mail « en-têtes seuls » (liste des pièces jointes `ServiceImplementation.cs:178`, export PDF, résumé IA, annule-et-remplace) fetche, analyse le CDA et **écrit `MailContents`**. Si l'extraction XDM échoue pour une cause technique, le mail est marqué « analysé » sans documents — **écarté définitivement** de l'enrichissement. Pas de `HasTechnicalFailure` (contrairement à `ImapService.cs:2048` et `BackgroundEnrichmentProcessor.cs:130`), pas de `LockEnrichPersistAsync` (course possible avec une Phase B ; `IX_MailContents_MailId` non unique). *Direction* : réutiliser la garde task-293 et le verrou, ou réserver ce repli à une lecture sans écriture. *Confirmé pour le chemin ; critique si le déclencheur survient.*

**AUD-20 — Les envois par brouillon et les envois hors ligne rejoués ne sont jamais archivés dans « Envoyés »** (origine M-3, E-3). Seuls `MailController.cs:1383` et `:1510` appellent `sentArchiveDispatcher.Dispatch` ; `DraftService.cs:261-302` et `PendingActionService.cs:367-390` non, et `SmtpService` ne fait pas d'`APPEND`. Le médecin n'a aucune trace de ce qu'il a adressé — or le chemin brouillon est majoritaire (AUD-06). *Direction* : archivage dans un point de passage commun à tous les envois. *Confirmé.*

**AUD-11 ✔ — La synchro de fond ne supprime jamais les archives IHE-XDM extraites** (`BackgroundImapService.cs:223-297`, `BackgroundEnrichmentProcessor.cs:89-172`). `FetchedBackgroundMail` est `IDisposable` et possède ses archives, mais la liste `fetched` n'est jamais libérée (ni `using`, ni `finally`) — le défaut que task-228 a corrigé au premier plan (`ImapService.cs:1699-1717`). CDA et PDF en clair restent dans `%TEMP%/mss-ihe-xdm/` jusqu'au redémarrage : hors rétention et hors opposition, disque qui grossit. *Confirmé.*

**AUD-16 — Une panne hôte pendant l'extraction ou l'analyse XDM enregistre le mail sans documents, définitivement** (`CdaParsingService.cs:40-90`, `interop/…/XDM.cs:27-140`). `XDM.Load` attrape tout et rend `false` (disque plein à l'extraction, droits, zip supprimé entre écriture et lecture) → `HasMedicalDocuments = false` + ligne de contenu = jamais réanalysé. task-293 ne classe comme technique que l'écriture du zip. Aucune borne de taille ni de ratio (bombe zip saturant le répertoire partagé de tous les praticiens) ; le balayage ne purge pas les sous-répertoires `Root/{guid}/` ; avec plusieurs réplicas sur un hôte, le balayage au démarrage de l'un peut supprimer le zip d'un autre. *Confirmé sur le code.*

**AUD-13 — Le constructeur de DTO de la synchro de fond a divergé du premier plan** (`BackgroundEnrichmentProcessor.cs:234-292`, `BackgroundImapService.cs:230-233`). Pour tout mail ingéré en fond : accusé de lecture jamais détecté (en-têtes non récupérés, `ReadReceiptTo` vide) ; messages patient Mon Espace Santé sans document COURRIER ni lien patient (`IsFromPatient`, `PatientInsMatricule` non posés) ; aucune trace `MailReceive` ni `MedicalDocumentProcess` ; aucun rafraîchissement SSE (enrichi, remplacé, suppression). La ligne de contenu étant le marqueur « enrichi », ces manques sont définitifs. *Direction* : un seul `IEmailBuildingService` et une seule séquence post-persistance. *Confirmé.*

**AUD-15 — Un mail dont seul l'en-tête est en base n'est jamais enrichi par la synchro de fond** (`BackgroundSyncService.cs:384-403`, `MailRepository.cs:3567-3575`). `missingUids = IMAP − GetExistingUidsAsync` exclut les lignes « en-têtes seuls » laissées par le listing ; si l'enrichissement de premier plan échoue (503 task-293, navigation), le mail n'est repris que si le praticien le rouvre. La couverture reste sous 100 % alors que la synchro dit « terminée ». *Direction* : candidats = `IMAP − GetEnrichedUidsAsync`. *Confirmé.*

**AUD-12 — La synchro de fond perd `TenantId` et le nom de base enregistré** (`BackgroundSyncManager.cs:147-158`, `BackgroundEnrichmentProcessor.cs:178-192`, `AddNewMailConsumer.cs:161-168`, `Create*ContactConsumer`). Copie d'identité champ par champ au lieu de `CopyIdentityTo` (interdite par task-234). Les actions rejouées en début de synchro (acquittement biologique avec `PatientIns`, drapeaux, envoi) sont tracées sous `Guid.Empty` → **invisibles** dans l'écran d'audit du praticien (RLS) — le défaut exact de task-300 × 312. Latent : le nom de base est recalculé au lieu d'être lu du registre. *Confirmé pour le tenant.*

**AUD-17 — Une trace d'audit « poison » fait perdre tout son lot** (`AuditBackgroundService.cs:178-231, 280-304`, `PostgresAuditSink.cs:86-144`). Le lot est une transaction ; une trace invalide (`\0` dans un sujet, 22021) fait échouer toutes les autres, qui épuisent ensemble leurs 5 tentatives et sont supprimées (« LOST »). Les classes 42 (42501, 42P01 — rôle ou partition mal provisionnés) sont classées poison : une erreur de déploiement transitoire efface le journal en 5 passes. Contraire à l'invariant task-292. *Confirmé.*

**AUD-30 — Renommer un dossier laisse ses mails orphelins en base, et leurs documents masquent les nouveaux** (origine M-7, D-3 ; `FolderRepository.cs:437-464, 472-484`, `ImapFolderService.cs:363-378`). Seule la ligne `MailFolders` est réécrite ; `ReconcileFoldersAsync` supprime les dossiers disparus sans purger leurs mails (contrairement à `DeleteFolderByPathAsync`, task-179). Le dossier renommé est retéléchargé ; `FindExactDuplicateIdAsync` marque chaque nouveau document « doublon » de l'orphelin, que le dossier patient garde — actions IMAP impossibles, bandeaux « doublon », accusés biologiques perdus. Permanent. *Confirmé sur le code.*

**AUD-29 — Mettre un message à la Corbeille purge tous les `\Deleted` du dossier source** (`ImapService.cs:3815, 3929, 4074, 4118-4121`). `CloseAsync(true)` après le MOVE expurge aussi les messages qu'un autre client MSSanté a marqués sans les expurger — destruction irréversible sans copie en Corbeille. *Probable* (suppose des `\Deleted` résiduels d'un autre client). *Direction* : `CloseAsync(false)`, `UID EXPUNGE` ciblé.

**AUD-32 — `ReadReceiptSentAt` n'est jamais persisté : accusés de lecture renvoyés à chaque ouverture, audit « échec »** (`MailRepository.cs:2541-2555`, `MailDataContext.cs:104-136`, `MdnService.cs:58-95`). Faute de `HasColumnType`, EF mappe la propriété en `timestamptz` et Npgsql refuse la valeur `Kind=Unspecified` écrite par `NormalizeUtc` — le mécanisme que le contexte documente lui-même pour `SuppressionRequestedAt`. *Probable, élevée* (hypothèse : pas de commutateur Npgsql hors dépôt).

**AUD-36 — Écritures non atomiques après la première `SaveChanges` d'`AddNewMail` ; course sur les tags de catégorie** (`MailRepository.cs:511-572, 3459-3490, 4234-4260` ; parallélisme 4 de `BackgroundEnrichmentProcessor`). Deux mails introduisant la même catégorie : 23505 sur `IX_Tags_Code` non rattrapé → le mail est validé mais ni embedding, ni tags IA, ni contacts, ni notification — et jamais rejoué (déjà « enrichi »). Même classe : échec transitoire du chaînage de version → deux versions actives du même CDA. *Probable.*

**AUD-41 — Pièces jointes adressées par nom de fichier : deux homonymes deviennent inaccessibles ou dupliquées** (`ImapService.cs:3564, 3654-3669`, `MailController.cs:862-871`). Deux `resultat.pdf` dans un mail : la seconde ne se télécharge jamais ; le ZIP contient deux copies de la première. *Confirmé.*

**AUD-27 — Le cache `Mail.Email` fige la version d'avant l'analyse pendant 15 minutes** (`MailController.cs:649-667`, `ImapService.cs:3373-3459, 2140-2203`). Le contenu ouvert avant enrichissement est mis en cache et jamais évincé par l'enrichissement : réouverture sans documents CDA ni biologie alors que la liste affiche `HasMedicalDocuments`. *Confirmé côté serveur.*

**AUD-28 — « Aujourd'hui » suit l'horloge de l'hôte, pas la journée du praticien** (`ImapService.cs:1334, 1370, 1504-1505`, `OfflineMailDataProvider.cs:206-212, 242-246`). En ligne, `DateTime.Now.Date` sur un conteneur UTC : les mails reçus entre 00 h et 02 h (Paris, été) disparaissent des tuiles du jour — dont les résultats de labo nocturnes. Hors ligne, faux même sur un hôte à Paris (`SentDate` UTC comparé à `DateTime.Today` local, en-tête `Date` au lieu d'`INTERNALDATE`). *Confirmé sur le code* ; les 3 tests d'intégration « du jour » rouges la nuit passent par un autre chemin (`ImapFolderService.GetFolderToday*`, non branché sur un contrôleur).

**AUD-31 — Le compte rendu d'enrichissement annonce « analysés » des messages non persistés** (`ImapService.cs:1733-1735, 2057-2077, 2209-2217`). Exception base, annulation en Phase B ou corps illisible → comptés analysés, 200, aucune remise en file. *Confirmé.*

**AUD-18 — Notifications et promotion de mails gérées en mémoire de processus alors que l'API tourne en plusieurs réplicas** (origine P-11 ; `SseNotificationBroker`/`SseMailEventBroker`/`SseSyncProgressBroker`, `AddNewMailConsumer.cs:331`, `MailClientSessionManager.cs:456-473`, `MailRepository.UpdateExistingMailWithContentAsync:574-660`, `MailDataContext.cs:166` ; `DevOps/Prod/api.yaml:7` — 4 réplicas, Service sans affinité). (a) RabbitMQ livre `AddNewMailMessage` à un réplica quelconque et `NotifyTagsUpdatedAsync` ne publie que dans le broker local : ~(N−1)/N des tags d'urgence n'atteignent pas le flux SSE. (b) Deux appareils du même praticien promeuvent la même ligne « en-têtes seuls » sur deux pods (verrou local, index `MailContents.MailId` non unique) : contenu, documents et biologie dupliqués. *Probable* (hypothèse : plusieurs réplicas sans affinité). *Direction* : backplane Redis pub/sub pour les brokers SSE ; verrou distribué ou contrainte unique sur `MailContents(MailId)`.

**AUD-19 — Les conversations de l'assistant IA vivent en mémoire d'un seul pod** (origine R-2 ; `AiConversationStateManager.cs:12` — `ConcurrentDictionary` enregistré en Singleton, `Api/DependencyInjection.cs:133`). Conversation créée sur le pod 1, message envoyé au pod 2 : « Conversation non trouvée ou expirée » — environ 3 tentatives sur 4 avec 4 réplicas ; le résumé initial payé au fournisseur est perdu, et tout redémarrage efface les conversations. *Probable* (hypothèse : aucune affinité sur `/api/v1/ai` en amont). *Direction* : état des conversations dans Redis (TTL 8 h), ou affinité exigée et documentée.

### Cycle de vie, concurrence, gestion d'erreur

**AUD-23 — `SmtpService.SendMailAsync` transforme toute erreur en 500, y compris les refus typés** (`SmtpService.cs:50-52, 86-90, 93-157, 197-208`, `SmtpConnectionFactory.cs:243-276`). L'`UnavailableException` voulue (« règle 12 → 503 ») du rejeu 421 est avalée par le `catch (Exception)` englobant ; idem `UnauthorizedException` / `PscIdentityConflictException`, échec d'authentification SMTP, annulation client, mode hors ligne, erreurs de validation (« au moins un destinataire »). Tout sort en 500 avec une trace `ConnectionError`. *Confirmé.*

**AUD-24 — Le balayage dispose une session dont un envoi SMTP est en cours** (`MailClientSessionManager.cs:691-713, 747-753`, `MailClientSession.cs:627-663`). **Suite de task-324** : l'éviction ne teste que `ImapLock.Wait(0)`. Lien IMAP mort (motif `disconnected`) + envoi en cours sous `SmtpLock` → `DetachSmtpClient(quit: true)` sur le `SmtpClient` en plein `SendAsync`, puis `_smtpLock.Dispose()` détenu. Envoi en échec (500, AUD-23) alors que le DATA a pu être accepté → risque de double envoi si le praticien réessaie ; client authentifié adopté par une session disposée, jamais fermé. *Probable* (≈ 2 200 sessions dans cet état au tir du 16/09). *Direction* : prendre aussi `SmtpLock.Wait(0)`, ou n'évincer que la voie IMAP.

**AUD-25 — L'éviction dispose des sémaphores enrich/fetch encore détenus** (`MailClientSessionManager.cs:434-488, 549-621, 747-768`, `ImapService.cs:1653-1685, 2031-2081, 2787-2832`). La Phase B d'enrichissement tourne hors verrou IMAP (souvent juste après la mort du lien) ; l'éviction de la dernière session de l'e-mail dispose le sémaphore `enrich:` détenu ; une nouvelle requête en crée un neuf et lance un second persist concurrent (la course que task-079 visait) ; le `Release` de l'ancien détenteur libère le neuf → troisième entrant ou `SemaphoreFullException` en 500. *Probable.*

**AUD-26 — `BackgroundImapService` fuit un client IMAP connecté à chaque échec de connexion** (`BackgroundImapService.cs:415-466, 531-546, 572-582`). Le contrôle hors ligne arrive après TCP + TLS + OCSP ; en `Unauthorized` ou exception post-connexion, le client n'est ni confié au bail ni disposé (`Dispose` se contente de `_imapClient = null`). Chaque cycle raté garde une connexion TLS ouverte vers MSSanté, qui compte dans le plafond de ~10 connexions par utilisateur. *Confirmé.*

**AUD-44 — Fermeture de session bloquante sur le chemin logout, l'ordre diffusé et le balayage** (`MailClientSession.cs:640-663`). `_keepAliveTask.Wait(2 s)`, `client.Disconnect(true)` synchrone, `DisconnectAsync(true).GetAwaiter().GetResult()` ; aucun `Timeout` MailKit réglé (120 s par défaut). Une connexion à moitié ouverte bloque un thread de requête jusqu'à ~4 min et fige le balayage de toutes les sessions du pod. *Confirmé (chemin), Probable (durée).* Complète la suite déjà notée de task-324 (RemoveSession sous le détenteur).

**AUD-22 — Un `Client-Email` périmé bloque en 403 les routes de gestion des boîtes** (`UserContextEnricherMiddleware.cs:658-686`, `MailboxSelectionService.cs:48-65`, `MailboxCompatibility.cs:85-92`). La boîte courante devient `Detached` ou `AuthFailing` ; les routes `[MailboxNotRequired]` (lister, rattacher, détacher, définir par défaut, logout, statut) répondent 403 `PscMismatch` — le praticien ne peut plus basculer ni se déconnecter. Déclencheur réel côté mobile (`mailbox-management.page.ts:214-226`). *Confirmé serveur.*

**AUD-33 — Registre : revenir à une ancienne boîte par défaut, ou détacher la boîte par défaut, viole l'index unique partiel** (`PostgresTenantRegistryClient.cs:608-682, 898-912` ; index `ux_mss_accounts_one_default_per_account` absent du modèle EF). EF ordonne les deux `UPDATE` par clé (Guid v7 croissants) : si la boîte promue est plus ancienne, son `true` part d'abord → 23505 rendu « registre injoignable ». Défaut A → B fonctionne, B → A échoue. Tests sur InMemory, qui n'applique pas les index. *Probable.*

**AUD-38 — Une panne de recherche est rendue comme « aucun résultat »** (`SemanticSearchService.cs:110-121, 263-268, 283-297, 486-489, 544-547`). Postgres, pgvector ou fournisseur d'embeddings en panne → liste vide, 200, `TotalResults = 0` ; le mode hybride perd sa partie sémantique sans signal ; `OperationCanceledException` avalée. Le médecin conclut que le compte rendu n'existe pas. *Confirmé.*

**AUD-39 — Des filtres de recherche comptés « actifs » ne sont jamais appliqués ; la recherche « filtres seuls » rend alors tout le dossier sans limite** (`SemanticSearchService.cs:62-75, 137, 689-733`, `SemanticSearchRepository.cs:663-781`). `PatientFilters`, `IsAnswered`/`IsDraft`, dates documentaires et biologiques, et les booléens de contenu à `false` sont ignorés. Scénario Blazor : désactiver la pastille « PJ » envoie `HasAttachments = false` → filtre actif, non appliqué → `Take(int.MaxValue)` sur tout le dossier (ou toute la boîte). *Confirmé.*

**AUD-40 — La recherche plein texte ignore les vues par tag** (`SemanticSearchRepository.cs:395, 430, 467-471, 489-493, 512-517`). `FolderPath == "tag:Urgent"` ne correspond jamais : 0 résultat en plein texte depuis une vue tag, et le mode hybride perd la correspondance par mot-clé (les noms propres). *Confirmé.*

**AUD-43 — Accusés de lecture : en-tête de demande obsolète et adresse de réponse inexploitable** (`SmtpService.cs:355-358`, `EmailAddressHelper.cs:51-62`, `MdnService.cs:111`). Seul `Return-Receipt-To` est émis (ignoré par Outlook/Thunderbird) au lieu de `Disposition-Notification-To` (RFC 8098) ; à la réception, la valeur brute `"Dr X" <x@y.fr>` est passée comme adresse → MDN en échec ; le MDN n'est pas un `multipart/report`. *(a) Confirmé, (b) Probable.*

---

## 5. Constats mineurs 🟡

| ID | Constat | Où | Confiance |
|---|---|---|---|
| AUD-45 | La clé de session est redécoupée sur `LastIndexOf('_')` alors que `Client-Session-Id` peut contenir `_` : sémaphores fetch/enrich jamais récupérés pour ce praticien | `MailClientSessionManager.cs:762-768`, `UserContextEnricherMiddleware.cs:817-831` | Confirmé |
| AUD-46 | `ImapConnectionService` : annulation → `Result.Error` (500 au lieu du 499 central) ; hors ligne et certificat révoqué → 500 au lieu de 401/503 | `ImapConnectionService.cs:96-99, 132-136, 265-273` | Confirmé |
| AUD-47 | Archivage « Envoyés » rejoué de façon non idempotente : APPEND réussi puis `CloseAsync` en échec → jusqu'à 3 copies | `ImapService.cs:4389-4403`, `SentArchiveService.cs:52-88` | Confirmé |
| AUD-48 | Verrou d'envoi de brouillon (30 s) plus court qu'un envoi (attente SMTP jusqu'à 120 s), libéré sans jeton → double envoi possible, `Sending` bloqué sur exception | `DraftService.cs:29, 239, 306`, `DraftCacheRepository.cs:224, 241` | Probable |
| AUD-49 | Déplacements : seul `folder:uids` est invalidé (compteurs et listes du jour périmés 10 s) ; traces `MailMove` groupées sans sujet ni MessageId | `ImapFolderService.cs:523-527, 627-631, 647` | Confirmé |
| AUD-50 | Repli COPY sans UIDPLUS : la copie existe déjà quand `ExpungeAsync(uids)` lève → 503, et un nouvel essai duplique | `ImapMoveHelper.cs:79-89, 118-128` | Probable |
| AUD-51 | Pagination non déterministe (pas de critère de départage) : dossier patient et écran d'audit peuvent doubler ou omettre une ligne | `PatientRepository.cs:502-507`, `PostgresAuditReader.cs:111-114, 188-202` | Probable |
| AUD-52 | `MinSimilarity` appliqué deux fois : au-delà de 0,6, plus aucun résultat trouvé seulement par mot-clé | `SemanticSearchService.cs:314, 331, 621-641` | Confirmé |
| AUD-53 | `POST diagnostics/test-similarity` rend toujours 500 dès qu'un document existe (Guid déballé en `int`) et charge toute la boîte en mémoire | `AiDiagnosticsController.cs` (`BuildResultObject`) | Confirmé |
| AUD-54 | Consommation de tokens fausse : `promptTokens` toujours 0, résumés non comptés | `AiConversationService.cs:167` | Confirmé |
| AUD-55 | Texte libre du praticien (description de modèle, texte corrigé) journalisé en Information/Debug | `AiController.cs:70, 102`, `AiTextService.cs:100` | Confirmé |
| AUD-56 | Comparaison des tags IA sensible à la casse : `"urgent"` ne pose pas l'étiquette, sans compteur | `EmailTaggingService.cs:21-26, 265` | Probable |
| AUD-57 | Résumé IA d'un mail non enrichi jamais persisté, donc refacturé à chaque ouverture | `EmailSummaryService.cs:90-123`, `MailRepository.cs:2834-2848` | Probable |
| AUD-58 | Panne Redis : la garde de session de boîte s'ouvre (refus 409 non appliqué) et chaque requête écrit une trace `MailboxSessionOpened` | `SessionMailboxGuard.cs:153-158`, `UserContextEnricherMiddleware.cs:249-268` | Confirmé |
| AUD-59 | La politique de débit « sensitive » n'est appliquée nulle part : rattachement de boîte (connexion XOAUTH2 à chaque appel), IA, diagnostics | `RateLimitingSetup.cs:60-76` (aucun `[EnableRateLimiting]`) | Confirmé |
| AUD-60 | `POST account/mss-imap-test` échoue toujours (route exclue du middleware → jeton PSC vide) et journalise l'adresse en clair ; aucun client vivant ne l'appelle | `UserContextEnricherMiddleware.cs:67-70, 164-169`, `AccountController.cs:53-57, 111, 291-294` | Confirmé |
| AUD-61 | Noms de dossiers IMAP des praticiens en labels Prometheus sur `/metrics` anonyme (cardinalité non bornée, dossiers nominatifs possibles) | `MailProcessingMetrics.cs:551-563`, `BackgroundSyncService.cs:399-506`, `Program.cs:219` | Probable |
| AUD-62 | Noms d'entrées du ZIP de pièces jointes non assainis (zip-slip côté poste du médecin) | `AttachmentZipNameDisambiguator.cs`, `MailController.cs:868` | Confirmé serveur |
| AUD-63 | « Annule et remplace » hors ligne : mis en file comme un envoi simple, l'original n'est jamais marqué annulé (AMBU.MSS) | `MailController.cs:1440-1455` | Confirmé |
| AUD-64 | Annuaire FHIR : seul le premier `PractitionerRole` est gardé, les BAL MSSanté des autres lieux d'exercice sont perdues | `FhirBundleParser.cs:21-26, 124-130, 208` | Probable |
| AUD-65 | Synchro de fond : notification « nouveau mail » jamais émise (`isIncrementalSync` toujours faux) ; synchro « réussie » sur des lots injoignables (`EnrichmentOutcome` ignoré) ; `ex.Message` brut envoyé au client par SSE ; vecteur `null` écrasant un index valide à la relivraison ; double politique de retry MassTransit (jusqu'à ~16 appels LLM) | `BackgroundImapService.cs:205`, `BackgroundSyncService.cs:134, 503-504`, `MailRepository.cs:2872` | Confirmé |
| AUD-66 | Retours hors ProblemDetails restants (règle 12) : `GetMailsByTagAsync` pose un 500 sans corps ; `DraftController` `StatusCode(500)` nu ; `BadRequest(ModelState)` en `SerializableError` | `MailController.cs:1722-1729`, `DraftController.cs:153` | Confirmé |

---

## 6. Proposition de regroupement en tasks (pour le second temps)

Regroupement par **cause**, pas par fichier — chaque ligne est une US candidate. Les priorités sont une proposition.

| # | US candidate | Constats | Priorité proposée | Repos probables |
|---|---|---|---|---|
| 1 | Validation des jetons : mode permissif opt-in, configuration de déploiement corrigée | AUD-01 | **0 — immédiat, vérifier le cluster** | api-mail, devops (manuel) |
| 2 | TLS MSSanté : chaîne, nom d'hôte, révocation authentifiée | AUD-02, 03 | **1** | api-mail |
| 3 | Assistant IA : isolation des requêtes sur le Kernel partagé | AUD-04 | **1** | api-mail |
| 4 | Un seul chemin d'envoi (brouillon, hors ligne, transfert, annule-et-remplace, archivage) | AUD-06, 07, 20, 63, 48 | **1** | api-mail, dtos-mss, client-blazor, client-mobile |
| 5 | Actions hors ligne fiables (rejeu, échecs visibles, stade d'échec SMTP) | AUD-08, 23 | **1** | api-mail (+ fronts pour l'affichage des échecs) |
| 6 | Rattachement manuel visible + dossier patient clé sur l'identité et non le matricule | AUD-05, 34 | **1** | api-mail |
| 7 | Messages de bus sans secrets | AUD-10 | **1** | api-mail |
| 8 | Marqueur d'enrichissement : garde d'échec technique partout, panne hôte XDM, bornes d'archive | AUD-09, 16 | **2** | api-mail, interop-cda |
| 9 | Synchro de fond alignée sur le premier plan (constructeur unique, identité, nettoyage, candidats, sanitation) | AUD-11, 12, 13, 14, 15, 65 | **2** | api-mail |
| 10 | Cycle de vie des sessions (voie SMTP, sémaphores email, fuite de fond, fermeture bloquante, clé) | AUD-24, 25, 26, 44, 45, 46 | **2** | api-mail |
| 11 | Multi-réplicas : conversations IA et backplane SSE partagés, promotion concurrente | AUD-18, 19, 21 | **2** | api-mail, fronts (SSE `?mailbox=`) |
| 12 | Journal d'audit : lot poison, classes d'erreur | AUD-17, 58 | **2** | api-mail |
| 13 | Recherche : pannes visibles, filtres appliqués, vues tag, seuil unique | AUD-38, 39, 40, 52 (+ task-192) | **2** | api-mail (+ dtos-mss si task-192 fusionnée) |
| 14 | Opérations de dossiers : renommage, expunge, déplacements, UIDPLUS, vue tag | AUD-29, 30, 35, 49, 50 | **2** | api-mail |
| 15 | Accusés de lecture de bout en bout | AUD-32, 43 | **3** | api-mail |
| 16 | Fuites de données dans les logs et la télémétrie | AUD-37, 55, 60, 61 | **2** | api-mail |
| 17 | Durcissement divers (SSRF serveur utilisateur, rate-limit sensible, ZIP, pièces homonymes, fuseau du praticien, registre par défaut, caches) | AUD-22, 27, 28, 31, 33, 36, 41, 42, 47, 51, 53, 54, 56, 57, 59, 62, 64, 66 | **3** — à redécouper | api-mail |

---

## 7. Couverture — zones examinées et jugées saines

Pour que l'absence de constat soit lisible comme une vérification et non comme un trou :

- **Sessions** : `ImapSessionLockHandle` (sémaphore capturé, double libération protégée) ; `LockImapClientAsync` / `AcquireSmtpSlotAsync` (verrou rendu sur annulation post-acquisition) ; `EvictIdleSmtpConnection` ; voies keep-alive ; `MailClientSession.Dispose` idempotent ; `BackgroundImapConnectionRegistry` ; boucles de balayage résilientes ; `PscTokenProvider` (clé (sid proxy, sub KC), single-flight) ; `DeadSessionPolicy` (rejeu SMTP limité au 421 avant DATA).
- **Opérations mail** : UIDVALIDITY (purge, génération, fantômes) ; cache d'UIDs confronté à un STATUS frais ; rejeu sur session morte limité aux lectures ; balayage « aujourd'hui » (bornes de séquence) ; découpage Phase A/B ; idempotence des suppressions ; verrou distribué de fetch ; résolution SPECIAL-USE ; streaming des pièces jointes.
- **Persistance** : réclamation atomique des actions ; `UpsertFoldersAsync` ; `FindExactDuplicateIdAsync` déterministe ; courses gérées (utilisateur, tags IA, compte au registre) ; RLS lecteur d'audit ; provisionnement (verrou consultatif, `CREATE DATABASE` quoté, aucun SQL concaténé à une entrée utilisateur) ; nom de base SHA-256 ; migrations récentes sans opération fantôme.
- **Ingestion** : `BackgroundTaskQueue` ; réservation de synchro (bail, battement) ; ordre UIDVALIDITY ; chemin de premier plan (archives libérées, persistance sous verrou, classement task-293) ; protection zip-slip à l'extraction ; purge de rétention ; aucun INS dans les logs (task-184 respecté).
- **HTTP / identité** : fallback policy et ordre du pipeline ; `Client-Email` toujours validé au registre ; rattacher / détacher / défaut bornés au compte ; audit borné au tenant ; brokers SSE abonnés sur l'adresse résolue ; `UserContextInfo` scoped ; CORS en liste blanche ; `GlobalExceptionHandler` ; health checks agrégés ; téléchargement de pièce jointe sans traversée de chemin.
- **Recherche / IA / flags** : `FlagsmithFeatureFlagService` (single-flight, dernier état connu, replis déclarés) ; historique de recherche (INS retiré, TTL) ; cache des réglages invalidé à l'écriture ; `BoundedEmbeddingInvoker` ; timeout OpenAI ; `UntrustedPrompt` ; conversion distance/similarité ; isolation vectorielle par base praticien. `TextChunkingService` est du code mort.
- **Envoi / exports** : rejeu SMTP ; Bcc ; encodage des en-têtes (MimeKit) ; fils de discussion ; `SentArchiveService` (rejeu borné) ; exports EML/PDF/ZIP asynchrones, sans récupération distante ; `HtmlBodySanitizer` (allowlist correcte, appliqué au stockage de premier plan et à la lecture) ; contacts et vCard ; réglages en remplacement complet respectés par les clients ; signatures et modèles filtrés par utilisateur.

**Écartés comme spéculatifs** : HTML CDA issu du XSLT non repassé par l'assainisseur (le XSL HL7 embarque son propre nettoyage et des iframes `sandbox`) ; signature injectée uniquement en HTML ; `ImapConnectionManager` (fuit ses clients, mais code mort non enregistré).

---

*Audit réalisé en lecture seule sur `develop` @ `14d58398`. Les numéros de ligne sont ceux de cette révision.*
