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

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] lien IMAP mort + envoi SMTP retenu sur un signal + balayage → le `SmtpClient` n'est pas disposé, l'envoi aboutit
  - [ ] Phase B tenant `enrich:` + éviction de la dernière session → le sémaphore n'est pas disposé ; aucun second entrant concurrent ; aucune `SemaphoreFullException`
  - [ ] déconnexion (`RemoveSession`) pendant une opération tenue → la session est fermée **après** le rendu du verrou
  - [ ] `BackgroundImapService` hors ligne → aucune connexion TCP ouverte ; échec d'authentification → client disposé
  - [ ] `Client-Session-Id` contenant `_` → les verrous de ce praticien sont récupérés à l'éviction
- [ ] Test : fermeture d'une session vers un serveur muet → bornée (le balayage des autres sessions se poursuit)
- [ ] Tests `ImapConnectionService` : annulation → relancée ; hors ligne → 401 ; certificat refusé → 503
- [ ] Test d'intégration (Dovecot + relais lent, sur le modèle de `ImapSessionSweepIntegrationTests`) : envoi SMTP pendant un balayage → envoi réussi
- [ ] Non-régression task-324 et task-315 : `SweepDuringEstablishmentTests`, `ImapSessionSweepIntegrationTests`, `SessionLockReleaseMismatchTests` verts
- [ ] Métrique `skipped_in_use` étendue ou complétée pour la voie SMTP ; aucune donnée de santé ni e-mail ajouté dans les logs

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
