# todo-back-folders-007 — Backend : Dossiers IMAP personnalisés

**Dependencies**: aucune
**Feature**: tests/Features/Mss/DossiersPersonnalises.feature
**Repo**: api-mail (path: `Api/Mail`)
**Touches**: dtos-mss (DTO contracts → run `/publish-dtos` first)
**Module**: Api/Mail

## Objectif

Étendre le backend pour permettre la création, le renommage, la suppression de dossiers IMAP personnalisés et le déplacement d'emails entre dossiers.

## Travail à réaliser

### 1. Service
- Étendre `IImapFolderService` :
  - `CreateFolderAsync(string name, string? parentPath)` → FolderDto
  - `RenameFolderAsync(string path, string newName)` → FolderDto
  - `DeleteFolderAsync(string path)` → bool
  - `MoveEmailAsync(string sourceFolderPath, int uid, string targetFolderPath)` → int (new UID)
  - `BulkMoveEmailsAsync(string sourceFolderPath, int[] uids, string targetFolderPath)` → int[]

### 2. DTOs
- Créer dans `Dtos/Mss/` :
  - `CreateFolderDto` (Name, ParentPath?)
  - `RenameFolderDto` (NewName)
  - `MoveEmailDto` (TargetFolderPath)
  - `BulkMoveEmailsDto` (Uids[], TargetFolderPath)

### 3. Controller
- Ajouter dans `MailController` :
  - `POST /api/v1/mail/folders` — Créer un dossier
  - `PUT /api/v1/mail/folders/{path}/rename` — Renommer un dossier
  - `DELETE /api/v1/mail/folders/{path}` — Supprimer un dossier
  - `PUT /api/v1/mail/folders/{path}/emails/{uid}/move` — Déplacer un email
  - `PUT /api/v1/mail/folders/{path}/emails/bulk/move` — Déplacer en lot

### 4. Validation
- Interdire la suppression/renommage des dossiers système (Inbox, Sent, Drafts, Trash, Junk)
- Gérer la suppression d'un dossier non vide (déplacer les mails vers Trash d'abord)

### 5. Synchronisation
- Mettre à jour `MailFolder` en base après les opérations IMAP
- Mettre à jour les UIDs des mails déplacés dans la base locale

### 6. Tests
- Tests unitaires du service (CRUD dossiers + move)
- Tests d'intégration des endpoints
- Test de validation : dossier système non supprimable

## Definition of Done
- [x] Build passes (0 errors) — `Api/Mail` solution compiles cleanly
- [x] Tests unitaires passent (>=1 test par méthode) — 18 tests in `ImapFolderServiceTests.cs` cover all 5 methods
- [x] Tests d'intégration passent (>=1 test par endpoint) — `FoldersUseCaseTests.cs` (4 use-case tests, real IMAP via Skippable fixture)
- [x] Les dossiers système ne peuvent pas être supprimés ou renommés
- [x] Le déplacement met à jour les UIDs correctement
- [x] La suppression d'un dossier non vide déplace les mails vers la corbeille
- [ ] Tous les scénarios Gherkin de DossiersPersonnalises.feature couverts — bloqué tant qu'aucun framework BDD n'est en place
