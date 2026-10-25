# Délégation de BAL — revue du code contre les tasks 397 à 400 (2026-10-25)

> **Objet.** Confronter au code les tasks du lot délégation, puis lister tout ce qu'elles
> **manquent** ou **affirment à tort**. Les tasks sont task-397 (lecture directe, règle 14),
> task-398 (affichage), task-399 (envoi de la part de), task-400 (traçabilité), et task-389 / 390
> pour le HPRIM. Analyse de départ : [delegation-bal-mailiz-analyse-20261025.md](delegation-bal-mailiz-analyse-20261025.md).
>
> **Méthode.** Quatre revues indépendantes en lecture seule, sur `develop` (api-mail `369b083b`) :
> - chemins de lecture et d'écriture d'api-mail ;
> - envoi, brouillons et audit ;
> - les deux clients ;
> - persistances transverses et bancs.
>
> Un **prototype Dovecot** (image du banc `dovecot/dovecot:2.3.21`, avec espace `shared` et ACL) a
> été monté pour vérifier le banc. Les affirmations bloquantes ont été recontrôlées à la main, et
> le journal Seq du poste a été interrogé.
>
> **Gravité.** **B** = bloquant : viole la règle 14, abîme la BAL du délégant ou rend la task
> fausse. **M** = majeur : la DoD laisserait passer le défaut. **m** = mineur.

## 1. Synthèse

Les tasks ont la bonne intention, mais **plusieurs mécanismes manquent ou sont faux** :

1. **Journaux et télémétrie.** La règle 14 interdit d'écrire les noms de dossiers délégués dans les
   journaux, mais aucune task ne dit comment. **Constaté dans Seq aujourd'hui** : le chemin
   `shared/virginie…` et l'UID du message consulté sont dans le journal des requêtes et dans
   celui du flux SSE.
2. **Le point d'insertion de la lecture directe n'est pas celui indiqué.** La moitié des routes
   contourne `OfflineMailDataProvider` / `OnlineMailDataProvider` : contenu, pièces jointes,
   suppression, drapeaux, enrichissement, résumé IA, export.
3. **Des écritures échappent à la liste.** Marquer « lu » écrit une ligne `PendingActions` à
   chaque fois. S'y ajoutent l'IA (OpenAI, puis la base et Redis), l'historique de recherche, les
   accusés de lecture, les étiquettes, « Annuler et remplacer » et l'export.
4. **L'audit écrit bien plus que l'objet et les adresses** : titre et LOINC du document, nom de
   pièce jointe, destinataires dans `server_request`, texte d'exception. Le `Message-ID` est lu en
   base, et sera donc vide. Les traces existantes **ne peuvent pas être réécrites**, faute de
   droit `UPDATE`.
5. **La task-400 ne fonctionnerait pas.** La sécurité par ligne de PostgreSQL ne laisse lire que
   les traces du tenant de la session. Les adresses organisationnelles partagées feraient fuiter
   des traces, et aucun nom PSC n'est disponible.
6. **La purge est mal ordonnée et incomplète.**
   - Ordre : la purge implicite des dossiers disparus s'exécute avant elle, et efface le lien
     document → patient.
   - Portée : les tenants dormants ne sont jamais migrés ; plusieurs tables ne sont pas en
     cascade ; des messages en erreur restent dans RabbitMQ.
7. **Chemins et révocation.** `shared/<A>/INBOX` et une casse différente ouvrent la même boîte.
   Après un retrait de droits, une session déjà ouverte continue de lire le contenu.
8. **Le décodage n'est pas « en mémoire ».** Les archives IHE-XDM sont extraites sur disque.
9. **Côté weda2, deux fuites hors de la plateforme.**
   - Le panneau Weda envoie **automatiquement** l'identité des patients au dossier Weda dès
     l'ouverture du message.
   - « Importer dans Weda » classe le document dans le dossier patient du délégataire.

**Conséquence** : la task-397 double de volume. La section 6 propose de la scinder.

## 2. Ce qui est confirmé (bonnes nouvelles)

- **Le banc reproduit Mailiz.** Le prototype Dovecot donne exactement ce que nous observons chez
  Mailiz :
  - `shared/<A>` pour la réception, puis `Sent`, `Drafts`, `Trash` et les sous-dossiers ;
  - aucun attribut SPECIAL-USE ;
  - état lu propre à chaque utilisateur ;
  - NAMESPACE `(("" "/")) (("shared/" "/")) NIL` ;
  - un utilisateur sans droit reçoit `NO Mailbox doesn't exist`.

  Les ACL se posent et se retirent **en IMAP** (`SETACL` / `DELETEACL` depuis la session de A), sans
  `doveadm`. Cela marche partout, y compris là où `kubectl` est refusé.
- **La lecture sans écriture existe déjà.** `ImapService.FetchSingleEmailAsync` →
  `ReadEmailWithoutPersistingAsync` (`ImapService.cs:3261`, `:4649-4735`) construit le détail avec
  le CDA décodé, sans écrire. `ReadFolderAsync`, `SearchIntoAsync` et le `FETCH` des en-têtes
  (`:3213`) n'écrivent pas non plus.
- **Les clients ne stockent rien en local** : ni stockage local, ni IndexedDB, ni service worker,
  ni SDK de télémétrie. api-mail répond en `Cache-Control: no-store`.
- **La synchronisation en arrière-plan** ne descend qu'au premier niveau et saute les `\Noselect`.
  Elle n'atteint donc jamais `shared/<A>`, mais par chance : il faut un filtre explicite.
- **Les métriques sont sûres** : `FolderMetricCategory` range `shared/…` dans `other`.
- **L'envoi n'écrit pas le message** en base ni dans Redis. Les contacts ne naissent que des CDA
  des messages reçus.

## 3. Constats par thème

### 3.1 Journaux et télémétrie — task-397 (B)

- **Journal des requêtes** : `RequestLoggingMiddleware.cs:127-180` écrit le chemin en Information.
  `SensitiveRequestDataSanitizer.SanitizePath` (`Api/Telemetry/SensitiveRequestDataSanitizer.cs:92`),
  aussi utilisé pour l'attribut OTel `url.path`, ne masque que l'INS.
  - Le chemin porte `shared%2F<A>%2FDemo%2FBiologie2026`, l'UID, et le **nom de la pièce jointe**
    (`MailController.cs:746`).
  - **Constaté dans Seq le 2026-10-25** :
    `GET /api/v1/mail/folders/shared%2Fvirginie…/emails/content/4933`.
- **Une quarantaine de gabarits de journal** portent `{Folder}` en Information ou plus :
  - `MailController.cs:276, 315, 337, 451, 492, 606, 640, 689, 772-776` (nom de pièce jointe),
    `:1240, 1754, 1989, 2017, 2045, 2073` ;
  - `MailEventsController.cs:106` (constaté dans Seq) ;
  - `ImapService.cs:442, 569-583, 630, 900-905` (avec des UID) ;
  - `ImapFolderService.cs:320, 390, 438, 450, 531, 637` ;
  - `MailEnrichmentNotifier.cs:35-72`, `EnrichedMailPersistence.cs:194`, `MailExportController.cs:78, 112` ;
  - `UserContextEnricherMiddleware.cs:77, 91`, qui écrit le chemin **avec** les RPPS.
- **Étiquettes de verrou** : `ImapLockScope.cs:161-163, 234-236` journalise
  `GetAttachmentStream:{folder}:{uid}:{nom de pièce jointe}` et `MoveEmail:{src}->{tgt}`.
- **Attribut OTel** `email.folder` (`TelemetryExtensions.cs:26`) et **texte d'exception**
  (`GlobalExceptionHandler.cs:111-119`). Une réponse `NO` de Dovecot cite le nom du dossier.
- **Contenu clinique** : `CdaParsingService.cs:182` (titre du CDA, en Debug) et `:351` (libellés de
  biologie, en Warning).
- **Côté client** : `console.info` du chemin (weda2 `mail-events-stream.service.ts:168`).

→ Il faut **un masquage central** :
- un enrichisseur Serilog sur les propriétés, le message et le texte d'exception ;
- `SanitizePath` et l'attribut `url.query` ;
- l'attribut `email.folder` ;
- les étiquettes de verrou, sans jamais de nom de pièce jointe.

Tout ce qui est sous `shared/<A>/` devient `shared/<A>/…`, ou `shared/<empreinte>/…` si l'adresse
elle-même doit disparaître. La preuve est un test d'intégration qui capture les journaux et les
traces pendant un parcours délégué.

### 3.2 Lecture directe — task-397

- **Point d'insertion (B, task fausse)** : la fabrique de fournisseurs ne sert que la liste des
  dossiers, les dossiers, `today`, `unread`, `recent`, les en-têtes et les fils. Ces routes passent
  directement par `ImapService`, `ImapFolderService` ou `EmailFlagService` :
  - contenu (`MailController.cs:705`) ;
  - pièces jointes et zip (`:784, 870, 937`) ;
  - suppression (`:1247, 1428`) ;
  - drapeaux ;
  - enrichissement (`:511, 607`) ;
  - résumé IA (`EmailSummaryService.cs:62`) ;
  - export, PDF et impression (`MailExportController`) ;
  - opérations de dossier.

  L'aiguillage par chemin se fait donc au niveau de ces services, par exemple avec un décorateur.
- **Enrichissement (M)** : le mobile appelle `enrich/sync` (`MailController.cs:594`), pas
  `enrich/async`. Il faut sortir **au tout début** de `ImapService.EnrichEmailsAsync` (`:1646`),
  avant la réservation `MailPromotionClaim` (`:1663`) et les notifications. La route sync doit
  répondre 200, pas 503 (`:614`).
- **Détail (M)** : `GetEmailContentInternalAsync` (`:3401-3482`) lit la base et, à défaut, ne rend
  que le corps, **sans documents**. Le détail délégué doit passer par
  `ReadEmailWithoutPersistingAsync`, et **ignorer** les lignes déjà en base, sinon on servirait les
  copies d'avant la purge.
- **Verrou (M)** : `FetchSingleEmailAsync` garde le verrou `imap_session` (`:4678`) pendant le
  décodage CDA, la XSLT et le rendu PDF. Il faut décoder hors verrou, comme le fait
  l'enrichissement avec ses phases A et B (`:1667-1743`).
- **Statut d'enrichissement (M)** : `BuildHeaderOnlyMailDto` pose `EnrichmentStatus = Pending`
  (`EmailBuildingService.cs:134`). Le mobile attendra alors indéfiniment
  (`mail-header.component.ts:234`). Il faut un statut terminal pour un en-tête délégué.
- **Croisement avec la base du délégataire (m)** :
  - les compteurs de fil viennent de sa base (`OnlineMailDataProvider.cs:93-96`) ;
  - un document décodé en direct peut porter le même `DocumentId` que la copie du délégataire.

  Il faut un identifiant de document non résolvable, et aucun état de patient, de doublon ou de
  version.
- **Cache de la liste des dossiers (M)** : `folder:metadata:{u}` contient **dans sa valeur** les
  dossiers délégués et leurs compteurs. Soit on met en cache les seuls dossiers personnels et on
  interroge `shared/*` en direct, soit on relit toute l'arborescence. Les deux coûtent du temps de
  verrou sur la route la plus chargée.

### 3.3 Écritures et envois qui échappent à la task-397

| Route ou chemin | Effet sur `shared/` | Gravité |
|---|---|---|
| Lu / non lu / drapeau, unitaire et groupé → `FlagPropagationService.cs:101` | une ligne **`PendingActions`** à chaque geste (vérifié) | B |
| Branches hors ligne `MailController.cs:1003, 1128, 1171, 1214, 1256` | lu, drapeau et suppression mis en attente dans `PendingActions` | B |
| Résumé IA `…/emails/summary/{id}` → `EmailSummaryService.cs:62, 132-162`, et `AiDiagnosticsController` `recalculate-summary` | lecture IMAP, **envoi à OpenAI**, puis écriture en base (`ImapService.cs:4272`) et dans Redis `mail:summary-ai` (24 h). Le chemin « message sans contenu en base » (AUD-57) est exactement le cas délégué. | B |
| Conversation IA (`AiConversationService.cs:112-126, 453`) | chemin du dossier et échanges stockés dans Redis (`mss:ai:conv`) | B |
| `sendreadreceipt` / `declinereadreceipt` (`MailController.cs:1014, 1041`) | **accusé envoyé par SMTP depuis l'adresse du délégataire**, puis état écrit en base. La garde d'écriture ne l'attrape pas. | M |
| Étiquettes manuelles (`:1744, 1793`) | écrit `MailTags` | M |
| Annuler et remplacer (`:1503, 1526`, `MailCancellationService`) | résolu par la base, marque en base | M |
| Export PDF / EML / impression (`MailExportController`) | trace d'audit avec objet et adresses lus en direct | B |
| Zip de pièces jointes (`:854`), réécriture de pièce jointe (`ImapService.cs:3558, 3777`) | écriture `MailAttachments` si une ligne existe | M |
| Créer ou renommer un dossier (`ImapFolderService.cs:314, 381`), déplacements (`:541, 647`) | écrit et réindexe `MailFolders` et `Mails` | B |
| Réglages `DefaultFolder` (`UserSettingsDto.cs:84`) | chemin `shared/…` enregistré, et mis en cache Redis | M |
| Recherche (`SearchController.cs:123`) | historique `mss:search-history` écrit **avant** tout refus | M |
| `suppression-decision`, `detach-patient`, actions de biologie | pas de refus explicite (404 par chance) | m |

### 3.4 Audit — task-397, task-399, task-400

- **Champs écrits au-delà de la liste (B).** Pour l'action `MedicalDocumentProcess`
  (`EmailBuildingService.cs:104-121`) :
  - `document_category` (le titre), `document_loinc`, `document_id` ;
  - `patient_ins`, `patient_name`, `server_request`.

  Ailleurs :
  - `server_request` contient le **nom de la pièce jointe** (`MailController.cs:148`), les
    **destinataires** (`SmtpService.cs:120-134`) ou l'**empreinte de l'INS** (opposition) ;
  - `error_details = ex.ToString()` et `error_message` portent le texte brut ;
  - export et impression (`MailExportController.cs:149-162`), déplacement
    (`ImapFolderService.cs:545`), brouillons (`DraftService.cs:78…308`) et accusés
    (`MdnService.cs:217-224`) écrivent objet et adresses.

  → **Réduction centrale dans `AuditService.Trace`, par liste blanche** : action, auteur, dossier,
  UID, `Message-ID`. Elle s'applique dès que le dossier **contient** le préfixe partagé : un
  déplacement s'écrit `src -> tgt`, donc un test « commence par » ne suffit pas.
- **`Message-ID` (M)** : toutes les traces le lisent en base (`EmailFlagService.cs:79, 135, 145`,
  `ImapService.cs:3798, 4040`, `MailController.cs:86`). Il sera vide pour un message délégué ; il
  faut le lire en direct (enveloppe IMAP).
- **Tampon Redis (M)** : `RedisAuditSpillStore` (`mss:audit:spill`) stocke la trace **entière**.
  La réduction doit précéder le tampon, et l'exception d'audit de la règle 14 doit le couvrir.
- **Traces existantes (B)** : `audit_traces` n'a **aucun droit ni politique `UPDATE`**
  (`20260913120000_CreateTenantRegistry.cs:342-343, 388-405`, vérifié). « Remettre à vide l'objet »
  mettrait à jour 0 ligne, sans erreur : un vert qui ment. Réécrire un journal PGSSI-S est en
  outre une **décision humaine**.
- **task-400 : lecture du délégant impossible (B, task fausse)**. La politique
  `audit_traces_tenant_read` (FORCE ROW LEVEL SECURITY) filtre sur `tenant_id = mss.tenant_id`.
  « Ajouter ou BAL propriétaire = ma BAL » à la requête ne rendrait rien. Il faut une nouvelle
  politique de lecture, avec un second réglage de session posé côté serveur. Le test doit tourner
  sous un **rôle non superutilisateur**, puisque le superutilisateur contourne la sécurité par
  ligne.
- **task-400 : adresses organisationnelles (B)**. Plusieurs praticiens partagent une adresse avec
  des tenants distincts. « Lire par adresse propriétaire » montrerait à l'un les traces ordinaires
  de l'autre. Le prédicat doit être `owner_mailbox = moi AND owner_mailbox <> user_id`, en
  minuscules.
- **task-400 : aucun nom PSC disponible (B)**. `PscIdentity(Subject, Rpps)`, et `PscContextDto`
  ne porte aucun nom (vérifié). Il faut une source : psc-auth-proxy (dépôt manuel), claims PSC, ou
  annuaire par RPPS.
  - Le RPPS doit venir de `SessionPscIdentity.Rpps`, pas de `TransportMssRpps`, qui est le RPPS
    de la BAL.
- **task-400 : traces sans identité PSC (M)**. Les consommateurs du bus (`RestoreFromMessage`),
  la purge, les erreurs de connexion et le hors-ligne Keycloak n'en ont pas. « Renseigné pour
  toutes les traces » est donc impossible : prévoir des valeurs nulles.
- **task-400 : propriétaire d'un envoi (M)**. Un envoi n'a pas de dossier. Le propriétaire doit
  être posé par l'appelant (`From`, ou dossier cible de l'archivage).
- **task-400 : données du délégataire montrées au délégant (M)**. `PostgresAuditReader.Map`
  (`:247-280`) rend `UserSessionId`, `SourceIp`, `UserAgent`, `CorrelationId` et
  `ServerRequest/Response`. Il faut une liste blanche côté lecteur pour une trace lue hors de son
  tenant.
- **task-400, autres** :
  - la route détail `GET /audit/traces/{id}` est elle aussi limitée au tenant ;
  - les filtres `ActionType` et `Search` envoyés par weda2 sont **ignorés** par
    `PostgresAuditReader.ApplyFilters` (`:208-244`) ;
  - l'index sur une table partitionnée doit être construit en `ON ONLY`, puis `CONCURRENTLY` par
    partition, puis `ATTACH`, sinon il bloque l'écriture du journal. « Sans effet sur les partitions
    existantes » contredit tout index.
  - les nouveaux champs doivent traverser `MssAuditTrace` (sans `[JsonIgnore]`, pour le rejeu du
    tampon), `AuditTraceRecord`, `ToRecord`, `PostgresAuditSink.Columns`, `AuditTraceRow` et le
    mapping.
- **task-400, côté weda2 (M)** :
  - dédoublonnage côté client par UID seul (`mss-audit.component.ts:224, 242`) : le délégant et le
    délégataire agissent sur les **mêmes UID**, donc l'un masque l'autre ;
  - traduction du chemin `shared/<A>/X` vers le chemin propre du délégant, pour ouvrir le message
    et pour l'affichage ;
  - **l'export CSV existe déjà** (`:129`), avec objet et destinataires, alors que la task le dit
    hors périmètre ;
  - la chronologie par `Message-ID` ne doit pas montrer au délégataire les actes des autres
    délégataires.

### 3.5 Purge de l'existant — task-397

- **Ordre (B).** Dès que les dossiers délégués ne sont plus enregistrés, le prochain
  `GET /folders` déclenche `PurgeMailsOfFoldersNotOnServerAsync` (`ImapService.cs:504`,
  `FolderRepository.cs:476-494`). Il efface les messages `shared/%` en cascade, mais **pas** les
  patients ni les contacts. Ensuite, on ne peut plus savoir quels patients « ne viennent que de
  là ».
  → La purge explicite doit passer **avant**, ou la purge implicite doit être neutralisée tant
  qu'elle n'est pas faite.
- **Portée (B).** Les migrations de tenant sont **paresseuses** : au premier accès, puis ignorées
  24 h (`BaseRepository.cs:605-657`). Un délégataire qui ne revient jamais, le cas même que vise la
  règle 14, ne serait jamais purgé. Il faut un **exécutant qui parcourt tous les tenants du
  registre**.
- **Tables hors cascade (M)** :
  - `PendingActions` (dossier sans clé étrangère) ;
  - `UserSettings.DefaultFolder` ;
  - `MailPatients` ;
  - contacts **enrichis en place** (`PatientContactService.cs:39-44`), ce qui est
    **irréversible**, avec leurs groupes et `ContactMssAddresses`.
- **Effets de bord sur les documents propres (M).** Les clés `SET NULL` laissent des drapeaux
  orphelins : `SuppressionRequestedAt`, `Duplicate*`, et des bandeaux « remplacé » en cache.
- **Bus (M).** Les files `*_error` de RabbitMQ gardent le contenu (`MassTransitExtensions.cs:66-109`,
  `CreatePatientContactMessage` : INS, nom, téléphone, adresse). Des messages `create-*-contact`
  encore en vol recréeraient des contacts après la purge.
- **Redis (M)** : il faut lire les **valeurs**, pas seulement les clés.
  - Clés : `folder:metadata`, `folder:uids|status|query`, `mail:email|summary|summary-ai`,
    `sync:coverage`, `mss:sync:progress`, `mss:search-history`, `mss:ai:conv`, `usersettings:*`,
    `mss:audit:spill`.
  - En production, le fichier AOF garde les données jusqu'à sa prochaine réécriture.
- **Hors périmètre technique, à décider** : journaux Seq et OTLP déjà écrits, sauvegardes
  PostgreSQL.

### 3.6 Sécurité des chemins et révocation — task-397

- **Alias (B).** `shared/<A>/INBOX` ouvre la réception de A, et une **casse différente** ouvre la
  même boîte (prototype). Aucune normalisation (`ImapHelper.cs:40-48`). Un 409 fondé sur la chaîne
  se contourne donc. Règle sûre : n'accepter un chemin `shared/` que s'il figure **tel quel** dans
  le `LIST` courant, et comparer les propriétaires sans tenir compte de la casse.
- **Révocation non immédiate (M).** Après un `DELETEACL`, une session qui avait sélectionné
  `shared/<A>` lit toujours en-têtes **et corps**. Seule une nouvelle sélection est refusée.
  api-mail garde ses sessions 5 minutes et laisse parfois des dossiers ouverts
  (`ImapService.cs:1926, 2016`). Les caches servent aussi des données après révocation. La DoD ne
  teste que la liste des dossiers.
- **Le serveur laisse supprimer les dossiers système du délégant (M).** Avec le droit `x`,
  `DELETE "shared/<A>/Trash"` passe. Le 409 de l'API est la **seule** protection, ce qui confirme
  la règle.
- **Corrections de la task-397** :
  - il n'existe pas de route « déplacer un dossier » : renommer garde le parent
    (`ImapFolderService.cs:365`) ;
  - les refus actuels sont des `Result.Error`, donc des **500** : le 409 demande une nouvelle
    exception typée ;
  - `IsSystemFolder` lit `MailFolders`, qui n'aura plus de ligne délégué ;
  - il manque le refus de créer un dossier sous `shared` et sous les dossiers système du délégant,
    et celui d'un déplacement entre deux délégations.

### 3.7 Décodage sur disque — task-397, task-389, task-390 (M)

Les archives IHE-XDM sont **écrites et extraites sur disque** (`IheXdmScratch.cs:32`,
`interop.cda.parser/…/XDM.cs:70-84`), supprimées à la fin, et balayées au démarrage après un arrêt
brutal. « Décodé en mémoire » est donc **faux** tel qu'écrit. À décider : décodage sans fichier,
ou répertoire de travail borné accepté explicitement.

Hors délégation : `EmbeddedStyleHelper.cs:78-84` (interop) écrit des données CDA dans `%TEMP%`
sans jamais les supprimer. Il ne semble pas utilisé par api-mail.

### 3.8 Clients — task-398

- **weda2, panneau Weda (B, vérifié).** `weda-patient-panel.component.ts:133` (`effect()`) appelle
  `resolvePatient` **dès que les documents du message changent**. Ouvrir un message délégué
  envoie l'identité des patients de A au dossier Weda du délégataire. « Importer dans Weda » y
  **classe** le document. La task-398 ne masque que « à intégrer ».
- **IA (B)** : à masquer sur un message délégué, dans les deux clients :
  - Synthèse IA ;
  - « Poser une question à l'IA » ;
  - « Analyser avec l'IA » en lot ;
  - conversation IA.
- **À masquer aussi (M)** :
  - éditeur d'étiquettes ;
  - « Annuler et remplacer » (weda2) ;
  - panneau de rattachement manuel ;
  - bandeaux doublon, version et suppression ;
  - puce « bio à acquitter » de la réception.
- **Impression, export PDF / EML, téléchargement de pièces jointes (M)** : décision nécessaire. Le
  nom de fichier est construit à partir de l'**objet** (weda2 `mail-detail.component.ts:1494`).
- **Les clients déclenchent eux-mêmes des fuites (M)** :
  - ils ouvrent le flux SSE par dossier (`?folder=shared/…`) ;
  - ils appellent `enrichEmailsSync` sur les dossiers délégués ;
  - en mode conversation, `getThread` peut ouvrir la **copie du délégataire** d'un même
    `Message-ID`.

  → pas de SSE, pas d'enrichissement, mode liste forcé dans une BAL déléguée.
- **Mobile (M)** :
  - la déconnexion ne purge ni `MailStateService` ni `DocumentContentService`, qui garde le HTML
    des CDA décodés (`logout.service.ts:58-66`) ;
  - le passage hors ligne laisse la BAL déléguée affichée ;
  - plusieurs recherches de dossier ne parcourent que la racine : détection de la corbeille,
    restauration, compteurs (`mail-state.service.ts:137, 360`, `mail-detail.component.ts:345, 398`,
    `mail-list.component.ts:198`).
- **Chemins à corriger** :
  - `includes('sent')` aux **quatre** endroits : mobile `mail-detail.component.ts:747` ; weda2
    `read-receipt.util.ts:18`, `mail-detail.component.ts:1136` (garde d'« Annuler et
    remplacer »), `mail-header.component.ts:450` ;
  - le glisser-déposer weda2 doit tenir compte du rôle du dossier, pas seulement de la BAL ;
  - le dossier virtuel « Brouillons » apparaît dans les sélecteurs de déplacement du mobile ;
  - weda2 n'a **aucune** interface « Restaurer » ni « Supprimer définitivement » : c'est de
    l'interface nouvelle ;
  - après la suppression d'un sous-dossier délégué, l'écran revient à la propre réception
    (`type === 0`) au lieu de la réception déléguée.
- **Révocation (M)** : il manque un contrat d'erreur (`type` ProblemDetails) pour afficher « Cette
  boîte ne vous est plus déléguée », et non « dossier supprimé ». Une racine passée en `\Noselect`
  vaut retrait.
- **Mineurs** :
  - notification système de weda2 : écarter les messages dont le dossier est `shared/` ;
  - historique de navigation (route mobile `mail/:folderPath/:uid`) ;
  - images distantes en cache du navigateur ;
  - réglage d'ouverture : ignorer une valeur `shared/…` déjà enregistrée.

### 3.9 Envoi et brouillons — task-399

- **Archivage (B)** : `SentArchiveDispatcher`, `SentArchiveService` et `AppendToSentAsync` n'ont
  **aucun dossier cible**. Il faut l'ajouter dans les trois, et prévoir un mode « ne rien
  archiver » si Mailiz classe lui-même la copie.
- **Brouillons IMAP (B)** : `AppendToDraftsAsync` vise les Brouillons **de la session**, et
  `ReplaceDraftAsync` ajoute puis supprime, sans atomicité. Il manque :
  - un identifiant stable de brouillon (l'UID change à chaque enregistrement) ;
  - une route de relecture en rédaction ;
  - un anti-double-envoi sans clé Redis nommant le dossier.

  Des champs n'existent que dans le brouillon Redis : `BlockPatientReply`, `RequestReadReceipt`,
  `OppositionAcknowledged`, `Packaging` IHE-XDM, `CancelAndReplace*`.
- **Hypothèses fausses dans la task** :
  - la règle de la task-394 (« corps non modifié ») est **côté client** : elle se teste en
    composant et en e2e, pas en intégration api-mail ;
  - changer de BAL suppose des brouillons IMAP partout, alors que ceux de l'utilisateur sont dans
    Redis ;
  - on ne sait pas où va l'enregistrement automatique tant que le champ De est vide.
- **SMTP (M)** : poser `Sender` change `MAIL FROM` (MailKit). La caractérisation doit tester les
  deux. Le libellé vient des réglages **du délégataire** (`SmtpService.cs:272-297`). Le client
  mobile envoie `from.name` = nom du délégataire (`mail-compose.component.ts:1204-1209`).
- **Contrôle du `From` (M)** : il manque aussi dans la confirmation d'un envoi différé
  (`MailController.cs:1661`), et le 403 demande une exception typée nouvelle.
- **Identités d'envoi** : elles doivent venir d'un `LIST` en direct, jamais du cache Redis
  `folder:metadata`.
- **Opposition MSSanté (M, task fausse)** : elle est lue dans la base **du délégataire**
  (`PatientRepository.cs:765-772`). Une opposition enregistrée chez le délégant est invisible. À
  décider.
- **Accusés de lecture (M)** : il faut un **refus côté serveur** sur `shared/`, et ne pas exposer
  `ReadReceiptTo`. Sans ligne en base, `ReadReceiptSentAt` reste nul, et un appel direct enverrait
  autant d'accusés qu'on veut.
- **Répondre / transférer en « (moi) » (B, à décider)** : le contenu délégué cité et le CDA
  transféré vont dans le brouillon Redis du délégataire, puis dans ses Envoyés, puis dans sa base
  par l'enrichissement.
- **Autres** :
  - « Répondre à tous » doit être recalculé quand on change le De ;
  - révocation en cours de rédaction ;
  - variables de modèle `{{SenderEmail}}` et `{{SenderRPPS}}` (cette dernière est la partie
    locale de l'adresse, bug existant de weda2) ;
  - correction orthographique par IA ;
  - journaux Seq des destinataires (`SmtpService.cs:78, 119`, `MssanteHeaderService.cs:67, 155`).

### 3.10 Bancs — task-397, task-398, task-399

- **Un seul `dovecot.conf`, quatre consommateurs (M)** : tests d'intégration, banc de charge local,
  banc e2e, plus une copie à la main dans `DevOps/Staging`. Activer les ACL change les
  iso-conditions du banc de charge.
  → un **fragment de délégation** séparé, monté par l'intégration et l'e2e seulement.
- **À ajouter au banc** :
  - le dossier `Junk` de A, qui n'existe pas par défaut ;
  - des droits copiés sur le `MYRIGHTS` réel de Mailiz ;
  - une vérification que le dictionnaire `acl_shared_dict` tient avec des tests parallèles.
- **e2e** :
  - une sous-commande de délégation, accord et retrait, dans `tests/mss.mail.e2e` ;
  - une donnée de seed « bal-déléguée » ;
  - pour la task-400 : une seconde identité PSC avec son tenant, et le contournement
    d'authentification paramétré par identité ;
  - pour la task-399 : un puits SMTP qui reproduit le comportement Mailiz caractérisé.
- **Mesure de la task-397** : le banc Testcontainers n'est pas un banc de performance, et le banc
  k6 n'a pas de délégation. Il faut préciser où l'on mesure.

## 4. Décisions à prendre

1. **Réécrire les traces d'audit existantes** sur `shared/` (nouvelle politique `UPDATE`), ou les
   laisser jusqu'au terme de leur conservation ?
2. **Journaux Seq et OTLP déjà écrits**, et sauvegardes : purge ciblée, ou terme de leur
   conservation ?
3. **Impression, export et téléchargement** d'un message ou d'une pièce jointe délégués : permis
   comme geste explicite, comme dans le webmail Mailiz, ou masqués ?
4. **Répondre ou transférer un message délégué en « (moi) »** : forcer l'identité du délégant, ou
   accepter que la copie entre dans la BAL du délégataire ?
5. **Opposition MSSanté** lors d'un envoi de la part du délégant : limite acceptée, ou lecture de
   l'opposition chez le délégant (lecture inter-tenant) ?
6. **Nom de la personne dans l'audit** : annuaire par RPPS, claims PSC (évolution de
   psc-auth-proxy), ou RPPS seul ?
7. **Décodage des archives IHE-XDM** : sans fichier, ou répertoire de travail borné accepté ?
8. **Révocation** : resélectionner le dossier à chaque accès délégué (coût en verrou), ou accepter
   une fenêtre bornée, de l'ordre de la durée de vie d'une session (5 min) ?
9. **Découpage de la task-397**, qui a doublé (§6).

## 5. Questions techniques à mesurer chez Mailiz

Elles sont à ajouter à la caractérisation de la task-397 :
- alias `shared/<A>/INBOX` et casse du propriétaire ;
- révocation en cours de session ;
- `MYRIGHTS` réel : le délégataire a-t-il le droit `x` sur les dossiers système ?
- présence d'un `Junk` chez le délégant ;
- `MAIL FROM` délégant ou délégataire (pour la task-399).

## 6. Découpage proposé pour la task-397

La task-397 réunit désormais la garde, les journaux, l'audit, la purge, la lecture directe et la
sécurité des chemins. Proposition :

| Task | Contenu | Effet visible |
|---|---|---|
| **397 — Protéger** | Garde unique (base, Redis, bus, journaux, télémétrie). Réduction centrale de l'audit. Refus des routes à risque : IA, accusés, étiquettes, annuler et remplacer, recherche, réglages, actes cliniques. Corbeille du propriétaire, dossiers système, déplacements entre BAL, alias de chemins. Exécutant de purge sur tous les tenants, ordonné avant tout le reste. | La BAL déléguée reste visible, **sans contenu** tant que la 401 n'est pas livrée : la liste est vide ou indique « disponible prochainement ». |
| **401 — Lire en direct** | Fournisseur de lecture directe au niveau des services : en-têtes, détail, pièces jointes, compteurs. Décodage hors verrou et sans fichier selon la décision 7. Statut terminal. Révocation effective selon la décision 8. Mesure. | La BAL déléguée redevient lisible. |

Elle ordonne aussi la livraison : **397 → 401 → 398 / 400 → 399**, et les tasks 389 et 390 après la
401.

## 7. Décisions prises (humain, 2026-10-25) et report dans les tasks

| # | Décision | Report |
|---|---|---|
| 1 | Traces d'audit passées : **laissées en l'état**, la base de test a été purgée | task-397 (décision 11), task-400 (décision 4) |
| 2 | Journaux déjà écrits et sauvegardes : **pas de purge**, il n'y a pas d'existant hors formation | task-397 (décision 11) |
| 3 | Impression, export et téléchargement : **permis**, comme geste explicite, sans l'objet dans le nom de fichier | task-397 (décision 8), task-398 (décision 6) |
| 4 | Répondre ou transférer en « (moi) » : **permis, copie assumée** | task-399 (décision 6), règle 14 |
| 5 | Opposition MSSanté au nom du délégant : **limite acceptée et affichée** | task-399 (décision 7) |
| 6 | Nom de la personne : route **`userinfo` du proxy PSC**, appelée avec le cookie de session déjà détenu par api-mail | task-400 (décision 2) |
| 7 | Décodage IHE-XDM et HPRIM : **répertoire de travail transitoire accepté**, borné et documenté | task-397 (décision 4), task-389, task-390, règle 14 |
| 8 | Révocation : **fenêtre bornée** à la durée de vie d'une session (5 min) | task-397 (décision 9, règle H) |
| 9 | Découpage : **une seule task-397**, sans scission | task-397 (décision 10) |
| — | Purge de l'existant : **retirée** | task-397 (décision 11) |
| — | Aide IA à la rédaction au nom du délégant : **non**, par cohérence avec « pas d'IA » | task-399 (décision 8) |

La règle 14 de CLAUDE.md doit être amendée en conséquence : exceptions limitatives et masquage des
journaux. L'amendement est soumis à relecture avant le push.

### Complément du 2026-10-25 — cache du contenu décodé

- **Constat** : la 397 ne prévoyait aucun cache. Chaque ouverture, impression ou export d'un message
  délégué redécodait l'archive, et weda2 n'a aucun cache côté client.
- **Défaut** : le **PDF associé à un CDA** est dans l'archive IHE-XDM, pas en pièce MIME.
  `GetAttachmentAsync` ne le trouve qu'en base (`ImapService.cs:3508`), donc ce serait un **404**
  pour un message délégué.
- **Décision** : un **cache Redis**, puisqu'api-mail tourne sur plusieurs pods et qu'un cache en
  mémoire du processus ne convient pas.
  - Clé en empreinte, propre à la personne.
  - Expiration de 5 minutes au plus, taille bornée.
  - Invalidé à la suppression, au déplacement et à la révocation.
  - **Résidu AOF accepté tel quel.**
  - Reporté dans la task-397 (décisions 12 et 13, section J) et dans l'amendement de la règle 14.
