# todo-task-274.md — Chaque widget du tableau de bord a son interrupteur (feature flag)

**Repos**: api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: —
**Epic**: E015

## Objectif

L'arrivée sur le tableau de bord est le **geste le plus fréquent du parcours**
et le **deuxième poste du temps serveur** mesuré au banc (24,8 % au palier 1000,
campagne du 2026-08-26) — porté par plusieurs appels distincts (dossiers,
compteur du jour, couverture de synchro…). Aujourd'hui, impossible d'attribuer
la charge à un widget précis autrement que par instrumentation, et impossible
de **délester** en production si un widget se révèle coûteux.

**Intention** : chaque widget du tableau de bord est gouverné par un feature
flag Flagsmith. Flag OFF → le widget est **masqué ET son appel API n'est pas
émis** — c'est le point central : masquer sans couper l'appel ne changerait
rien à la charge, l'objectif est un interrupteur de charge, pas un interrupteur
d'affichage. Bénéfices : attribution de charge par activation/désactivation
sélective (pré-prod, banc en conditions réelles), et levier d'exploitation en
cas d'incident (délester le widget coûteux sans redéployer).

**Règles métier** (le cœur de l'US) :

1. **Fail-open, sans exception** : flag absent, Flagsmith injoignable, endpoint
   en erreur, réponse lente → **tout est visible**, comportement d'aujourd'hui.
   Un cabinet médical ne perd jamais un widget à cause d'un incident de
   configuration. Aucune erreur visible du praticien.
2. **Coût nul sur le geste** : la lecture des flags ne doit PAS ajouter un
   appel à chaque affichage du tableau de bord (ce serait aggraver le poste
   qu'on instrumente). Les flags sont lus **une fois par session applicative**
   (au démarrage de l'app ou à la connexion, via l'endpoint existant
   `GET /api/v1/FeatureFlag`), mis en cache côté client, rafraîchis au plus
   toutes les N minutes (N ≥ 5, choix d'implémentation documenté). Un
   changement de flag se propage donc en quelques minutes — c'est accepté,
   l'usage est l'investigation et le délestage, pas le temps réel.
3. **Convention de nommage imposée** : `dashboard_widget_{slug}` (kebab/snake
   du nom du widget), identique sur les trois fronts pour le même widget —
   c'est ce qui rend l'attribution lisible dans Flagsmith. La liste des huit
   flags est fixée par l'inventaire préliminaire ci-dessous (section
   « Inventaire préliminaire widgets/flags ») ; `/develop` la confirme widget
   par widget en codant, complète la correspondance widget → appels serveur,
   et consigne l'inventaire final dans la task — repris dans le body des PRs
   pour que l'humain crée les flags dans Flagsmith.
4. **Création des flags — deux mondes** : sur le **banc**, le
   `FlagsmithSeeder` de l'AppHost (task-177, `src/AppHost/FlagsmithSeeder.cs`)
   crée déjà les flags de façon idempotente (`default_enabled = true`) — la US
   **ajoute les huit `dashboard_widget_*` à son tableau `FeatureFlags`** : au
   prochain démarrage du banc ils existent, ON. Dans les **environnements
   réels** (staging/prod), la création reste un geste d'exploitation manuel à
   partir de la liste livrée — le code applicatif ne crée jamais de flag
   (l'API admin et son token n'ont rien à faire hors du seeder de banc).
   Dans tous les cas le code des fronts se comporte correctement que les
   flags existent ou non (règle 1).
5. **Un widget masqué ne laisse pas de trou** : la mise en page se recompose
   proprement (pas d'emplacement vide figé).

**Hors périmètre, dit explicitement** :
- Côté `api-mail`, SEUL le seeder de banc (`src/AppHost/FlagsmithSeeder.cs`)
  change : l'endpoint `FeatureFlagController` existant suffit tel quel, et
  aucun garde serveur par flag (couper l'appel côté client coupe la charge —
  un garde serveur dupliquerait la logique pour rien).
- Le harnais k6 (l'attribution au banc passe déjà par les probabilités
  `JOURNEY_*` par geste ; les flags servent l'attribution en conditions
  réelles et le délestage).
- Tout widget hors tableau de bord.

## Inventaire préliminaire widgets/flags (PO, 2026-08-27 — à confirmer par /develop)

Huit flags, mêmes noms sur les trois fronts, tous créés **ON** :

| Flag | Widget | Blazor | Angular | Mobile |
|---|---|---|---|---|
| `dashboard_widget_mail_counters` | Compteurs de messagerie (dossiers, non-lus) | MailWidget | mss-mail-widget | messaging-counters-widget |
| `dashboard_widget_mail_notifications` | Notifications de nouveaux messages | MailNotificationWidget | mss-mail-notification-widget | — |
| `dashboard_widget_today_summary` | Résumé du jour / non-lus du jour | — | — | today-unread-summary-widget |
| `dashboard_widget_abnormal_biology` | Biologies anormales | AbnormalBiologyWidget | mss-abnormal-biology-widget | abnormal-biology-widget |
| `dashboard_widget_biology_ack_pending` | KPI acquittements en attente ⚠️ outil d'incident uniquement (obligation métier) | BiologyAckPendingKpiTile | mss-biology-ack-pending-kpi-tile | biology-ack-pending-tile |
| `dashboard_widget_patients` | Patients / documents non lus | PatientWidget | mss-patient-widget | patients-unread-widget |
| `dashboard_widget_sync_progress` | Couverture / progression de synchro | SyncProgressWidget | mss-sync-progress-widget | — |
| `dashboard_widget_offline_status` | Statut de connexion (candidat à l'exclusion : info « mode dégradé », charge locale) | OfflineStatusWidget | mss-offline-status-widget | — |

/develop confirme la correspondance widget → appels serveur et signale toute
divergence ; les NOMS ci-dessus sont définitifs sauf objection d'inventaire.

## Definition of Done

- [ ] Build + tests verts sur les quatre repos (`api-mail`, `client-blazor`,
      `client-angular` code-only, `client-mobile`)
- [ ] Les huit flags `dashboard_widget_*` de l'inventaire sont ajoutés au
      tableau `FeatureFlags` de `FlagsmithSeeder` (AppHost, banc uniquement,
      `default_enabled = true`) — au démarrage du banc ils existent, ON
- [ ] Inventaire des widgets par front consigné dans la task (section
      `## Inventaire widgets/flags`), avec le nom de flag de chaque widget —
      convention `dashboard_widget_{slug}`, mêmes noms sur les trois fronts
- [ ] Flag OFF → le widget n'est pas rendu **et son appel API n'est pas émis**
      (test par front : composant/service avec flag coupé → zéro requête vers
      la route du widget)
- [ ] Flag absent ou lecture des flags en échec → tous les widgets visibles,
      aucun message d'erreur praticien (test du fail-open par front)
- [ ] La lecture des flags est faite au plus une fois par session applicative
      + rafraîchissement périodique — PAS à chaque affichage du dashboard
      (test : deux affichages successifs → une seule lecture des flags)
- [ ] Aucune chaîne en dur côté UI (i18n) pour tout libellé éventuel ;
      `data-testid` sur tout élément interactif ajouté
- [ ] Aucun changement de contrat d'API (l'endpoint FeatureFlag existant est
      consommé tel quel)

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
  (le conteneur Flagsmith du profil démarre avec lui), puis le front à tester
  (Blazor : `Client/Blazor` ; mobile : `cd Client/Mobile && npm start` ;
  Angular : selon la branche humaine).
- Vérifier dans l'admin Flagsmith du banc que les huit `dashboard_widget_*`
  ont été créés par le seeder au démarrage, tous **ON** (aucune création
  manuelle au banc).
- Mettre `dashboard_widget_mail_counters` **OFF** (sur mobile, tester aussi
  `dashboard_widget_today_summary`).
- Ouvrir le tableau de bord : le widget des compteurs de messagerie est absent,
  la mise en page est propre, et l'onglet Réseau (DevTools) **ne montre pas**
  ses appels (`GET /mail/folders`…).
- Remettre le flag **ON** : au prochain rafraîchissement de session (ou après
  le TTL), le widget revient et l'appel repart.
- Supprimer le flag / couper Flagsmith : tous les widgets visibles, aucun
  message d'erreur (fail-open).
- Vérifier qu'ouvrir deux fois le dashboard ne déclenche qu'une lecture des
  flags (Réseau : un seul `GET /api/v1/FeatureFlag` par session).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage d'exploitation/attribution de
  charge, aucun changement du contenu médical affiché quand les flags sont ON
  (état par défaut)
- **Exigences DSR honorées** : non applicable — aucun flux MSSanté modifié.
  ⚠️ Point de vigilance : si un widget porteur d'une obligation d'affichage
  (ex. acquittements de biologie, task-118 et suivantes) entre dans
  l'inventaire, son flag doit être documenté comme **outil d'incident
  uniquement** — le masquer en usage nominal dégraderait une exigence métier ;
  `/develop` le signale dans l'inventaire et le PO tranche flag par flag
- **INS** : non applicable — aucun traitement patient modifié
- **Authentification PS** : inchangée (l'endpoint FeatureFlag est derrière
  l'authentification existante)
- **Habilitations** : inchangées — les flags sont globaux (pas de ciblage par
  praticien dans cette US)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable côté produit (des booléens d'affichage,
  aucune donnée de santé) ; l'historique des changements de flags vit dans
  Flagsmith
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — Flagsmith fait déjà partie de la plateforme
- **AIPD / impact RGPD** : néant — aucun nouveau traitement de données

## Branches
- `api-mail` (pushed) : feat/task-274-dashboard-widget-flags — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-274-dashboard-widget-flags
- `client-blazor` (pushed) : feat/task-274-dashboard-widget-flags — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-274-dashboard-widget-flags
- `client-mobile` (pushed) : feat/task-274-dashboard-widget-flags — https://github.com/codengine-technologies/HealthPlatform.Client.Mobile/tree/feat/task-274-dashboard-widget-flags
- `dtos-mss` (pushed, auto-inclus) : feat/task-274-dashboard-widget-flags — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-274-dashboard-widget-flags
- `client-angular` (code-only) : la forge écrit sur la branche actuellement checked out dans `Client/Angular/` (snapshot au /start : `feature/nova-rewriting-mss`) — humain gère branche, commit, push, PR TFS

## Inventaire widgets/flags (final, /develop 2026-08-27)

L'inventaire préliminaire du PO est confirmé tel quel — 8 flags, aucun widget
supplémentaire découvert, aucune divergence de nom :

| Flag | Blazor (IFlaggedWidget) | Angular (mss-dashboard) | Mobile (home) | Appels serveur coupés quand OFF |
|---|---|---|---|---|
| `dashboard_widget_mail_counters` | MailWidget | mss-mail-widget | messaging-counters-widget | `GET /mail/folders` (compteurs) |
| `dashboard_widget_mail_notifications` | MailNotificationWidget | mss-mail-notification-widget | — | résumé des non-lus |
| `dashboard_widget_today_summary` | — | — | today-unread-summary-widget | `…/emails/today`, `…/unread/today` |
| `dashboard_widget_abnormal_biology` | AbnormalBiologyWidget | mss-abnormal-biology-widget | abnormal-biology-widget | biologies anormales |
| `dashboard_widget_biology_ack_pending` ⚠️ | BiologyAckPendingKpiWidget | mss-biology-ack-pending-kpi-tile | biology-ack-pending-tile | KPI acquittements |
| `dashboard_widget_patients` | PatientWidget | mss-patient-widget | patients-unread-widget | patients non lus |
| `dashboard_widget_sync_progress` | SyncProgressWidget | mss-sync-progress-widget | — | `GET /sync/coverage` |
| `dashboard_widget_offline_status` | OfflineStatusWidgetDefinition | mss-offline-status-widget | — | statut local (charge ~nulle) |

⚠️ `biology_ack_pending` : obligation métier — outil d'incident uniquement
(consigne d'exploitation, cf. Conformité santé).

## Journal d'implémentation (/develop, 2026-08-27)

- **api-mail** (`878794c`) : 8 flags ajoutés au `FlagsmithSeeder` (banc, ON).
- **client-blazor** (`29c988f`) : contrat opt-in `IFlaggedWidget` + service
  `DashboardWidgetFlagService` (fail-open, cache 5 min, vol unique, budget
  3 s) sur l'endpoint existant ; gating dans `DashBoard.razor` (composant
  jamais instancié = appels jamais émis ; service absent = tout visible) ;
  7 widgets marqués. 6 tests (ProbeComponent compte les initialisations).
  Build vert, 150/152 tests (2 skips pré-existants).
- **client-mobile** (`86c3406`) : `DashboardWidgetFlagsService` (signal,
  mêmes règles), `MssApiService.getFeatureFlags()` (defer), `@if` sur les 5
  widgets du home, `ensureLoaded()` fire-and-forget à l'entrée d'onglet.
  6 tests. Build vert, 769/769.
- **client-angular** (code-only, branche humaine `feature/nova-rewriting-mss`,
  NON committé) : même triptyque (service signal + `getFeatureFlags()` +
  `@if` sur les 7 sélecteurs, en-têtes de section suivant leur widget).
  7 tests vitest. `mss-lib:test` 322/322, build `weda2` (aval) vert.
  Arbre humain préservé (2 fichiers environments modifiés pré-existants,
  non touchés).
- **dtos-mss** : aucun changement de contrat, branche sans commit.

## Simplify log (/forge-simplify, 2026-08-27)

- Examiné sur les 4 repos : rien à simplifier de substantiel — code mince,
  symétrique par construction. La duplication du service de flags entre
  `client-mobile` et `client-angular` est structurelle (workspaces sans lib
  partagée ; le mobile est le « miroir raisonné » d'Angular, convention
  existante du repo). `dtos-mss`/`interop-cda` non touchés.

## Sonar log (/sonar, 2026-08-27)

- Skip motivé : le seul fichier api-mail touché (`src/AppHost/FlagsmithSeeder.cs`)
  est dans un chemin **exclu de l'analyse Sonar** (`sonar.exclusions:
  **/AppHost/**`) — une analyse complète ne produirait aucun finding
  attribuable à la task. Build AppHost vert (validation /develop).

## Lint log (/lint-angular, 2026-08-27)

- Baseline scope MSS (`tag:scope:mss`, base `origin/next`) : mss-lib en échec
  sur le code frais de la task (prettier + jsdoc) — 5 erreurs.
- It. 1 : `--fix` (prettier + squelettes JSDoc auto), puis JSDoc remplis à la
  main (`@param`/`@returns`/`@example` réels, conventions du CLAUDE.md repo).
- Final : **0 erreur**, 35 warnings résiduels (jsdoc/@example et max-lines
  pré-existants du fichier mss-api.service, hors périmètre) ; `mss-lib:test`
  322/322 verts. Code-only : rien de committé (git humain).

## Lint mobile log (/lint-mobile, 2026-08-27)

- Baseline : **0 erreur, 0 warning** (« All files pass linting ») — rien à
  corriger, aucun commit de lint. Build + 769 tests déjà verts (/develop).

## Visual verify log (/verify-visual, 2026-08-27)

- Best-effort, non bloquant : l'outillage `tools/visual-verify/` est absent de
  ce poste (aucun `capture.mjs`) — capture impossible. Aucun design nouveau
  (pas de `## Stitch design log` : gating pur, rendu identique flags ON).
  Filet compensatoire : specs de rendu du `home` verts (769/769), dont les
  nouveaux tests @if (flag OFF → sélecteur absent, défaut → tous rendus).
  Le juge visuel reste l'humain au HAG (Manual Test Plan).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/204 — label `awaiting-human-merge` (seeder banc)
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/69 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/63 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit (pas de changement de contrat) — pas de PR ; branche à supprimer au /merge
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR (branche `feature/nova-rewriting-mss`). Fichiers modifiés/ajoutés par la forge :
  -  M front/apps/mss/src/environments/environment.ts
  -  M front/apps/weda2/src/environments/environment.ts
  -  M front/libs/mss/src/core/services/mss-api.service.ts
  -  M front/libs/mss/src/core/utils/reply-all-recipients.util.ts
  -  M front/libs/mss/src/features/dashboard/mss-dashboard.component.html
  -  M front/libs/mss/src/features/dashboard/mss-dashboard.component.ts
  -  M front/libs/mss/src/features/mail/components/ai-chat-panel/ai-chat-panel.component.ts
  - ?? front/libs/mss/src/core/services/dashboard-widget-flags.service.spec.ts
  - ?? front/libs/mss/src/core/services/dashboard-widget-flags.service.ts
  - ?? front/libs/mss/src/features/dashboard/mss-dashboard.component.spec.ts

## Code Review Summary

APPROVED — 0 bloquant. 1 suggestion : le DashBoard Blazor attend la première lecture des flags (3 s max, une fois par session) là où mobile/Angular sont en fire-and-forget — à aligner si la latence du premier affichage devient visible. Duplication mobile/Angular du service : structurelle (workspaces distincts, convention miroir). Règle 11 : les 3 PRs GitHub + le diff Angular forment UNE US — test humain sur l'ensemble assemblé avant merge.

## Merged (2026-08-29, /merge --i-tested)

- `api-mail` : squash `0cd80d4` (PR #204 closed)
- `client-blazor` : squash `63aeb52` (PR #69 closed)
- `client-mobile` : squash `46015b7` (PR #63 closed)
- `dtos-mss` : aucun commit — branche distante supprimée sans PR
- `client-angular` : code-only — managed manually by the human

**Arbitrage humain (2026-08-28/29)** : gate CI — `build-android` (PR #63) a
nécessité deux correctifs sur branche (rétention APK 3 j `ddce79d0` ; lock
régénéré sous npm 10.9.8 `03d1750` — le lock npm 11 local était invalide pour
le runner). Après quoi npm ci + build + Gradle passent ; seul l'upload d'APK
échoue encore (« Artifact storage quota has been hit », infra préexistante,
recalcul 6-12 h). L'humain a tranché : « merge quand même ».
