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
