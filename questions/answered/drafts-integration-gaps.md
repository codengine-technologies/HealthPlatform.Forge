# Brouillons — Refonte complète (UX + Architecture IMAP)

**Date** : 2026-04-04
**Source** : Analyse du code existant + décisions PO
**Statut** : ✅ RESOLVED 2026-04-07 — toutes les décisions sont reflétées dans `tests/Features/Mss/Brouillons.feature`

---

## Contexte

L'implémentation actuelle des brouillons sauvegarde uniquement en base locale avec des UIDs inventés, sans aucune interaction IMAP. Cela casse le principe fondamental : **la table Mails doit être un miroir exact du serveur IMAP, avec des UIDs réels.**

---

## Décision PO — Architecture backend (flux unifié PendingActions)

### Principe fondateur

- La table `Mails` est toujours alignée avec le serveur IMAP. Chaque UID en base = un UID réel sur le serveur. Pas de données "fantômes" locales.
- **Toutes les opérations brouillon passent par PendingActions**, online comme offline. La sync traite les PendingActions et synchronise avec IMAP.
- Créer un brouillon = INSERT dans PendingActions. Ne peut pas échouer sauf si le backend est down.

### Flux technique

```
1. Clic "Nouveau mail"
   → POST /api/v1/mail/drafts
   → INSERT PendingAction { Type: "SaveDraft", Payload: contenu MIME }
   → Retourne un ID local (PendingAction.Id) au frontend

2. Auto-save (toutes les 30s)
   → PUT /api/v1/mail/drafts/{pendingActionId}
   → UPDATE PendingAction.Payload avec le contenu mis à jour
   (tant que non synchronisé, on met à jour la même PendingAction)

3. Sync tourne
   → ProcessPendingActionsAsync traite "SaveDraft"
   → IMAP APPEND dans Drafts avec flag \Draft
   → Récupère le vrai UID retourné par IMAP
   → INSERT dans table Mails avec le vrai UID
   → DELETE la PendingAction

4. Auto-save suivants (après sync)
   → Le draft a maintenant un vrai UID IMAP
   → PendingAction "UpdateDraft" { UID: réel, Payload: contenu }
   → Sync traite: APPEND nouveau + DELETE ancien sur IMAP
   → Nouveau vrai UID en base

5. Utilisateur va dans Drafts
   → Sync normale du dossier → le brouillon est là avec son vrai UID
   → Visible naturellement comme n'importe quel email dans le dossier
```

### Ce qui doit changer dans le code backend

- `ImapService` : ajouter `AppendToDraftsAsync()` (APPEND + flag \Draft), `ReplaceDraftAsync()` (APPEND nouveau + DELETE ancien), `DeleteDraftAsync()`
- `PendingActionTypes` : ajouter `SaveDraft`, `UpdateDraft`, `DeleteDraft`
- `PendingActionService.ProcessActionAsync` : gérer les 3 nouveaux types avec logique IMAP
- `DraftService` : refondre entièrement — toutes les opérations passent par PendingActions, plus d'écriture directe en base
- Chemin du dossier Drafts : toujours résolu via l'attribut IMAP `\Drafts`, jamais en dur
- API modifiée : retourne `PendingAction.Id` (pas un UID mail) tant que non synchronisé

---

## Décision PO — Refonte UX frontend

### Suppression de la modale "Nouveau mail"

Le composeur d'email (`NewMailComponent`) ne s'affiche plus en modale.
Il s'affiche dans la **zone détail** (là où se positionne habituellement le détail d'un email).
**Applicable : Blazor ET Angular.**

### Flux "Nouveau mail"

1. L'utilisateur clique sur "Nouveau mail"
2. Un brouillon est **créé immédiatement** via PendingAction
3. Le composeur s'ouvre dans la zone détail
4. Le brouillon n'apparait **PAS** dans la liste courante (l'utilisateur est souvent sur INBOX)
5. L'auto-save met à jour la PendingAction existante (ou crée un UpdateDraft si déjà synchronisé)

### Flux "Clic sur un brouillon" (dans le dossier Brouillons)

1. L'utilisateur navigue vers le dossier Brouillons
2. Les brouillons sont affichés avec un **traitement visuel distinct** (icône/badge)
3. Un clic sur un brouillon ouvre **directement le composeur en mode édition** dans la zone détail (pas de vue lecture seule intermédiaire)

### Navigation pendant la rédaction

Si l'utilisateur clique sur un autre email pendant qu'il rédige :
- **Demander confirmation** : "Voulez-vous annuler ou enregistrer en tant que brouillon ?"
- Si "Enregistrer" → sauvegarde le brouillon puis affiche l'email sélectionné
- Si "Annuler" → supprime le brouillon puis affiche l'email sélectionné

---

## Décision PO sur la dernière question (résolue 2026-04-07)

### Feedback d'erreur auto-save → Bandeau "Hors ligne" discret

Quand le service de messagerie est injoignable pendant l'auto-save :
- **Affichage** : bandeau permanent en haut de la zone détail tant que le service ne répond pas
- **Comportement** : le brouillon reste en mémoire locale, le professionnel continue à rédiger sans interruption
- **Pas de toast / pas de modale** : aucune notification intrusive pendant la rédaction
- **Récupération** : quand le service revient, sync automatique et transparente, le bandeau disparaît
- **Rationale** : usage clinique, on ne veut JAMAIS interrompre un médecin en train de rédiger un message à un confrère ou un patient

Scénarios Gherkin ajoutés à `tests/Features/Mss/Brouillons.feature` (section "Mode hors ligne").

---

## Prochaine étape

✅ Les .feature sont à jour. Les tâches `todo-back-drafts-004`, `todo-front-blazor-drafts-005`, `todo-front-angular-drafts-006` peuvent être dispatchées par `/forge`.

Scénarios à couvrir :
- Créer un nouveau brouillon (PendingAction créée)
- Auto-save met à jour la PendingAction
- La sync traite la PendingAction et le brouillon apparait dans Drafts IMAP
- Modifier un brouillon déjà synchronisé (UpdateDraft)
- Supprimer un brouillon
- Envoyer un brouillon
- Composeur dans la zone détail (plus de modale)
- Confirmation de navigation pendant la rédaction
- Traitement visuel distinct dans la liste des brouillons
- Clic sur brouillon = édition directe
