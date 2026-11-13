# E024 — Messagerie premium : traiter, déléguer, boucler — Changelogs

> **Audience** : équipes techniques (ingénierie, backlog, dette)
> **Vue produit** : [E024-messagerie-premium-traiter-deleguer-bouc.md](E024-messagerie-premium-traiter-deleguer-bouc.md)
> **Dernière mise à jour** : 2026-11-13

---

## Historique détaillé des changelogs

### v0.1 — task-453 : un acquittement ne disparaît jamais (api-mail, dtos-mss, client-mobile, weda2)

- **État** : `archived` — PRs mergées par l'humain.
- **PRs** : api-mail [#364](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/364),
  dtos-mss [#63](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/63),
  client-mobile [#123](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/123). client-angular en
  code-only : 4 fichiers non commités sur `feature/nova-mss-weda-integration` (`audit.model.ts` + spec,
  `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`), **à commiter sur TFS avant le merge de
  la PR api-mail**.
- **NuGet** : `HealthPlatform.Dtos.Mss` 588.0.0 → **591.0.0** (`AuditActionType.DocumentWorkStateRelinked = 70`,
  `DocumentWorkStateRelinkSkipped = 71`) ; bump `api-mail` seul.
- **Défaut** : `Mails` → `MailMedicalDocuments` → `BiologyAcks` en `CASCADE`. Un déplacement hors plateforme
  (`DeleteMailsByUidsAsync` puis ré-ingestion), une purge d'UIDVALIDITY (`FolderRepository.SyncUidValidityAsync`) ou
  une suppression/restauration détruisaient acquittements et rattachement manuel. Prouvé par 8 tests d'intégration
  rouges sur `aeee2ba2`.
- **Conception** (ADR `Docs/adr/ADR-2026-11-11-ancrage-etats-de-travail.md`) :
  - `Domain/Rules/DocumentAnchor` : `v1:` + SHA-256(`Message-ID` + `\n` + identité) ; identité = `fp:{empreinte}`
    (HPRIM) ou `cda:{DocumentId}|{SetId}|{Version}` ; pas de clé pour `EMAIL` ni sans `Message-ID` ;
  - `BiologyAcks.AnchorKey`, `MedicalDocumentId` nullable, FK `SET NULL` ; table `ManualPatientAttachments`
    (`UX_…_AnchorKey`, patient `CASCADE`, document `SET NULL`) ; `MailMedicalDocuments.AnchorKey` (index partiel) ;
  - `DocumentWorkStateRelinker` : re-liaison à l'identique à l'ingestion (insertion et promotion, dans la
    transaction) et après la purge de `DeleteMailsByUidsAsync` ; une requête dans le cas courant (union des clés en
    attente) ; > 1 candidat → rien, avertissement + trace `DocumentWorkStateRelinkSkipped` ;
  - traces système après validation (`MailRepository.TraceRelinks`) ; `AuditService.Impute` laisse système un acte
    déclaré système ; `IAuditService` optionnel dans le constructeur DI de `MailRepository` ;
  - migration `20261111120000_AnchorDocumentWorkStates` : **schéma seul**. La reprise SQL d'abord écrite (clé des
    documents et des acquittements existants, rattachements manuels) a été **retirée** après la revue, sur décision
    humaine du 2026-11-12 (bases de test uniquement, perte des données existantes acceptée) — `fa144450`.
- **Tests** :
  - intégration `FolderOperationsEndToEndTests.WorkStateAnchoring` : 11 cas (déplacement, UIDVALIDITY,
    corbeille/restauration, destruction puis retour, ordre inverse purge/ingestion, CDA sans INS rattaché à la main,
    détachement, HPRIM, ambiguïté, délégataire) ;
  - migration `AnchorDocumentWorkStatesMigrationTests` (aucune ligne existante touchée — rouge sur la version avec
    reprise —, `confdeltype = 'n'`, aller-retour) ;
  - unitaires `DocumentAnchorTests` (11), `DocumentWorkStateRelinkerTests` (6), `AuditServiceSystemActTests`, contrat
    et rétention d'audit ;
  - mutations M1 à M7, toutes rouges sur l'assertion prévue (M7, détachement, faite à `/review`).
- **Suite complète api-mail** (état fusionné avec `develop`) : domain 221, infrastructure 749, application 4 197, api
  1 376, integration 1 263 — 0 rouge.
- **Sonar** : 1 issue imputable (S3776 sur `RelinkAsync`, complexité 16), corrigée (`RelinkKeyAsync`) ; aucune
  restante. QG projet ERROR inchangé dans ses causes (dette antérieure de la période « new code »).
- **Lint** : weda2 0 erreur sur les fichiers de la task ; mobile hors portée de `ng lint` (fichiers e2e seuls).
- **E2E** : E2E-BIO-004 v1 (mobile, angular) ajouté ; prouvé rouge sur le backend sans re-liaison (mutation M6),
  vert sur le correctif. `/e2e` : mobile 61 verts, angular 78 verts (3 flaky), porte verte sur le catalogue du merge
  à venir. Outil e2e : `message --move`, `message --create --kind bio-hprim`.
- **Limites différées** (suggestions de revue) : re-liaison après purge seulement sur `DeleteMailsByUidsAsync` ;
  re-liaison après purge hors transaction ; unicité `ManualPatientAttachments.AnchorKey` sans upsert SQL ; surcharge
  `IAuditService.TraceSystem` plutôt qu'un `IsSystemAct` posé par l'appelant.


### v0.2 — task-465 : mesurer la charge de la boîte (api-mail, dtos-mss) — ANNULÉE

- **État** : **annulée** le 2026-11-12 (voir l'entrée « Annulation de task-465 » ci-dessous) ; rien sur `develop`.
- **PRs** : api-mail [#366](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/366),
  dtos-mss [#64](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/64).
- **NuGet** : `HealthPlatform.Dtos.Mss` 597.0.0 → **601.0.0** (`AuditActionType.MailboxLoadComputed = 72`, famille
  technique) ; bump `api-mail` seul. Miroirs à reporter : `client-angular` `audit.model.ts`, `client-blazor`
  `AuditActionLabels.cs`.
- **Conception** :
  - migration registre `20261112090000_AddMailboxLoadStatistics` : rôle `mss_audit_statistics` (NOLOGIN, `SELECT` sur
    `audit_traces` et `mss_mailboxes(id, created_at)`), politique RLS `audit_traces_statistics_read`, tables
    `mailbox_load_days` / `mailbox_load_values` (`CHECK mailbox_count >= 5`) ;
  - `PostgresMailboxLoadStore` : faits du jour sous `SET LOCAL ROLE` (gestes, réceptions INBOX dédupliquées avec
    rodage de 24 h après création de la boîte, premières lectures, premiers acquittements, réception cherchée 30 j) ;
  - `MailboxLoadCalculator` (seuil par découpage, sessions à 15 min d'inactivité + 1 min, quantiles interpolés),
    `MailboxLoadCalendar` (Europe/Paris), `MailboxLoadGestures` (52 actions comptées, liste d'exclusion, test
    d'exhaustivité) ;
  - `MailboxLoadHostedService` : passe horaire, 7 jours rattrapés, verrou Redis `lock:mailbox-load:{jour}` (6 h),
    sans Redis aucun calcul ; jauges `mss_mailbox_load{indicator,breakdown,statistic}` et `mss_mailbox_load_day` ;
  - `GET /api/v1/product-metrics/mailbox-load?from=&to=` (366 j max) : `X-Product-Metrics-Key`, 404 sans clé
    configurée, 401 sinon, 400 RFC 7807 ; clé de dev dans l'AppHost ;
  - tableau de bord `src/AppHost/grafana/dashboards/mssante-mailbox-load.json` (13 panneaux + 3 réservés).
- **Écart de DoD à arbitrer** : le calcul ne lit pas les bases de boîte (catégorie tirée du LOINC du journal ; pool par
  praticien et règle 14) ; réception = instant vu par la plateforme.
- **Tests** : 61 unitaires (`Services/ProductMetrics/`), 9 d'intégration `MailboxLoadEndpointIntegrationTests` (base
  de registre propre à la classe) ; mutations : politique RLS fermée, seuil 4 (code + `CHECK` → `23514`), rodage
  retiré, validation de plage, clé de personne en découpage, contrôle de clé, garde de configuration — toutes rouges.
- **Suite complète api-mail** : domain 221, infrastructure 749, application 4 284, api 1 380, integration 1 291
  (+16 ignorés) — 0 rouge. Rouge préexistant instable, aussi sur `develop` :
  `TenantRegistryIntegrationTests.AttachMailboxAsync_UnderConcurrency_PersistsExactlyOneTenant`.
- **Sonar** : 4 findings dans le diff (CA1068, ASP0025, S138 ×2 aggravés sur `ConfigureOpenTelemetry` et
  `AddApplication`) → corrigés (`AddMssMeters`, `AddImap`, `AddMailSending`, `AddSemanticSearch`) ; 0 restant ;
  new coverage 97,8 → 97,9 %, new violations 98 → 96, code smells 94 → 92 ; QG projet ERROR inchangé dans ses causes.
- **E2E** : mobile 61 verts ; Angular 80 verts, 2 flaky (E2E-SEARCH-001, E2E-LIVE-001), quarantaine E2E-COMPOSE-002
  (34 j) ; porte verte. Aucun scénario ajouté (aucun parcours médecin).
- **Restes** : capture Grafana et mesure de référence sur la recette (HAG) ; secret `ProductMetrics__MailboxLoad__ApiKey`
  (DevOps) ; AIPD.


### v0.2.1 — task-465 (reprise du 2026-11-12) : indicateurs d'usage (api-mail) — ANNULÉE

- **Décision humaine** : ajoutés dans la même PR (#366, encore ouverte).
- **Indicateurs** : `connected_persons` (traces `MailboxSessionOpened`), `active_mailboxes`, `registered_mailboxes`
  et `registered_delegates` (`mss_accounts` actifs en fin de journée), `active_persons` (all/holder/delegate/member),
  `active_persons_by_hour` et `gesture_share_by_hour` (`00`…`23`, Paris) ; seuil 5 boîtes par valeur et par tranche.
- **Migration** `20261112110000_GrantMailboxLoadRegistryRead` : `GRANT SELECT (mailbox_id, account_id, role,
  attached_at, detached_at) ON mss_accounts` au rôle statistique.
- **Tableau de bord** : rangée « Usage » (6 stats) et 2 histogrammes horaires ; 29 panneaux.
- **Tests** : 69 unitaires, 10 d'intégration (`…ExposesUsage`) ; mutations : droit retiré (`42501`), borne de fin de
  journée retirée (`5` → `7`), heure en UTC — toutes rouges. Suite complète : 7 934 verts.
- **Sonar** : 0 finding dans le diff. **E2E** : mobile 61, Angular 80 (mêmes 2 flaky), porte verte.


### Retrait des tasks 454 à 466 (2026-11-12, décision humaine)

- **Décision** : l'humain ne souhaite pas engager ces développements. Les task files `todo` 454 à 464 et 466, et
  le task file archivé de task-465 (déjà annulée), sont **supprimés sans archivage**.
- **Rien à défaire dans le code** : aucune branche, aucune PR, aucun commit applicatif n'existait pour ces tasks.
- **Reste de l'EPIC** : task-453, livrée.

### Annulation de task-465 (2026-11-12, décision humaine)

- **Motif** : calcul jugé trop lourd pour l'API et ajoutant de la complexité (tâche de fond dans chaque réplica,
  lecture du journal de toutes les boîtes, verrou Redis, rôle statistique).
- **Défait** : PR api-mail [#366](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/366) et
  dtos-mss [#64](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/64) fermées sans merge ;
  branches `feat/task-465-mesurer-la-charge-de-la-boite` supprimées (locales et distantes). Paquet
  `HealthPlatform.Dtos.Mss` 601.0.0 publié mais non référencé ; ordinal 72 libre.
- **Conséquences** : task-454 et task-456 ne dépendent plus de task-465 ; leurs indicateurs de tableau de bord sont
  retirés de leur DoD.
- **Suite** : extraction des usages par un **cron job hors de l'API**, sur la base d'un rapport journalier (task à
  rédiger). Le task file de task-465 a été supprimé le 2026-11-12 ; sa conception et ses preuves restent dans l'historique git
  du plan de contrôle (commit `14464bf`).
- **Acquis conservés** : consignes `conventions/csharp.md` (S125, S4457, CA1068, S138, ASP0025,
  capture-de-metriques-serialisee), registre e2e des flaky.

### v0.3 — task-466 : date de début du suivi par boîte (api-mail, dtos-mss, client-mobile, weda2)

- **Contexte** : task réécrite le 2026-11-13 après le retrait du 2026-11-12 ; tasks 454, 456 à 459 et 462 de nouveau
  au backlog (454 dépend de 466).
- **État** : `done` — PRs ouvertes, `awaiting-human-merge` : api-mail
  [#368](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/368), dtos-mss
  [#66](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/66), client-mobile
  [#124](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/124). client-angular en code-only :
  22 fichiers non commités sur `feature/nova-mss-weda-integration`.
- **NuGet** : `HealthPlatform.Dtos.Mss` 597.0.0 → 604.0.0 (`MailDto.ArrivalDate`,
  `BiologyAckResolutionState.BeforeTrackingStart = 3`, `AuditActionType.MailboxTrackingStartChanged = 72`,
  `MailboxTrackingStartDto`, `MailboxErrorCodes.TrackingStartInFuture`) → **607.0.0** (`MailMedicalDocumentDto.IsTracked`,
  reprise 1) ; bump `api-mail` seul.
- **Conception** :
  - `Mails.ArrivalDate` (INTERNALDATE, insertion et promotion d'en-tête `??=`) ; table `MailboxTrackingStart` (une
    ligne), migration `20261113120000_AddMailboxTrackingStart` (date = montée de la base − 5 min, tronquée à la seconde) ;
  - `Domain/Rules/MessageTracking` : `IsTracked` (mémoire), `TrackedSince` (SQL), repli `SentDate`, sans date →
    historique ; appliquée à `pending-summary`, `pending-mail-uids[/page]` et à l'état des documents de `emails/{ids}` ;
  - `IsTracked` posé par document, indépendant de l'acquittement (un historique « en cours » ne réclame rien) ;
  - `GET/PUT api/v1/account/mailboxes/current/tracking-start` : date future → 400 `MAILBOX_TRACKING_START_IN_FUTURE`,
    corps sans date → 400 ; `[TracedInCode]` (ancienne et nouvelle date dans la trace) ;
  - éviction du seul contenu en cache (`RedisKeys.Mail.Email`) des messages reclassés (fenêtre [min, max) entre les
    deux dates), par lots de 50.
- **Tests** : intégration `FolderOperationsEndToEndTests.TrackingStart` (10 cas : avant/après la date, 400, UIDVALIDITY,
  recul de la date, délégataire, geste intermédiaire, cache de contenu, promotion d'en-tête, base sans ligne) ;
  migration `MailboxTrackingStartMigrationTests` ; unitaires règle, service, exception. Mutations M1 à M9 rouges ;
  B1 et S9 rouges avant correctif (weda2, mobile).
- **Suite complète api-mail** : domain 237, infrastructure 749, application 4 236, api 1 381, integration 1 295
  (+16 ignorés) — 0 rouge. Mobile Karma 1 430 ; weda2 2 683, mss-lib 1 648.
- **Sonar** : 1 S3925 (faux positif, triplet présent) ; QG OK, new coverage 96,3 → 96,5 %, 0 bug / smell.
- **E2E** : E2E-BIO-007 v1 (mobile, angular). 1er `/e2e` rouge (Angular : PATIENT-004, SEARCH-008, SEARCH-010,
  DASH-001) — donnée de seed sur le patient partagé ; corrigé en reprise 2 (HPRIM « HISTOE2E Dominique »). 2e `/e2e` :
  mobile 62/62, angular 83/83, porte verte.
- **Revue** : 3 passages (CHANGES REQUESTED B1/B3/B4, puis APPROVED ×2), 2 reprises.
- **Arbitrage ouvert (merge)** : B2 — la migration classe « antérieur au suivi » les résultats en attente des boîtes
  existantes ; S1 pose initiale non tracée ; S2 widget « Résultats anormaux » hors suivi ; S8 `ArrivalDate` sans `Z`.
- **Avant task-454** : S-A (`IsTracked` vrai pour un document non signalé d'un message historique), S-C
  (`GetStateAsync` ignore le suivi).

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle | Task |
|---|---|---|
| `api-mail/src/Domain/Rules/DocumentAnchor.cs` | identité stable d'un document reçu | task-453 |
| `api-mail/src/Domain/Entities/MailDb/ManualPatientAttachment.cs` | rattachement manuel ancré | task-453 |
| `api-mail/src/Infrastructure/Repositories/MailDb/DocumentWorkStateRelinker.cs` | re-liaison des états orphelins | task-453 |
| `api-mail/src/Infrastructure/Repositories/MailDb/MailRepository.WorkStates.cs` | clé à l'ingestion, re-liaison, traces | task-453 |
| `api-mail/src/Infrastructure/Migrations/MailDb/20261111120000_AnchorDocumentWorkStates.cs` | schéma (sans reprise de données) | task-453 |
| `dtos-mss/AuditActionType.cs` (70, 71) | actes système de re-liaison | task-453 |
| `api-mail/tests/mss.mail.e2e/E2eMessage.cs` | `message --move`, `--kind bio-hprim` | task-453 |
| `api-mail/src/Domain/Rules/MessageTracking.cs` | règle unique du suivi | task-466 |
| `api-mail/src/Infrastructure/Migrations/MailDb/20261113120000_AddMailboxTrackingStart.cs` | `Mails.ArrivalDate`, table `MailboxTrackingStart` | task-466 |
| `api-mail/src/Application/Services/Mailboxes/MailboxTrackingService.cs` | lecture, changement tracé, éviction | task-466 |
| `api-mail/src/Api/Controllers/V1/MailboxTrackingStartController.cs` | `account/mailboxes/current/tracking-start` | task-466 |
| `dtos-mss/MailMedicalDocumentDto.cs` (`IsTracked`), `BiologyAckResolutionState` (3) | contrat du suivi | task-466 |
| weda2 `libs/mss/src/core/models/biology-ack.model.ts` (`isBiologyAckClaimed`) | règle « réclamé » côté web | task-466 |
| client-mobile `core/services/mailbox-tracking.service.ts` | date de la boîte ouverte | task-466 |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-13)

- Tasks de l'EPIC : 9 (1 `archived`, 1 `done`, 1 annulée, 6 `todo`).
- Scénarios e2e de l'EPIC au catalogue : 2 (E2E-BIO-004, E2E-BIO-007).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | État |
|---|---|---|
| task-453 | Ancrage des acquittements et du rattachement manuel à l'identité stable du document ; re-liaison ; modèle imposé aux tasks 454 à 463 | `archived` (PRs #364, #63, #123) |
| task-465 | Mesure de la charge et de l'usage — **annulée** le 2026-11-12 (décision humaine, reprise hors API par un cron job) | annulée (PRs #366, #64 fermées) |
| task-466 | Date de début du suivi par boîte : seul ce qui arrive après réclame un acquittement ; socle de « À traiter » (task-454) | `done` (PRs #368, #66, #124) |
