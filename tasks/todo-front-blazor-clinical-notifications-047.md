# todo-front-blazor-clinical-notifications-047 — Blazor : NotificationCard cliniquement riche + Notification Center + DND consultation

**Dependencies**: todo-back-clinical-notifications-046 (DTO v2 publié)
**Repo**: client-blazor (path: `Client/Blazor`)
**Module**: Client/Blazor/Src/Modules/Mss + Src/Component/Shared
**Feature**: tests/Features/Mss/PreferencesNotification.feature (étendre via PO si besoin)

## Contexte

`done-front-blazor-notifications-realtime-041` a livré la plomberie : `MailHubService` souscrit à `NotificationReceived`, `NotificationDispatcher` route vers Radzen toast + JS interop desktop + JS interop son. Le toast est générique : titre + body, c'est tout.

Cette tâche remplace ce toast par un **NotificationCard cliniquement riche**, ajoute un **Notification Center** (cloche dans le header avec badge non-lu), et un **DND consultation** (auto-trigger quand un dossier patient est ouvert).

## Travail à réaliser

### 1. Composant `NotificationCard.razor`

Créer `Src/Modules/Mss/Plugin/Components/NotificationCard.razor` (et `.razor.css`).

Layout (déclinaisons par sévérité avec couleur de bordure et icône) :

```
┌─[badge sévérité]──────────────────────────[time]─[×]─┐
│                                                       │
│ [👤] Mme MARTIN Sophie, 67 ans   #12345              │
│                                                       │
│ Ionogramme sanguin                                   │
│ ─────────────────                                    │
│ ⚠️ K+ = 6.8 mmol/L  (N: 3.5-5.0)                     │
│ ⚠️ Créatinine = 215 µmol/L                            │
│                                                       │
│ Dr DUPONT, Biologiste — Labo Cerba                  │
│ Prélevé 08/04 09:14                                  │
│                                                       │
│ [📋 Ouvrir dossier] [📞 Rappeler] [⏰ Snooze] [✓ OK] │
└──────────────────────────────────────────────────────┘
```

Spécifications :
- Couleur bordure : `Critical = #d32f2f`, `Urgent = #f57c00`, `Abnormal = #fbc02d`, `Routine = #1976d2`, `Info = #757575`
- Icône en tête : `🔴 / 🟠 / 🟡 / 🔵 / ⚪`
- Patient en gras, taille +1
- Findings : tableau si `KeyFindings.Count > 1`, sinon ligne unique
- Findings critiques (Flag = CriticalHigh / CriticalLow) → en rouge gras avec ⚠️
- Findings High/Low → en orange
- Findings Normal → en gris
- Conclusion (imagerie/consult) : citation italique sous le titre
- Boutons d'action : générés depuis `payload.SuggestedActions[]`, pas hardcodés
- `data-testid` : `notification-card-{NotificationId}` sur le root, `notification-card-action-{Code}` sur chaque bouton
- `Critical` → sticky (pas de auto-dismiss), demande un acquittement explicite via le bouton OK
- `Urgent` → auto-dismiss après 30s
- `Routine`/`Info` → auto-dismiss après 8s

### 2. Refonte `NotificationDispatcher`

Étendre `Src/Modules/Mss/Plugin/Services/NotificationDispatcher.cs` (livré par 041) :
- Ne plus appeler `NotificationService.Notify(...)` (Radzen générique)
- À la place : utiliser un `NotificationStackService` (singleton, scopé app) qui maintient une `ObservableCollection<NotificationPayloadDto>` représentant la pile de cards visibles
- Le composant `NotificationStack.razor` (nouveau) consomme cette pile et rend une `NotificationCard` par item
- Le JS interop desktop utilise `payload.Title` + un body construit depuis `Patient.MaskedName + " — " + Document.DocumentType + KeyFindings.Length`
- Le son est choisi depuis `payload.SoundProfile` :
  - `critical` → `/sounds/notification-critical.mp3`
  - `urgent` → `/sounds/notification-urgent.mp3`
  - `soft` → `/sounds/notification-soft.mp3` (les 3 fichiers à demander au PO via question)

### 3. NotificationStack — où l'afficher

Composant `<NotificationStack />` à intégrer dans `Src/Component/Shared/Layout/MainLayout.razor` (à côté du `<NotificationHost />` existant). Position fixed top-right ou bottom-right avec un z-index élevé. Largeur 400px max.

Vide → invisible. Une pile verticale empilable (max 3 visibles, le reste dans le notification center).

### 4. Notification Center

Composant `Src/Modules/Mss/Plugin/Components/NotificationCenter.razor` :

- Bouton **cloche** dans le header de l'app shell (à intégrer dans le layout existant)
- Badge rouge avec compteur `unread-count` (issu de `GET /api/v1/mail/notifications/unread-count` — endpoint livré par 050)
- Click → ouvre un panneau latéral droit avec :
  - Filtres : sévérité (chips), patient, date range, état (unread/read/all)
  - Liste paginée de `NotificationCard` rendues en mode "compact" (pas d'actions, juste click pour ouvrir le mail/dossier)
  - Bouton "Marquer tout comme lu"
- Service `NotificationCenterService` : appelle les endpoints REST de 050 (GET liste, PATCH read/ack/snooze/dismiss)
- Polling de l'unread-count toutes les 30s (à défaut d'event push, ou utiliser le canal SignalR existant pour un event `NotificationCenterUpdated`)

### 5. DND consultation

Service `IConsultationStateService` (peut déjà exister — vérifier sinon créer dans `Src/Modules/Patient` ou équivalent).

Logique :
- Quand l'app navigue sur une route patient (ex: `/patient/{id}`) → `IConsultationStateService.IsInConsultation = true`
- Quand on quitte cette route → `false`
- `NotificationDispatcher` interroge `IConsultationStateService` avant d'afficher chaque card :
  - Si `IsInConsultation = true` ET `payload.RespectDnd = true` → ne pas afficher en pop-up, mais mettre quand même dans le Notification Center
  - Si `IsInConsultation = true` ET `payload.RespectDnd = false` (Critical/Urgent) → afficher
- Quand on quitte la consultation → afficher un toast récap "X notifications reçues pendant la consultation" cliquable pour ouvrir le notification center

### 6. Privacy mode

Toggle "Mode visible" dans `SettingsComponent` (déjà existant côté toggles notifs) :
- Si activé : les cards utilisent `Patient.MaskedName` au lieu de `Patient.FullName`
- Persisté dans `NotificationPreferences` via le toggle existant (étendre la DTO si besoin — coordonner avec backend)
- Le JS interop desktop utilise `MaskedName` quand le mode est activé

### 7. Widget dashboard `ClinicalNotificationsWidget` (décision PO 2026-04-08)

Ajouter un nouveau widget dédié dans le dashboard pour exposer les alertes cliniques en première vue, sans toucher aux widgets existants `MailNotificationWidget` et `AbnormalBiologyWidget`.

**Fichiers à créer** :
- `Src/Modules/Mss/Plugin/ClinicalNotificationsWidget.cs` : implémente `IAlertWidget` (zone `dashboard-alerts`)
  - `Title = "WidgetClinicalNotificationsTitle"` (clé i18n à ajouter)
  - `Icon = "fa-bell-exclamation"`
  - `EntryComponent = typeof(ClinicalNotificationsWidgetComponent)`
- `Src/Modules/Mss/Plugin/Widgets/ClinicalNotificationsWidgetComponent.razor` (+ `.razor.css`)

**Enregistrement** : ajouter `services.AddSingleton<IAlertWidget, ClinicalNotificationsWidget>()` dans le module bootstrap MSS (suivre le pattern de `AbnormalBiologyWidget`).

**Comportement du composant** :
- Au mount : appelle `NotificationCenterService.ListAsync(filter)` avec :
  - `Severity = [Critical, Urgent]`
  - `IncludeStates = [unread]`
  - `Page = 1, PageSize = 5`
- Affiche un **état vide** explicite si la liste est vide : icône `fa-check-circle`, libellé i18n `WidgetClinicalNotificationsEmpty` ("Aucune alerte clinique en attente")
- Affiche un **état de chargement** via `LoadingSpinner` (cohérent avec les autres widgets)
- Pour chaque notification, rend une **`NotificationCard` en mode compact** (nouvelle prop `Compact="true"` à ajouter au composant `NotificationCard.razor`) :
  - Pas de pile de findings détaillée (juste le 1er finding critique le plus parlant)
  - 2 actions maxi : `Voir` (navigue vers `/mail/{MailUid}`) et `Acquitter` (PATCH `/api/v1/mail/notifications/{id}/acknowledge`)
  - Bordure colorée selon sévérité (cohérent avec mode plein)
- **Header du widget** : titre + badge rouge avec le compteur Critical si > 0 (issu d'un `Where(n => n.Severity == "Critical").Count()` côté client sur les 5 chargées, ou via un appel séparé `unread-count?severity=Critical` si l'endpoint l'accepte)
- **Footer** : lien `<a>` "Voir toutes les notifications" qui déclenche l'ouverture du `NotificationCenter` panel (le composant cloche déjà ajouté au header du shell, partager une instance via `NotificationCenterService.OpenPanel()`)
- **Refresh temps réel** : souscrire à `MailHubService.NotificationReceived` (canal existant 040) — à la réception d'un payload de sévérité Critical ou Urgent, recharger la liste (max 1 reload/2s pour éviter le flood). Fallback : poll toutes les 60s.
- **Action Acquitter** : optimistic UI — retirer la ligne immédiatement, rollback si l'appel REST échoue (afficher un toast erreur via `NotificationService` Radzen).
- **Click sur la card** (hors boutons) : équivalent au bouton `Voir`.
- **Disposable** : annuler les souscriptions et CTS au dispose (cohérent avec les widgets existants).

**`data-testid`** :
- Root : `clinical-notifications-widget`
- Compteur Critical : `clinical-notifications-critical-count`
- Chaque ligne : `clinical-notifications-item-{NotificationId}`
- Bouton Voir : `clinical-notifications-action-view-{NotificationId}`
- Bouton Acquitter : `clinical-notifications-action-ack-{NotificationId}`
- Footer link : `clinical-notifications-open-center`
- État vide : `clinical-notifications-empty`

**i18n — clés à ajouter** :
- `WidgetClinicalNotificationsTitle` = "Alertes cliniques"
- `WidgetClinicalNotificationsEmpty` = "Aucune alerte clinique en attente"
- `WidgetClinicalNotificationsViewAll` = "Voir toutes les notifications"
- `WidgetClinicalNotificationsActionView` = "Voir"
- `WidgetClinicalNotificationsActionAck` = "Acquitter"
- `WidgetClinicalNotificationsCriticalBadge` = "{0} critique(s)"

**Important** :
- Ne PAS modifier `MailNotificationWidget` ni `AbnormalBiologyWidget` — ils gardent leur logique propre.
- Le widget consomme exclusivement le **notification center Redis** via les endpoints REST de 050. Aucun appel IMAP ni `BiologyService` direct.

### 8. Position de la NotificationStack et comportement mobile (décisions PO 2026-04-08)

- **Position desktop** : `NotificationStack` est ancrée **top-right** (z-index élevé, 16px de marge avec le bord). Décision PO pour ne pas entrer en collision avec le footer / actions principales en pied de page.
- **Mobile** (breakpoint à aligner avec le reste du shell, ex `< 768px`) : la `NotificationCard` passe en **full-width** (marges latérales 8px) avec **swipe-to-dismiss horizontal** :
  - Swipe gauche/droite → dismiss + appel `dismiss` REST
  - **Exception Critical** : le swipe est ignoré, seul le bouton OK acquitte (Critical reste sticky en toute circonstance)
- L'animation de swipe utilise les helpers Blazor existants ou un petit JS interop dédié si nécessaire.

### 9. Tests

**Unitaires** :
- `NotificationCardTests` (bUnit) : rendering selon chaque sévérité, présence des `data-testid`, click handlers sur les actions, **mode `Compact`**
- `NotificationStackServiceTests` : add/remove/clear, max 3 visibles
- `NotificationDispatcherTests` (existant 041, étendre) : DND consultation skip, sound profile selection, privacy mode masked name
- `NotificationCenterServiceTests` : appels REST mockés, unread count
- `ClinicalNotificationsWidgetComponentTests` (bUnit) : empty state, rendu de 5 lignes max, badge Critical, action Acquitter optimistic + rollback, refresh sur réception SignalR, click root navigue vers `/mail/{uid}`, footer ouvre le panel

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests passent (xUnit + bUnit)
- [ ] `NotificationCard` rend les 5 sévérités avec couleurs/icônes distinctes
- [ ] `data-testid` : `notification-card-{id}`, `notification-card-action-{code}`, `notification-center-bell`, `notification-center-badge`, `notification-stack`
- [ ] `NotificationStack` intégré dans `MainLayout.razor` et `Mobile/Layout/MainLayout.razor`
- [ ] `NotificationCenter` accessible via cloche dans le header, polling unread-count fonctionnel
- [ ] **`ClinicalNotificationsWidget` enregistré comme `IAlertWidget` et visible dans `dashboard-alerts`**
- [ ] **Widget dashboard : top 5 Critical+Urgent unread, refresh SignalR, action Acquitter optimistic, footer ouvre le NotificationCenter, empty state explicite**
- [ ] **Widgets existants `MailNotificationWidget` et `AbnormalBiologyWidget` inchangés (zéro régression visuelle ni fonctionnelle)**
- [ ] **`NotificationCard` accepte une prop `Compact`**
- [ ] **`NotificationStack` ancrée top-right en desktop, full-width + swipe-to-dismiss en mobile (exception Critical)**
- [ ] DND consultation : quand sur route `/patient/{id}`, `Routine`/`Info`/`Abnormal` ne pop pas mais arrivent au center ; `Critical`/`Urgent` pop quand même
- [ ] Privacy mode : toggle Settings, MaskedName utilisé sur cards et JS interop quand actif
- [ ] 3 fichiers audio (critical/urgent/soft) référencés (stubs si PO ne les a pas encore fournis, voir question 041 mp3)
- [ ] Aucun appel `new Notification(...)` direct en C# — tout via JS interop
- [ ] Aucune régression sur drafts/folders/signature/041 — tests existants passent
- [ ] Aucune chaîne hardcodée dans l'UI (tout via i18n)

## Manual Test Plan

1. `dotnet run --project Src/Shell/HealthPlatform.Shell.Wasm`
2. S'authentifier
3. Provoquer 5 notifications de test via le backend (voir Manual Test Plan de 046)
4. **Vérifier visuellement** :
   - Card Critical : bordure rouge, icône 🔴, sticky, K+ en rouge gras, bouton "📞 Rappeler" présent
   - Card Routine : bordure bleue, auto-dismiss à 8s
   - Cloche header : badge "5"
5. Click sur la cloche → notification center s'ouvre avec les 5
6. Filtrer par "Critique" → seule la critique reste affichée
7. Click sur "📋 Ouvrir dossier" sur la card critique → navigation vers `/patient/12345`
8. Pendant qu'on est sur `/patient/12345`, provoquer une notif Routine → ne doit PAS pop, mais le badge cloche doit incrémenter
9. Provoquer une notif Critical → doit pop même en consultation
10. Quitter la route patient → toast récap "1 notification reçue pendant la consultation"
11. Activer "Mode visible" dans Settings → re-provoquer une notif → vérifier que le nom du patient est masqué (`S.M.`) sur la card et la notif desktop
12. **Aller sur la vue Dashboard** → vérifier que :
    - Le widget "Alertes cliniques" est présent dans la zone alertes (à côté de Biologie anormale)
    - Il liste les notifications Critical+Urgent non lues (max 5)
    - Le badge rouge en header affiche le nombre de Critical
    - Cliquer "Acquitter" sur une ligne → la ligne disparaît immédiatement, l'unread count global décrémente
    - Cliquer une ligne (hors bouton) → navigation vers `/mail/{uid}`
    - Cliquer "Voir toutes les notifications" en footer → le NotificationCenter panel s'ouvre
    - Provoquer une nouvelle notif Critical → elle apparaît en tête du widget en < 2s (push SignalR)
    - Si aucune notif unread → état vide explicite affiché
13. **Vérifier non-régression** : les widgets `MailNotificationWidget` et `AbnormalBiologyWidget` existants affichent toujours leur contenu habituel

## Questions ouvertes

1. ~~**Position de la `NotificationStack`** : top-right ou bottom-right ?~~ → **Tranchée par PO 2026-04-08 : top-right.** Voir section 8.
2. **Trigger DND consultation** : route `/patient/{id}` est-elle la bonne signature ? Y a-t-il déjà un service `IConsultationStateService` à réutiliser ? *(reste ouverte — investigation dev nécessaire)*
3. **Polling unread-count** : 30s acceptable, ou push via SignalR `NotificationCenterUpdated` est obligatoire ? *(reste ouverte — décision technique)*
4. ~~**Mobile** : full-width, swipe-to-dismiss ?~~ → **Tranchée par PO 2026-04-08 : oui, full-width + swipe-to-dismiss avec exception Critical.** Voir section 8.
5. **i18n** : nouvelles clés à ajouter — sourcer depuis quel fichier de ressources ? *(reste ouverte — convention projet à confirmer)*
