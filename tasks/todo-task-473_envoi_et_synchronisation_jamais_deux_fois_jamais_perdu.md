# todo-task-473.md — Envoi et synchronisation : jamais deux fois, jamais perdu

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « concurrence et sessions », « entrées et
> injections »). Le double envoi et la purge sans garde `UidNext` ont été relus dans le code par l'orchestrateur le
> 2026-11-13.

## Ce qui est établi

Lecture du code au 2026-11-13 (`Api/Mail/src`) :

### Envoi

- **Double envoi.** `SmtpService.cs:130-161` : la transmission (`SendWithOneRetryOnDeadSessionAsync`) et la trace
  `MailSend` / `MailReply` sont dans le **même** `try`. Quand le journal est saturé (canal et tampon pleins),
  `AuditService.cs:206` lève `UnavailableException` après le 250 du serveur ; le `catch` (`:193-195`) la traite comme
  « rien n'a été accepté ». Envoi direct : 503 ; envoi différé confirmé : retour en « prêt à envoyer » ; brouillon :
  retour en rédaction (`MailController.cs:1692-1699`, `DraftService.cs:348-352`). L'archivage dans « Envoyés » n'est
  pas mis en file. Le médecin renvoie : le courrier part deux fois. Saturation déjà observée le 2026-09-08.
- **Archivage en mémoire seulement.** `SentArchiveDispatcher.cs:50-55` et `Background/BackgroundTaskQueue.cs:63-71`,
  `:103-112` : un arrêt du pod (déploiement) annule l'APPEND en cours et vide la file ; rien n'est persisté, aucune
  reprise. Le message envoyé n'apparaît jamais dans « Envoyés ».
- **Connexion SMTP non libérée.** `SmtpConnectionFactory.cs:297-298` exclut `UnauthorizedException`,
  `UnavailableException` et `PscIdentityConflictException` de la libération : TLS établi, jeton PSC refusé, le
  `SmtpClient` connecté reste ouvert jusqu'au ramasse-miettes.
- **File des drapeaux.** `FlagPropagationService.cs:251-252` rend une ligne sans passer `maxRetries` ;
  `PendingActionRepository.cs:215` (défaut 3) la passe en `Failed` après trois courses opportunistes. Pendant une
  panne IMAP, chaque clic « lu » réclame **toutes** les lignes en attente du dossier et incrémente leur compteur : au
  3ᵉ clic elles échouent définitivement, alors que task-330 visait 10 tentatives
  (`PendingActionService.MaxReplayAttempts = 10`). L'annulation par le geste opposé ne voit que les lignes `Pending`
  (`:308-316`, `:334-348`) : un « lu » en cours qui échoue redevient `Pending` après un « non lu » propagé, et remet
  `\Seen` plus tard. `DeletePendingActionAsync` supprime une ligne sans condition d'état.

### Synchronisation

- **Purge sans garde `UidNext`.** `BackgroundSyncService.cs:372-382` supprime tout UID présent en base et absent de la
  liste lue plus tôt (`SEARCH ALL`, `:351`). Un mail arrivé entre les deux lectures, inséré par une requête de premier
  plan, est supprimé avec son contenu, ses documents et ses étiquettes ; il est ré-ingéré au cycle suivant sous un
  nouvel identifiant, ré-analysé et notifié deux fois. Le premier plan porte la garde (`ImapService.cs:516-520`,
  task-353).
- **UIDVALIDITY confrontée par la seule synchro de fond.** `FolderRepository.cs:161-163` adopte la nouvelle génération
  sans purge sur le chemin de premier plan ; `SyncUidValidityAsync` n'a qu'un appelant
  (`BackgroundSyncService.cs:454`). `MailRepository.cs:284-304` (`TryResolveExistingMailAsync`) ne filtre pas la
  génération ; le cache `mail:email:{boîte}:{dossier}:{uid}` (`MailController.cs:707-714`, 15 min) n'en porte pas. Après
  une restauration de la boîte, le contenu d'un ancien message peut être servi sous l'en-tête du nouveau. (Plausible :
  dépend de `EnableFullSync`.)
- **État de synchro fantôme dans Redis.** `BackgroundSyncManager.cs:762-786` (`StopLocallyAsync`) efface l'état sans
  attendre le travail qui tient le verrou : un démarrage rapproché réserve un nouvel état que personne n'efface
  (`CompleteRunAsync`, `:256-282`, n'efface que `wasOwner && Ran`) ; « en cours » 15 min. `RedisSyncStateStore.cs:137-155`
  (`SetStatusAsync`) fait un GET puis un SET sans condition : une pause pendant la fin de synchro fait renaître la clé
  en « Paused » 15 min. Une exception Redis dans `TryStartAsync` laisse le runtime dans `_localRuntime` : le pod ignore
  tout démarrage de la boîte.
- **Verrou distribué.** `RedisDistributedLockService.cs:12` : la valeur du verrou est
  `MachineName:ProcessId`, commune à toutes les acquisitions du processus ; un appelant qui dépasse le TTL libère le
  verrou repris par un autre appelant du même processus. `BackgroundSyncService.cs:189` ignore le résultat de
  `TryRenewAsync` : un bail perdu n'arrête pas la synchro, deux pods synchronisent la même boîte.
- **Client IMAP hors verrou.** `ImapConnectionService.cs:102-104` cherche le client par clé de session ;
  `MailClientSessionManager.cs:121-148`, `:658-688` (`RemoveSession`) retirent l'entrée sans condition. Une
  déconnexion pendant une opération : la requête crée une nouvelle session et utilise son client sans en tenir le
  verrou, en parallèle d'une autre requête (MailKit n'est pas sûr entre fils).

### Divers

- **Contacts en double.** `PatientContactService.cs:39`, `:111-113` et `ContactRepository.cs:384-396`, `:408-428` :
  « vérifier puis insérer » ; seul index `IX_Contacts_UserId`, non unique (`MailDataContext.cs:524`). Trois résultats
  du même patient consommés en parallèle (`ConcurrentMessageLimit = 5`, plusieurs réplicas) créent trois contacts.
  `CreatePatientContactConsumer.cs:49` et `CreatePractitionerContactConsumer.cs:54` avalent toute exception et
  acquittent : le rejeu configuré ne sert jamais.
- **Heures.** `PendingActionRepository.cs:69`, `:115`, `:147`, `:376` : `DateTime.Now` dans les réclamations ;
  `MdnService.cs:292` date l'accusé de lecture à l'heure du serveur, sans décalage ; `MailExportService.cs:114` idem ;
  `ImapFolderService.cs:241`, `:247` : « aujourd'hui » en heure du serveur, alors que `PractitionerDay` existe.

## Objective

Un courrier médical ne part jamais deux fois et arrive toujours dans « Envoyés » ; une synchronisation ne supprime, ne
mélange ni ne bloque aucune boîte ; les heures lues par une personne sont celles de Paris.

Règles :

1. **Un envoi accepté (250) est acquis.** Aucune étape qui suit, trace d'audit comprise, ne le requalifie en échec.
   Si la trace ne peut pas être écrite à cet instant, elle est parquée (comme aujourd'hui) et l'envoi reste « envoyé » ;
   au pire, un échec postérieur au 250 range l'envoi en « remise incertaine ».
2. **Archivage dans « Envoyés » persisté.** L'intention d'archiver (message ou référence au message) est enregistrée
   avant la réponse au client, et rejouée au démarrage jusqu'à réussite ; un APPEND réussi n'est jamais rejoué.
3. **Connexion SMTP** : toute sortie sans succès libère le client.
4. **Drapeaux.**
   - Une tentative ne compte qu'une fois par passe de rejeu ; budget de 10 (`MaxReplayAttempts`).
   - Le geste opposé annule aussi l'action en cours de traitement.
   - Une suppression n'agit que sur une action encore en attente.
5. **Synchronisation.**
   - La purge par différence ne supprime que les UID inférieurs au `UidNext` lu, et évince les caches du message.
   - UIDVALIDITY est confrontée sur le chemin de premier plan aussi, avant toute adoption ; la génération entre dans
     les clés de cache du contenu et du résumé.
   - L'état Redis d'un run n'est effacé que par son propriétaire ; il est écrit sous condition ; un runtime local est
     libéré sur exception.
   - Le verrou distribué porte un jeton propre à chaque acquisition ; la synchro s'arrête si son renouvellement est
     refusé.
   - Le client IMAP d'une opération est celui de la session dont elle tient le verrou.
6. **Contacts.** Unicité par boîte sur l'INS (contact patient), le RPPS (contact praticien) et le nom d'un groupe
   système, avec reprise sur collision ; une erreur transitoire remonte au bus et est rejouée.
7. **Heures.** UTC (`TimeProvider`) pour toutes les échéances internes ; heure de Paris, avec son décalage, dans ce
   qu'une personne lit (accusé de lecture, export, vues « aujourd'hui »).

### Hors périmètre

- La connexion IMAP de fond par personne : task-472.
- Le format des erreurs d'envoi (502 brut, `detail` technique) : task-474.

## Definition of Done

- [ ] Tests unitaires : issue d'un envoi après un échec de trace ; budget et annulation des drapeaux ; borne `UidNext`
      de la purge ; jeton du verrou ; libération SMTP ; heure de Paris (accusé, export, « aujourd'hui », passage à
      l'heure d'été).
- [ ] **Test d'intégration de bout en bout (règle 1b) du double envoi** : le journal d'audit refuse (saturation
      simulée) pendant un envoi réussi ; `POST …/sendmail` répond « envoyé » ; le destinataire reçoit **un** message ;
      un envoi différé confirmé dans les mêmes conditions ne revient pas en « prêt à envoyer ». Vu rouge.
- [ ] **Test d'intégration de l'archivage** : l'hôte s'arrête pendant l'archivage ; au redémarrage, le message est
      dans « Envoyés », une seule fois. Vu rouge.
- [ ] **Test d'intégration de la purge** : un mail inséré entre la lecture des UID et la purge survit ; un mail
      réellement supprimé du serveur est purgé. Vu rouge.
- [ ] **Test d'intégration d'UIDVALIDITY** : la génération change ; une lecture de premier plan ne sert aucun contenu de
      l'ancienne génération. Vu rouge.
- [ ] **Test d'intégration de l'état de synchro** : arrêt puis démarrage rapprochés ; la synchro redémarre, aucun état
      « en cours » ou « en pause » sans propriétaire ne subsiste. Vu rouge.
- [ ] **Test d'intégration des contacts** : trois créations parallèles du contact d'un même patient donnent un seul
      contact ; une erreur transitoire de base est rejouée. Vu rouge.
- [ ] **Test d'intégration de l'accusé de lecture** : l'accusé porte l'heure de Paris et son décalage.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire envoie ; la trace `MailSend` porte le
      délégataire (RPPS, nom, rôle) ; le titulaire relit le message dans « Envoyés ».
- [ ] Pas de nouveau scénario e2e : ces défauts ne se reproduisent pas depuis le client (saturation du journal, arrêt
      de l'hôte, course de synchronisation). Les parcours existants sont rejoués verts par `/e2e`.
- [ ] Prévention (règle d'or) : `conventions/csharp.md` — « après un effet externe acquis, aucune étape ne requalifie
      l'issue » ; « un travail promis au client est persisté avant la réponse » ; « une purge par différence se borne à
      `UidNext` » ; « un verrou distribué porte un jeton par acquisition » ; « jamais `DateTime.Now` ».
- [ ] Migration (index uniques des contacts) : fichier relu, aucune opération fantôme, dédoublonnage des lignes
      existantes avant l'index (règle 7c).
- [ ] Aucune donnée de santé dans les logs.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et weda2 (`cd Client/Angular/front && npm start`).
2. Envoyer un message avec pièce jointe, puis arrêter l'API (Ctrl+C) dans la seconde. La relancer : le message est dans
   « Envoyés », une seule fois.
3. Lancer une synchronisation complète et, pendant qu'elle tourne, injecter un nouveau mail : il reste dans la boîte
   après la synchronisation.
4. Arrêter puis relancer aussitôt la synchronisation (réglages) : elle redémarre, sans « déjà en cours ».
5. Accuser lecture d'un message demandant un accusé : chez l'expéditeur, l'heure est celle de Paris.
6. Injecter trois résultats d'un même patient : un seul contact patient dans le carnet.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — échanges MSSanté
- **Vague Ségur** : hors Ségur — fiabilité de l'envoi et de la synchronisation
- **Exigences DSR honorées** : non applicable — exigences PGSSI-S (intégrité, disponibilité, traçabilité de l'envoi)
- **INS** : unicité du contact patient par INS dans la boîte ; aucune INS dans les journaux
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel pour l'envoi MSSanté
- **Habilitations** : inchangées (règle 14)
- **Interop CI-SIS** : MSSanté (SMTP, IMAP, accusé de lecture MDN) : un seul envoi, archivé, accusé daté juste
- **Tracé PGSSI-S** : l'envoi est tracé une fois, au nom de son auteur ; aucune trace ne requalifie un envoi acquis ;
  `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangée
