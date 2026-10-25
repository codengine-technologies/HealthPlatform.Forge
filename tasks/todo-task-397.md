# todo-task-397.md — Délégation de BAL : confiner la BAL déléguée (lisible, gérable, rien du CDA stocké chez le délégataire)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Priorité**: **1** — le serveur Mailiz expose déjà les BAL déléguées. Le 2026-10-25, en formation,
un délégataire a fait sortir 2 messages de la BAL de sa délégante. Sa base contenait en outre :
- 64 documents médicaux de la délégante, avec l'identité de leurs patients ;
- **323 résultats de biologie** ;
- 7 patients ;
- 106 étiquettes IA.

> **Analyse complète** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md)
> (règles Mailiz, comportement du serveur, dégâts constatés, découpage task-397 à task-400).
>
> **Périmètre backend seul (justification).** Les clients ne changent pas dans cette task.
> - Les refus de l'API arrivent en ProblemDetails, comme toute erreur.
> - Hors ligne, un message délégué arrive sans documents décodés ; sa pièce jointe reste listée.
> - Relèvent de la task-398 :
>   - la mention « document consultable en ligne » ;
>   - l'affichage dédié des BAL déléguées et le masquage des actions interdites ;
>   - l'ajout de la délégation au banc e2e et les scénarios `E2E-DELEG-…`, requis sur mobile et
>     weda2.

## Décisions actées (humain, 2026-10-25)

1. **Confiner plutôt que masquer.** Les dossiers `shared/<adresse du délégant>/…` restent visibles
   et gérables par le délégataire.
2. **Gestion seule, définitivement.** Un message d'une BAL déléguée n'est **jamais exploité** dans
   l'espace du délégataire : ni patient, ni dossier patient, ni doublons et versions, ni IA, ni
   embeddings, ni recherche, ni contacts, ni notification.
3. **Les documents CDA sont décodés et lisibles.** Le délégataire voit le compte rendu décodé, pas
   une pièce jointe `IHE_XDM.ZIP` brute.
4. **Rien de ce qui est extrait d'un CDA délégué n'est stocké chez le délégataire**, ni en base ni
   dans Redis :
   - documents, rendus (`Body`, `HtmlBody`) et métadonnées ;
   - **biologie** et résumés cliniques ;
   - identité du patient ;
   - texte des documents ajouté au corps du message.

   Le décodage se fait **à l'affichage, en mémoire**. La biologie est présente dans le rendu du
   document : exclure la seule table de biologie ne la protégerait pas.
5. **Hors ligne, les documents d'un message délégué ne sont pas consultables.** C'est la
   conséquence acceptée du point 4.
6. **Lecture seule sur ces documents.** Ni rattachement à un patient, ni acquittement de biologie :
   ces actes restent au délégant.

## Objective

Un délégataire ouvre la BAL qu'on lui délègue, y lit les messages et leurs documents décodés, les
trie, les déplace et les supprime. Trois garanties l'accompagnent :
- **La BAL du délégant n'est jamais abîmée** : un message supprimé reste dans sa corbeille, et ses
  dossiers système ne bougent pas.
- **Aucune donnée extraite des CDA du délégant n'est conservée** dans la base ou le cache du
  délégataire, et en particulier aucune biologie.
- **Rien de la BAL du délégant n'entre dans l'espace clinique du délégataire** : ni patients, ni
  IA, ni recherche, ni contacts, ni notifications.

Ce qui a déjà été produit à tort dans les bases des délégataires est purgé.

## Règles

- **Message délégué** : tout message dont le dossier est sous `shared/` (espace de noms partagé
  Mailiz). Le **propriétaire** est la racine `shared/<adresse>`.
- **Corbeille du propriétaire** : `shared/<adresse>/Trash`. Mailiz n'y pose aucun attribut
  SPECIAL-USE : on la reconnaît par sa position.
  - Supprimer un message délégué hors de cette corbeille l'y **déplace**.
  - Le supprimer depuis cette corbeille le **supprime définitivement**.
  - Jamais vers la corbeille personnelle du délégataire.
- **Dossiers système du délégant** : `shared/<adresse>` (sa réception) et ses `Sent`, `Drafts`,
  `Trash`, `Junk`. Ils ne peuvent être ni renommés, ni supprimés, ni déplacés. Ses sous-dossiers
  personnels restent gérables, comme le permet Mailiz.
- **Ce qui est conservé d'un message délégué** (base tenant et cache du délégataire) : l'en-tête,
  les drapeaux, la liste des pièces jointes et le corps **tel que reçu**. Le texte des documents
  n'est pas ajouté au corps. `HasMedicalDocuments` et `HasBiologyResults` peuvent rester, car ce
  sont des indicateurs et non des données.
- **Documents d'un message délégué** :
  - décodés à chaque affichage en ligne du détail, depuis la pièce jointe lue sur le serveur IMAP ;
  - renvoyés dans la réponse avec leur rendu, leur LOINC, leur biologie et la mise en évidence des
    valeurs anormales ;
  - **jamais écrits** : aucune ligne dans `MailMedicalDocuments`, `MailMedicalDocumentBiology`,
    `MailMedicalDocumentSummary`, `MailPatients` ni `BiologyAcks`, et aucune entrée Redis portant
    ces données ;
  - par voie de conséquence, absents du dossier patient, des doublons et versions, de l'indicateur
    « à intégrer », de l'IA, des embeddings et de la recherche, des contacts, des notifications et
    des tableaux de bord biologie.
- **Hors ligne** : le détail d'un message délégué n'a pas de documents décodés ; la pièce jointe
  reste listée.
- **Actes cliniques refusés** : rattachement à un patient et acquittement de biologie sur un
  document délégué.
- **Audit** : la trace de décodage d'un document délégué ne porte **ni INS ni nom de patient**.
- **La propre BAL du délégataire n'est pas affectée** : son traitement reste complet et
  persistant, comme aujourd'hui.

## Definition of Done

- [ ] **Banc de délégation.** Le Dovecot des tests d'intégration reproduit Mailiz :
      - espace `shared` ;
      - ACL : B délégataire de A, avec droits de lecture, écriture, suppression et création ;
      - état lu propre à chaque utilisateur.

      Sa configuration est documentée à côté de celle du banc existant.
- [ ] Test d'intégration de bout en bout pour `DELETE` d'un message de `shared/<A>` : le message
      est dans `shared/<A>/Trash` côté IMAP, absent de la corbeille de B. Lu dans l'état réel, vu
      rouge (règle 1b).
- [ ] Test d'intégration : suppression depuis `shared/<A>/Trash` → message supprimé définitivement,
      présent dans aucune corbeille. Idem pour la suppression groupée.
- [ ] Test d'intégration : suppression d'un sous-dossier de `shared/<A>` → ses messages vont dans
      `shared/<A>/Trash`.
- [ ] Test d'intégration : renommer, supprimer ou déplacer `shared/<A>`, `shared/<A>/Sent`,
      `/Drafts`, `/Trash` ou `/Junk` → **409** `application/problem+json`, dossier intact côté IMAP.
      Le même geste sur un sous-dossier personnel de A est accepté.
- [ ] **Test d'intégration — lecture.** Le détail d'un message de `shared/<A>` porteur d'un
      `IHE_XDM.ZIP` de biologie renvoie ses documents décodés : titre, LOINC, résultats de
      biologie et valeur anormale signalée. Lu dans la réponse réelle.
- [ ] **Test d'intégration — rien de stocké.** Après la liste, l'enrichissement et l'ouverture du
      détail de ce message, la base tenant de B contient **zéro** ligne pour ce message dans :
      - `MailMedicalDocuments`, `MailMedicalDocumentBiology`, `MailMedicalDocumentSummary` ;
      - `MailPatients`, `BiologyAcks`, `MailTags`.

      Aucun `AiTaggingPendingSince` ni embedding n'est posé. Le corps stocké dans `MailContents`
      ne contient pas le texte du document. Aucune clé Redis ne contient le rendu ni la biologie
      (vérifié par lecture des clés de B). Vu rouge sur le code actuel.
- [ ] Test d'intégration : aucune notification « Nouveau message » et aucun contact publié pour un
      message arrivé dans `shared/<A>`.
- [ ] Test d'intégration : en mode hors ligne, le détail du message délégué est renvoyé sans
      documents et avec sa pièce jointe listée, sans erreur.
- [ ] Test d'intégration : `attach-patient` et `biology-ack` avec un identifiant de document
      délégué → refus en ProblemDetails, rien d'écrit.
- [ ] Test d'intégration : la trace d'audit de décodage d'un document délégué ne contient ni INS ni
      nom de patient.
- [ ] Non-régression : les mêmes scénarios sur la propre réception de B gardent le traitement
      complet et persistant : document, biologie, patient, IA, notification, doublons.
- [ ] **Test de convention** : chaque chemin qui écrit dans les tables issues du CDA, ou qui
      publie vers l'IA, les embeddings ou les contacts, écarte les messages délégués. Un ajout
      futur qui l'oublie fait échouer le test, prouvé rouge par mutation.
- [ ] **Purge de l'existant**, rejouable et idempotente, sur toutes les bases tenant. Pour les
      messages sous `shared/`, elle supprime :
      - documents, biologie, résumés et acquittements ;
      - les patients qui n'ont plus aucun document ;
      - étiquettes et files IA, embeddings, et contacts créés uniquement depuis ces documents ;
      - le texte des documents dans les corps (`MailContents`), en le remplaçant par le corps reçu,
        ou en supprimant le contenu pour qu'il soit relu).

      Elle purge aussi les entrées Redis correspondantes et journalise des comptes, sans donnée de
      santé. Si l'origine d'un contact n'est pas traçable, arrêt et `questions/task-397.md`.
- [ ] Aucune donnée de santé (INS, nom de patient, contenu CDA, valeur de biologie) dans les logs
      ajoutés.
- [ ] Build et tests verts ; `/e2e` vert, avec les parcours existants rejoués.

## Manual Test Plan

Comptes de formation : Cyril (`cyril.toubib0072344@medecin.formation.mssante.fr`) est délégataire
de Virginie (`virginie.medecinrpps0062267@medecin.formation.mssante.fr`).

0. **Avant le test**, remettre à leur place les 2 messages déplacés à tort le 2026-10-25. Depuis le
   webmail Mailiz de Cyril : Corbeille, puis les deux messages du 2026-06-10, à déplacer vers la
   boîte déléguée de Virginie.
1. Lancer l'AppHost (`dotnet run --project Api/Mail/src/AppHost`), puis le mobile
   (`cd Client/Mobile && npm start`) ou weda2. Se connecter en Cyril par PSC.
2. **Purge.** Après passage de la purge sur la base de Cyril, dans sa base :
   - `MailMedicalDocuments`, `MailMedicalDocumentBiology` et `MailPatients` n'ont **plus aucune**
     ligne issue de `shared/…` ;
   - les 7 patients de Virginie ont disparu ;
   - les 323 résultats de biologie ont disparu.
3. **Lecture.** Ouvrir la boîte déléguée de Virginie, puis un compte rendu de biologie : le
   document est **décodé et lisible**, et les valeurs anormales sont signalées. Aucune invitation
   « à intégrer », aucun acquittement possible.
4. **Rien de stocké.** Relancer la requête de l'étape 2 : toujours **zéro** ligne issue de
   `shared/…`, alors que le document vient d'être affiché.
5. **Hors ligne.** Couper le réseau du poste, puis rouvrir ce message : il s'affiche avec sa pièce
   jointe, sans document décodé et sans erreur.
6. **Suppression.** Supprimer un message de la boîte déléguée.
   - Il apparaît dans la **Corbeille de Virginie** (sous sa boîte déléguée), pas dans celle de
     Cyril.
   - Vérifier dans le webmail Mailiz de Virginie : il est dans sa corbeille.
7. **Protection.** Tenter de renommer ou supprimer les Envoyés de Virginie : refus avec un message
   clair. Créer, puis renommer un sous-dossier dans sa boîte : accepté.
8. **Cloisonnement.**
   - Une recherche ne remonte aucun message de la boîte déléguée.
   - Aucune notification « Nouveau message » n'arrive quand Virginie reçoit un message.
9. **Non-régression.** Un compte rendu reçu dans la propre BAL de Cyril est traité comme avant :
   document stocké, patient, biologie, étiquettes, notification.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. La délégation de BAL est une fonctionnalité Mailiz (ANS, novembre
  2025), sans exigence DSR publiée pour les logiciels métier à ce jour.
- **Exigences DSR honorées** : non applicable — aucune exigence publiée. Le mode opératoire Mailiz
  est suivi : mêmes droits sur les messages, carnet d'adresses non partagé, gestion des
  délégations réservée au délégant.
- **INS** : non applicable en écriture. Aucun patient n'est créé, rattaché ni stocké depuis une BAL
  déléguée. L'INS est affiché en lecture dans le document décodé, sans être conservé ni journalisé.
- **Authentification PS** : inchangée. PSC / e-CPS pour le délégataire, condition Mailiz de la
  délégation.
- **Habilitations** : les droits sont tenus par le serveur Mailiz (ACL de délégation). L'API
  ajoute deux refus :
  - modification des dossiers système du délégant ;
  - actes cliniques (rattachement patient, acquittement) qui engagent le délégant.
- **Interop CI-SIS** : CDA r2 décodé à l'identique pour la lecture (volets existants via
  `interop-cda`), en mémoire. Aucun nouvel échange.
- **Tracé PGSSI-S** : l'audit existant continue de tracer lectures, décodages, suppressions et
  déplacements sur `shared/…`, **sans INS ni nom de patient** pour les documents délégués. Les
  refus sont tracés. Distinguer la personne qui agit de la propriétaire de la BAL relève de la
  task-400.
- **Consentement patient** : non applicable — aucun partage nouveau. La délégation est une décision
  du délégant, sous sa responsabilité (secret professionnel).
- **Référentiels métier** : LOINC des documents et codes de biologie, affichés en lecture, jamais
  stockés
- **Hébergement HDS** : inchangé. Après la purge, **plus aucune** donnée extraite des CDA d'un
  délégant n'est dupliquée dans la base d'un délégataire.
- **AIPD / impact RGPD** : **à mettre à jour**. Les BAL déléguées sont un nouveau flux d'accès aux
  données de santé d'un tiers. Il faut documenter :
  - consultation en lecture seule, décodage en mémoire ;
  - aucune copie de données issues des CDA chez le délégataire ;
  - purge à la révocation, déjà couverte par la purge des dossiers disparus.

## Notes de cadrage

- **Où se fait le stockage aujourd'hui.**
  - Le décodage `EmailBuildingService.BuildMailDtoAsync` → `ProcessIheXdmZips` est un calcul sans
    état. Il ajoute cependant le texte de chaque document au corps du message
    (`EmailBuildingService.cs:101`).
  - Le stockage se fait ensuite : `MailRepository` (documents, biologie, résumés) et
    `ResolveMedicalDocumentPatient` (`MailRepository.cs:454-487`).
  - Puis les consommateurs : `AddNewMailConsumer.cs:66-75, 206-355` (IA, embeddings, contacts) et
    `EnrichedMailPersistence.cs:93-99, 181-251` (publication, notification).
  - Pour un message délégué, on garde le décodage et on coupe tout le reste. Le chemin de lecture
    du détail doit savoir décoder depuis l'IMAP quand rien n'est stocké.
- **Marquer la provenance** : une colonne calculée sur `Mails.FolderPath`, comme
  `IsInSentDraftOrTrashFolder`, posée à l'écriture, sert à la fois au tri du pipeline, à la purge et
  au test de convention.
- **Coût** : décoder à chaque ouverture coûte quelques dizaines à quelques centaines de
  millisecondes par document. C'est acceptable pour un usage de délégation ; à mesurer pendant le
  développement.
- **Corbeille** : aujourd'hui `SpecialFolder.Trash` seul (`ImapService.cs:3814-3818`, `:3916`,
  `:4055`, `:4157` ; `ImapFolderService.cs:436`), c'est-à-dire celle de la session.
- **Hors périmètre, tasks suivantes** :
  - affichage dédié, libellés, mention « consultable en ligne », compteurs, sélecteurs et
    scénarios e2e : task-398 ;
  - envoi « de la part de », brouillons délégués, accusés de lecture : task-399 ;
  - traçabilité acteur / propriétaire : task-400.
