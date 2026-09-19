# todo-task-322.md — La page d'en-têtes lit 9 Mo de contenus qu'elle n'affiche pas : projeter les métadonnées seules, indexer `MailId`

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E011
**Single frontend**: true
**Priorité**: **1** — **93,6 % du temps SQL** du parcours praticien mesuré au banc (tir `terrain` 1 000 inscrits du 2026-09-19) tient dans le geste corrigé ici ; la cause est **mesurée**, attribuée par lecture du code, et le remède est une projection EF sans changement de contrat.

> **Origine.** Écrite le 2026-09-19 au matin comme cause *supposée* (relecture du
> stockage `bytea` des pièces jointes), cette US est devenue l'après-midi une cause
> **prouvée** : c'est le premier tir du banc instrumenté par `pg_stat_statements`
> (`Docs/audits/api-mail-loadtest-terrain-1000-postgres-20260919.md`). Le tir a
> aussi révélé une seconde moitié, plus lourde que la première : les **documents
> médicaux** sont chargés avec leur HTML, leur corps et leur vecteur d'embedding.
> Les deux moitiés sont le même défaut dans la même méthode ; elles forment une
> seule US. Les deux index de `MailId` qui manquent sont ajoutés dans le même lot,
> parce qu'ils se mesurent par le même tir avant/après.

## Ce qui est établi — tir `terrain-1000-20260919` (3 h, SLO 11/11, 92 actifs)

Sur **139 minutes de temps serveur SQL**, **130 vont à deux requêtes**, émises par la
même méthode, `LoadBulkMailLookupsAsync` (`Api/Mail/src/Infrastructure/Repositories/MailDb/MailRepository.cs`, ~l. 1412), en mode `MailBuildType.Header` :

| Requête | Appels | ms / appel | Lignes / appel | Blocs / appel | Part du SQL |
|---|---|---|---|---|---|
| `SELECT m.* … FROM "MailMedicalDocuments" m WHERE m."MailId" = ANY($1)` (+ deux compteurs corrélés) | 28 405 | **141** | 17 | 686 | **48,0 %** |
| `SELECT m."Id", m."Content", … FROM "MailAttachments" m WHERE m."MailId" = ANY($1)` | 28 404 | **134** | 28 | 491 | **45,6 %** |

**Le plan n'est pas la cause** : `explain (analyze, buffers)` sur une base praticien
hydratée rend ces requêtes en **0,2 à 0,5 ms**. **Le coût est le volume détoasté et
transféré** (tailles moyennes mesurées sur la base échantillon) :

| Colonne | Taille moyenne | Par appel |
|---|---|---|
| `MailAttachments.Content` (`bytea`) | 182 Ko | 28 lignes ≈ **5,1 Mo** |
| `MailMedicalDocuments.HtmlBody` | 222 Ko | 17 lignes ≈ **3,8 Mo** |
| `MailMedicalDocuments.Embedding` (vecteur) | 6 Ko | inclus |
| `MailMedicalDocuments.Body`, `MetadataJson` | 3,9 Ko | inclus |

**~9 Mo par page de 25 en-têtes**, lus dans le TOAST — dont **34 % (pièces) et 44 %
(documents) hors cache** (`pg_statio_user_tables`), ce qui fait à lui seul tomber le
taux de cache global de Postgres à 93,75 % —, transmis à api-mail, désérialisés en
entités EF, puis **jetés** : `ApplyBulkAttachments` ne garde que `FileName`,
`ContentType`, `Size` ; le DTO d'en-tête ne porte ni contenu de pièce ni HTML de
document. **Le client (Angular, Blazor, mobile) reçoit bien des en-têtes légers et va
chercher le contenu au clic** : la stratégie « en-têtes d'abord » est tenue dans le
contrat, pas dans la requête SQL.

**Appelants pendant le tir** : la page d'en-têtes `GET …/emails/{ids}` (15 615 appels)
et `GetMailAsync(Header)` derrière « marquer lu » (12 428) — 28 043 ≈ 28 405. Le tableau
de bord, lui, projette déjà correctement (`SELECT "FileName", "ContentType", "Size" FROM
"MailAttachments" WHERE "MailId" = $1`) : la projection attendue existe dans le code.

**Index.** Ni `MailAttachments` ni `MailMedicalDocuments` n'ont d'index sur `MailId`
(`MailDataContext.cs` : seul `MailContents` en a un, l. 159 ; le composite
`(Ins, MailId, Date)` de la l. 188 ne sert pas un filtre sur `MailId` seul). Seq scans
mesurés sur la base échantillon pendant le tir : 91 et 73. Coût nul aujourd'hui (150 à
250 lignes par praticien), croissant avec l'ancienneté de la boîte.

**Ce qu'on ne sait pas encore** : le gain **ressenti**. La page d'en-têtes répond en
97 ms au p50 pour 275 ms de SQL — les deux requêtes tournent en parallèle de l'IMAP et
entre elles. Le gain serveur est certain (SQL par requête HTTP 37,6 → ~3 ms attendu,
9 Mo d'allocations en moins par page) ; le gain praticien se lira au tir avant/après.

## Objective

Qu'afficher une liste de messages — boîte de réception, « marquer lu », filtre par
tag — **ne transporte jamais depuis la base ni le contenu d'une pièce jointe, ni le
HTML, le corps ou le vecteur d'un document médical**. Une ligne de liste a besoin de
savoir qu'une pièce existe (nom, type, poids) et qu'un document existe (titre, date,
catégorie, patient, marqueurs de biologie et de synthèse). Ses octets ne circulent que
lorsque le médecin **ouvre** le message ou **télécharge** la pièce, sur les chemins
`WithContent` et de téléchargement qui existent déjà.

Ce que cette US change pour le médecin : un serveur qui ne déplace plus des mégaoctets
de données de santé pour dessiner une liste, donc plus de praticiens servis par le même
hôte, et une boîte qui s'ouvre au moins aussi vite. Ce qu'elle **ne change pas** :
contenu affiché identique, contrats `MailDto` / `AttachmentDto` /
`MailMedicalDocumentDto` inchangés, aucun frontend touché.

### Périmètre

1. **Pièces jointes, page d'en-têtes** : le chargement bulk projette
   `Id, MailId, DocumentId, Guid, FileName, ContentType, Size` — jamais `Content`.
   `AttachmentCount` et l'exclusion du conteneur IHE_XDM (`IsXdmContainerPlaceholder`)
   ne lisent que ces colonnes et restent identiques.
2. **Documents médicaux, page d'en-têtes** (mode Header) : la projection garde toutes
   les colonnes de métadonnées et les deux compteurs corrélés (`BiologyCount`,
   `SummaryCount`, task-261), et **exclut `HtmlBody`, `Body`, `Embedding`,
   `MetadataJson`**. Le mode `WithContent` continue de charger l'entité entière.
   Établir **avant de projeter** ce que `BuildBulkMedicalDocumentDto` et l'enrichissement
   biologie (`EnrichManyWithBiologyAcksAsync`) lisent réellement : une colonne lue par
   le mapping reste dans la projection (même consigne que task-261 : on retire ce qui
   n'est pas utilisé, pas ce qu'on croit inutile).
3. **Liste par tag** (`GetMailsByTagAsync`, ~l. 3012) : remplacer les `Include` de
   `MailAttachments` et `MailMedicalDocuments` par les mêmes projections ; garder
   `AsNoTracking` + `AsSplitQuery` (task-070).
4. **Deux index** : `IX_MailAttachments_MailId` et `IX_MailMedicalDocuments_MailId`,
   par migration FluentMigrator dans `src/Infrastructure/Migrations/MailDb/`
   (convention `yyyyMMddHHmmss_Nom.cs`) **et** déclaration `HasIndex` dans
   `MailDataContext.cs`, les deux en cohérence (règle 7c : relire la migration, aucune
   opération fantôme, `MigrateUp` propre sur une base existante).
5. **Garde-fou d'ensemble** : un test prouve, sur le SQL réellement exécuté contre
   Postgres, que les trois chemins de liste ne sélectionnent ni `"Content"` de
   `MailAttachments`, ni `"HtmlBody"`, `"Body"`, `"Embedding"`, `"MetadataJson"` de
   `MailMedicalDocuments`. Outillage existant : `PostgreSqlFixture` (Testcontainers)
   et l'intercepteur `observed.Sql` de `ThreadCountsScopedLoadTests`.
6. **Télémétrie inchangée** : `DbOperationScope.AddMaterializedObjects` compte le même
   nombre d'objets ; ce sont les octets par objet qui changent.

### Hors périmètre, explicitement

- **Le stockage objet des pièces jointes** (sortir le `bytea` vers un S3 compatible) :
  ce correctif prend le gain de latence ; le déport reste un sujet de capacité Postgres,
  à instruire sur la mesure d'après.
- **La déduplication par signature** (`BuildExternalPdfSignatures`,
  `IsDuplicateOfExternalPdf`) : à l'ingestion, sur les DTOs venant de l'IMAP ; elle a
  besoin des octets et les a.
- **Les chemins `WithContent` et de téléchargement** (`StreamingFileResult`) : ils lisent
  les contenus légitimement.
- **Les sept requêtes par page** (tags, destinataires, PJ, contenus, fils, documents,
  doublons — témoin des 7 `DISCARD ALL` par requête HTTP) et les **3 lectures du
  registre** par requête : regroupement et cache sont une US ultérieure, après mesure.
- Toute modification de `Dtos/`, de `dtos-mss`, d'un frontend.

### Mesure — avant / après, obligatoire

Tir `terrain` 1 000 inscrits en **iso-conditions strictes** avec le tir du 2026-09-19
(même population **non purgée**, mêmes paramètres : 247 messages par boîte,
`UID_BASE=365`, corpus fileté 0,3, latence 96 ms, chauffe hydratée) — la ligne de
référence est déjà dans `Api/Mail/tests/loadtest-k6/reports/POSTGRES-INDEX.md` :

| Grandeur de référence (19/09) | Valeur | Attendu après |
|---|---|---|
| SQL ms / requête HTTP | 39,3 | ~3 |
| Taux de cache (blocs) | 93,75 % | ≥ 99 % |
| Lecture disque | 5,40 Mo/s | ÷ 5 |
| Top 1 du temps SQL | 48 % `MailMedicalDocuments` | une autre forme, sous 10 % |
| p50 / p95 page d'en-têtes (`read_list`/`emails`) | 97 / 155 ms | à lire, sans seuil |

Publication dans `Docs/audits/`, mise à jour de la mémoire « page d'en-têtes :
cause non établie » avec le verdict. **Aucun seuil de gain n'est un critère de DOD** :
le correctif se merge sur sa justesse, la mesure dit ce qu'il valait.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] `LoadBulkMailLookupsAsync` ne matérialise plus `Content` de `MailAttachments` (projection métadonnées)
- [ ] `LoadBulkMailLookupsAsync` en mode Header ne matérialise plus `HtmlBody`, `Body`, `Embedding`, `MetadataJson` de `MailMedicalDocuments` ; le mode `WithContent` est inchangé
- [ ] Le task file liste, pour chaque colonne exclue, la preuve qu'aucun mapping Header ne la lit (`BuildBulkMedicalDocumentDto`, `ApplyBulkContent`, enrichissement biologie)
- [ ] `GetMailsByTagAsync` n'a plus d'`Include` sur `MailAttachments` ni `MailMedicalDocuments` ; projections identiques
- [ ] Migration FluentMigrator + `HasIndex` : `IX_MailAttachments_MailId`, `IX_MailMedicalDocuments_MailId` ; migration relue (règle 7c), `MigrateUp` vert sur une base déjà migrée, `Down` présent
- [ ] **Test d'intégration Postgres** (`mss.mail.integration.tests`, `[Collection("PostgreSql")]`) : page d'en-têtes avec ≥ 2 messages porteurs de pièces non vides et de documents avec HTML — le SQL exécuté ne contient aucune des cinq colonnes exclues ; même assertion pour la liste par tag ; et le SQL du chemin `WithContent` les contient toujours
- [ ] **Preuve du ROUGE** : ce test est écrit d'abord et **échoue** sur le code actuel (log du run rouge dans le task file — mémoire `feedback-test-qui-stube-sa-propre-premisse`)
- [ ] **Non-régression fonctionnelle** : `AttachmentCount`, `Attachments` (nom, type, taille), `MedicalDocuments[]` (titre, date, catégorie, patient, `HasBiologyResults`, `HasPatientSummary`, doublons, PJ du document) de la page d'en-têtes sont **identiques** avant et après, exclusion du conteneur IHE_XDM comprise
- [ ] Les autres lectures de `MailAttachments` et `MailMedicalDocuments` du dépôt sont passées en revue ; le task file liste chacune avec « déjà projetée » ou « corrigée » ou « lit le contenu légitimement »
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché
- [ ] Aucune donnée de santé en clair dans les logs : le SQL capturé par le test n'est jamais journalisé avec ses paramètres
- [ ] Tir `terrain` 1 000 avant/après publié dans `Docs/audits/`, ligne ajoutée à `POSTGRES-INDEX.md`, mémoire « page d'en-têtes » mise à jour (peut être fait par l'humain au HAG si le banc n'est pas disponible dans le cycle ; à défaut, noter « mesure en attente » dans le task file, jamais de silence)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil par défaut), ou le profil `https-load-test` du skill de banc pour disposer d'un tenant hydraté (1 000 bases praticien en place, non purgées).
- Ouvrir `client-blazor` (`cd Client/Blazor && dotnet run`) ou `client-mobile`, se connecter sur une boîte contenant des messages avec pièces jointes (au moins un IHE_XDM.ZIP) et des documents CDA analysés.
- **Boîte de réception** : la liste s'affiche ; chaque message montre le bon nombre de pièces (le ZIP conteneur n'est pas compté), les noms et tailles d'avant, les marqueurs « biologie » et « synthèse » d'avant. Ouvrir un message : le HTML du document et le corps s'affichent (chemin `WithContent`). Télécharger une pièce : elle arrive entière.
- **Marquer lu** depuis la liste : l'état change, la ligne reste identique.
- **Filtre par tag** : poser un tag sur un message avec pièces et document, filtrer, vérifier les mêmes informations.
- **Preuve côté base** : dans Seq (`seq-local`) ou avec le log EF `Microsoft.EntityFrameworkCore.Database.Command` en Debug, ouvrir la boîte et vérifier que les `SELECT … FROM "MailAttachments"` et `… FROM "MailMedicalDocuments"` émis pendant le chargement de la liste **ne listent ni `"Content"`, ni `"HtmlBody"`, `"Body"`, `"Embedding"`, `"MetadataJson"`**. Les mêmes requêtes émises à l'ouverture du message ou au téléchargement les listent, elles.
- **Index** : `\d "MailAttachments"` et `\d "MailMedicalDocuments"` sur une base praticien montrent les deux index ; `explain` d'un `WHERE "MailId" = ANY(…)` sur une base de plus de quelques milliers de lignes les utilise.
- **Mesure** (si le banc est disponible) : `tests/loadtest-k6/run.sh terrain` en iso-conditions, puis comparer la nouvelle ligne de `POSTGRES-INDEX.md` à celle du 2026-09-19.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation interne, aucune exigence fonctionnelle nouvelle
- **Exigences DSR honorées** : non applicable — aucun comportement visible du PS ne change
- **INS** : non applicable — la US ne manipule aucun trait d'identité ; les colonnes projetées sont des métadonnées de fichier et de document (les traits patient déjà présents dans le DTO d'en-tête le restent, à l'identique)
- **Authentification PS** : inchangée (PSC / e-CPS existant) — les endpoints touchés gardent leurs garde-fous
- **Habilitations** : inchangées — même filtrage par tenant (`GetDataContextAsync`), le test `CrossTenantOwnershipTests` reste vert
- **Interop CI-SIS** : non applicable — les documents CDA ne sont ni lus ni produits ici ; leur HTML et leur corps cessent seulement d'être lus par un chemin qui ne les affichait pas
- **Tracé PGSSI-S** : inchangé — `AttachmentDownload` et `MailRead` (task-300/301) restent tracés sur leurs chemins ; l'affichage d'une liste n'est pas un accès au contenu et n'en émet pas. Effet positif : les octets d'une DSCP (pièce, compte-rendu) ne quittent plus la base pour un usage qui ne les affichait pas
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé, aucune donnée nouvelle stockée ni déplacée ; deux index ajoutés sur des colonnes techniques (`MailId`)
- **AIPD / impact RGPD** : inchangé — réduction de la circulation interne de données de santé, aucun traitement nouveau

## Timings

*(généré par `tools/timing/report.sh --task task-322 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 15 s | — | — | — | — |
| /develop | ok | 29 min 17 s | 2 (17 s) | 6 (4 min 01 s) | — | api-mail 2B/6T |
| /sonar | ok | — | 2 (35 s) | 10 (7 min 17 s) | 4 (58 s) | 2 itération(s), api-mail 2B/10T, no start marker |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché (Repos: api-mail ; working tree Angular : 2 fichier(s) modifié(s) hors task) |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché (Repos: api-mail ; Client/Mobile sur develop, propre) |
| /verify-visual | skipped | 0.5 s | — | — | — | aucun écran client-mobile touché |
| /review | ok | 4 min 54 s | 1 (5.4 s) | 1 (1 min 29 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 4 min 08 s | — | — | — | — |
| **Total cycle** | | **38 min 36 s** | **5 (57 s)** | **17 (12 min 48 s)** | **4 (58 s)** | |

## Branches
- `api-mail` (pushed) : feat/task-322-projection-entetes-index-mailid — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-322-projection-entetes-index-mailid

## Develop notes

### Preuve du ROUGE (2026-09-19, avant le correctif)

`dotnet test tests/mss.mail.integration.tests --filter HeaderListingProjectionTests` sur le code de `develop` (`6a82f28f`) :

```
Failed HeaderPageDoesNotReadAttachmentBytesNorDocumentEmbeddings   — Assert.All : `"Content"` présent dans SELECT … FROM "MailAttachments" ; `"Embedding"`, `"MetadataJson"` présents dans SELECT … FROM "MailMedicalDocuments"
Failed TagListingDoesNotReadAttachmentBytesNorDocumentBodies       — idem, plus `"HtmlBody"` dans la requête des documents (Include)
Passed HeaderPageStillRendersAttachmentsAndDocumentsIdentically    — caractérisation : verte des deux côtés, c'est son rôle
```

(Le premier run avait rendu quatre `NullReferenceException` : l'enrichissement des accusés de biologie exige un utilisateur courant que le dépôt sans contexte n'a pas — le décor a perdu sa ligne de biologie, les colonnes en cause sont celles du document.)

Après le correctif : **5 / 5 verts**, dont `MailIdIndexesMigrationTests` (base neuve du conteneur, `MigrateUp` avec le filtre de périmètre de production, `pg_indexes` porte les deux index).

### Ce que l'analyse des clients a changé au périmètre « documents »

La US demandait d'établir **avant de projeter** ce que les mappings Header lisent. Résultat :

| Colonne | Lue par un mapping de liste ? | Décision |
|---|---|---|
| `MailAttachments.Content` | non — `ApplyBulkAttachments` et `BuildBulkMedicalDocumentDto` ne recopient que nom, type, taille, Guid ; le DTO n'a jamais porté `Content` | **exclue** (page d'en-têtes, marquer lu, liste par tag, et aussi `WithContent` : le téléchargement est une route à part) |
| `MailMedicalDocuments.Embedding`, `MetadataJson` | non | **exclues** (page d'en-têtes et liste par tag) |
| `MailMedicalDocuments.HtmlBody`, `Body` | **oui en mode Header** — `BuildBulkMedicalDocumentDto` les recopie dans `MedicalDocuments[].BodyHtml/Body`, et **Blazor** (`MailDetailComponent` : `if (mail.Content == null) GetEmailContentAsync`, puis `MailBodyComponent` rend `doc.BodyHtml`) comme la **frise patient mobile** (`hasMedicalDocuments && !m.content`) affichent le document depuis la charge de la liste quand elle est présente. Angular recharge toujours (`loadContent`). | **conservées** sur la page d'en-têtes — les retirer serait un changement de contrat (écran vide sur Blazor). **Exclues** sur la liste par tag, dont le mapping (`MapTagMedicalDocument`) ne les lit pas. |

Conséquence chiffrée, à lire au tir avant/après : la moitié « pièces jointes » (45,6 % du temps SQL) est prise en entier ; la moitié « documents » (48 %) ne rend ici que l'embedding et les métadonnées (~7 Ko sur ~230 Ko par document). **Le HTML des documents (222 Ko × 17 par page) reste un poste ouvert, qui exige une US front** : Blazor et la frise mobile doivent recharger le contenu à l'ouverture comme Angular le fait déjà — alors seulement le serveur pourra cesser de le lire pour la liste. Proposé au PO comme suite, hors de cette US.

### Revue des autres lectures (DOD)

| Site | Statut |
|---|---|
| `MailRepository.GetMailAsync` ~l. 989 (pièces) | déjà projetée (`AttachmentDto` sans `Content`) |
| `MailRepository` ~l. 1299 (pièces par document) | déjà projetée |
| `MailRepository` ~l. 4619 (pièces, lecture unitaire) | déjà projetée |
| `PatientRepository` ~l. 442, ~l. 609 (pièces) | déjà projetées |
| `MailRepository.LoadBulkMailLookupsAsync` ~l. 1482 (pièces) | **corrigée** — `AttachmentMetadataProjection` |
| `MailRepository.GetMailsByTagAsync` ~l. 3103 / 3108 (pièces + documents) | **corrigée** — `Include` remplacés par deux projections |
| `MailRepository.LoadBulkContentLookupsAsync` ~l. 1563 (documents, Header) | **corrigée** — sans `Embedding` ni `MetadataJson`, corps conservés (voir ci-dessus) |
| `MailRepository.LoadBulkContentLookupsAsync` ~l. 1602 (documents, WithContent) | lit le contenu **légitimement** (page de détail) |
| `MailRepository.GetMailAsync` ~l. 1014 (documents, lecture unitaire) | entité entière pour un seul message — hors liste, non touchée |
| `MailRepository` ~l. 581 (`Include(MailMedicalDocuments)` dans la promotion d'un message) | chemin d'écriture, non touché |
| `MailRepository` ~l. 2685 / 2717 (`Content` lu pour le téléchargement / l'hydratation) | lit le contenu **légitimement** |

### Index (F2)

Découverte en écrivant le test : la **convention EF déclare déjà** `IX_MailAttachments_MailId` et `IX_MailMedicalDocuments_MailId` (index de clé étrangère), donc la base de la fixture (`EnsureCreated`) les avait, et seule la base réelle construite par FluentMigrator ne les avait pas — un test sur la fixture aurait été vert sur le code défaillant. D'où `MailIdIndexesMigrationTests` (base neuve + `MigrateUp`) et une migration FluentMigrator en API fluide (`Create.Index` / `Delete.Index`, comme ses voisines — la passe qualité a retiré le `IF NOT EXISTS` initial : aucune base réelle ne porte ces index, et la rejouabilité est celle de `VersionInfo`, règle 7c), plus les deux `HasIndex` explicites dans `MailDataContext` pour que le modèle dise ce que la base fait.

## Develop log

- Repos touched : api-mail
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : 434197b6 feat(mail): les listes de messages ne lisent plus les blobs qu'elles n'affichent pas (task-322)
  - api-mail : 1f2ce6b2 refactor(mail): simplify pass (/simplify) — task-322
- Local build / test : ✓ api-mail — 0 erreur, 4 498 tests verts (183 domain, 492 infrastructure, 837 api, 2 484 application, 502 integration + 16 skipped), deux fois (feature, puis re-validation après la passe qualité)
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 8 fichiers — boucle unique de raccrochage dans la liste par tag, projection tag réduite aux membres lus, migration en API fluide, constantes d'index partagées, coureur FluentMigrator de production réutilisé dans le test (`BaseRepository.CreateServices` → `internal`), observateur SQL partagé sur `PostgreSqlFixture`, sonde `SqlProbe`, assertions factorisées, commentaires allégés
  - Skipped (scope) : « table splitting » EF des colonnes blob (dépendant partagé sur la même table) — la forme générale qui rendrait tout `Include` correct par construction, mais un changement de contrat d'entité (sites d'écriture) → US dédiée, proposée au PO
  - Skipped (contract) : retirer `HtmlBody`/`Body` de la page d'en-têtes — Blazor et la frise mobile les lisent depuis la liste → US front
- DOD self-check : build ✓ · tests ✓ · projection pièces (Header, WithContent, tag) ✓ · projection documents Header sans Embedding/MetadataJson ✓ (corps conservés, preuve dans « Develop notes ») · liste par tag sans Include ✓ · migration + HasIndex, `MigrateUp` rejoué sur base neuve ✓ · test SQL réel avec preuve du rouge ✓ · non-régression fonctionnelle ✓ · revue des autres lectures ✓ · contrat inchangé (0 fichier `Dtos/`, 0 frontend) ✓ · aucun paramètre SQL journalisé hors test ✓ · tir avant/après : **à faire après /review** (demande humaine du jour : rejouer `terrain` 1000 iso-conditions et chiffrer les gains)
- Next step : /sonar task-322

## Sonar log

Serveur SonarQube 9.9.8 (`sonar.login`), projet `healthplatform-api-mail`, période « new code » = version précédente (projet, pas de branche en édition Community). Deux analyses complètes (build Release + 5 passes OpenCover + scan).

| KPI | Baseline (analyse du 17/09, `develop`) | Après task-322, itération 1 | Final (itération 2) |
|---|---|---|---|
| Quality Gate | **ERROR** (hotspot non revu) | OK | **OK** |
| Bugs / vulnérabilités | 0 / 0 | 0 / 0 | 0 / 0 |
| Code smells (total) | 228 | 230 | **216** |
| New code smells | 35 | 36 | **22** (−39 %) |
| New security hotspots | 1 | 0 | 0 |
| Couverture globale / new code | 87,8 % / 85,9 % | 87,8 % / 84,9 % | 87,8 % / 84,9 % (seuil QG 80 %) |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | A / A / A |
| Duplication new code | 0,10 % | 0,11 % | 0,11 % |

**Phase 1 (new code de la task)** : une seule issue issue du diff de task-322 — S125 (commentaire assimilé à du code) — corrigée. Aucun hotspot. Couverture du new code au-dessus du seuil de la Quality Gate (80 %), sous la cible interne de 95 % : la part non couverte est portée par `PostgresTenantRegistryClient` (166 lignes), `AccountController` (71), `MailController` (26) — code d'E016 antérieur à cette task, pas le sien.

**Phase 2 (dette héritée, 1 itération)** : 13 issues mécaniques corrigées — S1144 ×2 (constantes mortes de `BaseRepository`), CA1816 ×7 (`GC.SuppressFinalize` dans les `DisposeAsync` de fixtures), xUnit2033 ×4. **Restent 22**, toutes hors du diff : CA1068 ×15 (ordre du `CancellationToken` sur `ITenantRegistryClient` — interface + implémentation + appelants, hors périmètre d'une US de performance), AV0011 ×4 (version d'API par défaut dans des tests d'intégration), S3925 ×2 (`ISerializable` sur `TenantRegistryExceptions`), S3776 ×1 (blacklistée → `/sonar-s3776`). Acceptées, à traiter par la task E016 qui les a produites.

Commits Sonar : `fix(sonar/new): resolve 14 new-code findings — S125, S1144, CA1816, xUnit2033 (task-322)`.

## Lint log

- client-angular : **skipped** — repo non listé dans `**Repos**:` (api-mail seul) ; working tree `Client/Angular/front/` : 2 fichier(s) modifié(s), tous hors task-322, non touchés.

## Lint mobile log

- client-mobile : **skipped** — repo non listé dans `**Repos**:` ; `Client/Mobile` sur `develop`, arbre propre (0 fichier).

## Visual verify log

- **skipped** — aucun écran `client-mobile` touché par task-322 (backend seul).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/246 — label `awaiting-human-merge`

## Code Review Summary

**APPROVED** — 18 fichiers relus (revue indépendante), 0 bloquant, 4 suggestions non bloquantes (XML doc décalé dans `PostgreSqlFixture.cs`, assertion `"Body"` optionnelle sur le test tag et `EnableSensitiveDataLogging` superflu, `persisted[0]` résiduel dans `MailRepositoryTests.cs` l. 1695, libellé « 5 min » vs 330 s dans `BaseRepository.cs`).

- `MailRepository.cs` — ✅ chaque mapping consommateur ne lit que des membres projetés ; raccrochage tag sûr (`MailTags` unique, ids filtrés, collections initialisées) ; aucune écriture ne suit les entités projetées
- `MailDataContext.cs` — ✅ `HasIndex` sur les noms de la migration ; index de convention déjà présents sous le même nom, pas de doublon
- `20260919180000_AddMailIdIndexesOnAttachmentsAndDocuments.cs` — ✅ version la plus haute, `Up`/`Down` symétriques, idiome des voisines
- `BaseRepository.cs` — ✅ `CreateServices` en `internal` pour le test, constantes mortes retirées, cref mis à jour
- Tests (`HeaderListingProjectionTests`, `MailIdIndexesMigrationTests`, `SqlProbe`, fixture) — ✅ preuve sur le SQL exécuté, rouge établi sur `develop`, migration rejouée par le coureur de production, caractérisation du DTO
- Nettoyage Sonar (13 fichiers) — ✅ mécanique, comportement inchangé

Validation `/review` : build 0 erreur, 4 498 tests verts (troisième validation complète du cycle). Sync `develop` : déjà à jour.

## Mesure avant / après (tir A/B `terrain` 1 000, 2026-09-19 soir)

Audit : `Docs/audits/api-mail-loadtest-terrain-1000-task322-ab-20260919.md`. Tir A = matin (`develop`), tir B = soir (branche task-322), un seul facteur : le code.

| Grandeur | A | **B** | Δ |
|---|---|---|---|
| Temps SQL cumulé (3 h) | 139 min | **55,7 min** | −60 % |
| Coût SQL par requête HTTP | 39,3 ms | **16,5 ms** | −58 % |
| Backends actifs (équivalent) | 0,80 | **0,33** | ÷ 2,4 |
| Requête « pièces jointes » de la liste | 63 min (45,6 %) | **disparue** | |
| Requête « documents » de la liste | 141 ms/appel | 97 ms/appel | −31 % |
| Taux de cache / lecture disque | 93,75 % / 5,40 Mo/s | **95,72 % / 3,08 Mo/s** | |
| cgroup mémoire Postgres | 99–100 % | **37–39 %** | cache de pages libéré des blobs |
| Page d'en-têtes p50 / p95 | 96,6 / 155 ms | **69,9 / 110 ms** | −28 % |
| SLO | 11/11 | 10/11 — « Recherche » rouge par `api.openai.com` (p95 sortant 0,96 → ≥ 10 s), non attribuable | |

DOD « tir avant/après publié, ligne `POSTGRES-INDEX.md` ajoutée » : ✅ fait. Mémoire « page d'en-têtes » mise à jour.
