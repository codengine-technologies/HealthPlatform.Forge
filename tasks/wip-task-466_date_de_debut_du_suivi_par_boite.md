# todo-task-466.md — Date de début du suivi par boîte

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 1
**Dependencies**: done-task-453 (ancrage des états de travail)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-12. **À passer avant task-454 et task-463** : c'est le socle
commun de « à acquitter » et de « à traiter ».

> **Origine.** Échange avec l'humain du 2026-11-12, en arbitrant task-454 : « la biologie de l'historique ne doit pas
> attendre d'acquittement, car un médecin qui synchronise sa boîte la première fois va prendre deux ans d'historique.
> Le marquage « traité » ou l'acquittement de biologie ne doit s'activer que sur les nouveaux mails. » Décision du même
> jour : **toute personne de la boîte** peut modifier la date de début du suivi.

## Ce qui est établi

Lecture du code au 2026-11-12 (`Api/Mail/src`) :

- Une ligne `Mails` ne garde que la date **annoncée par l'expéditeur** (`Mail.SentDate`, en-tête `Date`). La date
  d'arrivée sur le serveur (`INTERNALDATE`) est lue pendant la synchronisation (`ImapService`, `MessageSummaryItems.InternalDate`)
  mais n'est pas stockée.
- « Bio à acquitter » compte **tous** les documents de biologie signalés par le laboratoire et non résolus, quelle que
  soit leur ancienneté : puce et pages servies (`BiologyAckRepository`, `biology-acks/pending-mail-uids[/page]`,
  `pending-summary`), compteurs par mail (`MailDto.PendingBiologyAcksCount`, `HasCriticalPendingBiologyAck`, calculés
  par `MailRepository.EnrichManyWithBiologyAcksAsync`), état d'un document (`BiologyAckState`, `Pending` par défaut),
  tuile du tableau de bord.
- Une première synchronisation ramène tout l'historique de la boîte. Une purge sur changement d'UIDVALIDITY, une base
  recréée ou une resynchronisation ré-ingèrent des messages anciens : leur **date d'ingestion** est récente, leur date
  d'arrivée ne l'est pas.

## Objective

Chaque boîte porte une **date de début du suivi**. Un message est **suivi** quand il est arrivé sur le serveur de
messagerie après cette date. Seuls les messages suivis **réclament** quelque chose : « Bio à acquitter » aujourd'hui,
« À traiter » demain (task-454). L'historique se consulte, s'acquitte si le praticien le souhaite, mais ne réclame
rien.

Règles :
- **Message suivi** : sa **date d'arrivée** (`INTERNALDATE`, désormais stockée à l'ingestion) est postérieure ou égale
  à la date de début du suivi de la boîte.
  - Date d'arrivée absente (lignes antérieures à cette US, pas de reprise) : repli sur la date d'envoi.
  - Aucune date : le message est traité comme **historique**.
- **Date posée à la création de la base de la boîte** (premier rattachement), **avant** la première synchronisation.
  Deux ans d'historique ramenés ensuite restent hors suivi ; un compte rendu arrivé pendant ou après la
  synchronisation est suivi.
  - Boîtes existantes : la migration pose la date à l'instant où elle s'exécute (une ligne par boîte, aucune reprise
    des messages).
- **Stabilité** : un déplacement, une purge d'UIDVALIDITY, une resynchronisation ou une base ré-ingérée ne font
  revenir aucun message dans le suivi, puisque la date d'arrivée ne change pas.
- **Nouvelle remise** : un ancien résultat **renvoyé aujourd'hui** par le laboratoire est une nouvelle arrivée, donc
  suivi.
- **Ce que le suivi gouverne** (biologie, dans cette US) : puce « Bio à acquitter » et ses pages, compteurs par mail,
  tuile du tableau de bord, alertes de résultat critique. Un document de biologie d'un message **non suivi** :
  - n'est compté nulle part, ne déclenche aucune alerte ;
  - affiche l'état neutre **« Antérieur au suivi »** (nouvel état du contrat), jamais « À traiter » ;
  - **peut** être acquitté : l'acquittement est enregistré, imputé et affiché comme aujourd'hui. Il n'est jamais
    réclamé.
- **Réglage** : dans les paramètres de la boîte, « Suivre les messages arrivés depuis le … ».
  - Valable pour **toute la boîte** (donnée de la boîte, règle 14).
  - Modifiable par **toute personne de la boîte** (titulaire, membre, délégataire), sous verdict récent de
    l'opérateur ; tracé au nom de la personne, avec l'ancienne et la nouvelle date.
  - Reculer la date fait entrer l'historique récent dans le suivi ; l'avancer l'en retire. Rien n'est écrit ni effacé
    sur les messages : le suivi se calcule à la lecture.
- **Ancrage** : la date d'arrivée suit le message ré-ingéré (modèle de task-453).

### Hors périmètre

- L'état « traité » et le compteur « à traiter » : task-454, qui s'appuiera sur cette règle.
- Le suivi daté d'un résultat jusqu'à « résultat communiqué » : task-463, idem.
- Un réglage par personne : la date appartient à la boîte.

## Definition of Done

- [x] Date d'arrivée stockée : colonne sur `Mails` alimentée par l'`INTERNALDATE` à l'ingestion (insertion et
      promotion d'un en-tête), sans reprise des lignes existantes ; migration FluentMigrator, audit de migration
      (règle 7c), modèle EF identique.
- [x] Date de début du suivi stockée dans la base de la boîte : posée à la création de la base, posée par la migration
      pour les bases existantes (une ligne) ; test de migration (base neuve et base existante).
- [x] Contrat : nouvel état `BiologyAckResolutionState` « Antérieur au suivi » (valeur appendue, explicite) ; date de
      début du suivi lue et modifiée par les réglages de la boîte ; paquet `HealthPlatform.Dtos.Mss` publié et
      consommateurs à jour ; miroirs TypeScript (weda2, mobile).
- [x] Acte d'audit `MailboxTrackingStartChanged` (personne réelle, ancienne et nouvelle date) en fin de
      `AuditActionType`, miroirs TypeScript, famille `HealthDataAccess`, contrôleur marqué `[Audited]` (écart : `[TracedInCode]` sur le PUT, voir Develop log).
- [x] Tests unitaires de la règle « suivi » : arrivée après / avant / égale à la date ; repli sur la date d'envoi ; sans
      aucune date → historique ; nouvelle remise d'un ancien résultat → suivi.
- [x] **Test d'intégration de bout en bout (règle 1b)** sur la puce et les compteurs de biologie
      (`GET biology-acks/pending-mail-uids/page`, `GET biology-acks/pending-summary`) et sur
      `GET api/v1/Mail/folders/{f}/emails/{ids}` : une boîte avec un compte rendu anormal **arrivé avant** la date de
      début et un **arrivé après** ; seul le second est compté, porte `PendingBiologyAcksCount = 1` et
      `BiologyAckState = Pending` ; le premier lit `BiologyAckState = Antérieur au suivi`, `PendingBiologyAcksCount = 0`,
      `HasCriticalPendingBiologyAck = false`. Cas d'échec : date de début invalide (future) → 400 en `ProblemDetails`.
      Vu rouge.
- [x] **Test d'intégration de la stabilité** : purge sur changement d'UIDVALIDITY puis ré-ingestion d'un compte rendu
      historique ; il reste « Antérieur au suivi ». Vu rouge (avec une date d'ingestion à la place de la date d'arrivée).
- [x] **Test d'intégration du réglage** : reculer la date fait compter le compte rendu historique ; la relecture le
      prouve. Acquitter un compte rendu historique reste possible, et son acquittement est relu.
- [x] **Deux personnes sur la même boîte** (règle 14) : le délégataire change la date de début du suivi ; le
      titulaire relit la nouvelle date et ses compteurs ; la trace d'audit porte le délégataire (RPPS, nom, rôle).
- [x] Tests de composant (weda2 et mobile), vus rouges par mutation : panneau d'acquittement « Antérieur au suivi »
      (pas de « À traiter », geste d'acquittement toujours disponible), réglage « Suivre les messages arrivés
      depuis le … ».
- [x] **Scénario e2e** `E2E-BIO-007` v1 ajouté à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis, vu rouge par
      mutation : « une première synchronisation avec de la biologie ancienne n'affiche rien à acquitter ; un compte
      rendu arrivé ensuite est à acquitter ». Le seed du banc pose des messages arrivés avant la date de début ;
      `E2E-BIO-001` à `004` restent verts (leur biologie est arrivée après).
- [x] Prévention (règle d'or) : consigne dans `conventions/csharp.md` — « un compteur ou un état qui réclame une
      action (à acquitter, à traiter) se borne à la date de début du suivi, comparée à la date d'arrivée, jamais à
      la date d'ingestion ».
- [x] Aucune donnée de santé dans les logs ; `data-testid` sur chaque élément interactif ajouté.
- [x] Build et tests verts : `HealthPlatform.Api.Mail.sln`, `Dtos`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [x] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et weda2 (`cd Client/Angular/front && npm start`).
2. Rattacher une **nouvelle** boîte de formation qui contient des comptes rendus de biologie anciens. Pendant et après
   la première synchronisation : la puce « Bio à acquitter » et la tuile du tableau de bord restent à 0 pour
   l'historique.
3. Ouvrir un ancien compte rendu anormal : le panneau dit « Antérieur au suivi » ; l'acquitter quand même : il est
   enregistré à votre nom.
4. Envoyer un nouveau compte rendu anormal vers la boîte : il apparaît dans « Bio à acquitter », état « À traiter ».
5. Paramètres de la boîte : « Suivre les messages arrivés depuis le » une date de la semaine dernière. Les comptes
   rendus anormaux de la semaine apparaissent dans « Bio à acquitter ». Remettre la date d'origine : ils sortent.
6. Mobile, délégataire de la même boîte : changer la date ; sur weda2, le titulaire voit la nouvelle date et les
   compteurs mis à jour ; le journal de la boîte dit que le délégataire l'a changée.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (biologie reçue, LGC)
- **Vague Ségur** : hors Ségur — organisation du suivi ; prolonge l'acquittement des comptes rendus de biologie
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucun identifiant patient manipulé
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : titulaire, membre et délégataire peuvent modifier la date (décision humaine du 2026-11-12),
  sous verdict récent de l'opérateur (règle 14) ; rien sans verdict
- **Interop CI-SIS** : non applicable — date d'arrivée IMAP, pas de document CI-SIS produit ; lecture inchangée des
  CDA R2 et HPRIM
- **Tracé PGSSI-S** : `MailboxTrackingStartChanged` au nom de la personne réelle (RPPS, nom PSC, rôle, boîte,
  ancienne et nouvelle date) ; pose initiale de la date en acte système ; famille `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (inchangé)
- **Hébergement HDS** : oui — base de la boîte, environnement HDS de production
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle sur le patient ; la date d'arrivée d'un message est une
  métadonnée de messagerie

## Branches

- `api-mail` (pushed) : feat/task-466-date-de-debut-du-suivi-par-boite — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-466-date-de-debut-du-suivi-par-boite
- `client-mobile` (pushed) : feat/task-466-date-de-debut-du-suivi-par-boite — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-466-date-de-debut-du-suivi-par-boite
- `dtos-mss` (lazy) : aucune branche au /start — `/develop` la crée depuis `origin/develop` (feat/task-466-date-de-debut-du-suivi-par-boite) au premier contrat touché
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au /start du 2026-11-13 : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

**Étape** : `/develop` du 2026-11-13. Commits : `dtos-mss` 9fcef29 (publié 604.0.0, CI #604), `api-mail` 569f7131
(bump DTOs 597→604) + 6485bcae, `client-mobile` f46a059 ; `client-angular` code-only, non commité.

### Ce qui est livré
- **Contrat** (`dtos-mss`) : `MailDto.ArrivalDate`, `BiologyAckResolutionState.BeforeTrackingStart = 3`,
  `AuditActionType.MailboxTrackingStartChanged = 72` (avant `Unknown`), `MailboxTrackingStartDto`,
  `MailboxErrorCodes.TrackingStartInFuture`. `client-blazor` n'est pas dans les Repos : non bumpé.
- **api-mail** : `Mails.ArrivalDate` (INTERNALDATE, insertion et promotion d'en-tête) ; table `MailboxTrackingStart`
  (une ligne), posée par la migration `20261113120000` à `maintenant − 5 min` (tolérance d'horloge
  `MessageTracking.InitialClockTolerance`), tronquée à la seconde ; règle unique `MessageTracking` (`IsTracked` en
  mémoire, `TrackedSince` en SQL) appliquée à `pending-summary`, `pending-mail-uids` (+ `/page`) et à l'état des
  documents servis par `emails/{ids}` ; route `api/v1/account/mailboxes/current/tracking-start` (GET, PUT) ; code
  d'erreur au catalogue et `docs/codes-erreur.md` régénéré.
- **client-mobile** : panneau « ANTÉRIEUR AU SUIVI » (geste conservé), section « Suivi » des réglages,
  `MailboxTrackingService` relu à chaque bascule de boîte.
- **client-angular** (non commité, à la charge de l'humain) : `core/models/biology-ack.model.ts` (+ spec neuve),
  `core/models/audit.model.ts` (+ spec), `core/models/user-settings.model.ts`, `core/services/mss-api.service.ts`
  (+ spec), `core/utils/local-date.util.ts` (neuf, extrait d'`audit-filter.component.ts`),
  `features/audit/components/audit-filter/audit-filter.component.ts`, `features/mail/components/biology-ack-panel/*`
  (ts, html, scss, spec), `features/mail/components/mail-detail/mail-detail.component.ts`,
  `features/mail/services/mail-state.service.ts`, `features/settings/mss-settings.component.*` (ts, html, spec),
  `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`.

### Preuves rouges (règle 1b)
- Intégration `FolderOperationsEndToEndTests.TrackingStart` (5 tests, vraie pile HTTP + PostgreSQL) :
  M1 filtre SQL retiré → 4 rouges ; M2 état « Antérieur au suivi » retiré → 2 rouges ; M3 date d'ingestion au lieu de
  la date d'arrivée → 4 rouges ; M4 date future acceptée → rouge ; M5 type d'acte tracé faussé → rouge.
- Composants mobile (Karma) : libellé du panneau et rafraîchissement du tableau de bord, mutés → rouges.
- Composants weda2 (Vitest, lanceur ciblé `--pool=forks`) : panneau, règle `isBiologyAckClaimed` (« Antérieur au
  suivi » réclamé) et enregistrement de la date (journée au lieu de minuit local), mutés → rouges.
- **e2e E2E-BIO-007** : vert sur les deux voies (`--serve-only`, avec BIO-001 et BIO-002 verts) ; rouge sur la voie
  mobile avec `TrackedSince` muté en `m => true` (`pending` contenait l'uid du compte rendu historique). La voie
  Angular porte la même assertion serveur en tête ; elle n'a pas été rejouée sous mutation (un seed neuf par essai).

### Écarts assumés
- **`[TracedInCode]` au lieu de `[Audited]`** sur le PUT : la trace porte l'ancienne et la nouvelle date, connues du
  service seul. Le GET est `[TraceExempt]` (une date de réglage, aucune donnée de santé).
- **Pose initiale non tracée en acte système** : la migration FluentMigrator n'a pas de contexte d'audit. La date
  initiale se lit dans la table ; à trancher au merge si une trace est exigée.
- **Seed e2e** : la migration pose la date APRÈS le dépôt IMAP des messages ; le seed la recule d'un jour et la relit
  (`E2eSeed.SetTrackingStartAsync`), sinon BIO-001…003 n'auraient rien à acquitter. Le compte rendu historique
  (3 jours) devient le plus ancien message : l'invariant de `E2eSeedPlanTests` porte désormais sur les messages suivis.
- `/stitch-design` non joué : aucun écran nouveau, une section ajoutée à l'écran de réglages existant.

### Vérification
- api-mail : build 0 avertissement ; suite complète 7 888 tests verts (un rouge, le document du catalogue d'erreurs,
  corrigé par régénération et rejoué vert).
- client-mobile : build vert (avertissements préexistants) ; Karma 1 428/1 428 trois fois de suite (une première
  passe à 4 rouges non reproduite) ; `ng lint` propre.
- weda2 : `nx build weda2` vert, `nx test weda2` 2 683 verts, `nx test mss-lib` 1 643 verts ; ESLint 0 erreur, aucun
  avertissement sur les lignes ajoutées.
- Passe qualité §Q : aucun nettoyage appliqué (code neuf déjà minimal ; `local-date.util` dupliqué entre mobile et
  weda2, dépôts distincts).

### Amélioration continue
- `conventions/csharp.md` : entrée `action-reclamee-bornee-au-suivi`.
- Mémoire de session : lanceur Vitest de `mss-lib` — preuves par mutation sur spec ciblée `--pool=forks`.

### Reprise 1 après /review

Commits : `dtos-mss` 957b28a (publié 607.0.0, CI #607), `api-mail` 267e9ca2 (bump 604→607) + 011d661a,
`client-mobile` 95e6dc1 ; `client-angular` non commité (code-only).

- **B1** — le suivi est dit à part de l'acquittement : `MailMedicalDocumentDto.IsTracked` (vrai par défaut, serveur
  antérieur), posé par `ApplyEnrichmentToMail` sur chaque document servi ; weda2 : `isBiologyAckClaimed(state,
  isTracked)` lu par `computeBiologyAggregates` et `hasPendingBiologyAck`, `MailMedicalDocumentDto.isTracked` au modèle.
  Le mobile n'avait pas le défaut (compteur du serveur, décrément à la seule résolution) : inchangé.
  Preuves : `AHistoricalReportAcknowledgedWithAnIntermediateAction_IsStillUntracked_AndClaimsNothing` (« Pris
  connaissance » → `InProgress`, `IsTracked = false`, 0 en attente, absent de `pending-summary` et de
  `pending-mail-uids/page?lastAction=Acknowledged`) et `IsTracked` lu dans le premier test, **rouges avant le
  correctif** ; specs weda2 (`biology-ack.model.spec`, `mail-state.service.spec` : « Pris connaissance » sur un
  historique ne le rend pas « à acquitter ») rouges avant le correctif ; e2e BIO-007 Angular **rouge** avec la règle
  web mutée (`isTracked` ignoré : `mail-summary-chip-ack` réapparaît).
- **B3** — `GetReclassifiedBiologyMailLocationsAsync(previous, current)` : seuls les messages dont `ArrivalDate ??
  SentDate` est entre l'ancienne et la nouvelle date ; le service ne retire que `RedisKeys.Mail.Email`
  (`RemoveMailContentEntryAsync`), par lots de 50, rien si la date ne change pas. Preuve :
  `MovingTheStart_RefreshesTheCachedContentOfTheReportsItReclassifies_AndOnlyThose` (cache qui garde réellement le
  contenu, route `emails/content/{uid}`) : **rouge** avant le correctif (le message hors fenêtre évincé), M6 (éviction
  neutralisée → contenu périmé) et M7 (fenêtre retirée) **rouges**.
- **B4** — BIO-007 (mobile et Angular) attend `mailBySubject('cr-bio-historique').hasAbnormalBiology === true` avant
  d'affirmer l'absence, puis vérifie après l'acquittement que rien n'est réclamé (pas de `mail-summary-chip-ack`,
  puce inchangée, uid absent du serveur). Voies vertes : mobile 7 parcours (BIO-001/002/003/007, SETTINGS), Angular
  10 parcours (BIO-001/002/003/007, SEARCH-006/012, SETTINGS).
- **S3** — la date de suivi n'est lue que si la page porte de la biologie signalée (`MailRepository`). Les requêtes
  de `BiologyAckRepository` (résumé, puce) ne sont pas sur la page d'en-têtes : inchangées.
- **S4** — PUT sans date (`{}`) → 400 ProblemDetails, date inchangée ; M8 (garde retirée) **rouge**.
- **S5** — écarté : retirer `GetStateAsync` supprimait 4 tests de dépôt (`BiologyAckRepositoryIntegrationTests`) pour
  une méthode sans appelant ; elle dit l'état de l'acquittement seul, le suivi est désormais porté par `IsTracked`.
- **S6** — `AHeaderWrittenBeforeTheMigration_GetsItsArrivalDateWhenPromoted` ; M9 (`??=` retiré) **rouge**.
- **S7** — l'historique du premier test porte un résultat critique (« HH ») ; prémisse vérifiée en reculant la date
  (`HasCriticalPendingBiologyAck` vrai une fois suivi).
- **S9** — champ rendu à la date enregistrée sur refus, journée vide ou future (weda2, mobile) ; `todayIso` devient une
  méthode. Specs rouges avant le correctif (weda2) et par mutation (mobile : 2 rouges). Le rafraîchissement weda2 est
  sans objet : `MailStateService` est fourni par la page messagerie (`MssMailComponent`), détruite en allant aux
  réglages ; liste et puce se relisent au retour.
- **S10** — SEARCH-006 et 012 prennent `cr-bio-historique` comme plus ancien message ; verts.
- Self-check du diff : la méthode d'interface renommée n'avait que des doublures NSubstitute ; `todayIso` du filtre
  d'audit (même défaut, antérieur) hors périmètre.
- Vérification : api-mail build 0 avertissement, suite complète verte sauf
  `ImapServiceTests.GetFolderNotSeenAsync_HappyPath_Tags…` (instable connu, 73/73 isolé deux fois) ; mobile build,
  Karma 1 430/1 430, `ng lint` propre ; weda2 build, `nx test weda2` 2 683, `nx test mss-lib` 1 648, ESLint 0 erreur.
- Amélioration continue : `conventions/e2e.md` `precondition-du-negatif`, récidive task-466 (Occurrences 3). Récidive =
  signal sur la lecture : la fiche n'avait pas été relue avant d'écrire BIO-007.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Relecteur indépendant, sur `dtos-mss` 9fcef29, `api-mail` 6485bcae, `client-mobile` f46a059 et l'arbre non commité de
`client-angular`. Règles 12 et 14 (verdict de l'opérateur par le middleware, acte imputé à la personne réelle, aucune
donnée de santé tracée) et règle 7c (migration ↔ modèle EF) : sans défaut.

#### À corriger par la reprise
- **B1 (bloquant)** — un compte rendu « Antérieur au suivi » acquitté par un geste intermédiaire (« Pris connaissance »)
  redevient « à acquitter » côté clients. Le serveur ne pose `BeforeTrackingStart` que sans acquittement, puis renvoie
  `InProgress`, et `isBiologyAckClaimed(InProgress)` (weda2 `biology-ack.model.ts`, `mail-state.service.ts:107`,
  `mail-detail.component.ts:393` ; même lecture côté mobile) le recompte : puce « Acquittement à traiter », compteur de la
  ligne, divergence avec le serveur, qui ne le compte jamais. Attendu : le contrat dit si un document est suivi,
  indépendamment de son acquittement (ex. `MailMedicalDocumentDto.IsTracked`), et les clients ne réclament rien pour
  un document hors suivi. Ajouter un test d'intégration (historique acquitté par un geste intermédiaire →
  `PendingBiologyAcksCount = 0`, absent de `pending-summary` et de `pending-mail-uids/page?lastAction=…`), vu rouge,
  et une assertion e2e après l'acquittement (pas de `mail-summary-chip-ack`, compteur de la puce inchangé).
- **B3 (bloquant)** — éviction du cache après un PUT de la date : non bornée (tous les messages de biologie signalée
  de la boîte), deux appels Redis en série par message dans la requête, et elle retire aussi le résumé IA
  (`RedisKeys.Mail.Summary`), qui ne dépend pas du suivi. Ne viser que les messages dont `ArrivalDate ?? SentDate` est
  entre l'ancienne et la nouvelle date, ne retirer que `RedisKeys.Mail.Email`, regrouper les retraits. Règle 1b : la
  route mise en cache (`GET …/emails/content/{uid}`) n'est lue par aucun test d'intégration ; prouver qu'après un PUT
  elle rend le nouvel état, avec un cache qui garde réellement l'entrée (`KeepInCache`), vu rouge sans l'éviction.
- **B4 (bloquant)** — E2E-BIO-007 (mobile et Angular) : la prémisse « le serveur compte des résultats en attente » ne
  prouve pas que `cr-bio-historique` est analysé ; tant qu'il ne l'est pas, les assertions d'absence passent d'office.
  Attendre d'abord que le compte rendu historique soit analysé, puis asserter l'absence. Rejouer la voie Angular
  sous mutation.
- Dans la même passe (défauts réels, non bloquants) :
  - S3 — `GetTrackingStartAsync` ne se lit que si la page porte de la biologie signalée (page d'en-têtes, chemin le
    plus chaud) ; idem `TrackedMailsAsync`.
  - S4 — PUT `{}` (date absente, `DateTime.MinValue`) accepté en 200 : refuser en 400 ProblemDetails.
  - S5 — `BiologyAckRepository.GetStateAsync` ignore la règle : la retirer si elle n'a aucun appelant, sinon l'aligner.
  - S6 — prouver `ArrivalDate ??=` à la promotion d'un en-tête (DoD).
  - S7 — `Assert.False(old.HasCriticalPendingBiologyAck)` : vérifier la prémisse (une valeur critique présente) ou
    prendre un document critique.
  - S9 — après un enregistrement refusé, le champ garde la journée refusée (mobile et weda2) ; weda2 ne relit ni la
    puce ni la liste après un changement de date ; `todayIso` figé après minuit.
  - S10 — vérifier que E2E-SEARCH-006 et 012 (Angular, « le plus ancien message est affiché, donc enrichi ») restent
    justes avec `cr-bio-historique` plus ancien que `mail-lu`.

#### Arbitrage humain
- **B2** — la migration pose la date au moment où chaque base monte (montée paresseuse, au premier accès). Toute ligne
  existante (`ArrivalDate` vide, repli sur `SentDate`) devient historique : un résultat critique en attente la veille
  du déploiement sort de « Bio à acquitter » sans avertissement, et un praticien absent au déploiement voit classés
  « Antérieur au suivi » les résultats arrivés pendant son absence. Pistes : un instant fixe de mise en production dans
  la migration, ou garder dans le suivi les documents en attente au moment de la migration. Recommandation de la forge :
  garder dans le suivi ce qui était en attente au moment de la migration (aucun résultat déjà réclamé ne disparaît).
- **S1** — la pose initiale de la date n'est pas tracée en acte système (la migration n'a pas de contexte d'audit).
- **S2** — le widget « Résultats anormaux » et les patients à messages non lus ignorent la date de suivi : un historique
  non lu y remonte. Hors de la liste de la story.
- **S8** — `MailDto.ArrivalDate` sort sans `Z` (colonne sans fuseau), comme `SentDate` ; aucun client ne le lit.

## Timings

*(généré par `tools/timing/report.sh --task task-466 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 33 s | — | — | — | — |
| /develop | ok | 41 min 32 s | 13 (2 min 56 s) | 25 (42 min 21 s) | — | dtos-mss 2B/0T, api-mail 6B/17T, client-angular 2B/5T, client-mobile 3B/3T |
| /review-code | changes | 38 min 24 s | — | — | — | reprise 1 |
| **Total cycle** | | **1 h 20 min** | **13 (2 min 56 s)** | **25 (42 min 21 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×2 (38 s), restore ×2 (7.1 s)
