# todo-task-038.md — Fix TLS validation manquante dans `mss-imap-test`

**Repos**: api-mail
**Dependencies**: archived-task-037
**Epic**: E009

## Objectif

L'endpoint `POST /api/v1/account/mss-imap-test` introduit par task-037
échoue en déploiement avec :

```
MailKit.Security.SslHandshakeException: An error occurred while attempting
to establish an SSL or TLS connection.
• The root certificate has the following errors:
  • unable to get local issuer certificate
```

Le serveur visé (`medecin.formation.mssante.fr`, IMAP IGC-Santé) présente
un certificat signé par l'**IGC-Santé**, dont la racine n'est pas dans le
trust store par défaut des images .NET Linux.

**Cause racine** :
[`MssAccountOnboardingService.TestImapConnectionAsync`](../Api/Mail/src/Application/Services/Implementation/MssAccountOnboardingService.cs#L26)
crée un client IMAP via `IImapClientWrapperFactory.Create()` puis appelle
`ConnectAsync` **sans installer de `ServerCertificateValidationCallback`**.
MailKit retombe sur la validation OS qui rejette la chaîne IGC-Santé.

Le chemin nominal
[`ImapConnectionService.ConnectInternalAsync`](../Api/Mail/src/Application/Services/Implementation/ImapConnectionService.cs#L57)
fait correctement le travail via sa méthode privée
[`ConfigureImapClientWrapper`](../Api/Mail/src/Application/Services/Implementation/ImapConnectionService.cs#L270),
qui délègue à [`CertificateValidator.ValidateAsync`](../Api/Mail/src/Application/Helpers/CertificateValidator.cs#L17)
(vérifie `IssuerName contains "IGC-SANTE"` + OCSP/CRL).

Cette task corrige le bug de cohérence en extrayant la configuration TLS
dans un helper partagé que les deux services consomment.

## Scope

### `api-mail` (backend, .NET 10)

- **Nouveau helper** :
  `Application/Helpers/ImapClientTlsConfigurer.cs`
  - Classe `sealed` injectée via DI (scoped).
  - Méthode `Configure(IImapClientWrapper client, ServerConfig config, string emailForLogs)` :
    - `client.SslProtocols = SslProtocols.Tls12`
    - Installe `ServerCertificateValidationCallback` avec la même
      logique que `ImapConnectionService.ConfigureImapClientWrapper` :
      1. `cert is null` → `false`
      2. `!opts.ValidateCertificate || !config.ValidateServerCertificate` → `true` (warn log)
      3. `opts.AllowUntrustedCertificates && errors != None` → `true` (warn log)
      4. `errors == None` → `true`
      5. sinon : `cert is X509Certificate2 c2 && certificateValidator.ValidateAsync(c2).GetAwaiter().GetResult().IsSuccess`
  - Dépendances : `CertificateValidator`, `IOptions<SslTlsOptions>`, `ILogger<ImapClientTlsConfigurer>`.

- **`ImapConnectionService`** :
  - Injecter `ImapClientTlsConfigurer` à la place du couple
    `CertificateValidator` + `IOptions<SslTlsOptions>` (qui devient
    transitif).
  - Remplacer l'appel `ConfigureImapClientWrapper(imapClient, serverConfig)`
    par `_tlsConfigurer.Configure(imapClient, serverConfig, userContextInfo.Email)`.
  - Supprimer les méthodes privées `ConfigureImapClientWrapper` et
    `ValidateCertificate` (déplacées dans le helper).

- **`MssAccountOnboardingService`** :
  - Injecter `ImapClientTlsConfigurer` (en plus du factory).
  - **Avant `ConnectAsync`** : appeler
    `_tlsConfigurer.Configure(imapClient, serverConfig, email)`.

- **DI** :
  - Enregistrer `ImapClientTlsConfigurer` (scoped) dans
    `ServiceImplementation.cs` ou le module DI applicatif équivalent.

### Tests (`tests/mss.mail.application.tests`)

- **Nouveau** `Helpers/ImapClientTlsConfigurerTests.cs` :
  - `Configure_Sets_Tls12_Protocol`
  - `Configure_Installs_Callback`
  - Callback : `Returns_True_When_ValidateCertificate_Disabled`
  - Callback : `Returns_True_When_AllowUntrusted_And_Errors_Present`
  - Callback : `Returns_True_When_No_Errors`
  - Callback : `Returns_True_When_CertificateValidator_Succeeds`
  - Callback : `Returns_False_When_CertificateValidator_Fails`
  - Callback : `Returns_False_When_Certificate_Is_Null`

- **`Services/Imap/MssAccountOnboardingServiceTests.cs`** :
  - Nouveau test : `TestImapConnectionAsync_Configures_Tls_Before_Connect`
    (vérifie via NSubstitute `Received.InOrder` que
    `_tlsConfigurer.Configure(...)` est appelé **avant**
    `imapClient.ConnectAsync(...)`).
  - Adapter les tests existants pour injecter le mock du configurer.

- **`Services/Imap/ImapConnectionServiceTests.cs`** (s'il existe) :
  - Adapter pour le nouveau ctor (mock `ImapClientTlsConfigurer`).
  - Vérifier que `Configure` est appelé avant `ConnectAsync`.

## Scope OUT

- Pas de modification du `Dockerfile` pour installer la racine IGC-Santé
  côté trust store OS. Le code applicatif fait déjà la validation
  custom, suffisant.
- Pas de modification de `CertificateValidator` (OCSP/CRL inchangé).
- Pas d'ajout d'options de configuration nouvelles.
- Pas de refactor du `Task.Run(...).GetAwaiter().GetResult()` du
  callback synchrone (anti-pattern connu mais hors scope ; à traiter
  dans une task dédiée si besoin).

## Definition of Done

- [ ] Build `api-mail` vert (0 erreur)
- [ ] Tests `mss.mail.application.tests` verts (0 failure)
- [ ] `ImapClientTlsConfigurer` enregistré dans la DI
- [ ] `MssAccountOnboardingService` appelle `Configure` **avant**
  `ConnectAsync` (vérifié par test `Received.InOrder`)
- [ ] `ImapConnectionService` consomme le helper (n'a plus de méthode
  `ConfigureImapClientWrapper` privée)
- [ ] Coverage du helper > 0 (tous les branches du callback testés)
- [ ] Sonar best-effort 5 itérations
- [ ] PR ouverte avec label `awaiting-human-merge`

## Manual Test Plan

> Validation **obligatoire en déploiement** (le bug ne se reproduit pas
> en local Windows car le trust store OS ≠ image Linux).

1. Déployer la branche `feat/task-038-fix-mss-imap-test-tls` sur l'env
   de dev (`https://weda2-archi.dev.k8s.office.weda.fr/` ou équivalent).
2. Se connecter avec un compte Keycloak **sans claim `mssEmail`** (cas
   task-037).
3. Naviguer sur `/mss` → écran `MssUnconfigured` (du fait de task-037).
4. Cliquer "Configurer mon compte" → `/mss/setup`.
5. Saisir l'email `virginie.medecinrpps0062267@medecin.formation.mssante.fr`
   + un RPPS valide.
6. Cliquer "Valider".

**Attendu** :
- L'appel `POST /api/v1/account/mss-imap-test` renvoie **`200 { ok: true }`**
  (ou un code métier explicite `AUTH_FAILED` / `MAILBOX_NOT_FOUND` si
  les creds sont mauvais, **PAS** une erreur 500 TLS).
- Logs api-mail : présence d'une trace
  `[ConfigureImapClientWrapper]` ou `[ImapClientTlsConfigurer] …` puis
  `[Validate] IGC Santé certificate issuerName=…`.
- **Absence** de `SslHandshakeException` dans les logs.
- Étape B (PUT `mss-profile`) s'enchaîne, étape C s'affiche.

**Régression à vérifier** : connexion IMAP "normale" via
`ImapConnectionService` (utilisateur avec `mssEmail` déjà configuré, qui
ouvre sa messagerie) — doit continuer à fonctionner sans aucune
différence (même validation TLS, mêmes logs).

## Branches

- `api-mail` (pushed) : `feat/task-038-fix-mss-imap-test-tls` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-038-fix-mss-imap-test-tls
- `dtos-mss` (pushed, auto-included per CLAUDE.md) : `feat/task-038-fix-mss-imap-test-tls` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-038-fix-mss-imap-test-tls

**Notes de pré-flight** :
- `Api/Mail/src/AppHost/packages.lock.json` était dirty au moment de `/start` (artefact stale d'un restore précédent) — stash automatique appliqué : `git -C Api/Mail stash list` exposera l'entrée `auto-stash before /start task-038 — stale packages.lock.json`. Récupérable via `git stash pop` si besoin ; sera de toute façon régénéré par `dotnet restore --force-evaluate` dans `/develop`.
- `Host/Modules` n'existe pas comme git repo sur disque (drift CLAUDE.md). Hors scope task-038.
- `interop-cda` vit en `interop/`, pas `interop/interop.cda.parser/` comme indiqué dans CLAUDE.md. Hors scope task-038.

## Develop log

- **Repos touchés** : api-mail (commits + push). dtos-mss : branche créée mais 0 commit (pas de changement de contrat DTO).
- **DTOs publiés** : aucun (pas de modification dans Dtos/).
- **Interop publié** : aucun (pas de modification dans interop/).
- **Commits sur api-mail** :
  - `f31976e` — feat(mss): extract ImapClientTlsConfigurer for shared IMAP TLS setup
  - `884d575` — test(mss): cover ImapClientTlsConfigurer + Configure-before-Connect ordering
- **Fichiers créés** :
  - `src/Application/Helpers/IImapClientTlsConfigurer.cs` (interface)
  - `src/Application/Helpers/ImapClientTlsConfigurer.cs` (sealed impl)
  - `tests/mss.mail.application.tests/Helpers/ImapClientTlsConfigurerTests.cs` (8 tests)
- **Fichiers modifiés** :
  - `src/Application/Helpers/CertificateValidator.cs` (1-mot : `ValidateAsync` marqué `virtual` pour permettre NSubstitute — OCSP/CRL inchangé, respecte scope OUT)
  - `src/Application/Services/Implementation/ImapConnectionService.cs` (consomme `IImapClientTlsConfigurer`, méthodes privées `ConfigureImapClientWrapper`/`ValidateCertificate` supprimées)
  - `src/Application/Services/Implementation/MssAccountOnboardingService.cs` (injecte `IImapClientTlsConfigurer`, appelle `Configure(...)` AVANT `ConnectAsync`)
  - `src/Application/Extensions/ServiceCollectionExtensions.cs` (DI : `services.AddScoped<IImapClientTlsConfigurer, ImapClientTlsConfigurer>()`)
  - `tests/mss.mail.application.tests/Services/Imap/MssAccountOnboardingServiceTests.cs` (adapte ctor + ajoute `TestImapConnectionAsync_Configures_Tls_Before_Connect` via `Received.InOrder`)
- **Décision de conception** : extraction de `IImapClientTlsConfigurer` (la spec dit `sealed` ET "mock ImapClientTlsConfigurer" — impossible sur sealed sans interface) ; helper reste `sealed`, DI via abstraction.
- **Local build / test** : ✓ api-mail solution build vert (0 erreur, 0 warning). Tests : 1356/1356 application + 86/86 domain + 112/112 api + 346/346 infra + 132/132 integration (16 skipped AI tests).
- **Flake constaté** : `MarkdownPdfRendererTests.RenderHeadingPreservesText` a failed une fois sur deux runs (erreur font `/F5` resource store, UglyToad.PdfPig), puis passé en isolation et en re-run. Pré-existant, ordre-dépendant, **aucun rapport avec task-038**. Documenté ici pour traçabilité ; à traiter dans une task dédiée si la flakiness persiste en CI.
- **DOD self-check** (best-effort par commande) :
  - [✓] Build api-mail vert (0 erreur)
  - [✓] Tests application verts sur les ajouts de cette task (1356 passés, le flake PDF est pré-existant et hors scope)
  - [✓] `ImapClientTlsConfigurer` enregistré dans la DI
  - [✓] `MssAccountOnboardingService` appelle `Configure` avant `ConnectAsync` (vérifié par test `Received.InOrder`)
  - [✓] `ImapConnectionService` consomme le helper (méthode `ConfigureImapClientWrapper` privée supprimée)
  - [✓] Coverage du helper > 0 (8 tests sur toutes les branches du callback)
  - [⏳] Sonar best-effort 5 itérations (étape suivante)
  - [⏳] PR ouverte avec label `awaiting-human-merge` (étape `/review`)
- **Next step** : `/sonar task-038` (api-mail touché, client-angular non touché → chaîne vers `/review` directement, skip clean de `/lint-angular`).

## Sonar log

- **Mode** : A (chained from /develop)
- **Analyses** : 2 runs (initial + re-analyse après ajout test coverage)
- **Branche** : feat/task-038-fix-mss-imap-test-tls
- **Commits Sonar** :
  - `b41725d` — test(mss): cover generic exception branch in MssAccountOnboardingService (pousse coverage MssAccountOnboardingService de 94.1% à 98.5%)

### Phase 1 — new code (MANDATORY, scope task-038)

✓ **Verte sur le périmètre task-038**

- 0 new bugs, 0 new vulnerabilities sur mes fichiers
- 0 new code smells sur mes fichiers (Sonar a analysé `ImapClientTlsConfigurer.cs`, `IImapClientTlsConfigurer.cs`, refactors `ImapConnectionService.cs` + `MssAccountOnboardingService.cs`)
- 0 new security hotspots sur mes fichiers
- new_coverage par fichier task-038 :
  - `ImapClientTlsConfigurer.cs` : **95.7%** (cible 95% — atteinte)
  - `MssAccountOnboardingService.cs` : **98.5%** (cible 95% — atteinte, ajout test catch(Exception))
  - `ImapConnectionService.cs` : **100% sur les lignes nouvelles** (refactor couvert par tests existants)

### Quality Gate global — ERROR (non-bloquant pour task-038)

- `new_coverage` = 74.7% (seuil 80%) — gap dû aux 182 violations new-code héritées des tasks précédentes
- `new_violations` = 182 (seuil 0) — répartition top 5 :
  - MailRepository.cs : 52
  - PatientRepository.cs : 33
  - Infrastructure.Mock/MailRepository.cs : 8
  - ImapService.cs : 7
  - ImapLockScopeTests.cs : 6
- `new_duplicated_lines_density` = 0.99% ✓ (seuil 3%)

### Phase 2 — legacy debt : skipped intentionnellement

Justification :
- Le "new code period" est configuré sur `PREVIOUS_VERSION` (2026-04-27, ~18 jours de cumul) ; les 182 findings new-code sont des héritages des tasks 018-037, pas du code task-038.
- Fixer cette dette sur la branche `feat/task-038-fix-mss-imap-test-tls` créerait du cross-pollination (changements TLS + cleanup legacy MailRepository dans la même PR) — violation de la règle "1 task = 1 concern".
- Le cleanup legacy reste l'objet des tasks dédiées (`/sonar-s3776` pour la cognitive complexity, ou des chore tasks Sonar ciblées).
- Best-effort acceptance per spec : "Cette phase peut être entièrement skipped si la baseline est déjà bonne **du point de vue de la task**" — c'est le cas ici (ma part = 0 finding).

### Hand-off

Next step : `/review task-038` (skip clean de `/lint-angular` car client-angular non touché par task-038).

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/60 — label `awaiting-human-merge`
- **dtos-mss** : pas de PR (0 commit ; la branche `feat/task-038-fix-mss-imap-test-tls` existe sur origin mais reste vide — supprimable si désiré)

## Code Review Summary

**APPROVED** — 8 fichiers reviewés, 0 issue bloquante.

- `Helpers/ImapClientTlsConfigurer.cs` (new, 74 lignes) — ✅ logic 1:1 avec l'original ; `Task.Run().GetAwaiter().GetResult()` reconnu anti-pattern mais hors scope task-038
- `Helpers/IImapClientTlsConfigurer.cs` (new, 9 lignes) — ✅ interface minimale
- `Helpers/CertificateValidator.cs` (+`virtual` sur `ValidateAsync`) — ✅ 1 mot, OCSP/CRL inchangé
- `Services/Implementation/ImapConnectionService.cs` — ✅ méthodes privées proprement retirées
- `Services/Implementation/MssAccountOnboardingService.cs` — ✅ `Configure(...)` AVANT `ConnectAsync` (le fix)
- `Extensions/ServiceCollectionExtensions.cs` (+1 ligne DI) — ✅
- `tests/.../Helpers/ImapClientTlsConfigurerTests.cs` (new, 197 lignes) — ✅ 8 tests, toutes les branches
- `tests/.../Services/Imap/MssAccountOnboardingServiceTests.cs` (+41 lignes) — ✅ ordering + catch générique

**Suggestions non-bloquantes** : déférer `Task.Run().GetAwaiter().GetResult()` à une task dédiée.

**Flake pré-existant signalé** : `MarkdownPdfRendererTests.RenderHeadingPreservesText` (font `/F5` UglyToad.PdfPig) — non déterministe, passe en isolation, existant sur `develop`, sans rapport avec task-038. À traiter en task dédiée.

## Merged

- **Timestamp** : 2026-05-15 23:42 +0200
- **Validation HAG** : humain a confirmé avoir testé en déploiement Linux (env weda2-archi dev k8s) avec un compte Keycloak sans `mssEmail` — `POST /api/v1/account/mss-imap-test` ne jette plus `SslHandshakeException`. Attestation : `/merge task-038 --i-tested` (typos d'invocation : `tasl-038 -i--tested`, intent clair).
- **Squash merge** :
  - api-mail : `4b33086` (PR #60 closed, https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/60) — merge commit "fix(mss): IMAP TLS callback missing on mss-imap-test probe (task-038) (#60)"
- **dtos-mss** : pas de merge (0 commit sur la branche). La branche `origin/feat/task-038-fix-mss-imap-test-tls` peut être supprimée manuellement si désiré.
- **develop CI** : ✓ green (workflow "Build and Publish", run @17:19:24Z UTC, conclusion=success)
- **Local feature branch** : ⚠️ **supprimée** par `gh pr merge --delete-branch` (la flag supprime local ET remote, contrairement à la note mémoire pré-existante). Pour récupérer si besoin : `git -C Api/Mail branch feat/task-038-fix-mss-imap-test-tls b41725d` (SHA pré-squash du reflog, contient les 3 commits originaux non-squashés).
- **Stash auto-/start** : `git -C Api/Mail stash list` expose toujours l'entrée `auto-stash before /start task-038 — stale packages.lock.json` (artefact `src/AppHost/packages.lock.json` régénéré par dotnet restore — peut être `git stash drop` en toute sécurité).
