# task-399 — Délégation de BAL : envoyer de la part du délégant

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-398 (BAL déléguées visibles, propriétaire et rôle des dossiers dans le contrat)
**Epic**: E009
**Priorité**: **3** — sans elle, un délégataire lit et trie la BAL du médecin mais ne peut pas
répondre pour lui. Répondre et Transférer sont masqués sur les messages délégués depuis la
task-398.

> **Analyse** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md)
> (§1 règles Mailiz, §4 inconnues).
> **Revue du code** : [Docs/audits/delegation-bal-revue-code-20261025.md](../Docs/audits/delegation-bal-revue-code-20261025.md),
> §3.9 et §3.4.
> **Règle 14** (CLAUDE.md) : rien d'une BAL déléguée n'est persisté chez le délégataire. Elle couvre
> les brouillons et copies **au nom du délégant**, les envois différés et les journaux.

## Ce que dit Mailiz (mode opératoire, novembre 2025)

- Le champ **De** porte **l'adresse du délégant**, avec le libellé « *Nom du délégataire*, de la
  part de *adresse du délégant* ».
- Le message va dans les **Envoyés du délégant**, visibles par lui et par les autres délégataires.
- Avec plusieurs délégations, le délégataire **choisit la BAL émettrice**.
- L'accès délégué depuis un logiciel métier n'est « pas encore » ouvert. Le comportement SMTP n'est
  pas documenté.

## Décisions actées (humain, 2026-10-25)

1. **Caractériser d'abord, avec un point d'arrêt.** Si Mailiz refuse l'envoi délégué depuis un
   logiciel métier, la task s'arrête sur `questions/task-399.md`.
2. **Choix obligatoire de la BAL émettrice.** Dès qu'on a une délégation, le champ **De** de toute
   rédaction est vide, réponses et transferts compris, jusqu'à ce qu'on choisisse. Sans délégation,
   rien ne change.
3. **Brouillons au nom du délégant dans ses Brouillons IMAP** (`shared/<adresse>/Drafts`), jamais
   dans Redis.
4. **Signature : celle du délégataire.**
5. **Jamais d'accusé de lecture en délégation.**
6. **Répondre ou transférer un message délégué en « (moi) » est permis, et la copie est assumée.**
   C'est un message **du délégataire** : brouillon Redis, Envoyés et traitement de **sa** BAL, y
   compris le contenu cité et le CDA transféré. C'est un acte volontaire, hors règle 14, qui ne
   protège que ce qui est fait **au nom du délégant**.
7. **Opposition MSSanté : limite acceptée et affichée.** L'opposition est lue dans la base du
   délégataire. Celle du délégant n'est pas connue, et la rédaction au nom du délégant le signale.
8. **Pas d'aide IA** à la rédaction au nom du délégant (correction, amélioration du texte), par
   cohérence avec « pas d'IA » sur la BAL déléguée.

## Objective

Un délégataire rédige un message, une réponse ou un transfert, choisit explicitement la BAL au nom
de laquelle il écrit, et l'envoie. Au nom du délégant : le destinataire voit un message du délégant
« de la part de » son délégataire, la copie est dans les Envoyés du délégant, et rien n'en reste
chez le délégataire.

## Règles

### Identités et champ De

- **Identités d'envoi** : sa propre adresse et chaque BAL déléguée découverte par un **`LIST` en
  direct**, jamais lue dans le cache Redis de la liste des dossiers.
- **Contrôle du `From`** : une **exception typée** nouvelle, mappée en **403** ProblemDetails, est
  levée si le `From` n'est pas une identité permise. Elle est vérifiée :
  - dans le point commun des envois (`OutgoingMailService` / `SmtpService`) ;
  - dans la mise en attente (`QueueReadyToSendAsync`) ;
  - à la **confirmation d'un envoi différé** (`MailController.cs:1661`).
- **Champ De** (décision 2) :
  - choix « `<adresse>` (moi) » et « `<adresse>` (délégation) », envoi impossible sans choix ;
  - **aucun enregistrement de brouillon** (automatique, à la fermeture, à la sortie) tant que le
    champ est vide ;
  - « Répondre à tous » est **recalculé à chaque changement** du champ De : il retire l'adresse
    émettrice et la propre adresse.

### Envoi au nom du délégant

- **En-têtes** : `From`, `Sender` et libellé suivent le contrat **caractérisé**. Attention :
  MailKit prend `Sender`, s'il est posé, comme `MAIL FROM`.
  - Le libellé « *Nom du délégataire*, de la part de *adresse* » remplace
    `ResolveSenderDisplayNameAsync` (`SmtpService.cs:272-297`) pour un envoi délégué.
  - Le client **n'envoie pas** de `from.name`, aujourd'hui le nom du délégataire (mobile
    `mail-compose.component.ts:1204-1209`).
- **Archivage** : `SentArchiveDispatcher`, `SentArchiveService` et `AppendToSentAsync` reçoivent un
  **dossier cible explicite**, `shared/<adresse>/Sent`. Si Mailiz classe lui-même la copie, on
  n'archive rien.
  - Jamais dans les Envoyés du délégataire.
  - La trace `MailArchiveSent` porte le dossier cible.
- **Signature** : celles du délégataire.
- **Modèles** : `{{SenderEmail}}` vaut l'adresse émettrice choisie, et `{{SenderRPPS}}` le RPPS du
  délégataire. Cela corrige au passage le bug de weda2, qui y met la partie locale de l'adresse
  (`mail-compose.component.ts:2664`).
- **Opposition** (décision 7) : un bandeau « Opposition du délégant non vérifiable » est affiché
  pour un destinataire patient.
- **Accusé demandé** sur un envoi délégué : l'accusé revient dans la BAL du délégant.
- **Pas d'aide IA** (décision 8) : correction et amélioration masquées, et refusées par l'API pour un
  `From` délégué.
- **Hors ligne** : aucun envoi ni brouillon au nom du délégant, refusé aux **trois** points
  d'entrée (`MailController.cs:1464`, `:1549`, `DraftService.cs:267`) et à la confirmation d'un
  envoi différé. Rien n'est mis en attente.
- **Révocation en cours de rédaction** : le 403 ou le refus d'enregistrement est affiché, et le texte
  reste **en mémoire**, sans repli sur Redis ni sur la file hors ligne.
- **Annuler et remplacer** reste refusé sur un message délégué (task-397).

### Brouillons au nom du délégant (décision 3)

- **Contrat** :
  - un **identifiant stable**, indépendant de l'UID, qui change à chaque enregistrement ;
  - une route de **relecture en rédaction** ;
  - l'en-tête `From` = délégant dans le brouillon ;
  - **aucun nom de dossier** dans les journaux (`ImapService.cs:4537`).
- **Champs conservés** : le contrat dit lesquels des champs de `SaveDraftDto` survivent à
  l'aller-retour IMAP : `BlockPatientReply`, `RequestReadReceipt`, `OppositionAcknowledged`,
  `Packaging` IHE-XDM, `CancelAndReplace*`.
- **Écriture** : `AppendToDraftsAsync` vise les Brouillons **de la session**, et `ReplaceDraftAsync`
  n'est pas atomique (ajout puis suppression). Il faut un remplacement qui ne laisse ni doublon ni
  orphelin.
- **Anti-double-envoi** : sans clé Redis contenant un chemin délégué.
- **Changer de BAL** en cours de rédaction :
  - de « moi » vers « délégation » : suppression du brouillon **Redis** ;
  - de « délégation » vers « moi » : suppression du brouillon **IMAP**.
- **La règle de la task-394** (« corps non modifié, pas de brouillon ») est **côté client** : elle
  vaut aussi pour un brouillon délégué, et se prouve en tests de composants et en e2e.
- **Dossier virtuel « Brouillons »** : il ne masque pas `shared/<A>/Drafts` une fois les rôles de la
  task-398 posés.

### Audit et journaux

Les traces d'envoi, de brouillon et d'acquittement d'opposition **au nom du délégant** suivent la
liste blanche de task-397 (règle E). Sont vidés :
- `Subject`, `ToAddresses` ;
- `ServerRequest` (destinataires, empreinte d'INS), `ServerResponse` ;
- `ErrorMessage`, `ErrorDetails`.

Aucun destinataire d'un envoi délégué n'apparaît dans Seq (`SmtpService.cs:78, 119`,
`MssanteHeaderService.cs:67, 155`).

## Definition of Done

- [ ] **Caractérisation SMTP et IMAP Mailiz** consignée dans le `## Develop log` et l'analyse (§4).
      Elle est faite sur les comptes de formation, vers une boîte de test lisible, et mesure :
      - `From` = délégant avec `MAIL FROM` = délégant, **et** avec `MAIL FROM` = délégataire (via
        `Sender`) ;
      - les en-têtes reçus ;
      - le classement automatique dans les Envoyés du délégant ;
      - les droits `MYRIGHTS` sur `shared/<A>/Drafts` et `/Sent` (ajout, suppression).

      **Refus → arrêt** et `questions/task-399.md`.
- [ ] **Bancs** : le banc d'intégration et le banc e2e reproduisent le comportement caractérisé.
      Pour l'e2e, le puits SMTP doit appliquer la règle d'acceptation du `From` et le classement des
      Envoyés.
- [ ] `dtos-mss` : identités d'envoi, BAL émettrice dans l'envoi et le brouillon, identifiant de
      brouillon délégué. Paquet publié, consommateurs mis à jour, types TypeScript alignés.
- [ ] Test d'intégration de bout en bout pour l'envoi au nom du délégant :
      - en-têtes reçus conformes ;
      - copie dans `shared/<A>/Sent` **une seule fois** ;
      - **absente** des Envoyés de B.

      Vu rouge (règle 1b).
- [ ] Test d'intégration : `From` hors identités → **403**, rien d'envoyé. Le même `From` dans un
      envoi différé confirmé → 403.
- [ ] Test d'intégration — brouillons délégués :
      - enregistrer deux fois : un seul brouillon ;
      - rouvrir par la route de relecture : champs conservés ;
      - envoyer : retiré du dossier ;
      - changer de BAL dans les deux sens : aucun brouillon orphelin, ni Redis ni IMAP ;
      - double envoi concurrent : un seul message parti.
- [ ] Test d'intégration « rien de persisté » (règle 14) après envoi, brouillons et **transfert avec
      pièce jointe par référence** au nom du délégant :
      - zéro ligne liée en base ;
      - aucune clé ni valeur Redis portant le brouillon, le contenu ou le chemin ;
      - aucune `PendingActions` ;
      - aucun contact créé ;
      - aucun destinataire dans les journaux capturés.
- [ ] Test d'intégration : hors ligne, envoi et brouillon délégués refusés aux trois points
      d'entrée, rien mis en attente.
- [ ] Test d'intégration : la trace d'audit de l'envoi délégué ne garde que les champs de la liste
      blanche. `MailArchiveSent` porte le dossier cible.
- [ ] Test d'intégration : correction et amélioration IA avec un `From` délégué → refus, zéro appel
      au fournisseur.
- [ ] Non-régression :
      - un utilisateur **sans** délégation envoie comme aujourd'hui ;
      - un envoi en « (moi) » répondant à un message délégué suit le circuit normal du délégataire
        (décision 6).
- [ ] Tests de composants, sur mobile et weda2 :
      - champ De vide, envoi impossible sans choix ;
      - **aucun enregistrement de brouillon tant que De est vide** ;
      - corps non modifié, pas de brouillon (task-394) ;
      - Répondre et Transférer rétablis, « Répondre à tous » recalculé au changement de De ;
      - pas de `from.name` ;
      - signature et variables de modèle ;
      - bandeau d'opposition non vérifiable ;
      - IA masquée au nom du délégant ;
      - révocation en cours de rédaction, texte conservé ;
      - message hors ligne.
- [ ] Scénarios ajoutés dans `Api/Mail/e2e/scenarios.yml`, implémentés sur mobile et angular :
      - **E2E-DELEG-005** : envoyer au nom du délégant → dans les Envoyés de la BAL déléguée, pas dans
        les siens ;
      - **E2E-DELEG-006** : brouillon au nom du délégant, rouvert, envoyé ;
      - **E2E-DELEG-007** : avec une délégation, l'envoi est impossible tant que la BAL émettrice
        n'est pas choisie.

      **E2E-DELEG-003** passe à la version 2 : Répondre et Transférer sont proposés.
- [ ] Build et tests verts sur les quatre dépôts ; `/e2e` vert, avec parité verte.

## Manual Test Plan

Comptes de formation : Cyril, délégataire de Virginie. Lancer l'AppHost, le mobile et weda2, puis
se connecter en Cyril par PSC.

1. **Nouveau message.** Le champ De est vide et l'envoi est impossible. Écrire une phrase, puis
   fermer : aucun brouillon n'est créé tant que De n'est pas choisi.
2. **Envoi.** Choisir Virginie et écrire à une boîte de test. À réception, le message vient de
   Virginie, de la part de Cyril. Il est dans les Envoyés de la boîte de Virginie, pas dans ceux de
   Cyril.
3. **Brouillon.** Au nom de Virginie, écrire puis fermer : le brouillon est dans les Brouillons de
   sa boîte, et son webmail le montre. Le rouvrir, puis l'envoyer : il disparaît.
4. **Changer de BAL.** Au milieu d'une rédaction enregistrée, passer de Virginie à « moi » : plus de
   brouillon dans la boîte de Virginie, un seul chez Cyril.
5. **Réponse en « moi ».** Répondre à un message délégué en choisissant « moi » : le message part de
   Cyril et va dans ses Envoyés. C'est permis.
6. **Opposition.** Au nom de Virginie, écrire à un patient : le bandeau « opposition du délégant non
   vérifiable » s'affiche.
7. **IA.** Au nom de Virginie, la correction et l'amélioration du texte ne sont pas proposées.
8. **Hors ligne.** Couper le réseau et tenter d'envoyer au nom de Virginie : refus clair, rien
   n'est mis en attente.
9. **Sans délégation** : la rédaction est inchangée, sans champ De.
10. **Rien chez Cyril** : après les étapes 2 à 4, sa base ne contient rien des envois et brouillons
    au nom de Virginie, et Seq ne montre aucun destinataire de ces envois.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — fonctionnalité Mailiz sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable. Le mode opératoire Mailiz est suivi : `From` du
  délégant, libellé « de la part de », Envoyés du délégant, choix explicite de la BAL émettrice.
- **INS** : inchangé. Pièces médicales jointes produites comme aujourd'hui, avec le délégataire pour
  auteur.
- **Authentification PS** : PSC / e-CPS du délégataire ; l'envoi reste un acte sensible
  authentifié fortement.
- **Habilitations** : un envoi au nom d'un délégant n'est permis que pour une BAL découverte en
  direct, et l'API refuse tout autre `From`.
- **Interop CI-SIS** : inchangé — enveloppe IHE-XDM existante, en-têtes selon la caractérisation
- **Tracé PGSSI-S** : envoi délégué tracé avec la BAL émettrice, liste blanche de la règle 14.
  Imputabilité complète en task-400.
- **Consentement patient** : opposition MSSanté vérifiée chez le délégataire seulement, **limite
  affichée** (décision 7)
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — rien d'un envoi au nom du délégant n'est stocké chez le
  délégataire
- **AIPD / impact RGPD** : à compléter. Il faut y ajouter l'envoi au nom d'un tiers et la copie
  assumée d'une réponse en « moi ».

## Notes de cadrage

- **Constats et lignes** : revue, §3.9 (envoi et brouillons) et §3.4 (audit).
- **Champ De obligatoire** : il s'applique à **toute** rédaction d'un utilisateur qui a une
  délégation, comme dans le webmail Mailiz.
- **Hors périmètre** : traçabilité consultable par le délégant (task-400), gestion des délégations.

## Branches
- `dtos-mss` (lazy) : aucune branche au /start — `/develop` crée `feat/task-399-delegation-envoyer-de-la-part-du` depuis `origin/develop` s'il touche un contrat
- `api-mail` (pushed) : feat/task-399-delegation-envoyer-de-la-part-du — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-399-delegation-envoyer-de-la-part-du
- `client-mobile` (pushed) : feat/task-399-delegation-envoyer-de-la-part-du — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-399-delegation-envoyer-de-la-part-du
- `client-angular` (code-only) : la forge écrit sur la branche checkée out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

### Caractérisation Mailiz (2026-10-26, décision 1 levée)

Sonde MailKit en session XOAUTH2 de Cyril (jeton PSC fourni par l'humain), deux passages. Détail :
[analyse §4 bis](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md).

- Envoi délégué **accepté** dans les trois variantes (`MAIL FROM` = délégant ; `Sender` = délégataire ;
  `MAIL FROM` = délégataire sans `Sender`). Aucun en-tête réécrit, aucun libellé ajouté.
- **Aucune copie automatique** dans `shared/<V>/Sent` ni dans les Envoyés de Cyril → `APPEND` à notre charge.
- `MYRIGHTS` = `lrwstipekxacd` sur `Drafts`, `Sent` et la racine ; `APPEND` + `UID EXPUNGE` d'un brouillon vérifiés.
- Dossiers partagés **sans** SPECIAL-USE : identification par le nom.
- **Mailiz ne contrôle pas le `From`** (adresse sans délégation acceptée) : le 403 de l'API est le seul garde-fou.
- Contrat retenu : `From` = « Nom, de la part de adresse » `<délégant>`, `Sender` = délégataire,
  enveloppe `MAIL FROM` = délégant.

### Implémentation

- **Repos touchés** : `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code seul, non commité).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` 536.0.0 → **540.0.0** (`SendingIdentityDto`,
  `SendingIdentityErrorCodes`, `SaveDraftDto.FromMailbox`, `DraftDto.FromMailbox`). Bump dans `api-mail`
  seulement : `client-blazor` n'est pas listé, le contrat est additif.
- **Commits** :
  - dtos-mss : `9edecc9` feat(dto): identités d'envoi, BAL émettrice d'un brouillon délégué
  - api-mail : `762ef40d` bump DTO 540 · `10f6be7e` feat(delegation) · `582d536e` test(e2e) catalogue ·
    `33db4b62` simplify pass · `d7c8a431` fix(imap) libellé du verrou réduit à sa famille
  - client-mobile : `5e4f70e` feat(mobile) · `0fe9801` simplify pass · `8432089` test(mobile) parcours
  - client-angular : branche `feature/nova-mss-weda-integration`, **non commité** (code seul) —
    `libs/mss/src/core/models/draft.model.ts`, `core/services/mss-api.service.ts`,
    `features/mail/services/mail-event.service.ts`, `features/mail/mss-mail.component.ts` (+ spec
    délégation), `features/mail/components/mail-compose/*`
    (dont `mail-compose-delegation.component.spec.ts`), `features/mail/components/mail-detail/*`,
    `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/{compose,e2e-backend}.ts`.
- **Backend** : `SendingIdentityService` (LIST en direct + STATUS de chaque racine), contrôle du `From`
  dans `SmtpService` (point commun : direct, brouillon, différé confirmé), refus hors ligne à la mise en
  attente (`sendmail`) et au brouillon délégué, en-têtes caractérisés (`DelegatedSend`), archivage
  explicite `shared/<A>/Sent` (surcharges `Dispatch`/`ArchiveWithRetryAsync`/`AppendToSentAsync`),
  `DelegatedDraftService` (Brouillons IMAP, identifiant `X-HealthPlatform-Draft-Id`, options en en-tête,
  remplacement sans orphelin, verrou d'envoi sans chemin), `DraftId` des brouillons délégués lu dans
  la liste et le détail, IA refusée (`AI_REFUSED_ON_BEHALF`), route `GET /mail/sending-identities`.
- **Bancs** : Mailiz accepte tout `From` et ne classe aucune copie ; GreenMail fait de même — le banc
  d'intégration et le banc e2e reproduisent déjà la caractérisation, sans changement.
- **Local build / test** : ✓ api-mail (api 1352, application 3702, intégration complète 1019/0 échec
  avant la passe qualité, puis classes de délégation et d'envoi 51/51), ✓ client-mobile (1353),
  ✓ client-angular lib mss (1356 avant passe, compose + détail 264 après).
- **Tests d'intégration (règle 1b)**, `DelegatedSendEndToEndTests` (14) — vus rouges par mutation :
  M1 archivage dans les Envoyés propres → `ASendOnBehalf…` (« Expected: 1 ») ; M2 identité non
  contrôlée → `AFromThatIsNeither…`, `AWithdrawnDelegation…`, `ADeferredSendConfirmed…` (« Attendu 403,
  reçu 200 ») ; M3 `MAIL FROM` = Sender → `ASendOnBehalf…` (Return-Path) ; M4 mise en attente hors ligne
  permise → `Offline_…` (« reçu 202 ») ; M5 version antérieure gardée et M8 brouillon laissé après envoi
  → `ADraftOnBehalf…SavedTwice…` ; M6 IA non refusée → `TheAiAids…` (« reçu 200 ») ; M7 trace sans
  dossier → `TheAuditOfASendOnBehalf…`. M9 (contrôle STATUS) : vu rouge en test unitaire
  (`SendingIdentityServiceTests`, 3 rouges), le banc Dovecot ne listant pas une racine retirée.
- **Fuite règle 14 trouvée par le test « rien de persisté »** : le libellé du verrou IMAP portait
  `shared/<A>:<uid>:<pièce>` (le masquage coupe au « / »). Corrigé à la source (`ImapLockScope` ne
  journalise que la famille), test unitaire vu rouge sur l'ancien code.
- **Fenêtre de retrait** (mesurée sur le banc) : une session poolée voit encore une délégation retirée
  tant que le cache ACL de Dovecot (30 s) ne l'a pas relue ; au-delà, 403. Test
  `ADelegationWithdrawnWhileHisSessionIsOpen…`. Celle de Mailiz est à caractériser au HAG
  (décision 9 de la task-397 : fenêtre bornée acceptée).
- **Passe qualité (/simplify)** :
  - Appliqué & committé : api-mail (`33db4b62` — règle « adresse d'autrui » unique, contrôle de racine
    partagé, `DelegatedMailboxRule.FolderOf`, code mort, `EmailAddressHelper`, fermeture tolérante) ;
    client-mobile (`0fe9801` — `onBehalfMailbox`, `normalizeAddress`, messages liés au gabarit).
  - Appliqué (code seul, non commité) : client-angular (`mail-compose.component.{ts,html}`,
    `mail-detail.component.ts`).
  - Écarté (hors « sans changement de comportement » ou trop large) : cache des identités d'envoi
    (client et serveur), contrôle d'une seule racine dans `ResolveAsync`, double résolution par envoi,
    fusion des surcharges d'archivage, `DraftMimeBuilder`, aiguillage des brouillons dans le service,
    `draftRef { id, mailbox }`, appels d'API sans ternaire (assertions d'espions).
  - Ignoré : `dtos-mss` (porteur de contrat).
- **Instabilité observée** : client-mobile, 4 tests de rendu des suggestions (task-388) rouges une fois,
  verts à la relance (1353/1353) — sans lien avec le diff.

### Parcours e2e (banc `e2e`, joués par `/develop` avant la chaîne)

- **Catalogue** (`api-mail` `582d536e`) : E2E-DELEG-003 v2 (Répondre / Transférer rétablis, IA et
  dossier Weda toujours masqués), E2E-DELEG-005 (envoi au nom de la délégante), 006 (brouillon chez
  elle, rouvert, envoyé), 007 (envoi impossible sans boîte émettrice). Clients requis : mobile et weda2.
- **Le champ De est obligatoire dès qu'une délégation existe** : les 12 parcours d'envoi existants
  choisissent désormais la boîte (`chooseSender`), sur les deux clients.
- **client-mobile** (`8432089`) : 003/005/006/007 verts. Mutations : `onBehalfMailbox` neutralisé →
  005 et 006 rouges ; `fromRequired` neutralisé → 007 rouge ; garde des réponses remise → 003 rouge.
- **client-angular** (code seul) : 003/005/006/007 verts. Mutations : WM1 `onBehalfMailbox` → 005
  (« la copie est dans les Envoyés de la délégante ») et 006 rouges ; WM2 `fromRequired` → 007 (« le
  choix est demandé ») rouge ; WM3 garde `!isDelegated()` remise sur les réponses → 003 rouge. Sources
  restaurées, horodatage rafraîchi.
- **Correctif trouvé par le parcours 006 sur weda2** : un clic sur un brouillon délégué ouvrait sa
  lecture, pas sa rédaction. `mss-mail.component.ts` rouvre désormais un brouillon délégué portant
  un identifiant en rédaction, avec `fromMailbox` = la délégante ; sans identifiant (brouillon écrit
  ailleurs), il se lit. Deux tests unitaires (`mss-mail.component.delegation.spec.ts`), le premier vu
  rouge par mutation. Dossier `features/mail` : 625/625.
- **Défauts préexistants relevés, hors périmètre** : la recherche de contacts du mobile garde son
  `distinctUntilChanged` d'une rédaction à l'autre (même saisie → aucune suggestion) ; le balayage du
  parcours DELEG-003 mobile est instable ; une surcouche d'erreur Vite passagère au rechargement weda2.

### Reprise après /e2e (2026-10-26, validée par l'humain)

- **api-mail** `5964f2c1` : seed e2e, budget d'appel du registre à 30 s (`RegistryComposition.SeedCallTimeout`).
- **client-mobile** `aac3ebb` : E2E-COMPOSE-002 choisit la boîte émettrice (« moi ») avant d'envoyer
  (règle 2) ; DELEG-005/006/007 suppriment en `finally` le message reçu par le praticien.
- **client-angular** (code seul, **à commiter par l'humain**) : mêmes deux correctifs dans
  `e2e/mss-e2e/specs/live-ai.e2e.ts` et `e2e/mss-e2e/specs/functional.e2e.ts` (prettier appliqué).
  Type-check des specs e2e vert sur les deux clients.

- **Preuves rouges complétées par `/review`** (2026-10-26, mutations réinjectées puis sources restaurées,
  arbre propre vérifié) :
  - MA — `DELETE /mail/drafts/{id}?mailbox=` routé vers Redis (`DraftController`, garde `IsOnBehalf`
    neutralisée) → `SwitchingTheSendingMailbox…` rouge (« Expected: 0, Actual: 1 » brouillon IMAP orphelin) ;
  - MB — verrou d'envoi neutralisé (`DelegatedDraftService.SendAsync`, jeton factice) →
    `TwoConcurrentSendsOfTheSameDelegatedDraft…` rouge (deux envois en 200) ;
  - MC — délégations non ajoutées à `GET /mail/sending-identities` (`SendingIdentityService.ListAsync`) →
    `TheSendingIdentities…` rouge (« Expected count: 2, Actual count: 1 »).

### Correction règle 14 après `/review` (2026-10-26, option 1 validée par l'humain)

- **Défaut** (trouvé par `/review`) : `[DelegatedAccess(Read)]` sur les routes de brouillon laissait un
  brouillon « (moi) » entrer dans Redis avec une pièce par référence `shared/<délégante>/<sous-dossier>`
  (`DraftCacheRepository` écrit sans passer par `DelegatedCacheGuardService`), puis éventuellement dans
  `PendingActions` hors ligne.
- **Correction** (`DraftService.DetachDelegatedReferencesAsync`, aux trois écritures : enregistrement,
  mise à jour, envoi avec contenu) : une pièce reprise d'une BAL déléguée est relue
  (`PartsByReference.ResolveAsync`) et entre par ses octets, référence effacée ; une pièce de sa propre BAL
  garde sa référence. Un annule-et-remplace qui vise une BAL déléguée est refusé en 400
  (`DelegatedCancelAndReplace`). **Gardes** : `DraftCacheRepository.SetInternalAsync` et
  `DraftService.SetAsideAsync` refusent tout chemin délégué (`DelegatedPersistenceGuard`).
- **Test d'intégration** `ADraftInHisOwnNameForwardingADelegatedPart_KeepsItsBytes_NeverTheSharedPath_InRedisNorInPendingActions` :
  valeur Redis sans `shared/`, brouillon rouvert avec ses octets et sans référence, envoi hors ligne mis en
  file sans `shared/`, annule-et-remplace délégué en 400. **Vu rouge** sur le code d'avant
  (« Sub-string found: shared/ » dans la valeur Redis) ; refus d'annule-et-remplace prouvé par mutation
  (« Attendu 400, reçu 500 » : la garde Redis intercepte quand même).
- **Tests unitaires** `DraftServiceDelegatedReferenceTests` (3) : octets sans chemin, référence propre
  conservée sans relecture, annule-et-remplace délégué refusé sans écriture.

## Sonar log

Analyse complète `healthplatform-api-mail` (SonarQube **25.6.0** local, `sonar.token` ; conteneurs
redémarrés en début d'étape), sur la branche `feat/task-399-…`, trois passes. Toutes les suites vertes à
chaque passe (domaine 264, application 3 712, infrastructure 701, api 1 352, intégration 1 019 + 16 sautés).

- **Période « nouveau code » du serveur** : `PREVIOUS_VERSION` depuis le **2026-04-17**. Elle couvre des
  mois de tasks mergées : le Quality Gate est `ERROR` avant comme après la task (81 violations, 13 hotspots,
  2 bugs `S2952` dans `MailClientSession`, scripts `loadtest-k6`…). **Aucune n'est sur une ligne de la task.**
  La porte de Phase 1 a donc été jugée sur les **lignes ajoutées par la task** (`origin/develop...HEAD`) :
  findings attribués ligne à ligne, couverture lue ligne à ligne (`api/sources/lines`).
- **1ʳᵉ analyse** : **3 findings sur les lignes de la task** : `S103` ×2 (résumés XML des deux exceptions
  de refus), `CA1859` (`TransmitAsync` déclaré `Task` au lieu de `Task<string>`). De plus, `S138` sur
  `SendMailAsync` (81 lignes sur `develop`, 95 après la task) : le dépassement existait déjà, la task l'a
  aggravé. Corrigés par `41014c4f` (la trace d'audit sort dans `TraceSent`).
- **2ᵉ analyse** : 0 finding sur les lignes de la task, mais **couverture des lignes de la task 93,4 %**
  (< 95 %) : constructeurs des deux exceptions et chemins d'échec de `DelegatedDraftService` non couverts.
  Tests ajoutés par `2d0cf762` : `DelegatedDraftServiceTests` (8 : identifiant vide, brouillon déjà
  parti, serveur indisponible, refus d'authentification non avalé, envoi incertain, erreur SMTP, dossier
  Brouillons absent, fermeture en échec) et 2 tests de constructeurs. Mutation : retirer le filtre
  `when` sur `MailServerAuthRefused` → `SendAsync_AuthRefused_IsNotSwallowed` rouge, source restaurée.
- **3ᵉ analyse** : **0 finding sur les lignes de la task, couverture de ses lignes 98,2 %** (448/456).
- Phase 1 (lignes de la task) : ✓ — 4 issues corrigées, 10 tests ajoutés.
- Phase 2 (legacy) : **non jouée**. La dette restante appartient à d'autres tasks (périmètre, règle 6),
  dont une part hors code applicatif (`tests/loadtest-k6`).

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-10-25, `4e7d3997`) | Final (`2d0cf762`) | Δ |
|---|---|---|---|
| Quality Gate (période serveur) | ERROR | ERROR | = (dette héritée) |
| Findings sur les lignes de la task | — | 0 (3 + 1 corrigés) | — |
| Couverture des lignes de la task | — | 98,2 % | — |
| New coverage (période serveur) | 98,2 % | 97,3 % | −0,9 pt |
| Bugs / Vulnérabilités | 2 / 0 | 2 / 0 | = |
| Code smells | 70 | 79 | +9 (hors lignes de la task, cf. ci-dessous) |
| Security hotspots | 15 | 15 | = |
| Coverage projet | 98,1 % | 97,5 % | −0,6 pt |
| Duplication | 0,3 % | 0,3 % | = |
| Fiabilité / Sécurité / Maintenabilité | D / A / A | D / A / A | = |

- La baseline est la dernière analyse de ce serveur, faite sur une **autre branche** : le +9 smells et
  le recul de couverture mesurent l'écart entre cette branche et celle-ci, pas la task seule.
  L'attribution ligne à ligne fait foi : aucun finding de la task ne reste.
- Conventions (`conventions/csharp.md`) : `S138` → 2, `S103` → 6, `CA1859` → **12**. CA1859 récidive sur
  du code frais : la consigne n'a pas été appliquée à l'écriture (règle d'or 3).

## Lint log

- Mode : chaîné. Contournement task-367 : `npx nx run-many -t lint --projects=mss-lib`, puis
  `npx eslint -f json` sur les 22 fichiers `.ts`/`.html` de la task. Les messages sont attribués à la
  task par `git diff -U0 HEAD`, et les fichiers non suivis comptent en entier.
- Base : `origin/next` (rafraîchie) ; affecté selon Nx : 13 projets (la branche de l'humain est loin de
  `next`) ; scope lint `tag:scope:mss`, `e2e/mss-e2e` contrôlé à part.
- Baseline (fichiers de la task) : **12 erreurs** / 45 warnings. Les 12 erreurs sont de la task :
  10 `prettier/prettier` dans les parcours DELEG-005/006/007 de `functional.e2e.ts`, et 2
  `jsdoc/require-param` sur `chooseSender` (`sender.address`, `sender.delegated`).
- Itération 1 : `prettier --write` sur `functional.e2e.ts` (seules les lignes de la task ont bougé).
  Itération 2 : les deux `@param` ajoutés à la main. Itération 3 : **un warning neuf de la task**,
  `complexity` sur `initializeFromPrefill` (24, non signalé sur HEAD), corrigé par extraction
  (`resumeDraft`, `applyPrefillRecipients`) ; `replacePlaceholders` passe de 44 à 45, dette antérieure laissée.
- Final : **0 erreur** ; `mss-lib` 43 warnings (le niveau d'avant la task), aucun sur une ligne de la task.
- Build / tests : ✓ `mss-lib` 1 358 tests (122 fichiers), build `weda2` ; specs de rédaction 186/186
  après l'extraction.

| Iter | Erreurs avant | Erreurs après | Build | Tests |
|------|---------------|---------------|-------|-------|
| 1 | 12 | 2 | — | — |
| 2 | 2 | 0 | ✓ | ✓ |
| 3 (warning neuf) | 0 | 0 | ✓ | ✓ |

- Conventions (`conventions/angular.md`) : `jsdoc/require-jsdoc` → Occurrences 12 (paramètre objet à valeur
  par défaut) ; nouvelle entrée `complexity`.
- Git : aucune opération (code-only) ; les changements restent non commités sur `feature/nova-mss-weda-integration`.

## Lint mobile log

- Repo : client-mobile (Client/Mobile/, Ionic/Angular CLI), branche `feat/task-399-…` @ `8432089`
- Commandes : `npm run lint` (deux passes, pendant `/sonar` puis à l'entrée de l'étape)
- Baseline : 0 erreur / 0 warning (« All files pass linting ») — **lint clean → no work**
- Itérations : 0 / 5 ; aucun commit
- Build / tests : ✓ verts depuis la passe §Q de `/develop` (1 353 tests), aucun changement depuis

## E2E log

**✅ VERT** (2026-10-26, 4ᵉ passage, après la correction de la règle 14 `7988195b` et le merge de
`develop` `8f607c15`). Passages précédents : outillage (seed, corrigé `5964f2c1`), puis deux tests de la
task (corrigés `aac3ebb` sur mobile et sur weda2), puis vert (3ᵉ passage).

| Voie | Déclencheur | Résultat | Tests |
|---|---|---|---|
| mobile | api-mail, client-mobile touchés | ✅ verte (jouée) | 52 verts, 1 flaky, 0 rouge, 0 quarantaine |
| angular | api-mail, client-angular touchés | ✅ verte (jouée) | 61 verts, 1 flaky, 0 rouge, 1 quarantaine (verte) |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`7988195b`)
- **Flaky récurrent → task de stabilisation à ouvrir** : E2E-DELEG-004 [mobile], 3ᵉ occurrence (fenêtre de
  révocation, requalification côté API déjà proposée en task-398) ; E2E-SEARCH-001 [angular], 13ᵉ.
- Quarantaines : E2E-COMPOSE-002 [angular] (task-350), verte
- Divergences ouvertes : E2E-MAILBOX-002 [angular] (task-395), **à retirer** du catalogue
- Parcours touchés sans spec e2e modifié : aucun
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (2) :

- [mobile] « BAL déléguée — la délégation retirée pendant la consultation ramène à sa propre réception » (E2E-DELEG-004)
- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-DELEG-001 | 1 | headless | Voir la BAL déléguée dans sa section, repliée sous la BAL principale, et lire un compte rendu | ✅ | ✅ |
| E2E-DELEG-002 | 1 | headless | Supprimer un message délégué vers la corbeille de la délégante, puis le restaurer | ✅ | ✅ |
| E2E-DELEG-003 | 2 | headless | Dans une BAL déléguée, gestion et réponse sont proposées, sans IA ni acte clinique | ✅ | ✅ |
| E2E-DELEG-005 | 1 | headless | Envoyer au nom de la délégante, copie dans ses Envoyés et jamais dans les siens | ✅ | ✅ |
| E2E-DELEG-006 | 1 | headless | Brouillon au nom de la délégante, rouvert, puis envoyé | ✅ | ✅ |
| E2E-DELEG-007 | 1 | headless | Avec une délégation, l'envoi est impossible tant que la BAL émettrice n'est pas choisie | ✅ | ✅ |
| E2E-DELEG-004 | 1 | headless | La délégation retirée pendant la consultation ramène à sa propre réception | ✅ | ⚠️ flaky |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-399 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 52 s | — | — | — | — |
| /develop | ok | 13 min 08 s | 26 (14 min 02 s) | 37 (48 min 36 s) | — | dtos-mss 1B/0T, api-mail 20B/29T, client-mobile 5B/6T, client-angular 0B/2T, correction regle 14 apres /review : brouillon (moi) sans chemin shared/ (7988195b) + merge develop DTO 544 (8f607c15) |
| /sonar | ok | 1 h 09 min | 3 (7 min 10 s) | 16 (34 min 20 s) | 6 (15 min 02 s) | 3 itération(s), api-mail 3B/16T, phase 1 sur lignes de la task : 0 finding, couverture 98,2 % |
| /lint-angular | ok | 1 h 24 min | 2 (2 min 13 s) | 2 (7 min 20 s) | — | 3 itération(s), client-angular 2B/2T |
| /lint-mobile | ok | 57 s | — | — | — | lint clean |
| /e2e | ok | 25 min 08 s | 1 (11 s) | — | — | api-mail 1B/0T, e2e ×17 (1 h 32 min), 4e passage vert apres correction regle 14 : mobile 52/1 flaky, angular 61/1 flaky |
| /review | ok | 2 min 01 s | 4 (2 min 28 s) | 3 (9 min 35 s) | — | api-mail 1B/1T, dtos-mss 1B/0T, client-mobile 1B/1T, client-angular 1B/1T, 2e passe APPROVED apres correction regle 14 ; PR Dtos #50, Api.Mail #317, Mobile #108 |
| /tech-writer | ok | 1 min 29 s | — | — | — | — |
| **Total cycle** | | **3 h 16 min** | **36 (26 min 05 s)** | **58 (1 h 39 min)** | **6 (15 min 02 s)** | |

Autres commandes mesurées : lint ×5 (6 min 04 s), nuget-wait ×1 (19 s), restore ×4 (4 min 38 s)

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/50 — `awaiting-human-merge` (NuGet **544.0.0**)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/317 — `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/108 — `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, sur `feature/nova-mss-weda-integration`. Fichiers MSS modifiés (non commités) :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/specs/live-ai.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/models/draft.model.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-draft.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-intent.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-recipients.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-safety.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-spelling.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-suggestions.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-toolbar.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.html`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.delegation.spec.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.delegation.spec.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-event.service.ts`
  - `front/e2e/mss-e2e/support/compose.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-delegation.component.spec.ts`

## Code Review Summary

**Verdict : APPROVED** (2ᵉ passe, 2026-10-26).

- **1ʳᵉ passe — CHANGES REQUESTED (règle 14)** : `[DelegatedAccess(Read)]` sur `POST/PUT /mail/drafts` et
  `…/send` laissait un brouillon « (moi) » entrer dans Redis avec une pièce par référence
  `shared/<délégante>/<sous-dossier>` (écriture directe, hors `DelegatedCacheGuardService`), puis dans
  `PendingActions` hors ligne. Option 1 choisie par l'humain : corrigé par `7988195b` (pièce relue en octets,
  référence effacée, annule-et-remplace délégué en 400, gardes à l'écriture Redis et à la file hors ligne).
- **Merge de `develop`** (tasks 389/390) : conflits mécaniques résolus (`8f607c15`), DTO republié en **544**
  (la 540 de la task ne portait pas la 539 de task-390).
- **Règle 1b — comportement → test → preuve rouge** (`DelegatedSendEndToEndTests`, 15 tests) :
  envoi délégué (en-têtes, Sent unique) → M1/M3 ; `From` étranger, délégation retirée, différé confirmé → M2 ;
  hors ligne → M4 ; brouillon délégué → M5/M8 ; IA → M6 ; audit → M7 ; retrait de session ouverte → mesuré ;
  bascule de BAL → MA ; double envoi → MB ; identités d'envoi → MC (+ M9 en unitaire) ;
  brouillon « (moi) » sans chemin `shared/` → rouge sur le code d'avant, annule-et-remplace → mutation ;
  réponse en « (moi) » → non-régression.
- **Revue** : contrôle du `From` sur les trois points d'entrée ✅, en-têtes encodés par MimeKit ✅, archivage
  unique dans `shared/<A>/Sent` ✅, liste blanche d'audit ✅, refus hors ligne et IA ✅, fuite du libellé de
  verrou corrigée ✅, mobile et weda2 conformes au modèle ✅.
- **Suggestions non bloquantes** : double envoi possible si la suppression du brouillon échoue après SMTP ;
  remplacement de brouillon non sûr entre réplicas ; `Packaging` IHE-XDM perdu à l'aller-retour IMAP d'un
  brouillon délégué (à confirmer au HAG) ; `LIST` + `STATUS` à chaque enregistrement automatique ; entrées
  MIME non validées (500 possible) ; `hasDelegation` asynchrone côté clients.
- **Qualité** : `/sonar` non rejoué après le merge et la correction (2 fichiers, couverts par 4 tests).
