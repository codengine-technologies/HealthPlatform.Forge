# todo-task-032ter-greenmail-fixture.md — Mock IMAP server (GreenMail Testcontainers)

**Repos**: api-mail
**Dependencies**: done-task-032bis-fhir-mock (à merger d'abord pour bénéficier du harness FHIR)
**Epic**: E009

> **Mode recommandé** : `/start task-032ter no-code` — l'humain implémente en WindSurf. La US demande une décision structurante (extraction d'interface `IMailClientSessionManager` ou Testcontainers GreenMail Docker) hors zone de confort de `/develop` autonome.

## Objectif

Stand-up un harness de test pour la couche IMAP, afin de retirer 4 `[ExcludeFromCodeCoverage]` posés à task-032 :
- `application.Services.Implementation.ImapService` (1 916 LOC)
- `application.Services.Implementation.BackgroundImapService` (584 LOC)
- `application.Services.Implementation.ImapFolderService` (614 LOC)
- `application.Services.Implementation.ImapConnectionService` (312 LOC)

→ Total potentiel : **~3 426 LOC** réintégrées au dénominateur de couverture.

US **technique / dette / outillage qualité** — aucun nouveau comportement métier.

## Périmètre — 2 approches à arbitrer

### Approche A — Refactor `IMailClientSessionManager` + mocks NSubstitute

1. Extraire une interface `IMailClientSessionManager` depuis la classe concrète actuelle (~30 LOC + remap DI dans `ServiceCollectionExtensions`).
2. Remplacer les injections `MailClientSessionManager` → `IMailClientSessionManager` dans les 4 services IMAP + leurs callers.
3. Tests : mock `IMailClientSessionManager` + `IImapClientWrapper` (déjà une interface) via NSubstitute. Pas de container Docker.
4. Couverture obtenue : tous les paths logiques des 4 services IMAP (sans IMAP réel).

**Avantages** : pas de dépendance Docker, tests rapides en CI, pattern cohérent avec le reste du codebase (interfaces + mocks).
**Inconvénients** : refactor non-trivial dans `MailClientSessionManager` qui a son propre état (lock holder, cache de sessions). Risque de bouger la sémantique du locking.

### Approche B — Testcontainers + GreenMail Docker

1. Ajouter `Testcontainers` (déjà utilisé pour PostgreSQL `Testcontainers.PostgreSql 4.11.0`) avec un `GenericContainer` pointant `greenmail/standalone:latest` (ports IMAP 3143 / SMTP 3025).
2. `GreenMailFixture` à la `PostgreSqlFixture` : démarrage du container + seed des mailboxes via SMTP.
3. `appsettings.test.json` orienté GreenMail (host=localhost:3143, no SSL, dummy creds).
4. Tests d'intégration sous `mss.mail.integration.tests/Imap/` : ConnectAsync, ReadInbox, MoveToFolder, Delete, etc.
5. Couverture obtenue : paths réels (IMAP wire-level), avec un coût de latence test (container démarrage ~10s, tests parallélisables limités).

**Avantages** : tests réellement représentatifs (vrai protocole IMAP), réutilisable pour de futurs services MSSanté.
**Inconvénients** : dépendance Docker en CI, complexité d'orchestration TLS si on veut tester le path complet de `ImapConnectionService` (qui valide les certificats).

### Hybride (recommandé si Approche A choisie)

Approche A pour les 3 services consommant `MailClientSessionManager` ; Approche B pour `ImapConnectionService` qui touche directement le wire IMAP/TLS. Cette répartition minimise le rework tout en couvrant le path TLS qui est le plus chargé en règles métier (validation cert, TLS 1.2+, OCSP/CRL). Mais **alourdit la suite** — préférer A pure si la perf CI le permet.

## Cibles chiffrées

À l'issue de cette US :

- **≥ 4 des 4 `[ExcludeFromCodeCoverage]` IMAP retirées** (`ImapService`, `BackgroundImapService`, `ImapFolderService`, `ImapConnectionService`)
- **≥ 70 % line coverage** sur chacun des 4 services IMAP (mesure cobertura per-class)
- **0 régression** sur la suite api-mail

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 failure), incluant les nouveaux tests IMAP
- [ ] Approche choisie documentée dans le body PR (A / B / Hybride)
- [ ] Si Approche A : interface `IMailClientSessionManager` extraite + DI remappée + 0 référence à la classe concrète dans les services IMAP (`grep` pour valider)
- [ ] Si Approche B (totale ou hybride) : `GreenMailFixture` orchestré par Testcontainers + appsettings.test.json + ≥ 1 fixture mailbox seedée
- [ ] 4 `[ExcludeFromCodeCoverage]` IMAP retirées (avec `// reason: ...` supprimés en même temps)
- [ ] ≥ 70 % line coverage sur chacun des 4 services IMAP (cobertura per-class report dans le body PR)
- [ ] Aucune régression Sonar (code_smells / hotspots / ratings) sur api-mail

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreur
3. (Si Approche B) Vérifier Docker Desktop running et image `greenmail/standalone:latest` pullable
4. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release --collect:"XPlat Code Coverage" --settings:codecoverage.runsettings`
5. Vérifier dans le rapport cobertura que les 4 services IMAP sont à ≥ 70 % line.
6. Smoke run : `dotnet run --project src/mss.mail.api`, faire un sync IMAP réel sur une boîte de test → preuve que le refactor (interfaces / DI) ne casse pas le runtime.

## Notes

- Issue du découpage **Option B (2026-05-07)** de la US d'origine `task-032bis-test-harness`. Le Chantier 2 (FhirClient mock) est livré dans `task-032bis-fhir-mock`.
- US sœur : `task-032quater-cda-samples` (Chantier 3, gated métier).
- Bénéficie de `task-033` (cleanup Sonar massif) car les classes IMAP réintégrées au dénom seront alors testées et le critère "0 régression" Sonar plus solide.
