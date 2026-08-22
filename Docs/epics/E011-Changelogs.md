# E011 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Vue produit** : [E011-performance-api-mail.md](E011-performance-api-mail.md)
> **Dernière mise à jour** : 2026-08-22 (v1.12)

---

## Historique détaillé des changelogs

### v1.12 — task-266 — Les compteurs de fils ne sont calculés que si un client les affiche (2026-08-22)

- **PR** : [HealthPlatform.Api.Mail#198](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/198) et [HealthPlatform.Mobile#62](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/62) — label `awaiting-human-merge`. `client-angular` : **code-only**, 3 fichiers non committés (l'humain gère TFS). `dtos-mss` : branche auto-incluse sans commit. Branche `feat/task-266-compteurs-fils-a-la-demande`.
- **LE CONSTAT.** Le serveur enrichissait **chaque** page d'en-têtes de compteurs de fils — **deux allers-retours base** — sans condition. Or `client-angular` et `client-mobile` **jettent** ces champs hors mode Conversation (`threadCountFor()` rend `undefined`, `displayedMails` ne filtre pas sur `isThreadRoot`), et le mode **Liste est le DÉFAUT**. Pour ces praticiens, **100 %** de ce travail serveur était jeté par le client. Constat fait le 2026-08-20 sur question humaine, en instruisant task-194.
- **⭐ LE MÉCANISME EST UN PARAMÈTRE DE REQUÊTE, ET LE REFUS DE L'ALTERNATIVE EST LE CŒUR DE L'ARBITRAGE.** L'hypothèse naturelle — brancher le calcul sur le réglage `MailViewMode` déjà persisté — est **fausse en l'état** : `client-blazor` n'a **aucune** notion de mode de vue et consomme `ThreadCount` en permanence. Un court-circuit piloté par le réglage lui ferait perdre ses badges de fil pour tout utilisateur en mode `List`, c'est-à-dire **par défaut tous**. Une préférence d'**affichage** d'un client ne pilote pas un **calcul** serveur partagé par trois clients. `includeThreadCounts`, **défaut `true`** : tout appelant muet garde le comportement d'aujourd'hui, l'économie est **opt-in**.
- **DEUX DÉCISIONS AU-DELÀ DE LA LETTRE DE LA US.** (1) Court-circuit sur les **DEUX** chemins de lecture (IMAP et base), pas seulement celui décrit — le faire sur un seul ferait dépendre le gain du **mode de connexion**, de façon invisible pour l'appelant, qui demande la même chose et paierait deux prix selon un état qu'il ne contrôle pas. (2) **Valeurs neutres explicites** (`1` / `true` / `false`) plutôt que les défauts de sérialisation : un `ThreadCount = 0` serait un piège pour un futur consommateur, incapable de distinguer « pas calculé » de « fil vide ». Ce sont exactement les valeurs que le comptage rend pour un message hors fil (task-268).
- **LE HARNAIS k6 FAISAIT PARTIE DU LIVRABLE, pas de la décoration.** `JOURNEY_THREAD_COUNTS` expose les **deux jambes**. Sans lui, le défaut serveur étant **compatible**, un appelant muet aurait continué de payer le calcul — et **la mesure « après » aurait été identique à la mesure « avant »**, rendant le DOD de la task invérifiable. Défaut `1` = l'appel d'avant la task à l'identique, ce qui rend la jambe « avant » comparable.
- **Tests** : 5 backend, dont le cœur — « **zéro** requête émise », assertionné sur le **repository** (`DidNotReceive()`) et non sur la réponse, parce qu'une assertion sur la réponse passerait sur du code qui **calcule puis jette**. **Constaté RED avant implémentation** (`CS1739`). Plus 2 tests d'**URL** par client, l'URL portant la déclaration. Suites : api **665/665**, application **2 163/2 163**, domain **136/136**, infrastructure **464/464**, integration **413/429** (16 skipped), mobile **763/763**, `mss-lib` **317/317**, selftest harnais 94 JS + 297 Python sans SKIP. Build api-mail 0 erreur / **0 avertissement**.
- **⚠️ UN TEST ÉCRIT PUIS RETIRÉ PARCE QU'IL NE PROUVAIT RIEN.** La passe qualité a révélé que les deux chemins produisent les valeurs neutres par des **mécanismes différents** (pose explicite côté IMAP, dictionnaires vides + défaut de `GetThreadCount` côté base) et que **rien ne surveillait** leur accord — la forme exacte de divergence que task-268 venait de fermer, rouverte par un chemin neuf. La première version du test vivait dans le projet **unitaire** et devait **stubber** la réponse du chemin base : elle **affirmait** la valeur attendue au lieu de la **constater**, et comparait mon propre stub à l'autre chemin. Retirée, réécrite en **intégration** contre le vrai repository, **mutation vérifiée**. Un test qui pose lui-même la réponse qu'il vérifie est pire qu'une absence de test : il donne le vert.
- **⚠️⚠️ DÉFAUT D'OUTILLAGE TROUVÉ SUR PIÈCE — le filtre de scope MSS de `/lint-angular` est INERTE.** La commande du playbook (`nx affected -t lint … --projects=tag:scope:mss`) **ne restreint rien** : Nx passe `--projects` **à l'exécuteur ESLint**, où il ne signifie rien. Preuve dans la sortie : `> nx run prescription:lint --projects=tag:scope:mss`, puis « Running target lint for **11 projects** ». Conséquence observée : l'auto-fixer a écrit dans **`apps/weda2`** (5 fichiers) et dans 2 fichiers `libs/mss` sans rapport — **hors charte MSS**, que la forge s'impose précisément pour ne pas toucher à la dette d'autrui. Les 7 fichiers ont été **annulés**, l'arbre remis à l'identique. Aggravant : les fixes ajoutaient des `@example` **vides**, qui ne résolvent même pas le warning. **Correction à porter dans `agents/lint-angular.md`** : `nx run-many -t lint --projects=tag:scope:mss` (ou `-p`), pas `affected --projects`.
- **⚠️ Build de production Angular cassé, et ce n'est pas cette task** : `apps/mss/src/environments/environment.prod.ts` n'existe pas sur la branche humaine `feature/nova-rewriting-mss` alors qu'il **existe sur `origin/next`**. **Contre-épreuve faite** : mes trois fichiers mis de côté (`git stash push` ciblé) + `--skip-nx-cache` → **échec identique**. `mss-lib`, où vit le code de la task, se construit sans erreur.
- **Sonar** : **zéro finding introduit**. Le seul finding sur un fichier de la task (`S138`, `LoadBulkContentLookupsAsync`) est **pré-existant** — méthode **identique au hash près** entre `develop` et la branche (`md5sum` `47ab6277…`), `git diff | grep -c` = 0 ; elle n'entre dans la fenêtre new-code que par **décalage de ligne**. `new_coverage` 88,3 % ; QG `ERROR` sur 68 `new_violations` dont 67 de tasks déjà mergées.
- **⏳ DÛ AU BANC, et la mesure sera MINORÉE.** L'ordre recommandé était **task-267 avant** : elle donne au banc un corpus **porteur de fils**. Lancée d'abord sur décision humaine, cette task se mesurera sur un corpus où `BuildMime` ne pose ni `In-Reply-To` ni `References` — le gain publié sera un **plancher** (deux requêtes dont un **scan complet de table** ramenées à **zéro**, mais sans la part de coût du comptage, vide sur ce corpus). L'erreur est **du côté sûr : on sous-promet**, et le rapport devra le dire.
- **Commits** : `0e675f4` (mécanisme + harnais), `fe89440` (passe qualité + test de convergence), `ff941d3` (mobile).

---

### v1.11 — task-076 — Sync background : parallélisation bornée, connexion IMAP poolée, throttling des notifications (2026-06-12)

- **PR** : [HealthPlatform.Api.Mail#102](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/102) — label `awaiting-human-merge`. Branche `feat/task-076-sync-background-parallelisation`. `dtos-mss` : branche auto-incluse sans commit task-076, pas de PR.
- **Findings traités** (audit perf 2026-06-10, 8 findings) :
  - **#1 enrichissement séquentiel** : split Phase A/B miroir de task-079 — Phase A = fetch IMAP séquentiel dans `BackgroundImapService` (1 commande à la fois par connexion MailKit), matérialisé en `FetchedBackgroundMail` ; Phase B = nouveau `BackgroundEnrichmentProcessor.PersistEnrichedBatchAsync` en `Parallel.ForEachAsync` borné configurable (`BackgroundSync:EnrichmentMaxDegreeOfParallelism`, défaut 4), **1 scope DI par worker** (les repositories scoped cachent un DbContext par scope — pattern de copie d'identité `BackgroundSyncManager`).
  - **#2 delete UID par UID** : `RemoveMissingUidsAsync` → 1 requête batch `DeleteMailsByUidsAsync` pour N UIDs (test le prouvant).
  - **#3 dispose/new par cycle** : `BackgroundImapConnectionRegistry` (singleton, lease exclusif par mailbox) + `BackgroundImapConnectionMaintenanceService` (keep-alive NOOP périodique, éviction idle > 60 min configurable) ; `BackgroundImapService` bascule sur `IImapClientWrapper`, probe NOOP au premier réemploi, reconnexion uniquement sur défaillance.
  - **#4 ConnectAsync par requête** : le routage par le pool (`GetOrCreateImapClientAsync`) était déjà posé par les tasks intermédiaires ; gap résiduel = keep-alive **factice** de `MailClientSession` (stub loggant un faux NOOP) → vrai `NoOpAsync` exposé sur `IImapClientWrapper` et envoyé toutes les 30 s.
  - **#5 sémaphore global** : `SemaphoreSlim(1,1)` de `MailClientSessionManager.GetOrCreateImapClientAsync` supprimé — `GetOrAdd` lock-free + verrou de création du wrapper **par session** (`MailClientSession`).
  - **#6 batches séquentiels** : Phase B parallélisée par batch + `InterBatchDelay` configurable (défaut 0, remplace le `Task.Delay(500)` codé en dur) ; pipelining inter-batch volontairement écarté (progression fausse sinon).
  - **#7 lock+ToArray par publication SSE** : `ImmutableArray` dans le `ConcurrentDictionary` des 3 brokers (`SseNotificationBroker`, `SseMailEventBroker`, `SseSyncProgressBroker`) — publication sans verrou ni copie, subscribe/unsubscribe en boucle CAS.
  - **#8 notifications par batch** : `SyncProgressNotificationThrottle` (singleton, `TimeProvider`) — max 1 notification intermédiaire/s/utilisateur, états terminaux (folder final, completed, error) toujours publiés, reset en fin de sync ; `_currentProgress` reste frais pour `/sync/status`.
- **Garde-fou anti-race** : le chemin background ne prenait pas le lock enrich-persist task-079 avant cette task — statu quo préservé (UIDs distincts par batch, dedup `AddNewMail` + isolation d'erreur par mail).
- **Tests** : 35 nouveaux — throttle (9), processor (12 : bound de parallélisme prouvé, isolation des échecs, identité copiée par scope, notifications incrémental/initial/self-action, batch delete), registry (10 : lease exclusif, réemploi inter-leases, NOOP, éviction `TimeProvider` factice, drop sur défaillance), session/manager (5 : 32 appels concurrents = 1 wrapper, NOOP réel, release en finally), + 3 intégration via le pipeline DI réel (`BackgroundSyncPipelineTests` : happy path 3 mails, 2 cycles = 1 seul ConnectAsync, interruption en cours de sync sans notification de complétion). Suites : 94 domain + 502 api + 353 infra + 1652 application verts ; intégration 224/226 — échecs = uniquement les 4 rouges pré-existants documentés, dont `PatientUseCaseTests.GetMailsByInsWithPagination` **vérifié pré-existant via stash + re-run sur branche vierge**.
- **Sonar (zero-new-debt, 2 itérations)** : 6 issues new-code fixées — S3776 + S138 sur `EnsureConnectedAsync` (fix manuel : extraction `TryReuseConnectedClientAsync`/`ConnectNewClientAsync`/`ValidateNegotiatedConnectionAsync`), S1854, S125, S103 (`SemanticSearchService`, new-code period hors task), CA2016 ×2 (dont 1 INFO legacy). Quality Gate **OK**, projet final : 0 bug / 0 vuln / 0 smell / 0 hotspot, ratings A/A/A, new_coverage 82,8 % ≥ 80, coverage projet **83,9 %**.
- **Review — suggestions non-bloquantes** : wrapper non-poolé non disposé en fin de scope sur échec terminal de connexion (chemins d'erreur font déjà `DisconnectAsync`) ; log « Session disposed » Information sur la session perdante d'une course `GetOrAdd`.
- **Commits** : b2226cd (throttle + options), 201fd41 (per-session locking + NOOP réel), 226a951 (pool + enrichissement parallèle + batch delete), 4c3deed (brokers SSE), e4faf1b + 1e1e456 (Sonar).

---

### v1.10 — task-069 — Certificats TLS : callbacks non bloquants, révocation post-handshake, grâce OCSP/CRL bornée (2026-06-11)

- **PR** : [HealthPlatform.Api.Mail#101](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/101) — label `awaiting-human-merge`. Branche `feat/task-069-tls-cert-validation-async-cache`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Arbitrage sécurité** (`questions/task-069.md`, humain 2026-06-11) : **Option C** — répondeur OCSP/CRL indisponible → cache périmé GOOD accepté 4 h après expiration (Warning PGSSI-S par acceptation dégradée), fail-close au-delà ou sans cache ; révoqué refusé immédiatement sans grâce ; timeout 5 s + 1 retry. Configurable `SslTls:RevocationDownloadTimeoutSeconds|RevocationDownloadRetries|RevocationGraceWindowHours`. Le pattern `X509Chain RevocationMode=Online` évalué et rejeté comme fallback (mêmes endpoints, bloquant, intestable).
- **Implémentation** :
  - `TlsCertificateValidationSession` (+ `ITlsCertificateValidationSessionFactory`, DI scoped) : le callback MailKit n'exécute que des checks sync sans I/O (opt-outs config, SslPolicyErrors, allowlist IGC Santé, fenêtre de validité) et capture le certificat cloné ; `ValidateCapturedAsync` exécute OCSP/CRL **post-handshake, avant toute authentification**, déconnexion si échec. Sémantique par site via `acceptWhenNoPolicyErrors` (true : `SmtpConnectionFactory`, `ImapClientTlsConfigurer` ; false : `ImapConnectionManager`, `BackgroundImapService`).
  - 4 sites débarrassés du `Task.Run(...).GetAwaiter().GetResult()` (50–500 ms de blocage thread pool par handshake) ; `IImapClientTlsConfigurer.Configure` retourne la session (callers `ImapConnectionService`, `MssAccountOnboardingService` adaptés).
  - `CertificateValidator` scindé : `ValidatePreHandshake` (sync, Result Ardalis) / `ValidateRevocationAsync` (OCSP → CRL fallback) / surcharge collection `Task.WhenAll` dédupliquée par thumbprint.
  - **🔒 Bug sécurité pré-existant corrigé** : `Success(false)` (révoqué) était traité comme un succès sur les chemins OCSP **et** CRL → certificat révoqué accepté. Révoqué = refus définitif sans fallback, prouvé par tests.
  - `OcspValidationService` : `OcspCacheEntry` (fraîcheur + grâce, prefix cache `ocsp:validation:v2:`), cache objet statique L1 des émetteurs `X509Certificate2` (zéro re-parse DER ; L2 Redis conservé), timeout/retry sur GET issuer + POST OCSP, panne Redis tolérée (online continue).
  - `CrlValidationService` : timeout 30 s → 5 s + 1 retry, last-resort périmé borné à `NextUpdate + 4 h` (Warning), TTL Redis = validité + grâce, `[ExcludeFromCodeCoverage]` retiré.
- **Tests** : 33 unitaires nouveaux/adaptés (session 13, OCSP 19 dont grâce/retry/Redis-down/cache objet, CRL 11 avec harnais `CertificateRevocationListBuilder` .NET 10, validator 16 dont parallélisme TCS et revoked refusé) + 3 intégration : pipeline DI complet (`AddApplication`) contre serveur SMTP TLS in-process — happy path, **révoqué refusé sans qu'aucun AUTH n'atteigne le serveur**, unknown fail-close. Suites : 2519 unitaires verts ; intégration 216/218 (2 échecs pré-existants documentés, vérifiés rouges sur develop vierge).
- **Sonar** : Quality Gate **OK** après 1 itération new-code (S3874 CRITICAL `out` param → Result ; CA1822 static). Projet : 0 bug, 0 vuln, 0 smell, 0 hotspot, coverage 82,8 → **83,8 %**.
- **Observations hors scope** (à trier PO) : `AutodiscoveryHelper.GetSmtpServerConfig` mappe positionnellement `userConfig.UseStartTls → useAuth2` et `userConfig.UseOAuth2 → validateServerCertificate` (mis-mapping apparent pré-existant) ; suggestion non bloquante : `emailForLogs="smtp"` dans `SmtpConnectionFactory.ConfigureClient`.
- **Commits** : c5d142b, 5ce3b0b, e373b1c, 66edad5, f0d7bb5.

---

### v1.9 — task-077 — Exports streaming EML/PDF + audit trail par lots (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#99](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/99) — label `awaiting-human-merge`. Branche `feat/task-077-exports-streaming`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Implémentation** : `StreamingFileResult` (IActionResult, RFC 5987) — EML via `MimeMessage.WriteToAsync(Response.Body)` (MailKit a déjà matérialisé le message, copies MemoryStream+ToArray supprimées), PDF via QuestPDF `GeneratePdf(Stream)` ; `IMailExportService.BuildEmlAsync → Result<MimeMessage>`, `BuildPdf → WritePdf(Stream)` ; `AuditBackgroundService` par lots (≤100, groupés par contexte transport, `AddRangeAsync` 1 SaveChanges/groupe, drain final shutdown, fallback unitaire anti-trace-empoisonnée) ; log tagging gardé `IsEnabled` ; JWT `Base64Url.DecodeFromChars`.
- **Findings 3/4 différés** (évalués) : CDA borné + API aval byte[] ; Parallel.Invoke justifié — sémantique CDA inchangée.
- **Découverte .NET 10** : `BackgroundService` lance `ExecuteAsync` de façon asynchrone — un StopAsync immédiat annule la tâche AVANT exécution du corps (status Canceled, zéro log). Les tests d'un BackgroundService doivent attendre une preuve de démarrage (log) avant StopAsync.
- **Tests** : 9 nouveaux/adaptés (identité octet-à-octet EML streamé vs bufferisé, exécution StreamingFileResult contre HttpContext réel, 10 traces → 1 AddRangeAsync, groupement, drain shutdown, fallback). Suites vertes, flaky IMAP pré-existante seule.
- **Sonar** : Quality Gate **OK** en 2 itérations (1 S125 — prose avec « ; » et motif pseudo-code).
- **Commits** : 9fac915, c5da3f3.

---

### v1.8 — task-075 — CancellationToken de bout en bout + file de background gérée (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#98](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/98) — label `awaiting-human-merge`. Branche `feat/task-075-cancellation-fire-and-forget`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Implémentation** : `BackgroundTaskQueue` (Channel unbounded, SingleReader) + `BackgroundTaskQueueHostedService` (un task tracké par item, scope DI dédié, exceptions observées centralement, in-flight attendus au StopAsync) — remplace les 3 `_ = Task.Run` nus (enrich MailController, sync BackgroundSyncManager avec token lié user+shutdown, handler Redis qui tournait sur `CancellationToken.None`) ; `MailClientSessionCleanupService` (IHostedService) héberge la boucle de cleanup des sessions IMAP ; `IBackgroundSyncManager` tokens partout, propagation SyncController→manager→ISyncStateStore ; `ClearAsync` du finally en `CancellationToken.None` explicite (le slot Redis doit se libérer même annulé) ; `RemoveMissingUidsAsync` honore le token ; `DraftCacheRepository` await au lieu de `.Result`.
- **Tests** : 7 nouveaux + 5 adaptés (`EagerBackgroundTaskQueue` reproduisant la sémantique production). Piège : les tests qui pilotaient la lambda Task.Run via un scope-factory stubé doivent passer à un double de file capturant le work item.
- **Sonar** : Quality Gate **OK** en 3 itérations (S103 ×6, S2699, CA2016 ×8 — l'analyseur vérifie le transfert des tokens fraîchement disponibles). **Piège opérationnel** : des `coverage.opencover.xml` périmés dans un `TestResults/` à la RACINE du repo (pas seulement `tests/*/TestResults`) cassent le `sonarscanner end` — purger les deux emplacements.
- **Commits** : 2911eed, 9388cc7, 772be58.

---

### v1.7 — task-074 — Caching applicatif : settings, autoconfig, patient par INS, mémo LOINC (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#97](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/97) — label `awaiting-human-merge`. Branche `feat/task-074-caching-settings-referentiels`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Implémentation** : settings 5 min (`usersettings:{userId}`) + invalidation au `SaveSettingsAsync` ; autoconfig 24 h/domaine (positifs uniquement) ; patient par INS 5 min — clé `patient:ins:{SHA-256 16 octets hex}` (INS jamais en clair, test dédié), négatifs non cachés, invalidation à `UpdateOppositionAsync` ; `DocumentCategoryCache` mémoïsation process-wide LOINC (4 call sites repositories, interop non touché) ; `SafeCacheExtensions` (panne Redis → dégradation vers la source) ; `BaseRepository` ctors DataContext acceptent un cache optionnel (testabilité).
- **Finding 5 requalifié** : `FolderCacheManager` = code mort (non enregistré, zéro consommateur — grep) ; invalidation push sans objet, GetFolders déjà traité par task-080.
- **Tests** : 11 nouveaux (hit prouvé par mutation DB directe, invalidations, clé sans INS, équivalence LOINC, 1 fetch HTTP pour 2 appels autoconfig). Suite : 2707 verts, 1 flaky IMAP pré-existante. Piège : un namespace de test `X.Services.Helpers` shadowe la résolution relative `Helpers.Type` des tests voisins — namespace aligné sur `X.Helpers`.
- **Sonar** : Quality Gate **OK** premier scan, 0 issue new-code.
- **Limites différées** : écritures patient des chemins d'ingestion (MailRepository) → TTL filet 5 min ; settings par défaut (aucune ligne) non cachés.
- **Commits** : d0bac8f.

---

### v1.6 — task-073 — DI : Kernel singleton via IHttpClientFactory, registration unique IEmailEmbeddingService (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#96](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/96) — label `awaiting-human-merge`. Branche `feat/task-073-di-httpclientfactory`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Implémentation** : client nommé `SemanticKernelOpenAI` (`IHttpClientFactory` + `SocketsHttpHandler` `PooledConnectionLifetime` 5 min — keep-alive + rotation DNS pour un client longue durée) injecté aux connecteurs chat + embeddings ; `Kernel` en vrai singleton (registration Transient mensongère corrigée — l'instance était déjà unique) ; `IEmailEmbeddingService` réduit à sa registration effective (Application, Scoped, `EmailEmbeddingService` — last-wins) ; registrations mortes retirées (`FlexibleEmbeddingService` Singleton shadowé, doublon Api).
- **Corrections d'analyse vs audit** : finding 1 surestimé (Kernel déjà construit une fois — le vrai problème était les `new HttpClient` non poolés) ; finding 3 obsolète (zéro `X509Store` dans src, cache Redis OCSP/CRL task-057, Scoped correct sinon captive dependency) ; finding 4 déjà conforme (`.Get<T>()` one-shot au démarrage) ; finding 5 hors périmètre (AppHost bootstrap one-shot).
- **Tests** : 5 nouveaux (Kernel singleton cross-scope, generator singleton, AddSemanticKernel sans registration embedding, timeout client nommé, endpoint IA TestServer avec `IEmbeddingGenerator` substitué + `EmailEmbeddingService` réel). Suite : **2699 verts, 0 échec** (même la flaky IMAP passe sur ce run).
- **Sonar** : Quality Gate **OK** en 2 itérations (S125 prose-avec-point-virgule reformulée en anglais sans ponctuation piège, CA1861 tableau constant → champ `static readonly`).
- **Commits** : b9926d5, e7b4c30.

---

### v1.5 — task-072 — Pipeline HTTP : compression Brotli/Gzip, court-circuit logging anonyme, contexte allégé (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#95](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/95) — label `awaiting-human-merge`. Branche `feat/task-072-pipeline-http-compression`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Implémentation** : `ResponseCompressionSetup.AddMssResponseCompression` (Brotli > Gzip, `Fastest`, MIME `application/json`+`problem+json`, SSE exclu) + `app.UseResponseCompression()` avant les middlewares applicatifs ; court-circuit `RequestLoggingMiddleware` pour les requêtes **sans credential** vers endpoints protégés (trace compacte Warning : méthode/path/statut/correlationId/IP — PGSSI-S conservé) ; `ServerConnectionString` singleton résolu au démarrage et injecté au ctor de `UserContextEnricherMiddleware` (plus de `GetEnvironmentVariable` par requête) ; `JsonWebTokenHandler` statique + identité PSC mémoïsée par requête (`HttpContext.Items`) ; `X-Forwarded-For` via `IndexOf` (zéro `Split`).
- **Décision BREACH** (DOD) : compression sur HTTPS acceptée — auth Bearer header (pas cookie), périmètre MIME restreint, aucun secret dans les corps JSON. Gravée dans `ResponseCompressionSetup`.
- **Note d'audit** : le token PSC (`X-PSC-Token`) n'est pas le Bearer JwtBearer — « lire depuis les claims » inapplicable ; mémoïsation par requête = même objectif (zéro re-parse).
- **Tests** : 4 TestServer (compression br vérifiée par décompression BrotliStream, SSE non compressé, 401 anonyme avec correlation, 200 authentifié — harnais précédent task-048) + 3 unitaires middleware. Le ctor de `UserContextEnricherMiddleware` prend désormais `ServerConnectionString` : 7 constructions de tests + le harnais TestServer task-048 mis à jour (`AddSingleton(new ServerConnectionString(null))`).
- **Sonar** : Quality Gate **OK** en 2 itérations (2 ASP0015 INFO sur les tests corrigées). Piège opérationnel : des `coverage.opencover.xml` périmés (branche précédente, fichier plus long) font échouer le `sonarscanner end` (`Line N is out of range`) → purger les `TestResults/` avant le cycle scanner.
- **Commits** : e38e742, ce25df6 (fix ASP0015).

---

### v1.4 — task-071 — Recherche : bornage full-text, plafonds, logs sans termes ni vecteurs (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#94](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/94) — label `awaiting-human-merge`. Branche `feat/task-071-recherche-bornage`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Findings traités** (audit perf 2026-06-10) : (1) `ExecuteFullTextSearchAsync` : 3 requêtes `ILike '%term%'` sans `Take` puis dédoublonnage entièrement en mémoire sur volume non borné ; (2) `queryVector.ToArray().Length` dans les logs = un `float[1536]` alloué par recherche et par site ; (3) intersections d'UIDs — déjà `HashSet` (constat, rien à changer) ; (4) liste patients du jour non bornée.
- **Implémentation** : `Take(maxCandidatesPerTerm)` par terme (`OrderByDescending(Uid)` = plus récents d'abord) + borne du résultat final classé par `Rank` ; nouveau `SearchLimits` (Application) : `FullTextCandidatesPerTerm=200`, `TodayPatientsMax=500`, surchargeables par appel (paramètre optionnel d'interface — c'est ainsi que les tests prouvent le bornage avec un dataset > plafond) ; `queryVector.Memory.Length` (zéro allocation) ; `GetWithMedicalDocumentsTodayAsync(maxPatients)` avec `Take` après `Distinct`.
- **PGSSI-S** : les termes de recherche étaient journalisés en clair (SearchController ×4 dont `LoggerMessage` source-généré, SemanticSearchService ×3) → longueurs uniquement. 3 tests controller prouvent qu'un terme nominatif n'atteint jamais les logs (inspection des `ReceivedCalls()` du logger substitué).
- **Divergence de ranking documentée** : terme présent dans > 200 mails → seuls les 200 plus récents candidats ; Uid IMAP croissant par dossier, le tri global approxime « plus récent » en multi-dossiers.
- **Tests** : 3 intégration (happy full-text, plafond respecté, patients du jour bornés) + 4 controller. Suites : 2700 verts, 1 flaky IMAP pré-existante. Piège : ajouter un paramètre optionnel à une interface casse les arrangements NSubstitute positionnels (`Arg.Any<CancellationToken>` se lie au nouvel `int`) — 10 arrangements mis à jour.
- **Sonar** : Quality Gate **OK**, 0 issue new-code.
- **Limites différées** : le filtrage/dédoublonnage post-requête reste en mémoire (sur volume désormais borné à 3×200) ; descente en SQL (`ts_vector`) envisageable dans une itération future.
- **Commits** : dda520a.

---

### v1.3 — task-070 — Repositories : N+1 patients, index MailPatients.Ins, split query tag (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#93](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/93) — label `awaiting-human-merge`. Branche `feat/task-070-efcore-n1-index-projections`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Findings traités** (audit perf 2026-06-10) : (1) `AnyAsync` par pièce jointe dans le chemin promote ; (2) `FirstOrDefaultAsync` patient **par document** + `SaveChangesAsync` par document dans `AddNewMail` ; (3) aucune colonne indexée sur `MailPatients.Ins` alors que tous les lookups patient filtrent dessus ; (4) `GetMailsByTagAsync` : 5 Includes collection trackés en single query (cartesian explosion) ; (5) saves multiples sur le flux d'ingestion ; (6) `PatientRepository.LoadMailsWithAttachmentsAsync` : `FirstOrDefault` dans un `Select` = O(N²).
- **Implémentation** : `LoadPatientsByInsAsync` précharge en 1 SELECT tous les patients du lot (Dictionary par INS, dédup intra-lot : 2 documents partageant un INS inédit obtiennent la **même** entité) ; rattachement par navigation `Patient` et persistance par l'unique save final de `PersistNewMailAsync` ; chemin promote : HashSet des `FileName` existants (1 SELECT) + réutilisation du change tracker (`MailPatients.Local`) ; `GetMailsByTagAsync` passe en `AsNoTracking().AsSplitQuery()` (listing read-only) ; `PatientRepository` : Dictionary O(N). Exception délibérée : les `SaveChangesAsync` de `AddPatientMessageDocumentAsync` (courrier patient) laissés intacts — scope exact de task-078 (bug UTC), évite un conflit de branche.
- **Migration** : `20260610_AddMailPatientInsIndex.cs` (FluentMigrator) — `IX_MailPatients_Ins` non-unique, `Down()` fourni, auditée règle 7c, appliquée verte sur le conteneur Testcontainers.
- **Tests** : 3 tests d'intégration (dédup patient même INS sur `AddNewMail`, tag inconnu → liste vide, caractérisation du tri antéchronologique de `GetMailsByInsAsync` avant le swap Dictionary). Déviation DOD justifiée : l'endpoint tag est un flux SSE impraticable en TestServer → couverture niveau repository, pipeline EF/PostgreSQL réel. Suites : 2696 verts, 1 flaky IMAP pré-existante documentée.
- **Sonar** : Quality Gate **OK** du premier coup — 0 issue new-code. Fait opérationnel : SonarQube écoute sur le port hôte **9001** (`SONAR_HOST_URL` du `.env`), le port 9000 est occupé par un autre process.
- **Limites différées** (findings Moyen hors DOD) : projection ciblée du listing tag (colonnes lourdes `MailContents` encore chargées), bornage `Take` sur certaines recherches, audit des autres repositories.
- **Commits** : 75ff307 (tests), 2eca9da (refactor).

---

### v1.2 — task-080 — GetFolders : réutilisation du LIST-STATUS dans le probe anti-ghost (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#92](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/92) — label `awaiting-human-merge`. Branche `feat/task-080-getfolders-double-status-probe`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Finding** (analyse locks Seq 2026-06-10) : `ProbeValidFoldersAsync` refaisait un `StatusAsync(Count)` séquentiel **par dossier sous le lock IMAP de session** pour écarter les ghost folders MSS, alors que le `LIST-STATUS` initial (RFC 5819) avait déjà ramené `Count|Unread` de tous les dossiers en un aller-retour — jusqu'à ~10,7 s de `HoldTimeMs` observés (`[ImapLock] 🔓⚠️ Lock released (long)`), bloquant `GetFolderQuery`/`FetchSingleEmail` de la même session.
- **Implémentation** : un dossier au statut peuplé (`Count >= 0`, sémantique MailKit « −1 = inconnu ») est prouvé sélectionnable → inclus sans round-trip ; ghost folders (statut jamais peuplé) → re-probe **ciblé** levant « NO Mailbox doesn't exist » (même catch `IsMailboxNotFound`) → exclus comme avant ; serveurs sans LIST-STATUS complet → re-probe limité aux seuls dossiers indéterminés, en `Count | Unread` (compteurs complets, mieux que l'ancien `Count` seul) ; `\NoSelect`/`\NonExistent` inchangés (skip sans probe). Détention du lock : N+1 round-trips → 1 (nominal) ou 1+k (k = indéterminés).
- **Tests** : 4 test-first (RED→GREEN) — zéro `StatusAsync` quand LIST-STATUS peuplé + non-régression des compteurs mappés, ghost exclu via exactement 1 STATUS, NoSelect/NonExistent sans probe, re-probe limité aux indéterminés. Pièges harness : `GetTagFoldersAsync` substitué doit retourner `[]` (défaut null → `AddRange` crash) ; ctor 3-args d'`ImapCommandException` requis pour porter « doesn't exist » dans `Message`. Suites : 2479 unitaires verts (2 flaky pré-existants documentés).
- **Sonar** : Quality Gate **OK** du premier coup — 0 issue new-code, 0 hotspot, coverage projet 84,2 %.
- **Note review (non-bloquante)** : sur un serveur sans capability LIST-STATUS où MailKit émet lui-même les STATUS pendant le listing initial, un ghost ferait échouer le listing — comportement pré-existant inchangé.
- **Commits** : 73ad93a.

---

### v1.1 — task-079 — Enrichissement IMAP : séparation fetch (Phase A) / persistance DB (Phase B) (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#91](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/91) — label `awaiting-human-merge`. Branche `feat/task-079-enrichment-lock-split-phase-ab`. `dtos-mss` : branche auto-incluse sans commit, pas de PR.
- **Origine** : ré-implémentation propre du prototype du 2026-06-04 (stash orphelin `25efd481`, inspecté read-only — develop avait divergé via task-068 et le fix sémaphores #88). **À faire au merge : `git stash drop` du prototype.**
- **Implémentation** :
  - `ImapService.EnrichEmailsAsync` découpé : **Phase A** = lock IMAP de session (clé `EnrichEmails:{folder}:{pendingUidsHash}` inchangée) limité aux I/O réseau (summaries + body parts + zips IHE-XDM matérialisés en record privé `FetchedMail`), fermeture du dossier, release par sortie de scope ; **Phase B** = `PersistEnrichedBatchAsync` (build DTO + upsert par-UID + audit + notifications) HORS lock IMAP.
  - Nouveau lock dédié `LockEnrichPersistAsync`/`UnlockEnrichPersist` (`IMailClientSessionManager`/`MailClientSessionManager`, clé `enrich:{email}:{folder}`, timeout 3 min, miroir des fetch locks) : sérialise la Phase B per-(mailbox, folder) — préserve la garantie anti-`DbUpdateConcurrencyException` du design mono-lock, release dans un `finally` (cf. #88).
  - `_enrichPersistLocks` intégré au contrat anti-fuite task-058 : reclaim par `CleanupLocksForSession` quand la dernière session de l'email disparaît ; compteur interne `EnrichPersistLockCount` pour les tests.
  - Annulation par phase : OCE en Phase A → log + return (la persistance n'est jamais entamée) ; OCE en Phase B → log + release.
  - Pré-vol extrait en `ComputePendingEnrichmentAsync` (fix S3776, complexité 16 → sous le seuil).
- **Tests** : 11 nouveaux test-first (RED compile → GREEN) — sérialisation du persist lock même (email, folder), indépendance entre dossiers et vis-à-vis du lock IMAP de session, release/réacquisition, unlock sans lock, reclaim au `RemoveSession` ; `Received.InOrder` prouvant Unlock IMAP → Lock persist, pas de persist lock sans fetch, annulation Phase A, release en `finally` sur échec DB. Suites : 2475 unitaires verts ; intégration 230/231 (flaky IMAP préexistant).
- **Sonar (zero-new-debt, 3 fixes au fil de l'eau)** : S3776 (extraction pré-vol), S103 (ligne 163 chars d'`IImapService` héritée du merge task-068, wrappée), S125 (commentaire en prose pris pour du code, reformulé). Quality Gate **OK**, 0 issue new-code, 0 hotspot, new_coverage 83,2 % ≥ 80, coverage projet 84,2 %. Les ~165 lignes new-code non couvertes restantes d'`ImapService` appartiennent au diff task-068 mergé (hors périmètre, règle 6).
- **Review — suggestions non-bloquantes** : matérialisation du batch complet en mémoire (prescrite par la US ; chunking envisageable si les syncs massives grossissent) ; TOCTOU étroit hérité du pattern task-058 sur le reclaim des locks partagés.
- **Commits** : e9ac0e7 (feature + tests), f4d46e6 (S3776 + S103), e5f5067 (S125).

---

### v1.0 — task-068 — IMAP : fetch ciblé et streaming des pièces jointes (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#90](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/90) — label `awaiting-human-merge`. Branche `feat/task-068-imap-fetch-cible-streaming-pj`. `dtos-mss` : branche auto-incluse sans commit, pas de PR (contrats inchangés).
- **Implémentation** :
  - `ImapService.GetEmailContentAsync` : fetch `BODYSTRUCTURE` + `GetBodyPartAsync` ciblé text/html — plus de `GetMessageAsync` sur le chemin d'affichage.
  - `ImapService.GetAttachmentAsync` : téléchargement de la seule body part visée ; « introuvable » mappé `NotFound` (RFC 7807 → 404).
  - Nouveau `GetAttachmentStreamAsync` + `AttachmentStreamResult` (couche Application, volontairement hors NuGet de contrats) : DB-first, write-back DB ≤ 5 Mo (`MaxDbCacheableAttachmentBytes`), streaming pur sans buffer au-delà ; endpoint `DownloadAttachment` en `FileStreamResult`.
  - Suppressions : unitaire = UID SEARCH + `MoveToAsync`/`CopyToAsync` serveur ; bulk fallback sans capability MOVE = `CopyToAsync` batch (plus de boucle fetch + append).
  - Triple allocation décodage MIME corrigée (3 sites) : `EmailAddressHelper.GetBuffer`, délégation `BackgroundImapService`, refonte `ImapService` ; reste `MailExportService.GetMessageAsync` (périmètre task-077).
- **Tests** : 14 tests unitaires dédiés (`ImapServiceTests` région task-068, assertions comportementales `DidNotReceive GetMessageAsync`), 3 tests endpoint réécrits (`FileStreamResult`, 404, 500). Suites : 2463 unitaires verts ; intégration 230/231 — `ConnectAsyncWithCancellationShouldRespectTokenAsync` flaky **préexistant sur develop** (échoue en suite complète sur arbre propre, passe en isolation).
- **Sonar (zero-new-debt, 2 itérations)** : issues new-code 27 → 0. 18 fixées par le code (S3604 ×7, S3928 ×2, S125 ×2, S1643 ×2, S1905, S1168→try-pattern `[NotNullWhen]`, S3241, S107 ×3 via `BulkDeleteBatch` + `StartSyncAsync(UserContextInfo)`) ; 3 × S107 `[LoggerMessage]` **Accepted** (1 paramètre/placeholder imposé par le générateur, contrat d'audit PGSSI-S task-048/054, justification inline) ; 6 × S3925 **FP** (sérialisation binaire obsolète SYSLIB0051, analyseur 9.9 antérieur) ; 1 bug legacy S3887 **FP** (`StopWords` est un `FrozenSet`). Hotspots new-code : 0. Ratings new-code A/A/A, duplication 0,02 %.
- **Arbitrage humain** (`questions/task-068-sonar-newcoverage.md`) : `new_coverage` 75,8 % < gate 80 % — déficit porté par les merges antérieurs (période new-code figée à la 1ʳᵉ analyse). Option 1+2 : résidu accepté (mandat campagne task-067/E009) + période re-bornée `NUMBER_OF_DAYS=30` (niveau branche `main`).
- **Fixes embarqués hors périmètre strict** : assertion `UserDatabaseName` obsolète depuis PR #75 réalignée (test rouge sur develop) ; rotation token SonarQube + `SONAR_PROJECT_KEY` corrigé dans `.env` (incidents tooling documentés dans la task).
- **Commits** : b1f08ea (feature), 9f722b3 (test #75), 3b02fc2 / 27128d0 / 94eac45 / b2a721b / 33c3463 / dad045c (Sonar new-code), merge develop 8091e17.
- **Limites différées** : libellé d'audit « MOVE » affiché même en fallback COPY (suppression unitaire) ; body parts text+html récupérées en 2 allers-retours séquentiels (batch possible) ; write-back DB sauté pour PJ > 5 Mo (re-téléchargement IMAP au prochain accès).

---

## Annexe A — Cartographie des briques applicatives

| Brique | Chemins touchés (task-068) |
|---|---|
| Endpoint mail / pièces jointes | `src/Api/Controllers/V1/MailController.cs` (DownloadAttachment → FileStreamResult) |
| Service IMAP | `src/Application/Services/Implementation/ImapService.cs` (fetch ciblé, stream, deletes serveur, `BulkDeleteBatch`) |
| Sync background | `src/Application/Services/Implementation/BackgroundImapService.cs`, `BackgroundSyncManager.cs` (`StartSyncAsync(UserContextInfo)`) |
| Helpers MIME | `src/Application/Helpers/EmailAddressHelper.cs` (décodage sans copie supplémentaire) |
| Modèle de flux | `src/Application/Models/AttachmentStreamResult.cs` (nouveau) |
| Contrats internes | `src/Application/Services/Interfaces/IImapService.cs`, `IBackgroundSyncManager.cs` |
| Locks de session (task-079) | `src/Application/Session/IMailClientSessionManager.cs`, `MailClientSessionManager.cs` (`LockEnrichPersistAsync`, dictionnaire `_enrichPersistLocks` + reclaim task-058) |
| Enrichissement deux-phases (task-079) | `src/Application/Services/Implementation/ImapService.cs` (`EnrichEmailsAsync` Phase A/B, `FetchMailBodiesAsync`, `PersistEnrichedBatchAsync`, `ComputePendingEnrichmentAsync`, record `FetchedMail`) |
| Exports streaming + audit batch (task-077) | `src/Api/Results/StreamingFileResult.cs` (nouveau), `src/Api/Controllers/V1/MailExportController.cs`, `src/Application/Services/Implementation/MailExportService.cs` + `AuditBackgroundService.cs` + `TokenValidationService.cs`, `src/Application/Consumers/AddNewMailConsumer.cs`, `src/Infrastructure/Repository/AuditTraceRepository.cs` (AddRangeAsync) |
| Background géré + annulation (task-075) | `src/Application/Services/Background/` (nouveau : queue + 2 hosted services), `src/Api/Controllers/V1/SyncController.cs` + `MailController.cs` (tokens, file), `src/Application/Services/Implementation/BackgroundSyncManager.cs` + `RedisSyncStateStore.cs` + `BackgroundImapService.cs` + `DraftCacheRepository.cs`, `src/Application/Session/MailClientSessionManager.cs` |
| Caches applicatifs (task-074) | `src/Application/Helpers/SafeCacheExtensions.cs` + `DocumentCategoryCache.cs` (nouveaux), `src/Application/Services/Implementation/AutoconfigService.cs`, `src/Infrastructure/Repository/UserSettingsRepository.cs` + `PatientRepository.cs` + `BaseRepository.cs` |
| DI Semantic Kernel (task-073) | `src/Api/Extensions/SemanticKernelExtensions.cs` (factory + singleton), `src/Api/DependencyInjection.cs` + `src/Application/Extensions/ServiceCollectionExtensions.cs` (dédoublonnage IEmailEmbeddingService) |
| Pipeline HTTP (task-072) | `src/Api/Configuration/ResponseCompressionSetup.cs` + `ServerConnectionString.cs` (nouveaux), `src/Api/Program.cs` (UseResponseCompression + singleton), `src/Api/Middleware/RequestLoggingMiddleware.cs` (court-circuit anonyme, XFF), `src/Api/Middleware/UserContextEnricherMiddleware.cs` (ctor injecté, mémo PSC) |
| Chemin recherche (task-071) | `src/Infrastructure/Repository/SemanticSearchRepository.cs` (bornage full-text, logs vecteur), `src/Application/Models/SearchLimits.cs` (nouveau), `src/Application/Services/Implementation/SemanticSearchService.cs` + `src/Api/Controllers/V1/SearchController*.cs` (logs sans termes), `src/Infrastructure/Repository/PatientRepository.cs` (patients du jour bornés) |
| Repositories EF Core (task-070) | `src/Infrastructure/Repository/MailRepository.cs` (batch patients, HashSet promote, split query tag), `src/Infrastructure/Repository/PatientRepository.cs` (Dictionary O(N)), `src/Infrastructure/Migrations/20260610_AddMailPatientInsIndex.cs` (nouveau) |
| Probe ghost folders (task-080) | `src/Application/Services/Implementation/ImapService.cs` (`ProbeValidFoldersAsync` — réutilisation LIST-STATUS, re-probe ciblé) |
| Validation certificats TLS (task-069) | `src/Application/Helpers/TlsCertificateValidationSession*.cs` + `ITlsCertificateValidationSessionFactory.cs` (nouveaux), `CertificateValidator.cs` (split pré-handshake/révocation, WhenAll), `src/Application/Services/Implementation/OcspValidationService.cs` + `CrlValidationService.cs` (grâce 4 h, timeout/retry, cache objet émetteurs) + `SmtpConnectionFactory.cs` + `ImapConnectionManager.cs` + `BackgroundImapService.cs` + `ImapConnectionService.cs` + `MssAccountOnboardingService.cs`, `src/Application/Models/OcspCacheEntry.cs` (nouveau), `src/Application/Configuration/SslTlsOptions.cs` |
| Sync background parallélisée (task-076) | `src/Application/Configuration/BackgroundSyncOptions.cs` + `src/Application/Services/Implementation/SyncProgressNotificationThrottle.cs` + `BackgroundEnrichmentProcessor.cs` + `src/Application/Session/BackgroundImapConnectionRegistry.cs` + `src/Application/Services/Background/BackgroundImapConnectionMaintenanceService.cs` (nouveaux, + interfaces), `src/Application/Services/Implementation/BackgroundImapService.cs` (wrapper + lease + Phase A/B) + `BackgroundSyncService.cs` (throttle, délai configurable) + `SseNotificationBroker.cs`/`SseMailEventBroker.cs`/`SseSyncProgressBroker.cs` (ImmutableArray), `src/Application/Session/MailClientSessionManager.cs` (GetOrAdd lock-free) + `MailClientSession.cs` (NOOP réel), `src/Application/Services/Interfaces/IImapClientWrapper.cs` + `ImapClientWrapper.cs` (NoOpAsync), `src/Api/DependencyInjection.cs` |

---

## Annexe B — Inventaire fonctionnel (2026-06-12)

- Projets de tests : 5 (domain 94, application 1652, infrastructure 353, api 502, integration 242) — 2843 tests au total sur la branche task-076.
- Qualité projet (SonarQube) : bugs 0, vulnérabilités 0, smells 0, coverage 83,9 %, duplication 0,7 %, hotspots 0 — Quality Gate OK.
- Backlog EPIC : 0 task restante — les 12 features sont implémentées (1 mergée, 11 en PR `awaiting-human-merge`). Le blocage de séquencement de task-076 a été levé le 2026-06-11 (merge task-075).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | État | Contribution | RG touchées |
|---|---|---|---|
| task-266 | done (PR api-mail #198 + mobile #62 `awaiting-human-merge`, angular code-only) | **Les compteurs de fils ne sont calculés que si un client les affiche.** Le serveur payait deux requêtes base par page d'en-têtes ; `client-angular` et `client-mobile` jetaient ces champs hors mode Conversation, et le mode Liste est le **défaut** — 100 % du travail jeté pour ces praticiens. Paramètre de requête explicite à **défaut compatible**, et NON le réglage serveur : `client-blazor` n'a aucune notion de mode de vue et y perdrait ses badges. Court-circuit sur les **deux** chemins de lecture, valeurs neutres explicites, harnais k6 exposant les deux jambes (sans quoi la mesure « après » serait identique à « avant »). 5 tests backend dont « zéro requête » assertionné sur le repository, 2 tests d'URL par client. Trouvé au passage : le filtre de scope MSS de `/lint-angular` est **inerte**. | RG-E011-01 ✅, RG-E011-02 ✅ |
| task-068 | archivée (PR #90 mergée, squash b686640) | Fetch IMAP ciblé (contenu + PJ), streaming des PJ vers HTTP, deletes MOVE/COPY côté serveur, suppression des triples allocations MIME, cleanup Sonar new-code 27→0 | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-079 | done (PR #91 `awaiting-human-merge`) | Enrichissement deux-phases : lock IMAP limité au fetch réseau, persistance DB hors lock sous lock dédié per-(mailbox, folder), contrat anti-fuite task-058, 11 tests de concurrence | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-077 | done (PR #99 `awaiting-human-merge`) | Streaming EML/PDF dans Response.Body (zéro byte[] complet), audit trail par lots avec drain shutdown et fallback unitaire, logs paresseux, Base64Url JWT, 9 tests | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-075 | done (PR #98 `awaiting-human-merge`) | File de background gérée (Channel + IHostedService, exceptions centralisées, shutdown propre), cleanup sessions en hosted service, CancellationToken de bout en bout sur la chaîne sync, 7 tests | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-074 | done (PR #97 `awaiting-human-merge`) | 4 caches applicatifs (settings + invalidation à l'écriture, autoconfig 24 h, patient INS hashé, mémo LOINC), dégradation propre sur panne Redis, 11 tests | RG-E011-01 ✅ (INS hashé), RG-E011-02 ✅, RG-E011-03 ✅ |
| task-073 | done (PR #96 `awaiting-human-merge`) | HttpClientFactory pour Semantic Kernel (client nommé, handler poolé 5 min), Kernel vrai singleton, registration unique IEmailEmbeddingService (doublons morts retirés), 5 tests DI/pipeline | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-072 | done (PR #95 `awaiting-human-merge`) | Compression Brotli/Gzip (périmètre BREACH documenté), court-circuit logging des requêtes sans credential (trace PGSSI-S conservée), connection string au démarrage, mémo PSC par requête, 7 tests | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅, RG-E011-04 ✅ (BREACH documenté) |
| task-071 | done (PR #94 `awaiting-human-merge`) | Bornage full-text (plafond 200/terme surchargeable), patients du jour plafonnés, zéro allocation vecteur dans les logs, termes de recherche jamais loggés en clair, 7 tests | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-070 | done (PR #93 `awaiting-human-merge`) | Élimination des N+1 repositories : batch patients par INS + dédup intra-lot, index `IX_MailPatients_Ins`, `AsNoTracking/AsSplitQuery` sur le listing tag, Dictionary O(N) dossier patient, 3 tests d'intégration | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-080 | done (PR #92 `awaiting-human-merge`) | Probe ghost folders sans double-STATUS : réutilisation du LIST-STATUS initial, re-probe ciblé des seuls statuts indéterminés, détention du lock GetFolders N+1 → 1 round-trip, 4 tests | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |
| task-069 | done (PR #101 `awaiting-human-merge`) | Callbacks TLS non bloquants (session par connexion, révocation OCSP/CRL post-handshake avant authentification), grâce 4 h bornée arbitrée (Option C), cache objet des émetteurs, timeout 5 s + retry, fix sécurité revoked-accepted, 33 tests unitaires + 3 intégration | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ (révocation : refus renforcé, voulu), RG-E011-04 ✅ (Option C validée humainement) |
| task-076 | done (PR #102 `awaiting-human-merge`) | Sync background parallélisée : enrichissement Phase A/B borné configurable (1 scope DI/worker), delete batch des UIDs manquants, connexion IMAP poolée par mailbox avec keep-alive NOOP et éviction idle, NOOP réel des sessions foreground, verrouillage par session (fin du sémaphore global), brokers SSE sans verrou, throttling des notifications de progression, 35 tests + 3 intégration pipeline DI | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |

---

*Vue ingénierie — la vue produit (vision, features, conformité) vit dans [E011-performance-api-mail.md](E011-performance-api-mail.md).*
