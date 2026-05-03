# todo-task-025.md — Fallback PendingActions sur timeout lock IMAP (analyse-driven)

**Repos**: api-mail
**Dependencies**: todo-task-024
**Epic**: E009

## Objectif

Fix architectural du **Pattern 2** (timeout lock IMAP sur opérations
user-driven comme mark-read) identifié dans Seq sur la session
`virginie.medecinrpps0062267` du 2026-05-03 : un `PUT
/api/v1/mail/folders/INBOX/emails/3865/status/read` lève
`TaskCanceledException` après 1135 ms d'attente parce qu'une autre
opération (probablement un `EnrichSync` ou le `BackgroundSyncService`)
détient le lock IMAP.

Cette US **commence par une phase d'analyse obligatoire** des logs
collectés grâce à l'instrumentation posée par task-024 (`Lock IMAP
acquired by {Operation} after {WaitedMs}ms`, `Lock IMAP wait cancelled
for {Operation} after {WaitedMs}ms — holder was {HolderOperation}`).
Les résultats de cette analyse **conditionnent** la stratégie
d'implémentation. Pas de code écrit avant que l'analyse soit posée.

## Phase 1 — Analyse préalable (obligatoire, livrable séparé)

### 1.a Collecte minimale (1 semaine après task-024 mergée)

L'humain laisse la stack tourner en usage réel (Blazor + Angular) pendant
au moins **5 jours ouvrés** après le merge de task-024. La instrumentation
ajoutée par task-024 produit en Seq :

- `Information "Lock IMAP acquired by {Operation} after {WaitedMs}ms"`
- `Debug "Lock IMAP released by {Operation} after {HeldMs}ms"`
- `Warning "Lock IMAP wait cancelled for {Operation} after {WaitedMs}ms — holder was {HolderOperation} (heldFor={HolderHeldMs}ms)"`

### 1.b Questions à répondre dans l'analyse

L'humain (ou la forge avec le MCP Seq) produit un document
`Docs/analysis/lock-imap-contention-{YYYYMMDD}.md` qui répond aux
questions suivantes :

1. **Distribution des `HolderOperation` lors d'un timeout** : quelles
   opérations détiennent le lock au moment où une autre se fait cancel ?
   - Réponse attendue sous forme : `EnrichSync: 78%, BackgroundSync: 15%, IdleLoop: 7%`.
2. **Distribution des opérations qui se font cancel** : qui sont les
   victimes ?
   - Hypothèse plausible : `UpdateReadStatus` (mark-read) majoritaire,
     suivie de `MarkUnread`, `MoveToTrash`, `Delete`.
3. **Distribution des `WaitedMs` au moment du cancel** : la valeur
   moyenne / médiane / p95 / p99.
4. **Distribution des `HeldMs` des opérations qui causent les cancels** :
   le holder typique tient le lock combien de temps ?
5. **Fréquence absolue** : combien de timeouts par jour, par user,
   par opération ?
6. **Existe-t-il une corrélation temporelle** : les timeouts sont-ils
   regroupés (sync background tournant en boucle) ou diffus ?

### 1.c Décision conditionnelle

Sur la base de l'analyse, le PO + tech lead choisissent **une** des
stratégies suivantes (à acter avant d'implémenter) :

#### Stratégie A — File d'attente via PendingActions (recommandée)

Si l'analyse montre que les opérations cancellées sont **majoritairement
des actions user idempotentes** (mark-read, mark-unread, move, delete),
alors les "rejouer plus tard" via la table `PendingActions` est correct.

Concrètement : quand `EmailFlagService.ProcessEmailAsync` (ou n'importe
quelle opération IMAP user-driven) attrape une `TaskCanceledException`
issue de `LockImapClientAsync`, elle :

1. Crée une `PendingAction` avec `ActionType = "MarkRead"|"MarkUnread"|...`,
   `FolderPath`, `MailUid`, `UserId` (filtrage task-023), `Status = Pending`.
2. Retourne 202 Accepted (au lieu de 500) au client avec un payload
   `{ "deferred": true, "pendingActionId": "..." }`.
3. Le `PendingActionWorker` (déjà existant côté
   `BackgroundImapService` / `PendingActionService`) rejoue l'action
   au prochain cycle de sync, quand il pourra acquérir le lock.

Le frontend (Blazor + Angular) :
- Sur 202 + `deferred=true`, optimistic update de l'UI (le mail apparaît
  comme lu) + toast informationnel "Action différée — appliquée au
  prochain sync".
- Sur succès du replay (event SSE `PendingActionCompleted`), pas
  d'action UI nécessaire (déjà optimistement à jour).
- Sur échec du replay (event SSE `PendingActionFailed`), rollback
  optimistic UI + toast d'erreur.

#### Stratégie B — Augmenter le timeout du lock

Si l'analyse montre que les `HolderHeldMs` sont en moyenne **< 5 secondes**
et les contentions rares, simplement passer le timeout du lock de 1100
ms à 5000 ms peut suffire. Pas de fallback nécessaire.

Anti-pattern : timeout très long → frontend bloqué → mauvaise UX.
À éviter si la latence visible côté humain dépasse 2s.

#### Stratégie C — Découpler les opérations user-driven du lock IMAP global

Si l'analyse montre que les operations user-driven (`UpdateReadStatus`)
n'ont **strictement pas besoin du même client IMAP** que les
opérations background (sync / enrichissement), envisager d'avoir 2 pools :

- Pool **interactive** : 2-3 clients IMAP réservés aux user-actions.
- Pool **background** : 1 client réservé au sync / enrich.

Plus complexe (gestion de 2 pools, doublement de la consommation IMAP)
mais résout le problème de contention par séparation.

#### Stratégie D — Combinaison A + B

Stratégie A (PendingActions fallback) est implémentée avec un timeout
augmenté à 3-5 secondes. Pour les cas pathologiques (sync long), le
fallback PendingActions s'active en dernier ressort.

### 1.d Sortie de la phase 1

Le document `Docs/analysis/lock-imap-contention-{YYYYMMDD}.md` est
mergé et **valide la stratégie retenue** (A, B, C ou D). Sans ce
document, la phase 2 ne démarre pas.

## Phase 2 — Implémentation (conditionnelle)

### 2.a Si Stratégie A retenue (par défaut, hypothèse de travail)

**Backend** :

- Nouveau helper `IPendingActionFallback.QueueAsync(string folderPath, uint mailUid, string actionType, object? payload, CancellationToken ct)`
  encapsule la création de la `PendingAction`. Implémentation appelle
  `_pendingActionRepository.AddAsync(...)` (déjà task-023-scopé par UserId).
- `EmailFlagService.ProcessEmailAsync` catch refactorisé :
  ```csharp
  catch (TaskCanceledException ex) when (lockTimeout)
  {
      var pendingId = await _fallback.QueueAsync(folderPath, uid, "MarkRead", null, ct);
      _logger.LogInformation("[EmailFlag] Lock contention, deferred to pending action {PendingId}", pendingId);
      return new DeferredResult { PendingActionId = pendingId };
  }
  ```
- Le contrôleur retourne 202 Accepted avec le payload `{ deferred: true, pendingActionId }`.
- Le `PendingActionService` existant (qui exécute les actions au sync)
  doit gérer le nouveau `ActionType = "MarkRead"` (idem MarkUnread, Move,
  Delete — vérifier la liste). Si déjà présent, no-op.
- Quand le replay réussit, publier un event SSE
  `PendingActionCompleted { pendingActionId, originalAction }` via
  `ISseMailEventBroker` (canal déjà en place pour les events mail).
- Quand le replay échoue après N retries, publier
  `PendingActionFailed { pendingActionId, reason }`.

**Frontend (out of scope cette US — task suivante)** :

- Blazor + Angular gèrent 202 Accepted comme un succès optimiste.
- Toast "Action différée — appliquée au prochain sync".
- Listen `PendingActionCompleted` / `PendingActionFailed` sur le canal SSE.

### 2.b Si Stratégie B retenue

- Modifier `ImapOptions.LockTimeoutMs` (ou équivalent) de 1100 → 5000.
- Tests : vérifier que le timeout est bien lu depuis config et appliqué.
- Pas de changement code application.

### 2.c Si Stratégie C retenue

- Refonte significative. Cette US **n'a pas le périmètre** pour C —
  un follow-up dédié sera requis.

### 2.d Si Stratégie D retenue

- Implémenter B + A en séquence dans la même PR.

## Definition of Done

### Phase 1 (analyse, obligatoire)

- [ ] task-024 mergée et déployée depuis ≥ 5 jours ouvrés
- [ ] Document `Docs/analysis/lock-imap-contention-{YYYYMMDD}.md`
      produit avec les 6 réponses (cf. §1.b)
- [ ] Document validé par PO + tech lead
- [ ] Stratégie retenue (A / B / C / D) explicite dans le document
- [ ] Si stratégie C → la US est **fermée sans implémentation** et un
      nouveau task `chore-imap-pool-split` est créé pour la refonte

### Phase 2 (implémentation, conditionnelle à la stratégie A ou D)

- [ ] Build passes (0 errors) sur api-mail
- [ ] Tests passent (0 failures) sur api-mail
- [ ] Nouveau service `IPendingActionFallback` + impl + tests xUnit
- [ ] `EmailFlagService` (et autres services user-driven impactés)
      catch `TaskCanceledException` du lock IMAP et appellent le fallback
- [ ] Controllers retournent 202 Accepted + payload `{ deferred, pendingActionId }`
      au lieu de 500 quand fallback déclenché
- [ ] `PendingActionService` rejoue les nouvelles `ActionType` au sync
      (vérifier liste exhaustive : `MarkRead`, `MarkUnread`, `Move`, `Delete`)
- [ ] Event SSE `PendingActionCompleted` / `PendingActionFailed`
      publiés au replay
- [ ] Tests xUnit cross-tenant (cf. task-023 convention) :
  - [ ] User A queue une PendingAction → User B ne la voit pas dans `GetPendingActionsAsync`
  - [ ] User A queue → replay au sync de A → exécutée
  - [ ] User A queue → User B fait un sync → A's pending **n'est PAS** traitée
- [ ] Tests d'intégration : timeout simulé via `CancellationTokenSource`
      bref → fallback → 202 → replay → succès end-to-end
- [ ] Pas de régression sur la suite api-mail (1708+ baseline)

### Phase 2 — frontend (US suivante, hors scope ici)

Une task-026 sera créée pour Blazor + Angular UX (toast, gestion 202,
listen events SSE) une fois l'API stabilisée.

## Manual Test Plan

(Rempli après validation de la phase 1.)

### Si Stratégie A retenue

1. **Setup** : `cd Api/Mail`, `dotnet run` + Aspire AppHost.
2. **Reproduire la contention** : depuis Blazor, déclencher un
   `/enrich/sync` qui prend ≥ 30s sur un gros folder. Pendant
   l'enrichissement, ouvrir un mail (mark-read implicite).
3. **Attendu réseau** : la requête `PUT .../status/read` retourne
   202 Accepted avec `{ "deferred": true, "pendingActionId": "<guid>" }`.
4. **Attendu UI** : le mail apparaît comme lu immédiatement (optimistic).
   Toast informationnel court.
5. **Attendu Seq** : log `Information "[EmailFlag] Lock contention,
   deferred to pending action {PendingId}"`.
6. **Attendu fin de sync** : event SSE `PendingActionCompleted` reçu →
   pas de changement UI (déjà à jour).
7. **Attendu DB** : `SELECT * FROM PendingActions WHERE UserId = ...`
   montre la ligne en `Status=Completed` après le replay.

### Cross-tenant non-régression

8. Loguer en tant que doctor2, vérifier que `/api/v1/mail/pending-actions`
   ne retourne **jamais** les pending actions de doctor1 (filtre task-023).

## Notes

- US **analyse-driven** : la phase 1 doit produire des données réelles
  avant que la phase 2 démarre. Pas de "implémenter par anticipation"
  même si la Stratégie A semble la plus probable a priori.
- Lien direct avec le chantier sécurité E009 : la convention
  task-023 (ownership scoping) sur `PendingActionRepository` garantit
  que le fallback respecte le cloisonnement par UserId. Aucun risque
  de fuite cross-tenant introduit par cette US.
- L'US frontend (toast + UX 202 + listen SSE replay events) sera une
  task-026 séparée, créée après validation de la phase 2 backend.
- Si la phase 1 montre que les timeouts sont rares (< 1 par jour par
  user) et que la stratégie B (timeout 5s) suffit, on évite la
  complexité du fallback PendingActions — décision data-driven.
