# todo-task-363.md — Intégration Weda : importer à la demande un document reçu dans le dossier patient Weda

**Repos**: client-angular, api-mail (catalogue e2e et profil e2e seulement)
**Dependencies**: done-task-357 (panneau « Dossier Weda »), task-362 (boîte désignée, faux hôte de test)
**Epic**: E019
**Single frontend**: true — seul weda2 (client-angular) est embarqué dans Weda. Blazor et mobile
n'ont pas d'hôte Weda (raison fonctionnelle).
**Priorité**: **1** — c'est désormais tout le périmètre de l'intégration (ADR-007, amendement 3,
B2), et la valeur de RG-E009-034 : « visualiser et classer en 1 clic dans le dossier patient ».

> **Origine.** Décision de l'humain du 2026-10-10, consignée dans l'amendement 3 de l'ADR-007 (dépôt
> Weda) et de l'ADR client :
> - l'intégration se limite à **l'import des documents à la demande du médecin** ;
> - WMickey garde la réception, la biologie et HPRIM (coexistence).
>
> Cette tâche remplace task-360 (en attente, `tasks/onhold/`). task-360 classait par identifiants,
> par un canal serveur Weda → api-mail, qui est abandonné.
>
> Elle reprend aussi la **couverture e2e du panneau « Dossier Weda »**. Le PO l'avait reportée de
> task-357 à task-360 le 2026-10-10 (`questions/answered/task-357.md`), et task-360 est en attente.

## Ce qui existe (constaté dans le code le 2026-10-10)

- **client-angular** :
  - `MSS_PATIENT_RECORD_GATEWAY.fileDocuments()` relaie `file-documents` à l'hôte, avec transfert
    d'`ArrayBuffer` et un délai de 120 s (task-356). `IWedaFilingPart` porte `content: ArrayBuffer`.
  - Le panneau `mss-weda-patient-panel` (task-357) montre le dossier trouvé par INS vérifiée, ou des
    candidats par traits, et « Ouvrir le dossier ». Il n'apparaît que pour un message qui porte un
    document médical. `getFilingContext()` rend les destinations, les classifications et les
    destinataires possibles d'un post-it.
  - `MssApiService.downloadAttachment(folder, uid, fileName)` rend les octets d'une pièce jointe,
    **et aussi le PDF d'un document CDA** (`MailMedicalDocumentDto.pdfFileName`, utilisé par
    `mail-body.component.ts` › `loadPdf`). `exportMailAsPdf(folder, uid)` rend le message en PDF.
  - `MailMedicalDocumentDto.loinc` porte le code du document CDA.
  - **À retirer** (ADR client, amendement 3) : `getFilingStatus`, `IWedaFilingEntry`,
    `MAX_FILING_STATUS_MESSAGE_IDS`, et le type de demande `get-filing-status`.
- **Weda** (hors forge) :
  - `We.aspx.cs` › `ImportMessageDocuments` est le classement de l'ancien écran. Il crée, pour
    chaque pièce :
    - un événement et un document (`MSSanteImportService.ImportAttachmentInPatient` : destination,
      titre, commentaire, classification `glossaireId`) ;
    - le corps en PDF ;
    - un post-it (`PostIt` et `PostItRead`) ;
    - et il appelle `CreateIns`.
  - Tout dépend d'une ligne `T_MessageMSSante`, que les messages d'api-mail n'ont pas.
  - `resolve-patient` cherche par INS vérifiée, ou par nom et prénom (date de naissance
    facultative).
- **WMickey** : un CR de biologie est reconnu par le gabarit XD-LAB `1.3.6.1.4.1.19376.1.3.3`
  (`CdaImporterFactory`). Un message HPRIM est reconnu par son objet, qui contient `HNET.1/MSG/`
  (`Message.WithHprimAttachment`).

## Objective

**client-angular** : rien de ce qui suit n'est rendu ni lancé si
`MSS_PATIENT_RECORD_GATEWAY.available()` est faux.

1. **« Importer dans Weda »** : une action du message, présente dès qu'il a quelque chose à
   importer. Elle ouvre une fenêtre d'import :
   - **le patient** :
     - celui trouvé par INS vérifiée est présélectionné ;
     - sinon, le praticien **choisit explicitement** un candidat ;
     - sinon, il fait une recherche manuelle : nom et prénom, date de naissance facultative, par le
       `resolve-patient` existant. Le contrat ne change pas ;
     - sans patient choisi, l'import est impossible. **Aucune création de patient** ;
   - **les documents**, en cases à cocher :
     - le PDF de chaque document CDA (`pdfFileName`), coché par défaut ;
     - chaque pièce jointe, cochée par défaut, sauf l'enveloppe IHE_XDM ;
     - le message lui-même en PDF, non coché par défaut ;
     - un CDA sans PDF n'est pas proposé en v1 ;
   - **pour chaque document coché** : un titre (le titre du CDA, le nom du fichier, ou « MSSanté -
     {nom} ({adresse}) » pour le message), une destination (Consultation, Examen ou Courrier, avec
     le défaut de `get-filing-context`), une classification et un commentaire ;
   - **un post-it facultatif** : message, niveau et destinataires.
2. **« Importer »** lit les octets (`downloadAttachment` ou `exportMailAsPdf`), puis envoie
   `file-documents` :
   `{ messageId, sentAt, sender, subject, patientId, parts: [{ part, fileName, contentType, content,
   title, destination, classificationId, comment }], postIt? }`.
   - `part` vaut `body` ou `attachment-{rang}`.
   - Les `ArrayBuffer` sont **transférés**, jamais copiés en base64.
3. **Après l'import** :
   - un message de succès : « {n} document(s) importé(s) dans le dossier patient. » ;
   - **le message ne bouge pas** : ni corbeille, ni déplacement, ni mot-clé (ADR-007, B4). WMickey
     ne lit que l'INBOX ;
   - rien n'est mémorisé : un second import reste possible, comme dans l'ancien écran ;
   - une erreur du pont (`forbidden`, `not-found`, `payload-too-large`, `timeout`,
     `weda-session-expired`, `server-error`) donne un message clair, sans détail technique. Pour
     `payload-too-large` : « Documents trop volumineux pour un seul import : importez-les
     séparément. »
4. **Biologie** (ADR-007, B5) :
   - **aucune action d'import** pour un message qui contient un document de code LOINC `11502-2`,
     ou dont l'objet contient `HNET.1/MSG/` ;
   - à la place, une information fixe : « Les résultats de biologie sont intégrés par Weda dans la
     bannette des résultats. »
5. **Nettoyage** des types et méthodes obsolètes listés plus haut.
6. **Faux hôte de test** (créé par task-362). Il répond aussi à `resolve-patient`,
   `get-filing-context`, `open-patient-record` et `file-documents`. Pour `file-documents`, il garde
   seulement le nombre de pièces, leurs types et leurs tailles, **jamais leur contenu**.

**api-mail** : le profil e2e (`E2eProfile`) active `weda_integration`, et le catalogue reçoit le
scénario E2E-WEDA-002. Aucune route ne change.

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est nécessaire pour que la tâche soit complète (règle 11).

> **Repère `nova-mss`** (ADR-007, amendement 4) : tout le code Weda de cette partie vit sous
> `Weda/api/NovaMss/` (namespace `Weda.api.NovaMss`, classes préfixées `NovaMss`, route
> `api/nova-mss`) ou sous `Weda/FolderMedical/WedaEchanges/NovaMss/` (préfixe DOM et CSS `nova-mss-`).
> Chaque fichier porte l'en-tête `nova-mss — …`. **Aucun fichier Mickey ou de l'ancien écran n'est
> modifié** : une règle à reprendre est **copiée** dans `NovaMss`, avec un commentaire qui cite sa
> source. Hors de ces dossiers, seuls changent `Weda.csproj` et, au besoin, l'inclusion dans
> `Default.aspx`.
>
> **Périphérique « Expérience Nova » (9892, `HasNovaMss`), déjà livré** (ADR-007, amendement 5) : sans lui,
> rien ne s'exécute. `NovaMssHost.ascx` n'est pas rendu, et toute route `api/nova-mss` répond `403` par
> `[NovaMssEnabled]`, posé sur `NovaMssController` : une nouvelle route en hérite, rien à ajouter. Seule
> exception écrite à la règle : les ajouts du périphérique dans `GlobalConstantes`, `Peripherique`,
> `CustomPrincipal` et les trois écrans d'administration.

- **`POST /api/nova-mss/documents`** (multipart), dans `NovaMssController` (repère `nova-mss`, ADR-007 amendement 4) :
  - `[Authorize]`, `HasWmss` exigé, refusé à un secrétaire ;
  - le patient doit appartenir au cabinet de la session ;
  - taille et type des fichiers : les limites de l'ancien écran (`We._MAX_FILE_SIZE`) ;
  - pour chaque partie :
    - un événement à la date du message, du type de la destination ;
    - un document : titre, classification, commentaire, vignette pour une image ;
  - le post-it, comme `ImportMessageDocuments` ;
  - **ni `CreateIns`, ni trace INS, ni création de patient** ;
  - rend `{ results: [{ part, fileStreamId }] }`.
  - La logique « événement et document » est **copiée** de
    `MSSanteImportService.ImportAttachmentInPatient` dans `Weda/api/NovaMss/NovaMssDocumentImporter.cs`,
    sans dépendre de `T_MessageMSSante` (date, type et nom passés explicitement). La création du post-it
    est copiée de `We.aspx.cs` › `ImportMessageDocuments`. **`MSSanteImportService` et `We.aspx.cs`
    ne sont pas modifiés** : le commentaire de la classe cite les deux sources, à garder alignées.
  - **Aucun changement de schéma.**
- **Gestionnaire `file-documents`** dans `Weda/FolderMedical/WedaEchanges/NovaMss/nova-mss-host.js` : il transforme les `ArrayBuffer` en `Blob`,
  les met dans un `FormData`, puis appelle `fetch`. Un `413` donne `payload-too-large`.

## Definition of Done

- [ ] Build passes (0 errors) sur client-angular et api-mail ; Tests pass (0 failures, hors flaky
  préexistants documentés)
- [ ] **Angular — tests de composant**, rouges d'abord :
  - [ ] l'action et la fenêtre ne sont rendues que si `available()` ;
  - [ ] `available()` faux (flag `weda_integration` coupé, hors iframe, ou hôte incompatible) :
    **aucun appel** n'est émis — ni `downloadAttachment`, ni `exportMailAsPdf`, ni `file-documents` ;
  - [ ] `available()` faux : l'information fixe sur la biologie n'est pas affichée non plus ;
  - [ ] la liste des documents : PDF des CDA et pièces cochés, enveloppe IHE_XDM jamais proposée,
    message en PDF proposé et non coché ;
  - [ ] la demande `file-documents` porte exactement les documents cochés, avec leur titre,
    destination, classification et commentaire, le patient choisi et le post-it ; chaque `content`
    est dans la liste de transfert ;
  - [ ] un candidat doit être choisi explicitement : rien n'est présélectionné sans résultat par
    INS ; la recherche manuelle envoie nom, prénom et date de naissance à `resolve-patient` ;
  - [ ] un message de biologie (LOINC `11502-2`) ou HPRIM (`HNET.1/MSG/`) n'offre pas l'import et
    affiche l'information fixe ;
  - [ ] après un import réussi, aucun appel ne déplace, ne supprime ni ne marque le message ;
  - [ ] chaque erreur du pont donne son message, sans détail technique.
- [ ] **Angular** : les types et méthodes obsolètes sont retirés. Une recherche de
  `getFilingStatus`, `IWedaFilingEntry` et `MAX_FILING_STATUS_MESSAGE_IDS` ne donne plus rien, et
  c'est consigné dans la revue.
- [ ] Scénario **E2E-WEDA-002**, version 1, ajouté dans `Api/Mail/e2e/scenarios.yml` :
  - titre : « Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des
    documents dans un dossier » ;
  - attendu :
    - sous un message qui porte un document médical, le panneau « Dossier Weda » montre le dossier
      trouvé ou les correspondances « à vérifier », et « Ouvrir le dossier » envoie la demande
      d'ouverture à l'hôte ;
    - « Importer dans Weda » importe la pièce jointe et le message en PDF dans le dossier choisi :
      l'hôte reçoit les documents, et le message reste dans la boîte de réception ;
    - un compte rendu de biologie n'offre pas l'import, et affiche l'information fixe ;
  - clients : `angular: requis`, `mobile: non-applicable — l'application mobile n'est pas embarquée
    dans Weda` ;
  - seed : `boite-praticien`, `cda-sans-ins-a-rattacher`, `mail-avec-pj`, `cr-bio-a-acquitter` ;
  - implémenté dans client-angular avec le faux hôte. Le profil e2e d'api-mail active
    `weda_integration`.
- [ ] `data-testid` sur l'action, la fenêtre, chaque case de document, les listes, la recherche
  manuelle, l'information sur la biologie, et les boutons Importer et Annuler ; libellés FR en dur
- [ ] Aucune donnée de santé dans les journaux : ni INS, ni nom de patient, ni contenu de pièce
- [ ] **Weda — repère `nova-mss`** : `git diff --stat` de la partie Weda ne montre que des fichiers sous
  `NovaMss/`, plus `Weda.csproj` (et l'inclusion dans `Default.aspx`). Aucun fichier sous
  `Weda/api/WMickey/`, `WMickey/` ou `WedaGlobal/WCommunication/` n'est modifié.
- [ ] **Weda — périphérique** : sans « Expérience Nova », `POST api/nova-mss/documents` répond `403`, et
  le bandeau n'apparaît pas dans Échanges.
- [ ] Partie Weda faite et validée (règle 11) : voir le Manual Test Plan

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail && dotnet run --project src/AppHost`) et weda2
   (`cd Client/Angular/front && .\serve-weda2.ps1`). Weda tourne en `https://localhost:44300`.
   Prérequis :
   - l'utilisateur a, dans son cabinet, le périphérique Weda « Expérience Nova » (9892) et une boîte
     MSSanté V2 ;
   - dans Flagsmith, `weda_integration` est activé pour l'**identité de la boîte que Weda désigne**
     (le flag est évalué par identité, sur la boîte ouverte, pas par cabinet).
2. Dans Échanges (nouvelle expérience), ouvrir un courrier avec un PDF joint, dont le patient est
   connu de Weda par INS. « Importer dans Weda » présélectionne ce patient.
3. Importer le PDF en « Courrier », avec une classification et un commentaire. Le document apparaît
   dans le dossier du patient, à la date du message, avec la bonne destination et la bonne
   classification.
4. Le message est **toujours dans la boîte de réception**, dans weda2 comme dans un client IMAP de
   test.
5. **Lettre de liaison (CDA dans une enveloppe IHE_XDM)** : le PDF du CDA est proposé et s'importe ;
   l'enveloppe n'est pas proposée.
6. **Message en PDF** : le cocher, l'importer. Le PDF du message est dans le dossier.
7. **Sans INS** : choisir un candidat, ou faire une recherche manuelle, puis importer. Le document
   est dans le dossier choisi, et aucun patient n'a été créé.
8. **Post-it** : en ajouter un pour un confrère. Il le voit sur le dossier.
9. **CR de biologie** : pas d'action d'import, et l'information fixe s'affiche. Le CR arrive en
   bannette par WMickey, comme avant.
10. **Trop volumineux** : importer plusieurs gros fichiers ensemble. Le message invite à les importer
    séparément.
11. Dans les journaux du navigateur et du serveur Weda : ni INS, ni nom de patient.
12. **Flag coupé** : désactiver `weda_integration` pour cette identité, puis recharger Échanges. weda2
    s'affiche toujours, mais ni l'action « Importer dans Weda », ni l'information sur la biologie
    n'apparaissent. Dans l'onglet Réseau, aucune demande d'import n'est envoyée à l'hôte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : RG-E009-034 (MSS/va1.28), « visualiser et classer en 1 clic dans le
  dossier patient ». Elle passe de 🟡 partiel à couvert pour les pièces jointes, les PDF des
  documents CDA et le message lui-même.
- **INS** : l'import vise un **dossier existant**. Ce dossier est trouvé par **INS vérifiée**, ou
  choisi explicitement par le praticien, parmi les candidats ou par une recherche manuelle. C'est
  **une proposition, pas un rapprochement automatique** (identito-vigilance). **Aucune identité
  n'est créée ni modifiée**, donc aucun appel INSi et aucune création d'INS.
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel. Les pièces sont lues par la
  session du praticien dans api-mail, puis remises à Weda par sa session Weda.
- **Habilitations** : Weda vérifie côté serveur que le patient appartient au cabinet de la session.
  La boîte est celle que Weda désigne (task-362).
- **Interop CI-SIS** : les documents sont importés tels que reçus (PDF du CDA, pièce jointe). Pas de
  transformation de CDA.
- **Tracé PGSSI-S** :
  - la lecture des pièces est tracée dans le journal d'audit d'api-mail (route de téléchargement
    existante) ;
  - l'import est tracé dans Weda comme un classement de l'ancien écran (document créé, auteur,
    date).
- **Consentement patient** : non applicable — import d'un document reçu dans le dossier que tient
  le professionnel destinataire
- **Référentiels métier** : aucun (classifications propres au cabinet)
- **Hébergement HDS** : oui. Les pièces passent d'api-mail à Weda par le navigateur du praticien, en
  HTTPS, entre deux services hébergés. Elles sont stockées dans Weda comme aujourd'hui.
- **AIPD / impact RGPD** : inchangé, même finalité que le classement de l'ancien écran

## Branches
- `api-mail` (pushed) : feat/task-363-weda-import-documents — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-363-weda-import-documents
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au /start : `feature/nova-rewriting-mss-weda-integration`) — humain gère branche, commit, push, PR TFS
- Partie Weda : hors forge, faite par l'humain (règle 11)

## Develop log

- Repos touched : `api-mail` (profil e2e et catalogue), `client-angular` (code-only)
- DTOs published : no DTO change — Interop published : no interop change
- Commits :
  - api-mail : `2aff4aff` test(e2e): add E2E-WEDA-002 and force weda_integration in the e2e profile
    - `E2eProfile.ForcedFeatureFlags` ajoute `weda_integration` (via `FeatureFlags:ForcedOn`,
      refusé en Production). `ForcedOnFeatureFlagService` couvre aussi la lecture par identité
      (`GetAllFeaturesAsync(userIdentifier)`), celle de weda2. Aucune route ne change.
    - Tests `ForcedFeatureFlags_IncludeWedaIntegration` (vu **rouge** avant le correctif) et
      `ForcedFeatureFlags_AreAllKnownFlags` : un nom inconnu n'est qu'un avertissement, une
      faute de frappe éteindrait le flag en silence.
    - Catalogue : E2E-WEDA-002 v1 (angular `requis`, mobile `non-applicable`), seed
      `boite-praticien`, `cda-sans-ins-a-rattacher`, `mail-avec-pj`, `cr-bio-a-acquitter`.
  - client-angular : **non commité** (code-only) sur `feature/nova-rewriting-mss-weda-integration`.
    **À commiter sur TFS avant le merge de la PR api-mail** (E2E-WEDA-002 est `requis` côté angular).
    - `libs/mss/src/features/mail/components/weda-import/` (nouveau) : `weda-import.component.{ts,html,scss}`
      + spec (25 tests), `weda-import.utils.ts` + spec (16 tests). Rendu et appels seulement si
      `available()`. Patient présélectionné par INS vérifiée, sinon choix explicite d'un candidat ou
      recherche manuelle (nom, prénom, date de naissance facultative, `resolve-patient` inchangé).
      Documents : PDF des CDA et pièces jointes cochés, enveloppe IHE_XDM jamais proposée, message
      en PDF non coché. Titre, destination, classification et commentaire par document. Post-it
      facultatif. Octets lus par `downloadAttachment` / `exportMailAsPdf`, puis `file-documents`
      (le transfert des `ArrayBuffer` est fait par la passerelle weda2). Message de succès « {n}
      document(s) importé(s) dans le dossier patient. ». Aucun appel ne déplace, supprime ni
      marque le message, et rien n'est mémorisé. Une erreur du pont donne son message, sans détail.
      Biologie (LOINC `11502-2`) ou HPRIM (`HNET.1/MSG/`) : pas d'action, information fixe.
    - `mail-detail.component.{ts,html}` : `<mss-weda-import>` sous le panneau « Dossier Weda ».
    - Nettoyage (ADR client, amendement 3) : `getFilingStatus`, `IWedaFilingEntry`,
      `MAX_FILING_STATUS_MESSAGE_IDS`, `get-filing-status` et `WedaFiledBy` retirés. Une recherche
      sur `apps`, `libs` et `e2e` ne donne plus rien. `IWedaFilingResult` est aligné sur le contrat
      de l'amendement 3 (`{ results: [{ part, fileStreamId }] }`).
    - **Contrat du pont, ajout optionnel** : `IWedaFilingContext.postItLevels?` (les niveaux de
      post-it sont des libellés de Weda, table de configuration 70, et pas une liste fixe).
      Absent, weda2 envoie le niveau 0, celui de l'exemple de l'ADR. **Côté Weda (hors forge) :
      renseigner `postItLevels` dans `get-filing-context`.**
    - Faux hôte e2e (`e2e/mss-e2e/support/weda-host.ts`) : il répond aussi à `resolve-patient`
      (dossiers synthétiques « à vérifier » sur toute recherche par nom), `get-filing-context`,
      `open-patient-record` et `file-documents`. D'un import, il ne garde que le nombre de pièces,
      leurs types et leurs tailles, jamais leur contenu.
    - `e2e/mss-e2e/specs/functional.e2e.ts` : E2E-WEDA-002 v1, qui couvre le panneau (reprise de
      task-357/360), l'ouverture, l'import, le message toujours en INBOX relu à une nouvelle entrée,
      et la biologie.
- Local build / test :
  - client-angular : `nx build weda2` ✓, `nx run-many -t test` ✓ (11 projets). Specs touchées
    rejouées après Prettier : 64 + 85 ✓. `tsc` e2e ✓, `eslint` sur les fichiers touchés : 0 erreur.
    Fichiers neufs et fichiers propres en HEAD formatés. `mail-detail.component.html`, non
    conforme en HEAD, n'est pas reformaté.
  - Un premier build est sorti **rouge** sur une erreur que vitest ne voit pas : le typage strict
    du gabarit refusait un `number` pour `WedaDestination` (TS2322). Corrigé par
    `setDestination()`.
  - api-mail : l'AppHost de développement de l'humain tournait et verrouillait `src/Api/bin`
    (5 × `mss.mail.api`). Je ne l'ai pas arrêté. J'ai compilé dans `Api/Mail/artifacts/forge-363`,
    **dans le dépôt** et gitignoré : la convention ne vise que les artefacts *hors* du dépôt.
    Résultats : domain 190, infrastructure 683, api 1 188, application 3 569 ✓ ; integration 836
    ✓ et **2 ✗ préexistants**.
  - Ces 2 ✗ sont `SemanticSearchRepositoryIntegrationTests` (« different vector dimensions 3 and
    1536 », effet d'ordre de la suite). Verts en isolation (24/24), rouges dans la suite complète,
    **et rouges aussi sur `origin/develop` pur**, compilé dans `bin` dans un worktree jetable
    (avec en plus `AuditJournalIntegrationTests.Le_maintien_des_partitions…`). Ils ne viennent pas
    de task-363 (seule une constante de l'AppHost change). Le worktree est supprimé.
- Preuve par mutation (unitaires, code restauré, `grep -c MUTATION` = 0) :
  - MU1 disponibilité ignorée → « renders neither … when available() is false » rouge ;
  - MU2 biologie non reconnue → 4 rouges (utilitaire et composant, LOINC et HPRIM) ;
  - MU3 enveloppe XDM proposée → 5 rouges ;
  - MU4 candidat présélectionné → « preselects nothing … chosen explicitly » rouge ;
  - MU5 message déplacé après l'import → « … leaves the message where it is » rouge ;
  - MU6 erreurs génériques → les 5 codes rouges, côté utilitaire et côté composant ;
  - MU7 post-it toujours envoyé → « sends no post-it unless one is written » rouge.
- **Preuve par mutation e2e d'E2E-WEDA-002**, soldée pendant `/e2e`, en `--serve-only`. Avant
  chaque jeu : nouveau bundle servi et 0 `[ERROR]`. Après : code restauré, `grep -c MUTATION` à 0.
  Vert de contrôle après restauration.
  - ME3 import jamais envoyé → rouge sur « l'hôte a reçu un import » (0 au lieu de 1).
  - ME4 biologie non reconnue → rouge sur « l'information fixe sur la biologie s'affiche ». Le
    1er essai était **invalide** : la mutation ne compilait pas (TS6133) et l'ancien bundle était
    servi. Rejoué valide.
  - ME5 ouverture du dossier sans effet → rouge sur « « Ouvrir » envoie la demande d'ouverture ».
  - ME6 l'import supprime le message → rouge sur « le message importé est toujours dans la boîte
    de réception ». Le 1er essai était **invalide** : l'ancre ne correspondait plus (ligne coupée
    par Prettier), le code n'était pas muté et le jeu était vert. Rejoué valide sur un banc
    remonté.
  - Les deux essais invalides sont consignés en récidive dans `conventions/e2e.md`
    (`mutation-non-servie`, occurrence 4).
- **E2E-WEDA-002 : non joué pendant `/develop`.** Le port 5052 (AppHost) et le port 4200
  (`nx serve`) sont tenus par les serveurs de développement de l'humain. Type-check vert. La
  preuve par mutation e2e est à faire au premier passage de `/e2e`.
- Passe qualité (/simplify) : revue manuelle sur le diff (réutilisation de `patientIdentitiesOf`
  et `formatIsoDate` du panneau, fonctions pures dans l'utilitaire, mail-detail touché de 4
  lignes). Aucun nettoyage restant, donc aucune re-validation. api-mail : rien à simplifier.
- Partie Weda (hors forge, règle 11), **à faire par l'humain** :
  - `POST /api/nova-mss/documents` ;
  - gestionnaire `file-documents` de `nova-mss-host.js` (`413` → `payload-too-large`) ;
  - `postItLevels` dans `get-filing-context`.
- DOD self-check :
  - tests de composant ✓ (9 lignes) ;
  - nettoyage ✓ (recherche vide) ;
  - catalogue E2E-WEDA-002 v1 ✓ ;
  - profil e2e ✓ ;
  - `data-testid` ✓ ;
  - libellés FR ✓ ;
  - aucune donnée de santé dans les journaux ✓ (aucun `console.*` dans le code ajouté) ;
  - différés : parcours e2e joué (`/e2e`), partie Weda, périphérique et Manual Test Plan (HAG).
- Next step : `/sonar task-363`

## Sonar log

- **Skipped** : aucun code de production analysable dans le diff api-mail. Il contient :
  - `src/AppHost/E2eProfile.cs`, exclu du scan (`sonar.exclusions` contient `**/AppHost/**`) ;
  - 2 tests (`E2eProfileTests`), avec assertions ;
  - le catalogue `e2e/scenarios.yml`.
- Le build du scan aurait de plus visé `src/Api/bin`, verrouillé par l'AppHost de développement
  de l'humain. KPIs inchangés, aucune analyse lancée.

## Lint log

- Commande : `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss`
  (12 projets exécutés).
- Baseline : **0 erreur**, avertissements seuls (`jsdoc/require-example` surtout ; 47 sur
  `mss-lib`, contre 42 avant la task, soit les exemples de JSDoc des nouveaux fichiers).
- Itérations : 0. Aucun `--fix` (WIP humain préservé). Aucune modification, donc pas de
  re-build.
- Conventions : aucune règle corrigée à la main, donc `conventions/angular.md` inchangé.

## Timings

*(généré par `tools/timing/report.sh --task task-363 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| /develop | ok | 30 min 56 s | 2 (30 s) | 7 (8 min 54 s) | — | api-mail 0B/6T, client-angular 2B/1T, e2e non joué : 5052/4200 tenus par les serveurs de l'humain ; 2 rouges d'intégration préexistants (aussi sur develop) |
| /sonar | skipped | 8.0 s | — | — | — | aucun code de production analysable : AppHost exclu du scan, reste = tests et catalogue |
| /lint-angular | ok | 20 s | — | — | — | baseline 0 erreur (warnings seuls), aucun fix |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non listé ni touché |
| /e2e | ok | 25 min 47 s | — | — | — | e2e ×3 (11 min 02 s), porte verte ; WEDA-002 vert au 1er passage ; mutations e2e ME3-ME6 (2 essais invalides rejoués) |
| /review | ok | 4 min 55 s | 2 (40 s) | 2 (4 min 07 s) | — | api-mail 1B/1T, client-angular 1B/1T, APPROVED ; api-mail 1B/1T (bin), client-angular 1B/1T ; PR #286 (awaiting-human-merge) ; client-angular code-only |
| /tech-writer | ok | 1 min 15 s | — | — | — | — |
| **Total cycle** | | **1 h 03 min** | **4 (1 min 11 s)** | **9 (13 min 01 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (11 s)

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 31 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 45 s |
| angular | api-mail + client-angular touchés | ✅ verte à la porte | 32 verts, 0 flaky, 1 rouge **en quarantaine** (E2E-COMPOSE-002, task-350) | 5 min 17 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-363-weda-import-documents`, `2aff4aff`)
- **E2E-WEDA-002 vert dès son premier passage** (5,1 s). E2E-WEDA-001 vert.
- Quarantaines : E2E-COMPOSE-002 (angular), posée le 2026-10-09 (1 jour), correction task-350.
- Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun. `mail-detail` et le nouveau composant sont
  couverts par E2E-WEDA-002.
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).
- Historique de l'étape :
  - 1er passage **bloqué en outillage** : ports 5052 et 4200 tenus par les serveurs de
    développement de l'humain (`questions/task-363.md`) ;
  - relancé par l'humain une fois les ports libérés ;
  - magasin DCP élevé purgé avant le run, à titre préventif (`migrate.lock` de 0 octet, voir la
    mémoire DCP).
- Preuve par mutation d'E2E-WEDA-002 (dette de `/develop`, soldée ici en `--serve-only`) : voir le
  Develop log.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Failed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ❌ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/286 — label `awaiting-human-merge`
- `client-angular` (code-only) : l'humain gère le commit, le push TFS et la PR. Branche
  `feature/nova-rewriting-mss-weda-integration`. **À commiter avant le merge de la PR #286**
  (E2E-WEDA-002 requis côté angular). Fichiers :
  - `front/apps/weda2/src/lib/embedded/embedded-host.model.ts`
  - `front/apps/weda2/src/lib/embedded/weda-patient-record.gateway.ts` + `.spec.ts`
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/weda-host.ts`
  - `front/libs/mss/src/core/models/weda-patient-record.model.ts`
  - `front/libs/mss/src/core/tokens/mss-patient-record-gateway.token.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.{ts,html}`
  - `front/libs/mss/src/features/mail/components/weda-import/` (nouveau : composant, gabarit,
    styles, utilitaire et leurs specs)
- Partie Weda (hors forge) : à faire par l'humain (règle 11), validée par le Manual Test Plan.

## Code Review Summary

**Verdict : APPROVED**, 0 bloquant, 4 suggestions.

| Repo | Build | Tests | Re-validation `/review` |
|---|---|---|---|
| api-mail | ✓ 0 erreur (dans `bin`) | ✓ domain 190, infrastructure 683, api 1 188, application 3 569, integration 838 (+16 skip), 0 échec | les 2 rouges d'intégration de `/develop` ont disparu (voir plus bas) |
| client-angular | ✓ `nx build weda2` | ✓ 11 projets, 0 échec | — |

- **Règle 1b** : côté api-mail, seule une constante de profil AppHost et le catalogue changent,
  aucun endpoint. Le parcours frontend est prouvé par E2E-WEDA-002 sur le vrai backend : vert,
  et rouge sous ME3 (import jamais envoyé), ME4 (biologie non reconnue), ME5 (ouverture sans
  effet) et ME6 (le message supprimé par l'import).
- **DOD** :
  - ✓ les 9 lignes de tests de composant ;
  - ✓ nettoyage (recherche de `getFilingStatus`, `IWedaFilingEntry` et
    `MAX_FILING_STATUS_MESSAGE_IDS` vide sur `apps`, `libs` et `e2e`) ;
  - ✓ E2E-WEDA-002 v1, au catalogue et dans la suite ;
  - ✓ profil e2e ;
  - ✓ `data-testid` (action, fenêtre, cases, listes, recherche, information biologie, boutons) ;
  - ✓ libellés FR ;
  - ✓ aucun journal ajouté ;
  - différés au HAG : partie Weda, repère `nova-mss`, périphérique et Manual Test Plan.
- **Rouges d'intégration de `/develop`** (`SemanticSearchRepositoryIntegrationTests`,
  « different vector dimensions 3 and 1536 ») :
  - rouges trois fois, avec l'AppHost de développement de l'humain démarré : deux fois sur la
    branche, une fois sur `develop` pur ;
  - verts ici, une fois l'AppHost arrêté.
  - C'est une **corrélation, pas une cause prouvée** : le Postgres de développement est partagé.
    Consigné en mémoire de session.
- Revue par fichier (client-angular) :
  - `weda-import.component.ts` ✅ :
    - rien n'est rendu ni appelé sans `available()` ;
    - présélection par INS seulement ;
    - lecture des octets par l'API existante ;
    - aucun appel sur le message après l'import ;
    - erreurs traduites sans détail technique ;
    - méthodes courtes, JSDoc complet.
  - `weda-import.utils.ts` ✅ : fonctions pures (biologie, documents proposés, titres, erreurs).
  - Nettoyage gateway, modèle et token ✅ : `IWedaFilingResult` aligné sur l'amendement 3.
  - `weda-host.ts` (e2e) ✅ : il ne garde d'un import que le nombre, le type et la taille des
    pièces.
- ⚠️ Suggestions (non bloquantes) :
  1. **Préparation partielle** : si `resolve-patient` échoue pour une identité, toute la
     préparation est signalée en échec, alors que le contexte de classement a pu arriver.
     Piste : traiter les deux appels séparément.
  2. **Plusieurs patients dans un message** : le premier patient trouvé par INS est
     présélectionné pour tous les documents cochés. Le praticien peut décocher, mais une
     confirmation visible serait plus sûre.
  3. **Post-it sans destinataire** : il part si le message est rempli. À valider avec la règle de
     l'ancien écran côté Weda.
  4. **`sentAt` vide** si le message n'a pas de date : Weda daterait alors l'événement par
     défaut. À vérifier dans le contrôleur `nova-mss`.
