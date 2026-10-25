# todo-task-378.md — À l'entrée et dans la gestion des messageries, une panne est dite comme une panne, et chaque action dit si elle a réussi

**Repos**: client-angular, client-mobile, api-mail
**Dependencies**: task-374 (cycle de vie de la session de boîte)
**Epic**: E016
**Single frontend**: false — le mobile a les mêmes défauts d'entrée et de ré-authentification (revue du 2026-10-24, décision humaine)
**Priorité**: **2** — une panne passagère envoie un médecin qui a sa carte vers « reconnectez-vous avec PSC », ou vers un rattachement voué à l'échec ; une boîte en échec d'authentification reste bloquée sans issue indiquée.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-28, ANG-29, ANG-76**).

## Ce qui est établi

> **Revue du 2026-10-24** (avant `/start`) : les trois défauts sont toujours présents sur la branche
> `feature/nova-mss-weda-integration` de weda2. task-374 est mergée et archivée. Les références de
> lignes et deux mécanismes ont été corrigés ci-dessous.

- **ANG-28** — `mailbox-session.store.ts:206-210` (`initialize()`) puis `decide()` (~l. 454) : tout échec du chargement des boîtes vaut « zéro boîte » ; injoignable → écran « PSC requis » ; liste en échec mais statut en ligne → onboarding (en embarqué, rattachement d'une boîte déjà rattachée, 409). ~~Cas Probable : après détachement, 409 `SESSION_MAILBOX_MISMATCH` sur `initialize()` sans `Client-Session-Id`.~~ **Caduc depuis task-365** (revue du 2026-10-24) : quand le cookie `proxy_session_id` est présent, ce qui est le cas de weda2 derrière le proxy, la clé de session en dérive et l'en-tête `Client-Session-Id` est ignoré (`UserContextEnricherMiddleware.cs:763-767`). La liaison se fait alors boîte par boîte (`SessionMailboxGuard.cs:79`, `PerMailbox`), si bien qu'aucun 409 de non-concordance n'est possible. Ce 409 ne subsiste que sans proxy (en-tête, puis `sid`, liaison `SingleMailbox`). Ce chemin n'est pas celui du médecin et sort du périmètre.
- **ANG-29** — « Ré-essayer l'authentification » (`mss-mailbox-management.component.ts:244-246`) ne fait rien : une boîte `AuthFailing` n'est pas sélectionnable et ne repasse `Active` que sur un login XOAUTH2 réussi. **Aucune route de ré-authentification n'existe côté api-mail** (`AccountController` n'expose que GET/POST/DELETE `mailboxes` et PUT `default`), et un POST de rattachement sur une boîte `AuthFailing` répond 409 `AlreadyAttached` sans la sonder. La route est donc **à créer**.
- **ANG-76** — détacher, rattacher à nouveau, définir par défaut ignorent l'échec (un détachement échoué de la dernière boîte déconnecte) ; « déjà rattachée » et « session PSC requise » s'affichent « identifiants refusés », par deux mécanismes différents :
  - **409 « déjà rattachée »** : `ProblemDetailsSetup` estampille `instance` (« POST /api/v1/… ») sur **toute** réponse d'erreur. `toError()` (`mailbox-accounts.service.ts:200`) le lit comme un code avant d'atteindre la branche `detail` des 409, qui n'est donc jamais prise.
  - **401 `PSC_SESSION_REQUIRED`** : le code arrive bien dans `code`, mais `MSS_PROBE_ERROR_LABELS` n'a pas d'entrée pour lui. `describeError()` retombe alors sur `AUTH_FAILED`.

- **client-mobile, même défaut** : `mailbox-session.service.ts:161-165` fait la même chose qu'Angular (un échec vaut « zéro boîte »), et `mailbox-management.page.ts:160` fait de « Ré-essayer l'authentification » un simple `switchTo()`. Les actions de gestion (`setDefault`, détachement) sont à vérifier de la même façon pendant `/develop`.

## Objective

Qu'à l'entrée, le médecin soit orienté vers le bon écran — et vers un écran de panne avec réessai quand le service est indisponible — et que chaque action sur ses messageries (rattacher, détacher, définir par défaut, ré-essayer l'authentification) dise si elle a réussi et, sinon, pourquoi.

### Périmètre

1. **Entrée** : `initialize()` distingue « erreur » de « zéro boîte » ; écran de panne avec réessai. Comme toute erreur, un 409 au chargement mène à cet écran, jamais à « zéro boîte ». Pas de `Client-Session-Id` à tirer dès l'entrée : derrière le proxy, la clé de session vient de `proxy_session_id` (task-365).
2. **« Ré-essayer l'authentification »** : une nouvelle route api-mail qui fait une vraie sonde (elle réutilise la sonde XOAUTH2 du rattachement) qui fait repasser la boîte `Active` en cas de succès, et affiche l'erreur sinon.
3. **Gestion des comptes** : chaque action teste son résultat, affiche le motif, et ne poursuit (bascule, déconnexion) que sur succès.
4. **Messages d'erreur du rattachement** : `instance` lu comme un code seulement s'il en a la forme ; `detail` prioritaire sur les 409 ; libellé pour `PSC_SESSION_REQUIRED`.

## Definition of Done

- [ ] Build et tests verts : weda2, client-mobile, api-mail
- [ ] Test d'intégration de bout en bout pour la sonde de ré-authentification d'une boîte `AuthFailing` (route ajoutée — aucune n'existe) : sur login réussi la boîte repasse `Active` dans la réponse ; sur refus elle reste `AuthFailing` avec un code lisible, vu rouge (règle 1b)
- [ ] Tests unitaires et de store rouges d'abord, sur weda2 **et** sur client-mobile :
  - [ ] chargement des boîtes en 503 : écran de panne, pas « PSC requis » ni onboarding
  - [ ] DELETE de détachement en 500 : pas de déconnexion, message affiché, la boîte reste listée
  - [ ] 409 « déjà rattachée » : le `detail` du serveur s'affiche ; 401 `PSC_SESSION_REQUIRED` : libellé dédié
- [ ] Scénario E2E-MAILBOX-002 « api-mail indisponible à l'entrée : écran de panne puis réessai » ajouté au catalogue, `requis` sur angular **et** mobile, et implémenté dans les deux clients
- [ ] Aucune adresse ni identifiant de session ajouté aux journaux

## Manual Test Plan

Chaque étape se joue sur weda2 **puis** sur l'app mobile (`cd Client/Mobile && npm start`, puis http://localhost:8100).

1. Arrêter api-mail, ouvrir le client → écran « service indisponible » avec « Réessayer » ; relancer api-mail, réessayer → la boîte s'ouvre.
2. Boîte en échec d'authentification (mot de passe ou jeton refusé côté banc) : rétablir l'accès, cliquer « Ré-essayer l'authentification » → la boîte redevient utilisable.
3. Détacher sa dernière boîte avec api-mail en erreur → message d'erreur, pas de déconnexion.
4. Rattacher une boîte déjà rattachée → « Cette messagerie est déjà rattachée ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS ; l'écran « PSC requis » n'est plus montré à tort ; la sonde de ré-authentification passe par XOAUTH2 avec le jeton PSC de la session
- **Habilitations** : rattachement validé par l'opérateur MSSanté (inchangé, task-308)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : rattachement, détachement et ré-authentification tracés comme aujourd'hui (réussite et échec)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — aucune DSCP manipulée
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-378-pannes-entree-messageries — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-378-pannes-entree-messageries
- `client-mobile` (pushed) : fix/task-378-pannes-entree-messageries — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-378-pannes-entree-messageries
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Stitch design log

- Projet Stitch `client-mobile` (`10088502293310567548`), design system `assets/9aca84edc31f42798fd98bd24e151040`.
- `mailbox-unavailable` (écran neuf) : aucun écran à ce nom, donc **création** lancée une fois (`generate_screen_from_text`, MOBILE). Timeout MCP attendu. **Non matérialisé** après 3 lectures `get_project` espacées (aucune nouvelle instance). Pas de nouvelle génération (anti-doublon). Page Ionic codée sans référence, sur le gabarit de `mailbox-psc-required` (même en-tête, `h2` + texte + `ion-button expand="block"`).
  - **À faire par l'humain**, si l'écran n'apparaît pas d'ici la revue : dans le projet `client-mobile`, générer avec le prompt « Screen title: mailbox-unavailable. Mobile Ionic screen of a French secure medical messaging app (MSSanté), shown at app entry when the server cannot load the practitioner's mailboxes. Top toolbar titled "Messagerie MSSanté". Centered content: a muted cloud-off icon, heading "Service de messagerie momentanément indisponible", body text "Vos messageries n'ont pas pu être chargées. Rien n'a été modifié sur votre compte : réessayez dans un instant." Below, an optional small status line in muted text "Le service est toujours indisponible." Primary full-width button "Réessayer" with a refresh icon. No login prompt, no form, sober clinical style, Public Sans. »
- `mailbox-management` (écran existant) : seul un bandeau d'erreur ou de confirmation (`ion-note`) est ajouté. Pas de refonte, pas de nouvelle référence.

## Develop log

- Repos touched : api-mail, client-mobile, client-angular (code-only)
- DTOs published : no DTO change (la route rend le `MailboxDto` existant ; la trace d'audit `MailServerAuthRetry` est réutilisée, aucun membre d'enum ajouté)
- Interop published : no interop change
- Commits :
  - api-mail : `44cd9a4e` feat(mailboxes): route de ré-authentification d'une messagerie ; `3c50cf7c` refactor(mailboxes): simplify pass (/simplify)
  - client-mobile : `969ef90` fix(mobile): une panne à l'entrée est dite comme une panne, chaque action de messagerie dit si elle a réussi
  - client-angular : **non commité** sur `feature/nova-mss-weda-integration` (code-only). 17 fichiers modifiés, plus `libs/mss/src/core/models/mss-probe.model.spec.ts` et `libs/mss/src/features/mailbox-unavailable/` (4 fichiers) créés. **À commiter sur TFS avant le merge de la PR api-mail** : `front/e2e/mss-e2e/specs/functional.e2e.ts` porte le test du scénario requis E2E-MAILBOX-002 (convention `test-angular-non-commite`).
- Backend :
  - `POST /api/v1/account/mailboxes/{id}/reauthenticate` (`[MailboxNotRequired]`, limiteur `Sensitive` comme le rattachement) appelle `MailboxManagementService.ReauthenticateAsync` : boîte du compte (non détachée), jeton PSC requis, même garde d'ancrage qu'au rattachement, sonde XOAUTH2 (`TestImapConnectionAsync`), `MarkAuthenticationOutcomeAsync`, trace `MailServerAuthRetry` (succès ou échec, avec le code), boîte relue. Réponses : 200 avec la boîte relue ; 400, 401, 404, 409 en `problem+json` avec `code`.
  - Constat : `MarkAuthenticationOutcomeAsync` n'avait **aucun appelant** avant cette route. Une boîte ne passait donc jamais `AuthFailing` en production (écart E016 déjà connu : re-validation non câblée). La route en est le premier appelant.
- Règle 1b, test d'intégration de bout en bout (`MailboxReauthenticationIntegrationTests`, pile réelle + registre PostgreSQL, seuls la sonde opérateur et le proxy PSC simulés) :
  - `Reauthenticate_AcceptedByTheOperator_TurnsTheMailboxActiveAgain` : `state` `Active` lu dans la réponse et dans la liste relue ;
  - `Reauthenticate_RefusedByTheOperator_KeepsTheMailboxAuthFailing_WithAReadableCode` : 400, `code` `AUTH_FAILED`, liste relue `AuthFailing` ;
  - `Reauthenticate_OfAMailboxTheAccountDoesNotHave_Answers404_WithoutProbing`.
  - Prémisse affirmée : la boîte est `AuthFailing` et non sélectionnable avant l'appel.
  - **Mutations** (copie, restauration, `touch`) : M1, issue enregistrée toujours `false` → rouge `Accepted…` (« Expected Active / Actual AuthFailing ») ; M2, toujours `true` → rouge `Refused…` (« Expected AuthFailing / Actual Active ») ; restauré → 3/3 verts.
- Tests unitaires : `MailboxManagementServiceReauthenticateTests` (7, une par branche) ; `AccountControllerCoverageTests` (+6 : 404, 409, 401, 400 avec `code`, 200, 403).
- Fronts (weda2 et mobile, tests écrits d'abord) :
  - entrée : liste illisible → décision `Unavailable` → écran `unavailable` avec « Réessayer ». Jamais « PSC requis » ni l'onboarding, y compris avec une boîte désignée par l'hôte côté weda2 ;
  - gestion : définir par défaut, détacher, rattacher à nouveau et « Ré-essayer l'authentification » testent leur résultat et affichent le motif (`actionError`) ou la confirmation (`actionNotice`). Un détachement en échec ne déconnecte ni ne bascule. Une liste illisible ne vide plus l'écran ;
  - erreurs : `instance` lu comme code seulement s'il en a la forme ; 5xx → `SERVICE_UNAVAILABLE`, 404 → `MAILBOX_NOT_ATTACHED` ; libellés `PSC_SESSION_REQUIRED`, `MAILBOX_NOT_ATTACHED`, `SERVICE_UNAVAILABLE` ; une seule traduction, `describeMailboxError`, pour le formulaire de rattachement et la gestion.
  - Rouges vus avant le code : weda2, service 4, store 3, garde 2, gestion 6. Mobile, preuve par mutation (initialize sans branche `Unavailable` + détachement sans test de résultat) → 3 rouges ciblés ; restauré → vert.
- E2E (Step 6b) : catalogue `E2E-MAILBOX-002` v1 (mobile et angular requis). Tests ajoutés dans `Client/Mobile/e2e/specs/functional.spec.ts` et `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` : panne 503 simulée une fois à la frontière réseau, réessai sur le vrai backend, compteur à 1. `tsc` vert sur les deux suites. **Preuve par mutation e2e non jouée ici** (/develop ne lance pas de voie) : à constater par `/e2e`.
- Local build / test :
  - api-mail : build 0 erreur. Suite complète : 6 798 tests, 2 rouges **hors périmètre et flaky** (`BackgroundSyncServiceCoverageTests.StartSyncAsync_WhenLeaseRenewalFails…`, course sur une `List` partagée du test ; `E2eUnattachedXdmTests.TheSeededCda_CarriesATrappedCell…`, rendu CDA sous charge), tous deux verts rejoués isolément. Après la passe qualité : `mss.mail.api.tests` 1 286/1 286 et intégration ciblée 26/26.
  - weda2 : `npm run build` ✓, `npm test` ✓ (dont mss-lib 1 238/1 238).
  - client-mobile : `npm run build` ✓, `npm test` 1 254/1 254.
- Passe qualité (/simplify) :
  - Applied & committed : api-mail, 1 fichier (`3c50cf7c`) : `CodedProblem` réutilisé pour le 401 `PSC_SESSION_REQUIRED` du rattachement.
  - No change : client-mobile, client-angular (la traduction d'erreurs partagée avait été factorisée dans le code de la feature).
  - Contrôles mécaniques §Q 2b (S125, xUnit1045, S4457, xUnit2032) : aucun résultat.
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk, devops, psc-proxy-*
- Conventions : `csharp.md` xUnit1051 → 4 ; `angular.md` jsdoc → 10 (constante insérée au-dessus d'une signature documentée).
- DOD self-check : build et tests ✓ ; test d'intégration de la sonde ✓ (vu rouge) ; tests rouges d'abord (503 à l'entrée, DELETE en 500, 409 detail et 401 libellé) ✓ sur les deux fronts ; scénario E2E-MAILBOX-002 ✓ (catalogue + deux clients, à jouer par /e2e) ; aucune adresse ni identifiant de session ajouté aux journaux ✓ (le log serveur ne porte que le code ; l'adresse ne va qu'à l'audit, comme les autres traces de boîte).
- **Reprise après /review** : le test mobile de `describeMailboxError` (libellé `PSC_SESSION_REQUIRED`, ligne de DOD « sur weda2 **et** sur client-mobile ») manquait. Ajouté (`56ed09b`, 5 tests), prouvé rouge par mutation (libellé retiré : 1 rouge ciblé, puis restauré : 1 259/1 259), lint mobile propre, voie mobile rejouée verte.
- Next step : /sonar task-378

## Sonar log

- Serveur SonarQube 25.6.0.109173 (`sonar.token`), port 9001 mesuré, projet **`healthplatform-api-mail`** (clé surchargée), branche `fix/task-378-pannes-entree-messageries` (`3c50cf7c`). Une analyse complète : build Release + 5 passes OpenCover. Jeton masqué dans `metrics/timings.jsonl` (`sonar.token=***`).
- **Phase 1 (new code de la task)** : ✓ aucun problème imputable à la task.
  - 0 issue et 0 hotspot dans les fichiers touchés (`AccountController`, `MailboxManagementService`, `IMailboxManagementService` et leurs tests).
  - Couverture des fichiers modifiés : `MailboxManagementService` 97,3 %, `AccountController` 99,5 % (cible 95 %).
  - Aucune correction ni aucun test ajouté.
- **Quality Gate du projet : ERROR, hérité** (mémoire « la new-code period inclut des tasks déjà mergées ») :
  - `new_violations` 72, identiques à la baseline (rapport Python et scripts k6 du banc de charge, `AddNewMailConsumer`, `AuditService`, `IMailRepository`, task-384/385…) ;
  - `new_security_hotspots_reviewed` 0 % : 13 hotspots, aucun dans les fichiers de la task (Dockerfile, scripts k6, tests Python du rapport, `BaseRepository.cs:754`).
  - Même verdict que task-373 et task-376 : la dette héritée mérite une task dédiée.
- **Phase 2 (legacy)** : non jouée (optionnelle, best-effort).
- Tests sous couverture : domain 195, application 3 626, infrastructure 695, api 1 286, intégration 978/997 (16 ignorés préexistants). **3 rouges préexistants hors périmètre** : les tests « du jour » (`FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync`, `GetFolderTodayAsync_Inbox…`, `GetFolderNotSeenTodayAsync_Inbox…`), rouges entre 00:00 et 02:00 heure locale (passe jouée à 00:12), aussi rouges sur `develop`.
- `conventions/csharp.md` : non alimenté par /sonar (aucune règle corrigée).

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse précédente) | Final (branche task-378) | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (hérité, 0 problème imputable à la task) |
| New coverage | 98,2 % | 98,2 % | 0 |
| New violations | 72 | 72 | 0 |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Code smells | 70 | 70 | 0 |
| Coverage (projet) | 98,1 % | 98,1 % | 0 |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D/A/A | D/A/A | → |

## Lint log

- Base `origin/next` (fetch), portée lint `tag:scope:mss` (13 projets touchés par `nx affected`).
- Baseline : **0 erreur**, warnings préexistants seulement (jsdoc `require-example`, `max-lines`).
- Itération 1 : pas d'auto-fix nécessaire. Deux warnings `jsdoc/require-example` préexistants dans un fichier de la task (`reload`, `confirmRemove` de `mss-mailbox-management.component.ts`) complétés à la main. Le fichier re-linté est propre ; spec du composant 21/21.
- Restant : `mailbox-session.store.ts` `max-lines` (623 > 500), préexistant (~613 lignes avant la task), accepté.
- Build + tests weda2 complets : déjà verts au /develop (`npm run build`, `npm test`), seuls des commentaires ont changé depuis.
- Code-only : aucune opération git sur `client-angular`.

## Lint mobile log

- Branche `fix/task-378-pannes-entree-messageries`, arbre propre.
- Baseline `npm run lint` : **All files pass linting** (0 erreur, 0 warning). Aucune itération ni correction, donc aucun commit.
- Build + tests : verts au /develop (`npm run build`, `npm test` 1 254/1 254), inchangés depuis.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail + client-mobile touchés | ✅ verte — rejouée après le test ajouté en revue (`56ed09b`) | 45 verts, 0 flaky, 0 rouge, 0 quarantaine | 8 min 36 s |
| angular | api-mail + client-angular touchés | ✅ verte — 1er passage rouge (test frais corrigé), puis verte deux fois | 52 verts, 1 flaky, 0 rouge (quarantaine E2E-COMPOSE-002 verte) | 8 min 53 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`fix/task-378-pannes-entree-messageries`)
- **1er passage Angular rouge, défaut du test frais (pas de régression)** : E2E-MAILBOX-002 cherchait la boîte de réception après « Réessayer », qui rend la main à la page d'accueil. En weda2 autonome, cette page est le **tableau de bord** (la boîte était bien ouverte, compteurs et session PSC affichés). Le test navigue désormais explicitement vers `/messagerie/mail`. Prévention : `conventions/e2e.md` « accueil-selon-l-hote ».
- **Preuve par mutation des deux tests E2E-MAILBOX-002** (backend `--serve-only`, test isolé, `--retries=0`) : vert → mutation compilée de `initialize()` (« échec = zéro boîte », rechargement du serveur de dev attendu) → **rouge sur « la panne est dite comme une panne »** → restauré (copie + `touch`) → vert. Sur weda2 et sur le mobile.
- Rejeux : la voie Angular a été **rejouée** et non réutilisée après le commit mobile `56ed09b`, qui ne touche que `src/`. L'empreinte de `client-mobile-e2e` prend le HEAD du dépôt entier. Piste d'amélioration dans le rapport.
- Quarantaines : E2E-COMPOSE-002 [angular] (task-350), passée verte
- Flaky : E2E-SEARCH-001 [angular], vert au 2e essai à chacun des trois passages (registre : 9 occurrences, task de stabilisation à ouvrir, déjà signalée)
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (les deux suites portent E2E-MAILBOX-002)
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143 libres, aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

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
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
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
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/310 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/104 — label `awaiting-human-merge`
- `client-angular` (code-only) : l'humain gère le commit, le push TFS et l'ouverture de la PR. Fichiers modifiés, non commités sur `feature/nova-mss-weda-integration` (build + tests verts au /review) :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/core/guards/mailbox.guard.spec.ts`
  - `front/libs/mss/src/core/guards/mailbox.guard.ts`
  - `front/libs/mss/src/core/models/mailbox.model.ts`
  - `front/libs/mss/src/core/models/mss-probe.model.ts`
  - `front/libs/mss/src/core/services/mailbox-accounts.service.spec.ts`
  - `front/libs/mss/src/core/services/mailbox-accounts.service.ts`
  - `front/libs/mss/src/core/stores/mailbox-session.store.spec.ts`
  - `front/libs/mss/src/core/stores/mailbox-session.store.ts`
  - `front/libs/mss/src/features/index.ts`
  - `front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.html`
  - `front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.scss`
  - `front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.spec.ts`
  - `front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.ts`
  - `front/libs/mss/src/features/mailbox-select/mss-mailbox-select.component.ts`
  - `front/libs/mss/src/index.ts`
  - `front/libs/mss/src/ui/attach-mailbox-form/attach-mailbox-form.component.ts`
  - `front/libs/mss/src/core/models/mss-probe.model.spec.ts`
  - `front/libs/mss/src/features/mailbox-unavailable/`
  - ⚠️ À commiter sur TFS **avant le merge de la PR api-mail** : `functional.e2e.ts` porte le test du scénario requis E2E-MAILBOX-002.

## Code Review Summary

**Verdict : APPROVED** — 0 point bloquant, 2 suggestions. Une lacune de DOD trouvée en revue (test mobile du libellé `PSC_SESSION_REQUIRED`) a été renvoyée à `/develop` et comblée avant l'ouverture des PR (`56ed09b`, prouvé rouge par mutation).

### Règle 1b — comportement → test d'intégration → preuve rouge

| Comportement atteignable par un endpoint | Test d'intégration (pile réelle, registre PostgreSQL) | Preuve rouge |
|---|---|---|
| `POST …/mailboxes/{id}/reauthenticate`, sonde acceptée : la boîte repasse `Active` (réponse + liste relue) | `MailboxReauthenticationIntegrationTests.Reauthenticate_AcceptedByTheOperator_TurnsTheMailboxActiveAgain` | M1 (issue toujours `false`) : « Expected Active / Actual AuthFailing » |
| Sonde refusée : 400 `problem+json`, `code` `AUTH_FAILED`, boîte toujours `AuthFailing` | `…Reauthenticate_RefusedByTheOperator_KeepsTheMailboxAuthFailing_WithAReadableCode` | M2 (issue toujours `true`) : « Expected AuthFailing / Actual Active » |
| Boîte inconnue du compte : 404 `MAILBOX_NOT_ATTACHED`, aucune sonde | `…Reauthenticate_OfAMailboxTheAccountDoesNotHave_Answers404_WithoutProbing` | route absente avant la task (rouge par construction) |
| 401 `PSC_SESSION_REQUIRED` du rattachement (passage à `CodedProblem`, refactor) | `PscSessionIntegrationTests` existants, verts (26/26 ciblés) | refactor pur, comportement inchangé |

### api-mail
- `AccountController.ReauthenticateMailboxAsync` — ✅ scope d'opération, `[MailboxNotRequired]`, limiteur `Sensitive` comme le rattachement, refus en `problem+json` avec `code` (règle 12).
- `MailboxManagementService.ReauthenticateAsync` — ✅ validation hors du corps `async` (S4457), boîte détachée = 404, même garde d'ancrage PSC qu'au rattachement, trace d'audit `MailServerAuthRetry`, aucun identifiant ni adresse dans le journal applicatif (le code seul).
  - ⚠️ **Suggestion** : toute sonde en échec enregistre un échec d'authentification, y compris `HOST_UNREACHABLE` (opérateur injoignable). Par l'interface, sans effet : le bouton n'est offert que sur une boîte déjà `AuthFailing`. Par un appel direct sur une boîte `Active` pendant une panne de l'opérateur, la boîte passerait `AuthFailing`. Proposer de n'enregistrer l'échec que sur `AUTH_FAILED` (task de suivi).
- Constat : `MarkAuthenticationOutcomeAsync` n'avait aucun appelant avant cette route (re-validation E016 non câblée, déjà connue) : la route en est le premier.

### client-mobile / client-angular (weda2)
- Store / service de session — ✅ `initialize()` rend `Unavailable` sur toute erreur de liste ; garde d'entrée et écran de choix redirigent vers l'écran de panne (weda2 : y compris quand l'hôte désigne une boîte).
- Écrans `unavailable` — ✅ texte FR en dur, `data-testid`, `ds-button` avec `id` (weda2), « Réessayer » relit la liste avant de rendre la main.
- Gestion des messageries — ✅ chaque action teste son résultat ; un détachement en échec ne déconnecte ni ne bascule ; une liste illisible ne vide plus l'écran.
  - ⚠️ **Suggestion** : sur un détachement en échec de la boîte courante, la session serveur a déjà été fermée (fermer avant de détacher, task-310). Elle se rouvre à la requête suivante. Acceptable, mais une ligne de commentaire le dit déjà ; rien à faire.
- Lecture des erreurs — ✅ `instance` lu comme code seulement s'il en a la forme ; 5xx → `SERVICE_UNAVAILABLE` ; une seule traduction `describeMailboxError` (weda2 et mobile), réutilisée par le formulaire de rattachement.

### DOD
- [x] Build et tests verts : weda2, client-mobile, api-mail (api-mail : 3 tests « du jour » rouges entre 00:00 et 02:00, préexistants et hors périmètre ; voir le rapport)
- [x] Test d'intégration de la sonde de ré-authentification, vu rouge (tableau ci-dessus)
- [x] Tests rouges d'abord, weda2 **et** mobile : 503 à l'entrée → écran de panne ; DELETE en 500 → pas de déconnexion, motif, boîte listée ; 409 → `detail` du serveur ; 401 `PSC_SESSION_REQUIRED` → libellé dédié
- [x] Scénario E2E-MAILBOX-002 au catalogue, requis angular + mobile, implémenté dans les deux clients, prouvé rouge par mutation, voies vertes
- [x] Aucune adresse ni identifiant de session ajouté aux journaux

## Merged

- Le 2026-10-25, par `/merge task-378 --i-tested` (validation humaine attestée).
- `api-mail` : squash `fb9f9867` (PR #310 fermée, label retiré, branche distante et locale supprimées). CI `develop` verte : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/40173849169
- `client-mobile` : squash `d9dddee5` (PR #104 fermée, label retiré, branches supprimées). CI `develop` verte : https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/40173865699
- `client-angular` : managed manually by the human (TFS).

## Timings

*(généré par `tools/timing/report.sh --task task-378 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 29 s | — | — | — | — |
| /develop | ok | 49 min 52 s | 7 (3 min 21 s) | 6 (10 min 13 s) | — | api-mail 5B/3T, client-angular 1B/2T, client-mobile 1B/1T |
| /sonar | ok | 11 min 48 s | 1 (22 s) | 5 (6 min 17 s) | 2 (2 min 14 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 3 min 38 s | — | 1 (56 s) | — | 1 itération(s), client-angular 0B/1T |
| /lint-mobile | ok | 49 s | — | — | — | — |
| /e2e | ok | 42 min 32 s | — | — | — | e2e ×8 (44 min 37 s) |
| /review | ok | 1 h 02 min | 3 (1 min 37 s) | 4 (8 min 14 s) | — | client-mobile 1B/1T, client-angular 1B/1T, api-mail 1B/2T |
| /tech-writer | ok | 2 min 38 s | — | — | — | — |
| **Total cycle** | | **2 h 54 min** | **11 (5 min 21 s)** | **16 (25 min 41 s)** | **2 (2 min 14 s)** | |

Autres commandes mesurées : lint ×3 (2 min 30 s)
