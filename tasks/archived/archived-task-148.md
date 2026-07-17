# todo-task-148.md — Carnet de contacts + annuaire MSSanté sur mobile

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur `client-mobile` le module **Contacts** de `client-angular`
(`mss-contacts`, E009-F008/F009), aujourd'hui réduit à l'autocomplétion du
compose. Nouvel écran « Contacts » (accessible depuis Paramètres ou un point
d'entrée dédié — au choix du design, cohérent avec la coquille 3 onglets) :

1. **Carnet local** : liste (types Pro / Structure / Patient), recherche
   debouncée, index alphabétique, **favoris** (toggle), récents, fiche contact
   (consultation + édition), création, suppression.
2. **Groupes** : liste des groupes (système vs utilisateur), création /
   renommage / suppression des groupes utilisateur, affectation d'un contact.
3. **Annuaire national MSSanté** : recherche distincte (nom/prénom, RPPS,
   spécialité — `getSpecialties`, organisation, CP/ville) via
   `searchPractitioners`, et **import d'un praticien** vers le carnet local
   (source `Ldap`).
4. **Compose** : l'autocomplétion existante propose désormais les **favoris au
   focus** (parité Angular).

L'**import/export vCard** du web (task-086) est **exclu du périmètre mobile**
(divergence assumée : manipulation de fichiers `.vcf` = posture desktop).

US **frontend-only** : tous les endpoints existent (`getContacts`,
`createContact`, `updateContact`, `deleteContact`, `toggleFavorite`,
`getGroups`, `createGroup`, `updateGroup`, `deleteGroup`,
`searchPractitioners`, `getSpecialties` —
Angular `mss-api.service.ts:756-968`). Aucun changement backend ni DTO.
Contacts cloisonnés par praticien (backend task-023).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `MssApiService` : 11 méthodes + tests unitaires (succès + erreur)
- [ ] Écran Contacts : liste + recherche + index A-Z + favoris + fiche + CRUD
- [ ] Groupes : CRUD utilisateur ; groupes système non modifiables (testé)
- [ ] Annuaire : recherche multi-critères + import d'un praticien (dédoublonnage : RPPS/adresse existante → mise à jour, jamais de doublon)
- [ ] Compose : favoris proposés au focus du champ destinataire
- [ ] Tests : CRUD contact, toggle favori, import annuaire (dédoublonnage)
- [ ] Libellés FR en dur ; `data-testid` sur recherche, fiches, actions
- [ ] Aucune donnée de santé/RPPS dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; ouvrir Contacts
- Créer un contact Pro avec adresse MSSanté → visible dans la liste, recherche OK
- Le passer en favori → remonte dans les favoris ; compose → focus destinataire → il est proposé
- Créer un groupe « Cardiologues », y affecter le contact
- Annuaire : rechercher par spécialité + ville → importer un praticien → présent dans le carnet ; réimporter le même → mis à jour, pas de doublon

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité web (E009-F008/F009, task-086)
- **Exigences DSR honorées** : non applicable — l'annuaire reste interrogé côté serveur (Annuaire Santé ANS)
- **INS** : non applicable — les contacts « Patient » portent une adresse MES, pas d'INS manipulée par cette US
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées — carnet cloisonné par praticien ; **jamais de RPPS dans un sujet/header MSSanté** (garde-fou existant, inchangé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : CRUD contacts + imports via endpoints existants (canal serveur)
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS + référentiel de spécialités (via `getSpecialties`, source serveur)
- **Hébergement HDS** : oui — carnet stocké côté serveur (pas d'export local sur mobile)
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-148-contacts

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/52 — label `awaiting-human-merge`

## Staging
- Agrégée dans `forge/staging-task-142-160-20260716` sans conflit (593 tests verts).

## Code Review Summary
- APPROVED — 17 fichiers, module Contacts complet (carnet+groupes+annuaire+compose favoris). Réutilisation E014, FR en dur, data-testid, pas de RPPS/santé loggé. Build 0 erreur ; 563 tests (~51 nouveaux) ; ESLint clean. NgModule-based (pattern réel du repo).

## Merged
- 2026-07-17 — squash-merge sur `develop` (MERGEABLE sans conflit)
- `client-mobile` : 0625c87 (PR #52 fermée)
