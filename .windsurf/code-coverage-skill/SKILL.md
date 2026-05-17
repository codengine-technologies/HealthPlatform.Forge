---
name: code-coverage-skill
description: **WORKFLOW SKILL** — Processus itératif d'amélioration de la couverture de code par création de tests unitaires manquants. Lance une analyse SonarQube (via sonar-skill), identifie les classes sous 98% de couverture, génère les tests manquants, puis relance l'analyse. Itère jusqu'à 98% de couverture globale ou 5 itérations max. USE FOR: améliorer la couverture de code; créer des tests unitaires manquants; atteindre un objectif de couverture; processus itératif de test. INVOKES: sonar-skill, dotnet CLI, tests unitaires, API SonarQube.
applyTo:
  - "**/*.cs"
  - "**/*.csproj"
  - "**/tests/**"
  - "**/src/**"
---

# Code Coverage Improvement Skill

Ce skill implémente un processus itératif pour améliorer la couverture de code du projet backend `Api/Mail/HealthPlatform.Api.Mail.sln` (chemin relatif à la racine du repo) en créant les tests unitaires manquants jusqu'à atteindre un objectif de **98% de couverture globale** ou un maximum de **5 itérations**.

## Objectif

- **Couverture cible** : 98% globale
- **Seuil par classe** : 98% minimum
- **Itérations max** : 10
- **Classes traitées par itération** : entre 1 et 10

## Prérequis

- Le skill `sonar-skill` doit être disponible et fonctionnel
- SonarQube doit être en cours d'exécution sur http://localhost:9001
- Le token SonarQube et le projet doivent être configurés

## Processus itératif

### Vue d'ensemble

```
┌─────────────────────────────────────────────┐
│           BOUCLE PRINCIPALE                 │
│  (max 5 itérations ou couverture >= 98%)    │
├─────────────────────────────────────────────┤
│ 1. Lancer analyse SonarQube (sonar-skill)   │
│ 2. Récupérer KPI (couverture globale)       │
│ 3. Si couverture >= 98% → STOP ✓           │
│ 4. Extraire classes < 98% de couverture     │
│ 5. Sélectionner 1-10 classes à traiter      │
│ 6. Pour chaque classe :                     │
│    a. Lire le code source                   │
│    b. Identifier le projet de test associé  │
│    c. Lire les tests existants              │
│    d. Créer/compléter les tests manquants   │
│    e. Vérifier que les tests passent        │
│ 7. Retour à l'étape 1                       │
└─────────────────────────────────────────────┘
```

### Étape 1 : Lancer l'analyse SonarQube

Utiliser le skill `sonar-skill` pour lancer une analyse complète. Suivre la procédure documentée dans ce skill :
- Préparer l'environnement (se placer dans `Api/Mail`, relatif à la racine du repo)
- `dotnet sonarscanner begin` avec les exclusions `**/devops/**,**/load-tests/**,**/AppHost/**`
- Build de la solution `HealthPlatform.Api.Mail.sln`
- Exécuter les 5 projets de test (`mss.mail.*.tests`) avec couverture OpenCover
- `dotnet sonarscanner end`

### Étape 2 : Récupérer la couverture globale

```powershell
Start-Sleep -Seconds 10  # Attendre le traitement par SonarQube

$metrics = "coverage"
$result = Invoke-RestMethod -Uri "http://localhost:9001/api/measures/component?component=healthplatform-api-mail&metricKeys=$metrics" `
    -Headers @{Authorization="Bearer $env:SONAR_TOKEN"}
$globalCoverage = [double]$result.component.measures[0].value
Write-Host "Couverture globale : $globalCoverage%"
```

### Étape 3 : Condition d'arrêt

```powershell
if ($globalCoverage -ge 98) {
    Write-Host "✓ Objectif atteint : $globalCoverage% >= 98%"
    # STOP - Ne pas continuer les itérations
}
```

### Étape 4 : Extraire les classes sous 98%

```powershell
$result = Invoke-RestMethod -Uri "http://localhost:9001/api/measures/component_tree?component=healthplatform-api-mail&metricKeys=coverage,uncovered_lines,lines_to_cover&strategy=leaves&ps=500&metricSort=coverage&asc=true&qualifiers=FIL&s=metric" `
    -Headers @{Authorization="Bearer $env:SONAR_TOKEN"}

# Filtrer les fichiers C# source (pas les tests) avec couverture < 98%
$classesBelowTarget = $result.components | Where-Object {
    $_.path -like "src/*" -and
    $_.path -like "*.cs" -and
    $_.measures.Count -gt 0
} | ForEach-Object {
    $cov = ($_.measures | Where-Object { $_.metric -eq "coverage" }).value
    $uncovered = ($_.measures | Where-Object { $_.metric -eq "uncovered_lines" }).value
    $total = ($_.measures | Where-Object { $_.metric -eq "lines_to_cover" }).value
    if ($cov -ne $null -and [double]$cov -lt 98) {
        [PSCustomObject]@{
            Path = $_.path
            Coverage = [double]$cov
            UncoveredLines = [int]$uncovered
            TotalLines = [int]$total
        }
    }
} | Sort-Object Coverage

# Afficher les classes à traiter
$classesBelowTarget | Format-Table -AutoSize
Write-Host "Total classes < 98% : $($classesBelowTarget.Count)"
```

### Étape 5 : Sélectionner les classes à traiter (1-10)

**Stratégie de sélection** : Prioriser les classes avec le plus grand nombre de lignes non couvertes (impact maximal sur la couverture globale), en évitant les classes trop complexes à tester (dépendances HTTP externes, etc.).

**Règles de sélection** :
- Sélectionner entre 1 et 10 classes par itération
- Prioriser les classes avec un fort ratio `uncovered_lines / total_lines` ET un nombre raisonnable de lignes à couvrir
- Éviter les classes qui nécessitent des mocks HTTP complexes si des classes plus simples sont disponibles
- Préférer les classes du Domain et Application (plus faciles à tester) avant Infrastructure et Api

**Ordre de priorité des couches** :
1. `src/Domain/` — Modèles, logique métier pure (testé par `mss.mail.domain.tests`)
2. `src/Application/` — Services applicatifs, handlers (testé par `mss.mail.application.tests`)
3. `src/Infrastructure/` — Infrastructure (testé par `mss.mail.infrastructure.tests`)
4. `src/Api/` — Contrôleurs, middleware (testé par `mss.mail.api.tests` et `mss.mail.integration.tests`)

### Étape 6 : Créer les tests manquants

Pour chaque classe sélectionnée :

#### 6a. Identifier le projet de test correspondant

Base (relative à la racine du repo) : `Api/Mail/tests`

| Projet source               | Projet de test associé              |
|-----------------------------|-------------------------------------|
| `src/Domain`                | `tests/mss.mail.domain.tests`       |
| `src/Application`           | `tests/mss.mail.application.tests`  |
| `src/Infrastructure`        | `tests/mss.mail.infrastructure.tests` |
| `src/Api`                   | `tests/mss.mail.api.tests` (unit) / `tests/mss.mail.integration.tests` (intégration) |

#### 6b. Lire le code source et les tests existants

- Lire le fichier source pour comprendre la classe, ses méthodes, ses dépendances
- Vérifier s'il existe déjà un fichier de test pour cette classe
- Si oui, lire les tests existants pour identifier les cas manquants
- Si non, créer un nouveau fichier de test

#### 6c. Conventions de test du projet

- **Framework** : xUnit (`[Fact]`, `[Theory]`)
- **Mocking** : Moq (`Mock<T>`, `MockBehavior.Strict`)
- **Assertions** : FluentAssertions (`.Should().Be()`, `.Should().NotBeNull()`, etc.)
- **Nommage** : `{MethodName}Should{ExpectedBehavior}` (ex: `GetTokensShouldReturnTokensDto`) — jamais de `_` dans les noms de méthode
- **Structure** : Arrange / Act / Assert
- **VerifyNoOtherCalls** : Toujours appeler `VerifyNoOtherCalls()` à la fin des tests avec mocks stricts
- **Namespace** : Reprendre la structure du projet de test (ex: `namespace mss.mail.application.tests.Services`)

#### 6d. Ce qu'il faut tester

- **Cas nominaux** : Appels avec paramètres valides → résultat attendu
- **Cas limites** : null, empty, valeurs extrêmes
- **Cas d'erreur** : exceptions, codes HTTP d'erreur
- **Branches conditionnelles** : if/else, switch, patterns optionnels
- **Vérification des appels mock** : Verify + VerifyNoOtherCalls

#### 6e. Valider les tests

Après création/modification des tests, les exécuter pour s'assurer qu'ils passent :

```powershell
dotnet test tests/{ProjetDeTest}/{ProjetDeTest}.csproj --configuration Release --filter "{NomDuTest}" --logger "console;verbosity=minimal"
```

### Étape 7 : Retour à l'étape 1

Une fois les tests créés et validés pour les 1-10 classes de l'itération :
- Incrémenter le compteur d'itération
- Vérifier si max itérations atteint (5)
- Si non, retourner à l'étape 1 (analyse SonarQube complète)

## Suivi des itérations

Maintenir un tableau de suivi à chaque itération :

```
| Itération | Couverture avant | Classes traitées | Tests ajoutés | Couverture après |
|-----------|-----------------|------------------|--------------|-----------------|
| 1         | xx.x%           | ClassA, ClassB   | +12          | xx.x%           |
| 2         | xx.x%           | ClassC, ClassD   | +8           | xx.x%           |
| ...       | ...             | ...              | ...          | ...             |
```

## Règles importantes

1. **Ne jamais modifier le code source** pour améliorer la couverture — uniquement créer/modifier des tests
2. **Ne jamais créer de tests triviaux** juste pour la couverture (pas de tests vides ou sans assertions)
3. **Toujours vérifier que les tests passent** avant de passer à la classe suivante
4. **Respecter les conventions existantes** du projet (Moq strict, FluentAssertions, VerifyNoOtherCalls)
5. **Maximum 10 classes par itération** pour éviter les sessions trop longues
6. **Minimum 1 classe par itération** — toujours progresser
7. **Arrêt obligatoire** à 98% de couverture globale ou après 5 itérations
8. **Afficher le rapport KPI SonarQube** (comme défini dans sonar-skill) à chaque fin d'itération

## Exemple de déroulement

```
Itération 1:
  → Analyse SonarQube : couverture = 62.3%
  → 23 classes < 98%
  → Traitement de 5 classes (Domain)
  → +15 tests créés, tous passent
  
Itération 2:
  → Analyse SonarQube : couverture = 75.5%
  → 18 classes < 98%
  → Traitement de 8 classes (Application + Infrastructure)
  → +20 tests créés, tous passent

Itération 3:
  → Analyse SonarQube : couverture = 88.2%
  → 12 classes < 98%
  → Traitement de 10 classes
  → +25 tests créés, tous passent

Itération 4:
  → Analyse SonarQube : couverture = 98.1%
  → ✓ Objectif atteint ! STOP
```
