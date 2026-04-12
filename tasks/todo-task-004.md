# todo-task-004.md — Journal d'audit MSS

**Repos**: api-mail, client-blazor, client-angular
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

Reponse : `{ items: MssAuditTraceDto[], totalCount, page, pageSize }`

### Detail d'une trace

```
GET /api/v1/audit/traces/{id}
```

Retourne la trace complete (ServerRequest et ServerResponse non tronques).

### DTO `MssAuditTraceDto`

Tous les champs du modele. En mode liste, `ServerRequest` et `ServerResponse` sont
tronques a 500 caracteres. L'endpoint de detail expose la trace complete.

## Interface frontend (Blazor + Angular)

Page `/audit` accessible depuis le menu parametres :

- **Tableau pagine** avec colonnes : Date/heure, Action, Sujet, De/Vers, Patient, Statut
- **Filtres** :
  - Plage de dates (date debut / date fin)
  - Type d'action (dropdown multi-select)
  - INS patient (champ texte)
  - Succes/echec (toggle)
  - Recherche libre (sujet, adresse, erreur)
- **Detail** : clic sur une ligne ouvre le detail complet (demande serveur, reponse,
  metadata technique)

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

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Entite `MssAuditTrace` creee avec tous les champs documentes ci-dessus
- [ ] Enum `AuditActionType` avec toutes les valeurs listees
- [ ] Toutes les operations tracees : envoi, reception, consultation, suppression, deplacement, flags, brouillons, MDN, enrichissement medical, connexion/deconnexion
- [ ] Champs obligatoires ECO.4.1.2 renseignes (auteur, horodatage, type action, demande serveur, reponse serveur)
- [ ] Champs contextuels mail renseignes (UID, MessageId, FolderPath, Subject, From, To)
- [ ] Champs patient/document renseignes quand applicable (INS, DocumentId, LOINC, Category)
- [ ] Endpoint `GET /api/v1/audit/traces` securise PSC avec pagination et filtres (date, actionType, patientIns, mailUid, success, search)
- [ ] Endpoint `GET /api/v1/audit/traces/{id}` pour le detail complet
- [ ] DTO `MssAuditTraceDto` avec troncature des champs longs en mode liste
- [ ] Traces persistees en base (table dediee) avec duree de conservation configurable (defaut 6 mois)
- [ ] Ecriture des traces asynchrone (pas d'impact sur les performances)
- [ ] Blazor : page `/audit` avec tableau pagine, filtres (dates, action, INS, succes, recherche), detail au clic
- [ ] Angular : page `/audit` avec tableau pagine, filtres (dates, action, INS, succes, recherche), detail au clic
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Effectuer plusieurs operations : envoyer un message, ouvrir un message, supprimer un message, deplacer un message
- Ouvrir la page `/audit` sur Blazor
  - Verifier que les traces apparaissent dans le tableau pagine
  - Filtrer par date → verifier le filtrage
  - Filtrer par type d'action "Envoi" → verifier que seuls les envois apparaissent
  - Filtrer par INS patient → verifier le filtrage
  - Cliquer sur une trace → verifier le detail complet (demande/reponse serveur)
- Repeter sur Angular
- Provoquer un echec de connexion (token invalide) → verifier que la trace d'erreur apparait
- Appeler `GET /api/v1/audit/traces?dateFrom=...&dateTo=...` → verifier la reponse JSON paginee
- Verifier en base que les champs obligatoires ECO.4.1.2 sont renseignes sur chaque trace
