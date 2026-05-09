# todo-task-035.md — Widget Patient (5 derniers patients avec mails non lus)

**Repos**: api-mail, client-blazor, client-angular, dtos-mss
**Dependencies**: —
**Epic**: E009

## Objectif

Donner au médecin un accès rapide, depuis le dashboard de la messagerie
sécurisée, aux **5 derniers patients ayant au moins un mail non lu** dans
sa BAL MSSanté. Le widget est vertical, intégré au dashboard, propose une
ligne agrégée par patient (1 patient = 1 ligne, peu importe le nombre de
mails non lus), et expose 3 actions rapides via un menu kebab : ouvrir le
dossier patient, filtrer la BAL sur ce patient, ou lire directement le
mail non lu le plus récent.

US livrée à parité **Blazor + Angular**, alimentée par un nouvel endpoint
agrégé côté `api-mail`, avec DTO publié dans `dtos-mss`.

## Comportement attendu

### Critère de sélection et tri

- **Critère** : statut **non lu** sur les mails de la BAL du médecin connecté.
  La date du mail n'a pas d'importance — seul le statut lu/non-lu compte.
- **Top 5 patients** distincts ayant ≥ 1 mail non lu, classés par **date du
  mail non-lu le plus récent** (plus récent en haut).
- **Bouton "Voir plus"** : étend la liste à 20 patients (incrément non
  paginé — la sélection reste "patients avec ≥ 1 non lu", limit augmente).
- **Cloisonnement par UserId** (convention task-023) — un médecin ne voit
  jamais les patients/mails d'un autre utilisateur.

### Granularité

- **1 patient = 1 ligne agrégée**. Si Mme Dupont a 3 mails non lus, elle
  apparaît une seule fois avec un compteur `3 mails non lus`.

### Anatomie d'une ligne (parité Blazor + Angular)

| Bloc | Contenu |
|---|---|
| Identité | Avatar à initiales · Nom complet · Âge · Sexe |
| Compteur | `N mails non lus` + date relative du plus récent (`il y a 2h`, `hier`, `il y a 3 j`) |
| Catégories CDA | Chips distinctes parmi les mails non-lus du patient (Biologie, Imagerie, Consultation, Prescription, Hospitalisation, Microbiologie, DLU…) |
| Sévérité biologie | Badge 🔴 si biologie critique (HL7 `AA`/`HH`/`LL`/`CriticalHigh`/`CriticalLow`), 🟠 si anormale, rien sinon |
| Statut d'intégration | Pastille ✓ (tous intégrés) ou ⏳ (N en attente) — réutilise la logique task-010 |
| Doublon | Badge `DOUBLON` si au moins un mail non-lu du patient est marqué doublon (task-013) |
| Menu actions | Kebab `⋮` à droite — 3 entrées (cf. ci-dessous) |

### Menu kebab — 3 actions

1. **Voir le dossier patient**
   - Navigation vers la vue patient (E009-F004 : Timeline + Biologie + Synthèse).
   - **Désactivée** si le patient n'a pas d'INS qualifié rattaché — tooltip
     explicatif `Aucun INS qualifié — dossier non disponible`.
2. **Filtrer mails sur ce patient**
   - Applique le filtre patient existant à la BAL et navigue vers la vue
     liste des mails. Réutilise le mécanisme de filtrage existant de la
     BAL (chip patient / paramètre de recherche par INS).
3. **Voir l'email**
   - Ouvre **directement** le mail non-lu **le plus récent** du patient.
   - **Réutilise** le composant existant — **pas de nouveau composant** :
     - Blazor : `Client/Blazor/Src/Modules/Mss/Plugin/Components/MailDetailComponent.razor`
     - Angular : `Client/Angular/front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
   - **Side-effects automatiques** :
     - Mark-as-read côté serveur (réutilise l'endpoint existant
       `PUT /api/v1/mail/folders/INBOX/emails/{uid}/status/read`).
     - Trace d'audit (réutilise le mécanisme d'audit existant — un événement
       `MailRead` doit être émis sur le canal d'audit, comme pour la lecture
       classique d'un mail).
     - Refresh automatique du widget (le mail concerné disparaît du
       compteur ; si le patient n'a plus de non-lu, sa ligne disparaît).

### Temps réel

- Le widget s'abonne au canal SSE `MailEvents` (déjà en place) pour se
  rafraîchir automatiquement quand :
  - un nouveau mail arrive (peut faire monter/entrer un patient),
  - un mail est marqué lu (peut faire baisser le compteur d'un patient ou
    le faire sortir),
  - un mail est marqué non-lu (peut faire entrer un patient).
- Pas de polling.

### Empty state

- Si **aucun patient n'a de mail non-lu** : message friendly i18n
  `Aucun mail non lu — vous êtes à jour 🎉` (libellé à fournir FR + EN).

### Cas particuliers

- **Patient sans INS qualifié** : ligne affichée, action "Voir le dossier
  patient" désactivée avec tooltip. Les 2 autres actions (filtrer mails,
  voir l'email) restent disponibles.
- **Patient avec 1 seul mail non-lu** : action "Voir l'email" ouvre ce
  mail unique (cas trivial du "plus récent").
- **Cohabitation avec `AbnormalBiologyWidgetComponent`** : ce widget
  s'**ajoute** au dashboard, **il ne remplace pas** AbnormalBiology
  (critère différent : non-lu ≠ biologie anormale). Les deux peuvent
  afficher le même patient — c'est attendu.

## Backend (`api-mail` + `dtos-mss`)

### Nouveau DTO (`dtos-mss`)

```csharp
public record PatientWithUnreadMailsDto
{
    public Guid PatientId { get; init; }            // Guid v7 — null si patient pas rattaché
    public string? Ins { get; init; }               // null si pas d'INS qualifié
    public bool HasQualifiedIns { get; init; }
    public string LastName { get; init; } = "";
    public string FirstName { get; init; } = "";
    public string Initials { get; init; } = "";
    public int? Age { get; init; }
    public string? Gender { get; init; }            // M | F | U
    public int UnreadCount { get; init; }
    public uint LastUnreadMailUid { get; init; }    // UID IMAP du mail le plus récent non-lu
    public DateTimeOffset LastUnreadMailDate { get; init; }
    public List<string> CdaCategories { get; init; } = new();   // ex: ["Biology","Imaging"]
    public BiologySeverity? MaxBiologySeverity { get; init; }    // None | Abnormal | Critical
    public IntegrationStatus IntegrationStatus { get; init; }    // AllIntegrated | PartiallyPending
    public bool HasDuplicate { get; init; }
}

public enum BiologySeverity { None, Abnormal, Critical }
public enum IntegrationStatus { AllIntegrated, PartiallyPending }
```

### Nouvel endpoint

```
GET /api/v1/patients/with-unread-mails?limit={int}
```

- Auth requise (JWT — convention task-017).
- `limit` optionnel, défaut **5**, max **20**.
- Retourne `List<PatientWithUnreadMailsDto>` triée par `LastUnreadMailDate`
  desc.
- Filtré par `UserId` du token (convention task-023).

### Service / Repository

- `IPatientService.GetPatientsWithUnreadMailsAsync(int limit, CancellationToken)`
  — construit l'agrégation : patients distincts ayant ≥ 1 mail non lu,
  enrichi avec catégories CDA, sévérité bio, statut d'intégration, doublon.
- L'agrégation respecte le filtre `UserId` au niveau du repository.

## Frontend Blazor (`client-blazor`)

- Nouveau composant `Client/Blazor/Src/Modules/Mss/Plugin/Widgets/PatientWidgetComponent.razor`
  + CSS associée. S'inspire visuellement de `AbnormalBiologyWidgetComponent`
  (cards verticales, avatars à initiales, badges).
- Service Blazor `IPatientWidgetService` qui appelle le nouvel endpoint via
  `HttpClient` (refit ou direct selon convention du module).
- Abonnement SSE `MailEvents` (canal existant) pour refresh.
- Menu kebab via `BSDropdown` ou pattern existant du module.
- Action "Voir l'email" → invocation `MailDetailComponent` existant
  (paramétrage par `MailUid` + `FolderPath="INBOX"`). Pas de nouveau
  composant de visualisation email.
- i18n via `Localizer` du module Mss — toutes les chaînes affichées doivent
  être localisées FR + EN (suivre la convention task-026).
- `data-testid` sur tous les éléments interactifs.

## Frontend Angular (`client-angular`)

- Nouveau composant `Client/Angular/front/libs/mss/src/features/dashboard/widgets/patient-widget/patient-widget.component.ts`
  (chemin exact à confirmer pendant `/develop` selon arborescence du
  module dashboard Angular existant).
- Service Angular qui appelle le nouvel endpoint.
- Abonnement à l'observable du `MailEventsService` existant pour refresh.
- Menu kebab via composant existant (Angular Material ou équivalent du
  projet — réutiliser ce qui sert déjà sur les autres widgets).
- Action "Voir l'email" → invocation du composant existant
  `MailDetailComponent` (`mail-detail.component.ts`). Pas de nouveau
  composant.
- i18n via le mécanisme existant — FR + EN.
- `data-testid` sur tous les éléments interactifs.

## Definition of Done

### Backend (`api-mail` + `dtos-mss`)

- [ ] Build passe (0 erreur) sur `api-mail` et `dtos-mss`
- [ ] Tests passent (0 failure) sur `api-mail`
- [ ] DTO `PatientWithUnreadMailsDto` + enums associés publiés dans
      `dtos-mss` (NuGet bumpé via `/publish-dtos` — automatisé par `/develop`)
- [ ] Endpoint `GET /api/v1/patients/with-unread-mails?limit={int}` exposé
      sur `PatientsController`, paramètre `limit` validé (`5..20`, défaut 5)
- [ ] Service `IPatientService.GetPatientsWithUnreadMailsAsync` + impl
      avec ≥ 3 unit tests xUnit (cas nominal, empty, limit clamp)
- [ ] Repository : agrégation respecte le filtre `UserId` (convention task-023)
- [ ] ≥ 1 test d'intégration sur le nouvel endpoint (rule 1b — happy path
      avec données seedées + 1 cas empty)
- [ ] Test cross-tenant xUnit : User A a 3 patients avec non-lus, User B
      n'en voit aucun
- [ ] Pas de régression sur la suite api-mail (compteur tests stable ou +)

### Frontend Blazor (`client-blazor`)

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 failure)
- [ ] Nouveau widget `PatientWidgetComponent.razor` intégré au dashboard
- [ ] Empty state affiché quand aucun patient avec non-lu
- [ ] Menu kebab avec les 3 actions, l'action "Voir le dossier patient"
      désactivée si `HasQualifiedIns == false` avec tooltip
- [ ] Action "Voir l'email" réutilise `MailDetailComponent` existant
      (vérification : aucun nouveau composant de visualisation email créé
      sur cette branche — grep dans la PR)
- [ ] Action "Voir l'email" déclenche mark-as-read + audit + refresh widget
- [ ] Refresh sur événement SSE `MailEvents` fonctionnel
- [ ] Toutes les chaînes affichées sont localisées FR + EN (`Localizer`)
- [ ] `data-testid` sur tous les éléments interactifs
      (`patient-widget-row-{patientId}`, `patient-widget-kebab-{patientId}`,
      `patient-widget-action-view-patient`, `patient-widget-action-filter-mails`,
      `patient-widget-action-view-email`, `patient-widget-empty`,
      `patient-widget-see-more`)
- [ ] ≥ 1 test bUnit du widget (rendu, empty state, click sur action)

### Frontend Angular (`client-angular`)

- [ ] Build passe (0 erreur) — `npm ci && npm run build`
- [ ] Tests passent (0 failure) — `npm test`
- [ ] Nouveau widget Angular `PatientWidgetComponent` intégré au dashboard
- [ ] Empty state affiché quand aucun patient avec non-lu
- [ ] Menu kebab avec les 3 actions, action "Voir le dossier patient"
      désactivée si `hasQualifiedIns === false` avec tooltip
- [ ] Action "Voir l'email" réutilise `mail-detail.component.ts` existant
      (vérification : aucun nouveau composant de visualisation email créé
      sur cette branche — grep dans la PR)
- [ ] Action "Voir l'email" déclenche mark-as-read + audit + refresh widget
- [ ] Refresh sur événement `MailEvents` fonctionnel
- [ ] Toutes les chaînes affichées sont localisées FR + EN
- [ ] `data-testid` sur tous les éléments interactifs (mêmes conventions
      que Blazor)
- [ ] ≥ 1 test Vitest du widget (rendu, empty state, click sur action)

### Parité Blazor / Angular

- [ ] Comportement iso-fonctionnel : même tri, mêmes 3 actions, mêmes
      indicateurs visuels, même empty state
- [ ] Mêmes `data-testid` côté Blazor et Angular pour les éléments
      équivalents

## Manual Test Plan

### Setup

1. Lancer la stack :
   - `cd Api/Mail && dotnet run` (ou Aspire AppHost)
   - `cd Client/Blazor && dotnet run`
   - `cd Client/Angular && npm start`
2. Se connecter avec un compte test (`virginie.medecinrpps0062267` ou
   équivalent fixture). S'assurer que la BAL contient ≥ 6 patients
   distincts dont certains ont plusieurs mails non-lus.

### Cas nominal — Blazor

3. Ouvrir le dashboard → le **Widget Patient** s'affiche en colonne
   verticale.
4. Vérifier qu'il affiche **5 lignes maximum**, classées par mail non-lu
   le plus récent en haut.
5. Sur une ligne avec ≥ 1 mail biologie critique → badge 🔴 visible.
6. Sur une ligne avec mail "imagerie + consultation" → 2 chips de
   catégorie visibles.
7. Cliquer sur le bouton **"Voir plus"** → la liste s'étend (jusqu'à 20).
8. Cliquer sur le **menu kebab ⋮** d'une ligne :
   - **"Voir le dossier patient"** → navigue vers la vue patient
     (Timeline + Biologie + Synthèse) du patient sélectionné.
   - **"Filtrer mails sur ce patient"** → BAL filtrée, seuls les mails
     de ce patient visibles.
   - **"Voir l'email"** → ouvre le composant `MailDetailComponent`
     existant (pas un nouveau modal/écran), avec le mail non-lu le plus
     récent. Le mail passe automatiquement en lu, le widget se rafraîchit
     (compteur baisse ou ligne disparaît si plus de non-lu).
9. Vérifier la trace d'audit en base / Seq : événement `MailRead` émis
   pour ce mail.

### Cas nominal — Angular

10. Mêmes étapes 3 → 9 sur le frontend Angular. Comportement iso.

### Cas particuliers

11. **Patient sans INS qualifié** : forcer un patient sans INS qualifié →
    son action "Voir le dossier patient" est grisée avec tooltip
    `Aucun INS qualifié — dossier non disponible`. Les 2 autres actions
    fonctionnent.
12. **Empty state** : marquer tous les mails comme lus → le widget
    affiche le message `Aucun mail non lu — vous êtes à jour 🎉`.
13. **Temps réel** : envoyer un nouveau mail à la BAL → le widget se met
    à jour sans refresh manuel (un patient apparaît ou son compteur
    monte).
14. **Cohabitation** : si le médecin a un patient avec biologie critique
    ET non-lu → ce patient apparaît dans **les deux widgets** (Patient
    Widget et AbnormalBiology Widget). C'est attendu.

### Cross-tenant

15. Se déconnecter, se reconnecter avec un autre médecin (ex.
    `doctor2`) → le widget n'affiche **jamais** les patients du médecin
    précédent (cloisonnement task-023).

### Réseau

16. DevTools → onglet réseau : vérifier que `GET /api/v1/patients/with-unread-mails`
    retourne 200 avec la structure `PatientWithUnreadMailsDto[]`. Vérifier
    le paramètre `limit=5` par défaut, `limit=20` après "Voir plus".

## Notes

- **Composants email à réutiliser obligatoirement** :
  - Blazor : `MailDetailComponent.razor`
  - Angular : `mail-detail.component.ts`
  La rédaction d'un nouveau composant de visualisation email est interdite
  pour cette US (cf. memory `feedback_reuse_existing_components`).
- L'agrégation backend peut être coûteuse si la BAL contient des dizaines
  de milliers de mails non-lus. Limiter le périmètre au folder `INBOX`
  pour la v1 (les autres folders ne sont pas pertinents pour ce widget).
- Si `IntegrationStatus` ou `BiologySeverity` sont coûteux à calculer en
  agrégation directe, accepter une **lecture à 2 temps** (1 query patients
  + 1 query enrichissement par batch) — le coût d'un appel REST agrégé
  reste acceptable pour 5 → 20 lignes.
- Pas de pagination réelle (curseur) sur cet endpoint — un simple `limit`
  croissant suffit pour le besoin "voir plus" jusqu'à 20.
- L'action "Filtrer mails sur ce patient" réutilise le mécanisme de
  filtrage par patient/INS déjà en place dans la BAL (cf. v1.24 — la
  recherche avancée connaît déjà le filtre patient). Pas de nouveau
  paramètre query à introduire.
