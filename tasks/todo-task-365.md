# todo-task-365.md — Embarqué dans Weda : les sessions IMAP ne s'empilent plus à chaque rechargement de l'iframe

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
   - **B. Fermer la session en quittant la page** : `pagehide` + `navigator.sendBeacon` vers une
     route de fermeture d'api-mail. Limite : best-effort, perdu si l'onglet est tué.
   - **C. Borner côté serveur** : plafond de sessions par utilisateur (éviction de la plus
     ancienne), et/ou keep-alive qui ne prolonge pas une session sans requête client.
     Protège aussi les autres clients.
   - Une combinaison (par exemple A + C) est probablement la bonne réponse : A supprime la cause
     dans Weda, C garantit la borne quoi qu'il arrive.

### 2. Correctif (après arbitrage humain de la piste)

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

## Conformité santé / Ségur / ANS

- Disponibilité de la messagerie sécurisée : un praticien ne doit pas perdre l'accès à sa boîte
  par un effet de bord de la navigation dans son logiciel.
- Usage raisonnable de l'infrastructure de l'opérateur MSSanté : pas de connexions orphelines.
- Aucune donnée de santé manipulée par la correction (sessions et connexions seulement).
