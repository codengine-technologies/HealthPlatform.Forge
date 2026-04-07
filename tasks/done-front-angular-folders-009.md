# todo-front-angular-folders-009 — Angular : Dossiers personnalisés

**Dependencies**: todo-back-folders-007
**Feature**: tests/Features/Mss/DossiersPersonnalises.feature
**Repo**: client-angular (path: `Client/Angular`)
**Module**: Client/Angular/front/libs/mss

## Objectif

Implémenter la gestion des dossiers personnalisés et le déplacement d'emails dans Angular.

## Travail à réaliser

### 1. Service API
- Ajouter dans `MssApiService` :
  - `createFolder(dto)` → POST /api/v1/mail/folders
  - `renameFolder(path, dto)` → PUT /api/v1/mail/folders/{path}/rename
  - `deleteFolder(path)` → DELETE /api/v1/mail/folders/{path}
  - `moveEmail(folderPath, uid, dto)` → PUT /api/v1/mail/folders/{path}/emails/{uid}/move
  - `bulkMoveEmails(folderPath, dto)` → PUT /api/v1/mail/folders/{path}/emails/bulk/move

### 2. MailFolderListComponent
- Menu contextuel sur les dossiers custom (via DropdownMenu du design system)
- Actions : Nouveau, Renommer, Supprimer
- Masquer les actions sur les dossiers système

### 3. MailDetailComponent / MailListComponent
- Ajout d'une action "Déplacer vers" avec sélection de dossier
- Intégration dans les opérations bulk

### 4. MailStateService
- Méthode `moveMailFromList(uid)` pour retirer le mail de la liste courante après déplacement
- Mise à jour des compteurs de dossiers source/destination

## Definition of Done
- [x] Build passes (0 errors)
- [ ] Tests Vitest passent — à exécuter / écrire
- [x] CRUD dossiers fonctionnel (createFolder, renameFolder, deleteFolder in MssApiService + MailFolderListComponent)
- [x] Dossiers système protégés (context menu only on FolderType.Custom)
- [x] Déplacement unitaire et bulk fonctionnels (moveEmail, bulkMoveEmails in MssApiService + MailDetailComponent + MailListComponent)
- [x] State mis à jour après déplacement (compteurs, liste) (moveMailFromList, updateFolderCounts in MailStateService)
- [x] Standalone component, OnPush, Angular Signals
