# todo-task-331.md — Un document rattaché à un patient apparaît dans son dossier, et le dossier ne mélange jamais deux identités qui partagent un matricule

**Repos**: api-mail
**Dependencies**: — (aucune ; à coordonner avec task-191, qui traite les **doublons** de fiches pour une même identité)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — le rattachement manuel imposé par task-176 est **sans effet visible** : le document sort de la file « à intégrer » sans entrer dans aucun dossier ; et la garde d'opposition peut lire la mauvaise fiche.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-05** — contre-vérifié — et **AUD-34**).

## Ce qui est établi (develop @ `14d58398`)

**Rattachement invisible (AUD-05)** — `PatientRepository.cs:851-866` (`AttachDocumentToPatientAsync`)
ne pose que `doc.PatientId` ; le dossier (`/patients/{patientId}/medical-documents`) résout
l'identifiant en INS (`PatientHandleResolver.cs:37-48`) puis filtre `md.Ins == ins`
(`ActiveDocumentsForPatient`, `:548-564`). Un CDA arrivé **sans INS** (cas nominal depuis task-176)
garde `Ins = null` : il disparaît de la file (qui compte `PatientId == null`) sans entrer dans la
chronologie. Le test existant (`AttachDocumentToPatientAsyncShouldUpdatePatientIdAsync`) ne vérifie que `PatientId`.

**Identités fusionnées (AUD-34)** — task-183 crée deux fiches pour un même matricule dans deux domaines
(NIA/NIR, OID de test et de production). Mais :
- le dossier filtre sur le matricule seul (`PatientRepository.cs:548-552`) → la fiche X affiche aussi les documents de la fiche Y ;
- `GetOppositionAsync` / `UpdateOppositionAsync` (`:644-651`, `:667-671`) font
  `FirstOrDefaultAsync(x => x.Ins == ins)` **sans `ORDER BY`** → fiche arbitraire ;
  `PatientOppositionGuard.cs:55` peut lire la fiche **non opposée** et laisser partir un envoi sans acquittement ;
- `AddPatientMessageDocumentAsync` (`MailRepository.cs:471`) rattache les messages patient par matricule seul, sans l'arbitrage par domaine de task-183.

## Objective

Que le dossier d'un patient soit défini par **l'identité de la fiche** (et non par le matricule seul) :
un document rattaché à la main y apparaît immédiatement, deux identités distinctes partageant un
matricule ne se mélangent jamais, et l'opposition lue et écrite est celle de la fiche visée.

### Périmètre

1. **Dossier clé sur la fiche** : `ActiveDocumentsForPatient` et les requêtes du dossier filtrent par
   `PatientId` (ou par `(Ins, PatientOid)` si `/develop` établit que `PatientId` n'est pas renseigné
   sur tous les documents historiques — dans ce cas, reprise des documents existants documentée).
2. **Rattachement manuel** : le document rattaché apparaît dans le dossier de la fiche ; la file
   « à intégrer » et le dossier restent cohérents (un document est dans l'un ou dans l'autre).
3. **Opposition** : lecture et écriture par identifiant de fiche ; `PatientOppositionGuard` lit la fiche
   du destinataire effectivement visé.
4. **Messages patient** : rattachement avec le même arbitrage par domaine que le chemin CDA (task-183).
5. **Reprise des données** : les documents déjà rattachés à la main (PatientId posé, Ins nul) deviennent
   visibles sans action du praticien.

### Hors périmètre

- La déduplication des fiches d'une même identité (task-191).
- La création de patient depuis le rattachement — **interdite** (garde-fou métier), inchangée.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (log du run rouge dans le task file) : CDA sans INS rattaché à la main à la fiche X →
      sur le code actuel **absent** du dossier de X ; après correctif **présent**, et absent de la file « à intégrer »
- [ ] Test : deux fiches même matricule, domaines différents (NIR / NIA) → le dossier de chacune ne montre que ses documents
- [ ] Test : opposition posée sur la fiche Y → la garde lit l'opposition de la fiche **effectivement destinataire**, de façon déterministe
- [ ] Test : message patient Mon Espace Santé rattaché selon l'arbitrage de domaine task-183
- [ ] Test : document historique (PatientId posé, Ins nul) visible après la reprise
- [ ] Test d'intégration endpoint (règle 1b) : `POST /medical-documents/{id}/attach-patient` puis `GET /patients/{patientId}/medical-documents` → le document est présent
- [ ] Migration éventuelle auditée (règle 7c) : fichier lu, aucune opération fantôme, companion présent, aucun écart de modèle
- [ ] Aucune INS, NIR ni trait patient dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor ou mobile connecté à une boîte de test.
2. Recevoir un mail de test portant un CDA **sans INS** (corpus du banc) → il apparaît dans « à intégrer ».
3. Le rattacher à un patient existant de test → **Attendu** : il disparaît de « à intégrer » **et apparaît** dans la chronologie du patient. Avant : il n'apparaît nulle part.
4. Préparer (données de test anonymisées) deux fiches de même matricule dans deux domaines ; ouvrir chacune → chacune ne montre que ses propres documents.
5. Poser une opposition sur l'une, tenter un envoi vers le patient correspondant → la demande d'acquittement s'affiche pour la bonne fiche, et seulement pour elle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : identito-vigilance — rattachement d'un document à la bonne identité ; opposition patient respectée (Mon Espace Santé)
- **INS** : **au cœur** — distinction des domaines d'identité (NIR / NIA, OID) conformément au référentiel INS ; aucune fusion de deux identités sur le seul matricule ; statut INS inchangé par la US
- **Authentification PS** : PSC / e-CPS inchangée
- **Habilitations** : inchangées — dossier limité aux patients du praticien
- **Interop CI-SIS** : CDA r2 — identifiant patient et OID de domaine lus depuis le document (chemin `interop-cda` existant)
- **Tracé PGSSI-S** : rattachement manuel tracé (existant) ; lecture et modification d'opposition tracées
- **Consentement patient** : opposition Mon Espace Santé lue sur la fiche du destinataire effectif
- **Référentiels métier** : référentiel INS (OID des domaines NIR / NIA)
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — corrige un risque de mélange d'identités, sans traitement nouveau

## Branches
- `api-mail` (pushed) : fix/task-331-dossier-patient-par-fiche — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-331-dossier-patient-par-fiche (depuis `origin/develop` @ `91fb090c`, task-329 mergée)
- `dtos-mss` : aucune branche au `/start`. `/develop` la crée seulement si un contrat change. **Aucun contrat ne change** (routes et DTO identiques) : aucune branche.

## Réévaluation au démarrage de /develop (develop @ `91fb090c`)

| Point | Constat sur develop | Suite |
|---|---|---|
| 1. Dossier clé sur la fiche | **Ouvert.** `ActiveDocumentsForPatient` filtre `md.Ins == ins`, et le contrôleur résout la poignée en INS. Biologie : `Patient.Ins == ins`, donc toutes les fiches du matricule. | Corrigé : filtre `md.PatientId == patientId`, biologie `MedicalDocument.PatientId == patientId`. |
| 2. Rattachement manuel visible | **Ouvert.** Le rattachement pose `PatientId`, et le dossier lit `Ins`. | Corrigé par le point 1 : la file et le dossier comptent la même relation. |
| 3. Opposition par fiche | **Ouvert.** `GetOppositionAsync` et `UpdateOppositionAsync` font `FirstOrDefault(x => x.Ins == ins)` sans `ORDER BY` ; la garde lit une fiche arbitraire. | Corrigé : lecture et écriture par identifiant de fiche. La garde exige l'acquittement dès qu'**une** fiche du matricule est opposée (voir la décision ci-dessous). |
| 4. Messages patient arbitrés par domaine | **Déjà livré par task-191** : `AddPatientMessageDocument` appelle `MatchPatientOnDomain(candidates, domain: null)` sur des candidats triés par `Id`. | Rien à coder. Preuve existante : `MailRepositoryPatientIdentityIntegrityTests`, famille `PatientMessage_*` (une fiche, une fiche sans domaine parmi d'autres, deux domaines connus → la plus ancienne quel que soit l'ordre des lignes, message + CDA dans le même lot), rejouée verte. |
| 5. Reprise des documents historiques | **Sans objet en base.** Un document rattaché à la main (fiche posée, INS nulle) devient visible par la clé elle-même. L'inverse, une INS sans fiche, ne peut exister : l'ingestion résout ou crée la fiche dès que le document porte une INS, et `SetupMigration` refuse toute base antérieure à la consolidation du 2026-09-30. | Aucune migration de reprise. Test : document historique visible. |

**Trouvé en route (non listé par la task)** : `PatientId` n'avait **aucun index en base**, car PostgreSQL n'en crée pas pour une clé étrangère. Passer le filtre du dossier de `Ins` à `PatientId` aurait fait parcourir toute la table à chaque page de dossier, ce qui défait le gain mesuré par task-233. Migration `AddMedicalDocumentPatientFolderIndex` (20261002120000) : `(PatientId, MailId, Date)`, même forme que le composite de task-233. L'index par `Ins` reste, pour la détection des doublons et des versions à l'ingestion.

**Décision — l'opposition à l'envoi.** L'adresse Mon Espace Santé (`{matricule}@patient.mssante.fr`) ne porte pas le domaine. Pour un matricule à deux fiches, l'adresse désigne donc l'une **et** l'autre. Deux règles déterministes étaient possibles :
- lire la fiche que l'arbitrage des messages entrants désigne (la plus ancienne) ;
- honorer l'opposition de **n'importe quelle** fiche du matricule.

Retenu : la seconde. C'est la seule qui ferme le risque nommé par l'audit (« lire la fiche non opposée et laisser partir un envoi sans acquittement »). Un faux positif coûte un acquittement, pas un envoi bloqué. Un faux négatif viole une opposition. Ce choix est à confirmer par l'humain au HAG.

## Develop log

**Repos touchés** : `api-mail` seul. Aucun contrat ne change : routes, `MailPatientDto` et `PatientOppositionDto` sont identiques. Pas de branche `dtos-mss`, et les clients sont inchangés.

### Correctif
- **Dossier** (`PatientRepository.ActiveDocumentsForPatient`) : filtre `md.PatientId == patientId` au lieu de `md.Ins == ins`. `GetMailsByInsAsync` ×2 et `GetMedicalDocumentsByInsAsync` deviennent `…ByPatientIdAsync`, dans le dépôt et dans le service. La file « à intégrer » compte `PatientId == null` : un document est dans la file ou dans un dossier, jamais dans les deux, jamais dans aucun.
- **Biologie** (`BiologyRepository.GetBiologyByPatientIdAsync`) : `MedicalDocument.PatientId == patientId` au lieu de `MedicalDocument.Patient.Ins == ins`.
- **Opposition** : `GetOppositionAsync(Guid)` et `Task<bool> UpdateOppositionAsync(Guid, dto)`. `false` donne un 404, et le cache est invalidé par l'INS de la fiche. La garde d'envoi appelle `IsMssPatientOpposedAsync(ins)`, qui répond oui dès qu'**une** fiche du matricule est opposée (voir la décision ci-dessus). L'audit et le journal de la garde restent inchangés : clé hachée, jamais l'INS en clair.
- **Contrôleurs** : `PatientHandleResolver.ResolveInsOrThrowAsync` est remplacé par `EnsurePatientExistsAsync`, qui ne lève 404 que pour une poignée inconnue.
  - Changement de comportement assumé : une fiche sans INS n'est plus un 404. Son dossier, sa biologie et son opposition sont servis par son identifiant.
- **`GetByInsAsync`** (route `POST patients/resolve`) : déterministe, avec la règle de l'ingestion pour un document sans domaine (`MatchPatientOnDomain`) : la fiche de domaine inconnu d'abord, la plus ancienne ensuite.
- **Trouvé en route** :
  - la recherche et « patients du jour » rendaient `Id = Guid.Empty`, si bien que le dossier ouvert depuis ces listes répondait 404 ;
  - `PatientId` n'avait aucun index en base : la migration `20261002120000_AddMedicalDocumentPatientFolderIndex` crée `(PatientId, MailId, Date)`, déclaré aussi dans `MailDataContext`.

### Test d'intégration (règle 1b) : `PatientFolderEndToEndTests` (nouvelle, boîte 19)
Ces tests passent par HTTP sur la vraie pile : `PatientsController`, `MedicalDocumentsController`, `BiologyController`, les vrais services et dépôts, la base PostgreSQL du praticien. Le harnais HTTP de task-329 est extrait dans `UseCaseHttpHost`, partagé avec `SendPathsEndToEndTests`.

| Comportement | Test | Preuve rouge |
|---|---|---|
| CDA sans INS rattaché à la main → dans le dossier, hors de la file | `ADocumentWithoutIns_AttachedByHand_JoinsThePatientFolder_AndLeavesTheQueue` (`POST attach-patient` puis `GET medical-documents`) | Rouge sur le code d'avant : `Assert.Contains() Failure: Item not found` |
| Document historique (fiche posée, INS nulle) visible, paginé | `AHistoricalDocumentAttachedByHand_WithoutIns_IsInThePatientFolder` | Rouge : `Collections differ` |
| Deux fiches, même matricule, NIR et NIA → dossiers séparés | `TwoRecordsSharingAMatricule_InTwoDomains_EachFolderShowsOnlyItsOwnDocuments` | Rouge : `Collections differ at index 0` |
| Opposition écrite et lue sur la fiche visée | `TheOpposition_IsWrittenAndReadOnTheRecordAddressed_NeverOnItsHomonym` (PUT puis GET ×2) | Rouge : `Assert.False() Failure` (l'écriture tombait sur l'autre fiche) |
| Biologie de deux fiches du même matricule séparée | `TheBiologyOfTwoRecordsSharingAMatricule_StaysWithItsRecord` | Rouge : `Assert.Empty() Failure` |
| La garde : opposition sur la fiche NIA (la plus récente) seule → 409 | `SendPathsEndToEndTests.AMatriculeWithTwoRecords_OpposedOnlyOnTheNewerOne_RequiresAcknowledgement` (`POST sendmail`, GreenMail) | Rouge : `Attendu 409, reçu 200` (le message partait) |
| La recherche et la liste du jour portent l'identifiant ; le dossier s'ouvre | `APatientFoundBySearch_CarriesItsRecordId_AndItsFolderOpens`, `ThePatientsOfTheDay_CarryTheirRecordId_AndTheirFolderOpens` | Rouges : `Values differ` / `2 out of 2 items … Values are equal` (Guid.Empty) |
| Poignée inconnue → 404 problem+json (dossier, opposition GET/PUT, biologie) | `AnUnknownPatientHandle_Is404ProblemJson` ×3, `AnOppositionWrittenOnAnUnknownHandle_Is404ProblemJson` | Garde de non-régression, verte avant et après |
| L'index du dossier existe sur une base migrée par le coureur de production | `PatientFolderIndexMigrationTests` | Mutation : `OnColumn("PatientId")` → `OnColumn("Ins")` donne `Filter not matched` ; restauré par `cp` + `touch`, vert |
| *(revue, verrou 4a)* `POST patients/resolve` → la fiche de domaine inconnu avant une plus ancienne qui a un domaine | `ResolvingAMatriculeWithTwoRecords_OpensTheRecordOfUnknownDomain_AsIngestionDoes` | Mutation : tri réduit à `OrderBy(Id)` → `Values differ` ; restauré, vert |
| *(revue)* `POST patients/resolve` → deux domaines connus : la plus ancienne | `ResolvingAMatriculeKnownInTwoDomains_OpensTheOldestRecord` | Mutation : `ThenBy(Id)` → `ThenByDescending(Id)` → `Values differ` ; restauré, vert |
| *(revue)* Une fiche sans INS sert le dossier de ses documents rattachés | `ARecordWithoutIns_HasTheFolderOfTheDocumentsAttachedToIt` | Mutation : remettre « INS vide = 404 » dans `EnsurePatientExistsAsync` → 404 ; restauré, vert |

Le point 4 (messages patient) est déjà prouvé par task-191 : `MailRepositoryPatientIdentityIntegrityTests.PatientMessage_*`, vert dans la suite.

### Tests existants adaptés (26 fichiers)
Les nouvelles signatures sont appliquées partout. Chaque test qui lisait le dossier par INS sème désormais la fiche et pose `PatientId` (l'INS est gardée sur le document). Changements d'intention :
- Une fiche sans INS donne 200 servi par son identifiant (`…_WhenPatientHasNoIns_IsServedByItsRecordId`, contrôleurs dossier et biologie).
- « INS vide → vide » devient « `Guid.Empty` → vide ». Quatre variantes nulle/blanche sont retirées, car elles n'existent pas pour un `Guid`.
- Ajouts unitaires :
  - opposition par fiche, l'autre fiche intacte ;
  - fiche inconnue → `false` ;
  - `IsMssPatientOpposedAsync` (une fiche opposée sur deux, aucune, matricule vide) ;
  - `GetByInsAsync` (la plus ancienne ; la fiche de domaine inconnu avant une plus ancienne qui a un domaine) ;
  - biologie d'une autre fiche du même matricule invisible.

### Passe qualité §Q (4 revues : réutilisation, simplification, efficacité, altitude)
- **Appliqué** :
  - une seule projection `MailPatient → MailPatientDto` (`DtoProjection`, compilée pour `ToDto`) au lieu de trois copies, celles qui avaient divergé deux fois ;
  - `GetByInsAsync` aligné sur la règle d'arbitrage de l'ingestion ;
  - `GetOppositionAsync` réutilise `GetByIdAsync` ;
  - la biologie projette le titre et la date du document au lieu d'`Include` le document entier (corps, métadonnées, vecteur) une fois par analyte ;
  - commentaire périmé retiré.
- **Écarté**, sans changement :
  - les gardes `Guid.Empty` (elles évitent un aller-retour) ;
  - le renommage de `PatientHandleResolver` (cosmétique, change le nom de fichier) ;
  - l'abandon du `Task<bool>` d'`UpdateOppositionAsync` (il coûterait un aller-retour) ;
  - le contrôle d'existence seulement sur résultat vide (gain inférieur à la milliseconde) ;
  - la largeur de l'index `Ins` ;
  - l'insertion des helpers de contrôleur et la méthode de service sans appelant (antérieures).
- **Suivis proposés** (hors périmètre, à ouvrir en task) :
  1. **Doublons et versions à l'ingestion** (`MailRepository.FindExactDuplicateIdAsync` / `LoadActiveSetVersionsAsync`) : ils comparent toujours par `Ins`, avant la résolution de la fiche. Un document NIA de même `SetId` peut donc rendre obsolète le document de la fiche NIR et le cacher de son dossier. C'est le dernier endroit où la visibilité du dossier dépend du matricule (résidu d'AUD-34).
  2. Index sur `MailMedicalDocumentBiology.MedicalDocumentId` : la clé étrangère n'est pas indexée.
  3. Affichage : la fiche non opposée d'un matricule à deux fiches n'indique pas que l'envoi demandera un acquittement à cause de l'autre fiche.

### Vérifications
- Migration (règle 7c) : `20261002120000_AddMedicalDocumentPatientFolderIndex.cs` relue.
  - Une seule opération, `Create.Index` sur des colonnes existantes, et un `Down` symétrique.
  - FluentMigrator n'a pas de fichier compagnon.
  - Le modèle EF déclare le même index sous le même nom, donc aucun écart.
  - Aucune reprise de données.
- Journaux : aucune ligne de journal ajoutée ne porte d'INS ni de trait. Les contrôleurs journalisent la poignée, la garde la clé hachée.

## Sonar log

**Analyse** : une passe complète sur `fix/task-331-dossier-patient-par-fiche` (commit `77dd0af1`), avec la couverture des cinq suites :
- domain 190 ;
- application 3 373 ;
- infrastructure 681 ;
- api 1 159 ;
- integration 740, plus 16 ignorés préexistants ;
- 0 échec.

**Itérations de correction** : 0. Aucun constat sur le code de la task.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse task-329) | Final (task-331) | Δ |
|---|---|---|---|
| Quality Gate | OK | **OK** | = |
| New coverage | 97,5 % | 97,5 % | = |
| Coverage projet | 98,0 % | 98,0 % | = |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | = |
| Code smells | 13 | 13 | = |
| Duplication | 0,4 % | 0,4 % (nouveau code 0,16 %) | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

- **Fichiers de la task** : contrôleurs Patients et Biologie, `PatientHandleResolver`, `PatientService`, `BiologyService` et `PatientOppositionGuard` à 100 %. `PatientRepository` est à 99,1 % et `BiologyRepository` à 96,7 %. Aucun smell ajouté.
- **Restant, hors task** : S107 sur `SemanticSearchService:379`, déjà relevé par task-329, et S107 sur `PatientRepository:830`, du 2026-04-29. Les deux sont antérieurs.

## Lint log

**Skipped** : `client-angular` non touché (la task ne liste que `api-mail`).

## Lint mobile log

**Skipped** : `client-mobile` non touché (la task ne liste que `api-mail`).

## E2E log

| Voie | Déclencheur | Checkout | Résultat |
|---|---|---|---|
| mobile | `api-mail` touché | `Client/Mobile` sur `develop`, backend e2e sur `fix/task-331-dossier-patient-par-fiche` | ✅ 26/26 verts, 0 flaky, parité verte, démontage complet |
| angular | `api-mail` touché | `Client/Angular/front` sur la branche de l'humain (`feature/nova-rewriting-mss`, sans opération git) | ✅ 26/26 verts, 0 flaky, parité verte, backend démonté |

- **Porte `gate`** : code 0 (rapports `--report` des deux voies, ce run).
- **Flaky** : aucun. **Quarantaines** : aucune. **Divergences ouvertes** : aucune.
- **Écrans modifiés sans spec e2e modifié** : sans objet, la task ne touche aucun client. Les routes et le contrat sont inchangés ; seul le contenu servi change.
- **Démontage** : aucun conteneur e2e résiduel, ports libres.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
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
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/271 — label `awaiting-human-merge`. Branche `fix/task-331-dossier-patient-par-fiche`, commits `77dd0af1` (correctif et passe qualité) et `c563698c` (tests de la revue).
- `dtos-mss` : aucune PR, aucun contrat ne change.

## Code Review Summary

**Verdict : APPROVED** (0 bloquant).

- **Build** : 0 erreur.
- **Tests** : domain 190, infrastructure 681, application 3 373, api 1 159, integration 740, plus 16 ignorés préexistants. 0 échec. Les 3 tests ajoutés par la revue sont ensuite verts dans leurs classes (27/27).
- **DOD** :
  - [x] Build passes (0 errors)
  - [x] Tests pass (0 failures)
  - [x] Test rouge d'abord : `ADocumentWithoutIns_AttachedByHand_…`, rouge sur le code d'avant (log dans le Develop log)
  - [x] Deux fiches de même matricule, NIR et NIA, isolées : `TwoRecordsSharingAMatricule_…` (dossier) et `TheBiologyOfTwoRecords…` (biologie)
  - [x] Opposition sur la fiche Y lue de façon déterministe : `TheOpposition_IsWrittenAndReadOnTheRecordAddressed_…` (lecture et écriture par fiche) et `AMatriculeWithTwoRecords_OpposedOnlyOnTheNewerOne_RequiresAcknowledgement` (garde, 409)
  - [x] Message patient selon l'arbitrage de domaine : livré par task-191, `MailRepositoryPatientIdentityIntegrityTests.PatientMessage_*` verts
  - [x] Document historique (fiche posée, INS nulle) visible : `AHistoricalDocumentAttachedByHand_…`
  - [x] Règle 1b : `POST /medical-documents/{id}/attach-patient` puis `GET /patients/{id}/medical-documents`, document présent
  - [x] Migration auditée (7c) : un `Create.Index`, un `Down` symétrique, le modèle EF aligné, pas de reprise
  - [x] Aucune INS, NIR ni trait patient dans les journaux ajoutés
- **E2E** : vert, avec les deux voies à 26/26 et la parité verte.

**Verrou 4a — comportement → test → preuve rouge** : voir la table du Develop log. Neuf comportements atteignables par endpoint, chacun avec un test HTTP sur la vraie pile et une preuve rouge, sur l'ancien code ou par mutation.

La revue a trouvé deux comportements prouvés seulement par des tests unitaires : `resolve` et la fiche sans INS. Elle a ajouté leurs tests HTTP et leurs mutations dans le commit `c563698c`.

**Revue par fichier** :
- ✅ `PatientRepository` : filtre par fiche, une seule projection DTO, `resolve` aligné sur l'arbitrage de l'ingestion, `IsMssPatientOpposedAsync` couvert par les index `Ins` existants.
- ✅ `BiologyRepository` : filtre par fiche et projection minimale.
- ✅ Migration `20261002120000` et `MailDataContext` : index du dossier.
- ✅ `PatientsController` / `BiologyController` / `PatientHandleResolver` : 404 réservé à la poignée inconnue, aucune donnée de santé journalisée.
- ✅ `PatientOppositionGuard` : règle conservatrice ; l'audit et le journal gardent la clé hachée.
- ⚠️ La garde (« une fiche opposée suffit ») et la lecture par fiche peuvent sembler incohérentes à l'écran : la fiche non opposée n'annonce pas l'acquittement. C'est le suivi 3 ; le choix est à confirmer au HAG.

**Suivis à ouvrir** :
1. Doublons et versions à l'ingestion, toujours comparés par `Ins` (résidu d'AUD-34).
2. Index sur `MailMedicalDocumentBiology.MedicalDocumentId`.
3. Affichage de l'opposition portée par l'autre fiche d'un même matricule.

## Timings

*(généré par `tools/timing/report.sh --task task-331 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 43 min 52 s | 9 (33 s) | 4 (5 min 47 s) | — | api-mail 9B/4T |
| /sonar | ok | 5 min 28 s | 1 (15 s) | 5 (3 min 44 s) | 2 (35 s) | api-mail 1B/5T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touché (Repos: api-mail) |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché (Repos: api-mail) |
| /e2e | ok | 8 min 44 s | — | — | — | e2e ×3 (8 min 01 s) |
| /review | ok | 8 min 25 s | 1 (2.0 s) | 2 (3 min 08 s) | — | api-mail 1B/2T |
| /tech-writer | ok | 44 s | — | — | — | — |
| **Total cycle** | | **1 h 07 min** | **11 (51 s)** | **11 (12 min 40 s)** | **2 (35 s)** | |
