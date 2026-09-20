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

Pas de tir dédié : la prochaine campagne `terrain` 1 000 (celle de task-323 ou toute autre) doit montrer **0** `ObjectDisposedException: ImapClient` dans Seq sur la fenêtre, `http_req_failed` sans cette famille, et le compteur `skipped-in-use` non nul (preuve que la fenêtre existait et a été fermée). Si le compteur reste à zéro et la famille persiste, l'attribution était fausse : rouvrir.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Preuve du ROUGE** : test « balayage pendant l'établissement » écrit d'abord, échoue sur le code actuel avec `ObjectDisposedException` sur le client (log du run rouge dans le task file — mémoire `feedback-test-qui-stube-sa-propre-premisse`) ; **ou** ne reproduit pas, et l'US s'arrête sur `questions/task-324.md` sans correctif
- [ ] `CleanupExpiredSessions` n'évince ni ne dispose une session en cours d'établissement ni une session dont le verrou IMAP est détenu (motifs `expired` et `disconnected`) — ≥ 1 test par motif
- [ ] Un lien IMAP tombé **après** avoir été connecté est toujours évincé (`disconnected`) et recréé au prochain usage — tests task-315 verts, ≥ 1 test explicite de non-régression
- [ ] `ObjectDisposedException` pendant la connexion / authentification IMAP est rendue **503** (`Result.Unavailable`), plus jamais 500 — test unitaire sur `ImapConnectionService` avec un wrapper qui lève à l'authentification
- [ ] Motif d'éviction `skipped-in-use` (ou nom retenu) compté dans `MailProcessingMetrics` — test
- [ ] Le task file consigne la vérification des traces `MailArchiveSent` du tir du 19/09 soir pour l'occurrence sur `AppendToSent` : archivage rejoué avec succès, ou perdu (finding consigné)
- [ ] Aucune donnée de santé ni e-mail en clair ajouté dans les logs ou les messages d'erreur rendus au client
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché
- [ ] Le body de la PR cite la famille d'erreurs des trois tirs et l'attribution prouvée par le test rouge

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil par défaut, ou `https-load-test` du skill de banc).
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
