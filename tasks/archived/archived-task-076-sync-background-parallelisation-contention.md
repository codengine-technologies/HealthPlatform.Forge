# todo-task-076.md — Perf sync background : parallélisation, réutilisation des connexions IMAP et contention

**Repos**: api-mail
**Dependencies**: todo-task-075 (file de background gérée et propagation des tokens — à implémenter d'abord pour éviter les conflits sur les mêmes fichiers)
**Epic**: E011

> US mono-repo justifiée : optimisation du moteur de synchronisation IMAP
> background. Aucun changement de contrat ni d'UI.

## Objective

Accélérer massivement la synchronisation des boîtes MSSanté et réduire la
contention sous charge : l'enrichissement des mails est aujourd'hui strictement
séquentiel (1000 mails ≈ 1000 allers-retours en série), la connexion IMAP
background est détruite et recréée à chaque cycle (handshake + auth complets),
et l'accès aux sessions IMAP est sérialisé par un sémaphore binaire global.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/BackgroundImapService.cs:193-202` | Enrichissement séquentiel mail par mail (`foreach` + `await`) | Élevé |
| 2 | `src/Application/Services/Implementation/BackgroundImapService.cs:230-233` | Suppression des UIDs un par un → N allers-retours DB au lieu d'un delete batch | Moyen |
| 3 | `src/Application/Services/Implementation/BackgroundImapService.cs:326` | `_imapClient?.Dispose(); _imapClient = new ImapClient();` — reconnexion complète à chaque sync au lieu de réutiliser la session | Élevé |
| 4 | `src/Application/Services/Implementation/ImapConnectionService.cs:198` | `ConnectAsync` + `AuthenticateAsync` par requête au lieu de passer par le pool de sessions (`MailClientSessionManager`) | Élevé |
| 5 | `src/Application/Session/MailClientSessionManager.cs:57-77` | `SemaphoreSlim(1,1)` global : toutes les acquisitions de session IMAP sérialisées | Moyen-Élevé |
| 6 | `src/Application/Services/Implementation/BackgroundSyncService.cs:310-346` | Batches de sync traités séquentiellement, sans concurrence bornée | Moyen |
| 7 | `src/Application/Services/Implementation/Sse*Broker.cs` (3 brokers) | `lock` + `ToArray()` sur la liste des souscriptions à chaque publication | Moyen |
| 8 | `src/Application/Services/Implementation/BackgroundSyncService.cs:343` | Notifications de progression émises à chaque batch sans throttling (backpressure) | Moyen |

## Comportement attendu

- Enrichissement des mails parallélisé avec concurrence bornée
  (`Parallel.ForEachAsync` / batchs `Task.WhenAll`, degré configurable,
  en respectant les contraintes de MailKit : 1 commande à la fois par
  connexion IMAP → paralléliser côté DB/traitement, pas côté folder IMAP).
- Suppressions de mails par lot (une requête pour N UIDs).
- La connexion IMAP background est réutilisée entre cycles (keep-alive NOOP),
  reconnexion uniquement sur défaillance.
- Le chemin requête utilisateur réutilise systématiquement le pool de sessions.
- Verrouillage du gestionnaire de sessions à granularité par session
  (plus de sémaphore binaire global).
- Notifications de progression throttlées (ex. au plus 1/seconde par
  utilisateur).

## Definition of Done

- [x] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [x] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec hors les 3/4 rouges pré-existants documentés — voir Develop log)
- [x] Enrichissement parallélisé avec degré de concurrence borné et configurable (`BackgroundSync:EnrichmentMaxDegreeOfParallelism`, défaut 4 — test `PersistEnrichedBatchAsync_RespectsTheConfiguredParallelismBound`)
- [x] Delete batch des UIDs manquants (1 requête pour N UIDs — test `RemoveMissingUidsAsync_DeletesAllUidsInOneBatchedCall`)
- [x] Plus de dispose/new systématique de la connexion IMAP background entre cycles (registry + lease — test pipeline `FullSyncCycle_SecondCycle_ReusesThePooledConnectionWithoutReconnecting` : 2 cycles = 1 seul ConnectAsync)
- [x] `ImapConnectionService` passe par le pool de sessions (routage pool déjà posé par les tasks intermédiaires ; gap résiduel = keep-alive factice → vrai NOOP, cf. Develop log finding #4)
- [x] Verrou global du `MailClientSessionManager` remplacé par un verrouillage par session (tests : 32 appels concurrents = 1 wrapper ; user B non bloqué par user A)
- [x] Notifications de progression throttlées (max 1/s/utilisateur, finals toujours publiés — 9 tests throttle + 3 tests wiring)
- [x] Unit tests : >= 1 test par comportement modifié (parallélisme borné respecté, throttling, réutilisation de session via wrappers mockés) — 35 nouveaux tests
- [x] Integration test : cycle de sync complet sur un dossier mocké (happy path + interruption en cours de sync) — `BackgroundSyncPipelineTests` via le pipeline DI réel
- [x] Le résultat fonctionnel de la sync est identique : mêmes mails, mêmes états lus/non lus, mêmes notifications finales (pipeline : 3 mails persistés, NotifySyncCompleted unique ; règles de skip notifications inchangées)
- [x] Aucune donnée de santé en clair dans les logs (nouveaux logs = email/dossier/UID/compteurs uniquement)
- [x] Observabilité CDA fine-grained : histogramme `mssante_cda_processing_duration_seconds` (tags `step` = total/xdm_load/document_parse/html_transform + `status`) et compteur `mssante_cda_documents_total` (tag `status`) — instrumentation `CdaParsingService`, aucune donnée de santé dans les tags
- [x] Unit tests métriques CDA : 7 tests `MeterListener` (`CdaProcessingMetricsTests`) vérifiant nom d'instrument + tags `step`/`status` émis

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Sur un compte de test avec >= 500 mails (données anonymisées), lancer une
  synchronisation initiale complète ; chronométrer et comparer au temps
  pré-US (gain attendu significatif, à consigner dans la PR).
- Pendant la sync, utiliser l'application (ouvrir des mails, naviguer) :
  l'UI reste réactive (plus de sérialisation globale des sessions).
- Laisser l'application inactive 30 minutes puis relancer une action : pas de
  reconnexion complète visible dans les logs (keep-alive efficace).
- Vérifier que la progression s'affiche de façon fluide côté client (throttling
  ne casse pas l'affichage).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable — le comportement MSSanté (relève, états) est inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-076-sync-background-parallelisation — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-076-sync-background-parallelisation
- `dtos-mss` (pushed, auto-incluse) : feat/task-076-sync-background-parallelisation — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-076-sync-background-parallelisation

> Note : la modification locale non commitée de `src/AppHost/AppHost.cs` (pin
> PostgreSQL 17 pour flagsmith-db, fix humain) a été embarquée en commit
> `chore(apphost)` séparé `a5193d7` en tête de branche, conformément à la
> préférence « tout doit être commité ».

## Develop log

- Repos touched : api-mail (dtos-mss : branche auto-incluse, 0 commit task-076 — le commit `e931110` présent sur la branche est le tip de `develop` dtos, simple resync, pas de PR)
- DTOs / Interop published : no change
- Commits (api-mail) :
  - b2226cd feat(sync): throttle progress notifications, configurable BackgroundSync options
  - 201fd41 feat(session): per-session locking + real IMAP NOOP keep-alive
  - 226a951 feat(sync): pooled background IMAP connection + bounded-parallel enrichment + batch delete
  - 4c3deed refactor(sse): lock-free immutable snapshots in the SSE brokers
- Local build / test : ✓ build 0 erreur 0 warning ; tests ✓ 94 domain + 502 api + 353 infra + 1652 application verts ; intégration 224/226 — les 2 échecs sont **pré-existants** : `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellation…` (flaky IMAP cancel documenté) et `PatientUseCaseTests.GetMailsByInsWithPagination…` (**vérifié pré-existant via `git stash` + re-run sur la branche vierge** — probablement lié au merge develop #100 courrier patient INS, hors périmètre task-076, à signaler)
- Implementation notes (mapping findings audit → code) :
  - **#1 enrichissement séquentiel** → split Phase A/B miroir de task-079 : Phase A = fetch IMAP séquentiel dans `BackgroundImapService` (contrainte MailKit : 1 commande à la fois par connexion), matérialisé en `FetchedBackgroundMail` ; Phase B = `BackgroundEnrichmentProcessor.PersistEnrichedBatchAsync` en `Parallel.ForEachAsync` borné configurable (`BackgroundSync:EnrichmentMaxDegreeOfParallelism`, défaut 4), **1 scope DI par worker** (les repositories scoped cachent un DbContext par scope — pattern de copie d'identité `BackgroundSyncManager`)
  - **#2 delete UID par UID** → `RemoveMissingUidsAsync` appelle `DeleteMailsByUidsAsync` (1 requête pour N UIDs, test `RemoveMissingUidsAsync_DeletesAllUidsInOneBatchedCall` le prouvant)
  - **#3 dispose/new par cycle** → `BackgroundImapConnectionRegistry` (singleton, lease exclusif par mailbox) + `BackgroundImapConnectionMaintenanceService` (keep-alive NOOP périodique, éviction idle > `ConnectionIdleTimeout` défaut 60 min) ; `BackgroundImapService` passe sur `IImapClientWrapper`, probe NOOP au premier réemploi du cycle, **reconnexion uniquement sur défaillance** ; test pipeline « 2 cycles = 1 seul ConnectAsync »
  - **#4 ConnectAsync par requête** → le routage par le pool (`GetOrCreateImapClientAsync`) avait déjà été posé par les tasks intermédiaires depuis l'audit ; le gap résiduel était le **keep-alive factice** (`SendKeepAliveNoopAsync` ne loggait qu'un faux NOOP) → vrai `NoOpAsync` exposé sur `IImapClientWrapper` et envoyé par la boucle keep-alive (plus de drop serveur → plus de reconnexion+auth par requête)
  - **#5 sémaphore global** → supprimé ; `GetOrAdd` lock-free + verrou de création du wrapper **par session** dans `MailClientSession` ; tests : 32 appels concurrents même session = 1 wrapper, user B non sérialisé derrière user A
  - **#6 batches séquentiels** → couvert par la Phase B parallélisée par batch + `InterBatchDelay` configurable (défaut 0, remplace le `Task.Delay(500)` codé en dur) ; le pipelining inter-batch (fetch N+1 pendant persist N) volontairement non fait — la progression resterait fausse (compteur en avance sur la persistance réelle)
  - **#7 lock+ToArray par publication SSE** → `ImmutableArray` dans le `ConcurrentDictionary` des 3 brokers : publication sans verrou ni copie, subscribe/unsubscribe en boucle CAS
  - **#8 notifications par batch** → `SyncProgressNotificationThrottle` (singleton, `TimeProvider`) : max 1 notification intermédiaire/s/utilisateur, états terminaux (folder final, completed, error) toujours publiés, reset en fin de sync
  - Garde-fou anti-race : le chemin background ne prenait PAS le lock enrich-persist task-079 (foreground) avant cette task — statu quo préservé (les workers d'un batch traitent des UIDs distincts ; la race inter-passes éventuelle est absorbée par le dedup `AddNewMail` + l'isolation d'erreur par mail, comme avant)
  - `BackgroundImapService` reste `[ExcludeFromCodeCoverage]` (IMAP network IO) — la logique DB/processing extraite dans le processor est, elle, pleinement testée
- Tests : 35 nouveaux — throttle (9), processor (12 : bound, isolation échec, identité par scope, notifications incrémental/initial/self-action, batch delete), registry (10 : lease exclusif, réemploi, NOOP, éviction, drop sur défaillance), session/manager (5 : concurrence création, NOOP réel, release du lock), pipeline DI complet (3 : happy path, réemploi inter-cycles, interruption)
- DOD self-check : 12/12 verts (détails ci-dessus ; « résultat fonctionnel identique » prouvé par le pipeline : mêmes mails persistés, mêmes notifications finales, mêmes règles de skip)

## Complément — observabilité CDA fine-grained (suspicion de régression 80 ms → 142 ms)

Motivation : le temps de traitement par CDA n'avait aucune métrique dédiée
(reconstruit a posteriori depuis les logs Seq : médiane ~142,6 ms, moyenne
~212,3 ms sur 13 CDA, vs ~80 ms/CDA constatés historiquement). Sans
décomposition par phase, impossible d'isoler *quelle* étape régresse.

Instrumentation ajoutée (`CdaParsingService`) :

- Histogramme `mssante_cda_processing_duration_seconds`, unité `seconds`,
  tags `step` ∈ { `total`, `xdm_load`, `document_parse`, `html_transform` } et
  `status` ∈ { `success`, `error` }. Permet de mesurer indépendamment :
  - `total` : durée bout-en-bout de `ParseIheXdmZip` (par zip)
  - `xdm_load` : chargement/validation XSD du IHE_XDM (par zip)
  - `document_parse` : parsing d'un CDA (par document)
  - `html_transform` : transformation XSLT → HTML (par document, phase
    historiquement la plus lourde et sensible au cache XSLT)
- Compteur `mssante_cda_documents_total`, tag `status` — volume de CDA parsés.

Définitions dans `MailProcessingMetrics` (meter `Mssante.MailProcessing`,
exposé sur `/metrics` Prometheus) ; constantes de `step` dans
`MetricsConstants`. Aucune donnée de santé dans les tags (uniquement
`step`/`status`, pas d'INS, de contenu CDA ni de patient).

Tests : `tests/mss.mail.application.tests/Telemetry/CdaProcessingMetricsTests.cs`
— 7 tests `MeterListener` (nom d'instrument + tags par step + statut error +
compteur). Verts (7/7).

> Analyse de la régression : une fois en prod, comparer les quantiles de
> `html_transform` vs `document_parse` vs `xdm_load`. Un saut isolé sur
> `html_transform` pointerait un cache XSLT froid / non réutilisé ; un saut sur
> `xdm_load` pointerait l'I/O ou la validation XSD.
- no angular change → skipped /lint-angular
- Next step : /sonar task-076 (chaîne ensuite vers /review)

## Sonar log

- Phase 1 (new code) : ✓ Quality Gate **OK** après 1 itération — new_violations 0, new_security_hotspots_reviewed 100 %, new_coverage 82.8 % ≥ 80 (seuil gate ; la new-code period projet reste une baseline large, cf. note opérationnelle /sonar)
- Phase 1 — Issues fixées : 6 (commit `e4faf1b`) — S3776 + S138 sur `EnsureConnectedAsync` (fix manuel privilégié, règle blacklistée mais new code : extraction `TryReuseConnectedClientAsync` / `ConnectNewClientAsync` / `ValidateNegotiatedConnectionAsync`), S1854 (init morte `missingUids`), S125 (commentaire reformulé), S103 (ligne longue `SemanticSearchService` — new-code period, pas task-076), CA2016 (token → `UsageLock.Wait`)
- Phase 2 (legacy) : 1 itération — 1 seule issue restante (CA2016 INFO héritée, ligne conservée par le rework), fixée commit `1e1e456` → **dette nulle**
- État final projet : 0 bug / 0 vulnérabilité / 0 smell / 0 hotspot, ratings A/A/A, coverage 83.9 %, Quality Gate OK
- Build / tests : ✓ Release 0 erreur ; échecs uniquement dans le set pré-existant documenté (middleware Release-only, MailExport PDF flaky — y c. variante `BuildPdfWithMedicalDocumentHtmlBodyFallback` vérifiée verte en isolation 22/22, IMAP cancel flaky, patient INS pagination)
- no angular change → skipped /lint-angular
- Hand-off : /review task-076

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/102 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche auto-incluse, 0 commit task-076 (le commit présent est le tip de develop dtos, simple resync)

## Code Review Summary

**Verdict : APPROVED** (28 fichiers revus, +2254/−429, 2 suggestions non-bloquantes, 0 bloquant)

- `BackgroundImapService` — ✅ split Phase A/B fidèle au précédent task-079 ; cycle de vie du lease correct (release garanti par le Dispose scoped, ownership transféré au registry seulement après auth réussie) ; refacto Sonar (extraction probe/connect/validation) sans changement de comportement. ⚠️ suggestion : sur échec terminal de connexion, le dernier wrapper non-poolé n'est pas disposé en fin de scope (impact faible — les chemins d'erreur font `DisconnectAsync`, les retries sont couverts par `DropCurrentClient`)
- `BackgroundEnrichmentProcessor` — ✅ 1 scope DI par worker (DbContext par scope), isolation des échecs par mail, OCE re-levée, règles de notification préservées à l'identique
- `MailClientSessionManager` / `MailClientSession` — ✅ `GetOrAdd` lock-free + double-checked lock par session, NOOP réel sous `Wait(0)` release en `finally`. ⚠️ suggestion : log « Session disposed » Information sur la session perdante d'une course `GetOrAdd` (bruit cosmétique)
- `BackgroundImapConnectionRegistry` + maintenance hosted service — ✅ entrées jamais supprimées (anti-stranding documenté), skip des entrées louées, échec NOOP → drop + reconnexion au cycle suivant
- Brokers SSE — ✅ snapshots immuables, retrait CAS, comportement identique
- Throttle + `BackgroundSyncService` — ✅ états terminaux toujours publiés, `_currentProgress` frais pour `/sync/status`

Validation : build ✓ 0 erreur (Debug + Release) · tests ✓ (échecs = uniquement les 4 rouges pré-existants documentés, dont 1 vérifié pré-existant via stash) · DOD ✓ 12/12 · Sonar ✓ Quality Gate OK, 0 issue projet, new-code 0 violation, coverage 83.9 %

## Merged

- Date : 2026-06-12
- `api-mail` : squash commit `fa44219` (PR #102 closed, branche remote supprimée, branche locale conservée)
- Le squash inclut un commit humain final « Add metrics » (télémétrie CDA : `MailProcessingMetrics`, `MetricsConstants`, `CdaParsingService`, dashboard Grafana, +1 fichier de tests) poussé sur la branche après la review forge — couvert par l'attestation `--i-tested`
- `dtos-mss` : aucune PR (0 commit task-076) — branche remote supprimée, clone resynchronisé sur `develop`
- develop CI : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27430036650
