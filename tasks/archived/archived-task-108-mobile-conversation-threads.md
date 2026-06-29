# todo-task-108-mobile-conversation-threads.md — Vue Conversations (threads) sur le client mobile

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: none
**Epic**: E012

> **US mono-repo justifiée** : le backend expose déjà le thread
> (`GET /api/v1/mail/thread/{messageId}`) et les champs de threading sont déjà
> sur le `MailDto` ; l'écart est l'absence de mode Conversation côté `client-mobile`.

## Objective

Offrir une **vue Conversation** (regroupement par fil de discussion) sur le
mobile, à parité avec `client-angular` : bascule Liste / Conversation, affichage
des racines de conversation, et dépliage des messages d'un fil.

## Analyse de référence (client-angular)

- API : `getThread(messageId)` → `GET /api/v1/mail/thread/{messageId}`
  → `MailThreadInfoDto` (`threadItems[]`, `threadCount`, `isReply`, `hasReplies`).
- `MailDto` porte déjà : `threadCount`, `isThreadRoot`, `isPartOfThread`,
  `inReplyTo`, `references` (déjà présents dans le modèle mobile).
- `mail-state` (angular) : `MailViewMode` (List/Conversation), `threadChildren`,
  `expandThread(messageId)` / `collapseThread()`.

## Comportement attendu

- Un sélecteur **Liste / Conversation** dans l'inbox.
- En mode Conversation : la liste n'affiche que les **racines** de fil (un par
  conversation), avec un compteur « N messages » sur les fils à plusieurs messages.
- Taper sur le chevron/compteur d'un fil **déplie** ses messages (chargés via
  `getThread`), indentés sous la racine ; re-taper **replie**.
- Ouvrir un message (racine ou enfant) → détail habituel.
- Le tri et les actions existants restent fonctionnels ; pas de doublon.

## Scénarios d'acceptation

1. **Bascule** — Quand je passe en mode Conversation, alors la liste regroupe
   par fil (racines uniquement).
2. **Dépliage** — Quand je déplie un fil, alors ses messages s'affichent sous la
   racine (chargés via le thread).
3. **Repliage** — Re-taper replie le fil sans rechargement inutile.
4. **Retour Liste** — Le mode Liste restaure l'affichage à plat.
5. **Aucune régression** — Ouverture d'un mail, actions et pagination restent OK.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreur)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] `MssApiService.getThread(messageId)` + modèle `MailThreadInfoDto`/`MailThreadItemDto` (déjà partiellement présents)
- [ ] `mail-state` : `mailViewMode` (List/Conversation), `threadChildren`, `expandThread`/`collapseThread`
- [ ] Sélecteur Liste/Conversation dans l'inbox ; `mss-mail-header` affiche le compteur « N messages » + chevron sur les racines à plusieurs messages
- [ ] Dépliage/repliage d'un fil (chargement `getThread`), sans doublon ni reload superflu
- [ ] Libellés FR en dur ; `data-testid` sur le sélecteur, le chevron, les enfants de fil
- [ ] Tests : `mail-state` (mode + expand/collapse + threadChildren), `mss-api.getThread`, `mss-mail-header` (compteur/chevron visibles en racine multi-messages)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Backend `cd Api/Mail && dotnet run` ; Mobile `cd Client/Mobile && npm start`
- Se connecter (PSC), ouvrir une boîte contenant des fils (réponses multiples)
- Basculer en mode Conversation → vérifier le regroupement par racine + compteur
- Déplier un fil → vérifier l'affichage des messages enfants ; replier
- Ouvrir un message enfant → détail OK ; revenir en mode Liste
- Comparer avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : ergonomie de consultation MSS
- **Authentification PS** : PSC / e-CPS (en place)
- **Interop CI-SIS** : non applicable (regroupement par en-têtes RFC-5322 In-Reply-To/References)
- **Tracé PGSSI-S** : consultation journalisée côté backend (inchangé)
- **Sécurité** : aucune donnée de santé en clair dans les logs
- **AIPD / RGPD** : inchangé — regroupement d'affichage, pas de nouveau traitement

## Branches
- `client-mobile` (pushed) : feat/task-108-mobile-conversation-threads — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-108-mobile-conversation-threads

> Single frontend (client-mobile only). Deps none (socle E012 sur develop).

## Develop log
- Repos : client-mobile
- mss-api.getThread ; mail-state MailViewMode + conversationList (roots) + expand/collapse/threadChildren ; mss-mail-header chip+chevron+toggleThread ; mss-mail-list rendu racines + enfants ; inbox segment Liste/Conversation ; requestSelectByUid$
- Build ✓ · Tests ✓ 106/106 (6 nouveaux) · Lint ✓
- Commit : client-mobile @a707509

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/13 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 106/106 · Lint ✓
- regroupement par fil (roots/expand/collapse/chip), pas de doublon/reload superflu ; FR + data-testid

## Merged
- Merged : 2026-06-19 (squash) by human authorization
- client-mobile : develop @2991ca1 (PR #13 closed)
- Local feature branch conservée
