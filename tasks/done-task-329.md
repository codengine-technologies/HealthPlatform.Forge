# todo-task-329.md — Un message envoyé part complet et laisse une trace, quel que soit le chemin : brouillon, transfert, envoi hors ligne ou « annule et remplace »

**Repos**: api-mail, dtos-mss, client-blazor, client-mobile, client-angular
**Dependencies**: task-330 (le rejeu hors ligne fiable, sur lequel l'envoi hors ligne unifié s'appuie)
**Epic**: E009
**Single frontend**: false
**Priorité**: **1** — des **pièces jointes médicales partent absentes** avec un « envoyé » affiché, et des envois n'apparaissent jamais dans « Envoyés ».

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-06** — contre-vérifié —, **AUD-07**, **AUD-20**,
> **AUD-63**, **AUD-48**). Cause commune : **plusieurs chemins d'envoi qui ont divergé** — `sendmail`
> a reçu chaque correctif (archivage, garde d'opposition, file hors ligne, annule-et-remplace), les
> chemins brouillon, transfert et rejeu hors ligne non.

## Ce qui est établi (develop @ `14d58398`)

1. **Brouillon (AUD-06)** — `DraftService.cs:319-341` (`BuildMailDto`) ne copie ni les pièces jointes,
   ni `RequestReadReceipt`, ni `OppositionAcknowledged`, ni le mode annule-et-remplace ;
   `SaveDraftDto` (dtos-mss) ne porte que `AttachmentIds`, que `BuildMailDto` ne lit même pas.
   L'autosave (30 s, Blazor `NewMailComponent.razor:390`) crée un brouillon dans tous les cas, puis
   « Envoyer » passe par `POST drafts/{id}/send` (`:1060-1065`) — **chemin majoritaire**. Patient
   sous opposition acquittée : 409 systématique, et l'exception laisse le brouillon en `Sending`
   (`DraftService.cs:257-262`). Hors ligne : `DraftController` rend 502 au lieu de mettre en file.
2. **Transfert mobile (AUD-07)** — `SmtpService.cs:306-312` filtre `a?.Content != null` : les pièces
   reprises « par référence » (`carriedOver: true`, `mail-compose.component.ts:305-316, 1173-1180`)
   sont **écartées en silence** ; aucun chemin d'envoi ne résout `AttachmentDto.Guid`. Les en-têtes
   X-MSS-CODECDA / X-MSS-INS disparaissent avec elles. Le contrôle de taille (`:396`) les compte pourtant.
3. **Archivage (AUD-20)** — seuls `MailController.cs:1383` et `:1510` appellent
   `sentArchiveDispatcher.Dispatch` ; `DraftService.cs:261-302` et `PendingActionService.cs:367-390`
   non ; `SmtpService` ne fait pas d'APPEND.
4. **Annule-et-remplace hors ligne (AUD-63)** — `MailController.cs:1440-1455` le met en file comme un
   envoi simple ; `ProcessSendMailAsync` n'appelle jamais `MarkAsCancelledAsync` ni ne force
   `InReplyTo`/`References` : l'original reste affiché valide (AMBU.MSS/va1.02).
5. **Verrou d'envoi de brouillon (AUD-48)** — TTL 30 s (`DraftService.cs:29`) plus court qu'un envoi
   (attente du verrou SMTP jusqu'à 120 s) et libéré sans jeton (`DraftCacheRepository.cs:224, 241`) :
   double envoi possible.
6. **Brouillon côté Angular** (ajouté le 2026-09-30, vérifié sur `feature/nova-rewriting-mss`) —
   même défaut que le point 1, côté `client-angular`
   (`Client/Angular/front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`) :
   - l'autosave (30 s, `:1586-1597`) crée un brouillon dès qu'il y a un objet, un corps ou un
     destinataire ; ensuite, `dispatchSend` (`:841-855`) passe par `executeSendDraft` → `sendDraft`
     (`:985-1000`), et plus par `sendMailDirect` ;
   - `buildSaveDraftDto` (`:1524-1537`) ne transmet ni pièce jointe (`attachmentIds` jamais rempli),
     ni `requestReadReceipt`, ni `oppositionAcknowledged`, ni `blockPatientReply` ; le modèle TS
     `SaveDraftDto` (`libs/mss/src/core/models/draft.model.ts:11-23`) n'a même pas ces trois champs ;
   - la route `cancel-and-replace` n'est appelée que depuis `sendMailDirect` (`:1141-1147`) : un
     « annuler et remplacer » rédigé plus de 30 s part comme un envoi simple, et l'original reste valide ;
   - `loadDraft` ne restaure pas les pièces jointes.

   **Conséquence** : sur l'Angular, tout message rédigé plus de 30 s part amputé, avec « envoyé »
   affiché. Cela touche aussi le transfert, qui reprend désormais l'`IHE_XDM.ZIP` d'origine (correctif
   hors chaîne du 2026-09-30). Déjà noté sans suite en task-154 (`archived-task-154.md:134` : « chemin
   sendDraft (SaveDraftDto) hors garde »).

## Objective

Qu'**un seul chemin** décide de ce qui part et de ce qui reste : tout envoi — direct, depuis un
brouillon, transfert, rejeu hors ligne, annule-et-remplace — part avec ses pièces jointes (ou est
refusé explicitement), respecte la garde d'opposition et l'accusé de lecture demandé, est archivé dans
« Envoyés », et ne part jamais deux fois.

### Périmètre

1. **Chemin d'envoi unique côté serveur** : `SendDraftAsync` et le rejeu hors ligne convergent vers
   la même séquence que `sendmail` (validation, garde d'opposition, construction du message,
   SMTP, archivage « Envoyés », annule-et-remplace). L'archivage est déclenché **par ce point commun**,
   plus par le contrôleur.
2. **Pièces jointes par référence** : résolues côté serveur (base ou IMAP) à partir de leur identifiant ;
   si une pièce ne peut pas être résolue, l'envoi est **refusé en 400** avec un message clair — jamais
   écarté en silence.
3. **Contrat brouillon** (`dtos-mss`) : `SaveDraftDto` porte `RequestReadReceipt`,
   `OppositionAcknowledged` et les informations d'annule-et-remplace ; publication NuGet et bump des
   consommateurs .NET.
4. **Brouillon en `Sending`** : toute exception remet le brouillon en `Editing`.
5. **Hors ligne** : l'envoi d'un brouillon hors ligne est mis en file comme `sendmail` ; un
   annule-et-remplace hors ligne est mis en file avec son original et rejoué comme tel.
6. **Verrou d'envoi** : durée au-delà du délai maximal d'envoi (ou renouvelée), libération conditionnée à un jeton.
7. **Clients** : Blazor, mobile et Angular transmettent les pièces jointes du brouillon (référence
   résolvable) et les nouveaux champs ; aucune régression de l'autosave.
8. **Angular** (point 6 ci-dessus) :
   - le modèle TS `SaveDraftDto` suit le contrat `dtos-mss` ;
   - `buildSaveDraftDto` transmet les pièces jointes (par la référence du point 2, ou par leur
     contenu si le contrat le prévoit), `requestReadReceipt`, `oppositionAcknowledged`,
     `blockPatientReply` et les informations d'annule-et-remplace ;
   - un compose ouvert en annule-et-remplace n'est jamais envoyé comme un brouillon simple ;
   - `loadDraft` restaure les pièces jointes.

   Le client est **code-only** : la forge écrit le code sur la branche en cours dans
   `Client/Angular/`, l'humain gère le commit, le push et la PR TFS.

### Hors périmètre

- La fiabilité du rejeu hors ligne lui-même (task-330, prérequis).
- Le format des accusés de lecture (task-340).

## Definition of Done

- [ ] Build passes (0 errors) sur les 5 repos ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), chacun rouge sur le code actuel :
  - [ ] brouillon avec une pièce jointe PDF envoyé par `drafts/{id}/send` → le message SMTP émis **contient** la pièce
  - [ ] transfert d'un mail avec pièce reprise par référence → la pièce est présente dans le message émis
  - [ ] pièce par référence **introuvable** → 400 `ProblemDetails`, aucun envoi
  - [ ] envoi par brouillon → un APPEND « Envoyés » est déclenché
  - [ ] envoi hors ligne rejoué → un APPEND « Envoyés » est déclenché
  - [ ] brouillon vers un patient sous opposition **acquittée** → envoyé ; non acquittée → 409 et brouillon revenu en `Editing`
  - [ ] annule-et-remplace hors ligne rejoué → l'original est marqué annulé, `In-Reply-To`/`References` posés
  - [ ] deux envois concurrents du même brouillon au-delà de 30 s → **un seul** message émis
- [ ] Test d'intégration endpoint (règle 1b) : `POST drafts/{id}/send` de bout en bout (DI, GreenMail) — message relu dans le puits **avec** sa pièce jointe
- [ ] `dtos-mss` publié via la CI, consommateurs .NET bumpés
- [ ] Composants Blazor et mobile : tests de composant sur l'envoi d'un brouillon à pièce jointe et à accusé de lecture
- [ ] Compose Angular : tests de composant, chacun rouge sur le code actuel :
  - [ ] brouillon à pièce jointe → le `SaveDraftDto` envoyé la porte
  - [ ] brouillon à accusé de lecture, à opposition acquittée, à blocage de réponse patient → les trois champs sont transmis
  - [ ] annule-et-remplace après autosave → la route `cancel-and-replace` est appelée
  - [ ] brouillon rechargé → ses pièces jointes sont restaurées
- [ ] Trou du filet : scénario **E2E-DRAFT-002** (v1, `mobile: requis`, `angular: requis`) ajouté dans
  `Api/Mail/e2e/scenarios.yml` — « un message à pièce jointe, envoyé après l'enregistrement
  automatique du brouillon, arrive avec sa pièce jointe ». Implémenté dans les deux clients, prouvé
  rouge sur le bug non corrigé, ligne ajoutée dans `conventions/e2e.md`
- [ ] `data-testid` sur tout élément interactif ajouté ; libellés FR (mobile) / Localizer (Blazor)
- [ ] Aucune donnée de santé ni contenu de pièce jointe dans les logs

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor : `cd Client/Blazor && dotnet run --project <projet Shell>` ; mobile : `cd Client/Mobile && npm start` ; Angular : `cd Client/Angular/front && npm start`.
2. **Brouillon + PDF (Blazor)** : nouveau message, joindre un PDF de test anonymisé, attendre 40 s (autosave), Envoyer → le destinataire de test reçoit le PDF ; le message est dans « Envoyés ». Avant : sans pièce, absent d'« Envoyés ».
3. **Transfert mobile** : transférer un mail porteur d'un `IHE_XDM.ZIP` de test → le destinataire reçoit l'archive et les en-têtes X-MSS. Avant : sans pièce.
4. **Opposition** : destinataire patient de test sous opposition, confirmer « Continuer » après autosave → envoyé. Avant : 409 et brouillon bloqué.
5. **Hors ligne** : couper l'accès PSC (mode hors ligne), envoyer un brouillon → message mis en file (202) ; rétablir → envoyé et archivé.
6. **Annule et remplace hors ligne** : sur un message envoyé, « annuler et remplacer » hors ligne, puis reconnexion → l'original est marqué annulé chez le destinataire de test.
7. **Double clic** : cliquer deux fois « Envoyer » sur un brouillon pendant un envoi lent (latence SMTP simulée au banc) → un seul message reçu.
8. **Angular, brouillon + PDF** : nouveau message, joindre un PDF de test anonymisé, cocher « Accusé de lecture », attendre 40 s (« Brouillon enregistré » s'affiche), Envoyer → le destinataire de test reçoit le PDF, et l'accusé de lecture est demandé. Avant : sans pièce ni demande d'accusé.
9. **Angular, transfert** : transférer un mail porteur d'un `IHE_XDM.ZIP` de test, attendre 40 s, Envoyer → le destinataire reçoit l'archive. Avant : sans pièce.
10. **Angular, annule et remplace** : sur un message envoyé porteur d'un document, « Annuler et remplacer », attendre 40 s, Envoyer → l'original est marqué annulé. Avant : envoyé comme un message simple, original resté valide.
11. **Angular, reprise de brouillon** : rédiger avec une pièce jointe, fermer, rouvrir le brouillon depuis « Brouillons » → la pièce jointe est toujours là.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : traçabilité de l'envoi MSSanté (copie dans « Envoyés ») ; annule-et-remplace conforme à la recommandation MSSanté AMBU.MSS/va1.02 ; respect de l'opposition patient Mon Espace Santé
- **INS** : inchangé — les en-têtes X-MSS-INS accompagnent à nouveau les documents transférés ; aucune INS nouvelle manipulée
- **Authentification PS** : PSC / e-CPS inchangée pour l'envoi MSSanté
- **Habilitations** : inchangées (envoi depuis la boîte sélectionnée du praticien)
- **Interop CI-SIS** : IHE-XDM (pièces jointes `IHE_XDM.ZIP`) transmises intactes ; en-têtes MSSanté X-MSS-CODECDA / X-MSS-INS préservés
- **Tracé PGSSI-S** : envoi, archivage et annule-et-remplace tracés comme sur le chemin `sendmail` (même événements d'audit)
- **Consentement patient** : opposition Mon Espace Santé respectée sur tous les chemins et tous les clients (acquittement explicite du praticien) ; le blocage de réponse patient (`X-MSS-MES: FIN`, ECO.2.2.8) survit au chemin brouillon
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau ; supprime des pertes de données

## Réévaluation au démarrage de /develop (2026-10-02, develop après task-320 et task-330)

La task a été rédigée contre `develop @ 14d58398`, avant task-320 (aucun envoi sans la carte) et task-330 (rejeu fiable, remise incertaine). Relue sur le code actuel :

| Point | État sur develop | Reste à faire |
|---|---|---|
| 1. Brouillon : pièces jointes, accusé de lecture, acquittement d'opposition perdus | **ouvert**. `BuildMailDto` ne les copie pas, `SaveDraftDto` ne les porte pas, `MapToDraftDto` rend toujours `Attachments = []` | tout |
| 1. Brouillon hors ligne en 502 | **réglé par task-320** : `SetAsideAsync` le met en file « prêt à envoyer » | rien |
| 2. Transfert : pièces « par référence » écartées en silence | **ouvert**. Le mobile envoie `guid` vide (le serveur ne remplit jamais `Guid` pour un mail ordinaire). `SmtpService` écarte toute pièce sans contenu, mais compte sa taille. Blazor ne reprend pas les pièces au transfert. Angular les télécharge côté client | résolution serveur, refus 400 si introuvable |
| 3. Archivage « Envoyés » | **ouvert pour le brouillon**. L'envoi confirmé hors ligne archive depuis task-320 | brouillon |
| 4. Annule-et-remplace hors ligne | **ouvert**. La file ne garde aucun lien vers l'original, et la confirmation ne marque jamais l'original annulé. Blazor et Angular contournent aussi l'annule-et-remplace dès qu'un brouillon existe. Le mobile n'a pas d'annule-et-remplace | tout |
| 4 bis. Brouillon bloqué en `Sending` | **réglé par task-330** (`SendThroughSmtpAsync`) | rien |
| 5. Verrou d'envoi de brouillon | **ouvert** : TTL 30 s, valeur constante, libération sans jeton et sautée si la requête est annulée, clé non bornée au praticien | tout |
| 6. Angular | **ouvert**, conforme au constat du 2026-09-30 | tout |

**Décision d'architecture requise avant le contrat DTO** : où vivent les pièces jointes d'un brouillon entre deux enregistrements automatiques (voir l'arbitrage ci-dessous).

## Arbitrage humain du 2026-10-02 (au démarrage de /develop)

**Question** : où vivent les pièces jointes d'un brouillon entre deux enregistrements automatiques ?

**Décision : dans le brouillon (Redis).**
- `SaveDraftDto` porte les pièces jointes. Une pièce ajoutée depuis le poste voyage avec son contenu. Une pièce reprise d'un message (transfert, annule-et-remplace) voyage **par référence** (dossier, UID, nom, occurrence), et le serveur la relit à l'envoi.
- Rouvrir un brouillon restaure ses pièces.
- Coût accepté : l'enregistrement automatique renvoie le contenu des pièces locales (jusqu'à 10 Mo) toutes les 30 s, et Redis le garde jusqu'à 7 jours.

## Branches
- `api-mail` (pushed) : fix/task-329-envoi-chemin-unique — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-329-envoi-chemin-unique (depuis `origin/develop` @ `c3fdc010`, task-330 mergée)
- `client-blazor` (pushed) : fix/task-329-envoi-chemin-unique — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-329-envoi-chemin-unique
- `client-mobile` (pushed) : fix/task-329-envoi-chemin-unique — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-329-envoi-chemin-unique
- `dtos-mss` (pushed, créée par `/develop`) : fix/task-329-envoi-chemin-unique — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-329-envoi-chemin-unique (commit `c3d95e0`, NuGet 505.0.0)
- `client-angular` (code-only) : la forge écrit sur la branche en cours dans `Client/Angular/` (au `/start` : `feature/nova-rewriting-mss`, avec du travail de task-349 non commité). L'humain gère la branche, le commit, le push et la PR TFS.

## Develop log

**Repos touchés** : `dtos-mss` (contrat), `api-mail`, `client-blazor`, `client-mobile`,
`client-angular` (code-only).

**Contrat** : branche `dtos-mss` `fix/task-329-envoi-chemin-unique`, commit `c3d95e0`. Le package
**505.0.0** est publié par la CI. Les consommateurs .NET sont bumpés : api-mail `e70adfe9`, Blazor
`d945868`. Ajouts purs :
- `AttachmentDto.SourceFolderPath` / `SourceUid` / `SourceOccurrence` : une pièce **par référence**,
  relue par le serveur à l'envoi ;
- `MailDto.CancelAndReplaceFolderPath` / `CancelAndReplaceUid` : le message sait ce qu'il annule ;
- `SaveDraftDto` : `Attachments`, `RequestReadReceipt`, `OppositionAcknowledged`, la cible
  d'annule-et-remplace. `DraftDto` reçoit les mêmes, plus `BlockPatientReply`.

**Commits** (branches `fix/task-329-envoi-chemin-unique`, poussées) :
- `api-mail` : `e70adfe9` bump, `d7f03f53` le chemin unique, `593158b7` le catalogue e2e,
  `09a2f87a` la passe qualité, `ac0c462e` la pièce relue n'est plus écrite dans le brouillon,
  `3db132af` S125.
- `client-blazor` : `d945868` bump, `429940e` le brouillon garde tout.
- `client-mobile` : `be03e77` transfert par référence et brouillon complet, `8d31315`
  E2E-DRAFT-002, `e6e3afb` la passe qualité.
- `client-angular` : **non commité** sur `feature/nova-rewriting-mss`, à commiter et pousser sur TFS
  par l'humain. Fichiers :
  - `libs/mss/src/core/models/draft.model.ts`, `libs/mss/src/core/models/mail.model.ts` ;
  - `libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts` ;
  - `libs/mss/src/features/mail/components/mail-compose/mail-compose-draft.component.spec.ts` (nouveau) ;
  - `e2e/mss-e2e/specs/functional.e2e.ts`.

  Les deux `environment.ts` modifiés dans l'arbre sont à l'humain, et ne sont pas touchés.

### Le point commun des envois (serveur)

`OutgoingMailService` est désormais le **seul** chemin par lequel un message part. Il sert
`sendmail`, l'envoi d'un brouillon, la confirmation avec la carte d'un message écrit sans elle,
et l'annule-et-remplace. Il fait, dans l'ordre :
1. **Pièces par référence** (AUD-07) : relues depuis le message d'origine (dossier, UID, nom,
   rang). Une pièce illisible refuse l'envoi en **400**, un serveur de messagerie muet en **503**.
   Une pièce n'est jamais écartée en silence. La pièce relue remplace la référence **dans le message
   envoyé seulement** : un brouillon dont l'envoi échoue garde sa référence.
2. **Annule-et-remplace** (AUD-63), quand le message porte sa cible, quelle que soit la route :
   l'original est marqué annulé, et les en-têtes de fil sont posés.
3. **Envoi**, puis **archivage dans « Envoyés »** (AUD-20), mis en file comme avant (task-272).

`MailSendRules` refuse aussi une pièce sans contenu, au lieu de l'écarter.

**Brouillon** (AUD-06, AUD-48) :
- il porte et envoie ses pièces, l'accusé de lecture, l'acquittement d'opposition, le blocage de
  réponse patient et la cible d'annule-et-remplace ;
- `GET drafts/{id}` les restaure ; la liste ne porte que le nom et la taille des pièces ;
- le verrou d'envoi dure **5 min**, au lieu de 30 s, pour couvrir l'attente du verrou SMTP (jusqu'à
  120 s). Il est pris avec un **jeton unique**, libéré par compare-et-supprime, jamais annulé avec la
  requête, et borné au praticien.

**Annule-et-remplace hors ligne** (AUD-63) : la file garde la cible, et la confirmation avec la carte
marque l'original annulé.

**Déjà réglé avant cette task**, constaté et non refait :
- l'envoi d'un brouillon hors ligne est mis en file depuis task-320 ;
- un échec d'envoi ne bloque plus le brouillon en `Sending` depuis task-330.

### Clients

- **Blazor** : le `SaveDraftDto` porte les pièces (contenu), les trois choix et la cible
  d'annule-et-remplace. Rouvrir le brouillon les restaure.
- **Mobile** :
  - **transfert** : les pièces d'origine voyagent par leur référence dans le message d'origine,
    avec le rang parmi les pièces du même nom. Elles partaient derrière un `guid` vide que le
    serveur ne remplit jamais ;
  - **brouillon** : il porte et restaure tout ;
  - le repli « pièce locale → `sendmail` » est retiré, car il contournait la perte du brouillon.
- **Angular** (code-only) :
  - le brouillon porte et restaure les pièces et les choix du praticien ;
  - un annule-et-remplace enregistré automatiquement passe par la route d'annule-et-remplace, puis
    le brouillon est retiré.

### Décisions prises en implémentant

- **Arbitrage humain** : les pièces vivent dans le brouillon (Redis), avec leur contenu pour une
  pièce locale, par référence pour une pièce reprise.
- **Référence = dossier + UID + nom + rang**, pas un `Guid` : le serveur ne remplit pas
  `AttachmentDto.Guid` pour un message ordinaire, et c'est le même identifiant que la route de
  téléchargement existante.
- **Opposition** : l'acquittement voyage avec le brouillon. Le serveur revérifie à l'envoi, et un
  brouillon non acquitté vers un patient opposé reste refusé en 409.
- **Échec d'un annule-et-remplace** : il garde le statut de l'envoi au lieu d'un 500 générique
  (règle 12). Les tests de contrôleur qui attendaient `InvalidOperationException` ont été adaptés.

### Preuves rouges

- **HTTP de bout en bout** (`SendPathsEndToEndTests`, vraie pile : `DraftController` et
  `MailController`, `DraftService`, `SmtpService`, Redis, GreenMail, Dovecot, base du praticien) :
  **7 tests rouges sur 8** sur le code d'avant.
  - brouillon + PDF : la pièce manquait à l'arrivée ;
  - pièce par référence, par le brouillon puis par `sendmail` : manquante ;
  - référence illisible : 200 au lieu de 400 ;
  - opposition acquittée : 409 ;
  - annule-et-remplace, depuis un brouillon puis hors ligne avec confirmation : `In-Reply-To`
    absent, original non annulé.
  - Le double envoi rapide était vert sur l'ancien code : le verrou de 30 s suffit quand l'envoi
    est court.
- **Verrou** (Redis réel) : `TheDraftSendLock_IsReleasedOnlyByItsHolder`, rouge par mutation
  (libération par `KeyDeleteAsync`, sans jeton).
- **Pièce relue non écrite dans le brouillon** :
  `ARefusedSendOfADraftWithAPartByReference_LeavesThePartAReference` est rouge sur le code d'avant
  le correctif `ac0c462e` (le brouillon stockait les octets du ZIP).
- **Pièce sans contenu** : `SendMailAsync_AnAttachmentWithoutContent_IsRefusedBeforeAnyConnection`,
  rouge par mutation (retrait du contrôle).
- **Unitaires** : `DraftServiceTests` (+3), `OutgoingMailServiceTests` (11), compose Blazor (3,
  rouges sur l'ancien composant), compose mobile (4, rouges), compose Angular (4, rouges).
- **E2E-DRAFT-002** : rouge sur **les deux clients** avec le bug réinjecté côté serveur
  (`BuildMailDto` sans pièces). Le brouillon est bien enregistré, le message arrive, mais sans sa
  pièce jointe. Restauré par `cp` puis `touch`. Le vert sera prouvé par `/e2e`.

### Validation

- **api-mail** : build 0 erreur, **6 120 tests verts**, 16 ignorés (déjà ignorés avant).

| Suite | Verts |
|---|---|
| domain | 190 |
| infrastructure | 675 |
| application | 3 373 |
| api | 1 157 |
| integration | 725 |

- **client-blazor** : 392 verts, 2 ignorés.
- **client-mobile** : build vert, 972 tests verts. ESLint ciblé propre, avec
  `ESLINT_USE_FLAT_CONFIG=false` (voir la consigne).
- **client-angular** : `mss-lib` 540 verts, compose 67 verts, `tsc` de la librairie propre, ESLint
  ciblé 0 erreur. Les 3 warnings (`max-lines`, `complexity`) existaient avant.

### Passe qualité (§Q)

**Appliqué** :
- api-mail : alias `EmptyPart` retiré ; `MemoryStream` dimensionné ; `SendThroughOutgoingAsync`
  renommé ; commentaire du verrou clarifié ;
- mobile : `carryOver` réutilise `fromDraftAttachment` ; `attachmentIds` retiré du modèle TS ;
- Angular :
  - type `CancelAndReplaceContext` réutilisé, en champ simple plutôt qu'en signal ;
  - les deux branches de `dispatchSend` qui partaient par la route directe sont fusionnées ;
  - `file` devenu facultatif, ce qui supprime un décodage base64 inutile à la réouverture ;
  - `attachmentIds` retiré du modèle TS.
- La revue a aussi relevé un vrai défaut, corrigé hors de la passe et test rouge d'abord
  (`ac0c462e`) : la pièce relue était écrite dans le brouillon.

**Écarté, à arbitrer par `/review`** :
- regrouper les options d'envoi dans un sous-objet partagé par `SaveDraftDto`, `DraftDto` et
  `MailDto` : changement de contrat ;
- rendre le résultat complet d'un envoi de brouillon (`originalMarkedCancelled`, `warning`) :
  changement de réponse ;
- typer le rappel de `IMailCancellationService` ;
- Angular : retirer le `updateDraft` qui précède `sendDraft` (les pièces montent deux fois). Un test
  existant fige ce `updateDraft` ;
- **Redis** : stocker le contenu des pièces sous sa propre clé. La liste des brouillons et chaque
  enregistrement automatique désérialisent aujourd'hui le contenu entier. C'est une suite naturelle
  de l'arbitrage, à mesurer au banc.

**Leçons** :
- `conventions/angular.md` › `prettier-fichier-existant`, 5 occurrences. Deux récidives dans cette
  task, attrapées par le lint ciblé avant tout commit. Un **remède mécanique** est ajouté : tester la
  propreté en HEAD, puis `prettier --write` limité aux lignes de la task.
- Même consigne : l'ESLint ciblé du mobile exige `ESLINT_USE_FLAT_CONFIG=false`.
- `conventions/csharp.md` › `xUnit1051`, 3 occurrences.
- `conventions/e2e.md` › « Trous du filet » : le brouillon qui perdait ses pièces, et E2E-DRAFT-002.

## Sonar log

Serveur SonarQube 9.9.8.100196 (`sonar.login`), new code sur 30 jours. Il était arrêté :
conteneurs `sonarqube_db` puis `sonarqube` redémarrés. Deux analyses complètes de la branche. Les
cinq passes Release avec couverture sont vertes aux deux : 0 échec, intégration 725/725 (16
ignorés).

- **Phase 1 (new code)** : Quality Gate **OK**, `new_coverage` = **97,5 %** (cible 95 %).
- **Phase 1, findings de la task** : 2, tous deux corrigés (`993bd1d3`).
  - **S4457** : `OutgoingMailService.SendAsync` avait sa garde d'argument dans le corps `async`.
    Elle est désormais dans une enveloppe synchrone, avec un `SendCheckedAsync` privé. **Récidive** :
    4ᵉ occurrence d'une règle déjà consignée.
  - **xUnit2032** : `Assert.IsAssignableFrom` → `Assert.IsType(…, exactMatch: false)`. Première
    occurrence, l'entrée est créée.
- **Phase 1, finding hors task** : **S107** sur `SemanticSearchService.cs:379`, déjà relevé par
  task-330. Il est hors du périmètre de la task, et le Quality Gate reste OK.
- **Phase 1, tests ajoutés par `/sonar`** : aucun. La couverture du new code dépasse la cible.
- **Phase 2 (legacy)** : non lancée, les cibles du projet sont atteintes.
- **Build / tests** : verts.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,5 % | 97,5 % | 0 |
| New code smells | 1 (S107, hors task) | 1 (S107, hors task) | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | 13 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

**Conventions** (`conventions/csharp.md`) :
- S4457 passe à 4 occurrences, et une entrée **xUnit2032** est créée.
- **Récidive = lecture** : `agents/develop.md` §Q 2b reçoit deux contrôles mécaniques de plus,
  S4457 et xUnit2032. Celui de S4457 attrape le défaut d'origine sur le commit `d7f03f53`. Ce
  changement de la chaîne est à relire par l'humain avant le push.

**Incident d'outillage** : le scratchpad de session a été effacé en cours d'étape, sans doute par le
nettoyage d'un autre processus Claude Code.
- Une première analyse avait été lancée par erreur avec le script de task-330. Je l'ai arrêtée, et
  ses 3 lignes de journal attribuées à task-330 ont été retirées, puisqu'elles n'étaient pas
  commitées.
- Les outils ont été recréés.

## Lint log

`/lint-angular` en mode A. Base `origin/next`, lint limité à `tag:scope:mss`, build et test sur tout le périmètre affecté. Code-only : aucune opération git hormis `git fetch origin next`.

| Mesure | Baseline | Final |
|---|---|---|
| Erreurs ESLint (scope mss) | 0 | **0** |
| Warnings | 41 | 41 (aucun nouveau dans les fichiers de la task, hors `max-lines` et `complexity` déjà présents sur `mail-compose.component.ts`) |

- **Itérations** : aucune. Les erreurs Prettier des lignes ajoutées ont été corrigées dans `/develop`, attrapées par le lint ciblé.
- **Filet** :
  - test : ✅ `nx affected -t test`, 11 projets verts ;
  - build : 10 cibles sur 11, dont `mss-lib` et `weda2`, le consommateur. Seule `mss:build:production` échoue, sur `apps/mss/src/environments/environment.prod.ts` absent de la branche `feature/nova-rewriting-mss`. Ce rouge existait avant la task (mémoire de session), et la task n'y touche pas.

## Lint mobile log

`/lint-mobile` en mode A, sur `fix/task-329-envoi-chemin-unique`. `npm run lint` : **All files pass linting** (0 erreur). Aucune itération, aucun commit. Build et tests (972 verts) inchangés depuis la dernière validation de `/develop` : pas de nouveau build.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | ✅ verte | 26 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 30 s |
| angular | api-mail, client-angular, dtos-mss touchés | ✅ verte | 26 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 47 s |

- Backend e2e construit depuis `Api/Mail` sur `fix/task-329-envoi-chemin-unique` @ `993bd1d3`.
- Clients : `Client/Mobile` sur `fix/task-329-envoi-chemin-unique`, et `Client/Angular` sur `feature/nova-rewriting-mss` (branche de l'humain, avec le travail de la task non commité).
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task. **E2E-DRAFT-002** v1 est ajouté, requis sur les deux clients. Il était rouge sur les deux avec le bug réinjecté (Develop log), et il est vert ici.
- **Incident d'outillage** : le premier passage mobile est sorti en code 2 (NETSDK1045), parce qu'une mise à jour du SDK .NET 10 (10.0.302 → 10.0.401) était en cours sur le poste. Les voies ont été rejouées une fois l'installeur terminé (mémoire de session).
- Quarantaines : aucune.
- Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun. Le compose est couvert par E2E-DRAFT-002.
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/39 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/270 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/87 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/84 — label `awaiting-human-merge`
- `client-angular` : code-only. L'humain gère le commit, le push TFS et l'ouverture de la PR. Fichiers modifiés, non commités, sur `feature/nova-rewriting-mss` :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/core/models/draft.model.ts`
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-draft.component.spec.ts` (nouveau)

Ordre de merge : `dtos-mss` d'abord (package 505.0.0 déjà publié), puis `api-mail`, `client-blazor` et `client-mobile`.
Attention : task-338 (api-mail #268) est encore ouverte et épingle les DTO en 500.0.0. Celle qui merge en second devra fusionner `develop`.

## Code Review Summary

**Verdict : APPROVED.** 0 point bloquant restant, 6 suggestions. Deux constats bloquants du verrou
4a ont été trouvés pendant la revue et corrigés par des tests seuls, sans changement de production
(voir plus bas).

### Validation (SDK .NET 10.0.401, mis à jour sur le poste pendant le cycle)

- **dtos-mss** : build ✓.
- **api-mail** : build ✓, **6 122 tests verts**, 0 échec, 16 ignorés (déjà ignorés avant).

  | Suite | Verts |
  |---|---|
  | domain | 190 |
  | infrastructure | 675 |
  | application | 3 373 |
  | api | 1 157 |
  | integration | 727 |

- **client-blazor** : build ✓, 392 verts, 2 ignorés.
- **client-mobile** : build ✓, 972 verts, lint 0 erreur.
- **client-angular** (code-only) :
  - `nx affected` test : 11 projets verts ;
  - build : 10 cibles sur 11, dont `mss-lib` et `weda2`. `mss:build:production` est rouge depuis
    avant la task : `environment.prod.ts` absent de la branche de l'humain ;
  - lint MSS : 0 erreur.
- **E2E** : vert. Les deux voies ont 26 tests verts chacune, dont **E2E-DRAFT-002**, et la parité
  est verte.

### DOD

| Ligne | Statut |
|---|---|
| Build 5 repos, tests 0 échec | ✅ (Angular : seul le rouge préexistant décrit ci-dessus) |
| Brouillon + PDF envoyé par `drafts/{id}/send` : la pièce est dans le message émis | ✅ `ADraftWithAPdf_…`, rouge avant |
| Transfert avec pièce par référence : présente | ✅ `ADraftCarryingAPartByReference_…` et `AMessageSentDirectlyWithAPartByReference_…`, rouges avant |
| Référence introuvable : 400 `ProblemDetails`, aucun envoi | ✅ `APartByReferenceThatCannotBeRead_…`, rouge avant |
| Envoi par brouillon : APPEND « Envoyés » | ✅ `ADraftWithAPdf_…` lit le dossier Sent (Dovecot) |
| Envoi hors ligne confirmé : APPEND « Envoyés » | ✅ `ACancelAndReplaceWrittenWithoutTheCard_…` lit Sent. Le comportement existait depuis task-320, donc pas de rouge possible |
| Opposition acquittée → envoyé ; non acquittée → 409 et brouillon en `Editing` | ✅ `ADraftToAnOpposedPatient_…`, rouge avant (409 sur la version acquittée) |
| Annule-et-remplace hors ligne : original annulé, `In-Reply-To` / `References` posés | ✅ `ACancelAndReplaceWrittenWithoutTheCard_…`, rouge avant |
| Deux envois concurrents d'un brouillon au-delà de 30 s : un seul message | ✅ partiel, voir la suggestion 1 |
| Test d'intégration `POST drafts/{id}/send` (DI, GreenMail), message relu avec sa pièce | ✅ |
| `dtos-mss` publié par la CI, consommateurs bumpés | ✅ 505.0.0 (api-mail, Blazor) |
| Tests de composant Blazor et mobile : brouillon à pièce jointe et accusé de lecture | ✅ 3 Blazor et 4 mobile, rouges avant |
| Compose Angular : 4 tests rouges avant | ✅ `mail-compose-draft.component.spec.ts` |
| E2E-DRAFT-002 au catalogue, implémenté dans les 2 clients, prouvé rouge, ligne dans `conventions/e2e.md` | ✅ |
| `data-testid`, libellés | ✅ aucun élément interactif ajouté |
| Aucune donnée de santé dans les logs | ✅ ni nom de pièce, ni adresse, ni INS journalisés par le nouveau code |

### Verrou 4a — comportement → test d'intégration (HTTP, vraie pile) → preuve rouge

Tous les tests sont dans `SendPathsEndToEndTests` : vrais `DraftController` et `MailController`,
`DraftService`, `SmtpService` vers le puits GreenMail, Redis, IMAP Dovecot et base du praticien.

| Comportement | Test | Preuve rouge |
|---|---|---|
| Le brouillon envoie ses pièces et l'accusé de lecture, et il est archivé | `ADraftWithAPdf_SentAfterItWasSaved_…` | rouge avant |
| Pièce par référence relue (brouillon, `sendmail`) | `ADraftCarryingAPartByReference_…`, `AMessageSentDirectlyWithAPartByReference_…` | rouges avant |
| Référence illisible : 400, rien ne part, brouillon en `Editing` | `APartByReferenceThatCannotBeRead_…` | rouge avant |
| Pièce sans contenu refusée par `sendmail` | `AMessageWithAnAttachmentWithoutContent_…` | mutation (contrôle retiré). Ajouté par la revue |
| L'acquittement d'opposition voyage avec le brouillon | `ADraftToAnOpposedPatient_…` | rouge avant |
| Annule-et-remplace depuis un brouillon / hors ligne puis confirmé | `ACancelAndReplaceSentFromADraft_…`, `ACancelAndReplaceWrittenWithoutTheCard_…` | rouges avant |
| `GET drafts/{id}` restaure les pièces et les choix, la liste ne porte pas le contenu (champs `DraftDto`) | `AReopenedDraft_RestoresItsAttachmentAndChoices_…` | mutation (`Attachments = []`). Ajouté par la revue |
| Un envoi refusé après la relecture laisse la pièce en référence dans le brouillon | `ARefusedSendOfADraftWithAPartByReference_…` | rouge avant le correctif `ac0c462e` |
| Verrou d'envoi : seul son porteur le libère | `TheDraftSendLock_IsReleasedOnlyByItsHolder` (Redis réel, dépôt réel) | mutation (`KeyDeleteAsync`) |
| Deux envois concurrents : un message | `TwoConcurrentSendsOfOneDraft_DeliverOneMessage` | vert avant (voir la suggestion 1) |

**Constatations de revue, corrigées** (tests seuls) :
- la restauration d'un brouillon (`GET drafts/{id}`, liste) et le refus d'une pièce sans contenu
  n'étaient prouvés qu'en unitaire. Les tests HTTP ont été ajoutés (`78232e37`), chacun rouge par
  mutation ;
- l'arrivée dans « Envoyés » après confirmation n'était pas lue dans le dossier réel (`b203ea18`).

### Revue par axe

- `OutgoingMailService` ✅ : un seul point d'envoi.
  - Il ne modifie plus les objets de l'appelant.
  - Il refuse une référence illisible en 400, et un serveur muet en 503.
  - L'annule-et-remplace est typé (404, 400, ou le statut de l'envoi).
  - Les journaux ne portent ni nom de pièce ni adresse.
- `DraftService` / `DraftCacheRepository` ✅ :
  - le brouillon complet est conservé et restauré ;
  - le verrou est à jeton, compare-et-supprime, borné au praticien, libéré même sur une requête
    abandonnée.
- `MailController` ✅ : les trois actions d'envoi délèguent au point commun. L'annule-et-remplace
  hors ligne garde sa cible.
- **Sécurité** ✅ : une référence ne lit que la boîte du praticien (sa session IMAP). La taille des
  pièces relues est contrôlée par `SmtpService` après la relecture. Aucun secret.
- **Clients** ✅ :
  - Blazor et mobile restaurent et transmettent tout ;
  - mobile : le transfert passe par références, et le repli `sendmail` est retiré ;
  - Angular : l'annule-et-remplace enregistré passe par sa route.

### Suggestions (non bloquantes)

1. **Double envoi au-delà de 30 s** : la preuve HTTP est verte sur l'ancien code, parce que le banc
   n'a pas d'envoi lent. Le correctif est prouvé au niveau du dépôt (Redis réel, mutation) et de la
   durée du verrou (unitaire). Une preuve HTTP demanderait une latence SMTP injectée (Toxiproxy),
   c'est l'étape 7 du Manual Test Plan.
2. **Volume Redis** :
   - la liste des brouillons et chaque enregistrement automatique désérialisent le contenu entier
     des pièces (jusqu'à 10 Mo par brouillon) ;
   - un stockage du contenu sous sa propre clé Redis éviterait ce coût ;
   - c'est la suite naturelle de l'arbitrage, à mesurer au banc.
3. **Angular** : `executeSendDraft` fait `updateDraft` puis `sendDraft` avec la même charge, donc
   les pièces montent deux fois. Le `updateDraft` est figé par un test existant.
4. **Contrat** : les cinq options d'envoi sont recopiées champ à champ (`SaveDraftDto`, `DraftDto`,
   `MailDto` et leurs miroirs TS), et c'était la cause d'AUD-06. Un sous-objet partagé, au prochain
   changement de contrat, fermerait cette classe de défaut.
5. **Résultat d'un brouillon envoyé** : `originalMarkedCancelled` et `warning` ne remontent pas
   par `drafts/{id}/send`, alors qu'ils remontent par la route d'annule-et-remplace.
6. **Verrou** : un porteur qui plante bloque ce brouillon 5 min. Un renouvellement du bail serait
   plus juste que la durée fixe.

### Manual Test Plan aligné (recopié dans les PRs)

> Aligné sur task-320 : un message écrit sans la carte ne part plus tout seul, il se confirme avec
> la carte. L'étape 5 du plan initial devient donc « mise de côté, puis confirmation ».

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor : `cd Client/Blazor && dotnet run --project <projet Shell>` ; mobile : `cd Client/Mobile && npm start` ; Angular : `cd Client/Angular/front && npm start`.
2. **Brouillon + PDF (Blazor)** : nouveau message, joindre un PDF de test anonymisé, cocher « Accusé de lecture », attendre 40 s (« Brouillon enregistré »), Envoyer. **Attendu** : le destinataire de test reçoit le PDF, l'accusé est demandé, et le message est dans « Envoyés ». Avant : sans pièce, absent d'« Envoyés ».
3. **Transfert mobile** : transférer un mail porteur d'un `IHE_XDM.ZIP` de test. **Attendu** : le destinataire reçoit l'archive et les en-têtes X-MSS. Avant : sans pièce.
4. **Opposition** : destinataire patient de test sous opposition, confirmer « Continuer » après l'enregistrement automatique. **Attendu** : envoyé. Avant : 409 et brouillon bloqué. Sans « Continuer » : refus, et le brouillon reste modifiable.
5. **Hors ligne** : sans la carte, envoyer un brouillon. **Attendu** : 202 « prêt à partir ». Avec la carte, le confirmer dans la liste des messages prêts à partir : il part et il est archivé.
6. **Annule et remplace hors ligne** : sur un message envoyé, « annuler et remplacer » sans la carte, puis confirmer avec la carte. **Attendu** : l'original est marqué annulé (badge [ANNULÉ]), et le remplacement porte `In-Reply-To`.
7. **Double clic** : cliquer deux fois « Envoyer » sur un brouillon pendant un envoi lent (latence SMTP simulée au banc par Toxiproxy). **Attendu** : un seul message reçu.
8. **Angular, brouillon + PDF** : nouveau message, joindre un PDF, cocher « Accusé de lecture », attendre 40 s, Envoyer. **Attendu** : le destinataire reçoit le PDF, et l'accusé est demandé.
9. **Angular, transfert** : transférer un mail porteur d'un `IHE_XDM.ZIP`, attendre 40 s, Envoyer. **Attendu** : le destinataire reçoit l'archive.
10. **Angular, annule et remplace** : sur un message envoyé porteur d'un document, « Annuler et remplacer », attendre 40 s, Envoyer. **Attendu** : l'original est marqué annulé.
11. **Angular, reprise de brouillon** : rédiger avec une pièce jointe, fermer, rouvrir le brouillon depuis « Brouillons ». **Attendu** : la pièce jointe est toujours là, et l'accusé de lecture aussi.


## Timings

*(généré par `tools/timing/report.sh --task task-329 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 32 s | — | — | — | — |
| /develop | ok | 3 h 55 min | 5 (28 s) | 17 (10 min 20 s) | — | dtos-mss 1B/0T, api-mail 2B/10T, client-blazor 1B/3T, client-mobile 1B/2T, client-angular 0B/2T |
| /sonar | ok | 19 min 53 s | 4 (42 s) | 12 (13 min 42 s) | 4 (1 min 20 s) | 2 itération(s), api-mail 4B/12T |
| /lint-angular | ok | 1 min 57 s | 1 (26 s) | 1 (46 s) | — | client-angular 1B/1T |
| /lint-mobile | ok | 16 s | — | — | — | — |
| /e2e | ok | 17 min 11 s | — | — | — | e2e ×4 (8 min 29 s) |
| /review | ok | 8 min 08 s | 4 (29 s) | 5 (3 min 35 s) | — | api-mail 1B/3T, dtos-mss 1B/0T, client-blazor 1B/1T, client-mobile 1B/1T |
| /tech-writer | ok | 49 s | — | — | — | — |
| **Total cycle** | | **4 h 44 min** | **14 (2 min 06 s)** | **35 (28 min 24 s)** | **4 (1 min 20 s)** | |

Autres commandes mesurées : lint ×2 (17 s), nuget-wait ×1 (16 s), restore ×2 (4.6 s)
