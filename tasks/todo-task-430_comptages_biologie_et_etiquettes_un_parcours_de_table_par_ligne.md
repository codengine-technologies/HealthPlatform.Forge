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
