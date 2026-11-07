# todo-task-429.md — Le dossier patient ne lit plus le contenu des pièces jointes qu'il n'affiche pas

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1**. Ce défaut fait près d'un tiers des lectures disque de Postgres sur un tir court. Il charge 13,7 Go de
contenus binaires dans l'API pour n'afficher que des noms et des tailles. Le correctif est petit, et ne change aucun
comportement visible.

> **Origine.** Évaluation « sortir les pièces jointes de Postgres (SeaweedFS) » du 2026-11-06, faite sur le tir
> « après » de l'A/B/A du même jour (`Api/Mail/tests/loadtest-k6/reports/2026-11-06/pgstats-journey-193047.tsv`,
> synthèse `Docs/audits/api-mail-loadtest-ab-findings-task422-20261106.md`). Conclusion de l'évaluation : corriger ce
> défaut d'abord, remesurer, et différer SeaweedFS.

## Ce qui est établi

| Forme `pg_stat_statements` (tir court 1400 → 1996, code `develop` `f50f2ae5`) | Appels | Lignes | Lus en cache | Lus sur disque | Temps SQL |
|---|---|---|---|---|---|
| `SELECT m."MailId", m."Id", m."Content", m."ContentType", … FROM "MailAttachments" AS m WHERE m."MailId" = ANY ($1) ORDER BY m."MailId"` | 3 862 | 117 891 | 8,7 Go | **5,1 Go** | **67,6 s** |
| Pour comparaison, le téléchargement d'une pièce jointe (seule lecture légitime de `Content`) | 15 798 | 15 798 | 1,3 Go | 1,5 Go | 22,9 s |

- Ces 5,1 Go représentent **31 % des lectures disque du tir** (16,4 Go au total), et 18,6 s des 104 s d'attente de
  lecture disque.
- **Cause, établie dans le code** : `PatientRepository.LoadMailsWithAttachmentsAsync` regroupe les pièces jointes par
  message avec `GroupBy(a => a.MailId).ToDictionaryAsync(g => g.Key, g => g.Select(a => new AttachmentDto { … }))`.
  - EF Core ne traduit pas la projection faite dans le groupe. Il matérialise donc l'entité `MailAttachment` entière,
    **avec `Content`**, puis projette en mémoire.
  - Le DTO rendu ne porte que `Guid`, `FileName`, `ContentType` et `Size` : le contenu est lu, transféré, puis jeté.
- **Routes concernées** (toutes passent par `GetMailsByPatientIdAsync`) :
  - `GET /api/v1/Patients/{patientId}/medical-documents`, avec ou sans `page`/`pageSize` : c'est l'étape « page d'un
    dossier patient » du parcours, et la rafale de la « fiche patient complète » ;
  - `POST /api/v1/Patients/mails`.
- **Même famille que task-322** (la page d'en-têtes chargeait les contenus) : c'est une **récidive**, au sens de la
  règle d'or. La prévention doit porter sur la lecture, pas seulement sur cette ligne.
- **Contexte** : les pièces jointes pèsent 51 % du disque des bases du banc (20 bases tirées au hasard). Postgres
  range ces contenus à part (TOAST), et une requête qui ne les sélectionne pas ne lit pas leurs pages. C'est pourquoi
  corriger les requêtes suffit, sans déplacer le stockage.

## Objective

Le dossier patient ne lit en base que les métadonnées des pièces jointes qu'il affiche. Seul le téléchargement d'une
pièce jointe lit son contenu.

Règles :
- **Projeter avant de regrouper** : la requête des pièces jointes du dossier ne sélectionne que `MailId`, `Guid`,
  `FileName`, `ContentType` et `Size`. Le regroupement par message se fait sur ces seules colonnes. La forme existante
  `AttachmentMetadataProjection` de `MailRepository` montre le motif.
- **Réponse strictement identique** : chaque message du dossier porte les mêmes pièces jointes, avec les mêmes nom,
  type, taille et identifiant, dans le même ordre qu'aujourd'hui. Aucun contrat ne change.
- **Garde contre la récidive** : un test d'intégration parcourt les routes de lecture du parcours médecin et échoue
  si l'une d'elles sélectionne `MailAttachments."Content"`. La route de téléchargement d'une pièce jointe est la seule
  exemptée. Ce test échoue aujourd'hui sur les routes du dossier patient.
- **Règle 14 inchangée** : même base de la boîte, même verdict de l'opérateur, même trace `PatientRecordViewed`
  imputée à la personne réelle. Aucune donnée ne change de place.

### Hors périmètre

- Sortir les pièces jointes de Postgres (SeaweedFS ou autre stockage objet) : décision différée par l'évaluation du
  2026-11-06, à rouvrir sur la mesure qui suit ce correctif.
- Les autres colonnes volumineuses (`MailMedicalDocuments.Body`/`HtmlBody`, `MailContents.Body`/`BodyHtml`) : la
  garde contre la récidive peut les couvrir si c'est sans effort. Sinon, une task distincte, sur mesure.
- Le téléchargement lui-même (lecture complète en mémoire, réponse 500 sur annulation du client) : hors de cette task.
- Aucun client, aucun contrat, aucune migration de schéma.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Test d'intégration de bout en bout (règle 1b), `GET /api/v1/Patients/{patientId}/medical-documents?page=&pageSize=`**
      sur la vraie pile, avec la vraie base du fixture, un patient et au moins deux messages porteurs de pièces jointes
      au contenu non vide :
      - le SQL émis, relevé par intercepteur EF, ne sélectionne pas `MailAttachments."Content"` ;
      - la réponse réelle porte, pour chaque message, ses pièces jointes avec `fileName`, `contentType` et `size`
        attendus ;
      - **vu rouge** sur le code d'avant (`Content` sélectionné), ou par mutation (le `GroupBy` d'origine réinjecté).
- [ ] **Même test sans pagination** (`GET …/medical-documents` sans `page`), et pour **`POST /api/v1/Patients/mails`** :
      aucune sélection de `Content`, pièces jointes présentes dans la réponse
- [ ] **Cas d'échec inchangé** : un patient inconnu rend toujours 404 en `application/problem+json`
- [ ] **Garde contre la récidive** : test d'intégration qui parcourt les routes de lecture du parcours médecin
      (inbox, message servi par la base, étiquettes, recherche, dossier patient, fiche patient) et échoue si l'une
      d'elles sélectionne `MailAttachments."Content"`. Le téléchargement d'une pièce jointe est la seule exemption, et le
      test vérifie que lui lit bien `Content`. Vu rouge sur le code d'avant
- [ ] Tests existants du dossier patient et des pièces jointes verts sans modification de leurs assertions
- [ ] **Prévention (règle d'or)** : entrée dans `conventions/csharp.md`. Le `GroupBy` en opérateur final matérialise
      l'entité entière : toujours projeter avant de regrouper, et ne jamais matérialiser une entité qui porte une colonne
      binaire ou volumineuse hors du chemin qui la sert. Récidive de task-322, citée
- [ ] **Mesure au banc**, tir court 1400 → 1996, IA simulée, pool 1, contre un contrôle `develop` joué dans la même
      session (A/B, puis A/B/A si un écart de plus de 20 % apparaît, voir task-426) :
      - la forme `SELECT … m."Content" … WHERE m."MailId" = ANY ($1) ORDER BY m."MailId"` a **0 appel** ;
      - lectures disque et temps SQL du tir relevés avant/après ;
      - p50/p95 des étapes « page d'un dossier patient » et « fiche patient complète » relevés avant/après ;
      - aucune étape ralentie par le code ;
      - rapports copiés dans `Docs/audits/`.
- [ ] Aucune donnée de santé en clair dans les logs, ni dans les rapports de banc
- [ ] Parcours e2e verts (`/e2e`) : aucun parcours n'est modifié, aucun scénario n'est ajouté

## Manual Test Plan

- [ ] `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, une boîte rattachée qui contient des
      messages porteurs de pièces jointes rattachés à un patient.
- [ ] Ouvrir le dossier de ce patient (`client-blazor` ou `client-mobile`) : chaque message affiche ses pièces jointes,
      avec les mêmes noms et tailles qu'avant.
- [ ] Faire défiler le dossier (« charger plus ») : les pages suivantes s'affichent normalement.
- [ ] Télécharger une pièce jointe depuis le dossier : le fichier s'ouvre, contenu intact.
- [ ] Ouvrir le dossier d'un patient sans message : liste vide, aucune erreur.
- [ ] Au banc (facultatif) : rejouer le tir court et vérifier dans le rapport que la forme SQL des pièces jointes du
      dossier ne lit plus `Content`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — correctif de performance interne, aucun échange ni fonctionnalité nouvelle
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable — le dossier patient est lu comme aujourd'hui, l'identité n'est ni lue ni écrite autrement
- **Authentification PS** : inchangée — PSC/e-CPS, verdict de l'opérateur MSSanté (règle 14)
- **Habilitations** : inchangées — accès à la base de la boîte par le verdict de l'opérateur, aucune route nouvelle
- **Interop CI-SIS** : non applicable — aucun document CDA n'est produit ni consommé autrement
- **Tracé PGSSI-S** : inchangé — `PatientRecordViewed` reste imputé à la personne réelle (RPPS, nom PSC, rôle) sur les
  deux routes, conservation 3 653 jours (famille `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — données inchangées, dans la base de la boîte, sur l'environnement HDS de la plateforme
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau. Moins de données de santé transitent vers l'API.

## Branches

- `api-mail` (pushed) : fix/task-429-fiche-patient-ne-plus-lire-le-contenu — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-429-fiche-patient-ne-plus-lire-le-contenu

> Pré-flight du /start (2026-11-06) : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` sur `develop`. `host` (`Host/Modules`) n'est pas un dépôt (connu). `interop` n'est plus la racine d'un dépôt (`--show-prefix` = `interop/`) : non bloquant pour cette task, à signaler à l'humain.

## Timings

*(généré par `tools/timing/report.sh --task task-429 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| **Total cycle** | | **20 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

## Develop log

**Correctif** (`api-mail`, `src/Infrastructure/Repositories/MailDb/PatientRepository.cs`) :
- `LoadMailsWithAttachmentsAsync` : la requête des pièces jointes projette `MailId`, `Guid`, `FileName`, `ContentType`,
  `Size`, et est lue en flux (`AsAsyncEnumerable`) directement dans la liste de chaque message. Plus de `GroupBy` final,
  plus de liste intermédiaire ni de second dictionnaire. SQL émis : `SELECT m."MailId", m."Guid", m."FileName",
  m."ContentType", m."Size" FROM "MailAttachments" AS m WHERE m."MailId" = ANY ($1)`.
- `EnrichBiologyAndAttachmentsAsync` (même fichier, relevé par la passe qualité, axe « altitude ») : le regroupement des
  résultats de biologie avait la même forme de `GroupBy` final. Aucune colonne volumineuse n'y est lue, mais la forme
  contredit la consigne. Elle est remise en « projection, puis regroupement en mémoire ». Le comportement est inchangé,
  et les tests de biologie et du dossier patient restent verts.

**Tests (règle 1b)** — `tests/mss.mail.integration.tests/UseCases/AttachmentBytesReadEndToEndTests.cs` (collection
`UseCases`, boîte n° 22) :
- **Vraie pile** : hôte HTTP, contrôleurs `Mail` et `Patients`, vrais services et dépôts, Dovecot, base PostgreSQL du
  praticien.
- **Scène semée une fois pour la classe** :
  - compte rendu de microbiologie du kit ANS déposé dans Dovecot, enrichi par `POST …/emails/enrich/sync` ;
  - fiche patient créée par l'ingestion ;
  - contenu de `IHE_XDM.ZIP` mis en base par un premier téléchargement, comme au banc ;
  - étiquette `SUIVI` posée par la vraie route.
- **SQL relevé par `Harness/NpgsqlQueryCapture.cs`** (nouveau) : écouteur des traces Npgsql (`db.query.text`), filtré
  sur la base du praticien dès l'enregistrement. Les dépôts construisent leur contexte eux-mêmes, et un intercepteur EF
  n'y est pas injectable depuis un test HTTP.

| Comportement | Test | Preuve rouge |
|---|---|---|
| `GET /patients/{id}/medical-documents?page=&pageSize=` liste les pièces jointes (noms, tailles, types identiques à la base) sans sélectionner `Content` | `ThePatientFolderPage_ListsTheAttachments_WithoutReadingTheirContent` | mutation M1 |
| Même chose sans pagination | `TheWholePatientFolder_ListsTheAttachments_WithoutReadingTheirContent` | M1 |
| Même chose pour `POST /patients/mails` | `ThePatientMailsPage_ListsTheAttachments_WithoutReadingTheirContent` | M1 |
| **Garde** : 15 routes GET de lecture du parcours (dossiers, page d'en-têtes, contenu du message, vues du jour, étiquettes, fiche, dossier, documents, opposition, patients du jour) ne sélectionnent jamais `MailAttachments."Content"`. Le téléchargement est la seule exemption, et la garde vérifie qu'il le lit | `NoReadRouteOfTheJourney_ReadsAttachmentContent_OnlyTheDownloadDoes` | M1 : la garde désigne exactement les deux routes `medical-documents`, avec la forme SQL du banc (`SELECT m."MailId", m."Id", m."Content", …`) |
| Cas d'échec : patient inconnu, 404 `application/problem+json`, pour la page du dossier | `PatientFolderEndToEndTests.AnUnknownPatientHandle_Is404ProblemJson` (ligne `?page=1&pageSize=20` ajoutée à la théorie existante) | inchangé, vert |

- **M1** = le `GroupBy(a => a.MailId).ToDictionaryAsync(g => g.Key, g => g.Select(a => new AttachmentDto {…}))`
  d'origine réinjecté. Joué deux fois : sur le premier correctif, puis sur le code final après la passe qualité. Les 4
  tests sont rouges les deux fois.
- **Restauration** : depuis une copie (`cp` puis `touch`), vérifiée par `cmp`, puis recompilation complète avant toute
  suite `--no-build`. Mémoire « mutation restaurée ». Une première suite complète, lancée par erreur sur un binaire
  encore muté, a été arrêtée avant son verdict.
- **Prémisses affirmées** :
  - patient rattaché par l'enrichissement ;
  - au moins une pièce jointe avec son contenu en base ;
  - commandes SQL captées (par test, et au total pour la garde) ;
  - requête sur `MailAttachments` vue ;
  - téléchargement qui lit `Content`.

**Passe qualité (§Q, /simplify, 4 axes)** :
- **Appliqué** :
  - lecture en flux dans `dtosByMailId` (efficacité) ;
  - capture filtrée par base dès l'enregistrement, `AllData` au lieu de `AllDataAndRecorded`, et créée après le
    démarrage du serveur avec libération du serveur en cas d'échec (efficacité, simplification) ;
  - `Scene` construite d'un bloc (constructeur principal, `Seed` exposé) ;
  - une seule assertion pour les trois routes du dossier patient ;
  - le test 404 ajouté rejoint la théorie existante de `PatientFolderEndToEndTests` ;
  - `AddScoped<IPatientService, PatientService>()` ;
  - regroupement de la biologie (altitude) ;
  - garde élargie de 11 à 15 routes.
- **Écarté, noté** :
  - mettre en commun la détection « lit `Content` » avec `HeaderListingProjectionTests` (task-322) : les deux helpers
    sont privés et hors du diff ;
  - une fixture de classe pour ne démarrer l'hôte qu'une fois : gain de durée de test seulement ;
  - une projection `AttachmentDto` partagée : sept copies à la main dans les deux dépôts, déjà divergentes (`Guid`
    absent en deux endroits), hors du sujet `Content`.
- **Suggestions de suite**, hors périmètre, pour l'humain :
  - **sortir `Content` dans une entité dépendante sur la même table** (table splitting EF, sans migration de schéma).
    C'est la cause de fond : toute matérialisation de `MailAttachment` ramène le binaire, et task-322 puis task-429 en
    sont deux cas. Seuls le téléchargement et les écritures y accèdent ;
  - **une garde qui refuse tout par défaut** au niveau de la collection `UseCases` (toute lecture de `Content` hors
    d'une liste d'exemptions), au lieu d'une liste de routes. À rapprocher de task-431 et task-432.

**Observation hors périmètre** :
- `GET /api/v1/mail/tags/{code}/emails` sur une étiquette **inconnue** rend **500** (`Result-mapped 500 … Tag not
  found`) au lieu de 404. C'est un écart à la règle 12, vu en écrivant la garde.
- Non corrigé ici, à ouvrir en task.

**Prévention (règle d'or)** : entrée `groupby-final-materialise-l-entite` dans `conventions/csharp.md`
(2 occurrences : task-322, task-429).

## Mesure au banc

**Tir court 1400 → 1996** :
- conditions : IA simulée, pool 1, tireur k6bench, banc mail cluster, `LATENCY_MS=96` ;
- harnais : celui de `develop` (`f50f2ae5`) pour les deux tirs.

**Ordre** : task-429 (`1d0d5185`, 2026-11-06 23:20) **puis** contrôle `develop` (`f50f2ae5`, 2026-11-07 00:10), même
session. Le tir de la task, passé en premier sur le cache le plus froid (33,9 contre 28,2 fautes majeures/s), est le
défavorisé : l'écart mesuré ne peut pas être surestimé par l'ordre.

| Mesure | Contrôle `develop` | **task-429** |
|---|---|---|
| Forme `SELECT m."MailId", m."Id", m."Content", … ORDER BY m."MailId"` | 3 941 appels, 84 s, 14,1 Go lus | **0 appel** |
| Forme qui la remplace (`SELECT m."MailId", m."Guid", m."FileName", m."ContentType", m."Size"`) | — | 3 455 appels, 0,2 s, 0,1 Go |
| Lectures disque du tir (`shared_read`) | 16,2 Go | **6,4 Go (−60 %)** |
| Temps cumulé de lecture disque | 123 s | 92 s |
| Temps SQL total | 22,9 min | **19,9 min (−13 %)** |
| Coût SQL par requête HTTP | 4,7 ms | **4,1 ms** |
| Taux de cache (blocs) | 96,02 % | **98,58 %** |
| Backends actifs (équivalent) | 1,52 | 1,34 |
| Débit à 1996, erreurs | 410,6 req/s, 0,01 % | 414,2 req/s, 0,01 % |

**Étapes du parcours, p50 / p95 (ms)** — palier 1400 | palier 1996 :

| Étape | Contrôle `develop` | **task-429** |
|---|---|---|
| Page d'un dossier patient | 57/114 \| 88/251 | **56/65 \| 59/80** |
| Fiche patient complète | 307/520 \| 452/1 092 | **262/430 \| 355/754** |
| Ouvrir / rafraîchir l'inbox | 40/99 \| 57/182 | 40/92 \| 53/144 |
| Ouvrir un message enrichi | 34/68 \| 57/154 | 34/61 \| 49/116 |
| Télécharger une PJ | 37/78 \| 64/236 | 37/69 \| 55/231 |
| Recherche | 328/606 \| 373/734 | 327/649 \| 351/657 |

- **Critère de la DoD** : **aucune étape ralentie**. Le pire écart au p95 est la recherche à 1400 (+7 %), qui
  s'améliore à 1996 (−10 %). Aucun écart ne dépasse 20 % : l'A/B/A n'est pas requis.
- **Effet attendu, constaté** : la page du dossier patient perd 68 % de son p95 à 1996, et la fiche patient complète
  31 %. Les autres étapes gagnent un peu, parce que Postgres relit moins le disque et sert plus vite le reste.

Rapports :
- `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task429-20261106.md`
- `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task429-controle-develop-20261107.md`

Lignes d'index : commit `ce971762` sur la branche de la task.
