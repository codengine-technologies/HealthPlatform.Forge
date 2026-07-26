# todo-task-187.md — Sessions IMAP détruites en cours d'usage : lots de messages perdus, verrous corrompus

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes sessions IMAP et
> concurrence).

## Objective

Garantir qu'une session IMAP n'est jamais détruite pendant qu'elle est utilisée, et
qu'un verrou n'est jamais libéré au profit d'une autre session que la sienne.

Le nettoyage des sessions expirées ne tient aucun compte de l'usage en cours :
aucune session n'est marquée « occupée », et le temps d'accès n'est pas rafraîchi
pendant une opération longue. Une session peut donc être déconnectée et libérée
**au milieu d'une récupération de messages**. Les conséquences se cascadent :
lot de messages silencieusement perdu, libération d'un verrou appartenant à une
autre session (deux requêtes pilotant alors le **même** client IMAP, qui n'est pas
thread-safe), ou exception au retour du bloc de verrouillage.

**US backend-only (justification)** : cycle de vie des sessions côté serveur.

### Preuve (état actuel du code)

1. **Expiration pendant l'usage** —
   `src/Application/Session/MailClientSessionManager.cs:275` : le chemin de
   verrouillage crée la session par un `GetOrAdd` **sans** rafraîchir son temps
   d'accès (seuls `GetOrCreateImapClientAsync` et `RefreshSession` le font).
   `CleanupExpiredSessions` (`:515`) détruit toute session inactive depuis 5 minutes
   **sans vérifier si elle est verrouillée ou en cours d'usage** :
   `kvp.Value.Dispose()` puis `TryRemove`.
   Or `EnrichEmailsAsync` (`src/Application/Services/Implementation/ImapService.cs:713`)
   récupère, **sous un seul verrou**, les résumés puis les corps et archives de
   jusqu'à 50 messages : sur un serveur MSSanté lent, cela dépasse 5 minutes (le
   code journalise déjà des listages de dossiers de ~68 s).
   Le lot meurt alors dans le `catch (Exception)` de `:762`, journalisé « Error
   during IMAP fetch for enrichment », **sans reprise** : ces messages sont perdus
   jusqu'à une synchronisation ultérieure.
2. **Déverrouillage sur la mauvaise session** — au retour du bloc, `UnLockImapClient`
   (`:118`) retrouve la session **par clé** et libère le verrou de *ce qui occupe
   désormais la clé*. Si une requête concurrente a recréé une session et détient
   son verrou, la libération accorde un **second jeton** sur un sémaphore de
   capacité 1 : deux requêtes pilotent le même client IMAP — précisément l'erreur
   « ImapClient is currently busy processing a command in another thread » que les
   commentaires de `ImapFolderService.cs:84` et `EmailFlagService.cs:177` visent à
   prévenir. Si le verrou est libre, la libération lève une exception qui s'échappe
   du bloc en 500.
3. **Destruction bloquante et concurrente du client** —
   `src/Application/Session/MailClientSession.cs:218-220` : après une attente
   bornée à 2 s de la tâche de keep-alive, `Dispose` enchaîne
   **inconditionnellement** `_imapLock.Dispose()` puis
   `_imapClientWrapper.DisconnectAsync(true).GetAwaiter().GetResult()`. Si le
   keep-alive est encore en vol (connexion à demi-ouverte après coupure NAT), une
   seconde commande partit sur le même client. De plus l'appel bloquant s'exécute
   sur la boucle de nettoyage : **un** serveur qui ne répond pas gèle la reprise des
   sessions de **tous** les autres praticiens. (Viole aussi la règle S4462 du repo :
   pas de `.GetAwaiter().GetResult()` en flux normal.)
4. **Déconnexion pendant un flux** —
   `src/Application/Services/Implementation/BackgroundSyncManager.cs:206` et `:398` :
   à la déconnexion, `RemoveSession` détruit la session sans vérifier l'usage, puis
   `StopLocallyAsync(..., resetUserContext: true)` appelle immédiatement
   `runtime.UserContextInfo?.Reset()`. L'annulation étant coopérative, la
   synchronisation est encore en train de se dénouer : elle recopie alors un
   contexte vidé (`Email = ""`, chaîne de connexion vide) et la persistance des
   messages déjà récupérés échoue (« Host is null »). Les messages du lot sont
   perdus.
5. **Sémaphores partagés détruits sous leur détenteur** —
   `src/Application/Session/MailClientSessionManager.cs:441`
   (`CleanupLocksForSession`) : les sémaphores par email/dossier sont libérés dès
   qu'il n'y a plus de session **de premier plan**, alors que leur détenteur peut
   être un travail d'arrière-plan qui ne possède aucune session.
6. **Registre de connexions d'arrière-plan** —
   `src/Application/Session/BackgroundImapConnectionRegistry.cs:143-154` : `Dispose`
   détruit tous les sémaphores sans vérifier s'ils sont prêtés ; la libération
   ultérieure du prêt lève alors une exception depuis un chemin de destruction, à
   l'arrêt du service.

### Contenu attendu

1. **Notion d'usage explicite** : une session en cours d'utilisation ne doit
   **jamais** être recyclée. Compteur d'usage, marquage « occupée », ou rafraîchi
   du temps d'accès pendant l'opération — le mécanisme est un choix technique, la
   propriété est non négociable.
2. **Libération sûre** : la libération d'un verrou doit porter sur **l'instance**
   acquise, jamais sur ce qu'une recherche par clé retourne au moment du retour.
3. **Destruction ordonnée et non bloquante** : attendre effectivement la fin des
   opérations en vol avant de déconnecter et de libérer ; supprimer l'appel
   bloquant de la boucle de nettoyage (conformité S4462) de sorte qu'un serveur
   muet n'affecte qu'une session.
4. **Déconnexion propre** : ne pas réinitialiser le contexte utilisateur tant que
   les travaux qui le lisent ne sont pas terminés ; les messages déjà récupérés
   doivent être persistés ou explicitement re-planifiés, jamais perdus.
5. **Sémaphores partagés** : ne les libérer que sans détenteur ni attente, en
   tenant compte des travaux d'arrière-plan sans session.
6. **Pas de perte silencieuse** : un lot interrompu doit être re-planifié ou
   signalé — jamais avalé par un `catch` journalisé.

### Hors scope

- L'identité des mails (UIDVALIDITY) → task-179.
- Le plan de contrôle de la synchronisation (pause, état Redis) → task-188.
- La performance des requêtes de liste → task-191.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : une session **en cours d'usage** n'est pas recyclée par le
      nettoyage, même au-delà du délai d'expiration (ce test doit échouer sur le
      code actuel — le vérifier explicitement)
- [ ] Test unitaire : la libération d'un verrou porte sur l'instance acquise ;
      recréer une session sous la même clé pendant l'opération ne provoque ni
      double jeton, ni exception au retour
- [ ] Test unitaire : deux requêtes concurrentes ne peuvent jamais piloter le même
      client IMAP (le sémaphore de capacité 1 tient sous le scénario de recréation)
- [ ] Test unitaire : destruction pendant un keep-alive en vol ⇒ pas de seconde
      commande concurrente, pas d'exception depuis le chemin de destruction
- [ ] Test unitaire : plus aucun `.GetAwaiter().GetResult()` sur le chemin de
      nettoyage (conformité S4462) ; un serveur muet n'affecte qu'une session
- [ ] Test unitaire : déconnexion pendant une synchronisation ⇒ le contexte n'est
      réinitialisé qu'après dénouement ; aucun « Host is null », aucun message
      récupéré perdu
- [ ] Test unitaire : un sémaphore partagé détenu par un travail d'arrière-plan
      n'est pas libéré par la disparition de la dernière session de premier plan
- [ ] Test unitaire : à l'arrêt du service, aucune exception depuis un chemin de
      destruction du registre de connexions
- [ ] Un lot d'enrichissement interrompu est re-planifié ou signalé — vérifié par
      test, plus de perte silencieuse
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Opération longue** : sur une boîte de test fournie (plusieurs centaines de
   messages, avec archives IHE_XDM pour alourdir), lancer l'enrichissement d'un
   gros dossier et laisser l'opération dépasser le délai d'expiration de session
   (5 min). Ralentir le serveur si besoin (le profil de latence dégradée du banc de
   charge task-173/174 est utilisable ici).
   **Attendu** : l'enrichissement se termine complètement ; aucun message manquant ;
   aucune ligne « Error during IMAP fetch for enrichment ». Avant correctif, le lot
   en cours est perdu en silence.
3. **Concurrence sur la même boîte** : depuis deux onglets du **même** praticien,
   naviguer simultanément dans les dossiers et lancer une synchronisation → aucune
   erreur « busy processing a command in another thread », aucun 500, aucune
   attente anormalement longue.
4. **Serveur muet** : couper brutalement le réseau vers le serveur IMAP pendant une
   session active (ou geler le conteneur mail), attendre le passage du nettoyage →
   les sessions des **autres** praticiens continuent d'être reprises normalement
   (avant correctif, la boucle de nettoyage se bloque).
5. **Déconnexion en cours de sync** : lancer une synchronisation complète puis se
   déconnecter immédiatement → pas de « Host is null » dans Seq ; les messages déjà
   récupérés sont soit persistés, soit re-planifiés à la synchronisation suivante.
6. **Arrêt du service** : arrêter l'application pendant une synchronisation
   d'arrière-plan → arrêt propre, sans exception de destruction dans les logs.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — fiabilité et complétude de
  la réception MSSanté (un message reçu ne doit pas être perdu par un défaut de
  cycle de vie technique)
- **INS** : non applicable directement — mais les messages perdus peuvent porter
  des documents CDA avec INS, donc des documents cliniques jamais restitués
- **Authentification PS** : inchangée ; le correctif touche la réutilisation des
  sessions authentifiées, sans changer le moyen d'authentification
- **Habilitations** : inchangées. **Point de vigilance** : le défaut de libération
  croisée de verrou concerne des sessions du **même** praticien (clé
  `{email}_{clientSessionId}`) — il n'y a **pas** de franchissement de frontière
  entre praticiens ici (la fuite inter-praticiens est traitée par task-175)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : journaliser l'interruption et la re-planification d'un lot
  (évènement technique, sans contenu) — indispensable pour détecter une perte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement, pas de
  divulgation. Risque d'exactitude/disponibilité (art. 5.1.d) à mentionner au
  humain : des messages ont pu ne pas être restitués.
