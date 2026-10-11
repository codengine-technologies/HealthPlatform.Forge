# todo-task-366.md — Interop : produire en mémoire l'enveloppe IHE_XDM d'un CDA existant ou d'un PDF/A, conforme à celle de Weda

**Repos**: interop-cda
**Dependencies**: aucune
**Partie Weda** : aucune. Le dépôt Weda n'est lu que comme référence (`IHE_XDM.cs`), jamais modifié.
**Epic**: E019
**Single frontend**: true — aucun frontend : c'est un package partagé.
**Priorité**: 1 — task-367 (envoi d'un document Weda par la nouvelle messagerie) en dépend.

> **Origine.** Décision de l'humain du 2026-10-11, consignée dans l'**amendement 6 de l'ADR-007**
> (dépôt Weda), C4 et C5 : c'est HealthPlatform qui construit l'enveloppe IHE_XDM d'un document
> envoyé, par Interop. Le circuit d'envoi de WMickey est appelé à disparaître, et les autres clients
> de HealthPlatform auront besoin de la même enveloppe.
>
> **L'enveloppe de Weda sert de référence** (`WedaGlobal/Services/CDA/Old/IHE_XDM.cs` et
> `WedaGlobal/Services/IheXdm/Services/IheXdmService.cs`, dépôt `D:\Workspaces\WD`) : elle est en
> production pour le Ségur. La forge la lit, sans la modifier.

## Ce qui existe (constaté dans le code le 2026-10-11)

Chemins relatifs à `interop/interop.cda.parser/src/Interop.Cda/`.

- **Le générateur d'enveloppe n'est utilisé nulle part** dans HealthPlatform. Trois entrées :
  - `IHEPackageGeneratorService.GeneratePackage(IHEPackageConfiguration)` ;
  - `IHEPackageBuilder.Build()` ;
  - `CDADocumentHelper.GetIheXdmZipFile(...)`.
- **Il est inutilisable en l'état** :
  1. `METADATA.XML` n'est jamais produit pour un CDA d'Interop :
     - `MetadataGenerator.cs:157` lève une exception sur `"".Substring(2)`, parce que `CdaBuilder`
       n'émet pas de `componentOf` ;
     - l'exception est avalée par un `Debug.WriteLine` (`IHEPackageGeneratorService.cs:70-79`), et
       le résultat est un succès ;
     - le test qui vérifiait la présence de `METADATA.XML` est commenté (`IheFileHelperTests.cs:450`).
  2. Le gabarit `METADATATemplate.XML` est un exemple de compte rendu de biologie, figé. Ne sont jamais
     mis à jour :
     - la classe `10`, le format XD-LAB, le type `11502-2` ;
     - la structure SA07 et le cadre `AMBULATOIRE` ;
     - les dates de 2016 ;
     - **l'INS-C d'exemple comme identifiant du patient**, et les identifiants de document et de lot
       constants ;
     - une association vers un objet inexistant.
  3. Défauts de valeurs :
     - le jeton `IDPNS` au lieu de `IDNPS` ;
     - `&amp;` échappé deux fois (`&amp;amp;`) ;
     - le nom du patient décalé dans PID-5 ;
     - `creationTime` lu dans `serviceEvent`, absent ;
     - le `Name` du document jamais mis à jour.
  4. `CdaBuilder` (interne) :
     - ne connaît que l'INS-C (`1.2.250.1.213.1.4.2`) ;
     - donne à l'organisation l'OID des cartes CPS, et au gardien celui du sexe
       (`OIDHelpers.cs:43`) ;
     - ajoute l'OID LOINC comme `templateId` ;
     - n'émet ni `documentationOf`, ni `componentOf`, ni `informationRecipient` ;
     - lit le corps d'un document non structuré depuis un **chemin de fichier**.
  5. Sous Linux, l'archive n'a pas de dossier `IHE_XDM/` : le séparateur est un `\\` en dur
     (`IHEPackageGeneratorService.cs:53`).
  6. Tout passe par le disque. `GetIheXdmZipFile` laisse un dossier temporaire à chaque appel.
  7. Rien n'emballe un **CDA déjà produit** : `GeneratePackage` part d'une entité `CDADocument`.
  8. Aucun `ILogger`. Les tests du générateur écrivent dans `C:\Temp` et ne passent que sous
     Windows.
- **Ce qui marche et se réutilise** : la lecture d'enveloppe (`XDM.Load`, `XdmArchiveExtractor`), le
  calcul SHA-1 et taille (`FileMetadataService`), les jeux de valeurs (`LOINCHelper`,
  `ConvertDocumentTypeConverter`).

## Objective

1. **Une API publique, en mémoire**, par exemple `IIheXdmPackager.Package(IheXdmPackageRequest)` →
   `IheXdmPackageResult { byte[] Zip; string FileName = "IHE_XDM.ZIP"; string DocumentTypeCode; string PatientId }`.
   - `IheXdmPackageRequest` :
     - `Document`, l'un des deux :
       - **CDA existant** : les octets du XML, N1 ou N3, emballés **tels quels** ;
       - **PDF/A** : les octets, le titre, le code LOINC et son libellé, la date du document, la
         confidentialité (`N` par défaut). Interop construit un **CDA R2 N1** en mémoire
         (`nonXMLBody`, `application/pdf`, base64), sans fichier ;
     - `Patient` : INS (valeur et OID : NIR `1.2.250.1.213.1.4.8`, NIA `1.2.250.1.213.1.4.9`, et
       leurs OID de test `.10` et `.11`), noms (naissance, usage), prénoms, sexe, date de naissance,
       code INSEE du lieu de naissance ;
     - `Author` : identifiant national (`8` + RPPS), nom, prénoms, profession et savoir-faire (G15) ;
     - `Structure` : identifiant de structure, nom, MSP ou non ;
     - `IntendedRecipients` : adresses MSSanté des destinataires ;
     - `Software` (nom, version, éditeur) et `DisableZip64`.
   - Aucune écriture sur le disque.
   - Un échec n'est jamais un succès : une donnée manquante ou invalide lève une exception typée
     qui nomme le champ (`IheXdmPackagingException`, avec un code). Aucun `Debug.WriteLine`.
   - La validation des entrées précède toute génération.
2. **Le CDA N1 construit à partir d'un PDF/A** porte :
   - le patient par son INS, avec l'OID donné ;
   - l'auteur sous `1.2.250.1.71.4.2.1` ;
   - l'organisation et le gardien sous `1.2.250.1.71.4.2.2` et l'identifiant de structure ;
   - `documentationOf/serviceEvent` (date du document) ;
   - `componentOf/encompassingEncounter/location/healthCareFacility` (SA52 si MSP, sinon SA07) ;
   - un `informationRecipient` par destinataire ;
   - les `templateId` du N1, sans l'OID LOINC.

   Ces corrections valent pour la nouvelle API. Avant de toucher `CdaBuilder` lui-même, la forge
   liste ses autres consommateurs dans le `## Develop log`. Elle ne le corrige que si personne ne
   dépend de son comportement actuel ; sinon, la nouvelle API a son propre constructeur de N1.
3. **Les métadonnées**, construites en mémoire avec un échappement XML correct. Le tableau
   ci-dessous donne la valeur attendue de chaque champ. La colonne « Weda » est la référence.
4. **L'archive** :
   - `IHE_XDM.ZIP` ;
   - entrées dans l'ordre de Weda : `INDEX.HTM`, `README.TXT`, les dossiers `IHE_XDM/` et
     `IHE_XDM/SUBSET01/`, `IHE_XDM/SUBSET01/METADATA.XML`, `IHE_XDM/SUBSET01/DOC00001.XML` ;
   - séparateur `/` ;
   - UTF-8 sans BOM ;
   - Zip64 désactivable, comme Weda pour TerrE Santé.
5. **L'ancienne API** (`GeneratePackage`, `IHEPackageBuilder`, `GetIheXdmZipFile`) est marquée
   `[Obsolete]`, avec un renvoi vers la nouvelle. Le package porte un contrat : on ne la supprime pas
   dans cette task.

### Valeurs attendues des métadonnées

| Champ | Valeur attendue | Référence Weda (`IHE_XDM.cs`) |
|---|---|---|
| SubmissionSet `submissionTime` | instant de génération, UTC, `yyyyMMddHHmmss` | `ArchiveDate`, heure locale : **corrigé en UTC** |
| SubmissionSet `authorPerson` | `{idNat}^{nom}^{prénoms}^^^^^^&1.2.250.1.71.4.2.1&ISO^D^^^IDNPS` | :345, :599 |
| SubmissionSet `authorSpecialty` | `G15_{profession}/{savoirFaire}^{libellé}^1.2.250.1.213.1.1.4.5` | :354-359 |
| SubmissionSet `authorInstitution` | `{nom}^^^^^&1.2.250.1.71.4.2.2&ISO^IDNST^^^{identifiantStructure}` | :372 |
| SubmissionSet `contentTypeCode` | SA52 si MSP, sinon SA07, système `1.2.250.1.71.4.2.4` | :381-391 |
| SubmissionSet `patientId` | `{ins}^^^&{oid}&ISO^NH` | :258, :399-452 |
| SubmissionSet `sourceId` | `1.2.250.1.213.1.1.9.8.1.{identifiantStructure}` | :457 |
| SubmissionSet `uniqueId` | `1.2.250.1.213.1.1.9.{identifiantStructure}.{yyyyMMddHHmmss}{suffixe unique}`, différent à chaque appel | :467 |
| SubmissionSet `intendedRecipient` | une valeur par destinataire (forme XTN de l'adresse) | **absent chez Weda : ajouté** |
| DocumentEntry `mimeType`, `hash`, `size`, `URI` | `text/xml`, SHA-1 hexadécimal en majuscules, taille en octets, `DOC00001.XML` | :486, :494 |
| DocumentEntry `creationTime` | `effectiveTime` du CDA, UTC | :510 |
| DocumentEntry `languageCode` | `languageCode` du CDA, `fr-FR` par défaut | :518 |
| DocumentEntry `legalAuthenticator` | celui du CDA, à défaut l'auteur | :532 |
| DocumentEntry `serviceStartTime` / `serviceStopTime` | `serviceEvent/effectiveTime` du CDA (`low`, `high`), à défaut `creationTime` / absent | :540 |
| DocumentEntry `sourcePatientId` | les identifiants du patient dans le CDA, l'INS en `^NH` | :546-558 |
| DocumentEntry `sourcePatientInfo` | PID-3, PID-5 (`{nom de naissance}^{prénom}^^^^^L`, et le nom d'usage en `D` s'il diffère), PID-7, PID-8, PID-11 (lieu de naissance) | :562-577 |
| DocumentEntry `title` (Name et Description) | `title` du CDA | :582, :588 |
| DocumentEntry `classCode` | déduit du type de document (10, 11, 52, 60, 90) | `DocumentEntry.cs:433-488` |
| DocumentEntry `confidentialityCode` | `confidentialityCode` du CDA, `N` par défaut | :650 (figé à `N`) |
| DocumentEntry `formatCode` | déduit du gabarit du CDA, par exemple N1 PDF : `urn:ihe:iti:xds-sd:pdf:2008`, système `1.2.250.1.213.1.1.4.2.282` | `DocumentEntry.cs:98-176` |
| DocumentEntry `healthcareFacilityTypeCode` | SA52 si MSP, sinon SA07 | :678-685 |
| DocumentEntry `practiceSettingCode` | `ETABLISSEMENT`, système `1.2.250.1.213.1.1.4.9` | :692 |
| DocumentEntry `typeCode` | `code` du CDA (LOINC), libellé du jeu de valeurs | :705-745 |
| DocumentEntry `eventCodeList` | `serviceEvent/code` du CDA s'il existe, sinon absent | :750 (code figé, objet parasite) : **non recopié** |
| DocumentEntry `patientId` | comme le SubmissionSet | :766 (caractère parasite) : **non recopié** |
| DocumentEntry `uniqueId` | `id` du CDA, `{root}^{extension}` | `IheXdmService.cs:206-228` |
| DocumentEntry `status` | `Approved` | :480 |
| Associations | une `HasMember` par document, aucune vers un objet inexistant | :789-801 |

## Definition of Done

- [ ] `dotnet build interop.cda.parser.sln` : 0 erreur ; `dotnet test` : 0 échec, **sous Windows et
  sous Linux** (aucun chemin `C:\` dans les tests)
- [ ] Tests unitaires, rouges d'abord, sur la nouvelle API :
  - [ ] un CDA N3 synthétique est emballé tel quel : l'archive relue par le lecteur d'Interop
    (`XDM.Load`) rend le même document, octet pour octet ;
  - [ ] un PDF/A synthétique donne un CDA N1 valide (patient par INS NIR, auteur, structure,
    `documentationOf`, `componentOf`, un `informationRecipient` par destinataire), relu par le
    lecteur d'Interop ;
  - [ ] **chaque ligne du tableau des métadonnées** a son assertion, dans les deux cas ;
  - [ ] deux appels donnent deux `uniqueId` de lot différents ;
  - [ ] l'ordre et les noms des entrées de l'archive sont ceux de Weda ; séparateur `/` ; pas de
    BOM ; Zip64 désactivé quand demandé ;
  - [ ] un nom de structure ou un titre contenant `&`, `<` et `"` donne un XML valide ;
  - [ ] chaque donnée obligatoire manquante (INS, identifiant national, identifiant de structure,
    code LOINC) lève l'exception typée qui la nomme, sans rien produire ;
  - [ ] aucun fichier n'est écrit sur le disque pendant la génération ;
  - [ ] l'INS-C d'exemple du gabarit n'apparaît dans aucune archive.
- [ ] Preuve rouge consignée dans le `## Develop log` : chaque test vu rouge sur le générateur
  actuel, ou par mutation
- [ ] L'ancienne API est `[Obsolete]`, avec un renvoi vers la nouvelle ; ses consommateurs (s'il y
  en a) sont listés dans le `## Develop log`
- [ ] Package `Interop.Cda.Parser` publié par la CI, version notée dans le `## Develop log` (consommée
  par task-367)
- [ ] Aucune donnée de santé réelle dans les tests ni dans les journaux : patient synthétique, INS
  sous OID de test

## Manual Test Plan

1. Produire deux archives avec la nouvelle API (un VSM synthétique, un PDF/A synthétique) par le
   petit programme ou le test que la forge indique dans le `## Develop log`.
2. Obtenir les deux archives de référence de Weda, **sans aucun développement Weda** : depuis
   l'ancien écran, envoyer à sa propre adresse les deux mêmes documents, pour le même patient de
   test, puis récupérer les `IHE_XDM.ZIP` reçus.
3. Comparer les deux `METADATA.XML`, champ par champ. Les seuls écarts admis sont ceux du tableau
   (UTC, `intendedRecipient`, `eventCodeList`, défauts de Weda non recopiés).
4. **Valider les deux archives d'Interop avec les outils de test de l'ANS** (validateur des documents
   et des métadonnées XDM du CI-SIS). Aucune erreur bloquante. Les avertissements sont consignés.
5. Ouvrir chaque archive dans weda2, après un envoi à soi-même : elle est reconnue comme document
   médical, avec le bon type.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : partage des données structurées lors d'un envoi MSSanté (enveloppe
  IHE_XDM, CI-SIS « Transport MSSanté » et « Volet structuration minimale »). La task les rend
  possibles dans HealthPlatform ; task-367 les met en œuvre.
- **INS** : l'identifiant du patient est l'INS fournie par le logiciel appelant, avec son OID (NIR ou
  NIA). Interop ne la qualifie pas et ne la modifie pas. L'INS-C n'est plus produite.
- **Authentification PS** : non applicable (package).
- **Habilitations** : non applicable (package). C'est l'appelant qui vérifie que l'auteur est
  l'émetteur (task-367).
- **Interop CI-SIS** : CDA R2 N1 et N3, enveloppe IHE_XDM, jeux de valeurs de l'ANS (types de
  document, formats, structures, spécialités G15). Validation par les outils de l'ANS avant la mise
  en service (Manual Test Plan).
- **Tracé PGSSI-S** : non applicable (package, aucun journal de données).
- **Consentement patient** : non applicable.
- **Référentiels métier** : LOINC, TRE-R*/JDV de l'ANS (classCode, formatCode,
  healthcareFacilityTypeCode, practiceSettingCode), G15.
- **Hébergement HDS** : non applicable (aucune donnée stockée).
- **AIPD / impact RGPD** : aucun.

## Branches
- `interop-cda` (pushed) : feat/task-366-ihe-xdm-packager — https://github.com/codengine-technologies/interop.cda.parser/tree/feat/task-366-ihe-xdm-packager
  - Dépôt réel : `interop/interop.cda.parser` (le tableau de CLAUDE.md disait `interop`, sans `.git`). Un premier essai a créé et poussé la branche sur le plan de contrôle ; elle a été supprimée (locale et distante) avant la création ci-dessus. Prévention : chemin corrigé dans CLAUDE.md, garde `git rev-parse --show-toplevel` ajoutée à `/start` (pré-flight et step 5).

## Develop log

- **Repos touched** : `interop-cda` (`interop/interop.cda.parser`, branche `feat/task-366-ihe-xdm-packager`)
- **DTOs published** : no DTO change
- **Interop published** : `Interop.Cda.Parser` **105.0.0** (CI run 105, 2026-10-11 16:02 UTC, build + **tests sous ubuntu** + pack + push verts).
  `api-mail` est en 101.0.0. **Aucun bump ici** : `api-mail` n'est pas dans les `**Repos**` ; c'est task-367 qui consomme 105.0.0.
  (104.0.0 a été publié par le premier push de la branche, code identique à `develop` : la CI publie à chaque push.)
- **Commits** :
  - interop-cda : `4d10204` feat(interop): enveloppe IHE_XDM en mémoire d'un CDA ou d'un PDF/A (task-366) — 31 fichiers
- **Local build / test** :
  - Windows : `dotnet test interop.cda.parser.sln` → **501 réussis, 0 échec, 6 ignorés** (507). Base avant task : 407 / 0 / 5.
  - Linux (`docker run mcr.microsoft.com/dotnet/sdk:10.0 … dotnet test`) → **500 réussis, 0 échec, 6 ignorés** (506, avant l'ajout
    du test d'export). **Base avant task : 41 échecs sous Linux.**
  - CI ubuntu (run 105) : étape `Test` verte.

### La nouvelle API (`Interop.Cda.IheXdm`, assembly `Interop.Cda`, livrée dans le package `Interop.Cda.Parser`)

- `IIheXdmPackager.Package(IheXdmPackageRequest)` → `IheXdmPackageResult { Zip, FileName = "IHE_XDM.ZIP", DocumentTypeCode, PatientId }`.
  Implémentation `IheXdmPackager(TimeProvider? = null, ILogger<IheXdmPackager>? = null)` : à enregistrer en singleton.
- `IheXdmPackageRequest` : `Document` (`IheXdmCdaDocument(byte[] Xml)` **ou** `IheXdmPdfDocument(Pdf, Title, TypeCode,
  TypeDisplayName, DocumentDate) { ConfidentialityCode = "N" }`), `Patient` (INS + `IheXdmInsOids.Nir/Nia/NirTest/NiaTest`, noms,
  prénoms, sexe, naissance, INSEE), `Author` (`NationalId` = 8 + RPPS, profession + savoir-faire G15), `Structure` (identifiant, nom,
  `IsMsp`), `IntendedRecipients`, `Software`, `DisableZip64`.
- Échec : `IheXdmPackagingException { Code (MissingField | InvalidField | InvalidCda | PatientMismatch), Field }`, levée **avant**
  toute génération. Aucun `Debug.WriteLine`, aucune archive partielle.
- Rien n'est écrit sur le disque. Le journal ne porte que le type, le format et la taille (aucune identité, aucun contenu).

### `CdaBuilder` : consommateurs listés, non modifié

- **Seul appelant** : `CDADocumentHelper.Convert`, utilisé par l'ancien générateur (`IHEPackageGeneratorService`). Ses
  sous-constructeurs sont couverts par `CdaAuteurBuilderTests`, `CdaComponentBuilderTests`, `CdaMedicalRecordBuilderTests`,
  `CdaMedicationsBuilderTests`, `CdaPathologiesBuilderTests`, `CdaMedecinTraitantBuilderTests`.
- **Hors Interop : aucun.** `api-mail` (grep `Api/ Client/ Host/ Sdk`) n'appelle de `CDADocumentHelper` que
  `GetCdaDocumentType`, `GetDocumentCategory` et `GetLoincCodesForDocumentType`. Weda (`D:\Workspaces\WD`) ne référence pas Interop.
- **Décision** : des tests dépendent de sa sortie actuelle, donc la nouvelle API a **son propre constructeur de N1**
  (`CdaN1Builder`, en mémoire, XDocument). Seule retouche dans les sous-constructeurs : la date « vide » construite au lieu
  d'être analysée (portabilité Linux, ci-dessous). Aucun changement de comportement sous Windows.

### Ancienne API `[Obsolete]` (renvoi vers `IIheXdmPackager`)

- `IHEPackageGeneratorService.GeneratePackage`, `IHEPackageBuilder.Build`, `CDADocumentHelper.GetIheXdmZipFile`, et les deux
  `IheFileHelper.GenerateIHEZipPackage` (ils relaient le même générateur ; l'un portait déjà un `[Obsolete]`, remplacé).
- **Consommateurs** : aucun hors d'Interop. Dans Interop : `IheFileHelperTests` et `IHEPackageBuilderTests` (`#pragma warning
  disable CS0618`, ils couvrent l'ancienne API tant que le package la porte). Rien n'est supprimé.

### Preuve rouge

1. **Sur le bouchon** (`Package` lève `NotImplementedException`) : **94/94 rouges**. Ce rouge n'est pas attribuable (convention
   `test-de-rejet-attribuable`), d'où l'étape 2.
2. **Par mutation**, 22 défauts réinjectés un à un dans le code livré (harnais : réécriture du fichier, suite `IheXdm` rejouée,
   restauration par réécriture, mtime neuf). **Chaque mutation est rouge sur le test qui la nomme** :

   | Mutation | Test(s) rouge(s) attendu(s) |
   |---|---|
   | M1 `submissionTime` en heure locale | `SubmissionSet_SubmissionTime_IsTheGenerationInstantInUtc` (cda, pdf) |
   | M2 pas d'échappement HL7 | `Package_SpecialCharactersInStructureNameAndTitle_ProduceValidXml` |
   | M3 double échappement XML (`&amp;amp;`) | `…Author_CarriesPersonSpecialtyAndInstitution` (×4), `Package_SpecialCharacters…` |
   | M4 suffixe d'unicité constant | `SubmissionSet_UniqueId_DiffersFromOneCallToTheNext` |
   | M5 `README.TXT` avant `INDEX.HTM` | `Package_Entries_FollowWedaOrderAndNamesWithSlashSeparator` (cda, pdf) |
   | M6 séparateur `\` | `Package_Entries_…WithSlashSeparator` (+ 75 dépendants : l'archive n'a plus de `METADATA.XML` lisible) |
   | M7 BOM UTF-8 | `Package_TextEntries_AreUtf8WithoutBom` (+ dépendants : le XML ne se relit plus) |
   | M8 INS absente non contrôlée | `Package_MissingMandatoryField_ThrowsNamingTheField(Patient.Ins)` |
   | M9 écriture dans le dossier temporaire | `Package_WritesNothingOnDisk` (cda, pdf) |
   | M10 INS-C du gabarit publiée | `Package_NoArchive_CarriesTheTemplateInsC` (cda, pdf), `…SourcePatientInfo…` |
   | M11 contrôle du patient retiré | `Package_CdaOfAnotherPatient_IsRefused` |
   | M12 responsable légal = toujours l'auteur | `DocumentEntry_LegalAuthenticator_IsTheCdaOneElseTheAuthor(cda)` |
   | M13 `creationTime` non converti en UTC | `DocumentEntry_CreationTime_…InUtc` (cda, pdf), `…ServiceTimes…` (cda, pdf) |
   | M14 classe toujours 11 | `DocumentEntry_ClassCode_DerivesFromTheDocumentType(pdf)` |
   | M15 `eventCode` toujours présent (code figé de Weda) | `DocumentEntry_EventCodeList_IsTheServiceEventCodeWhenPresent(pdf)` |
   | M16 référence parasite (caractère de Weda) | `Associations_…NoDanglingReference` (cda, pdf), `DocumentEntry_PatientId_…` (cda, pdf) |
   | M17 format N1 figé « hors profils » | `DocumentEntry_FormatCode_DerivesFromTheCdaTemplate(pdf)` |
   | M18 OID LOINC en `templateId` | `Package_Pdf_TemplateIdsAreThoseOfAnN1WithoutTheLoincOid` |
   | M19 un seul `informationRecipient` | `Package_Pdf_OneInformationRecipientPerRecipient` |
   | M20 `componentOf` absent | `Package_Pdf_ComponentOfCarriesTheFacilityType` (SA07, SA52) |
   | M21 CDA ré-sérialisé au lieu d'emballé tel quel | `Package_CdaN3_DocumentEntryIsTheSuppliedCdaByteForByte`, `…IsReadBackByXdmLoadAsTheSameDocument` |
   | M22 confidentialité figée à N | `DocumentEntry_ConfidentialityCode_IsTheCdaOne(cda, R)` |

3. **Validation du N1 contre le schéma CDA** : prouvée par mutation à part (`legalAuthenticator` placé avant
   `informationRecipient` → rouge « The element 'ClinicalDocument' … »). Les avertissements de validation sont promus en erreurs :
   un schéma non chargé ne passe pas à vide.
4. **Zip64** : non mutable (`ZipArchive` sur un `MemoryStream` n'émet jamais de Zip64 en dessous de 4 Go). Le test lit le
   répertoire central de l'archive produite (6 en-têtes parcourus, vérifié) : version requise < 45, aucun champ extra `0x0001`,
   aucune signature Zip64. `DisableZip64` pose en plus une garde explicite à 4 Go.

### Portabilité Linux (DOD « sous Windows et sous Linux »)

41 tests rouges sous Linux avant la task, invisibles : la CI ubuntu ne jouait que le build.
- `CdaMedicationsBuilder`, `CdaPathologiesBuilder` : `DateTime.Parse("30/12/1899")` (culture de l'hôte, levée en culture invariante
  dans l'initialiseur statique) → `new DateTime(1899, 12, 30)`. **Défaut de la bibliothèque, pas seulement des tests.**
- `IHEPackageGeneratorService` : `$"IHE_XDM\\{subset}"` → `Path.Combine(dest, "IHE_XDM", subset)` (défaut 5 de la task).
- `IheFileHelperTests` : `C:\Temp` → `Path.GetTempPath()`. `IHEPackageBuilderTests` : `C:\Test\Output*` (31 occurrences) → chemins
  temporaires. **Plus aucun `C:\` dans les tests.**
- `IheXdmZipParserTests` : jeux d'archives réelles du poste (`D:\…\JEUX_TESTS_FULL`) → attribut `LocalTestDataFact`, **ignoré** (et
  le dit) là où les données manquent, au lieu d'échouer.
- CI (`.github/workflows/dotnet.yml`) : étape `dotnet test` ajoutée, `setup-dotnet` 10.0.x. Un rouge bloque la publication.

### Écarts et décisions à relire au HAG

1. **`formatCode` d'un N1 PDF, système** : `1.3.6.1.4.1.19376.1.2.3`, comme Weda (`DocumentEntry.cs`, schéma des formats IHE) et le
   JDV J10. L'exemple du tableau de la task écrit `1.2.250.1.213.1.1.4.2.282` (système des formats CI-SIS). La task désigne Weda comme
   référence ; à confirmer par le validateur de l'ANS (Manual Test Plan, étape 4).
2. **`intendedRecipient`** : `||^^Internet^{adresse}` (XON|XCN|XTN, XON et XCN vides), forme des exemples IHE ITI TF-3. Absent chez
   Weda : à confirmer par le validateur.
3. **Échappement HL7** des délimiteurs dans les textes libres des métadonnées (`&` → `\T\`, etc.) : brut, un `&` dans un nom de
   structure découpe la composante. Weda écrit brut.
4. **`classCode`** : les types « CR … » du jeu de valeurs et la lettre de sortie → 10 ; vaccination et `CERT_DECL` → 52 ; `REMB` → 60 ;
   `EXPPAT_*` → 90 ; le reste → 11 (défaut de Weda). Weda classe un PDF typé CR en 11. Limité aux valeurs 10, 11, 52, 60, 90 de la task :
   une prescription tombe donc en 11. Libellé de 60 (« Données de remboursement ») absent du JDV de Weda : à confirmer.
5. **`formatCode` d'un N3** : par gabarit (VSM `.1.13`, LDL-EES `.1.21`, LDL-SES `.1.29`, XD-LAB) ; à défaut, VSM si le type est `SYNTH`
   ou `60591-5` (la VSM IPS-FR de Weda ne déclare pas le gabarit VSM) ; sinon `urn:asipSante:modelesHorsProfils:2011`, comme Weda.
6. **Garde patient** : un CDA fourni doit porter l'INS de la demande (racine + extension), sinon `PatientMismatch`. Évite une enveloppe
   qui publie un patient que le document ne désigne pas.
7. **Identifiant du N1** : OID dérivé d'un UUID (`2.25.{uuid}`, ISO/IEC 9834-8), sans extension ; `setId` distinct, `versionNumber` 1.
8. **`uniqueId` du lot** : forme de Weda, suivie de 12 chiffres aléatoires (Weda y mettait l'identifiant interne du patient).
9. **PDF/A** : seule la signature `%PDF-` est contrôlée. La conversion en PDF/A reste à l'appelant (Weda convertit en PDF/A-1b avant).
10. **`README.TXT`** : sans adresse ni téléphone, absents de la demande.
11. **Schéma CDA du dépôt** : `CDA.xsd` ne compile pas sous .NET (`datatypes.xsd` remplacé par sa variante SDTC → `typeId` déclaré deux
    fois). Le N1 est validé contre `CDA_SDTC.xsd`.
12. **31 fichiers** dans la PR (plafond indicatif ~30) : 8 fichiers de tests neufs, 13 de code neuf, 10 retouches (obsolètes, Linux, CI).

### Pour le Manual Test Plan (étape 1)

```bash
cd interop/interop.cda.parser
IHEXDM_SAMPLES_DIR=/chemin/de/sortie dotnet test interop.cda.parser.sln --filter "FullyQualifiedName~ExportSampleArchives"
```

Produit `vsm-n3/IHE_XDM.ZIP` (VSM N3 synthétique) et `pdf-n1/IHE_XDM.ZIP` (PDF synthétique emballé en N1), pour le patient synthétique
`TESTXDM Camille`, INS `299991234567890` sous l'OID de test NIR (`1.2.250.1.213.1.4.10`). Sans la variable, le test est ignoré.

- **Passe qualité (/simplify)** :
  - Skipped (contract carrier) : `interop-cda` — §Q, tier 3
- **DOD self-check** :
  - [x] build 0 erreur ; tests 0 échec sous Windows (501) et Linux (500, docker + CI ubuntu) ; aucun `C:\` dans les tests
  - [x] N3 emballé tel quel, relu par `XDM.Load` à l'identique (`Package_CdaN3_*`)
  - [x] PDF → N1 valide (schéma + `XDM.Load`) : INS NIR de test, auteur, structure, `documentationOf`, `componentOf`, un
    `informationRecipient` par destinataire (`IheXdmPackagerN1Tests`)
  - [x] chaque ligne du tableau des métadonnées a son assertion, cda et pdf (`IheXdmPackagerMetadataTests`, 30 tests, 57 cas)
  - [x] deux appels → deux `uniqueId` de lot ; ordre et noms des entrées, `/`, sans BOM, sans Zip64 ; `&`, `<`, `"` → XML valide
  - [x] INS, identifiant national, identifiant de structure, code de type manquants → exception typée qui nomme le champ
  - [x] aucune écriture disque ; INS-C du gabarit absente de toute archive
  - [x] preuve rouge consignée (bouchon + 22 mutations attribuées)
  - [x] ancienne API `[Obsolete]` avec renvoi ; consommateurs listés
  - [x] package publié par la CI : **105.0.0**
  - [x] données synthétiques seulement, INS sous OID de test
  - Manual Test Plan (comparaison à Weda, validateur ANS, weda2) : **différé au HAG**
- **Plan de contrôle — à relire par l'humain avant push (règle d'or 7)** : `CLAUDE.md` (chemin `interop/interop.cda.parser` +
  avertissement) et `.claude/commands/start.md` (garde `git rev-parse --show-toplevel`), posés au `/start` de cette task après la
  création par erreur d'une branche sur le plan de contrôle (supprimée, locale et distante). Ajout de l'entrée
  `portabilite-linux` dans `conventions/csharp.md`.
- **Next step** : `/e2e task-366` (ni `api-mail`, ni `client-angular`, ni `client-mobile` touchés)

## E2E log

- **Skip propre** (2026-10-11) : aucune voie touchée. La task ne touche que `interop-cda` (package `Interop.Cda.Parser` 105.0.0,
  que l'api-mail ne consomme pas encore : son bump est porté par task-367). Ni `api-mail`, ni `client-mobile`, ni `client-angular`,
  ni `dtos-mss` : voies mobile et Angular non déclenchées (règle 1), porte non jouée, parité inchangée.
  Les parcours qui exerceront l'enveloppe (envoi d'un document Weda) relèvent de task-367.

## PRs

- `interop-cda` : https://github.com/codengine-technologies/interop.cda.parser/pull/10 — label `awaiting-human-merge`
  (package `Interop.Cda.Parser` 105.0.0 déjà publié depuis la branche, consommé par task-367)

## Code Review Summary

**APPROVED** — 31 fichiers relus, 0 bloquant, 4 suggestions.

- Validation `/review` : build 0 erreur ; tests 501 réussis / 0 échec / 6 ignorés (507, total cohérent). Linux : 500 / 0 / 6
  (docker) et étape `Test` verte en CI ubuntu (run 105).
- Règle 1b : sans objet (bibliothèque sans endpoint). Preuve équivalente : aller-retour par le vrai lecteur `XDM.Load` et
  validation au schéma CDA, chaque comportement vu rouge par mutation (22 mutations attribuées, `## Develop log`).
- Verrou e2e : aucune voie touchée, `## E2E log` en skip propre, accepté.
- Sécurité : XML lu sans DTD ni résolution externe ; aucune écriture disque ; journal sans identité ni contenu.
- Suggestions non bloquantes :
  1. `IntendedRecipients = null` (hors contrat nullable) → `NullReferenceException` au lieu d'une exception typée.
  2. Identifiant de structure non numérique → `sourceId` / `uniqueId` qui ne sont pas des OID stricts (forme de Weda).
  3. Supprimer l'ancienne API dans une task dédiée après task-367.
  4. Libellé de la classe 60 à confirmer au validateur de l'ANS.

## Timings

*(généré par `tools/timing/report.sh --task task-366 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 54 s | — | — | — | 1 repo (interop-cda) ; chemin interop corrigé |
| /develop | ok | 29 min 21 s | 2 (4.4 s) | 7 (1 min 50 s) | — | interop-cda 2B/7T, interop 105.0.0 ; 94 tests neufs ; Linux 41 rouges -> 0 |
| /e2e | skipped | 12 s | — | — | — | aucune voie touchée (interop-cda) |
| /review | ok | 1 min 49 s | 1 (1.2 s) | 1 (11 s) | — | interop-cda 1B/1T, PR interop #10 ; APPROVED |
| **Total cycle** | | **32 min 17 s** | **3 (5.7 s)** | **8 (2 min 02 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (47 s)
