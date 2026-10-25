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
- **Détail** : passe par `ReadEmailWithoutPersistingAsync`. Les lignes déjà en base pour ce chemin
  sont **ignorées**.
  - Le décodage CDA, XSLT et PDF se fait **hors du verrou** `imap_session`.
  - Les documents rendus portent un **identifiant non résolvable**, sans patient, ni doublon, ni
    version, ni demande de suppression.
- **Pièces jointes, zip, impression, export PDF / EML** : servis en flux depuis le serveur, sans
  réécriture `MailAttachments`.
- **Lu, non lu, drapeaux** (unitaires et groupés) : commande IMAP `STORE` directe. **Aucune**
  ligne `PendingActions` : on contourne la file de `FlagPropagationService`.
- **Enrichissement** : `enrich/async` **et `enrich/sync`** ne font rien sur un chemin délégué. Ils
  sortent avant toute lecture IMAP, réservation Redis, notification ou reprise IA, et répondent
  **200**.
- **Synchronisation en arrière-plan** : elle exclut explicitement l'espace partagé, au lieu de
  l'éviter par chance.

### C. Aucune écriture

Une **garde unique** refuse toute écriture ou mise à jour dont un chemin est délégué. Elle couvre :
- **les dépôts** de la base tenant, dont `PendingActions`, `UserSettings`, `MailAttachments`,
  `MailFolders` à la création et au renommage, et `MailTags` ;
- **le cache**, par un décorateur sur `IResilientCacheService`, qui contrôle aussi les **valeurs** :
  la liste des dossiers mise en cache ne contient aucun dossier délégué ;
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
        donnée de document délégués (inspection des clés et des valeurs) ;
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
- [ ] **Lecture** : le détail d'un compte rendu de biologie délégué renvoie le corps, les documents
      décodés, la valeur anormale signalée et un identifiant de document non résolvable. Les
      en-têtes ont un statut terminal. Lu dans la réponse réelle.
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
- [ ] **Synchronisation en arrière-plan** : test sur un banc où le conteneur partagé est
      sélectionnable, qui montre qu'elle n'y touche pas.
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
5. **Suppression.** Supprimer un message délégué : il est dans la Corbeille de Virginie, et son
   webmail Mailiz le confirme.
6. **Protection.**
   - Renommer les Envoyés de Virginie : refus.
   - Déplacer un message de sa boîte vers celle de Cyril : refus.
   - Créer, renommer un sous-dossier dans sa boîte : accepté.
7. **Refus.** Demander une synthèse IA ou envoyer un accusé de lecture sur un message délégué :
   refus clair, rien d'envoyé.
8. **Révocation.** Virginie retire la délégation dans le webmail Mailiz. Après au plus 5 minutes,
   l'accès à sa boîte est refusé avec le message « délégation retirée ».
9. **Non-régression.** Un compte rendu reçu dans la propre BAL de Cyril est traité comme avant.

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
