# todo-task-390.md — Les lignes structurées d'un compte rendu HPRIM deviennent des résultats de biologie, avec alerte d'anomalie

**Repos**: api-mail, dtos-mss
**Dependencies**: task-389 (le document HPRIM existe)
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

## Manual Test Plan

1. Envoyer un HPRIM avec des lignes `RES|` — une hors normes sans indicateur, une avec indicateur `H`, une qualitative sans indicateur — et le rattacher : les deux premières sont signalées, pas la troisième ; le patient apparaît dans « anormaux non lus ».
2. Envoyer un partiel puis le complété du même dossier labo, sans les rattacher : les deux restent à intégrer, le premier marqué « partiel ».
3. Patient ayant une glycémie LOINC issue d'un CDA, plus une glycémie HPRIM : deux séries distinctes dans la biologie du patient.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — format historique HPRIM
- **Exigences DSR honorées** : non applicable — aucune exigence DSR sur le HPRIM ; règle de prudence : codes locaux jamais présentés comme LOINC
- **INS** : non applicable — aucun changement d'identité ; l'alerte ne vaut qu'après rattachement (task-391)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — HPRIM Santé, lignes `RES|` ; indicateurs d'anomalie sur la table HL7 commune avec le CDA
- **Tracé PGSSI-S** : aucun nouvel évènement
- **Consentement patient** : non applicable
- **Référentiels métier** : codes d'examen locaux au labo (ni LOINC ni NABM) ; indicateurs d'anomalie HL7 (L, H, LL, HH, A, AA, N)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé
