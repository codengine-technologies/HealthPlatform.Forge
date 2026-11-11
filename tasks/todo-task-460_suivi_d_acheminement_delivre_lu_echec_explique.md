# todo-task-460.md — Suivi d'acheminement : délivré, lu, échec expliqué

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 4 (trouver le bon destinataire : 3/5) et
n° 5 (2/5). 45 % des adresses publiées dans l'annuaire sont inactives (comité opérateurs ANS, 07/2026). Le
référentiel opérateurs 1.7 (2027) rend obligatoires les accusés de remise et les avis de non-remise **rédigés en
français**.

> **Origine.** Analyse du 2026-11-11, manque D1. Lifen est le seul acteur du marché à suivre la remise et la lecture,
> côté hôpital.

## Ce qui est établi

Lecture du code au 2026-11-11 :

- **Aucune demande d'accusé de remise.** `SmtpConnectionFactory` crée un `new SmtpClient()` brut. Aucune sous-classe ne
  surcharge `GetDeliveryStatusNotifications` ou `GetEnvelopeId` de MailKit : ni `NOTIFY`, ni `ENVID`, ni `RET`.
- Demande d'accusé de lecture : `Disposition-Notification-To` et `Return-Receipt-To` si `MailDto.RequestReadReceipt`
  (`SmtpService.SetMessageHeaders`).
- **Aucun rapport entrant n'est lu.** Pas de lecture de `multipart/report` ni de `message/delivery-status`, pas de
  détection de MAILER-DAEMON. Un avis de non-remise ou un accusé de lecture **arrive comme un mail ordinaire** dans la
  Boîte de réception.
- La synchro relit déjà les en-têtes et la structure (`BackgroundImapService.FetchPendingMailsAsync`,
  `EmailBuildingService.MapHeaderFields`) : c'est là que la détection se branche.
- `MailRecipient` ne porte que le type, l'adresse et le nom : **aucun statut par destinataire**.
- `Message-ID` sortant : `{Guid}@{MailOptions.MessageIdDomain}`.
- **Écart de documentation** : E009 (F011, l.433, 783, 1006) annonce « MDN / DSN OK ». C'est faux pour les DSN.
- **Inconnu** : l'opérateur (Mailiz) et le relais MSSanté annoncent-ils l'extension `DSN` (`SmtpCapabilities.Dsn`) ?

## Objective

Pour chaque message envoyé, le praticien voit, **destinataire par destinataire**, où en est son message : **envoyé**,
**délivré**, **lu**, **en échec**. En cas d'échec, il lit **en français** ce qui s'est passé et quoi faire. Les
rapports techniques ne polluent plus la Boîte de réception.

Règles :
- **Demander la remise** : chaque envoi demande l'accusé de remise et l'avis d'échec (`NOTIFY=SUCCESS,FAILURE`,
  `ENVID` = identifiant du message, `RET=HDRS`), **si l'opérateur l'annonce**. Sinon, seuls les échecs et les lectures
  sont suivis, et l'écran le dit (« la remise n'est pas confirmée par votre opérateur »).
- **Lire les rapports** : un rapport de remise, un avis d'échec ou un accusé de lecture reçu est relié au message
  d'origine (par `Original-Envelope-Id`, `Original-Message-ID` ou les en-têtes joints), puis au destinataire concerné.
- **Statut par destinataire** :
  - « Envoyé » à l'envoi ;
  - « Délivré » à l'accusé de remise ;
  - « Lu » à l'accusé de lecture ;
  - « Échec » à l'avis de non-remise définitif ;
  - « Retardé, nouvel essai en cours » sur un échec temporaire (4.x.x).
- **Échec expliqué en français**, au moins :
  - 5.1.1 : « Cette adresse n'existe pas » ;
  - 5.2.2 : « La boîte du destinataire est pleine » ;
  - 5.7.x : « Le message a été refusé par la messagerie du destinataire » ;
  - dépassement de taille ;
  - échecs Mon espace santé (RG-E009-085) : messagerie du patient fermée, patient non trouvé, adresse invalide.

  Chaque motif dit **quoi faire** : vérifier l'adresse dans l'annuaire, réessayer plus tard, réduire les pièces
  jointes. Code inconnu : « Le message n'a pas pu être remis » et le code brut, à copier pour le support.
- **Où** :
  - dans Envoyés, une pastille de statut sur chaque ligne (le plus mauvais des destinataires) ;
  - dans le détail d'un envoi, une section « Suivi » qui liste chaque destinataire, son statut et son heure ;
  - un échec déclenche une notification dans l'application (« Votre message à Dr X n'a pas pu être remis ») et remet
    l'envoi dans « À traiter », si task-454 est livrée.
- **Rapports rangés** : un rapport relié à un envoi n'apparaît plus dans la Boîte de réception ; il reste consultable
  depuis le « Suivi ». Un rapport qu'on ne sait pas relier reste visible, comme aujourd'hui.
- **Boîte partagée** : le suivi appartient à la boîte, chacun le voit.

### Hors périmètre

- Signaler une adresse déjà en échec à la saisie : task-461.
- Relancer faute de réponse : task-462.
- Exploitation Mon espace santé (MDN patient, mineurs, taille) : task-464, qui s'appuie sur cette task.

## Definition of Done

- [ ] **D'abord, mesurer** : l'annonce `DSN` de l'opérateur (Mailiz formation et opérateur de test) relevée et
      consignée dans le `## Develop log`. Si les avis de non-remise eux-mêmes n'arrivent pas : `questions/task-460.md`
      et arrêt.
- [ ] Sous-classe de `SmtpClient` qui pose `NOTIFY`, `ENVID` et `RET` quand l'opérateur l'annonce ; repli sans DSN
      testé.
- [ ] Lecture des rapports entrants (RFC 3464, RFC 8098) à la synchro ; table des évènements de remise par
      destinataire dans la base de la boîte (migration FluentMigrator, audit règle 7c).
- [ ] Table de traduction des codes en français, avec action conseillée, et motifs Mon espace santé.
- [ ] Contrat : statut par destinataire et motif dans `MailDto` des envois ; paquet DTO publié.
- [ ] Acte système « rapport de remise reçu et relié » (sans personne) ; `HealthDataAccess`.
- [ ] Tests unitaires : lecture d'un DSN de succès, d'un 5.1.1, d'un 5.2.2, d'un 4.x.x, d'un MDN, d'un rapport non
      relié ; traduction de chaque code ; statut le plus mauvais pour la pastille.
- [ ] **Test d'intégration de bout en bout (règle 1b)** :
      - envoi vers une adresse inexistante (GreenMail et Dovecot), rapport d'échec injecté ou produit ;
      - `GET` de l'envoi : le destinataire est « Échec », avec « Cette adresse n'existe pas » ;
      - le rapport n'apparaît plus dans la liste de la Boîte de réception ;
      - cas nominal : un accusé de lecture passe le destinataire à « Lu ».
      Vu rouge.
- [ ] **Prévention (règle d'or)** : E009 corrigé (F011, l.433, 783, 1006 : « MDN / DSN OK » remplacé par l'état
      réel). Consigne dans `conventions/csharp.md` : un statut de conformité écrit dans une EPIC se prouve par un test
      qui le lit.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : pastille de statut, section « Suivi », motif et
      action en français, notification d'échec.
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-DELIVERY-001` v1 : un message envoyé à une adresse inexistante affiche « Échec — Cette adresse n'existe
        pas » dans Envoyés, et le rapport n'est pas dans la Boîte de réception ;
      - `E2E-DELIVERY-002` v1 : un envoi avec accusé de lecture passe à « Lu » quand l'accusé revient.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les logs (adresses du destinataire
      masquées, comme pour les autres journaux).
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend, weda2 et mobile sur la boîte de formation.
2. Envoyer un message à une adresse MSSanté inventée du domaine de formation (`inconnu.test@…`). Attendre l'avis :
   dans Envoyés, la ligne porte « Échec ». Le détail dit « Cette adresse n'existe pas — vérifiez l'adresse dans
   l'annuaire ». La Boîte de réception ne contient pas l'avis brut.
3. Envoyer un message à une seconde boîte de test avec « Demander un accusé de lecture », ouvrir le message depuis
   cette boîte et accepter l'accusé : le statut passe à « Lu », avec l'heure.
4. Si l'opérateur annonce `DSN` : le statut « Délivré » apparaît avant « Lu ». Sinon, la mention « la remise n'est pas
   confirmée par votre opérateur » est affichée.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 / référentiel MSSanté #2 Clients (DSN et MDN) ; anticipation du référentiel opérateurs 1.7
  (DSN et NDR en français)
- **Exigences DSR honorées** : Ref#2 Clients — demande d'accusé de remise (DSN, RFC 3461) et de lecture (MDN,
  RFC 8098) ; RG-E009-085 (non-distribution MES) en lecture
- **INS** : non applicable — aucun identifiant patient lu dans les rapports (les adresses `@patient.mssante.fr` sont
  masquées dans les logs)
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; envoi MSSanté par jeton PSC (XOAUTH2)
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : volet de transport MSSanté ; RFC 3461, 3464, 8098
- **Tracé PGSSI-S** : réception et rattachement d'un rapport en acte système ; envoi inchangé (`MailSend`) ;
  `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : codes d'état SMTP étendus (RFC 3463)
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé — les statuts concernent des envois déjà traités
