# todo-task-397.md — Délégation de BAL : lire la BAL déléguée en direct, sans jamais rien en persister

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Priorité**: **1** — le serveur Mailiz expose déjà les BAL déléguées. Le 2026-10-25, en formation,
un délégataire a fait sortir 2 messages de la BAL de sa délégante. Sa base contenait en outre :
- 101 de ses messages ;
- 64 documents ;
- **323 résultats de biologie** ;
- 7 patients.

Les journaux Seq portaient les chemins de sa BAL.

> **Analyse** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md).
> **Revue du code** (constats et références de lignes) : [Docs/audits/delegation-bal-revue-code-20261025.md](../Docs/audits/delegation-bal-revue-code-20261025.md),
> §3.1 à 3.7 et §3.10.
>
> **Règle 14** (CLAUDE.md) : **aucune donnée venant d'une BAL déléguée n'est persistée chez le
> délégataire.** Cette task en est la mise en œuvre côté api-mail.
>
> **Périmètre backend seul (justification).** Les clients ne changent pas dans cette task : les
> refus arrivent en ProblemDetails. L'affichage dédié, le masquage des gestes, le contrat
> d'erreur côté client et les scénarios e2e relèvent de la task-398.

## Décisions actées (humain, 2026-10-25)

1. **Confiner plutôt que masquer.** Les dossiers `shared/<adresse>/…` restent visibles et gérables.
2. **Règle d'or : rien n'est persisté** chez le délégataire, ni en base, ni dans Redis, ni dans un
   journal ou une télémétrie, ni dans le bus de messages. Tout est lu en direct sur le serveur
   IMAP.
3. **Seule exception : le journal d'audit**, réduit à l'action, l'auteur, le dossier, l'UID et le
   `Message-ID`.
4. **Documents CDA et HPRIM décodés et lisibles**, jamais conservés. Le **répertoire de travail
   transitoire** du décodage IHE-XDM est accepté, avec ses garanties : fichiers supprimés à la
   fin, balayés au démarrage. C'est un stockage technique, jamais un lieu de conservation.
5. **Gestion seule** : un message délégué n'est jamais exploité (patient, dossier patient,
   doublons, IA, recherche, contacts, notification). Les documents sont en lecture seule : ni
   rattachement, ni acquittement.
6. **Jamais de déplacement entre BAL**, y compris entre deux délégations.
7. **Pas de hors-ligne** pour la BAL déléguée.
8. **Impression, export PDF / EML et téléchargement de pièces jointes : permis**, comme geste
   explicite de l'utilisateur. Ils sont servis en direct, avec un audit réduit, et l'objet
   n'apparaît jamais dans un nom de fichier.
9. **Révocation : fenêtre bornée acceptée**, au plus la durée de vie d'une session IMAP poolée
   (5 min). Au-delà, plus rien n'est servi.
10. **Une seule task** : protection et lecture directe ne sont pas scindées.
11. **Pas de purge de l'existant** : la délégation n'a existé que sur des comptes de formation,
    déjà purgés. Les traces d'audit passées restent en l'état.
12. **Cache Redis du contenu décodé**, pour ne pas décoder plusieurs fois un même message :
    réouverture, PDF du compte rendu, impression, export. api-mail tourne sur **plusieurs pods**,
    donc un cache en mémoire du processus ne convient pas. C'est une exception à la règle 14,
    bornée par la section J.
13. **Persistance AOF de Redis acceptée telle quelle** : le résidu du cache dans le fichier AOF,
    jusqu'à sa réécriture, est accepté. Pas de chiffrement applicatif, pas d'instance dédiée.

## Objective

Un délégataire ouvre la BAL qu'on lui délègue, y lit les messages et leurs documents décodés, les
trie, les déplace, les supprime, les imprime ou les exporte. Tout est lu en direct sur le serveur
Mailiz. La BAL du délégant n'est jamais abîmée, rien n'est conservé chez le délégataire, et ses
journaux ne contiennent ni noms de dossiers délégués, ni objets, ni noms de pièces jointes.

## Règles

### A. Chemins délégués

- Le **préfixe partagé** est lu dans la réponse `NAMESPACE` du serveur, avec `shared/` par défaut.
  Il est comparé **après** décodage de l'URL et résolution des étiquettes.
- Un chemin sous ce préfixe n'est accepté **que s'il figure tel quel** dans le `LIST` courant de la
  session.
  - Les alias sont refusés en **404** ProblemDetails : `shared/<A>/INBOX` pour la réception, une
    autre casse du propriétaire.
  - Les propriétaires sont comparés sans tenir compte de la casse.
- **Propriétaire** d'un chemin : sa racine `shared/<adresse>`.
- **Rôle** d'un dossier délégué, déduit de sa **position** sous la racine (Mailiz ne pose aucun
  attribut SPECIAL-USE) : réception = la racine ; `Sent`, `Drafts`, `Trash`, `Junk` ; dossier
  personnel sinon.
  - La règle de nommage `MailFolderNamingRule`, qui découpe aussi sur `.`, ne sert **pas** à
    déterminer ce rôle.

### B. Lecture directe

- **L'aiguillage se fait au niveau des services** : `IImapService`, `IImapFolderService`,
  `IEmailFlagService`, et les services d'export et de pièces jointes. Ce n'est pas la fabrique de
  fournisseurs en ligne / hors ligne, que la moitié des routes contourne.
- **Liste des dossiers** : les dossiers personnels restent mis en cache comme aujourd'hui. Les
  dossiers délégués et leurs compteurs (`LIST`, `STATUS`) sont lus en direct, jamais mis en cache
  ni enregistrés.
- **Listes de messages** (en-têtes, `today`, `unread-today`, `unread`, `recent`) : `SEARCH` et
  `FETCH` en direct.
  - Les en-têtes portent un **statut d'enrichissement terminal**, et non `Pending`.
  - Aucun nombre de messages de fil n'est calculé à partir de la base du délégataire.
  - **Indicateur « document médical » sans décodage** : `HasMedicalDocuments` est posé à partir de
    la **structure du message**, déjà lue avec l'enveloppe. Il suffit de la présence d'une pièce
    `ihe_xdm.zip` (ou `.hpm` après task-389), selon la même règle de nom que
    `EnrichmentFetchPlan`. `HasBiologyResults` reste inconnu (faux) jusqu'à l'ouverture.
- **Détail** : passe par `ReadEmailWithoutPersistingAsync`. Les lignes déjà en base pour ce chemin
  sont **ignorées**.
  - Le décodage CDA, XSLT et PDF se fait **hors du verrou** `imap_session`.
  - Les documents rendus portent un **identifiant non résolvable**, sans patient, ni doublon, ni
    version, ni demande de suppression.
- **Pièces jointes MIME, zip, impression, export PDF / EML** : servis depuis le serveur, sans
  réécriture `MailAttachments`. Impression et export réutilisent le contenu décodé du cache
  (section J).
- **PDF associé à un CDA** : il est **à l'intérieur de l'archive IHE-XDM**, pas en pièce MIME.
  Aujourd'hui, `GetAttachmentAsync` (`ImapService.cs:3508`) ne le trouve qu'en base, où
  l'enrichissement l'a déposé, puis cherche une pièce MIME du même nom (`:3534`). Pour un message
  délégué, ce serait un **404**.
  - Il est servi depuis le **cache** de la section J.
  - À défaut, il est servi en **redécodant** l'archive.
- **Lu, non lu, drapeaux** (unitaires et groupés) : commande IMAP `STORE` directe. **Aucune**
  ligne `PendingActions` : on contourne la file de `FlagPropagationService`.
- **Enrichissement** : `enrich/async` **et `enrich/sync`** ne font rien sur un chemin délégué. Ils
  sortent avant toute lecture IMAP, réservation Redis, notification ou reprise IA, et répondent
  **200**.
- **Synchronisation** : voir la section I. Aucun dossier délégué n'est jamais traité, et chaque
  écart est journalisé « skipped ».

### C. Aucune écriture

Une **garde unique** refuse toute écriture ou mise à jour dont un chemin est délégué. Elle couvre :
- **les dépôts** de la base tenant, dont `PendingActions`, `UserSettings`, `MailAttachments`,
  `MailFolders` à la création et au renommage, et `MailTags` ;
- **le cache**, par un décorateur sur `IResilientCacheService`, qui contrôle aussi les **valeurs** :
  la liste des dossiers mise en cache ne contient aucun dossier délégué. **Seule** la famille de
  clés du cache de contenu délégué (section J) est admise, et seulement par son propre service ;
- **la publication sur le bus**.

Une tentative est un bug : erreur typée. Les suppressions restent permises : il n'y a de toute façon
aucune ligne déléguée à supprimer.

**Hors ligne** : tout geste d'écriture sur un chemin délégué (lu, drapeau, suppression) est refusé
en ProblemDetails, et rien n'est mis en attente.

### D. Journaux et télémétrie

Un **masquage central** remplace par `shared/<adresse>/…` tout ce qui suit la racine d'un chemin
délégué, et retire tout nom de pièce jointe déléguée. Il s'applique :
- aux propriétés, au message et au texte d'exception de chaque événement Serilog, par un
  enrichisseur ;
- au chemin et à la requête HTTP (`SensitiveRequestDataSanitizer`, journal des requêtes, attributs
  OTel `url.path` et `url.query`) ;
- à l'attribut OTel `email.folder` ;
- aux étiquettes du verrou (`ImapLockScope`), qui ne contiennent jamais de nom de pièce jointe ;
- aux libellés des tâches en arrière-plan.

Les journaux de contenu clinique (`CdaParsingService`) ne s'écrivent pas pour un document délégué.

### E. Audit

- **Liste blanche appliquée dans `AuditService.Trace`, avant le tampon Redis** : pour toute trace
  dont le dossier **contient** le préfixe partagé (un déplacement s'écrit `src -> tgt`), seuls
  restent l'action, la date, le succès, l'auteur, le dossier, l'UID et le `Message-ID`.
  Tous les autres champs sont vidés : objet, adresses, INS, nom de patient, `document_*`,
  `server_request`, `server_response`, `error_message`, `error_details`. Cela vaut pour toutes les
  familles :
  - lecture, drapeau, suppression, déplacement ;
  - décodage de document (`MedicalDocumentProcess`) ;
  - téléchargement de pièce jointe et zip ;
  - impression, export PDF et EML.
- **`Message-ID` lu en direct** (enveloppe IMAP), puisqu'aucune ligne n'existe en base.
- Le tampon Redis `mss:audit:spill` relève de l'exception d'audit.

### F. Routes refusées sur un chemin délégué (ProblemDetails, rien d'écrit ni d'envoyé)

- **Résumé IA** (`…/emails/summary/{id}`), `recalculate-summary`, conversation IA portant sur un
  message délégué : **aucun appel au fournisseur d'IA**.
- **Accusés de lecture** `sendreadreceipt` et `declinereadreceipt` : aucun envoi SMTP. Un message
  délégué n'expose pas `ReadReceiptTo`.
- **Étiquettes manuelles** : ajout et retrait.
- **Annuler et remplacer** (`cancel-and-replace`, `cancel-and-replace-draft`) sur un message
  délégué.
- **Actes cliniques** : `attach-patient`, `detach-patient`, `duplicate-decision`,
  `suppression-decision`, `biology-ack` et actions de biologie sur un document délégué.
- **Recherche** sur un dossier délégué, refusée **avant** tout enregistrement d'historique.
- **Réglages** : un dossier d'ouverture sous le préfixe partagé.

### G. BAL du délégant

- **Corbeille du propriétaire** : `shared/<adresse>/Trash`.
  - Supprimer, unitairement ou en groupe, l'y déplace.
  - Supprimer depuis elle est définitif.
  - Supprimer un sous-dossier délégué y envoie ses messages.
  - Jamais vers la corbeille du délégataire.
- **Dossiers système du délégant** (racine, `Sent`, `Drafts`, `Trash`, `Junk`) : renommer ou
  supprimer → **409**, avec une **exception typée nouvelle**. Les refus actuels sont des
  `Result.Error`, donc des 500. Il faut aussi refuser :
  - de créer un dossier **sous le conteneur** `shared` ;
  - de créer un dossier sous un dossier système du délégant.

  Les sous-dossiers personnels du délégant restent gérables. Le serveur, lui, laisse supprimer
  ses dossiers système : ce 409 est la seule protection.
- **Jamais de déplacement entre BAL**, unitaire ou groupé : propre vers délégué, délégué vers
  propre, ou délégation A vers délégation C → **409**, rien ne bouge.

### H. Révocation

- Effet au plus tard à la fin de la fenêtre bornée (décision 9). Aucun cache ne sert de donnée
  déléguée au-delà.
- Une racine absente du `LIST` courant, ou passée en `\Noselect`, vaut retrait. L'accès suivant
  répond **404** ProblemDetails avec un **`type` dédié** « délégation retirée », que la task-398
  affichera.

### I. Synchronisation : les dossiers délégués ne sont jamais traités, et chaque écart se voit

**Exigence de l'humain** (2026-10-25) : les dossiers `shared/` ne sont pas traités par la
synchronisation, et les journaux affichent « skipped » pour **chacun** d'eux.

- **Un seul prédicat** « dossier délégué » (règle A) est appliqué à **l'entrée de chaque mécanisme
  de synchronisation**, avant toute lecture IMAP, réservation, écriture ou publication :
  - `BackgroundSyncService` et `BackgroundImapService`, la synchronisation périodique ;
  - l'enregistrement et le rapprochement des dossiers à la liste (`ImapService.cs:490`, `:496`),
    et la purge des dossiers disparus (`:504`), qui ne voient jamais un dossier délégué ;
  - l'enregistrement des en-têtes (`FetchEmailsInternalAsync`, `:3182`) ;
  - l'enrichissement `enrich/async` et `enrich/sync` (`EnrichEmailsAsync`, avant `:1646`) ;
  - la couverture de synchronisation (`SyncCoverageService`) et l'état d'avancement
    (`RedisSyncStateStore`) ;
  - la reprise de l'étiquetage IA (`AiTaggingRecoveryService`).
- **La synchronisation périodique liste aussi l'espace partagé**, avec un `LIST` du préfixe lu dans
  `NAMESPACE`, pour **voir** les dossiers délégués et les écarter explicitement. Aujourd'hui elle ne
  les voit pas, par accident : elle ne descend qu'au premier niveau et saute le conteneur.
- **Journal « skipped »** : une entrée par dossier délégué écarté, à chaque passage, au niveau
  **Information**. Gabarit unique :

  ```
  [Sync] Skipped delegated folder {Folder} (owner={Owner}, role={Role}, by={Mechanism})
  ```

  - `{Folder}` est masqué selon la règle D : `shared/<adresse>` pour la réception, `shared/<adresse>/…`
    pour tout le reste, sans aucun nom de sous-dossier.
  - `{Role}` vaut `Inbox`, `Sent`, `Drafts`, `Trash`, `Junk` ou `Personal`. C'est un rôle, jamais
    un nom choisi par le délégant.
  - `{Mechanism}` est le mécanisme qui écarte : `BackgroundSync`, `FolderList`, `Enrich`,
    `Coverage`…
  - Le journal ne porte ni UID, ni objet, ni compteur de messages.
- **Pas de journal « skipped » pour la lecture directe** : lire un dossier délégué à la demande de
  l'utilisateur n'est pas une synchronisation (règle B).

### J. Cache Redis du contenu délégué décodé (décisions 12 et 13)

- **Contenu** : le résultat décodé d'un message délégué, c'est-à-dire corps, documents rendus,
  biologie et **PDF associés**.
- **Famille de clés dédiée**, la seule admise par la garde pour un contenu délégué. La clé est une
  **empreinte** (HMAC) de : personne qui agit (RPPS de la session PSC), BAL propriétaire, dossier,
  `UIDVALIDITY` et UID. Elle ne contient **jamais** de chemin, d'adresse ni d'UID en clair.
- **Propre à la personne** : un autre utilisateur, y compris le délégant ou un autre délégataire,
  ne peut jamais la lire. L'empreinte inclut la personne.
- **Durée de vie de 5 minutes au plus** (expiration absolue, sans prolongation), alignée sur la
  fenêtre de révocation (décision 9). Le cache ne prolonge aucun accès.
- **Taille bornée** : une entrée au-delà d'une taille maximale configurable n'est pas mise en cache,
  et sera redécodée. Un nombre maximal d'entrées par personne est fixé par configuration.
- **Invalidation**, valable pour tous les pods par un `DEL` Redis :
  - suppression ou déplacement du message ;
  - révocation détectée (règle H), qui efface toutes les entrées de la personne pour ce
    propriétaire.
- **Lecture** : l'ouverture, le téléchargement du PDF, l'impression et l'export lisent le cache
  d'abord. En cas d'absence, ils décodent puis écrivent dans le cache.
- **Journaux** : un succès ou un échec de lecture du cache peut être journalisé, sans clé ni
  contenu.
- **Ni l'audit, ni la synchronisation, ni le bus ne lisent ce cache.**
- **AOF** : le résidu dans le fichier de persistance de Redis est accepté (décision 13).

## Definition of Done

- [ ] **Caractérisation Mailiz** consignée dans le `## Develop log` et dans l'analyse (§4), faite
      sur les comptes de formation. Elle mesure :
      - `NAMESPACE` et `MYRIGHTS` du délégataire, droit `x` sur les dossiers système compris ;
      - les alias `shared/<A>/INBOX` et la casse du propriétaire ;
      - la présence de `Junk` ;
      - l'effet d'un retrait de droits sur une session ouverte.

      Les écarts avec le banc sont reportés dans le banc.
- [ ] **Banc de délégation** : un **fragment** de configuration Dovecot, monté par les tests
      d'intégration et le banc e2e, **pas** par le banc de charge ni par la copie DevOps. Il
      contient :
      - les plugins `acl` et `imap_acl` ;
      - un espace `shared` (`prefix=shared/%%u/`, `INDEXPVT`, `list=children`) ;
      - un `Junk` pour A ;
      - des droits posés par `SETACL` IMAP et alignés sur le `MYRIGHTS` mesuré.

      Documenté à côté du banc existant. Le prototype de la revue sert de point de départ.
- [ ] **Test d'intégration « rien de persisté »**, vu rouge, sur le parcours délégué complet :
      - liste des dossiers ; en-têtes ; `today`, `unread-today`, `unread`, `recent` ;
      - détail avec document de biologie ; pièce jointe et zip ; impression et exports ;
      - lu et non lu, drapeaux, unitaires et groupés ;
      - déplacement, suppression ;
      - `enrich/sync` et `enrich/async`.

      Après le parcours :
      - **zéro** ligne liée au chemin dans toutes les tables du tenant, `PendingActions` et
        `UserSettings` compris ;
      - **aucune** clé **ni valeur** Redis portant un chemin, un UID, un objet, un corps ou une
        donnée de document délégués (inspection des clés et des valeurs), **hors** la famille du
        cache de contenu délégué (section J). Ses clés sont des empreintes et ses entrées ont une
        expiration de 5 minutes au plus ;
      - **aucun** message publié sur le bus.
- [ ] **Test d'intégration journaux et traces** : un collecteur des événements Serilog et des
      activités OTel, pendant le même parcours, ne trouve aucun nom de sous-dossier délégué, aucun
      objet, aucun nom de pièce jointe ni aucune donnée patient. Vu rouge par mutation du
      masquage.
- [ ] **Test d'intégration audit** : pour chaque famille listée en E, la trace ne contient que les
      champs de la liste blanche, et son `Message-ID` est **non vide**. Le même contrôle est fait
      sur une trace passée par le tampon Redis.
- [ ] **Test de convention** : chaque chemin d'écriture (dépôt, cache, publication) passe par la
      garde. Prouvé rouge par mutation.
- [ ] **Indicateur de liste** : la liste de `shared/<A>` marque `HasMedicalDocuments` pour un
      message porteur d'un `IHE_XDM.ZIP`, sans aucun décodage (zéro appel à
      `ProcessIheXdmZips` pendant la liste), lu dans la réponse réelle.
- [ ] **Lecture** : le détail d'un compte rendu de biologie délégué renvoie le corps, les documents
      décodés, la valeur anormale signalée et un identifiant de document non résolvable. Les
      en-têtes ont un statut terminal. Lu dans la réponse réelle.
- [ ] **Cache de contenu délégué** — test d'intégration avec **deux instances** de l'API sur le même
      Redis :
      - le message est ouvert sur l'instance 1, puis rouvert, le PDF téléchargé et le message
        exporté sur l'instance 2 : **un seul** décodage (compteur de `ProcessIheXdmZips`) ;
      - expiration ≤ 5 min, vérifiée par le TTL ;
      - la clé est une empreinte, sans chemin ni adresse ;
      - un autre utilisateur ne l'atteint pas ;
      - suppression, déplacement et révocation l'effacent ;
      - une entrée trop grosse n'est pas mise en cache.

      Vu rouge (règle 1b).
- [ ] **PDF associé à un CDA délégué** : « Télécharger le PDF » rend le PDF, servi depuis le cache, et
      en redécodant si l'entrée a expiré. Jamais de 404. Lu dans la réponse réelle, vu rouge sur le
      code actuel.
- [ ] **Corbeille** : suppressions unitaire et groupée, suppression définitive depuis
      `shared/<A>/Trash`, suppression d'un sous-dossier. Vérifié côté IMAP, vu rouge.
- [ ] **Dossiers système et chemins** :
      - renommer ou supprimer un dossier système délégué → 409, intact côté IMAP ;
      - créer sous `shared` ou sous `shared/<A>/Sent` → refus ;
      - `shared/<A>/INBOX` et une autre casse → 404 ;
      - un sous-dossier personnel de A reste gérable.
- [ ] **Déplacements** : propre vers délégué, délégué vers propre, et A vers C (deux délégations au
      banc) → 409, rien ne bouge. Un déplacement dans `shared/<A>` passe.
- [ ] **Routes refusées** (F) : chacune testée → ProblemDetails, et :
      - **zéro** appel au fournisseur d'IA (faux fournisseur) ;
      - **zéro** envoi SMTP pour les accusés ;
      - rien d'écrit, historique de recherche compris.
- [ ] **Hors ligne** : lu, drapeau et suppression sur un chemin délégué → refus, `PendingActions`
      vide. Le fournisseur hors ligne ne renvoie aucun dossier délégué.
- [ ] **Révocation** : après `DELETEACL` au banc, le `LIST` suivant ne contient plus `shared/<A>`. Un
      accès au-delà de la fenêtre bornée → 404 de `type` « délégation retirée ». Aucune donnée
      servie depuis un cache.
- [ ] **Synchronisation — test d'intégration** sur le banc de délégation : B a la BAL de A
      (réception, `Sent`, `Trash`, `Junk`, `Demo`, `Demo/Biologie2026`). On lance un passage de
      synchronisation périodique, une liste des dossiers, puis `enrich/sync` et `enrich/async` sur
      la réception de A. Après quoi :
      - **zéro** écriture et **zéro** publication pour ces dossiers ;
      - **une** entrée « Skipped delegated folder » **par dossier délégué** et par mécanisme, au
        niveau Information, lue dans les journaux capturés ;
      - le chemin est masqué (`shared/<A>/…`), aucun nom de sous-dossier (`Demo`) n'apparaît, et le
        rôle est juste.

      Vu rouge en retirant le prédicat d'un mécanisme : test de convention par mutation.
- [ ] **Synchronisation — robustesse** : sur un banc où le conteneur `shared` est **sélectionnable**,
      la synchronisation périodique ne traite toujours aucun dossier délégué et journalise
      « skipped » pour chacun.
- [ ] **Mesure** sur le banc d'intégration : temps de réponse **et temps de détention du verrou**
      `imap_session`, pour la liste, le détail et la pièce jointe délégués, comparés à la propre
      BAL. Consignés dans le `## Develop log`, sans objectif chiffré. Aucune régression sur la propre
      BAL.
- [ ] Non-régression : la propre BAL de B garde sa lecture « base d'abord » et son traitement
      complet.
- [ ] Build et tests verts ; `/e2e` vert, avec les parcours existants rejoués.

## Manual Test Plan

Comptes de formation : Cyril (`cyril.toubib0072344@medecin.formation.mssante.fr`) est délégataire
de Virginie (`virginie.medecinrpps0062267@medecin.formation.mssante.fr`).

1. Lancer l'AppHost (`dotnet run --project Api/Mail/src/AppHost`), puis le mobile
   (`cd Client/Mobile && npm start`) ou weda2. Se connecter en Cyril par PSC.
2. **Lecture.** Ouvrir la boîte déléguée de Virginie, puis un compte rendu de biologie : il est
   décodé, et les valeurs anormales sont signalées. Exporter le message en PDF : le fichier ne
   porte pas l'objet dans son nom.
3. **Rien de persisté.** Dans la base de Cyril, aucune ligne liée à `shared/…`, `PendingActions`
   compris, même après avoir marqué des messages lus.
4. **Journaux.** Dans Seq, filtrer sur l'heure du test : on voit `shared/<adresse>/…`, jamais un
   sous-dossier (`Demo`…), un objet ni un nom de pièce jointe.
5. **Synchronisation.** Dans Seq, filtrer sur `Skipped delegated folder` après un passage de
   synchronisation :
   - une entrée par dossier de la boîte de Virginie : réception, Envoyés, Corbeille, Spam,
     Brouillons, et ses sous-dossiers en rôle `Personal`, masqués ;
   - aucune entrée de synchronisation ni d'enrichissement « réussi » pour ces dossiers.
6. **Suppression.** Supprimer un message délégué : il est dans la Corbeille de Virginie, et son
   webmail Mailiz le confirme.
7. **Protection.**
   - Renommer les Envoyés de Virginie : refus.
   - Déplacer un message de sa boîte vers celle de Cyril : refus.
   - Créer, renommer un sous-dossier dans sa boîte : accepté.
8. **Refus.** Demander une synthèse IA ou envoyer un accusé de lecture sur un message délégué :
   refus clair, rien d'envoyé.
9. **Révocation.** Virginie retire la délégation dans le webmail Mailiz. Après au plus 5 minutes,
   l'accès à sa boîte est refusé avec le message « délégation retirée ».
10. **Non-régression.** Un compte rendu reçu dans la propre BAL de Cyril est traité comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. La délégation de BAL est une fonctionnalité Mailiz (ANS, novembre
  2025), sans exigence DSR publiée pour les logiciels métier.
- **Exigences DSR honorées** : non applicable. Le mode opératoire Mailiz est suivi.
- **INS** : non applicable en écriture. L'INS est affiché en lecture dans le document décodé, sans
  être conservé, journalisé ni audité.
- **Authentification PS** : inchangée — PSC / e-CPS du délégataire, condition Mailiz
- **Habilitations** : ACL Mailiz lues en direct, avec une fenêtre de révocation bornée (5 min).
  L'API ajoute ses refus : dossiers système, déplacements entre BAL, actes cliniques, IA, accusés.
- **Interop CI-SIS** : CDA r2 décodé pour la lecture via `interop-cda`, dans un répertoire de travail
  transitoire. Aucun nouvel échange.
- **Tracé PGSSI-S** : l'imputabilité est conservée par l'audit réduit. Les journaux applicatifs
  sont expurgés des données déléguées.
- **Consentement patient** : non applicable — décision du délégant, sous sa responsabilité
- **Référentiels métier** : LOINC et codes de biologie, affichés, jamais stockés
- **Hébergement HDS** : inchangé — aucune donnée d'une BAL déléguée dupliquée chez un délégataire
- **AIPD / impact RGPD** : **à mettre à jour**. Il faut documenter :
  - l'accès en lecture directe, sans copie ;
  - la minimisation (audit réduit, journaux expurgés) ;
  - les exports à l'initiative de l'utilisateur ;
  - la fenêtre de révocation.

## Notes de cadrage

- **Constats et lignes** : revue, §3.1 (journaux), §3.2 (lecture directe), §3.3 (écritures et
  envois), §3.4 (audit), §3.6 (chemins, révocation), §3.7 (décodage), §3.10 (bancs).
- **Lecture sans écriture déjà présente** : `ImapService.FetchSingleEmailAsync` →
  `ReadEmailWithoutPersistingAsync` (`:3261`, `:4649-4735`), `ReadFolderAsync`, `SearchIntoAsync`,
  `FETCH` des en-têtes (`:3213`).
- **Corrections de la version précédente de la task** :
  - `ImapFolderService.cs:126-139` est du code mort ; l'écriture vivante des dossiers est
    `ImapService.cs:490` ;
  - `ImapService.cs:504` est une **suppression** ;
  - il n'existe pas de route de déplacement de dossier.
- **Retiré par décision** : purge de l'existant, réécriture des traces d'audit passées.
- **Hors périmètre, tasks suivantes** :
  - affichage, gestes et scénarios e2e : task-398 ;
  - envoi « de la part de » : task-399 ;
  - traçabilité acteur / propriétaire : task-400 ;
  - HPRIM : task-389 et task-390.

## Branches

- `api-mail` (pushed) : feat/task-397-delegation-bal-lecture-directe — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-397-delegation-bal-lecture-directe
- Pré-flight 2026-10-25 : api-mail, client-blazor, client-mobile, dtos-mss, sdk sur `develop`. `host` (Host/Modules) et `interop` ne sont pas des racines de dépôt (noté, non bloquant, hors périmètre de la task).

## Timings

*(généré par `tools/timing/report.sh --task task-397 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| **Total cycle** | | **18 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

## Develop log

> Journal de progression (mis à jour à chaque tranche commitée — point de reprise en cas de compaction).

**Plan des tranches** (api-mail, branche `feat/task-397-delegation-bal-lecture-directe`) :

| # | Tranche | État |
|---|---|---|
| 1 | Règle de domaine `DelegatedMailboxRule` : prédicat, propriétaire, rôle, BAL identique, masquage de texte (clair et encodé) + tests unitaires | ✅ `c07a423f` — 45 tests |
| 2 | Banc de délégation : fragment Dovecot (`acl`, `imap_acl`, espace `shared`, `INDEXPVT`), `DovecotFixture` le monte, aide de délégation par `SETACL` IMAP | ✅ `44ba4947` — 3 tests de banc ; suite d'intégration complète inchangée (984/1000, 16 ignorés) |
| 3 | Masquage central des journaux (puits Serilog enveloppant : gabarit, propriétés, exception), `SanitizePath`, attribut OTel `email.folder`, étiquettes de verrou | ✅ `afd2a874` — 6 tests |
| 4 | Garde d'écriture : intercepteur EF (`SaveChanges`), méthodes `ExecuteUpdate`/SQL à chemin, décorateur de cache (clés + valeurs structurelles), filtre de publication MassTransit, test de convention | ✅ `85c5f500` — 6 + 10 + 5 tests ; convention prouvée rouge par 2 mutations |
| 5 | Synchronisation : prédicat à l'entrée de chaque mécanisme + journal « Skipped delegated folder » ; la synchro périodique liste l'espace partagé | ✅ `31f46721` (avec 7 partielle) — 3 tests de bout en bout, rouges par 3 mutations |
| 6 | Filtre MVC des politiques par route : refus (IA, accusés, étiquettes, annuler-remplacer, recherche, réglages), écritures hors ligne, chemin exact du `LIST` (alias, révocation 404 typée), dossiers système 409, création sous `shared`/système, déplacements inter-BAL 409 | ✅ `0cd0c4aa` — 5 tests de bout en bout + convention, rouges par 6 mutations |
| 7 | Lecture directe : liste des dossiers (propres en cache + délégués en direct), en-têtes / today / unread / recent, détail par `ReadEmailWithoutPersistingAsync` hors verrou, statut terminal, `HasMedicalDocuments` par structure, pièces jointes / zip / export, `STORE` direct | ✅ `31f46721` + `92da51b7` : liste, en-têtes, contenu (CDA décodé hors verrou), `STORE` direct, pièces jointes / zip / EML sans réécriture. Listes du jour non testées de bout en bout (fenêtre minuit, mémoire) |
| 8 | Corbeille du propriétaire (unitaire, groupée, définitive, sous-dossier) | ✅ `92da51b7` — avec déplacement interne à la BAL déléguée |
| 9 | Audit : liste blanche dans `AuditService.Trace` avant le tampon, `Message-ID` lu en direct | ✅ `97e18a13` — 1 test de bout en bout (8 familles) + 5 unitaires (dont le tampon), rouges par 6 mutations |
| 10 | Cache Redis du contenu délégué décodé (section J) + PDF du CDA servi depuis le cache | à faire |
| 11 | Caractérisation Mailiz, mesure, passe qualité, DoD | à faire |

**Constats et preuves (au fil des tranches)**

- **Banc** : sans `userdb`, Dovecot ne peut pas monter la BAL du délégant (« userdb reply doesn't contain uid ») ; le fragment ajoute une `userdb` statique alignée sur le banc. NAMESPACE range `shared/` dans le groupe **« autres utilisateurs »** : MailKit l'expose dans `OtherNamespaces`, pas `SharedNamespaces` — le code lit les deux.
- **Suites complètes après tranches 3-4** : domaine 240, infrastructure 701, API 1 297, application 3 636, intégration 984 réussis + 16 ignorés sur 1 000 — tout vert.
- **Mutations (test de convention)** :
  - 2026-10-25 — retrait de `AddInterceptors(DelegatedPersistenceInterceptor.Instance)` dans `BaseRepository` → `OnlyBaseRepositoryCreatesAPractitionerContext_AndItInstallsTheInterceptor` rouge ; restauré par copie, vert.
  - 2026-10-25 — retrait des deux gardes de `FolderRepository.RenameFolderAsync` → `EveryBulkUpdateWritingAPathIsGuarded` rouge (lignes 583, 587) ; restauré par copie, vert.
  - **Faux vert trouvé et corrigé** : la première version du scan cherchait `SetProperty(…FolderPath` sur **une** ligne ; l'appel réel s'écrit sur deux. La mutation est restée verte → regex multiligne sur la ligne d'appel et les deux suivantes. Leçon à consigner (`conventions/csharp.md`).
- **Tranche 5/7 (`31f46721`)** — tests de bout en bout `DelegationEndToEndTests` (vraie pile HTTP, base PostgreSQL du délégataire, Dovecot en délégation) :
  - `TheFolderList_…` : la liste rend la BAL de A, aucune ligne `MailFolders` sous `shared/`, une entrée « Skipped delegated folder » par dossier délégué (`by=FolderList`), aucun nom de sous-dossier dans le journal ;
  - `ReadingADelegatedMessage_…` : en-têtes et contenu lus en direct ; `HasMedicalDocuments` par la structure, statut `Enriched` (terminal), `ThreadCount = 1` ; CDA décodé (`DocumentTitle`, `BodyHtml`), `Id = Guid.Empty`, sans patient ; zéro ligne `Mails` / `MailMedicalDocuments` / `MailPatients` ;
  - `EnrichingADelegatedFolder_…` : `enrich/sync` → 200, `analysed = 0`, rien en base, une entrée `role=Inbox, by=Enrich`.
- **Mutations (2026-10-25)**, restaurées par copie + `touch` :
  - M1 — aiguillage de la lecture directe neutralisé (`GetEmailFromUidsAsync`, `GetEmailContentInternalAsync`) → `ReadingADelegatedMessage_…` rouge (`HasMedicalDocuments` faux) ;
  - M2 — sortie anticipée de `EnrichEmailsAsync` neutralisée → `EnrichingADelegatedFolder_…` rouge (503 : la garde d'écriture refuse l'enregistrement) ;
  - M3 — écart des dossiers délégués de la liste neutralisé → `TheFolderList_…` rouge (500 : la garde refuse la ligne `MailFolders`).
  - Première tentative invalide : `if (false)` ne compile pas (CS0162 en erreur) — une mutation qui ne compile pas n'est pas un rouge. Remplacé par une condition non constante.
- **Contrat modifié** : un succès du cache de la liste des dossiers ouvre désormais la session IMAP, pour relire **en direct** les espaces des BAL déléguées (règle B). La BAL propre reste servie par le cache, sans `LIST` ni `STATUS` (test `GetFoldersAsync_OnCacheHit_WithoutBackgroundQueue_…` ajusté en ce sens). Coût à mesurer en tranche 11 ; si la mesure montre une régression, piste : ne relire que pour un compte qui a des délégations.
- **Contenu délégué jamais mis en cache sous les clés du délégataire** : provenance `MailContentProvenance.DelegatedLiveRead`, exclue par `IsCacheable` (la garde de cache l'aurait refusé en 500). Le cache dédié arrive en tranche 10.
- **À traiter en tranche 9** : `EmailBuildingService.ProcessMedicalDocuments` trace `MedicalDocumentProcess` avec objet, INS et nom du patient — la liste blanche d'audit doit les vider pour un chemin délégué.
- **Tranche 6 (`0cd0c4aa`)** — `DelegatedMailboxPolicyFilter` (global) + `[DelegatedAccess]` sur les 35 actions à dossier ; une action muette **refuse** tout chemin délégué reçu (route, requête, corps) : recherche, conversation IA, envoi « annuler et remplacer », réglages sont fermés par défaut. `DelegatedMailboxPolicyException` (403 / 404 / 409, code `DELEGATED_*`, `type` dédié `urn:mss:problem:delegation-withdrawn`).
  - Tests de bout en bout : gestes refusés (résumé IA sans appel au faux fournisseur, accusés, étiquettes, brouillon annuler-remplacer) ; alias `shared/<A>/INBOX` et autre casse → 404 ; délégation retirée → 404 de type dédié ; `Sent` non renommable, racine non supprimable, création sous `shared` ou `Sent` → 409, intacts côté IMAP ; sous-dossier personnel créé puis renommé sans ligne `MailFolders` ; déplacements propre → délégué et délégué → propre → 409, rien ne bouge ; hors ligne → 403, `PendingActions` vide.
  - Convention : `DelegatedAccessDeclarationTests` (toute action à dossier déclare sa politique ; les gestes de la règle 14 sont `Refused`).
  - Mutations, toutes rouges : M4 refus neutralisé (404 « AI summary is not available » au lieu de 403) ; **M5 contrôle inter-BAL neutralisé → le déplacement d'un message propre vers la BAL de A RÉUSSIT (200)** : c'est le défaut que la règle G prévient ; M6 alias accepté → 500 ; M7 dossier système → 500 ; M8 hors ligne → 500 (la garde d'écriture refuse la ligne `PendingActions`) ; M9 attribut retiré de `GetEmailAsync` → convention rouge.
- **Constat de banc** : Dovecot refuse au délégataire la création d'un dossier **à la racine** de la BAL de A (`NO Permission denied`), malgré le droit `k` posé sur chaque dossier. Sous un dossier personnel (`Demo`), création et renommage passent. Ce que Mailiz permet à la racine est à **caractériser** (DoD, session humaine).
- **Arbitrage technique, tenu dans la règle 14** : le test `DashboardArrivalCostIntegrationTests` (task-273, propriété mesurée en charge) exige zéro aller-retour IMAP sur un second affichage du tableau de bord. La relecture en direct des BAL déléguées le cassait **pour tous les comptes**. Correctif : le marqueur `folder:no-delegation:{email}`, posé avec la liste des dossiers et pour la même durée, **seulement quand aucune BAL déléguée n'est vue**. Il ne porte qu'une absence ; un compte délégataire n'a rien en cache qui vienne de ses délégations, et relit l'espace partagé à chaque liste. Une délégation accordée pendant la vie du marqueur apparaît à l'expiration (5 min) ou par « Actualiser ».
- **Suites après tranche 6** : domaine 254, infrastructure 701, API 1 340, application 3 637, intégration 992 réussis + 16 ignorés sur 1 008 — tout vert.
- **Tranches 7 (fin) et 8 (`92da51b7`)** — 4 tests de bout en bout de plus (12 au total) :
  - `FlagsOnDelegatedMessages_…` : lu unitaire + suivi groupé, posés **avant la réponse** (la session du délégataire les voit aussitôt), `PendingActions` et `Mails` vides ;
  - `TheDelegatedFolderAndItsAttachments_…` : le dossier liste l'UID, la pièce jointe rend ses octets, zip et export EML en 200, zéro ligne `MailAttachments`, `Mails`, `MailFolders` ;
  - `DeletingInADelegatedMailbox_…` : suppression unitaire, groupée et d'un sous-dossier → **corbeille de A**, rien dans celle de B ; suppression depuis `shared/<A>/Trash` définitive ;
  - `MovingWithinTheDelegatedMailbox_Passes`.
- **Mutations** : M10 drapeau renvoyé vers la file → rouge ; M11 corbeille du délégataire → rouge ; M12 corbeille reconnue par attribut (Mailiz n'en pose pas) → rouge ; M14 sous-dossier vidé chez le délégataire → rouge. **M13 survivante, équivalente** : sans la condition, l'écriture en retour de la pièce jointe appelle `UpdateAttachmentAsync`, qui sort sans rien écrire faute de ligne `Mails` ; la condition n'évite qu'un aller-retour base. Gardée comme défense en profondeur.
- **Suites après tranche 8** : domaine 254, infrastructure 701, API 1 340, application 3 637, intégration 996 réussis + 16 ignorés sur 1 012 — tout vert.
- **Tranche 9 (`97e18a13`)** — `AuditService.Trace` applique la liste blanche dès qu'un chemin délégué figure dans `FolderPath` (« source -> cible » compris), avant le canal **et** avant le tampon Redis. `Message-ID` lu en direct dans la session du geste (`DelegatedEnvelopes.ReadMessageIdsAsync`) : drapeaux (même session que le `STORE`), suppression unitaire et groupée, déplacement unitaire et groupé ; pièce jointe et zip par les en-têtes en direct ; export par ses propres en-têtes ; décodage déjà porteur.
  - `EveryAuditedGestureOnADelegatedMailbox_…` (bout en bout) : ouverture d'un compte rendu de biologie, lu, suivi, pièce jointe, zip, export EML, déplacement, suppression → les 8 familles présentes, chacune avec le `Message-ID` du message et **aucun** objet, adresse, INS, nom de patient, document, requête, réponse ni erreur.
  - `AuditServiceDelegatedWhitelistTests` (unitaire) : dossier délégué, déplacement dans les deux sens, **trace passée par le tampon** (canal plein), et une trace propre intacte.
  - **Défaut réel trouvé** : l'export EML/PDF nommait le fichier par l'**objet** du message (`t397_piece_jointe.eml`), contre la décision 8. Corrigé : `email-{uid}`.
  - Mutations, toutes rouges : M15 liste blanche retirée (8/8 traces en défaut) ; M16 drapeaux sans `Message-ID` ; M17 suppression sans ; M18 déplacement sans ; M19 pièce jointe sans ; M20 export nommé par l'objet.
- **Flaky préexistant, hors périmètre** : `AnnuaireQuotaSharedRedisIntegrationTests.TwoInstances_SimultaneousSearches_NeverGetMoreThanTheBudgetPerSecondTogether` rouge une fois dans la suite complète (51 recherches pour un budget de 48 : le tir chevauche sans doute deux secondes), vert 3/3 en isolé. Ni le code de l'annuaire ni ce test ne sont touchés par la task.
- **Suites après tranche 9** : domaine 254, infrastructure 701, API 1 340, application 3 642, intégration 996 + 16 ignorés + 1 flaky (ci-dessus) sur 1 013.
