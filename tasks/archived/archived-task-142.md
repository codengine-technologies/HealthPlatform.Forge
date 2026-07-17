# todo-task-142.md — Corbeille complète sur mobile (restauration, undo, suppression définitive)

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Compléter le cycle de vie « Corbeille » du mobile, aujourd'hui limité à la mise
à la Corbeille sans retour possible :

1. **Restauration** : depuis le dossier Corbeille, action « Restaurer »
   (swipe + détail) → `moveEmail` vers la boîte de réception. Parité avec la
   règle drag Trash→Inbox d'Angular (`mail-drop-rules.util.ts`).
2. **Undo après suppression** : après une mise à la Corbeille (unitaire ou en
   masse), toast « Email supprimé · Annuler » (6 s) — portage de
   `mail-undo-toast` Angular : tant que le toast est visible, « Annuler »
   remet le courrier à sa place (aucune suppression réellement effectuée ou
   déplacement inverse, selon la mécanique Angular portée à l'identique).
3. **Suppression définitive** : dans le dossier Corbeille uniquement, l'action
   « Supprimer » devient « Supprimer définitivement » avec confirmation
   explicite (« Cette action est irréversible »).

Rappel métier : la mise à la Corbeille **supprime le lien patient** du courrier
(reconstruit à la restauration) — comportement backend existant, à vérifier
dans le plan de test.

US **frontend-only** : `moveEmail`, `deleteEmail`, `bulkDeleteEmails`
existants. Aucun changement backend ni DTO.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Dans la Corbeille : action « Restaurer » (swipe + détail) → retour Inbox
- [ ] Toast « Email supprimé · Annuler » (6 s) après mise à la Corbeille ; « Annuler » restaure l'état exact (liste + compteurs)
- [ ] Undo couvre l'unitaire **et** le bulk (si task-141 déjà livrée ; sinon unitaire seul, sans casse)
- [ ] Dans la Corbeille : « Supprimer » = suppression définitive, confirmation « irréversible », le mail disparaît pour de bon
- [ ] Hors Corbeille : comportement de suppression inchangé (mise à la Corbeille)
- [ ] Tests : restauration, undo (dans les 6 s / après expiration), suppression définitive, libellés d'action selon le dossier
- [ ] Libellés FR en dur ; `data-testid` sur toast/undo, restaurer, supprimer définitivement
- [ ] Aucune donnée de santé dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start`
- Supprimer un mail depuis l'inbox → toast « Email supprimé · Annuler » ; taper « Annuler » → le mail réapparaît à sa place
- Supprimer à nouveau, laisser expirer le toast → le mail est en Corbeille
- Ouvrir la Corbeille → « Restaurer » par swipe → le mail revient en Inbox ; vérifier que son lien patient est reconstruit (timeline patient)
- Dans la Corbeille, « Supprimer définitivement » → confirmation → le mail ne réapparaît nulle part après refresh
- Vérifier les compteurs non-lus après chaque opération

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité web (task-093 côté Angular)
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : suppression/restauration journalisées côté `api-mail` (canal existant) ; la suppression définitive reste une action tracée serveur
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé — la suppression définitive suit la politique de conservation existante

## Branches
- `client-mobile` (pushed) : feat/task-142-trash-lifecycle

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/50 — label `awaiting-human-merge`

## Staging
- Agrégée dans `forge/staging-task-142-160-20260716` (chore(staging): aggregate task-142)

## Code Review Summary
- APPROVED — 11 fichiers, réutilisation forte (port fidèle du pending-delete web), optimistic UI + rollback cohérents, FR en dur, data-testid complets, dead code retiré.
- Build 0 erreur ; 528 tests OK ; ESLint clean.
- Vérification visuelle Playwright : best-effort non exécutée dans ce run (non bloquant).

## Merged
- 2026-07-17 — squash-merge sur `develop`
- `client-mobile` : 5ed7ca1 (PR #50 fermée)
- develop CI : run 29568787772 (in_progress au moment du merge — à confirmer verte)
