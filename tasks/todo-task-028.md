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
convoqué / adressé à un confrère, puis explicitement **clôturer le cas**
via une action de résolution distincte. Chaque action génère une trace
audit horodatée portant l'identité du médecin, le `DocumentId` du CDA
concerné et l'action choisie.

L'objectif n'est pas réglementaire (la table E009 §10.x ne mentionne pas
encore d'exigence d'acquittement — RG-E009-051/052 couvrent uniquement
détection + affichage) mais **médico-légal** : aujourd'hui rien dans le
système ne prouve qu'un médecin identifié a effectivement pris en charge
une anomalie biologique. Un mail MSS peut être lu par une secrétaire ou
un assistant administratif sans qu'un médecin n'ait réellement vu les
données cliniques critiques ; le mécanisme d'ack lève cette ambiguïté en
exigeant un clic explicite signé par le user JWT authentifié (avec rôle
`Doctor` requis côté backend).

Le workflow introduit un **état de résolution clinique** : tant qu'une
action `MarkResolved` n'est pas posée, le CDA reste visible (badge inbox,
panneau viewer, tuile dashboard) — le médecin doit consciemment clôturer
le cas. Une **tuile KPI sur le dashboard** surface le volume de CDA en
attente de résolution, et un **filtre chip "bio non-résolue"** dans
l'inbox permet d'accéder rapidement à la liste.

## Contexte — l'existant à réutiliser

| Pièce | Localisation | Réutilisation |
|---|---|---|
| Détection `IsFlagged` (HL7) | `Api/Mail/src/Application/Services/Implementation/CdaParsingService.cs` (≈ ligne 192) | Pas de changement — déjà en place |
| Distinction critical / warning | `AbnormalBiologyValueDto.IsCritical` (helper sur codes `LL/HH/AA`) | Réutilisé pour la couleur du badge persistant + déclenche la modal de confirmation |
| Widget « biologie anormale » F004 | `Client/Blazor/Src/Modules/Mss/Plugin/Widgets/AbnormalBiologyWidgetComponent.razor` + Angular `ui/abnormal-biology-widget/` | **Inchangé** dans cette US — la nouvelle tuile KPI est un composant séparé sur le dashboard |
| Audit framework task-004 | `Api/Mail/src/Domain/Entities/MssAuditTrace.cs` + `Dtos/AuditActionType.cs` (19 types existants) | Étendu de 5 nouveaux types |
| PendingAction queue offline | `Dtos/PendingActionTypes.cs` (6 types existants) | Étendu de 5 nouveaux types |
| Pattern aggregate inbox-row | `MailDto.PendingIntegrationsCount` (task-011) — calculé serveur-side, surface inbox sans charger le contenu | Pattern strictement copié pour `HasAbnormalBiology` + `PendingBiologyAcksCount` |
| Filtres chips inbox | Mécanique chips existante de la barre filtres inbox (Blazor + Angular) | Étendue d'un nouveau chip `bio-non-resolved` |

## Comportement attendu

### Granularité — 1 ack par CDA, pas par mail

Un mail IHE_XDM peut porter plusieurs `MailMedicalDocument`. Chaque CDA
qui contient au moins une valeur `IsFlagged` est **éligible** à
l'acquittement. L'ack est posé **par-CDA**, jamais par-mail. Si un mail
porte 3 CDA dont 2 avec bio anormale, le médecin pose 2 résolutions
distinctes (et autant d'actions de prise en charge intermédiaires que
nécessaire).

### 5 actions exposées (enum partagée)

`BiologyAckActionType` (nouvel enum dans `Dtos/`) :

**4 actions de prise en charge (déclaratives, non clôturantes)** :
- `Acknowledged` (« J'ai pris connaissance »)
- `PatientCalled` (« J'ai rappelé le patient » — déclaratif, pas
  d'intégration téléphonie ni SMS)
- `PatientSummoned` (« Je convoque le patient »)
- `ReferredToColleague` (« J'adresse à un confrère »)

**1 action de clôture (résolutoire)** :
- `MarkResolved` (« Marquer comme résolu » — clôture explicite du cas
  clinique. Le médecin déclare avoir fini la prise en charge OU que le
  cas n'est pas actionnable (drift connu, patient sous traitement). Une
  note libre est recommandée pour ce dernier usage.)

Aucune des 5 actions ne déclenche d'envoi automatique vers le patient
(pas de SMS, pas de mail auto, pas de notification MES). Pure trace
déclarative.

### Workflow d'état dérivé (Pending / InProgress / Resolved)

L'état de résolution clinique d'un CDA flaggé est **calculé** à la lecture
(pas stocké comme état mutable) :

| État | Critère |
|---|---|
| `Pending` | Aucun ack posé par le user courant sur ce CDA |
| `InProgress` | ≥ 1 ack posé, mais aucun `MarkResolved` |
| `Resolved` | Au moins un `MarkResolved` posé (le plus récent) |

Cet état n'est pas un champ de l'entité — c'est une vue calculée par le
repository. Pas de migration d'état stocké, pas de mutation. Append-only
préservé.

### Affichage des boutons

Sous le viewer mail (Blazor `MailDetailComponent`, Angular `mail-detail`)
**dès qu'au moins un CDA du mail porte `IsFlagged == true`** (critical
ou warning indifféremment — la sévérité drive la couleur du badge ET la
friction UX sur les boutons, mais **pas** la disponibilité), un panneau
d'actions par CDA s'affiche.

Si plusieurs CDA flaggés cohabitent dans le mail :
- En Blazor : un panneau par CDA, en pied de chaque section CDA dans
  le viewer (ou dans l'onglet Biologie)
- En Angular : idem, panneau par CDA

Chaque panneau présente les 4 boutons de prise en charge, **plus** le
bouton `MarkResolved` visuellement distinct (séparateur + style "primary
confirm"), plus la **dernière action posée** (si déjà ackée) :

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Bio anormale — Compte-rendu du 03/05/2026               │
│                                                             │
│  Dernière action : « J'ai rappelé le patient »             │
│  par Dr Dupont, le 03/05/2026 à 14:32                     │
│                                                             │
│  [ Pris connaissance ] [ Rappel patient ] [ Convocation ]  │
│  [ Adressage confrère ]                                    │
│  ─────────────────────────────────────────────────────     │
│  [ ✓ Marquer comme résolu ]                                │
└─────────────────────────────────────────────────────────────┘
```

### Friction supplémentaire pour les valeurs critiques

Quand le CDA contient au moins une valeur `IsCritical` (codes `LL/HH/AA`),
**chaque clic sur l'un des 5 boutons** ouvre une modal de confirmation
qui :
- Affiche le code LOINC du compte-rendu
- Liste les valeurs critiques avec valeur + unité + intervalle de
  référence (par ex. « Potassium = 2.1 mmol/L — réf. 3.5-5.0 »)
- Confirme l'action choisie en clair
- Exige un clic explicite `[ Confirmer ]` pour persister, sinon `[ Annuler ]`

Pour les CDA non-critical (uniquement `L/H/A`), pas de modal — clic direct
sur le bouton enregistre l'action.

**Médico-légal** : la modal prouve que le médecin a vu la valeur précise,
pas juste « un truc anormal ». Capture screenshot-friendly pour litige.

### Réversibilité — non-réversible, mais rectifiable

Aucun bouton « annuler ». Une fois une action posée, elle est dans
l'audit pour toujours.

Le médecin peut **poser une action complémentaire** (par ex. d'abord
« pris connaissance » à 14:00, puis « convoque » à 14:15 après
réflexion, puis « marquer comme résolu » à 16:00). Chaque clic = un
nouvel audit entry. L'UI affiche **uniquement la dernière action** comme
état courant, mais l'historique complet est conservé en BDD.

Le `MarkResolved` lui-même peut être suivi d'autres actions (par ex.
le médecin marque résolu trop vite, puis pose un `PatientCalled`
complémentaire). Dans ce cas l'état dérivé du CDA reste `Resolved`
tant que **le dernier `MarkResolved` est postérieur à la dernière
action non-résolutoire** — sinon repasse à `InProgress`.

L'UI n'expose pas l'historique complet en v1 (gardé en audit, accessible
via `/audit-trail` si besoin). Follow-up possible : affichage timeline
des actions posées sur ce CDA si le PO le demande.

### Persistance et badge inbox — 3 états

Le badge sur la ligne inbox reflète l'état agrégé des CDA flaggés du mail :

| État badge | Condition |
|---|---|
| **Rouge** | Au moins un CDA flaggé `IsCritical` n'est pas `Resolved` |
| **Orange** | Au moins un CDA flaggé (warning uniquement) n'est pas `Resolved` |
| **Invisible** | Tous les CDA flaggés du mail sont `Resolved` |

La transition est driven par `MarkResolved` uniquement. Un clic
`Acknowledged` seul ne fait **pas** disparaître le badge (changement
par rapport à la v0 de la spec — décision PO : éviter qu'un médecin
ferme accidentellement un cas).

Le panneau d'actions reste visible dans le viewer même après
`MarkResolved` — le médecin peut toujours poser une action complémentaire
si la situation évolue.

### Aggregates serveur-side

Pour éviter de charger le contenu CDA complet quand l'inbox calcule
ses badges, le backend ajoute des champs sur `MailDto` :

- `MailDto.HasAbnormalBiology : bool` — vrai si au moins un CDA du
  mail a au moins une valeur `IsFlagged`
- `MailDto.PendingBiologyAcksCount : int` — nombre de CDA flaggés
  du mail qui ne sont **pas** `Resolved` pour le user courant
- `MailDto.HasCriticalPendingBiologyAck : bool` — vrai si au moins un
  CDA flaggé `IsCritical` n'est pas `Resolved` (drive la couleur rouge
  du badge inbox sans charger le contenu)

Et sur `MailMedicalDocumentDto` :
- `LastBiologyAck : BiologyAckDto?` — denormalized last ack pour
  affichage rapide ; null tant qu'aucune action posée
- `BiologyAckState : BiologyAckResolutionState` — vue calculée
  (`Pending` / `InProgress` / `Resolved`) pour le composant panel

Le calcul se fait en 1 query SQL agrégée par mail (pas N+1).

### Audit trace — 5 nouveaux `AuditActionType`

- `BiologyAcknowledged`
- `BiologyPatientCalled`
- `BiologyPatientSummoned`
- `BiologyReferredToColleague`
- `BiologyMarkedResolved`

Chaque action enregistre un `MssAuditTrace` avec les champs habituels
(task-004) **plus** :
- `DocumentId` (FK CDA)
- `DocumentLoinc` (code LOINC du compte-rendu)
- `PatientIns` (matricule INS du patient — snapshot au moment de l'ack,
  conservé même si l'INS est corrigé ultérieurement)
- `PatientName` (nom + prénom du patient — snapshot, si dispo via le CDA)

### Note libre optionnelle

Chaque action peut porter une **note libre** courte (max 500 chars), par
ex. « Patient injoignable, laissé message » sur `PatientCalled`, ou
« Drift connu, patient sous diurétique » sur `MarkResolved`. Stockée
sur l'**entité `BiologyAck`** (colonne `Note VARCHAR(500) NULL` —
voir migration ci-dessous), **pas** sur l'audit trace. L'audit trace
porte le `BiologyAck.Id` en référence ; la note est consultable via
l'entité.

Optionnelle pour les 5 actions. Pas de validation de longueur minimale.

### Mode offline (PendingAction)

Les 5 actions sont enqueable comme `PendingAction` quand le médecin est
hors ligne (parité avec `MarkRead`/`MarkFlagged`). 5 nouveaux
`PendingActionType` :
- `BiologyAckAcknowledged`
- `BiologyAckPatientCalled`
- `BiologyAckPatientSummoned`
- `BiologyAckReferredToColleague`
- `BiologyAckMarkResolved`

Le payload de la pending action porte `DocumentId` + éventuelle note +
horodatage local du clic. Au reconnect, `PendingActionService` rejoue
l'appel à l'endpoint, l'audit trace porte le timestamp client-side
(le serveur stocke aussi son `ServerReceivedAt`).

## Widget KPI Dashboard — nouvelle tuile

### Composant `BiologyAckPendingKpiTile` (Blazor + Angular)

Tuile compacte sur le dashboard, distincte du widget F004 existant
(qui reste inchangé) :

```
╔══════════════════════════════════╗
║  ⚠️  Bio en attente d'ack       ║
║                                  ║
║       🔴 2 critical              ║
║       🟠 3 warning               ║
║                                  ║
║       [ Voir l'inbox → ]         ║
╚══════════════════════════════════╝
```

- Si `criticalPending > 0` → bordure rouge + icône ⚠️ rouge
- Sinon si `warningPending > 0` → bordure orange
- Sinon → état "vide" stylé sobre (« Aucune bio en attente d'acquittement »)
- Clic sur la tuile ou sur `[ Voir l'inbox → ]` → navigation vers
  l'inbox avec le filtre `bio-non-resolved` pré-appliqué (cf. section
  suivante)

### Endpoint dédié

`GET /api/v1/biology-acks/pending-summary` — léger, retourne :
```csharp
public class BiologyAckPendingSummaryDto
{
    public int CriticalPending { get; init; }   // CDA flaggés IsCritical non-Resolved
    public int WarningPending { get; init; }    // CDA flaggés warning non-Resolved
}
```

Scoped au user courant (convention task-023). 1 query SQL agrégée
(count groupé par sévérité).

## Filtre inbox "bio non-résolue" — nouveau chip

### UI

Nouveau chip dans la barre filtres inbox (Blazor + Angular), libellé
« Bio à acquitter » (FR) / « Bio to ack » (EN), avec compteur :
- Texte : `Bio à acquitter (X)` où X = nombre de mails avec
  `PendingBiologyAcksCount > 0`
- Activé : filtre actif → l'inbox ne liste que les mails dont au moins
  un CDA flaggé est non-`Resolved`
- Désactivé par défaut. Pré-activé quand on arrive depuis le clic du
  widget KPI (navigation paramétrée par query string).

### Backend

L'endpoint listing inbox (déjà existant) gagne un query param
`?onlyPendingBiologyAck=true`. Quand vrai, filtre serveur-side via
join sur `BiologyAcks` + agrégation `MarkResolved`. Pas de nouveau
endpoint.

## Périmètre détaillé

### `dtos-mss`

- **Nouvel enum** `BiologyAckActionType` (5 valeurs ci-dessus)
- **Nouvel enum** `BiologyAckResolutionState` (`Pending` / `InProgress` / `Resolved`)
- **Nouveau DTO** `BiologyAckDto` :
  ```csharp
  public class BiologyAckDto
  {
      public Guid Id { get; init; }                    // PK Guid v7
      public Guid MedicalDocumentId { get; init; }     // FK CDA
      public BiologyAckActionType Action { get; init; }
      public string? Note { get; init; }
      public DateTime CreatedAt { get; init; }
      public string CreatedByUserEmail { get; init; }
      public string? CreatedByUserName { get; init; }
  }
  ```
- **Nouveau record** `BiologyAckRequestDto` :
  ```csharp
  public record BiologyAckRequestDto(BiologyAckActionType Action, string? Note);
  ```
- **Nouveau DTO** `BiologyAckPendingSummaryDto` :
  ```csharp
  public class BiologyAckPendingSummaryDto
  {
      public int CriticalPending { get; init; }
      public int WarningPending { get; init; }
  }
  ```
- **Champs ajoutés** sur `MailDto` :
  - `HasAbnormalBiology : bool`
  - `PendingBiologyAcksCount : int`
  - `HasCriticalPendingBiologyAck : bool`
- **Champs ajoutés** sur `MailMedicalDocumentDto` :
  - `LastBiologyAck : BiologyAckDto?`
  - `BiologyAckState : BiologyAckResolutionState`
- **5 nouveaux** `AuditActionType` enum members + **5 nouveaux**
  `PendingActionType` enum members (cf. plus haut)
- **NuGet bump** automatique via `/develop` (selon convention task-018+)

### `api-mail`

#### Migration BDD

Nouvelle migration `20260512_AddBiologyAcks.cs` (FluentMigrator) :

```sql
CREATE TABLE BiologyAcks (
  Id            UUID PRIMARY KEY,                 -- Guid v7 via UuidV7ValueGenerator
  UserId        UUID NOT NULL REFERENCES Users(Id),
  MedicalDocumentId UUID NOT NULL REFERENCES MailMedicalDocuments(Id) ON DELETE CASCADE,
  Action        INT NOT NULL,                     -- BiologyAckActionType enum int
  Note          VARCHAR(500) NULL,
  CreatedAt     TIMESTAMP WITH TIME ZONE NOT NULL,
  CreatedByUserEmail VARCHAR(255) NOT NULL,
  CreatedByUserName  VARCHAR(255) NULL
);
CREATE INDEX IX_BiologyAcks_DocumentId_CreatedAt
  ON BiologyAcks (MedicalDocumentId, CreatedAt DESC);
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
  - `Task<BiologyAck?> GetLastAckAsync(Guid documentId, Guid userId)`
  - `Task<BiologyAckResolutionState> GetStateAsync(Guid documentId, Guid userId)`
  - `Task<int> CountPendingForMailAsync(Guid mailId, Guid userId)`
  - `Task<BiologyAckPendingSummaryDto> GetPendingSummaryAsync(Guid userId)` (count groupé critical/warning)
- `IBiologyAckService` (Application) :
  - `Task<BiologyAckDto> RecordAckAsync(Guid documentId, BiologyAckRequestDto req, ClaimsPrincipal user)`
  - **Vérifie que le user JWT porte le rôle `Doctor`** (claim role) ;
    sinon → 403 Forbidden. La secrétaire / staff non-médecin ne peut
    pas poser d'ack.
  - Vérifie que le CDA appartient au tenant (via repository ownership
    scoping task-023, cumulatif sur UserId)
  - Vérifie que le CDA porte au moins une valeur `IsFlagged` (refus
    400 si pas de bio anormale — pas de pollution audit)
  - Crée l'entité, persiste, retourne le DTO
  - Émet l'audit trace via `IAuditService` avec le bon
    `AuditActionType` selon l'action choisie
- `IBiologyAckSummaryService` (ou méthode sur le service ci-dessus) :
  - `Task<BiologyAckPendingSummaryDto> GetPendingSummaryAsync(ClaimsPrincipal user)`

#### Endpoints

**POST** `/api/v1/medical-documents/{documentId:guid}/biology-ack`
- Body : `BiologyAckRequestDto`
- Auth : JWT obligatoire (FallbackPolicy task-021) + rôle `Doctor`
- Réponses :
  - `200 OK` + `BiologyAckDto` au succès
  - `400 BadRequest` si le CDA ne porte pas de bio anormale
  - `403 Forbidden` si le user n'a pas le rôle `Doctor`
  - `404 NotFound` si le CDA n'existe pas / ne tenant pas (silent
    leak per task-023 convention)
  - `401` si non authentifié

**GET** `/api/v1/biology-acks/pending-summary`
- Auth : JWT (rôle `Doctor` requis → 403 sinon)
- Réponse : `200 OK` + `BiologyAckPendingSummaryDto`

**Query param** `?onlyPendingBiologyAck=true` sur l'endpoint listing
inbox existant — filtre les mails dont au moins un CDA flaggé n'est
pas `Resolved` pour le user.

#### Aggregates `MailDto`

`MailRepository` étendu pour calculer :
- `HasAbnormalBiology`
- `PendingBiologyAcksCount`
- `HasCriticalPendingBiologyAck`

Le calcul se fait en 1 query SQL agrégée (pas N+1). État `Resolved`
inféré par sous-requête `EXISTS(... AND Action = MarkResolved AND CreatedAt > MAX(autres actions))`.

#### Tests

- ≥ 10 unit tests `BiologyAckServiceTests` :
  - 5 happy paths (1 par action, incluant `MarkResolved`)
  - 1 idempotency-revisit (poser 2 actions différentes sur le même
    CDA → 2 entries en BDD, dernier ack reflète la 2e)
  - 1 reject sur CDA sans bio flaggée (400)
  - 1 reject sur CDA inexistant (404)
  - 1 cross-tenant rejected (User A ne peut pas acker un CDA de User B → 404 silent leak)
  - 1 reject sur user sans rôle Doctor (403)
- ≥ 5 integration tests Postgres-backed :
  - Round-trip insertion + read `GetLastAckAsync`
  - `GetStateAsync` retourne `Pending` / `InProgress` / `Resolved` selon historique
  - `GetStateAsync` repasse à `InProgress` si action posée après `MarkResolved`
  - **CASCADE DELETE** : suppression d'un `MailMedicalDocument` purge ses `BiologyAcks` associés
  - `GetPendingSummaryAsync` retourne counts corrects (critical / warning séparés)
- ≥ 3 tests sur le filtre inbox `onlyPendingBiologyAck=true`
- 5 nouveaux tests audit trace (1 par action)

### `client-blazor`

#### Composant `BiologyAckPanelComponent.razor` (nouveau)

Sous le viewer mail (`MailDetailComponent`), un panneau par CDA flaggé :

- 4 boutons de prise en charge (Radzen ou design-system existant) +
  séparateur + 1 bouton `MarkResolved` distinct (couleur primaire)
- Header : titre du CDA + date
- Affichage du dernier ack si présent (via `mail.medicalDocuments[i].lastBiologyAck`)
- État badge calculé à partir de `BiologyAckState` (Pending / InProgress / Resolved)
- Au clic d'un bouton :
  - Si `medicalDocument.HasCriticalValue` : ouvre `BiologyAckConfirmDialog`
    (modal Radzen) qui montre LOINC + valeurs critiques + action,
    persiste seulement après `[ Confirmer ]`
  - Sinon : appel direct `IBiologyAckService.RecordAckAsync(documentId, action)`,
    optimistic update du `lastBiologyAck` local, toast succès
- Sur erreur API : revert + toast erreur

#### Composant `BiologyAckConfirmDialog.razor` (nouveau)

Modal de confirmation. Inputs : `DocumentLoinc`, `CriticalValues` (liste),
`ActionLabel`. Outputs : confirmé / annulé.

#### Tuile dashboard `BiologyAckPendingKpiTileComponent.razor` (nouveau)

Compose le dashboard côté Blazor. Lit `IBiologyAckService.GetPendingSummaryAsync()`,
affiche les 2 compteurs, clic → `NavigationManager.NavigateTo("/inbox?onlyPendingBiologyAck=true")`.

#### Filtre chip inbox

Extension de la barre filtres inbox Blazor : nouveau chip `Bio à acquitter (X)`,
toggle active `?onlyPendingBiologyAck=true` côté API.

#### Service Blazor

`IBiologyAckService` (côté client) avec :
- `RecordAckAsync(documentId, request)`
- `GetPendingSummaryAsync()`

#### Localizer

Nouvelles clés FR + EN :
- `BiologyAckPanelTitle` (« Bio anormale — {0} »)
- `BiologyAckActionAcknowledged` (« Pris connaissance »)
- `BiologyAckActionPatientCalled` (« Rappel patient »)
- `BiologyAckActionPatientSummoned` (« Convocation »)
- `BiologyAckActionReferredToColleague` (« Adressage confrère »)
- `BiologyAckActionMarkResolved` (« Marquer comme résolu »)
- `BiologyAckLastAction` (« Dernière action : {0} par {1} le {2} »)
- `BiologyAckSuccess` / `BiologyAckError`
- `BiologyAckConfirmDialogTitle` (« Confirmer l'action sur valeur critique »)
- `BiologyAckConfirmDialogBody` (« Vous êtes sur le point de poser : {0} sur {1} (valeur(s) : {2}) »)
- `BiologyAckKpiTitle` (« Bio en attente d'acquittement »)
- `BiologyAckKpiCriticalCount` (« {0} critical »)
- `BiologyAckKpiWarningCount` (« {0} warning »)
- `BiologyAckKpiEmpty` (« Aucune bio en attente »)
- `BiologyAckKpiOpenInbox` (« Voir l'inbox → »)
- `InboxFilterPendingBiologyAck` (« Bio à acquitter ({0}) »)

#### Tests bUnit

- ≥ 6 tests `BiologyAckPanelTests.cs` :
  - Render des 5 boutons quand bio flaggée présente
  - Pas de panneau quand `IsFlagged == false`
  - Affichage du dernier ack quand `lastBiologyAck != null`
  - Clic d'un bouton (non-critical) appelle le service et update optimistic
  - Clic d'un bouton (critical) ouvre la modal de confirmation
  - Confirmer la modal persiste, annuler ne fait rien
- ≥ 3 tests `BiologyAckPendingKpiTileTests.cs` :
  - Render des 2 compteurs critical/warning
  - Clic navigue vers inbox?onlyPendingBiologyAck=true
  - État vide (« Aucune bio en attente »)
- ≥ 2 tests filtre inbox chip

### `client-angular` (mode code-only)

Symétrique à Blazor :

- Nouveau composant standalone `BiologyAckPanelComponent` dans
  `front/libs/mss/src/features/mail/components/biology-ack-panel/`
  - Signal-first, OnPush, JSDoc
  - Inputs : `medicalDocument`, `mailUid`
  - Output : `(ackPosted)` pour propager au parent
- Nouveau composant `BiologyAckConfirmDialogComponent` (Angular CDK
  Dialog ou design system equivalent)
- Nouveau composant `BiologyAckPendingKpiTileComponent` sur le dashboard
- Filtre chip dans la barre filtres inbox Angular
- Service `MssApiService.recordBiologyAck(documentId, request)` ajouté
- Service `MssApiService.getBiologyAckPendingSummary()` ajouté
- État local : `signal<BiologyAckDto | null>` pour le dernier ack
- Tests Vitest ≥ 6 sur le panel + 3 sur la KPI + 2 sur le service +
  2 sur le filtre chip + 2 sur la modal confirmation

### Pas de modification

- Widget « Biologie anormale » F004 (`AbnormalBiologyWidget*`) reste
  inchangé en v1. Follow-up possible si le PO veut intégrer les acks
  dans le widget existant.
- TODO `notifications-abnormal-biology-043` (SSE pipe) **non wirée** —
  scope creep évité, task séparée si demandé.

## Convention scellée

- **Granularité** : 1 ack = 1 action sur 1 CDA. Pas par-mail, pas par-valeur.
- **Sévérité** : drive la couleur du badge ET la friction UX (modal de
  confirmation pour `IsCritical`), mais **pas** la disponibilité des
  boutons. Toute bio `IsFlagged` ouvre les 5 boutons.
- **Réversibilité** : non. Une fois posée, l'action est dans l'audit
  forever. Le médecin peut poser une action complémentaire (= nouvel
  audit entry, jamais d'écrasement).
- **État de résolution** : calculé, pas stocké. `Resolved` ssi le
  dernier `MarkResolved` est postérieur à la dernière action
  non-résolutoire du user sur ce CDA.
- **Badge inbox** : disparaît UNIQUEMENT après `MarkResolved`. Un
  clic `Acknowledged` seul ne ferme pas le badge.
- **Modèle multi-user** : **personnel** (1 médecin = ses propres acks).
  Cohérent avec le tenancy mono-utilisateur task-023. Pas applicable
  à un cabinet partagé — refonte tenancy nécessaire avant de l'envisager.
- **Rôle requis** : `Doctor` côté backend (claim JWT). Secrétaire /
  staff non-médecin ne peut pas poser d'ack (403).
- **Notification patient** : aucune. Les 5 actions sont **purement
  déclaratives**, audit-only. Pour écrire au patient, le médecin
  utilise Compose comme aujourd'hui.
- **Audit médico-légal** : chaque action porte `DocumentId`,
  `DocumentLoinc`, `PatientIns` (snapshot), `PatientName` (snapshot),
  identité médecin, timestamp serveur.
- **Note libre** : sur l'entité `BiologyAck` (colonne `Note`),
  optionnelle pour les 5 actions, max 500 chars. PAS sur l'audit trace.

## Definition of Done

### Build + tests
- [ ] `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreurs
- [ ] `dotnet test HealthPlatform.Api.Mail.sln` → 0 failures, **+10 unit
  tests min sur `BiologyAckServiceTests`**, **+5 integration tests min
  sur `BiologyAckRepositoryTests` Postgres-backed (incluant CASCADE DELETE)**,
  **+3 tests filtre inbox `onlyPendingBiologyAck`**, **+5 audit trace
  tests min**
- [ ] `dotnet build HealthPlatform.Client.sln` → 0 erreurs
- [ ] `dotnet test HealthPlatform.Client.sln` → 0 failures, **+6 bUnit
  tests min sur `BiologyAckPanelTests`**, **+3 sur `BiologyAckPendingKpiTileTests`**,
  **+2 sur le filtre inbox chip**
- [ ] `cd Client/Angular/front && npm run build` → 0 erreurs
- [ ] `cd Client/Angular/front && npm test` → 0 failures, **+6 Vitest
  tests min sur `biology-ack-panel.component.spec.ts`**, **+3 sur
  `biology-ack-pending-kpi-tile.component.spec.ts`**, **+2 sur la modal
  confirmation**, **+2 sur le filtre chip**, **+2 sur
  `mss-api.service.spec.ts` (méthodes ack + summary)**

### Backend
- [ ] Enums `BiologyAckActionType` (5 valeurs) + `BiologyAckResolutionState` (3 valeurs) publiés dans `dtos-mss` + NuGet bump
- [ ] DTOs `BiologyAckDto` + `BiologyAckRequestDto` + `BiologyAckPendingSummaryDto` publiés
- [ ] `MailDto.HasAbnormalBiology` + `MailDto.PendingBiologyAcksCount` + `MailDto.HasCriticalPendingBiologyAck` calculés serveur-side, pas N+1
- [ ] `MailMedicalDocumentDto.LastBiologyAck` + `MailMedicalDocumentDto.BiologyAckState` populés serveur-side
- [ ] Migration `BiologyAcks` table avec FK `Users` + FK `MailMedicalDocuments` ON DELETE CASCADE + index `(DocumentId, CreatedAt DESC)` + index `UserId`
- [ ] Endpoint `POST /api/v1/medical-documents/{id}/biology-ack` retourne 200/400/403/404 selon spec
- [ ] **Vérification rôle `Doctor`** sur le JWT → 403 si absent
- [ ] Endpoint `GET /api/v1/biology-acks/pending-summary` retourne 200/401/403
- [ ] Query param `?onlyPendingBiologyAck=true` sur listing inbox filtre correctement
- [ ] 5 nouveaux `AuditActionType` enum members + audit trace émise par chaque action avec `DocumentId` / `DocumentLoinc` / `PatientIns` / `PatientName`
- [ ] 5 nouveaux `PendingActionType` enum members + payload + replay logic dans `PendingActionService`
- [ ] Cross-tenant ownership scoping vérifié (User A ne peut pas acker CDA User B → 404 silent leak per task-023)

### Frontend (les 2)
- [ ] Panneau `BiologyAckPanel` rendu quand `medicalDocument.biologyResults` contient au moins une valeur `IsFlagged`
- [ ] 5 boutons cliquables avec `data-testid` posés (`bio-ack-acknowledged`, `bio-ack-called`, `bio-ack-summoned`, `bio-ack-referred`, `bio-ack-resolved`)
- [ ] Bouton `MarkResolved` visuellement distinct (séparateur + style primary)
- [ ] Modal de confirmation `BiologyAckConfirmDialog` s'ouvre uniquement quand `medicalDocument.HasCriticalValue`, affiche LOINC + valeur(s) + unité + référence + action choisie, `data-testid="bio-ack-confirm-dialog"`
- [ ] Affichage du `lastBiologyAck` (action + médecin + date) quand présent
- [ ] Badge inbox sur `mail-header` : rouge si `HasCriticalPendingBiologyAck`, orange si `PendingBiologyAcksCount > 0` sans critical, invisible si `PendingBiologyAcksCount == 0` ; `data-testid="mail-row-pending-bio-ack"`
- [ ] Tuile KPI `BiologyAckPendingKpiTile` sur le dashboard avec compteurs critical + warning, `data-testid="bio-ack-kpi-tile"`, clic navigue vers inbox avec filtre actif
- [ ] Filtre chip `Bio à acquitter (X)` dans la barre filtres inbox, `data-testid="inbox-filter-pending-bio-ack"`, toggle ajoute `?onlyPendingBiologyAck=true` au query
- [ ] Clic optimistic update + toast succès / revert sur erreur
- [ ] i18n FR + EN (Blazor Localizer + Angular i18n inline) pour toutes les clés listées
- [ ] Localizer parity FR/EN sur les 5 actions + tooltips + tuile KPI + filtre chip

### Documents
- [ ] EPIC E009 doc enrichie via `/tech-writer E009` : nouvelle ligne dans la table §10.x ou §6.13 (à décider) « Workflow d'acquittement bio anormale » avec mention « non Ségur — driven médico-légal ; backend + 2 frontends + audit + tuile dashboard + filtre inbox »

### Audit grep DOD
- [ ] `grep -rn "BiologyAckActionType" Api/Mail/src/` → matches dans Domain (entité), Application (service), Api (controller), Infrastructure (repository)
- [ ] `grep -rn "BiologyAckResolutionState" Api/Mail/src/Application` → matches dans le service + repository
- [ ] `grep -rn "BiologyAck" Client/Blazor/Src/` → matches dans Plugin (composant + service + Localizer + KPI tile + filter chip)
- [ ] `grep -rn "biologyAck\|BiologyAck" Client/Angular/front/libs/mss/src/` → matches dans `core/models`, `features/mail/services/mss-api.service.ts`, `features/mail/components/biology-ack-panel/`, `features/dashboard/components/biology-ack-pending-kpi-tile/`
- [ ] `grep -rn "HasAbnormalBiology\|PendingBiologyAcksCount\|HasCriticalPendingBiologyAck" Api/Mail/src/Application` → matches dans le repository (calcul) + le mapper
- [ ] Nouveau enum members `BiologyAcknowledged|BiologyPatientCalled|BiologyPatientSummoned|BiologyReferredToColleague|BiologyMarkedResolved` présents dans `AuditActionType` ET `PendingActionType`

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
4. Loguer en tant que doctor (claim `role=Doctor`) avec une boîte qui
   contient au moins 1 mail avec un CDA portant valeur(s) bio `IsFlagged`
   (utiliser un mail de test PSC ou injecter manuellement un CDA avec
   `InterpretationCode="HH"`).

### Vérification 1 — affichage du panneau + tuile KPI
1. Sur Blazor + Angular successivement, ouvrir le dashboard.
2. **Vérifier** : tuile KPI `BiologyAckPendingKpiTile` affiche
   `X critical` + `Y warning`. Bordure rouge si X > 0, orange sinon.
3. Ouvrir le mail concerné.
4. **Vérifier** : un panneau `BiologyAckPanel` s'affiche dans la
   section Biologie / sous le viewer, portant le titre du CDA + 5 boutons
   (4 prise en charge + 1 `MarkResolved` distinct).
5. **Vérifier** : badge rouge ou orange visible sur la ligne inbox.

### Vérification 2 — friction modal pour critical
1. Sur un mail avec CDA `IsCritical` (`LL/HH/AA`), cliquer
   « Pris connaissance ».
2. **Vérifier** : la modal `BiologyAckConfirmDialog` s'ouvre, montre
   le code LOINC, la (les) valeur(s) critique(s) avec unité + référence,
   et l'action « Pris connaissance ».
3. Cliquer `[ Annuler ]` → modal se ferme, aucun appel API ne part.
4. Re-cliquer « Pris connaissance », puis `[ Confirmer ]`.
5. **Vérifier** : 200 + toast succès. Le panneau affiche « Dernière
   action : Pris connaissance par Dr Dupont, le {date} ».

### Vérification 3 — flux complet jusqu'à résolution
1. Sur le même mail/CDA, cliquer « Rappel patient ». (Confirmation
   modale si critical.)
2. **Vérifier** : `lastBiologyAck` mis à jour. Badge inbox toujours
   présent (état `InProgress`).
3. Cliquer « Marquer comme résolu ». (Confirmation modale si critical.)
4. **Vérifier** : toast succès. Le badge inbox **disparaît**. Le panneau
   reste visible et affiche « Dernière action : Marquer comme résolu ».
5. **Vérifier** : tuile KPI dashboard mise à jour (compteur décrémenté).

### Vérification 4 — action complémentaire après résolution
1. Sur le même CDA déjà `Resolved`, cliquer « Convocation ».
2. **Vérifier** : ack enregistré. État du CDA repasse à `InProgress`
   (le dernier `MarkResolved` n'est plus le plus récent). Badge inbox
   réapparaît.
3. Re-cliquer « Marquer comme résolu » → badge disparaît à nouveau.

### Vérification 5 — DB cohérente
1. `SELECT * FROM BiologyAcks WHERE MedicalDocumentId = ... ORDER BY CreatedAt`
   retourne toutes les actions posées dans l'ordre, sans suppression.
2. Aucune action ne remplace une autre — pure append.

### Vérification 6 — mail avec 2 CDA, 1 résolu
1. Trouver / construire un mail avec 2 CDA flaggés.
2. Acker + `MarkResolved` uniquement le 1er CDA.
3. **Vérifier** : badge inbox toujours présent (le 2e CDA est encore
   `Pending`).
4. `MarkResolved` le 2e CDA.
5. **Vérifier** : badge inbox a disparu. Tuile KPI dashboard décrémentée.

### Vérification 7 — filtre inbox "bio à acquitter"
1. Cliquer le chip « Bio à acquitter (X) » dans la barre filtres inbox.
2. **Vérifier** : l'inbox liste uniquement les mails avec
   `PendingBiologyAcksCount > 0`. Les mails entièrement résolus ne sont
   plus listés.
3. Désactiver le chip → inbox revient à liste complète.
4. Depuis le dashboard, cliquer la tuile KPI → navigation vers
   `/inbox?onlyPendingBiologyAck=true`, chip pré-activé.

### Vérification 8 — refus rôle non-Doctor
1. Loguer en tant que user avec rôle `Staff` (ou sans rôle `Doctor`).
2. Tenter via Postman : `POST /api/v1/medical-documents/{guid}/biology-ack`
   `{ "action": "Acknowledged" }`.
3. **Vérifier** : 403 Forbidden.
4. **Vérifier** : la tuile KPI dashboard retourne aussi 403 — pas affichée
   pour les non-doctors (composant masqué côté frontend si claim absent).

### Vérification 9 — refus sur CDA sans bio flaggée
1. Tenter via Postman : `POST /api/v1/medical-documents/{guid-sans-bio-anormale}/biology-ack`
   `{ "action": "Acknowledged" }`.
2. **Vérifier** : 400 BadRequest avec message explicite.

### Vérification 10 — refus cross-tenant
1. Loguer User A, noter le DocumentId d'un CDA de sa boîte.
2. Loguer User B (autre médecin).
3. Tenter via Postman : `POST /api/v1/medical-documents/{guid-A}/biology-ack`
   avec session User B.
4. **Vérifier** : 404 NotFound (silent leak per task-023, pas 403).

### Vérification 11 — mode offline (PendingAction)
1. Couper le réseau (devtools offline).
2. Cliquer une action (ou la modal confirm si critical).
3. **Vérifier** : le panneau affiche optimisticly l'action posée.
   Pas de toast d'erreur (PendingAction queue silently).
4. Reconnecter.
5. **Vérifier** : `PendingActionService` rejoue, l'audit trace est
   bien émise serveur-side, `lastBiologyAck` réfléchit le state, KPI
   tuile mise à jour.

### Vérification 12 — non-régression widget F004
1. Aller sur le dashboard / widget « Biologie anormale » (F004).
2. **Vérifier** : comportement strictement inchangé. Aucune nouvelle
   notion d'ack sur le widget F004. Les patients listés ne tiennent pas
   compte des acks posés (gardé pour follow-up).
3. **Vérifier** : la nouvelle tuile `BiologyAckPendingKpiTile` est
   bien un composant séparé, coexiste avec F004 sans interférence.

## Limites et follow-ups

- **Pas d'affichage timeline d'historique** des acks posés sur un CDA
  (gardé en audit accessible via `/audit-trail`). Follow-up si demandé.
- **Pas de wiring SSE notif** abnormal biology (TODO
  `notifications-abnormal-biology-043` reste ouvert) — task séparée.
- **Pas d'intégration au widget F004** (`AbnormalBiologyWidget*`).
  Follow-up : filtrer les patients dont la bio a déjà été résolue pour
  réduire la pollution du widget.
- **Pas de notification patient** quelle que soit l'action.
- **Pas de délégation / multi-médecin** — chaque user gère ses acks
  séparément (cohérent avec le multi-tenant single-user actuel).
- **Pas d'unique constraint** `(DocumentId, UserId)` — convention
  d'actions complémentaires en série.
- **Pas de SLA temporels stockés** (`FirstAcknowledgedAt`, `ResolvedAt`,
  `ResolutionDuration`) — les valeurs sont **dérivables** depuis la
  table `BiologyAcks` (`MIN(CreatedAt)`, `MAX(CreatedAt) WHERE Action = MarkResolved`).
  Pas de dénormalisation tant qu'aucun dashboard SLA n'est demandé.
  Follow-up dédié si besoin.
- **Pas de DTO `BiologyAckSummary` enrichi** (`AckCount`, `FirstAckAt`,
  `LastActor`, etc.) — `LastBiologyAck` + `BiologyAckState` couvrent
  les besoins UI actuels. Si futur UX en demande plus, extension
  progressive de `MailMedicalDocumentDto`. YAGNI v1.
- **Pas de moteur générique de workflow clinique acquittable** —
  cette feature est dédiée à la bio anormale. Si un jour on a 3+ cas
  concrets (imagerie critique, ECG anormal, CR hospitalier), refactor
  d'extraction en moteur générique. Pas d'over-engineering préventif.

## References

- `Api/Mail/src/Application/Services/Implementation/CdaParsingService.cs`
  (≈ ligne 192) — détection `IsFlagged`
- `Dtos/AbnormalBiologyValueDto.cs` — distinction `IsCritical`
- `Api/Mail/src/Domain/Entities/MssAuditTrace.cs` + `Dtos/AuditActionType.cs`
  — framework audit task-004
- `Dtos/PendingActionTypes.cs` — pattern offline queue
- `Api/Mail/src/Application/Services/NewMailNotifier.cs:35` — TODO
  `notifications-abnormal-biology-043` (intentionnellement non wiré)
- `Client/Blazor/Src/Modules/Mss/Plugin/Widgets/AbnormalBiologyWidgetComponent.razor`
  — widget F004 existant (inchangé par cette US)
- archived-task-011 — pattern `PendingIntegrationsCount` agrégé serveur-side
- archived-task-004 — framework audit MSS
- archived-task-021 — FallbackPolicy JWT
- archived-task-023 — convention ownership scoping cumulatif `UserId`
- EPIC E009 §6.13 (RG-E009-051/052) — détection / affichage bio
  anormale (acquittement non couvert par ces règles)
