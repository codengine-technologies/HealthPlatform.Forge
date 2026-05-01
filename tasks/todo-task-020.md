# todo-task-020.md — PK Guid v7 : User / Contact / Audit + scellement final

**Repos**: dtos-mss, api-mail, client-blazor, client-angular
**Dependencies**: archived-task-019
**Epic**: E009

## Objectif

Troisième et **dernière** phase du chantier durcissement sécurité. Migre les
clusters restants vers Guid v7 :

- **User / paramètres** : `User`, `UserSetting`, `MailSignature`
- **Contact** : `Contact`, `ContactMssAddress`, `ContactGroup`,
  `ContactGroupMember`, `ContactTag` — **et supprime le hack**
  `ContactDto.GetIntId()` (BitConverter sur 4 bytes du Guid, collision-prone)
- **Audit & utilitaires** : `MssAuditTrace`, `PendingAction`, `MailFolder`,
  `MailTemplate`

Et **scelle la convention** par un audit grep complet sur tous les repos
+ rejet de toute apparition future de `{id:int}` dans les nouvelles routes.

## Périmètre détaillé

### Tables Postgres — édition de la migration consolidée

- `Users.Id` : int → Guid
- `UserSettings.Id`, `.UserId` : int → Guid
- `MailSignatures.Id`, `.UserId` : int → Guid
- `Contacts.Id` : int → Guid (⚠ aligne enfin avec `ContactDto.Id` qui était
  déjà Guid côté DTO via le hack `GetIntId()`)
- `ContactMssAddresses.Id`, `.ContactId` : int → Guid
- `ContactGroups.Id` : int → Guid
- `ContactGroupMembers.Id`, `.ContactId`, `.GroupId` : int → Guid
- `ContactTags.Id`, `.ContactId` : int → Guid
- `MssAuditTraces.Id` : int → Guid
- `PendingActions.Id` : int → Guid
- `MailFolders.Id` : int → Guid
- `MailTemplates.Id` : int → Guid
- `MailMedicalDocuments.PractitionerContactId` : int → Guid (FK vers
  `Contacts.Id` — **achève** la migration de `MailMedicalDocument`
  démarrée en task-018)

### Entités EF Core

Toutes les entités citées ci-dessus : `Id` (et FK) en Guid. `MailDataContext`
applique le `UuidV7ValueGenerator` sur chaque PK.

### DTOs (`Dtos/`)

- **`ContactDto`** : déjà `Guid Id` côté DTO. **Suppression** de la méthode
  `GetIntId() => BitConverter.ToInt32(Id.ToByteArray(), 0)` (ligne 117) —
  collision-prone (4 bytes sur 16, ~1/65k birthday). Tout consommateur du
  `GetIntId()` doit être audité par `/develop` : remplacer par usage direct
  du Guid (l'entité `Contact.Id` étant désormais Guid, le mapping est trivial).
- `ContactGroupDto`, `ContactAuditEntryDto`, `ContactSearchFilterDto.GroupId` :
  déjà Guid, inchangés
- `MailSignatureDto.Id` : int → Guid
- `MailTemplateDto.Id` : int → Guid (init-only)
- `ManagementDtos` : 6 records (`UserDto`, `MailDto` Mgmt, `MailFolderDto`,
  `EmailListItemDto`, etc. selon ce qui est dans le fichier — `/develop`
  scanne) → tous `Id` Guid
- `MssAuditTraceDto.Id` : int → Guid
- `AuditTraceFilterDto` : si `int Id` → Guid
- `FolderDto.Id` (si exposée) : Guid
- `UserSettingsDto` : si `Id` → Guid
- `MailMedicalDocumentDto.PractitionerContactId` : int → Guid (complète
  task-018)
- Bump NuGet : `HealthPlatform.Dtos.Mss` → `302.0.0`

### Endpoints API

- `ContactController` : 8 routes `{id:int}` / `{contactId:int}` / `{groupId:int}`
  → `:guid` (5 endpoints simples + 3 endpoints groupes + 2 endpoints
  composites contact/group)
- `AuditController.GetTraceById` : `{id:int}` → `{id:guid}`
- `MailTemplateController` : 3 routes `{id:int}` → `{id:guid}`
- `MailController.DeletePendingEmail` : `{id}` (untyped → vérifier par
  `/develop`, sans doute `int` implicite) → `{id:guid}`

### Repositories / Services

- `ContactRepository`, `IContactRepository`, `ContactService` : signatures
  Guid partout
- `UserRepository`, `MailSignatureRepository`, `MailTemplateRepository`,
  `MssAuditTraceRepository`, `MailFolderRepository`, `PendingActionRepository`
  (selon ce qui existe — `/develop` scanne) : signatures Guid
- Tests xUnit : ~100-150 tests touchés sur Contact + User + Audit + Template

### Frontend Blazor

- Bump `Directory.Packages.props` à `HealthPlatform.Dtos.Mss 302.0.0`
- Composants signature, template, audit, contacts : bindings Guid
- Tests bUnit : Arrange Guid

### Frontend Angular (mode code-only)

- `audit.model.ts:40` : `id: number` → `id: string`
- `mail-template.model.ts:7` et `:53` : `id: number` → `id: string`
- `pending-email.model.ts:7` : `id: number` → `id: string`
- `signature.model.ts:7` et `:28` : `id: number` → `id: string`
- `mss-api.service.ts` :
  - `cancelPendingEmail(id: number)` (ligne 229) → `string`
  - `updateSignature(id: number, ...)` (307) → `string`
  - `deleteSignature(id: number)` (314) → `string`
  - `setDefaultSignature(id: number)` (320) → `string`
  - `updateTemplate(id: number, ...)` (445) → `string`
  - `deleteTemplate(id: number)` (452) → `string`
  - `getAuditTraceById(id: number)` (1011) → `string`
- Composants : signature-list, template-list, audit-list, pending-list
  (selon le code) — props et bindings string
- Tests Vitest : Arrange string

### Scellement final — convention auditée

Cette task ferme le chantier. Les checks suivants doivent passer **strictement**
sur l'ensemble des repos (pas de tolérance) :

- `grep -rE '\bint\s+Id\s*\{' Api/Mail/src/Domain/Entities/` → **vide**
- `grep -rE '{id:int}|{contactId:int}|{groupId:int}|{patientId:int}|{documentId:int}|{mailId:int}|{tagId:int}|{templateId:int}|{userId:int}|{traceId:int}' Api/Mail/src/Api/Controllers/` → **vide**
- `grep -rE '\.AsInt32\(\).*PrimaryKey' Api/Mail/src/Infrastructure/Migrations/` → **vide**
- `grep -rE 'public\s+(int|long)\s+Id\s*\{' Dtos/` → **vide**
- `grep -rE 'public\s+(int|long)\??\s+\w*Id\s*\{' Dtos/` → **vide** (toutes
  FK exposées en DTO sont Guid)
- `grep -rnE 'id\s*:\s*number|\w+Id\s*:\s*number' Client/Angular/front/libs/mss/src/core/models/` → **vide** (en excluant les fichiers générés)
- `grep -n 'GetIntId' Dtos/` → **vide** (hack supprimé)
- `grep -nE 'BitConverter\.ToInt32.*ToByteArray' Dtos/` → **vide**

## Convention — rappel (cf. task-018 pour le détail)

1. Routes : `{id:guid}`
2. Génération : `Guid.CreateVersion7()` via `UuidV7ValueGenerator`
3. Type Angular : `string`
4. Type C# : `Guid` / `Guid?`
5. Tests : `Guid.NewGuid()` / `Guid.CreateVersion7()` dans Arrange
6. Pas de legacy
7. Linting strict en sortie de cette task

## Definition of Done

- [ ] Build passes (0 errors) sur les 4 repos
- [ ] Tests passent (0 failures) sur les 4 repos
- [ ] Migration consolidée éditée pour les 12 tables restantes du cluster
      User / Contact / Audit / Template + finalisation
      `MailMedicalDocuments.PractitionerContactId`
- [ ] `DROP DATABASE` + replay → toutes les tables Postgres ont `id uuid`
      (vérification psql `\d+`)
- [ ] **Aucun `int Id` ne subsiste** sur aucune entité du domaine
      (audit grep complet — cf. liste scellement)
- [ ] **Aucune route `{id:int}`** ne subsiste dans aucun controller (audit
      grep complet)
- [ ] **`ContactDto.GetIntId()` supprimé** ; aucun consommateur ne référence
      cette méthode (build casse si oublié)
- [ ] **Aucun `gen_random_uuid()` ni `WithDefault(SystemMethods.NewGuid)`**
      dans la migration consolidée (audit grep — sinon c'est du v4
      indésirable)
- [ ] Tests :
  - [ ] >= 1 test xUnit par méthode publique de `ContactRepository`,
        `MailSignatureRepository`, `MailTemplateRepository`,
        `MssAuditTraceRepository` adapté à Guid
  - [ ] Test de non-régression : un Contact créé par l'UI a bien un `Id`
        Guid v7 (préfixe temporel observable)
  - [ ] Test bUnit : suppression d'une signature, application d'un template
        — bindings Guid OK
  - [ ] Tests Vitest : composants signature/template/audit-list avec string id
- [ ] `HealthPlatform.Dtos.Mss 302.0.0` publié
- [ ] `Directory.Packages.props` bumpé sur `api-mail` et `client-blazor`
- [ ] **`/tech-writer E009`** : nouveau chapitre **Sécurité — Identifiants
      opaques (Guid v7)** ajouté à `Docs/epics/E009-...md`. Le chapitre
      résume :
  - La motivation (anti-énumération IDOR, durcissement)
  - Le choix Guid v7 (RFC 9562, time-ordered, B-tree friendly, .NET 10
    natif)
  - Le découpage en 3 tasks (018 / 019 / 020) avec leurs clusters
  - La convention figée (routes `{id:guid}`, ValueGenerator côté .NET,
    string côté Angular, pas de legacy)
- [ ] Aucune régression : `dotnet test` (api-mail) + `nx test mss-lib`
      entièrement verts

## Manual Test Plan

1. **DB schema final** :
   ```bash
   docker exec mss-mail-postgres psql -U postgres -d mss_mail -c "\dt"
   docker exec mss-mail-postgres psql -U postgres -d mss_mail -c "
     SELECT table_name, column_name, data_type
     FROM information_schema.columns
     WHERE column_name = 'Id' AND table_schema = 'public';"
   ```
   Attendu : **toutes les colonnes `Id`** sont `uuid`. Aucune n'est
   `integer`. Aucun default `gen_random_uuid()` n'est positionné.

2. **Audit énumération** : essayer une URL avec un ancien id int sur les
   entités migrées par 020 :
   ```
   GET /api/v1/contact/1
   GET /api/v1/audit/traces/1
   GET /api/v1/mailtemplate/1
   ```
   Attendu : 404 (route ne match plus le constraint `:guid`). Aucune fuite
   d'information sur le ratio "id existant vs id inexistant" — toute
   tentative donne 404.

3. **Workflow Contact** : créer un contact via l'UI, vérifier que son `Id`
   dans le payload est un Guid v7 (préfixe temporel = maintenant). Le
   modifier, le supprimer, l'ajouter à un groupe — tous les `PUT/DELETE/
   POST` partent avec des Guids dans l'URL.

4. **Workflow Signature** : créer / éditer / supprimer une signature mail
   → ids Guid dans toutes les requêtes.

5. **Workflow Template** : idem.

6. **Workflow Audit** : ouvrir une trace d'audit depuis la liste → URL
   `GET /audit/traces/{guid}` → 200, contenu correct. Tenter
   `/audit/traces/00000000-0000-0000-0000-000000000001` → 404.

7. **Anti-régression task-018 + task-019** : workflow complet patient +
   document + duplicate + tag + signature en un seul scénario manuel
   (envoyer un mail avec CDA, recevoir le doublon, confirmer doublon,
   rattacher patient, tagger, archiver) — tout doit fonctionner avec
   uniquement des Guids v7 en circulation.

8. **Doc E009** : ouvrir `Docs/epics/E009-...md` après `/tech-writer` →
   chapitre Sécurité présent, lisible, à jour.
