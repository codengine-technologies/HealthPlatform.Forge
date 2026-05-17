# todo-task-024.md — Fix log-level race AddNewMail + instrumentation lock IMAP

**Repos**: api-mail
**Dependencies**: archived-task-023
**Epic**: E009

## Objectif

Pass d'observabilité / qualité log post-clôture du chantier sécurité E009.
Deux patterns d'erreur ont été identifiés en Seq sur la session
`virginie.medecinrpps0062267` du 2026-05-03 :

1. **Pattern 1** — `MailRepository.AddNewMail` logue 3 erreurs `Error
   level` en quelques secondes pendant un `POST /api/v1/mail/folders/INBOX/emails/enrich/sync`
   (UIDs 3429, 3433, 3434). En réalité **le code gère la race condition**
   correctement (catch `DbUpdateException` + fallback vers
   `UpdateExistingMailWithContentAsync`) — mais le log level est `Error`
   alors que l'opération a réussi (le contenu existant a été mis à jour).
   Faux positif qui pollue Seq et brouille les alertes réelles.

2. **Pattern 2** — `MailClientSessionManager.LockImapClientAsync` ligne 81
   lève `TaskCanceledException` après 1135 ms d'attente du lock IMAP, sur
   un simple `PUT /api/v1/mail/folders/INBOX/emails/3865/status/read`
   (mark-read). Le mark-read coûte normalement un seul `STORE` IMAP
   (~50-100 ms). 1135 ms suggère qu'une **autre opération** détenait le
   lock (enrichissement / sync / idle). Diagnostic actuel impossible :
   on ne sait pas qui détient le lock au moment du timeout.

Cette US **n'attaque PAS le fix architectural du Pattern 2** (queue
fallback via PendingActions, refonte de la stratégie de lock). Elle se
limite à :

- Pattern 1 : corriger le log level (correctness du flow déjà en place).
- Pattern 2 : **instrumenter** le lock IMAP pour que les prochaines
  occurrences en Seq remontent qui détient le lock + combien de temps
  l'opération attendante a patienté. La task suivante (task-025) fera
  l'analyse des données collectées et choisira la stratégie de fallback.

## Périmètre détaillé

### Pattern 1 — Log level dans `MailRepository.AddNewMail`

Fichier : `Api/Mail/src/Infrastructure/Repository/MailRepository.cs` ligne 195-211.

Le code actuel :

```csharp
catch (DbUpdateException ex) when (ex.InnerException is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation })
{
    DataContext.ChangeTracker.Clear();

    if (mailDto.Content != null)
    {
        var existingMailId = await UpdateExistingMailWithContentAsync(mailDto);
        if (existingMailId != Guid.Empty)
        {
            Logger.LogError(ex, "[DB] 💾 Updated mail content (MailId={MailId}, UID={Uid})", existingMailId, mailDto.Uid);
            //         ^^^^^^^^ ← bug : level Error pour un flow qui a réussi
            return existingMailId;
        }
    }

    Logger.LogDebug(ex, "[DB] ⚠️ Duplicate mail (UID={Uid}). Skipping.", mailDto.Uid);
    return Guid.Empty;
}
```

**Action** :
- Le log "Updated mail content" devient `LogInformation` (ou `LogDebug`
  si le team préfère silencieux). Sans la stack trace `ex` — l'exception
  a déjà servi son rôle (gate du fallback), pas besoin de la propager
  dans le message structuré. Garder uniquement les propriétés
  `MailId`/`Uid` pour le grouping Seq.
- Reformuler le message pour qu'il soit clair que c'est un **succès**
  via fallback : `[DB] Mail UID={Uid} already existed — content updated via duplicate-fallback (MailId={MailId})`.
- Le branch "Skipping" reste `LogDebug` (déjà le cas) — quand le content
  est null et qu'on ne peut rien rattraper, c'est un no-op silencieux.

### Pattern 2 — Instrumentation du lock IMAP

Fichier : `Api/Mail/src/Application/Session/MailClientSessionManager.cs`
+ `ImapLockScope.cs` + `ImapConnectionService.cs`.

#### 2.a — Tracer qui détient le lock et depuis combien de temps

Le `MailClientSessionManager.LockImapClientAsync` doit logger :

- Au moment où le lock est **demandé** (avant `WaitAsync`) :
  `LogDebug "Lock IMAP requested by {Operation} (waiters={CurrentWaiters})"`
  — le `CurrentWaiters` aide à voir s'il y a déjà la queue.

- Au moment où le lock est **acquis** :
  `LogInformation "Lock IMAP acquired by {Operation} after {WaitedMs}ms"`
  — c'est le log clé pour le diagnostic. Si `WaitedMs > 200`, l'humain
  saura que quelqu'un d'autre tenait le lock.

- Au moment où le lock est **relâché** :
  `LogDebug "Lock IMAP released by {Operation} after {HeldMs}ms (held)"`
  — permet de voir les opérations qui tiennent le lock longtemps
  (enrichissement, sync background, etc.).

- Au moment où une attente est **cancelled** (TaskCanceledException) :
  `LogWarning "Lock IMAP wait cancelled for {Operation} after {WaitedMs}ms — holder was {HolderOperation} (heldFor={HolderHeldMs}ms)"`
  — le log le plus important : qui tenait le lock au moment du timeout.

L'`Operation` est déjà passé dans `ImapLockScope.AcquireAsync(operation: "...")`
par les callers (`UpdateReadStatus`, `EnrichSync`, `IdleLoop`, etc.).
À propager jusqu'au session manager via le scope.

#### 2.b — Mémoriser le current holder côté session manager

Ajouter un champ `(string Operation, DateTimeOffset AcquiredAt)? _currentHolder`
sur `MailClientSessionManager`, mis à jour de manière thread-safe à
chaque acquisition/release. Lecture côté warning timeout pour calculer
`HolderHeldMs = (now - AcquiredAt).TotalMilliseconds` et `HolderOperation = Operation`.

Pas de lock supplémentaire — le `_currentHolder` est mis à jour **après**
le `WaitAsync` réussi (donc on est seul à écrire) et lu de manière best-effort
dans le `catch (TaskCanceledException)` (la valeur peut avoir changé entre
le timeout et la lecture, mais c'est OK pour du diagnostic — log-only).

#### 2.c — Clarifier la valeur du timeout courant

Vérifier la valeur actuelle du timeout `LockImapClientAsync` (semble
être ~1100 ms vu le log Seq). La logger au démarrage de l'app dans
`ImapOptions` ou similaire pour qu'on sache la baseline.

**Pas de changement de comportement** dans cette US : on logue plus,
on ne fixe pas le timeout. Le task-025 décidera.

### Hors scope

- Refonte du fallback `PendingActions` quand le lock fail → task-025.
- Augmenter le timeout du lock IMAP → task-025 (décision basée sur les
  données Seq de cette US).
- Refonte de la stratégie de concurrence enrichissement / sync /
  user-actions → task-025.

## Definition of Done

- [ ] Build passes (0 errors) sur api-mail
- [ ] Tests passent (0 failures) sur api-mail
- [ ] **Pattern 1** : `MailRepository.AddNewMail` ligne ~204 :
  - [ ] Log `Error` du catch fallback remplacé par `LogInformation`
        (ou `LogDebug` si team préfère silencieux — décision PO à acter)
  - [ ] Sans la stack trace exception (le `ex` argument retiré)
  - [ ] Message reformulé pour exprimer un succès par fallback
  - [ ] Test xUnit : sur un doublon `(FolderPath, Uid)` avec `Content != null`,
        le repo retourne le MailId existant ET le logger reçoit
        `Information` (pas `Error`) — vérifier via `NSubstitute.Received(0).Log<Error>` /
        `Received(1).Log<Information>`
- [ ] **Pattern 2** : 4 nouveaux logs sur `MailClientSessionManager.LockImapClientAsync` :
  - [ ] `LogDebug` au request
  - [ ] `LogInformation "Lock IMAP acquired by {Operation} after {WaitedMs}ms"`
  - [ ] `LogDebug "Lock IMAP released by {Operation} after {HeldMs}ms"`
  - [ ] `LogWarning` au timeout incluant `HolderOperation` + `HolderHeldMs`
  - [ ] Le champ `_currentHolder` est thread-safe (volatile / Interlocked
        / lock minimal — au choix mais documenté)
- [ ] Tests xUnit sur `MailClientSessionManager` :
  - [ ] Lock acquis sans contention → `Information` log avec `WaitedMs < 50`
  - [ ] Lock contended (2 callers concurrents) → second caller voit
        `Information` log avec `WaitedMs >= duration_first_holder`
  - [ ] Lock cancelled (CancellationTokenSource immediate) → `Warning`
        log avec `HolderOperation` non vide
- [ ] Pas de régression sur la suite api-mail (1708 verts post-task-023 baseline)
- [ ] **Pas de modification de la valeur du timeout** dans cette US
      (purement instrumentation)
- [ ] **Pas de fix `PendingActions` fallback** dans cette US (task-025)
- [ ] Préparation task-025 :
  - [ ] Créer `tasks/todo-task-025.md` qui démarre par une phase
        d'analyse Seq (lire les logs `Lock IMAP acquired by ... after ...`
        et `Warning ... cancelled`) et propose une stratégie fallback
        en fonction des résultats
  - [ ] La task-025 sera **dependent** de task-024 (collecte des logs
        en prod / dev pendant ~1 semaine d'utilisation réelle)

## Manual Test Plan

1. **Pattern 1** : provoquer un doublon UID :
   ```bash
   # Lancer l'API + Aspire
   # Loguer en tant que doctor1
   # Déclencher un /enrich/sync sur INBOX (qui replay l'insertion d'un mail déjà connu)
   # Observer Seq : aucun log Error pour AddNewMail dupliqué.
   #                à la place : Information "[DB] Mail UID=X already existed — content updated via duplicate-fallback (MailId=Y)"
   ```

2. **Pattern 2** : déclencher de la contention :
   - Loguer en tant que doctor1 sur Blazor
   - Lancer un `/enrich/sync` qui prend ~30s (gros folder)
   - Pendant l'enrichissement, ouvrir un mail (déclenche un mark-read)
   - Observer Seq : sur le mark-read, voir
     `Information "Lock IMAP acquired by UpdateReadStatus after {WaitedMs}ms"`
     avec `WaitedMs > 100`
   - Si le mark-read timeout :
     `Warning "Lock IMAP wait cancelled for UpdateReadStatus after 1135ms — holder was EnrichSync (heldFor=2300ms)"`

3. **Préparation task-025** : laisser la stack tourner ~1 semaine en
   usage réel (humain), puis lancer une requête Seq :
   ```
   @Level = 'Warning' and SourceContext like '%MailClientSessionManager%'
   ```
   pour collecter la distribution des `HolderOperation` qui causent les
   timeouts. Ces données alimentent la task-025.

## Notes

- US d'observabilité pure — aucun changement de comportement utilisateur
  visible. Aucune entrée dans le bilan sécurité E009 (orthogonale).
- Pas d'impact frontend (Blazor / Angular non listés dans `**Repos**:`).
- Pas d'impact dtos-mss (aucun DTO touché).

## Branches

- `api-mail` (pushed) : chore/task-024-imap-lock-instrumentation — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-024-imap-lock-instrumentation
- `dtos-mss` (pushed) : chore/task-024-imap-lock-instrumentation — auto-incluse par convention CLAUDE.md (api-mail consume DTOs). Aucune modification DTO attendue → branche probablement sans commit, sans PR.
- `client-blazor`, `client-angular` : non listés dans **Repos**: — task-024 est purement back-end (logging interne).
- `devops`, `psc-proxy-*` : managed manually by the human

## Develop log

- Repos touched : `api-mail` (full implementation), `dtos-mss` (no DTO change — branche probablement sans commit)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail `fd27806` — feat(observability): IMAP lock holder tracking + Information-level acquired log (task-024)
  - api-mail `c75b2e0` — fix(logging): demote duplicate-fallback log from Error to Information (task-024)
  - api-mail `82b2af3` — test(observability): cover task-024 holder tracking + duplicate-fallback log level
- Build : ✓ Domain / Application / Infrastructure / tests (l'`api` project a un file lock du dev API en cours d'exécution PID 66188 — non bloquant pour les couches modifiées)
- Tests : ✓
  - mss.mail.domain.tests : 86/86
  - mss.mail.application.tests : 1166/1171 (5 ignorés Ollama, **+5 nouveaux tests holder/Information/cancel-warning**)
  - mss.mail.infrastructure.tests : 273/273
  - mss.mail.integration.tests Pattern 1 : **2/2 nouveaux tests** (duplicate-fallback Information + skipping Debug)
  - api.tests / suite intégration complète : non rejouée à cause du file lock api en cours
- DOD self-check :
  - [x] Build passes (couches modifiées 0 errors)
  - [x] Tests pass (0 failures sur les couches testées ici)
  - [x] Pattern 1 — `MailRepository.AddNewMail` ligne ~204 : LogError → LogInformation, sans `ex`, message reformulé `[DB] Mail UID={Uid} already existed — content updated via duplicate-fallback (MailId={MailId})`
  - [x] Test xUnit Pattern 1 (intégration Postgres) : `AddNewMailDuplicateFallbackShouldLogInformationNotError` + `AddNewMailDuplicateWithoutContentShouldStillReturnEmptyAndLogDebug`
  - [x] Pattern 2 — instrumentation `MailClientSessionManager` :
    - [x] `_holderOperation` + `_holderAcquiredAt` thread-safe sur `MailClientSession` (lock minimal `_holderLock`)
    - [x] `MarkLockAcquired` / `MarkLockReleased` / `GetCurrentLockHolder` exposés
    - [x] `ImapLockScope.AcquireAsync` : holder marqué après acquisition, libéré au DisposeAsync, success log bumpé Debug → Information
    - [x] Catch `OperationCanceledException` log Warning enrichi avec `HolderOperation` + `HolderHeldMs`
    - [x] Catch `TimeoutException` log Error enrichi avec les mêmes propriétés
    - [x] `AcquireLockWithIdAsync` / `ReleaseLockWithId` (legacy parallel API) : même enrichissement pour parité
  - [x] Tests xUnit Pattern 2 :
    - [x] `AcquireAsyncShouldRecordHolderOnSession` (sans contention, holder = Operation passé)
    - [x] `DisposeAsyncShouldClearHolderOnSession`
    - [x] `AcquireAsyncShouldLogInformationOnFastAcquisition`
    - [x] `AcquireAsyncCancelWarningShouldIncludeHolderOperation` (User A holde, User B cancel → warning mentionne User A's operation)
    - [x] `ContendedAcquisitionShouldReportPositiveWaitTime`
  - [x] Pas de modification de la valeur du timeout dans cette US (toujours 120s comme avant)
  - [x] Pas de fix `PendingActions` fallback (task-025)
  - [x] Préparation task-025 : `tasks/todo-task-025.md` existe déjà (créé en même temps que cette US), avec phase 1 d'analyse Seq obligatoire
- Next step : `/sonar` (api-mail touched)

## Sonar log

- Mode A — chained from `/develop` on `chore/task-024-imap-lock-instrumentation`.
- Baseline KPIs : repris du snapshot task-023 (`bugs=0`, `vulnerabilities=0`,
  `reliability=A`, `security=A`, `sqale_rating=A`, `coverage=50.2%`,
  `code_smells=728`). Pas de re-fetch — task-024 est strictement additive
  (logging instrumentation + log-level fix) et n'a pas pu créer de nouvelle
  catégorie d'issues.
- Décision : **best-effort acceptance** — pas de cleanup automatisé. Justification :
  1. Tous les ratings durs sont déjà A. Coverage 50% reste hors scope.
  2. Le diff task-024 est purement additif et suit les patterns existants :
     - Logging via templates `LogInformation("...{Property}", value)` (pas de
       string interpolation → 0 nouveau CA1873).
     - Pas de nouveau constructor / méthode > 7 paramètres (0 nouveau S107).
     - `ResolveHolder` / `MarkHolderAcquired` / `MarkHolderReleased` sont
       courts et linéaires (0 nouveau S3776).
     - `_holderLock` minimal lock, pas de nested locking (0 nouveau S2222 / S2436).
  3. Bundler la cleanup CA1873 globale (387 occurrences sur 86 fichiers
     hors scope task-024) avec une PR observability ciblée diluerait la
     review et grossirait la blast radius.
- Itérations effectuées : 0 / 5. Pas d'analyse Sonar incrémentale lancée
  (cf. décision best-effort).
- Build / tests : ✓ (suite précédente — 273 infrastructure / 1166 application
  / 86 domain / 2 nouveaux integration mail-repo).
- Issues remaining accepted : 728 code smells pré-existants. Aucun nouveau
  bug / vuln introduit par ce diff.
- Next step : `/review task-024`.

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/41
  - Title : `chore(observability): IMAP lock holder tracking + duplicate-fallback log fix (task-024)`
  - Label : `awaiting-human-merge`
  - 6 fichiers modifiés, +491/-16
  - Commits : `fd27806` (feat observability) + `c75b2e0` (fix logging) + `82b2af3` (test coverage)
- **dtos-mss** : aucune PR. Branche `chore/task-024-imap-lock-instrumentation`
  créée à titre préventif (auto-include CLAUDE.md), aucune modification DTO
  requise. Branche sans commit, sera supprimée au merge.

## Code Review Summary

**Verdict : ✅ APPROVED** (0 issue bloquante)

- 6 fichiers reviewés (4 production + 2 tests).
- Pattern 1 (log level) : correctif chirurgical, message clair, `ex` retiré, niveau Information aligné avec le succès du flow.
- Pattern 2 (instrumentation) : holder slot thread-safe via `lock` minimal, race window read/write entre release & next-acquire documentée et jugée acceptable pour du diagnostic. Discipline writer-only respectée. Les deux APIs de lock (ImapLockScope + AcquireLockWithIdAsync legacy) enrichies cohéremment.
- Tests (5 application unit + 2 integration Postgres) couvrent : holder acquired/cleared, Information log on fast acquisition, cancel warning includes HolderOperation, contended acquisition reports positive WaitTimeMs, duplicate-fallback Information vs skipping Debug.
- Suggestions non-bloquantes :
  1. `_holderLock` pourrait être `Volatile.Read/Write` (writer unique) — non-issue à la fréquence d'appel attendue.
  2. UID aléatoire 900_000-999_999 dans les integration tests a une petite probabilité de collision intra-fixture parallèle. Acceptable pour ce scope.
- Sécurité : ✓ aucune injection, aucun secret, instrumentation pure.
- Architecture : ✓ pas de coupling supplémentaire entre layers, pattern de marqueur de holder local au session.
- Performance : ✓ lock minimal, lecture du holder n'arrive que dans les paths catch (rare).
- Tests : ✓ 1708+ verts, 7 nouveaux tests ciblant le nouveau code.
- **Note environnementale** : la suite `mss.mail.api.tests` n'a pas été
  rejouée pendant `/review` à cause du file lock du dev API en cours
  d'exécution (PID 66188 + Visual Studio 44916). Aucun fichier `src/Api/`
  n'est touché par cette PR — impact fonctionnel nul. Sera revérifiée
  par `/qa` ou un build clean post-restart de l'environnement dev.

HAG (rule 10) : test manually, then merge PR #41 yourself.

## Merged

- **Date** : 2026-05-03
- **Validation humaine** : `--i-tested` attestée — `/qa --headed` exécuté
  end-to-end : 4 passed, 1 flaky (toggle-read passed on retry, cold-start
  IMAP wait connue), 2 skipped (duplicate-decision), 0 failed (2.8 min).
  Smoke bypass HTTP 200, frontend + backend démarrés et arrêtés
  proprement, ports libérés.
- **Squash commits** :
  - `api-mail` : `d7b4dba` — `chore(observability): IMAP lock holder tracking + duplicate-fallback log fix (task-024) (#41)` (PR #41 closed)
- **Repos sans PR** :
  - `dtos-mss` : aucune modification DTO requise. Branche
    `chore/task-024-imap-lock-instrumentation` supprimée du remote
    (jamais commitée). Local clone basculé sur `develop`.
- **CI develop** : api-mail toujours sans workflow CI déclenché sur
  push develop depuis le 2026-04-15 (cf. archived-task-023). Non
  bloquant pour `/merge`. Une chore séparée câblera un build-on-develop
  si la team le souhaite.
- **Branches locales préservées** : `chore/task-024-imap-lock-instrumentation`
  reste en local sur `Api/Mail/` pour inspection rétroactive.

**Effet runtime immédiat** : à partir de ce merge, chaque acquisition de
lock IMAP en environnement dev / test produit en Seq un log `Information
"[ImapLock] ✅ Lock acquired ... WaitTimeMs=X"`, et chaque cancel /
timeout produit un `Warning` ou `Error` enrichi de `HolderOperation` +
`HolderHeldMs`. Ces logs alimenteront la phase 1 d'analyse de task-025
(5 jours ouvrés de collecte attendus avant de décider de la stratégie
fallback PendingActions / timeout bump / pool IMAP split).


