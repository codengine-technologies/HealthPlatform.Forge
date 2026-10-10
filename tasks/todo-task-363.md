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
  - La logique « événement et document » est extraite de
    `MSSanteImportService.ImportAttachmentInPatient`, sans dépendre de `T_MessageMSSante` (date,
    type et nom passés explicitement).
  - **Aucun changement de schéma.**
- **Gestionnaire `file-documents`** dans `Weda/FolderMedical/WedaEchanges/NovaMss/nova-mss-host.js` : il transforme les `ArrayBuffer` en `Blob`,
  les met dans un `FormData`, puis appelle `fetch`. Un `413` donne `payload-too-large`.

## Definition of Done

- [ ] Build passes (0 errors) sur client-angular et api-mail ; Tests pass (0 failures, hors flaky
  préexistants documentés)
- [ ] **Angular — tests de composant**, rouges d'abord :
  - [ ] l'action et la fenêtre ne sont rendues que si `available()` ;
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
- [ ] Partie Weda faite et validée (règle 11) : voir le Manual Test Plan

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail && dotnet run --project src/AppHost`) et weda2
   (`cd Client/Angular/front && .\serve-weda2.ps1`). Weda tourne en `https://localhost:44300`, dans
   un cabinet de test où `weda_integration` est active.
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
