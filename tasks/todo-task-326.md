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
