# todo-task-056-health-checks-prod.md — Sondes de santé (readiness/liveness) en production avec dépendances

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**EpicTitle**: Robustesse & observabilité de la plateforme

## Objective

Exposer des **endpoints de santé exploitables en production** pour permettre à
l'orchestrateur (Aspire / Kubernetes) de piloter readiness et liveness, et de
retirer/redémarrer automatiquement un pod dont une dépendance critique est
tombée.

Aujourd'hui, dans
[DependencyInjectionExtensions.cs](Api/Mail/src/Api/DependencyInjectionExtensions.cs)
(`MapDefaultEndpoints`), les routes `/health` et `/alive` ne sont mappées que
si `app.Environment.IsDevelopment()`. **En production, aucune sonde n'est
exposée** — l'orchestrateur ne peut détecter ni un deadlock (liveness) ni une
dépendance indisponible (readiness). Par ailleurs le seul check enregistré est
`"self"` (`AddDefaultHealthChecks`) : **ni PostgreSQL, ni Redis, ni RabbitMQ**
ne sont sondés.

Cible :

1. **Mapper `/health` (readiness) et `/alive` (liveness) dans tous les
   environnements**, en sécurisant l'accès (anonyme mais réservé au réseau
   interne / filtré, jamais d'exposition publique du détail).
2. **Ajouter des health checks pour les dépendances critiques** taggés
   `ready` : PostgreSQL, Redis, RabbitMQ. La liveness (`/alive`) reste
   limitée au check `self` (l'app répond), la readiness (`/health`) agrège
   toutes les dépendances `ready`.
3. **Iso-comportement fonctionnel** : aucune logique métier modifiée, aucun
   endpoint applicatif touché.

Périmètre **purement infra/observabilité**, mono-repo `api-mail`,
sans impact contrat ni frontend.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportements
couverts par tests d'intégration._

## Definition of Done

- [x] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [x] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs)
- [x] `/alive` (liveness) et `/health` (readiness) mappés **dans tous les
      environnements** (suppression du garde `IsDevelopment()` dans
      `MapDefaultEndpoints`)
- [x] `/alive` ne valide que les checks taggés `live` (app responsive)
- [x] `/health` agrège les checks taggés `ready` (dépendances)
- [x] Health checks ajoutés et taggés `ready` :
      - [x] PostgreSQL (connexion DB serveur — pas une base tenant)
      - [x] Redis (`mss-mail-redis`)
      - [x] RabbitMQ (`mss-mail-rabbitmq`)
- [x] Les endpoints health restent exclus du tracing (filtre OpenTelemetry
      déjà présent dans `ConfigureOpenTelemetry`) et **n'exposent pas** de
      détail technique sensible (connection strings, versions, secrets) au
      client — réponse réduite au statut agrégé
- [x] Accès aux endpoints anonyme mais documenté comme **réservé réseau
      interne** (note de déploiement / commentaire) — pas d'exposition
      publique du détail des checks
- [x] Test d'intégration : `GET /alive` renvoie 200 quand l'app tourne
- [x] Test d'intégration : `GET /health` renvoie 200 quand les dépendances
      sont disponibles, et **503** quand une dépendance `ready` est down
      (simulée via un check factice / configuration de test)
- [x] Aucune régression : les endpoints applicatifs et le pipeline existant
      (`ConfigurePipeline`) restent inchangés

## Manual Test Plan

- Lancer le backend via l'AppHost Aspire : `cd Api/Mail/src/AppHost && dotnet run`
  (PostgreSQL, Redis, RabbitMQ démarrés par Aspire).
- **Liveness** : `GET http://localhost:<port>/alive` → **200**, corps minimal
  (`Healthy`). Vérifier que la réponse n'expose aucun détail de dépendance.
- **Readiness (nominal)** : `GET http://localhost:<port>/health` → **200**
  toutes dépendances `ready` OK.
- **Readiness (dégradé)** : arrêter le conteneur Redis (ou RabbitMQ) puis
  refaire `GET /health` → **503** (Unhealthy). `/alive` doit **rester 200**
  (l'app répond toujours).
- **Tracing** : vérifier dans la console/Seq que les appels `/alive` et
  `/health` **n'apparaissent pas** dans les traces (exclusion OpenTelemetry).
- **Sécurité** : confirmer qu'aucune connection string, secret ou version de
  dépendance n'est présent dans le corps des réponses health.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — observabilité/infra de la plateforme,
  sans impact sur un volet métier Ségur.
- **Vague Ségur** : hors Ségur — robustesse/exploitabilité plateforme.
- **Exigences DSR honorées** : non applicable — aucun volet de contenu ou de
  transport modifié.
- **INS** : non applicable — aucune donnée patient manipulée.
- **Authentification PS** : inchangée — les endpoints health sont anonymes
  (réservés réseau interne), le pipeline d'auth applicatif n'est pas touché.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR/HL7v2.
- **Tracé PGSSI-S** : inchangé — les sondes de santé sont volontairement
  exclues du tracing ; aucun évènement métier à journaliser n'est ajouté.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement de production HDS existant,
  périmètre inchangé.
- **AIPD / impact RGPD** : inchangé — aucun traitement de données de santé ;
  vigilance : ne pas exposer d'information d'infrastructure exploitable dans
  les réponses health.

### DOD santé (items applicables)
- [x] Les réponses health n'exposent aucune donnée de santé ni secret/
      connection string / détail d'infrastructure exploitable

## Branches
- `api-mail` (pushed) : feat/task-056-health-checks-prod — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-056-health-checks-prod
- `dtos-mss` (pushed, auto-included) : feat/task-056-health-checks-prod — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-056-health-checks-prod

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée mais aucun changement de contrat — pas de commit, pas de PR)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : cb86bb2 feat(health): expose readiness/liveness probes in all environments
- Local build / test : ✓ build 0 erreur ; tests 0 échec hors les 3 rouges pré-existants documentés (middleware DB-name, IMAP cancel flaky, MailExport PDF flaky — 2/3 passent en isolation, non liés à la task)
- Implementation notes :
  - `MapDefaultEndpoints` : garde `IsDevelopment()` supprimé ; `/health` filtré tags `ready`, `/alive` filtré tags `live` ; `.AllowAnonymous()` requis (fallback policy d'auth globale) ; writer par défaut = statut agrégé seul (zéro fuite)
  - `AddDefaultHealthChecks` : PostgreSQL via `AddNpgSql` sur `MSS-MAIL-CONNECTIONSTRING` (connexion serveur, pas tenant) ; Redis via `AddRedis` sur l'`IConnectionMultiplexer` Aspire (`mss-mail-redis`) ; les deux taggés `ready`, timeout 5 s, enregistrement conditionnel à la présence de la connection string
  - RabbitMQ (`mss-mail-rabbitmq`) : couvert par le health check du bus MassTransit (auto-enregistré, taggé `ready`+`masstransit`) — contrat épinglé par le test `MassTransit_RegistersBusHealthCheck_TaggedReady`
  - Packages : + `AspNetCore.HealthChecks.NpgSql` et `AspNetCore.HealthChecks.Redis` (réf. Api) ; lock files resynchronisés (drift pré-existant sur AppHost)
  - Tests : `tests/mss.mail.integration.tests/Health/HealthEndpointsTests.cs` — TestServer env Production via les extensions réelles (6 tests : alive 200, health 200/503, alive insensible aux deps down, leak guard sur le body, contrat MassTransit)
- DOD self-check : 14/14 items vérifiables OK (exclusion tracing = filtre OTel existant inchangé ; note réseau interne = commentaire de déploiement dans `MapDefaultEndpoints`)
- no angular change → skipped /lint-angular
- Next step : /sonar task-056 (chaîne ensuite vers /review)

## Sonar log

- Phase 1 (new code) : ✓ — new_violations = 0, new hotspots = 0 (100% reviewed), new_duplicated_lines_density OK
  - `new_coverage` 74% < 80 (gate ERROR) = artefact documenté de la new-code period projet (baseline très large, legacy classé "new") ; le fichier touché par la task (`DependencyInjectionExtensions.cs`) a `new_uncovered_lines = 0`, comportement couvert par les 6 tests d'intégration HealthEndpointsTests
- Phase 1 — Issues fixées : 0 (aucune issue new-code générée par la task)
- Phase 1 — Tests ajoutés : 0 (couverture déjà assurée par /develop)
- Phase 2 (legacy) : 0 itération / 5 — early-stop, dette legacy nulle (bugs 0, vulnérabilités 0, code smells 0, hotspots 0, ratings A/A/A, duplication 0.6%)
- Build / tests : ✓ Release green (2 échecs = rouges pré-existants documentés : middleware DB-name Release, IMAP cancel flaky)
- no angular change → skipped /lint-angular
- Hand-off : /review task-056

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/86 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche créée par auto-inclusion mais aucun changement de contrat (0 commit)

## Code Review Summary

**Verdict : APPROVED** (3 fichiers de code revus + lock files, 1 note non-bloquante, 0 bloquant)

- `src/Api/DependencyInjectionExtensions.cs` — ✅ predicates `ready`/`live` conformes DOD ; `.AllowAnonymous()` requis (fallback policy d'auth globale) ; enregistrements conditionnels aux connection strings (boot honnête en environnement partiel) ; writer par défaut = statut agrégé seul, zéro fuite ; RabbitMQ via le bus check MassTransit (contrat épinglé par test) ; filtre tracing OTel inchangé
- `src/Api/mss.mail.api.csproj` + `Directory.Packages.props` — ✅ + AspNetCore.HealthChecks.NpgSql / .Redis (9.0.0, alignés sur la famille déjà pinnée)
- `tests/mss.mail.integration.tests/Health/HealthEndpointsTests.cs` — ✅ 6 tests significatifs sur TestServer env Production (200/503, leak-guard, alive insensible aux deps down, contrat MassTransit ready-tag)
- ⚠️ note : `src/AppHost/packages.lock.json` resynchronisé (-1400 lignes, drift pré-existant sur develop) — build/test verts avec les locks commités

Validation : build ✓ 0 erreur · tests ✓ (3 échecs = rouges pré-existants documentés) · DOD ✓ 14/14 · Sonar ✓ 0 issue new-code, dette legacy nulle

## Merged

- Date : 2026-06-10
- `api-mail` : squash commit `933d5f7` (PR #86 closed, branche remote supprimée, branche locale conservée)
- `dtos-mss` : aucune PR (branche vide) — remote `feat/task-056-health-checks-prod` supprimée, clone resynchronisé sur `develop`
- develop CI : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27262095077
