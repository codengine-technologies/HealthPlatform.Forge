# todo-task-365.md — Embarqué dans Weda : les sessions IMAP ne s'empilent plus à chaque rechargement de l'iframe, et weda2 quitte l'application quand Weda ferme la session

**Repos**: api-mail, client-angular
**Dependencies**: — (aucune ; constat fait pendant `/e2e task-364`)
**Epic**: E019
**Single frontend**: true — seul weda2 est embarqué dans Weda. L'éventuel correctif backend
(fermeture ou reprise de session) vaut pour tous les clients, mais le déclencheur est l'iframe.
**Priorité**: **1** — risque de panne en production. Un médecin qui navigue dans Weda peut épuiser
la limite de connexions IMAP de son compte chez l'opérateur MSSanté. Sa messagerie tombe alors
en « boîte momentanément indisponible », sans cause visible.

> **Arbitrage humain du 2026-10-18 : pistes D + C retenues.** La clé du pool de sessions dérive de
> la session du proxy (`proxy_session_id`), calculée par api-mail (piste D), et le serveur borne le
> nombre de sessions (piste C). La piste A est abandonnée : D la rend inutile. La piste B (décision
> du 2026-10-11) est **restreinte au mode autonome** : en mode embarqué, fermer au `pagehide`
> fermerait à chaque navigation Weda le pool que l'iframe suivante reprend. Voir « 2. Correctif ».

> **Arbitrage humain du 2026-10-18 (après revue de code, `questions/answered/task-365.md`).**
> - **La piste B est retirée.** Avec D, une seule session de messagerie est partagée par Weda,
>   l'iframe et l'onglet weda2 : fermer au `pagehide` coupait la session de l'iframe, et un F5 pouvait
>   fermer la session que la page rechargée venait de reprendre. Un onglet fermé laisse sa session
>   expirer (5 à 6 min), dans la limite du plafond par boîte (C).
> - **Après une déconnexion de Weda, on s'en remet à l'expiration.** psc-auth-proxy efface le cookie
>   `proxy_session_id` : un ordre de fermeture parti ensuite ne vise plus la bonne session et
>   écrirait une trace fausse. La surveillance du § 3 fait quitter weda2 **sans** ordre de
>   fermeture. Il en va de même au changement de praticien : la session de A expire seule.
> - Ces deux points remplacent les passages correspondants du § 2 (B) et du § 3 (étape 1 de la
>   sortie, étape 1 du changement d'utilisateur), ainsi que les lignes de DoD et du Manual Test Plan
>   qui s'y rapportent (5 et 6 : fermeture par expiration).

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
   - **D. Dériver la clé du pool de la session du proxy** (analyse du 2026-10-17). api-mail lit
     déjà le cookie `proxy_session_id` (`UserContextEnricherMiddleware.ResolveProxySession`,
     `UserContextInfo.ProxySessionId`, task-171). Ce cookie est stable quand l'iframe se recharge,
     commun à Weda, à l'iframe et à l'onglet weda2, et il change avec l'utilisateur. Une clé
     `{Email}_{dérivé de la session du proxy}` borne le pool à **boîtes utilisées × réplicas**,
     quel que soit le nombre de rechargements ou d'onglets. Points établis :
     - le cookie est `HttpOnly` : le client ne peut pas le lire. **Seul api-mail** fait la
       substitution, et le client ne change pas ;
     - c'est un **secret d'authentification** : celui qui le détient obtient des jetons du proxy
       (`PscTokenProvider` le rejoue en cookie). Or `ClientSessionId` se retrouve dans les journaux,
       dans l'audit (`UserSessionId`, en base), dans les clés Redis et dans les ordres de fermeture
       entre réplicas. Il faut donc utiliser une **valeur dérivée non rejouable**
       (`HMAC-SHA256(clé serveur, proxy_session_id)` tronqué), **jamais** la valeur brute ;
     - `SessionMailboxGuard` (409 `SESSION_MAILBOX_MISMATCH`) lie un identifiant à la première
       boîte pendant 12 h. Avec un identifiant qui dure toute la journée, la deuxième boîte
       recevrait 409 toute la journée. La clé contient l'adresse, donc revenir à une boîte reprend
       son pool au lieu de l'abandonner : la garde est à retirer ou à réécrire pour les clés
       dérivées du proxy ;
     - repli quand le cookie est absent (session Keycloak seule, authentification de test du banc
       e2e, autres clients) : en-tête `Client-Session-Id`, puis claims, puis `"default"`,
       comme aujourd'hui ;
     - **à vérifier** (proxy hors forge) : la valeur du cookie doit rester la même après
       `POST /session/token`. Si le proxy la régénère à chaque refresh, on retombe dans le défaut
       de la task-282.
   - **Retenu par l'humain le 2026-10-18 : D + C.** D supprime la cause dans Weda sans rien changer
     côté client, et C garantit la borne quoi qu'il arrive.

### 2. Correctif (D + C, arbitrage humain du 2026-10-18)

**D — clé de pool dérivée de la session du proxy (api-mail).**
- `UserContextInfo.ClientSessionId` = valeur dérivée du cookie `proxy_session_id` quand il est
  présent. La dérivation est un HMAC avec une clé serveur : stable, non rejouable, et donc
  journalisable.
- Repli inchangé sans cookie : en-tête `Client-Session-Id`, puis claims, puis `"default"`.
- La valeur brute du cookie n'apparaît ni dans les journaux, ni dans l'audit, ni dans Redis, ni
  dans les métriques.
- `SessionMailboxGuard` : plus de 409 pour une clé dérivée du proxy (la clé du pool porte déjà
  l'adresse). Le comportement actuel reste pour l'en-tête client.
- Le changement de boîte (`MAILBOX_SESSION_CLOSER`) ferme désormais un pool qu'un autre onglet
  peut partager. Vérifier, et prouver par un test, que le pool et les flux SSE se recréent à la
  demande.
- Fin de la session du proxy : quand la session est révoquée (déconnexion de Weda), les pools de
  cette clé doivent se fermer sans attendre l'expiration. Instruire la détection côté serveur (le
  proxy répond « pas de session » à une résolution) en plus de la surveillance client du § 3,
  impossible quand l'iframe a disparu. Règle RG-S : une vérification de fond ne prolonge jamais la
  session.

**C — borne côté serveur (api-mail).**
- Plafond de sessions par utilisateur et par réplica : au-delà, la plus ancienne est fermée. Le
  plafond est fixé par l'analyse (hypothèse prudente : limite opérateur de 10) et réglable dans
  `appsettings.json`.
- Le keep-alive (NOOP toutes les 30 s) ne compte pas comme activité : seule une requête du client
  repousse `ImapIdleTimeout`. À mesurer d'abord (Analyse, point 1).

**B — fermeture au `pagehide`, restreinte au mode autonome (révision du 2026-10-18).** En mode
embarqué, **aucune** fermeture au `pagehide` : chaque navigation Weda fermerait le pool que
l'iframe suivante reprend, et une requête `keepalive` arrivée en retard pourrait fermer une session
à peine reprise. En mode autonome, la fermeture d'onglet libère la session. Limite connue : si une
iframe Weda partage la même session du proxy, son pool est fermé lui aussi, puis recréé à la
demande. Le fonctionnement en mode autonome :
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
- en mode embarqué, l'écouteur n'est pas posé ;
- le corps reste vide (`keepalive` limite le corps à 64 Kio) ;
- un échec n'est ni affiché ni réessayé : la page s'en va. Le filet serveur (expiration, piste C)
  reste.

A est abandonnée (arbitrage du 2026-10-18).

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
  ≤ 3 par réplica actif par exemple) après 30 rechargements de l'iframe. Avec D, la cible attendue
  est **boîtes utilisées × réplicas**, indépendante du nombre de rechargements et d'onglets.
- Aucune régression : changement de boîte (rotation, et 409 pour les clients sans cookie),
  déconnexion, plusieurs onglets réels qui partagent désormais un pool.

## Definition of Done

- [ ] `## Develop log` : mesures avant correctif (connexions après N rechargements, délai réel de
      libération, le NOOP repousse-t-il l'expiration ?), limite opérateur documentée ou hypothèse
      explicite. Pistes comparées et arbitrées par l'humain le 2026-10-18 (D + C)
- [ ] Stabilité de `proxy_session_id` au refresh (`POST /session/token`) constatée et consignée
      (valeur du cookie avant et après, sur l'AppHost de dev)
- [ ] Correctif D + C livré, mesures **après** au même protocole
- [ ] api-mail — **D**, tests d'intégration d'endpoint rouges d'abord (règle 1b) :
  - [ ] deux requêtes avec le même cookie `proxy_session_id` et des `Client-Session-Id` différents
    résolvent **la même** session IMAP (une seule connexion créée) ;
  - [ ] deux cookies différents donnent deux sessions ;
  - [ ] sans cookie : repli sur l'en-tête `Client-Session-Id`, comportement inchangé (409 compris) ;
  - [ ] avec cookie, changer de boîte puis revenir à la première ne renvoie pas 409 et reprend son
    pool ;
  - [ ] la valeur brute du cookie n'apparaît ni dans les journaux capturés, ni dans
    l'audit (`UserSessionId`), ni dans les clés Redis ;
  - [ ] session du proxy révoquée : les sessions de cette clé sont fermées sans attendre
    l'expiration (ou, si la détection serveur est écartée, la raison est consignée au
    `## Develop log`).
- [ ] api-mail — **C**, tests rouges d'abord :
  - [ ] au-delà du plafond par utilisateur, la session la plus ancienne est fermée ;
  - [ ] le NOOP de keep-alive ne repousse pas l'expiration d'une session sans requête client.
- [ ] client-angular : tests de composant ou de store pour la fermeture de session
- [ ] client-angular — **fermeture au `pagehide` (B, mode autonome seulement)**, tests unitaires
  rouges d'abord :
  - [ ] en mode embarqué, aucun écouteur `pagehide` n'est posé et aucun `fetch` ne part ;
  - [ ] en mode autonome, `pagehide` avec une boîte ouverte : un `fetch` `POST …/api/v1/sync/logout`
    part avec `keepalive: true`, `credentials: 'include'` et les en-têtes `Authorization`,
    `Client-Email` et `Client-Session-Id` ;
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
- [ ] Scénario E2E : en mode autonome, fermer l'onglet ferme la session côté api-mail.
  L'événement de fermeture est visible dans le journal d'audit (`MailboxSessionClosed`), et la
  connexion IMAP est libérée sans attendre l'expiration. En mode embarqué, une navigation de
  l'hôte **ne ferme pas** la session : l'iframe suivante la reprend sans nouvelle connexion IMAP
- [ ] Scénario E2E au catalogue (`Api/Mail/e2e/scenarios.yml`) : rechargements répétés de l'iframe,
      nombre de connexions borné. Implémenté dans la suite Angular (voie Weda)
- [ ] Le plafond du banc peut alors **redescendre** (`mail_max_userip_connections`, aujourd'hui
      1000 depuis task-364) sans que le filet ne tombe. À tenter, et le résultat consigné
- [ ] Aucune donnée de santé ni identifiant de session dans les journaux ajoutés

## Manual Test Plan

1. Weda Échanges ouvert, AppHost de dev, Seq : naviguer 30 fois entre pages Weda.
2. `doveadm who` (ou Seq) : le nombre de connexions du praticien reste sous la borne. Dans Seq,
   aucun nouvel événement `🌱 New ImapClient` n'apparaît à chaque navigation : l'iframe reprend la
   même session.
3. Revenir sur Weda Échanges : la messagerie s'ouvre sans « boîte momentanément indisponible ».
4. Changer de boîte dans weda2, revenir à la première (aucun 409), puis se déconnecter : les
   sessions correspondantes sont fermées.
5. **Déconnexion de Weda** depuis Weda Échanges (bouton « Déconnexion ») : aucun
   `POST /api/v1/sync/logout` au `pagehide` (mode embarqué). Dans Seq, la session de messagerie est
   fermée à la détection de la fin de la session du proxy, ou au plus tard à l'expiration (C).
   Relever le délai.
6. **weda2 en onglet à part**, fermer l'onglet : `POST /api/v1/sync/logout` part au `pagehide`,
   avec l'en-tête `Authorization`. Dans Seq, la session est fermée tout de suite.
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

## Branches
- `api-mail` (pushed) : fix/task-365-session-imap-bornee — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-365-session-imap-bornee
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-rewriting-mss-weda-integration`) — l'humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-365 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 1 h 01 min | 8 (1 min 22 s) | 16 (17 min 13 s) | — | api-mail 6B/14T, client-angular 2B/2T, e2e non joués : banc indisponible (api-mail profil e2e sans réponse 480 s) |
| /sonar | ok | 8 min 17 s | 2 (1 min 23 s) | 10 (10 min 25 s) | 4 (1 min 28 s) | 1 itération(s), api-mail 2B/10T |
| /lint-angular | ok | 2 min 14 s | 1 (11 s) | 1 (18 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | — | 2 (18 s) | 4 (4 min 27 s) | — | api-mail 1B/3T, client-angular 1B/1T, e2e ×16 (1 h 20 min), porte verte : mobile 37, angular 45; no start marker |
| /review | ok | — | 2 (12 s) | 2 (4 min 16 s) | — | api-mail 1B/1T, client-angular 1B/1T, no start marker |
| /tech-writer | ok | 41 s | — | — | — | — |
| **Total cycle** | | **1 h 13 min** | **15 (3 min 28 s)** | **33 (36 min 40 s)** | **4 (1 min 28 s)** | |

Autres commandes mesurées : lint ×1 (27 s)

## Develop log

### 1. Analyse

- **Arbitrage humain** (2026-10-18, encadré en tête de task) : pistes **D + C**. A est abandonnée. B est restreinte au mode autonome. Aucun arbitrage restant à demander.
- **Mesures avant correctif, embarqué dans Weda : non faites par la forge.** Elles exigent Weda sous IIS Express et le vrai psc-auth-proxy. Elles sont renvoyées au Manual Test Plan (étapes 1 et 2), à jouer au HAG avant et après. Ce qui est établi par le code et les tests :
  - **avant le correctif**, chaque chargement de l'iframe présentait un `Client-Session-Id` neuf, donc une clé de pool neuve. Résultat : une session IMAP par chargement, et par réplica touché, plus la voie SMTP d'un envoi. Chacune vit jusqu'à son expiration. Le constat de task-364 (Seq, 2026-10-10) l'illustre : 107, puis environ 100 connexions IMAP neuves en 5 min pour un seul praticien ;
  - **délai réel de libération d'une session abandonnée** : de 5 à 6 min, soit `ImapIdleTimeout` (5 min, les deux voies) plus la cadence du balayage (`SessionCleanupInterval`, 1 min) ;
  - **le NOOP de keep-alive ne repousse pas l'expiration.** `LastImapAccessTime` n'est rafraîchi que par une requête du client. C'est figé par `KeepAliveDoesNotExtendSessionTests` : rouge quand le NOOP rafraîchit la session (mutation).
- **Limite des opérateurs MSSanté** : aucune limite publique connue de la forge, pour l'opérateur de l'ANS comme pour les autres. On dimensionne sur l'**hypothèse prudente de 10 connexions IMAP simultanées par compte**. D'où le plafond de 3 sessions par boîte et par réplica : 3 réplicas actifs restent sous 10.
- **Stabilité de `proxy_session_id` au refresh (`POST /session/token`) : non vérifiée.** Le proxy est hors forge et absent du poste. **À constater au HAG** : relever la valeur du cookie avant et après un refresh. Si le proxy la régénère, la piste D retombe dans le défaut de task-282 ; le plafond (C) borne alors le compte.
- **Détection côté serveur de la révocation de la session du proxy : écartée.** Après la déconnexion de Weda, l'iframe disparaît et plus aucune requête n'atteint api-mail. La détecter imposerait une interrogation de fond du proxy, session par session. Or on ne sait pas si `has-session` prolonge la session (règle RG-S, proxy hors forge), et cela chargerait le proxy. La borne reste C : la session expire en 5 à 6 min, sans requête cliente, et le NOOP ne la prolonge pas. En mode autonome, la surveillance du § 3 et la fermeture au `pagehide` ferment tout de suite.
- **Charge sur le proxy** : un `has-session` toutes les 60 s par onglet weda2 authentifié, journalisé au niveau Information par le proxy. C'est le même ordre que la surveillance de Weda (`/session/introspect` toutes les 60 s). Proxy inchangé.

### 2. Correctif

**api-mail** (`fix/task-365-session-imap-bornee`)
- **D** : `ProxySessionPoolKey.Derive`. Quand la requête présente le cookie `proxy_session_id`, la clé du pool vaut `px-` suivi de 32 caractères hexadécimaux d'un SHA-256 avec séparation de domaine. Le cookie passe avant l'en-tête `Client-Session-Id`. Sans cookie, le repli est inchangé : en-tête, puis claims, puis `"default"`.
  - **Écart au texte du § 2** (« HMAC avec une clé serveur ») : on utilise une empreinte SHA-256 sans clé. Une clé HMAC ne protège qu'une entrée devinable, et un identifiant de session tiré au hasard ne l'est pas. Elle obligerait en plus à partager un secret entre réplicas, faute de quoi l'ordre de fermeture diffusé ne retrouverait plus la clé. La valeur brute du cookie n'atteint ni la clé, ni les journaux, ni Redis : c'est prouvé par test.
  - `SessionMailboxGuard` : une clé dérivée du proxy est liée **par boîte** (`SessionMailboxBinding.PerMailbox`, préfixe Redis `session:proxy-mailbox:`). Jamais de 409, et la trace `MailboxSessionOpened` est posée une fois par couple (session du proxy, boîte). La règle historique (409) reste pour l'en-tête client.
  - Le flux SSE (sans en-tête) partage désormais la clé des autres requêtes. Il ne passe pas par le pool IMAP (il passe par les courtiers) : pas de contention.
  - À noter : `RequestLoggingMiddleware` journalise toujours l'en-tête `ClientSessionId`, pas la clé du pool. Dans Seq, compter les sessions par les événements `🌱 New ImapClient` et `[SessionCap]`, pas par cette propriété.
- **C** : `MailServers:MaxSessionsPerMailbox`, 3 par défaut, `0` = pas de plafond. Au-delà, la session de la boîte la moins récemment utilisée est fermée (`[SessionCap]`, motif métrique `capacity`), jamais une session tenue par une opération. Le défaut est posé dans `MailServersOptions` : c'est la valeur de production. À vérifier par l'humain contre les configmaps DevOps (hors forge).
- **Catalogue e2e** : `E2E-SESSION-001`, `002` et `003` (Angular requis, mobile non applicable).

**client-angular** (code-only, **non commité**, sur la branche `feature/nova-rewriting-mss-weda-integration`)
- **B** : `core/session/page-exit-mail-session.service.ts`. Au `pagehide`, en mode autonome seulement, un `fetch` `POST /api/v1/sync/logout` part avec `keepalive` et `credentials: 'include'`, et les en-têtes `Authorization`, `Client-Email` et `Client-Session-Id` posés à la main. Pas de `sendBeacon`. Rien n'est envoyé sans boîte ou sans jeton. Une page restaurée depuis le cache arrière rouvre la session sous un nouvel identifiant. Un échec est avalé.
- **§ 3** : `core/session/shared-session-watch.service.ts`. Vérification toutes les 60 s (`sessionWatchIntervalMs` dans `environment*.ts`) et au retour sur l'onglet (`visibilitychange`, `focus`). Une seule vérification à la fois, aucune pendant l'amorçage ni sur `/logout`, et plus aucune après la sortie.
  - Sur « pas de session » : fermeture des flux SSE, puis la déconnexion existante du store (`createLogoutMethod` : messagerie fermée avec le jeton encore présent, `$logout`, purge). En mode autonome, `redirectToLoginOnSessionLoss` mène à `/logout`. En mode embarqué, `$logout` notifie `session-expired`, sans DELETE et sans redirection.
  - Au retour sur l'onglet, `/auth/userinfo` est lu. Sur un `sub` différent : la messagerie du précédent est fermée avec son jeton, les flux sont fermés, l'état est purgé, puis l'application est rechargée. Jamais `logout()` ici : il révoquerait la session du nouveau praticien.
  - Journal : la cause seule, sans identifiant.
- `AuthenticationCallbackService.$probeSession()` rend `active`, `absent` ou `unknown`. Délai de 10 s ; une erreur, un 5xx ou un délai dépassé valent `unknown`. La requête est silencieuse grâce au jeton `SILENT_HTTP_ERRORS`, respecté par `errorInterceptor`. `closeMailSession` de `store-helpers.utils.ts` est exporté pour être réutilisé.
- Le flux de l'assistant appartient à son panneau : il se ferme avec lui (navigation vers `/logout` ou rechargement).
- Fichiers Angular modifiés (non commités) : `app/app.config.ts`, `app/core/interceptors/error.interceptor(.spec).ts`, `app/core/session/*` (nouveaux, 2 services + 2 specs), `environments/environment{,.prod,.test}.ts`, `lib/auth/index.ts`, `lib/auth/models/silent-http-errors.token.ts` (nouveau), `lib/auth/services/authentication-callback.service(.spec).ts`, `lib/auth/store/utils/store-helpers.utils.ts`, et l'e2e : `e2e/mss-e2e/specs/functional.e2e.ts`, `support/{session,weda-host,e2e-backend}.ts`.
- Banc e2e : le faux proxy pose désormais le cookie `proxy_session_id`, un par contexte, comme un login réel. Il peut être révoqué (`revokeProxySession`). Le relais transmet le cookie à api-mail (`allHeaders()`). Le faux hôte enregistre les notifications de weda2 (`hostEvents`), et le second appareil relit les traces de session (`sessionTraces`).

### 3. Preuves

- **api-mail, intégration d'endpoint** (`ProxySessionPoolKeyIntegrationTests`, pipeline réel : Bearer, middleware, garde, gestionnaire de sessions, `SyncController`, RFC 7807), 8 tests :
  - deux chargements avec le même cookie partagent une session (1 client IMAP créé) ; trente rechargements aussi ;
  - deux cookies donnent deux sessions ;
  - sans cookie, l'en-tête décide et le 409 tient ;
  - avec cookie, bascule A → B → A sans 409, le pool est repris et il y a deux `MailboxSessionOpened` ;
  - la déconnexion ferme la clé du proxy, pas celle de l'en-tête ;
  - le cookie brut est absent de la clé, des journaux capturés (capture prouvée non vide) et des clés du cache ;
  - sans cookie, trente en-têtes neufs restent sous le plafond.
- **Mutations** (fichier copié, muté, rouge constaté, restauré) :
  - M1, retour à l'en-tête comme clé et liaison historique : 6 rouges sur 7 ;
  - M2, cookie brut pris comme clé : `TheRawProxySession…` rouge (« Sub-string found ») ;
  - M3, plafond inopérant : `WithoutACookie_ThirtyFreshHeaders…` et 6 tests de `SessionCapPerMailboxTests` rouges ;
  - M4, le NOOP rafraîchit la session : `KeepAliveDoesNotExtendSessionTests` rouge ;
  - M5, `PerMailbox` retombe sur la règle historique : 2 tests de `SessionMailboxGuardTests` rouges.
- **api-mail, unitaires** : `ClientSessionIdResolutionTests` (+4, rouges avant le correctif : 2 en échec d'assertion), `SessionMailboxGuardTests` (+3), `SessionCapPerMailboxTests` (9), `KeepAliveDoesNotExtendSessionTests` (1).
- **client-angular** : `page-exit-mail-session.service.spec.ts` (9), `shared-session-watch.service.spec.ts` (14), `$probeSession` (+6), `errorInterceptor` silencieux (+1). 10 mutations, toutes rouges sur l'assertion visée : keepalive coupé ; fermeture en mode embarqué ; pas de nouvel identifiant au `pageshow` ; purge avant fermeture ; `unknown` qui fait sortir ; vérifications parallèles ; `userinfo` lu sur le minuteur ; pas d'arrêt après la sortie ; une erreur de `$probeSession` lue comme `absent` ; intercepteur bruyant. L'ordre « messagerie fermée avant la purge » de la déconnexion du store est couvert par `store-helpers.utils.spec` (« should emit the mail-session close order before the proxy logout »).
- **e2e** : les 4 tests (`E2E-SESSION-001`, `002`, et `003` en autonome et en embarqué) passent le type-check (`tsc -p e2e/mss-e2e`). **Ni joués ni prouvés par mutation : le banc n'a pas démarré**, à deux reprises. `run.mjs --serve-only` : « api-mail (profil e2e) ne répond pas après 480 s ». api-mail lancé seul démarre pourtant (conteneur DI construit en Development, `/health` répond). Piste d'environnement non tranchée : des conteneurs Weda et psc-auth-proxy tournent sur le poste (Redis 6379, RabbitMQ 5672, Keycloak 8081). **À jouer par `/e2e`, preuves par mutation comprises.**
- **Plafond du banc** (`mail_max_userip_connections`, 1000) : la baisse n'a pas été tentée, faute de banc.

### 4. Validation

- api-mail : build ✓. Tests ✓ : domain 195, infrastructure 690, application 3656, api 1237, integration 895 (+16 ignorés). Rejoués verts après la passe qualité.
- client-angular : `npm run build` ✓, `npm test` ✓ (weda2 : 2730 verts, 14 ignorés, aucune erreur non gérée). Rejoués verts après la passe qualité.
- Contrôles mécaniques C# (S125, xUnit1045, S4457, xUnit2032) : rien.

### 5. Passe qualité (/simplify)

- **Appliquée et commitée** : api-mail, 5 fichiers (`6c2c24de`). Un seul chemin de création de session (course d'insertion et plafond) ; une seule condition « clé issue du proxy » ; plus de surcharge sans liaison sur la garde ; tri du plafond limité aux sessions de la boîte ; empreinte tronquée à la source.
- **Appliquée, non commitée (code-only)** : client-angular. La sortie sur perte de session réutilise `logout()` du store et `redirectToLoginOnSessionLoss`, et la fermeture au mieux réutilise `closeMailSession` (exporté). Retirés : la garde redondante de `onPageShow` et le repli en double de l'intervalle. Un helper e2e `expectMailSessionClosed` remplace les blocs répétés.
- **Écartées** :
  - `HttpClient` en `keepalive` à la place du `fetch` : la chaîne d'intercepteurs est asynchrone et pourrait ne pas partir pendant le déchargement ;
  - retrait de l'écoute de `focus` et arrêt du minuteur en onglet caché : exigés par la task (sortie en moins de 60 s sans revenir sur l'onglet) ;
  - fusion de `$hasSession` dans `$probeSession` : changerait l'amorçage ;
  - mémoire locale de la garde par boîte : gain négligeable face aux entrées-sorties IMAP ;
  - jeton `SILENT_HTTP_ERRORS` déplacé vers `core/` : il est consommé par `lib/auth`, la dépendance irait à l'envers.

### 6. Récapitulatif

- Repos touchés : api-mail, client-angular.
- DTOs publiés : aucun changement de DTO. Interop : aucun changement.
- Commits api-mail :
  - `1198d7c8` fix(session) : sessions IMAP bornées ;
  - `6c2c24de` refactor(session) : passe qualité ;
  - `e25a7f05` test(e2e) : scénarios E2E-SESSION.
- DOD self-check : les tests unitaires et d'intégration exigés existent et ont été vus rouges. Restent pour le HAG et `/e2e` :
  - mesures avant et après sur Weda ;
  - stabilité du cookie au refresh ;
  - jeu et preuve par mutation des 3 scénarios e2e ;
  - baisse du plafond du banc.
- Next step : `/sonar task-365`.

## Sonar log

- Mode A (chaîné), SonarQube 9.9.8, branche `fix/task-365-session-imap-bornee` (HEAD `e25a7f05`). 1 itération.
- Référence avant analyse : bugs 0, vulnérabilités 0, code smells 0, couverture 97,9 %, notes A/A/A.
- Analyse de la branche : Quality Gate **OK**. Nouveau code : 0 issue, 0 hotspot à revoir, couverture 96,7 % (cible 95 %), duplication 0,11 %. Projet : bugs 0, vulnérabilités 0, code smells 0, couverture 97,9 %.
- Phase 1 verte sans correctif ; Phase 2 sans objet (cibles projet atteintes). Aucune consigne nouvelle pour `conventions/csharp.md`.
- Rejeu final (HEAD `8e7e1cb8`, après corrections de revue) : Quality Gate **OK**, 0 issue sur le nouveau code.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | — | 96,7 % | cible 95 % |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Coverage projet | 97,9 % | 97,9 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | = |

- Next step : `/lint-angular task-365`.

## Lint log

- Mode A, code-only (`Client/Angular/front`, branche `feature/nova-rewriting-mss-weda-integration`, rien de commité). Contournement de task-367 appliqué : `npx eslint --format json` sur les 19 fichiers `.ts` de la task (weda2 et e2e), avertissements attribués par `git diff -U0 HEAD`.
- Référence : 8 erreurs, toutes de la task (7 `prettier/prettier` sur des lignes ajoutées, 1 `jsdoc/require-param` sur `fakeAuthProxy` → consigne incrémentée dans `conventions/angular.md`), 38 avertissements, tous antérieurs (`@example` vides, `max-lines` de `functional.e2e.ts`).
- Itération 1 : `@param session` écrit à la main, `eslint --fix` sur 4 fichiers. Diff vérifié : +8 lignes, aucun fichier reformaté en entier.
- Après : **0 erreur**, 38 avertissements, aucun sur une ligne de la task. `tsc -p e2e/mss-e2e` ✓, `nx build weda2` ✓, `nx test weda2` ✓ (2730 verts).
- Next step : `/lint-mobile task-365` (client-mobile non touché → skip).

## Lint mobile log

- `client-mobile` non listé ni touché (arbre propre, sur `develop`) → skip. Next step : `/e2e task-365`.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ❌ outillage (code 2) | aucun joué — api-mail (profil e2e) ne répond pas après 480 s | ~11 min |
| angular | api-mail et client-angular touchés | ⏸️ non lancée | même backend, en panne (2 échecs identiques en `/develop`) | — |

- Verdict : **bloqué — outillage**. La non-régression n'est pas prouvée. Voir `questions/task-365.md`.
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-365-session-imap-bornee` (+ E2E-SESSION-001, 002, 003, Angular requis).
- Porte : non exécutée (aucun rapport).
- Quarantaines : E2E-COMPOSE-002 (angular, task-350), inchangée.
- Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun (les specs e2e Angular sont modifiés).
- Démontage : ports libres ; 2 conteneurs `e2e-*` résiduels **antérieurs** au run (arrêtés depuis le 2026-10-14), laissés en place.

### E2E — rejeu du 2026-10-18 (outillage réparé)

- Outillage : la base Flagsmith persistante gardait un port (26760) tombé dans une plage réservée par Windows (WinNAT 26687-26786) ; port mémorisé dans les user-secrets de l'AppHost (`Resources:mss-mail-flagsmith-db:tcp:port`). Secret retiré et conteneur supprimé par l'humain ; volume `flagsmith-db-data` conservé. Banc rétabli.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 37 verts, 0 flaky, 0 rouge, parité verte | 6 min 40 s |
| angular | api-mail, client-angular touchés | ❌ rouge | 44 verts, **1 rouge** (E2E-PATIENT-002, deux essais), 0 flaky, parité verte | 6 min 42 s |

- E2E-SESSION-001 à 003 : **verts**. Preuves par mutation : ME1 (fermeture au pagehide en embarqué) → `001` rouge « naviguer dans Weda ne ferme pas la session » ; ME2 (aucun ordre au pagehide) → `002` rouge sur l'attente de l'ordre ; ME3 (absence de session ignorée) → `003` autonome et embarqué rouges sur l'attente de l'ordre ; ME4 (api-mail, clé repassée à l'en-tête) → les 4 rouges sur leurs relectures serveur.
- Défaut trouvé par `E2E-SESSION-001` et corrigé : deux `MailboxSessionOpened` pour un chargement, du fait de requêtes parallèles qui lisaient « non lié » avant toute écriture. Liaison par boîte rendue atomique (`SET NX`), test rouge puis vert, api-mail `90645c42`.
- Tests e2e ajustés au banc : le `pagehide` est déclenché sur la page vivante (une requête keepalive émise au déchargement n'est plus relayée par Playwright) ; le jeton émis est relevé par une route de page (le relais du banc le remplace par le bypass).
- **Rouge E2E-PATIENT-002 : antérieur à la task** (boucle de `POST /auth/refresh` du planificateur de task-370, `setTimeout` au-delà de 2³¹−1 ms avec le jeton du banc échu en 2099). Voir `questions/task-365.md`.
- Porte : non exécutée (rapport mobile écrasé par les montages suivants, à rejouer).
- Démontage : complet.

### E2E — rejeu final du 2026-10-18 (porte verte)

- Correctif complémentaire (client-angular, non commité) : `TokenRefreshSchedulerService` borne son minuteur à 2³¹−1 ms (`MAX_TIMER_DELAY_MS`) ; au-delà, il replanifie au lieu de rafraîchir. Cause du rouge E2E-PATIENT-002 : une boucle de `POST /auth/refresh` (4 844 appels sur un test) avec le jeton du banc échu en 2099. Défaut antérieur (task-370), latent en production. 2 tests unitaires, rouges avant, verts après. weda2 : 2732 verts, build ✓.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 37 verts, 0 flaky, 0 rouge, 0 quarantaine | ~7 min |
| angular | api-mail, client-angular touchés | ✅ verte | 45 verts, 0 flaky, 0 rouge, 1 quarantaine (passée) | ~7 min |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-365-session-imap-bornee`
- Quarantaines : E2E-COMPOSE-002 (angular, task-350) — passée.
- Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun.
- Démontage : complet (orchestrateurs) ; 2 conteneurs `e2e-*` résiduels antérieurs (arrêtés depuis le 2026-10-14), laissés en place.
- Plafond Dovecot du banc (`mail_max_userip_connections` = 1000) : baisse non tentée dans cette task.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 1 | headless | Quitter weda2 autonome ferme la session de messagerie | ✅ | — |
| E2E-SESSION-003 | 1 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

### Develop — corrections après revue de code (2026-10-18)

Revue `/review` : CHANGES REQUESTED, 4 points bloquants (`questions/answered/task-365-review.md`), arbitrés par l'humain (piste B retirée ; après une déconnexion de Weda, on s'en remet à l'expiration).

- **R1, api-mail** (`930152a4`) : `POST /sync/logout` retire la liaison (session du proxy, boîte) ; une réouverture écrit de nouveau `MailboxSessionOpened`. Nouveau magasin `ISessionBindingStore` (Redis `SET NX` / `DEL` sans condition de propriétaire, borné à 500 ms comme le cache). Garde injectée dans l'action de déconnexion seulement (`[FromServices]`). Preuves :
  - `ProxySessionPoolKeyIntegrationTests.ASwitchAndBack_TracesEveryOpening_TheLogoutReleasesTheBinding` (A → déconnexion → B → déconnexion → A : 3 `Opened`, 2 `Closed`) ; rouge sous mutation R1 (déconnexion sans libération : 2 `Opened` reçus au lieu de 3) ;
  - unitaires : `PerMailbox_AfterRelease_TheMailboxIsBoundAgain`, `SingleMailbox_ReleaseChangesNothing…`, `PerMailbox_ReleaseWithStoreDown_NeverThrows`.
- **Course de liaison** (trouvée par E2E-SESSION-001, `90645c42`) : deux `Opened` pour un chargement → liaison atomique. Tests rouges d'abord.
- **R2, weda2** : `PageExitMailSessionService` et son spec supprimés, branchement retiré d'`app.config.ts`.
- **R3 et R4, weda2** : la surveillance ne fait plus aucun ordre de fermeture. En cas de perte de session : flux fermés → `$logout` → purge → `/logout` en autonome, `session-expired` en embarqué. Au changement de praticien : flux fermés → purge → rechargement. Le banc efface le cookie du faux proxy à la révocation, comme le vrai (confirmé par l'humain).
- **Suggestions appliquées** :
  - vérifications « retour sur l'onglet » espacées de 15 s au moins (`RETURN_CHECK_MIN_GAP_MS`) ;
  - `/auth/userinfo` lu en silence (`$getUserInfo({ silent: true })`) et borné à 10 s ;
  - sortie autonome d'E2E-SESSION-003 fixée sur l'écran de connexion du proxy ;
  - note sur la course rare du plafond dans `EnforceSessionCap`.
  - Mutations, toutes rouges sur leur test : écart de 15 s retiré, borne de `userinfo` retirée, lecture non silencieuse.
- **Suggestions non appliquées** :
  - `RequestLoggingMiddleware` journalise toujours l'en-tête, car il s'exécute avant l'enrichissement. Le pool se lit dans `[SessionCap]`, `🌱 New ImapClient` et `UserSessionId` de l'audit ;
  - exposer `redirectToLoginOnSessionLoss` par le barrel est devenu sans objet (n'est plus utilisé).
- **Plafond Dovecot du banc** : redescendu de 1000 à 30 (`8e7e1cb8`). Les deux voies sont vertes à 30 (mobile 37, angular 45) ; les suites d'intégration aussi (même fichier).
- **Catalogue** : E2E-SESSION-002 v2 (« quitter weda2 autonome ne ferme pas la session partagée ») et E2E-SESSION-003 v2 (sortie sans ordre de fermeture, aucune trace `Closed` fausse).
- **Validation** : api-mail 6 679 verts (0 échec) ; weda2 2 726 verts, build ✓ ; lint 0 erreur ; `tsc -p e2e/mss-e2e` ✓.

### E2E — rejeu après corrections de revue (2026-10-18) — VERT

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 37 verts, 0 flaky, 0 rouge | ~7 min |
| angular | api-mail, client-angular touchés | ✅ verte | 45 verts, 0 flaky, 0 rouge, 1 quarantaine (passée) | ~7 min |

- Plafond Dovecot du banc : 30 (était 1000).
- E2E-SESSION-003 v2 : un premier passage rouge (variante embarquée) venait du test. Un clic dans l'iframe avait consommé le créneau de 15 s des vérifications « retour sur l'onglet » ; le test redonne désormais le focus jusqu'à la réaction (`returnToTabUntil`). Mutations : MV3 (absence ignorée) → les deux variantes de `003` rouges ; MV2 (fermeture au pagehide réintroduite) → `002` rouge.
- Quarantaines : E2E-COMPOSE-002 (angular, task-350), passée. Divergences : aucune. Démontage : complet.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/300 — `fix/task-365-session-imap-bornee` → `develop`, label `awaiting-human-merge`.
- `client-angular` (code-only) : l'humain gère commit/push TFS et l'ouverture de la PR. Fichiers modifiés, non commités, sur `feature/nova-rewriting-mss-weda-integration` :
   M front/apps/weda2/src/app/app.config.ts
   M front/apps/weda2/src/app/core/interceptors/error.interceptor.spec.ts
   M front/apps/weda2/src/app/core/interceptors/error.interceptor.ts
   M front/apps/weda2/src/environments/environment.prod.ts
   M front/apps/weda2/src/environments/environment.test.ts
   M front/apps/weda2/src/environments/environment.ts
   M front/apps/weda2/src/lib/auth/index.ts
   M front/apps/weda2/src/lib/auth/services/authentication-callback.service.spec.ts
   M front/apps/weda2/src/lib/auth/services/authentication-callback.service.ts
   M front/apps/weda2/src/lib/auth/services/token-refresh-scheduler.service.spec.ts
   M front/apps/weda2/src/lib/auth/services/token-refresh-scheduler.service.ts
   M front/e2e/mss-e2e/specs/functional.e2e.ts
   M front/e2e/mss-e2e/support/e2e-backend.ts
   M front/e2e/mss-e2e/support/session.ts
   M front/e2e/mss-e2e/support/weda-host.ts
  ?? front/apps/weda2/src/app/core/session/
  ?? front/apps/weda2/src/lib/auth/models/silent-http-errors.token.ts
  (`core/session/` contient `shared-session-watch.service.ts` et son spec.)

## Code Review Summary

- **Première revue : CHANGES REQUESTED** (4 bloquants, tous dus à la session partagée par la piste D) → `questions/answered/task-365-review.md`. Arbitrage humain : piste B retirée ; pas d'ordre de fermeture après une déconnexion de Weda (le proxy efface son cookie).
- **Revue ciblée après corrections : APPROVED.** R1 (liaison retirée à la déconnexion), R2 (piste B supprimée), R3 et R4 (aucun ordre de fermeture, faux proxy qui efface le cookie) résolus ; aucun nouveau bloquant.
- Remarques non bloquantes laissées :
  - `RequestLoggingMiddleware` journalise l'en-tête, pas la clé du pool ;
  - course rare du plafond (documentée) ;
  - `$logout()` non silencieux en autonome : un 5xx du proxy pendant la sortie afficherait un message.
- Comportements d'endpoint → tests d'intégration → preuves rouges : table dans la PR #300.
- DoD :
  - **Fait** : tests d'intégration et unitaires (rouges d'abord ou prouvés par mutation) ; scénarios E2E-SESSION-001 à 003 au catalogue et joués en headless ; plafond du banc redescendu à 30 (vert) ; aucune donnée de santé ni identifiant de session dans les journaux ajoutés.
  - **Différé au HAG (Manual Test Plan)** : mesures avant/après sur Weda ; stabilité du cookie `proxy_session_id` au refresh.
