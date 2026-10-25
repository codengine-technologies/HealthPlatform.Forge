# todo-task-397.md — Délégation de BAL : confiner la BAL déléguée (lisible, gérable, jamais exploitée chez le délégataire)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Priorité**: **1** — le serveur Mailiz expose déjà les BAL déléguées. Le 2026-10-25, en formation,
un délégataire a fait sortir 2 messages de la BAL de sa délégante. Sa base contenait aussi les
documents, les patients et les étiquettes IA de celle-ci.

> **Analyse complète** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md)
> (règles Mailiz, comportement du serveur, dégâts constatés, découpage task-397 à task-400).
>
> **Périmètre backend seul (justification).** Les clients ne changent pas dans cette task.
> - Les refus de l'API arrivent en ProblemDetails, comme toute erreur.
> - L'indicateur « à intégrer » vient du serveur.
> - L'affichage dédié des BAL déléguées, les libellés et le masquage des actions interdites relèvent
>   de la task-398. Celle-ci ajoute aussi la délégation au banc e2e et les scénarios
>   `E2E-DELEG-…`, requis sur mobile et weda2.

## Décisions actées (humain, 2026-10-25)

1. **Confiner plutôt que masquer.** Les dossiers `shared/<adresse du délégant>/…` restent visibles
   et gérables par le délégataire.
2. **Gestion seule, définitivement.** Un message d'une BAL déléguée n'est **jamais exploité** dans
   l'espace du délégataire : ni patient, ni dossier patient, ni doublons et versions, ni IA, ni
   embeddings, ni recherche, ni contacts, ni notification.
3. **Mais les documents CDA sont décodés et lisibles.** Le délégataire voit le compte rendu
   décodé, pas une pièce jointe `IHE_XDM.ZIP` brute. La lecture fait partie des droits que Mailiz
   lui donne.
4. **Lecture seule sur ces documents.** Le délégataire ne peut ni les rattacher à un patient, ni
   acquitter un résultat de biologie : ces actes restent au délégant.

## Objective

Un délégataire ouvre la BAL qu'on lui délègue, y lit les messages et leurs documents décodés, les
trie, les déplace et les supprime. Deux garanties l'accompagnent :
- **La BAL du délégant n'est jamais abîmée** : un message supprimé reste dans sa corbeille, et ses
  dossiers système ne bougent pas.
- **Rien de la BAL du délégant n'entre dans l'espace clinique du délégataire** : ni patients, ni
  dossiers patients, ni IA, ni recherche, ni contacts, ni notifications.

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
- **Documents d'un message délégué** :
  - décodés et conservés **avec leur message**, et affichés dans son détail : rendu, LOINC,
    résultats de biologie et leur mise en évidence ;
  - **aucun patient** créé ni rattaché ;
  - exclus du dossier patient, des doublons, versions et demandes de suppression, de l'indicateur
    « à intégrer » (`PendingIntegrationsCount`), de l'étiquetage IA, des embeddings et de la
    recherche, des contacts, des notifications « Nouveau message », des tableaux de bord biologie ;
  - rattachement à un patient et acquittement de biologie **refusés** par l'API.
- **La propre BAL du délégataire n'est pas affectée** : son traitement reste complet.

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
- [ ] Test d'intégration : un message de `shared/<A>` porteur d'un `IHE_XDM.ZIP` est enrichi.
      Le détail du message rend ses documents décodés (titre, LOINC, biologie). En base, **aucun**
      `MailPatients`, `MailTags`, `AiTaggingPendingSince`, embedding ni contact n'est créé, et
      aucune notification n'est émise. Vu rouge.
- [ ] Test d'intégration : `PendingIntegrationsCount` vaut 0 sur un message délégué porteur de
      documents.
- [ ] Test d'intégration : dossier patient, doublons et versions, recherche sémantique et
      tableaux de bord biologie ignorent les documents délégués. Un même CDA présent dans la
      réception de B et dans `shared/<A>` ne marque pas la copie de B comme doublon.
- [ ] Test d'intégration : `attach-patient` et `biology-ack` sur un document délégué →
      **409** ProblemDetails, rien d'écrit.
- [ ] Non-régression : les mêmes scénarios sur la propre réception de B gardent le traitement
      complet (patient, IA, notification, doublons).
- [ ] **Test de convention** : toute requête qui alimente le dossier patient, la détection de
      doublons, l'IA, la recherche ou les contacts exclut les messages délégués. Un ajout futur
      qui l'oublie fait échouer le test, prouvé rouge par mutation.
- [ ] **Purge de l'existant**, rejouable et idempotente, sur toutes les bases tenant. Pour les
      messages sous `shared/` :
      - elle supprime étiquettes IA, files IA, embeddings, et contacts créés uniquement depuis eux ;
      - elle détache leurs documents de tout patient ;
      - elle supprime les patients qui n'ont plus aucun document.

      Elle journalise des comptes, sans donnée de santé. Si l'origine d'un contact n'est pas
      traçable, arrêt et `questions/task-397.md`.
- [ ] Aucune donnée de santé (INS, nom de patient, contenu CDA) dans les logs ajoutés.
- [ ] Build et tests verts ; `/e2e` vert, avec les parcours existants rejoués.

## Manual Test Plan

Comptes de formation : Cyril (`cyril.toubib0072344@medecin.formation.mssante.fr`) est délégataire
de Virginie (`virginie.medecinrpps0062267@medecin.formation.mssante.fr`).

0. **Avant le test**, remettre à leur place les 2 messages déplacés à tort le 2026-10-25. Depuis le
   webmail Mailiz de Cyril : Corbeille, puis les deux messages du 2026-06-10, à déplacer vers la
   boîte déléguée de Virginie.
1. Lancer l'AppHost (`dotnet run --project Api/Mail/src/AppHost`), puis le mobile
   (`cd Client/Mobile && npm start`) ou weda2. Se connecter en Cyril par PSC.
2. **Lecture.** Ouvrir la boîte déléguée de Virginie, puis un message porteur d'un compte rendu
   CDA : le document est **décodé et lisible**. Aucune invitation « à intégrer », aucun bouton
   d'acquittement actif. Un clic sur l'action échoue proprement.
3. **Suppression.** Supprimer un message de la boîte déléguée.
   - Il apparaît dans la **Corbeille de Virginie** (sous sa boîte déléguée), pas dans celle de
     Cyril.
   - Vérifier dans le webmail Mailiz de Virginie : il est dans sa corbeille.
4. **Protection.** Tenter de renommer ou supprimer les Envoyés de Virginie : refus avec un message
   clair. Créer, puis renommer un sous-dossier dans sa boîte : accepté.
5. **Cloisonnement.**
   - La liste de patients de Cyril ne contient aucun patient de Virginie.
   - Une recherche ne remonte aucun message de la boîte déléguée.
   - Aucune notification « Nouveau message » n'arrive quand Virginie reçoit un message.
6. **Non-régression.** Un message reçu dans la propre BAL de Cyril est traité comme avant :
   patient, étiquettes, notification.
7. **Purge.** Après passage de la purge sur la base de Cyril :
   - les 7 patients issus des documents de Virginie ont disparu ;
   - ses messages délégués restent lisibles, documents décodés compris.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. La délégation de BAL est une fonctionnalité Mailiz (ANS, novembre
  2025), sans exigence DSR publiée pour les logiciels métier à ce jour.
- **Exigences DSR honorées** : non applicable — aucune exigence publiée. Le mode opératoire Mailiz
  est suivi : mêmes droits sur les messages, carnet d'adresses non partagé, gestion des
  délégations réservée au délégant.
- **INS** : non applicable en écriture. Aucun patient n'est créé ni rattaché depuis une BAL
  déléguée. L'INS du document reste affiché en lecture, comme dans le document lui-même.
- **Authentification PS** : inchangée. PSC / e-CPS pour le délégataire, condition Mailiz de la
  délégation.
- **Habilitations** : les droits sont tenus par le serveur Mailiz (ACL de délégation). L'API
  ajoute deux refus :
  - modification des dossiers système du délégant ;
  - actes cliniques (rattachement patient, acquittement) qui engagent le délégant.
- **Interop CI-SIS** : CDA r2 décodé à l'identique pour la lecture (volets existants via
  `interop-cda`). Aucun nouvel échange.
- **Tracé PGSSI-S** : l'audit existant continue de tracer lectures, suppressions et déplacements
  sur `shared/…`. Les refus 409 sont tracés. Distinguer la personne qui agit de la propriétaire de
  la BAL relève de la task-400.
- **Consentement patient** : non applicable — aucun partage nouveau. La délégation est une décision
  du délégant, sous sa responsabilité (secret professionnel).
- **Référentiels métier** : LOINC des documents, affichés en lecture
- **Hébergement HDS** : inchangé. **Moins** de données de santé dupliquées dans les bases des
  délégataires après la purge.
- **AIPD / impact RGPD** : **à mettre à jour**. Les BAL déléguées sont un nouveau flux d'accès aux
  données de santé d'un tiers. Il faut documenter :
  - la lecture seule clinique ;
  - l'absence de copie exploitée ;
  - la purge à la révocation, déjà couverte par la purge des dossiers disparus.

## Notes de cadrage

- **Marquer la provenance, le recommander** : une colonne calculée sur `Mails.FolderPath`, comme
  `IsInSentDraftOrTrashFolder`, posée à l'écriture, donc impossible à oublier. Le décodage
  (`EmailBuildingService.BuildMailDtoAsync` → `ProcessIheXdmZips`) reste inchangé. C'est
  l'exploitation qui se coupe, à commencer par `ResolveMedicalDocumentPatient`.
- **Points d'exploitation repérés** :
  - `MailRepository.cs:454-487` (patient), `:4487`, `:4555-4611`, `:4733-4809` (doublons et
    versions) ;
  - `PatientRepository.cs:610-626` ;
  - `AddNewMailConsumer.cs:66-75, 206-355` (IA, embeddings, contacts) ;
  - `EnrichedMailPersistence.cs:93-99, 181-251` (publication, notification) ;
  - `SemanticSearchRepository.cs:150-161`.
- **Corbeille** : aujourd'hui `SpecialFolder.Trash` seul (`ImapService.cs:3814-3818`, `:3916`,
  `:4055`, `:4157` ; `ImapFolderService.cs:436`), c'est-à-dire celle de la session.
- **Hors périmètre, tasks suivantes** :
  - affichage dédié, libellés, compteurs, sélecteurs et scénarios e2e : task-398 ;
  - envoi « de la part de », brouillons délégués, accusés de lecture : task-399 ;
  - traçabilité acteur / propriétaire : task-400.
