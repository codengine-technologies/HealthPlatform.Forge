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
| /develop | ok | 3 h 33 min | 13 (6 min 45 s) | 15 (56 min 19 s) | — | api-mail 8B/8T, client-angular 2B/4T, client-mobile 3B/3T |
| /review-code | changes | 10 min 44 s | — | — | — | reprise 1 |
| **Total cycle** | | **3 h 45 min** | **13 (6 min 45 s)** | **15 (56 min 19 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×2 (28 s), restore ×2 (15 s)

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
