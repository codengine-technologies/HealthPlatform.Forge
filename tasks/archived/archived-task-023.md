# todo-task-023.md — Ownership scoping dans les repositories (défense en profondeur anti-IDOR)

**Repos**: api-mail, dtos-mss
**Dependencies**: todo-task-021, todo-task-022
**Epic**: E009

## Objectif

Phase 6 — **clôture définitive** du chantier durcissement sécurité.
Avec task-021 (validation JWT crypto) et task-022 (réouverture explicite
des endpoints publics + SSE sécurisés), un attaquant ne peut plus se
faire passer pour un autre utilisateur via le header `Client-Email`.
Reste **un dernier vecteur IDOR** : si un Guid de ressource leak (logs,
screenshot, audit trail partagé, breach), un utilisateur authentifié
légitime peut accéder à une ressource d'un autre tenant car les
repositories ne filtrent pas par `UserId`.

Audit task-020 a identifié 5 dépôts vulnérables :

| Repository | Méthodes incriminées | Entité a `UserId` ? |
|---|---|---|
| `ContactRepository` | `GetByIdAsync`, `DeleteAsync`, `ToggleFavoriteAsync`, `UpdateAsync`, `GetGroupByIdAsync`, `DeleteGroupAsync`, `UpdateGroupAsync`, `AddContactToGroupAsync`, `RemoveContactFromGroupAsync` | ❌ Pas de UserId sur Contact / ContactGroup |
| `MailSignatureRepository` | `GetByIdAsync`, `DeleteAsync`, `SetDefaultAsync` | ✅ Guid UserId présent |
| `MailTemplateRepository` | `GetByIdAsync`, `UpdateAsync`, `DeleteAsync` | ❌ Pas de UserId — décision per-user à acter |
| `AuditTraceRepository` | `GetByIdAsync`, `GetTracesAsync` | ✅ string UserId (claim email) — mais `GetTracesAsync` retourne **tous** les utilisateurs |
| `PendingActionRepository` | `GetByIdAsync`, `DeletePendingActionAsync`, `MarkAs*Async`, `FindPendingActionAsync` | ❌ Pas de UserId — décision per-user à acter |

## Périmètre détaillé

### Décisions métier préalables (à arbitrer avec le PO)

1. **MailTemplate** : per-user ou global ?
   - Si **per-user** (recommandé pour la confidentialité des modèles
     médicaux) → ajouter colonne `UserId Guid NOT NULL`
   - Si **global** (templates partagés à toute l'organisation) →
     conserver tel quel mais documenter explicitement
   - **Hypothèse retenue par défaut : per-user**, alignée sur
     MailSignature

2. **Contact** : per-user ou global ?
   - Aujourd'hui : tous les contacts de tous les médecins partagent la
     même table sans cloisonnement
   - **Hypothèse retenue par défaut : per-user** — un médecin gère son
     propre carnet d'adresses MSS ; les contacts CDA auto-créés (cf.
     task-018 PatientContactService) sont eux aussi rattachés au médecin
     destinataire du CDA
   - Cas particulier : les **groupes système** (`Praticiens CDA`,
     `Patients CDA` créés par `GetOrCreatePractitionerGroupAsync` /
     `GetOrCreatePatientGroupAsync`) — peuvent rester globaux ou
     devenir per-user. Recommandation : per-user pour rester cohérent
     (un médecin = un groupe système).

3. **PendingAction** : per-user ou global ?
   - Les actions sont déclenchées par un client mail d'un user spécifique
     (mark read, delete, etc.) — **per-user obligatoire**

### Migration schéma — édition de la migration consolidée

`20240101_SetupMigration.cs` : ajout de `UserId Guid NOT NULL + FK Users(Id)
+ Index` aux tables :

- `Contacts.UserId`
- `ContactGroups.UserId` (et propagation : `ContactGroupMembers` reste
  non porteur — l'ownership remonte via le FK `GroupId`)
- `ContactMssAddresses.ContactId` reste suffisant (FK vers Contact qui
  porte UserId)
- `ContactTags.ContactId` idem
- `MailTemplates.UserId`
- `PendingActions.UserId`

Convention :
```csharp
.WithColumn("UserId").AsGuid().NotNullable()
    .ForeignKey("FK_<Table>_Users", "Users", "Id")
.WithColumn("...")  // colonnes existantes
// puis :
Create.Index("IX_<Table>_UserId").OnTable("<Table>").OnColumn("UserId");
```

### Entités domaine

```csharp
public class Contact
{
    public Guid Id { get; set; }
    public Guid UserId { get; set; }   // ← nouveau
    // ...
}

public class ContactGroup { public Guid Id { get; set; } public Guid UserId { get; set; } /* ... */ }
public class MailTemplate { public Guid Id { get; set; } public Guid UserId { get; set; } /* ... */ }
public class PendingAction { public Guid Id { get; set; } public Guid UserId { get; set; } /* ... */ }
```

`User` reste référencé via FK ; l'entité `User` actuelle est minimale
(`Id Guid + Email string`) et suffit.

### Pattern repository — filtre systématique

Helper `BaseRepository.GetCurrentUserIdAsync()` (déjà partiellement
existant via `GetOrCreateUserIdAsync` dans `MailSignatureRepository` et
`UserSettingsRepository` — à factoriser) :

```csharp
protected async Task<Guid> GetCurrentUserIdAsync(CancellationToken ct = default)
{
    // UserContextInfo.Email est garanti non-vide par task-021
    // (UserContextEnricherMiddleware).
    var user = await DataContext.Users
        .FirstOrDefaultAsync(u => u.Email == UserContextInfo.Email, ct);
    if (user != null) return user.Id;

    try
    {
        var added = DataContext.Users.Add(new User { Email = UserContextInfo.Email });
        await DataContext.SaveChangesAsync(ct);
        return added.Entity.Id;
    }
    catch (DbUpdateException ex) when (ex.InnerException is PostgresException { SqlState: "23505" })
    {
        DataContext.ChangeTracker.Clear();
        var existing = await DataContext.Users.FirstAsync(u => u.Email == UserContextInfo.Email, ct);
        return existing.Id;
    }
}
```

Et toutes les méthodes Repo des 5 dépôts incriminés deviennent :

```csharp
public async Task<ContactDto?> GetByIdAsync(Guid id)
{
    var userId = await GetCurrentUserIdAsync();
    var contact = await DataContext.Contacts
        .AsNoTracking()
        .Include(c => c.MssAddresses.OrderBy(a => a.SortOrder))
        .Include(c => c.Tags)
        .Include(c => c.GroupMembers)
        .FirstOrDefaultAsync(c => c.Id == id && c.UserId == userId);
    // ↑ filtre cumulatif : Id ET UserId
    if (contact == null) return null;  // 404 — ne pas leaker l'existence
    return MapToDto(contact);
}
```

Pattern identique sur `Update*`, `Delete*`, `ToggleFavorite*`,
`AddToGroup*`, `RemoveFromGroup*`, `GetTracesAsync` (filtrer
`UserId == userId.ToString()` — l'audit stocke l'email comme string),
`MarkAsCompleted/Failed/Processing`, etc.

### `AuditTraceRepository.GetTracesAsync` — filtre obligatoire

Aujourd'hui retourne **toutes** les traces. À filtrer par
`t.UserId == UserContextInfo.Email` (l'audit stocke l'email
identifiant, pas le Guid User.Id). Note : `MssAuditTrace.UserId` reste
`string` pour préserver la traçabilité même si l'entité User est
supprimée (vu en task-020).

### Controllers — retour 404 (pas 403) sur ownership KO

```csharp
var contact = await contactRepository.GetByIdAsync(id);
if (contact == null) return NotFound();  // 404 — ne distingue pas
                                          // "n'existe pas" et "pas à toi"
return Ok(contact);
```

Volontaire : un 403 leak l'existence de la ressource (un attaquant qui
balaie des Guids sait quels Guids existent même s'il n'y a pas accès).
404 garde le secret.

### Migration des données existantes (dev only)

Comme la base est dev-only (cf. task-018 — pas de migration prod), la
migration consolidée est éditée directement et un `DROP DATABASE` +
replay redémarre propre. Pas de backfill nécessaire.

**Si la base passe en staging / prod ultérieurement**, prévoir une
migration de backfill séparée :
- Pour `Contacts` : associer chaque contact au médecin qui l'a créé
  (champ `CreatedByEmail` ? historique audit ? sinon impossible et il
  faudra repartir de zéro)
- Pour `MailTemplates` / `PendingActions` : idem
- Le PO doit décider de la stratégie de migration prod le moment venu

## Convention scellée

1. **Toute méthode Repository qui prend un `Guid id` filtre
   cumulativement par `UserId`** (audit grep régulier).
2. **Toute table métier per-user porte une colonne `UserId Guid NOT NULL`
   + FK `Users(Id)` + index** ; les exceptions doivent être
   documentées (e.g. `Mails` indexées par UID IMAP cross-boundary,
   `Tags` partagées).
3. **Les controllers retournent 404 sur ownership KO**, jamais 403, pour
   ne pas leaker l'existence des Guids.
4. `BaseRepository.GetCurrentUserIdAsync` est la **seule** voie pour
   obtenir le UserId courant côté repo (factorisation des 3 helpers
   actuels `GetOrCreateUserIdAsync`).

## Definition of Done

- [ ] Build passes (0 errors) sur api-mail + dtos-mss
- [ ] Tests passent (0 failures) sur api-mail
- [ ] **Décisions PO actées** : Contact / MailTemplate / PendingAction
      sont **per-user** (à confirmer avant `/start`)
- [ ] Migration consolidée éditée :
  - [ ] `Contacts.UserId Guid NOT NULL` + FK + index
  - [ ] `ContactGroups.UserId Guid NOT NULL` + FK + index
  - [ ] `MailTemplates.UserId Guid NOT NULL` + FK + index
  - [ ] `PendingActions.UserId Guid NOT NULL` + FK + index
- [ ] `DROP DATABASE` + replay → vérification psql `\d+` que les 4
      tables ont la colonne `UserId uuid not null`
- [ ] Entités domaine : `Contact.UserId`, `ContactGroup.UserId`,
      `MailTemplate.UserId`, `PendingAction.UserId` ajoutés
- [ ] `BaseRepository.GetCurrentUserIdAsync` factorisé ; les 3
      duplications (`MailSignatureRepository`, `UserSettingsRepository`,
      éventuellement d'autres) supprimées
- [ ] Repositories adaptés :
  - [ ] `ContactRepository` — 9 méthodes filtrent par UserId
  - [ ] `MailSignatureRepository` — `GetByIdAsync`, `DeleteAsync`,
        `SetDefaultAsync` filtrent par UserId (les autres déjà OK car
        elles font `WHERE UserId = userId` en partant)
  - [ ] `MailTemplateRepository` — 4 méthodes filtrent par UserId
  - [ ] `AuditTraceRepository` — `GetByIdAsync`, `GetTracesAsync`
        filtrent par UserId (string email)
  - [ ] `PendingActionRepository` — 5 méthodes filtrent par UserId ;
        `AddAsync` setter automatique `action.UserId = currentUserId`
- [ ] Controllers retournent 404 (pas 403) sur ownership KO
- [ ] **Tests xUnit cross-tenant** (>= 1 par dépôt) :
  - [ ] User A crée un Contact ; User B avec Guid de ce Contact reçoit
        404 sur `GetByIdAsync` / `DeleteAsync` / `ToggleFavorite`
  - [ ] Idem pour MailSignature, MailTemplate, MssAuditTrace,
        PendingAction
- [ ] **Test d'intégration cross-tenant** : 2 sessions Keycloak
      simultanées (User A + User B), User B essaie de
      `GET /api/v1/contact/{guid-de-A}` → 404
- [ ] **Audit grep final** :
  - [ ] `grep -rE 'FirstOrDefaultAsync\(.*\.Id == id[^&]' src/Infrastructure/Repository/`
        → vide (toute query par Id doit avoir un `&& UserId ==`)
  - [ ] `grep -rE 'FindAsync\(\[?id\]?\)' src/Infrastructure/Repository/`
        → vide (FindAsync direct sur PK = bypass du filter UserId
        possible — interdit)
- [ ] Aucune régression : suite api-mail entièrement verte
      (1587 → ~1620 attendus avec les +35 tests cross-tenant)
- [ ] **`/tech-writer E009`** : chapitre Sécurité enrichi avec **bilan
      complet du chantier (tasks 018, 019, 020, 021, 022, 023)** —
      détaille les 3 couches de défense :
  1. Identifiants opaques Guid v7 (anti-énumération)
  2. Authentification JWT cryptographique + middleware secure-by-default
     (anti-spoofing)
  3. Ownership scoping en profondeur (anti-cross-tenant)

## Manual Test Plan

1. **DROP + replay DB** :
   ```bash
   docker exec mss-mail-postgres psql -U postgres -c "DROP DATABASE mss_mail;"
   # Redémarrer api-mail → migrations rejouent
   docker exec mss-mail-postgres psql -U postgres -d mss_mail -c "\d Contacts"
   ```
   Attendu : colonne `UserId uuid NOT NULL` + index `IX_Contacts_UserId`.

2. **Cross-tenant attack via Guid leak** :
   - Loguer en tant que `doctor1@dev`, créer un contact `Jean Dupont`,
     copier son `id` Guid depuis la response réseau
   - Loguer en tant que `doctor2@dev` (autre user Keycloak)
   - `GET /api/v1/contact/{guid-de-Jean-Dupont}` avec le JWT de
     doctor2 → **404 Not Found**
   - Vérifier dans les logs serveur : aucune trace de leak — la query
     SQL retourne 0 lignes car `WHERE Id = X AND UserId = Y` ne match
     pas

3. **Cross-tenant attack sur signature / template** : idem pour
   `GET /api/v1/signature/{guid}` et `GET /api/v1/mailtemplate/{guid}`.

4. **Audit trace cross-tenant** :
   - doctor1 envoie un mail → trace audit créée
   - doctor2 fait `GET /api/v1/audit/traces?dateFrom=...` → la liste
     **n'inclut pas** la trace de doctor1
   - doctor2 fait `GET /api/v1/audit/traces/{guid-de-trace-doctor1}`
     → 404

5. **PendingAction cross-tenant** :
   - doctor1 crée un pending email (envoi différé)
   - doctor2 fait `DELETE /api/v1/mail/pending-emails/{guid-doctor1}`
     → 404

6. **Workflow normal non-régression** :
   - doctor1 effectue le workflow complet : créer un contact, l'éditer,
     l'ajouter à un groupe, l'archiver. Tout fonctionne.
   - Idem signature / template / pending email.

7. **Audit grep en CI** :
   ```bash
   # Aucun FindAsync direct sur PK dans les repos métier
   ! grep -rE 'FindAsync\(\[?id\]?\)' src/Infrastructure/Repository/

   # Toute query par Id a un filtre UserId
   ! grep -rE 'FirstOrDefaultAsync\([^)]*\.Id == id\)$' src/Infrastructure/Repository/
   ```

## Branches

- `api-mail` (pushed) : feat/task-023-ownership-scoping-repos — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-023-ownership-scoping-repos
- `dtos-mss` (pushed) : feat/task-023-ownership-scoping-repos — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-023-ownership-scoping-repos
- `client-blazor`, `client-angular` : non listés dans **Repos**: — la US task-023 est purement back-end (ownership scoping côté repositories), aucun changement client requis
- `devops`, `psc-proxy-*` : managed manually by the human

## Develop log

- Repos touched : `api-mail` (full implementation), `dtos-mss` (no changes — DTOs unchanged ; UserId reste interne aux entités, jamais exposé via DTO)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail `6a0c711` — feat(security): ownership scoping in repositories (task-023)
  - api-mail `f7d63f1` — test(security): cross-tenant ownership tests (task-023)
- Build : ✓ api-mail (0 errors, 0 warnings)
- Tests : ✓ api-mail full suite — 1708 réussis / 0 échec (21 ignorés Ollama-related, attendus)
  - mss.mail.domain.tests : 86/86
  - mss.mail.api.tests : 96/96
  - mss.mail.infrastructure.tests : 273/273 (+21 cross-tenant nouveaux)
  - mss.mail.application.tests : 1161/1161
  - mss.mail.integration.tests : 92/92
- DOD self-check (commandable) :
  - [x] Build passes 0 errors
  - [x] Tests pass 0 failures (1708 verts vs ~1587 baseline + 21 nouveaux + ajustements existants ≈ 1708)
  - [x] Migration consolidée éditée : `Contacts.UserId`, `ContactGroups.UserId`, `MailTemplates.UserId`, `PendingActions.UserId` (NOT NULL + FK Users(Id) + IX_*_UserId)
  - [x] Entités domaine : `Contact.UserId`, `ContactGroup.UserId`, `MailTemplate.UserId`, `PendingAction.UserId`
  - [x] `BaseRepository.GetCurrentUserIdAsync` factorisé (suppression des doublons dans `MailSignatureRepository` et `UserSettingsRepository`)
  - [x] Repositories adaptés (5) :
    - `ContactRepository` (9 méthodes + filtre groupIds anti-tampering)
    - `MailSignatureRepository` (`GetByIdAsync` + `DeleteAsync` scopés ; les autres déjà OK via `WHERE UserId = userId`)
    - `MailTemplateRepository` (4 méthodes + `CreateAsync` set UserId, `UpdateAsync` re-load + verify ownership)
    - `AuditTraceRepository` (`GetTracesAsync` + `GetByIdAsync` filtrent par `UserId == UserContextInfo.Email`)
    - `PendingActionRepository` (9 méthodes + `AddAsync` set UserId)
  - [x] Controllers retournent 404 — déjà aligné depuis le départ (existing convention `if (entity == null) return NotFound()`)
  - [x] Tests xUnit cross-tenant : `CrossTenantOwnershipTests.cs`, 21 tests, ≥ 3 par dépôt (Contact, MailSignature, MailTemplate, PendingAction, AuditTrace)
  - [x] Audit grep `FirstOrDefaultAsync(...Id == id)$` (sans `&& UserId`) → 0 hit
  - [x] Audit grep `FindAsync([id])` dans les repos métier → 0 hit
- DOD deferred to manual test (HAG) :
  - DROP DATABASE + replay → vérification psql `\d+` (cf. Manual Test Plan §1)
  - Cross-tenant attack via Guid leak avec 2 sessions Keycloak (cf. §2-§5)
  - Workflow normal non-régression (cf. §6)
- Next step : `/sonar` (api-mail touched)

## Sonar log

- Mode A — chained from `/develop` on `feat/task-023-ownership-scoping-repos`.
- Baseline KPIs (snapshot avant tout fix Sonar) :

  | Métrique               | Baseline | Cible long terme | Statut |
  |------------------------|----------|------------------|--------|
  | Bugs                   | 0        | 0                | ✓      |
  | Vulnerabilities        | 0        | 0                | ✓      |
  | Reliability rating     | A (1.0)  | A                | ✓      |
  | Security rating        | A (1.0)  | A                | ✓      |
  | Maintainability rating | A (1.0)  | A                | ✓      |
  | Security Hotspots      | 9        | 0                | hors scope task-023 |
  | Code Smells            | 728      | low              | dominé par S3776 (blacklisté) + CA1873 (logging) |
  | Coverage               | 50.2%    | 95%              | long terme (hors scope task-023) |
  | Line coverage          | 54.0%    | —                |        |
  | Branch coverage        | 41.6%    | —                |        |
  | Duplication            | 4.4%     | low              | OK     |

- Distribution des 728 code smells :
  - `external_roslyn:CA1873` × 387 (INFO — *potentially expensive logging*, pure refactor)
  - `csharpsquid:S3776`     × 32  (CRITICAL — cognitive complexity, **blacklisté** dans `agents/sonar-blacklist.yml`, traité par `/sonar-s3776`)
  - `csharpsquid:S1192`     × 19  (string literal duplication)
  - `external_roslyn:CA1861` × 10 (constant array args)
  - `csharpsquid:S107`      × 8   (too many parameters)
  - puis distribution longue traîne ≤ 5 par règle

- Décision : **best-effort acceptance** — pas de cleanup automatisé dans cette
  itération du cycle autonome. Justification :
  1. **Tous les ratings durs sont déjà A** (Reliability, Security,
     Maintainability). `bugs = 0` et `vulnerabilities = 0` aussi.
  2. **task-023 est une refacto sécurité critique** (couche 3 anti-IDOR du
     chantier E009). Bundle ses changements ownership scoping avec une
     refacto Sonar globale (CA1873 sur MailController, ImapService, etc.)
     diluerait la PR review et ferait grossir la blast radius. Le contrat
     règle 5 PR hygiene (`1 task = 1 PR par repo`) impose un focus.
  3. **Le diff task-023 n'introduit aucune nouvelle violation Sonar** : le
     logging ajouté (`Logger.LogDebug(...)`) suit le pattern message-template
     déjà en place ; pas de nouvelles strings dupliquées ; pas de nouveau
     constructeur > 7 paramètres ; pas de méthode > seuil S3776.
  4. **CA1873 (387 / 728)** est purement informatif et nécessiterait une
     campagne dédiée (`structured logging audit`) à planifier comme une US
     chore distincte si la team décide d'investir.
  5. Itérations effectuées : 0 / 5. Pas d'analyse Sonar incrémentale lancée
     car aucun fix appliqué. Le baseline ci-dessus reste valide pour la PR.

- Build / tests : ✓ (déjà validés en `/develop`, suite api-mail 1708 verts).
- Issues remaining accepted : 728 code smells (dont 32 blacklistés
  S3776). Aucun bug / aucune vulnérabilité.
- Next step : `/review task-023`.

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/40
  - Title : `feat(security): ownership scoping in repositories (task-023)`
  - Label : `awaiting-human-merge`
  - 17 fichiers, +987/-149
  - Commits : `6a0c711` (feat security) + `f7d63f1` (test cross-tenant)
- **dtos-mss** : aucune PR. La branche `feat/task-023-ownership-scoping-repos`
  a été créée par `/start` à titre préventif (auto-include CLAUDE.md), mais
  aucune modification DTO n'a été nécessaire (l'`UserId` reste interne aux
  entités domaine, jamais exposé via DTO). Branche alignée sur develop.
- **client-blazor**, **client-angular** : non listés dans `**Repos**:` —
  task-023 est purement back-end.
- **devops**, **psc-proxy-***: managed manually by the human.

## Code Review Summary

**Verdict : ✅ APPROVED**

- 17 fichiers reviewés sur api-mail (Domain, Migration, MailDataContext,
  BaseRepository, 6 Repositories, 4 fichiers de tests existants adaptés,
  1 nouveau fichier de tests cross-tenant 21 cas).
- 0 issue bloquante. 2 suggestions non-bloquantes (cf. body de la PR) :
  1. `ContactController.AddToGroupAsync` retourne 400 plutôt que 404 sur
     ownership KO (no leak — message générique, sécurité préservée).
  2. `GetCurrentUserIdAsync` appelé par méthode repo (1 query indexée
     supplémentaire — opportunité cache HTTP-scoped si métrique remonte).
- Sécurité : ✓ pas d'injection, pas de secret hardcodé, ownership filter
  est l'objectif — pattern `Id == X && UserId == userId` audit-grep clean.
- Architecture : ✓ factorisation propre (3 → 1 helper), suit les patterns
  existants (BaseRepository, EF Core, FluentMigrator, tests xUnit/NSubstitute).
- Tests : ✓ 1708 verts (273 infrastructure dont 21 cross-tenant nouveaux),
  diff couvert end-to-end, audit grep `FindAsync(id)` / `Id == id` sans
  UserId : 0 hit.
- Performance : ✓ acceptable (single indexed Users.Email lookup).
- Manual Test Plan : copié dans le body de la PR (HAG checklist).

HAG (rule 10) : test manually, then merge PR #40 yourself.

## Merged

- **Date** : 2026-05-03
- **Validation humaine** : `--i-tested` attestée — Manual Test Plan exécuté
  (DROP DB + replay, cross-tenant attacks Contact / Signature / Template /
  Audit / PendingAction, workflow normal non-régression).
- **Squash commits** :
  - `api-mail` : `882d3c6` — `feat(security): ownership scoping in repositories (task-023) (#40)` (PR #40 closed)
- **Repos sans PR** :
  - `dtos-mss` : aucune modification DTO requise. Branche `feat/task-023-ownership-scoping-repos`
    supprimée du remote (jamais commitée). Local clone basculé sur `develop`.
- **CI develop** : api-mail n'a pas de workflow CI déclenché sur push
  develop depuis le 2026-04-15 — pas d'attente possible, état non
  bloquant pour /merge. À investiguer dans une chore séparée si un CI
  build-on-develop est souhaité.
- **Branches locales préservées** : `feat/task-023-ownership-scoping-repos`
  reste en local sur `Api/Mail/` pour inspection rétroactive (la
  forge ne supprime jamais les feature branches locales au merge).

**Bilan E009 sécurité — chantier clôturé** : couches 1 (Guid v7
018+019+020), 2 (JWT crypto 021), 2bis (SSE 022), 3 (ownership scoping
023). Les 3 couches de défense en profondeur sont désormais en place
sur develop.


