# todo-task-019.md — PK Guid v7 : cluster Mail + enfants

**Repos**: dtos-mss, api-mail, client-blazor, client-angular
**Dependencies**: archived-task-018
**Epic**: E009

## Objectif

Deuxième phase du chantier durcissement sécurité (cf. `archived-task-018.md`
pour l'objectif global et la convention complète). Migre le **cluster Mail**
de `int` vers `Guid` v7 — Mail (root du cluster) et toutes ses tables filles.
Achève également la migration de `MailMedicalDocument.MailId` qui était
restée en `int` à la fin de task-018 par contrainte de fermeture FK.

## Périmètre détaillé

### Tables Postgres — édition de la migration consolidée

- `Mails.Id` : int → Guid (v7 généré côté .NET, pas de default DB)
- `MailContents.Id`, `MailContents.MailId` : int → Guid
- `MailRecipients.Id`, `MailRecipients.MailId` : int → Guid
- `MailAttachments.Id`, `MailAttachments.MailId` : int → Guid
- `MailPatients.Id` : int → Guid (vérifier avec `/develop` si MailPatient
  a une FK vers Mail ou Patient — Patient est déjà Guid depuis task-018)
- `Tags.Id` : int → Guid
- `MailTags.Id`, `MailTags.MailId`, `MailTags.TagId` : int → Guid
- `MailMedicalDocuments.MailId` : int → Guid (FK vers le nouveau
  `Mails.Id` — **achève** la migration de cette table)

### Entités EF Core

- `Mail.cs`, `MailContent.cs`, `MailRecipient.cs`, `MailAttachment.cs`,
  `MailPatient.cs`, `Tag.cs`, `MailTag.cs` : `Id` Guid + FK vers `Mail` /
  `Tag` en Guid
- `MailMedicalDocument.cs` : `MailId` int → Guid (complète task-018)
- `MailDataContext` : `ValueGenerator<Guid>` (réutilisation du
  `UuidV7ValueGenerator` créé en task-018) appliqué aux 7 nouvelles
  entités du cluster

### DTOs (`Dtos/`)

- `MailDto.Id` : int → Guid (`DraftId` déjà Guid, inchangé)
- `MailMedicalDocumentDto.MailId` : int → Guid (complète task-018)
- `DuplicateClusterDto.MailId` : int → Guid (complète task-018)
- `TagDto.Id` : int → Guid
- Tous les DTOs `MailRecipientDto`, `MailAttachmentDto`, `MailContentDto`,
  `MailPatientDto` : `Id` et FKs Mail/Patient → Guid (à scanner par
  `/develop`)
- Bump NuGet : `HealthPlatform.Dtos.Mss` → `301.0.0`

### Endpoints API

- **Aucun changement de route** : `MailController` utilise déjà des
  identifiants IMAP UID (string `{emailid}`) qui sont indépendants de la
  PK Postgres `Mail.Id`. La migration est purement DB / DTO / payload —
  les routes restent identiques.
- `MailExportController.{folderId}` : `{folderId}` n'est ni int ni guid
  ici (it's a folder name string), pas touché.
- Vérifier qu'aucun controller du périmètre n'introduit `{mailId:int}` ou
  `{tagId:int}` — sinon migrer en `:guid`.

### Repositories / Services

- `MailRepository` : signatures `int mailId` / `int tagId` → `Guid`
  partout. Inclut les méthodes critiques `AddNewMailAsync`,
  `UpdateExistingMailWithContentAsync`, `FindExistingDuplicateOfAsync`
  (retours impactés), `RecordDuplicateDecisionAsync` (reçoit document
  Guid depuis task-018, propage vers `Mail` Guid désormais), bulk move /
  flag / read.
- `IMailRepository` interface mise à jour
- Tests xUnit : ~250-300 tests touchés (Arrange Guid)

### Frontend Blazor

- Bump `Directory.Packages.props` à `HealthPlatform.Dtos.Mss 301.0.0`
- Composants `MailHeader.razor`, `MailDetailComponent.razor`,
  `MailReadOnlyView.razor`, `DuplicateCleanupDialog.razor`,
  `BaseComponent.razor` : bindings `@mail.Id`, `@tag.Id` typés Guid
- `IPatientService` / `IMailService` : signatures `int mailId` → `Guid`
- Tests bUnit : Arrange Guid

### Frontend Angular (mode code-only)

- `mail.model.ts:27` (= `MailDto.id`) : `id: number` → `id: string`
- `mail.model.ts` autres occurrences avec `mailId` / `tagId` numérique →
  string
- Modèles `tag.model.ts` (s'il existe) ou la définition inline du Tag →
  string
- `mss-api.service.ts` : toutes les signatures avec `mailId: number` ou
  `tagId: number` → `string`
- Composants `mail-header`, `mail-detail`, `mail-list` (s'il existe),
  `tag-*` : props et trackBy en string
- Tests Vitest : Arrange string id

## Convention — rappel (cf. task-018 pour le détail complet)

1. Routes : `{id:guid}` jamais `{id:int}` pour les entités migrées
2. Génération : `Guid.CreateVersion7()` via EF `UuidV7ValueGenerator` —
   **pas** `gen_random_uuid()` (v4)
3. Type Angular : `string`, **pas** `number`
4. Type C# : `Guid` PK, `Guid?` FK optionnel
5. Tests : `Guid.NewGuid()` ou `Guid.CreateVersion7()` dans Arrange
6. Pas de legacy : aucun `int Id` ne subsiste sur les entités migrées
7. Linting : `/sonar` et `/review` rejettent toute apparition résiduelle
   de `{id:int}` dans les routes du périmètre

## Definition of Done

- [ ] Build passes (0 errors) sur les 4 repos
- [ ] Tests passent (0 failures) sur les 4 repos
- [ ] Migration consolidée éditée pour les 7 tables du cluster + finalisation
      `MailMedicalDocuments.MailId`
- [ ] `DROP DATABASE` + replay → DB recréée, `\d+ "Mails"` montre `id uuid`
      sans default DB ; idem pour `MailContents`, `MailRecipients`,
      `MailAttachments`, `MailPatients`, `Tags`, `MailTags`
- [ ] Toutes les entités du cluster ont `Id` de type `Guid`
- [ ] Tous les DTOs cross-boundary du cluster exposent `Guid`
- [ ] `grep -rE 'public\s+int\s+Id\s*\{' Api/Mail/src/Domain/Entities/Mail.cs Api/Mail/src/Domain/Entities/MailContent.cs Api/Mail/src/Domain/Entities/MailRecipient.cs Api/Mail/src/Domain/Entities/MailAttachment.cs Api/Mail/src/Domain/Entities/MailPatient.cs Api/Mail/src/Domain/Entities/Tag.cs Api/Mail/src/Domain/Entities/MailTag.cs`
      → vide
- [ ] `grep -rE 'public\s+int\??\s+MailId\s*\{' Api/Mail/src/Domain/Entities/`
      → vide (toutes les FK Mail sont Guid, y compris MailMedicalDocument)
- [ ] `grep -rE 'id\s*:\s*number' Client/Angular/front/libs/mss/src/core/models/mail.model.ts`
      → vide
- [ ] Tests :
  - [ ] >= 1 test xUnit par méthode publique de `MailRepository` mise à
        jour pour Guid (en particulier `AddNewMailAsync`,
        `UpdateExistingMailWithContentAsync`, `FindExistingDuplicateOfAsync`,
        `RecordDuplicateDecisionAsync`)
  - [ ] Test d'intégration Postgres : insert d'un Mail avec ses children
        → tous les ids générés sont des Guid v7 strictement croissants
  - [ ] Tests bUnit Blazor sur composants Mail (au moins le badge
        duplicate, la dialog cleanup, le détail) avec Guid
  - [ ] Tests Vitest Angular sur composants Mail avec string id
- [ ] `HealthPlatform.Dtos.Mss 301.0.0` publié via GH Actions
- [ ] `Directory.Packages.props` bumpé sur `api-mail` et `client-blazor`
- [ ] Aucune régression : `dotnet test` (api-mail) + `nx test mss-lib`
      verts

## Manual Test Plan

1. **DB schema** :
   ```bash
   docker exec mss-mail-postgres psql -U postgres -d mss_mail -c '\d+ "Mails"'
   ```
   Attendu : `id uuid` sans default DB, FK `MailFolderId` (vers MailFolders
   qui sera migré en task-020 — peut rester int provisoirement, à valider
   par `/develop`).

2. **Boot stack** + **réception d'un mail** : envoyer un mail vers la
   mailbox de test, vérifier qu'il apparaît dans l'inbox avec un `id`
   UUID dans le payload réseau (DevTools → Network → response JSON).
   `mail.id` = string UUID, **plus** un nombre.

3. **Lecture du contenu** : ouvrir le mail → contenu chargé via
   `/folders/{folder}/emails/content/{emailid}` (UID IMAP, pas Guid →
   inchangé) ; le payload retourné contient `mail.id` Guid + tous les
   `attachments[].id`, `recipients[].id`, `medicalDocuments[].id`,
   `medicalDocuments[].mailId` en Guid.

4. **Tag** : appliquer/retirer un tag sur un mail → request body avec
   `tagId` Guid. Lister les mails par tag → réponses avec ids Guid.

5. **Tri temporel v7** : insérer 5 mails à 1 s d'intervalle puis
   `SELECT id FROM "Mails" ORDER BY id` — l'ordre lexicographique reflète
   l'ordre d'arrivée (preuve v7 active sur Mails comme sur le cluster
   task-018).

6. **Anti-régression cluster task-018** : workflow doublon CDA + workflow
   rattachement patient continuent de fonctionner end-to-end (les
   MailMedicalDocument.MailId Guid sont bien résolus côté repo).

## Branches

- `dtos-mss` (pushed) : feat/task-019-pk-guid-v7-mail-cluster — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-019-pk-guid-v7-mail-cluster
- `api-mail` (pushed) : feat/task-019-pk-guid-v7-mail-cluster — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-019-pk-guid-v7-mail-cluster
- `client-blazor` (pushed) : feat/task-019-pk-guid-v7-mail-cluster — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-019-pk-guid-v7-mail-cluster
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` — humain gère branche, commit, push, PR TFS. Snapshot au /start : `feature/nova-rewriting-mss-fixes-20260410` (l'humain peut switcher avant /develop ; /develop relit la branche au moment de l'exécution).
