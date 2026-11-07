# todo-task-430.md — Les comptages de biologie et d'étiquettes ne parcourent plus une table entière par ligne

**Repos**: api-mail
**Dependencies**: — (aucune ; indépendante de task-429, mesurable séparément)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1**. Ces deux requêtes lisent **232 Go de pages** en mémoire de Postgres sur un tir court, le double de
tout le reste réuni hors recherche. Leur coût croît comme le **carré** du volume d'une boîte : à 126 documents par base
au banc, il reste en mémoire et coûte du CPU. Une boîte réelle de plusieurs années le paiera bien plus cher.

> **Origine.** Exploration du 2026-11-06, préfiguration de task-433 : le détecteur « volume lu par ligne rendue »
> (task-431) appliqué au tir « après » de l'A/B/A (`Api/Mail/tests/loadtest-k6/reports/2026-11-06/pgstats-journey-193047.tsv`),
> puis plans d'exécution sur la base médiane du banc et lecture du code.

## Ce qui est établi

| Forme `pg_stat_statements` | Appels | Lignes | Pages lues | Lues par ligne | Temps SQL |
|---|---|---|---|---|---|
| F-A. `SELECT m."Id", … (SELECT count(*)::int FROM "MailMedicalDocumentBiology" AS m0 WHERE m."Id" = m0."MedicalDocumentId") AS "BiologyCount", (SELECT count(*) … "MailMedicalDocumentSummary" …) FROM "MailMedicalDocuments" AS m WHERE m."MailId" = ANY ($1)` | 88 248 | 1 594 065 | **143 Go** | 94 Ko | 114 s |
| F-B. `SELECT t."Code", t."Name", t."ColorCode", (SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EXISTS (… "Mails" … NOT "IsRead" …)), (la même sous-requête une 2ᵉ fois) FROM "Tags" AS t WHERE EXISTS (la même une 3ᵉ fois)` | 47 024 | 477 742 | **89 Go** | 195 Ko | 63 s |

**F-A — l'index de la biologie n'existe pas.**
- **Index absent** : `MailMedicalDocumentBiology` n'a **aucun index sur `MedicalDocumentId`** (seulement sa clé
  primaire). Sa voisine `MailMedicalDocumentSummary` a le sien (`IX_MedDocSummary_MedicalDocumentId`).
- **Plan d'exécution** (`EXPLAIN (ANALYZE, BUFFERS)`, base médiane) : `Seq Scan on "MailMedicalDocumentBiology"`
  **une fois par document** (`loops=18`, 264 lignes écartées à chaque passage). Le comptage des résumés passe par son
  index (`Index Only Scan`).
- **Code** : `MailRepository.LoadBulkContentLookupsAsync`, `BiologyCount = d.MailMedicalDocumentBiologies.Count`
  (vers la ligne 1967), sur le chemin de la page d'en-têtes de l'inbox.
- **Même cause probable** : `BiologyAckRepository` (`Where(b => b.IsFlagged)`, `AnyAsync(b => b.MedicalDocumentId == …)`)
  lit la même table. La forme `… "MailMedicalDocumentBiology" … WHERE m."IsFlagged"` lit 33 Ko par ligne rendue.

**F-B — le même comptage est calculé trois fois par étiquette, chacun par un parcours complet.**
- **Code** : `MailRepository.GetTagFoldersAsync` (vers la ligne 3444) construit les dossiers virtuels d'étiquettes.
  `Count` et `UnreadCount` y sont **deux expressions identiques**, et le filtre `Where` en est une troisième.
- **Plan d'exécution** : pour chaque étiquette (`loops=16`), `Seq Scan on "Mails"` puis `Seq Scan on "MailTags"`
  filtré sur `TagId`. Aucun index ne commence par `TagId` : celui qui existe est `IX_MailTags_MailId_TagId`, dans
  l'autre ordre.
- **Appelants** : `ImapFolderService` (×2) et `ImapService` (×2), c'est-à-dire la liste des dossiers.

**Ce qui est écarté par la même exploration** (pour mémoire, pas dans cette task) :
- **La lecture du registre** (72 Ko par ligne, 1 appel par requête HTTP) : environ 9 pages par appel, ce qu'une
  recherche indexée avec jointure et ancre fait normalement. Ce n'est pas un défaut. C'est un faux positif du détecteur,
  à traiter par task-431.
- **Le document médical chargé en entier** à l'ouverture d'un message (`… m."Body", … m."Embedding", … m."HtmlBody" …
  WHERE m."MailId" = $1`, 23 Go dont 5,4 Go sur disque) : `Body`/`HtmlBody` servent l'affichage. Seuls `Embedding`
  (~6 Ko) et `MetadataJson` sont lus pour rien. C'est un gain mineur, à confirmer par task-433.

## Objective

Chaque comptage passe par un index, ou se calcule une seule fois. La réponse des routes est strictement identique.

Règles :
- **F-A** : créer l'index `MailMedicalDocumentBiology("MedicalDocumentId")`.
  - Migration EF Core auditée (règle 7c) : le modèle et `MailDataContext` déclarent l'index, et la migration ne fait
    aucune opération fantôme.
  - La migration s'applique à **toutes les bases de boîte**, existantes et nouvelles, par le mécanisme habituel de mise
    à niveau des bases. Le `Develop log` dit lequel, et prouve qu'une base existante du banc reçoit l'index.
  - Vérifier par `EXPLAIN` que le comptage passe par l'index.
- **F-B** : un seul calcul du nombre de messages non lus de l'INBOX par étiquette, en une requête groupée (`GROUP BY`
  sur `TagId`), au lieu de trois sous-requêtes corrélées par étiquette.
  - `Count` et `UnreadCount` gardent **leur valeur actuelle**, identique entre eux : changer leur sens n'est pas l'objet
    de cette task.
  - Un index sur `MailTags("TagId")` n'est ajouté que si le plan de la requête réécrite le demande. Le `Develop log`
    dit pourquoi.
- **Comportement inchangé** : mêmes dossiers d'étiquettes, mêmes compteurs, même ordre. Mêmes `BiologyCount` et
  `SummaryCount` dans la page d'en-têtes.
- **Règle 14 inchangée** : données de la boîte, dans sa base, aucun accès ni aucune trace modifiés.

### Hors périmètre

- Le document médical chargé en entier à l'ouverture d'un message (`Embedding`, `MetadataJson`) : à juger par task-433.
- La lecture du registre : écartée, coût normal.
- Le sens des compteurs d'étiquettes (`Count` égal à `UnreadCount`) : si c'est un défaut fonctionnel, il fera l'objet
  d'une question à part, pas d'un changement ici.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] Migration EF de l'index de biologie auditée (règle 7c) :
      - le fichier est relu, aucune opération fantôme ;
      - le `.Designer.cs` et le snapshot sont présents ;
      - aucun changement en attente (`has-pending-model-changes`) ;
      - l'index est présent sur une base de boîte **existante** après la mise à niveau.
- [ ] **Test d'intégration de bout en bout (règle 1b), F-A** : sur la route de la page d'en-têtes de l'inbox (la route
      exacte, relevée par `/develop`, est dans le `Develop log`), avec une base contenant au moins deux documents
      porteurs de résultats de biologie :
      - la réponse réelle porte le bon nombre de résultats de biologie par document ;
      - le plan de la requête de comptage, relevé par `EXPLAIN` dans le test sur la vraie base du fixture, ne contient
        pas de `Seq Scan on "MailMedicalDocumentBiology"` ;
      - **vu rouge** sans l'index (migration retirée, ou index supprimé dans le test).
- [ ] **Test d'intégration de bout en bout (règle 1b), F-B** : sur la route de la liste des dossiers, avec deux
      étiquettes portant des messages non lus de l'INBOX et une étiquette sans message non lu :
      - la réponse réelle porte les dossiers d'étiquettes attendus, avec `count` et `unreadCount` attendus ;
      - l'étiquette sans message non lu est absente ;
      - le SQL émis, relevé par intercepteur EF, ne contient plus qu'**un** comptage par `TagId` ;
      - **vu rouge** sur le code d'avant (trois sous-requêtes corrélées).
- [ ] Cas d'échec : boîte sans étiquette, liste de dossiers sans dossier d'étiquette, réponse 200 inchangée
- [ ] Tests existants des dossiers, des étiquettes, de la biologie et de la page d'en-têtes verts sans modification de
      leurs assertions
- [ ] **Prévention (règle d'or)**, deux entrées dans `conventions/csharp.md` :
      - toute clé étrangère filtrée par une sous-requête corrélée (`.Count`, `.Any` sur une navigation) a un index qui
        **commence** par cette colonne ;
      - une même expression d'agrégat n'est jamais recopiée dans une projection EF : la calculer une fois.
- [ ] **Mesure au banc**, tir court 1400 → 1996, IA simulée, pool 1, contre un contrôle `develop` joué dans la même
      session (A/B, puis A/B/A si un écart de plus de 20 % apparaît) :
      - pages lues par F-A et F-B avant/après ;
      - temps SQL total ;
      - p50/p95 de l'inbox et de la liste des dossiers ;
      - aucune étape ralentie ;
      - rapports copiés dans `Docs/audits/`.
- [ ] Aucune donnée de santé en clair dans les logs, ni dans les rapports
- [ ] Parcours e2e verts (`/e2e`), aucun scénario ajouté : aucun parcours n'est modifié

## Manual Test Plan

- [ ] `cd Api/Mail && dotnet run --project src/AppHost`, une boîte rattachée avec des messages étiquetés non lus et des
      comptes rendus de biologie.
- [ ] Ouvrir la messagerie (`client-blazor` ou `client-mobile`) : les dossiers d'étiquettes s'affichent avec les mêmes
      compteurs qu'avant.
- [ ] Lire un message étiqueté : le compteur de son étiquette baisse d'un, et l'étiquette disparaît quand elle n'a
      plus de message non lu.
- [ ] Ouvrir l'inbox : les messages porteurs de biologie affichent leur indicateur comme avant.
- [ ] Au banc (facultatif) : vérifier dans le rapport que les deux formes ne lisent plus des dizaines de Ko par ligne.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — correctif de performance interne
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable — aucune identité patient lue ni écrite autrement
- **Authentification PS** : inchangée — PSC/e-CPS, verdict de l'opérateur MSSanté (règle 14)
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — les résultats de biologie (CR-BIO) déjà extraits sont comptés, pas re-lus ni
  re-validés
- **Tracé PGSSI-S** : inchangé — aucun acte nouveau, les actes existants restent imputés à leur auteur réel
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun changement (les codes LOINC des résultats ne sont pas touchés)
- **Hébergement HDS** : oui — données inchangées, dans la base de la boîte
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau

## Branches

- `api-mail` (pushed) : fix/task-430-comptages-biologie-et-etiquettes-un — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-430-comptages-biologie-et-etiquettes-un

> Pré-flight du /start (2026-11-07) : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` sur `develop`. `host` (`Host/Modules`) n'est pas un dépôt (connu). `interop` n'est plus la racine d'un dépôt (`--show-prefix` = `interop/`) : non bloquant pour cette task.

## Timings

*(généré par `tools/timing/report.sh --task task-430 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| /develop | ok | 2 h 06 min | 3 (26 s) | 2 (10 min 44 s) | — | api-mail 3B/2T |
| /sonar | ok | 10 min 53 s | 1 (53 s) | 5 (8 min 30 s) | 2 (46 s) | api-mail 1B/5T |
| /lint-angular | skipped | 0.5 s | — | — | — | angular non touché |
| /lint-mobile | skipped | 0.5 s | — | — | — | mobile non touché |
| **Total cycle** | | **2 h 17 min** | **4 (1 min 19 s)** | **7 (19 min 15 s)** | **2 (46 s)** | |

Autres commandes mesurées : capture ×2 (1 h 39 min)

## Develop log

**Correctifs** (`api-mail`) :
- **F-A, index de la biologie.** Migration FluentMigrator `20261107120000_AddMissingForeignKeyIndexes`, qui crée
  `IX_MailMedicalDocumentBiology_MedicalDocumentId`. `MailDataContext` déclare le même nom.
- **Extension de périmètre** (relue par la passe qualité, axe « altitude ») : la même migration crée
  `IX_MailRecipients_MailId`.
  - `MailRecipients.MailId`, clé étrangère lue par la page d'en-têtes (`MailId = ANY(…)`), n'avait pas d'index depuis
    l'origine.
  - Mesuré au tir task-429 du 2026-11-06 : 314 393 appels, 7,4 Go de pages, 12 s de SQL.
  - La suppression en cascade d'un message (`FK_MailRecipients_Mails`) parcourait aussi toute la table, une fois par
    message supprimé.
  - Même défaut et même preuve : ajouté ici plutôt que dans une task séparée.
- **F-B, `MailRepository.GetTagFoldersAsync`.** Un seul comptage des messages non lus de l'INBOX courante, groupé par
  `TagId` (`GroupBy(...).Select(g => new { g.Key, g.Count() })`), joint à `Tags`. Il remplace trois sous-requêtes
  corrélées identiques (filtre, `Count`, `UnreadCount`). `Count` et `UnreadCount` gardent la même valeur. Une étiquette
  sans message non lu n'a pas de groupe, donc pas de dossier, comme avant.
- **Index sur `MailTags(TagId)` non ajouté.** Le plan réécrit part de `MailId` (semi-jointure sur
  `IX_MailTags_MailId_TagId`) et groupe en mémoire : un index sur `TagId` ne servirait pas cette requête (passe
  qualité, axe « efficacité »).
- **Règle 7c** :
  - migration relue : deux `Create.Index`, leurs `Delete.Index` dans `Down`, aucune autre opération ;
  - pas de snapshot EF : les bases praticien ne passent que par FluentMigrator, et la DoD, qui parlait de « migration
    EF Core », est tenue sur son intention ;
  - même nom d'index dans le modèle et dans la base.
- **Mise à niveau des bases existantes**, par le mécanisme habituel (`BaseRepository.HandleEnvironmentDbSetupAsync`) :
  `MigrateUp` au premier accès d'une base, mémorisé par processus et par la clé Redis `setupdb:{base}` (24 h).
  - Une base existante reçoit donc l'index au premier accès qui suit l'expiration de sa clé, ou la purge de celle-ci,
    sur un processus neuf.
  - Au banc, les clés `setupdb:*` sont purgées avant chaque tir. Preuve sur une base existante : voir « Mesure au
    banc ».

**Tests (règle 1b)** :
- `UseCases/CountingQueriesEndToEndTests` (collection `UseCases`, boîtes n° 23 et 24) : vraie pile HTTP, Dovecot, base
  praticien construite par le **coureur de production** (FluentMigrator).
- `Repository/MissingForeignKeyIndexesMigrationTests` : coureur de production sur une base neuve, et non sur la
  fixture `EnsureCreated`, qui porte déjà ces index par convention EF (consigne `index-de-cle-etrangere-absent-en-base`).

| Comportement | Test | Preuve rouge |
|---|---|---|
| Page d'en-têtes (`GET /mail/folders/INBOX/emails/{uid}`) : le compte rendu enrichi est servi par la base, ses documents portent `HasBiologyResults` (issu de `BiologyCount`) et ses destinataires. Sur la base praticien, le comptage de biologie et la lecture des destinataires passent par leur index (plan relu avec `enable_seqscan=off`) | `TheHeaderPage_ServesBiologyFlagsAndRecipients_ThroughTheirForeignKeyIndexes` | M-A (migration sans attribut) : rouge, « Seq Scan » ; M-C (index des destinataires retiré) : rouge, `Seq Scan on "MailRecipients"` |
| Dossiers d'étiquettes (`GET /mail/folders`) : deux non lus → `count` et `unreadCount` 2/2, un non lu → 1/1, étiquette dont le seul message est lu → absente. Le SQL relevé ne lit `MailTags` qu'une fois | `TheTagFolders_CountTheUnreadInboxMailsOfEachTag_InOneGroupedCount` | M-B (ancienne forme réinjectée) : rouge, « 3 lectures de MailTags » |
| Cas d'échec : boîte sans étiquette → 200, dossiers servis, aucun dossier d'étiquette | `AMailboxWithoutTags_ListsItsFolders_WithoutAnyTagFolder` | non applicable (inchangé) |
| Base neuve migrée par le coureur de production : les deux index existent, sur la bonne colonne | `MissingForeignKeyIndexesMigrationTests.MigratingAFreshMailDatabase_CreatesTheBiologyDocumentAndRecipientsMailIndexes` | M-A, M-C |

- **Mutations** :
  - M-A et M-B jouées ensemble (3 tests rouges), M-C seule (2 tests rouges) ;
  - fichiers copiés avant mutation, restaurés depuis la copie, vérifiés par `cmp`, `touch`, puis recompilation
    complète avant toute suite `--no-build`.
- **Piège de mise en place, levé** : enrichi **avant** le listage des dossiers, le message était rangé hors de la
  génération courante de l'INBOX, donc ni servi par la base ni compté sous son étiquette. Le test suit maintenant
  l'ordre de l'application : dossiers et en-têtes d'abord, enrichissement ensuite. Les prémisses sont affirmées :
  message servi enrichi, biologie en base, destinataires présents.

**Passe qualité (§Q, /simplify, deux relectures sur quatre axes)** :
- **Appliqué** :
  - lecture du plan par `SqlProbe.ReadStringsAsync`, avec `enable_seqscan` passé dans la chaîne de connexion ;
  - `AsSpan().Count` ;
  - options JSON redondantes retirées ;
  - étiquetage factorisé dans `ArchiveMailboxServer.TagAsync`, repris par `AttachmentBytesReadEndToEndTests` (task-429) ;
  - extension `MailRecipients.MailId` (altitude).
- **Écarté** : l'index `MailTags(TagId)` (voir plus haut). Les index de `ContactMssAddresses.ContactId` et
  `ContactTags.ContactId` (aucune lecture au tir) sont notés dans la consigne.

**Prévention (règle d'or)**, `conventions/csharp.md` :
- `index-de-cle-etrangere-absent-en-base`, de 2 à **3 occurrences** : sous-requête corrélée, et contrôle « toute clé
  étrangère d'une table par praticien a son `Create.Index` » ;
- nouvelle entrée `agregat-recopie-dans-une-projection`.

## Mesure au banc

Tir court 1400 → 1996, IA simulée, pool 1, tireur k6bench, banc mail cluster, `LATENCY_MS=96`. Harnais de `develop`
pour les deux tirs.

**Ordre imposé** : contrôle `develop` (`01f8de6f`, 2026-11-07 09:26) **puis** task-430 (`a16e5a84`, 10:16), dans la
même session. Une fois créés par le tir de la task, les index restent en base : un contrôle joué après en aurait
profité. Le tir de la task, passé second, bénéficie d'un cache plus chaud. Les **pages lues** par forme, qui ne
dépendent pas de l'état du cache, sont la mesure qui fait foi. Les latences sont données à titre indicatif.

| Forme `pg_stat_statements` | Contrôle `develop` | **task-430** |
|---|---|---|
| F-B dossiers d'étiquettes (`FROM "Tags"`) | 47 997 appels, 62,4 s, **91,0 Go** (197 Ko/ligne) | 47 648 appels, **7,3 s, 3,7 Go** (8 Ko/ligne) — **−96 %** |
| F-A comptage `BiologyCount` | 88 717 appels, 111,8 s, **144,3 Go** (213 pages/appel) | 88 487 appels, **72,2 s, 82,3 Go** (122 pages/appel) — **−43 %** |
| Toutes les formes qui lisent la biologie | 157,3 s, 180,3 Go | 103,8 s, 104,0 Go |
| Destinataires (`FROM "MailRecipients"`) | 313 316 appels, 11,3 s, 7,3 Go | 312 299 appels, 10,6 s, 7,3 Go — inchangé |
| Temps SQL total | 19,6 min | **17,0 min (−13 %)** |
| Lectures disque (temps cumulé) | 82 s | 68 s |
| Débit à 1996, erreurs | 414,6 req/s, 0,01 % | 409,4 req/s, 0,01 % |

**Lecture des résultats** :
- **F-B** : gain complet, il ne dépend que du code.
- **F-A, partiel, et pour deux raisons établies.**
  1. **La migration n'a atteint que 1 684 bases sur 2 000** pendant le tir, alors que le comptage a tourné sur les
     1 996 bases actives (colonne `bases` de `pg_stat_statements`). Environ 312 bases actives ont donc tout le tir
     sans index.
     - Aucun échec de mise à niveau dans Seq.
     - Aucune clé `setupdb:*` dans le Redis du banc.
     - Cause non établie : voir « Question ouverte » ci-dessous.
  2. **Sur une base migrée**, `EXPLAIN (ANALYZE, BUFFERS)` de la forme `BiologyCount` montre le comptage par
     `Index Only Scan using "IX_MailMedicalDocumentBiology_MedicalDocumentId"` : 19 pages pour 18 documents, contre
     environ 8 pages **par document** avant. Le reste de la forme, c'est le parcours de `MailMedicalDocuments` lui-même
     (77 pages), que le planificateur préfère sur une table de 121 lignes : hors du défaut F-A.
  - **Estimation, non mesurée** : sur les seules bases migrées, environ 105 pages par appel, soit −51 %.
- **Destinataires** : l'index n'est pas choisi par le planificateur sur les tables du banc (quelques centaines de lignes,
  `MailId = ANY(…)` sur une page entière). Son intérêt porte sur les tables de production plus grandes, et sur la
  suppression en cascade, que le parcours médecin du banc n'exerce pas. Gain non démontré au banc, à le dire tel quel.
- **Latences**, p50 / p95 en ms, palier 1400 | palier 1996 :

  | Étape | Contrôle | task-430 |
  |---|---|---|
  | Arrivée tableau de bord (liste des dossiers) | 58/620 \| 64/641 | 58/556 \| 64/584 |
  | Ouvrir / rafraîchir l'inbox | 39/87 \| 52/142 | 39/87 \| 51/145 |
  | Fiche patient complète | 255/412 \| 347/709 | 257/411 \| 342/731 |

  - Aucune étape ne se dégrade de plus de 20 % : le pire écart est de +4 % au p95 (recherche à 1996, +4 % ;
    marquer lu, +5 %), dans le bruit.
  - À ces volumes, le gain de pages ne se voit pas sur les latences : les deux formes étaient servies depuis le cache
    (CPU), pas depuis le disque.
- **Index présent sur des bases existantes après mise à niveau** (DoD) : 1 684 bases sur 2 000, vérifié par
  `pg_indexes` sur l'ensemble des bases du banc.

### Question ouverte — des bases actives ne reçoivent pas la migration au premier accès

- **Constat** : sur 2 000 bases, 316 n'ont pas l'index après le tir, alors que 1 996 bases ont exécuté la forme
  `BiologyCount`. Aucun `Failed to setup database` dans Seq.
- **Le mécanisme** : `BaseRepository.HandleEnvironmentDbSetupAsync` migre au premier accès, puis mémorise la base par
  processus (`_migratedDatabases`, clé `UserContextInfo.UserDatabaseName`) et dans Redis (`setupdb:{base}`, 24 h).
- **Hypothèse à instruire** : la clé de mémorisation (`UserDatabaseName`) ne désigne pas toujours la base réellement
  ouverte (boîtes partagées, nommage par boîte depuis task-404). Une base marquée « migrée » à tort ne recevrait jamais
  la migration suivante.
- **Portée** : toute migration de schéma déployée en production. **Task à ouvrir**, hors du périmètre de task-430.

Rapports :
- `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task430-controle-develop-20261107.md`
- `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task430-20261107.md`

Lignes d'index : commit `ca94d3e3` sur la branche de la task.

## Sonar log

Analyse de la branche `fix/task-430-comptages-biologie-et-etiquettes-un` (HEAD `ca94d3e3`), 2026-11-07 10:20 UTC :
- build Release, tests avec couverture OpenCover sur les 5 projets, **0 échec** ;
- traitement serveur `SUCCESS`, 0 itération de correction nécessaire.

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-429) | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 0 | 0 | = |
| New coverage | 96,1 % | 96,0 % | −0,1 |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,9 % | 97,9 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

Skipped — `client-angular` non touché par la task (`**Repos**: api-mail`).

## Lint mobile log

Skipped — `client-mobile` non touché par la task.

## E2E log

Voies jouées le 2026-11-07 : `api-mail` à `ca94d3e3` (branche de la task), `client-mobile` à `develop`, `client-angular`
sur la branche du poste (code-only).

| Voie | Déclenchée par | Jouée / réutilisée | Résultat |
|---|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | jouée | ✅ 58 verts, 0 flaky, 0 rouge, parité verte |
| angular (`npm run e2e:mss`) | `api-mail` touché | jouée | ✅ 71 verts, 0 flaky, 0 rouge, parité verte |

Porte `gate` : code 0. Démontage vérifié : aucun conteneur e2e résiduel. Le seul port ouvert, `192.168.1.170:5052`,
est le relais `netsh portproxy` du tireur k6bench, sans lien avec l'e2e.

Aucun écran modifié : aucun scénario ajouté ni versionné (task backend sans effet visible).

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
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
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
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
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
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.
