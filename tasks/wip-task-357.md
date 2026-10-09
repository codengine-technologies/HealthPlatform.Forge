# wip-task-357.md — Intégration Weda, phase B : afficher le patient Weda d'un document reçu

**Repos**: client-angular
**Dependencies**: task-356 (pont v1, `WedaIntegrationService`, `MSS_PATIENT_RECORD_GATEWAY`)
**Epic**: E019
**Single frontend**: true — seul weda2 est embarqué dans Weda.
**Priorité**: **2** — premier livrable visible de l'intégration : dans un message reçu, le praticien
voit à quel dossier patient Weda correspond chaque document médical, et l'ouvre en un clic. C'est le
préalable au classement (phase C).

> **Origine.** Suite de task-356, décidée le 2026-10-09. Le contrat est celui de l'ADR-007 du dépôt
> Weda (§ D2 : `resolve-patient`, `get-filing-context`, `open-patient-record`). Côté Weda, le travail
> est hors forge : contrôleur `api/mss/filing` et gestionnaires du pont dans `Default.aspx`, sur la
> branche `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`. **api-mail n'est pas touché** : les
> traits du patient (`patientIns`, `patientOid`, nom, prénom, naissance, sexe) sont déjà dans
> `MailMedicalDocumentDto`.

## Ce qui existe (constaté dans le code le 2026-10-09)

- **client-angular** :
  - `MSS_PATIENT_RECORD_GATEWAY.resolvePatient()` et `openPatientRecord()` existent (task-356) ;
    ils sont relayés au pont et rejettent `unsupported` tant que `available()` est faux.
  - `mail-detail.component.ts` › `medicalDocumentsOfMail()` expose les documents médicaux du mail,
    avec les traits du patient extraits du CDA.
- **Weda** :
  - l'ancien écran rapproche un patient dans `api/WMickey/Builder/MessageBuilder.cs`
    › `GetCDAMetadata` : INS vérifiée d'abord (`PatientMixte.SelectPatientsByVerifiedIns`), sinon nom
    et prénom (`vitalzen.patient.searchPatients`) filtrés par la date de naissance ;
  - l'URL signée du dossier vient de `PatientHelpers.GetPatientUrl`.

## Objective

1. **Weda** — contrôleur `api/mss/filing` (`[Authorize]`, réservé aux utilisateurs
   `HasMessagerieSecurisee`, cloisonné par le cabinet de la session) :
   - `POST resolve-patient` `{ ins?, insOid?, lastName?, firstName?, birthDate?, gender? }` →
     `{ byIns, candidates }`. Il applique **les mêmes règles que l'ancien écran**, extraites dans une
     classe partagée que `MessageBuilder` utilise aussi. Seuls les patients Weda (`PatientID > 0`)
     sont rendus ; les patients Archimed non convertis sont exclus en v1.
   - `GET context` → destinations (1 Consultation, 2 Examen, 3 Courrier), destination par défaut
     (`LastDestinationUploadEvent`), classifications (glossaires « classification » du cabinet),
     destinataires de post-it (praticiens et secrétaires du cabinet).
   - `GET patient-url/{patientId}` (`[PatientCabinetAuthorization]`) → URL signée du dossier.
2. **Weda** — `Default.aspx` : gestionnaires `resolve-patient`, `get-filing-context` et
   `open-patient-record`. Ce dernier navigue la fenêtre principale vers l'URL signée. Les erreurs HTTP
   sont traduites en codes du contrat (400 `invalid-payload`, 401 `weda-session-expired`,
   403 `forbidden`, 404 `not-found`, sinon `server-error`).
3. **client-angular** — composant `mss-weda-patient-panel`, rendu dans `mail-detail` **seulement si**
   `MSS_PATIENT_RECORD_GATEWAY` est fourni, si `available()` est vrai et si le mail porte au moins un
   document médical avec une identité patient :
   - une ligne par identité patient distincte (INS + OID, sinon nom + prénom + naissance) ;
   - un patient trouvé par INS → « Dossier Weda : DUPONT Marie, née le 31/01/1970 », avec le bouton
     « Ouvrir le dossier » ;
   - sinon, les candidats par traits → « Correspondances possibles », chacune avec le bouton
     « Ouvrir » ;
   - aucun → « Aucun dossier Weda correspondant » ;
   - recherche en échec → « Recherche du dossier Weda impossible », sans détail technique.

## Definition of Done

- [x] Build passes (0 errors) ; Tests pass (0 failures, hors flaky préexistants documentés)
- [x] **Angular** — tests de composant :
  - [x] rien n'est rendu, et `resolvePatient` n'est pas appelé, si le port est absent ou
    `available()` faux
  - [x] une seule recherche par identité distincte, même avec plusieurs documents
  - [x] chacun des trois affichages (par INS, candidats, aucun) et l'état d'échec
  - [x] « Ouvrir le dossier » appelle `openPatientRecord` avec l'identifiant Weda
  - [x] l'INS n'apparaît ni dans le DOM ni dans les logs
- [x] **Weda** — build du projet `Weda.csproj` (MSBuild Debug, 0 erreur) ; le rapprochement de l'ancien écran (`MessageBuilder`) est
  inchangé après l'extraction (même classe, mêmes règles)
- [x] `data-testid` sur le panneau, chaque ligne et chaque bouton ; libellés FR en dur
- [x] Aucune donnée de santé dans les logs : ni INS ni traits, côté Weda comme côté weda2

## Manual Test Plan

Prérequis : phase A en place (`available=true` dans la console de l'iframe), et un message reçu
contenant un CDA (IHE_XDM).

1. Un patient avec INS **qualifiée** dans Weda, et un CDA portant cette INS → le panneau affiche
   « Dossier Weda : … ». « Ouvrir le dossier » ouvre la fiche du patient dans la fenêtre Weda.
2. Un CDA sans INS, mais dont le nom, le prénom et la date de naissance correspondent à un patient
   Weda → « Correspondances possibles », avec ce patient.
3. Un CDA dont le patient est inconnu de Weda → « Aucun dossier Weda correspondant ».
4. Flag `weda_integration` éteint, ou weda2 ouvert dans un onglet → aucun panneau, et aucune demande
   `resolve-patient` dans les messages échangés.
5. Un mail sans document médical → aucun panneau.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : préalable à RG-E009-034 (« classer en 1 clic dans le dossier
  patient »), qui sera couverte par la phase C
- **INS** : l'INS du CDA transite par le pont dans le `payload` (jamais dans une URL), et n'est
  comparée qu'aux INS **vérifiées** du cabinet. **Aucune identité n'est créée ni modifiée.** Un
  rapprochement par traits n'est qu'une **proposition**, présentée comme telle (identito-vigilance).
- **Authentification PS** : inchangée (session Weda et session proxy partagées)
- **Habilitations** : Weda revérifie tout. Les recherches sont cloisonnées par le cabinet de la
  session, et l'ouverture du dossier passe par `[PatientCabinetAuthorization]`.
- **Interop CI-SIS** : lecture des traits du CDA déjà extraits par api-mail ; rien n'est produit
- **Tracé PGSSI-S** : inchangé, aucune donnée de santé journalisée
- **Consentement patient** : non applicable — consultation du dossier par le praticien du cabinet
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé. Aucun identifiant Weda n'est persisté côté HealthPlatform.
- **AIPD / impact RGPD** : inchangé

## Branches

- `client-angular` (code-only) : branche courante `feature/nova-rewriting-mss-weda-integration`
  (humain : commit, push, PR TFS)
- Hors forge, `Weda` : `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`
- `api-mail` : non concerné

## Avancement (2026-10-09)

Implémenté directement (hors `/develop`), à la demande de l'humain.

- **Weda** (non commité) :
  - `api/MssFilingController.cs` : `resolve-patient`, `context`, `patient-url/{patientId}` ;
  - `api/MssFiling/MssPatientMatcher.cs` : règles extraites de `MessageBuilder`, qui les appelle
    désormais (−64 lignes dans `MessageBuilder`) ;
  - `api/MssFiling/MssFilingContracts.cs` ;
  - entrées `Compile` dans `Weda.csproj`. Au commit, il faudra isoler ces 3 lignes des réglages
    weda-dev (`/weda-dev off https`).
  - `Default.aspx` : gestionnaires `resolve-patient`, `get-filing-context`, `open-patient-record`, et
    traduction des erreurs HTTP. Une redirection vers la page de connexion devient
    `weda-session-expired`.
  - Vérifications : build MSBuild du projet Weda OK ; gestionnaires vérifiés par simulation Node
    (faux `fetch`).
- **client-angular** (non commité) :
  - `mss-weda-patient-panel` (composant, utilitaires, styles), branché dans `mail-detail` ;
  - tests : 20 tests du panneau ; `libs/mss` 608 verts ; weda2 2 654 verts ;
  - couverture du panneau 98,1 % (lignes) ; ESLint sans erreur. Seul avertissement : `max-lines`,
    préexistant sur `mail-detail` ;
  - build `nx build weda2` (development) OK, templates vérifiés.

**Non vérifié** : le parcours réel dans le navigateur (Manual Test Plan), et le rendu de l'ancien
écran après l'extraction du rapprochement (même code, déplacé).
