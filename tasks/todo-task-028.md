# todo-task-028.md — Workflow d'acquittement bio anormale

**Repos**: api-mail, dtos-mss, client-blazor, client-angular
**Dependencies**: archived-task-004, archived-task-011
**Epic**: E009

## Objectif

Ajouter un **workflow structuré d'acquittement** quand un mail MSS porte
au moins un compte-rendu de biologie avec une valeur anormale (`IsFlagged`
posé par `CdaParsingService` sur tout `InterpretationCode` ∈
`{L, H, A, LL, HH, AA}`). Le médecin doit pouvoir, en 1 clic, déclarer
**l'action qu'il a entreprise** : pris connaissance / rappelé le patient /
convoqué / adressé à un confrère. Chaque action génère une trace audit
horodatée portant l'identité du médecin, le `DocumentId` du CDA concerné
et l'action choisie.

L'objectif n'est pas réglementaire (la table E009 §10.x ne mentionne pas
encore d'exigence d'acquittement — RG-E009-051/052 couvrent uniquement
détection + affichage) mais **médico-légal** : aujourd'hui rien dans le
système ne prouve que le médecin a vu une valeur critique. Une bio
anormale non-ackée reste visuellement persistante tant qu'aucune action
n'a été posée — le médecin ne peut pas « louper » la valeur silencieusement.

## Contexte — l'existant à réutiliser

| Pièce | Localisation | Réutilisation |
|---|---|---|
| Détection `IsFlagged` (HL7) | `Api/Mail/src/Application/Services/Implementation/CdaParsingService.cs` (≈ ligne 192) | Pas de changement — déjà en place |
| Distinction critical / warning | `AbnormalBiologyValueDto.IsCritical` (helper sur codes `LL/HH/AA`) | Réutilisé pour la couleur du badge persistant |
| Widget « biologie anormale » F004 | `Client/Blazor/Src/Modules/Mss/Plugin/AbnormalBiologyWidgetComponent.razor` + Angular `ui/abnormal-biology-widget/` | Pas modifié dans cette US — focus sur le viewer mail |
| Audit framework task-004 | `Api/Mail/src/Domain/Entities/MssAuditTrace.cs` + `Dtos/AuditActionType.cs` (19 types existants) | Étendu de 4 nouveaux types |
| PendingAction queue offline | `Dtos/PendingActionTypes.cs` (6 types existants) | Étendu de 4 nouveaux types |
| Pattern aggregate inbox-row | `MailDto.PendingIntegrationsCount` (task-011) — calculé serveur-side, surface inbox sans charger le contenu | Pattern strictement copié pour `HasAbnormalBiology` + `AbnormalBiologyCount` |

## Comportement attendu

### Granularité — 1 ack par CDA, pas par mail

Un mail IHE_XDM peut porter plusieurs `MailMedicalDocument`. Chaque CDA
qui contient au moins une valeur `IsFlagged` est **éligible** à
l'acquittement. L'ack est posé **par-CDA**, jamais par-mail. Si un mail
porte 3 CDA dont 2 avec bio anormale, le médecin pose 2 acks distincts.

### 4 actions exposées (enum partagée)

`BiologyAckActionType` (nouvel enum dans `Dtos/`) :
- `Acknowledged` (« J'ai pris connaissance »)
- `PatientCalled` (« Je rappelle le patient » — déclaratif, pas
  d'intégration téléphonie ni SMS)
- `PatientSummoned` (« Je convoque le patient »)
- `ReferredToColleague` (« J'adresse à un confrère »)

Aucune des 4 actions ne déclenche d'envoi automatique vers le patient
(pas de SMS, pas de mail auto, pas de notification MES). Pure trace
déclarative.

### Affichage des boutons

Sous le viewer mail (Blazor `MailDetailComponent`, Angular `mail-detail`)
**dès qu'au moins un CDA du mail porte `IsFlagged == true`** (critical
ou warning indifférement — la sévérité drive la couleur du badge mais
**pas** la disponibilité des boutons), un panneau d'actions par-CDA
s'affiche.

Si plusieurs CDA flaggés cohabitent dans le mail :
- En Blazor : un panneau par CDA, en pied de chaque section CDA dans
  le viewer (ou dans l'onglet Biologie)
- En Angular : idem, panneau par CDA

Chaque panneau présente les 4 boutons + la **dernière action posée**
(si déjà ackée) :

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Bio anormale — Compte-rendu du 03/05/2026               │
│                                                             │
│  Dernière action : « Je rappelle le patient »              │
│  par Dr Dupont, le 03/05/2026 à 14:32                     │
│                                                             │
│  [ Pris connaissance ] [ Rappel patient ] [ Convocation ]  │
│  [ Adressage confrère ]                                    │
└─────────────────────────────────────────────────────────────┘
```

### Réversibilité — non-réversible, mais rectifiable

Aucun bouton « annuler ». Une fois une action posée, elle est dans
l'audit pour toujours.

Le médecin peut **poser une action complémentaire** (par ex. d'abord
« pris connaissance » à 14:00, puis « convoque » à 14:15 après
réflexion). Chaque clic = un nouvel audit entry. L'UI affiche
**uniquement la dernière action** comme état courant, mais l'historique
complet est conservé en BDD.

L'UI n'expose pas l'historique complet en v1 (gardé en audit, accessible
via `/audit-trail` si besoin). Follow-up possible : affichage timeline
des actions posées sur ce CDA si le PO le demande.

### Persistance et badge inbox

Tant qu'**au moins un CDA flaggé du mail n'a aucune action posée**, le
mail garde un badge persistant sur la ligne inbox :

- **Couleur rouge** si au moins un CDA non-acké contient une valeur
  critique (`LL/HH/AA`)
- **Couleur orange** sinon (que des `L/H/A`)

Une fois que **tous les CDA flaggés du mail ont au moins une action
posée**, le badge disparaît. Le bouton du dernier ack reste visible
dans le viewer.

### Aggregates serveur-side

Pour éviter de charger le contenu CDA complet quand l'inbox calcule
ses badges, le backend ajoute deux nouveaux champs sur `MailDto` :

- `MailDto.HasAbnormalBiology : bool` — vrai si au moins un CDA du
  mail a au moins une valeur `IsFlagged`
- `MailDto.PendingBiologyAcksCount : int` — nombre de CDA flaggés
  du mail qui n'ont **aucune** action posée par l'utilisateur courant

Le badge inbox lit ces deux champs (pas le contenu).

### Audit trace — 4 nouveaux `AuditActionType`

- `BiologyAcknowledged`
- `BiologyPatientCalled`
- `BiologyPatientSummoned`
- `BiologyReferredToColleague`

Chaque action enregistre un `MssAuditTrace` avec les champs habituels
(task-004) **plus** :
- `DocumentId` (FK CDA)
- `DocumentLoinc` (code LOINC du compte-rendu)
- `PatientIns` (matricule INS du patient)
- `PatientName` (nom + prénom du patient — si dispo via le CDA)

### Note libre optionnelle

Chaque action peut porter une **note libre** courte (max 500 chars), par
ex. « Patient injoignable, laissé message » sur `PatientCalled`. Stockée
sur l'audit trace dans un champ existant `Note` (à vérifier) ou nouveau
`AckNote`. Optionnel — pas bloquant si absent.

### Mode offline (PendingAction)

Les 4 actions sont enqueable comme `PendingAction` quand le médecin est
hors ligne (parité avec `MarkRead`/`MarkFlagged`). 4 nouveaux
`PendingActionType` :
- `BiologyAckAcknowledged`
- `BiologyAckPatientCalled`
- `BiologyAckPatientSummoned`
- `BiologyAckReferredToColleague`

Le payload de la pending action porte `DocumentId` + éventuelle note +
horodatage local du clic. Au reconnect, `PendingActionService` rejoue
l'appel à l'endpoint, l'audit trace porte le timestamp client-side
(le serveur stocke aussi son `ServerReceivedAt`).

## Périmètre détaillé

### `dtos-mss`

- **Nouvel enum** `BiologyAckActionType` (4 valeurs ci-dessus)
- **Nouveau DTO** `BiologyAckDto` :
  ```csharp
  public class BiologyAckDto
  {
      public Guid Id { get; init; }                    // PK Guid v7
      public Guid MedicalDocumentId { get; init; }     // FK CDA
      public BiologyAckActionType Action { get; init; }
      public string? Note { get; init; }
      public DateTime CreatedAt { get; init; }
      public string CreatedByUserEmail { get; init; }  // identifiant médecin
      public string? CreatedByUserName { get; init; }  // nom médecin pour affichage
  }
  ```
- **Nouveau record** `BiologyAckRequestDto` (input endpoint) :
  ```csharp
  public record BiologyAckRequestDto(BiologyAckActionType Action, string? Note);
  ```
- **Champ ajouté** sur `MailDto` :
  - `HasAbnormalBiology : bool` (server-managed)
  - `PendingBiologyAcksCount : int` (server-managed)
- **Champ ajouté** sur `MailMedicalDocumentDto` :
  - `LastBiologyAck : BiologyAckDto?` — denormalized last ack pour
    affichage rapide ; null tant qu'aucune action posée
- **2 nouveaux** `AuditActionType` enum members + **4 nouveaux**
  `PendingActionType` enum members (cf. plus haut)
- **NuGet bump** automatique via `/develop` (selon convention task-018+)

### `api-mail`

#### Migration BDD

Nouvelle migration `20260504_AddBiologyAcks.cs` (FluentMigrator) :

```sql
CREATE TABLE BiologyAcks (
  Id            UUID PRIMARY KEY,                 -- Guid v7 via UuidV7ValueGenerator
  UserId        UUID NOT NULL REFERENCES Users(Id),
  MedicalDocumentId UUID NOT NULL REFERENCES MailMedicalDocuments(Id) ON DELETE CASCADE,
  Action        INT NOT NULL,                     -- BiologyAckActionType enum int
  Note          VARCHAR(500) NULL,
  CreatedAt     TIMESTAMP WITH TIME ZONE NOT NULL,
  CreatedByUserEmail VARCHAR(255) NOT NULL,
  CreatedByUserName  VARCHAR(255) NULL,

  CONSTRAINT IX_BiologyAcks_DocumentId_CreatedAt
    INDEX (MedicalDocumentId, CreatedAt DESC)     -- pour fetcher le dernier ack rapidement
);
CREATE INDEX IX_BiologyAcks_UserId ON BiologyAcks(UserId);
```

- Pas d'unique constraint `(MedicalDocumentId, UserId)` — le même
  médecin peut poser plusieurs actions complémentaires sur le même CDA
- `OnDelete CASCADE` du CDA — si le mail est supprimé, l'historique
  d'ack est purgé. Cohérent avec la rétention.
- `UserId` cumulatif (convention task-023 — single source of ownership
  sur les tables métier per-user).

#### Entité Domain

`Mail/src/Domain/Entities/BiologyAck.cs` — entité simple, FK
`MailMedicalDocument`, propriétés alignées sur le DTO.

#### Repository + Service

- `IBiologyAckRepository` :
  - `Task<Guid> AddAsync(BiologyAck entity)`
  - `Task<BiologyAck?> GetLastAckAsync(Guid documentId)` (le plus
    récent, scoped UserId)
  - `Task<int> CountPendingAcksForMailAsync(Guid mailId)` (count des
    `MailMedicalDocument` du mail dont `IsFlagged ∧ aucun ack`)
- `IBiologyAckService` (Application) :
  - `Task<BiologyAckDto> RecordAckAsync(Guid documentId, BiologyAckRequestDto req, ClaimsPrincipal user)`
  - Vérifie que le CDA appartient au tenant (via repository ownership
    scoping task-023, cumulatif sur UserId)
  - Vérifie que le CDA porte au moins une valeur `IsFlagged` (refus
    400 si pas de bio anormale — pas de pollution audit)
  - Crée l'entité, persiste, retourne le DTO
  - Émet l'audit trace via `IAuditService` avec le bon
    `AuditActionType` selon l'action choisie

#### Endpoint

`POST /api/v1/medical-documents/{documentId:guid}/biology-ack`
- Body : `BiologyAckRequestDto`
- Auth : JWT obligatoire (FallbackPolicy task-021)
- Réponses :
  - `200 OK` + `BiologyAckDto` au succès
  - `400 BadRequest` si le CDA ne porte pas de bio anormale (pas
    `IsFlagged`)
  - `404 NotFound` si le CDA n'existe pas / ne tenant pas (silent
    leak per task-023 convention)
  - `401` si non authentifié

#### Aggregates `MailDto`

`MailRepository` étendu pour calculer :
- `HasAbnormalBiology` : `EXISTS(SELECT 1 FROM MailMedicalDocumentBiologies WHERE MailMedicalDocumentId IN (...) AND IsFlagged = true)`
- `PendingBiologyAcksCount` : count des `MailMedicalDocument` du mail
  qui ont au moins une bio flaggée ET aucun `BiologyAck` posé
  par le user courant

Le calcul se fait en 1 query SQL agrégée (pas N+1).

#### Tests

- ≥ 8 unit tests `BiologyAckServiceTests` :
  - 4 happy paths (1 par action)
  - 1 idempotency-revisit (poser 2 actions différentes sur le même
    CDA → 2 entries en BDD, dernier ack reflète la 2e)
  - 1 reject sur CDA sans bio flaggée (400)
  - 1 reject sur CDA inexistant (404)
  - 1 cross-tenant rejected (User A ne peut pas acker un CDA de User B)
- ≥ 3 integration tests Postgres-backed :
  - Round-trip insertion + read `GetLastAckAsync`
  - `CountPendingAcksForMailAsync` cohérent (mail avec 3 CDA dont 2
    flaggés dont 1 acké → returns 1)
  - `MailRepository` retourne `HasAbnormalBiology` + count corrects
- 4 nouveaux tests audit trace (1 par action)

### `client-blazor`

#### Composant `BiologyAckPanelComponent.razor` (nouveau)

Sous le viewer mail (`MailDetailComponent`), **dans l'onglet ou la
section Biologie déjà existant** (à confirmer pendant l'implé), un
panneau par CDA flaggé :

- 4 boutons (Radzen ou design-system existant)
- Header : titre du CDA + date
- Affichage du dernier ack si présent (via `mail.medicalDocuments[i].lastBiologyAck`)
- Au clic d'un bouton : appel `IBiologyAckService.RecordAckAsync(documentId, action)`,
  optimistic update du `lastBiologyAck` local, toast succès
- Sur erreur API : revert + toast erreur

#### Service Blazor

`IBiologyAckService` (côté client) avec 1 méthode `RecordAckAsync` qui
wrap l'appel HTTP.

#### Badge inbox

Sur `MailHeader.razor` (liste inbox), nouveau badge :
- Lecture `mail.HasAbnormalBiology && mail.PendingBiologyAcksCount > 0`
- Couleur rouge si au moins un CDA non-acké du mail porte critical
  (le client doit savoir cette info — soit on enrichit `MailDto` d'un
  bool `HasPendingCriticalBiologyAck`, soit on fait un `min` sur les
  CDA chargés en mode détail. Pour l'inbox, simplifier : si
  `PendingBiologyAcksCount > 0` ET un des CDA chargés est critical,
  rouge ; sinon orange. À discuter avec le PO si ambigu).
- Disparition du badge dès que `PendingBiologyAcksCount == 0`

> **Note d'implémentation** : pour éviter d'ajouter un 3e champ sur
> `MailDto`, simplifier en couleur unique (rouge si pending, neutre
> sinon) en v1. La distinction rouge/orange peut être un follow-up.

#### Localizer

Nouvelles clés FR + EN :
- `BiologyAckPanelTitle` (« Bio anormale — {0} »)
- `BiologyAckActionAcknowledged` (« Pris connaissance »)
- `BiologyAckActionPatientCalled` (« Rappel patient »)
- `BiologyAckActionPatientSummoned` (« Convocation »)
- `BiologyAckActionReferredToColleague` (« Adressage confrère »)
- `BiologyAckLastAction` (« Dernière action : {0} par {1} le {2} »)
- `BiologyAckSuccess` / `BiologyAckError`
- `BiologyAckBadgePending` (« Bio anormale à acquitter »)

#### Tests bUnit

≥ 4 tests `BiologyAckPanelTests.cs` :
- Render des 4 boutons quand bio flaggée présente
- Pas de panneau quand `IsFlagged == false`
- Affichage du dernier ack quand `lastBiologyAck != null`
- Clic d'un bouton appelle le service et update optimistic

### `client-angular` (mode code-only)

Symétrique à Blazor :

- Nouveau composant standalone `BiologyAckPanelComponent` dans
  `front/libs/mss/src/features/mail/components/biology-ack-panel/`
  - Signal-first, OnPush, JSDoc
  - Inputs : `medicalDocument`, `mailUid`
  - Output : `(ackPosted)` pour propager au parent
- Service `MssApiService.recordBiologyAck(documentId, request)` ajouté
- État local : `signal<BiologyAckDto | null>` pour le dernier ack,
  bumpé optimisticly au clic
- Badge inbox sur `mail-header` côté Angular avec lecture des champs
  agrégés
- Tests Vitest ≥ 4 sur le composant + 2 sur le service

### Pas de modification

- Widget « Biologie anormale » F004 (`AbnormalBiologyWidget*`) reste
  inchangé en v1. Follow-up possible si le PO veut intégrer les acks
  dans le widget (filtrer les patients dont la bio a déjà été ackée).
- TODO `notifications-abnormal-biology-043` (SSE pipe) **non wirée** —
  scope creep évité, task séparée si demandé.

## Convention scellée

- **Granularité** : 1 ack = 1 action sur 1 CDA. Pas par-mail, pas par-valeur.
- **Sévérité** : drive la couleur du badge **mais pas la disponibilité**
  des boutons. Toute bio `IsFlagged` ouvre les 4 boutons.
- **Réversibilité** : non. Une fois posée, l'action est dans l'audit
  forever. Le médecin peut poser une action complémentaire (= nouvel
  audit entry, jamais d'écrasement).
- **Notification patient** : aucune. Les 4 actions sont **purement
  déclaratives**, audit-only. Pour écrire au patient, le médecin
  utilise Compose comme aujourd'hui.
- **Délégation** : pas applicable v1 (pas de modèle de délégation
  dans le système).
- **Audit médico-légal** : chaque action porte `DocumentId`, `DocumentLoinc`,
  `PatientIns`, `PatientName`, identité médecin, timestamp serveur.

## Definition of Done

### Build + tests
- [ ] `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreurs
- [ ] `dotnet test HealthPlatform.Api.Mail.sln` → 0 failures, **+8 unit
  tests min sur `BiologyAckServiceTests`**, **+3 integration tests min
  sur `BiologyAckRepositoryTests` Postgres-backed**, **+4 audit trace
  tests min**
- [ ] `dotnet build HealthPlatform.Client.sln` → 0 erreurs
- [ ] `dotnet test HealthPlatform.Client.sln` → 0 failures, **+4 bUnit
  tests min sur `BiologyAckPanelTests`**
- [ ] `cd Client/Angular/front && npm run build` → 0 erreurs
- [ ] `cd Client/Angular/front && npm test` → 0 failures, **+4 Vitest
  tests min sur `biology-ack-panel.component.spec.ts`** + **+2 sur
  `mss-api.service.spec.ts` méthode `recordBiologyAck`**

### Backend
- [ ] Enum `BiologyAckActionType` publié dans `dtos-mss` + NuGet bump
- [ ] DTOs `BiologyAckDto` + `BiologyAckRequestDto` publiés
- [ ] `MailDto.HasAbnormalBiology` + `MailDto.PendingBiologyAcksCount` calculés serveur-side, pas N+1
- [ ] `MailMedicalDocumentDto.LastBiologyAck` populé serveur-side
- [ ] Migration `BiologyAcks` table avec FK `Users` + FK `MailMedicalDocuments` + index `(DocumentId, CreatedAt DESC)`
- [ ] Endpoint `POST /api/v1/medical-documents/{id}/biology-ack` retourne 200/400/404 selon spec
- [ ] 4 nouveaux `AuditActionType` enum members + audit trace émise par chaque action avec `DocumentId` / `DocumentLoinc` / `PatientIns` / `PatientName`
- [ ] 4 nouveaux `PendingActionType` enum members + payload + replay logic dans `PendingActionService`
- [ ] Cross-tenant ownership scoping vérifié (User A ne peut pas acker CDA User B → 404 silent leak per task-023)

### Frontend (les 2)
- [ ] Panneau `BiologyAckPanel` rendu quand `medicalDocument.biologyResults` contient au moins une valeur `IsFlagged`
- [ ] 4 boutons cliquables avec `data-testid` posés (`bio-ack-acknowledged`, `bio-ack-called`, `bio-ack-summoned`, `bio-ack-referred`)
- [ ] Affichage du `lastBiologyAck` (action + médecin + date) quand présent
- [ ] Badge inbox sur `mail-header` quand `HasAbnormalBiology && PendingBiologyAcksCount > 0` ; disparaît à `PendingBiologyAcksCount == 0` ; `data-testid="mail-row-pending-bio-ack"`
- [ ] Clic optimistic update + toast succès / revert sur erreur
- [ ] i18n FR + EN (Blazor Localizer + Angular i18n inline) pour toutes les clés listées
- [ ] Localizer parity FR/EN sur les 4 actions + tooltips

### Documents
- [ ] EPIC E009 doc enrichie via `/tech-writer E009` : nouvelle ligne dans la table §10.x ou §6.13 (à décider) « Workflow d'acquittement bio anormale » avec mention « non Ségur — driven médico-légal ; backend + 2 frontends + audit »

### Audit grep DOD
- [ ] `grep -rn "BiologyAckActionType" Api/Mail/src/` → matches dans Domain (entité), Application (service), Api (controller), Infrastructure (repository)
- [ ] `grep -rn "BiologyAck" Client/Blazor/Src/` → matches dans Plugin (composant + service + Localizer)
- [ ] `grep -rn "biologyAck\|BiologyAck" Client/Angular/front/libs/mss/src/` → matches dans `core/models`, `features/mail/services/mss-api.service.ts`, `features/mail/components/biology-ack-panel/`
- [ ] `grep -rn "HasAbnormalBiology\|PendingBiologyAcksCount" Api/Mail/src/Application` → matches dans le repository (calcul) + le mapper
- [ ] Nouveau enum members `BiologyAcknowledged|BiologyPatientCalled|BiologyPatientSummoned|BiologyReferredToColleague` présents dans `AuditActionType` ET `PendingActionType`

### Aucune régression
- [ ] Suite api-mail >= 1733 + nouveaux tests, 0 failed
- [ ] Suite client-blazor inchangée + nouveaux tests, 0 failed
- [ ] mss-lib Vitest 98/98 + nouveaux tests, 0 failed
- [ ] Pas de modification du `AbnormalBiologyWidget*` existant
- [ ] Pas de wiring du TODO `notifications-abnormal-biology-043`

## Manual Test Plan

### Setup
1. `cd Api/Mail/src/AppHost && dotnet run --launch-profile https`
2. `cd Client/Blazor/Src/Shell && dotnet run --launch-profile https_test`
3. `cd Client/Angular/front && npm start`
4. Loguer en tant que doctor avec une boîte qui contient au moins
   1 mail avec un CDA portant valeur(s) bio `IsFlagged` (utiliser
   un mail de test PSC ou injecter manuellement un CDA avec
   `InterpretationCode="HH"`).

### Vérification 1 — affichage du panneau
1. Sur Blazor + Angular successivement, ouvrir le mail.
2. **Vérifier** : un panneau `BiologyAckPanel` s'affiche dans la
   section Biologie / sous le viewer (selon implé), portant le titre
   du CDA + 4 boutons.
3. **Vérifier** : badge rouge ou orange visible sur la ligne inbox
   correspondante (selon sévérité).

### Vérification 2 — pose d'une action « Pris connaissance »
1. Cliquer le bouton « Pris connaissance ».
2. **Vérifier** : toast succès, puis le panneau affiche
   « Dernière action : Pris connaissance par Dr Dupont, le {date} ».
3. **Devtools réseau** : `POST /api/v1/medical-documents/{guid}/biology-ack`
   avec body `{ "action": "Acknowledged", "note": null }` → 200.
4. **Seq** : log `MssAuditTrace` émis avec
   `ActionType=BiologyAcknowledged`, `DocumentId=...`, `PatientIns=...`.
5. Retourner sur l'inbox : le badge a disparu (le seul CDA flaggé
   du mail est désormais acké).

### Vérification 3 — action complémentaire
1. Sur le même mail/CDA, cliquer « Convocation ».
2. **Vérifier** : toast succès. Le panneau affiche maintenant
   « Dernière action : Convocation par Dr Dupont, le {date+15min} ».
   L'historique précédent (« Pris connaissance ») n'est plus dans
   le panneau **mais reste dans l'audit**.
3. **DB** : `SELECT * FROM BiologyAcks WHERE MedicalDocumentId = ...`
   retourne **2 rows** (Acknowledged + PatientSummoned), ordonnées
   par `CreatedAt`.

### Vérification 4 — mail avec 2 CDA, 1 acké
1. Trouver / construire un mail avec 2 CDA flaggés.
2. Acker uniquement le 1er.
3. **Vérifier** : badge inbox toujours présent (le 2e CDA n'a aucun ack).
4. Acker le 2e.
5. **Vérifier** : badge inbox a disparu.

### Vérification 5 — refus sur CDA sans bio flaggée
1. Tenter via Postman : `POST /api/v1/medical-documents/{guid-d-un-CDA-sans-bio-anormale}/biology-ack`
   `{ "action": "Acknowledged" }`.
2. **Vérifier** : 400 BadRequest avec message explicite.

### Vérification 6 — refus cross-tenant
1. Loguer User A, noter le DocumentId d'un CDA de sa boîte.
2. Loguer User B (autre médecin).
3. Tenter via Postman : `POST /api/v1/medical-documents/{guid-A}/biology-ack`
   avec session User B.
4. **Vérifier** : 404 NotFound (silent leak per task-023, pas 403).

### Vérification 7 — mode offline (PendingAction)
1. Couper le réseau (devtools offline).
2. Cliquer une action.
3. **Vérifier** : le panneau affiche optimisticly l'action posée.
   Pas de toast d'erreur (PendingAction queue silently).
4. Reconnecter.
5. **Vérifier** : `PendingActionService` rejoue, l'audit trace est
   bien émise serveur-side, `lastBiologyAck` réfléchit le state.

### Vérification 8 — non-régression widget F004
1. Aller sur le dashboard / widget « Biologie anormale » (F004).
2. **Vérifier** : comportement strictement inchangé. Aucune nouvelle
   notion d'ack sur le widget. Les patients listés ne tiennent pas
   compte des acks posés (gardé pour follow-up).

## Limites et follow-ups

- **Pas de filtrage inbox « bio anormale non-ackée »** dans cette US.
  Les chips rapides sont l'axe 11 du brainstorm — task séparée.
- **Pas d'affichage timeline d'historique** des acks posés sur un CDA
  (gardé en audit accessible via `/audit-trail`). Follow-up si demandé.
- **Pas de wiring SSE notif** abnormal biology (TODO
  `notifications-abnormal-biology-043` reste ouvert) — task séparée.
- **Pas d'intégration au widget F004** (`AbnormalBiologyWidget*`).
  Follow-up : filtrer les patients dont la bio a déjà été ackée pour
  réduire la pollution du widget.
- **Pas de notification patient** quelle que soit l'action.
- **Pas de délégation / multi-médecin** — chaque user gère ses acks
  séparément (cohérent avec le multi-tenant single-user actuel).
- **Pas d'unique constraint** `(DocumentId, UserId)` — convention
  d'actions complémentaires en série.

## References

- `Api/Mail/src/Application/Services/Implementation/CdaParsingService.cs`
  (≈ ligne 192) — détection `IsFlagged`
- `Dtos/AbnormalBiologyValueDto.cs` — distinction `IsCritical`
- `Api/Mail/src/Domain/Entities/MssAuditTrace.cs` + `Dtos/AuditActionType.cs`
  — framework audit task-004
- `Dtos/PendingActionTypes.cs` — pattern offline queue
- `Api/Mail/src/Application/Services/NewMailNotifier.cs:35` — TODO
  `notifications-abnormal-biology-043` (intentionnellement non wiré)
- archived-task-011 — pattern `PendingIntegrationsCount` agrégé serveur-side
- archived-task-004 — framework audit MSS
- archived-task-023 — convention ownership scoping cumulatif `UserId`
- EPIC E009 §6.13 (RG-E009-051/052) — détection / affichage bio
  anormale (acquittement non couvert par ces règles)
