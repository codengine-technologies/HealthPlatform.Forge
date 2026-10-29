# todo-task-403 — L'accès à la base d'une boîte est ouvert par l'opérateur MSSanté

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-402 (le rôle du rattachement)
**Epic**: E020

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 — « l'opérateur ouvre l'accès ; seule
> exception, le hors-ligne du titulaire ». Cette task est le **verrou** qui doit exister **avant**
> que la task-404 fasse partager la base d'une boîte entre plusieurs personnes : sans lui, partager
> la base donnerait à un délégataire révoqué un accès durable aux données du titulaire.
>
> **Aucune reprise** : registre et bases de dev repartent vides (humain, 2026-10-28).

## Ce qui est établi

- **Verdict de compatibilité** (`Api/Mail/src/Domain/Entities/TenantDb/MailboxCompatibility.cs`) :
  une boîte active reste **sélectionnable et lisible hors ligne** (`NoPscToken`), quelle que soit la
  personne. `AuthFailing` et `Detached` la rendent non sélectionnable.
- **Refus du jeton en cours d'usage** : reconnu par `MailServerTokenRefusal.TryDescribe`
  (`ImapConnectionService`, `SmtpConnectionFactory`, `BackgroundImapService`), qui évince le jeton du
  cache — mais **rien n'est reporté au registre**. Seule la ré-authentification explicite
  (`MailboxManagementService.ReauthenticateAsync` → `MarkAuthenticationOutcomeAsync`) pose
  `AuthFailing`. Une révocation est donc invisible pour l'accès aux données (écart déjà relevé par
  l'audit sécurité E016 du 2026-09-16 : « re-validation AuthFailing jamais câblée »).
- **Redis** sert des données de la boîte (listes, contacts, métadonnées) indexées par adresse : un
  contrôle placé après le cache ne protège rien.

## Objective

Une personne ne lit ni n'écrit les données d'une boîte que si l'opérateur MSSanté lui en a ouvert
l'accès **récemment**. Un refus ou une révocation ferment l'accès, y compris aux données déjà
synchronisées. Seul le **titulaire** garde la lecture hors ligne sur sa boîte personnelle.

## Règles

1. **Verdict de l'opérateur.** Toute authentification XOAUTH2 réussie (IMAP ou SMTP) enregistre un
   verdict favorable pour la paire (personne, boîte). Tout refus du jeton reconnu en cours d'usage
   passe le rattachement en **`AuthFailing`** au registre.
2. **Fenêtre de 5 minutes**, alignée sur la révocation. Pour un **délégataire**, un **membre** ou une
   boîte **« à requalifier »**, toute requête qui touche les données de la boîte exige un verdict de
   moins de 5 minutes. Au-delà, le serveur **renouvelle** le verdict auprès de l'opérateur avant de
   servir ; un échec est un refus.
3. **Refus** : `application/problem+json` 403, code distinct selon ce que le serveur **sait** —
   accès refusé par l'opérateur, connexion PSC requise. **Aucune donnée servie**, cache Redis
   compris : le contrôle passe **avant** toute lecture.
   - *Amendement du 2026-10-29 (référentiel socle MSSanté #2, § « Cas du retrait d'une
     délégation »)* : un retrait de délégation se traduit **seulement** par un échec
     d'authentification, et l'ANS précise que le logiciel **ne peut pas en identifier la cause** ;
     c'est l'opérateur qui prévient le délégant et le délégataire par courriel. Une délégation
     retirée, un jeton refusé ou un compte verrouillé échouent de la même façon. Le code, le
     message et l'écran disent donc « accès refusé par l'opérateur de messagerie », **jamais**
     « délégation retirée » ni « accès révoqué ».
4. **Hors-ligne** (session sans jeton PSC) :
   - **titulaire** : lecture inchangée (sans envoi ni drapeaux, comme aujourd'hui) ;
   - **délégataire, membre, « à requalifier »** : refus « connexion PSC requise ».
5. **`AuthFailing` ferme tout**, titulaire compris (comportement actuel). On en sort par la
   ré-authentification.
6. **Temps réel** : le flux SSE d'une personne dont l'accès tombe est **fermé**, et la
   synchronisation de fond lancée pour elle s'arrête.
7. **Tâches de fond et consommateurs du bus** : ils travaillent pour la boîte sans rien exposer à une
   personne ; ils ne passent pas par ce verrou et restent des **actes système** (règle 14).
8. **Traces (règle 14)** : refus d'accès, passage en `AuthFailing`, renouvellement refusé — avec la
   personne qui agit, son rôle, la boîte et la cause.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : codes de refus et état « accès suspendu » — package publié, consommateurs
      .NET bumpés, types TypeScript mobile et Angular régénérés
- [ ] Unit tests du verdict d'accès : chaque rôle (titulaire, membre, délégataire, à requalifier)
      croisé avec chaque état (en ligne verdict frais, en ligne verdict périmé, hors ligne,
      `AuthFailing`)
- [ ] Test d'intégration de bout en bout : délégataire dont l'opérateur refuse le renouvellement →
      403 problem+json, **aucune donnée** dans la réponse réelle, y compris une liste déjà en cache
      Redis ; rattachement `AuthFailing` relu au registre — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : délégataire hors ligne → 403 « connexion PSC requise » ;
      titulaire hors ligne → ses messages lus dans la réponse réelle — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : refus du jeton en cours d'usage (IMAP, puis SMTP) →
      `AuthFailing` posé au registre — vu rouge (règle 1b)
- [ ] Test d'intégration : flux SSE fermé après révocation — vu rouge (règle 1b)
- [ ] Test d'intégration : traces de refus lues dans le journal réel (personne, rôle, cause) — vu
      rouge (règle 1b)
- [ ] Mobile et weda2 : écran « accès suspendu » qui dit ce que le serveur sait (refus de l'opérateur
      ou connexion PSC requise), jamais « délégation retirée » ni « accès révoqué » (règle 3), sans
      aucune donnée de la boîte, `data-testid` sur tous les éléments interactifs
- [ ] UI component tests : écran « accès suspendu » (rendu de chaque cause + action proposée) ;
      aucun libellé n'affirme un retrait de délégation
- [ ] **Banc e2e** : le banc sait **refuser une personne donnée sur une boîte donnée** (révocation
      simulée), sans affecter les autres personnes de la même boîte
- [ ] Scénario E2E-MAILBOX-005 (v1, le délégataire révoqué perd l'accès en ligne puis hors ligne ; le
      titulaire garde le sien) ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque
      client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté)
- [ ] Évènements PGSSI-S journalisés : refus d'accès, échec d'authentification opérateur,
      `AuthFailing`

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`)
- Mobile : `cd Client/Mobile && npm start` → http://localhost:4200 ; weda2 via le faux hôte e2e
- Le titulaire e2e et le délégataire e2e sont rattachés à `boite-praticien` (task-402).
- Le délégataire lit la boîte. Révocation simulée sur le banc → en moins de 5 minutes, l'écran passe
  à « Accès suspendu — accès retiré par la messagerie » ; plus aucun message ne s'affiche, même en
  revenant sur un dossier déjà ouvert.
- Le titulaire continue de lire. Couper sa session PSC → lecture hors ligne maintenue, envoi
  indisponible.
- Délégataire sans session PSC → « Connexion Pro Santé Connect requise ».
- Écran Audit de weda2 : refus et révocation tracés au nom du délégataire.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — contrôle d'accès interne, sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient n'est ajoutée ; l'accès à celles qui existent est
  restreint
- **Authentification PS** : PSC / e-CPS, eIDAS substantiel ; l'opérateur MSSanté reste juge par
  XOAUTH2. Hors-ligne réservé au titulaire
- **Habilitations** : rôle du rattachement (task-402) et verdict de l'opérateur de moins de 5 minutes
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refus d'accès, échec d'authentification, `AuthFailing` — personne, rôle, boîte,
  cause. Conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : à mettre à jour — la révocation d'une délégation coupe l'accès aux données
  déjà synchronisées

## Branches

- `api-mail` (pushed) : feat/task-403-l-acces-a-la-base-d-une-boite-est-ouvert — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-403-l-acces-a-la-base-d-une-boite-est-ouvert
- `client-mobile` (pushed) : feat/task-403-l-acces-a-la-base-d-une-boite-est-ouvert — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-403-l-acces-a-la-base-d-une-boite-est-ouvert
- `dtos-mss` (lazy) : aucune branche au /start — `/develop` la crée au premier contrat touché
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` (`feature/nova-mss-weda-integration` au /start) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-403 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 15 s | — | — | — | — |
| /develop | ok | 45 min 25 s | 7 (1 min 48 s) | 6 (16 min 33 s) | — | api-mail 5B/3T, client-mobile 1B/2T, client-angular 1B/1T |
| /sonar | ok | 30 min 23 s | 4 (1 min 13 s) | 15 (20 min 04 s) | 6 (2 min 03 s) | 3 itération(s), api-mail 4B/15T |
| /lint-angular | ok | 2 min 13 s | 1 (13 s) | 1 (22 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 24 s | — | — | — | — |
| /e2e | ok | 17 min 57 s | — | — | — | e2e ×6 (34 min 02 s) |
| /review | ok | 13 min 14 s | 2 (17 s) | 4 (9 min 03 s) | — | api-mail 1B/3T, client-mobile 1B/1T |
| **Total cycle** | | **1 h 49 min** | **14 (3 min 32 s)** | **26 (46 min 03 s)** | **6 (2 min 03 s)** | |

Autres commandes mesurées : lint ×3 (49 s), nuget-wait ×1 (14 s), restore ×1 (23 s)

## Develop log

**Run** : `forge-20261029-403-405` — `/develop` du 2026-10-29.

### Conception

- **Le verrou est dans la sélection de la boîte** (`MailboxSelectionService` → `IMailboxAccessGate`),
  c'est-à-dire dans le middleware, **avant** toute lecture et avant tout cache Redis : chaque requête
  qui touche une boîte passe par là.
- **Règle pure** : `MailboxAccessPolicy.Evaluate(role, online)` (Domain). Titulaire → ouvert, en
  ligne comme hors ligne. Délégataire, membre, « à requalifier » → verdict de l'opérateur de moins de
  5 minutes en ligne, refus « session PSC requise » hors ligne. `AuthFailing` est déjà non
  sélectionnable (compatibilité), désormais refusé avec le code `MAILBOX_ACCESS_REFUSED`.
- **Verdicts** : Redis partagé (`mailbox-access:verdict:{empreinte(sujet, adresse)}`, TTL 5 min),
  **échec fermé** (Redis injoignable = pas de verdict = renouvellement).
- **Renouvellement** : la sonde IMAP du rattachement (`ImapOperatorAccessProbe`), XOAUTH2 avec le
  jeton PSC de la session (mot de passe sur les bancs). Refus → `AuthFailing` au registre, verdict
  retiré, synchronisation de fond **lancée par cette personne** arrêtée
  (`IBackgroundSyncManager.StopSyncStartedByAsync`), traces. Opérateur injoignable → 503
  `MAILBOX_ACCESS_UNVERIFIED`, sans `AuthFailing`.
- **Pendant l'usage** : `MailServerTokenRetry` (IMAP et SMTP) enregistre chaque authentification
  acceptée comme verdict favorable, et un refus **définitif** (jeton frais refusé à son tour) comme
  `AuthFailing`. Un premier refus suivi d'une reprise réussie n'est pas un refus de l'opérateur.
- **Temps réel** : les flux SSE (`mail/events/stream`, `mail/notifications/stream`) revérifient
  l'accès toutes les `MailboxAccess:StreamRecheckInterval` (30 s) ; au premier refus, ils poussent
  `MailboxAccessSuspended` (avec le code) et se ferment.
- **Codes et écrans** : `MAILBOX_ACCESS_REFUSED` (403, « accès refusé par l'opérateur de
  messagerie »), `MAILBOX_PSC_SESSION_REQUIRED` (403), `MAILBOX_ACCESS_UNVERIFIED` (503). Aucun
  libellé ne dit « délégation retirée » ni « accès révoqué » (amendement ANS du 2026-10-29).
- **Traces (règle 14)** : `MailboxAccessRefused` (42) et `MailboxAccessSuspended` (43), avec la
  boîte (`TenantId`, `FromAddress`), le rôle, le compte et le RPPS de la personne qui agit, et la
  cause. Rétention : `HealthDataAccess` (preuve qu'une donnée de santé n'a **pas** été servie).
- **Banc e2e** : l'opérateur simulé (`BenchOperatorRefusals` + `BenchOperatorAccessProbe`,
  enregistré seulement là où le bypass de test existe — Development, Testing) refuse une personne
  donnée sur une boîte donnée ; route `POST|DELETE /api/v1/testing/operator-refusals?mailbox=`
  (404 hors bypass). Le Dovecot du banc, à mot de passe commun, ne sait pas refuser une seule
  personne d'une boîte.
- **Composition** : le verrou est enregistré dans `AddApi` (à côté du gestionnaire de
  synchronisation et du registre), pas dans `AddApplication` : les suites qui composent la couche
  application sans registre restent intactes ; `ImapServerAccess` et `SmtpConnectionFactory` le
  reçoivent en paramètre facultatif (motif de task-231).

### Commits

| Repo | Commit | Contenu |
|---|---|---|
| `dtos-mss` | `40e44e2` | codes de refus, `AuditActionType` 42/43 — **NuGet 554.0.0** (run 40867562625) |
| `api-mail` | `57a85321` | bump `HealthPlatform.Dtos.Mss` 554.0.0 + lock files |
| `api-mail` | `1962a5f7` | verrou, verdicts, sonde, SSE, banc, tests |
| `client-mobile` | `d37c55d` | écran « accès suspendu », intercepteur, flux SSE, E2E-MAILBOX-005 |
| `client-angular` | — | **code-only**, non commité (voir ci-dessous) |

### Règle 1b — comportements atteignables par un endpoint, tests d'intégration, preuves rouges

| Comportement | Test d'intégration (pile réelle) | Preuve rouge |
|---|---|---|
| Délégataire refusé au renouvellement → 403 problem+json `MAILBOX_ACCESS_REFUSED`, **aucune donnée** (liste de contacts déjà en cache), `AuthFailing` relu au registre, titulaire `Active`, plus de sonde ensuite | `MailboxAccessLockIntegrationTests.Delegate_RefusedAtRenewal_Gets403_WithNoData_EvenCached_AndIsAuthFailingInTheRegistry` | M2 (sélection sans verrou) : rouge ; M3 (refus sans suspension) : rouge |
| Renouvellement accepté → servi, verdict relu dans Redis (TTL 4-5 min), pas de seconde sonde | `…Delegate_AcceptedAtRenewal_IsServed_AndNotProbedAgainWithinTheVerdict` | M2 : rouge |
| Hors ligne : délégataire 403 `MAILBOX_PSC_SESSION_REQUIRED` ; titulaire lit sa liste | `…OfflineDelegate_Gets403PscSessionRequired_WhileTheOfflineHolder_ReadsItsList` | M2 : rouge |
| Flux SSE fermé après révocation, dernier évènement `MailboxAccessSuspended` + code | `…TheStreamOfADelegateWhoseAccessFalls_IsClosedWithTheRefusalCode` | M2 : rouge ; M4 (flux sans surveillance) : rouge |
| Refus du jeton en cours d'usage, SMTP (envoi de brouillon) puis IMAP (quota) → `AuthFailing` relu au registre PostgreSQL réel, trace `MailboxAccessSuspended` ; reprise réussie → reste `Active`, verdict relu dans Redis | `MailServerTokenRefusalEndpointIntegrationTests.SendDraft_BothTokensRefused_…`, `Quota_BothTokensRefused_…`, `SendDraft_TheFirstTokenRefused_…` | M1 (refus définitif non enregistré) : les deux tests de refus rouges |
| Traces de refus : personne (compte, RPPS), rôle, boîte, cause | assertions de `Delegate_RefusedAtRenewal_…` sur les traces émises | M3 : rouge |

Mutations (réinjectées, vues rouges, restaurées par `cp` + `touch`) :

- **M1** `MailServerTokenRetry` : `await verdicts.RecordRefusedAsync(...)` retiré → 2 rouges / 4.
- **M2** `MailboxSelectionService.GuardAsync` : verrou court-circuité (`Granted`) → 4 rouges / 4.
- **M3** `MailboxAccessGate` : `SuspendAsync` retiré sur refus → 1 rouge / 4 (le bon).
- **M4** `SseHelper.AccessWatchAsync` : surveillance désactivée → 1 rouge / 4 (le bon).

**Écart assumé, à juger par `/review`** : les traces sont lues à la frontière `IAuditService` (le
vrai service, un double qui capture), pas relues dans la table `audit_traces`. La persistance du
journal n'est pas modifiée par cette task et reste prouvée par `AuditJournalIntegrationTests`.

### Tests unitaires

- `MailboxAccessPolicyTests` (8 cas rôle × session), `MailboxAccessGateTests` (titulaire en
  ligne/hors ligne ; délégataire, membre, à requalifier × verdict frais / périmé accepté / périmé
  refusé / hors ligne ; opérateur injoignable ; jeton indisponible ; refus et acceptation en cours
  d'usage), `MailboxSelectionServiceTests` (`AuthFailing` → refus de l'opérateur sans consulter le
  verrou ; chaque refus du verrou ; boîte par défaut verrouillée aussi),
  `AuditActionTypeContractTests` (42, 43, 45 membres), `AuditRetentionPolicyTests`.
- Mobile : `MailboxAccessSuspendedPage` (6), `MssHeadersInterceptor — accès à la boîte refusé` (4).
- weda2 : `MssMailboxAccessSuspendedComponent` (6), `MailboxAccessSuspensionService` (6),
  `audit.model.spec` (42, 43).

### Scénario e2e

- `E2E-MAILBOX-005` v1 ajouté à `Api/Mail/e2e/scenarios.yml` **avant** les tests, implémenté dans
  `Client/Mobile/e2e/specs/functional.spec.ts` et `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts`.

### Validation

- `dtos-mss` : build vert, CI NuGet verte (554).
- `api-mail` : build 0 erreur ; suite complète verte — domain 204, infrastructure 697, api 1 295, application 3 807, intégration 1 036 (+16 ignorés) ; re-validation ciblée après la correction S4457 (224 + 8 verts).
- `client-mobile` : `npm run build` vert ; `npm test` 1 332 / 1 332.
- `client-angular` : `nx build weda2` vert ; `nx run-many -t test` 12 projets verts (lib MSS 1 925).

### Passe qualité (§Q)

- `api-mail` : contrôles mécaniques §Q 2b : **S4457** trouvé (`MailboxAccessGate.RecordRefusedAsync`)
  et un second que le contrôle n'a pas vu (`CheckAsync`, garde à plus de trois lignes de la
  signature) — scindés en enveloppe synchrone + `…CoreAsync` ; compteur S4457 porté à 7 dans
  `conventions/csharp.md`. Revue du diff : aucune autre simplification.
- `client-mobile` : `MailboxAccessSuspensionService` factorise la suspension entre l'intercepteur
  et les deux flux SSE (au lieu de trois copies) ; aucune autre simplification.
- `client-angular` : même factorisation (`MailboxAccessSuspensionService` de la lib).
- `dtos-mss` : hors passe (porteur de contrat).

### client-angular (code-only) — à commiter par l'humain sur TFS

Branche courante : `feature/nova-mss-weda-integration`. Fichiers de task-403 :

- `apps/weda2/src/app/core/interceptors/mss-headers.interceptor.ts`
- `libs/mss/src/core/index.ts`, `libs/mss/src/index.ts`
- `libs/mss/src/core/models/audit.model.ts`, `audit.model.spec.ts`, `mailbox.model.ts`
- `libs/mss/src/core/services/mail-events-stream.service.ts`, `notification-stream.service.ts`
- `libs/mss/src/core/services/mailbox-access-suspension.service.ts` (+ `.spec.ts`)
- `libs/mss/src/core/stores/mailbox-session.store.ts`
- `libs/mss/src/features/mailbox-access-suspended/` (composant, gabarit, style, spec)
- `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts` — **ces deux fichiers
  portaient déjà les modifications non commitées de task-377** (`pendingBiologyTotal`) : les deux
  changements s'y cumulent.

## Sonar log

- Serveur SonarQube 9.9.8 (`sonar.login`), déjà démarré. Branche `feat/task-403-l-acces-a-la-base-d-une-boite-est-ouvert`.
- Itération 1 (`1962a5f7`) : QG OK, new_coverage 95,0 % ; **2 issues** sur le code neuf (`csharpsquid:S927`,
  `MailboxAccessGate`, noms de paramètres différents de l'interface) ; fichiers de la task mal couverts
  (sonde de l'opérateur, magasin des verdicts, banc, arrêt ciblé de la synchronisation, surveillance SSE).
- Corrections : `22ce37df` (S927, paramètres de l'interface renommés), `b6e16a17` (tests : sonde,
  magasin Redis en échec fermé, surveillance des flux, arrêt de la synchronisation par personne, opérateur
  simulé du banc), `e7f3bcbf` (flux de notifications fermé sur révocation — test d'intégration, vu rouge
  par mutation M5 : surveillance retirée de `NotificationsController`).
- Itération 2 : QG OK, 0 issue, new_coverage 97,0 % ; une ligne restante (`NotificationsController`).
- Itération 3 (`e7f3bcbf`) : **QG OK, 0 issue, 0 hotspot, new_coverage 97,1 %** ; tous les fichiers de la
  task à 100 % de lignes neuves couvertes (`OperatorVerdicts` 92 %, `MailboxSelectionService` 96 % en
  conditions). Tests : 204 + 3 830 + 697 + 1 302 + 1 037 verts (16 ignorés).
- Phase 2 (legacy) : sans objet — 0 bug, 0 vulnérabilité, 0 code smell.
- Conventions : **S927** ajoutée à `conventions/csharp.md` (Occurrences : 1).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,8 % | 97,1 % | +0,3 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 pt |
| Duplication | 0,4 % | 0,4 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode : chaîné. Comme task-377 : `npx eslint -f json` sur les 16 fichiers `.ts`/`.html` de la task
  (suite e2e comprise), messages attribués aux lignes de la task par `git diff -U0` (fichiers créés
  comptés en entier). Base `origin/next` rafraîchie.
- Baseline : **9 erreurs**, toutes `prettier/prettier` et toutes sur des lignes de la task
  (intercepteur weda2, `audit.model.ts`, spec et support e2e).
- Itération 1 : `eslint --fix` sur ces fichiers → **0 erreur**. Avertissements : aucun sur une ligne de
  la task (seuls les avis « fichier ignoré » des specs et du gabarit HTML) ; les 22 autres
  (`jsdoc/require-example` vides, `max-lines`) sont antérieurs.
- Prettier `--write` sur les seuls fichiers créés par la task (une spec reformatée).
- Build / tests : `nx build weda2` vert ; `nx test mss-lib` 1 351 verts.
- Conventions : aucune règle corrigée à la main (auto-fixer seul), `conventions/angular.md` inchangé.
- Code-only : aucune opération git sur `client-angular` (seul `git fetch origin next`).

## Lint mobile log

- Mode : chaîné, branche `feat/task-403-l-acces-a-la-base-d-une-boite-est-ouvert` (`d37c55d`), arbre propre.
- Baseline = final (`ng lint`) : **0 erreur, 0 warning** (« All files pass linting »).
- Itérations : 0. Build et tests verts depuis `/develop` (`npm run build`, `npm test` 1 332/1 332) ;
  rien modifié par cette étape, aucun commit.
- Conventions : aucune règle corrigée à la main, `conventions/angular.md` inchangé.

## E2E log

| Voie | Jouée | Résultat |
|---|---|---|
| mobile (`npm run e2e:headless`) | oui — `api-mail` et `client-mobile` touchés | 51 verts, 0 flaky, 0 rouge |
| Angular (`npm run e2e:mss`) | oui — `api-mail` et `client-angular` touchés | 61 verts, 0 flaky, 0 rouge |

- Nouveau scénario **E2E-MAILBOX-005** v1 vert dans les deux clients (révocation simulée par l'opérateur
  du banc, écran « Accès suspendu », refus relus côté serveur en ligne et hors ligne, titulaire servi).
- Démontage vérifié : ports du banc libres, aucun conteneur e2e résiduel.
- Écrans modifiés sans spec e2e : aucun (l'écran « accès suspendu » est couvert par E2E-MAILBOX-005).

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
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
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
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-MAILBOX-003 | 1 | headless | Rattacher ses boîtes depuis « Mes boîtes » — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/53 — `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/323 — `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/113 — `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Branche
  `feature/nova-mss-weda-integration`. Fichiers modifiés par task-403 :
  - `apps/weda2/src/app/core/interceptors/mss-headers.interceptor.ts`
  - `libs/mss/src/core/index.ts`, `libs/mss/src/index.ts`
  - `libs/mss/src/core/models/audit.model.ts`, `audit.model.spec.ts`, `mailbox.model.ts`
  - `libs/mss/src/core/services/mail-events-stream.service.ts`, `notification-stream.service.ts`
  - `libs/mss/src/core/services/mailbox-access-suspension.service.ts` (+ `.spec.ts`) — nouveaux
  - `libs/mss/src/core/stores/mailbox-session.store.ts`
  - `libs/mss/src/features/mailbox-access-suspended/` — nouveau (composant, gabarit, style, spec)
  - `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts` (cumulent les
    modifications non commitées de task-377)
- Ordre de merge : `dtos-mss` (#53) → `api-mail` (#323) → `client-mobile` (#113).

## Code Review Summary

**Verdict : APPROVED** — 1 blocage au premier passage, corrigé ; 4 suggestions non bloquantes.

- **Premier passage : CHANGES REQUESTED** — la DoD exige les traces de refus « lues dans le journal
  réel » ; le test les lisait à la frontière `IAuditService`. Corrigé (`8ee621a6`) : la suite
  d'intégration compose le vrai `AuditService`, son canal, `AuditBackgroundService` et
  `PostgresAuditSink`, et relit `audit_traces` avec `PostgresAuditReader` ; vu rouge par mutation (M6).

### api-mail
- `MailboxAccessPolicy` (Domain) — ✅ règle pure, titulaire seul exempté, hors-ligne refusé aux autres.
- `MailboxAccessGate` — ✅ verrou avant toute lecture ; refus → `AuthFailing`, verdict retiré,
  synchronisation lancée par la personne arrêtée, traces (personne, rôle, boîte, cause).
- `MailboxSelectionService` — ✅ le verrou s'applique à la boîte demandée **et** à la boîte par défaut ;
  `AuthFailing` devient « refusé par l'opérateur ».
- `UserContextEnricherMiddleware` — ✅ trois codes problem+json ; les routes `[MailboxNotRequired]`
  restent servies (c'est depuis elles qu'on ré-authentifie ou détache).
- `MailServerTokenRetry` — ✅ seul un refus **définitif** (jeton frais refusé) suspend ; un jeton périmé
  repris avec succès renouvelle le verdict.
- `RedisOperatorVerdictStore` — ✅ clé en empreinte, échec fermé.
- `SseHelper`, `MailEventsController`, `NotificationsController` — ✅ revérification périodique, dernier
  évènement `MailboxAccessSuspended`, fermeture.
- `BenchOperatorController` / `BenchOperatorRefusals` — ✅ enregistrés seulement là où le bypass de
  test existe (Development, Testing), 404 sinon et sans bypass.
- ⚠️ Suggestion : un renouvellement n'est pas mutualisé ; N requêtes simultanées d'une même personne
  à l'expiration du verdict lancent N sondes IMAP.
- ⚠️ Suggestion : une route de gestion (`[MailboxNotRequired]`) qui porte `Client-Email` renouvelle aussi
  le verdict, donc peut sonder l'opérateur sans servir de données.
- ⚠️ Suggestion : chaque requête refusée écrit une trace `MailboxAccessRefused` ; un délégataire hors
  ligne qui insiste en écrit une par requête.
- ⚠️ Suggestion : Redis injoignable = sonde à chaque requête d'un non-titulaire (échec fermé assumé).

### client-mobile
- `MailboxAccessSuspensionService`, intercepteur, flux SSE — ✅ purge des données de la boîte, écran
  « accès suspendu », flux non rouverts.
- Écran « accès suspendu » — ✅ ce que le serveur sait, jamais « délégation retirée » ; `data-testid`.

### client-angular (code-only)
- Même conception (service de la lib MSS, intercepteur weda2, composant) — ✅.

### Règle 1b — comportement → test d'intégration → preuve rouge

| Comportement | Test | Preuve rouge |
|---|---|---|
| Refus au renouvellement : 403, aucune donnée (cache compris), `AuthFailing` relu, traces relues dans `audit_traces` | `MailboxAccessLockIntegrationTests.Delegate_RefusedAtRenewal_…` | M2, M3, M6 |
| Renouvellement accepté : servi, verdict Redis 5 min | `…Delegate_AcceptedAtRenewal_…` | M2 |
| Hors ligne : délégataire 403 PSC requise, titulaire servi | `…OfflineDelegate_…` | M2 |
| Flux SSE (mail et notifications) fermés sur révocation | `…TheStreamOfADelegateWhoseAccessFalls_…` ×2 | M2, M4, M5 |
| Refus en cours d'usage SMTP puis IMAP → `AuthFailing` au registre réel | `MailServerTokenRefusalEndpointIntegrationTests` | M1 |
