# todo-task-040-sonar-batch-quick-wins.md — Sonar batch quick-wins api-mail (CA1862 + S1075 + S1135 + exclusion migrations)

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E010
**EpicTitle**: Sonar cleanup api-mail (hors coverage)
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Première vague de cleanup Sonar sur `api-mail` (hors S3776 et hors security
hotspots). Vise les "quick wins" Sonar : les 30 occurrences de CA1862, le 1 URI
hardcodée S1075, le 1 TODO tag S1135. Inclut un changement de **configuration
forge** : ajouter `**/Migrations/**` à `sonar.exclusions` pour éliminer
définitivement les 17 issues S1192 concentrées dans la migration EF historique
de janvier 2024 (refactor sans valeur, append-only, déjà appliquée partout).

## Baseline Sonar (snapshot 2026-05-17, avant l'exclusion migrations)

| Métrique            | Valeur | Cible |
|---------------------|--------|-------|
| Bugs                | 0      | 0 ✅  |
| Vulnerabilities     | 0      | 0 ✅  |
| Code Smells         | 100    | 0     |
| Security Hotspots   | 5      | 0     |
| Reliability rating  | A      | A ✅  |
| Security rating     | A      | A ✅  |
| Maintainability     | A      | A ✅  |
| Coverage            | 65.4 % | **EXCLU de cet EPIC** |

## Périmètre de la task

### Étape 0 — Exclusion migrations (config forge, AVANT toute analyse)

Modifier `D:\TechWatch\HealthPlatform\agents\sonar.md`, section "Sonar analysis
commands" → bloc `Begin` (~ligne 538). Ajouter `**/Migrations/**` à la liste
des exclusions :

```diff
- /d:sonar.exclusions="**/devops/**,**/load-tests/**,**/AppHost/**" \
+ /d:sonar.exclusions="**/devops/**,**/load-tests/**,**/AppHost/**,**/Migrations/**" \
```

Justifier dans le commit message (sur `api-mail` ? non — `agents/sonar.md`
vit dans le **workspace forge** qui n'est pas un repo git. La modification
est locale au poste forge ; aucun commit ni PR ne lui correspond.) Logger
l'edit dans le `## Journal` de cette task.

Re-lancer une analyse Sonar complète **avant** de commencer le batch (Step 1)
pour re-baseliner les compteurs et confirmer que les 17 S1192 disparaissent.

### Étape 1 — Batch /sonar Mode A (chaîné depuis /develop)

Cette task suit le cycle autonome :
`/start task-040` → `/develop task-040` → `/sonar task-040` → `/review task-040`.

`/develop` n'a pas grand-chose à écrire en propre ici (c'est `/sonar` qui fait
le travail). Le code écrit par `/sonar` portera sur :

| Règle | # | Fichiers principaux | Stratégie de fix |
|---|---|---|---|
| `external_roslyn:CA1862` | 30 | `MailRepository.cs` (18), `PatientRepository.cs` (12) | Remplacer `.Contains(x)` par `.Contains(x, StringComparison.OrdinalIgnoreCase)`. **Behavioural** car la comparaison passe de culture-sensitive à invariante : ajouter **un test par méthode impactée** qui vérifie le matching insensible à la casse avant le fix. |
| `csharpsquid:S1075` | 1 | `FlagsmithExtensions.cs` | Externaliser l'URI Flagsmith dans `appsettings.json` (clé `Flagsmith:Url`) avec valeur par défaut hardcodée si absente du config. Pur refacto + test de binding config. |
| `csharpsquid:S1135` | 1 | `NewMailNotifier.cs` | Soit résoudre le TODO (vérifier d'abord ce qu'il demande), soit le convertir en `// Note:` neutre + ouvrir une issue dédiée. Décision dans le PR description. |

S1192 (17) : **éliminés par l'exclusion migrations** (Étape 0), pas par du code.

S3776 (39), S107 (9), S6960 (3) : **hors scope** de cette task.
- S3776 → campagne `meta-task-046` (lancements `/sonar-s3776` au fil de l'eau)
- S107 → `todo-task-041-sonar-s107-param-objects.md`
- S6960 → `todo-task-042/043/044-split-*-controller.md`

## Scope OUT

- Aucune modification du code des migrations (`src/Infrastructure/Migrations/`).
- Aucun touchee aux 39 méthodes S3776, aux 9 méthodes S107, aux 3 controllers S6960.
- Aucun toucher aux 5 security hotspots (traités par `todo-task-045-*`).
- Aucun touchee à la coverage (hors scope EPIC entier).

## Definition of Done

- [ ] `agents/sonar.md` modifié : `**/Migrations/**` ajouté à `sonar.exclusions`
- [ ] Build `api-mail` passes en Release (0 errors)
- [ ] Tests `api-mail` passent (0 failures, y compris les nouveaux tests
      CA1862 case-insensitive)
- [ ] Re-analyse Sonar post-batch : **0 occurrence** restante des règles
      CA1862, S1075, S1135 **et** S1192 (cette dernière éliminée par exclusion)
- [ ] Reliability / Security / Maintainability rating restent A
- [ ] Smells restants : ≤ 51 (100 - 30 - 1 - 1 - 17 = 51, soit S3776 × 39 + S107 × 9 + S6960 × 3)
- [ ] Pour chaque fix CA1862 dans `MailRepository`/`PatientRepository` :
      ≥ 1 unit test vérifie le matching insensible à la casse
- [ ] `FlagsmithExtensions` : URI lue depuis config avec fallback testé
- [ ] Décision documentée pour le TODO `NewMailNotifier` (résolu OU
      reformulé en `// Note:` + issue ouverte référencée dans le PR)
- [ ] Aucune régression sur les tests préexistants
- [ ] Journal d'itération `/sonar` rempli dans cette task
- [ ] PR ouverte sur `api-mail` avec label `awaiting-human-merge`

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreurs
3. `dotnet test  HealthPlatform.Api.Mail.sln --configuration Release` → 0 failures
4. Lancer l'API locale (Aspire AppHost) ; smoke-test deux flux qui exercent
   les `Contains` patchés :
   - Recherche de mail avec un terme contenant des majuscules (vérifier
     que ça match insensible à la casse) → résultat attendu identique
     à avant pour les requêtes lowercase, ÉLARGI pour les mixed-case
   - Recherche patient par nom partiel mixed-case
5. Vérifier Flagsmith : démarrer avec / sans la clé `Flagsmith:Url` dans
   `appsettings.json` → fallback hardcodé doit fonctionner
6. Vérifier sur SonarQube : http://localhost:9000/dashboard?id=healthplatform
   - **0** issues CA1862, S1075, S1135, **S1192** restantes
   - Maintainability rating toujours A
   - 51 smells restants (correspondant aux 3 règles non traitées par cette task)

## Journal

(rempli par `/develop` et `/sonar` au fur et à mesure)

| Iter | Catégorie | Règles traitées | Fichiers | Issues fixed | Build | Tests | KPIs après |
|------|-----------|-----------------|----------|--------------|-------|-------|------------|
|      |           |                 |          |              |       |       |            |
