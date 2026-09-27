# todo-task-335.md — Une session de messagerie n'est jamais fermée pendant qu'elle sert, et sa fermeture ne bloque plus personne

**Repos**: api-mail
**Dependencies**: — (aucune ; prolonge task-324)
**Epic**: E011
**Single frontend**: true
**Priorité**: **2** — suite directe de task-324 : le balayage peut encore fermer une session **pendant un envoi SMTP** (risque de double envoi d'un courrier médical), disposer des verrous encore tenus, et la fermeture synchrone peut figer un thread de requête plusieurs minutes.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-24**, **AUD-25**, **AUD-26**, **AUD-44**, **AUD-45**,
> **AUD-46**), plus les suites notées par task-324 (`RemoveSession` dispose sous le détenteur ;
> `IsExpired` journalise à chaque évaluation).

## Ce qui est établi (develop @ `14d58398`)

1. **Voie SMTP ignorée par le balayage (AUD-24)** — `MailClientSessionManager.cs:691-713, 747-753` :
   `EvictSessionUnlessInUse` (task-324) ne teste que `ImapLock.Wait(0)`. Lien IMAP mort (motif
   `disconnected`) + envoi en cours sous `SmtpLock` → `DetachSmtpClient(quit: true)` sur le `SmtpClient`
   en plein `SendAsync`, puis `_smtpLock.Dispose()` détenu. Envoi en échec alors que le DATA a pu être
   accepté ; client authentifié adopté par une session disposée et jamais fermé.
2. **Sémaphores e-mail disposés sous leur détenteur (AUD-25)** — `:434-488, 549-621, 747-768` ;
   `ImapService.cs:1653-1685, 2031-2081, 2787-2832` : la Phase B d'enrichissement tourne sous le seul
   verrou `enrich:` ; l'éviction de la dernière session de l'e-mail le dispose ; un nouvel entrant en crée
   un neuf (course d'upsert que task-079 visait) ; le `Release` de l'ancien détenteur libère le neuf →
   troisième entrant, ou `SemaphoreFullException` en 500.
3. **Fuite de client en fond (AUD-26)** — `BackgroundImapService.cs:415-466, 531-546, 572-582` : le contrôle
   hors ligne arrive après TCP + TLS ; en `Unauthorized` ou exception post-connexion, le client n'est ni
   confié au bail ni disposé (`Dispose` fait `_imapClient = null`) — connexion TLS ouverte vers MSSanté à
   chaque cycle raté (plafond ~10 connexions par utilisateur).
4. **Fermeture bloquante (AUD-44)** — `MailClientSession.cs:640-663` : `_keepAliveTask.Wait(2 s)`,
   `Disconnect(true)` synchrone, `DisconnectAsync(true).GetAwaiter().GetResult()` ; aucun `Timeout` MailKit
   réglé (120 s par défaut). Appelé par le logout HTTP, l'ordre de fermeture diffusé et le balayage séquentiel.
5. **Clé redécoupée (AUD-45)** — `:762-768` : `LastIndexOf('_')` alors que `Client-Session-Id` peut contenir `_`.
6. **Statuts (AUD-46)** — `ImapConnectionService.cs:96-99, 132-136, 265-273` : annulation → `Result.Error`
   (500 au lieu du 499 central) ; hors ligne et certificat révoqué → 500 au lieu de 401/503.
7. **Suites task-324** : `RemoveSession` (logout) dispose encore une session sous son détenteur ;
   `IsExpired` journalise un Warning à chaque évaluation (doublé à l'éviction).

## Objective

Qu'une session — voie IMAP **ou** SMTP — ne soit **jamais disposée pendant qu'une opération la tient**,
par le balayage comme par la déconnexion ; que sa fermeture soit asynchrone et bornée ; qu'aucun client
réseau ne fuie ; et que les échecs de connexion sortent avec leur vrai statut.

### Périmètre

1. **Éviction** : une session n'est évincée que si **ses deux voies** sont libres ; ou, motif `disconnected`,
   seule la voie IMAP est remplacée — choix de `/develop`, justifié. `AdoptSmtpClient` sur une session
   disposée dispose le client reçu.
2. **Fermeture différée** : une session demandée fermée (déconnexion, balayage) pendant qu'elle est tenue
   est fermée au **dernier rendu de verrou** — le principe général « jamais disposée sous un détenteur »
   porté par `MailClientSession`. Le `catch` 503 de task-324 reste comme filet.
3. **Sémaphores e-mail** (`fetch:`, `enrich:`) : jamais disposés tant qu'ils sont tenus (comptage de
   références, ou durée de vie liée au dernier détenteur) ; libération par un jeton capturé, pas par clé.
4. **Fond** : contrôle hors ligne **avant** la connexion ; tout client non confié au bail est disposé.
5. **Fermeture asynchrone bornée** : `Timeout` MailKit explicite, annulation courte, hors du thread de
   requête ; le balayage ne peut plus être figé par un serveur muet.
6. **Session** : e-mail et identifiant de session conservés dans `MailClientSession` au lieu de redécouper la clé.
7. **Statuts** : annulation relancée (499 central) ; hors ligne → 401 ; certificat refusé → 503.
8. **`IsExpired`** sans effet de bord ; le Warning d'expiration émis une fois, à l'éviction.

### Hors périmètre

- Les fenêtres de verrou et la stratégie de pool (mémoires E011) — inchangées.
- Le multi-réplicas (task-336).

## Definition of Done

- [x] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [x] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [x] lien IMAP mort + envoi SMTP retenu sur un signal + balayage → le `SmtpClient` n'est pas disposé, l'envoi aboutit
  - [x] Phase B tenant `enrich:` + éviction de la dernière session → le sémaphore n'est pas disposé ; aucun second entrant concurrent ; aucune `SemaphoreFullException`
  - [x] déconnexion (`RemoveSession`) pendant une opération tenue → la session est fermée **après** le rendu du verrou
  - [x] `BackgroundImapService` hors ligne → aucune connexion TCP ouverte ; échec d'authentification → client disposé
  - [x] `Client-Session-Id` contenant `_` → les verrous de ce praticien sont récupérés à l'éviction
- [x] Test : fermeture d'une session vers un serveur muet → bornée (le balayage des autres sessions se poursuit)
- [x] Tests `ImapConnectionService` : annulation → relancée ; hors ligne → 401 ; certificat refusé → 503
- [x] Test d'intégration (Dovecot + relais lent, sur le modèle de `ImapSessionSweepIntegrationTests`) : envoi SMTP pendant un balayage → envoi réussi
- [x] Non-régression task-324 et task-315 : `SweepDuringEstablishmentTests`, `ImapSessionSweepIntegrationTests`, `SessionLockReleaseMismatchTests` verts
- [x] Métrique `skipped_in_use` étendue ou complétée pour la voie SMTP ; aucune donnée de santé ni e-mail ajouté dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, Toxiproxy) avec `MailServers:SessionCleanupInterval=00:00:01`.
2. Ouvrir la boîte, couper le proxy IMAP (lien mort), puis envoyer un message avec une latence SMTP de 5 s (Toxiproxy) → **Attendu** : l'envoi aboutit, un seul message reçu. Avant : échec possible et risque de double envoi au nouvel essai.
3. Se déconnecter pendant l'ouverture d'un gros dossier → la déconnexion aboutit sans erreur, la requête en cours se termine.
4. Rendre le serveur IMAP muet (Toxiproxy `timeout`) puis se déconnecter → la déconnexion répond en quelques secondes. Avant : jusqu'à ~4 minutes.
5. Passer hors ligne et laisser tourner la synchro de fond → aucune connexion IMAP ouverte vers le serveur (`netstat`).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — robustesse interne
- **Exigences DSR honorées** : non applicable — effet indirect : pas de double envoi de courrier médical, disponibilité de la messagerie
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée ; hors ligne rendu en 401
- **Habilitations** : inchangées — sessions par praticien, clé `{email}_{clientSessionId}`
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `ImapConnect` / `ConnectionError` inchangés ; événements d'éviction et de fermeture différée journalisés sans e-mail en clair
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-335-session-imap-fermee-hors-usage — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-335-session-imap-fermee-hors-usage

## Develop log

**Repo** : `api-mail` seul — branche `fix/task-335-session-imap-fermee-hors-usage`, 10 commits sur `origin/develop` (`8aa1bfcf`), poussés.

| Commit | Objet | Périmètre |
|---|---|---|
| `6c41a405` | une session n'est plus fermée sous un détenteur, voie IMAP ou SMTP | 1, 2 |
| `aa25cf44` | fermeture de session asynchrone et bornée | 5 |
| `4058f447` | `IsExpired` sans effet de bord, avertissement une fois à l'éviction | 8 |
| `2290bb14` | la session conserve e-mail et Client-Session-Id | 6 |
| `3ea9596f` | verrous par boîte `fetch:`/`enrich:` comptés et rendus par jeton | 3 |
| `b15da435` | synchro de fond : pas de connexion hors ligne, client non confié disposé | 4 |
| `e78d6beb` | `ImapConnectionService` : annulation 499, hors ligne 401, certificat refusé 503 | 7 |
| `adcb2275` | intégration : envoi SMTP pendant le balayage d'un lien IMAP mort | DOD |
| `896bb580` | intégration sans capture de métrique (garde d'architecture task-291) | DOD |
| `4c9c7d6d` | passe qualité `/simplify` | §Q |

### Choix d'éviction — attendre que les DEUX voies soient libres

Retenu : une session n'est évincée que si ni la voie IMAP ni la voie SMTP n'est tenue (une attente compte comme une détention). Écarté : remplacer la seule voie IMAP sur motif `disconnected`.

1. **Un cycle de vie unique par session** — remplacer le client IMAP en place exigerait un échange à chaud du client qu'une requête concurrente peut utiliser.
2. **Le lien IMAP mort se répare déjà** — la requête IMAP suivante se reconnecte sous le verrou (`ConnectInternalAsync`) ; l'éviction est seulement reportée, d'au plus un intervalle de balayage après la fin de l'envoi.
3. **Aucun envoi en cours n'est touché** — plus de double envoi possible.

### Mécanismes

- **Voies + fermeture différée** : `LockImapClientAsync` / `AcquireSmtpSlotAsync` entrent dans la voie (`TryEnterLane`) *avant* d'attendre le sémaphore ; le jeton en sort (`ExitLane`) *après* l'avoir rendu. `RequestClose()` (déconnexion, `Dispose`) ferme tout de suite sans détenteur, sinon au dernier `ExitLane` (événement `close_deferred`). Le balayage appelle `TryRetire`, atomique sous la même garde : détenteurs, motif réexaminé, puis refus de toute nouvelle entrée. Une entrée refusée retire *cette* session de l'index et repart sur une neuve. `AdoptSmtpClient` sur une session fermée dispose le client reçu. Le filet 503 de task-324 est conservé.
- **Fermeture bornée** : hors du fil de la requête ; les deux verrous pris (bornés), puis QUIT SMTP et LOGOUT IMAP en parallèle, chacun borné par le `Timeout` MailKit et une échéance d'annulation (5 s par défaut) ; client disposé dans tous les cas (`close_timed_out` au dépassement). Plus aucun `.Wait()` / `GetResult()` / `Disconnect` synchrone.
- **Verrous par boîte** : `MailboxLockTable` compte les références (détenteurs et attendants) ; `Reclaim` ne retire que les entrées libres, les autres au dernier rendu. `LockEmailFetchAsync` / `LockEnrichPersistAsync` rendent un `MailboxLockHandle`, rendu par jeton — plus aucune recherche par clé.
- **Métrique** `mssante_imap_session_events_total` : libellés fermés `skipped_in_use_smtp`, `close_deferred`, `close_timed_out` (`skipped_in_use` garde son sens, voie IMAP). Journaux par `SessionId` (GUID) : aucun e-mail ni donnée de santé ajouté.

### Log des runs rouges (sur le code d'avant chaque correctif)

| DOD | Test | Rouge |
|---|---|---|
| SMTP + balayage | `Sweep_DeadImapLinkWhileAnSmtpSendIsHeld_DoesNotCloseTheSmtpClientAndTheSendCompletes` | « le client SMTP a été fermé en plein envoi » |
| SMTP + balayage | `Sweep_ExpiredSessionWhileAnSmtpSendIsHeld_KeepsTheSession` | `Assert.NotNull() Failure: Value is null` |
| métrique SMTP | `Sweep_WhenTheSmtpLaneIsHeld_CountsTheSmtpSkippedInUseEvent` | `Item not found in collection ["created", "disconnected"]` |
| adoption | `AdoptSmtpClient_OnAClosedSession_DisposesTheReceivedClient` | `Assert.Null() Failure: Value is not null` |
| déconnexion | `RemoveSession_WhileAnImapOperationHoldsTheLock_ClosesTheSessionOnlyAfterTheRelease` | « la session a été fermée sous la requête qui la tenait » |
| déconnexion | `RemoveSession_WhileAnSmtpSendIsHeld_ClosesTheSmtpClientOnlyAfterTheRelease` | « la déconnexion a fermé le client SMTP en plein envoi » |
| `enrich:` | `EnrichLock_HeldWhileTheLastSessionIsEvicted_KeepsExcludingOtherEntrants` | « un second enrichissement est entré de front avec la Phase B en cours » |
| `fetch:` | `FetchLock_HeldWhileTheLastSessionIsEvicted_KeepsExcludingOtherEntrants` | « un second fetch est entré de front » |
| `enrich:` | `EnrichLock_TwoHoldersAcrossAnEviction_ReleaseWithoutSemaphoreFullException` | `System.Threading.SemaphoreFullException` |
| fond hors ligne | `Offline_OnAnOAuth2Domain_OpensNoConnectionAtAll` | `ConnectAsync` : « Actually received 1 matching call » |
| fond, fuite | `AuthenticationRefused_…`, `PscSessionGone_AfterTheConnection_…`, `CipherSuiteRefused_…` | « Expected to receive a call matching: Dispose() » |
| clé avec `_` | `Sweep_ClientSessionIdContainingUnderscores_ReclaimsThePractitionersMailboxLocks` | `Expected: 0 Actual: 1` |
| serveur muet | `Sweep_WhenOneServerIsMute_ReturnsAndClosesTheOtherSessions` | « le balayage est resté figé sur le serveur muet » |
| serveur muet | `RemoveSession_OnAMuteServer_ReturnsWithoutWaitingForTheServer` | « la déconnexion attend le serveur muet » |
| `IsExpired` | `IsExpired_EvaluatedRepeatedly_LogsNothing`, `Sweep_AnExpiredSessionStillInUse_LogsNoExpiryWarning`, `Sweep_EvictingAnExpiredSession_LogsTheExpiryWarningExactlyOnce` | `Expected: 0` / `Expected: 1` |
| statuts | `ConnectInternalAsync_WhenCancelledBeforeConnecting_…` / `…WhenCancelledDuringTheConnection_RethrowsTheCancellation` | « No exception was thrown » |
| statuts | `ConnectInternalAsync_WhenOAuth2DomainButOffline_ReturnsUnauthorizedAsync` | `Expected: Unauthorized Actual: Error` |
| statuts | `…WhenCapturedCertificateIsRevoked…`, `…WhenRevocationStatusIsUnknown…` | `Expected: Unavailable Actual: Error` |
| intégration | `SmtpSend_WhileTheSweepRunsOnADeadImapLink_IsDeliveredExactlyOnceAsync` (sur develop `8aa1bfcf`) | `ObjectDisposedException … 'SmtpClient'` dans `SmtpClient.SendAsync` |

`Close_OnAMuteServer_IsBoundedAndStillClosesTheSocket` a été écrit après le correctif (il utilise la borne interne, qui n'existait pas). `RemoveSession_WithoutHolder_ClosesTheSessionAtOnce` est une garde, verte d'emblée. Le test d'intégration est vert 3 fois de suite sur la branche.

### Tests existants modifiés

- Deux filets rendus inatteignables par la fermeture différée (`SessionLockReleaseMismatchTests`, `SmtpSessionSlotCoverageTests`) sont désormais éprouvés directement sur un sémaphore disposé, et complétés d'un test du nouveau comportement.
- Tests qui figeaient l'ancien statut 500 (annulation, hors ligne) : renommés et réécrits vers « annulation relancée » (499) / 401.
- Libération par clé → par jeton (`Unlock*ShouldIgnoreASecondRelease`, aides `MailboxLockStubs`).
- `SweepDuringEstablishmentTests` inchangé ; `ImapSessionSweepIntegrationTests` seulement enrichi ; tous verts.

### Passe qualité §Q (`/simplify`) — appliquée, re-validée verte

- **Appliqué** : fermeture IMAP/SMTP factorisée (`DisconnectWithinBoundAsync`, une échéance par étape, QUIT et LOGOUT en parallèle) ; `TryRetire` rend `(issue, motif)` au lieu d'un motif capturé ; `LockImapClientAsync` au patron `acquired + finally` ; `IsCloseRequested` en `Volatile.Read` ; `OwnerEmail`/`OwnerClientSessionId` requis (publics : CS9032) ; `BackgroundImapService` passe le client aux étapes ; `Reclaim` sans copie de clés.
- **Écarté** : table de verrous par entrée (refonte de concurrence, hors passe qualité) ; fusion des aides de rendu des jetons (changerait le comportement) ; retrait des constructeurs de test ; entrée de voie déplacée dans la session ; mutualisation d'aides de test ; fusion des deux `Unlock*` (gabarits de log distincts) et de la boucle « session en fermeture » (algorithmes différents).

### Validation

- Build `-c Release` : 0 erreur, aucun nouvel avertissement sur les fichiers touchés (Debug verrouillé par une instance locale de l'humain).
- Tests : **0 échec — 5 679 réussis, 16 ignorés** (les `UC-AI-*` d'intégration, ignorés comme avant) ; domain 190, infrastructure 665, application 3 214, api 1 005, integration 605.

### Suites possibles (hors périmètre)

- Verrous de dossier (`LockImapFolderAsync`/`UnlockImapFolder`) toujours libérés par clé — aucun appelant en production.
- `MarkLockReleased(userContext)` retrouve la session par clé : après une fermeture différée, il peut effacer le détenteur *affiché* d'une session neuve de même clé (diagnostic seulement).
- `BackgroundImapService` rend `Result.Error` pour un certificat refusé (chemin de fond, sans sortie HTTP).
- `MailboxLockTable` : une garde unique pour toute la table (au lieu de l'ancien `ConcurrentDictionary`) — sections critiques courtes, mais un point de sérialisation entre praticiens à surveiller au banc ; piste : verrou par entrée ou table indexée par e-mail.
- Tableaux de bord : exposer `skipped_in_use_smtp`, `close_deferred`, `close_timed_out`.

## Sonar log

Mode A (chaîné), branche `fix/task-335-session-imap-fermee-hors-usage` @ `4c9c7d6d`. SonarQube 9.9.8 (`sonar.login`), projet `healthplatform-api-mail`, période de new code = 30 jours (depuis le 2026-08-29 : inclut d'autres tasks mergées récemment).

- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 98,5 % (cible 95 %)
- Phase 1 — Issues traitées : 3 code smells (0 bug / 0 vuln / 0 hotspot) — 3 × S3604, **faux positifs** résolus avec justification sur le serveur (aucun changement de code)
- Phase 1 — Tests ajoutés : 0 (couverture new code déjà au-dessus de la cible)
- Phase 2 (legacy) : itérations 0 / 5 — non engagée : cibles projet déjà atteintes (bugs 0, vulnérabilités 0, maintenabilité A, couverture 98,0 %)
- Phase 2 — Issues fixées : 0
- Phase 2 — Issues restantes : 8 (best-effort acceptance) — 8 × S107 (trop de paramètres) préexistants : constructeurs DI de `BackgroundImapService`, `ImapConnectionService`, `BackgroundSyncService`, `ImapFolderService` ; méthodes de `FlagPropagationService` (×2), `ImapLockScope`, `PatientRepository`. Hors new code ; le correctif (objets-paramètres) est une refonte de conception, pas un nettoyage.
- Build / tests : ✓ green — build `-c Release` 0 erreur ; 5 passes OpenCover : domain 190, application 3 214, infrastructure 665, api 1 005, integration 605 (+16 ignorés `UC-AI-*`) — 0 échec
- Commits : aucun (aucune correction de code nécessaire) — `conventions/csharp.md` inchangé (aucune règle corrigée à la main)

| Iter | Phase | Règles | Fichiers | Issues fixed | Issues skipped | Build | Tests | KPIs après |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 (new code) | S3604 ×3 | `MailClientSession.cs` (l. 645 `_lifecycleGate`, 650 `_closed`, 820 `CloseTimeout`) | 0 — 3 résolus faux positifs | 0 | ✓ | ✓ | QG OK, new smells 3 → 0, new_coverage 98,5 % |

**Pourquoi faux positif et non correctif.** `MailClientSession` a un constructeur primaire **et** un constructeur secondaire qui chaîne sur `this(...)` : aucun constructeur n'affecte ces trois membres, l'initialiseur est leur seule affectation. Le retirer laisserait le verrou de cycle de vie et la `TaskCompletionSource` de fermeture à `null`, et la borne de fermeture à zéro (les tests et le manager s'appuient sur `DefaultCloseTimeout`). Même motif que les 13 S3604 de ce fichier déjà résolus faux positifs (task-183 et suivantes).

**Couverture new code par fichier (task-335)** : `ImapConnectionService` 100 %, `SmtpSessionSlot` 100 %, `ImapSessionLockHandle` 100 %, `MailboxLockHandle` 96,1 % (3 lignes), `MailClientSessionManager` 96,0 % (4 lignes, 3 conditions), `MailClientSession` 93,8 % (5 lignes, 8 conditions) — sous la cible au niveau du fichier, au-dessus au niveau du projet.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98,8 % | 98,5 % | −0,3 pt |
| New bugs / vulnerabilities / code smells | 0 / 0 / 0 | 0 / 0 / 0 | → (3 S3604 apparus au scan de la branche, résolus faux positifs) |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 8 | 8 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 pt |
| Duplication | 0,5 % | 0,5 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

Baseline = dernière analyse présente sur le serveur avant ce run (analyse du 2026-09-27 17:18 UTC, d'une autre lignée) ; final = analyse de la branche (2026-09-27 19:37 UTC) après résolution des trois faux positifs.

## Timings

*(généré par `tools/timing/report.sh --task task-335 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 4.9 s | — | — | — | — |
| /develop | ok | 1 h 04 min | 9 (58 s) | 29 (12 min 33 s) | — | api-mail 9B/29T, api-mail — 8 points + intégration, passe qualité appliquée |
| /sonar | ok | 8 min 26 s | 1 (18 s) | 5 (3 min 10 s) | 2 (36 s) | 1 itération(s), api-mail 1B/5T, Phase 1 : 3 S3604 faux positifs résolus, QG OK ; Phase 2 non requise |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non listé dans Repos |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non listé dans Repos |
| /verify-visual | skipped | 0.5 s | — | — | — | aucun écran client-mobile touché |
| /review | ok | 7 min 53 s | 1 (2.0 s) | 1 (2 min 06 s) | — | api-mail 1B/1T, PR api-mail #256 |
| /tech-writer | ok | 1 min 04 s | — | — | — | E011 v1.17 |
| **Total cycle** | | **1 h 22 min** | **11 (1 min 18 s)** | **35 (17 min 51 s)** | **2 (36 s)** | |

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/256 — label `awaiting-human-merge` (branche `fix/task-335-session-imap-fermee-hors-usage`, synchro develop sans conflit)

## Code Review Summary

**APPROVED** — 0 bloquant ; build 0 erreur, tests 0 échec (5 679 réussis, 16 ignorés). Revue centrée sur la concurrence : comptes de voie équilibrés, décisions de fermeture atomiques, pas d'interblocage, sémaphores jamais disposés sous détenteur, index qui ne retire jamais une session neuve, 499 réservé à l'annulation du jeton de requête.

Suggestions non bloquantes :
1. **(task dédiée recommandée)** Un attendant du verrou au moment de la déconnexion recrée par clé une session neuve (`ConnectInternalAsync` → `GetOrCreateImapClientAsync(key)`) en tenant le verrou de l'ancienne : connexion authentifiée qui survit à la déconnexion jusqu'à expiration ; si le même Client-Session-Id revient, deux opérations possibles sur le même `ImapClient`. Préexistant pour un détenteur, plus fréquent maintenant. Piste : résoudre le client depuis la session dont la voie est tenue.
2. `StopKeepAliveAsync` : tâche keep-alive annulée avant démarrage = « arrêtée » (Warning parasite sinon).
3. Observer les tâches de déconnexion abandonnées après l'échéance.
4. `ExitLane` : assertion/journal au lieu de `Math.Max(0, …)`.
5. `RequestClose` à trois états (`close_deferred` compté seulement sur un vrai report).
6. `try/finally` autour du rendu du verrou distribué dans `ReleaseFetchLocksAsync` (préexistant).
7. Tests manquants : attendant bloquant `TryRetire`, entrant redirigé vers une session neuve, OCE hors jeton → `Result.Error`, annulation dans `BackgroundImapService`.
8. Surveiller au banc la garde unique de `MailboxLockTable`.
