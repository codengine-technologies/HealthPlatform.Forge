# todo-task-399.md — Délégation de BAL : envoyer de la part du délégant

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-398 (BAL déléguées visibles, propriétaire et rôle des dossiers dans le contrat)
**Epic**: E009
**Priorité**: **3** — sans elle, un délégataire lit et trie la BAL du médecin mais ne peut pas
répondre pour lui. Répondre et Transférer sont masqués sur les messages délégués depuis la
task-398.

> **Analyse** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md)
> (§1 règles Mailiz, §4 inconnues).
> **Règle 14** (CLAUDE.md) : rien d'une BAL déléguée n'est persisté chez le délégataire. Elle
> s'applique ici aux brouillons, aux copies envoyées, aux envois différés et aux contacts.

## Ce que dit Mailiz (mode opératoire, novembre 2025)

- Le délégataire peut envoyer « de la part de » le délégant. Le champ **De** porte **l'adresse du
  délégant**, avec le libellé « *Nom du délégataire*, de la part de *adresse du délégant* ».
- Le message va dans les **Envoyés du délégant**, visibles par lui et par les autres délégataires.
- Avec plusieurs délégations, le délégataire **choisit la BAL émettrice**, « pour éviter les pertes
  de données de santé ou les erreurs de traitement ».
- **L'accès délégué depuis un logiciel métier n'est « pas encore » ouvert** selon le document,
  alors que le serveur IMAP l'expose déjà. Le comportement SMTP n'est pas documenté.

## Décisions actées (humain, 2026-10-25)

1. **Caractériser d'abord, avec un point d'arrêt.** La task commence par mesurer le comportement
   SMTP de Mailiz sur les comptes de formation. Si l'envoi délégué depuis un logiciel métier est
   refusé, la task s'arrête sur `questions/task-399.md` : l'envoi délégué attend Mailiz.
2. **Choix obligatoire de la BAL émettrice.** Dès que l'utilisateur a au moins une délégation, le
   champ **De** de toute rédaction est vide, y compris pour une réponse ou un transfert.
   - Il faut choisir entre sa propre adresse et celles de ses délégants avant d'envoyer.
   - Sans délégation, rien ne change : l'envoi part de sa propre adresse, sans champ à choisir.
3. **Brouillons dans les Brouillons IMAP du délégant** (`shared/<adresse>/Drafts`), comme dans
   Mailiz : visibles du délégant et de ses autres délégataires. Jamais dans Redis ni dans la base
   du délégataire (règle 14).
4. **Signature : celle du délégataire.** C'est lui qui écrit, et le libellé « de la part de » dit
   pour qui. Aucune signature au nom du délégant.
5. **Jamais d'accusé de lecture en délégation.** Un accusé atteste que le médecin destinataire a lu
   ; une lecture par son délégataire ne doit pas l'attester. Aucune proposition sur un message
   délégué ; la demande reste visible pour le délégant.

## Objective

Un délégataire rédige un message, une réponse ou un transfert, choisit explicitement la BAL au nom
de laquelle il écrit, et l'envoie. Le destinataire voit un message du délégant, « de la part de »
son délégataire. La copie est dans les Envoyés du délégant, et rien n'en reste chez le
délégataire.

## Règles

- **Identités d'envoi** : sa propre adresse et l'adresse de chaque BAL déléguée découverte en
  direct (task-397).
  - L'API publie cette liste.
  - Elle **refuse** un envoi dont le `From` n'y figure pas : **403** ProblemDetails. Aujourd'hui le
    `From` est pris tel quel du client.
- **Champ De** (décision 2) :
  - vide tant qu'aucune BAL n'est choisie, et l'envoi est impossible ;
  - les choix affichés sont « `<adresse>` (moi) » et « `<adresse>` (délégation) » ;
  - le choix reste visible dans l'en-tête de la rédaction jusqu'à l'envoi.
- **En-têtes** : `From`, `Sender` et libellé « *Nom du délégataire*, de la part de *adresse* »
  suivent **le contrat constaté à la caractérisation**. À défaut de règle serveur, ils suivent le
  mode opératoire : `From` = délégant, libellé « de la part de », `Sender` = délégataire.
- **Copie envoyée** : dans `shared/<adresse>/Sent` seulement, jamais dans les Envoyés du
  délégataire.
  - Si Mailiz la classe lui-même, l'API n'ajoute rien.
  - Sinon, l'API la dépose là, et une seule fois.
- **Brouillons délégués** (décision 3) :
  - enregistrés dans `shared/<adresse>/Drafts` par commandes IMAP directes ; chaque
    enregistrement remplace le précédent ;
  - rouverts depuis ce dossier, éditables, envoyables ; supprimés du dossier à l'envoi ;
  - la règle de task-394 tient : un corps non modifié ne crée aucun brouillon.
- **Changer de BAL en cours de rédaction** : un brouillon déjà enregistré dans les Brouillons d'une
  BAL n'est ni dupliqué ni laissé orphelin. Il est retiré de l'ancienne BAL et enregistré dans la
  nouvelle au prochain enregistrement.
- **Hors ligne** : pas d'envoi ni de brouillon pour une identité déléguée. Un message clair le dit.
  Aucune mise en attente (`PendingActions`) d'un envoi délégué.
- **Répondre, Répondre à tous, Transférer** sont à nouveau proposés sur un message délégué, avec le
  champ De vide (décision 2).
- **Répondre à tous** retire des destinataires l'adresse choisie comme émettrice et la propre
  adresse du délégataire.
- **Signature** (décision 4) : les signatures du délégataire, y compris sa signature par défaut.
- **Accusés de lecture** (décision 5) : jamais proposés sur un message délégué.
  - Un message envoyé de la part du délégant peut en demander un.
  - L'accusé reviendra dans la BAL du délégant, puisque l'en-tête de demande vaut le `From`.
- **Carnet d'adresses** : les suggestions de destinataires viennent du carnet du délégataire, car le
  carnet du délégant n'est pas partagé. **Aucun contact** n'est créé à partir d'un envoi délégué.
- **Pièces médicales jointes** (`IHE_XDM.ZIP`) : l'auteur reste le délégataire. La règle actuelle
  « RPPS de l'auteur = RPPS de la session » est inchangée.
- **Opposition MSSanté patient** et règles d'envoi aux patients : inchangées, appliquées aux
  destinataires quel que soit l'émetteur.
- **Audit** (exception de la règle 14) : l'envoi délégué est tracé avec l'action, l'auteur, la BAL
  émettrice et le `Message-ID`, sans objet, sans destinataires, sans contenu.

## Definition of Done

- [ ] **Caractérisation SMTP Mailiz** consignée dans le `## Develop log` et dans l'analyse (§4).
      Elle est faite sur les comptes de formation (Cyril délégataire de Virginie), par un envoi
      vers une boîte de test lisible :
      - acceptation de `From` = délégant en session XOAUTH2 du délégataire ;
      - en-têtes reçus (`From`, `Sender`, libellé) ;
      - classement automatique ou non dans les Envoyés du délégant ;
      - refus éventuels.

      **Refus → arrêt** et `questions/task-399.md` (décision 1).
- [ ] **Banc** : le banc d'intégration et le banc e2e reproduisent le comportement constaté (règle
      d'acceptation du `From`, classement des Envoyés).
- [ ] `dtos-mss` : identités d'envoi publiées et BAL émettrice dans la requête d'envoi et de
      brouillon. Paquet publié, consommateurs .NET mis à jour, types TypeScript alignés.
- [ ] Test d'intégration de bout en bout pour l'envoi depuis l'identité du délégant :
      - message reçu avec les en-têtes attendus ;
      - copie dans `shared/<A>/Sent`, présente **une seule fois** ;
      - **absente** des Envoyés de B.

      Lu dans l'état réel, vu rouge (règle 1b).
- [ ] Test d'intégration : envoi avec un `From` hors des identités de B → **403**, rien n'est
      envoyé. Vu rouge.
- [ ] Test d'intégration — brouillons délégués :
      - enregistrer, puis réenregistrer : un seul brouillon dans `shared/<A>/Drafts` ;
      - rouvrir, puis envoyer : le brouillon a disparu du dossier ;
      - corps non modifié : aucun brouillon ;
      - changer de BAL en cours de rédaction : aucun brouillon orphelin.
- [ ] Test d'intégration « rien de persisté » (règle 14) après envoi et brouillons délégués :
      - zéro ligne liée en base de B ;
      - aucune clé Redis de brouillon ou de contenu ;
      - aucune `PendingActions` ;
      - aucun contact créé.
- [ ] Test d'intégration : en mode hors ligne, envoi et brouillon délégués refusés proprement, rien
      mis en attente.
- [ ] Test d'intégration : la trace d'audit de l'envoi délégué ne porte ni objet, ni destinataires,
      ni contenu.
- [ ] Non-régression : un utilisateur **sans** délégation envoie comme aujourd'hui, sans champ De,
      avec brouillons Redis et copie dans ses Envoyés.
- [ ] Tests de composants, sur mobile et weda2 :
      - champ De vide, envoi impossible sans choix, libellés « (moi) » et « (délégation) » ;
      - Répondre et Transférer rétablis sur un message délégué ;
      - Répondre à tous sans l'adresse émettrice ;
      - signature du délégataire ;
      - aucune proposition d'accusé de lecture sur un message délégué ;
      - message hors ligne.
- [ ] Scénarios ajoutés dans `Api/Mail/e2e/scenarios.yml` et implémentés sur mobile et angular :
      - **E2E-DELEG-005** : envoyer de la part du délégant → le message est dans les Envoyés de la
        BAL déléguée, pas dans les siens ;
      - **E2E-DELEG-006** : brouillon délégué enregistré dans les Brouillons de la BAL déléguée,
        rouvert, envoyé ;
      - **E2E-DELEG-007** : avec une délégation, l'envoi est impossible tant que la BAL émettrice
        n'est pas choisie.

      **E2E-DELEG-003** passe à la version 2 : Répondre et Transférer sont désormais proposés sur
      un message délégué.
- [ ] Build et tests verts sur les quatre dépôts ; `/e2e` vert, avec parité verte.

## Manual Test Plan

Comptes de formation : Cyril, délégataire de Virginie. Lancer l'AppHost, puis le mobile
(`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.

1. **Nouveau message.** Le champ De est vide et l'envoi est impossible. Les choix proposés sont
   « cyril.toubib0072344@… (moi) » et « virginie.medecinrpps0062267@… (délégation) ».
2. Choisir Virginie et écrire à une boîte de test. À réception, le message vient de Virginie,
   « de la part de » Cyril. Il est dans les Envoyés de la boîte de Virginie, pas dans ceux de
   Cyril.
3. **Brouillon.** Commencer un message au nom de Virginie, écrire une phrase, fermer.
   - Le brouillon est dans les Brouillons de la boîte de Virginie.
   - Le webmail Mailiz de Virginie le montre.
   - Le rouvrir, l'envoyer : il disparaît des Brouillons.
4. **Réponse.** Répondre à un message de la boîte déléguée : le champ De est vide. Choisir Virginie.
   Avec « Répondre à tous », l'adresse de Virginie n'est pas parmi les destinataires.
5. **Accusé de lecture.** Ouvrir un message délégué qui en demande un : aucune proposition d'envoi.
6. **Hors ligne.** Couper le réseau, puis tenter d'envoyer au nom de Virginie : message clair, rien
   n'est mis en attente.
7. **Sans délégation.** Se connecter avec un compte sans délégation : la rédaction est inchangée,
   sans champ De.
8. **Rien chez Cyril.** Après les étapes 2 à 4, sa base ne contient aucune trace des messages
   envoyés ni des brouillons au nom de Virginie, et aucun contact nouveau.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — fonctionnalité Mailiz sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable. Le mode opératoire Mailiz est suivi : `From` du
  délégant, libellé « de la part de », Envoyés du délégant, choix explicite de la BAL émettrice.
- **INS** : inchangé — pièces médicales jointes produites comme aujourd'hui, auteur = délégataire
- **Authentification PS** : PSC / e-CPS du délégataire. L'envoi MSSanté reste un acte sensible
  authentifié fortement (garde-fou PO).
- **Habilitations** : l'envoi au nom d'un délégant n'est permis que pour une BAL déléguée découverte
  en direct. L'API refuse tout autre `From`, ce qu'elle ne fait pas aujourd'hui.
- **Interop CI-SIS** : inchangé — enveloppe IHE-XDM existante ; en-têtes MSSanté selon la
  caractérisation
- **Tracé PGSSI-S** : envoi délégué tracé avec auteur et BAL émettrice, sans objet ni destinataires
  (règle 14). L'imputabilité complète relève de la task-400.
- **Consentement patient** : non applicable. L'opposition MSSanté patient est respectée comme pour
  tout envoi.
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — rien d'un envoi délégué n'est stocké chez le délégataire
- **AIPD / impact RGPD** : à compléter avec l'envoi au nom d'un tiers. La mise à jour de l'AIPD
  ouverte par task-397 couvre la délégation.

## Notes de cadrage

- **Constats** (analyse, §3.2) :
  - `From` pris tel quel du client (`SmtpService.cs:299-302`, `MailSendRules.cs:33-36`) ;
  - libellé toujours celui du délégataire (`SmtpService.cs:272-297`) ;
  - aucun `Sender` ;
  - copie envoyée toujours dans les Envoyés de la session (`ImapService.cs:2634-2684`, `:4347`,
    `:4416-4469`) ;
  - brouillons Redis forcés sur l'adresse de session (`DraftService.cs:58-76`, `:390-397`) ;
  - `ImapService.AppendToDraftsAsync` (`:4497-4545`) et `ReplaceDraftAsync` (`:4552`) existent
    sans appelant, et peuvent servir de base aux brouillons IMAP délégués ;
  - accusés de lecture émis depuis l'adresse de session (`MdnService.cs:231-235`).
- **Choix obligatoire** : il s'applique à **toute** rédaction d'un utilisateur qui a une délégation,
  y compris un message pour lui-même. C'est le choix du webmail Mailiz, retenu pour éviter
  d'écrire au nom de la mauvaise BAL.
- **Hors périmètre** : traçabilité acteur / propriétaire consultable par le délégant (task-400) ;
  gestion des délégations (webmail Mailiz seul).
