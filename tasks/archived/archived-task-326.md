# todo-task-326.md — Un jeton non signé n'ouvre plus aucune boîte : le mode d'authentification permissif devient un choix explicite, jamais un défaut

**Repos**: api-mail, devops
**Dependencies**: — (aucune)
**Epic**: E016
**Single frontend**: true
**Priorité**: **0** — immédiat. Si le manifeste `DevOps/Prod` est celui qui tourne, **n'importe qui peut lire la boîte d'un praticien** avec un JWT forgé. Première action, avant tout code : vérifier la configuration du cluster réel.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-01**, contre-vérifié ligne à ligne).
> Le défaut était connu en local (mémoire « api-mail local = devPermissive, jamais de 401 ») ;
> l'audit établit qu'il **s'active aussi avec le manifeste de déploiement du dépôt**.

## Ce qui est établi (develop @ `14d58398`)

- `src/Api/Program.cs:166-196` : `devPermissive = !hasKeycloak && !builder.Environment.IsProduction()`.
  En mode permissif : `ValidateLifetime`, `ValidateIssuerSigningKey`, `RequireSignedTokens` à
  `false`, `ValidateIssuer = hasKeycloak` (donc `false`), et `SignatureValidator` rend le jeton
  parsé **sans aucune vérification**.
- `Keycloak:Authority` n'est défini **nulle part** : ni appsettings, ni AppHost, ni `DevOps/**`.
- `DevOps/Prod/configmap.yaml:10` (et `Staging`) : `ASPNETCORE_ENVIRONMENT: "Staging"` ;
  `DevOps/Prod/api.yaml:20-21` ne charge **que** ce configmap. Donc `IsProduction()` est faux et
  le mode permissif est actif avec ce manifeste.
- Défense en profondeur perdue : le blocage « Production » du bypass de test
  (`src/Api/Authentication/TestBypassAuthenticationHandler.cs:41-45`) lit la variable
  d'environnement brute, pas `IHostEnvironment` ; seule barrière restante, un `TestMode:BypassKey` vide.
- Conséquence annexe : le limiteur de débit partitionné par `sub` se contourne en changeant de `sub`.

**Scénario** : un JWT non signé (ou expiré, ou d'un autre émetteur) portant le `sub` Keycloak d'un
praticien est accepté ; le middleware résout son compte au registre puis ses boîtes ; lecture de ses
mails, patients, documents et journal d'audit.

## Objective

Qu'**aucun environnement autre que le poste du développeur** ne puisse démarrer avec une validation de
jeton désactivée, que ce mode ne s'active jamais par l'absence d'une variable, et que le déploiement
du dépôt porte une configuration d'authentification complète.

### Périmètre

1. **Constat sur le cluster réel d'abord** (humain ou `/develop` en lecture) : environnement effectif
   des pods `api-mail`, présence d'une Authority Keycloak. Résultat consigné dans le task file
   **avant** tout correctif. Si l'exposition est réelle : l'humain décide d'une mesure immédiate
   hors cycle (couper l'accès, poser l'Authority) — la forge ne touche pas au cluster.
2. **Mode permissif opt-in explicite** : actif seulement si `Environment == Development` **et** un
   drapeau de configuration dédié vaut vrai (nom retenu par `/develop`, par exemple
   `Authentication:AllowUnsignedTokensForLocalDev`). Plus aucune activation par défaut.
3. **Refus de démarrer** hors Development sans `Keycloak:Authority` : message d'erreur explicite au
   démarrage, pas de repli.
4. **Bypass de test** : sa garde « jamais en production » s'appuie sur `IHostEnvironment` et refuse
   tout environnement autre que Development/Testing explicite.
5. **Manifestes `DevOps/Prod` et `DevOps/Staging`** : ajout de `Keycloak__Authority` (et
   `Keycloak__Audience` si le jeton porte une audience dédiée) dans le configmap — **c'est la mesure
   immédiate**, applicable sans attendre le code : avec une Authority, la validation complète s'active
   même en `Staging`. `devops` est **hors automation** — la forge rédige la modification attendue dans
   le task file, **l'humain l'applique**.
   > ⚠️ **Ne PAS passer `ASPNETCORE_ENVIRONMENT` à `Production` dans le cadre de cette US** (corrigé le
   > 2026-09-27). `BaseRepository.cs:582-585` ne crée et ne migre les bases praticien **qu'en
   > `Development` ou `Staging`** : en `Production`, un nouveau praticien n'aurait pas de base et les
   > migrations ne s'appliqueraient plus. `AuditJournalSwitch` et le bypass de test lisent aussi le nom
   > d'environnement. Le nom d'environnement est donc aujourd'hui une **bascule de comportement** et non
   > une étiquette : c'est le point 7 ci-dessous.
7. **Découpler les comportements du nom d'environnement** : le provisionnement des bases praticien
   (`BaseRepository.cs:582`) devient une option de configuration explicite (activée par défaut en
   déploiement), de sorte que l'environnement puisse passer à `Production` plus tard sans rien casser.
   Le passage effectif à `Production` reste une décision humaine, **après** ce découplage.
6. Le poste local et l'AppHost continuent de fonctionner (le drapeau est posé par l'AppHost / le
   `launchSettings` de développement).

### Hors périmètre

- La vérification de signature du jeton PSC côté api-mail (audit E016 du 2026-09-16).
- La refonte du limiteur de débit (task-342 couvre la politique « sensitive »).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Constat cluster consigné** dans le task file (environnement effectif, Authority présente ou non)
- [ ] **Test rouge d'abord** : hôte d'intégration en environnement `Staging` sans Authority, requête
      avec un JWT **non signé** → sur le code actuel **200** (log du run rouge dans le task file),
      après correctif **refus** (démarrage refusé, ou 401)
- [ ] Test : environnement `Development` **sans** le drapeau → la validation complète s'applique (401 sur jeton non signé)
- [ ] Test : environnement `Development` **avec** le drapeau → comportement local actuel préservé
- [ ] Test : démarrage hors Development sans `Keycloak:Authority` → échec explicite au démarrage
- [ ] Test : le bypass de test est refusé quand `IHostEnvironment` n'est ni Development ni Testing
- [ ] Modification des manifestes `DevOps/Prod` et `DevOps/Staging` rédigée dans le task file
      (bloc prêt à appliquer : `Keycloak__Authority`, `Keycloak__Audience`) — application par l'humain ;
      `ASPNETCORE_ENVIRONMENT` **inchangé**
- [ ] Test : provisionnement des bases praticien piloté par une option explicite — actif en `Staging`
      **et** en `Production` quand l'option est vraie ; aucun comportement ne dépend plus du seul nom `Staging`
- [ ] AppHost et poste local : `dotnet run --project src/AppHost` démarre et authentifie comme avant
- [ ] Aucun jeton, `sub` ni e-mail en clair ajouté dans les logs

## Manual Test Plan

1. **Cluster** : `kubectl -n healthplatform get configmap healthplatform-configmap -o yaml` et
   `kubectl -n healthplatform exec deploy/<api-mail> -- printenv | grep -E "ASPNETCORE_ENVIRONMENT|Keycloak"`
   → consigner l'environnement effectif et l'Authority.
2. Localement, lancer l'API seule en `Staging` sans Authority :
   `cd Api/Mail && ASPNETCORE_ENVIRONMENT=Staging dotnet run --project src/Api`
   → **Attendu** : refus de démarrer avec un message explicite. Avant correctif : l'API démarre.
3. Forger un JWT non signé (`alg: none`, `sub` d'un compte de test du registre) et appeler
   `GET /api/v1/mail/folders` → **Attendu** : 401 (ou API non démarrée). Avant : 200.
4. `cd Api/Mail && dotnet run --project src/AppHost` → connexion normale depuis `client-mobile`
   (`cd Client/Mobile && npm start`) : la boîte s'ouvre comme avant.
5. Appliquer (humain) le correctif de manifeste sur l'environnement visé, redéployer, rejouer l'étape 3.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de sécurité de la plateforme
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle nouvelle ; rétablit le socle PGSSI-S d'authentification
- **INS** : non applicable — aucun trait d'identité manipulé
- **Authentification PS** : **au cœur de la US** — jeton Keycloak adossé à PSC / e-CPS, niveau eIDAS substantiel ; le mode permissif est réservé au poste du développeur
- **Habilitations** : inchangées — l'accès à une boîte reste conditionné au registre (compte × adresse)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : les refus d'authentification restent journalisés (401, sans jeton ni `sub` en clair) ; le démarrage refusé est journalisé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnements de déploiement ; la US ferme un accès non authentifié aux DSCP
- **AIPD / impact RGPD** : **à évaluer** si le constat cluster établit une exposition réelle (possible violation de données à qualifier par le DPO) ; inchangé sinon

## Constat (2026-10-13)

> **Cluster réel : NON vérifié par la forge** — aucun accès (`kubectl` sans contexte sur le poste).
> **À faire par l'humain, en premier** (Manual Test Plan, étape 1). Si le cluster tourne avec l'un des
> manifestes ci-dessous, l'exposition AUD-01 est **réelle aujourd'hui** : appliquer le bloc
> « Manifestes » sans attendre le merge, puis faire qualifier par le DPO (AIPD).

Constat sur les manifestes du dépôt (`DevOps/`) :

| Manifeste | `ASPNETCORE_ENVIRONMENT` | `Keycloak__Authority` | Bypass (`TestMode__BypassKey`) | Exposé ? |
|---|---|---|---|---|
| `DevOps/Prod/configmap.yaml` (namespace `healthplatform`) | `Staging` | absente | absente | **oui** — jeton non signé accepté |
| `DevOps/Staging/configmap.yaml` | `Staging` | absente | absente | **oui** |
| `DevOps/Weda/configmap.yaml` (namespace `weda-dev`) — **non cité par l'audit** | `Staging` | absente | absente | **oui** |

Preuve par le test (code d'avant correctif, run rouge du 2026-10-13) :
`AnUnsignedToken_OnADeployedHostWithoutAuthority_…(Staging)` → « Hôte Staging démarré sans Keycloak:Authority ;
jeton non signé → **200** ».

> ⚠️ Hors périmètre, relevé au passage : `DevOps/Prod/configmap.yaml` porte en clair des secrets
> (clé OpenAI, mot de passe d'un compte de messagerie, clé Flagsmith, chaînes PostgreSQL). `DevOps/Weda`
> les a déjà sortis dans un `Secret`. À traiter par l'humain (rotation de la clé OpenAI conseillée).

## Manifestes à appliquer (devops — humain)

> **ORDRE IMPÉRATIF : appliquer ces ConfigMaps AVANT de déployer l'image issue de cette task.**
> Le correctif fait **refuser le démarrage** d'api-mail hors Development sans `Keycloak__Authority`
> (c'est voulu). Les déploiements tirent `pcabanel/healthplatform-api-mail:develop` avec
> `imagePullPolicy: Always` : au premier redémarrage de pod après le merge, sans ces clés, les pods
> **bouclent en échec** (`CrashLoopBackOff`, message « api-mail refuse de démarrer en environnement
> 'Staging' sans Keycloak:Authority … »).
>
> Appliquer l'Authority **suffit à fermer AUD-01 dès maintenant**, même sur l'image actuelle : avec une
> Authority, la validation complète (signature, émetteur, échéance) s'active en Staging.

À ajouter dans la section `data:` de **chacun** des trois ConfigMaps (`DevOps/Prod/configmap.yaml`,
`DevOps/Staging/configmap.yaml`, `DevOps/Weda/configmap.yaml`) — `ASPNETCORE_ENVIRONMENT` **inchangé** :

```yaml
  # ============================================================================
  # AUTHENTIFICATION -> API (task-326, AUD-01)
  # ============================================================================
  # Realm Keycloak qui SIGNE les jetons que weda2 et le mobile reçoivent du proxy PSC :
  # la valeur exacte du claim « iss » d'un vrai jeton d'accès (le décoder sur jwt.io, sans
  # le coller ailleurs). api-mail y lit la découverte OIDC et les clés de signature (HTTPS).
  # Realm : weda-realm (celui du proxy PSC). En local : https://localhost:5600/realms/weda-realm
  # (lu le 2026-10-13 sur le Keycloak du poste).
  # DevOps/Weda (weda-dev) : https://keycloak.dev.k8s.office.weda.fr/realms/weda-realm — hôte lu dans
  #   psc-auth-proxy/Doc/ARCHI_Proxy_EDC_Deploiement_Keycloak_PROD.md, réseau interne : « issuer » à
  #   confirmer, et joignabilité depuis les pods à vérifier (curl de la découverte depuis le pod).
  # DevOps/Prod, DevOps/Staging : hôte à compléter.
  Keycloak__Authority: "https://<hôte du Keycloak de l'environnement>/realms/weda-realm"
  # Facultatif — seulement si les jetons portent une audience dédiée à api-mail (claim « aud »).
  # Absente, l'audience n'est pas vérifiée (signature, émetteur et échéance le sont).
  # Keycloak__Audience: "<audience>"
  # Provisionnement des bases praticien (task-326) : explicite. Actif par défaut, il ne
  # dépend plus du nom d'environnement — un passage futur à Production ne casse rien.
  MSS_DB_PROVISION_PRACTITIONER_DATABASES: "true"
```

Vérification après application (Manual Test Plan, étapes 3 et 5) : un jeton `alg: none` → **401** ; une
session réelle depuis weda2 / le mobile → la boîte s'ouvre. Si la session réelle prend aussi 401,
l'Authority ne correspond pas à l'émetteur des jetons (`iss`) ou le pod ne joint pas Keycloak en HTTPS.

## Develop log

- Repos touched : `api-mail` (branche `fix/task-326-authentification-permissive-opt-in`). `devops` : bloc rédigé
  ci-dessus (« Manifestes à appliquer »), application par l'humain.
- DTOs published : no DTO change. Interop published : no interop change.
- Commits :
  - api-mail : `94b3b422` fix(auth): un jeton non signé n'ouvre plus aucune boîte — mode permissif opt-in, refus de démarrer sans Authority
  - api-mail : `57a7c767` refactor(auth): simplify pass (/simplify)
- Ce qui change :
  - `MssAuthenticationExtensions` (nouveau, extrait de `Program`) : `ResolveUnsignedTokenMode` — Authority ⇒ validation
    complète ; hors Development sans Authority ⇒ `InvalidOperationException` au démarrage (message nommant l'environnement
    et `Keycloak__Authority`) ; Development sans Authority ⇒ permissif **seulement** avec
    `Authentication:AllowUnsignedTokensForLocalDev=true`, sinon 401.
  - `TestBypassEnvironment` (nouveau) : bypass autorisé en `Development` / `Testing` seulement, lu sur `IHostEnvironment`
    (handler **et** `RequestHelper`, qui lisaient la variable brute et ne refusaient que `Production`).
  - `PractitionerDatabaseProvisioning` (nouveau) : `MSS_DB_PROVISION_PRACTITIONER_DATABASES`, actif par défaut, coupé par
    `false` seulement ; `BaseRepository` ne lit plus `ASPNETCORE_ENVIRONMENT`.
  - Poste local : drapeau posé par l'AppHost (`ConfigureMssMailApi`, tous profils) et les 3 profils de `launchSettings.json`.
- **Run rouge (code d'avant, auth extraite à l'identique)** — `AuthenticationModeEndpointIntegrationTests`, 6 rouges / 11 :
  - `…OnADeployedHostWithoutAuthority…(Staging)` : « Hôte Staging démarré sans Keycloak:Authority ; jeton non signé → **200** »
  - `(Testing)` → 200 ; `(Production)` → 401 mais démarré
  - `AnUnsignedToken_InDevelopmentWithoutTheFlag_Is401` : attendu 401, obtenu **200**
  - `TheTestBypass_IsRefused_OutsideDevelopmentAndTesting(Staging|Production)` : attendu 401, obtenu **200**
- **Règle 1b — comportement → test d'intégration → preuve rouge** :

| Comportement | Test d'intégration (pile réelle) | Preuve rouge |
|---|---|---|
| Jeton non signé refusé hors Development sans Authority (refus de démarrer) | `AnUnsignedToken_OnADeployedHostWithoutAuthority_IsNeverAccepted_TheHostRefusesToStart` (Staging, Production, Testing — drapeau posé) | run rouge (200 en Staging) |
| Development sans drapeau : 401 | `AnUnsignedToken_InDevelopmentWithoutTheFlag_Is401` | run rouge (200) |
| Development avec drapeau : comportement local conservé | `AnUnsignedToken_InDevelopmentWithTheFlag_IsAccepted_AndItsSubjectIsRead` | — (non-régression, vert avant/après) |
| Avec Authority, jamais de détente | `AnUnsignedToken_WithAnAuthority_Is401_WhateverTheFlag` | — (non-régression) |
| Bypass refusé hors Development/Testing | `TheTestBypass_IsRefused_OutsideDevelopmentAndTesting` | run rouge (200) |
| Bypass conservé en Development/Testing | `TheTestBypass_StillAuthenticates_InDevelopmentAndTesting` (prémisse : sujet `bypass-…`) | — (non-régression) |
| Provisionnement piloté par l'interrupteur, Staging et Production | `PractitionerDatabaseProvisioningSwitchIntegrationTests` (vrai PostgreSQL, `pg_database`) | mutation M1 : règle « Development ou Staging » réinjectée → 4 rouges / 6 (Production on/absent, Staging/Development off) |

- Tests unitaires : `MssAuthenticationModeTests` (14), `UnsignedTokenFlagPlacementTests` (3 — drapeau dans l'AppHost et
  chaque profil Development, jamais dans `appsettings*.json`), `TestBypassAuthenticationHandlerTests` (garde sur
  `IHostEnvironment`, Staging/Preprod refusés, Testing accepté), `PractitionerDatabaseProvisioningTests` (7).
- Tests adaptés : `LoadTestBenchProvisioningIntegrationTests` (hôte en Development, comme le banc) ; helper
  `ProvisioningEnvironment` et `PgBouncerTransactionPoolingTests` posent l'interrupteur au lieu de `Development`. Les tests
  qui modifient l'environnement du processus ont leur collection non parallèle (`ProcessEnvironment`).
- Local build / test : ✓ api-mail — domain 190, infrastructure 690, application 3 617, api 1 220, intégration 880 (+16 ignorés),
  0 échec, aucun crash ; rejoué identique après la passe qualité.
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 2 fichiers (`57a7c767`) — S125 (« Development ; ») dans le commentaire de l'AppHost,
    attrapé par le contrôle mécanique §Q 2b ; constante de test déplacée avec les autres.
  - Skipped (contract/excluded) : devops.
- Amélioration continue : S125 → 16ᵉ occurrence ; nouvelle consigne `restauration-de-mutation` (`conventions/csharp.md`) —
  la restauration de M1 par `git checkout --` avait effacé le correctif non commité, rendu par une copie préalable.
- DOD self-check :
  - [x] build, tests ; test rouge d'abord (run consigné) ; Development sans / avec drapeau ; refus de démarrer sans Authority ;
    bypass refusé hors Development/Testing ; provisionnement par option explicite ; bloc de manifestes rédigé
    (`ASPNETCORE_ENVIRONMENT` inchangé) ; aucun log ajouté (aucun jeton, `sub` ni e-mail).
  - [ ] **Constat cluster** : non réalisable par la forge (pas d'accès) — à faire par l'humain, voir « Constat ».
  - [ ] AppHost et poste local : couverts par `UnsignedTokenFlagPlacementTests` et le test Development+drapeau ; le
    lancement réel (`dotnet run --project src/AppHost` + connexion mobile) reste au Manual Test Plan (étape 4).
- Next step : /sonar task-326

## Reprise de /develop (2026-10-13, décision humaine « go »)

Deux ajouts à la PR #291, demandés après la revue :

1. **Refus de jeton journalisés en Warning** — la section Conformité affirmait « les refus d'authentification restent
   journalisés » : c'était faux. Les journaux du handler JwtBearer (`Microsoft.AspNetCore.*`) sont filtrés sous
   `Warning` par l'override Serilog, en développement comme en déploiement. `OnAuthenticationFailed` écrit désormais
   `[Auth] Jeton refusé ({FailureType})` en Warning, catégorie `mss.mail.api.Authentication` : le type d'exception
   seulement, jamais le jeton, son `sub`, l'adresse ni le message de l'exception.
   - Test d'intégration : `ARefusedToken_IsLoggedAsAWarning_WithItsFailureType_AndNothingOfTheToken` (hôte réel,
     capture des journaux de l'hôte) — **rouge avant** (« Assert.Single() Failure: The collection did not contain any
     matching items »), vert après ; `AnAcceptedToken_LeavesNoWarning` (non-régression).
2. **Développement interactif : signature vérifiée contre le Keycloak local** — `LocalTokenValidation` (AppHost) :
   `Keycloak__Authority=https://localhost:5600/realms/weda-realm` (émetteur fixé par `KC_HOSTNAME`, certificat approuvé
   par Windows) ; mode sans vérification gardé pour e2e (jetons simulés, temps réel par `?token=`), loadtest (pas de
   Keycloak) et conteneur (`localhost` = le conteneur). `MSS_KEYCLOAK_AUTHORITY` désigne un autre realm, ou `off`
   (une valeur vide est une variable absente sous Windows). `launchSettings` : Authority locale dans les 3 profils.
   - Vérifié en manuel par l'humain sur son AppHost : session réelle → `Bearer was successfully authenticated` ;
     jeton forgé `alg: none` au bon émetteur → **401**.
   - Client Blazor : `UseOpenId: true` en local → jetons Keycloak, non impacté.
   - Tests : `LocalTokenValidationTests` (9 cas), `UnsignedTokenFlagPlacementTests` réécrit (Authority dans les profils,
     AppHost délégué à la règle, drapeau jamais dans `appsettings*.json`). Mutation M2 : exception e2e retirée → 2 rouges
     sur 9 (cas e2e), restaurée **depuis une copie** (consigne `restauration-de-mutation`).
- Contrôles mécaniques §Q 2b : vides.
- Commits : `ff64c67d` (refus journalisés), `69bb5b3e` (vérification en développement interactif), `28d75b6b` (ASPIRE010
  neutralisé, demande humaine : DCP et dashboard restent ceux des packages 13.5.3, la CLI du poste est en 13.1.0).
- Build / tests : ✓ domain 190, infrastructure 690, application 3 617, api 1 228, intégration 882 (+16 ignorés).

## Sonar log

- Mode A (chaîné), serveur SonarQube 9.9.8 (`sonar.login`), projet `healthplatform-api-mail`. 5 analyses complètes.
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 97,1 % (cible 95 %).
  - S3604 sur `TestBypassAuthenticationHandler` (`9216aa38`) ; CA1068 introduit par le refactoring S107 de
    `ImapLockScope.AcquireAsync` (`380c97f0` : l'appelant avant le jeton, surcharge adjacente sans appelant).
  - Lignes neuves non couvertes : le repli SSE `?token=` d'`MssAuthenticationExtensions` (déplacé tel quel).
- Phase 2 (dette existante) — **jouée en entier à la demande de l'humain (« fixer l'ensemble des code smells »,
  dans cette PR)** : 13 → **0**.
  - CA1829 ×4 (`81b371f9`) : `.Count` au lieu de `Count()` dans `SemanticSearchServiceTests`.
  - S107 ×9 (`77f09c1a`), sans changement de comportement :
    - constructeurs injectés : `ImapServerAccess` (ImapConnectionService), `ImapFolderStores` (ImapFolderService),
      `BackgroundImapConnectivity` (BackgroundImapService), `BackgroundSyncCoordination` (BackgroundSyncService),
      enregistrés en DI (scoped) à côté de leur service, et dans les deux hôtes de test qui les enregistrent à la main ;
    - `FlagPropagationService` : `PropagationServices` (dépendances explicites conservées, cf. son commentaire) ;
    - `SemanticSearchService.PerformSemanticSearchAsync` : reçoit `SemanticSearchOptions` ;
    - `PatientRepository.ComputeScore` : `PatientTraits` (candidat / recherché, calcul en mémoire) ;
    - `ImapLockScope.AcquireAsync` : `ImapLockCaller`.
  - 18 constructions de test réécrites par script (arguments identiques, regroupés ; arrêt sur argument nommé).
- Build / tests : ✓ après chaque lot (domain 190, infrastructure 690, application 3 617, api 1 228, intégration 882 +16
  ignorés) — totaux inchangés par les refactorings.
- `conventions/csharp.md` : S3604 → 2 ; CA1068 → 2 ; S125 → 17 (attrapé après le commit : contrôle et commit enchaînés
  dans la même commande, corrigé par `00ed3829`).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,1 % | 97,1 % | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | **0** | **−13** |
| Coverage (projet) | 97,9 % | 98,0 % | +0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- skipped — no angular change : `client-angular` absent des `**Repos**`, aucun fichier Angular écrit par `/develop`.
  L'arbre Angular porte 13 entrée(s) de travail non commité **antérieur** (task-340 : accusé de lecture et
  `_form-control.scss`, en attente de commit TFS par l'humain) — non lintées, hors périmètre (règle 6).

## Lint mobile log

- skipped — no mobile change : `client-mobile` absent des `**Repos**`, arbre propre sur `develop`.

## E2E log

Passe finale (après la reprise : refus journalisés, vérification en développement, 13 code smells corrigés).

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 34 verts, 0 flaky, 0 rouge | 6 min 18 s |
| angular | api-mail touché | ✅ verte | 38 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, humain) | 5 min 24 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-326-authentification-permissive-opt-in` (inchangé par la task).
- Ce que la passe prouve en plus des tests : le profil e2e garde le mode sans vérification (`LocalTokenValidation`) ;
  l'API réelle démarre avec les quatre regroupements S107 résolus par la DI de production ; les parcours IMAP,
  synchronisation, recherche, accusés de lecture et temps réel passent après le refactoring.
- Rapports copiés dans la même commande que leur voie (consigne `agents/e2e.md`, respectée cette fois).
- Parcours touchés sans spec e2e modifié : aucun (aucun écran modifié).
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).

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
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
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
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
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
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Branches
- `api-mail` (pushed) : fix/task-326-authentification-permissive-opt-in — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-326-authentification-permissive-opt-in
- `dtos-mss` (paresseuse) : aucune branche créée par `/start` — `/develop` la crée seulement s'il touche un contrat
- `devops` (manual) : managed manually by the human — la forge rédige dans ce task file le bloc de configmap `DevOps/Prod` et `DevOps/Staging` (`Keycloak__Authority`, `Keycloak__Audience`), l'humain l'applique

## Timings

*(généré par `tools/timing/report.sh --task task-326 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 8 min 17 s | 8 (1 min 00 s) | 9 (11 min 41 s) | — | api-mail 8B/9T |
| /sonar | ok | 41 min 33 s | 7 (1 min 33 s) | 28 (36 min 50 s) | 10 (3 min 05 s) | 3 itération(s), api-mail 7B/28T |
| /lint-angular | skipped | 9.1 s | — | — | — | client-angular non touché (WIP task-340 non commité, hors périmètre) |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 12 min 22 s | — | — | — | e2e ×9 (30 min 41 s) |
| /review | ok | 7 min 06 s | 2 (17 s) | 2 (7 min 07 s) | — | api-mail 2B/2T |
| /tech-writer | ok | 0.4 s | — | — | — | — |
| **Total cycle** | | **1 h 09 min** | **17 (2 min 50 s)** | **39 (55 min 38 s)** | **10 (3 min 05 s)** | |

## PRs

- api-mail : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/291 [awaiting-human-merge]
- devops : managed manually by the human — appliquer le bloc « Manifestes à appliquer » (Prod, Staging, **Weda**) **avant**
  de déployer l'image issue de la PR (sinon refus de démarrer, voulu).
- client-angular : non touché par la task (le WIP non commité de task-340 reste à commiter sur TFS).

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 2 suggestions. Deux revues : la première sur le correctif (`9216aa38`), la seconde sur
la reprise demandée par l'humain (`9216aa38..380c97f0` : refus journalisés, vérification en développement, ASPIRE010,
13 code smells). Validation finale : build + tests verts (domain 190, infrastructure 690, application 3 617, api 1 228,
intégration 882 + 16 ignorés, hors flaky ci-dessous), branche à jour avec `origin/develop`, arbre propre.

- `MssAuthenticationExtensions` ✅ — décision au démarrage ; `OnAuthenticationFailed` → Warning sous
  `mss.mail.api.Authentication`, type d'exception seulement.
- `TestBypassEnvironment`, handler, `RequestHelper` ✅ — même garde des deux côtés, sur `IHostEnvironment`.
- `PractitionerDatabaseProvisioning`, `BaseRepository` ✅ — actif par défaut, indépendant du nom d'environnement.
- `LocalTokenValidation` (AppHost), `launchSettings` ✅ — Authority locale en développement interactif ; e2e, loadtest,
  conteneur sans vérification ; vérifié à la main par l'humain (session réelle acceptée, jeton forgé → 401).
- Regroupements S107 ✅ — mêmes champs réaffectés, groupes `scoped` comme leurs services, enregistrés en DI de production
  et dans les deux hôtes de test manuels ; DI réelle prouvée par les voies e2e.
- `ImapLockScope` ✅ — surcharge sans appelant adjacente, déléguant à la version complète (CA1068, S4136).
- Règle 1b : tableau comportement → test → preuve rouge au `## Develop log` et dans la PR.

Suggestions (non bloquantes) :
1. Le repli SSE `?token=` (déplacé tel quel) n'a pas de test d'intégration.
2. L'environnement `Testing` ouvre le test-bypass : aucun manifeste ne doit l'utiliser.

**Flaky préexistant** (non lié) : `SeededThreadsAreCountableTests.AnUnthreadedCorpusProducesNoCountableThread` — UID tirés au
hasard (300 000 valeurs) pour 60 à 120 messages d'un même dossier sous contrainte d'unicité → collision 23505 occasionnelle.
Rouge 1 fois sur la validation finale, vert 10/10 au rejeu. Task à ouvrir : UID séquentiels.

Relevé hors périmètre : `DevOps/Prod/configmap.yaml` porte des secrets en clair (clé OpenAI notamment).

## Merged

- **Date** : 2026-10-13, `/merge task-326 --i-tested` (validation humaine attestée).
- api-mail : squash `f271b044` (PR #291) — CI develop : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38458418470 ✓
- Branche `fix/task-326-authentification-permissive-opt-in` supprimée (distante et locale) ; label `awaiting-human-merge` retiré.
- devops : managed manually by the human — `Keycloak__Authority` à poser dans les ConfigMaps Prod, Staging et Weda **avant** tout redémarrage de pod sur l'image `develop` (refus de démarrer sinon).
- client-angular : non touché par la task.
