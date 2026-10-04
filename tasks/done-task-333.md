# todo-task-333.md — Un mail n'est marqué « analysé » que si ses documents médicaux ont réellement pu être lus : fin des pertes silencieuses de comptes rendus

**Repos**: api-mail, interop-cda
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — un incident technique (disque, répertoire de travail, archive supprimée entre écriture et lecture) peut faire enregistrer un mail **sans ses comptes rendus CDA, définitivement** : plus de document, plus de rattachement patient, plus de biologie, sans aucun signal.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-09** et **AUD-16**). Rappel : la ligne
> `MailContents` est le **marqueur d'enrichissement** — une ligne écrite à tort écarte le mail de toute
> analyse future (mémoire « MailContents = marqueur d'enrichissement », tasks 222/225/293).

## Ce qui est établi (develop @ `14d58398`)

**Repli de lecture (AUD-09, ouvert par `14d58398`)** — `ImapService.cs:3253-3292, 4573-4576, 4613-4621` :
depuis ce commit, toute lecture `WithContent` d'un mail « en-têtes seuls » passe par un repli qui
fetche le message, extrait les archives IHE-XDM, construit le DTO et **écrit `MailContents`**
(`mailRepository.AddNewMail`). Appelants : liste des noms de pièces jointes (`ServiceImplementation.cs:178`),
export PDF (`MailExportController.cs:109`), résumé IA (`EmailSummaryService.cs:52`), annule-et-remplace
(`MailCancellationService.cs:95`). Ce chemin **ne teste pas `HasTechnicalFailure`** (contrairement à
`ImapService.cs:2048` et `BackgroundEnrichmentProcessor.cs:130`) et **ne prend pas `LockEnrichPersistAsync`**
— course possible avec une Phase B d'enrichissement sur le même UID (`IX_MailContents_MailId` non unique).
Il coûte aussi un fetch complet et une analyse CDA pour une simple liste de noms.

**Panne hôte pendant l'extraction (AUD-16)** — `CdaParsingService.cs:40-90`, `interop/…/XDM.cs:27-140` :
`XDM.Load` attrape **toute** exception et rend `false` (disque plein pendant `ExtractToDirectory`, droits,
zip supprimé entre l'écriture et l'analyse) → `ParseIheXdmZip` rend `[]` → mail persisté avec sa ligne
de contenu et `HasMedicalDocuments = false`. task-293 ne classe comme technique que **l'écriture** du zip.
Aggravants : aucune borne de taille ni de ratio de décompression (bombe zip saturant le répertoire de
travail partagé par tous les praticiens) ; `IheXdmScratchDirectory.Sweep()` ne purge pas les
sous-répertoires `Root/{guid}/` ; avec plusieurs réplicas sur un hôte, le balayage au démarrage de l'un
peut supprimer le zip d'un autre entre écriture et lecture.

## Objective

Que le marqueur « analysé » ne soit posé **que si** les archives médicales du mail ont été lues sans
incident technique ; qu'un incident technique laisse le mail **à traiter** (et le signale) ; qu'une
lecture ne déclenche jamais d'écriture d'enrichissement hors des gardes et du verrou existants ; et
qu'une archive anormale ne puisse pas saturer l'hôte.

### Périmètre

1. **Repli de lecture** : soit il ne persiste plus rien (lecture pure, le contenu servi sans écrire le
   marqueur), soit il applique **exactement** la garde task-293 (`HasTechnicalFailure` → pas de
   persistance, indisponibilité 503) **et** prend le verrou de persistance d'enrichissement. Choix
   justifié par `/develop` ; la liste des noms de pièces jointes ne doit pas déclencher d'analyse CDA.
2. **`interop-cda`** : `XDM.Load` / `ParseIheXdmZip` distinguent **archive invalide** (contenu : le mail
   est analysé, sans document) de **panne hôte** (disque, droits, fichier absent : remontée comme
   échec technique). Publication NuGet et bump du consommateur.
3. **Bornes d'archive** : taille décompressée totale, nombre d'entrées et ratio de compression bornés
   (valeurs configurables, défauts documentés) ; dépassement → mail signalé, non marqué « analysé ».
4. **Répertoire de travail** : le balayage purge aussi les sous-répertoires d'extraction ; il ne
   supprime jamais une archive en cours d'usage par un autre réplica (âge minimal, ou répertoire propre au processus).

### Hors périmètre

- La libération des archives par la synchro de fond (task-334).
- Le rejeu des mails déjà marqués à tort (à évaluer après correctif : inventaire des mails porteurs
  d'un `IHE_XDM.ZIP` sans document — requête à rédiger dans le task file, reprise par une US dédiée si nécessaire).

## Definition of Done

- [ ] Build passes (0 errors) — `api-mail` et `interop-cda` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file) :
  - [ ] lecture `WithContent` d'un mail « en-têtes seuls » dont l'extraction échoue pour cause technique → sur le code actuel `MailContents` est écrit ; après correctif **aucune** écriture, le mail reste à enrichir
  - [ ] `XDM.Load` sur une panne hôte simulée (répertoire en lecture seule / fichier supprimé) → sur le code actuel `false` indistinct ; après correctif échec technique distinct
- [ ] Test : archive invalide (zip corrompu) → le mail est analysé sans document (comportement actuel conservé)
- [ ] Test : archive dépassant la borne de taille décompressée ou de ratio → refusée, mail non marqué, événement journalisé
- [ ] Test : liste des noms de pièces jointes d'un mail non enrichi → aucune analyse CDA déclenchée
- [ ] Test : repli de lecture concurrent d'une Phase B sur le même UID → une seule ligne de contenu
- [ ] Test : le balayage purge un sous-répertoire d'extraction orphelin et épargne une archive récente
- [ ] `interop-cda` publié via la CI, `api-mail` bumpé
- [ ] Non-régression task-293 : tests existants de classement technique verts ; test d'intégration `GetEmailAsync_WithFullContent_ShouldReturnCompleteEmailAsync` vert
- [ ] Aucun contenu CDA, INS ni nom de fichier patient dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc) ; seeder une boîte avec des mails porteurs d'`IHE_XDM.ZIP` réels (skill `loadtest-skill`).
2. Afficher la liste de la boîte sans ouvrir les mails (lignes « en-têtes seuls »).
3. Rendre le répertoire de travail IHE-XDM non inscriptible, puis ouvrir un de ces mails → **Attendu** : message « réessayez » (503), le mail n'est **pas** marqué analysé. Rétablir les droits, rouvrir → les documents CDA apparaissent et le patient est rattaché. Avant : le mail reste définitivement sans document.
4. Déposer (banc) un mail avec une archive anormalement volumineuse à la décompression → refus journalisé, les autres mails continuent d'être traités.
5. Vérifier qu'exporter en PDF un mail non enrichi ne crée pas de ligne d'enrichissement (requête SQL de contrôle fournie dans le task file).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : intégration des documents CDA reçus par MSSanté — aucun document reçu ne doit être perdu sans signal
- **INS** : inchangé — l'INS est lue du CDA par le chemin existant ; la US évite qu'un document soit perdu avant cette lecture
- **Authentification PS** : PSC / e-CPS inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : IHE-XDM (`IHE_XDM.ZIP`), CDA r2 — lecture par `interop-cda` ; distinction archive invalide / panne hôte
- **Tracé PGSSI-S** : échec technique d'extraction et archive hors bornes journalisés (sans contenu ni nom patient) ; `MedicalDocumentProcess` inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — répertoire de travail des archives dans le périmètre HDS ; purge renforcée
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : fix/task-333-marqueur-analyse-garde-technique — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-333-marqueur-analyse-garde-technique (depuis `origin/develop` @ `9452245c`)
- `interop-cda` (pushed) : fix/task-333-marqueur-analyse-garde-technique — https://github.com/codengine-technologies/interop.cda.parser/tree/fix/task-333-marqueur-analyse-garde-technique (depuis `origin/develop` @ `8f40526`)

## Develop log

### Plan et ordre

`interop-cda` d'abord (contrat consommé par NuGet), puis `api-mail`. Aucun contrat DTO touché, donc pas de branche `dtos-mss`. Aucun client touché.

### interop-cda — `09159dd`, publié en **Interop.Cda.Parser 101.0.0** (run 101)

- `XdmLoadFailure` (`None`, `InvalidArchive`, `HostFailure`, `LimitExceeded`) exposé par `XDM.Failure`. Évolution additive : `Load(fichier, xsd)` garde sa signature et délègue à `Load(fichier, xsd, XdmExtractionLimits)`.
- **Panne de l'hôte** : archive absente à la lecture, schéma absent, répertoire d'extraction impossible à créer, répertoire disparu en cours d'analyse, `IOException` / `UnauthorizedAccessException` (y compris à la lecture d'un CDA, que `CdaValidator` avalait comme une validation ratée).
- **Archive invalide** : zip indécodable, entrée hors de son répertoire ou au nom invalide. `ExtractToDirectory` rapportait ce dernier cas en `IOException`, le type désormais réservé à l'hôte : il est remplacé par `XdmArchiveExtractor`.
- **Bornes** (`XdmExtractionLimits`) : 1 000 entrées, 256 Mio décompressés, rapport de 100 au-delà de 1 Mio. Contrôlées sur les tailles déclarées, puis sur les octets réellement décompressés (un en-tête peut mentir). Le dépassement supprime l'extraction partielle.
- Tests : `XdmLoadFailureTests` (10). Suite : 407 verts, 5 ignorés.
- **Preuves par mutation** :
  - A, `IsHostFailure` qui rend `false` : `Load_ExtractionDirectoryCannotBeCreated_IsAHostFailure` rouge (`Expected: HostFailure, Actual: InvalidArchive`) ;
  - B, retour à `ExtractToDirectory` sans bornes : 4 rouges (bombe, entrées, taille : `Actual: True` ; entrée évadée : `Actual: HostFailure`).

### api-mail — `a269a40c` (bump 101.0.0 et lock files), `2dbf6735` (correctif)

- **AUD-16** : `CdaParsingService` lève `IheXdmTechnicalFailureException` (cause `Io` ou `ArchiveLimitExceeded`) quand `XDM.Failure` vaut `HostFailure` ou `LimitExceeded`, et compte l'échec (`mssante_ihe_xdm_extraction_failures_total`, nouvelle étiquette `limit_exceeded`). Une archive invalide rend toujours `[]` (comportement conservé).
  - Phase B (`PersistEnrichedBatchAsync`) : l'UID rejoint les échecs techniques. Rien n'est persisté, le lot rend le 503 `DOCUMENT_PROCESSING_UNAVAILABLE` (même voie que la garde d'extraction de task-293).
  - Synchro de fond (`BackgroundEnrichmentProcessor`) : le mail est laissé en attente, avec un avertissement au lieu d'une erreur générique.
  - Bornes configurables : `IheXdmOptions`, section `IheXdm`, défauts de `XdmExtractionLimits`, documentés sur la classe. Aucun défaut posé dans `appsettings.json` ni dans l'AppHost : les défauts du code s'appliquent partout.
- **AUD-09, choix : lecture pure.** `ReadEmailWithoutPersistingAsync` remplace `ProcessEmailSummaryAsync`. Le repli n'écrit plus rien, ni ligne de contenu ni message `AddNewMail`. Une panne technique d'extraction (`HasTechnicalFailure`) ou d'analyse y rend un 503 `DOCUMENT_PROCESSING_UNAVAILABLE`, au lieu de servir un message amputé de ses documents.
  - **Pourquoi pas « garde + verrou + persistance »** : le plan de test manuel exige à l'étape 5 qu'un export PDF ne crée aucune ligne d'enrichissement. Une lecture qui n'écrit pas ne peut ni poser le marqueur à tort, ni entrer en course avec la Phase B. Le marqueur reste l'affaire du seul enrichissement, qui porte déjà la garde et le verrou.
  - **Coût assumé** : un export ou un résumé d'un mail pas encore analysé relit le serveur à chaque appel. C'est rare, l'enrichissement suivant le liste presque aussitôt. Le résumé IA d'un mail non analysé n'est pas mis en cache (`UpdateEmailSummaryAsync` ne trouve pas de ligne de contenu) : il sera recalculé.
  - Une lecture `Header` sans ligne en base construit désormais l'en-tête sans extraction. La liste des noms de pièces jointes (`GetAttachmentFileNamesAsync`) lit `Header` : plus aucune analyse CDA.
  - Le dossier IMAP est refermé dans un `finally`, sur tous les chemins.
- **Répertoire de travail** : `Sweep()` purge aussi les sous-répertoires d'extraction orphelins, et n'efface rien de plus récent que `SweepMinimumAge` (1 h). Un autre réplica du même hôte ne perd plus son archive entre l'écriture et la lecture.
- `UnavailableException` gagne un constructeur `(message, code, inner)`, pour garder le code machine sur une panne remontée d'une couche basse.

### Règle 1b — `ArchiveAnalysisMarkerEndToEndTests` (6 tests HTTP)

Vraie pile : serveur HTTP de test, vrais contrôleurs, vrai `ImapService`, vraie extraction, vrai parseur CDA (archive CDA réelle du corpus), vrai dépôt sur la base PostgreSQL du praticien, IMAP Dovecot. La panne d'hôte est injectée par `IheXdmFaultInjection` (fixture `UseCases`, indexée par boîte) : l'archive écrite est retirée avant sa lecture, comme le faisait le balayage d'un autre réplica. Chaque test affirme sa prémisse (ligne « en-têtes seuls » créée, extraction effectivement demandée).

| Comportement | Test | Rouge sur le code d'avant |
|---|---|---|
| Export d'un mail non analysé dont l'archive est illisible → 503 `DOCUMENT_PROCESSING_UNAVAILABLE`, aucune ligne de contenu | `ExportingAMailNotYetAnalysed_WhenItsArchiveCannotBeRead_Returns503_AndWritesNothing` | `Attendu 503, reçu 200 : %PDF-1.4` |
| Export d'un mail non analysé → 200 PDF sans ligne de contenu ; l'enrichissement le constitue ensuite avec ses documents | `ExportingAMailNotYetAnalysed_ServesItWithoutMarkingItAnalysed_AndItsAnalysisStillHappens` | `Expected: 0, Actual: 1` |
| Archive des pièces jointes d'un mail non analysé → 200, zéro extraction, aucune ligne de contenu | `DownloadingTheAttachmentsOfAMailNotYetAnalysed_TriggersNoArchiveAnalysis` | `Expected: 0, Actual: 1` (une extraction) |
| Lecture concurrente d'une analyse sur le même UID → une seule ligne de contenu | `ReadingAMailWhileItIsBeingAnalysed_LeavesASingleContentRow` | `Expected: 1, Actual: 2` (la course s'est produite) |
| Enrichissement, archive balayée avant lecture → 503, aucune ligne ; hôte rétabli → analysé avec ses documents | `EnrichingAMail_WhoseArchiveVanishesBeforeItIsRead_Returns503_LeavesItPending_ThenAnalysesItOnceRestored` | `Attendu 503, reçu 200 : {"analysed":1,…}` |
| Enrichissement, archive hors bornes → 503, aucune ligne | `EnrichingAMail_WhoseArchiveInflatesBeyondTheBounds_RefusesIt_AndDoesNotMarkItAnalysed` | `Attendu 503, reçu 200 : {"analysed":1,…}` |

Preuve rouge : les 6 tests rejoués après `git stash` de `src/` (code de production d'avant le correctif, tests et fixture inchangés) : **6 échecs, chacun sur son assertion**, puis 6 verts après restauration.

### Tests unitaires

- `CdaParsingServiceTechnicalFailureTests` (4) : archive retirée → `Io` (message sans chemin) ; bombe → `ArchiveLimitExceeded` ; borne configurée appliquée (seule elle refuse l'archive) ; zip corrompu → analysé sans document, sans exception. `ParseIheXdmZip_NonExistentPath_ReturnsEmpty` figeait le défaut : il est retiré, avec la raison en commentaire.
- `IheXdmScratchSweepAgeTests` (4) : répertoire orphelin purgé ; archive récente et extraction en cours épargnées ; seul ce qui dépasse l'âge minimal part.
  - Mutation, contrôle d'âge retiré : 3 rouges. Mutation, sous-répertoires ignorés : `Sweep_PurgesAnOrphanExtractionFolder_WithItsClinicalFiles` rouge.
- Trois tests de balayage existants créaient des résidus « récents » : ils sont vieillis de 2 h (une exécution précédente). L'assertion du message de journal est alignée.
- `ServiceImplementationCoverageTests` : les noms de pièces jointes lisent `Header`, et `DidNotReceive` d'un appel `WithContent`.

### Inventaire des mails déjà marqués à tort (hors périmètre, pour une US de rejeu)

À exécuter sur chaque base praticien : les mails porteurs d'une archive IHE-XDM, marqués analysés, sans aucun document médical.

```sql
SELECT m."Id", m."FolderPath", m."Uid", m."SentDate"
FROM "Mails" m
JOIN "MailAttachments" a ON a."MailId" = m."Id"
WHERE lower(a."FileName") = 'ihe_xdm.zip'
  AND EXISTS (SELECT 1 FROM "MailContents" c WHERE c."MailId" = m."Id")
  AND NOT EXISTS (SELECT 1 FROM "MailMedicalDocuments" d WHERE d."MailId" = m."Id")
ORDER BY m."SentDate" DESC;
```

Un résultat inclut aussi les archives réellement invalides, analysées à bon droit sans document : le rejeu les écartera de lui-même.

Contrôle de l'étape 5 du plan de test manuel (export d'un mail non analysé) : avant et après l'export, pour l'UID exporté, aucune ligne ne doit apparaître :

```sql
SELECT count(*) FROM "MailContents" c JOIN "Mails" m ON m."Id" = c."MailId"
WHERE m."FolderPath" = 'INBOX' AND m."Uid" = :uid;
```

### Points à arbitrer (non bloquants)

- **Archive hors bornes** : conformément à la DOD, elle est refusée et le mail n'est pas marqué analysé. Il reste donc en attente, et chaque enrichissement du dossier rend le 503 « traitement des documents indisponible », au libellé « Réessayez ». Pour une archive volontairement anormale, réessayer ne changera rien. Un état terminal dédié (mail signalé, sans document, hors des reprises) relève d'une décision produit : à router vers le PO.

### Passe qualité (§Q)

- `interop-cda` : non éligible (porteur de contrat).
- `api-mail` : revue du diff (réutilisation, simplification, efficacité, altitude), **aucune simplification appliquée**. Chaque élément nouveau a un seul usage. Les deux traitements de la panne d'analyse (Phase B et synchro de fond) restent distincts à dessein : task-334 unifie les deux constructeurs. Pas de commit, pas de re-validation.
- Contrôles mécaniques §Q 2b (S125, xUnit1045, S4457, xUnit2032) : aucune occurrence, sur les deux dépôts.

### Validation

- interop-cda : build 0 erreur, 407 verts.
- api-mail : build 0 erreur. Suite complète : domain 190, infrastructure 683, application 3 441, api 1 176, intégration 800 verts sur 816 (16 ignorés). Le premier passage complet a sorti 12 rouges, tous des tests qui figeaient l'ancien comportement (repli qui enregistrait et publiait, noms de pièces jointes lus en WithContent, archive absente rendant une liste vide, libellé du journal XDM exempté) : ils sont mis à jour dans `ab5e8247`, puis rejoués verts. Aucun des rouges d'ordre connus (vecteurs, partitions d'audit) n'est apparu sur ce passage. Mutation supplémentaire : garde d'extraction retirée du repli → `GetEmailAsync_WhenTheArchiveCannotBeExtractedForATechnicalCause_Returns503_WithoutBuildingAsync` rouge.

## Sonar log

- Serveur : SonarQube 25.6.0.109173 (`sonar.token`), port 9001. Projet `healthplatform-api-mail`. La période de nouveau code « previous version » couvre des dizaines de tasks déjà mergées : chaque finding est trié par provenance.
- Référence : la dernière analyse du serveur (2026-10-03, état final de task-348).
- **Phase 1 (nouveau code de task-333) : verte** en 2 itérations.
  - Itération 1, sur les 11 fichiers `src/` de la task : **2 issues introduites**.
    - S103, `IheXdmScratch.cs:160` : message du balayage allongé au-delà de 150 caractères.
    - S134, `ImapService.cs:2093` : `try/catch` ajouté dans la boucle de Phase B, quatre niveaux.
    - Aucun hotspot.
    - Couverture du nouveau code sous 95 % : `IheXdmTechnicalFailureException` (40 %, constructeurs non appelés) et `BackgroundEnrichmentProcessor` (93,8 %, le `catch` de la panne d'analyse).
  - Corrigé (`d6c39aa1`) :
    - S134 : la persistance protégée sort dans `PersistUnlessArchiveUnreadableAsync`, qui rend un booléen ;
    - S103 : le gabarit est scindé par concaténation.
  - Tests (`51815492`) : constructeurs de l'exception (cause par défaut, cause explicite, exception interne) ; `UnavailableException(message, code, inner)` ; synchro de fond, archive illisible → mail en attente et reste du lot persisté.
  - Itération 2 : **aucune issue ni aucun hotspot introduits** par la task. Couverture du nouveau code des fichiers touchés : 95,2 à 100 % (`ServiceImplementation` 94,7 % sur des conditions antérieures, 0 ligne non couverte).
- Reste dans les fichiers de la task : S138 `AddApplication` (101 lignes), **dette antérieure** (issue créée le 2026-09-07). task-333 y ajoute une ligne (`Configure<IheXdmOptions>`), elle ne la crée pas.
- Nouveau code hors task-333 : 67 violations et 13 hotspots `TO_REVIEW` hérités. Deux sont apparus depuis la référence, dans des fichiers que la task ne touche pas : S1151 `PatientService.cs:198`, S138 `BiologyRepository.GetBiologyByPatientIdAsync`. Ils viennent des tasks fusionnées dans la base de la branche après l'analyse de référence.
- Phase 2 (dette héritée) : non lancée (optionnelle, hors périmètre).
- Build et tests Release, couverture OpenCover, aux deux itérations : 0 erreur, domain 190, application 3 441 puis 3 446, infrastructure 683, api 1 176, intégration 800 verts (16 ignorés). Aucun rouge.
- Conventions : S103 → 3 (récidive sur un message modifié) ; **S134 ajoutée**.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-10-03) | Final (branche task-333) | Δ |
|---|---|---|---|
| Quality Gate (nouveau code) | ERROR | ERROR | → (conditions héritées : hotspots non revus, violations) |
| New coverage | 98,1 % | 98,1 % | 0 |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 (aucun sur le code de la task) |
| Code smells | 68 | 70 | +2, hors task-333 (S1151 `PatientService`, S138 `BiologyRepository`) ; les 2 de la task sont corrigés |
| Reliability / Security / Maintainability | D / A / A | D / A / A | → |
| Coverage (global) | 98,0 % | 97,9 % | −0,1 pt |
| Duplication | 0,4 % | 0,3 % | −0,1 pt |

## Lint log

- `/lint-angular` : **skipped**, `client-angular` n'est pas listé dans `**Repos**:` (task backend : api-mail et interop-cda).

## Lint mobile log

- `/lint-mobile` : **skipped**, `client-mobile` n'est pas listé dans `**Repos**:`.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 29 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 11 s |
| angular | api-mail touché | ✅ verte | 29 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 42 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task, après fusion d'`origin/develop` (`8a546c07`, qui apporte task-352).
- Quarantaines : aucune.
- Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun (task backend, aucun écran touché).
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).
- Historique du passage :
  - 1ᵉʳ passage : voie mobile rouge sur `E2E-FOLDER-003` / `004`. La branche api-mail partait d'un `develop` antérieur à task-352, sans la sous-commande `folder` ni les scénarios. Corrigé par la fusion de `develop`.
  - 2ᵉ passage : mobile verte, Angular de parité rouge. Le code Angular de task-352 n'était plus dans le checkout. L'humain l'a remis à jour.
  - 3ᵉ passage : Angular verte. Le rapport mobile du 2ᵉ passage est repris pour la porte : api-mail est au même commit (`8a546c07`) et le mobile au même `develop`.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

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
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
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

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-333 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 41 min 57 s | 6 (1 min 09 s) | 3 (4 min 33 s) | — | interop-cda 1B/1T, api-mail 5B/2T |
| /sonar | ok | 25 min 57 s | 3 (1 min 20 s) | 10 (10 min 39 s) | 4 (5 min 32 s) | 2 itération(s), api-mail 3B/10T |
| /lint-angular | skipped | 2.0 s | — | — | — | client-angular non listé dans Repos |
| /lint-mobile | skipped | 2.1 s | — | — | — | client-mobile non listé dans Repos |
| /e2e | ok | 6 min 27 s | 1 (31 s) | — | — | api-mail 1B/0T, e2e ×7 (22 min 53 s) |
| /review | ok | 6 min 16 s | 2 (25 s) | 2 (4 min 04 s) | — | interop-cda 1B/1T, api-mail 1B/1T |
| **Total cycle** | | **1 h 21 min** | **12 (3 min 26 s)** | **15 (19 min 17 s)** | **4 (5 min 32 s)** | |

Autres commandes mesurées : nuget-wait ×1 (38 s), restore ×1 (8.1 s)

## PRs

- `interop-cda` : https://github.com/codengine-technologies/interop.cda.parser/pull/9 — label `awaiting-human-merge` (Interop.Cda.Parser 101.0.0, à merger en premier)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/276 — label `awaiting-human-merge`
- Aucun client touché ; aucun contrat DTO (pas de branche `dtos-mss`).

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 4 suggestions (non bloquantes).

- ✅ `interop-cda` `XDM.Load` : `Failure` distingue archive invalide, panne de l'hôte et archive hors bornes ; extraction bornée (entrées, taille, ratio, vérifiés sur les tailles déclarées puis sur les octets réels) ; entrée hors de son répertoire refusée comme archive invalide ; évolution additive (`Load(fichier, xsd)` inchangée).
- ✅ `CdaParsingService` : panne de l'hôte ou hors bornes → `IheXdmTechnicalFailureException`, comptée (`limit_exceeded` nouveau) ; archive invalide → analysée sans document (inchangé).
- ✅ Phase B et synchro de fond : le mail dont l'archive est illisible n'est pas persisté, il reste à traiter ; le lot rend le 503 `DOCUMENT_PROCESSING_UNAVAILABLE` (même voie que la garde d'extraction de task-293).
- ✅ Repli de lecture (export, résumé, archive des pièces jointes d'un mail « en-têtes seuls ») : lecture pure, plus aucune écriture du marqueur ; panne technique → 503 ; lecture `Header` sans extraction ; dossier refermé sur tous les chemins.
- ✅ Balayage au démarrage : sous-répertoires d'extraction orphelins purgés, rien de plus récent qu'une heure (archive d'un autre réplica).
- ✅ Aucun chemin, sujet, INS ni contenu dans les messages d'erreur ; les journaux d'`XDM.Load` ne citent qu'un nom de fichier GUID.
- ⚠️ Suggestion — **archive hors bornes** : conforme à la DOD (refusée, non marquée analysée), mais le mail reste en attente et chaque enrichissement du dossier rend le 503 « Réessayez », alors que réessayer ne changera rien. Un état terminal dédié (mail signalé, sans document, hors des reprises) relève du PO.
- ⚠️ Suggestion — `XDM.Load` journalise une archive invalide en `Error` : c'est une propriété du message de l'expéditeur, un `Warning` suffirait (bruit d'exploitation).
- ⚠️ Suggestion — le repli relit le serveur à chaque export ou résumé d'un mail pas encore analysé, et un résumé IA calculé sur un tel mail n'est pas mis en cache (aucune ligne de contenu). Rare : l'enrichissement suit la liste presque aussitôt.
- ⚠️ Suggestion — à l'envoi, une pièce `IHE_XDM.ZIP` hors bornes ne produit plus d'en-têtes `X-MSS-CODECDA` / `X-MSS-INS` (le parseur la refuse, l'appelant rend `[]` comme pour toute erreur).

**Règle 1b (tests d'intégration d'endpoint, vus rouges)** — `ArchiveAnalysisMarkerEndToEndTests`, vraie pile (HTTP, vrais contrôleurs, vraie extraction, vrai parseur, base praticien, Dovecot) ; panne d'hôte injectée en retirant l'archive écrite avant sa lecture :

| Comportement | Test | Rouge sur le code d'avant |
|---|---|---|
| Export d'un mail non analysé, archive illisible → 503, aucune ligne de contenu | `ExportingAMailNotYetAnalysed_WhenItsArchiveCannotBeRead_Returns503_AndWritesNothing` | `Attendu 503, reçu 200 : %PDF-1.4` |
| Export d'un mail non analysé → 200 sans ligne de contenu ; l'enrichissement le constitue ensuite avec ses documents | `ExportingAMailNotYetAnalysed_ServesItWithoutMarkingItAnalysed_AndItsAnalysisStillHappens` | `Expected: 0, Actual: 1` |
| Archive des pièces jointes d'un mail non analysé → 200, aucune extraction | `DownloadingTheAttachmentsOfAMailNotYetAnalysed_TriggersNoArchiveAnalysis` | `Expected: 0, Actual: 1` |
| Lecture concurrente d'une analyse → une seule ligne de contenu | `ReadingAMailWhileItIsBeingAnalysed_LeavesASingleContentRow` | `Expected: 1, Actual: 2` |
| Enrichissement, archive balayée avant lecture → 503, mail en attente ; hôte rétabli → analysé avec ses documents | `EnrichingAMail_WhoseArchiveVanishesBeforeItIsRead_Returns503_LeavesItPending_ThenAnalysesItOnceRestored` | `Attendu 503, reçu 200` |
| Enrichissement, archive hors bornes → 503, non marqué | `EnrichingAMail_WhoseArchiveInflatesBeyondTheBounds_RefusesIt_AndDoesNotMarkItAnalysed` | `Attendu 503, reçu 200` |
