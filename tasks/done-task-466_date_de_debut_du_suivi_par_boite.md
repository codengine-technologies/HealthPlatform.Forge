# todo-task-466.md — Date de début du suivi par boîte

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 2
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

### Reprise 2 après /e2e (lancée par l'humain, `/develop task-466 --reprise`)

Commit `api-mail` 0f0605cd ; `client-angular` non commité (code-only, un spec e2e).

- **E2E rouge Angular (4 parcours)** — `cr-bio-historique` réutilisait le CDA de `cr-bio-a-acquitter` : second compte
  rendu au même patient. Il devient un **HPRIM synthétique au nom d'un patient fictif propre** (« HISTOE2E
  Dominique », potassium « H », `E2eAttachmentKind.HistoricalHprim`), expéditeur « Laboratoire HPRIM E2E » ; seed,
  plan, test du plan et description au catalogue. Preuve rouge : les 4 parcours rouges au `/e2e` sur le code d'avant.
- Rejeu ciblé, voie Angular (`--serve-only`) : PATIENT-004, SEARCH-010, DASH-001 **verts** ; BIO-001/002/003/007,
  SEARCH-006/012 verts. **SEARCH-008** restait rouge (3 biologies anormales au lieu de 2) : le filtre « Biologie
  anormale » rend aussi le HPRIM historique, anormal par construction. Le comportement est juste ; le parcours web est
  ajusté à 3 lignes, la troisième nommée, et vérifie qu'elle sort au filtre `PAT-TROIS` (autre patient). Vert.
  Comportement du scénario inchangé : pas de nouvelle version.
- Rejeu ciblé, voie mobile : BIO-001/002/003/007, DASH-001, PATIENT-*, SETTINGS — 11 verts.
- api-mail : build 0 avertissement, suite complète verte (237 / 749 / 1 381 / 4 236 / 1 295 + 16 ignorés).
- Amélioration continue : `conventions/e2e.md` `seed-partage-des-deux-clients` — récidive task-466 (Occurrences 2) :
  une donnée de seed porteuse d'un document prend un patient fictif propre, et la recherche d'assertions couvre les
  parcours patient et tableau de bord.

## Sonar log

- Analyse de la branche `feat/task-466-date-de-debut-du-suivi-par-boite` (SonarQube 9.9.8, `sonar.login`), deux passes.
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,5 % ; fichiers de la task : `MailboxTrackingService`,
  `MailboxTrackingRepository`, `MailboxTrackingStartInFutureException` à 100 %.
- Phase 1 — Issues : 1, S3925 sur `MailboxTrackingStartInFutureException` (triplet de constructeurs présent d'emblée ;
  la règle réclame encore le constructeur `ISerializable`, obsolète SYSLIB0051) → FALSE-POSITIVE avec motif, comme
  les exceptions voisines. Hotspots : 0.
- Phase 1 — Tests ajoutés : 4 (`f009fc96`) — constructeurs de l'exception, date locale, base sans date précédente
  (trace « none », tous les messages signalés reclassés), boîte sans adresse ; et un test d'intégration : une base
  sans ligne de suivi en reçoit une au premier réglage.
- Phase 2 (legacy) : non jouée — 0 bug, 0 vulnérabilité, 0 code smell, couverture 97,8 % (cibles atteintes).
- Build / tests (Release, avec couverture) : ✓ vert — 237 / 4 236 / 749 / 1 381 / 1 295 (+16 ignorés).
- `conventions/csharp.md` : S3925 → Occurrences 9 (consigne lue, faux positif attendu).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,3 % | 96,5 % | +0,2 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,7 % | 97,8 % | +0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

Baseline : dernière analyse du projet avant la task (2026-11-12) ; new code = 30 derniers jours.

- **Après la reprise 2** (0f0605cd, seed e2e seulement) : troisième analyse — Quality Gate OK, 0 constat et
  0 hotspot sur le new code, new_coverage 96,5 %, KPIs inchangés ; suites Release vertes.

## Lint log

### client-angular (`/lint-angular`)
- Commande : `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` (13 projets).
- Baseline : **0 erreur**, avertissements seulement (préexistants : `max-lines`, `jsdoc/require-example` hors des
  lignes ajoutées, vérifié ligne à ligne pendant `/develop`).
- Itérations : 0 — rien à corriger ; pas d'auto-fix (il reformaterait du code hors de la task). Arbre inchangé.
- Build / tests : vert de `/develop` réutilisé (`nx build weda2`, `nx test weda2` 2 683, `nx test mss-lib` 1 648).
- Code-only : aucune opération git d'écriture.
- Après la reprise 2 (spec e2e SEARCH-008) : lint rejoué, 0 erreur ; `functional.e2e.ts` 5 avertissements, comme sur HEAD.

## Lint mobile log

- `npm run lint` sur `feat/task-466-date-de-debut-du-suivi-par-boite` (95e6dc1) : **All files pass linting**.
- Itérations : 0 — rien à corriger, aucun commit. Build / tests : vert de `/develop` réutilisé (Karma 1 430/1 430).
- Après la reprise 2 : `client-mobile` inchangé (95e6dc1, arbre propre) — lint non rejoué, skip mesuré.

## E2E log

| Voie | Jouée / réutilisée | Résultat |
|---|---|---|
| mobile | jouée (api-mail 0f0605cd, client-mobile 95e6dc1) | ✅ 62/62, parité verte |
| angular | jouée (api-mail 0f0605cd, client-angular arbre de travail) | ✅ 83/83, parité verte |

Démontage vérifié : ports libres. Deux conteneurs `e2e-greenmail-*` / `e2e-dovecot-*` arrêtés depuis le 2026-10-14,
étrangers à ce run, restent présents (non supprimés).

Historique du cycle :
- 1er passage `/e2e` : voie mobile tombée en cours (serveur de l'app et API coupés ensemble, 7 `ERR_CONNECTION_REFUSED`,
  outillage), rejouée verte ; voie Angular **rouge** (PATIENT-004, SEARCH-008, SEARCH-010, DASH-001) — la donnée de seed
  `cr-bio-historique` rattachait un second compte rendu au patient des parcours web. Question posée, chaîne arrêtée.
- Reprise 2 (humain) : HPRIM historique au nom d'un patient fictif propre, SEARCH-008 ajusté à 3 lignes.
- 2e passage `/e2e` : les deux voies vertes.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

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
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
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
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

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

### Passage 2 (revue anticipée) — APPROVED

Relecteur indépendant, diff de reprise lu d'abord : rien de cassé ailleurs (fenêtre d'éviction `[min, max)`
cohérente avec `IsTracked`, méthode renommée sans autre implémentation, `Summary` sans état d'acquittement,
`isBiologyAckClaimed` passé `isTracked` par ses deux appelants, `FlaggedCdaArchive` rétrocompatible, comptage des
appels du cache fiable). B1, B3, B4, S3, S4, S6, S7, S9, S10 corrigés et prouvés ; S5 écarté, refus jugé défendable.

**approved at** : `dtos-mss` 957b28a, `api-mail` 011d661a, `client-mobile` 95e6dc1, `client-angular` arbre de travail
au 2026-11-13 (branche `feature/nova-mss-weda-integration`, base ce7741dd).

#### Suggestions (non bloquantes, pour la PR)
- **S-A** — `IsTracked` vaut `true` pour un document NON signalé d'un message historique (`untrackedDocIds` ne
  contient que les signalés), alors que le contrat dit « le message porteur est arrivé depuis la date de début ».
  Sans effet aujourd'hui (seuls les documents signalés sont lus) ; **à reprendre avant task-454** (« À traiter »),
  qui réutilisera ce champ : restreindre le commentaire du contrat, ou calculer `IsTracked` par message.
- **S-B** — le test B1 n'a pas de témoin positif pour `AcknowledgedPending` et `pending-mail-uids/page?lastAction=`
  (reculer la date dans le même test et voir l'uid apparaître). Serveur inchangé par la reprise : risque faible.
- **S-C** — `GetStateAsync` (gardé) devrait dire dans son commentaire qu'il ignore le suivi et ne rend jamais
  `BeforeTrackingStart`, avant qu'un appelant de task-454 ou task-463 ne s'en serve.
- **S-D** — l'éviction (au meilleur effort) reçoit le jeton d'annulation de la requête : une annulation pendant
  l'éviction rend 499 alors que la date est enregistrée et tracée. `CancellationToken.None` pour l'éviction.

### Passage 3 (revue anticipée, après la reprise 2) — APPROVED

Relecteur indépendant : la reprise **remplace** un message du seed (même âge, même état lu, même place) ; expéditeur,
objet, pièce et patient changés, sans effet sur les autres parcours des deux suites (BIO-003 désigne son HPRIM par
uid, empreinte HPRIM distincte par patient, « HISTOE2E » cité nulle part, DASH ne vérifie que l'affichage).
L'ajustement de SEARCH-008 est honnête (troisième ligne nommée par uid, présence avant absence). Les tests de
couverture de `/sonar` portent de vraies assertions.

**approved at** : `dtos-mss` 957b28a, `api-mail` 0f0605cd, `client-mobile` 95e6dc1, `client-angular` arbre de travail
au 2026-11-13 (base ce7741dd).

#### Suggestions (non bloquantes, pour la PR)
- **S-E** — `MailboxTrackingServiceTests.ALocalDate_IsConvertedToUtc` dépend du fuseau du poste : en UTC (runner CI),
  il ne distingue pas une conversion d'un simple `SpecifyKind`.
- **S-F** — `WithoutAPreviousDate_…` : la dernière assertion (`GetAsync` → `MinValue`) éprouve la doublure, pas le
  scénario ; la remplacer par `Received(1).SetTrackingStartAsync(requested, …)`.
- **S-G** — `E2eSeedPlan.cs` : le bloc `HistoricalHprimPatient` s'est inséré entre le `<summary>` de `HprimContent`
  et sa déclaration (doc déplacée) ; le remettre après `HprimContent`.
- **S-H** — catalogue, E2E-SEARCH-008 : ajouter `cr-bio-historique` à `seed:` (le parcours web en dépend désormais).
- **S-I** — commentaire de SEARCH-008 (web) : « Les deux lignes » → « Les trois lignes ».
- Traçabilité : la preuve rouge du test d'intégration « base sans ligne de suivi » (ajouté par `/sonar`) n'est pas
  consignée ; une mutation sur l'`Add` de `MailboxTrackingRepository` suffirait.

### Validation finale — APPROVED (2026-11-13)

- Build + tests : vert réutilisé pour `api-mail` (/sonar, 0f0605cd), `client-mobile` (/develop, 95e6dc1), `dtos-mss`
  (/develop, 957b28a) ; `client-angular` rejoué (arbre modifié depuis) : `nx build weda2`, `nx test mss-lib` 1 648,
  `nx test weda2` 2 683.
- DoD : toutes les lignes cochées (écart `[TracedInCode]` consigné). E2E double verrou : `## E2E log` vert,
  E2E-BIO-007 v1 au catalogue et dans les deux clients.
- Règle 1b : correspondance comportement → test → preuve rouge au Develop log (M1 à M9, rouges avant correctif).
- api-mcp : aucun impact (`Tools/contracts/mcp_impact.py check` → 0).
- Revue du diff depuis l'approbation (passage 3) : aucun commit de code depuis.
- Synchronisation `develop` : les trois dépôts poussables étaient à jour, aucun merge.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/66 — `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/368 — `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/124 — `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Branche `feature/nova-mss-weda-integration`.
  Liste des fichiers modifiés ci-dessous :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/models/audit.model.spec.ts`
  - `front/libs/mss/src/core/models/audit.model.ts`
  - `front/libs/mss/src/core/models/biology-ack.model.ts`
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/core/models/user-settings.model.ts`
  - `front/libs/mss/src/core/services/mss-api.service.spec.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/features/audit/components/audit-filter/audit-filter.component.ts`
  - `front/libs/mss/src/features/mail/components/biology-ack-panel/biology-ack-panel.component.html`
  - `front/libs/mss/src/features/mail/components/biology-ack-panel/biology-ack-panel.component.scss`
  - `front/libs/mss/src/features/mail/components/biology-ack-panel/biology-ack-panel.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/biology-ack-panel/biology-ack-panel.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.html`
  - `front/libs/mss/src/features/settings/mss-settings.component.spec.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.ts`
  - `front/libs/mss/src/core/models/biology-ack.model.spec.ts`
  - `front/libs/mss/src/core/utils/local-date.util.ts`

## Timings

*(généré par `tools/timing/report.sh --task task-466 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 33 s | — | — | — | — |
| /develop | ok | 12 min 28 s | 14 (3 min 02 s) | 27 (49 min 06 s) | — | dtos-mss 2B/0T, api-mail 7B/19T, client-angular 2B/5T, client-mobile 3B/3T, reprise 2 (e2e) |
| /review-code | ok | 4 min 21 s | — | — | — | — |
| /sonar | ok | 9 min 36 s | 3 (2 min 05 s) | 17 (24 min 21 s) | 6 (2 min 21 s) | 1 itération(s), api-mail 3B/17T |
| /lint-angular | ok | 22 s | — | — | — | 0 erreur (après reprise 2) |
| /lint-mobile | skipped | 1.0 s | — | — | — | client-mobile inchangé depuis le dernier lint propre (95e6dc1) |
| /e2e | ok | 20 min 25 s | — | 1 (7.9 s) | — | api-mail 0B/1T, e2e ×7 (49 min 07 s) |
| /review | ok | 3 min 56 s | 1 (14 s) | 2 (1 min 01 s) | — | client-angular 1B/2T |
| **Total cycle** | | **51 min 45 s** | **18 (5 min 21 s)** | **47 (1 h 14 min)** | **6 (2 min 21 s)** | |

Autres commandes mesurées : lint ×3 (50 s), nuget-wait ×2 (38 s), restore ×2 (7.1 s)
