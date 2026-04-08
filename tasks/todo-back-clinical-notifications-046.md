# todo-back-clinical-notifications-046 — Backend : enrichissement clinique des notifications

**Dependencies**: done-back-notifications-realtime-040 mergé (la plomberie SSE/SignalR/broker doit être en place)
**Repo**: api-mail (path: `Api/Mail`)
**Touches**: dtos (`NotificationPayloadDto` v2 — rupture majeure), interop-cda (lecture seule)
**Module**: Api/Mail
**Feature**: tests/Features/Mss/PreferencesNotification.feature (à étendre par le PO si nécessaire)

## Contexte

`done-back-notifications-realtime-040` a livré la plomberie temps-réel (SSE + SignalR + `NewMailNotifier` + broker). Mais le payload est cliniquement vide : pas de patient, pas de type de document, pas de findings, pas de sévérité réelle (juste `IsFlagged`). Pour un médecin en consultation, "Nouveau message de Dr X" est inutile — il doit pouvoir décider en 1 seconde s'il interrompt sa consultation.

Cette tâche enrichit le DTO en lisant le **CDA HL7** des pièces jointes MSS via `interop/interop.cda.parser` (déjà présent dans le workspace), résout le patient contre la base locale, et calcule une vraie sévérité clinique.

## Objectif

Quand un mail MSS arrive avec une pièce jointe CDA exploitable, produire un `NotificationPayloadDto` v2 contenant : patient identifié, type de document HL7, findings clés extraits, sévérité clinique calculée, expéditeur résolu, actions suggérées.

## Travail à réaliser

### 1. DTO v2 (rupture — repo `dtos`)

`NotificationPayloadDto` v2 dans le repo `dtos`. Publier via `/publish-dtos` AVANT le reste.

```csharp
public class NotificationPayloadDto
{
    public Guid NotificationId { get; set; }
    public NotificationKind Kind { get; set; }
    public DateTimeOffset ReceivedAt { get; set; }
    public uint MailUid { get; set; }
    public string FolderPath { get; set; }

    public ClinicalSeverity Severity { get; set; }   // Critical, Urgent, Abnormal, Routine, Info
    public string SeverityReason { get; set; }

    public PatientContextDto? Patient { get; set; }   // null si non résolu
    public ClinicalDocumentDto? Document { get; set; } // null si CDA non parsable
    public List<ClinicalFindingDto> KeyFindings { get; set; } = new();

    public SenderDto Sender { get; set; }
    public List<SuggestedActionDto> SuggestedActions { get; set; } = new();

    public bool ShowDesktop { get; set; }
    public bool PlaySound { get; set; }
    public string SoundProfile { get; set; }   // "critical", "urgent", "soft"
    public bool RespectDnd { get; set; }
}

public class PatientContextDto
{
    public string FullName { get; set; }
    public string MaskedName { get; set; }    // ex: "S.M."
    public int? Age { get; set; }
    public string? Sex { get; set; }          // "F", "M", "U"
    public string? InternalRecordId { get; set; }  // null si pas de match local
    public string? Ipp { get; set; }
    public DateTime? BirthDate { get; set; }
}

public class ClinicalDocumentDto
{
    public string LoincCode { get; set; }
    public ClinicalDocumentType DocumentType { get; set; }
    // ConsultationNote, LabReport, ImagingReport, DischargeSummary, ReferralNote, PrescriptionRequest, AdminLetter, Other
    public string? Specialty { get; set; }
    public DateTimeOffset? ProductionDate { get; set; }   // date du soin/prélèvement
}

public class ClinicalFindingDto
{
    public string? LoincCode { get; set; }
    public string Label { get; set; }              // "Kaliémie"
    public string? Value { get; set; }             // "6.8"
    public string? Unit { get; set; }              // "mmol/L"
    public string? ReferenceRange { get; set; }    // "3.5-5.0"
    public FindingFlag Flag { get; set; }          // Normal, Low, High, CriticalLow, CriticalHigh
    public string? Conclusion { get; set; }        // pour imagerie : 1 phrase, sinon null
}

public class SenderDto
{
    public string FullName { get; set; }
    public string? RpsId { get; set; }
    public string? Specialty { get; set; }
    public string? Institution { get; set; }
    public string? Role { get; set; }
}

public class SuggestedActionDto
{
    public string Code { get; set; }    // "OpenRecord", "CallPatient", "Acknowledge", "Forward", "Snooze"
    public string Label { get; set; }
    public string? Reason { get; set; }
    public Dictionary<string, string>? Parameters { get; set; }
}

public enum ClinicalSeverity { Critical, Urgent, Abnormal, Routine, Info }
public enum ClinicalDocumentType { ConsultationNote, LabReport, ImagingReport, DischargeSummary, ReferralNote, PrescriptionRequest, AdminLetter, Other }
public enum FindingFlag { Normal, Low, High, CriticalLow, CriticalHigh, Unknown }
```

### 2. Service `IClinicalNotificationBuilder`

`src/Application/Services/Interfaces/IClinicalNotificationBuilder.cs` + impl.

```csharp
public interface IClinicalNotificationBuilder
{
    Task<NotificationPayloadDto> BuildAsync(MailDto mail, NotificationPreferences prefs, CancellationToken ct);
}
```

Pipeline interne :
1. **Extraction CDA** : pour chaque pièce jointe XML, appeler `interop.cda.parser` et obtenir un `CdaDocument` structuré (header, sections, observations)
2. **Type de document** : mapper le code LOINC du header CDA vers `ClinicalDocumentType` (table de mapping à créer en `Domain/ReferenceData/LoincToDocumentType.cs`)
3. **Patient** : extraire `recordTarget/patientRole` du CDA → tenter résolution contre `IPatientRepository` (matching IPP exact ; fallback nom+prénom+date naissance — confirmation PO requise)
4. **Findings** : selon `DocumentType`
   - `LabReport` : extraire toutes les `Observation` de la section `Resultats` (LOINC `30954-2` ou similaire), pour chaque obs : value, unit, reference range, flag depuis l'attribut `interpretationCode` HL7. **Si Flag = High/Low → consulter `ICriticalThresholdsRepository` pour reclassifier en `CriticalHigh`/`CriticalLow` si dépassement seuil critique**.
   - `ImagingReport` : extraire la section `Conclusion` (LOINC `19005-8`), 1 phrase max, et un flag binaire `AbnormalityDetected` heuristique (mots-clés "anomalie", "lésion", "suspect")
   - `ConsultationNote` / `DischargeSummary` : 1 ligne extraite de la section `Conclusion` ou `Plan`
   - Sinon : findings vide
5. **Sévérité** : règle d'évaluation
   - Si tout `KeyFindings` contient au moins un `CriticalHigh`/`CriticalLow` → `Critical`
   - Sinon si CDA tag urgence MSS = "U" / `priorityCode == U` → `Urgent`
   - Sinon si DocumentType = `DischargeSummary` ET `ProductionDate` < 48h → `Urgent`
   - Sinon si au moins un finding `High`/`Low` → `Abnormal`
   - Sinon si DocumentType ∈ {ConsultationNote, ImagingReport sans abnormality, ReferralNote, PrescriptionRequest} → `Routine`
   - Sinon → `Info`
6. **Expéditeur** : extraire `author/assignedAuthor` du CDA, lookup RPPS si possible (méthode existante côté `IAnnuaireSanteService` du repo — vérifier disponibilité)
7. **SuggestedActions** :
   - Toujours : `OpenRecord` (paramètre `MailUid`), `Acknowledge`
   - Si `Severity = Critical` : ajouter `CallPatient` avec `Reason = SeverityReason`
   - Si `DocumentType = ReferralNote` : ajouter `Forward`
8. **SoundProfile** : `Critical → "critical"`, `Urgent → "urgent"`, sinon `"soft"`
9. **RespectDnd** : `true` si `Severity ∈ {Routine, Info, Abnormal}`, `false` si `Critical`/`Urgent`

### 3. Table seuils critiques

Créer `src/Domain/ReferenceData/CriticalThresholds.cs` avec les top 20 analytes critiques en biologie (à valider par le PO — voir question ouverte ci-dessous). Stockée en code dans un premier temps, puis migrer vers DB en wave ultérieure.

Set par défaut proposé (à valider) :
```
LOINC          Analyte           CriticalLow   CriticalHigh   Unit
2823-3         Potassium         < 2.5         > 6.0          mmol/L
2951-2         Sodium            < 120         > 160          mmol/L
2160-0         Créatinine        —             > 200          µmol/L
6690-2         Leucocytes        < 1.0         > 50           G/L
777-3          Plaquettes        < 20          > 1000         G/L
718-7          Hémoglobine       < 7           —              g/dL
14749-6        Glycémie          < 2.5         > 25           mmol/L
2885-2         Calcium total     < 1.6         > 3.2          mmol/L
6298-4         Kaliémie urinaire —             —              (info)
33914-3        eGFR              < 15          —              mL/min/1.73m²
4548-4         HbA1c             —             > 12           %
2284-8         Folate            < 2           —              ng/mL
2132-9         Vitamine B12      < 100         —              pmol/L
4544-3         Hématocrite       < 25          > 60           %
6301-6         INR               —             > 5            ratio
3173-2         APTT              —             > 100          s
3094-0         Urée              —             > 30           mmol/L
1742-6         ALT               —             > 1000         UI/L
1920-8         AST               —             > 1000         UI/L
14682-9        Troponine         —             > 0.04         ng/mL
```

### 4. Câblage dans le pipeline existant

Remplacer dans `NewMailNotifier.HandleNewMailAsync` (livré par 040) la construction "manuelle" du `NotificationPayloadDto` par un appel à `IClinicalNotificationBuilder.BuildAsync(mail, prefs, ct)`. Garder la logique de filtrage existante (EnableNewMail / EnableUrgentOnly / EnableAbnormalBiology) **devant** l'appel au builder, mais désormais alimenter `EnableUrgentOnly` par `payload.Severity ∈ {Critical, Urgent}` plutôt que par `IsFlagged`.

### 5. Tests

**Unitaires** (`mss.mail.application.tests`) :
- `ClinicalNotificationBuilderTests` : couverture des 5 sévérités, des 7 `DocumentType`, des cas null (pas de pièce jointe CDA, CDA invalide, patient non résolu, sender sans RPPS), de la reclassification critique via `CriticalThresholds`, des `SuggestedActions` selon sévérité.
- `LoincToDocumentTypeTests` : mapping pour les 10 codes LOINC les plus fréquents en MSS.

**Intégration** (`mss.mail.integration.tests`) :
- Charger 3 CDA de référence dans `tests/TestData/cda/` (LabReport critique, ImagingReport normal, DischargeSummary récente) → vérifier le payload produit bout en bout.
- Vérifier que le payload arrive bien sur le canal SSE existant avec tous les champs renseignés.

**BDD** (`mss.mail.bdd.tests`) : étendre `PreferencesNotificationStepDefinitions` avec 2 scénarios `Critical_Lab_Bypasses_DND` et `Routine_Document_Skipped_If_DND_On` — features à demander au PO si nécessaire.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests passent — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] DTO v2 publié via `/publish-dtos` (nouvelle version majeure du package, ex 165.0.0)
- [ ] `IClinicalNotificationBuilder` implémenté + 100% des branches sévérité couvertes en unitaire
- [ ] Mapping LOINC → DocumentType pour au moins 10 codes courants
- [ ] Table `CriticalThresholds` chargée depuis `Domain/ReferenceData/CriticalThresholds.cs` avec les 20 analytes proposés (ou liste validée par PO)
- [ ] Résolution patient : IPP exact en priorité, fallback nom+prénom+date naissance (si validé PO)
- [ ] Résolution sender : RPPS lookup via `IAnnuaireSanteService` si dispo, sinon fallback nom du `assignedAuthor` CDA
- [ ] `NewMailNotifier.HandleNewMailAsync` câblé sur le builder, pipeline de filtrage préservé
- [ ] 3 fixtures CDA de référence ajoutées dans `tests/TestData/cda/` et utilisées en tests d'intégration
- [ ] Logs structurés sur chaque décision : sévérité retenue + raison + patient match success/fail + sender resolution success/fail
- [ ] Aucune régression sur les tests existants de 040
- [ ] Endpoint SSE retourne des payloads avec `Severity != Info` quand on injecte un CDA biologique critique en test d'intégration

## Manual Test Plan (à promouvoir par l'orchestrator en commentaire de PR)

1. Démarrer api-mail localement
2. Configurer un compte IMAP MSS de test
3. Préparer 3 mails MSS de test contenant chacun une pièce jointe CDA :
   - **Test A — Bio critique** : un CDA `LabReport` LOINC `2823-3` avec `value = 6.8 mmol/L` → attendu `Severity = Critical`, `SoundProfile = critical`, `SuggestedActions` contient `CallPatient` avec reason
   - **Test B — Imagerie normale** : un CDA `ImagingReport` avec section Conclusion "Pas d'anomalie significative" → attendu `Severity = Routine`, `SoundProfile = soft`
   - **Test C — Sortie hospitalisation** : un CDA `DischargeSummary` avec `effectiveTime` < 48h → attendu `Severity = Urgent`
4. Pour chaque mail, ouvrir une connexion `curl -N` au stream SSE
5. Vérifier le JSON reçu contient bien : `Patient.FullName`, `Patient.InternalRecordId` (si fixture patient en base), `Document.DocumentType`, `KeyFindings[]` non vide, `Sender.FullName`, `Severity` correcte, `SuggestedActions[]` non vide

## Questions ouvertes (PO doit trancher avant dispatch)

1. **Source des seuils critiques** : la liste proposée ci-dessus suffit pour démarrer, ou tu as une référence officielle (SFBC, HAS, table interne) ?
2. **Patient match fallback** : si l'IPP n'est pas dans la base locale, on tente nom+prénom+date naissance ? Risque de faux positifs (homonymes) — on accepte ?
3. **Privacy mode default** : `Patient.MaskedName` toujours calculé, ou seulement si le toggle "Mode visible" est activé côté front (donc backend toujours envoie le nom complet) ?
4. **Sévérité urgent pour DischargeSummary < 48h** : règle pertinente ou trop large ? (ex: sortie programmée vs sortie d'urgence — distinguable via le CDA ?)
5. **`AdminLetter`** est-il un type qu'on veut router vers les notifications, ou bien filtré (`Severity = Info` toujours) ?

## Notes

- Le repo `interop/interop.cda.parser` est déjà disponible. Vérifier la signature exacte du parser et adapter — ne PAS modifier ce repo, juste le consommer.
- La table seuils critiques sera migrée vers DB dans une wave future si elle devient longue. Pour l'instant code statique = simplicité de maintien et de test.
- `interop.cda.parser` retourne potentiellement plusieurs documents par mail (pièces jointes multiples). Stratégie : 1 notification par CDA cliniquement exploitable, batching laissé à la tâche 049.
