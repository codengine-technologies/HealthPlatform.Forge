# todo-task-041-sonar-s107-param-objects.md — Refactor S107 (méthodes > 7 paramètres) en param objects

**Repos**: api-mail
**Dependencies**: aucune (parallélisable avec task-040, 042, 043, 044, 045)
**Epic**: E010
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Éliminer les **9 occurrences** de `csharpsquid:S107` (Methods should not have
too many parameters) sur `api-mail`. Chaque méthode (en réalité un constructeur
primaire ou une signature de service) avec > 7 paramètres est refactorée en
**param object** (record `*Options` ou `*Args`) pour gagner en lisibilité, en
testabilité, et en évolutivité.

Refactor structurel — pas un patch Sonar batch. Justifie une task et une PR
dédiées, isolées du batch quick-wins de la task-040.

## Liste exacte des 9 méthodes (Sonar snapshot 2026-05-17)

| # | Fichier | Ligne | Nature |
|---|---|---|---|
| 1 | `src/Api/Controllers/V1/MailController.cs` | 25 | Constructeur primaire (16 dépendances DI) |
| 2 | `src/Application/Services/Implementation/ImapConnectionService.cs` | 29 | Constructeur / méthode |
| 3 | `src/Application/Services/Implementation/ImapFolderService.cs` | 29 | Constructeur / méthode |
| 4 | `src/Application/Services/Implementation/ImapService.cs` | 42 | Constructeur primaire |
| 5 | `src/Application/Services/Implementation/BackgroundImapService.cs` | 36 | Constructeur |
| 6 | `src/Application/Services/Implementation/SmtpService.cs` | 15 | Constructeur |
| 7 | `src/Application/Services/Interfaces/ISemanticSearchService.cs` | 23 | Signature interface |
| 8 | `src/Application/Session/ImapLockScope.cs` | 38 | Méthode publique |
| 9 | `src/Infrastructure/Repository/PatientRepository.cs` | 565 | Méthode publique |

## Stratégie de refactor

Trois patrons applicables selon le cas, à arbitrer méthode par méthode :

### A. Constructeur primaire DI lourd (cas MailController, ImapService, etc.)

Pas un vrai problème S107 au sens design — c'est une accumulation de
dépendances liée à un Controller/Service trop large. Deux pistes :

- **Court terme (cette task)** : extraire les dépendances DI dans une
  `record MailControllerDependencies(ILogger<MailController> Logger,
  ServiceImplementation ServiceImpl, ...)` enregistrée dans DI elle-même,
  et injecter `MailControllerDependencies deps` en un seul paramètre. Effet
  Sonar : 1 paramètre. Effet design : cosmétique (juste un wrapper).
- **Long terme (hors task)** : split fonctionnel du controller (cf. S6960
  task-042 pour PatientsController). Mais ici MailController n'est pas
  S6960 ; on reste sur le wrapper.

### B. Signature d'interface / méthode métier (cas ISemanticSearchService, ImapLockScope, PatientRepository)

Vrai S107 design. Refactor en :

```csharp
public sealed record SemanticSearchOptions(
    string Query,
    int TopK,
    float MinScore,
    // ... 5-10 propriétés ...
);

Task<IReadOnlyList<SearchHit>> SearchAsync(
    SemanticSearchOptions options,
    CancellationToken ct);
```

Le param object est immutable (record), avec valeurs par défaut quand pertinent.
Touche **tous les callers** : à mettre à jour dans la PR + tests adaptés.

### C. Si une signature est exposée HTTP (cas MailController endpoints internes)

Vérifier que le binding ASP.NET reste compatible. Pour `[FromQuery]` mixé avec
`[FromBody]`, un param object est plus naturel — privilégier `[FromBody]
Options opts` quand possible. **Ne pas casser le contrat HTTP** (mêmes
query params côté client). Si un endpoint expose réellement > 7 params en
query, garder la signature publique et wrap en interne.

## Scope OUT

- Aucun touchee aux 39 S3776, 30 CA1862, 17 S1192 (autres tasks ou
  exclusion).
- Aucun split de controller (S6960) ; même si MailController est lourd,
  il n'est pas dans la liste S6960 — c'est juste un constructeur dense.
- Aucune modification des frontends (Blazor, Angular) : si un param object
  est exposé HTTP, le contrat reste isomorphe (même propriétés sur le wire).
  Vérifié au cas par cas pendant l'implémentation.

## Definition of Done

- [ ] Build `api-mail` passes en Release (0 errors)
- [ ] Tests `api-mail` passent (0 failures)
- [ ] **0 occurrence** restante de `csharpsquid:S107` post-analyse Sonar
- [ ] Chaque param object introduit est immutable (`record` ou
      `record struct`), nommé `*Options` ou `*Args` ou `*Dependencies`
- [ ] Pour chaque méthode métier refactorée (≠ constructeur DI) : au moins
      1 test unitaire couvrant les valeurs par défaut + 1 cas non-défaut
- [ ] Tous les callers internes au repo `api-mail` mis à jour (compile-time
      checked par le build)
- [ ] Aucune modification du contrat HTTP exposé (vérifié pour les
      endpoints touchés : query/body identique sur le wire)
- [ ] Aucune régression sur les tests préexistants
- [ ] PR ouverte sur `api-mail` avec label `awaiting-human-merge`

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreurs
3. `dotnet test  HealthPlatform.Api.Mail.sln --configuration Release` → 0 failures
4. Lancer l'API locale (Aspire AppHost)
5. Smoke-test des endpoints `/api/v1/mail/*` qui passent par les
   constructeurs refactorés (folders, search, send) → comportement
   identique à avant
6. Smoke-test recherche sémantique (si endpoint exposé) → résultats
   identiques pour les mêmes paramètres
7. Vérifier sur SonarQube : **0** issue S107 restante sur `healthplatform`
