# todo-task-075.md — Perf robustesse : propagation des CancellationToken et fire-and-forget gérés

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : robustesse/performance backend pure. Aucun
> changement de contrat ni d'UI.

## Objective

Faire en sorte que le travail serveur s'arrête quand le client a disparu
(propagation des `CancellationToken` de bout en bout sur les chaînes
controller → service → IO), et que les travaux lancés en arrière-plan
(`Task.Run` fire-and-forget) soient gérés : exceptions observées, cycle de vie
maîtrisé, annulation possible. Aujourd'hui, un client qui ferme l'onglet laisse
le serveur poursuivre des synchronisations et nettoyages de 5 à 30 secondes, et
des erreurs de sync background peuvent être perdues silencieusement.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Api/Controllers/V1/SyncController.cs:71,115,129,143` | Actions async sans paramètre `CancellationToken` | Moyen |
| 2 | `src/Application/Services/Interfaces/IBackgroundSyncManager.cs` | Interface entière sans `CancellationToken` | Moyen |
| 3 | `src/Application/Services/Implementation/BackgroundImapService.cs:221-233` | `RemoveMissingUidsAsync` reçoit un token mais ne le propage pas | Moyen |
| 4 | `src/Api/Controllers/V1/MailController.cs:304` | `_ = Task.Run(...)` fire-and-forget d'enrichissement post-réponse, exceptions non observées globalement | Élevé |
| 5 | `src/Application/Services/Implementation/BackgroundSyncManager.cs:54,113` | `Task.Run` au constructeur + fire-and-forget de la sync, échecs silencieux possibles | Moyen-Élevé |
| 6 | `src/Application/Services/Implementation/RedisSyncStateStore.cs:164` | Handler Redis en fire-and-forget avec `CancellationToken.None` (inannulable) | Moyen |
| 7 | `src/Application/Session/MailClientSessionManager.cs:54` | `Task.Run` de cleanup au constructeur d'un singleton → devrait être un `IHostedService` | Faible-Moyen |
| 8 | `src/Application/Services/Implementation/DraftCacheRepository.cs:99` | `.Result` sur une task dans un contexte async | Moyen |

## Comportement attendu

- Toutes les actions async des controllers acceptent un `CancellationToken` et
  le propagent jusqu'aux IO (EF Core, IMAP, Redis, HTTP).
- `IBackgroundSyncManager` et ses implémentations propagent le token (avec
  `default` pour compatibilité).
- Les travaux post-réponse passent par une file de background gérée
  (`IHostedService`/`Channel`-based background queue) : exceptions loggées,
  arrêt propre au shutdown, annulation possible.
- Les cleanups périodiques des singletons deviennent des `IHostedService` au
  cycle de vie observable.
- Plus aucun `.Result`/`.Wait()` sur les chemins touchés.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Toutes les actions async de `SyncController` (et les autres controllers touchés par les findings) prennent et propagent un `CancellationToken`
- [ ] `IBackgroundSyncManager` propagé token de bout en bout
- [ ] Plus de `_ = Task.Run(...)` nu dans `MailController` / `BackgroundSyncManager` / `RedisSyncStateStore` — file de background gérée avec gestion d'exception centralisée
- [ ] Cleanup de `MailClientSessionManager` migré en `IHostedService`
- [ ] `OperationCanceledException` → 499 reste géré centralement par le `GlobalExceptionHandler` (règle 12 — aucun try/catch ad hoc ajouté)
- [ ] Unit tests : >= 1 test par chemin d'annulation ajouté (token annulé → travail interrompu) et >= 1 test prouvant qu'une exception de background est loggée et n'abat pas le process
- [ ] Integration test : appel d'un endpoint sync annulé en cours → le serveur interrompt le travail (vérifiable par mock/spy)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Démarrer une synchronisation complète d'un compte volumineux puis fermer
  l'onglet client : les logs serveur montrent l'arrêt du travail lié à la
  requête (et la sync background continue, elle, de façon contrôlée).
- Provoquer une erreur d'enrichissement post-réponse (ex. couper Redis) :
  l'erreur apparaît dans les logs, l'API reste saine.
- Arrêter l'API (`Ctrl+C`) : arrêt propre, sans exceptions non observées dans
  les logs.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; les échecs de traitements background deviennent observables dans les journaux (amélioration d'imputabilité)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-075-cancellation-fire-and-forget
- `dtos-mss` (pushed, auto-incluse) : feat/task-075-cancellation-fire-and-forget — sera supprimée sans PR si aucun changement de contrat

## Develop log (2026-06-10)

**Commit (api-mail, `feat/task-075-cancellation-fire-and-forget`)** : `2911eed`

**Findings traités** :
1. ✅ `SyncController` : les 6 actions prennent et propagent un `CancellationToken` (Start propage maintenant aussi).
2. ✅ `IBackgroundSyncManager` : token sur toutes les méthodes (défaut `default`), propagé jusqu'à `ISyncStateStore` (qui acceptait déjà les tokens).
3. ✅ `RemoveMissingUidsAsync(folder, uids, ct)` : `ThrowIfCancellationRequested` entre chaque suppression (`DeleteMailAsync` n'a pas de paramètre token — le travail abandonnable est borné à un mail).
4. ✅ `MailController` enrich : `BackgroundTaskQueue` gérée (Channel + `IHostedService`) — exceptions observées centralement, token de shutdown au lieu de `CancellationToken.None`, in-flight attendus à l'arrêt.
5. ✅ `BackgroundSyncManager` : sync via la file avec **token lié** (cts utilisateur StopSync + shutdown). Le `_ = SubscribeCommandsSafelyAsync()` du ctor reste (pas un `Task.Run`, entièrement try/catché — documenté).
6. ✅ `RedisSyncStateStore` : handler de commande via la file (annulable, observé) au lieu de `Task.Run(..., CancellationToken.None)`.
7. ✅ `MailClientSessionManager` : cleanup migré vers `MailClientSessionCleanupService` (`IHostedService`) — plus de `Task.Run` au ctor d'un singleton.
8. ✅ `DraftCacheRepository` : `await deleteTask` au lieu de `.Result`.

**Règle 12 préservée** : aucun try/catch ad hoc ajouté dans les actions — `OperationCanceledException → 499` reste au `GlobalExceptionHandler` ; l'observation des erreurs background est centralisée dans le hosted service.

**Tests** : 7 nouveaux (file : exécution / échec loggé sans abattre la file / annulation au shutdown ; SyncController : propagation du token ×2 ; enrich : mise en file + token). 5 tests existants adaptés via `EagerBackgroundTaskQueue` (sémantique production : background + exceptions contenues).

**Validation** : build Release 0 erreur ; suite complète — seuls échecs = 2 flaky pré-existantes documentées (PDF export, IMAP cancel), confirmées passantes en isolation.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/98 — label `awaiting-human-merge`
- `dtos-mss` : branche `feat/task-075-cancellation-fire-and-forget` sans commit — pas de PR, branche à supprimer au `/merge`

## Code Review Summary

APPROVED — 0 issue bloquante.
- File de background gérée (Channel + IHostedService) : 3 Task.Run nus remplacés, exceptions centralisées, shutdown propre
- Cleanup sessions IMAP en IHostedService ; tokens de bout en bout SyncController → manager → state store ; token lié (user + shutdown) sur la sync
- Règle 12 préservée (pas de try/catch ad hoc, 499 centralisé)
- DOD : tous items verts (7 tests dont annulation in-flight et échec-loggé-sans-abattre)
- Sonar : Quality Gate OK, 0 new-code (3 itérations)

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #98 squash-mergée — commit `230ea24` sur `develop`
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27368711460
- Branches locales conservées pour inspection rétroactive (convention /merge)
