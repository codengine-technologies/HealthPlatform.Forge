# todo-back-clinical-notifications-persistence-050 — Backend : stockage Redis 48h des notifications + endpoint REST notification center

**Dependencies**: todo-back-clinical-notifications-046 (contrat DTO v2 figé)
**Repo**: api-mail (path: `Api/Mail`)
**Module**: Api/Mail

## Contexte

Aujourd'hui les notifications vivent uniquement en mémoire dans le `SseNotificationBroker` : si le médecin rate l'événement (déconnecté, en consultation, en DND), il est perdu. Pour avoir un notification center utilisable et permettre le batching (tâche 049), il faut un stockage côté serveur, par user.

> **Décision PO 2026-04-08 (révision)** : on remplace la persistance Postgres initialement envisagée par un **stockage Redis avec TTL 48 heures**. Pas de table SQL, pas de migration EF Core, pas de job de purge — Redis gère l'expiration nativement. Rationale : les notifications sont éphémères par nature (un événement raté de plus de 48h n'est plus actionnable cliniquement, le médecin doit le retrouver via le mail/dossier patient lui-même), et on évite d'alourdir le schéma Postgres pour de la donnée volatile.

## Objectif

- Stocker chaque `NotificationPayloadDto` produit dans Redis avec un TTL strict de **48 heures**
- Exposer un endpoint REST paginé pour que le frontend (Blazor + Angular) puisse afficher les notifications encore vivantes
- Permettre le marquage lu / acquitté / snoozé / dismiss tant que la notification n'a pas expiré

## Pré-requis techniques déjà en place

Le repo `api-mail` consomme déjà Redis :
- `StackExchange.Redis` / `IConnectionMultiplexer` dans la DI
- Constantes centralisées : `src/Application/Constants/RedisKeys.cs` (étendre, ne pas créer un nouveau fichier)
- Exemple d'usage existant : `src/Application/Services/Implementation/RedisDistributedLockService.cs`

→ Aucune nouvelle dépendance NuGet à introduire.

## Travail à réaliser

> ⚠️ **Contrainte non négociable** : aucune table SQL, aucune entité EF Core, aucune migration, aucun `DbContext`, aucun fichier sous `src/Infrastructure/Repository/` ou `src/Domain/Repositories/` pour les notifications. **Le stockage est exclusivement Redis.** Si une partie de l'implémentation semble exiger Postgres, c'est un signal de blocage : ouvrir une `questions/` avant de continuer.

### 1. Modèle de stockage Redis

Le dev choisit la structure (hash + zset, JSON unique, etc.) en respectant ces invariants fonctionnels :

- **TTL 48h glissant à partir de `received_at`** appliqué à chaque clé liée à une notification (pas de réinitialisation lors du marquage lu).
- **Scoping strict par `userEmail`** : impossibilité technique pour le user A de lire/modifier les notifications du user B (clé Redis préfixée par l'email, vérification serveur en plus).
- **Listing trié par `received_at` décroissant** avec pagination.
- **Filtrage** sur : `severity`, `patientRecordId`, `documentType`, `from`/`to`, `includeStates`.
- **Marquage idempotent** des états : `unread`, `read`, `acknowledged`, `snoozed`, `dismissed`.
- **Compteur unread** récupérable en O(1) ou O(log n) (zset cardinality ou clé compteur dédiée).

Suggestion (non contractuelle) : un hash Redis par notification `notif:{userEmail}:{notifId}` (TTL 48h, JSON sérialisé du payload + champs d'état) + un zset `notif:{userEmail}:index` (score = timestamp Unix, member = notifId, TTL 48h aligné). Le dev peut diverger s'il a meilleure idée — la DOD valide les comportements, pas les clés.

### 2. Service `INotificationStore`

**Localisation imposée** :
- Interface : `src/Application/Notifications/INotificationStore.cs` — **PAS** sous `Domain/Repositories/` ni sous `Infrastructure/Repository/`. Le terme "Store" et le namespace `Notifications` traduisent explicitement qu'on n'est pas dans un pattern DAO/Repository SQL.
- Implémentation : `src/Infrastructure/Redis/RedisNotificationStore.cs`.

Pas d'`INotificationRepository`. Pas de classe `Repository` dans le périmètre. Pas de `DbSet<Notification>` nulle part.

```csharp
public interface INotificationStore
{
    Task SaveAsync(string userEmail, NotificationPayloadDto payload, CancellationToken ct);
    Task<PagedResult<NotificationRecord>> ListAsync(string userEmail, NotificationListFilter filter, CancellationToken ct);
    Task<int> CountUnreadAsync(string userEmail, CancellationToken ct);
    Task MarkAsync(string userEmail, Guid notificationId, NotificationState state, DateTimeOffset? snoozedUntil, CancellationToken ct);
    Task PurgeByMailUidsAsync(string userEmail, IReadOnlyCollection<long> mailUids, CancellationToken ct);
}
```

`NotificationListFilter` : `Page`, `PageSize`, `Severity?`, `PatientRecordId?`, `DocumentType?`, `From?`, `To?`, `IncludeStates: NotificationState[]`.

`NotificationRecord` reflète le payload + l'état + `read_at` / `acknowledged_at` / `snoozed_until`.

### 3. Hook dans `NewMailNotifier`

Avant de dispatcher vers les canaux SSE/SignalR, **persister dans Redis** :
```csharp
await notificationStore.SaveAsync(userEmail, payload, ct);
await Task.WhenAll(sseTask, hubTask);
```

Si l'écriture Redis échoue → log error mais on continue le dispatch (la notif reste éphémère mais ne bloque pas l'envoi temps réel).

### 3bis. Purge automatique quand un mail passe en lu

**Règle business (décision PO 2026-04-08)** : dès qu'un mail est marqué comme lu côté backend — que ce soit unitairement (`PATCH /api/v1/mail/messages/{uid}/read`) ou en batch (`PATCH /api/v1/mail/messages/read` avec une liste d'UIDs) — **toutes les notifications Redis associées à ce(s) mail(s) doivent être supprimées immédiatement**, sans attendre l'expiration TTL 48h.

Rationale métier : si le médecin a ouvert le mail, il a vu l'événement. Garder une notification "non lue" dans le notification center serait redondant et bruiteux. Le mail lu = l'événement traité.

**Périmètre fonctionnel** :
- Trigger : tout point de code qui passe l'état IMAP `\Seen` sur un mail (endpoint REST unitaire, endpoint batch, marquage automatique éventuel après ouverture).
- Action : appel à `INotificationStore.PurgeByMailUidsAsync(userEmail, [mailUid, ...])` qui supprime toutes les clés Redis dont la notification référence l'un des `mailUid` listés.
- Idempotent : purger une notification déjà absente (TTL expiré, déjà dismissée) ne lève pas d'erreur.
- Best-effort : si l'appel Redis échoue, log error mais **ne pas faire échouer le marquage du mail** (la notif s'auto-purgera dans ≤ 48h via TTL).
- Scoping strict : la purge n'agit que sur les clés du `userEmail` qui marque le mail comme lu. Aucun cross-user.

**Implémentation indicative** (le dev tranche) :
- Maintenir un index inverse Redis `notif:{userEmail}:by-mail:{mailUid}` → set des `notifId` correspondants, TTL aligné 48h, écrit lors du `SaveAsync`.
- Ou scan + filtrage des notifications du user (acceptable si le volume par user ≤ quelques centaines en fenêtre 48h).
- Le choix doit être motivé en commentaire dans la PR.

**Hook d'intégration** : identifier dans `api-mail` les contrôleurs/services qui marquent un mail comme lu (probablement dans `MailController` + le service IMAP correspondant) et y brancher l'appel à `INotificationStore.PurgeByMailUidsAsync`. **Ne pas dupliquer** la logique : un seul point de couplage, idéalement dans le service applicatif et pas dans le controller.

### 4. Endpoints REST

`src/Api/Controllers/NotificationsController.cs` (étendre celui livré par 040 si pertinent, ou créer un nouveau `NotificationCenterController`).

```
GET    /api/v1/mail/notifications                       liste paginée
       ?page=1&pageSize=20
       &severity=Critical,Urgent
       &patientRecordId=...
       &documentType=LabReport
       &from=2026-04-07&to=2026-04-08
       &includeStates=unread,read

GET    /api/v1/mail/notifications/unread-count          { count: int }
PATCH  /api/v1/mail/notifications/{id}/read             204
PATCH  /api/v1/mail/notifications/{id}/acknowledge      204
PATCH  /api/v1/mail/notifications/{id}/snooze           body: { until: datetime } → 204 (max 48h)
PATCH  /api/v1/mail/notifications/{id}/dismiss          204
```

Toutes scoppées par `userEmail` du token (vérification serveur, pas juste filtre URL).

**Snooze borné** : `until` doit être ≤ `received_at + 48h`. Au-delà → 400 Bad Request, message clair "snooze max 48h, la notification expirera dans Redis". Ce comportement est business : on ne triche pas avec le TTL.

### 5. Tests

**Unitaires** : enregistrement, listing avec filtres combinés, count unread, marquage idempotent, snooze borné à 48h, **purge par mailUid (unitaire et batch)**, **purge idempotente** (mailUid inconnu → no-op), **purge échoue → marquage mail réussit quand même**. Utiliser un Redis in-memory / testcontainers Redis selon l'existant du projet (regarder comment `RedisDistributedLockServiceTests` s'y prend).

**Intégration** (`mss.mail.integration.tests`) : endpoints + pagination + filtres + scoping par user (un user A n'accède pas aux notifs du user B même en forgeant l'ID dans l'URL → 404, pas 403). **Test E2E purge** : créer une notif via flux normal, marquer le mail correspondant comme lu via l'endpoint mail existant, vérifier que `GET /api/v1/mail/notifications` ne contient plus la notif et que `unread-count` a décrémenté.

**Test TTL** : créer une notif, simuler avance du temps de 49h (ou TTL court en test), vérifier que la notif n'est plus listée et que le GET par ID retourne 404. Si le test utilise un vrai Redis, accepter d'utiliser un TTL configurable (ex: `appsettings.Test.json` avec TTL 5s) — la valeur 48h reste hardcodée en prod via constante claire.

### 6. Configuration

Constante `NotificationStoreOptions.Ttl = TimeSpan.FromHours(48)` exposée via `IOptions<NotificationStoreOptions>` pour permettre l'override en test, mais valeur prod **non configurable** côté ops (pas dans `appsettings.json` prod). Ce point est business : on ne veut pas qu'un sysadmin allonge silencieusement la rétention.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests passent
- [ ] **Aucune** migration EF Core / aucune table SQL créée pour les notifications
- [ ] `INotificationStore` + impl Redis avec les 5 méthodes (Save, List, CountUnread, Mark, **PurgeByMailUids**)
- [ ] TTL 48h appliqué à TOUTES les clés Redis liées à une notification (vérifié par test)
- [ ] `NewMailNotifier` persiste avant dispatch (échec persistance ≠ échec dispatch)
- [ ] 5 endpoints REST avec scoping serveur par userEmail
- [ ] Tous les endpoints ont au moins 1 test d'intégration end-to-end (règle 1b CLAUDE.md)
- [ ] Filtres combinables testés (severity + patient + date)
- [ ] Snooze > 48h rejeté en 400
- [ ] Test "expiration" : une notif expirée n'est plus listée et /{id}/* retourne 404
- [ ] **Marquage mail lu (unitaire) → notification associée purgée immédiatement (test E2E intégration)**
- [ ] **Marquage mail lu (batch) → toutes les notifications associées purgées (test E2E intégration)**
- [ ] **Purge idempotente : mailUid sans notif associée → no-op silencieux**
- [ ] **Échec Redis lors de la purge → log error mais marquage mail réussit (best-effort)**
- [ ] **Scoping purge : user A marquant son mail lu ne touche pas les notifs du user B**
- [ ] Logs structurés sur chaque persistance + chaque marquage
- [ ] Aucune régression sur les tests de 040/046

## Manual Test Plan

1. Démarrer api-mail + Redis local (`docker run -p 6379:6379 redis:7-alpine` si pas déjà via AppHost)
2. Provoquer 5 notifications de sévérité variée (voir Manual Test Plan de 046)
3. `redis-cli KEYS "notif:*"` → vérifier les clés créées et `redis-cli TTL <key>` → ~172800 (48h en secondes)
4. `curl GET /api/v1/mail/notifications/unread-count` → doit renvoyer `{ "count": 5 }`
5. `curl GET /api/v1/mail/notifications?severity=Critical` → doit ne renvoyer que la critique
6. `curl PATCH /api/v1/mail/notifications/{id}/read` → 204, puis re-curl unread-count → 4
7. `curl PATCH /api/v1/mail/notifications/{id}/snooze -d '{"until":"<received_at + 24h>"}'` → 204
8. `curl PATCH /api/v1/mail/notifications/{id}/snooze -d '{"until":"<received_at + 72h>"}'` → 400 avec message snooze max 48h
9. Forger un appel avec un autre user (token différent) sur l'ID ci-dessus → doit retourner 404 (pas 403, pour ne pas leak l'existence)
10. Avancer manuellement Redis (`redis-cli DEBUG SLEEP` n'expire rien — utiliser `EXPIRE notif:... 1` puis attendre 2s) → vérifier que GET /{id} retourne 404 et que la notif disparaît du listing
11. **Purge automatique unitaire** : créer une nouvelle notif via flux mail, noter le `mailUid`, marquer ce mail comme lu via l'endpoint mail existant (`PATCH /api/v1/mail/messages/{mailUid}/read`), re-curl `GET /api/v1/mail/notifications` → la notif a disparu, `unread-count` a décrémenté.
12. **Purge automatique batch** : créer 3 notifs liées à 3 mails différents, marquer les 3 mails lus en un seul appel batch, vérifier que les 3 notifs ont disparu du listing.

## Questions ouvertes

1. **Multi-device** : si le médecin a Blazor sur PC + Angular sur tablette, le marquage "lu" sur l'un doit-il se propager à l'autre en temps réel via SSE/SignalR ? (probable oui — à confirmer en wave 2 si besoin, ne bloque pas cette US)
2. **Audit / traçabilité long terme** : avec un TTL 48h on perd toute trace au-delà. Est-ce un problème pour la conformité ou les besoins métier (ex : "le médecin a-t-il vu le résultat critique ?") ? Si oui, prévoir une **wave ultérieure** avec un journal d'événements append-only séparé (out of scope ici). À trancher avant une éventuelle US "audit notifications".

## Notes implémentation

- Le `RedisKeys.cs` existant doit être étendu, pas dupliqué, pour centraliser les patterns de clés (`notif:{user}:{id}`, `notif:{user}:index`, etc.).
- Sérialisation : System.Text.Json, conventions camelCase (cohérent avec le reste du repo).
- Pas de pipeline complexe Lua sauf si nécessaire pour l'atomicité d'un marquage. Préférer `IDatabase.HashSetAsync` + `KeyExpireAsync` simples si c'est suffisant.
- Pas de test contre Postgres pour cette feature : aucune table impliquée.
