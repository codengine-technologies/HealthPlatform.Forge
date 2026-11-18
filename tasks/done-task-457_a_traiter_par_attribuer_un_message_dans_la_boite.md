# todo-task-457.md — « À traiter par » : attribuer un message dans la boîte

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 1
**Dependencies**: done-task-454 (état « traité »)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. L'accès partagé est fait (douleur n° 6 : 5/5) ; il
manque le **travail à plusieurs dans la boîte**. Le pré-tri par le secrétariat est le levier le mieux documenté
(Michigan : −16 % de messages par médecin, −62 % de doublons ; tri administratif britannique : jusqu'à −80 % de
courrier sur le bureau du médecin).

> **Origine.** Analyse du 2026-11-11, manques C1 et C2. Demande explicite de l'humain du 2026-11-11 : « indiquer *à
> traiter par* : choisir le médecin affecté ou la secrétaire, pour que le message lui soit attribué ».

## Ce qui est établi

- **Aucun modèle ni endpoint d'attribution.**
- **Aucun endpoint ne liste les personnes rattachées à une boîte** : `/api/v1/account/mailboxes*` ne rend que les
  boîtes de l'utilisateur.
- La liste existe dans le registre commun : `RegistryTenantRow` (`MailboxId`, `Role`, `PersonFirstName/LastName`,
  `State`), lu par `PostgresTenantRegistryClient`.
- La base de la boîte ne connaît que le `sub` de la personne (`User.AuthenticationSubject`), sans nom ni RPPS. Les
  auteurs sont **dénormalisés** sur chaque ligne (`ActorNames`, comme `BiologyAck.CreatedBy*`).
- `NewMailNotifier` tourne en tâche de fond **sans personne** : il lit les réglages de la ligne boîte. Une notification
  destinée à une personne précise demande une résolution par personne.
- Rôles affichables : `MailboxRole` / `MAILBOX_ROLE_LABELS` (Titulaire, Membre, Délégation), `actorWithRole`
  (weda2).

## Objective

Sur n'importe quel message, une personne de la boîte indique **« À traiter par »** et choisit une personne rattachée à
cette boîte : le médecin titulaire, un confrère membre, la secrétaire délégataire. Le message lui est **attribué**. Il
apparaît dans sa vue **« Pour moi »**, et elle en est avertie.

Règles :
- **Choisir la personne** : la liste des personnes rattachées à la boîte et actives (verdict de l'opérateur valide),
  avec nom et rôle (« Dr Virginie MARTIN — titulaire », « Cyril DELEGUE — délégataire »). On ne saisit jamais un nom
  libre.
- **Une seule personne attribuée à la fois.** On peut réattribuer ou retirer l'attribution. Chaque geste est imputé.
- **Affichage** : « À traiter par {Prénom NOM} — attribué par {Prénom NOM} le … », sur la ligne (une pastille avec les
  initiales) et dans le détail.
- **Vue « Pour moi »** : les messages attribués à la personne connectée et non traités, avec un compteur. Sur weda2,
  dans l'arborescence au-dessus des tags système ; sur mobile, en puce et en tuile d'Accueil (flag
  `dashboard_widget_for_me`).
- **Avertir** : la personne attribuée reçoit une notification dans l'application, en direct si elle est connectée,
  sinon à sa prochaine ouverture (« Cyril DELEGUE vous a attribué un message »). Le contenu clinique n'est jamais dans
  la notification.
- **Traiter clôt l'attribution** : quand quelqu'un marque le message traité (task-454), il sort de « Pour moi ». Le
  détail garde « Attribué à … — traité par … ».
- **Une personne qui perd l'accès** (révocation, refus de l'opérateur) n'est plus proposée. Ses attributions en cours
  s'affichent « À traiter par {nom} (accès retiré) » et restent visibles dans « À traiter » de la boîte.
- **Groupé** : attribuer une sélection en une fois (weda2 et mobile).
- **Ancrage** selon task-453.

### Hors périmètre

- Attribution automatique par règle (ex. tout le « Pour info » à la secrétaire).
- Notes internes : task-458.
- Détection de collision (« Cyril rédige déjà une réponse »).

## Definition of Done

- [ ] Endpoint des personnes rattachées à la boîte (registre commun), limité aux personnes actives, accessible
      seulement aux personnes de cette boîte sous verdict valide.
- [ ] Attribution stockée dans la base de la boîte, ancrée selon l'ADR de task-453 ; migration FluentMigrator, audit
      (règle 7c).
- [ ] Contrat : personne attribuée, auteur et date dans `MailDto` ; vue « Pour moi » et compteur ; paquet DTO publié.
- [ ] Actes d'audit `MailAssigned`, `MailUnassigned` en fin de `AuditActionType`, miroirs TypeScript,
      `HealthDataAccess`.
- [ ] Notification ciblée sur **la personne attribuée** (pas sur la ligne boîte) : la résolution par personne est
      ajoutée et testée.
- [ ] Tests unitaires : attribuer, réattribuer, retirer, traiter clôt l'attribution, personne sans accès non proposée,
      attribution d'une personne qui a perdu l'accès.
- [ ] **Test d'intégration de bout en bout (règle 1b), deux personnes sur la même boîte** (règle 14), sur
      `PUT api/v1/Mail/emails/{id}/assignee` :
      - le titulaire attribue au délégataire ; le délégataire relit le message dans « Pour moi » ;
      - la trace porte le titulaire comme auteur et le délégataire comme objet ;
      - le délégataire traite, le message sort de « Pour moi » ;
      - cas d'échec : personne non rattachée à la boîte → 400 en `ProblemDetails`, rien n'est écrit.
      Vu rouge.
- [ ] Test d'intégration : une personne d'une **autre** boîte ne peut ni lister les personnes ni attribuer (403).
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : sélecteur « À traiter par », pastille, vue et
      compteur « Pour moi », notification, attribution groupée.
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-ASSIGN-001` v1 : le titulaire attribue un message à la secrétaire délégataire, qui le trouve dans « Pour
        moi » ;
      - `E2E-ASSIGN-002` v1 : traiter un message attribué le retire de « Pour moi » et affiche « traité par ».
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans la notification ni les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Boîte du médecin avec un délégataire secrétaire rattaché (environnement de formation). Titulaire sur weda2,
   secrétaire sur le mobile.
2. Titulaire : sur un courrier, « À traiter par » → la liste montre la secrétaire et le titulaire, avec leurs rôles.
   Choisir la secrétaire.
3. Mobile, secrétaire : la notification « Dr … vous a attribué un message » arrive ; la puce « Pour moi » compte 1.
4. Secrétaire : marquer le message traité. Titulaire : le détail dit « Attribué à … — traité par … ».
5. Attribuer trois messages d'un coup depuis la sélection groupée de weda2.
6. Révoquer la délégation chez l'opérateur : la secrétaire n'est plus proposée ; ses attributions en cours affichent
   « (accès retiré) ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du travail en cabinet
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; secrétaire par e-CPS (RPPS+)
- **Habilitations** : seules les personnes rattachées à la boîte, sous verdict récent de l'opérateur, sont proposées et
  peuvent attribuer (règle 14) ; le rôle vient du rattachement (Annuaire Santé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `MailAssigned`, `MailUnassigned` au nom de la personne qui agit, avec la personne attribuée en
  objet ; `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte et registre commun
- **AIPD / impact RGPD** : à mettre à jour — la liste des personnes d'une boîte est visible de chacune d'elles, et les
  attributions révèlent la répartition du travail

## Branches
- `api-mail` (pushed) : feat/task-457-a-traiter-par-attribuer-un-message-dans — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-457-a-traiter-par-attribuer-un-message-dans
- `client-mobile` (pushed) : feat/task-457-a-traiter-par-attribuer-un-message-dans — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-457-a-traiter-par-attribuer-un-message-dans
- `dtos-mss` (paresseuse) : aucune branche au /start — `/develop` la crée depuis `origin/develop` (feat/task-457-a-traiter-par-attribuer-un-message-dans) au premier contrat touché
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS
- Pré-flight : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk`, `interop-cda` sur `develop` ; `host` sans `.git` (noté) ; `api-mcp` (`Api/Mcp`) **absent du disque** — non listé par la task, mais `Tools/contracts/mcp_impact.py check` (Step 4c de /develop) en a besoin si api-mail ou dtos-mss touchent la surface consommée

## Timings

*(généré par `tools/timing/report.sh --task task-457 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 32 s | — | — | — | — |
| /develop | ok | 52 min 03 s | 16 (9 min 25 s) | 19 (1 h 12 min) | — | api-mail 9B/9T, client-angular 3B/6T, client-mobile 4B/4T, reprise 1 |
| /review-code | ok | 11 min 07 s | — | — | — | — |
| /sonar | ok | 41 min 19 s | 3 (1 min 38 s) | 12 (21 min 35 s) | 4 (5 min 49 s) | 2 itération(s), api-mail 3B/12T |
| /lint-angular | ok | 13 min 42 s | 1 (1 min 06 s) | 1 (6 min 28 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 1 min 34 s | — | — | — | — |
| /e2e | ok | 30 min 28 s | — | — | — | e2e ×7 (1 h 30 min) |
| /review | ok | 47 min 11 s | 3 (1 min 52 s) | 2 (10 min 10 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-mobile 1B/1T, e2e ×2 (31 min 45 s), sync develop (task-487) |
| /tech-writer | ok | 2 min 15 s | — | — | — | — |
| **Total cycle** | | **3 h 21 min** | **23 (14 min 02 s)** | **34 (1 h 50 min)** | **4 (5 min 49 s)** | |

Autres commandes mesurées : lint ×2 (2 min 09 s), nuget-wait ×3 (35 s), restore ×3 (26 s)

## Develop log

### Plan (2026-11-17, avant le code)

Ordre : dtos-mss, api-mail, weda2, mobile, e2e.

**Qui est une « personne de la boîte »** : un rattachement du registre commun (`mss_accounts`) de la même boîte
(`MailboxId`), à l'état **Active** (non détaché, pas `AuthFailing`). Un refus de l'opérateur pose `AuthFailing`, une
révocation détache : ces deux cas sortent la personne de la liste (règle 14). L'identifiant exposé est l'**identifiant
du rattachement** (`TenantId`, Guid opaque), jamais le `sub` Keycloak. La personne connectée est `UserContextInfo.TenantId`.
Nouvelle lecture du registre : `ITenantRegistryClient.ListActivePeopleOfMailboxAsync(mailboxId)`.

**Données** (base de la boîte) : table `MailAssignments`, une ligne par message (attribution courante), ancrée au
**Message-ID** sans chevrons comme `MailHandlingStates` (ADR task-453 l. 113 ; pas de clé étrangère vers `Mails`).
Colonnes : `MessageId` (unique), `AssigneeTenantId`, `AssigneeRpps/FirstName/LastName/Role` (dénormalisés : ils
affichent encore la personne après la perte d'accès), `ByRpps/FirstName/LastName/Role`, `At`, `SeenAt` (nul tant que la
personne attribuée n'a pas vu l'avis). Retirer = supprimer la ligne (le journal garde l'historique). Message sans
Message-ID : 409 `ProblemDetails`, comme task-454.

**« Traiter clôt l'attribution »** : l'attribution est **ouverte** tant qu'aucun état « traité » n'est posé **après**
elle (`MailHandlingStates.State = Handled` et `At >= attribution.At`). Attribuer un message déjà traité le rouvre pour
la personne. La ligne reste : le détail dit « Attribué à … — traité par … ».

**Routes** (`MailAssignmentController`, base `api/v1/Mail`) — la DOD écrit `emails/{id}/assignee` ; un message n'a pas
d'identifiant hors de son dossier dans ce contrat, la route suit donc la convention de task-454 :
- `GET mailbox/people` : les personnes actives de la boîte (nom, rôle, RPPS, `IsMe`).
- `PUT folders/{f}/emails/{uid}/assignee` `{ assigneeId }` : attribuer / réattribuer. Personne hors de la boîte → 400.
- `DELETE folders/{f}/emails/{uid}/assignee` : retirer.
- `PUT folders/{f}/emails/bulk/assignee` `{ uids, assigneeId }` : attribution groupée.
- `GET folders/{f}/emails/for-me/page` : la page des UID « Pour moi » (servie par le serveur, comme « À traiter »).
- `GET assignments/notices` et `PUT assignments/notices/seen` : les avis non vus (« à sa prochaine ouverture »).

**Contrat** (dtos-mss) : `MailAssignmentDto` (`AssigneeId`, `Assignee`, `By`, `At`, `IsOpen`, `IsMine`,
`AssigneeAccessRemoved`), `MailDto.Assignment`, `MailboxPersonDto`, `MailAssignRequestDto`,
`MailBulkAssignRequestDto`, `MailAssignmentBulkResultDto`, `MailAssignmentNoticeDto`, `FolderDto.ForMeCount`,
`InboxFilterType.ForMe`, `NotificationKind.MailAssigned` + `NotificationPayloadDto.RecipientId`,
`AuditActionType.MailAssigned = 75`, `MailUnassigned = 76`.

**Avertir la personne attribuée** : `NotificationPayloadDto` ciblé (`RecipientId` = son rattachement). Le broker de
notifications filtre à la livraison : un abonnement ne reçoit un avis ciblé que si son rattachement est le
destinataire (résolution par personne, pas par ligne boîte). Corps sans contenu clinique : « {Prénom NOM} vous a
attribué un message ». Hors ligne : l'avis reste non vu en base (`SeenAt` nul) et le client le montre à l'ouverture.

**Temps réel boîte** : évènement SSE `MailAssignmentChanged` (dossier, UID, `MailAssignmentDto`) pour mettre à jour la
pastille chez toutes les personnes ouvertes sur la boîte (`IsMine` recalculé côté client par `AssigneeId`).

**Audit** : `[TracedInCode(MailAssigned|MailUnassigned)]`, au nom de la personne qui agit, la personne attribuée en
objet (`ServerRequest` : `assignee={TenantId} rpps={RPPS}`), famille `HealthDataAccess` par défaut.

### Implémentation (2026-11-17)

- **dtos-mss** : contrat publié, paquet `622.0.0` (commit `28bf60ab`) ; api-mail bumpé (`88eca007`).
- **api-mail** (`212078e6`) : `MailAssignmentController` (7 routes), `MailAssignmentService`, `MailAssignmentRepository`
  (forme SQL de `MailAssignmentRule`), table `MailAssignments` (migration `20261117180000_AddMailAssignments`, `Down` =
  suppression de la table, **aucune donnée existante touchée** — règle 7c relue, point 5 sans objet),
  `ITenantRegistryClient.ListActivePeopleOfMailboxAsync`, `ForbiddenException` (403), broker des avis résolu par
  personne (`ISseNotificationBroker.Subscribe(email, personId)`), évènement SSE `MailAssignmentChanged`, compteur
  `FolderDto.ForMeCount`, audit `MailAssigned` / `MailUnassigned` (`HealthDataAccess`).
- **Écart à la DOD, assumé** : la route est `PUT folders/{f}/emails/{uid}/assignee` et non `emails/{id}/assignee` — un
  message n'a pas d'identifiant hors de son dossier dans ce contrat (convention de task-454).
- **Limite assumée** : « Pour moi » est servi pour la Boîte de réception (comme la tuile « À traiter »). Ranger un message
  le traite (task-454), donc il sort de « Pour moi » ; un message attribué depuis un autre dossier garde sa pastille
  mais n'entre pas dans la vue.

### Preuves rouges — api-mail (règle 1b), par mutation

Script `mutate.py` (scratchpad), build + test d'intégration ciblé par mutant, restauration depuis une copie datée du
jour (`RESTAURATION build 0`). Tests : `FolderOperationsEndToEndTests.Assignment` (UseCaseHttpHost, vraie pile HTTP,
PostgreSQL et Dovecot du fixture, vrai `PostgresTenantRegistryClient` sur la base commune, vrai `SseNotificationBroker`).

| Comportement | Mutation | Test vu rouge |
|---|---|---|
| `PUT …/assignee` écrit l'attribution | M1 non écrite | `TheHolderAssignsToTheDelegate_…` |
| « Pour moi » = la personne | M2 filtre de personne retiré | idem |
| traiter clôt l'attribution (SQL) | M3 condition neutralisée | idem |
| trace : la personne attribuée en objet | M4 objet retiré | idem |
| personne hors boîte → 400 | M5 acceptée | `AssigningToAPersonNotAttachedToTheMailbox_…` |
| demandeur hors boîte → 403 | M6 accepté | `APersonOfAnotherMailbox_…` |
| avis ciblé (destinataire) | M7 sans destinataire | `TheDelegateIsWarned_…` |
| relais résolu par personne | M8 filtre retiré | idem |
| avis marqués vus | M9 jamais | idem |
| « (accès retiré) » | M10 jamais signalé | `BulkAssignment_ThenTheDelegateLosesAccess_…` |
| registre : seules les personnes actives | M11 `AuthFailing` gardé | idem |
| `DELETE …/assignee` | M12 non fait | idem |
| compteur `ForMeCount` | M13 autre personne | `TheHolderAssignsToTheDelegate_…` |
| `IsMine` | M14 jamais vrai | idem |
| groupé : une trace par message | M15 une seule | `BulkAssignment_…` |

Tests unitaires : `MailAssignmentServiceTests` (15), `MailAssignmentRuleTests` (5), broker
(`Publish_AddressedNotification_ReachesTheRecipientsSessionsOnly_…`), contrat d'audit (75, 76) et rétention.

**Défaut de test trouvé et corrigé** (task-454, sur `develop`) : `TheBulkHandling_…` et
`TheToHandleCounterPageAndTagFilter_…` partageaient la boîte `4549` ; en collection, le compteur du second comptait les
messages du premier (8 au lieu de 4, selon l'ordre). Le premier a désormais sa boîte (`4553`).

**Flaky constaté** : `TenantRegistryIntegrationTests.AttachMailboxAsync_UnderConcurrency_PersistsExactlyOneTenant`,
rouge deux fois (suite complète puis seul), vert à la suite suivante ; code non touché par la task (le diff du registre
n'ajoute qu'une méthode).

### Passe qualité §Q — api-mail

- Vérifications mécaniques : 7 commentaires en « ; » (S125) réécrits ; aucun autre motif.
- Réutilisation : `HandlingActor.Of(UserContextInfo)`, partagé par `MailHandlingService` et `MailAssignmentService`
  (la personne qui agit se construisait deux fois).
- Re-validation : suite complète verte (domain 348, infrastructure 749, application 4299, api 1382, intégration 1353 —
  0 échec).
- Écarté (à mesurer avant) : mise en cache de la liste des personnes pour « (accès retiré) » (une lecture du registre par
  page qui porte des attributions).

### Preuves rouges — weda2 (tests de composant), par mutation

Script `mutate_w.py` (scratchpad), vitest ciblé par mutant, sources restaurées octet pour octet (restauration :
32/32 verts).

| Comportement | Mutation | Spec vue rouge |
|---|---|---|
| pastille aux initiales | W1 jamais affichée | `mail-header.assignment.spec` |
| sélecteur : choix émis | W2 | `mail-assignee-picker.component.spec` |
| sélecteur : « Retirer l'attribution » | W3 | idem |
| attribution posée sur la ligne | W4 | `mail-assignment.service.spec` |
| attribution groupée, une requête par dossier | W5 | idem |
| « c'est à moi » recalculé (SSE) | W6 | idem |
| avis en direct | W7 | idem |
| avis à l'ouverture | W8 | idem |
| « Pour moi » servi par le serveur | W9 | `mail-state.service.handling.spec` |
| compteur « Pour moi » | W10 | idem |
| entrée « Pour moi » de l'arborescence | W11, W12 | `mail-folder-list.for-me.spec` |
| « traité par », « (accès retiré) » | W13, W14 | `mail-assignment.util.spec` |

`mss-lib` : 1808/1808. `MssMailComponent` injecte le service en facultatif, comme le détail et la liste : onze specs
de l'écran remplacent ses fournisseurs.

### client-mobile

- Modèles et contrat (`MailAssignmentDto`, `MailboxPersonDto`, `forMeCount`, `SettingsInboxFilter.ForMe`,
  `NotificationKind.MailAssigned`, évènement `MailAssignmentChanged`), API (7 appels), `MailAssignmentService` (racine,
  porteur d'état de boîte : purgé à la bascule), puce « Pour moi » (segment du filtre, compteur du serveur), pages servies
  par le serveur comme « À traiter » (`isServerFilteredInbox`), pastille de la ligne, « À traiter par » dans le détail
  (`ion-select` en feuille d'actions, « Retirer l'attribution »), attribution groupée depuis la sélection, avis en toast
  (en direct et à l'ouverture), tuile d'Accueil « Pour moi » derrière `dashboard_widget_for_me` (flag ajouté côté
  api-mail : constante, repli ouvert, semis du banc).
- Traiter un message le sort aussi de « Pour moi » (les deux clients : `applyHandling`).
- Specs mises à jour : les bouchons de `MailEventsStreamService` et de l'API des trois specs de la page Messages
  (flux `assignmentChanged$`, `getMailboxPeople`, `getAssignmentNotices`).

### Preuves rouges — client-mobile (specs Jasmine), par mutation

Script `mutate_m.py` (scratchpad), Karma ciblé par mutant, sources restaurées octet pour octet (restauration :
740/740 verts sur `features`).

| Comportement | Mutation | Spec vue rouge |
|---|---|---|
| pastille aux initiales | X1 jamais affichée | `mail-header.assignment.spec` |
| attribution posée sur la ligne | X2 | `mail-assignment.service.spec` |
| groupé, une requête par dossier | X3 | idem |
| « c'est à moi » recalculé (SSE) | X4 | idem |
| avis en direct | X5 | idem |
| avis à l'ouverture | X6 | idem |
| « Pour moi » servi par le serveur | X7 | `mail-state.for-me.spec` |
| réattribué : sort de « Pour moi » | X8 | idem |
| traité : sort de « Pour moi » | X9 | idem |
| tuile : compteur « Pour moi » | X10 | `for-me-tile.component.spec` |
| tuile : ouvre « Pour moi » | X11 | idem |
| réglage par défaut « Pour moi » | X12 | `mail-state.for-me.spec` |

### Parcours e2e — catalogue et tests

- Catalogue (`Api/Mail/e2e/scenarios.yml`, relu par `yaml.safe_load`, 96 scénarios) : `E2E-ASSIGN-001` v1 et
  `E2E-ASSIGN-002` v1, `clients: mobile requis, angular requis`, seed `[delegataire, boite-praticien]` (aucune donnée
  ajoutée au seed : les messages sont déposés par le test, d'objet unique, et retirés en fin d'essai).
- Tests : `Client/Mobile/e2e/specs/functional.spec.ts` et `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts`
  (aides `forMeUids`, `OtherDevice.mailboxPeople`, `OtherDevice.assign`). Chaque test juge l'état **relu du serveur**
  (`etat-optimiste`), arme l'attente de la réponse avant le geste, et prouve la présence d'avant ses absences
  (`precondition-du-negatif` : non attribué au départ, dans « Pour moi » avant d'être traité). Sélecteurs selon
  `selecteur-de-controle-de-formulaire` (mobile : `ion-action-sheet` → `radio` ; weda2 : `<select>` natif). Les deux
  suites compilent (`tsc`) ; weda2 : ESLint 0 erreur après Prettier.

### Parcours e2e — voie mobile (`--serve-only`, scénarios seuls)

`conventions/e2e.md` lu avant l'écriture des tests (`etat-optimiste`, `precondition-du-negatif`,
`selecteur-de-controle-de-formulaire`, `depot-hors-application`).

Premier passage : ASSIGN-001 rouge (option « Cyril DELEGUE — délégataire » introuvable), ASSIGN-002 rouge
(« Attribué à 90000009003 »). **Défaut réel trouvé par le parcours** : le registre n'enregistre le nom d'une personne
qu'à sa première requête sur la boîte (`PersonNameResolver`, middleware), pas au rattachement ; une attribution posée
avant gardait le RPPS pour tout nom.
- Correctif serveur (`eb6d9a10`) : la ligne nomme une personne encore active comme le registre la nomme aujourd'hui ;
  une personne qui a perdu l'accès garde le nom recopié. Test d'intégration `BulkAssignment_…` (renommage au registre
  relu dans la réponse), mutation **M16** (nom figé à l'attribution) rouge ; test unitaire
  `ApplyAsync_AnActiveAssignee_IsNamedAsTheRegistryNamesHerToday`.
- Parcours : la délégataire ouvre la boîte dans son application juste après son rattachement, comme l'écran le fait
  (consigne `personne-nommee-a-sa-session` ajoutée à `conventions/e2e.md`).
- **Limite constatée, non corrigée** : une personne rattachée sans avoir encore ouvert la boîte est proposée par son RPPS
  dans « À traiter par ». En pratique l'application ouvre la boîte dès le rattachement ; enregistrer le nom au
  rattachement (`MailboxManagementService`) est hors du périmètre de la task (à juger en revue).
- Durcissement : ASSIGN-001 dépose un second message à traiter, non attribué, et affirme son absence de « Pour moi »
  (après la présence du message attribué) ; sans lui, un « Pour moi » servi comme « À traiter » restait vert.

Second passage : 2/2 verts. Preuves par mutation (client servi par `ng serve`, reconstruction vue dans `ngserve.log`
avant de jouer, restauration octet pour octet) :

| Mutation | Scénario rouge | Assertion |
|---|---|---|
| E1 « À traiter par » n'appelle pas le serveur | ASSIGN-001 | attente de `PUT …/assignee` |
| E2 « Pour moi » servi comme « À traiter » | ASSIGN-001 | « un message à traiter qui ne lui est pas attribué n'est pas dans « Pour moi » » |
| E3 libellé de l'attribution vide | ASSIGN-002 | « le détail dit « traité par » la délégataire » |
| E4 pastille jamais affichée | ASSIGN-001 | « la ligne porte la pastille » |

Témoin restauré : 2/2 verts.

### Parcours e2e — voie Angular (`--serve-only`, scénarios seuls)

Premier passage : 2/2 verts.

Preuves par mutation (weda2 code-only : sauvegarde et restauration octet pour octet ; serveur de dev muet, 150 s
laissées à la reconstruction ; restauration vérifiée par l'absence des marqueurs dans les sources) :

| Mutation | Scénario rouge | Assertion |
|---|---|---|
| A1 « À traiter par » n'appelle pas le serveur | ASSIGN-001 | attente de `PUT …/assignee` |
| A2 « Pour moi » servi comme « À traiter » | ASSIGN-001 | « un message à traiter qui ne lui est pas attribué n'est pas dans « Pour moi » » |
| A3 libellé de l'attribution vide | ASSIGN-002 | « le détail dit « traité par » la délégataire » |
| A4 pastille jamais affichée | ASSIGN-001 | « la ligne porte la pastille » |

A1 et A2, dans leur première écriture, ne compilaient pas (paramètre `mail` inutilisé, méthode privée `forMePage$`
sans appel) : rouges sur un clic d'`openFolder` de la délégataire, avant le geste visé — ce n'était pas une preuve.
Réécrites (`void mail`, `&& Date.now() < 0`), elles tombent sur l'assertion visée (récidive de `mutation-non-servie`,
compteur porté à 8). Témoin restauré : 2/2 verts.

> **À commiter sur TFS avant le merge de la PR api-mail** (conventions/e2e.md, `test-angular-non-commite`) :
> `front/e2e/mss-e2e/specs/functional.e2e.ts` et `front/e2e/mss-e2e/support/e2e-backend.ts` (scénarios
> E2E-ASSIGN-001, E2E-ASSIGN-002), avec le code weda2 de la task.

### client-angular (weda2, code-only, non commité)

Fichiers modifiés (branche `feature/nova-mss-weda-integration`) : modèles `audit`, `folder`, `mail`, `mail-event`,
`notification-payload`, `user-settings` (+ `audit.model.spec`) ; `mail-events-stream.service`, `mss-api.service` ;
`mail-assignment.util` (+ spec) ; composant `mail-assignee-picker` (+ spec) ; `mail-header` (+ spec
`assignment`), `mail-detail`, `mail-list`, `mail-folder-list` (+ spec `for-me`) ; `mss-mail.component` ;
`mail-event.service`, `mail-state.service` (+ spec `handling`), `mail-handling.service`, `mail-assignment.service`
(+ spec) ; e2e `functional.e2e.ts`, `support/e2e-backend.ts`. `mss-lib` 1808/1808, `weda2` 2683/2683, `nx build weda2`
vert ; passe qualité : `actorDisplayName` réutilisé pour nommer une personne dans les avis.

### api-mcp

`Api/Mcp` absent du poste au `/start` : cloné sur `develop` (`34469f1`) pour l'outil. `mcp_impact.py check` →
**aucun impact** (après la correction d'encodage ci-dessous).

### Défaut trouvé en route : `MailAssignmentDto.cs` en Windows-1252

Le fichier de dtos-mss a été écrit sans forcer l'UTF-8 (Python sous Windows), et publié ainsi dans le paquet 622
(tirets cadratins illisibles dans la documentation XML, contrat inchangé) ; `mcp_impact.py` a refusé de le lire.
Réencodé (`3e8bfa55`), republié en **623.0.0**, api-mail bumpé (`ccf04729`). Prévention : la consigne existe déjà
en mémoire (« Python écrit en CRLF sur ce poste ») ; les scripts d'édition de cette task passent désormais par une
écriture binaire en UTF-8.

### Fin de /develop

- dtos-mss : `28bf60ab` (contrat), `3e8bfa55` (UTF-8) ; paquet **623.0.0**.
- api-mail : `88eca007` (bump 622), `212078e6` (feature), `ecc2d98f` (flag, catalogue), `543e64a6` (passe qualité),
  `ccf04729` (bump 623), `eb6d9a10` (nom courant, trouvé par l'e2e), `f5f58002` (catalogue durci).
- client-mobile : `9bc47e3` (feature, passe qualité incluse), `361c0d6` (e2e durci), poussé ; 1611/1611 ; `ng lint`
  propre ; vert marqué.
- client-angular : non commité, voir ci-dessus ; vert marqué sur l'arbre.
- Suite api-mail finale (01:41, état poussé) : 8 132 réussis, 0 échec. Rouges vus en cours de route, hors task : `ImapFolderServiceIntegrationTests` « du jour » ×2 et `EmailReadingUseCaseTests.FilterToday…`
  (fenêtre 00:00–02:00, connus) ; `TenantRegistryIntegrationTests.AttachMailboxAsync_UnderConcurrency_…` (flaky,
  vert au passage suivant) ; mobile `MailComposeComponent` suggestions ×4 (rouge aussi sans les changements de la task,
  vert au passage suivant : flaky de présentation du `ion-modal`).

### Reprise 1 après /review (2026-11-18)

Périmètre : la liste « À corriger par la reprise » du passage 1 (B1, B2, S2, S3, S4, S6, S7, S8, S10). Les arbitrages
S1, S5, S9 ne sont pas touchés : ils vont à la PR.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** avis en direct non prouvé par le vrai flux | — (le code était juste : la preuve manquait) | intégration `MailboxAccessLockIntegrationTests.AnAddressedNotice_ReachesTheStreamOfItsRecipientOnly_NotTheOtherPersonOfTheMailbox` (Theory : `notifications/stream` et `events/stream`) : les deux personnes ouvrent leur flux HTTP réel, le titulaire attribue, `MailAssigned` n'arrive que sur le flux de la délégataire | **M17** (abonnement des avis sans la personne) et **M18** (abonnement des évènements sans la personne) : rouges, chacune sur sa route |
| **B2** « Pour moi » limité à la Boîte de réception | api-mail : `GET emails/for-me/page` rend une page de clés (dossier, UID) sur tous les dossiers hors Envoyés, Brouillons et Corbeille (`MailHandlingQueries.OutsideSelfActionFolders`, la règle d'« À traiter »), triée par instant d'attribution ; compteur sur la boîte. Clients : page de clés, puis lecture dossier par dossier, remise dans l'ordre du serveur | intégration `ForMe_CoversAMessageFiledInAnotherFolder_AndCountsAMessageInTwoCopiesOnce` ; weda2 `mail-state.service.handling.spec` (dossiers entrelacés) ; mobile `mail-state.for-me.spec` « keeps the server order… » | **M19** (Boîte de réception seule) rouge ; weda2 **WM4** (ordre des lectures par dossier) et **WM5** (un seul dossier lu) rouges ; mobile **MM6** rouge |
| **S2** une copie en double compte deux fois | compteur et page : une ligne par ancre (Message-ID), copie de la Boîte de réception d'abord | même test d'intégration (deux copies, compté une fois, une ligne) | **M20** (compteur par copie), **M21** (page par copie) rouges |
| **S3** avis non bornés, avis d'attributions closes, « vus » trop large | `GetUnseenNoticesAsync` : attributions ouvertes seules, 50 au plus ; `PUT assignments/notices/seen?until=` ne marque que jusqu'à l'instant lu ; les deux clients passent l'instant du plus récent avis montré | intégration `Notices_AreThoseOfOpenAssignments_AndSeenStopsAtTheInstantRead` ; unitaire `MarkNoticesSeenAsync_StopsAtTheInstantRead…` ; specs weda2 et mobile (`until`) | **M22** (« vus » au-delà de l'instant), **M23** (avis d'une attribution close) rouges ; weda2 **WM1**, **WM2** ; mobile **MM4**, **MM5** rouges |
| **S4** retrait sans objet tracé et publié | `UnassignAsync` sort sans acte quand le message n'est attribué à personne | unitaire `UnassignAsync_OnAMessageAssignedToNobody…` ; intégration (DELETE sur un message non attribué dans le test groupé) | **M24** (retrait sans objet imputé) rouge |
| **S6** avis en double | mobile : la page Messages ne fait plus de toast pour `MailAssigned` (seul `MailAssignmentService` le montre) ; weda2 : le service ne pose plus le bandeau sur l'avis en direct (le diffuseur des notifications l'affiche déjà), il relit les compteurs | mobile `inbox.page.spec` « does not toast an assignment notice itself » (un seul toast) ; weda2 `mail-assignment.service.spec` (bandeau nul, compteurs relus) | mobile **MM1**, weda2 **WM3** rouges |
| **S7** l'`ion-select` garde un choix non confirmé | le détail remet tout de suite la liste sur l'attribution confirmée ; seule la réponse du serveur la change | `mail-detail.component.spec` « resets the « À traiter par » select… » | **MM2** rouge |
| **S8** ligne d'attribution groupée sans « attribué par » | la ligne porte la personne qui lit comme auteur | `mail-assignment.service.spec` « assigns a selection at once » | **MM3** rouge |
| **S10** JSDoc d'`attachDelegation` séparée de sa fonction | replacée au-dessus de sa fonction | — (commentaire) | — |

Mutations api-mail M17 à M24 : chacune réinjectée seule, rouge sur son test ciblé, restauration recompilée (build 0).
M18 et M19, jouées d'abord sans `touch`, rougissaient le test de M17 (binaire non reconstruit) : rejouées après `touch`,
chacune rouge sur son seul test (consigne `mutation-non-servie`).
Mutations des clients : weda2 WM1 à WM5 (vitest), mobile MM1 à MM6 (Karma), chacune seule, restauration octet pour
octet. **WM4 a d'abord survécu** : la page du test listait les dossiers dans l'ordre de leurs lectures, donc une page non
réordonnée restait verte. Le test entrelace désormais les dossiers (INBOX, Patients, INBOX) ; WM4 rouge.

Pièges du test mobile : `applyForMePage(1, …)` s'ajoute à la liste en place (`startTagViewPaging` d'abord, comme
l'écran) ; le toast de `MailAssignmentService` passe par le même `ToastController` que la page, d'où l'assertion « un
seul toast » au lieu d'« aucun ».

Validation de la reprise :
- api-mail `d2a0c7a3`, poussé : build 0 ; suite complète 8 138 réussis, 0 échec, 16 ignorés ; vert marqué.
- client-mobile `02c9aa8`, poussé : build 0 ; 1 614/1 614 ; `ng lint` propre ; vert marqué.
- client-angular (code-only, non commité) : `mss-lib` 1 808/1 808, `weda2` 2 683/2 683, `nx build weda2` 0 ; eslint
  0 erreur, prettier appliqué ; vert marqué sur l'arbre.
- api-mcp : `mcp_impact.py check` → aucun impact.
- Parcours rejoués seuls (`--serve-only`, `--grep E2E-ASSIGN`), les routes ayant changé : voie mobile 2/2 verts, voie
  Angular 2/2 verts. Les voies complètes restent à `/e2e`.

## Sonar log

- Analyse de la branche `feat/task-457-a-traiter-par-attribuer-un-message-dans` (SonarQube 25.6.0, `sonar.token`,
  conteneurs redémarrés : `sonarqube_db` puis `sonarqube`, port 9001), deux passes : `d2a0c7a3` (code approuvé par la
  revue anticipée, passage 2), puis `45b2624a` (correctifs).
- Provenance vérifiée constat par constat (`git blame` contre `origin/develop`) : la période de new code (30 jours)
  porte 97 constats et 16 hotspots d'autres tasks (scripts du banc `tests/loadtest-k6`, `Dockerfile`, `AppHost`,
  `BaseRepository`…), déjà présents à la baseline. Un seul constat vient des lignes de la task.
- Phase 1 (new code de la task) : ✓ 0 constat restant sur les lignes de la task, 0 hotspot, new_coverage 97,7 %.
- Phase 1 — Issue fixée : **S3776** ×1 — `MailController.GetFoldersAsync`, complexité 16 : le compteur « Pour moi »
  ajoutait un second `if` de service facultatif après celui de task-454. Les deux sont extraits en
  `ApplyWorkCountsAsync` (`e79b443d`), complexité 14. Refactor pur : les compteurs restent lus dans `GET /folders` par
  les tests d'intégration de task-454 et task-457.
- Phase 1 — Tests ajoutés (`45b2624a`) :
  - intégration `InvalidAssignmentRequests_AreRefusedInProblemJson_AndAssignNothing` (vraie pile, problem+json) :
    message absent → 404 à l'attribution et au retrait, sélection vide → 400, sélection de plus de 2 000 messages →
    400, aucune attribution écrite. Trois mutations, chacune rouge : Q1 sélection vide acceptée (« Attendu 400, reçu
    200 »), Q2 sélection trop grande acceptée (« Attendu 400, reçu 200 »), Q3 message absent non refusé (« Attendu 404,
    reçu 500 »). Restauration recompilée (build 0) ;
  - unitaire `ForbiddenException_EveryConstructor_KeepsMessageAndCause`.
  - Couverture new code des fichiers de la task : `MailAssignmentController` 80,3 → 89,4 %, `MailAssignmentService`
    91,9 → 92,8 %, `ForbiddenException` 33,3 → 100 %, `MailAssignmentRepository` 90,7 % (reste : reprise sur conflit
    23505, retours anticipés sur entrée vide, propriétés de la ligne de projection). La cible globale du new code est
    tenue.
- Restent dans des fichiers touchés, sur des lignes **antérieures** à la task : S1067 `PostgresTenantRegistryClient`
  l.1392 (`PractitionerOf`, task-409), S103 `SseNotificationBroker` l.107 (ligne de log antérieure). Non corrigés.
- Phase 2 (legacy) : non jouée. Les constats restants de la période de new code appartiennent à d'autres tasks, la
  couverture du projet est de 97,7 % et la note de maintenabilité est A. Une passe Phase 2 coûte une analyse complète,
  environ 15 min.
- Build / tests (Release) : ✓ vert sur `45b2624a`. Suite complète 348 / 4 303 / 749 / 1 382 / 1 358 (+16 ignorés),
  0 échec, soit +1 unitaire et +1 intégration. Première passe : 1 rouge flaky connu,
  `TenantRegistryIntegrationTests.AttachMailboxAsync_UnderConcurrency_PersistsExactlyOneTenant`, vert à la passe
  suivante. Vert marqué (`green.py mark --by sonar`, api-mail `45b2624a`).
- `conventions/csharp.md` : S3776 → 9 (récidive : un service facultatif de plus dans une action déjà pleine).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (constats d'autres tasks, voir ci-dessus) |
| New coverage | 97,8 % | 97,7 % | −0,1 pt |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 2 | 2 | 0 |
| Security hotspots | 16 | 16 | 0 |
| Code smells | 94 | 95 | +1 |
| Coverage (projet) | 97,8 % | 97,7 % | −0,1 pt |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D/D/A | D/D/A | → |

Baseline : la dernière analyse sur ce serveur (2026-11-13, `b87aa7cf`, task-459) ; new code = 30 derniers jours.
Le +1 code smell n'est pas attribué : la branche porte aussi les commits de `develop` postérieurs à la baseline
(task-454 notamment), et aucun constat restant n'est sur une ligne de la task (`git blame`). Bugs, vulnérabilités et
notes D (fiabilité, sécurité) : constats d'autres tasks, inchangés par celle-ci.

## Lint log

- Mode : affected (npx nx affected -t lint --base=origin/next --head=HEAD --projects=tag:scope:mss)
- Scope : tag:scope:mss (default — `mss`, `mss-lib`, `mss-e2e`) ; aucun override `**LintBase**` / `**LintProjects**`
- Pipeline fidelity : same commands as Client/Angular/azure-pipelines.yml (Stage 2 CI),
  with two intentional divergences :
  1. BASE_BRANCH default = origin/next (active TFS branch, not pipeline's origin/master fallback)
  2. Lint scoped to tag:scope:mss (the pipeline lints every affected project)
  Build/test stay un-scoped to catch downstream regressions.
- Arbre : branche `feature/nova-mss-weda-integration` @ `5fbc7e28` (code-only, rien de commité). Le `git fetch origin
  next` a échoué sur l'authentification TFS (invite de mot de passe impossible) : `origin/next` local, tel quel.
- Comptage : `npx eslint libs/mss apps/mss e2e/mss-e2e --format json` (contournement de task-367, comme task-454).
- Baseline : 0 errors / 100 warnings (75 `jsdoc/require-example`, 22 `max-lines`, 3 `complexity`)
- Final    : 0 errors / 99 warnings (75 `jsdoc/require-example`, 21 `max-lines`, 3 `complexity` — tous antérieurs,
  aucun sur une ligne de la task)
- Iterations : 1 / 5
- Build / tests : ✓ tests 12 projets, 11 984 tests, 0 échec. Build : `weda2` et deux autres projets verts ;
  `mss:build:production` et `prescription:build:production` rouges sur le budget de bundle initial, rouge connu,
  antérieur à la task (déjà noté par task-454). Vert marqué (`green.py mark --by lint-angular`).

| Iter | Errors before | Errors after | Warnings before | Warnings after | Build | Tests |
|------|---------------|--------------|-----------------|----------------|-------|-------|
| 1 — `max-lines` de la task : `mail.model.ts` passé de 472 à 521 lignes par les types « À traiter par » | 0 | 0 | 100 | 99 | ✓ ¹ | ✓ |

¹ Hors budget de bundle initial de `mss` / `prescription`, antérieur.

Correctif de l'itération 1 : les quatre types de task-457 (`MailAssignmentDto`, `MailboxPersonDto`,
`MailAssignmentBulkResultDto`, `MailAssignmentNoticeDto`) sortent de `mail.model.ts` dans
`core/models/mail-assignment.model.ts`, exporté par le barrel `core/index.ts` comme `mail.model`. Les 12 fichiers qui les
importaient lisent le nouveau fichier (imports `type`, aucun changement de comportement). `mail.model.ts` : 478 lignes.

## Lint mobile log

- Branche : `feat/task-457-a-traiter-par-attribuer-un-message-dans` @ `02c9aa8`, arbre propre.
- Baseline : `npm run lint` → « All files pass linting » (0 error, 0 warning).
- Iterations : 0 / 5. Aucun correctif, donc aucun commit et aucun build ni test rejoués : le vert de /develop
  (`02c9aa8` : build 0, 1 614/1 614) tient sur ce code exact (`green.py check` → 0).

## E2E log

> ⚠️ **Quarantaine âgée de 40 jours** (> 14 j) : E2E-COMPOSE-002 (angular, `live-ai.e2e.ts`), posée le 2026-10-09 en
> citant task-350. task-350 est **archivée**, et le test est passé vert à ce run : la levée de la quarantaine est à
> décider par l'humain.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, dtos-mss et client-mobile touchés | ✅ verte (jouée, api-mail `45b2624a`, client-mobile `02c9aa8`) | 73 verts, 0 flaky, 0 rouge, 0 quarantaine | 13 min 59 s |
| angular | api-mail, dtos-mss et client-angular touchés (arbre non commité) | ✅ verte (jouée, api-mail `45b2624a`, weda2 `5fbc7e28` + arbre de travail) | 92 verts (dont 1 en quarantaine, vert), 2 flaky, 0 rouge | 15 min 10 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-457-a-traiter-par-attribuer-un-message-dans`, `45b2624a`)
- Porte `gate` : code 0, sur les deux rapports exécutés de ce run (aucune voie réutilisée, aucun rejeu d'outillage)
- Nouveaux scénarios de la task, verts sur les deux clients : E2E-ASSIGN-001, E2E-ASSIGN-002 (v1)
- Flaky (verts au second essai, non bloquants) : [angular] E2E-SEARCH-001, E2E-SESSION-004 — hors périmètre de la task
- Quarantaines : E2E-COMPOSE-002 [angular], task-350, posée le 2026-10-09 (40 jours) — passée verte
- Divergences ouvertes : 9 [mobile] (E2E-SEARCH-001, 004, 005, 006, 007, 009 → task-450 ; E2E-SEARCH-008, 010, 012 → task-451), aucune à retirer
- Parcours touchés sans spec e2e modifié : aucun (écrans mobiles et weda2 modifiés, `Client/Mobile/e2e/specs/functional.spec.ts` et `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` modifiés)
- Durées : au-dessus de task-454 (mobile 11 min 04 s, angular 11 min 53 s), sous l'effet de deux scénarios de plus par voie et des deux flaky angular rejoués
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143 et 47399 libres ; aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (2) :

- [angular] « recherche — composer ses critères puis lancer la recherche » (E2E-SEARCH-001)
- [angular] « session — après la déconnexion, la personne suivante n’arrive jamais dans la boîte de la précédente » (E2E-SESSION-004)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-BIO-007 | 1 | headless | Un compte rendu arrivé avant la date de début du suivi ne réclame rien, et s'acquitte quand même | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-DETAIL-006 | 1 | headless | Après une réponse, le message d'origine dit « Vous avez répondu à ce message le… » | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ⚠️ flaky | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-012 | 1 | headless | Traiter tous les résultats d'une recherche | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ⚠️ flaky | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |
| E2E-TAG-001 | 1 | headless | Choisir un tag de la boîte dans la liste, créer un tag de plusieurs mots | ✅ | ✅ |
| E2E-TAG-002 | 2 | headless | Les tags système classent la Boîte de réception : Biologie, Patient, Pour info | ✅ | ✅ |
| E2E-TAG-003 | 1 | headless | Combiner deux tags et retrouver le filtre « Non lus » | ✅ | ✅ |
| E2E-TRIAGE-001 | 1 | headless | Traiter un message le retire de « À traiter », le compteur baisse, « Annuler » le remet | ✅ | ✅ |
| E2E-TRIAGE-002 | 1 | headless | Traiter les messages affichés laisse le compte rendu de biologie à acquitter | ✅ | ✅ |
| E2E-TRIAGE-006 | 1 | headless | Dans la vue « Biologie », « Traiter les résultats sans anomalie » laisse le résultat anormal à traiter | ✅ | ✅ |
| E2E-TRIAGE-007 | 1 | headless | Répondre à un message le fait sortir de « À traiter », libellé « — répondu » | ✅ | ✅ |
| E2E-SHARED-003 | 1 | headless | Le délégataire traite un message, le titulaire le voit traité « par » le délégataire | ✅ | ✅ |
| E2E-ASSIGN-001 | 1 | headless | Le titulaire attribue un message à la secrétaire délégataire, qui le trouve dans « Pour moi » | ✅ | ✅ |
| E2E-ASSIGN-002 | 1 | headless | Traiter un message attribué le retire de « Pour moi », et le détail dit « traité par » | ✅ | ✅ |

**Divergences temporaires ouvertes** (9) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-012 [mobile] — la sélection de tous les résultats arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Relecteur indépendant (sous-agent, code seul). Verrous :
- **4a (règle 1b)** : correspondance comportement → test → preuve rouge dans le `## Develop log` (M1 à M16, tous
  rouges), **sauf** le chemin réel de l'avis en direct par les flux SSE (B1).
- **4b (clause DOD)** : `E2E-ASSIGN-001` v1 et `E2E-ASSIGN-002` v1 au catalogue, déclarés v1 dans les deux clients.
- **4c** : api-mcp : aucun impact.

Vérifié sain : garde du demandeur (403) et de la personne attribuée (400, rien d'écrit), concurrence (index unique +
réécriture), règle SQL = règle en mémoire, trace par message au nom de l'auteur réel avec la personne attribuée en
objet, aucun contenu clinique dans les avis ni les journaux, migration (règle 7c), miroirs `AuditActionType`,
`isMine` recalculé sur l'évènement dans les deux clients, e2e jugés sur l'état serveur.

#### À corriger par la reprise
- **B1 (bloquant)** — l'avis en direct passe par `NotificationsController` / `MailEventsController`
  (`Subscribe(email, TenantId)`), mais aucun test n'ouvre le vrai flux : le test d'intégration s'abonne au relais
  directement. Ouvrir les flux HTTP réels du délégataire et du titulaire, attribuer, lire `MailAssigned` sur le seul
  flux du délégataire ; vu rouge en retirant `TenantId` de l'abonnement du contrôleur.
- **B2 (bloquant)** — « Pour moi » ne sert que la Boîte de réception, alors que l'objectif dit « les messages
  attribués à la personne connectée et non traités », sans limite de dossier : un message attribué dans un autre
  dossier (classé « Patients/… ») reste attribué et ouvert, mais absent de la vue et du compteur. Servir « Pour moi »
  sur tous les dossiers hors Envoyés, Brouillons et Corbeille (comme « À traiter »), page de clés (dossier, UID) et
  compteur sur la boîte ; les deux clients hydratent par dossier.
- S2 — une copie en double d'un même Message-ID compte deux fois dans « Pour moi » : une ligne par ancre.
- S3 — avis : lecture non bornée, avis d'attributions déjà closes rendus, et « vus » qui marque aussi un avis arrivé
  entre la lecture et l'accusé : borner, ne rendre que les attributions ouvertes, marquer vus jusqu'à l'instant lu.
- S4 — `DELETE …/assignee` sur un message attribué à personne trace un acte et publie un évènement pour rien.
- S6 — avis en double à l'arrivée (mobile : toast générique de la page Messages + toast du service ; weda2 : snackbar
  générique + bandeau).
- S7 — mobile : sur un refus du serveur, l'`ion-select` du détail garde la personne non confirmée.
- S8 — mobile : l'attribution groupée pose une ligne sans « attribué par ».
- S10 — mobile e2e : la JSDoc d'`attachDelegation` séparée de sa fonction.

#### Arbitrage humain
- **S1** — « active » = rattachement `Active` : une révocation chez l'opérateur ne devient `AuthFailing` qu'à la
  prochaine requête de la personne révoquée. L'étape 6 du Manual Test Plan (« n'est plus proposée ») ne se vérifie
  donc qu'après une tentative d'usage de la secrétaire. *Recommandation de la forge* : l'accepter (même source de
  vérité que le verrou d'accès de task-403) ; interroger l'opérateur pour chaque personne listée coûterait une sonde
  IMAP par personne et par lecture.
- **S5** — une lecture du registre par page portant des attributions : à mesurer avant d'y poser un cache (règle
  d'or 5).
- **S9** — le test 403 joue la garde du service avec une persona fabriquée, pas le refus du middleware
  (`Client-Email` d'une boîte non rattachée), déjà couvert par les tests du verrou d'accès.

### Passage 2 (revue anticipée) — APPROVED

Relecture de la reprise d'abord (diffs `f5f58002..d2a0c7a3` api-mail, `361c0d6..02c9aa8` mobile, arbre weda2), par
un relecteur indépendant, à la recherche de ce que le correctif a cassé : tous les appelants des routes et méthodes
changées (`GET emails/for-me/page`, `PUT assignments/notices/seen?until=`, `GetForMePageAsync`,
`GetUnseenNoticesAsync`, `MarkNoticesSeenAsync`, `forMeUids`) sont à jour dans api-mail, les deux clients et leurs
supports e2e ; aucun appelant dans client-blazor ni api-mcp. `until` fait l'aller-retour sans perte (`+` encodé
`%2B` par les deux clients ; `At` tronqué à la microseconde par Npgsql, donc `At <= until` tient pour l'avis
montré). Les actions groupées sur une liste « Pour moi » à plusieurs dossiers agissent déjà dossier par dossier.

**Constats du passage 1** : B1, B2, S2, S3, S4, S6, S7, S8, S10 corrigés (preuves rouges : Develop log,
« Reprise 1 »).

**Verrou 1b (4a)** :

| Comportement | Test d'intégration (vraie pile) | Preuve rouge |
|---|---|---|
| L'avis n'arrive que sur le flux de la personne visée (`notifications/stream`, `events/stream`) | `MailboxAccessLockIntegrationTests.AnAddressedNotice_ReachesTheStreamOfItsRecipientOnly_NotTheOtherPersonOfTheMailbox` ; moitié `PUT …/assignee` → relais : `FolderOperationsEndToEndTests.Assignment` | M17, M18 |
| « Pour moi » sur tous les dossiers hors Envoyés, Brouillons, Corbeille ; une ligne et un compte par Message-ID | `ForMe_CoversAMessageFiledInAnotherFolder_AndCountsAMessageInTwoCopiesOnce` | M19, M20, M21 |
| Avis : attributions ouvertes seules, bornés ; « vus » jusqu'à l'instant lu | `Notices_AreThoseOfOpenAssignments_AndSeenStopsAtTheInstantRead` | M22, M23 |
| Retrait sans objet : ni acte ni évènement | `DELETE` d'un message non attribué dans le test groupé (`Assert.Single` sur la trace `MailUnassigned`) | M24 |

**api-mcp** : aucun impact (`mcp_impact.py check` → 0).
**DOD, scénarios** : `E2E-ASSIGN-001` et `-002` en v1 au catalogue, déclarés v1 par les deux clients ; rejoués seuls
après la reprise, 2/2 verts par voie.

**Suggestions (non bloquantes)** :
- N1 — mobile : `loadNextForMePage` ne demande pas l'enrichissement des lignes (le chemin « À traiter » le fait).
  Portée faible : attribuer un message exige de l'avoir affiché, donc enrichi dans la base de la boîte, partagée.
  Les pages servies de weda2 n'enrichissent pas non plus (antérieur à la task).
- N2 — les lignes « Pour moi » d'un autre dossier ne reçoivent pas les évènements en direct (flux par dossier, ouvert
  sur la Boîte de réception) : elles se mettent à jour au rechargement, le compteur au rafraîchissement des dossiers.
- N3 — performance : « Pour moi » joint `Mails` aux attributions sur une ancre calculée, sans index sur
  `Mails.MessageId`, sur toute la boîte à chaque `GET /folders` ; la page et les avis se chargent en mémoire avant
  la pagination. À mesurer au banc avec S5 (règle d'or 5).
- N4 — l'ordre de pagination n'a pas de départage par dossier : un message à plusieurs copies hors Boîte de
  réception, attribué en lot (même instant), pourrait changer de page entre deux requêtes. Ajouter `ThenBy(FolderPath)`
  et un choix de copie ordonné.

**Amélioration continue** : le mutant WM4 a d'abord survécu (fixture dans l'ordre des lectures par dossier) →
consigne ajoutée à `conventions/angular.md`, `liste-ordonnee-par-le-serveur` (occurrences 2).

**Approved at** : api-mail `d2a0c7a3` · client-mobile `02c9aa8` · dtos-mss `3e8bfa5` · client-angular arbre de
travail sur `5fbc7e28` (code-only, vert marqué).

### Validation finale — APPROVED (2026-11-18)

- Build + tests : vert réutilisé — api-mail `45b2624a` (/sonar : 348 / 4 303 / 749 / 1 382 / 1 358, 0 échec),
  client-mobile `02c9aa8` (/develop : 1 614/1 614), client-angular arbre sur `5fbc7e28` (/lint-angular : 12 projets,
  11 984 tests ; build `weda2` vert, budget de bundle `mss` / `prescription` rouge antérieur) ; dtos-mss `3e8bfa5`
  construit ici (build 0, pas de tests).
- DOD : ✓ chaque ligne. Personnes de la boîte (`GET mailbox/people`, 403 hors boîte) ; attribution dans la base de la
  boîte ancrée au Message-ID, migration FluentMigrator ; contrat 623.0.0 ; `MailAssigned` = 75, `MailUnassigned` = 76
  en fin d'énumération, miroirs TypeScript ; avis adressé à la personne (`RecipientId`), prouvé sur les vrais flux ;
  tests unitaires, d'intégration (dont 400 / 403 / 404 en problem+json), de composant, vus rouges ; E2E-ASSIGN-001 et
  -002 v1 verts sur les deux voies. La route de la DOD (`emails/{id}/assignee`) est servie sous
  `folders/{dossier}/emails/{id}/assignee`, comme toutes les routes de message.
- 4a (règle 1b) : tables des passages 1 et 2, plus Q1-Q3 du `## Sonar log`.
- 4b : `## E2E log` vert, parité verte. 4c : api-mcp, aucun impact.
- Revue des changements postérieurs à l'approbation (`d2a0c7a3..45b2624a` api-mail ; séparation de
  `mail-assignment.model.ts` côté weda2 ; aucun sur mobile ni dtos-mss) : ✅ refactor pur et tests, aucun constat.
- Synchronisation : `develop` n'avait pas avancé sous les trois branches (0 commit à fusionner).

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/70 (awaiting-human-merge)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/374 (awaiting-human-merge)
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/129 (awaiting-human-merge)
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, **avant le merge de la PR api-mail** (les specs e2e E2E-ASSIGN en font partie). Branche `feature/nova-mss-weda-integration`. Liste des fichiers modifiés :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/index.ts`
  - `front/libs/mss/src/core/models/audit.model.spec.ts`
  - `front/libs/mss/src/core/models/audit.model.ts`
  - `front/libs/mss/src/core/models/folder.model.ts`
  - `front/libs/mss/src/core/models/mail-assignment.model.ts`
  - `front/libs/mss/src/core/models/mail-event.model.ts`
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/core/models/notification-payload.model.ts`
  - `front/libs/mss/src/core/models/user-settings.model.ts`
  - `front/libs/mss/src/core/services/mail-events-stream.service.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/core/utils/mail-assignment.util.spec.ts`
  - `front/libs/mss/src/core/utils/mail-assignment.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-assignee-picker/mail-assignee-picker.component.html`
  - `front/libs/mss/src/features/mail/components/mail-assignee-picker/mail-assignee-picker.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-assignee-picker/mail-assignee-picker.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-assignee-picker/mail-assignee-picker.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.for-me.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.assignment.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.html`
  - `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-assignment.service.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-assignment.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-event.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-handling.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.handling.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
- Ordre de merge : dtos-mss, api-mail, client-mobile (règle 11 : la US entière, testée de bout en bout).

### Synchronisation avec develop après task-487 (2026-11-18, demande humaine)

`/merge task-457 --i-tested` s'est arrêté au gate 5 : task-487 (conversation en chat) avait été mergée entre-temps,
api-mail #374 et client-mobile #129 étaient en conflit. Synchronisation par merge (règle 4) :

- dtos-mss : `origin/develop` fusionné sans conflit (`7521de3`), paquet **627.0.0** publié depuis la branche, porteur
  des contrats de task-457 et de task-487.
- api-mail `0ef2848a` : `Directory.Packages.props` et les `packages.lock.json` passés à 627.0.0
  (`dotnet restore --force-evaluate`) ; `e2e/scenarios.yml` = les scénarios des deux tasks (deux ajouts en fin de
  catalogue) ; `UseCaseFixture.cs` garde les enregistrements des deux tasks. Build 0 ; suite complète 368 / 4 346 /
  749 / 1 382 / 1 369 (+16 ignorés), 0 échec.
- client-mobile `11f0603` : `functional.spec.ts` (les deux blocs de scénarios), `mail-detail.component.ts` (les
  imports des deux tasks), `mail-detail.component.scss` (les styles des deux tasks). `ng lint` propre, build 0,
  1 679/1 679.
- e2e rejoués en entier sur le code synchronisé : mobile 76 verts, Angular 96 verts (1 flaky : E2E-SEARCH-001), porte
  verte, parité verte — E2E-ASSIGN-001/002 et E2E-CONV-001/002/003 verts sur les deux clients.
- Les trois PRs : MERGEABLE, CLEAN, CI verte.
