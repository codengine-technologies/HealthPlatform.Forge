# todo-task-390.md — Les lignes structurées d'un compte rendu HPRIM deviennent des résultats de biologie, avec alerte d'anomalie

**Repos**: api-mail, dtos-mss
**Dependencies**: task-389 (le document HPRIM existe), task-397 (lecture directe des messages d'une BAL déléguée sans stockage)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — sans cette US, un résultat HPRIM n'est qu'un texte : ni suivi dans la biologie du patient, ni alerte sur une valeur anormale.

> **Origine.** Séance `/po` du 2026-10-23 (parsing HPRIM dans api-mail), suite de task-389. Arbitrages : profondeur « texte + `RES|` », anomalie « indicateur labo, sinon normes », résultat partiel « affiché avec la mention partiel, remplacé par le complété ».

## Ce qui est établi

- **Format `RES|` (référence Weda, `D:\Workspaces\WD`, lecture seule)** — `Weda/FolderMedical/HprimForm.aspx.cs:2128-2286` découpe une ligne `RES|` sur `|` :
  `[1]` libellé · `[2]` code labo · `[3]` type (`N` numérique, `A` alphanumérique, `T` texte…) · `[4]` valeur 1 · `[5]` unité 1 · `[6]` norme basse 1 · `[7]` norme haute 1 · `[8]` indicateur d'anomalie · `[9]` statut · `[10]` valeur 2 · `[11]` unité 2 · `[12]` norme basse 2 · `[13]` norme haute 2.
  Variante UTF-16 sans BOM : `R\0E\0S\0|` (`WedaGlobal/BLL/Hprim.cs:63`). Valeurs nettoyées des ` . / *` en bordure (`Hprim.GoodCaractere`).
- **Anomalie côté Weda** (`WedaGlobal/BLL/Hprim.cs:1070-1098`) : comparaison de la valeur aux normes, l'indicateur `[8]` n'est **pas** utilisé ; les lignes de type `A` sont ignorées.
- **Anomalie côté api-mail (CDA)** : `CdaParsingService.FlaggedInterpretationCodes = ["L", "A", "H", "LL", "AA", "HH"]` → `MailMedicalDocumentBiology.IsFlagged`.
- **Modèle d'accueil** : `MailMedicalDocumentBiology` — `Section`, `Name`, `Code`, `CodeSystem`, `PrimaryValue/Unit/MinValue/MaxValue`, `Secondary*`, `InterpretationCode`, `Interpretation`, `DateResult`, `IsFlagged`. Pas de champ « statut ».
- **Remplacement de version existant** : `MailMedicalDocument.SupersededByDocumentId` (task-034, SC.CDA/INT.18), aujourd'hui alimenté par le `SetId`/`Version` du CDA — et **interdit sans INS** (task-193, `DetectDuplicateAsync`). Pour le HPRIM, il n'est appliqué qu'au rattachement (task-391).
- **Circuit d'écriture** : `CdaParsingService.ProcessBiologyResults` remplit `MailMedicalDocumentDto.BiologyResults` ; `MailRepository.AddBiologyResultsToDocument` (`MailRepository.cs:4843`) les copie en `MailMedicalDocumentBiology` et écarte ceux sans `Name`. Le lecteur HPRIM remplit la **même** liste ; l'écriture ne change pas, à la colonne « statut » près.
- **Alerte « anormaux non lus »** : `BiologyController` `GET abnormal-unread` → `IBiologyRepository.GetPatientsWithAbnormalUnreadResultsAsync` — liste de **patients**, donc seuls les documents rattachés y entrent.

## Décisions actées (humain, 2026-10-23)

1. **Anomalie** : indicateur du labo s'il est rempli (même liste que le CDA) ; sinon, valeur numérique hors de ses normes. Une valeur qualitative sans indicateur n'est jamais signalée.
2. **Résultat partiel** : rangé et exposé avec la mention « partiel ». Son remplacement par le compte rendu complété se fait **au rattachement** (task-391), jamais à la réception (task-193 — arbitrage du 2026-10-23).
3. (rappel task-389) Codes d'examen **locaux au labo**, jamais présentés comme du LOINC.
4. **BAL déléguée : affichage seul, aucune injection en base** (humain, 2026-10-25 — task-397,
   décision 8 de task-389). Pour un message d'une BAL déléguée (`shared/…`), les lignes `RES|` sont
   lues **sans stockage**, à l'affichage du détail : valeurs, unités, normes, statut, anomalie
   signalée.
   - **Aucun** résultat n'est stocké chez le délégataire : aucune ligne
     `MailMedicalDocumentBiology`, rien dans Redis, aucune entrée « anormaux non lus ».
   - Hors ligne, non consultable.

## Objective

Chaque ligne `RES|` d'un document HPRIM (task-389) devient un **résultat de biologie** du document, avec valeur, unité, normes, indicateur d'anomalie et statut, au même titre qu'un résultat de CR-BIO en CDA.

**US backend-only (justification)** : les résultats sont lus dans la biologie du patient par le test d'intégration ; leur affichage (mention « partiel », séries distinctes) est livré par task-392, qui porte le scénario e2e.

### Règles métier

- **Une ligne `RES|` = un résultat.** Ligne de moins de 8 champs ou sans libellé : ignorée ; le document et ses autres résultats sont conservés.
- **Correspondance champ → colonne** de `MailMedicalDocumentBiology` : `[1]` → `Name` ; `[2]` → `Code` ; `[4]`–`[7]` → `PrimaryValue`, `PrimaryUnit`, `PrimaryMinValue`, `PrimaryMaxValue` ; `[10]`–`[13]` → `Secondary*` ; `[8]` → `InterpretationCode` ; `IsFlagged` calculé à la lecture (décision 1) ; `[9]` → **nouvelle colonne statut**.
- **Système de codes** : **une valeur unique, définie une fois dans le contrat partagé (dtos-mss)** et reprise telle quelle par api-mail et les clients, signifiant « code local du labo émetteur » (jamais LOINC). Un résultat HPRIM ne rejoint pas la série LOINC du même examen.
- **Section** : les résultats d'un document HPRIM forment **une seule section**, intitulée « Résultats de laboratoire » (le HPRIM n'a pas de sections).
- **Seconde valeur** (champs 10–13) : rangée en valeur secondaire quand elle est présente.
- **Date** : date du résultat de l'en-tête HPRIM.
- **Anomalie** : décision 1. Décimales avec point ou virgule acceptées pour la comparaison aux normes.
- **Alerte « anormaux non lus »** : n'inclut un résultat HPRIM qu'une fois son document rattaché à un patient.
- **Statut** : **persisté** (nouvelle colonne de `MailMedicalDocumentBiology`, migration de la base mail) et exposé dans le contrat de biologie ; « partiel » visible. Vide pour les résultats CDA existants.
- **Pas de remplacement à la réception** : un partiel et son complété reçus avant rattachement restent tous deux visibles, le partiel marqué « partiel ». Le remplacement est livré par task-391.
- **Sans ligne `RES|`** : le document reste un document texte, sans résultat structuré.
- **BAL déléguée** (décision 4) : le lecteur `RES|` alimente aussi le **chemin de lecture
  directe** de task-397.
  - Les résultats d'un message délégué sont renvoyés dans le détail, avec `IsFlagged` et le statut
    calculés à la lecture.
  - Ils ne passent **jamais** par `AddBiologyResultsToDocument`.

## Gherkin

Voir `tests/Features/Mss/HprimStructuredResults.feature`.

## Definition of Done

- [ ] Build et tests verts : api-mail, dtos-mss (statut du résultat et valeur du système de codes « local labo » ajoutés au contrat de biologie, package publié)
- [ ] Migration de la base mail : colonne statut sur `MailMedicalDocumentBiology`, nullable, sans effet sur les résultats CDA existants
- [ ] Le lecteur HPRIM alimente `MailMedicalDocumentDto.BiologyResults` ; l'écriture passe par `AddBiologyResultsToDocument`, sans chemin parallèle
- [ ] ≥ 1 test unitaire par règle : découpage `RES|` (14 champs, ligne courte, sans libellé, seconde valeur absente, variante UTF-16), anomalie (indicateur seul, normes seules, qualitatif sans indicateur, normes vides, décimale à virgule), statut partiel / final / corrigé
- [ ] Test d'intégration de bout en bout (règle 1b) : un HPRIM à lignes `RES|`, rattaché, donne des résultats **lus dans la réponse réelle** de la biologie du patient — valeur, unité, normes, système de codes local, `IsFlagged` à vrai pour la valeur hors normes sans indicateur, statut « partiel » (cas nominal) ; un HPRIM sans `RES|` ne donne aucun résultat (cas d'échec) ; vu rouge
- [ ] Test d'intégration : résultat anormal **rattaché** → le patient est dans `abnormal-unread` ; **non rattaché** → absent
- [ ] Test d'intégration : un partiel puis son complété reçus avant rattachement restent tous deux actifs, aucun n'est remplacé ni signalé doublon (task-193)
- [ ] Test : un résultat HPRIM et un résultat LOINC du même examen restent deux séries distinctes
- [ ] Aucune valeur de résultat, libellé d'examen ni trait patient dans les journaux
- [ ] **BAL déléguée — test d'intégration de bout en bout** (banc de délégation de task-397) : un
      HPRIM à lignes `RES|` dans `shared/<A>`, ouvert par le délégataire B.
      - Le détail renvoie les résultats : valeur, unité, normes, statut « partiel », `IsFlagged` à
        vrai pour la valeur hors normes. Lu dans la réponse réelle.
      - La base de B contient **zéro** ligne `MailMedicalDocumentBiology` pour ce message.
      - Aucun patient n'apparaît dans `abnormal-unread` de B.
      - Aucune clé Redis de B ne porte ces valeurs.
      - Vu rouge (règle 1b).

## Manual Test Plan

1. Envoyer un HPRIM avec des lignes `RES|` — une hors normes sans indicateur, une avec indicateur `H`, une qualitative sans indicateur — et le rattacher : les deux premières sont signalées, pas la troisième ; le patient apparaît dans « anormaux non lus ».
2. Envoyer un partiel puis le complété du même dossier labo, sans les rattacher : les deux restent à intégrer, le premier marqué « partiel ».
3. Patient ayant une glycémie LOINC issue d'un CDA, plus une glycémie HPRIM : deux séries distinctes dans la biologie du patient.
4. **BAL déléguée.** Envoyer à Virginie un HPRIM avec une valeur hors normes, puis se connecter en
   Cyril, son délégataire, et ouvrir le message dans la boîte déléguée.
   - Les résultats sont lisibles, et la valeur anormale est signalée.
   - La base de Cyril ne contient aucun résultat de biologie pour ce message.
   - Le patient n'apparaît pas dans ses « anormaux non lus ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — format historique HPRIM
- **Exigences DSR honorées** : non applicable — aucune exigence DSR sur le HPRIM ; règle de prudence : codes locaux jamais présentés comme LOINC
- **INS** : non applicable — aucun changement d'identité ; l'alerte ne vaut qu'après rattachement (task-391)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées. Pour une BAL déléguée, lecture seule sans stockage chez le
  délégataire (décision 4, task-397).
- **Interop CI-SIS** : non applicable — HPRIM Santé, lignes `RES|` ; indicateurs d'anomalie sur la table HL7 commune avec le CDA
- **Tracé PGSSI-S** : aucun nouvel évènement
- **Consentement patient** : non applicable
- **Référentiels métier** : codes d'examen locaux au labo (ni LOINC ni NABM) ; indicateurs d'anomalie HL7 (L, H, LL, HH, A, AA, N)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Branches
> **Empilée sur task-389** : task-390 enrichit le document HPRIM que task-389 crée. La branche api-mail part de `feat/task-389-hprim-vers-document-biologie` (PR #315), pas de `develop` : **merger #315 avant la PR de task-390**. Une fois #315 mergée, la PR de task-390 se resynchronise par `git merge origin/develop` (règle 4).

- `api-mail` (pushed) : feat/task-390-hprim-lignes-structurees-resultats — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-390-hprim-lignes-structurees-resultats (base : `feat/task-389-hprim-vers-document-biologie` @ `6998e4fa`)
- `dtos-mss` (lazy) : aucune branche au /start — créée par /develop depuis `origin/develop` au premier contrat touché (CLAUDE.md, « Repo à branche PARESSEUSE »)
- Run `/forge` `forge-20261026-389-390` (staging `forge/staging-task-389-390-20261026`)

## Timings

*(généré par `tools/timing/report.sh --task task-390 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| /develop | ok | 8 min 28 s | 6 (36 s) | 13 (19 min 24 s) | — | api-mail 6B/13T, reprise revue : regroupement sans code, statut en-tête, anomalie affinée |
| /sonar | ok | 8 min 33 s | 2 (59 s) | 10 (13 min 07 s) | 4 (1 min 20 s) | 1 itération(s), api-mail 2B/10T, re-scan 86e110df : QG OK, 0 issue |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 16 min 22 s | — | — | — | e2e ×6 (31 min 17 s), rejeu après reprise de revue : 2 voies vertes, porte 0 |
| /review | ok | — | 2 (14 s) | 1 (4 min 17 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, APPROVED 2e passe, PR Dtos #49, Api.Mail #316; no start marker |
| **Total cycle** | | **33 min 40 s** | **10 (1 min 50 s)** | **24 (36 min 49 s)** | **4 (1 min 20 s)** | |

Autres commandes mesurées : nuget-wait ×1 (19 s)

## Develop log

> Journal de progression (point de reprise en cas de compaction).

- **Repos touchés** :
  - `dtos-mss`, branche paresseuse `feat/task-390-hprim-lignes-structurees-resultats`, `d5058633` publiée en **539.0.0** (CI run 539) :
    - `MailMedicalDocumentBiologyDto.Status` et `BiologyValueDto.Status` ;
    - `BiologyCodeSystems.LaboratoryLocal = "LABORATORY-LOCAL"` (la valeur unique du contrat) ;
    - `BiologyResultStatus` (`P`, `F`, `C`).
  - `api-mail`, branche empilée sur task-389, avec le bump `HealthPlatform.Dtos.Mss` 536 → 539.
- **Gherkin** : `tests/Features/Mss/HprimStructuredResults.feature` n'est pas créé. Le BDD est retiré (règle 1), et les scénarios sont couverts par des tests unitaires et d'intégration.

**Conception** :
- `src/Application/Hprim/HprimStructuredResults.cs` : une ligne `RES|` donne un `MailMedicalDocumentBiologyDto`. C'est un module pur, sans journal.
  - **Découpe** sur `|`, à la manière de Weda (`HprimForm.aspx.cs`). Une ligne de moins de 8 champs, ou sans libellé, est ignorée.
  - **Champs** : [1] `Name`, [2] `Code`, [4]–[7] valeur primaire, [8] `InterpretationCode` en majuscules, [9] `Status` en majuscules, [10]–[13] valeur secondaire.
  - **Valeurs** : rognées des espaces, points, barres et étoiles de bordure, comme Weda. Chaque valeur est **tronquée à la longueur de sa colonne**, car un texte libre de type `T` plus long ferait échouer l'écriture du message entier.
  - **Section** : unique, « Résultats de laboratoire ». **Système de codes** : `BiologyCodeSystems.LaboratoryLocal`. **Date** : celle du résultat de l'en-tête.
  - **Anomalie (décision 1)** :
    - l'indicateur du laboratoire, s'il est rempli, décide seul : un indicateur `N` n'est pas renversé par les normes ;
    - sinon, une valeur numérique hors de ses normes est signalée. Le point et la virgule sont acceptés, une norme seule suffit, et la valeur secondaire compte aussi ;
    - une valeur qualitative, ou sans normes, n'est jamais signalée.
  - **Écart avec Weda** : Weda ignore l'indicateur et ne regarde que les normes ; la décision 1 fait l'inverse. `GoodCaractere` (correction d'un mauvais décodage) n'est pas repris : la détection d'encodage de task-389 décode correctement.
- `src/Application/Helpers/BiologyInterpretation.cs` : la liste HL7 `L, A, H, LL, AA, HH`, désormais **partagée** avec `CdaParsingService`, qui avait sa propre copie.
- `HprimReader.DetectEncoding` : **UTF-16 sans préambule**, reconnu à ses octets nuls (au moins un quart de la sonde ; petit-boutiste si les nuls sont aux positions impaires). C'est la variante `R\0E\0S\0|` de Weda. Sans cela, le fichier passait pour de l'UTF-8 valide, avec un nul entre chaque caractère.
- `HprimMedicalDocuments` : `BiologyResults` et `HasBiologyResults` sont remplis par le lecteur. Le chemin de lecture déléguée (task-397) l'emprunte tel quel, donc les résultats sont calculés à l'affichage et jamais écrits.
- **Persistance** : circuit inchangé (`AddBiologyResultsToDocument`), plus la colonne `Status`. Un statut vide est stocké `null`, comme pour un CDA.
  - Migration FluentMigrator `20261026120000_AddBiologyResultStatus` : `MailMedicalDocumentBiology.Status varchar(16) NULL`, sans valeur par défaut, avec descente.
  - Configuration EF : `HasMaxLength(16)`.
- **Lecture** : `Status` est projeté par le contenu du message, l'en-tête, les documents du patient et la biologie du patient (`BiologyRepository`).
- **Journaux** : le `LogDebug` des résultats écartés (sans libellé) écrivait `PrimaryValue` et `PrimaryUnit`. Ces deux champs sont retirés, conformément à la DoD « aucune valeur de résultat dans les journaux ».
- **Écarté** :
  - élargir la liste des valeurs du widget « anormaux non lus » aux valeurs signalées sans code. Un test d'infrastructure fige la règle voulue « signalée hors L/H/A : comptée, jamais listée ». Le patient y entre bien, par le compteur. L'affichage revient à task-392 ;
  - ajouter le système de codes à la clé de regroupement de `BiologyRepository`. Un document ne mélange pas deux systèmes : la séparation tient au document et au `CodeSystem`, et le test d'intégration la prouve.

**Tests et preuves**
- **Unitaires** (`HprimStructuredResultsTests`, 44 cas) :
  - 14 champs ; seconde valeur absente ; 7 champs ; sans libellé ; autres lignes ; ordre ;
  - bordures de valeur ; troncature ;
  - indicateurs `H`, `L`, `HH`, `A` ; `N` non renversé ; normes seules ; décimale à virgule ; qualitatif ; normes vides ; norme haute seule ; seconde valeur ;
  - statuts `P`, `p`, `F`, `C`, vide, champ absent ;
  - document avec et sans `RES|` ;
  - UTF-16 sans BOM, petit et gros-boutiste ;
  - `BiologyInterpretation`.
- **Journal sans donnée de santé** : `Process_LogsNoHealthData…` cherche aussi le libellé, la valeur et l'unité d'un résultat structuré.
- **Intégration (règle 1b)** : `HprimStructuredResultsEndToEndTests`, 5 tests. Le message passe par Dovecot, puis `enrich/sync`, puis la vraie route `attach-patient`, et les résultats sont lus dans les réponses réelles de `GET biology/patients/{id}`, `GET biology/abnormal-unread` et `emails/content` :
  - nominal : valeur, unité, normes, code local, `IsFlagged` hors normes sans indicateur et avec `H`, qualitatif non signalé, seconde valeur, statut « partiel » ;
  - sans `RES|` : aucun résultat ;
  - « anormaux non lus » : absent avant rattachement, présent après, `AbnormalCount = 2` ;
  - partiel puis complété avant rattachement : deux documents actifs, ni doublon ni remplacement, statuts `P` et `F` ;
  - même examen en HPRIM et en LOINC (CR-BIO de microbiologie, rattaché par son INS) : deux séries, deux documents, deux systèmes de codes.
- **Migration** : `BiologyResultStatusMigrationTests` (nullable sans défaut, 16 caractères ; descente puis remontée).
- **BAL déléguée** : `DelegationEndToEndTests.ADelegatedHprimWithResLines_…`. Le détail renvoie valeur, unité, normes, `IsFlagged` et statut « partiel » ; la base du délégataire contient 0 ligne de biologie et 0 document ; « anormaux non lus » est vide ; Redis ne contient rien hors cache J. Les marqueurs sont propres au test, car Redis est partagé par la collection.
- **Rouge** :
  - **sur le code d'avant le branchement** (lecteur écrit, non branché) : 4 tests d'intégration rouges, « Assert.Single() Failure: The collection was empty », « Sequence contains no matching element », « Expected: 2 Actual: 1 » ;
  - **par mutation** (fichier restauré par copie) :

  | # | Mutation | Tests rouges |
  |---|---|---|
  | MF | l'anomalie par les normes est ignorée | nominal, « anormaux non lus », délégué |
  | MS | le statut n'est pas persisté | nominal, partiel/complété |
  | MC | le code local est présenté comme LOINC | nominal, séries distinctes, délégué |
  | MW | les lignes `RES|` ne sont pas lues | 5 tests sur 6 (dont le délégué) |
- **Piège** : un script Python en heredoc a écrit trois **octets nuls réels** dans un commentaire (`R\0E\0S\0|`). `git diff --stat` a révélé le fichier en `Bin`, et il a été corrigé. C'est une récidive du piège déjà en mémoire (`script-node-backslash-b-backspace-invisible`), désormais complétée de ce signe et de son contrôle.

### Passe qualité §Q (`/simplify`, 4 relectures : réutilisation, simplification, efficacité, altitude)

**Appliqué** :
- `UseCaseHttpHost.AddProductionBiology` : l'enregistrement de la biologie existait en trois copies (`PatientFolderEndToEndTests`, `HprimStructuredResultsEndToEndTests`, `DelegationEndToEndTests`). Les noms qualifiés de la délégation ont disparu avec lui.
- **Longueurs des colonnes de biologie déclarées une seule fois**, en constantes de l'entité (`MailMedicalDocumentBiology.Lengths.cs`). La configuration EF et la troncature du lecteur HPRIM s'y réfèrent ; la migration garde ses littéraux, comme toute migration figée.
- `HprimReader.Utf16WithoutPreamble` : le comptage des octets nuls passe par `nulls[i & 1]`.
- `HprimSamples.ResLine` : une interpolation au lieu de deux branches.

**Écarté** :
- **Harnais `Server` commun** aux tests de cas d'usage : 8 copies, toutes antérieures à la task, hors du diff.
- **Helpers partagés des tests de migration** : 5 copies, motif antérieur.
- **Troncature à la frontière d'écriture** (`AddBiologyResultsToDocument`) pour tous les formats : cela change le comportement du CDA (une valeur trop longue serait tronquée au lieu de faire échouer l'écriture), donc hors d'une passe qualité. → **Suivi** proposé : borner les valeurs à la frontière d'écriture pour toutes les sources.
- **`IsFlaggedCode` insensible à la casse** : changement de comportement pour le CDA.
- **Micro-gains d'efficacité** (double découpe du texte, comptage vectorisé) : négligeables au volume d'un HPRIM, et seulement sur les mails HPRIM. Pour les mails sans HPRIM, le chemin chaud est inchangé.
- **Re-validation après §Q** : build 0 erreur ; suites vertes, 7 119 tests (domain 264, infrastructure 701, api 1 347, application 3 785, intégration 1 022 + 16 ignorés).
- **Commits api-mail** : `d18766c5` (feature), `36578190` (passe qualité). Poussés. **dtos-mss** : `d5058633`, poussé et publié en 539.
- **DoD, auto-contrôle** :
  - [x] build et tests verts sur api-mail et dtos-mss ; statut et système de codes « local labo » dans le contrat, publié en 539 ;
  - [x] migration : colonne `Status` nullable, sans défaut, prouvée par `BiologyResultStatusMigrationTests` ;
  - [x] lecteur branché sur `BiologyResults`, écriture par `AddBiologyResultsToDocument` ;
  - [x] tests unitaires : découpage (14 champs, ligne courte, sans libellé, seconde valeur absente, UTF-16), anomalie (indicateur seul, normes seules, qualitatif, normes vides, virgule), statuts P/F/C ;
  - [x] intégration nominal + sans `RES|`, vue rouge ;
  - [x] « anormaux non lus » : absent sans rattachement, présent après ;
  - [x] partiel puis complété : deux documents actifs, aucun doublon ;
  - [x] HPRIM et LOINC du même examen : deux séries ;
  - [x] journaux : aucune valeur, aucun libellé (test étendu ; `LogDebug` du dépôt purgé de la valeur) ;
  - [x] BAL déléguée, vue rouge (MW, MF, MC).

### Reprise après la 1ʳᵉ revue de `/review` (CHANGES REQUESTED)

**❌ 1 — des résultats sans code fusionnaient dans la biologie du patient.**
- **Cause** : `BiologyRepository` regroupe par `(Section, Code)` et prend le libellé du premier. Le code d'analyse est facultatif en HPRIM, et toutes ses lignes partagent la même section. « Sodium » 140 et « Potassium » 4,2, tous deux sans code, donnaient un seul résultat « Sodium » à deux valeurs.
- **Correction** : la clé de regroupement inclut le libellé quand le code est vide. Rien ne change pour un CDA, qui a toujours un code.
- **Test d'intégration** : `TwoResLinesWithoutCode_StayTwoResultsInThePatientBiology`, **vu rouge** sur le code d'avant (« Assert.Single() Failure: The collection did not contain any matching items »). `PatientFolderEndToEndTests` reste vert.
- **Prévention** : `conventions/csharp.md#cle-de-regroupement-champ-facultatif`.

**❌ 2 — le statut n'était lu que par le contenu et la biologie du patient.**
- **En-têtes** (`GET folders/INBOX/emails/{uid}` → `Content.MedicalDocuments`, lignes signalées seules) : le test nominal y lit désormais le statut `P`. **Mutation MH** (statut retiré de la projection en-tête) : rouge, « Expected: "P" Actual: "" ».
- **`PatientRepository.GetMedicalDocumentsByPatientIdAsync`** : aucune route ne l'atteint. Les contrôleurs passent par `PatientFolderService` et `GetMailsByPatientIdAsync`. Ce n'est donc pas un comportement atteignable par un endpoint, et la règle 1b ne s'y applique pas. La projection est gardée par cohérence.

**Suggestions adoptées** (décision 1, fidélité à Weda) :
- **Type** : seule une ligne de type `N` (ou de type vide) se compare aux normes. Une ligne `A` à valeur numérique n'est jamais signalée sans indicateur.
- **Normes `0 | 0`** : une absence de normes, comme chez Weda.
- **Indicateur hors table HL7** (`*`, `+`…) : il ne décide pas, et les normes reprennent la main. Seuls `N, L, H, LL, HH, A, AA` décident.
- **Point de tête conservé** : « .5 » vaut 0,5 (Weda le retirait et lisait 5). Seul le point de fin est retiré.
- **Tests unitaires** : 7 cas ajoutés (type A, type vide, `0|0`, indicateurs inconnus, point de tête et de fin).

**Non adopté** :
- **Ligne sans valeur gardée.** La spécification n'écarte que les lignes courtes et sans libellé. Écart avec Weda, signalé au HAG.
- **Valeurs signalées sans code HL7, comptées mais non listées par « anormaux non lus »** : la règle existante est figée par un test d'infrastructure. task-391 et task-392 ne sont **pas encore écrites** dans `tasks/`. → **Suivi** : à prévoir dans task-392, avec `api-mail` dans ses `**Repos**:`.

- **Suites après reprise** : 7 127 tests verts (domain 264, infrastructure 701, api 1 347, application 3 792, intégration 1 023 + 16 ignorés).
  - `E2eUnattachedXdmTests.TheSeededCda_CarriesATrappedCell_ThatTheCdaPipelineDoesNotRender` (api) a été **rouge une fois** sur 7 runs complets.
  - Il est vert isolé (2/2) et en projet complet (2/2).
  - C'est un test de parsing CDA pur : la task n'y touche que par l'extraction de `BiologyInterpretation`, sans changement de comportement.
  - → Instable à suivre, signalé dans le rapport. Le message d'échec n'a pas été capturé par le filtre.
- `NoBreakSpace` : l'espace insécable littéral devient l'échappement `\u00A0`, plus lisible.

## Sonar log

Analyse complète `healthplatform-api-mail` (SonarQube 9.9.8 local, `sonar.login`), sur la branche `feat/task-390-…` à `36578190`.

- **1ʳᵉ analyse** : **QG OK, 0 issue** sur le nouveau code, aucun hotspot, new coverage 95,1 %. Les cinq suites sont vertes (7 119).
- **2ᵉ analyse** (`86e110df`, correctif de la revue de `/review`) : **QG OK, 0 issue**, new coverage 95,1 %, KPIs inchangés. Suites vertes (7 127).
- **Phase 1 (nouveau code)** : rien à corriger. Les consignes CA1861 et S3267 de `conventions/csharp.md` ont été appliquées d'emblée : les tableaux attendus des tests sont dans des champs `static readonly`. Aucune récidive.
- **Phase 2 (legacy)** : rien à faire (0 bug, 0 vulnérabilité, 0 smell sur le projet).

### KPIs qualité (baseline → final)

| Métrique | Baseline (`6998e4fa`, task-389) | Final (`86e110df`) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | 95,0 % | 95,1 % | +0,1 pt |
| New bugs / vulnérabilités / smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Bugs / Vulnérabilités / Smells (projet) | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,5 % | 97,5 % | = |
| Duplication | 0,3 % | 0,4 % | +0,1 pt (harnais de tests de cas d'usage : la copie du `Server`, écartée de §Q, est déjà relevée) |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log
- skipped — `client-angular` non listé dans `**Repos**:` et aucun fichier Angular écrit par `/develop` pour cette task.

## Lint mobile log
- skipped — `client-mobile` non touché par la task.

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 [angular], posée le 2026-10-09 (17 jours), correction due par **task-350**.
> ⚠️ **Divergence à retirer** : E2E-MAILBOX-002 [angular] (task-395). Le client weda2 est revenu à la version du catalogue ; la décision appartient à l'humain.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail (`86e110df`, après la reprise de revue) et dtos-mss touchés ; client-mobile sur `develop` à jour | ✅ verte (rejouée) | 50 verts, 0 flaky, 0 rouge, 0 quarantaine | 7 min 53 s |
| angular | api-mail (`86e110df`) et dtos-mss touchés ; weda2 sur son checkout courant | ✅ verte (rejouée) | 59 verts, 0 flaky, 0 rouge, 1 quarantaine (verte) | 8 min 4 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (inchangé par la task : US backend, aucun parcours médecin modifié ; l'affichage et E2E-BIO-003 relèvent de task-392)
- Contrat : `dtos-mss` 539 n'ajoute que des champs ; les clients consomment leurs propres types TypeScript, inchangés
- Porte : **code 0**, rendue par ce run
- Historique : première passe verte sur `36578190` (7 min 38 s et 7 min 42 s). Les deux voies ont été **rejouées** sur `86e110df`, le correctif de la revue, pour que `/review` valide exactement le code testé.
- Flaky : aucun
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché)
- Démontage : complet. Les ports 5052, 8100, 4200, 3993, 3465 et 3143 sont libres, aucun conteneur e2e ne tourne.

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
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-DELEG-001 | 1 | headless | Voir la BAL déléguée dans sa section, repliée sous la BAL principale, et lire un compte rendu | ✅ | ✅ |
| E2E-DELEG-002 | 1 | headless | Supprimer un message délégué vers la corbeille de la délégante, puis le restaurer | ✅ | ✅ |
| E2E-DELEG-003 | 1 | headless | Dans une BAL déléguée, seuls les gestes de gestion sont proposés | ✅ | ✅ |
| E2E-DELEG-004 | 1 | headless | La délégation retirée pendant la consultation ramène à sa propre réception | ✅ | ✅ |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/49 — label `awaiting-human-merge` (publié en 539.0.0) — **à merger en premier**
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/316 — label `awaiting-human-merge` (head `86e110df`) — **empilée sur #315 (task-389) : merger #315, puis #49, puis celle-ci** (après `git merge origin/develop`)

## Code Review Summary

**Verdict : APPROVED en 2ᵉ passe** (revue indépendante, en lecture seule).

- **1ʳᵉ passe : CHANGES REQUESTED.**
  - ❌ 1 : deux examens sans code fusionnaient dans la biologie du patient, car le regroupement se faisait par `(Section, Code)` alors que le code est facultatif en HPRIM. Corrigé par `86e110df`, avec un test d'intégration vu rouge. Prévention : `conventions/csharp.md#cle-de-regroupement-champ-facultatif`.
  - ❌ 2 : le statut des en-têtes n'était pas prouvé. Il est désormais lu dans la réponse (mutation MH). `PatientRepository.GetMedicalDocumentsByPatientIdAsync` n'est atteint par aucune route : code mort, hors règle 1b.
  - Suggestions adoptées : type `N` seul comparé aux normes, normes `0|0`, indicateur hors table HL7, point de tête.
- **2ᵉ passe : APPROVED.** Suggestion restante : les branches affinées de l'anomalie sont prouvées par des tests unitaires seulement ; leur branchement est prouvé par l'intégration (MF).
- **À arbitrer au HAG** (encadré dans la PR) :
  - la ligne `RES|` sans valeur gardée ;
  - l'indicateur hors table qui laisse décider les normes ;
  - les valeurs signalées par les normes, comptées mais non listées par « anormaux non lus » (suivi task-392, à écrire).

| Comportement atteignable par un endpoint | Test d'intégration | Rouge |
|---|---|---|
| Biologie du patient : valeur, unité, normes, code local, `IsFlagged`, seconde valeur, statut | `HprimStructuredResultsEndToEndTests.AnAttachedHprimWithResLines_…` | avant branchement ; MF, MS, MC, MW |
| Statut dans la réponse des en-têtes | idem | MH |
| Deux examens sans code → deux résultats | `TwoResLinesWithoutCode_…` | code d'avant le correctif |
| Sans `RES|` → aucun résultat | `AnAttachedHprimWithoutResLines_…` | témoin (MW) |
| « Anormaux non lus » après rattachement seulement | `AnAbnormalHprimResult_…` | avant branchement ; MF |
| Partiel / complété : actifs, statuts P et F | `APartialThenItsCompletedResult_…` | avant branchement ; MS |
| HPRIM et LOINC : deux séries | `AnHprimResultAndALoincResultOfTheSameExam_…` | avant branchement ; MC |
| BAL déléguée : affichés, rien persisté | `DelegationEndToEndTests.ADelegatedHprimWithResLines_…` | MW, MF, MC |
| Colonne `Status` | `BiologyResultStatusMigrationTests` | test de schéma |
