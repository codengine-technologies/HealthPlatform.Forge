# todo-task-367.md — Intégration Weda : un envoi lancé depuis le dossier patient ouvre la rédaction de la nouvelle messagerie, et api-mail emballe le document en IHE_XDM

**Repos**: dtos-mss, api-mail, client-angular
**Dependencies**: task-366 (enveloppe IHE_XDM d'Interop), done-task-362 (boîte désignée, faux hôte),
done-task-363 (import, transfert d'octets par le pont)
**Epic**: E019
**Single frontend**: true — seul weda2 (client-angular) est embarqué dans Weda. Blazor et mobile
n'ont pas d'hôte Weda (raison fonctionnelle). La demande d'emballage d'api-mail leur servira plus
tard.
**Priorité**: 2 — sans elle, un praticien passé à la nouvelle expérience revient à l'ancien écran
pour chaque envoi depuis le dossier patient.

> **Origine.** Décisions de l'humain du 2026-10-11, consignées dans l'**amendement 6 de l'ADR-007**
> (dépôt Weda) et l'**amendement 4 de l'ADR client** :
> - un envoi lancé hors de la messagerie ouvre la rédaction de weda2 quand la bascule est active ;
> - les documents structurés partent dans leur enveloppe IHE_XDM, **construite par api-mail à
>   l'envoi, avec Interop** (task-366). WMickey est appelé à disparaître ;
> - l'envoi laisse une trace dans Weda ;
> - l'envoi depuis un courrier ou un résultat d'examen (`PatDk`, `Hprim`) est traité dans le
>   périmètre `nova-mss` seulement.
>
> Elle remplace task-361 (en attente), qui passait par le canal serveur Weda → api-mail abandonné.

## Ce qui existe (constaté dans le code le 2026-10-11)

- **Weda** : tous les envois qui ouvrent une rédaction aboutissent sur
  `/FolderMedical/WedaEchanges/?Mode=1&…&crypt=` :
  - `Fil` et `Pat` depuis l'historique du dossier ou la génération d'un CDA ;
  - `Add=1` et `Pat` depuis la fiche patient (Mon espace santé) ;
  - `PatDk` et `Hprim` (l'identifiant d'un `Document`) depuis un courrier ou un résultat d'examen.

  L'ancien écran envoie par WMickey et trace l'envoi dans `T_MSSanteTraceLog_Mtl`.
- **api-mail** :
  - `POST api/v1/mail/sendmail` prend un `MailDto`, avec les pièces en base64 dans `Attachments`
    (`AttachmentDto`). Limite : 10 Mio au total (`MailSendRules.CheckAttachments`) ;
  - toutes les voies d'envoi passent par `OutgoingMailService.SendCheckedAsync` : envoi direct,
    annuler et remplacer, confirmation d'un envoi différé, brouillon. Juste après
    `ResolvePartsByReferenceAsync` (`OutgoingMailService.cs:39`), toutes les pièces ont leurs
    octets : **c'est là que l'emballage s'insère**, avant les règles de taille et les en-têtes ;
  - `MssanteHeaderService` lit `mailDto.Attachments` et tire `X-MSS-CODECDA` et `X-MSS-INS` d'une
    pièce `ihe_xdm.zip`. Ce n'est prouvé que par un test unitaire ;
  - le RPPS de l'émetteur est connu (`UserContextInfo.SessionPscIdentity.Rpps`, et `MssRpps`). Son
    nom officiel, sa spécialité et sa structure ne le sont pas ;
  - api-mail référence `Interop.Cda.Parser` (101.0.0).
- **client-angular** :
  - `ComposePrefill = Partial<MailDto> & { quoted? }` (`mail-event.service.ts:20`). La rédaction ne
    reprend des pièces que pour un transfert, par référence (`mail-compose.component.ts:1454-1508`) ;
  - `MailEventService` est fourni par `mss-mail.component` : le shell ne l'atteint pas ;
  - aucun événement « message envoyé » : `executeSend` pose `sendResult` (`success`, `queued`,
    `awaiting`), puis émet `composeClosed$` ;
  - le pont n'a que des demandes de weda2 vers l'hôte. La boîte désignée suit déjà le patron « jeton
    de `libs/mss` fourni par le shell » (`designated-mailbox.provider.ts`).

## Objective

### dtos-mss

`AttachmentDto.Packaging` (`IheXdmPackagingDto?`), facultatif :
- `Kind` : `ExistingCda` ou `PdfA` ;
- `Title`, `DocumentTypeCode` (LOINC), `DocumentTypeLabel`, `DocumentDate`, `Confidentiality` ;
- `Patient` : INS (valeur, OID), noms, prénoms, sexe, date de naissance, lieu de naissance ;
- `Author` : identifiant national, nom, prénoms, profession, savoir-faire ;
- `Structure` : identifiant, nom, MSP.

Sans `Packaging`, rien ne change.

### api-mail

1. **Emballage à l'envoi**, dans `OutgoingMailService.SendCheckedAsync`, après
   `ResolvePartsByReferenceAsync`. Pour la pièce qui porte `Packaging` :
   - **l'auteur doit être l'émetteur** : son identifiant national doit correspondre au RPPS de la
     session (avec ou sans le préfixe `8`). Sinon `403` `ProblemDetails`, et rien ne part ;
   - api-mail appelle le packager d'Interop (task-366), avec pour destinataires prévus les adresses
     `To` et `Cc` du message ;
   - `ExistingCda` : la pièce est **remplacée** par `IHE_XDM.ZIP`, comme l'ancien écran pour un CDA ;
   - `PdfA` : le PDF reste, et `IHE_XDM.ZIP` est **ajoutée** ;
   - au plus une pièce avec `Packaging` par message, sinon `400` ;
   - un échec du packager donne un `422` `ProblemDetails`, avec le champ manquant, et rien ne part ;
   - les règles de taille s'appliquent ensuite, enveloppe comprise. `MssanteHeaderService` pose les
     en-têtes `X-MSS-*` comme aujourd'hui.
2. **Envoi différé** (sans carte CPS) : le `MailDto` mis en attente garde `Packaging`. L'enveloppe est
   construite à la confirmation, quand le message part vraiment.
3. **Journal** : l'emballage est journalisé avec le type de document et la taille seulement. Ni INS,
   ni nom, ni contenu.
4. Le catalogue reçoit le scénario E2E-WEDA-003.

### client-angular

Rien de ce qui suit n'est lancé si `WedaIntegrationService.available()` est faux.

1. **Port `MSS_COMPOSE_INTENT`**, dans `libs/mss`, optionnel : `() => Promise<ComposeIntent | null>`.
   - `ComposeIntent = { patientId: number; to: MailAddressDto[]; attachments: { fileName; contentType; content: ArrayBuffer; fileStreamId: number; packaging?: IheXdmPackagingDto }[] }`.
   - `apps/weda2` le fournit en mode embarqué seulement : `EmbeddedHostService.request('get-compose-intent')`,
     délai **120 s**.
   - Il rend `null` dans quatre cas : sur `{ intent: null }`, hors iframe, sans intégration
     disponible, ou si l'hôte ne connaît pas la demande (`unsupported`).
2. **Ouverture** : `mss-mail.component` interroge le port **une fois**, la boîte ouverte. Une
   intention ouvre la rédaction par `openCompose$`, avec ses destinataires et ses pièces.
   - Pendant la préparation : « Préparation des documents du dossier… ».
   - Une erreur du pont donne un message clair, sans détail technique, et n'ouvre pas de rédaction :
     - `forbidden` : le message de l'hôte (refus du patient, droits, identifiant de structure absent) ;
     - `payload-too-large` : « Documents trop volumineux pour un seul message (10 Mo au plus). » ;
     - les autres codes : leurs messages habituels.
3. **Pièces par contenu** : `ComposePrefill` accepte des pièces avec `content` (base64) et
   `packaging`.
   - La rédaction les ajoute comme un ajout à la main : nom, type, taille, même limite.
   - `packaging` est recopié tel quel dans `AttachmentDto`. weda2 ne le lit pas, mais signale la
     pièce « Données structurées (IHE_XDM) ».
   - Le transfert, par référence, ne change pas.
4. **Pas de brouillon** pour une rédaction ouverte par une intention (amendement 4 de l'ADR client) :
   - l'enregistrement automatique est coupé ;
   - « Enregistrer le brouillon » est absent ;
   - fermer la rédaction l'abandonne, après la confirmation habituelle.
5. **Erreurs d'envoi propres à l'emballage** (`403` auteur, `400`, `422`) : un message clair, et la
   rédaction reste ouverte.
6. **Après l'envoi** : un envoi `success` d'une rédaction ouverte par une intention émet
   `document-sent` `{ patientId, fileStreamIds, recipients }`. `recipients` ne porte que des
   adresses.
   - Un échec de `document-sent` ne change pas le résultat affiché : le message est parti. Il est
     journalisé avec le code d'erreur seulement.
   - `queued` et `awaiting` n'émettent rien en v1.
   - Une rédaction ouverte à la main, ou une réponse, n'émet rien.
7. **Faux hôte de test** (`e2e/mss-e2e/support/weda-host.ts`) :
   - `get-compose-intent` rend une intention configurable par le test : un CDA N3 synthétique avec
     `packaging`, ou un PDF/A synthétique avec `packaging`. Ce sont des fixtures du catalogue, sans
     donnée réelle, avec une INS sous OID de test ;
   - `document-sent` garde le patient, les identifiants de documents et le **nombre** de
     destinataires, jamais les adresses.

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est nécessaire pour que la tâche soit complète (règle 11).

> **Repère `nova-mss`** (ADR-007, amendement 4) : tout le code vit sous `Weda/api/NovaMss/` et
> `Weda/FolderMedical/WedaEchanges/NovaMss/`. **Aucun fichier de l'ancien écran, de WMickey ni de
> `WedaGlobal` n'est modifié** : les règles reprises sont **copiées**, avec un commentaire qui cite
> leur source. Hors de ces dossiers, seul `Weda.csproj` change. Sans le périphérique 9892, rien ne
> s'exécute.

- **`GET /api/nova-mss/compose-intent?{requête signée}`**, dans `NovaMssController` :
  - revalide `crypt` (`Crt.Security.ValidateUrl`). Sans `Mode=1`, rend `{ intent: null }` ;
  - le document :
    - `Fil` (et `Pat`) : un `FileStream` du cabinet de la session ;
    - `Hprim` (identifiant de `Document`) et `PatDk` : le `FileStream` du document, avec les contrôles
      de la page DMP (`Dmp.aspx.cs` › `LoadAuthorizedFile`, `CheckUserAuthorizedForHprimByDocId`) ;
  - la nature du document :
    - un CDA, reconnu à son contenu (`CdaMetadataService.GetCdaLevel`), donne `ExistingCda` ;
    - un PDF est converti en PDF/A-1b (`PdfAService`) et donne `PdfA` ;
    - le code LOINC et le cas « brut, sans enveloppe » suivent les règles de `FileCdaService`
      (`ResolveDocumentType`, `ShouldSendRawInsteadOfXdm`), copiées dans `NovaMssComposeDocuments` ;
  - les identités de `packaging` :
    - le patient : INS et OID par `CdaIdService.GetIns`, noms, sexe, naissance ;
    - l'auteur : l'utilisateur de la session, avec profession et savoir-faire tirés de l'annuaire
      (`AuthorAsipCAT18ToutePopulation.LoadByRpps`) ;
    - la structure : `Cabinet.IdentifiantStructure`, nom, MSP ;
  - `Add=1` : l'adresse Mon espace santé selon `MSSPatientTargeting.CanTargetPatient` et
    `MSSPatientService.GetPatientAdresse`. Un patient qui refuse les envois vers Mon espace santé,
    ou sans identifiant : aucun destinataire, comme l'ancien écran ;
  - les refus :
    - `DoNotConsentProfessionnal` avec un document : `403`, message « Le patient ne consent pas à ce
      que l'on envoie des données le concernant à d'autres professionnels. » ;
    - identifiant de structure absent : `403`, avec un message qui renvoie vers WIdentité ;
    - plus de 10 Mio au total : `413`.
- **`POST /api/nova-mss/sent-trace`** : `{ patientId, fileStreamIds, recipients }`.
  - Il revérifie que chaque document appartient au cabinet et au patient.
  - Il écrit les lignes `T_MSSanteTraceLog_Mtl` par `IMSSanteTraceLogRepo.Create`. La règle est
    **copiée** de `OutgoingSyncMailService.LogMssTraceAsync` : une ligne par type de destinataire
    (`@patient.mssante.fr`, autre `*.mssante.fr`), `Status = true`, statut INS courant, type de
    document recalculé, `Mss_ID` nul.
  - **Aucun changement de schéma.**
- **`nova-mss-host.js`** :
  - `get-compose-intent` : appelle la route avec `location.search`, une seule fois par chargement de
    la page, puis rend `{ intent: null }` ;
  - `document-sent` : appelle `sent-trace` ;
  - la réponse au pont accepte une liste de transfert ;
  - bascule inactive : rien ne change, l'ancien écran rédige.

## Definition of Done

- [ ] Build passes (0 errors) sur dtos-mss, api-mail et client-angular ; Tests pass (0 failures, hors
  flaky préexistants documentés)
- [ ] `dtos-mss` publié, consommé par api-mail ; `Interop.Cda.Parser` de task-366 consommé par
  api-mail
- [ ] **api-mail — tests d'intégration de la route** `POST api/v1/mail/sendmail` (règle 1b, preuve
  rouge consignée), le message relu dans la boîte du destinataire (Dovecot de test) :
  - [ ] `ExistingCda` : la pièce reçue est `IHE_XDM.ZIP` seule. Relue par `ParseIheXdmZip`, elle
    rend le CDA d'origine octet pour octet, l'INS du patient, le type de document et le destinataire
    prévu. Le message porte `X-MSS-CODECDA` et `X-MSS-INS` ;
  - [ ] `PdfA` : le PDF et `IHE_XDM.ZIP` (CDA N1 qui embarque le PDF) ;
  - [ ] sans `Packaging` : envoi inchangé ;
  - [ ] auteur différent de l'émetteur : `403`, rien n'est reçu ;
  - [ ] deux pièces avec `Packaging` : `400` ; donnée manquante : `422` qui la nomme ; rien n'est
    reçu ;
  - [ ] enveloppe qui dépasse la limite : refus de taille habituel ;
  - [ ] envoi différé puis confirmé : l'enveloppe est construite à la confirmation ;
  - [ ] aucun INS ni nom dans les journaux de l'emballage.
- [ ] **Angular — tests unitaires**, rouges d'abord :
  - [ ] le port n'est pas fourni hors mode embarqué, et rend `null` sans intégration disponible ;
  - [ ] `get-compose-intent` utilise un délai de 120 s ;
  - [ ] `available()` faux : **aucune** demande `get-compose-intent` ni `document-sent` n'est émise ;
  - [ ] une intention ouvre la rédaction avec ses destinataires et ses pièces. `packaging` est
    recopié tel quel dans `AttachmentDto`, et la pièce est signalée « Données structurées » ;
  - [ ] le port n'est interrogé qu'une fois par entrée ;
  - [ ] une pièce par contenu respecte la limite de taille, et le transfert par référence est
    inchangé ;
  - [ ] rédaction ouverte par une intention : ni enregistrement automatique, ni « Enregistrer le
    brouillon » ;
  - [ ] chaque erreur du pont donne son message et n'ouvre pas de rédaction ; chaque erreur
    d'emballage à l'envoi donne son message et laisse la rédaction ouverte ;
  - [ ] `document-sent` part après un envoi `success` d'une rédaction ouverte par une intention, avec
    `patientId`, `fileStreamIds` et les seules adresses ; rien après `queued`, `awaiting`, un
    abandon, une rédaction ouverte à la main ou une réponse ;
  - [ ] un échec de `document-sent` laisse le résultat « envoyé ».
- [ ] Scénario **E2E-WEDA-003**, version 1, ajouté dans `Api/Mail/e2e/scenarios.yml` :
  - titre : « Envoyer un document du dossier patient Weda par la nouvelle messagerie » ;
  - attendu :
    - à l'entrée, la rédaction s'ouvre avec le destinataire et le document de l'intention, signalé
      « Données structurées » ;
    - l'envoi à soi-même arrive : relu côté serveur, il porte l'enveloppe IHE_XDM, qui rend le CDA
      d'origine, et il est reconnu comme document médical ;
    - l'hôte reçoit `document-sent` avec le patient et le document de l'intention ;
    - un abandon n'envoie rien, et l'hôte ne reçoit pas `document-sent` ;
  - clients : `angular: requis`, `mobile: non-applicable — l'application mobile n'est pas embarquée
    dans Weda` ;
  - seed : `boite-praticien`. Le CDA synthétique est une fixture du catalogue ;
  - implémenté dans client-angular avec le faux hôte, et **prouvé rouge** (trou du filet) dans trois
    cas : `packaging` non recopié, `document-sent` jamais émis, pièces de l'intention ignorées.
- [ ] `data-testid` existants inchangés ; nouveaux : l'indicateur de préparation, le message d'erreur
  de l'intention, le signal « Données structurées ». Libellés FR en dur.
- [ ] Aucune donnée de santé dans les journaux : ni INS, ni nom, ni adresse patient, ni nom de
  fichier, ni contenu
- [ ] **Weda — repère `nova-mss`** : `git diff --stat` de la partie Weda ne montre que des fichiers sous
  `NovaMss/`, plus `Weda.csproj`. Aucun fichier sous `WMickey/`, `Weda/api/WMickey/`, `WedaGlobal/`
  ni de l'ancien écran (`SourceScripts/weda/apps/echanges/`, `Default.aspx(.cs)`)
- [ ] **Weda — périphérique** : sans « Expérience Nova », `compose-intent` et `sent-trace` répondent
  `403`
- [ ] Partie Weda faite et validée (règle 11) : voir le Manual Test Plan

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail && dotnet run --project src/AppHost`) et weda2
   (`cd Client/Angular/front && .\serve-weda2.ps1`). Weda tourne en `https://localhost:44300`.
   Prérequis :
   - le périphérique « Expérience Nova » (9892) et une boîte MSSanté V2 ;
   - `weda_integration` actif pour l'identité de la boîte désignée ;
   - la bascule « Nouvelle expérience Nova » active.
2. **PDF de l'historique** : dans le dossier d'un patient, « Envoyer le document par Weda
   Echanges ». La rédaction de weda2 s'ouvre avec le PDF, signalé « Données structurées ».
3. Envoyer à sa propre adresse. Le message reçu porte le PDF et `IHE_XDM.ZIP`, et il est reconnu
   comme document médical. Dans « Traces MSSanté » du dossier, une ligne « professionnel » apparaît
   pour ce document (colonne des destinataires vide : limite connue).
4. **VSM ou LDL** : générer, puis « Partager par Weda Echanges ». La pièce reçue est `IHE_XDM.ZIP`
   seule, et elle rend le CDA généré.
5. **Comparer** l'enveloppe reçue à celle de l'ancien écran pour le même document. Les écarts admis
   sont ceux de task-366. **Valider l'enveloppe avec les outils de test de l'ANS.**
6. **Mon espace santé** : depuis la fiche d'un patient au ciblage autorisé. L'adresse
   `…@patient.mssante.fr` est en destinataire. Après l'envoi, une ligne « patient » apparaît dans
   les traces.
7. **Courrier ou résultat d'examen CDA** : « Envoyer le document original via MSSanté ». La
   rédaction porte le document. Sur l'ancien écran (bascule inactive), elle reste vide : défaut
   connu, hors périmètre.
8. **Patient qui refuse les envois aux professionnels** : un message clair, aucune rédaction.
9. **Cabinet sans identifiant de structure** : un message renvoie vers WIdentité.
10. **Abandon** : fermer la rédaction. Rien n'est parti, aucune trace n'est écrite, aucun brouillon
    n'est créé.
11. **Bascule inactive** : même geste qu'à l'étape 2. L'ancien écran rédige, comme avant.
12. **Sans le périphérique** : même geste. L'ancien écran rédige, et `api/nova-mss/compose-intent`
    répond `403`.
13. Dans les journaux du navigateur, de Weda et d'api-mail : ni INS, ni nom, ni adresse patient, ni
    nom de fichier.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : F6 de l'EPIC E009 (« envoi contextuel depuis tout document Weda »),
  dans la nouvelle expérience. Partage des données structurées conservé : CDA emballé en IHE_XDM,
  PDF accompagné de son enveloppe CDA N1. L'enveloppe nomme désormais ses destinataires prévus.
- **INS** : l'enveloppe porte l'INS du dossier, par la règle de l'ancien écran
  (`CdaIdService.GetIns`). L'adresse Mon espace santé exige une identité qualifiée. Aucune identité
  n'est créée ni modifiée.
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel. **L'envoi reste un geste du
  praticien dans weda2**, avec sa session PSC. api-mail refuse un auteur qui n'est pas l'émetteur.
- **Habilitations** :
  - la signature `crypt` est revalidée côté serveur ;
  - le document doit appartenir au cabinet de la session, et au patient pour la trace ;
  - la boîte est celle que Weda désigne.
- **Interop CI-SIS** : CDA R2 N1 et N3, enveloppe IHE_XDM produite par Interop (task-366), validée par
  les outils de l'ANS avant la mise en service. En-têtes `X-MSS-CODECDA` et `X-MSS-INS`.
- **Tracé PGSSI-S** : l'envoi est tracé par api-mail comme tout envoi, et dans
  `T_MSSanteTraceLog_Mtl` côté Weda (document, patient, type de destinataire, statut INS).
- **Consentement patient** : `DoNotConsentProfessionnal` revérifié côté serveur. Envoi vers Mon
  espace santé selon les règles existantes (`MSSPatientTargeting`, `DoNotConsentPatient`).
- **Référentiels métier** : LOINC, jeux de valeurs de l'ANS (via Interop), G15
- **Hébergement HDS** : oui. Les documents et les identités passent de Weda à api-mail par le
  navigateur du praticien, en HTTPS, entre deux services hébergés. Rien n'est stocké en dehors de la
  boîte MSSanté.
- **AIPD / impact RGPD** : inchangé, même finalité que l'envoi depuis l'ancien écran. Les identités
  du patient transitent par le navigateur, en mémoire seulement : jamais dans l'URL, le stockage du
  navigateur ni les journaux.

## Branches

- `api-mail` (pushed) : feat/task-367-weda-envoi-ihe-xdm — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-367-weda-envoi-ihe-xdm
- `dtos-mss` (lazy) : branche `feat/task-367-weda-envoi-ihe-xdm` créée par `/develop` au moment où il touche le contrat (`AttachmentDto.Packaging`)
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` — snapshot à `/start` : `feature/nova-rewriting-mss-weda-integration` — humain gère branche, commit, push, PR TFS
- Weda (hors forge) : partie `nova-mss` faite par l'humain, en dehors de `/develop` (règle 11)
- Pré-flight : la garde de racine de `/start`, posée à task-366, comparait `--show-toplevel` à `pwd` et refusait tous les repos sous Git Bash (`D:/…` contre `/d/…`). Corrigée en `--show-prefix` vide (`.claude/commands/start.md`, CLAUDE.md), en attente de relecture humaine avec le reste.

## Develop log

- **Repos touched** : `dtos-mss`, `api-mail`, `client-angular` (code-only). Partie Weda : hors forge, **à faire par l'humain** (règle 11).
- **DTOs published** : `HealthPlatform.Dtos.Mss` 521.0.0 → **524.0.0** (CI run 524, branche `feat/task-367-weda-envoi-ihe-xdm`
  créée paresseusement par `/develop`, commit `2751a10`). `AttachmentDto.Packaging` (`IheXdmPackagingDto` : `Kind`
  `ExistingCda | PdfA` sérialisé en chaîne, titre, type, date, confidentialité, patient par INS, auteur, structure).
  Bump **api-mail seulement** : `client-blazor` n'est pas dans les `**Repos**` (champ additif, rien à recompiler côté Blazor).
- **Interop** : `Interop.Cda.Parser` 101.0.0 → **107.0.0** dans api-mail (construit depuis `develop` après le merge de task-366).
- **Commits** :
  - dtos-mss : `2751a10` feat(dto): AttachmentDto.Packaging — enveloppe IHE_XDM demandée à l'envoi
  - api-mail : `bcd44d9c` chore(deps) bump (lock files compris) ; `2bed2f86` feat(send) ; `b67c4ad3` refactor simplify pass
  - client-angular : **non commité** sur `feature/nova-rewriting-mss-weda-integration` (27 fichiers, ci-dessous)

### api-mail

- `IIheXdmEnvelopeService` / `IheXdmEnvelopeService`, appelé dans `OutgoingMailService.SendCheckedAsync` juste après
  `ResolvePartsByReferenceAsync` : toutes les voies d'envoi (direct, annuler-et-remplacer, confirmation différée,
  brouillon) passent par là. `ExistingCda` → la pièce est **remplacée** par `IHE_XDM.ZIP` ; `PdfA` → le PDF reste,
  `IHE_XDM.ZIP` est **ajoutée** juste après. Les entrées de la liste sont remplacées, jamais les objets de l'appelant.
- Refus :
  - plusieurs pièces emballées → `ValidationException` (400) ;
  - auteur ≠ émetteur → `IheXdmAuthorNotSenderException` (403, `code: IHE_XDM_AUTHOR_NOT_SENDER`) ;
  - donnée refusée par Interop → `IheXdmPackagingRefusedException` (422, `code: IHE_XDM_PACKAGING_REFUSED`,
    extension `field` : un nom de champ, jamais une valeur).
- Émetteur : le RPPS de la carte de la session (`SessionPscIdentity.Rpps`), à défaut celui de la boîte (`MssRpps`),
  préfixe 8 de l'identifiant national ignoré.
- Envoi différé : `Packaging` survit à la sérialisation du `MailDto` mis en attente ; l'enveloppe est construite à la
  confirmation. Le `Packaging` d'une pièce par référence est conservé à la relecture (`OutgoingMailService`).
- Journal : nature, type de document, taille. Aucun INS, nom ni nom de fichier (prouvé par test).
- `IIheXdmPackager` enregistré en singleton (sans état), `TimeProvider` de l'application.
- README de l'enveloppe : logiciel `HealthPlatform`, éditeur `Codengine Technologies`, version de l'assembly
  (**à confirmer par l'humain**).
- Catalogue : **E2E-WEDA-003 v1** (`angular: requis`, `mobile: non-applicable`).

### client-angular (code-only, à commiter sur TFS **avant** le merge de la PR api-mail — convention `test-angular-non-commite` : E2E-WEDA-003 est requis côté angular)

- `libs/mss` :
  - port optionnel `MSS_COMPOSE_INTENT` et `MSS_DOCUMENT_SENT` (`core/tokens/mss-compose-intent.token.ts`) ;
  - `ComposeIntentLauncherService` (racine) : l'hôte n'est interrogé qu'une fois par entrée, et l'intention n'est
    livrée qu'à une messagerie **vivante** (`take()` mis en cache, `claim()` une fois, documents libérés ensuite) ;
  - `mss-mail` : indicateur « Préparation des documents du dossier… », message d'erreur du pont
    (`compose-intent-preparing`, `compose-intent-error`, `compose-intent-error-dismiss`) ;
  - rédaction : pièces par contenu (même limite de taille qu'un ajout à la main), `packaging` recopié tel quel,
    signal « Données structurées (IHE_XDM) » (`compose-attachment-structured-{i}`), pas d'enregistrement automatique,
    `document-sent` après un envoi `success` seulement, refus d'emballage (codes du serveur, ou 400 avec pièce
    emballée) affichés avec l'explication du serveur, rédaction laissée ouverte ;
  - `problem-details.utils` : `isIheXdmPackagingRefusal`.
- `apps/weda2` : `compose-intent.provider.ts` (`get-compose-intent`, délai 120 s ; `document-sent`), types du pont,
  `WedaIntegrationService.settled` / `whenSettled()` : aucune demande tant que la disponibilité n'est pas tranchée.
- e2e : faux hôte (`get-compose-intent` une fois par chargement, CDA N3 synthétique + demande d'emballage, INS sous
  OID de test ; `document-sent` retenu par patient, documents et **nombre** de destinataires) ; `OtherDevice.readMessage` ;
  test **E2E-WEDA-003**.
- « Enregistrer le brouillon » : **ce bouton n'existe pas** dans weda2 (le brouillon n'est qu'automatique) ; le critère
  revient à couper l'enregistrement automatique, ce qui est fait et testé.
- **Décision produit prise par la forge, à valider** : une demande de fermeture venue d'ailleurs (changement de
  dossier, sélection d'un message) **demande la confirmation d'abandon** pour une rédaction d'intention, au lieu de
  l'abandonner en silence (elle n'a pas de brouillon : le document serait perdu).
- Fichiers (non commités) : `apps/weda2/src/app/app.config.ts`, `apps/weda2/src/lib/embedded/{embedded-host.model.ts,
  weda-integration.service.ts, weda-integration.service.spec.ts, compose-intent.provider.ts, compose-intent.provider.spec.ts}`,
  `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/{e2e-backend.ts, weda-host.ts}`,
  `libs/mss/src/core/{index.ts, models/mail.model.ts, tokens/mss-compose-intent.token.ts,
  services/compose-intent-launcher.service(.spec).ts, utils/compose-intent.utils(.spec).ts,
  utils/problem-details.utils(.spec).ts}`, `libs/mss/src/features/mail/{mss-mail.component.{ts,html,scss},
  mss-mail.component.compose-intent.spec.ts, services/mail-event.service.ts,
  components/mail-compose/{mail-compose.component.{ts,html,scss}, mail-compose-intent.component.spec.ts}}`.
  Le WIP humain `docs/ADR-2026-10-09-integration-weda-mode-embarque.md` n'est pas touché.

### Validation

- api-mail (dans le dépôt) : build 0 erreur ; domain 190, infrastructure 683, api **1 190**, application **3 587**,
  intégration **846** (16 ignorés), 0 échec. Base avant task : 1 188 / 3 569 / 838.
  Flaky préexistant vu une fois : `ImapServiceTests.GetFolderNotSeenAsync_HappyPath_TagsTheImapActivity…` (réentrance
  statique `ActivitySources`, déjà décrite par task-292/294), vert 5/5 seul et au passage complet suivant.
- client-angular : `nx build weda2` OK ; `nx run-many -t test` : 11 projets verts (mss-lib **759**, weda2 **2 686**,
  14 ignorés préexistants) ; ESLint des fichiers touchés : 0 erreur ; `tsc` de la suite e2e : OK.
- E2E-WEDA-003 joué contre le backend e2e (`--serve-only`) : **vert 3/3** puis à chaque contrôle.

### Règle 1b — comportements atteignables par l'endpoint, prouvés rouges

Route `POST api/v1/mail/sendmail`, vraie pile (`MailController`, `OutgoingMailService`, service d'enveloppe, packager
d'Interop, `SmtpService` vers le puits GreenMail, en-têtes `X-MSS-*`) — `IheXdmEnvelopeSendEndToEndTests`, 8 tests :

| Comportement | Test | Mutation rouge |
|---|---|---|
| CDA → `IHE_XDM.ZIP` seule, CDA octet pour octet, INS, type, destinataire prévu, `X-MSS-CODECDA` / `X-MSS-INS` | `AnExistingCda_ArrivesAsIheXdmZipAlone…` | MA1 (enveloppe jamais appliquée), MA3 (CDA ajouté au lieu d'être remplacé), MA4 (destinataires omis), MA7 (INS journalisée) |
| PDF/A → PDF + `IHE_XDM.ZIP` dont le N1 l'embarque | `APdfA_ArrivesWithThePdf…` | MA1 |
| sans `Packaging`, envoi inchangé | `WithoutPackaging_TheSendIsUnchanged` | (garde) |
| auteur ≠ émetteur : 403, rien reçu | `AnAuthorWhoIsNotTheSender_Is403…` | MA2 (auteur jamais comparé) |
| deux pièces emballées : 400, rien reçu | `TwoPackagedParts_Is400…` | MA5 |
| donnée manquante : 422 qui la nomme, rien reçu, journaux sans donnée de santé | `AMissingDatum_Is422NamingTheField…` | MA6 (422 → 400), MA8 (champ omis) |
| enveloppe au-delà de la limite : refus de taille habituel | `AnEnvelopePushingTheMessageOverTheLimit…` | MA1 (sans enveloppe, 6 Mo passent) |
| différé puis confirmé : demande gardée, enveloppe construite à la confirmation | `ASendWrittenWithoutTheCard_KeepsThePackagingRequest…` | MA1, MA3 |

Chaque mutation : marqueur compté (1), projet d'intégration recompilé, rouge sur le test qui la nomme, restaurée
(aucun `MUTATION` restant).

### Angular — preuves rouges

- Tests unitaires : 17 (rédaction d'intention), 7 (`mss-mail` × intention), 11 (provider weda2), 10 + 4 (utilitaires,
  lanceur), 6 (`whenSettled`), 6 (`isIheXdmPackagingRefusal`).
- **Deux défauts trouvés par l'e2e** (E2E-WEDA-003 vert 1 fois sur 3), corrigés, chacun avec son test unitaire **rouge
  sous mutation du correctif** (trou du filet, consigné `conventions/angular.md` › `service-propre-au-composant`) :
  1. messagerie remontée pendant la préparation : l'intention partait dans le service d'événements de l'instance
     détruite → lanceur racine + `claim()` + `destroyRef.destroyed` ;
  2. le chargement du premier dossier fermait la rédaction ouverte → corrigé **à la source** dans `mss-mail` (le
     premier dossier n'est pas « quitté ») ; une fermeture demandée d'ailleurs demande la confirmation d'abandon.
- E2E-WEDA-003 prouvé rouge dans les trois cas exigés par la DOD (bundle neuf servi, ~15 s d'attente, témoin restauré
  vert) : ME1 `packaging` non recopié → rouge sur « la pièce reçue est l'enveloppe IHE_XDM seule » ; ME2
  `document-sent` jamais émis → rouge sur « l'hôte reçoit document-sent » ; ME3 pièces ignorées → rouge sur « le
  document de l'intention est signalé « Données structurées » ».

### Passe qualité (/simplify)

- Applied & committed : api-mail : 3 fichiers (`b67c4ad3`) — recherche de la pièce emballée sans allocation, commentaire
  task-329 rendu à sa ligne, capture des journaux laissée globale (un `AsyncLocal` reste vide : essayé, gardes rouges).
- Applied (code-only, uncommitted) : client-angular — correctif du premier dossier remonté à la source,
  `destroyRef.destroyed`, documents libérés après prise, `whenSettled` direct si tranché, `describeSendError` sur
  `HttpErrorResponse` + codes du serveur (`isIheXdmPackagingRefusal`), `readComposeIntent` par gardes de type,
  journalisation de `document-sent` sortie de la méthode, entrées redondantes retirées. Re-validé vert.
- Écartés (notés) : factoriser le banc d'intégration avec `SendPathsEndToEndTests` (hors diff) ; généraliser
  `describeImportError` ; base64 asynchrone (≤ 10 Mo) ; interface générale pour l'extension `field`.
- Skipped (contract) : dtos-mss.

### DOD self-check

- [x] Build / tests verts sur dtos-mss, api-mail, client-angular
- [x] dtos-mss publié (524.0.0) et consommé ; Interop 107.0.0 consommé
- [x] Tests d'intégration de la route (8 cas de la DOD), preuve rouge consignée
- [x] Tests unitaires Angular de la DOD (port, délai 120 s, aucune demande sans intégration, ouverture, une seule
  interrogation, limite de taille, transfert par référence inchangé, pas de brouillon, erreurs du pont et
  d'emballage, `document-sent` et ses non-cas, échec de l'avis)
- [x] E2E-WEDA-003 v1 au catalogue, implémenté côté angular, prouvé rouge dans les trois cas
- [x] `data-testid` nouveaux posés ; libellés FR en dur ; existants inchangés
- [x] Aucune donnée de santé dans les journaux (api-mail prouvé ; weda2 : code d'erreur seul)
- [ ] Partie Weda (`compose-intent`, `sent-trace`, `nova-mss-host.js`, repère `nova-mss`, périphérique) : **humain**
- Manual Test Plan : HAG

- **Plan de contrôle, à relire avant push (règle d'or 7)** : `agents/develop.md` (les lock files se commitent avec
  le bump), `.claude/commands/start.md` + `CLAUDE.md` (garde de racine `--show-prefix`, corrigée à ce `/start`).
- **Next step** : `/sonar task-367`

## Sonar log

- Serveur 9.9.8.100196 (`sonar.login`), conteneurs redémarrés (arrêtés depuis 28 h). Deux analyses complètes, cinq suites vertes à chacune (domain 190, application 3 587 → 3 591, infrastructure 683, api 1 190, intégration 846 + 16 ignorés).
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 97,3 %
- Phase 1 — Issues traitées : 2 (0 bug / 0 vuln / 2 smells / 0 hotspot)
  - **S3925** × 2 sur `IheXdmAuthorNotSenderException` et `IheXdmPackagingRefusedException` : le triplet de constructeurs est présent d'emblée. La règle réclame encore le constructeur `ISerializable`, obsolète (SYSLIB0051). Marquées **FALSE-POSITIVE** avec commentaire, comme les exceptions voisines (`conventions/csharp.md`, S3925 : compteur à 5).
- Phase 1 — Constat restant, **hors code de la task** : S107 sur `SemanticSearchService.cs:395` (créé le 2026-10-02 par task-329), déjà dans la baseline et laissé par les tasks 351 à 355 pour le même motif.
- Phase 1 — Tests ajoutés : 4 (commit `test(sonar/new)`)
  - `IheXdmEnvelopeServiceTests` : une PDF/A sans ses données facultatives (valeurs neutres, confidentialité `N`, destinataires vides ignorés), puis un CDA sans contenu ni prénoms.
  - `TypedExceptionsCoverageTests` : les constructeurs standards des deux exceptions.
  - Couverture du nouveau code : `IheXdmEnvelopeService` passe de 87,6 % à 93,5 % (les conditions restantes sont des `?.` défensifs et le repli de version du logiciel), et les deux exceptions passent de 43–46 % à 100 %.
- Phase 2 (legacy) : non jouée, car les cibles projet sont déjà atteintes (0 bug, 0 vulnérabilité, A/A/A, couverture 97,9 % ≥ 95 %).
- Build / tests : ✓ green

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,5 % | 97,3 % | −0,2 pt (nouveau code de la task inclus) |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | 13 | 0 |
| Coverage (projet) | 98,0 % | 97,9 % | −0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode : affected. `npx nx affected -t lint --base=origin/next --head=HEAD --projects=tag:scope:mss` a lancé lint sur **12 projets** : le filtre `--projects` n'a pas restreint la liste. Avec `--output-file` en chemin absolu, Nx a préfixé le chemin du workspace (ENOENT). Lint rejoué en `run-many` sur les quatre projets touchés par la task : `mss`, `mss-lib`, `mss-e2e`, `weda2`. `weda2` est hors du défaut `tag:scope:mss`, mais la task y a écrit `compose-intent.provider` et `weda-integration.service`.
- Scope des corrections : les seuls fichiers de la task. Dette des autres fichiers non touchée (règle 6).
- Pipeline fidelity : mêmes commandes que `Client/Angular/azure-pipelines.yml` (Stage 2 CI), avec deux divergences voulues :
  1. BASE_BRANCH par défaut = `origin/next` ;
  2. lint restreint aux projets touchés.
- Branche : `feature/nova-rewriting-mss-weda-integration` (code-only, aucune opération git sauf `git fetch origin next`).
- Baseline : 0 erreur / 112 warnings sur les 4 projets, dont 35 dans les fichiers de la task. Attribution ligne à ligne par `git diff -U0 HEAD` : **5 introduits par la task**, 30 antérieurs (`max-lines`, `complexity` de `replacePlaceholders`, `require-example` des fonctions déjà présentes).
- Final : 0 erreur / 107 warnings, et 0 warning introduit par la task.
- Itérations : 1 / 5 (corrections manuelles, l'auto-fix n'avait rien à faire : 0 erreur).
- Build / tests : non rejoués, car les corrections sont des commentaires JSDoc dans `mss-e2e`, projet sans cible build ni test (`e2e`, `lint`). `tsc` du projet e2e est vert et Prettier aussi. Les suites sont rejouées par `/e2e` puis `/review`.

| Iter | Warnings task avant | Warnings task après | Build | Tests |
|------|---------------------|---------------------|-------|-------|
| 1 | 5 (`jsdoc/require-example`) | 0 | n/a (commentaires, projet sans build) | n/a |

Warnings restants : antérieurs, hors du code de la task. Dans les fichiers touchés : `max-lines` sur `mail-compose.component.ts`, `mss-mail.component.ts` et `functional.e2e.ts`, `complexity` sur `replacePlaceholders`, et `require-example` sur les fonctions préexistantes du support e2e et de `problem-details.utils.ts`.

## Lint mobile log

- skipped — `client-mobile` absent des `**Repos**` et arbre propre sur `develop`.

## E2E log

| Voie | Jouée | Résultat | Durée |
|---|---|---|---|
| mobile | oui (`api-mail` touché) — `npm run e2e:headless`, clone mobile sur `develop`, à jour avec `origin/develop` | ✅ 31 vert(s), 0 flaky, 0 rouge, parité de colonne verte | 5 min 42 s |
| angular | oui (`api-mail`, `client-angular` touchés) — `npm run e2e:mss`, branche `feature/nova-rewriting-mss-weda-integration` | ✅ 35 vert(s), 0 flaky, 0 rouge, dont **E2E-WEDA-003** (11,3 s) | 5 min 14 s |

- Backend e2e construit depuis `Api/Mail` sur `feat/task-367-weda-envoi-ihe-xdm` (catalogue de la branche).
- Démontage vérifié : ports 5052 / 3993 / 3465 / 3143 libres, aucun conteneur e2e résiduel.
- Spec e2e modifié avec les écrans : `e2e/mss-e2e/specs/functional.e2e.ts` (E2E-WEDA-003). Aucun avertissement « parcours touché sans spec ».
- **Signal (non bloquant)** : la quarantaine `E2E-COMPOSE-002` [angular] passe au vert, alors que sa task de correction (task-350) est archivée, donc mergée. La levée revient à l'humain seul.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

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
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
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
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
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
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/44, label `awaiting-human-merge`, à merger **en premier**.
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/289, label `awaiting-human-merge`.
- `client-angular` : code-only. L'humain gère le commit et le push TFS, puis l'ouverture de la PR, sur la branche `feature/nova-rewriting-mss-weda-integration`. Ces fichiers doivent être sur TFS **avant** le merge d'api-mail, car E2E-WEDA-003 est `requis` côté angular. Fichiers modifiés, 27 :

```
front/apps/weda2/src/app/app.config.ts
front/apps/weda2/src/lib/embedded/embedded-host.model.ts
front/apps/weda2/src/lib/embedded/weda-integration.service.spec.ts
front/apps/weda2/src/lib/embedded/weda-integration.service.ts
front/apps/weda2/src/lib/embedded/compose-intent.provider.ts (nouveau)
front/apps/weda2/src/lib/embedded/compose-intent.provider.spec.ts (nouveau)
front/e2e/mss-e2e/specs/functional.e2e.ts
front/e2e/mss-e2e/support/e2e-backend.ts
front/e2e/mss-e2e/support/weda-host.ts
front/libs/mss/src/core/index.ts
front/libs/mss/src/core/models/mail.model.ts
front/libs/mss/src/core/utils/problem-details.utils.ts
front/libs/mss/src/core/utils/problem-details.utils.spec.ts
front/libs/mss/src/core/services/compose-intent-launcher.service.ts (nouveau)
front/libs/mss/src/core/services/compose-intent-launcher.service.spec.ts (nouveau)
front/libs/mss/src/core/tokens/mss-compose-intent.token.ts (nouveau)
front/libs/mss/src/core/utils/compose-intent.utils.ts (nouveau)
front/libs/mss/src/core/utils/compose-intent.utils.spec.ts (nouveau)
front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.html
front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.scss
front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts
front/libs/mss/src/features/mail/components/mail-compose/mail-compose-intent.component.spec.ts (nouveau)
front/libs/mss/src/features/mail/mss-mail.component.html
front/libs/mss/src/features/mail/mss-mail.component.scss
front/libs/mss/src/features/mail/mss-mail.component.ts
front/libs/mss/src/features/mail/mss-mail.component.compose-intent.spec.ts (nouveau)
front/libs/mss/src/features/mail/services/mail-event.service.ts
```

  Le WIP humain `docs/ADR-2026-10-09-integration-weda-mode-embarque.md` n'a pas été touché.
- Partie Weda (hors forge, règle 11) : `compose-intent`, `sent-trace`, `nova-mss-host.js`, repère `nova-mss`, périphérique 9892, **à faire par l'humain**, puis validée par le Manual Test Plan.

## Code Review Summary

**APPROVED**, aucun point bloquant, 2 suggestions.

- Validation `/review` :
  - dtos-mss : build vert.
  - api-mail : build 0 erreur ; domain 190, infrastructure 683, api 1 190, application 3 591, intégration 846 (16 ignorés), 0 échec.
  - client-angular : `nx build weda2` vert ; `nx run-many -t test` : 11 projets verts (dont mss-lib 759, weda2 2 686 + 14 ignorés préexistants).
- Branches à jour avec `origin/develop` : aucune fusion nécessaire.
- **Règle 1b** : les 8 comportements de `POST api/v1/mail/sendmail` sont prouvés par `IheXdmEnvelopeSendEndToEndTests`, sur la vraie pile jusqu'au puits SMTP, avec preuve rouge MA1–MA8 (table du `## Develop log`).
- **E2E** : `**E2E : vert**`, voies mobile 31/31 et angular 35/35, parité verte, E2E-WEDA-003 au catalogue en v1 et vert.
- **api-mail** :
  - point d'entrée unique sur le chemin d'envoi commun, envoi différé compris ;
  - auteur comparé au RPPS de la carte ou de la boîte ;
  - exceptions typées 403 / 400 / 422, avec un nom de champ, jamais une valeur ;
  - Cci exclus des destinataires prévus ;
  - journaux sans donnée de santé, prouvé.
- **client-angular** :
  - intention livrée à une instance vivante une seule fois (lanceur racine, `claim()`, `destroyRef.destroyed`) ;
  - le premier dossier ne ferme plus la rédaction ;
  - aucune demande au pont sans intégration ;
  - `document-sent` seulement après un envoi `success` d'une intention.
- ⚠️ Suggestions :
  1. le message par défaut de `IheXdmPackagingRefusedException()` diffère de `PackagingRefused` (sans effet) ;
  2. à valider par l'humain : le logiciel et l'éditeur du README de l'enveloppe (`HealthPlatform`, `Codengine Technologies`).
- **Décisions de la forge à valider (HAG)** :
  - une demande de fermeture venue d'ailleurs demande la confirmation d'abandon d'une rédaction d'intention ;
  - le nom du logiciel et de l'éditeur dans le README de l'enveloppe.

## Timings

*(généré par `tools/timing/report.sh --task task-367 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 43 s | — | — | — | api-mail poussée ; dtos-mss paresseux ; angular code-only |
| /develop | ok | 1 h 24 min | 8 (2 min 05 s) | 18 (13 min 36 s) | — | dtos-mss 1B/0T, api-mail 4B/13T, client-angular 3B/5T, dtos 524 ; api-mail 8 intégration + mutations ; angular code-only ; 2 courses corrigées |
| /sonar | ok | 18 min 49 s | 2 (1 min 02 s) | 11 (11 min 08 s) | 4 (1 min 24 s) | 2 itération(s), api-mail 2B/11T |
| /lint-angular | ok | 4 min 50 s | — | — | — | 1 itération(s) |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 11 min 50 s | — | — | — | e2e ×3 (11 min 04 s) |
| /review | ok | 6 min 20 s | 3 (36 s) | 2 (4 min 05 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 1 min 11 s | — | — | — | — |
| **Total cycle** | | **2 h 07 min** | **13 (3 min 44 s)** | **31 (28 min 50 s)** | **4 (1 min 24 s)** | |

Autres commandes mesurées : lint ×3 (48 s), nuget-wait ×1 (18 s), restore ×1 (23 s)

## Merged

- **Date** : 2026-10-11, par `/merge task-367 --i-tested` (validation manuelle attestée par l'humain).
- `dtos-mss` : PR #44 squash-mergée dans `develop`, commit `f7cba20` (`AttachmentDto.Packaging`). Label
  `awaiting-human-merge` retiré. Branche `feat/task-367-weda-envoi-ihe-xdm` supprimée (distante et locale).
  CI `develop` verte : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/38171703555
- `api-mail` : PR #289 squash-mergée dans `develop`, commit `d283fc83` (enveloppe IHE_XDM construite à l'envoi par
  Interop). Label retiré. Branche `feat/task-367-weda-envoi-ihe-xdm` supprimée (distante et locale).
  CI `develop` verte : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38171724662
- `client-angular` : géré manuellement par l'humain (TFS).
- Partie Weda (hors forge), branche `lotus/segur/17546-enveloppe-segur-v2-with-mss-api` :
  - `5017d610e8` — `GET api/nova-mss/compose-intent`, `POST api/nova-mss/sent-trace`, gestionnaires
    `get-compose-intent` et `document-sent` du pont ;
  - `c6cfa10054` — ADR-007, amendement 6 ;
  - `d3c5f9c63b` — la pièce jointe porte le titre du document (deux documents du même jour et du même type
    portaient le même nom).
- Constat du test manuel : sans INS qualifiée, l'envoi d'un CDA est refusé par Weda (message de `CdaIdService`),
  alors que l'ancien écran l'envoie avec l'identifiant interne. Décision humaine en attente (garder le refus, ou
  faire accepter un identifiant local par Interop).
