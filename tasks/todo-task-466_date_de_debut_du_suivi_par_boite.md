# todo-task-466.md — Date de début du suivi par boîte

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-453 (ancrage des états de travail)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-12. **À passer avant task-454 et task-463** : c'est le socle
commun de « à acquitter » et de « à traiter ».

> **Origine.** Échange avec l'humain du 2026-11-12, en arbitrant task-454 : « la biologie de l'historique ne doit pas
> attendre d'acquittement, car un médecin qui synchronise sa boîte la première fois va prendre deux ans d'historique.
> Le marquage « traité » ou l'acquittement de biologie ne doit s'activer que sur les nouveaux mails. » Décision du même
> jour : **toute personne de la boîte** peut modifier la date de début du suivi.

## Ce qui est établi

Lecture du code au 2026-11-12 (`Api/Mail/src`) :

- Une ligne `Mails` ne garde que la date **annoncée par l'expéditeur** (`Mail.SentDate`, en-tête `Date`). La date
  d'arrivée sur le serveur (`INTERNALDATE`) est lue pendant la synchronisation (`ImapService`, `MessageSummaryItems.InternalDate`)
  mais n'est pas stockée.
- « Bio à acquitter » compte **tous** les documents de biologie signalés par le laboratoire et non résolus, quelle que
  soit leur ancienneté : puce et pages servies (`BiologyAckRepository`, `biology-acks/pending-mail-uids[/page]`,
  `pending-summary`), compteurs par mail (`MailDto.PendingBiologyAcksCount`, `HasCriticalPendingBiologyAck`, calculés
  par `MailRepository.EnrichManyWithBiologyAcksAsync`), état d'un document (`BiologyAckState`, `Pending` par défaut),
  tuile du tableau de bord.
- Une première synchronisation ramène tout l'historique de la boîte. Une purge sur changement d'UIDVALIDITY, une base
  recréée ou une resynchronisation ré-ingèrent des messages anciens : leur **date d'ingestion** est récente, leur date
  d'arrivée ne l'est pas.

## Objective

Chaque boîte porte une **date de début du suivi**. Un message est **suivi** quand il est arrivé sur le serveur de
messagerie après cette date. Seuls les messages suivis **réclament** quelque chose : « Bio à acquitter » aujourd'hui,
« À traiter » demain (task-454). L'historique se consulte, s'acquitte si le praticien le souhaite, mais ne réclame
rien.

Règles :
- **Message suivi** : sa **date d'arrivée** (`INTERNALDATE`, désormais stockée à l'ingestion) est postérieure ou égale
  à la date de début du suivi de la boîte.
  - Date d'arrivée absente (lignes antérieures à cette US, pas de reprise) : repli sur la date d'envoi.
  - Aucune date : le message est traité comme **historique**.
- **Date posée à la création de la base de la boîte** (premier rattachement), **avant** la première synchronisation.
  Deux ans d'historique ramenés ensuite restent hors suivi ; un compte rendu arrivé pendant ou après la
  synchronisation est suivi.
  - Boîtes existantes : la migration pose la date à l'instant où elle s'exécute (une ligne par boîte, aucune reprise
    des messages).
- **Stabilité** : un déplacement, une purge d'UIDVALIDITY, une resynchronisation ou une base ré-ingérée ne font
  revenir aucun message dans le suivi, puisque la date d'arrivée ne change pas.
- **Nouvelle remise** : un ancien résultat **renvoyé aujourd'hui** par le laboratoire est une nouvelle arrivée, donc
  suivi.
- **Ce que le suivi gouverne** (biologie, dans cette US) : puce « Bio à acquitter » et ses pages, compteurs par mail,
  tuile du tableau de bord, alertes de résultat critique. Un document de biologie d'un message **non suivi** :
  - n'est compté nulle part, ne déclenche aucune alerte ;
  - affiche l'état neutre **« Antérieur au suivi »** (nouvel état du contrat), jamais « À traiter » ;
  - **peut** être acquitté : l'acquittement est enregistré, imputé et affiché comme aujourd'hui. Il n'est jamais
    réclamé.
- **Réglage** : dans les paramètres de la boîte, « Suivre les messages arrivés depuis le … ».
  - Valable pour **toute la boîte** (donnée de la boîte, règle 14).
  - Modifiable par **toute personne de la boîte** (titulaire, membre, délégataire), sous verdict récent de
    l'opérateur ; tracé au nom de la personne, avec l'ancienne et la nouvelle date.
  - Reculer la date fait entrer l'historique récent dans le suivi ; l'avancer l'en retire. Rien n'est écrit ni effacé
    sur les messages : le suivi se calcule à la lecture.
- **Ancrage** : la date d'arrivée suit le message ré-ingéré (modèle de task-453).

### Hors périmètre

- L'état « traité » et le compteur « à traiter » : task-454, qui s'appuiera sur cette règle.
- Le suivi daté d'un résultat jusqu'à « résultat communiqué » : task-463, idem.
- Un réglage par personne : la date appartient à la boîte.

## Definition of Done

- [ ] Date d'arrivée stockée : colonne sur `Mails` alimentée par l'`INTERNALDATE` à l'ingestion (insertion et
      promotion d'un en-tête), sans reprise des lignes existantes ; migration FluentMigrator, audit de migration
      (règle 7c), modèle EF identique.
- [ ] Date de début du suivi stockée dans la base de la boîte : posée à la création de la base, posée par la migration
      pour les bases existantes (une ligne) ; test de migration (base neuve et base existante).
- [ ] Contrat : nouvel état `BiologyAckResolutionState` « Antérieur au suivi » (valeur appendue, explicite) ; date de
      début du suivi lue et modifiée par les réglages de la boîte ; paquet `HealthPlatform.Dtos.Mss` publié et
      consommateurs à jour ; miroirs TypeScript (weda2, mobile).
- [ ] Acte d'audit `MailboxTrackingStartChanged` (personne réelle, ancienne et nouvelle date) en fin de
      `AuditActionType`, miroirs TypeScript, famille `HealthDataAccess`, contrôleur marqué `[Audited]`.
- [ ] Tests unitaires de la règle « suivi » : arrivée après / avant / égale à la date ; repli sur la date d'envoi ; sans
      aucune date → historique ; nouvelle remise d'un ancien résultat → suivi.
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur la puce et les compteurs de biologie
      (`GET biology-acks/pending-mail-uids/page`, `GET biology-acks/pending-summary`) et sur
      `GET api/v1/Mail/folders/{f}/emails/{ids}` : une boîte avec un compte rendu anormal **arrivé avant** la date de
      début et un **arrivé après** ; seul le second est compté, porte `PendingBiologyAcksCount = 1` et
      `BiologyAckState = Pending` ; le premier lit `BiologyAckState = Antérieur au suivi`, `PendingBiologyAcksCount = 0`,
      `HasCriticalPendingBiologyAck = false`. Cas d'échec : date de début invalide (future) → 400 en `ProblemDetails`.
      Vu rouge.
- [ ] **Test d'intégration de la stabilité** : purge sur changement d'UIDVALIDITY puis ré-ingestion d'un compte rendu
      historique ; il reste « Antérieur au suivi ». Vu rouge (avec une date d'ingestion à la place de la date d'arrivée).
- [ ] **Test d'intégration du réglage** : reculer la date fait compter le compte rendu historique ; la relecture le
      prouve. Acquitter un compte rendu historique reste possible, et son acquittement est relu.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire change la date de début du suivi ; le
      titulaire relit la nouvelle date et ses compteurs ; la trace d'audit porte le délégataire (RPPS, nom, rôle).
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : panneau d'acquittement « Antérieur au suivi »
      (pas de « À traiter », geste d'acquittement toujours disponible), réglage « Suivre les messages arrivés
      depuis le … ».
- [ ] **Scénario e2e** `E2E-BIO-007` v1 ajouté à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis, vu rouge par
      mutation : « une première synchronisation avec de la biologie ancienne n'affiche rien à acquitter ; un compte
      rendu arrivé ensuite est à acquitter ». Le seed du banc pose des messages arrivés avant la date de début ;
      `E2E-BIO-001` à `004` restent verts (leur biologie est arrivée après).
- [ ] Prévention (règle d'or) : consigne dans `conventions/csharp.md` — « un compteur ou un état qui réclame une
      action (à acquitter, à traiter) se borne à la date de début du suivi, comparée à la date d'arrivée, jamais à
      la date d'ingestion ».
- [ ] Aucune donnée de santé dans les logs ; `data-testid` sur chaque élément interactif ajouté.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, `Dtos`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et weda2 (`cd Client/Angular/front && npm start`).
2. Rattacher une **nouvelle** boîte de formation qui contient des comptes rendus de biologie anciens. Pendant et après
   la première synchronisation : la puce « Bio à acquitter » et la tuile du tableau de bord restent à 0 pour
   l'historique.
3. Ouvrir un ancien compte rendu anormal : le panneau dit « Antérieur au suivi » ; l'acquitter quand même : il est
   enregistré à votre nom.
4. Envoyer un nouveau compte rendu anormal vers la boîte : il apparaît dans « Bio à acquitter », état « À traiter ».
5. Paramètres de la boîte : « Suivre les messages arrivés depuis le » une date de la semaine dernière. Les comptes
   rendus anormaux de la semaine apparaissent dans « Bio à acquitter ». Remettre la date d'origine : ils sortent.
6. Mobile, délégataire de la même boîte : changer la date ; sur weda2, le titulaire voit la nouvelle date et les
   compteurs mis à jour ; le journal de la boîte dit que le délégataire l'a changée.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (biologie reçue, LGC)
- **Vague Ségur** : hors Ségur — organisation du suivi ; prolonge l'acquittement des comptes rendus de biologie
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucun identifiant patient manipulé
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : titulaire, membre et délégataire peuvent modifier la date (décision humaine du 2026-11-12),
  sous verdict récent de l'opérateur (règle 14) ; rien sans verdict
- **Interop CI-SIS** : non applicable — date d'arrivée IMAP, pas de document CI-SIS produit ; lecture inchangée des
  CDA R2 et HPRIM
- **Tracé PGSSI-S** : `MailboxTrackingStartChanged` au nom de la personne réelle (RPPS, nom PSC, rôle, boîte,
  ancienne et nouvelle date) ; pose initiale de la date en acte système ; famille `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (inchangé)
- **Hébergement HDS** : oui — base de la boîte, environnement HDS de production
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle sur le patient ; la date d'arrivée d'un message est une
  métadonnée de messagerie
