# todo-task-103-mobile-inbox-pagination-scroll.md — Étudier et implémenter une pagination inbox adaptée au scroll mobile

**Repos**: client-mobile
**Dependencies**: none
**Epic**: E012

> **US mono-repo justifiée** : le blocage fonctionnel est côté `client-mobile` sur la liste inbox (limite locale à 30 items). L'objectif est d'améliorer l'expérience mobile via un chargement progressif orienté scroll, sans imposer de changement backend immédiat si l'API actuelle permet déjà la stratégie.

## Objective

Concevoir puis implémenter une solution de pagination mobile-first pour la liste
des emails inbox, orientée scroll (infinite scroll ou load-more progressif),
afin de dépasser la limite actuelle à 30 emails tout en conservant de bonnes
performances et une UX fluide sur smartphone.

## Problème observé

- Le client mobile tronque actuellement la liste des emails à 30 items.
- Constat technique actuel : dans `inbox.page.ts`, les UIDs sont limités via
  `slice(0, 30)`.
- En conséquence, l'utilisateur ne peut pas parcourir les emails plus anciens
  depuis le mobile.

## Comportement attendu

- La liste inbox charge un premier lot (page initiale) optimisé mobile.
- Un scroll vers le bas déclenche le chargement du lot suivant.
- Les éléments déjà chargés restent affichés (append), sans saut de scroll.
- Le chargement s'arrête proprement quand il n'y a plus d'emails.
- La solution reste robuste aux erreurs réseau et aux doublons.

## Scénarios d'acceptation

1. **Chargement initial** — À l'ouverture de l'inbox, un premier lot d'emails
   est affiché rapidement.
2. **Scroll bas de liste** — En atteignant le bas, un lot suivant se charge et
   s'ajoute à la liste sans perdre la position de lecture.
3. **Fin de liste** — Quand tous les emails sont chargés, un état "fin de
   liste" est affiché et aucun appel supplémentaire inutile n'est effectué.
4. **Erreur de chargement** — Si une page échoue, un message clair permet de
   réessayer sans vider les emails déjà chargés.
5. **Aucune régression** — Le tri (plus récent vers plus ancien), l'ouverture
   d'un email et les actions existantes restent fonctionnels.

## Étude attendue (avant implémentation finale)

- Évaluer les options UX mobile :
  - infinite scroll automatique
  - bouton "Charger plus" en bas (fallback accessibilité / stabilité)
- Définir la taille de lot optimale mobile (ex: 20/30/50) selon perf réelle.
- Vérifier la capacité de l'API actuelle à paginer côté UIDs/fetch, sinon
  proposer l'évolution API minimale.
- Proposer une stratégie anti-doublons et anti-double-trigger scroll.

## Definition of Done

- [ ] Build passe (`cd Client/Mobile && npm run build`, 0 erreur)
- [ ] Tests passent (`cd Client/Mobile && npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] La limite fixe à 30 n'empêche plus l'accès aux emails anciens
- [ ] Pagination orientée scroll implémentée (ou load-more validé si retenu)
- [ ] Gestion de fin de liste, loading state et erreur/retry implémentées
- [ ] Aucune duplication d'items lors des chargements successifs
- [ ] Aucune boucle d'appels réseau au scroll
- [ ] Performance mobile validée : scroll fluide et temps de chargement acceptable
- [ ] Tests unitaires couvrant au minimum :
  - append de pages successives
  - fin de liste
  - erreur puis retry
  - anti-doublons
- [ ] Aucun log contenant donnée de santé en clair

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC avec une boîte contenant >100 emails
- Ouvrir inbox, vérifier le temps de rendu initial
- Scroller jusqu'en bas à plusieurs reprises et vérifier :
  - chargement progressif des emails anciens
  - absence de doublons
  - conservation de la position de scroll
- Aller jusqu'à la fin de liste et vérifier l'absence d'appels additionnels
- Simuler une perte réseau pendant un chargement puis réessayer
- Vérifier qu'ouvrir un email après plusieurs pages fonctionne normalement
- Comparer le ressenti UX avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR** : amélioration ergonomique d'accès aux messages MSS
- **Sécurité** : pas de changement d'authentification ; pas de logs sensibles
- **AIPD / RGPD** : inchangé (amélioration de consultation, pas de nouveau traitement)

## Branches (attendues via /start)

- `client-mobile` : `feat/task-103-mobile-inbox-pagination-scroll`

## Branches
- `client-mobile` (pushed) : feat/task-103-mobile-inbox-pagination-scroll — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-103-mobile-inbox-pagination-scroll

> Single frontend (client-mobile only). Deps none.

## Étude (décision d'implémentation)
- API actuelle : `getFolder` renvoie déjà **tous** les UIDs du dossier → pagination **côté client** sur la liste d'UIDs triée desc, sans évolution backend.
- UX retenue : **infinite scroll** (`ion-infinite-scroll`) + état fin-de-liste + retry sur erreur (fallback accessible). Taille de lot : **30** (cohérent avec l'existant, bon compromis perf mobile).
- Anti-doublons : append dédupliqué par `uid` dans `mail-state`. Anti-double-trigger : `ion-infinite-scroll [disabled]` quand `!hasMore` + garde `isLoadingMore`.

## Develop log
- Repos : client-mobile
- mail-state : pagedUids/pageCursor, PAGE_SIZE=30, hasMore, isLoadingMore, startPaging/nextUidPage/appendEmails(dédup)/rewindPage
- inbox.page : 1er lot + ion-infinite-scroll append, fin-de-liste, erreur+retry (rollback curseur)
- Pagination 100% cliente (getFolder renvoie tous les UIDs) — pas d'évolution backend
- Build ✓ · Tests ✓ 81/81 (4 nouveaux) · Lint ✓
- Commit : client-mobile @10d9149

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/8 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 81/81 · Lint ✓
- append/fin-de-liste/dédup/rollback-retry testés ; anti-boucle ; pas de log santé ; FR + data-testid

## Merged
- Merged : 2026-06-19 (squash) by human authorization
- client-mobile : develop @d44b065 (PR #8 closed)
- Local feature branch conservée
