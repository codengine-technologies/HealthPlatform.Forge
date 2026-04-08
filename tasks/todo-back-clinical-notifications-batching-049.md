# todo-back-clinical-notifications-batching-049 — Backend : batching, daily digest, DND quiet hours

**Dependencies**: todo-back-clinical-notifications-046, todo-back-clinical-notifications-persistence-050
**Repo**: api-mail (path: `Api/Mail`)
**Module**: Api/Mail

## Contexte

Une fois l'enrichissement clinique en place (046) et la persistance (050), il faut éviter de spammer le médecin :
- 5 résultats de bio reçus en 30s pour la même patiente → 1 seule notification groupée
- Documents reçus la nuit (22h-7h) → pas de réveil, mais un "daily digest" affiché le matin
- Critical → jamais batché, jamais quiet-hours-suppressed

## Travail à réaliser

### 1. Service `NotificationBatchingPolicy`

`src/Application/Services/Interfaces/INotificationBatchingPolicy.cs` + impl.

```csharp
public interface INotificationBatchingPolicy
{
    Task<BatchingDecision> EvaluateAsync(string userEmail, NotificationPayloadDto incoming, CancellationToken ct);
}

public class BatchingDecision
{
    public BatchAction Action { get; set; }   // DispatchImmediately, MergeIntoExistingBatch, StartNewBatch, DeferToDigest
    public Guid? BatchId { get; set; }
    public DateTimeOffset? DispatchAt { get; set; }   // pour Defer
}
```

Règles :
1. **Si `Severity == Critical` → DispatchImmediately, jamais batché**
2. **Si quiet hours actives** (default 22h-7h, configurable par user) **ET `Severity ∈ {Routine, Info}`** → `DeferToDigest` (sera dispatché à 7h)
3. **Si une notification existe pour le même `Patient.InternalRecordId` dans les 5 dernières minutes ET même user ET state=unread** → `MergeIntoExistingBatch` :
   - La notif existante est mise à jour : `KeyFindings` augmenté, `Title` devient "X nouveaux résultats — Mme MARTIN", `MailUid` devient une liste, `NotificationId` reste celui de la première
   - Pas de nouveau push SSE/SignalR — push d'un événement spécial `"NotificationUpdated"` avec le payload updaté
4. **Sinon** → `StartNewBatch` (= dispatch normal mais l'ID devient batch root)

### 2. Daily digest

Job hosted service `DailyDigestJob` qui tourne à l'heure de fin de quiet hours (default 7h, par user).

Pour chaque user :
- Lire toutes les notifications `state=unread` `received_at ∈ [début_quiet_hours, now]` qui ont été marquées `DeferToDigest`
- Construire 1 `NotificationPayloadDto` synthétique de `Kind = DailyDigest` :
  - `Title = "Récapitulatif nocturne — N éléments"`
  - `Body = "X documents biologiques, Y consultations, Z autres"`
  - `KeyFindings = top 5 des notifs les plus pertinentes (les plus récentes ou les plus sévères)`
  - `Severity = max(severity des notifs deferred)` capée à `Urgent`
  - `SuggestedActions = [OpenNotificationCenter]`
- Dispatcher via SSE + SignalR
- Marquer les notifs sources comme `state = digested` (nouveau state à ajouter) — elles restent visibles en notification center

### 3. Mode DND / Quiet hours par user

Étendre l'entité `NotificationPreferences` (déjà persistée en Postgres depuis 022 — c'est de la **config user durable**, légitimement SQL ; **rien à voir avec le stockage des notifications elles-mêmes qui restent strictement Redis via 050**) avec :
```
QuietHoursStart: TimeOnly       (default 22:00)
QuietHoursEnd: TimeOnly         (default 07:00)
QuietHoursEnabled: bool         (default true)
DndDuringConsultation: bool     (default true) — voir tâche 047 frontend pour le déclenchement
```

Migration EF Core sur l'entité `NotificationPreferences` **uniquement**. Garder la rétro-compat (anciens users prennent les defaults). **Audit migration obligatoire (règle 7c CLAUDE.md).**

### 4. Câblage dans `NewMailNotifier`

Avant `notificationStore.SaveAsync` (livré par 050 — service Redis, **pas** un repository SQL), appeler `batchingPolicy.EvaluateAsync`. Selon la décision :
- `DispatchImmediately` → comportement actuel
- `MergeIntoExistingBatch` → update du hash Redis existant + push `NotificationUpdated`
- `StartNewBatch` → comportement actuel
- `DeferToDigest` → save dans Redis mais ne PAS dispatcher (le job batch reprendra)

L'opération de "merge" se fait sur la même clé Redis (`notif:{userEmail}:{notifId}`) : on met à jour le hash en place, on incrémente un compteur `mergedCount`, et le TTL 48h reste celui de la notification originale (pas de réinitialisation — sinon une rafale de mails repousserait indéfiniment l'expiration).

### 5. Tests

**Unitaires** :
- 6 cas de batching policy (critical bypass, quiet hours bypass critical, merge in window, no merge out of window, no merge other patient, defer routine in quiet hours)
- `DailyDigestJob` : génération du payload synthétique, marquage `digested`, gestion 0 notifs deferred (no-op)

**Intégration** :
- 3 mails même patient en 30s → 1 notif initiale + 2 updates (vérifier 2 events `NotificationUpdated` sur le canal SSE)
- 1 mail Critical pendant quiet hours → dispatché immédiatement
- 1 mail Routine pendant quiet hours → en base mais pas dispatché live ; déclencher manuellement le `DailyDigestJob` → vérifier dispatch du digest

## Definition of Done

- [ ] Build passes, tests passent
- [ ] `INotificationBatchingPolicy` avec 4 actions, 100% des règles testées en unitaire
- [ ] `DailyDigestJob` enregistré comme `IHostedService` avec scheduling cron
- [ ] Extension `NotificationPreferences` (4 nouveaux champs) avec migration EF auditée — **migration limitée à l'entité `NotificationPreferences` (config user). Aucune table notifications créée.**
- [ ] Critical jamais batché, jamais defer (test explicite)
- [ ] Merge dans la fenêtre 5 min ne crée pas de nouvelle clé Redis (update du hash existant only, TTL inchangé)
- [ ] Event SignalR `"NotificationUpdated"` émis sur batch merge — contrat figé pour les frontends 047/048
- [ ] State `digested` ajouté à l'enum `NotificationState`
- [ ] Aucune régression sur les tests de 040/046/050

## Manual Test Plan

1. Configurer un user avec quiet hours 22h-7h
2. À 23h, envoyer un mail biologique routine → vérifier dans Redis (`redis-cli HGETALL notif:{user}:{id}`) que la notif est `state=unread, dispatched=false`, et qu'aucun event SSE n'est arrivé sur la connexion ouverte
3. À 23h05, envoyer un mail biologique critique → vérifier dispatch SSE immédiat (bypass quiet hours)
4. Avancer l'horloge serveur ou déclencher manuellement `DailyDigestJob` → vérifier qu'un événement SSE `Kind=DailyDigest` arrive
5. Tester le merge : 3 résultats bio même patient en 30s → vérifier 1 event initial + 2 events `NotificationUpdated`

## Questions ouvertes

1. **Fenêtre de batching** : 5 min par défaut, ou configurable par user ?
2. **DailyDigestJob** : 1 job global qui itère les users, ou 1 job par user instancié dynamiquement ? (impact perf si beaucoup d'users)
3. **Critical pendant quiet hours** : bypass total, ou son réduit ? (sécurité vs sommeil du médecin)
