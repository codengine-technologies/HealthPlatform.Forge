# todo-task-147.md — Gestion des tags depuis le détail d'un mail (mobile)

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur `client-mobile` la **gestion des tags** de `client-angular`
(détail d'un mail) : le mobile **affiche** déjà les tags (section TAGS du
volet dossiers, chips sur les lignes) mais ne permet ni d'en **ajouter** ni
d'en **retirer** sur un message.

1. **Détail d'un mail** : zone tags éditable — chips existantes avec croix de
   suppression (`removeTag`), bouton « + » ouvrant la saisie/sélection d'un
   tag (`addTag`) avec suggestions des tags existants.
2. **Cohérence liste** : les chips de la ligne inbox et la section TAGS du
   volet dossiers reflètent l'ajout/retrait (patch in-place via l'état,
   convention `TagsUpdated` SSE existante).
3. **Navigation par tag** : tap sur un tag du volet dossiers → liste filtrée
   (`getEmailsByTag`) — si déjà présent sur mobile, vérifier ; sinon l'ajouter.

US **frontend-only** : endpoints existants (`addTag`, `removeTag`,
`getEmailsByTag`, `getMailsByTag` — Angular `mss-api.service.ts:1775-1840`).
Aucun changement backend ni DTO.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `MssApiService` : méthodes tags + tests unitaires (succès + erreur)
- [ ] Détail : ajout d'un tag (saisie + suggestions), suppression par croix — mise à jour optimiste + rollback
- [ ] Ligne inbox + section TAGS mises à jour sans rechargement complet
- [ ] Navigation par tag depuis le volet dossiers → liste filtrée + retour propre
- [ ] Tests : ajout/suppression optimistes, suggestions, filtre par tag
- [ ] Libellés FR en dur ; `data-testid` sur chips, bouton +, champ de saisie
- [ ] Aucune donnée de santé dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; ouvrir un mail
- Ajouter un tag « urgent » → chip visible dans le détail et sur la ligne inbox
- La section TAGS du volet dossiers liste « urgent » avec compteur
- Tap sur « urgent » dans le volet → liste filtrée sur ce tag
- Supprimer le tag depuis le détail → chip disparaît partout
- Couper le réseau, ajouter un tag → rollback + toast d'erreur

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité web
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ajout/retrait de tags via endpoints existants (canal serveur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun — **ne jamais utiliser un tag pour porter une donnée patient identifiante** (garde-fou : pas d'INS/NIR/nom dans un libellé de tag suggéré par l'app)
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-147-mail-tags

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/51 — label `awaiting-human-merge`

## Staging
- Agrégation dans `forge/staging-task-142-160-20260716` : **CONFLIT** avec task-142 sur
  `mail-detail.component.ts` → merge abandonné (best-effort). PR #51 intacte (clean vers develop).

## Code Review Summary
- APPROVED — 10 fichiers. Réutilisation forte, optimistic+rollback, FR en dur, data-testid complets. Build 0 erreur ; 526 tests (+15) ; ESLint clean.
- Note parité : compteur section TAGS non rafraîchi instantanément (patch mail.tags only, comme le web).

## Merged
- 2026-07-17 — squash-merge sur `develop` (résolution conflit `mail-detail` : imports 142+147 combinés)
- `client-mobile` : a5c25ae (PR #51 fermée)
