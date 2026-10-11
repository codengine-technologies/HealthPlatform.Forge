# todo-task-365.md — Embarqué dans Weda : les sessions IMAP ne s'empilent plus à chaque rechargement de l'iframe, et weda2 quitte l'application quand Weda ferme la session

**Repos**: api-mail, client-angular
**Dependencies**: — (aucune ; constat fait pendant `/e2e task-364`)
**Epic**: E019
**Single frontend**: true — seul weda2 est embarqué dans Weda. L'éventuel correctif backend
(fermeture ou reprise de session) vaut pour tous les clients, mais le déclencheur est l'iframe.
**Priorité**: **1** — risque de panne en production. Un médecin qui navigue dans Weda peut épuiser
la limite de connexions IMAP de son compte chez l'opérateur MSSanté. Sa messagerie tombe alors
en « boîte momentanément indisponible », sans cause visible.

> **Origine.** Constaté le 2026-10-10 pendant `/e2e task-364`, puis analysé dans Seq. Le filet e2e
> joue tous ses tests avec un seul praticien, et chaque test ouvre une nouvelle session
> navigateur. La voie Angular a franchi le plafond Dovecot du banc
> (`mail_max_userip_connections = 100`) : 107, puis environ 100 connexions IMAP neuves en
> 5 minutes. Dovecot a alors coupé les connexions suivantes (`SocketException 10053` en plein
> TLS, côté api-mail).
>
> Le plafond du banc a été relevé à 1000 pour débloquer le filet (api-mail `ca7e9e0a`, task-364).
> C'est un **contournement**. Le phénomène de fond, l'**empilement de sessions IMAP**, existe en
> production dès que la page est rechargée souvent. Or l'iframe Weda est rechargée à **chaque**
> changement de page Weda.

## Ce qui existe (constaté dans le code le 2026-10-11)

- **client-angular** — `libs/mss/src/core/stores/mailbox-session.store.ts` :
  - `Client-Session-Id` est un `crypto.randomUUID()` tiré **en mémoire** à l'ouverture d'une
    boîte (`rotateSessionId()`). Chaque chargement de l'application, donc chaque rechargement de
    l'iframe, présente un nouvel identifiant.
  - `MAILBOX_SESSION_CLOSER` (fourni par `apps/weda2/src/app/app.config.ts`) ferme la session à
    la déconnexion et au changement de boîte, **pas** à la sortie de la page. Aucun `pagehide`,
    `beforeunload` ni `sendBeacon` dans `libs/mss` ou `apps/weda2`.
- **api-mail** :
  - une session IMAP est poolée par `(utilisateur, Client-Session-Id)`
    (`Application/Session/MailClientSessionManager.cs`, `MailClientSession.cs`) ;
  - sous charge, elle peut exister sur **plusieurs réplicas**, et l'envoi a sa propre voie
    d'écriture (task-213). Une session navigateur peut donc tenir plusieurs connexions ;
  - `ImapIdleTimeout = 00:05:00`, `ImapKeepAliveInterval = 00:00:30` (`Api/appsettings.json`).
    Une session abandonnée garde sa connexion **au moins 5 minutes**. À vérifier : le NOOP de
    keep-alive repousse-t-il l'expiration ? Si oui, l'abandon n'expire jamais tant que le
    réplica vit.
- **Weda** (`/FolderMedical/WedaEchanges/`, `NovaMssHost`) : l'iframe est recréée à chaque page
  Weda qui l'affiche. Rien ne prévient weda2 qu'il va être déchargé.

## Objective

Établir, chiffres à l'appui, combien de connexions IMAP un médecin réel accumule chez son opérateur
en naviguant dans Weda, puis faire en sorte que ce nombre **reste borné** quel que soit le nombre de
rechargements.

### 1. Analyse (avant tout correctif, livrée dans le `## Develop log`)

1. **Mesurer** sur l'AppHost de dev, embarqué dans Weda :
   - ouvrir Weda Échanges, naviguer N fois entre pages Weda (N = 10, 30), et relever les
     connexions ouvertes ;
   - sources : `doveadm who` sur le Dovecot local, et les événements `🌱 New ImapClient` / fermeture
     dans Seq, avec le nombre de `Client-Session-Id` distincts ;
   - relever le temps réel de libération d'une session abandonnée : 5 min, plus, ou jamais avec le
     keep-alive.
2. **Établir les limites des opérateurs MSSanté** visés (opérateur de l'ANS en priorité) :
   connexions IMAP simultanées par compte, et comportement au-delà (refus, coupure). Si
   l'information n'est pas publique, le noter et dimensionner sur l'hypothèse prudente (10).
3. **Comparer les pistes de correctif** et en **proposer une** à l'humain avant de coder. Pistes à
   instruire au minimum :
   - **A. Reprendre la session au rechargement** : garder `Client-Session-Id` dans le
     `sessionStorage` de l'iframe (par boîte), pour qu'un rechargement réutilise la session et sa
     connexion. Points à vérifier : portée du `sessionStorage` dans une iframe recréée, sécurité
     (l'identifiant n'est pas un secret d'authentification), règle 409 `SESSION_MAILBOX_MISMATCH`.
   - **B. Fermer la session en quittant la page** — **retenue par l'humain le 2026-10-11, à livrer
     quelle que soit l'issue de l'analyse** (voir « 2. Correctif », B obligatoire). Au `pagehide`,
     `fetch(..., { keepalive: true })` vers `POST /api/v1/sync/logout`, la route qui existe déjà.
     **Pas `navigator.sendBeacon`** : il ne pose pas l'en-tête `Authorization`, et api-mail exige le
     jeton Bearer. Limite : best-effort, perdu si l'onglet est tué (C reste le filet).
   - **C. Borner côté serveur** : plafond de sessions par utilisateur (éviction de la plus
     ancienne), et/ou keep-alive qui ne prolonge pas une session sans requête client.
     Protège aussi les autres clients.
   - Une combinaison (par exemple A + C) est probablement la bonne réponse : A supprime la cause
     dans Weda, C garantit la borne quoi qu'il arrive.

### 2. Correctif (après arbitrage humain de la piste)

**B obligatoire, décidé par l'humain le 2026-10-11.** Il ferme aussi la session de messagerie
quand l'iframe disparaît à la déconnexion de Weda : la page quitte Weda Échanges, et rien ne
prévenait api-mail jusqu'ici. Le fonctionnement :
- dans `apps/weda2` (ou `libs/mss`, au plus près de `MAILBOX_SESSION_CLOSER`), un écouteur
  `pagehide` envoie `fetch(\`${mssApiUrl}/api/v1/sync/logout\`, { method: 'POST', keepalive: true,
  credentials: 'include', headers })` ;
- l'intercepteur Angular ne s'applique pas à ce `fetch` : les en-têtes sont posés **à la main**,
  les mêmes que `mss-headers.interceptor.ts` :
  - `Authorization: Bearer {jeton d'accès en mémoire}` ;
  - `Client-Email` : la boîte ouverte ;
  - `Client-Session-Id` : l'identifiant de session de la boîte ;
- rien n'est envoyé sans boîte ouverte ni jeton ;
- `pagehide` avec `event.persisted === true` (page mise en cache arrière, bfcache) : la session
  est fermée aussi, puis **rouverte au `pageshow`** suivant (nouvel identifiant, comme une ouverture
  de boîte). Sinon une page restaurée parlerait avec une session fermée ;
- en mode autonome comme en mode embarqué : une fermeture d'onglet libère aussi la connexion ;
- le corps reste vide (`keepalive` limite le corps à 64 Kio) ;
- un échec n'est ni affiché ni réessayé : la page s'en va. Le filet serveur (expiration, piste C)
  reste.

A et C restent à arbitrer après l'analyse.

### 3. Surveillance de la session partagée (décidé par l'humain le 2026-10-11)

**Constat.**
- Weda, weda2 dans l'iframe et weda2 dans un onglet à part partagent **une seule session du proxy**,
  le cookie `proxy_session_id`, posé sur `.weda.fr` en production.
- La déconnexion de Weda révoque cette session : `DELETE /auth/logout`, depuis `MasterNavigate`
  et `logout-helper.js`.
- weda2 ne le sait pas. Ses jetons sont en mémoire, et api-mail les valide localement, jusqu'à
  `exp` + 2 min. Il ne surveille pas le proxy et ne rafraîchit qu'à la demande.
- Un onglet weda2 reste donc utilisable après la déconnexion de Weda, et son flux SSE reste
  ouvert.

**Attendu.** Quand Weda ferme la session, weda2 quitte proprement l'application, sur une réponse
« pas de session » de `GET {authEndpoint}/session/has-session`.

- **Quand vérifier** :
  - toutes les **60 s** (réglable dans `environment*.ts`), tant que l'utilisateur est
    authentifié ;
  - et **aussitôt** au retour sur l'onglet (`visibilitychange` vers `visible`, et `focus`).
  - Une seule vérification à la fois. Aucune pendant l'amorçage, la connexion ou une
    déconnexion déjà en cours.
- **Comment lire la réponse** (constaté dans `psc-auth-proxy`, `SessionController.HasSession`) :
  - **pas de session** : `200` au corps vide (cookie absent, session absente de Redis, jeton de
    rafraîchissement expiré). Seul `{ hasActiveSession: true }` vaut « session active » ;
  - **une erreur réseau, un 5xx ou un délai dépassé ne déconnectent pas** : on garde l'état, et la
    vérification suivante tranche. Comme la surveillance de session de Weda, on échoue ouvert.
    `$hasSession()` actuel rend `false` sur une erreur : la surveillance a besoin d'une variante
    qui distingue « pas de session » de « erreur ».
- **Quitter proprement, sur « pas de session »**, dans cet ordre :
  1. fermer la session de messagerie (`POST /api/v1/sync/logout`, par `MAIL_SESSION_CLOSER`).
     Le jeton Bearer est encore accepté par api-mail : c'est lui qui authentifie l'ordre ;
  2. fermer les flux SSE ouverts : événements de la boîte, notifications, assistant ;
  3. vider l'état d'authentification ;
  4. puis, selon le mode :
     - **autonome** : le chemin existant de perte de session (`redirectToLoginOnSessionLoss`,
       puis `/logout`). Le `DELETE /auth/logout` du proxy, alors sans objet, échoue en
       silence ;
     - **embarqué** : `$logout()` ne révoque rien (la session appartient à Weda), et l'hôte est
       prévenu par l'événement `session-expired`, qui existe déjà. Aucune redirection dans
       l'iframe.
- **Vérifier aussi À QUI appartient la session** (décidé par l'humain le 2026-10-11) :
  - **Pourquoi.** Le cookie `proxy_session_id` est commun à Weda et à weda2. Un poste de cabinet
    est souvent partagé :
    1. le Dr A se déconnecte de Weda, mais laisse un onglet weda2 ouvert ;
    2. le Dr B se connecte à Weda sur le même navigateur. Le proxy pose un **nouveau** cookie,
       celui de B, sur le même domaine ;
    3. le `has-session` de l'onglet de A répond alors « active », et weda2 continuerait d'afficher
       la messagerie de A avec ses jetons en mémoire.
  - **Comment.**
    - Au **retour sur l'onglet** (`visibilitychange` vers `visible`, et `focus`), quand
      `has-session` répond « active », weda2 lit `GET {authEndpoint}/auth/userinfo`
      (`$getUserInfo()`, qui existe déjà) et compare son `sub` à celui de l'utilisateur en cours.
      C'est le seul moment où un changement d'utilisateur devient visible : B s'est connecté
      depuis un autre onglet.
    - **Ne pas utiliser `POST /session/token`** : à chaque appel, le proxy rafraîchit les jetons
      auprès de Keycloak et de PSC et réécrit la session (`SessionController`). Un appel par
      minute ferait tourner les jetons de rafraîchissement en concurrence avec ceux de Weda.
      `/auth/userinfo` est en lecture seule.
    - Pas de vérification d'identité sur le minuteur de 60 s : elle interroge Keycloak, et
      `has-session` suffit à détecter une déconnexion.
  - **Sur un `sub` différent** :
    1. fermer la session de messagerie de l'utilisateur précédent, avec **son** jeton, encore
       accepté ;
    2. fermer les flux SSE et vider l'état ;
    3. **recharger l'application** (`location.reload()`), dans les deux modes. L'amorçage reprend
       sur la session de B, et le mécanisme de task-052 (`last_authenticated_sub`) s'applique.
  - Une erreur de `/auth/userinfo` ne déconnecte pas et ne recharge pas : la vérification suivante
    tranche.
  - **Évolution possible, hors task** : que `has-session` renvoie le `sub`, lu dans Redis sans appel
    à Keycloak. Cela modifie le proxy (`psc-auth-proxy`, dépôt hors forge).
- **Journal** : la sortie est journalisée côté client avec sa cause (« session du proxy absente » ou
  « utilisateur différent »), sans identifiant de session, ni `sub`, ni adresse.
- **Charge** : le proxy journalise chaque `has-session` au niveau Information. À 60 s par onglet,
  c'est le même ordre que la surveillance de Weda (`/session/introspect` toutes les 60 s). Le
  signaler dans le `## Develop log` ; on ne change pas le proxy dans cette task.

- Le nombre de connexions IMAP d'un praticien reste **borné** (cible à fixer par l'analyse,
  ≤ 3 par réplica actif par exemple) après 30 rechargements de l'iframe.
- Aucune régression : changement de boîte (rotation + 409), déconnexion, plusieurs onglets réels.

## Definition of Done

- [ ] `## Develop log` : mesures avant correctif (connexions après N rechargements, délai réel de
      libération), limite opérateur documentée ou hypothèse explicite, pistes comparées, piste
      retenue **par l'humain** (encadré « arbitrage humain requis » avant le code)
- [ ] Correctif livré selon la piste retenue, mesures **après** au même protocole
- [ ] api-mail : tests d'intégration d'endpoint qui prouvent le comportement (reprise, fermeture ou
      plafond), vus rouges avant le correctif (règle 1b)
- [ ] client-angular : tests de composant ou de store pour la conservation ou la fermeture de session
- [ ] client-angular — **fermeture au `pagehide` (B, obligatoire)**, tests unitaires rouges d'abord :
  - [ ] `pagehide` avec une boîte ouverte : un `fetch` `POST …/api/v1/sync/logout` part avec
    `keepalive: true` et les en-têtes `Authorization`, `Client-Email` et `Client-Session-Id` ;
  - [ ] **`navigator.sendBeacon` n'est pas utilisé** ;
  - [ ] sans boîte ouverte, ou sans jeton : rien n'est envoyé ;
  - [ ] `pagehide` persisté puis `pageshow` : la session est rouverte sous un nouvel identifiant ;
  - [ ] un échec du `fetch` ne lève rien et n'affiche rien.
- [ ] client-angular — **surveillance de la session partagée (§ 3)**, tests unitaires rouges d'abord :
  - [ ] une vérification toutes les 60 s quand authentifié, et une au retour sur l'onglet
    (`visibilitychange`, `focus`) ; aucune avant l'authentification, ni pendant une déconnexion ;
    jamais deux en parallèle ;
  - [ ] un `200` au corps vide déclenche la sortie : fermeture de la session de messagerie
    **avant** la purge des jetons, fermeture des flux SSE, purge ;
  - [ ] `{ hasActiveSession: true }` ne fait rien ;
  - [ ] une erreur réseau, un 5xx ou un délai dépassé ne déconnectent pas ;
  - [ ] en mode autonome, la sortie passe par `/logout` ; en mode embarqué, l'hôte reçoit
    `session-expired`, sans redirection dans l'iframe et sans `DELETE /auth/logout` ;
  - [ ] la surveillance s'arrête après la sortie (aucune vérification ne repart) ;
  - [ ] **identité** : au retour sur l'onglet, `/auth/userinfo` est lu. Un `sub` identique ne fait
    rien. Un `sub` différent ferme la session de messagerie avec le jeton de l'utilisateur
    précédent, vide l'état, puis recharge l'application. Une erreur ne fait rien ;
  - [ ] `POST /session/token` n'est jamais appelé par la surveillance, et `/auth/userinfo` ne l'est
    pas par le minuteur de 60 s.
- [ ] Scénario E2E au catalogue : « la session fermée par Weda fait quitter weda2 ». Une fois la
  session du proxy révoquée en dehors de weda2, un retour sur l'onglet affiche la sortie, et la
  session de messagerie est fermée côté api-mail. Il est joué en `headless` si le banc e2e passe
  par le proxy. Sinon, il est catalogué en mode `humain`, avec la raison.
- [ ] Scénario E2E : quitter la page (navigation de l'hôte, ou fermeture de l'onglet) ferme la
  session côté api-mail. L'événement de fermeture est visible dans le journal d'audit
  (`MailboxSessionClosed`), et la connexion IMAP est libérée sans attendre l'expiration
- [ ] Scénario E2E au catalogue (`Api/Mail/e2e/scenarios.yml`) : rechargements répétés de l'iframe,
      nombre de connexions borné. Implémenté dans la suite Angular (voie Weda)
- [ ] Le plafond du banc peut alors **redescendre** (`mail_max_userip_connections`, aujourd'hui
      1000 depuis task-364) sans que le filet ne tombe. À tenter, et le résultat consigné
- [ ] Aucune donnée de santé ni identifiant de session dans les journaux ajoutés

## Manual Test Plan

1. Weda Échanges ouvert, AppHost de dev, Seq : naviguer 30 fois entre pages Weda.
2. `doveadm who` (ou Seq) : le nombre de connexions du praticien reste sous la borne.
3. Revenir sur Weda Échanges : la messagerie s'ouvre sans « boîte momentanément indisponible ».
4. Changer de boîte dans weda2, puis se déconnecter : les sessions correspondantes sont fermées.
5. **Déconnexion de Weda** depuis Weda Échanges (bouton « Déconnexion ») : dans l'onglet Réseau
   de l'iframe, `POST /api/v1/sync/logout` part, avec l'en-tête `Authorization`. Dans Seq, la
   session est fermée tout de suite, sans attendre les 5 minutes d'inactivité.
6. **weda2 en onglet à part**, fermer l'onglet : même constat.
7. **Déconnexion de Weda, weda2 ouvert dans un onglet à part** (« Ouvrir dans un onglet ») :
   - se déconnecter de Weda dans l'onglet Weda ;
   - revenir sur l'onglet weda2 : il quitte l'application tout de suite, et affiche l'écran de
     connexion ;
   - sans y revenir, la sortie a lieu en moins de 60 s ;
   - dans Seq, la session de messagerie est fermée.
8. **Coupure réseau** de quelques minutes (mode avion, ou proxy arrêté) : weda2 ne se déconnecte
   pas. Au retour du réseau, il continue normalement.
9. **Session expirée dans l'iframe** : révoquer la session depuis un autre onglet, puis revenir
   sur Weda Échanges. Le bandeau « Votre session a expiré » de la page hôte s'affiche.
10. **Changement d'utilisateur sur un poste partagé** :
    - le Dr A ouvre weda2 dans un onglet à part, puis se déconnecte de Weda dans un autre onglet ;
    - le Dr B se connecte à Weda dans ce même onglet Weda ;
    - revenir sur l'onglet weda2 : il ne montre **jamais** la messagerie de A. Il se recharge sur
      la session de B, ou affiche l'écran de connexion ;
    - dans Seq, la session de messagerie de A est fermée.

## Conformité santé / Ségur / ANS

- Disponibilité de la messagerie sécurisée : un praticien ne doit pas perdre l'accès à sa boîte
  par un effet de bord de la navigation dans son logiciel.
- Usage raisonnable de l'infrastructure de l'opérateur MSSanté : pas de connexions orphelines.
- Aucune donnée de santé manipulée par la correction (sessions et connexions seulement).
