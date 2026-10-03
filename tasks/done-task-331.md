# todo-task-331.md — Un document rattaché à un patient apparaît dans son dossier, et le dossier ne mélange jamais deux identités qui partagent un matricule

**Repos**: api-mail, client-angular, client-blazor, client-mobile
**Dependencies**: — (aucune ; à coordonner avec task-191, qui traite les **doublons** de fiches pour une même identité)
**Epic**: E009
**Single frontend**: false — périmètre étendu aux trois clients le 2026-10-03 (voir « Extension du périmètre »)
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
- Un écran « file à intégrer » regroupant tous les documents sans fiche (le rattachement reste
  ouvert depuis le mail qui porte le document).

## Extension du périmètre — choisir un patient quand l'appariement échoue (décision humaine, 2026-10-03)

> Posée par l'humain au HAG de la première itération : « si les traits d'identité du CDA ne
> permettent pas de trouver un dossier, il faut pouvoir tout de même choisir un patient, sinon il
> n'est pas possible de rattacher. » À coder **dans cette US**.

**Constat** (analyse des trois clients, develop @ 2026-10-03) — Angular, Blazor et mobile ont le
même parcours (task-012 / task-137) : bandeau « Rattachement en attente » dans le détail d'un mail →
dialogue « comparaison visuelle » qui n'affiche **que** les candidats de `GET /patients/match`.

| Cas | Les trois clients aujourd'hui |
|---|---|
| `/match` renvoie 0 candidat | seul « Ignorer » ; le document ne peut pas être rattaché |
| `/match` en erreur | message ou toast, aucun « Réessayer », seul « Ignorer » |
| CDA sans nom, prénom ni date de naissance (le sexe n'est pas compté) | **aucun bouton** dans le bandeau ; le compteur ⏳ / « À rattacher (N) » l'annonce quand même |
| Recherche libre de patient | existe dans chaque client (écran Patients) mais n'est jamais branchée sur le rattachement |

`/match` ne retient que les fiches dont le nom ou le prénom **contient** celui du CDA (`ILIKE %…%`) :
une faute de frappe, un nom d'usage ou un accent suffisent à vider la liste.

La règle de task-176 interdit le rattachement **automatique** par traits, et la création de patient.
Elle n'interdit pas que le **praticien choisisse lui-même** une fiche existante : c'est le recours
manquant.

**Périmètre ajouté (les trois clients, comportement identique)** :

6. **Recherche libre dans le dialogue de rattachement** : un champ de recherche de patient
   (nom, et INS si le client sait déjà le faire), toujours disponible sous la liste des candidats,
   mis en avant quand `/match` ne renvoie rien. Il réutilise la recherche patient existante du client
   (`/patients/search` ou `/patients/search/advanced`). Le résultat choisi est une **fiche
   existante** ; jamais de création.
7. **Confirmation d'un choix manuel** : rattacher une fiche trouvée par la recherche libre (et non
   proposée par `/match`) demande une confirmation explicite qui rappelle les traits du document et
   ceux de la fiche (identito-vigilance). Rattacher un candidat de `/match` reste en un clic.
8. **Document sans trait exploitable** : le bandeau propose aussi un bouton pour un document sans
   nom, prénom ni date de naissance ; le dialogue s'ouvre directement sur la recherche libre (sans
   appeler `/match`, qui répond 400 sans trait). Le compteur et le bandeau comptent alors les mêmes
   documents.
9. **Erreur de `/match`** : un bouton « Réessayer » ; la recherche libre reste utilisable.

Contrats : **aucun changement** attendu (`attach-patient`, `/patients/search`, `/patients/search/advanced`
existent). Si `/develop` constate qu'un champ manque au résultat de recherche pour comparer les
identités (date de naissance, sexe, INS), il l'établit et l'ajoute dans `dtos-mss` (branche paresseuse).

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

### DOD de l'extension (points 6 à 9) — Angular, Blazor, mobile

- [ ] Build et tests verts sur `client-angular`, `client-blazor`, `client-mobile` (commandes de la table des repos)
- [ ] Test de composant du dialogue, par client : 0 candidat → la recherche libre est affichée ; une recherche renvoie une fiche ; la choisir demande une confirmation ; confirmer appelle `attach-patient` avec l'identifiant de la fiche choisie et émet le rattachement
- [ ] Test de composant : un candidat de `/match` se rattache sans confirmation supplémentaire (non-régression)
- [ ] Test de composant : document sans nom, prénom ni date de naissance → `/match` n'est pas appelé, la recherche libre est ouverte d'emblée
- [ ] Test de composant : `/match` en erreur → « Réessayer » relance l'appel ; la recherche libre reste utilisable
- [ ] Test du bandeau (détail du mail), par client : un document sans trait a son bouton de rattachement ; le nombre de boutons égale le compteur « en attente »
- [ ] Aucun bouton ni chemin de création de patient dans le dialogue (test existant conservé ou étendu)
- [ ] `data-testid` sur le champ de recherche, chaque résultat, la confirmation et « Réessayer » ; libellés via i18n là où le client en a (Blazor `Localizer`), en dur en français sinon (Angular, mobile — convention actuelle)
- [ ] Scénario `E2E-PATIENT-002` ajouté à `Api/Mail/e2e/scenarios.yml` (clients mobile et angular **requis**), donnée de seed déclarée (document sans INS dont les traits ne correspondent à aucune fiche, et une fiche existante à choisir), et implémenté dans les deux suites : rattachement par recherche libre, puis le document est **présent dans le dossier de la fiche choisie** (règle 1b côté frontend)
- [ ] `/e2e` vert sur les deux voies, parité verte

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor ou mobile connecté à une boîte de test.
2. Recevoir un mail de test portant un CDA **sans INS** (corpus du banc) → il apparaît dans « à intégrer ».
3. Le rattacher à un patient existant de test → **Attendu** : il disparaît de « à intégrer » **et apparaît** dans la chronologie du patient. Avant : il n'apparaît nulle part.
4. Préparer (données de test anonymisées) deux fiches de même matricule dans deux domaines ; ouvrir chacune → chacune ne montre que ses propres documents.
5. Poser une opposition sur l'une, tenter un envoi vers le patient correspondant → la demande d'acquittement s'affiche. Décision de la première itération (à confirmer) : l'adresse Mon Espace Santé ne portant pas le domaine, l'acquittement est demandé dès qu'**une** fiche du matricule est opposée.
6. **Choix manuel quand l'appariement échoue** (Angular, Blazor et mobile) : ouvrir un mail dont le CDA sans INS porte un nom qui ne correspond à aucune fiche → « Rattacher » → le dialogue annonce 0 candidat et propose la recherche ; chercher un patient existant par son nom, le choisir → une confirmation rappelle les traits du document et ceux de la fiche → confirmer → le document quitte le bandeau et apparaît dans le dossier de ce patient.
7. **Document sans trait** : un CDA sans nom, prénom ni date de naissance a désormais un bouton dans le bandeau ; le dialogue s'ouvre directement sur la recherche.
8. **Non-régression** : un candidat proposé par `/match` se rattache toujours en un clic, sans confirmation ; aucun bouton « Créer un patient » nulle part.

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
- *Extension du 2026-10-03 :*
  - `client-blazor` (pushed) : fix/task-331-dossier-patient-par-fiche — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-331-dossier-patient-par-fiche (depuis `origin/develop` @ `2ced0fb`)
  - `client-mobile` (pushed) : fix/task-331-dossier-patient-par-fiche — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-331-dossier-patient-par-fiche (depuis `origin/develop` @ `a3570b8`)
  - `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` (`feature/nova-rewriting-mss` au 2026-10-03) — l'humain gère branche, commit, push et PR TFS. Les deux `environment.ts` modifiés localement par l'humain ne sont pas touchés.
  - `api-mail` : même branche ; la PR #271 reste ouverte et passe en `awaiting-us-completion` (règle 11) jusqu'à ce que l'US assemblée soit prête.

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
| /develop | ok | 54 min 00 s | 19 (2 min 54 s) | 15 (10 min 47 s) | — | api-mail 11B/8T, client-blazor 4B/3T, client-angular 2B/2T, client-mobile 2B/2T |
| /sonar | ok | 6 min 18 s | 2 (34 s) | 10 (8 min 04 s) | 4 (1 min 14 s) | api-mail 2B/10T |
| /lint-angular | ok | 26 s | — | — | — | — |
| /lint-mobile | ok | 11 s | — | — | — | — |
| /e2e | ok | 9 min 30 s | — | — | — | e2e ×6 (16 min 30 s) |
| /review | ok | 5 min 57 s | 5 (31 s) | 6 (6 min 11 s) | — | api-mail 2B/3T, client-blazor 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 44 s | — | — | — | — |
| **Total cycle** | | **1 h 17 min** | **26 (4 min 01 s)** | **31 (25 min 03 s)** | **4 (1 min 14 s)** | |

Autres commandes mesurées : lint ×2 (14 s)

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | patient-attachment-dialog | patient-attachment-dialog | a715989e69434a318fddc14a9e78a087 | reused, puis `edit_screens` (recherche libre, liste de résultats, carte de confirmation) — **délai MCP dépassé, attendu, non relancé** : la mise à jour est probablement appliquée côté Stitch, à vérifier dans l'UI | https://lh3.googleusercontent.com/aida/AEtjO1VSF-ohz5I73BGiuu1ZaI0fAoESPNFIjIS3cEyd4DtGuyCrCXO3IugHyZgzU0_YHtM1369Uvf6XdG9q4zRgbGxEEZhc1X8hKbKCxUPei3NIlafdBGH5-UPNwuluGZ9oUgoQkv9m782X3b4XRZbQRvbS9mFyLjcvbSP3JufULPLS_WC9DMiO4ORqGTRV8A4-3sp0cipcgvneTxymFkfY5yaYqyHBgO03cgMLvR3E96E1Uy9cOv4OJm-Ol1aG (capture d'avant la mise à jour) |
- ⚠ Rename / labelliser in Stitch UI : none
- ⚠ Doublons suspectés à nettoyer dans l'UI : none
- Stitch reachable : ✓
- Référence appliquée : la structure existante (traits du CDA, candidats classés, « Ignorer ») est conservée. La section de recherche et la carte de confirmation reprennent les composants Ionic du dialogue (cartes, listes, boutons primaire et secondaire).

## Develop log — extension du 2026-10-03 (choix manuel du patient)

**Repos touchés** : `api-mail` (seed e2e et catalogue seulement, aucun code de production), `client-blazor`, `client-angular` (code-only), `client-mobile`. Aucun contrat ne change : la recherche libre réutilise `GET /patients/search`, dont l'identifiant de fiche est garanti par la première itération (test HTTP `APatientFoundBySearch_CarriesItsRecordId_AndItsFolderOpens`). Pas de branche `dtos-mss`.

### Commits
- `api-mail` : `ace30916` seed et catalogue E2E-PATIENT-002 ; `e98c2936` relecture des traits sans les espaces du corpus ; `b0979b0f` passe qualité.
- `client-blazor` : `fbd26cd` feature ; `322d608` passe qualité.
- `client-mobile` : `640676d` feature ; `7353bf7` parcours e2e ; `438bd20` passe qualité.
- `client-angular` (code-only, **non commité**, branche `feature/nova-rewriting-mss`) : `libs/mss/.../patient-attachment-dialog/*` (ts, html, scss, spec), `libs/mss/.../mail-detail/mail-detail.component.{ts,html,spec.ts}`, `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/{session,e2e-backend}.ts`. Les deux `environment.ts` modifiés par l'humain ne sont pas touchés.

### Ce qui change (identique sur les trois clients)
- **Dialogue de rattachement** : section « Rechercher un patient » toujours présente (champ, « Rechercher » à partir de 2 caractères, résultats avec « Choisir »), mise en avant par une consigne quand aucun candidat ne correspond. Une fiche choisie par la recherche ouvre une **confirmation** qui montre son identité sous les traits du document ; « Confirmer le rattachement » appelle `attach-patient`, « Retour » revient aux résultats. Un candidat de `/match` se rattache toujours en un clic. Aucune création de patient.
- **Document sans trait** (ni nom, ni prénom, ni date de naissance) : `/match` n'est pas appelé (il répond 400), le dialogue s'ouvre sur la recherche.
- **Échec de `/match`** : « Réessayer » relance l'appel ; la recherche reste utilisable. Blazor : `MatchByTraitsAsync` rend `null` en cas d'échec (au lieu d'une liste vide indiscernable de « personne »).
- **Bandeau** : tout document sans `patientId` a son bouton, y compris sans trait ; le bandeau et le compteur « en attente » comptent les mêmes documents. Texte : « … ne porte aucun INS qualifié et n'est rattaché à aucun patient ».

### Tests et preuves rouges
| Client | Tests | Preuve |
|---|---|---|
| Blazor | `PatientAttachmentDialogTests` (7) et `PatientAttachmentBannerTests` (2), bUnit | Mutation « bandeau limité aux documents à trait » → les 2 tests du bandeau rouges ; « Choisir rattache sans confirmation » → les 2 tests de confirmation rouges. Restauré, 401/401 |
| Angular | 7 cas dans la spec du dialogue, 2 dans la spec `mail-detail` (vitest) | Mêmes mutations → 4 rouges ; restauré, 549/549 (`mss-lib`), 11 projets verts |
| Mobile | 7 cas dans la spec du dialogue, 2 dans `mail-detail` (le test « masque le bandeau sans trait » est scindé : l'intention change) | Mêmes mutations → 4 rouges ; restauré, 981/981 |
| api-mail | `E2eUnattachedXdmTests` (5) dont le passage de la fixture par le vrai `CdaParsingService` ; `E2eSeedPlanTests` (+2) | Mutation : INS réinjectée dans la fixture → `Document_CarriesNoInsIdentifier` rouge |

### Parcours e2e E2E-PATIENT-002 (règle 1b côté frontend)
- **Catalogue** (`Api/Mail/e2e/scenarios.yml`) : scénario v1, mobile et angular **requis** ; données `cda-sans-ins-a-rattacher` et `fiche-patient-bio`.
- **Seed** : une lettre de liaison du corpus ANS (`LDL-SES_2022.01`), réécrite sans INS ni adresse Mon Espace Santé, aux traits « SANSDOSSIER Camille » qu'aucune fiche ne porte, embarquée dans `mss.mail.e2e` (le corpus local n'est pas versionné). Le seed relit : document servi sans patient, `/patients/match` vide, fiche `PAT-TROIS` (créée par le compte rendu de biologie) présente avec son identifiant. Il écrit l'uid du message au manifeste : une ligne porteuse d'un CDA affiche le titre du document, pas l'objet.
- **Choix d'un document non biologique** : un second compte rendu de biologie serait lui aussi en attente d'acquittement et ferait mentir E2E-BIO-001, qui en attend exactement un. Le nouveau message est lu, et n'est pas le plus ancien : les compteurs et l'ordre des parcours existants ne bougent pas.
- **Parcours** (mobile et Angular) : le dossier de PAT-TROIS ne contient pas le message (relu du serveur) → bandeau → aucun candidat → recherche « PAT-TROIS » → une seule fiche → confirmation → `POST attach-patient` accepté → le dossier relu **contient** le message → après rechargement, contenu chargé, le bandeau ne le propose plus.
- **Preuve par mutation** (`--serve-only`, test seul) : « Confirmer » sans appel (`if (Date.now() > 0) return`, bundle neuf vérifié dans le journal du serveur de dev) → rouge sur « le rattachement est accepté par le serveur » (mobile, Angular) ; restauré → vert (mobile 6,0 s, Angular 6,2 s, seed neuf).
- **Trouvé en route, corrigé dans le seed** : le parseur CDA garde l'espace qui suit `<family>` dans le corpus ANS (`"SANSDOSSIER "`). La relecture du seed comparait au caractère près : premier banc en échec d'outillage, cause établie par le test qui passe la fixture dans `CdaParsingService`. Le seed compare désormais les traits sans espaces de bord, comme les clients.
- **Trouvé en route, corrigé dans le test** : l'ancre Angular « onglet du document rattaché » n'existe pas pour un message à document unique (pas d'onglets) ; l'absence du bandeau se lit désormais après le chargement de `mss-mail-body`, alimenté par le même `mailContent()` que le bandeau.

### Passe qualité (/simplify, 4 revues)
- **Appliqué** :
  - seed : l'uid est rendu par la vérification au lieu d'un champ écrit en effet de bord ; lectures JSON par `GetJsonOkAsync` ; `StringOf` partagé avec `PlaywrightReport` (`E2eJson`) ; le test de la fixture lit les domaines INS dans `InsIdentityDomain` ;
  - Angular et mobile : une seule remise à zéro par état (`resetSearch` pour la recherche, `clearCandidates` pour l'appariement) ; la ligne « date · sexe · INS » en un seul `ng-template` ; le nom d'une fiche par `getPatientFullName` ;
  - Blazor : la même ligne en un seul fragment `IdentityMeta` ; « Retour » sans méthode dédiée.
  - Re-validation verte partout (api 1 166, Blazor 401, Angular 11 projets, mobile 981).
- **Écarté** : requête d'en-têtes en double dans le seed (une fois par run) ; double déclencheur Entrée / submit sur mobile (le second appel est déjà bloqué par `isSearching`, garder Entrée préserve la saisie au clavier) ; réutiliser `mss-patient-search` / `SearchPatientComponent` (recherche à la frappe, « patients du jour » sur saisie vide, pas de bouton : comportement différent).
- **Suivis proposés** (hors périmètre) :
  4. `CdaParsingService` : retirer les espaces de bord des traits patient à l'analyse ; aujourd'hui chaque lecteur doit penser au `Trim()`, et les fiches créées depuis le corpus portent l'espace.
  5. `GET /patients/match` sans trait : renvoyer `[]` (ce que fait déjà le dépôt, et ce qu'annonce le commentaire du contrôleur) au lieu d'un 400 ; les trois clients n'auraient plus à recopier la règle « a des traits ». Le serveur compte le sexe comme trait, les clients non.
  6. Recherche de fiche : constante de longueur minimale non partagée (2 dans le dialogue, 3 dans `SearchPatientComponent` Blazor).

### Vérifications
- Build + tests verts : api-mail, client-blazor, client-angular (build `weda2`, tests 11 projets), client-mobile (build, 981 tests).
- Lint des fichiers touchés : 0 erreur (Angular : avertissements `max-lines` et `@example` vides préexistants ; mobile : 0). Budget de style mobile : le SCSS du dialogue dépasse le seuil d'**avertissement** de 2 Ko (2,47 Ko ; erreur à 8 Ko), comme 12 autres composants.
- Contrôles mécaniques C# : un S125 attrapé avant commit (commentaire du seed) ; S4581 et S6562 corrigés à la main dans les tests Blazor. Les trois sont consignés dans `conventions/csharp.md` (S125 → 9 ; S4581 et S6562 créés).
- Branches poussées : api-mail, client-blazor, client-mobile à jour avec `origin`.
- Next step : `/sonar task-331`

## Sonar log — extension du 2026-10-03

**Analyse** : une passe complète sur `fix/task-331-dossier-patient-par-fiche` (commit `b0979b0f`), SonarQube 9.9.8, avec la couverture des cinq suites : domain 190, application 3 373, infrastructure 681, api 1 166, integration 743 (+16 ignorés préexistants), 0 échec.

**Itérations de correction** : 0. L'extension ne touche api-mail que dans des projets de test et l'outil e2e (`SonarQubeTestProject`), hors du périmètre analysé comme code de production.

| Métrique | Baseline (passe task-331 du 2026-10-02) | Final (extension) | Δ |
|---|---|---|---|
| Quality Gate | OK | **OK** | = |
| New coverage | 97,5 % | 97,5 % | = |
| Coverage projet | 98,0 % | 98,0 % | = |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | = |
| Code smells | 13 | 13 | = |
| Duplication | 0,4 % (nouveau code 0,15 %) | 0,4 % (nouveau code 0,15 %) | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

- **Constat restant sur la période de nouveau code** : S107 sur `SemanticSearchService:379` (8 paramètres), déjà relevé par task-329 et par la première passe de task-331. Il n'appartient pas au code de la task : laissé, comme alors.

## Lint log — extension du 2026-10-03 (client-angular)

- Commande : `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` (Client/Angular/front, branche `feature/nova-rewriting-mss`, code-only).
- Résultat : **0 erreur**, avertissements préexistants seulement (`jsdoc/require-example` sur des `@example` vides, `max-lines` sur `mail-detail.component.ts` et les deux specs e2e). Aucune itération, aucune modification.
- Build `weda2` et tests (11 projets) verts après la passe qualité de `/develop`, arbre inchangé depuis : pas de re-validation.
- Rappel code-only : les fichiers Angular de la task restent **non commités**, à commiter et pousser par l’humain sur TFS (liste dans le Develop log).

## Lint mobile log — extension du 2026-10-03

- Branche `fix/task-331-dossier-patient-par-fiche` (Client/Mobile), à jour avec `origin`.
- `npm run lint` : **All files pass linting** (0 erreur, 0 avertissement). Aucune itération, aucun commit.
- Build et tests (981) verts après la passe qualité de `/develop`, arbre inchangé depuis.

## E2E log — extension du 2026-10-03

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | `api-mail` et `client-mobile` touchés | ✅ verte | 27 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 20 s |
| angular | `api-mail` et `client-angular` touchés | ✅ verte | 27 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 00 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-331-dossier-patient-par-fiche` (E2E-PATIENT-002 v1 ajouté).
- Checkouts : `Client/Mobile` sur `fix/task-331-dossier-patient-par-fiche` ; `Client/Angular/front` sur `feature/nova-rewriting-mss` avec le travail non commité de la task (aucune opération git).
- Porte `gate` : code 0.
- Quarantaines : aucune. Flaky : aucun. Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun (les deux specs portent E2E-PATIENT-002).
- Démontage : complet (ports 4200 et 8100 libres, aucun conteneur e2e résiduel).
- Amélioration continue (`conventions/e2e.md`) : ligne « Trous du filet » pour le rattachement manuel impossible ; consigne `ancre-conditionnelle`.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 1 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche | ✅ | ✅ |
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

## PRs — extension du 2026-10-03

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/271 — corps mis à jour (extension, parcours e2e, plan de test), label repassé de `awaiting-us-completion` à `awaiting-human-merge` : l'US assemblée est prête.
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/88 — label `awaiting-human-merge`.
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/85 — label `awaiting-human-merge`.
- `client-angular` : code-only, l'humain gère commit, push TFS et PR. Fichiers modifiés, non commités, sur `feature/nova-rewriting-mss` :
  - `front/libs/mss/src/features/mail/components/patient-attachment-dialog/patient-attachment-dialog.component.{ts,html,scss,spec.ts}`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.{ts,html,spec.ts}`
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/session.ts`, `front/e2e/mss-e2e/support/e2e-backend.ts`
  - (les deux `environment.ts` modifiés sont ceux de l'humain, hors task)
- `dtos-mss` : aucune PR, aucun contrat ne change.
- **Ordre de merge** : les quatre ensemble (règle 11). Les clients dépendent de la recherche patient qui renvoie l'identifiant de la fiche (api-mail #271).

## Code Review Summary — extension du 2026-10-03

**Verdict : APPROVED** (0 bloquant).

- **Build et tests** : api-mail (domain 190, application 3 373, infrastructure 681, api 1 166, integration 743 + 16 ignorés), client-blazor 401 (+2 ignorés), client-mobile 981, client-angular build `weda2` et tests de 11 projets. 0 échec.
- **DOD de l'extension** :
  - [x] Build et tests verts sur les trois clients
  - [x] Tests de composant du dialogue, par client : 0 candidat → recherche affichée ; une fiche trouvée ; choix → confirmation ; confirmer → `attach-patient` avec l'identifiant choisi
  - [x] Un candidat de `/match` se rattache sans confirmation (non-régression)
  - [x] Document sans trait → `/match` non appelé, recherche ouverte d'emblée
  - [x] `/match` en erreur → « Réessayer » relance ; la recherche reste utilisable
  - [x] Bandeau : bouton pour un document sans trait ; boutons = documents sans patient
  - [x] Aucune création de patient (tests « no creation » dans les trois clients)
  - [x] `data-testid` sur le champ, chaque résultat, la confirmation et « Réessayer » ; libellés Blazor par `Localizer` (FR et EN), en dur en français sur Angular et mobile
  - [x] E2E-PATIENT-002 au catalogue (mobile et angular requis), données de seed déclarées, implémenté dans les deux suites, document relu dans le dossier de la fiche
  - [x] `/e2e` vert sur les deux voies, parité verte
- **Verrou 4a (règle 1b)** : aucun comportement atteignable par un endpoint ne change dans cette itération (api-mail : outillage e2e et tests seulement). Côté clients, le test d'intégration du parcours est E2E-PATIENT-002, vu rouge sous mutation sur les deux clients.
- **Verrou 4b** : `## E2E log` de l'extension vert, recopié dans les trois PRs.
- **Revue par zone** :
  - ✅ Dialogues (3 clients) : recherche par `GET /patients/search` existant, confirmation obligatoire pour une fiche non proposée, aucun chemin de création, états remis à zéro à l'ouverture.
  - ✅ Bandeaux : cas particulier « au moins un trait » retiré, alignés sur le compteur serveur.
  - ✅ Seed e2e : chaque donnée du parcours est relue avant de rendre la main ; fixture sans donnée réelle (corpus de test ANS réécrit).
  - ⚠️ Mobile : Entrée et le submit du formulaire déclenchent tous deux la recherche ; le second appel est bloqué par `isSearching`.
  - ⚠️ Les clients ne comptent pas le sexe seul comme trait, le serveur si : un document au seul sexe s'ouvre sur la recherche. Voir le suivi 5.

**Suivis à ouvrir (extension)** :
4. `CdaParsingService` : rogner les traits patient à l'analyse (l'espace qui suit `<family>` du corpus ANS arrive en base).
5. `GET /patients/match` sans trait : rendre `[]` au lieu de 400, comme le dépôt et le commentaire du contrôleur, pour retirer la règle « a des traits » recopiée dans trois clients.
6. Longueur minimale de recherche de fiche non partagée (2 dans le dialogue, 3 dans `SearchPatientComponent` Blazor).
