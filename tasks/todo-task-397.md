# todo-task-397.md — Délégation de BAL : lire la BAL déléguée en direct, sans jamais rien en persister

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Priorité**: **1** — le serveur Mailiz expose déjà les BAL déléguées. Le 2026-10-25, en formation,
un délégataire a fait sortir 2 messages de la BAL de sa délégante. Sa base contenait en outre :
- 101 de ses messages, avec leur corps ;
- 64 documents médicaux, avec l'identité de leurs patients ;
- **323 résultats de biologie** ;
- 7 patients ;
- 106 étiquettes IA.

> **Analyse complète** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md)
> (règles Mailiz, comportement du serveur, dégâts constatés, découpage task-397 à task-400).
>
> **Règle d'or** (CLAUDE.md règle 14, garde-fou `agents/po.md`, humain 2026-10-25) : **aucune
> donnée venant d'une BAL déléguée n'est persistée chez le délégataire.** Cette task en est la
> première application.
>
> **Périmètre backend seul (justification).** Les clients ne changent pas dans cette task.
> - Les refus de l'API arrivent en ProblemDetails.
> - Hors ligne, la BAL déléguée est simplement absente.
> - Relèvent de la task-398 :
>   - l'affichage dédié et la mention « disponible en ligne uniquement » ;
>   - le masquage des actions interdites ;
>   - l'ajout de la délégation au banc e2e et les scénarios `E2E-DELEG-…`, requis sur mobile et
>     weda2.

## Décisions actées (humain, 2026-10-25)

1. **Confiner plutôt que masquer.** Les dossiers `shared/<adresse du délégant>/…` restent visibles
   et gérables par le délégataire.
2. **Règle d'or : rien n'est persisté.** Aucune donnée d'une BAL déléguée n'est écrite chez le
   délégataire, ni en base tenant, ni dans Redis, ni dans un journal applicatif.
   - Sont visés : messages, en-têtes, corps, pièces jointes, documents CDA et HPRIM, biologie,
     résumés, identité patient, **noms de dossiers**, compteurs.
   - Tout est lu **en direct sur le serveur IMAP**, à chaque affichage, en mémoire.
   - **Pourquoi** : la délégation donne un droit d'**accès**, pas de copie. Une copie survit à la
     révocation : la purge actuelle ne tourne qu'au prochain listage en ligne des dossiers, et
     jamais si le délégataire ne revient pas. Elle survit aussi aux sauvegardes et aux caches.
3. **Seule exception : le journal d'audit** (PGSSI-S, imputabilité). Il garde l'action, l'auteur,
   le dossier, l'UID et le `Message-ID`. Il ne garde **ni objet, ni expéditeur ou destinataires,
   ni donnée patient**, et suit la durée de conservation de l'audit.
4. **Les documents CDA et HPRIM sont décodés et lisibles**, en mémoire, à l'ouverture du message :
   le délégataire ne voit pas une pièce jointe `IHE_XDM.ZIP` brute.
5. **Gestion seule, définitivement.** Un message délégué n'est jamais exploité : ni patient, ni
   dossier patient, ni doublons et versions, ni IA, ni embeddings, ni recherche, ni contacts, ni
   notification.
6. **Lecture seule sur les documents.** Ni rattachement à un patient, ni acquittement de biologie :
   ces actes restent au délégant.
7. **Pas de hors-ligne pour la BAL déléguée** : c'est la conséquence acceptée du point 2.

## Objective

Un délégataire ouvre la BAL qu'on lui délègue, y lit les messages et leurs documents décodés, les
trie, les déplace et les supprime. Tout est lu en direct sur le serveur Mailiz.

- **La BAL du délégant n'est jamais abîmée** : un message supprimé reste dans sa corbeille, et ses
  dossiers système ne bougent pas.
- **Rien de la BAL du délégant n'est conservé chez le délégataire.** Retirer la délégation ne
  laisse aucune donnée derrière elle, sans purge à déclencher.

Ce qui a déjà été copié à tort dans les bases et caches des délégataires est purgé une fois.

## Règles

- **Message, dossier délégué** : tout ce qui est sous `shared/` (espace de noms partagé Mailiz). Le
  **propriétaire** est la racine `shared/<adresse>`.
- **Lecture directe**, pour tout chemin `shared/…` :
  - la liste des dossiers délégués et leurs compteurs viennent du serveur (`LIST` et `STATUS`), à
    chaque demande, sans `MailFolders` ;
  - la liste paginée des messages vient du serveur (`SEARCH` et `FETCH` des enveloppes) ;
  - le détail vient du serveur (`FETCH` du corps et des pièces jointes) ; ses documents CDA (et
    plus tard HPRIM, task-389 et task-390) sont décodés en mémoire, par la **même liste de
    lecteurs** de pièces médicales que l'enrichissement ;
  - pièces jointes et PDF sont servis en flux depuis le serveur ;
  - lu, non lu, drapeaux, déplacement et suppression sont des commandes IMAP directes.
- **Aucune écriture chez le délégataire** pour un chemin `shared/…` :
  - aucune ligne `Mails`, `MailContents`, `MailAttachments`, `MailRecipients`, `MailFolders`,
    `MailTags` ;
  - aucune ligne `MailMedicalDocuments`, `MailMedicalDocumentBiology`, `MailMedicalDocumentSummary`,
    `MailPatients`, `BiologyAcks`, `PendingActions`, ni contact ;
  - aucune clé Redis porteuse d'une donnée du message ou du dossier ;
  - aucune publication vers l'IA, les embeddings, les contacts ou les notifications ;
  - aucun log portant objet, adresse de correspondant, nom de dossier sous la racine, contenu ou
    donnée patient.

  Une **garde unique à la frontière d'écriture** refuse tout chemin `shared/` ; une tentative est
  un bug, pas un cas métier.
- **La route d'enrichissement** (`…/emails/enrich/async`) ne fait rien sur un dossier délégué : il
  n'y a rien à enrichir, tout est lu à la demande.
- **Corbeille du propriétaire** : `shared/<adresse>/Trash`. Mailiz n'y pose aucun attribut
  SPECIAL-USE : on la reconnaît par sa position.
  - Supprimer un message délégué hors de cette corbeille l'y **déplace**.
  - Le supprimer depuis cette corbeille le **supprime définitivement**.
  - Jamais vers la corbeille du délégataire. Même règle pour la suppression groupée et la
    suppression d'un sous-dossier.
- **Dossiers système du délégant** : `shared/<adresse>` (sa réception) et ses `Sent`, `Drafts`,
  `Trash`, `Junk`. Ils ne peuvent être ni renommés, ni supprimés, ni déplacés : réponse **409**.
  Ses sous-dossiers personnels restent gérables, comme le permet Mailiz.
- **Jamais de déplacement entre BAL** (humain, 2026-10-25, séance de la task-398). Un déplacement
  ou une copie, unitaire ou groupé, ne se fait qu'à l'intérieur d'une même BAL : propre à propre,
  ou `shared/<A>/…` à `shared/<A>/…`.
  - Vers ou depuis une autre BAL : **409** ProblemDetails, rien ne bouge.
  - C'est le dégât du 2026-10-25 par un autre geste : un message déplacé de la BAL du délégant vers
    celle du délégataire en sort.
- **Actes cliniques refusés** : rattachement à un patient et acquittement de biologie sur un
  document délégué.
- **Recherche** : la recherche ne porte pas sur la BAL déléguée. Une recherche côté serveur
  (`SEARCH`) est envisageable plus tard, dans une task à part.
- **Hors ligne** : la BAL déléguée n'apparaît pas. Le fournisseur hors ligne ne renvoie aucun
  dossier `shared/`.
- **Audit** (exception de la décision 3) : `MailRead`, `MailDelete`, `MailMove`, `MailFlag`,
  `MedicalDocumentProcess` et les refus restent tracés, avec les seuls champs autorisés.
- **La propre BAL du délégataire n'est pas affectée** : elle reste lue « base d'abord », avec son
  traitement complet, comme aujourd'hui.

## Definition of Done

- [ ] **Banc de délégation.** Le Dovecot des tests d'intégration reproduit Mailiz :
      - espace `shared` ;
      - ACL : B délégataire de A, avec droits de lecture, écriture, suppression et création ;
      - état lu propre à chaque utilisateur.

      Sa configuration est documentée à côté de celle du banc existant.
- [ ] **Test d'intégration — liste des dossiers** : la liste de B contient la BAL déléguée de A et
      ses sous-dossiers, avec leurs compteurs lus sur le serveur. Après l'appel, `MailFolders` de B
      ne contient **aucune** ligne `shared/…`. Vu rouge (règle 1b).
- [ ] **Test d'intégration — liste et détail** :
      - la liste paginée de `shared/<A>` renvoie les messages du serveur ;
      - le détail d'un message porteur d'un `IHE_XDM.ZIP` de biologie renvoie son corps et ses
        documents décodés, valeur anormale signalée comprise ;
      - le PDF joint se télécharge.

      Le tout est lu dans la réponse réelle.
- [ ] **Test d'intégration — rien de persisté.** Après liste des dossiers, liste des messages,
      enrichissement, ouverture du détail, lu / non lu, déplacement et téléchargement de pièce
      jointe sur `shared/<A>`, la base de B et Redis sont vérifiés.
      - La base de B contient **zéro** ligne liée à `shared/…` dans toutes les tables listées en
        « Règles ».
      - **Aucune** clé Redis ne contient un UID, un objet, un corps, un nom de dossier sous la
        racine ni une donnée de document de A. Les clés sont inspectées.
      - Vu rouge sur le code actuel.
- [ ] **Garde d'écriture** : tout appel de dépôt avec un chemin `shared/…` lève une erreur typée.
      Prouvé par test unitaire. Un **test de convention** échoue si un nouveau chemin d'écriture
      (repository, cache, publication) la contourne, prouvé rouge par mutation.
- [ ] Test d'intégration : la route d'enrichissement sur `shared/<A>` ne produit rien et répond
      sans erreur.
- [ ] Test d'intégration de bout en bout pour `DELETE` d'un message de `shared/<A>` : le message
      est dans `shared/<A>/Trash` côté IMAP, absent de la corbeille de B. Vu rouge.
- [ ] Test d'intégration : suppression depuis `shared/<A>/Trash` → message supprimé définitivement,
      présent dans aucune corbeille. Idem pour la suppression groupée.
- [ ] Test d'intégration : suppression d'un sous-dossier de `shared/<A>` → ses messages vont dans
      `shared/<A>/Trash`.
- [ ] Test d'intégration : renommer, supprimer ou déplacer `shared/<A>`, `shared/<A>/Sent`,
      `/Drafts`, `/Trash` ou `/Junk` → **409** `application/problem+json`, dossier intact. Le même
      geste sur un sous-dossier personnel de A est accepté.
- [ ] Test d'intégration : déplacer, unitairement et en groupe, un message de `shared/<A>` vers la
      réception de B, et un message de B vers `shared/<A>` → **409**, les deux messages restent
      dans leur dossier côté IMAP. Un déplacement de `shared/<A>` vers `shared/<A>/Demo` est
      accepté. Vu rouge.
- [ ] Test d'intégration : `attach-patient` et `biology-ack` sur un document délégué → refus en
      ProblemDetails, rien d'écrit.
- [ ] Test d'intégration : aucune notification « Nouveau message » et aucun contact publié quand A
      reçoit un message.
- [ ] Test d'intégration : la recherche de B ne renvoie aucun message de A ; le mode hors ligne de
      B ne renvoie aucun dossier `shared/`.
- [ ] Test d'intégration — **révocation** : l'ACL de B sur A est retirée au banc. La liste suivante
      ne contient plus la BAL de A, et **il n'y a rien à purger** : zéro ligne avant comme après.
- [ ] Test d'intégration — **audit** : les traces d'une lecture et d'une suppression déléguées
      portent l'action, l'auteur, le dossier, l'UID et le `Message-ID`, et **ni** objet, **ni**
      adresses de correspondants, **ni** INS ni nom de patient.
- [ ] Non-régression : la propre BAL de B garde sa lecture « base d'abord » et son traitement
      complet : document, biologie, patient, IA, notification.
- [ ] **Purge unique de l'existant**, rejouable et idempotente, sur toutes les bases tenant et
      Redis. Pour tout ce qui est sous `shared/` :
      - les messages et tout ce qui en dépend (contenus, pièces jointes, destinataires, documents,
        biologie, résumés, acquittements, étiquettes, embeddings) ;
      - les dossiers `MailFolders` ;
      - les patients et contacts qui n'en proviennent que là ;
      - les clés Redis.

      Elle épure aussi les traces d'audit `shared/…` déjà écrites : objet, adresses et données
      patient remises à vide. Elle journalise des comptes, sans donnée de santé. Si l'origine d'un
      contact n'est pas traçable, arrêt et `questions/task-397.md`.
- [ ] **Mesure** : temps de réponse de la liste et du détail d'un dossier délégué au banc, comparés
      à la propre BAL, consignés dans le `## Develop log`. Aucune régression sur la propre BAL.
- [ ] Build et tests verts ; `/e2e` vert, avec les parcours existants rejoués.

## Manual Test Plan

Comptes de formation : Cyril (`cyril.toubib0072344@medecin.formation.mssante.fr`) est délégataire
de Virginie (`virginie.medecinrpps0062267@medecin.formation.mssante.fr`).

0. **Avant le test**, remettre à leur place les 2 messages déplacés à tort le 2026-10-25. Depuis le
   webmail Mailiz de Cyril : Corbeille, puis les deux messages du 2026-06-10, à déplacer vers la
   boîte déléguée de Virginie.
1. Lancer l'AppHost (`dotnet run --project Api/Mail/src/AppHost`), puis le mobile
   (`cd Client/Mobile && npm start`) ou weda2. Se connecter en Cyril par PSC.
2. **Purge.** Après passage de la purge, la base de Cyril ne contient **plus aucune** ligne liée à
   `shared/…`, dans aucune table, et ses 7 patients issus de Virginie ont disparu. La purge ne
   touche à aucun de ses propres messages.
3. **Lecture.** Ouvrir la boîte déléguée de Virginie, puis un compte rendu de biologie : le message
   et le document décodé s'affichent, et les valeurs anormales sont signalées. Aucune invitation
   « à intégrer », aucun acquittement possible.
4. **Rien de persisté.** Relancer la requête de l'étape 2 : toujours **zéro** ligne `shared/…`,
   alors que des messages viennent d'être lus.
5. **Suppression.** Supprimer un message de la boîte déléguée : il apparaît dans la **Corbeille de
   Virginie**, et le webmail Mailiz de Virginie le confirme.
6. **Protection.** Tenter de renommer les Envoyés de Virginie : refus. Créer, puis renommer un
   sous-dossier dans sa boîte : accepté.
7. **Cloisonnement.**
   - Aucune notification quand Virginie reçoit un message.
   - La recherche de Cyril ne remonte rien de Virginie.
   - Hors ligne, la boîte déléguée n'apparaît pas.
8. **Révocation.** Virginie retire la délégation dans le webmail Mailiz. Au rafraîchissement, la
   boîte déléguée disparaît chez Cyril, et sa base ne contient toujours rien de Virginie.
9. **Non-régression.** Un compte rendu reçu dans la propre BAL de Cyril est traité comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. La délégation de BAL est une fonctionnalité Mailiz (ANS, novembre
  2025), sans exigence DSR publiée pour les logiciels métier à ce jour.
- **Exigences DSR honorées** : non applicable — aucune exigence publiée. Le mode opératoire Mailiz
  est suivi : mêmes droits sur les messages, carnet d'adresses non partagé, gestion des
  délégations réservée au délégant.
- **INS** : non applicable en écriture. L'INS est affiché en lecture dans le document décodé, sans
  être conservé ni journalisé.
- **Authentification PS** : inchangée. PSC / e-CPS pour le délégataire, condition Mailiz de la
  délégation.
- **Habilitations** : les droits sont tenus par le serveur Mailiz (ACL de délégation), lus en
  direct à chaque accès. Un retrait est donc effectif immédiatement. L'API ajoute deux refus :
  - modification des dossiers système du délégant ;
  - actes cliniques qui engagent le délégant.
- **Interop CI-SIS** : CDA r2 décodé à l'identique pour la lecture (volets existants via
  `interop-cda`), en mémoire. Aucun nouvel échange.
- **Tracé PGSSI-S** : l'imputabilité est conservée (décision 3). Les actes du délégataire sur la BAL
  déléguée sont tracés avec action, auteur, dossier, UID et `Message-ID`, sans objet, sans
  correspondants, sans donnée patient. Distinguer la personne qui agit de la propriétaire de la
  BAL relève de la task-400.
- **Consentement patient** : non applicable — aucun partage nouveau. La délégation est une décision
  du délégant, sous sa responsabilité (secret professionnel).
- **Référentiels métier** : LOINC et codes de biologie, affichés en lecture, jamais stockés
- **Hébergement HDS** : inchangé. Après la purge, **plus aucune** donnée d'une BAL déléguée n'est
  dupliquée chez un délégataire.
- **AIPD / impact RGPD** : **à mettre à jour**. Les BAL déléguées sont un nouveau flux d'accès aux
  données de santé d'un tiers. Il faut documenter :
  - accès en lecture directe, sans copie ;
  - minimisation : rien de persisté, hors audit réduit ;
  - effet immédiat de la révocation.

## Notes de cadrage

- **Changement d'architecture, limité aux chemins `shared/`.** api-mail lit « base d'abord » :
  liste depuis la base, enrichissement asynchrone. Les dossiers délégués ont besoin d'un
  **fournisseur de lecture directe**, qui pourrait s'appuyer sur `OnlineMailDataProvider` et
  `ImapService` sans leurs écritures, choisi par le chemin.
  - La séparation existe déjà entre `OfflineMailDataProvider` et `OnlineMailDataProvider` : c'est
    le point d'insertion naturel.
- **Points d'écriture à couvrir par la garde** :
  - `ImapService.cs:303` et `:504`, `ImapFolderService.cs:126-139` (dossiers) ;
  - `ImapService.cs:3182` (en-têtes) ;
  - `EnrichedMailPersistence`, `MailRepository` (messages, documents, patients) ;
  - `AddNewMailConsumer` (IA, embeddings, contacts) ;
  - les clés `RedisKeys.Folder.*` et le cache des contenus ;
  - `DraftService` et `PendingActions`.
- **Corbeille** : aujourd'hui `SpecialFolder.Trash` seul (`ImapService.cs:3814-3818`, `:3916`,
  `:4055`, `:4157` ; `ImapFolderService.cs:436`), c'est-à-dire celle de la session.
- **Performance** : le verrou de session IMAP est le goulet connu au banc de charge (E015). La
  lecture directe d'une BAL déléguée ajoute des allers-retours IMAP. On les mesure (DoD), sans
  viser un objectif chiffré dans cette task.
- **HPRIM** (task-389 et task-390, décision 8 et décision 4) : affiché seulement, par le même
  chemin de lecture en mémoire et la même liste de lecteurs.
- **Hors périmètre, tasks suivantes** :
  - affichage dédié, mention « disponible en ligne uniquement », compteurs, sélecteurs et
    scénarios e2e : task-398 ;
  - envoi « de la part de », brouillons délégués, accusés de lecture : task-399 ;
  - traçabilité acteur / propriétaire : task-400.
