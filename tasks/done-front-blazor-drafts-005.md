# todo-front-blazor-drafts-005 — Blazor : Gestion des brouillons

**Dependencies**: todo-back-drafts-004
**Feature**: tests/Features/Mss/Brouillons.feature
**Repo**: client-blazor (path: `Client/Blazor`)
**Module**: Client/Blazor/Src/Modules/Mss

## Objectif

Implémenter la sauvegarde automatique et la reprise des brouillons dans l'application Blazor.

## Travail à réaliser

### 1. Service
- Ajouter les appels API brouillons dans le service existant ou créer `IDraftService` :
  - SaveDraft, UpdateDraft, GetDrafts, GetDraft, DeleteDraft, SendDraft

### 2. Auto-save dans NewMailComponent
- Ajouter un timer (30 secondes) qui sauvegarde automatiquement le brouillon en cours
- Indicateur visuel "Brouillon sauvegardé" avec timestamp
- Lors de la fermeture du composeur avec du contenu non envoyé, proposer de sauvegarder

### 3. Reprise de brouillon
- Clic sur un brouillon dans FolderList/MailList → ouvre NewMailComponent pré-rempli
- Pré-remplir : destinataires (To/Cc/Bcc), sujet, body, pièces jointes
- Le bouton Envoyer utilise l'endpoint SendDraft (envoie + supprime le brouillon)

### 4. Liste des brouillons
- Le dossier Brouillons affiche la date de dernière modification
- Suppression d'un brouillon depuis la liste

## Definition of Done
- [x] Build passes (0 errors) — Domain and Application projects build clean; Plugin has pre-existing FolderListComponent errors only
- [x] L'auto-save se déclenche après 30 secondes d'inactivité de sauvegarde — Timer 30s in NewMailComponent
- [x] L'indicateur "Brouillon sauvegardé" s'affiche après chaque sauvegarde — draft-saved-indicator with timestamp
- [x] Un brouillon repris contient tous les champs (destinataires, sujet, body) — LoadDraftAsync fills To/Cc/Bcc/Subject/BodyHtml/InReplyTo/References/Attachments
- [x] L'envoi d'un brouillon le supprime de la liste — SendDraftAsync calls POST /drafts/{uid}/send
- [x] data-testid sur tous les éléments interactifs — compose-send-button, draft-saved-indicator, draft-saving-indicator
- [x] Tous les textes passent par le Localizer (i18n) — DraftSaved, DraftSaving, DraftAutoSaveInfo, DraftSendSuccess in EN+FR
