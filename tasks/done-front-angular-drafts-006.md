# todo-front-angular-drafts-006 — Angular : Gestion des brouillons

**Dependencies**: todo-back-drafts-004
**Feature**: tests/Features/Mss/Brouillons.feature
**Repo**: client-angular (path: `Client/Angular`)
**Module**: Client/Angular/front/libs/mss

## Objectif

Implémenter la sauvegarde automatique et la reprise des brouillons dans l'application Angular.

## Travail à réaliser

### 1. Service API
- Ajouter dans `MssApiService` :
  - `saveDraft(dto)` → POST /api/v1/mail/drafts
  - `updateDraft(uid, dto)` → PUT /api/v1/mail/drafts/{uid}
  - `getDrafts()` → GET /api/v1/mail/drafts
  - `getDraft(uid)` → GET /api/v1/mail/drafts/{uid}
  - `deleteDraft(uid)` → DELETE /api/v1/mail/drafts/{uid}
  - `sendDraft(uid)` → POST /api/v1/mail/drafts/{uid}/send

### 2. Modèles
- `SaveDraftDto`, `DraftDto` dans `libs/mss/src/models/`

### 3. Auto-save dans MailComposeComponent
- Timer 30 secondes via `interval()` + `takeUntilDestroyed()`
- Signal `lastSavedAt` pour l'indicateur visuel
- Sauvegarde à la fermeture si contenu non envoyé
- Sauvegarde du contenu courant avant envoi d'un brouillon (évite perte sur le gap de 30s)

### 4. Reprise de brouillon
- Clic sur brouillon → emit `openCompose$` avec `isDraft: true`
- Chargement complet via `getDraft(uid)` API (body, Bcc, InReplyTo, References, Attachments)
- Pré-remplir tous les champs : To, Cc, Bcc, Subject, BodyHtml, InReplyTo, References
- Envoi via `updateDraft()` + `sendDraft()` → suppression automatique

### 5. Liste des brouillons
- Affichage du badge "Brouillon" dans MailHeaderComponent pour les drafts
- Notification `draftSent$` retire le brouillon envoyé de la liste

### 6. data-testid
- `compose-send-button` sur le bouton Envoyer
- `draft-saved-indicator` sur l'indicateur "Brouillon sauvegardé"
- `draft-saving-indicator` sur l'indicateur "Sauvegarde..."

## Definition of Done
- [x] Build passes (0 errors)
- [ ] Tests Vitest passent — à exécuter / écrire
- [x] L'auto-save fonctionne après 30 secondes
- [x] L'indicateur de sauvegarde s'affiche avec data-testid
- [x] La reprise de brouillon restaure tous les champs (To, Cc, Bcc, Subject, Body, InReplyTo, References)
- [x] L'envoi d'un brouillon le supprime du dossier via draftSent$
- [x] Le contenu est sauvegardé avant envoi (updateDraft avant sendDraft)
- [x] Standalone component, OnPush, Angular Signals
