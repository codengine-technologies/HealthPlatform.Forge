# todo-task-324.md — Un client IMAP disposé pendant sa connexion ne rend plus une erreur au médecin : l'éviction respecte une session en cours d'usage

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E011
**Single frontend**: true
**Priorité**: **2** — c'est la **seule famille d'erreurs** des trois tirs `terrain` 1 000 inscrits des 18 et 19/09 (matin et soir), 16 à 18 requêtes en échec par tir de 3 h (0,008 à 0,012 %), rendues en **HTTP 500** au médecin à l'ouverture de sa boîte, et une fois sur l'archivage d'un envoi. Faible en volume, mais c'est un défaut de cycle de vie qui **augmente avec le nombre d'inscrits** (le balayage d'éviction croise d'autant plus de connexions en cours), et il pollue la lecture des taux d'erreur de chaque campagne.

> **Origine.** Consignée dans les rapports de tir des 18/09, 19/09 matin et 19/09 soir
> (`Api/Mail/tests/loadtest-k6/reports/2026-09-19/report-terrain-1000-20260919-140456.md`
> § « Analyse Seq », et le rapport `…-task322-222838.md`) : `Failed to connect to IMAP
> server`, exception `System.ObjectDisposedException: ImapClient` dans
> `ImapConnectionService.AuthenticateClientAsync` (~l. 291), sur `GET
> /api/v1/mail/folders/INBOX` (`GetFolderAsync`) et une fois dans `AppendToSentAsync`.
> Le rapport du 19/09 matin la qualifie de « défaut de cycle de vie (client disposé
> pendant une reconnexion), à instruire côté `ImapConnectionService` ». Cette US
> l'instruit. Elle n'a **aucun lien** avec le `SemaphoreFullException` de 2026-08,
> corrigé par task-223 et task-272 — la mémoire de la forge qui le disait encore
> ouvert a été corrigée le 2026-09-20.

## Revue du constat (2026-09-27)

**Toujours d'actualité.** Sur `origin/develop` d'api-mail (`dff07dce`) :

- `MailClientSession.cs` n'a pas été modifié depuis task-315 ; `MailClientSessionManager.cs` non plus
  (dernier commit : #243, task-315, 2026-09-17).
- `IsImapLinkDead` est inchangé (`ImapClientWrapperOrDefault is { IsConnected: false }`) ;
  `EvictSession` dispose toujours sans consulter le verrou ni un état « établissement en cours » ;
  le motif `expired` n'est pas protégé non plus.
- `ConnectAndAuthenticateAsync` n'a toujours **aucun** `catch (ObjectDisposedException)` : le
  `catch (Exception)` générique rend `Result.Error` → **500**.
- **Quatrième tir, même famille** : l'A/B task-323 du **21/09** (`terrain` 1 000) compte **17**
  réponses 5xx `ObjectDisposedException: ImapClient` dans `AuthenticateClientAsync`
  (`ImapConnectionService.cs:291`), identique à la référence
  (`Docs/audits/api-mail-loadtest-terrain-1000-task323-ab-20260921.md`). task-323 ne l'a pas
  affectée.

**Ce que task-171 (#248, mergée le 2026-09-26) change** — aucun tir n'a encore tourné dessus :

- **Un appel réseau s'insère au milieu de l'établissement.** En XOAUTH2, `AuthenticateClientAsync`
  demande désormais le jeton au proxy PSC (`IPscTokenProvider.GetAccessTokenAsync`) **entre** la
  connexion TCP/TLS et la commande `AUTHENTICATE`. L'établissement dure donc plus longtemps en
  production. Pendant cet appel, le client est `IsConnected: true` : le motif `disconnected` ne le
  vise pas, mais le motif `expired` le peut. La voie « état explicite d'établissement » (§2) couvre
  ce segment ; la voie « `_imapLock.Wait(0)` » ne le couvre que si le verrou est tenu pendant
  `ConnectInternalAsync` — **à vérifier par `/develop`** avant de choisir.
- **Le banc ne voit pas ce segment.** Au banc, le bypass de test authentifie l'IMAP par mot de
  passe : pas d'appel au proxy. La reproduction et la mesure au tir restent valables pour la
  fenêtre « client créé, pas encore connecté », pas pour l'appel au proxy. Le test unitaire du
  §1 doit donc couvrir les deux fenêtres (avant connexion ; entre connexion et authentification,
  avec un fournisseur de jeton factice qui attend un signal).
- **Le rendu 503 (§3) doit préserver le filtre de task-171.** Le `catch (Exception)` générique porte
  désormais `when (ex is not (UnavailableException or PscIdentityConflictException))` : ces refus
  typés remontent au `GlobalExceptionHandler` (règle 12). Le nouveau `catch (ObjectDisposedException)`
  s'ajoute **avant** le générique sans toucher à ce filtre.
- Lien avec task-319 (re-validation continue) : une `ObjectDisposedException` à l'authentification
  n'est **pas** un refus de l'opérateur et ne doit **jamais** compter comme échec d'authentification
  au registre. Si task-319 est livrée avant, ajouter ce cas à ses tests de classification ; sinon,
  task-319 le reprendra.

## Ce qui est établi, et l'hypothèse à vérifier d'abord

**Établi (trois tirs, Seq + k6)** :
- L'exception est levée sur le client IMAP **pendant l'authentification**, donc après sa création et sa connexion TCP, avant qu'il soit `IsAuthenticated`.
- Le `catch (Exception)` générique de `ConnectAndAuthenticateAsync` la transforme en `Result.Error("Erreur inattendue lors de la connexion: ObjectDisposedException")`, rendu en **500** — alors que les erreurs réseau du même chemin (socket, timeout, IO) sont rendues en **503** « réessayable ».
- Le médecin voit un échec d'ouverture de boîte ; la requête suivante réussit (la session est recréée). Sur `AppendToSent`, le message est remis mais l'archivage échoue sur cette tentative ; le rejeu borné de `SentArchiveService` (3 tentatives, task-272) le reprend normalement — à vérifier sur les traces `MailArchiveSent` du tir.

**Hypothèse d'attribution, par lecture du code et par la chronologie** — à **prouver par un test** avant tout correctif (cette EPIC a déjà payé une US écrite sur une cause supposée, task-222) :
- task-315, mergée le **2026-09-16**, a ajouté à `MailClientSessionManager.CleanupExpiredSessions` l'éviction du « lien mort » : `IsImapLinkDead` évince toute session dont `ImapClientWrapperOrDefault is { IsConnected: false }`. La famille d'erreurs apparaît au tir du **18/09**, premier tir après ce merge ; elle est absente des tirs antérieurs.
- Or un client **en cours de connexion** est exactement dans cet état : `MailClientSession` crée le wrapper (~l. 288) avant que `ConnectInternalAsync` le connecte et l'authentifie. Si le balayage passe entre les deux, `EvictSession` appelle `session.Dispose()`, qui dispose le client (~l. 175 / 647) **sous les pieds** de l'authentification en cours.
- `EvictSession` ne vérifie pas que la session est **en cours d'usage** : ni le verrou `_imapLock` (pris par l'opération), ni un état « connexion en cours ». Le keep-alive, lui, fait `_imapLock.Wait(0)` (~l. 395) avant de toucher le client ; l'éviction non.
- L'exposition croît avec le nombre de sessions établies par unité de temps (première visite de chaque médecin, reconnexions après expiration) et avec la latence d'établissement (2,4 s de p95 mesurés au tir B) : plus le handshake dure, plus la fenêtre est large.

**Ce que l'US doit établir avant de corriger** : un test qui fait passer le balayage pendant l'établissement d'une session reproduit l'`ObjectDisposedException` sur le code actuel (**rouge**), ou ne la reproduit pas — auquel cas l'attribution est fausse, et l'US s'arrête sur une `questions/task-324.md` avec les éléments (règle 7), sans correctif à l'aveugle.

## Objective

Qu'une session de messagerie **en cours d'usage** — connexion en cours, authentification en cours, ou opération IMAP sous verrou — ne soit **jamais évincée ni disposée** par le balayage de nettoyage, et qu'un défaut de cycle de vie du client IMAP, s'il subsiste, soit rendu au médecin comme une **indisponibilité transitoire réessayable**, jamais comme une erreur serveur.

Ce que cette US change pour le médecin : plus d'échec d'ouverture de boîte « au hasard », dont il ne comprend ni la cause ni la conduite à tenir. Ce qu'elle **ne change pas** : l'éviction des sessions expirées et des liens réellement morts (task-315) reste, avec ses métriques ; les contrats ne bougent pas.

### Périmètre

1. **Preuve d'abord** : test unitaire sur `MailClientSessionManager` + `MailClientSession` (projet `mss.mail.application.tests/Session/`, à côté de `MailClientSessionManagerCleanupTests`) — une session dont le client est créé et non connecté (établissement en cours, simulé par un wrapper factice dont `ConnectAsync` attend un signal), balayage `CleanupExpiredSessions` pendant l'attente, puis reprise de l'établissement : sur le code actuel, le client est disposé et l'authentification lève `ObjectDisposedException`. Log du run rouge dans le task file.
2. **L'éviction respecte l'usage** : `IsImapLinkDead` ne désigne qu'un lien **qui a été connecté puis est tombé**, pas un lien jamais établi ni en cours d'établissement. Deux voies possibles, au choix de `/develop` après lecture du code, l'une n'excluant pas l'autre :
   - un état explicite sur la session (« établissement en cours », posé par `ConnectInternalAsync` avant la création du client, levé après authentification ou échec), consulté par le balayage ;
   - le balayage tente `_imapLock.Wait(0)` comme le keep-alive, et **ne touche pas** une session dont le verrou est détenu (elle sera réexaminée au passage suivant). Attention à la sémantique : une session sous verrou depuis très longtemps est un autre défaut, à journaliser et non à évincer.
   Le même respect vaut pour l'éviction « expired » : une session expirée par inactivité mais sous verrou au moment du balayage n'est pas disposée pendant l'opération.
3. **Rendu au médecin** : dans `ConnectAndAuthenticateAsync`, `ObjectDisposedException` (et, si le code le montre nécessaire, `InvalidOperationException` de MailKit sur un client déconnecté) sont rendus `Result.Unavailable` (**503**, « réessayable »), comme les erreurs socket / timeout / IO déjà traitées, avec la trace `ImapConnect` en échec et un message sans donnée de santé. Le `catch (Exception)` générique reste pour l'inattendu.
4. **Observabilité** : un motif d'éviction `skipped-in-use` (ou équivalent) dans `MailProcessingMetrics.RecordImapSessionEvent`, pour voir au tir suivant combien de fois le balayage a rencontré une session en usage ; un log Information, sans e-mail en clair au-delà de ce que le log existant porte déjà (`Key`).
5. **Non-régression task-315** : les tests existants de l'éviction « disconnected » restent verts ; un lien **tombé après avoir été connecté** est toujours évincé au passage suivant, et la reconnexion au prochain usage fonctionne (`DeadSessionPolicyTests`, `MailClientSessionManagerCleanupTests`).

### Hors périmètre, explicitement

- La **durée d'établissement** de la session IMAP (439 ms de p50 à l'arrivée sur le tableau de bord, 2,4 s de p95) : c'est un finding de performance distinct, à instruire par la télémétrie d'établissement, pas ici.
- La **rareté de l'archivage non rejoué** : si les traces `MailArchiveSent` du tir montrent un archivage définitivement perdu après 3 tentatives, c'est une question pour `SentArchiveService`, à consigner, pas à corriger ici.
- Toute modification de `Dtos/`, des frontends, de la politique d'expiration (`MailSessionTimeouts`).

### Mesure — après, sur le tir suivant

Pas de tir dédié : la prochaine campagne `terrain` 1 000 après le merge (référence à battre :
**17** occurrences au tir A/B task-323 du 21/09, 16 à 18 aux trois tirs des 18-19/09) doit montrer **0** `ObjectDisposedException: ImapClient` dans Seq sur la fenêtre, `http_req_failed` sans cette famille, et le compteur `skipped-in-use` non nul (preuve que la fenêtre existait et a été fermée). Si le compteur reste à zéro et la famille persiste, l'attribution était fausse : rouvrir.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Preuve du ROUGE** : test « balayage pendant l'établissement » écrit d'abord, couvrant les deux fenêtres (client créé non connecté ; connecté, en attente du jeton du proxy avant `AUTHENTICATE`), échoue sur le code actuel avec `ObjectDisposedException` sur le client (log du run rouge dans le task file — mémoire `feedback-test-qui-stube-sa-propre-premisse`) ; **ou** ne reproduit pas, et l'US s'arrête sur `questions/task-324.md` sans correctif
- [ ] `CleanupExpiredSessions` n'évince ni ne dispose une session en cours d'établissement ni une session dont le verrou IMAP est détenu (motifs `expired` et `disconnected`) — ≥ 1 test par motif
- [ ] Un lien IMAP tombé **après** avoir été connecté est toujours évincé (`disconnected`) et recréé au prochain usage — tests task-315 verts, ≥ 1 test explicite de non-régression
- [ ] `ObjectDisposedException` pendant la connexion / authentification IMAP est rendue **503** (`Result.Unavailable`), plus jamais 500 — test unitaire sur `ImapConnectionService` avec un wrapper qui lève à l'authentification
- [ ] Le filtre task-171 du `catch (Exception)` générique est intact : `UnavailableException` et `PscIdentityConflictException` remontent toujours au `GlobalExceptionHandler` — tests existants de task-171 verts
- [ ] Motif d'éviction `skipped-in-use` (ou nom retenu) compté dans `MailProcessingMetrics` — test
- [ ] Le task file consigne la vérification des traces `MailArchiveSent` du tir du 19/09 soir pour l'occurrence sur `AppendToSent` : archivage rejoué avec succès, ou perdu (finding consigné)
- [ ] Aucune donnée de santé ni e-mail en clair ajouté dans les logs ou les messages d'erreur rendus au client
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché
- [ ] Le body de la PR cite la famille d'erreurs des trois tirs et l'attribution prouvée par le test rouge

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil par défaut, ou `https-load-test` du skill de banc). Avec les comptes seedés du banc, lancer l'AppHost avec `MSS_TENANT_REGISTRY_DB=mss_registry_loadtest`, sinon toutes les routes rendent 403 `MAILBOX_NOT_ATTACHED`.
- **Reproduction dirigée** (avant/après, sur la branche) : régler le timeout d'inactivité IMAP très court (configuration `MailSessionTimeouts`, ou le profil de test), ouvrir la boîte dans `client-blazor`, attendre l'expiration, puis rouvrir la boîte au moment où le balayage passe (le balayage est périodique — répéter l'ouverture une dizaine de fois). Avant le correctif : au moins une ouverture en erreur avec `ObjectDisposedException` dans Seq (`seq-local`). Après : aucune ; les événements `[CleanupExpiredSessions]` montrent le motif `skipped-in-use` quand le balayage a croisé une ouverture.
- **Lien mort toujours guéri** (task-315) : couper le service IMAP du banc (Toxiproxy, cf. mémoire « Provoquer la panne de messagerie au banc ») pendant que la boîte est ouverte, le rétablir, rouvrir la boîte : elle s'ouvre (session recréée), Seq montre l'éviction `disconnected`.
- **Rendu au médecin** : provoquer un client disposé pendant l'authentification (test dirigé ci-dessus si le correctif d'éviction est désactivé, ou test unitaire) : la réponse est 503 avec `ProblemDetails` (règle 12), le client affiche une indisponibilité transitoire, pas une erreur serveur.
- **Preuve au tir suivant** : dans Seq sur la fenêtre du prochain `terrain` 1 000, `ObjectDisposedException: ImapClient` = 0 ; `http_req_failed` sans la famille `Failed to connect to IMAP server`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de robustesse interne, aucune exigence fonctionnelle nouvelle
- **Exigences DSR honorées** : non applicable — aucun comportement fonctionnel nouveau ; effet indirect sur la disponibilité perçue de la messagerie MSSanté
- **INS** : non applicable — aucun trait d'identité manipulé
- **Authentification PS** : inchangée (PSC / e-CPS, jeton OAuth2 vers le serveur MSSanté) — l'authentification IMAP reste celle du chemin existant ; l'US ne touche que le moment où le client est disposé
- **Habilitations** : inchangées — sessions par praticien, clé `{email}_{clientSessionId}`
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `ImapConnect` en échec reste tracé (déjà le cas) ; ajout d'un motif d'éviction métrique, sans donnée personnelle nouvelle. L'archivage `MailArchiveSent` (task-223) reste tracé pour lui-même
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé, aucune donnée nouvelle stockée
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau ; réduction d'un cas où le praticien pouvait renvoyer un document déjà remis (doublon évité)

## Branches
- `api-mail` (pushed) : fix/task-324-imap-eviction-respects-in-use-session — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-324-imap-eviction-respects-in-use-session

## Timings

*(généré par `tools/timing/report.sh --task task-324 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 12 min 33 s | — | — | — | git fetch bloqué sur prompt credential GCM (~10 min) — contourné via gh auth git-credential |
| /develop | ok | 21 min 47 s | 3 (32 s) | 5 (5 min 25 s) | — | api-mail 3B/5T |
| /sonar | ok | 16 min 33 s | 2 (38 s) | 11 (7 min 05 s) | 4 (3 min 54 s) | 1 itération(s), api-mail 2B/11T, Phase 1 verte sur le code de la task ; QG projet ERROR hors task ; Phase 2 skippée |
| /lint-angular | skipped | 17 s | — | — | — | client-angular non listé ; seules modifs = environment.ts locaux de l'humain |
| /lint-mobile | skipped | 2.2 s | — | — | — | client-mobile non touché |
| /verify-visual | skipped | 1.8 s | — | — | — | aucun écran mobile touché |
| /review | ok | 17 min 05 s | 1 (11 s) | 2 (4 min 36 s) | — | api-mail 1B/2T |
| /tech-writer | ok | 2 min 28 s | — | — | — | — |
| **Total cycle** | | **1 h 10 min** | **6 (1 min 22 s)** | **18 (17 min 07 s)** | **4 (3 min 54 s)** | |

## Develop log

- Repos touched : `api-mail` (seul repo listé)
- DTOs published : no DTO change (aucune branche `dtos-mss` créée) — Interop / SDK : no change
- Commits (`api-mail`, branche `fix/task-324-imap-eviction-respects-in-use-session`) :
  - `14b8fc03` fix(session): le balayage ne dispose plus une session IMAP en cours d'usage
  - `bac8502f` refactor(session): simplify pass (/simplify)
- Local build / test : ✓ build 0 erreur ; unitaires 4 963/4 963 verts (domain 190, infrastructure 663,
  application 3 143, api 967). Intégration 594 verts / 16 ignorés / **4 rouges pré-existants** (voir plus bas).

### Preuve du ROUGE (attribution) — run sur le code d'origine (`dff07dce`, avant correctif)

Tests écrits d'abord (`tests/mss.mail.application.tests/Session/SweepDuringEstablishmentTests.cs`), à travers
le **vrai** `MailClientSessionManager` et le **vrai** `ImapConnectionService` (`ConnectAsync`, verrou compris) :

```
[FAIL] SweepDuringEstablishmentTests.Sweep_WhileTheClientIsConnecting_DoesNotDisposeIt
       Erreur inattendue lors de la connexion: ObjectDisposedException          ← fenêtre 1 (client créé, non connecté ; motif disconnected)
[FAIL] SweepDuringEstablishmentTests.Sweep_WhileAwaitingThePscTokenBeforeAuthenticate_DoesNotDisposeTheClient
       Erreur inattendue lors de la connexion: ObjectDisposedException          ← fenêtre 2 (connecté, attente du jeton PSC ; motif expired)
[FAIL] Sweep_WhenTheLockIsHeld_DoesNotEvictAnExpiredSession        Assert.NotNull() Failure: Value is null
[FAIL] Sweep_WhenTheLockIsHeld_DoesNotEvictADisconnectedSession    Assert.NotNull() Failure: Value is null
[FAIL] Sweep_WhenItMeetsASessionInUse_CountsTheSkippedInUseEvent   Collection: ["created", "disconnected"] — Not found: "skipped_in_use"
[FAIL] ImapConnectionServiceCoverageTests.ConnectInternalAsync_WhenTheClientIsDisposedDuringAuthentication_ReturnsUnavailable
       Expected: Unavailable — Actual: Error
[PASS] Sweep_ALinkThatDroppedAfterBeingConnected_IsStillEvictedAndRecreatedOnNextUse   (non-régression task-315, vert avant et après)
Échoué! - échec : 6, réussite : 1, total : 7
```

Les deux fenêtres reproduisent **mot pour mot** le message rendu en 500 aux tirs (`Erreur inattendue lors de la
connexion: ObjectDisposedException`). L'attribution à l'éviction task-315 est prouvée ; après correctif : 7/7 verts.

### Choix d'implémentation

- **Voie retenue : `_imapLock.Wait(0)` dans le balayage** (vérification demandée par la revue du 2026-09-27) : les
  ~30 appelants de `ConnectInternalAsync` détiennent **tous** le verrou IMAP de session (scan des appels ; le seul
  sans `AcquireLockAsync` à proximité, `ImapService.cs:753`, est une reprise exécutée sous le verrou déjà pris). Le
  verrou couvre donc l'établissement entier, **appel au proxy PSC compris** — un état « établissement en cours »
  séparé aurait dupliqué ce que le verrou dit déjà.
- Verrou détenu → session laissée au passage suivant, `RecordImapSessionEvent("skipped_in_use")`, log Information
  (`Key`, motif, opération détentrice) ; Warning si le verrou est détenu depuis plus de `ImapLockWaitTimeout` (120 s,
  le délai d'abandon des attentes) — journalisé, jamais évincé. Verrou obtenu → **re-examen du motif sous le verrou**,
  puis retrait du dictionnaire **avant** `Dispose` (ordre aligné sur `RemoveSession`).
- `ConnectAndAuthenticateAsync` : `catch (ObjectDisposedException)` → `Result.Unavailable` (503), trace
  `ConnectionError` ; ajouté **avant** le générique, filtre task-171 intact (tests
  `…LetsTheTypedExceptionThrough` / `…LetsTheConflictThrough` verts). Message rendu et log **sans e-mail**.
  `InvalidOperationException` MailKit non ajoutée : rien dans le code ne la montre nécessaire.
- `SessionLockReleaseMismatchTests` (task-223) : leur scénario « session recyclée sous le détenteur » passait par le
  balayage, qui ne le fait plus ; il passe désormais par `RemoveSession` (déconnexion, diffusée par task-285), qui le
  fait toujours. Les 5 garanties task-223 restent testées.
- task-319 (re-validation continue) n'est pas livrée : la classification « `ObjectDisposedException` ≠ refus de
  l'opérateur » lui revient.

### Traces `MailArchiveSent` du tir du 19/09 soir (DOD)

**Non vérifiable directement** : Seq local ne conserve plus aucun événement de la fenêtre (requête vide du
2026-09-19T18:00Z au 2026-09-20T04:00Z — rétention), et les rapports du tir (`Docs/audits/…-20260919.md`) ne
détaillent pas l'occurrence `AppendToSent`. **Par le code** : `SentArchiveService.ArchiveWithRetryAsync` rejoue
sur **tout** échec (3 tentatives, délais 2 s puis 10 s), quel que soit le statut rendu — l'occurrence a donc été
reprise par le rejeu ; un archivage définitivement perdu aurait laissé une trace « 3/3 » non consultable
aujourd'hui. **Finding** : à re-consigner au prochain tir, filtre Seq
`@MessageTemplate like '[SentArchive]%' and Attempt > 1`.

### Tests d'intégration rouges pré-existants (hors task)

4 tests « du jour » (`FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync`, `GetFolderTodayAsync_Inbox_…`,
`GetFolderNotSeenTodayAsync_Inbox_…`, `GetEmailAsync_WithFullContent_…`) rouges à 00:33 locale (jour UTC ≠ jour
local) — **rejoués sur `develop` non modifié : mêmes 4 échecs**. Pas une régression.

### Passe qualité (/simplify)

- Applied & committed : `api-mail` : 2 fichiers (`bac8502f`) — motif calculé une seule fois dans
  `EvictSessionUnlessInUse`, `heldFor` unique, constante `ImapLockWaitTimeout` partagée avec
  `LockImapClientAsync`, test task-315 resserré sur le même gestionnaire.
- La re-validation a révélé une vraie règle : `SweepDuringEstablishmentTests` capture un Meter statique →
  rattachée à `MailMetricsCaptureCollection` (scan task-291, qui ne voit que les fichiers suivis par git).
- Écartés (notés pour `/review`) :
  - `IsExpired` journalise un Warning à chaque évaluation : le re-examen sous verrou le double à l'éviction —
    correctif propre = rendre `IsExpired` pur (hors diff, change les logs existants).
  - **Suite possible (altitude)** : la déconnexion (`RemoveSession`) dispose encore une session sous son détenteur ;
    le principe général « jamais disposée sous un détenteur » se porterait dans `MailClientSession` (fermeture
    différée au dernier rendu du verrou), ce qui rendrait le `catch` 503 superflu. Changement de comportement, hors
    périmètre.
  - Factorisation des fixtures de test (`BuildService`/TLS/`ScriptedImapClient` dupliqués avec
    `ImapConnectionServiceCoverageTests`, écouteur de Meter ad hoc) — hors diff.
  - Consolidation des `catch` Timeout/IO/ObjectDisposed — niveaux de log différents.
- Skipped (contract/excluded) : dtos-mss, interop-cda, sdk non touchés.

- DOD self-check : 10/12 vérifiés par commande (build, tests, rouge, ≥1 test par motif, non-régression task-315,
  503, filtre task-171, métrique, aucun fichier `Dtos/`/frontend, pas d'e-mail ajouté) ; 1 consigné non vérifiable
  (traces `MailArchiveSent`, rétention Seq) ; 1 reporté à `/review` (body de PR).
- Next step : `/sonar task-324`

## Sonar log

- Mode A (chaîné), serveur SonarQube 25.6.0 (`sonar.token`), 2 analyses complètes sur la branche (2026-09-26 22:50Z puis re-analyse après tests).
- **Phase 1 (new code de la task) : ✓ verte.** Sur les 3 fichiers de production modifiés : **0 issue, 0 hotspot** ;
  **41/41 lignes modifiées couvertes** (ImapConnectionService 4/4, MailClientSessionManager 32/32, MailClientSession 5/5).
  Seule branche partielle : `holder?.Operation` dans la branche Warning (l. 723), où `holder` est non nul par construction.
  - 1ʳᵉ analyse : 26/32 lignes couvertes sur MailClientSessionManager (re-examen sous verrou + Warning de verrou détenu
    trop longtemps non couverts) → 2 tests ajoutés (`e7acf008`, crochet de test `MailClientSession.BackdateHolder`,
    sur le modèle de `ForceExpire`) → 32/32.
- Phase 1 — Issues fixées : 0 (aucune issue sur le code de la task) — Tests ajoutés : 2.
- **Quality Gate projet : ERROR, non imputable à la task** (période new-code = `PREVIOUS_VERSION` depuis le 2026-04-17,
  cf. mémoire « new-code period inclut des tasks déjà mergées ») : `new_violations` 91 — 68 dans `tests/loadtest-k6`,
  le reste sur des fichiers non touchés ; les 12 issues vues pour la première fois (dernière analyse : 17/09) sont
  toutes hors diff (`MailController`, `ImapService`, `report.py`, `journey.js`…) ; `new_security_hotspots_reviewed` 0 %
  — 13 hotspots, tous hors diff (Dockerfile, loadtest-k6, `BaseRepository`). Provenance vérifiée fichier par fichier.
- Phase 2 (legacy) : **skippée** (optionnelle) — elle élargirait la PR hors du périmètre de la task (règle 6).
- Build / tests : ✓ build Release 0 erreur ; unitaires verts ; intégration : 3 rouges pré-existants « du jour »
  (fenêtre 00:00-02:00 locale, rouges aussi sur `develop`).
- `conventions/csharp.md` : non alimenté — aucune règle corrigée à la main.

### KPIs qualité (baseline → final)

> Baseline = dernière analyse disponible, **`develop` du 2026-09-17** (task-188) : elle ne porte pas les tasks mergées
> depuis. Les Δ mesurent donc l'écart entre deux états du dépôt, **pas** l'effet de cette task — qui n'ajoute aucune issue.

| Métrique | Baseline (17/09) | Final (branche) | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (hors task) |
| New coverage | 87,7 % | 98,5 % | +10,8 pt |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Code smells | 250 | 89 | −161 |
| Coverage (projet) | 87,8 % | 98,0 % | +10,2 pt |
| Duplication | 0,3 % | 0,4 % | +0,1 pt |
| Reliability / Security / Maintainability | C/A/A | C/A/A | → |

## Lint log

- `/lint-angular` : **skipped — no angular change by this task.** `client-angular` absent de `**Repos**:` ; l'arbre
  `Client/Angular/front` porte 2 modifications (`apps/mss/src/environments/environment.ts`,
  `apps/weda2/src/environments/environment.ts`) — configuration locale préexistante de l'humain, non écrite par la
  forge, laissée intacte.
- `/lint-mobile` : **skipped — no mobile change.** `client-mobile` absent de `**Repos**:`, arbre propre sur `develop`.

## Visual verify log

- skipped — `client-mobile` non touché, aucun écran dans un `## Stitch design log` (task backend `api-mail` seule).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/252 — label `awaiting-human-merge`
  (branche `fix/task-324-imap-eviction-respects-in-use-session`, 3 commits : `14b8fc03` fix, `bac8502f` simplify, `e7acf008` test sonar/new)

## Code Review Summary

- **Verdict : APPROVED** — 6 fichiers relus (3 production, 3 tests), 0 bloquant, 4 suggestions.
- Validation `/review` : build 0 erreur ; unitaires 4 965/4 965 verts ; intégration 594 verts / 16 ignorés / 4 rouges
  pré-existants « du jour » (rouges aussi sur `develop`, fenêtre 00:00-02:00 locale). Un premier passage d'intégration a
  rendu 58 rouges en rafale dans les `UseCases` : saturation Docker (SonarQube + OpenSearch + Graylog + conteneurs de
  test) — rejoué après arrêt des conteneurs SonarQube démarrés par `/sonar` : 594 verts, mêmes 4 pré-existants.
- Suggestions (non bloquantes, détaillées dans la PR) : (1) la déconnexion `RemoveSession` dispose encore une session
  sous son détenteur — US de suite possible (fermeture différée dans `MailClientSession`, rendrait le `catch` 503
  superflu) ; (2) `IsExpired` journalise à chaque évaluation — le rendre pur ; (3) fenêtre résiduelle entre prise du
  verrou par le balayage et retrait du dictionnaire (pré-existante, resserrée) ; (4) fixtures de test à factoriser.
- DOD : 11/12 vérifiés par commande ; « traces `MailArchiveSent` du 19/09 soir » consigné **non vérifiable**
  (rétention Seq), avec l'analyse du rejeu par le code et le filtre à rejouer au prochain tir.
