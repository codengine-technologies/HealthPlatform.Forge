# todo-task-104-mobile-enrichment-sse-parity.md — Parité mobile enrichissement email + mise à jour SSE

**Repos**: client-mobile
**Dependencies**: task-100, task-102
**Epic**: E012

> **US mono-repo justifiée** : le backend expose déjà les endpoints et événements nécessaires ; l'écart est dans l'orchestration client-mobile (pas d'appel enrichissement sync ni d'écoute SSE folder-scoped).

## Objective

Aligner `client-mobile` sur l'algorithme `client-angular` pour les emails dont
le contenu enrichi n'est pas encore disponible au premier affichage.

Objectif UX : quand un email arrive sans contenu enrichi, le mobile doit
lancer l'enrichissement serveur, écouter les événements SSE de finalisation,
et rafraîchir automatiquement la liste et le détail sans action utilisateur.

## Analyse de référence (client-angular)

Flux observé côté Angular (libs/mss) :

1. Chargement des emails de la page (`getEmails`).
2. Déclenchement d'un enrichissement serveur sync (`POST /emails/enrich/sync`) sur les UIDs affichés.
3. Connexion SSE folder-scoped (`/api/v1/mail/events/stream?folder=...&token=...`).
4. Réception événement `EmailsEnriched` : patch in-place des lignes de liste.
5. Si le mail actuellement ouvert est touché par `EmailsEnriched` : re-fetch `getEmailContent` pour mettre à jour le panneau détail.
6. Réception `TagsUpdated` : patch léger des tags de la ligne.
7. Reconnexion stream quand le dossier change ; fermeture stream au teardown.

## Problème observé côté mobile

- Pas de méthode API `enrichEmailsSync` dans le service mobile.
- Pas de service SSE `MailEventsStream` folder-scoped.
- Le chargement inbox récupère des UIDs puis des mails, mais ne déclenche pas
  la chaîne enrichissement + notifications live.
- Conséquence : un email peut rester sans contenu enrichi côté mobile alors que
  le web Angular se met à jour automatiquement.

## Comportement attendu

- Après chargement des emails du dossier courant, le mobile déclenche
  `enrichEmailsSync(folder, uidsVisibles)`.
- Le mobile maintient une connexion SSE sur le dossier sélectionné.
- Sur `EmailsEnriched`, la liste est patchée UID par UID.
- Si le mail affiché en détail est concerné, le contenu est rechargé
  (`getEmailContent`) pour affichage immédiat.
- Sur `TagsUpdated`, patch des tags sans reload complet.
- Pas de double connexion SSE, pas de fuite mémoire, pas de boucle de reload.

## Scénarios d'acceptation

1. **Email sans contenu initial** — À l'ouverture de l'inbox, un email initialement
   incomplet est enrichi puis son contenu apparaît automatiquement sans refresh manuel.
2. **Patch liste live** — À réception `EmailsEnriched`, la ligne mail est mise à jour
   in-place (statuts, documents médicaux, indicateurs associés).
3. **Patch détail live** — Si le mail est ouvert au moment de l'événement,
   le panneau détail se met à jour automatiquement.
4. **Changement de dossier** — Le stream SSE se reconnecte sur le nouveau dossier,
   l'ancien est correctement fermé.
5. **Robustesse** — En cas d'erreur SSE transitoire, la reconnexion native
   EventSource reprend sans casser l'UI.

## Definition of Done

- [ ] Build passe (`cd Client/Mobile && npm run build`, 0 erreur)
- [ ] Tests passent (`cd Client/Mobile && npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] `MssApiService` mobile expose `enrichEmailsSync(folderPath, uids)`
- [ ] Service SSE folder-scoped implémenté (connect/disconnect/setFolder)
- [ ] Écoute des événements `EmailsEnriched` et `TagsUpdated` implémentée
- [ ] Patch in-place de la liste emails sur événements SSE
- [ ] Refresh automatique du contenu détail si UID affiché enrichi
- [ ] Fermeture/reconnexion SSE correcte au changement de dossier et au destroy
- [ ] Garde-fous anti doubles connexions / anti fuites mémoire
- [ ] Tests unitaires couvrant au minimum :
  - déclenchement enrichissement après chargement liste
  - patch liste sur `EmailsEnriched`
  - refresh détail sur `EmailsEnriched` du mail courant
  - patch tags sur `TagsUpdated`
  - reconnect au changement de dossier
- [ ] Aucun token ni donnée de santé loggés en clair

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC
- Ouvrir inbox avec au moins un email récemment reçu dont l'enrichissement est différé
- Vérifier en Network :
  - appel `POST /api/v1/mail/folders/{folder}/emails/enrich/sync`
  - ouverture stream SSE `/api/v1/mail/events/stream?...`
- Vérifier en UI :
  - la ligne mail se met à jour automatiquement après enrichissement
  - si mail ouvert, son contenu se met à jour sans navigation manuelle
- Changer de dossier puis revenir : vérifier qu'une seule connexion SSE active est maintenue
- Simuler une coupure réseau courte : vérifier reprise du stream et continuité UI

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR** : continuité d'affichage des contenus MSS et CDA
- **Authentification PS** : inchangée (PSC/e-CPS)
- **Sécurité** : flux SSE authentifié, pas de fuite de token dans les logs
- **AIPD / RGPD** : inchangé (amélioration de synchronisation client)

## Branches (attendues via /start)

- `client-mobile` : `feat/task-104-mobile-enrichment-sse-parity`

## Branches
- `client-mobile` (pushed) : feat/task-104-mobile-enrichment-sse-parity — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-104-mobile-enrichment-sse-parity

> Single frontend (client-mobile only). Dépend de task-100, task-102 (mergés).

## Develop log
- Repos : client-mobile
- mss-api.enrichEmailsSync + MailEventsStreamService (EventSource folder-scoped, NgZone, reconnect/dedup/close-on-destroy)
- inbox : enrich par lot + connect stream + patch liste (EmailsEnriched/TagsUpdated) ; mail-detail : reload contenu si mail ouvert enrichi
- Build ✓ · Tests ✓ 87/87 (6 nouveaux) · Lint ✓
- Commit : client-mobile @ff624ca

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/9 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 87/87 · Lint ✓
- enrich+SSE folder-scoped, patch in-place, reconnexion/dedup, close au destroy ; token en ?token= jamais loggé ; FR + data-testid

## Merged
- Merged : 2026-06-19 (squash) by human authorization
- client-mobile : develop @a11e9da (PR #9 closed)
- Local feature branch conservée
