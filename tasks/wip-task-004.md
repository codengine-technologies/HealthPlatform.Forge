# wip-task-004.md — Journal d'audit MSS

**Repos**: api-mail, client-blazor, client-angular, dtos-mss
**Dependencies**: aucune

## Objectif

Le systeme doit generer, persister et exposer des traces fonctionnelles pour toutes
les operations effectuees sur la BAL MSSante, conformement aux exigences ECO.4.1.1 et
ECO.4.1.2 du Ref#2 (§5.1). Un endpoint securise PSC permet de consulter ces traces,
et les deux frontends proposent une interface de consultation avec pagination et filtres.

## Modele `MssAuditTrace`

### Champs obligatoires (ECO.4.1.2)

| Champ | Type | Description |
|---|---|---|
| `Id` | int | Cle primaire |
| `UserId` | string | Identifiant de l'auteur authentifie (email PSC) |
| `UserSessionId` | string | Client-Session-Id de la session |
| `Timestamp` | DateTimeOffset | Horodatage local du poste |
| `ActionType` | enum | Type d'action (voir enum ci-dessous) |
| `ServerRequest` | string | Demande effectuee sur le serveur MSSante (commande IMAP/SMTP) |
| `ServerResponse` | string | Reponse du serveur (y compris en cas d'echec) |
| `Success` | bool | Succes ou echec de l'operation |
| `ErrorMessage` | string? | Detail de l'erreur si echec |
| `ErrorDetails` | string? | Stack trace complete de l'exception (backend only, non expose au front) |

### Champs contextuels mail

| Champ | Type | Description |
|---|---|---|
| `MailUid` | int? | UID IMAP du message concerne |
| `MailMessageId` | string? | Message-ID RFC 5322 |
| `FolderPath` | string? | Dossier IMAP (INBOX, Sent, etc.) |
| `Subject` | string? | Objet du message |
| `FromAddress` | string? | Adresse expediteur |
| `ToAddresses` | string? | Adresses destinataires (separees par `;`) |
| `HasAttachments` | bool? | Presence de pieces jointes |
| `AttachmentCount` | int? | Nombre de PJ |

### Champs contextuels patient/document medical

| Champ | Type | Description |
|---|---|---|
| `PatientIns` | string? | INS du patient concerne |
| `PatientName` | string? | Nom complet du patient |
| `DocumentId` | string? | Identifiant du document medical |
| `DocumentCategory` | string? | Categorie du document (biologie, CR, VSM, etc.) |
| `DocumentLoinc` | string? | Code LOINC |

### Champs techniques

| Champ | Type | Description |
|---|---|---|
| `CorrelationId` | string? | X-Correlation-Id pour tracabilite inter-services |
| `SourceIp` | string? | Adresse IP source |
| `UserAgent` | string? | User-Agent du client |
| `DurationMs` | long? | Duree de l'operation en millisecondes |

## Enum `AuditActionType`

| Valeur | Description |
|---|---|
| `ImapConnect` | Connexion IMAP |
| `ImapDisconnect` | Deconnexion IMAP |
| `SmtpConnect` | Connexion SMTP |
| `SmtpDisconnect` | Deconnexion SMTP |
| `MailSend` | Envoi d'un message |
| `MailReceive` | Reception/synchronisation |
| `MailRead` | Consultation d'un message |
| `MailDelete` | Suppression d'un message |
| `MailMove` | Deplacement entre dossiers |
| `MailFlagChange` | Changement de flag (lu/non lu, important, etc.) |
| `DraftSave` | Sauvegarde d'un brouillon |
| `DraftSend` | Envoi d'un brouillon |
| `DraftDelete` | Suppression d'un brouillon |
| `ReadReceiptSend` | Envoi d'un accuse de lecture MDN |
| `MedicalDocumentProcess` | Traitement/enrichissement d'un document medical |
| `ConnectionError` | Erreur de connexion |

## Endpoint API

### Liste paginee avec filtres

```
GET /api/v1/audit/traces
```

Securise par token PSC (comme le reste de l'API).

Parametres de requete :
- `page` (int, defaut 1)
- `pageSize` (int, defaut 50, max 200)
- `dateFrom` (DateTimeOffset?) — filtre date debut
- `dateTo` (DateTimeOffset?) — filtre date fin
- `actionType` (AuditActionType?) — filtre par type d'action
- `patientIns` (string?) — filtre par INS patient
- `mailUid` (int?) — filtre par UID mail
- `success` (bool?) — filtre succes/echec
- `search` (string?) — recherche texte sur sujet, adresse, erreur
- `sortBy` (string?) — colonne de tri
- `sortDirection` (string?) — asc/desc
- `mailMessageId` (string?) — filtre par Message-ID RFC 5322

Reponse : `{ items: MssAuditTraceDto[], totalCount, page, pageSize }`

### Detail d'une trace

```
GET /api/v1/audit/traces/{id}
```

Retourne la trace complete (ServerRequest et ServerResponse non tronques).

### DTO `MssAuditTraceDto`

Tous les champs du modele sauf `ErrorDetails` (non expose au frontend pour raisons de
securite). En mode liste, `ServerRequest` et `ServerResponse` sont tronques a 500
caracteres. L'endpoint de detail expose la trace complete.

## Interface frontend (Blazor + Angular)

Page `/audit` accessible depuis le menu parametres :

- **Tableau pagine** avec colonnes : Statut, Date/heure, Action, Sujet, Dossier, Utilisateur
- **Filtres** (panneau lateral gauche) :
  - Recherche libre (sujet, adresse, erreur)
  - Message-ID (champ texte)
  - Periode (Aujourd'hui, 3j, 7j, 30j, Personnalise avec date debut/fin)
  - Type d'action (dropdown)
  - Statut succes/echec (dropdown Tous / Succes / Erreur)
- **Bouton toggle "Erreurs"** dans le header de la liste : filtre rapide erreurs uniquement
- **Bouton "CSV"** dans le header de la liste : export des traces filtrees au format CSV (separateur `;`, encodage UTF-8 avec BOM)
- **Detail** : clic sur une ligne ouvre le detail complet (apercu mail + timeline)
- **Timeline** : affichage chronologique de toutes les traces pour un meme Message-ID avec :
  - Informations mail (ToAddresses, MailUid, MailMessageId)
  - Mise en evidence des operations lentes (duration > 3000ms) en orange
  - Message d'erreur et ServerResponse

## Decisions de securite

- `ErrorDetails` (stack trace) est persiste en base pour le diagnostic backend mais
  **n'est pas expose** dans le DTO ni dans les frontends. Seuls `ErrorMessage` et
  `ServerResponse` sont visibles cote frontend.

## Historique des changements

### Sprint initial — Audit core

- Entite `MssAuditTrace` avec tous les champs (migration FluentMigrator `20260410_CreateMssAuditTracesTable`)
- Enum `AuditActionType` (16 valeurs)
- Service `AuditService` (ecriture asynchrone via `Channel<MssAuditTrace>`)
- `AuditBackgroundService` (hosted service consommant le channel, persistance via `IAuditTraceRepository`)
- `AuditTraceRepository` avec filtrage, pagination, tri, recherche texte
- `AuditController` (GET /traces, GET /traces/{id})
- DTO `MssAuditTraceDto` (tous les champs sauf `ErrorDetails`)
- Tracage de toutes les operations : ImapConnect, ImapDisconnect, SmtpConnect, SmtpDisconnect, MailSend, MailReceive, MailRead, MailDelete, MailMove, MailFlagChange, DraftSave, DraftSend, DraftDelete, ReadReceiptSend, MedicalDocumentProcess, ConnectionError

### Iteration 2 — ErrorDetails + metadata mail

- Ajout colonne `ErrorDetails` (migration `20260413_AddErrorDetailsToAuditTracesMigration`)
- Population de `ErrorDetails` avec `ex.ToString()` sur toutes les traces en erreur :
  - `ImapConnectionService` (5 sites)
  - `SmtpConnectionFactory` (2 sites)
  - `SmtpService` (MailSend)
  - `ImapService` (MailDelete, bulk delete)
  - `ImapFolderService` (MailMove, bulk move)
  - `MdnService` (ReadReceiptSend)
- Enrichissement timeline frontend avec metadata mail (ToAddresses, MailUid, MailMessageId)
- Decision : ne pas exposer `ErrorDetails` au frontend (securite)

### Iteration 3 — Ameliorations UX

- **Error-only toggle** : bouton bascule dans le header de la liste (Blazor + Angular)
  - Active : force `Success=false` dans le filtre
  - Reset remet le toggle a inactif
- **Slow operation highlight** : duree affichee en orange gras dans la timeline quand `DurationMs > 3000`
  - Classe CSS `audit-timeline__duration--slow`
- **Export CSV** : bouton dans le header de la liste (Blazor + Angular)
  - Colonnes : Date, Action, Statut, Sujet, Dossier, Utilisateur, Destinataires, UIDL, Message-ID, Erreur, Duree (ms)
  - Separateur `;` (compatible Excel FR), encodage UTF-8 avec BOM
  - Blazor : via `IJSRuntime` et `window.downloadFile` (JS existant)
  - Angular : via `Blob` + `URL.createObjectURL` natif

## Fichiers modifies

### Backend (Api/Mail)

| Fichier | Changement |
|---|---|
| `Domain/Entities/MssAuditTrace.cs` | Entite audit + champ `ErrorDetails` |
| `Domain/Entities/AuditActionType.cs` | Enum 16 valeurs |
| `Infrastructure/Migrations/20260410_CreateMssAuditTracesTable.cs` | Table MssAuditTraces |
| `Infrastructure/Migrations/20260413_AddErrorDetailsToAuditTracesMigration.cs` | Colonne ErrorDetails |
| `Infrastructure/Repository/AuditTraceRepository.cs` | CRUD, filtrage, tri, pagination |
| `Application/Services/Implementation/AuditService.cs` | Service tracage via Channel |
| `Application/Services/Implementation/AuditBackgroundService.cs` | Hosted service persistence |
| `Application/Services/Interfaces/IAuditService.cs` | Interface |
| `Application/Services/Repository/IAuditTraceRepository.cs` | Interface repository |
| `Application/Extensions/ServiceCollectionExtensions.cs` | DI Channel + AuditService + BackgroundService |
| `Api/Controllers/V1/AuditController.cs` | Endpoints REST |
| `Api/DependencyInjection.cs` | AddHttpContextAccessor |
| `Application/Services/Implementation/ImapConnectionService.cs` | Traces IMAP connect/disconnect + ErrorDetails |
| `Application/Services/Implementation/SmtpConnectionFactory.cs` | Traces SMTP connect/disconnect + ErrorDetails |
| `Application/Services/Implementation/SmtpService.cs` | Trace MailSend + ErrorDetails |
| `Application/Services/Implementation/ImapService.cs` | Traces MailReceive, MailRead, MailDelete + ErrorDetails |
| `Application/Services/Implementation/ImapFolderService.cs` | Traces MailMove + ErrorDetails |
| `Application/Services/Implementation/EmailFlagService.cs` | Trace MailFlagChange |
| `Application/Services/Implementation/EmailBuildingService.cs` | Trace MedicalDocumentProcess |
| `Application/Services/Implementation/DraftService.cs` | Traces DraftSave, DraftSend, DraftDelete |
| `Application/Services/Implementation/MdnService.cs` | Trace ReadReceiptSend + ErrorDetails |

### DTOs (Dtos/Mss)

| Fichier | Changement |
|---|---|
| `MssAuditTraceDto.cs` | DTO complet (sans ErrorDetails) |
| `AuditTraceFilterDto.cs` | Filtre pagination + tri + recherche |

### Blazor (Client/Blazor)

| Fichier | Changement |
|---|---|
| `Modules/Mss/Plugin/Pages/Audit.razor` | Page audit complete : filtre, liste, timeline, detail, toggle erreurs, export CSV, highlight lenteur |
| `Modules/Mss/Plugin/Pages/Audit.razor.css` | Styles complets (toolbar, toggle, export, slow duration) |
| `Modules/Mss/Domain/Services/IAuditService.cs` | Interface client audit |
| `Modules/Mss/Infrastructure/Services/AuditService.cs` | Client HTTP appels API |

### Angular (Client/Angular)

| Fichier | Changement |
|---|---|
| `libs/mss/src/core/models/audit.model.ts` | Interfaces DTO, filter, enum, labels |
| `libs/mss/src/core/services/mss-api.service.ts` | Methode `getAuditTraces()` |
| `libs/mss/src/features/audit/mss-audit.component.ts` | Composant principal : state, API, export CSV |
| `libs/mss/src/features/audit/mss-audit.component.html` | Layout 3 colonnes |
| `libs/mss/src/features/audit/mss-audit.component.scss` | Styles layout |
| `libs/mss/src/features/audit/components/audit-filter/` | Composant filtre (signals, outputs) |
| `libs/mss/src/features/audit/components/audit-list/` | Composant liste (tableau, tri, pagination, toggle erreurs, export CSV) |
| `libs/mss/src/features/audit/components/audit-timeline/` | Composant timeline (metadata mail, slow highlight) |
| `libs/mss/src/features/audit/components/audit-detail/` | Composant detail trace |

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/JournalAuditMss.feature`

## Exigences Segur couvertes

- SC.MSS/CONF.17 (ECO.4.1.1) — Traces fonctionnelles pour tous les traitements sur BAL
- SC.MSS/CONF.18 (ECO.4.1.2) — Contenu obligatoire de chaque trace
- SC.MSS/UX.37 — Tracer et historiser tous les flux de transmissions MSSante

## References reglementaires

- Referentiel socle MSSante #2 v1.0.1 — §5.1 Gestion des traces
- ECO.4.1.1 — Traces fonctionnelles pour tous les traitements sur BAL
- ECO.4.1.2 — Contenu obligatoire (auteur, horodatage, type, demande serveur, reponse)
- Conservation recommandee : 6 mois

## Definition of Done

- [x] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [x] Entite `MssAuditTrace` creee avec tous les champs documentes ci-dessus
- [x] Enum `AuditActionType` avec toutes les valeurs listees
- [x] Toutes les operations tracees : envoi, reception, consultation, suppression, deplacement, flags, brouillons, MDN, enrichissement medical, connexion/deconnexion
- [x] Champs obligatoires ECO.4.1.2 renseignes (auteur, horodatage, type action, demande serveur, reponse serveur)
- [x] Champs contextuels mail renseignes (UID, MessageId, FolderPath, Subject, From, To)
- [x] Champs patient/document renseignes quand applicable (INS, DocumentId, LOINC, Category)
- [x] Endpoint `GET /api/v1/audit/traces` securise PSC avec pagination et filtres (date, actionType, patientIns, mailUid, success, search, mailMessageId, sortBy, sortDirection)
- [x] Endpoint `GET /api/v1/audit/traces/{id}` pour le detail complet
- [x] DTO `MssAuditTraceDto` avec troncature des champs longs en mode liste
- [x] Traces persistees en base (table dediee) avec duree de conservation configurable (defaut 6 mois)
- [x] Ecriture des traces asynchrone (Channel + BackgroundService, pas d'impact sur les performances)
- [x] Blazor : page `/audit` avec tableau pagine, filtres, detail au clic, timeline, toggle erreurs, export CSV, highlight lenteur
- [x] Angular : page `/audit` avec tableau pagine, filtres, detail au clic, timeline, toggle erreurs, export CSV, highlight lenteur
- [x] `ErrorDetails` persiste en base mais non expose au frontend (securite)
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Effectuer plusieurs operations : envoyer un message, ouvrir un message, supprimer un message, deplacer un message
- Ouvrir la page `/audit` sur Blazor
  - Verifier que les traces apparaissent dans le tableau pagine
  - Filtrer par date → verifier le filtrage
  - Filtrer par type d'action "Envoi" → verifier que seuls les envois apparaissent
  - Filtrer par Message-ID → verifier le filtrage
  - Cliquer sur une trace → verifier le detail complet + timeline + apercu mail
  - Cliquer sur le toggle "Erreurs" → verifier que seules les erreurs s'affichent
  - Cliquer sur "CSV" → verifier le telechargement du fichier CSV avec les bonnes colonnes
  - Verifier que les operations > 3s apparaissent en orange dans la timeline
- Repeter sur Angular
- Provoquer un echec de connexion (token invalide) → verifier que la trace d'erreur apparait avec ErrorMessage visible et ErrorDetails NON visible
- Appeler `GET /api/v1/audit/traces?dateFrom=...&dateTo=...` → verifier la reponse JSON paginee
- Verifier en base que les champs obligatoires ECO.4.1.2 sont renseignes sur chaque trace
- Verifier en base que `ErrorDetails` contient bien le stack trace pour les traces en erreur

## Branches
- `api-mail` (pushed) : feat/task-004-journal-audit-mss — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-004-journal-audit-mss
- `dtos-mss` (pushed) : feat/task-004-journal-audit-mss — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-004-journal-audit-mss
- `client-blazor` (pushed) : feat/task-004-journal-audit-mss — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-004-journal-audit-mss
- `client-angular` : managed manually by the human
