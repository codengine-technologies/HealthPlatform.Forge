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
| **Total cycle** | | **18 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
