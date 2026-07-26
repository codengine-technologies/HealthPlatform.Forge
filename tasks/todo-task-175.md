# todo-task-175.md — Fuite inter-praticiens sur le flux SSE : le broker d'évènements mail est clé par dossier, pas par boîte

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe surface HTTP).
> Finding vérifié sur pièces par le PO — voir « Preuve » ci-dessous.

## Objective

Cloisonner par praticien le flux d'évènements mail Server-Sent Events. Aujourd'hui
**le contenu de la boîte MSSanté d'un praticien est diffusé aux flux SSE des autres
praticiens connectés** : `SseMailEventBroker` est un singleton dont la table
d'abonnés est indexée sur le **seul nom de dossier** (`INBOX`, `Sent`, …), qui est
identique pour tout le monde. L'isolation base-par-praticien qui protège le reste
de l'API n'intervient pas ici : le fan-out a lieu **en mémoire, après** la lecture
des données.

**US backend-only (justification)** : le défaut est entièrement côté serveur
(clé d'abonnement). Les frontends consomment le flux inchangé — aucun contrat,
aucune URL, aucun payload modifié. Correctif invisible côté client, hormis la
disparition des évènements qui ne les concernaient pas.

### Preuve (état actuel du code)

- `src/Api/Controllers/V1/MailEventsController.cs:89-93` — les deux premiers
  brokers sont abonnés sur l'identité JWT, le troisième sur la query string :
  ```csharp
  using var notifSub = _notificationBroker.Subscribe(email);   // mssEmail (OK)
  using var syncSub  = _syncProgressBroker.Subscribe(email);   // mssEmail (OK)
  ISseMailEventSubscription? mailSub = !string.IsNullOrWhiteSpace(folder)
      ? _mailEventBroker.Subscribe(folder)                     // <-- dossier seul
      : null;
  ```
- `src/Application/Services/Implementation/SseMailEventBroker.cs:17` — la table
  d'abonnés n'a pas de dimension utilisateur :
  `ConcurrentDictionary<string, ImmutableArray<Subscription>>` clé = `folder`.
- `src/Application/Services/Implementation/SseMailEventBroker.cs:64-85` —
  `PublishAsync(folder, …)` écrit l'évènement à **tous** les abonnés du bucket.
- `src/Application/Extensions/ServiceCollectionExtensions.cs:85` — broker
  enregistré en **singleton** : le bucket est partagé par tout le process.
- `src/Api/Hubs/MailEnrichmentNotifier.cs:20,27,40` — les publications ne
  transportent que `folder`, jamais l'identité de la boîte d'origine.

Le contraste interne est net : `SseNotificationBroker.Subscribe(string userEmail)`
est correctement clé par praticien. Seul le broker mail a été oublié.

### Contenu attendu

1. **Clé d'abonnement composite** : le bucket doit être `(mssEmail, folder)` — ou
   toute forme équivalente garantissant qu'aucun évènement ne franchit la
   frontière de boîte. `mssEmail` provient **exclusivement** du claim JWT validé
   (contrat de sécurité task-022 déjà en place dans ce controller : toute query
   string `?email=` est ignorée par construction — ne pas régresser).
2. **Propagation côté publication** : `PublishEmailsEnrichedAsync` /
   `PublishTagsUpdatedAsync` et leurs appelants (`MailEnrichmentNotifier`, chaîne
   d'enrichissement IMAP) doivent porter l'identité de la boîte dont les mails
   sont issus. L'identité doit venir du contexte de la boîte réellement
   synchronisée, **pas** d'un `IHttpContextAccessor` (l'enrichissement tourne en
   arrière-plan, hors requête HTTP).
3. **Fail-close** : si l'identité de boîte est absente au moment de publier, ne
   diffuser à **personne** et journaliser une alerte — jamais de repli sur une
   diffusion large.
4. **Non-régression du nettoyage** : `Remove` / `SubscriberCount` / la boucle CAS
   doivent rester corrects avec la nouvelle clé (pas de bucket orphelin après
   déconnexion).

### Hors scope

- Refonte du transport SSE, passage à SignalR, changement d'URL ou de payload.
- Les brokers notification et sync-progress (déjà correctement cloisonnés).
- Le durcissement des autres endpoints de l'exploration (tasks séparées).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire **de cloisonnement** sur `SseMailEventBroker` : deux abonnés
      de boîtes différentes sur le **même** nom de dossier ; une publication pour
      la boîte A n'écrit **rien** dans le canal de B (ce test doit échouer sur le
      code actuel — le vérifier explicitement)
- [ ] Test unitaire : deux abonnés de la **même** boîte et du même dossier
      reçoivent bien l'évènement (pas de sur-correction)
- [ ] Test unitaire : publication sans identité de boîte → aucun abonné servi,
      alerte journalisée
- [ ] Test unitaire : après `Dispose` du dernier abonné d'une boîte, le bucket est
      retiré (`SubscriberCount` = 0, pas de fuite mémoire par boîte)
- [ ] Test d'intégration sur `GET /api/v1/mail/events/stream` : l'identité
      d'abonnement est bien issue du claim `mssEmail` et une query string
      `?email=` reste ignorée (contrat task-022 préservé)
- [ ] Aucune donnée de santé en clair dans les logs du broker (le log de
      publication ne cite ni sujet, ni INS, ni contenu — compteur + dossier +
      identité pseudonymisée uniquement)
- [ ] Aucun changement de contrat : URL, noms d'évènements et forme du payload
      inchangés (les trois frontends ne sont pas modifiés)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Ouvrir **deux navigateurs** (ou deux profils) authentifiés avec **deux
   praticiens MSSanté distincts** (deux `mssEmail` différents), chacun sur sa
   boîte de réception.
3. Sur chaque session, ouvrir les outils réseau et observer le flux
   `GET /api/v1/mail/events/stream?folder=INBOX` (type `text/event-stream`).
4. Envoyer un message MSSanté vers la boîte du **praticien A uniquement**, puis
   déclencher/attendre la synchronisation de A.
5. **Attendu** : le flux de A reçoit `EmailsEnriched` avec le message ; le flux de
   **B ne reçoit rien** (seuls ses heartbeats). Avant correctif, B reçoit
   l'évènement complet de A — sujet, expéditeur, contenu, documents CDA, INS.
6. Vérifier ensuite le fonctionnement nominal : chez A, l'arrivée d'un mail
   rafraîchit toujours la liste en temps réel (pas de régression d'UX), et un
   second onglet du **même** praticien A reçoit bien l'évènement.
7. Fermer les onglets, vérifier dans les logs le désabonnement propre
   (`remaining=0`) et l'absence de contenu médical dans les lignes de log.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité sur le cloisonnement des
  données de santé entre praticiens (exigences MSSanté et PGSSI-S
  confidentialité / contrôle d'accès) — aucune nouvelle exigence adressée
- **INS** : non applicable en tant que traitement nouveau — mais l'INS figure
  dans le payload fuité (`PatientInsMatricule`), ce qui qualifie l'incident
- **Authentification PS** : inchangée (PSC / e-CPS, claim `mssEmail` du JWT
  validé, niveau eIDAS substantiel) — le correctif **renforce** l'usage de cette
  identité comme clé de cloisonnement
- **Habilitations** : inchangées — aucun contrôle RPPS / profession ajouté
- **Interop CI-SIS** : non applicable — transport interne SSE, pas un échange
  CI-SIS ; les documents CDA transportés restent inchangés
- **Tracé PGSSI-S** : abonnement / désabonnement au flux et publication
  (compteurs) journalisés **sans donnée de santé** ; conservation selon la
  politique de journalisation existante du repo. Ajouter une alerte sur
  publication sans identité de boîte (fail-close)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS cible de `api-mail`
- **AIPD / impact RGPD** : **à mettre à jour** — le défaut constitue une
  divulgation de données de santé à des tiers non autorisés (praticiens tiers).
  Qualifier la portée réelle (environnements concernés, fenêtre d'exposition,
  nombre de praticiens simultanés) avec le DPO et statuer sur la notification
  CNIL au titre de la violation de données. **Cette qualification est un
  livrable de la task, distinct du correctif technique.**
