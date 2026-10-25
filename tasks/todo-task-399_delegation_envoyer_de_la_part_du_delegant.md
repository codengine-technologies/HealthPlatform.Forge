# todo-task-399.md — Délégation de BAL : envoyer de la part du délégant

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
