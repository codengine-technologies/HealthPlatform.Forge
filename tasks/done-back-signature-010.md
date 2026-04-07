# done-back-signature-010 — Backend : Signatures email

**Dependencies**: aucune
**Feature**: tests/Features/Mss/Signature.feature
**Repo**: api-mail (path: `Api/Mail`)
**Touches**: dtos-mss (CreateMailSignatureDto, MailSignatureDto, UpdateMailSignatureDto)
**Module**: Api/Mail
**Status**: done (rétroactif — livré via PR #15 `feature/draft_and_sign`, commit `931d0c0 Signature mail` du 2026-04-03)

## Objectif

Gérer les signatures email du professionnel de santé : CRUD, signature par défaut, injection automatique à l'envoi via SMTP.

## Travail réalisé

### 1. Domain
- `src/Domain/Entities/MailSignature.cs` — entité avec `Name`, `Content`, `IsDefault`, `UserId`
- `src/Infrastructure/Migrations/20260402_AddMailSignatureMigration.cs` — migration EF Core
- `src/Infrastructure/Persistance/MailDataContext.cs` — DbSet ajouté

### 2. Repository
- `src/Application/Services/Repository/IMailSignatureRepository.cs`
- `src/Infrastructure/Repositories/MailSignatureRepository.cs`

### 3. Controller
- `src/Api/Controllers/V1/SignatureController.cs` — endpoints CRUD + toggle default

### 4. Service SMTP
- `src/Application/Services/Implementation/SmtpService.cs` modifié — injection de la signature par défaut dans le corps des messages sortants (nouveaux + réponses)

### 5. DTOs (repo `dtos-mss`)
- `CreateMailSignatureDto.cs`, `MailSignatureDto.cs`, `UpdateMailSignatureDto.cs`

### 6. Tests
- `tests/mss.mail.domain.tests/Entities/MailSignatureTests.cs`
- `tests/mss.mail.application.tests/Services/SmtpServiceTests.cs`
- `tests/mss.mail.integration.tests/Repository/MailSignatureRepositoryIntegrationTests.cs`

## Definition of Done

- [x] Build passes (0 errors) — commit `931d0c0` mergé dans PR #15
- [x] Entité `MailSignature` persistée via EF Core + migration
- [x] CRUD complet exposé par `SignatureController` — couvre scénarios 1, 2, 3
- [x] Gestion "signature par défaut" via `IsDefault` — couvre scénario 4
- [x] Injection automatique via `SmtpService` pour nouveaux messages — couvre scénario 5
- [x] Injection automatique lors des réponses (même chemin SmtpService) — couvre scénario 6
- [x] DTOs publiés dans le repo `dtos` — consommés par Blazor et Angular
- [x] Tests unitaires (domain + application) et intégration (repository) présents
- [ ] Scénarios Gherkin Signature.feature couverts par step definitions BDD — **à vérifier** (pas de trace d'un `SignatureStepDefinitions.cs` dans le projet `mss.mail.bdd.tests` livré via PR #15)

## Notes de clôture rétroactive (2026-04-07)

Cette tâche a été créée **après coup** pour tracer du travail déjà mergé sur `develop`. Les scénarios 7 (changement pendant compose) et 8 (prévisualisation) sont hors scope backend — ils sont traités côté Blazor et Angular. Si un audit BDD ultérieur révèle que `Signature.feature` n'a pas de step definitions, créer un `todo-back-signature-bdd-*.md` pour combler ce gap.
