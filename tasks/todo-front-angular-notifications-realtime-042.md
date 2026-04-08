# todo-front-angular-notifications-realtime-042 — Angular : affichage temps-réel des notifications (via SSE)

**Dependencies**: todo-back-notifications-realtime-040
**Feature**: tests/Features/Mss/PreferencesNotification.feature
**Repo**: client-angular (path: `Client/Angular`) — **EXCLU de la forge, implémentation manuelle par le PO**
**Module**: Client/Angular/front/libs/mss

## Contexte

Le repo Angular est sur TFS et n'utilise pas SignalR (contrairement au Blazor). La tâche `done-front-angular-notifications-024` a livré les toggles dans `mss-settings.component`, mais **aucune notification n'est jamais déclenchée** — comme pour Blazor, la feature livrée n'est qu'une persistance de préférences.

Cette tâche rend la feature visible côté Angular **sans introduire SignalR** en utilisant **Server-Sent Events (SSE)** via l'API native `EventSource` du navigateur. Aucune nouvelle dépendance npm à ajouter.

**Note sur l'exécution** : ce repo est exclu de la forge. Le PO implémente manuellement, pas d'agent dev forge. Cette tâche est une **spec**, pas un contrat de dispatch orchestrator.

## Objectif

Quand le backend émet une notification (cf. tâche 040) sur son endpoint SSE `/api/v1/mail/notifications/stream`, afficher à l'utilisateur Angular le toast et la notification desktop selon ses préférences — parité fonctionnelle avec Blazor.

> **Note PO 2026-04-08** : la feature "notification sonore" a été ABANDONNÉE (cf. `questions/answered/041-notification-mp3-asset.md`). Aucun asset audio, aucun toggle, aucune logique son côté Angular. Seuls le toast et la notification desktop subsistent.

## Pourquoi SSE et pas SignalR

| Critère | SSE | SignalR JS | WebSocket natif |
|---|---|---|---|
| Nouvelle dépendance npm | ❌ aucune (`EventSource` natif) | ✅ `@microsoft/signalr` | ❌ aucune |
| Protocole | HTTP/1.1 long-lived | Multi-transport (WS/SSE/polling) | WebSocket upgrade |
| Reconnection auto | ✅ intégrée | ✅ intégrée | ❌ manuel |
| Unidirectionnel suffisant ? | ✅ oui (server → client seulement) | ✅ | ✅ |
| Proxy/firewall friendly | ✅ très | ⚠️ selon transport | ⚠️ selon infra |
| Compat Angular actuel | ✅ natif | ❌ ajout lib | ✅ natif |

**Décision PO** : SSE. Pas de négo.

## Travail à réaliser

### 1. Modèle TypeScript

Créer `front/libs/mss/src/core/models/notification-payload.model.ts` :
```typescript
export type NotificationKind = 'NewMail' | 'AbnormalBiology';

export interface NotificationPayloadDto {
  kind: NotificationKind;
  title: string;
  body: string;
  mailUid: number;
  folderPath: string;
  receivedAt: string;
  urgency: 'Normal' | 'Urgent' | 'Critical';  // aligner avec backend UrgencyLevel
  showDesktop: boolean;
}
```

Exporter depuis `front/libs/mss/src/core/index.ts`.

### 2. Service `NotificationStreamService`

Créer `front/libs/mss/src/core/services/notification-stream.service.ts` :

```typescript
@Injectable({ providedIn: 'root' })
export class NotificationStreamService {
  private eventSource?: EventSource;
  private readonly _notification$ = new Subject<NotificationPayloadDto>();
  readonly notification$ = this._notification$.asObservable();
  readonly connected = signal(false);

  constructor(
    @Inject(API_BASE_URL) private apiBase: string,
    private authService: AuthService,  // à brancher sur le service auth existant
  ) {}

  connect(): void {
    if (this.eventSource) return;

    const token = this.authService.getToken();
    const url = `${this.apiBase}/api/v1/mail/notifications/stream?token=${encodeURIComponent(token)}`;
    this.eventSource = new EventSource(url);

    this.eventSource.addEventListener('notification', (ev: MessageEvent) => {
      try {
        const payload = JSON.parse(ev.data) as NotificationPayloadDto;
        this._notification$.next(payload);
      } catch (e) {
        console.error('[NotificationStream] invalid payload', e);
      }
    });

    this.eventSource.onopen = () => this.connected.set(true);
    this.eventSource.onerror = () => {
      this.connected.set(false);
      // EventSource reconnecte automatiquement
    };
  }

  disconnect(): void {
    this.eventSource?.close();
    this.eventSource = undefined;
    this.connected.set(false);
  }
}
```

Points clés :
- **Authentification** : `EventSource` natif ne supporte pas les headers custom → token en query param. Côté backend (tâche 040), accepter ce query param comme fallback à l'auth JWT.
- Le `Subject` est `private`, seul `notification$` (Observable) et `connected` (signal) sont exposés.
- `connect()` est idempotent.

### 3. Composant `NotificationDispatcherComponent`

Composant invisible (standalone, OnPush) qui écoute le flux et dispatche vers les APIs d'affichage. À créer dans `front/libs/mss/src/core/components/notification-dispatcher/` :

```typescript
@Component({
  selector: 'mss-notification-dispatcher',
  standalone: true,
  template: '',  // invisible
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationDispatcherComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  constructor(
    private stream: NotificationStreamService,
    private snackbar: SnackbarService,  // service existant du design system Weda
  ) {}

  ngOnInit() {
    this.stream.connect();
    this.stream.notification$
      .pipe(takeUntil(this.destroy$))
      .subscribe(payload => this.handle(payload));
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    this.stream.disconnect();
  }

  private handle(payload: NotificationPayloadDto): void {
    // 1. Toast (toujours, pas de filtrage local — backend a déjà filtré)
    this.snackbar.info(payload.title, { description: payload.body, duration: 6000 });

    // 2. Desktop notification si autorisé par le payload
    if (payload.showDesktop && 'Notification' in window && Notification.permission === 'granted') {
      const n = new Notification(payload.title, { body: payload.body, icon: '/favicon.ico' });
      setTimeout(() => n.close(), 8000);
    }
  }
}
```

### 4. Intégration dans AppComponent

Ajouter `<mss-notification-dispatcher />` dans le template root (`front/apps/weda2/src/app/app.component.html` ou équivalent), conditionnellement au fait qu'un user est authentifié :

```html
@if (authService.isAuthenticated()) {
  <mss-notification-dispatcher />
}
```

### 5. Demande de permission desktop

Vérifier que `mss-settings.component.ts` (livré dans done-front-angular-notifications-024) appelle bien `Notification.requestPermission()` quand le toggle "Notifications bureau" est activé. Si non, ajouter l'appel. Sinon, rien à faire.

### 6. Tests

**Vitest unitaires** :
- `NotificationStreamService` : mock de `EventSource` via jsdom, vérifier que le parse JSON fonctionne, que les erreurs sont loggées, que `disconnect()` ferme bien le channel
- `NotificationDispatcherComponent` : mock du stream + du SnackbarService, vérifier les 2 branches (toast toujours, desktop conditionnel)

**Manuel** (à documenter dans le ticket TFS avant merge) :
- Ouvrir l'app Angular, s'authentifier
- Vérifier dans les DevTools → Network → que la connexion SSE est ouverte (type `eventsource`, status `200 pending`)
- Envoyer un mail au user de test depuis un autre client MSS
- Vérifier : snackbar apparaît, notification desktop apparaît (si permission)

## Definition of Done

- [ ] Build passes (`npm run build` dans `front/`)
- [ ] Tests Vitest passent (`npm test` dans `front/`)
- [ ] `NotificationPayloadDto` (TS) aligné avec le DTO backend
- [ ] `NotificationStreamService` standalone, reconnection auto fonctionnelle
- [ ] `NotificationDispatcherComponent` OnPush, standalone, intégré dans `AppComponent`
- [ ] Test manuel : toast et desktop fonctionnent avec un mail réel (captures d'écran dans le ticket TFS)
- [ ] Aucune nouvelle dépendance npm ajoutée (`package.json` inchangé côté dependencies, sauf ajout éventuel de types si TS strict l'impose)
- [ ] data-testid : `notification-dispatcher` sur le composant (même s'il est invisible, utile pour les tests e2e)
- [ ] Standalone component, OnPush, Angular Signals — respect des conventions du projet
- [ ] Pas de régression sur les features existantes (drafts, folders, signature, settings)

## Notes

- **Ce repo est exclu de la forge** — pas de dispatch d'agent dev forge. Le PO (humain) implémente, pousse sur une feature branch TFS, crée la PR manuellement.
- Le backend (tâche 040) doit être déployé et fonctionnel **avant** de pouvoir tester en bout-en-bout côté Angular. Les deux tâches peuvent être développées en parallèle mais l'intégration E2E nécessite le backend.
- Si le backend refuse le query param `?token=...` (pour raisons de sécurité, tokens dans URL loggués par les proxies), l'alternative est : créer un endpoint `POST /api/v1/mail/notifications/stream-ticket` qui retourne un ticket éphémère utilisable une seule fois dans l'URL du stream. À négocier avec le dev backend si le reviewer le demande.
- Le filtrage selon les préférences utilisateur est fait **côté backend** (tâche 040). Pas de logique locale Angular à écrire pour "est-ce que ce toggle est activé ?" — si le backend a envoyé le payload, c'est que l'événement doit être affiché.
