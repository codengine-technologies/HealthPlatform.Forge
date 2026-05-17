# todo-task-047-ca1862-ef-linq-investigation.md — CA1862 EF Core LINQ — investigation Npgsql + décision fix vs SuppressMessage

**Repos**: api-mail
**Dependencies**: aucune (mais informée par `questions/answered/task-040.md`)
**Epic**: E010
**EpicTitle**: Sonar cleanup api-mail (hors coverage)
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Contexte (pourquoi cette task existe séparément)

`todo-task-040-sonar-batch-quick-wins` proposait initialement de "fixer" les
49 occurrences de `external_roslyn:CA1862` dans `MailRepository.cs` (24) et
`PatientRepository.cs` (25) en remplaçant mécaniquement :

```diff
- .ToLower().Contains(x)
+ .Contains(x, StringComparison.OrdinalIgnoreCase)
```

L'analyse `/sonar` du 2026-05-17 a révélé que **toutes** les occurrences sont
dans des `Where(...)` EF Core LINQ → traduites en SQL Postgres via Npgsql. Le
fix mécanique présente **3 risques** :

1. `InvalidOperationException` au runtime ("could not be translated") si Npgsql
   10 ne supporte pas l'overload `Contains(string, StringComparison)`.
2. **Client-side evaluation silencieuse** — EF charge toute la table en mémoire
   puis filtre côté .NET. Désastreux sur `MailMedicalDocuments` (potentiellement
   millions de lignes en prod).
3. Traduction correcte mais légèrement différente du `LOWER(field) LIKE '%x%'`
   actuel — risque comportemental marginal (collation différente, edge cases
   Unicode).

Stack confirmée (`Api/Mail/Directory.Packages.props`) :
- `Microsoft.EntityFrameworkCore` : **10.0.7**
- `Npgsql.EntityFrameworkCore.PostgreSQL` : **10.0.1**
- `Microsoft.EntityFrameworkCore.Design` : **9.0.8** (drift mineur, EF Core 9
  vs 10 — probablement involontaire, à signaler en passant)

Cette task **n'applique aucun fix** par défaut : elle investigue, puis décide.
Le fix lui-même est conditionnel à la décision documentée en phase 2.

## Phase 1 — Investigation (mandatoire, pas de fix)

### Objectif

Déterminer empiriquement le SQL généré par chacune des 3 stratégies suivantes
sur PostgreSQL via Npgsql 10, dans le contexte `api-mail` :

| Stratégie | LINQ | SQL attendu | Translatable ? |
|---|---|---|---|
| Actuelle | `.ToLower().Contains("sent")` | `LOWER(field) LIKE '%sent%'` | Oui (validé en prod) |
| CA1862 idéal | `.Contains("sent", StringComparison.OrdinalIgnoreCase)` | `ILIKE '%sent%'` ou `LOWER(field) LIKE '%sent%'` (selon provider) | **À vérifier** |
| Alternative | `EF.Functions.ILike(field, "%sent%")` | `ILIKE '%sent%'` | Oui (Npgsql primitive) |

### Méthodologie

1. **Activer `EnableSensitiveDataLogging`** dans un projet de test ou un
   endpoint dev-only :
   ```csharp
   optionsBuilder.UseNpgsql(connStr)
                 .EnableSensitiveDataLogging()
                 .LogTo(Console.WriteLine, LogLevel.Information);
   ```

2. **Écrire 3 tests d'intégration** (Testcontainers.PostgreSql, déjà dépendance
   du projet `tests/mss.mail.integration.tests/`) — un par stratégie. Chaque
   test :
   - Construit une `IQueryable<MailMedicalDocument>` avec la clause `Where(...)`
     correspondante.
   - Capture le SQL généré (via `IQueryable.ToQueryString()` qui est dispo en
     EF Core 7+ et ne nécessite pas d'exécution).
   - Asserte sur la forme du SQL attendu (présence de `LIKE` / `ILIKE`,
     absence de client-eval warning).
   - Optionnel : exécute la query et vérifie les résultats sur un dataset
     mixed-case pour confirmer la case-insensitivity.

3. **Si la stratégie CA1862 idéal échoue** (exception ou client-eval) :
   - Marquer CA1862 comme `[SuppressMessage("Globalization", "CA1862", Justification = "EF Core LINQ — translation case-insensitive déléguée à LOWER() LIKE")]` au niveau des **classes** `MailRepository` et `PatientRepository`, ou au niveau des **méthodes** concernées si on veut une granularité plus fine.
   - Documenter la décision dans la PR description.
   - Phase 2 → application des SuppressMessage uniquement.

4. **Si la stratégie CA1862 idéal réussit** (translatable, génère du SQL
   équivalent, pas de client-eval) :
   - Phase 2 → application du fix aux 49 occurrences (Contains) + 1 (Equals L841).
   - Tests d'intégration ajoutés pour les méthodes Repository touchées
     (assertion sur le SQL via `ToQueryString()`, pas juste sur le résultat).

5. **Si la stratégie alternative `EF.Functions.ILike` est préférable** :
   - Décision design — `ILike` est Npgsql-spécifique, casse la portabilité
     éventuelle vers SQL Server. Trade-off à discuter.

### Livrables Phase 1

- 1 fichier test `tests/mss.mail.integration.tests/CA1862TranslationProbe.cs`
  avec les 3 tests + assertions sur le SQL.
- Une **décision documentée** dans le journal de cette task : "fix CA1862",
  "SuppressMessage par classe", ou "SuppressMessage par méthode".
- Mention du drift `EFCore.Design 9.0.8` vs `EFCore 10.0.7` dans le journal
  (à fixer dans une task séparée si confirmé non-intentionnel).

## Phase 2 — Application (conditionnelle à la décision de Phase 1)

### Si décision = "fix CA1862"

- **MailRepository.cs** — 24 occurrences à patcher :
  - L2384-2389 (méthode `DetectDuplicateAsync` step 1)
  - L2414-2419 (idem step 2)
  - L2566-2571
  - L2629-2634
- **PatientRepository.cs** — 25 occurrences à patcher :
  - L186-191
  - L241-246
  - L349-354
  - L678-683
  - L841 (cas spécial — `==` au lieu de `.Contains` → `.Equals(string, StringComparison)`)

Pour chaque méthode Repository touchée :
1. Test d'intégration avec assertion SQL (`.ToQueryString()` + regex check sur
   `LIKE` / `ILIKE`) écrit AVANT le fix → confirme le SQL actuel.
2. Application du fix `.Contains(x, StringComparison.OrdinalIgnoreCase)` (ou
   `.Equals(x, StringComparison.OrdinalIgnoreCase)` pour L841).
3. Re-run du test → confirme que le SQL nouveau est équivalent (ou pas — si
   non-équivalent, rollback et passer à SuppressMessage).
4. Test fonctionnel sur dataset mixed-case → résultats identiques.

### Si décision = "SuppressMessage"

- Appliquer `[SuppressMessage("Globalization", "CA1862", Justification = "...")]`
  au niveau classe pour `MailRepository` et `PatientRepository`.
- Aucune modification du code applicatif.
- Aucun test ajouté (la justification est suffisante).
- Note dans le PR description : explication + lien vers cette task pour la
  trace d'investigation.

## Scope OUT

- Aucune autre règle Sonar (task-040 traite S1075/S1135, task-041 traite S107,
  etc.).
- Aucune refonte de l'architecture Repository (filtrage folder paths reste tel
  quel — pas de migration vers un enum, pas d'extraction de méthode).
- Aucune modification des migrations EF (`src/Infrastructure/Migrations/`).
- Pas de touch à la coverage (hors scope EPIC E010).

## Definition of Done

### Phase 1 (mandatoire)

- [ ] `tests/mss.mail.integration.tests/CA1862TranslationProbe.cs` créé avec
      3 tests : stratégie actuelle, CA1862 idéal, `EF.Functions.ILike`.
- [ ] Chaque test capture le SQL via `.ToQueryString()` et asserte sa forme.
- [ ] Build `api-mail` vert (0 erreurs), tests verts.
- [ ] Décision documentée dans le journal : "fix" / "SuppressMessage classe" /
      "SuppressMessage méthode" / "ILike (Npgsql-only)".
- [ ] Le journal mentionne le drift `EFCore.Design 9.0.8` vs `EFCore 10.0.7`
      (informational only — fix séparé si nécessaire).

### Phase 2 — branche "fix"

- [ ] 49 occurrences `.ToLower().Contains(x)` remplacées par
      `.Contains(x, StringComparison.OrdinalIgnoreCase)`.
- [ ] L841 PatientRepository : `.ToLower() == "inbox"` remplacé par
      `.Equals("inbox", StringComparison.OrdinalIgnoreCase)`.
- [ ] 1 test d'intégration par méthode Repository touchée, assertion SQL +
      assertion résultat mixed-case.
- [ ] Build + tests verts.
- [ ] Re-analyse Sonar : 0 occurrence CA1862 restante.

### Phase 2 — branche "SuppressMessage"

- [ ] `[SuppressMessage]` posé au niveau `MailRepository` et
      `PatientRepository` (ou méthode par méthode si granularité fine
      choisie).
- [ ] Build vert, aucune régression de test.
- [ ] Re-analyse Sonar : 0 occurrence CA1862 restante (Sonar respecte les
      `SuppressMessage` Roslyn).

### Commun aux deux branches

- [ ] Reliability / Security / Maintainability rating restent A.
- [ ] PR ouverte sur `api-mail` avec label `awaiting-human-merge`.

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreurs
3. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release` → 0 failures
4. **Phase 1 validation** — Lire la sortie des 3 tests `CA1862TranslationProbe`,
   confirmer la décision prise.
5. **Phase 2 validation** (selon décision) :
   - **Branche "fix"** — Lancer l'API locale (Aspire AppHost). Sur un dataset
     mixed-case (`Inbox`, `INBOX`, `inbox`, `SENT`, `Sent`), vérifier que
     recherche mail + recherche patient retournent les mêmes résultats qu'avant
     le fix. Vérifier les logs Postgres (`pg_stat_statements` ou
     `log_min_duration_statement = 0`) : le SQL généré ne doit pas exploser en
     volume (pas de SELECT * sans WHERE).
   - **Branche "SuppressMessage"** — Aucun changement runtime, juste confirmer
     que Sonar ne flagge plus CA1862.
6. Vérifier sur SonarQube : http://localhost:9001/dashboard?id=healthplatform
   - **0** issue restante pour `external_roslyn:CA1862`
   - Maintainability rating toujours A
   - Compteur global Code Smells : baisse de ~50 par rapport à la baseline post-task-040
