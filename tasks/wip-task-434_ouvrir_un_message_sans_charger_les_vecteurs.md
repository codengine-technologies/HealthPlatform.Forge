# todo-task-434.md — Ouvrir un message ne charge plus les vecteurs du document et du contenu

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1**, demandée par l'humain le 2026-11-08 après le bilan du lot 426-432. Le gain direct attendu est
**modeste**, borné ci-dessous. La valeur principale est la **garde** : la classe `colonne-volumineuse` en est à sa
troisième récidive, et la prévention nommée deux fois par `/loadtest-findings` n'a jamais été posée.

> **Origine.** Findings FND-007 et FND-009 du registre `Docs/audits/findings-registry.md`, confirmés deux fois :
> - au rejeu du 2026-11-07 (tir `apres` du 2026-11-06) ;
> - au tir `bilan-apres` du 2026-11-08, code `5b4e394f`, section « Findings — analyse de code » de
>   `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-bilan-apres-20261108.md`.
>
> Synthèse de la campagne : `Docs/audits/api-mail-loadtest-ab-bilan-lot-20261108.md`.

## Ce qui est établi

| Forme `pg_stat_statements` (tir court 1400 → 1996, IA simulée, `5b4e394f`) | Appels | Temps SQL | Pages lues | Lu sur disque |
|---|---|---|---|---|
| FND-007 `9a63b74fac8c0708f158bb2588df9b57` : `MailMedicalDocuments` entier, `WHERE MailId = $1` | 168 211 | 151,5 s (14,7 % du SQL du tir) | 22,7 Go | 3,2 Go (**52,4 %** des lectures disque du tir) |
| FND-009 `4b9380ddd1837d2bc365a5afbc833f85` : `MailContents` entier, `WHERE MailId = $1` | 168 039 | 38,5 s | 10,7 Go | 0,1 Go |

- **Site** : `MailRepository.PopulateMailContentAsync`
  (`src/Infrastructure/Repositories/MailDb/MailRepository.cs:1253`), au commit `5b4e394f`. En mode
  `MailBuildType.WithContent`, les deux lectures matérialisent l'entité entière :
  - `documentsOfMail`, ligne 1260 ;
  - `contentsOfMail`, ligne 1323.
- **Cause** : les deux entités sont matérialisées avec `Embedding` (pgvector, 6 148 octets par ligne au banc).
  `MailMedicalDocument` porte aussi `MetadataJson`. Ni `BuildMedicalDocumentDto` (ligne 1355) ni le `MailContentDto`
  (ligne 1337) n'en recopient rien : ces colonnes sont lues, détoastées, transférées, puis jetées.
- **Les projections existent déjà**, pour le mode en-tête :
  - `MedicalDocumentHeaderProjection` (ligne 1759) ;
  - `ContentHeaderProjection` (ligne 1795).

  Le chemin groupé (`GetMailsByUidsAsync`) projette déjà sans `Embedding` ni `MetadataJson` depuis task-322 (ligne
  1928). Il ne reste que le **message seul en `WithContent`**.
- **Poids des colonnes**, mesuré sur la plus grosse base du banc :
  - plans : `Docs/audits/findings/plans/20261108-bilan-apres/FND-007-colonnes.txt`, `FND-009-colonnes.txt` ;
  - `MailMedicalDocuments`, octets par ligne : `Body` 2 482, `HtmlBody` 37 860, `Embedding` 6 148, `MetadataJson`
    vide au banc ;
  - `MailContents`, octets par ligne : `Body` 2 842, `Embedding` 6 148.
- **Gain borné**, à mesurer par A/B :
  - FND-007 : `Embedding` pèse 13 % des octets de la forme. Au plus ≈ 13 % de 151,5 s, et ≈ 0,4 Go de lectures
    disque ;
  - FND-009 : `Embedding` pèse 68 % des octets de la forme. Au plus ≈ 68 % de 38,5 s ;
  - total : **au plus ≈ 46 s sur 1 031 s de SQL du tir (≈ 4,5 %)** ;
  - `HtmlBody` (37 860 octets) est affiché par la vue du message : il reste, et FND-007 restera le premier lecteur de
    disque. Ce n'est pas un échec de la task.
- **Routes et appelants concernés** (tous passent par `GetMailAsync(…, WithContent)`) :
  - `GET /api/v1/Mail/folders/{folderName}/emails/content/{emailId}` : l'ouverture d'un message, étape « ouvrir un
    message enrichi (servi base) » du parcours ;
  - l'enrichissement (`ImapService.cs:3438`), qui relit le message existant ;
  - le hors-ligne (`OfflineMailDataProvider.cs:125`).

  Aucun ne lit le vecteur dans le DTO rendu.
- **Récidive, troisième de la classe** `colonne-volumineuse` :
  - task-322 / task-323 (page d'en-têtes) ;
  - task-429 (dossier patient, FND-003) ;
  - FND-007 / FND-009.

  La consigne `groupby-final-materialise-l-entite` existe dans `conventions/csharp.md`. Sa garde
  (`AttachmentBytesReadEndToEndTests`) ne couvre que `MailAttachments."Content"`. La garde « aucune route de lecture
  ne sélectionne `Embedding` » a été nommée le 2026-11-07, puis le 2026-11-08, et n'a pas été posée (règle d'or,
  point 3 : la lecture est à corriger, pas seulement la ligne).

## Objective

Ouvrir un message ne lit plus en base les colonnes que la vue n'affiche pas. Le document médical et le contenu sont
projetés sans `Embedding` ni `MetadataJson`. Seuls les chemins qui servent le vecteur le lisent : la recherche
sémantique et l'écriture de l'embedding.

Règles :
- **Projeter en `WithContent` aussi** : la lecture des documents et celle du contenu, dans
  `PopulateMailContentAsync`, sélectionnent les colonnes dont le DTO a besoin, et seulement celles-là.
  - Pour le document, ce sont les colonnes de l'en-tête, plus `Body` et `HtmlBody`.
  - Pour le contenu, ce sont `Body`, `BodyHtml`, `ContentType` et `Summary`.
  - Le motif est celui des projections d'en-tête existantes, étendues ou dérivées sans recopie.
- **Réponse strictement identique** : chaque champ du message rendu garde la même valeur qu'aujourd'hui, dans le même
  ordre : documents, corps, résumé, biologie, synthèse, pièces jointes des documents, doublons, acquittements. Aucun
  contrat ne change.
- **Le vecteur en base est intact** : ouvrir un message ne l'efface ni ne le recalcule. Les écritures
  `UpdateMailContentEmbeddingAsync` et `UpdateMedicalDocumentEmbeddingAsync` sont inchangées.
- **Garde contre la récidive, sur toute la classe** : un test d'intégration parcourt les routes de lecture du parcours
  médecin. Il échoue si l'une d'elles sélectionne une colonne volumineuse qu'elle ne sert pas :
  - `MailAttachments."Content"` : garde existante, reprise ;
  - `MailMedicalDocuments."Embedding"`, `MailMedicalDocuments."MetadataJson"`, `MailContents."Embedding"` : nouveau.

  Exemptions explicites, chacune vérifiée par la garde comme lisant bien sa colonne :
  - le téléchargement d'une pièce jointe pour `Content` ;
  - la recherche sémantique pour `Embedding`.

  Une colonne volumineuse ajoutée plus tard doit pouvoir y entrer en une ligne.
- **Règle 14 inchangée** : même base de la boîte, même verdict de l'opérateur, même trace d'ouverture imputée à la
  personne réelle. Aucune donnée ne change de place.

### Hors périmètre

- `HtmlBody` du document, affiché : il reste lu.
- FND-010 (recherche vectorielle exacte) et FND-014 (`LIKE '%…%'` sur `References`) : ils attendent un tir sur des
  boîtes 10 fois plus grosses.
- Le stockage du vecteur (table à part, table splitting EF) : à rouvrir seulement si la garde ne suffit pas.
- Le second site non résolu de la forme FND-007 (`bus:AddNewMail`, `site=?`) : il passe par le même
  `GetMailAsync(…, WithContent)` et profite du correctif. Résoudre son étiquette `site=` est hors de cette task.
- Aucun client, aucun contrat, aucune migration de schéma.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Test d'intégration de bout en bout (règle 1b), `GET /api/v1/Mail/folders/{folderName}/emails/content/{emailId}`**,
      sur la vraie pile avec la vraie base du fixture. Le message est porteur d'un document CDA enrichi, et son
      contenu et son document ont un `Embedding` non nul en base. Le test vérifie que :
      - le SQL émis, relevé par `Harness/NpgsqlQueryCapture.cs` (task-429), ne sélectionne ni
        `MailMedicalDocuments."Embedding"`, ni `MailMedicalDocuments."MetadataJson"`, ni `MailContents."Embedding"` ;
      - la réponse réelle porte le document avec `body` et `htmlBody`, et le contenu avec `body`, `bodyHtml` et
        `summary`, égaux aux valeurs en base ;
      - la biologie, la synthèse et les pièces jointes du document sont présentes comme avant ;
      - **vu rouge** par mutation : la matérialisation de l'entité entière est réinjectée, puis restaurée et
        recompilée (mémoire « mutation restaurée »). La preuve est consignée dans le `## Develop log`.
- [ ] **Vecteur intact** : dans le même test, après l'ouverture, `Embedding` du contenu et du document est inchangé en
      base
- [ ] **Cas d'échec inchangé** : un `emailId` inconnu rend la même réponse d'échec qu'aujourd'hui, en
      `application/problem+json`
- [ ] **Garde contre la récidive** : test d'intégration qui parcourt les routes de lecture du parcours médecin. Il
      échoue si l'une d'elles sélectionne une colonne de la liste. Les routes : dossiers, page d'en-têtes, contenu
      du message, vues du jour, étiquettes, recherche, fiche patient, dossier patient, documents, opposition,
      patients du jour.
      - Liste des colonnes : `MailAttachments."Content"`, `MailMedicalDocuments."Embedding"`,
        `MailMedicalDocuments."MetadataJson"`, `MailContents."Embedding"`.
      - Exemptions : le téléchargement d'une pièce jointe (`Content`) et la recherche sémantique (`Embedding`). Le
        test vérifie que chacune lit bien sa colonne.
      - Vue rouge sur le code d'avant : elle désigne la route du contenu du message.
      - La garde de task-429 (`NoReadRouteOfTheJourney_ReadsAttachmentContent_OnlyTheDownloadDoes`) est étendue ou
        remplacée, jamais dupliquée.
- [ ] Tests existants du message, de l'enrichissement, du hors-ligne et de la recherche sémantique verts sans
      modification de leurs assertions
- [ ] **Prévention (règle d'or)** : l'entrée `groupby-final-materialise-l-entite` de `conventions/csharp.md` est
      généralisée, ou une entrée sœur est créée. Elle dit : ne jamais matérialiser une entité qui porte une colonne
      volumineuse (binaire, vecteur, JSON) hors du chemin qui la sert, et toute colonne volumineuse nouvelle entre
      dans la liste de la garde. Elle cite les occurrences task-322, task-429 et task-434.
- [ ] **Registre** : FND-007 et FND-009 passent en `corrigé et mesuré` dans `Docs/audits/findings-registry.md`, avec
      la mesure du banc
- [ ] **Mesure au banc**, tir court 1400 → 1996, IA simulée, pool 1, tireur k6bench, banc cluster, `LATENCY_MS=96`.
      Elle est jouée contre un contrôle `develop` dans la même session (A/B, puis A/B/A si un écart de plus de 20 %
      apparaît), sur les bases hydratées du 2026-11-08 sans `reset-state`. Le compte rendu doit montrer que :
      - les formes `9a63b74fac8c0708f158bb2588df9b57` et `4b9380ddd1837d2bc365a5afbc833f85` ont **0 appel**, et les
        formes qui les remplacent sont relevées (appels, temps, pages) ;
      - les lectures disque, le temps SQL du tir et le coût SQL par requête HTTP sont relevés avant et après ;
      - les p50 et p95 de l'étape « ouvrir un message enrichi (servi base) » sont relevés avant et après ;
      - aucune étape n'est ralentie par le code ;
      - la section « Findings — analyse de code » du tir B est produite par `/loadtest-findings` ;
      - les rapports sont copiés dans `Docs/audits/`.
- [ ] Aucune donnée de santé en clair dans les logs, ni dans les rapports de banc
- [ ] Parcours e2e verts (`/e2e`) : aucun parcours n'est modifié, aucun scénario n'est ajouté

## Manual Test Plan

- [ ] Lancer `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut. Il faut une boîte rattachée qui
      contient un message porteur d'un compte rendu CDA déjà enrichi (biologie et synthèse).
- [ ] Ouvrir ce message (`client-blazor` ou `client-mobile`). Vérifier que :
      - le corps du message s'affiche comme avant ;
      - le résumé s'affiche comme avant ;
      - le document s'affiche comme avant (vue HTML), avec ses résultats de biologie, sa synthèse et ses pièces
        jointes.
- [ ] Ouvrir un message sans document : le corps s'affiche, aucune erreur.
- [ ] Lancer une recherche sémantique qui retrouve ce message : il apparaît dans les résultats (le vecteur est
      toujours là).
- [ ] Au banc (facultatif) : rejouer le tir court et vérifier dans la section « Findings » du rapport que FND-007 et
      FND-009 ont disparu.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — correctif de performance interne, aucun échange ni fonctionnalité nouvelle
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable — l'identité du patient n'est ni lue ni écrite autrement
- **Authentification PS** : inchangée — PSC/e-CPS, verdict de l'opérateur MSSanté (règle 14)
- **Habilitations** : inchangées — accès à la base de la boîte par le verdict de l'opérateur, aucune route nouvelle
- **Interop CI-SIS** : non applicable — le document CDA est servi tel qu'il est stocké aujourd'hui, aucun document
  n'est produit ni consommé autrement
- **Tracé PGSSI-S** : inchangé — l'ouverture d'un message reste tracée au nom de la personne réelle (RPPS, nom PSC,
  rôle), conservation 3 653 jours (famille `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — données inchangées, dans la base de la boîte, sur l'environnement HDS de la plateforme
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau. Moins de données dérivées de données de santé (les
  vecteurs) transitent vers l'API.

## Branches

- `api-mail` (pushed) : fix/task-434-ouvrir-un-message-sans-charger-les — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-434-ouvrir-un-message-sans-charger-les

> Pré-flight du /start (2026-11-08) : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` sur `develop`.
> `host` (`Host/Modules`) et `interop` ne sont pas des racines de dépôt (`--show-prefix` non vide) : connu, non
> bloquant pour cette task. Les index du banc (`tests/loadtest-k6/reports/INDEX.md`, `POSTGRES-INDEX.md`), modifiés
> par la campagne du 2026-11-08, suivent la branche et partiront avec la PR.

## Timings

*(généré par `tools/timing/report.sh --task task-434 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 2 h 45 min | 14 (1 min 33 s) | 15 (24 min 43 s) | — | api-mail 14B/15T |
| /loadtest-findings | ok | 4 min 05 s | — | — | — | — |
| **Total cycle** | | **2 h 50 min** | **14 (1 min 33 s)** | **15 (24 min 43 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : capture ×2 (1 h 41 min)

## Develop log

- **Repos touchés** : `api-mail` seul. Aucun DTO, aucun interop, aucune migration.
- **Commits** (`fix/task-434-ouvrir-un-message-sans-charger-les`, poussés) :
  - `a33f14b0` chore(loadtest) : index des tirs du bilan du lot du 2026-11-08 (portés par la PR, comme annoncé au /start) ;
  - `36f7c703` fix(mail) : ouvrir un message ne lit plus les vecteurs du document et du contenu ;
  - `dfda613b` refactor(mail) : passe qualité (/simplify).

### Correctif (`src/Infrastructure/Repositories/MailDb/MailRepository.cs`)

- **Deux projections « contenu »**, dérivées des projections d'en-tête par `WithColumns`, sans recopie de la liste des
  champs :
  - `MedicalDocumentContentProjection` = `MedicalDocumentHeaderProjection` + `Body` + `HtmlBody` ;
  - `ContentProjection` = `ContentHeaderProjection` avec `Body`, `BodyHtml`, `Summary` lus.
  - Ni `Embedding` ni `MetadataJson`, qu'aucun DTO ne recopie.
- **Quatre sites corrigés** :

| Site | Route / appelant | Trouvé par |
|---|---|---|
| `PopulateMailContentAsync`, `WithContent` (FND-007 + FND-009) | `GET …/emails/content/{emailId}`, enrichissement, hors-ligne | le task file |
| `GetMedicalDocumentsAsync`, `withBodies` | `GET /patients/{id}/folder?withBodies=true` | la garde élargie |
| `GetMailsByTagAsync`, `Include(m => m.MailContents)` | `GET /mail/tags/{code}/emails/{uids}` | la garde élargie |
| `LoadBulkContentLookupsAsync`, `WithContent` | `GetMailsByUidsAsync(…, WithContent)` : l'assistant IA | la passe qualité (axe altitude) |

- **Vue d'étiquette** : le contenu n'est plus raccroché à l'entité. `MailContents.Add` y était lu comme une écriture
  par le scan d'architecture de task-227 ; le contenu est désormais passé au DTO (`BuildTagMailDto`,
  `BuildMailContentDto`).

### Tests (règle 1b) — `tests/mss.mail.integration.tests/UseCases/AttachmentBytesReadEndToEndTests.cs`

- **Vraie pile** : hôte HTTP, contrôleurs `Mail` et `Patients`, vrais services et dépôts, Dovecot, base PostgreSQL du
  praticien. SQL relevé par `NpgsqlQueryCapture` (task-429).
- **Scène** : compte rendu de microbiologie du kit ANS enrichi par la vraie route, pièce jointe en base, étiquette
  `SUIVI`, et un vecteur écrit sur le contenu et le document **par les écrivains du dépôt**
  (`UpdateMailContentEmbeddingAsync`, `UpdateMedicalDocumentEmbeddingAsync`), au modèle et à la dimension actifs.
  `MetadataJson` est posé à part, faute d'écrivain dédié.

| Comportement | Test | Preuve rouge |
|---|---|---|
| `GET …/emails/content/{id}` rend corps, HTML, résumé et document (texte, HTML, biologie, synthèse, patient) égaux à la base, sans lire `Embedding` ni `MetadataJson` ; le vecteur reste intact en base | `OpeningAMessage_ServesItsDocumentAndBody_WithoutReadingTheirVectors` | rouge sur le code d'avant ; M1, M2, M5, M6 |
| `GET /mail/tags/{code}/emails/{uid}` rend corps, HTML et résumé, sans lire le vecteur | `TheTagView_ServesTheBody_WithoutReadingItsVector` | M4, M5 |
| `GET /patients/{id}/folder?withBodies=true` rend texte et HTML du document, sans vecteur ni `MetadataJson` | `ThePatientFolderWithBodies_ServesTheDocumentHtml_WithoutReadingItsVector` | M3, M6 |
| Cas d'échec : `emailId` inconnu, 404 `application/problem+json` | `OpeningAnUnknownMessage_Is404ProblemJson` | inchangé, vert |
| **Garde** : 15 routes de lecture du parcours ne lisent ni `MailAttachments."Content"`, ni `MailMedicalDocuments."Embedding"` / `"MetadataJson"`, ni `MailContents."Embedding"`. Exemptions vérifiées : le téléchargement lit `Content` ; la recherche sémantique (dépôt) lit les deux vecteurs et retrouve le message | `NoReadRouteOfTheJourney_ReadsAVoluminousColumn_OnlyThePathsThatServeIt` | rouge sur le code d'avant (contenu, étiquette, dossier) ; M1 à M4 |
| Chemin groupé `WithContent` : corps lus, ni vecteur ni `MetadataJson` | `HeaderListingProjectionTests.WithContentReadsDocumentBodiesButNeverEmbeddingsNorAttachmentBytes` | M7, M8 |

- **Mutations** :
  - M1 document entier, M2 contenu entier, M3 dossier `withBodies` entier, M4 étiquette sans projection ;
  - M5 contenu sans corps, M6 document sans HTML ;
  - M7 chemin groupé, document entier ; M8 chemin groupé, contenu entier.

  Chacune est rouge sur le test visé. Restauration depuis une copie, avec la date du jour, puis recompilation. Code
  restauré : 14/14 verts sur les deux classes.
- **⚠️ Exception à « tests existants verts sans modification de leurs assertions »** :
  - `HeaderListingProjectionTests.WithContentStillReadsDocumentEmbeddingsButNeverAttachmentBytes` affirmait que le
    chemin groupé en `WithContent` lit `Embedding`. C'est le défaut lui-même, épinglé ;
  - l'assertion est retournée (ni vecteur ni `MetadataJson`, et les corps toujours lus), et le test est renommé
    `WithContentReadsDocumentBodiesButNeverEmbeddingsNorAttachmentBytes` ;
  - les tests du message, de l'enrichissement, du hors-ligne et de la recherche sémantique sont inchangés et verts.
- **Défaut de la garde de task-429, corrigé** :
  - elle semait le message **avant** tout listage des dossiers, donc en génération 0 ;
  - dès que la garde listait les dossiers, le message devenait invisible à la base, et les routes de message étaient
    servies par IMAP : la garde ne les éprouvait pas ;
  - la scène liste désormais les dossiers d'abord (`ArchiveMailboxServer.ListFoldersAsync`, partagé).

### Validation

- Build `HealthPlatform.Api.Mail.sln` : 0 erreur, 0 avertissement.
- Tests, après la passe qualité :
  - domaine 210/210, infrastructure 728/728, api 1 370/1 370, application 4 031/4 031 ;
  - intégration 1 142/1 158, 16 ignorés comme avant, 0 échec, +2 tests par rapport au passage précédent.
- Un rouge rencontré en cours de route, corrigé : `MailContentWriterScanTests` (task-227) lisait le raccrochage du
  contenu à l'entité de la vue d'étiquette comme une écriture. Le contenu est désormais passé au DTO.

### Passe qualité (§Q, /simplify, 4 axes)

- **Appliqué** :
  - chemin groupé `WithContent` projeté (altitude, relevé par deux axes) ;
  - variables intermédiaires héritées de l'ancien ternaire retirées, commentaires remis d'aplomb ;
  - éviction Redis retirée de la scène : sans effet, le cache de la fixture est un substitut ;
  - vecteurs écrits par les écrivains du dépôt, à la dimension du modèle actif ;
  - prémisses posées une fois au semis, `ObserveWithoutVoluminousReadsAsync` partagé, `Reads` unique ;
  - `ArchiveMailboxServer.ListFoldersAsync` partagé.
- **Écarté, noté** :
  - remplacer `WithColumns` par une projection littérale pour `ContentProjection` : `WithColumns` garde les deux
    projections alignées quand l'en-tête gagne un champ ;
  - le table splitting EF (vecteur dans une entité dépendante) traiterait la cause de fond. Mais c'est un changement
    de modèle qui touche la recherche sémantique et les écrivains : à proposer en task si la classe récidive encore.
- **Suggestions de suite, hors périmètre, pour l'humain** :
  - `PatientRepository.GetDuplicateClusterAsync` et le pivot de chaîne de versions lisent un document entier pour un
    ou deux champs (`DuplicateOfId`, `SupersededByDocumentId`). Leurs routes, `…/duplicate-cluster` et
    `…/version-chain`, sont hors de la garde et peu fréquentes ;
  - `GetMailMedicalDocumentsAsync` (indexation, `AddNewMailConsumer`) et `EnrichDraftMailAsync` chargent l'entité
    entière. Ce sont des chemins de fond ;
  - une garde **statique**, qui refuserait toute lecture `db.MailMedicalDocuments` / `db.MailContents` sans `Select`
    hors des écrivains déclarés, aurait attrapé les quatre sites d'un coup, qu'ils aient une route ou non.

### Prévention (règle d'or)

- `conventions/csharp.md`, entrée `groupby-final-materialise-l-entite`, passée à 3 occurrences (task-322, task-429,
  task-434) :
  - la consigne s'étend à toute lecture d'entité à colonne volumineuse : projection, même pour servir le contenu, et
    un `Include` vaut entité entière ;
  - la garde est renommée et étendue ;
  - le piège de la génération 0 dans les scènes de test y est noté.
- La lecture a échoué deux fois : la prévention nommée par `/loadtest-findings` le 2026-11-07, puis le 2026-11-08,
  n'avait pas été posée. La garde couvre désormais toute la classe, et une colonne volumineuse nouvelle y entre en une
  ligne.

## Mesure au banc

**Tir court 1400 → 1996.**
- Conditions : IA simulée, pool 1, tireur k6bench (lien 76 Mo/s), banc mail cluster, `LATENCY_MS=96`.
- Bases hydratées du 2026-11-08, sans `reset-state`.
- Harnais de la branche pour les deux tirs.

**Ordre** : task-434 (`dfda613b`, 12:44-13:35) **puis** contrôle `develop` (`5b4e394f`, 13:35-14:25), dans la même
session. Le tir de la task, passé en premier, est **défavorisé** : il a joué sur le cache le plus froid.
- Attente de lecture disque : 124,6 s contre 44,3 s.
- Fautes majeures du cgroup Postgres : max 23/s contre 1/s.

Les deux tirs sont valides : SMTP sain (obtention de session 220 ms dans les deux), 0,008 % et 0,013 % d'erreurs. Aucun
écart d'étape n'atteint 20 % : l'A/B suffit, sans A/B/A.

| Mesure | Contrôle `develop` | **task-434** |
|---|---|---|
| Forme FND-007 d'avant (`9a63b74f…`, document entier) | 168 539 appels, 140,7 s, 24,4 Go de pages, 3,48 Go sur disque | **20 appels** (voie du bus `bus:AddNewMail`, hors périmètre) |
| Forme du document à l'ouverture (`bc5acb2c…`, projetée) | — | 166 290 appels, 161,7 s, **19,3 Go** de pages (−21 %), 3,53 Go sur disque |
| Forme FND-009 d'avant (`4b9380dd…`, contenu entier) | 168 372 appels, 37,6 s, 11,5 Go de pages | **0 appel** |
| Forme du contenu à l'ouverture (`2a6ce021…`, projetée) | — | 166 260 appels, **23,4 s**, **6,3 Go** de pages (−45 %), 0,07 Go sur disque |
| Pages lues du tir (cache + disque) | 546,1 Go | 535,8 Go (−1,9 %) |
| Lectures disque du tir | 6,47 Go | 7,73 Go (cache plus froid) |
| Temps SQL du tir | 1 020,7 s | 1 110,1 s |
| Coût SQL par requête HTTP | 3,6 ms | 3,9 ms |

**Lecture.**
- Les octets lus par les deux formes baissent comme prévu : −21 % pour le document, −45 % pour le contenu. C'est la
  part du vecteur, mesurée au poids des colonnes.
- Les lectures disque du document ne baissent pas. Elles viennent de `HtmlBody` (37 860 octets par ligne, contre
  6 148 pour le vecteur), que la vue affiche : c'était annoncé par la borne du task file.
- Le temps SQL du tir ne départage pas les deux codes. Les 90 s d'écart viennent de l'attente de lecture disque du tir
  passé en premier, sur un cache plus froid : 80 s de plus. Un effet sur le temps de réponse n'est pas démontré, ni
  dans un sens, ni dans l'autre.

**Étapes du parcours, p50 / p95 (ms) à 1996 médecins** — contrôle → task :

| Étape | Contrôle `develop` | **task-434** |
|---|---|---|
| 1 Arrivée dashboard | 65 / 639 | 63 / 551 |
| 2 Inbox | 52 / 136 | 50 / 134 |
| 3 **Message enrichi (servi base)** | 48 / 106 | **45 / 104** |
| 4 Message froid (IMAP) | 452 / 519 | 451 / 516 |
| 5 Recherche | 349 / 616 | 348 / 664 |
| 6 Envoi | 485 / 948 | 485 / 946 |
| 7 Pièce jointe | 54 / 124 | 51 / 123 |
| 8 Marquer lu | 54 / 107 | 51 / 105 |
| 9 Rechercher un patient | 56 / 76 | 56 / 76 |
| 10 Page d'un dossier patient | 59 / 77 | 59 / 77 |
| 11 Fiche patient complète | 348 / 681 | 331 / 685 |

- **Aucune étape n'est ralentie par le code.** Le seul écart supérieur à 5 % est le p95 de la recherche à 1996
  (+8 %), dans le bruit du tir : la même étape est à −24 % au palier 1400 (742 → 563).
- L'étape visée, « ouvrir un message enrichi », passe de 48 / 106 à 45 / 104 ms.

**Rapports** :
- `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-t434-task-20261108.md`, qui porte la section « Findings —
  analyse de code » : 8 candidats, contrôle 79 éléments, 0 écart ;
- `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-t434-controle-20261108.md`.

**Registre** : FND-007 et FND-009 portent leur forme d'après correctif et la mesure de cet A/B. Ils restent en `task`,
et passent en `corrigé et mesuré` au `/merge` (règle du registre, `agents/loadtest-findings.md` § 7). FND-008 est
écarté ; FND-016, FND-017 et FND-018, nouveaux, sont écartés.
