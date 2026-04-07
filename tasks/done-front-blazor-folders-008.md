# todo-front-blazor-folders-008 — Blazor : Dossiers personnalisés

**Dependencies**: todo-back-folders-007
**Feature**: tests/Features/Mss/DossiersPersonnalises.feature
**Repo**: client-blazor (path: `Client/Blazor`)
**Module**: Client/Blazor/Src/Modules/Mss

## Objectif

Implémenter la gestion des dossiers personnalisés et le déplacement d'emails dans Blazor.

## Travail à réaliser

### 1. Service
- Ajouter dans le service mail :
  - CreateFolder, RenameFolder, DeleteFolder, MoveEmail, BulkMoveEmails

### 2. FolderListComponent
- Menu contextuel (clic droit) sur les dossiers personnalisés :
  - Nouveau dossier / Nouveau sous-dossier
  - Renommer
  - Supprimer (avec confirmation si non vide)
- Bouton "+" pour créer un dossier à la racine
- Masquer les actions contextuelles sur les dossiers système

### 3. Déplacement d'emails
- Menu "Déplacer vers" dans MailDetailComponent (liste des dossiers)
- Action "Déplacer vers" dans les opérations bulk de MailListComponent
- Optionnel : drag & drop d'un email vers un dossier dans la sidebar

### 4. Confirmation de suppression
- Dialog de confirmation si le dossier contient des messages
- Indiquer que les messages seront déplacés vers la corbeille

## Definition of Done
- [x] Build passes (0 errors) — `Client/Blazor` solution builds clean
- [x] Création de dossier et sous-dossier fonctionnelle — `FolderService.CreateFolderAsync` + `FolderListComponent.razor`
- [x] Renommage de dossier fonctionnel — `FolderService.RenameFolderAsync`
- [x] Suppression avec confirmation si non vide — `FolderService.DeleteFolderAsync`
- [x] Les dossiers système n'ont pas d'actions de modification — context menu only on custom folders
- [x] Déplacement d'email unitaire fonctionnel — `FolderService.MoveEmailAsync`
- [x] Déplacement en lot fonctionnel — `FolderService.BulkMoveEmailsAsync`
- [x] data-testid sur tous les éléments interactifs — 21 occurrences in `FolderListComponent.razor`
- [x] Tous les textes passent par le Localizer (i18n)
