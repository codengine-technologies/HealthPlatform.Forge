# todo-front-angular-clinical-notifications-048 — Angular : NotificationCard cliniquement riche + Notification Center + DND consultation (SPEC, manuel TFS)

**Dependencies**: todo-back-clinical-notifications-046 (DTO v2 publié)
**Repo**: client-angular (path: `Client/Angular`) — **EXCLU de la forge, implémentation manuelle par le PO**
**Module**: Client/Angular/front/libs/mss
**Feature**: tests/Features/Mss/PreferencesNotification.feature

## Contexte

Ce repo est sur TFS, exclu de la forge. Cette tâche est une **spec**, pas un contrat de dispatch orchestrator. Elle est le miroir Angular de `todo-front-blazor-clinical-notifications-047`.

`todo-front-angular-notifications-realtime-042` (toujours en attente d'implémentation manuelle) couvrait la plomberie SSE. Cette tâche remplace son toast snackbar générique par la même expérience cliniquement riche que côté Blazor (cf 047), pour garantir la parité fonctionnelle Blazor/Angular.

## Travail à réaliser

Mêmes principes que 047, transposés Angular. Résumé :

### 1. Modèles TS étendus

Aligner `notification-payload.model.ts` sur le `NotificationPayloadDto` v2 du backend (cf 046) — **rupture** avec celui prévu dans 042.

### 2. Composant `NotificationCardComponent`

Standalone, OnPush, signals.
- Couleurs/icônes par sévérité (Critical / Urgent / Abnormal / Routine / Info)
- Bandeau patient en gras
- Tableau de findings avec mise en valeur Critical/High/Low
- Boutons générés depuis `payload.suggestedActions`
- `data-testid` : `notification-card-{notificationId}`, `notification-card-action-{code}`

### 3. Service `NotificationStackService`

Injecté providedIn root. `Signal<NotificationPayloadDto[]>` exposé. Add/remove/clear avec max 3 visibles.

### 4. Composant `NotificationStackComponent`

Standalone. Affiche la pile via `@for` sur le signal du service. Position fixed top-right (à valider PO). Intégré dans `app.component.html`.

### 5. Refonte `NotificationDispatcherComponent` (livré par 042)

Au lieu d'appeler le snackbar, alimenter le `NotificationStackService`. Garder le JS interop desktop + le son. Choix du son depuis `payload.soundProfile`.

### 6. Notification Center

Composant `NotificationCenterComponent` (drawer) accessible via cloche dans le header.
- Badge depuis `GET /api/v1/mail/notifications/unread-count`
- Liste paginée filtrable (severity, patient, date, state)
- Service `NotificationCenterService` qui consomme les endpoints REST de 050
- Polling 30s ou push via SSE — choix à confirmer (cf 047)

### 7. DND consultation

Service `ConsultationStateService` (signal). Trigger sur route `/patient/:id`. Filtrage dans `NotificationDispatcherComponent`.

### 8. Privacy mode

Toggle Angular dans `mss-settings.component`. Utilisation de `payload.patient.maskedName` quand actif.

### 9. Widget dashboard `ClinicalNotificationsWidgetComponent` (décision PO 2026-04-08)

Miroir Angular de la section 7 de 047. Ajouter un widget dédié au dashboard Angular pour exposer les alertes cliniques en première vue, **sans toucher aux widgets dashboard existants**.

Spécification fonctionnelle :
- Source de données : `GET /api/v1/mail/notifications?severity=Critical,Urgent&includeStates=unread&page=1&pageSize=5`
- Top 5 unread, tri récent → ancien
- Card compacte (prop `compact` du `NotificationCardComponent`), 2 actions : `Voir` (navigue vers la route mail) + `Acquitter` (PATCH acknowledge)
- Header : titre i18n + badge rouge avec compteur Critical
- Footer : lien "Voir toutes les notifications" → ouvre le `NotificationCenterComponent` drawer (partager une instance via `NotificationCenterService.openPanel()`)
- Empty state explicite "Aucune alerte clinique en attente"
- Refresh : souscription au flux SSE existant (`NotificationStreamService` livré par 042) — reload max 1/2s, fallback poll 60s
- Optimistic UI sur Acquitter, rollback + toast erreur si échec REST
- Click sur la card (hors boutons) = équivalent au bouton Voir
- `data-testid` : `clinical-notifications-widget`, `clinical-notifications-item-{id}`, `clinical-notifications-action-view-{id}`, `clinical-notifications-action-ack-{id}`, `clinical-notifications-open-center`, `clinical-notifications-empty`, `clinical-notifications-critical-count`
- Standalone, OnPush, Angular Signals

**Intégration dashboard Angular** : à brancher dans la vue dashboard existante côté Angular (le PO humain identifiera l'équivalent Angular du `DashBoard.razor` Blazor — vraisemblablement un composant dashboard de `front/apps/weda2`). Si la structure dashboard n'existe pas encore côté Angular, **ne pas la créer dans cette US** : poser une question PO et bloquer le widget en attendant — le widget seul ne fait pas partie du périmètre d'invention de la home Angular.

### 10. Tests Vitest

Mêmes scénarios que 047 transposés Angular Testing Library + Vitest, **incluant** les tests du widget dashboard (empty state, 5 lignes max, badge Critical, action Acquitter optimistic + rollback, refresh sur réception SSE, click root navigue, footer ouvre le drawer).

## Definition of Done

- [ ] Build Angular passe (`npm run build` dans `front/`)
- [ ] Tests Vitest passent
- [ ] Modèles TS alignés sur le DTO v2 backend
- [ ] `NotificationCardComponent` rend les 5 sévérités
- [ ] `NotificationStackComponent` intégré dans `AppComponent`
- [ ] `NotificationCenterComponent` accessible via cloche header
- [ ] DND consultation actif sur route `/patient/:id`
- [ ] Privacy mode fonctionnel
- [ ] **`ClinicalNotificationsWidgetComponent` intégré dans le dashboard Angular** (zone alertes, à côté des widgets existants s'ils existent côté Angular)
- [ ] **Widgets dashboard Angular existants inchangés (zéro régression)**
- [ ] **`NotificationCardComponent` accepte une prop `compact`**
- [ ] **`NotificationStackComponent` ancrée top-right en desktop, full-width + swipe-to-dismiss en mobile (exception Critical)**
- [ ] Aucune nouvelle dépendance npm (rester sur EventSource natif + zone-less si possible)
- [ ] Standalone components, OnPush, signals
- [ ] data-testid sur tous les éléments interactifs
- [ ] Test manuel documenté dans le ticket TFS avec captures d'écran

## Manual Test Plan

Identique à 047 mais sur l'app Angular. Inclure dans le ticket TFS :
- Captures avant/après pour la card cliniquement riche
- Vidéo courte du DND consultation
- Capture du notification center filtré par "Critique"

## Questions ouvertes (mêmes que 047 + spécifiques Angular)

1. ~~Position `NotificationStack`~~ → **Tranchée par PO 2026-04-08 : top-right desktop, full-width swipe-to-dismiss mobile (Critical sticky).**
2. Trigger DND : route `/patient/:id` Angular est-elle la bonne signature ? Service consultation existant ? *(reste ouverte)*
3. Polling vs push pour unread-count *(reste ouverte)*
4. **Spécifique Angular** : intégration avec le design system Weda existant — quels composants atomiques réutiliser pour la card ?
5. **Spécifique Angular** : auth pour le notification center REST — token JWT déjà géré par interceptor ?
6. **Spécifique Angular dashboard** : la home Angular dispose-t-elle déjà d'une vue dashboard avec une zone "alertes" / "widgets" ? Si non, le widget `ClinicalNotificationsWidgetComponent` est-il à brancher ailleurs (page d'accueil, header de l'app), ou faut-il créer la home dashboard dans une US séparée ?

## Notes

- **Repo exclu de la forge** — pas de dispatch d'agent dev, le PO implémente manuellement, pousse sur une branche TFS, crée la PR manuellement.
- Le contrat DTO v2 est figé par 046 backend, donc cette spec peut démarrer dès que 046 est mergé.
- Conserver la parité fonctionnelle stricte avec 047 Blazor — toute divergence doit être justifiée et documentée dans le ticket TFS.
