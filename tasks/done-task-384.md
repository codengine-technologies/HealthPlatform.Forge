# todo-task-384.md — Le praticien voit, en bas des Paramètres, la version et la date de build de l'application et du serveur de messagerie

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: aucune
**Priorité**: 3 — fonctionnalité de support : identifier exactement ce qui est déployé quand un praticien signale un problème.

> **Origine.** Demande humaine du 2026-10-20 (`/po`). Décisions prises au cadrage :
> SemVer GitVersion + date et heure de build pour le serveur, information du serveur réservée
> à un praticien connecté, mobile inclus, environnement affiché.

## Ce qui est établi (2026-10-20)

- **api-mail** n'a aucun numéro de version : l'image Docker de la CI (`.github/workflows/dotnet.yml`) est
  étiquetée `latest` (master) ou `develop`. Endpoints existants hors métier : `/health`, `/alive`.
- **client-angular** : `front/package.json` reste à `0.0.1`. La CI Azure calcule déjà une version GitVersion
  (`GitVersion.SemVer`, suffixe `-{n}-dev` hors master) mais ne s'en sert que pour le tag de l'image Docker.
- **client-mobile** : `package.json` à `0.0.1`.
- Page Paramètres de weda2 : `libs/mss/src/features/settings/mss-settings.component.html`, dernière section
  « Serveur » (`mss-settings__row--last`). La branche de travail Angular est désormais
  `feature/nova-mss-weda-integration` (tirée de `next`).

## Objective

Quand un praticien signale un problème, le support doit savoir exactement quelles versions il utilise. En bas
de la page Paramètres de la messagerie (weda2 et mobile), l'application affiche **sa propre version, sa date de
build et son environnement**, ainsi que **les mêmes informations pour le serveur de messagerie**. L'information
du serveur n'est lisible que par un praticien connecté, pour ne pas divulguer la version à un tiers.

### Règles métier

1. **Numéro de version** : SemVer calculé par GitVersion, pour api-mail, weda2 et le mobile (ex. `1.4.0` sur la
   branche principale, `1.4.0-0012-dev` ailleurs).
2. **Date de build** : affichée à l'heure de Paris, au format « 20/10/2026 à 14:32 ».
3. **Environnement** : libellé « Développement », « Recette » ou « Production » ; une valeur inconnue est affichée
   telle quelle.
4. **Accès** : l'information du serveur n'est lisible que par un praticien authentifié ; sans session, elle est
   refusée et rien n'est révélé.
5. **Serveur injoignable** : la version de l'application reste affichée ; la ligne du serveur indique
   « information indisponible ».
6. **Emplacement** : tout en bas des Paramètres — après la section « Serveur » sur weda2, en fin d'écran sur
   mobile.

Rendu attendu (exemple) :

> Application — 1.4.0 · build du 20/10/2026 à 14:32 · Production
> Serveur de messagerie — 2.1.0 · build du 19/10/2026 à 09:05 · Production

## Gherkin

See `tests/Features/Mss/VersionInformation.feature`

## Definition of Done

- [ ] Build vert sur api-mail, client-angular et client-mobile (0 erreur)
- [ ] api-mail : version SemVer GitVersion et date de build intégrées au build, y compris dans l'image Docker produite par la CI
- [ ] Test d'intégration de bout en bout pour l'endpoint de version (règle 1b), vu rouge : cas nominal — `version`, `buildDate` et `environment` présents dans la réponse réelle et cohérents avec le build ; cas d'échec — sans session, refus et aucune version dans la réponse
- [ ] ≥ 1 test unitaire sur la fourniture des informations de build côté api-mail
- [ ] weda2 et mobile : version, date de build et environnement injectés au build (aucune valeur codée en dur ; `package.json` n'est plus la source de la version affichée)
- [ ] Tests de composant (weda2 et mobile) : affichage nominal, date convertie à l'heure de Paris, serveur injoignable
- [ ] `data-testid` sur la ligne Application et sur la ligne Serveur de messagerie (weda2 et mobile)
- [ ] Scénario E2E-SETTINGS-003 ajouté (version 1) dans `Api/Mail/e2e/scenarios.yml` — titre « Lire la version de l'application et du serveur dans les Paramètres », attendu « les deux lignes affichent une version, une date de build et un environnement non vides » — et implémenté dans chaque client où il est requis (angular `requis`, mobile `requis`)
- [ ] Aucune donnée de santé ni identifiant de session dans la réponse ou dans les logs

## Manual Test Plan

1. Lancer api-mail et weda2, se connecter, ouvrir Messagerie > Paramètres, descendre tout en bas : les lignes
   « Application » et « Serveur de messagerie » affichent chacune une version, une date de build à l'heure de
   Paris et un environnement.
2. Comparer la version du serveur affichée avec le tag GitVersion de l'image déployée.
3. Arrêter api-mail, recharger les Paramètres : la ligne Application reste affichée, la ligne Serveur indique
   « information indisponible ».
4. Interroger l'endpoint de version sans session : refus, aucune version renvoyée.
5. Refaire les vérifications 1 et 3 sur l'application mobile.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — fonctionnalité de support, sans échange métier
- **Vague Ségur** : hors Ségur — aucune exigence de référencement concernée
- **Exigences DSR honorées** : non applicable — fonctionnalité de support
- **INS** : non applicable — aucun patient manipulé
- **Authentification PS** : session existante (PSC / e-CPS) exigée pour lire la version du serveur ; niveau eIDAS inchangé
- **Habilitations** : tout praticien connecté ; pas de contrôle de profession ou de spécialité
- **Interop CI-SIS** : non applicable — aucun document ni échange métier
- **Tracé PGSSI-S** : aucun évènement nouveau — la lecture de la version n'est pas un acte métier
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — aucune donnée de santé produite ni manipulée (l'API reste hébergée en environnement HDS)
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle
- **Sécurité** : version non exposée publiquement (limitation de la divulgation d'informations, OWASP) ; réponse sans donnée de santé ni secret

## Branches
- `api-mail` (pushed) : feat/task-384-version-et-date-de-build — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-384-version-et-date-de-build
- `client-mobile` (pushed) : feat/task-384-version-et-date-de-build — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-384-version-et-date-de-build
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`, propre, HEAD `c084e198`) — l'humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-384 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| /develop | ok | 26 min 42 s | 5 (1 min 06 s) | 4 (5 min 04 s) | — | api-mail 2B/2T, client-angular 2B/1T, client-mobile 1B/1T |
| /sonar | ok | 9 min 14 s | 1 (42 s) | 5 (6 min 18 s) | 2 (50 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 2 min 26 s | 1 (13 s) | 1 (28 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 23 s | — | — | — | — |
| /e2e | ok | 29 min 18 s | — | — | — | e2e ×4 (22 min 41 s) |
| /review | ok | 7 min 27 s | 3 (25 s) | 3 (4 min 22 s) | — | api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| **Total cycle** | | **1 h 15 min** | **10 (2 min 27 s)** | **13 (16 min 13 s)** | **2 (50 s)** | |

Autres commandes mesurées : lint ×3 (32 s), restore ×1 (43 s)

## Develop log

- Repos touchés : api-mail, client-angular (code-only), client-mobile. DTOs : aucun changement (`BuildInfoResponse` est un contrat propre à api-mail, consommé par les clients TypeScript avec leurs propres types). Interop : aucun changement.
- **api-mail** (`feat/task-384-version-et-date-de-build`) :
  - `5ed5fb3a` feat(build-info) : `GET /api/v1/build-info` (`BuildInfoController`, `[MailboxNotRequired]`, scope d'opération `GetBuildInfo`) ; `BuildInfoProvider` (version informationnelle sans « +sha », date de la métadonnée d'assembly `BuildDate` avec repli sur la date du fichier en build local, environnement lu dans `Deployment:Environment` puis dans le nom d'environnement ASP.NET) ; `mss.mail.api.csproj` (`AssemblyMetadata BuildDate` seulement si `-p:BuildDate` est fourni) ; Dockerfile (`APP_VERSION`, `BUILD_DATE`) ; CI GitHub (`fetch-depth: 0`, GitVersion.Tool 6.3.0 → SemVer de l'image).
  - `c45138e4` test(e2e) : E2E-SETTINGS-003 v1 au catalogue (mobile `requis`, angular `requis`).
  - Tests : `BuildInfoProviderTests` (17), `BuildInfoControllerTests` (2), `BuildInfoEndpointIntegrationTests` (2, hôte réel + `AddMssAuthentication` + politique par défaut).
  - **Preuve rouge par mutation** (règle 1b) : M1 version vidée dans la réponse → `AnAuthenticatedPractitioner_ReadsTheVersionBuildDateAndEnvironment_OfTheRunningApi` rouge (Expected "1.0.0", Actual "") ; M2 `[AllowAnonymous]` sur l'action → `WithoutASession_TheRequestIsRefused_AndNoVersionIsRevealed` rouge (Expected Unauthorized, Actual OK) ; M3 clé `Deployment:Environment` ignorée → premier test rouge (Expected "Production", Actual "Development"). Restauration vérifiée, 2/2 verts.
  - Validation : build solution 0 erreur ; tests 195 + 690 + 3 661 + 1 259 + 898 (16 ignorés préexistants). Premier passage : `ControllerOperationScopeScanTests` rouge (action sans scope d'opération) → scope ajouté, vert.
- **client-angular** (code-only, branche `feature/nova-mss-weda-integration`, rien de commité) — fichiers modifiés :
  - `azure-pipelines.yml` (BuildWeda2 : GitVersion, `APP_VERSION` = même expression que le tag d'image, `BUILD_DATE`) ; `devops/k8s/weda2-frontend-configmap.yaml` (`environmentName` ← `${ENVIRONMENT_NAME}`)
  - `front/.gitignore`, `front/scripts/write-build-info.mjs`, `front/apps/weda2/project.json` (cible `build-info`, dont dépendent `build` et `serve`)
  - `front/apps/weda2/src/main.ts` (charge aussi `assets/build-info.json`), `environments/*.ts` (`environmentName`, `appVersion`, `appBuildDate`), `app/app.config.ts` (+ `appBuildInfoFactory`, jeton `MSS_APP_BUILD_INFO`), `app/app.config.spec.ts`
  - `front/libs/mss/src/core/` : `models/build-info.model.ts`, `tokens/mss-app-build-info.token.ts`, `utils/build-info.util.ts` (+ spec), `services/mss-api.service.ts` (`getServerBuildInfo`) + `mss-api.build-info.service.spec.ts`, `index.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.{ts,html,spec.ts}` : section « À propos » en dernière position (`settings-app-build-info`, `settings-server-build-info`)
  - `front/e2e/mss-e2e/specs/functional.e2e.ts` : E2E-SETTINGS-003 v1
  - Validation : `nx build weda2 --configuration=production` vert (budget initial 2 MB dépassé de 44 kB — avertissement préexistant, +2 kB) ; tests weda2 2 655, mss-lib 937, design-system 1 924 ; `tsc -p e2e/mss-e2e` ✓.
  - Environnement local remis d'aplomb (hors code) : `npm ci` (les `node_modules` dataient de l'ancienne branche, `vitest-canvas-mock` manquant) ; client hey-api **généré et ignoré par git** `apps/weda2/src/app/core/api/generated/` resté de l'ancienne branche (il importait `../hey-api.config`, exclu du report) déplacé vers le scratchpad de session — rien ne l'importe sur la branche.
- **client-mobile** (`feat/task-384-version-et-date-de-build`) :
  - `ef0bb31` feat(mobile) : `scripts/write-build-info.mjs` → `src/assets/build-info.json` (hooks `prestart`/`prebuild`/`prebuild:local`, `e2e/headless/run.mjs`, CI Android avec GitVersion) ; `AppBuildInfoService` (lecture unique de l'asset par `fetch`, hors intercepteur MSS) ; `build-info.util` ; `getServerBuildInfo` ; section À propos ; `environment.appVersion: '0.0.1'` remplacé par `environmentName`.
  - `034be6a` test(e2e) : E2E-SETTINGS-003 v1 dans `e2e/specs/functional.spec.ts`.
  - Validation : `npm run build` vert ; `npm test` 1 125/1 125 ; `tsc -p e2e` ✓. Stitch : sans objet (aucun écran créé ni réécrit, seule la section À propos change).
- Passe qualité (/simplify) :
  - No change : api-mail (contrôles mécaniques S125 / xUnit1045 / S4457 / xUnit2032 vides), client-angular, client-mobile — diff court, réutilise l'existant (scope d'opération, `MailboxNotRequired`, politique par défaut, chargement runtime de `main.ts`). L'utilitaire de mise en forme est dupliqué entre weda2 et le mobile : deux dépôts sans bibliothèque commune.
  - Skipped (contrat/exclu) : dtos-mss, interop-cda.
- **E2E** : E2E-SETTINGS-003 écrit dans les deux suites, typé ; **preuve par mutation reportée à `/e2e`** (elle demande le banc complet : backend e2e + serveurs de dev).
- **À faire hors forge (humain / DevOps)** :
  - Release weda2 : déclarer la variable `ENVIRONMENT_NAME` (Development / Staging / Production) pour la configmap.
  - DevOps api-mail : `DevOps/Prod/configmap.yaml` (et Staging, Weda) — poser `Deployment__Environment` (ex. `Production`) : la production tourne aujourd'hui avec `ASPNETCORE_ENVIRONMENT=Staging`, ce qui afficherait « Recette » sans la clé dédiée.
- DOD self-check : build ✓ (3 repos) ; version + date dans l'image Docker ✓ (Dockerfile + CI, non exécutables localement) ; test d'intégration nominal + échec vus rouges ✓ ; ≥ 1 test unitaire ✓ ; weda2/mobile injectés au build ✓ ; tests de composant (nominal, heure de Paris, serveur injoignable) ✓ ; `data-testid` ✓ ; E2E-SETTINGS-003 catalogué + implémenté ✓ (preuve rouge à `/e2e`) ; aucune donnée de santé ni identifiant de session dans la réponse ✓.
- Next step : `/sonar task-384`.

## Sonar log

- Mode A (chaîné), SonarQube 9.9.8 (`sonar.login`), branche `feat/task-384-version-et-date-de-build` (HEAD `c45138e4`). 1 analyse, aucun correctif nécessaire.
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,6 % ; 0 issue, 0 hotspot sur le new code. Fichiers de la task : `BuildInfoController.cs` 100 %, `BuildInfoProvider.cs` 90,9 % (0 ligne non couverte, 5 conditions dans les lectures statiques de l'assembly réellement chargée).
- Phase 1 — Issues fixées : 0 ; tests ajoutés : 0 (ceux de `/develop` suffisent).
- Phase 2 (legacy) : sans objet — 0 bug, 0 vulnérabilité, 0 code smell, 0 hotspot sur le projet.
- Build Release / tests : ✓ 195 + 3 661 + 690 + 1 259 + 898 (16 ignorés préexistants).
- Aucune consigne nouvelle pour `conventions/csharp.md` (rien à corriger).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | 96,8 % | 96,6 % | −0,2 pt (cible 95 %) |
| Bugs | 0 | 0 | = |
| Vulnerabilities | 0 | 0 | = |
| Security hotspots | 0 | 0 | = |
| Code smells | 0 | 0 | = |
| Coverage (projet) | 97,9 % | 97,9 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Reliability / Security / Maintainability | A / A / A | A / A / A | = |

- Next step : `/lint-angular task-384`.

## Lint log

- Mode A, code-only (`Client/Angular/front`, branche `feature/nova-mss-weda-integration`, rien de commité). Comme task-372 : `npx eslint --format json` sur les 18 fichiers `.ts`/`.html`/`.mjs` de la task, puis `nx run-many -t lint --projects=tag:scope:mss` aligné sur le pipeline.
- Référence : 12 erreurs, toutes de la task, toutes `prettier/prettier` (signatures longues, jeton, bloc E2E-SETTINGS-003).
- Itération 1 : `eslint --fix` sur les fichiers de la task. Le fixer a aussi converti l'import existant de la ligne 1 de `functional.e2e.ts` en `import type` (avertissement hors task) : ligne restaurée, pour ne toucher aucune ligne préexistante (`prettier-fichier-existant`).
- Après : **0 erreur** (fichiers de la task et `mss`, `mss-lib`, `mss-e2e`). Avertissements : `mss-lib` 45 → 46 — `mss-settings.component.ts` passe à 508 lignes (`max-lines` 500, avertissement accepté) ; les autres sont antérieurs à la task.
- Revalidation : `nx build weda2 --configuration=production` ✓, `nx test mss-lib weda2` ✓ (937 + 2 655), `tsc -p e2e/mss-e2e` ✓.
- Next step : `/lint-mobile task-384`.

## Lint mobile log

- Mode A, branche `feat/task-384-version-et-date-de-build` (HEAD `034be6a`), arbre propre.
- `npm run lint` : **All files pass linting** — 0 erreur, 0 avertissement. Aucune itération de correction, aucun commit.
- Build et tests déjà verts à `/develop` (`npm run build`, `npm test` 1 125/1 125) ; arbre inchangé depuis, pas de revalidation.
- Next step : `/e2e task-384`.

## E2E log

> **Flaky récurrent → task de stabilisation à ouvrir** : E2E-COMPOSE-001 (angular), 5ᵉ occurrence, et première récidive après le correctif de task-370.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail + client-mobile touchés | ✅ verte | 38 verts, 0 flaky, 0 rouge, 0 quarantaine | 6 min 36 s |
| angular | api-mail + client-angular touchés | ✅ verte | 45 verts, 1 flaky, 0 rouge, 1 quarantaine | 7 min 23 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `feat/task-384-version-et-date-de-build` (E2E-SETTINGS-003 v1).
- **Premier passage de la voie Angular en outillage (code 2)** : weda2 servi en HTTP, le banc l'attend en HTTPS. `run.mjs` passait `--ssl-cert`/`--ssl-key` sans `--ssl` et comptait sur `ssl: true` de la cible `serve`, retirée au report sur `next` (elle codait des chemins de certificat propres à un poste). Corrigé dans `front/e2e/mss-e2e/run.mjs` (`--ssl` explicite, non commité, code-only), voie rejouée : verte.
- Quarantaines : E2E-COMPOSE-002 (angular, task-350) — Passed.
- Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun (Paramètres weda2 et mobile couverts par E2E-SETTINGS-003).
- Démontage : complet — ports 5052/8100/4200/3993/3465/3143 libres. Deux conteneurs `e2e-greenmail-gcgjbrzp` / `e2e-dovecot-kgrndjwd` arrêtés **depuis 6 jours**, antérieurs à ce run (non retirés : le run ne retire que ce qu'il crée).
- **Preuve rouge par mutation** (banc `--serve-only`, `--retries=0`, une mutation à la fois, recompilation du serveur de dev attendue avant chaque test, restauration vérifiée identique) :
  - weda2 — témoin vert ; M1 réponse du serveur jamais affichée (`next: () => undefined`) → rouge « la ligne Serveur affiche version, date de build et environnement » (Received "") ; M2 informations de l'application ignorées (`formatBuildInfo(this.appBuildInfo && null)`) → rouge « la ligne Application… » (Received "information indisponible") ; après restauration : vert.
  - mobile — témoin vert ; M1 (`formatBuildInfo(server && null)`) → rouge sur la ligne Serveur ; M2 (`formatBuildInfo(app && null)`) → rouge sur la ligne Application ; après restauration : vert.
  - Mutations écrites pour rester compilables (aucun symbole rendu inutilisé : piège `mutation-non-servie`).
- Registre des flaky (`conventions/e2e.md`) : E2E-COMPOSE-001 angular 4 → 5, dernière task task-384.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « rédaction — envoyer, recevoir, lire, supprimer » (E2E-COMPOSE-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ⚠️ flaky | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version de l'application et du serveur dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
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
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/302 — label `awaiting-human-merge` (route `GET /api/v1/build-info`, Dockerfile, CI GitVersion, catalogue E2E-SETTINGS-003). **À merger en premier** : le mobile et weda2 consomment la route.
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/97 — label `awaiting-human-merge`.
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Branche `feature/nova-mss-weda-integration`. Fichiers modifiés (non commités) :
  - `azure-pipelines.yml`
  - `devops/k8s/weda2-frontend-configmap.yaml`
  - `front/.gitignore`
  - `front/apps/weda2/project.json`
  - `front/apps/weda2/src/app/app.config.spec.ts`
  - `front/apps/weda2/src/app/app.config.ts`
  - `front/apps/weda2/src/environments/environment.prod.ts`
  - `front/apps/weda2/src/environments/environment.test.ts`
  - `front/apps/weda2/src/environments/environment.ts`
  - `front/apps/weda2/src/main.ts`
  - `front/e2e/mss-e2e/run.mjs`
  - `front/e2e/mss-e2e/serve-only.log`
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/core/index.ts`
  - `front/libs/mss/src/core/models/build-info.model.ts`
  - `front/libs/mss/src/core/services/mss-api.build-info.service.spec.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/core/tokens/mss-app-build-info.token.ts`
  - `front/libs/mss/src/core/utils/build-info.util.spec.ts`
  - `front/libs/mss/src/core/utils/build-info.util.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.html`
  - `front/libs/mss/src/features/settings/mss-settings.component.spec.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.ts`
  - `front/scripts/write-build-info.mjs`
- **Hors forge (humain / DevOps)** :
  - Release weda2 : déclarer `ENVIRONMENT_NAME` (Development / Staging / Production) pour `config.json`.
  - DevOps api-mail (`DevOps/Prod`, `Staging`, `Weda`) : poser `Deployment__Environment` — la production tourne avec `ASPNETCORE_ENVIRONMENT=Staging`.

## Code Review Summary

**APPROVED** — 0 bloquant, 4 suggestions.

- Verrou intégration (règle 1b) : `GET /api/v1/build-info` → `BuildInfoEndpointIntegrationTests` (hôte réel, `AddMssAuthentication`, politique par défaut). Nominal : `version`, `buildDate` (UTC), `environment` lus dans la réponse ; échec : sans session, 401 et aucune version dans le corps. Preuve rouge par mutation : M1 version vidée, M2 `[AllowAnonymous]`, M3 clé `Deployment:Environment` ignorée — chacune rouge sur l'assertion prévue.
- Double verrou e2e : `## E2E log` vert ; E2E-SETTINGS-003 v1 au catalogue et dans les deux suites, prouvé rouge par mutation (weda2 et mobile, lignes Application et Serveur).
- Sécurité : la version n'est lisible qu'authentifié (politique par défaut conservée) ; `[MailboxNotRequired]` n'exempte que la boîte, pas l'authentification ; réponse sans donnée de santé ni secret.

Suggestions (non bloquantes) :
1. CI : GitVersion (6.3.0 sur api-mail et mobile, 5.12.0 sur weda2 comme le tag d'image) n'est exercé qu'au premier push sur `develop`/`master` — vérifier la version de la première image publiée.
2. Déploiement : poser `Deployment__Environment` sur les configmaps api-mail (la production tourne avec `ASPNETCORE_ENVIRONMENT=Staging`, ce qui afficherait « Recette ») et la variable de release `ENVIRONMENT_NAME` pour weda2 ; selon le mécanisme de substitution de la release, une variable non déclarée pourrait s'afficher brute (`${ENVIRONMENT_NAME}`).
3. `BuildInfoProvider` : 5 conditions non couvertes, dans les lectures statiques de l'assembly réellement chargée (repli sur la date du fichier) ; les extraire en méthodes internes paramétrées les rendrait testables.
4. weda2 : l'app autonome `apps/mss` ne fournit pas `MSS_APP_BUILD_INFO` — sa ligne Application dira « information indisponible » (weda2 est la cible de la US).

- Validation finale (`/review`) : api-mail build ✓, tests 195 + 690 + 3 661 + 1 259 + 898 (16 ignorés préexistants) — **un échec isolé et non identifié dans `mss.mail.api.tests` au premier passage** (lancé en parallèle des validations mobile et weda2), jamais reproduit ensuite (3 passages verts dont un sous la même charge) ; mobile build ✓, 1 125/1 125 ; weda2 build production ✓, weda2 2 655, mss-lib 937, design-system 1 924.
