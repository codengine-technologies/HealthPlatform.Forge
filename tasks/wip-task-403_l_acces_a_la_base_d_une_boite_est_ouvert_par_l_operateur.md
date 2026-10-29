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
| **Total cycle** | | **1 h 18 min** | **12 (3 min 15 s)** | **22 (37 min 00 s)** | **6 (2 min 03 s)** | |

Autres commandes mesurées : lint ×2 (35 s), nuget-wait ×1 (14 s), restore ×1 (23 s)

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
