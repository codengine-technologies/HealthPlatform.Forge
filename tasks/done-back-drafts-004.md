# todo-back-drafts-004 — Backend : Gestion des brouillons

**Dependencies**: aucune
**Feature**: tests/Features/Mss/Brouillons.feature
**Repo**: api-mail (path: `Api/Mail`)
**Touches**: dtos-mss (DTO contracts → run `/publish-dtos` first)
**Module**: Api/Mail

## Objectif

Implémenter les endpoints dédiés à la gestion des brouillons (save, update, list, delete) en s'appuyant sur le flag `IsDraft` existant et le dossier IMAP Drafts.

## Travail à réaliser

### 1. Service
- Créer `IDraftService` dans `Api/Mail/src/Application/Services/`
  - `SaveDraftAsync(SaveDraftDto)` → DraftDto (crée un mail avec IsDraft=true dans le dossier Drafts)
  - `UpdateDraftAsync(int uid, SaveDraftDto)` → DraftDto (met à jour un brouillon existant)
  - `GetDraftsAsync()` → List<DraftDto>
  - `GetDraftAsync(int uid)` → DraftDto (avec contenu complet pour reprise)
  - `DeleteDraftAsync(int uid)` → bool
  - `SendDraftAsync(int uid)` → envoie le brouillon puis le supprime du dossier Drafts
- Implémenter le service (utiliser IMAP APPEND pour sauvegarder dans le dossier Drafts)

### 2. DTOs
- Créer dans `Dtos/Mss/` :
  - `SaveDraftDto` (To[], Cc[], Bcc[], Subject, Body, Attachments[], InReplyTo?, References?)
  - `DraftDto` (Uid, Subject, To[], Cc[], Bcc[], Body, Attachments[], LastModifiedAt)

### 3. Controller
- Ajouter dans `MailController` ou créer `DraftController` :
  - `POST /api/v1/mail/drafts` — Sauvegarder un brouillon
  - `PUT /api/v1/mail/drafts/{uid}` — Mettre à jour un brouillon
  - `GET /api/v1/mail/drafts` — Lister les brouillons
  - `GET /api/v1/mail/drafts/{uid}` — Récupérer un brouillon (contenu complet)
  - `DELETE /api/v1/mail/drafts/{uid}` — Supprimer un brouillon
  - `POST /api/v1/mail/drafts/{uid}/send` — Envoyer un brouillon

### 4. Tests
- Tests unitaires du service
- Tests d'intégration des endpoints

## Definition of Done
- [x] Build passes (0 errors) — `Api/Mail` solution compiles cleanly
- [x] Tests unitaires passent (>=1 test par méthode) — `DraftServiceTests.cs`, `MailDraftTests.cs`
- [x] Tests d'intégration passent (>=1 test par endpoint) — `tests/mss.mail.api.tests/Controllers/V1/DraftControllerTests.cs` (16 tests, all 6 endpoints)
- [x] Un brouillon sauvegardé est récupérable avec tout son contenu — `IDraftService.GetDraftAsync`
- [x] La mise à jour d'un brouillon ne crée pas de doublon — `IDraftService.UpdateDraftAsync` (uid réutilisé)
- [x] L'envoi d'un brouillon le supprime du dossier Brouillons — `IDraftService.SendDraftAsync`
- [ ] Tous les scénarios Gherkin de Brouillons.feature couverts côté backend — bloqué tant qu'aucun framework BDD (Reqnroll/SpecFlow) n'est en place
