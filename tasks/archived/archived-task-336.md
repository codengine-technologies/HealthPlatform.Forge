# todo-task-336.md — Après une bascule de boîte, le praticien reçoit en temps réel les messages de la boîte qu'il regarde, et d'aucune autre

**Repos**: api-mail, client-blazor, client-mobile
**Dependencies**: — (aucune)
**Epic**: E016
**Single frontend**: false
**Priorité**: **2** — un praticien à plusieurs boîtes qui bascule sur la boîte B reçoit les nouveaux mails, les enrichissements et la progression de synchronisation **de la boîte A**, et rien de B : les indicateurs « en cours » ne se terminent jamais et les tags d'urgence de B n'apparaissent pas.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-21**, trouvé par deux zones indépendamment).
> **Découpage validé par l'humain le 2026-09-27** : l'ancienne task-336 (« plusieurs serveurs, un seul
> comportement ») est scindée en trois — **task-336** (ce fichier : flux SSE et boîte suivie), **task-343**
> (backplane SSE et conversations IA partagés entre réplicas), **task-344** (promotion unique d'un mail).
> Chacune est testable et mergeable seule.

## Ce qui est établi (develop @ `14d58398`)

- `EventSource` (navigateur) **ne peut pas poser d'en-tête HTTP** : le flux SSE n'envoie jamais `Client-Email`.
  Le jeton passe déjà par la query sur ces routes (`token=***` dans les logs de requête).
- `src/Api/Middleware/UserContextEnricherMiddleware.cs:596-605, 722-730` : la boîte n'est lue **que** dans l'en-tête
  `Client-Email` ; sans en-tête, le middleware sélectionne la boîte **par défaut** du compte et remplit
  `UserContextInfo.Email`.
- `src/Api/Controllers/V1/MailEventsController.cs:71, 93-95` : le contrôleur ne lit `?mailbox=` que si
  `_userContext.Email` est vide — ce qui n'arrive jamais (la route exige une boîte). Ce **repli brut, non validé
  contre le registre**, deviendrait exploitable le jour où il serait atteignable (route marquée
  `[MailboxNotRequired]`, ou correctif mal placé dans le contrôleur).
- **Aucun client n'envoie `?mailbox=`** : mobile `mail-events-stream.service.ts:66-69`, Blazor `MailSseService.cs:162-176`.
- Le commentaire de `MailEventsControllerTests.cs:90` (« le middleware aurait déjà répondu 403 ») est faux.

## Objective

Que le flux temps réel d'un praticien suive **la boîte qu'il affiche**, validée contre le registre comme toute
autre requête, et se réaligne dès qu'il change de boîte.

### Périmètre

1. **Middleware** : pour les routes SSE **uniquement** (`MailEventsController`, `NotificationsController`), quand
   l'en-tête `Client-Email` est absent, lire `?mailbox=` et le soumettre **à la même validation** que l'en-tête
   (compte × adresse au registre, compatibilité de la boîte). Adresse non rattachée ou non sélectionnable →
   403 `ProblemDetails` (même refus que l'en-tête). Sans `?mailbox=` ni en-tête : comportement actuel (boîte par défaut).
2. **Contrôleur** : suppression du repli brut sur le paramètre `mailbox` (`MailEventsController.cs:93-95`) ; le
   contrôleur ne lit plus que `UserContextInfo.Email`, déjà validé.
3. **Clients** : `client-mobile` et `client-blazor` ouvrent le flux avec `?mailbox=` de la boîte **affichée**, et
   **ferment puis rouvrent** le flux à chaque bascule de boîte. Aucune autre évolution du flux (format des
   événements inchangé).
4. Correction du commentaire erroné de `MailEventsControllerTests.cs:90`.

### Hors périmètre

- La diffusion des événements entre réplicas (**task-343**) : cette US garantit la **bonne boîte**, task-343
  garantira que l'événement atteint le praticien **quel que soit le réplica** qui l'émet.
- `client-angular` : non listé — l'humain vérifie son propre flux SSE (code-only).

## Definition of Done

- [ ] Build passes (0 errors) sur les 3 repos ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (log du run rouge dans le task file) : flux SSE ouvert **sans en-tête** avec
      `?mailbox=B` (B rattachée au compte) → sur le code actuel abonné à la boîte **par défaut A** ; après correctif abonné à **B**
- [ ] Test : `?mailbox=` d'une boîte **non rattachée** au compte → 403 `application/problem+json`, aucun abonnement
- [ ] Test : `?mailbox=` d'une boîte rattachée mais non sélectionnable (`Detached`, `AuthFailing`) → même refus que l'en-tête
- [ ] Test : en-tête `Client-Email` présent → il prime sur `?mailbox=` (comportement actuel inchangé)
- [ ] Test : `?mailbox=` sur une route **non** SSE → ignoré (aucun élargissement de la sélection de boîte)
- [ ] Test d'intégration endpoint (règle 1b) : `GET` du flux SSE avec `?mailbox=` validé de bout en bout (DI, registre)
- [ ] `client-mobile` : spec Jasmine — l'URL du flux porte `?mailbox=` de la boîte affichée ; à la bascule, le flux est fermé puis rouvert avec la nouvelle boîte
- [ ] `client-blazor` : test bUnit / service — même comportement
- [ ] `data-testid` et libellés (FR mobile / Localizer Blazor) sur tout élément ajouté (a priori aucun élément visuel)
- [ ] Aucune adresse ni jeton ajouté dans les logs

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost` ; mobile : `cd Client/Mobile && npm start` ; Blazor en parallèle.
2. Praticien de test disposant de **deux boîtes** A (par défaut) et B.
3. Sur mobile, basculer sur B, puis envoyer un mail de test **vers B** depuis une autre boîte → il apparaît en temps réel dans B. **Avant** : rien n'apparaît, et un mail envoyé vers A déclenchait une notification alors que B est affichée.
4. Rebasculer sur A, envoyer un mail vers A → il apparaît en temps réel ; aucun événement de B ne s'affiche.
5. Même scénario dans Blazor.
6. `curl -N "https://localhost:{port}/api/v1/mail/events/stream?folder=INBOX&mailbox=adresse-non-rattachee@…&token={jeton}"` → 403 `ProblemDetails`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité du multi-boîtes (E016) existant
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée (jeton en query sur les routes SSE, comme aujourd'hui)
- **Habilitations** : **au cœur** — la boîte suivie par le flux est validée contre le registre (compte × adresse), jamais crue telle quelle ; le repli non validé est supprimé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refus d'ouverture de flux sur une boîte non rattachée tracé comme les autres refus de sélection de boîte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — supprime une diffusion d'événements vers la mauvaise boîte d'un même praticien

## Branches
- `api-mail` (pushed) : fix/task-336-sse-follows-selected-mailbox — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-336-sse-follows-selected-mailbox
- `client-blazor` (pushed) : fix/task-336-sse-follows-selected-mailbox — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-336-sse-follows-selected-mailbox
- `client-mobile` (pushed) : fix/task-336-sse-follows-selected-mailbox — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-336-sse-follows-selected-mailbox

## Develop log

**Conception retenue** : marqueur d'action nominatif `[MailboxFromQuery]` (`src/Api/Middleware/MailboxFromQueryAttribute.cs`),
posé sur les deux flux SSE (`MailEventsController.Stream`, `NotificationsController.Stream`). Sur ces actions seulement,
`UserContextEnricherMiddleware` lit `?mailbox=` quand `Client-Email` est absent et le soumet à **la même**
`IMailboxSelectionService.SelectAsync` que l'en-tête (registre compte × adresse, compatibilité) : l'en-tête prime,
une boîte non rattachée est refusée à l'identique, les routes non marquées ignorent le paramètre. Le contrôleur
ne relit plus jamais le paramètre brut — le repli `mailbox?.Trim()` qui contournait la validation est supprimé
(et son test de couverture `Stream_WithoutContextMailbox_FallsBackToTheTrimmedMailboxParameter` avec lui).

### Tests rouges d'abord

- **api-mail** — `UserContextEnricherMiddlewareTests` (5 tests task-336) : `Échoué! - échec : 2, réussite : 15` —
  `OnAMailboxFromQueryRoute_TheQueryMailboxIsTheOneSubmittedToSelection` (SelectAsync reçu avec `null` au lieu de la
  boîte de `?mailbox=` : le flux ouvert sans en-tête sur B était abonné à la boîte par défaut) et
  `BothSseStreams_AreMarkedMailboxFromQuery`. Verts après correctif.
- **client-mobile** — specs `mail-events-stream` / `notification-stream` : `TOTAL: 4 FAILED, 9 SUCCESS` (URL sans
  `mailbox=` ; à la bascule, `Expected 1 to be 2` — aucun flux rouvert). Verts après correctif (13/13).
- **client-blazor** — `MailSseServiceMailboxTests` : correctif neutralisé → `Échoué! - échec : 2, réussite : 1`
  (`Assert.Contains() Failure: Sub-string not found` sur `mailbox=` ; `Ouverture de flux n°2 jamais reçue (reçues : 1)`
  à la bascule). Verts après correctif (3/3).

### Livré

| Repo | Commit | Contenu |
|---|---|---|
| api-mail | `64e36465` | `[MailboxFromQuery]`, lecture validée de `?mailbox=` dans le middleware, suppression du repli brut du contrôleur, 5 tests middleware + 1 test contrôleur (`Stream_WithoutAResolvedMailbox_IgnoresTheRawQueryMailbox`) |
| client-mobile | `477830b` | `MailEventsStreamService` et `NotificationStreamService` : `&mailbox=` de `MailboxSessionService.currentEmail()`, `effect` qui ferme/rouvre le flux à la bascule ; 4 specs |
| client-blazor | `7efb2a4` | `MailSseService` : `mailbox=` de `IMailboxSessionService.Current` (reconstruit à chaque reconnexion), réouverture sur `OnChanged` quand la boîte change ; 3 tests |

### Validation

- api-mail : build 0 erreur ; `mss.mail.api.tests` 1010/1010, `application` 3186/3186, `domain` 190/190, `infrastructure` 665/665.
  Premier run complet de la solution **figé** (testhosts inactifs 40 min, sans sortie) — tué, relancé projet par projet avec `--blame-hang-timeout`.
  `mss.mail.integration.tests` : 603/620 (16 ignorés), 1 rouge `PgBouncerTransactionPoolingTests.ConcurrentClients_AreMultiplexed_OntoBoundedPostgresBackends` — **vert rejoué seul (7/7)**, sensible à la charge, sans rapport avec le SSE.
- client-mobile : build OK (avertissements de budget SCSS / NG8107 pré-existants) ; 946/946.
- client-blazor : build 0 erreur ; 347/347 (2 ignorés pré-existants).
- Passe qualité §Q : diffs courts et dans les idiomes existants (helper `mailboxQuery` partagé côté mobile, abonnement
  `OnChanged` désabonné au `DisposeAsync` côté Blazor) — aucun cleanup appliqué, pas de re-validation.
- Aucun élément visuel ajouté (DOD `data-testid` / libellés : sans objet).

## Sonar log

**1 analyse, 0 correction** — aucun finding sur les fichiers touchés (`MailboxFromQueryAttribute.cs`,
`UserContextEnricherMiddleware.cs`, `MailEventsController.cs`, `NotificationsController.cs` et leurs tests).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | = (pré-existant — new-code period large, cf. mémoire) |
| New coverage | 98,6 % | 92,6 % | −6,0 pt ⚠️ artefact de mesure (voir ci-dessous) |
| New bugs / vulnérabilités / smells | 2 / 0 / 89 | 2 / 0 / 89 | = |
| Coverage projet | 98,1 % | 91,6 % | −6,5 pt ⚠️ même artefact |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | C / A / A | C / A / A | = |

**Baisse de couverture = trou de mesure, pas une régression.** La passe de couverture de
`mss.mail.integration.tests` s'est figée (testhost inactif 26 min, conteneur Dovecot Testcontainers démarré) et a été
tuée : l'analyse n'a reçu que la couverture des quatre projets unitaires. Rejouée à l'identique (Release + couverture +
`--blame-hang-timeout`) juste après : **604/620 verts en 2 min 8 s**, aucun blocage. Même gel intermittent observé au
premier run complet de `/develop` (conteneur GreenMail) — lié au démarrage de conteneurs sous charge Docker, non à la task.

## Lint log

Skipped — `client-angular` non listé dans `**Repos**:`, aucun code Angular touché.

## Lint mobile log

Baseline `ng lint` : **All files pass linting** — 0 erreur, 0 itération, aucun commit. Build + tests déjà verts à `/develop` (946/946).

## Visual verify log

Skipped — aucun écran `client-mobile` touché (seuls `mail-events-stream.service.ts` et `notification-stream.service.ts` changent, sans rendu), pas de `## Stitch design log`.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/257 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/85 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/80 — label `awaiting-human-merge`

À merger **ensemble** (règle 11) : le backend seul n'a pas d'effet (aucun client n'envoie `?mailbox=`), les clients
seuls non plus (le paramètre serait ignoré).

## Code Review Summary

**APPROVED** — 3 repos, 0 bloquant, 1 suggestion.

- api-mail — ✅ une seule voie de validation (la query passe par `SelectAsync`, jamais relue par le contrôleur) ;
  exemption nominative par attribut, sur le modèle de `[MailboxNotRequired]` ; `?mailbox=a&mailbox=b` → `"a,b"`,
  refusé par la sélection ; repli brut du contrôleur supprimé.
- client-mobile — ✅ `effect` dans un service `root` (contexte d'injection) ; l'anti double-connexion par URL absorbe
  les déclenchements sans changement de boîte.
- client-blazor — ✅ URL reconstruite à chaque reconnexion, désabonnement au `DisposeAsync`.
  ⚠️ Suggestion : `RestartStreamAsync` peut être appelé en concurrence (bascule + `JoinFolderAsync`) et laisser une
  boucle de lecture orpheline — schéma **pré-existant** du service (déjà vrai entre `JoinFolderAsync` et
  `JoinUserGroupAsync`), non aggravé ; candidat à un verrou `SemaphoreSlim` dans une task dédiée.

**Incident de revue corrigé** : le test Blazor `MailSseServiceMailboxTests.cs` avait été omis du commit `7efb2a4`
(chemin saisi `Tests/`, le dépôt suit `tests/` — `git add` l'a ignoré sans erreur). Rattrapé par un commit dédié avant
ouverture de la PR.

**Revalidation post-merge develop** (api-mail +1 commit, task-335) : build 0 erreur ; domain 190, application 3214,
infrastructure 665, api 1010, integration 605/621 (16 ignorés) ; Blazor 347/347 ; mobile build OK, 946/946.

## Timings

*(généré par `tools/timing/report.sh --task task-336 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 40 s | — | — | — | — |
| /develop | ok | 53 min 09 s | 5 (1 min 52 s) | 6 (46 min 01 s) | — | api-mail 2B/3T, client-mobile 1B/2T, client-blazor 2B/1T |
| /sonar | ok | 57 min 38 s | 1 (44 s) | 5 (29 min 26 s) | 3 (2 min 04 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 1.7 s | — | — | — | client-angular absent de Repos |
| /lint-mobile | ok | 50 s | — | — | — | 0 erreur au baseline |
| /verify-visual | skipped | 2.3 s | — | — | — | aucun écran touché (services SSE uniquement) |
| /review | ok | 7 min 02 s | 3 (1 min 28 s) | 11 (4 min 28 s) | — | api-mail 1B/9T, client-blazor 1B/1T, client-mobile 1B/1T |
| /tech-writer | ok | 1 min 29 s | — | — | — | — |
| **Total cycle** | | **2 h 00 min** | **9 (4 min 06 s)** | **22 (1 h 19 min)** | **3 (2 min 04 s)** | |

Autres commandes mesurées : lint ×1 (38 s)

## Merged

Merged le 2026-09-28 par `/merge task-336 --i-tested` (HAG attesté par l'humain). Squash, ordre topologique api-mail → client-blazor → client-mobile.

| Repo | PR | Squash commit | CI `develop` |
|---|---|---|---|
| `api-mail` | [#257](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/257) | `cea97189cac629849c31fa926d8432c2d416628a` | ✓ [36409548685](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/36409548685) |
| `client-blazor` | [#85](https://github.com/codengine-technologies/HealthPlatform.Client/pull/85) | `086cc816cc9cdcd2f73554d3226165ab434d5bad` | ✓ [36410929596](https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/36410929596) |
| `client-mobile` | [#80](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/80) | `60339cf554d412fe3f808aeb0acbdac69ed4c800` | ✓ [36410952249](https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/36410952249) |

- Label `awaiting-human-merge` retiré des trois PRs.
- Branche `fix/task-336-sse-follows-selected-mailbox` supprimée (distante + locale) sur les trois repos ; clones revenus sur `develop`.
- Staging : aucune branche `forge/staging-task-*` (task hors run `/forge`).
- Incident : `git pull` bloqué sur `git credential-manager get` (invite GUI invisible) — contourné via `credential.helper='!gh auth git-credential'` + `GIT_TERMINAL_PROMPT=0`.
