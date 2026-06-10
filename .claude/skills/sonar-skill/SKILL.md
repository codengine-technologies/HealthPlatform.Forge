---
name: sonar-skill
description: >-
  Gestion complète de l'analyse SonarQube pour le projet backend
  Api/Mail/HealthPlatform.Api.Mail.sln : configuration de l'environnement,
  build, exécution des tests avec couverture OpenCover, envoi vers SonarQube
  et compte rendu des KPI. Utiliser pour lancer une analyse SonarQube complète,
  configurer l'environnement SonarQube, exécuter les tests avec couverture de
  code, résoudre les problèmes de build, ou valider la qualité du code.
  INVOKES : dotnet CLI, SonarScanner, tests unitaires, rapports de couverture,
  API SonarQube.
allowed-tools: Read, Bash
---

# SonarQube Analysis Skill

Ce skill documente la procédure complète pour effectuer une analyse SonarQube
sur le projet `Api/Mail/HealthPlatform.Api.Mail.sln` (chemin relatif à la
racine du repo).

## Configuration SonarQube

### Variables d'environnement

Les valeurs sensibles ne sont **jamais** codées en dur dans ce skill. Définir
ces variables dans la session avant de lancer l'analyse (ou les charger depuis
un `.env` non versionné) :

```powershell
$env:SONAR_HOST_URL  = "http://localhost:9001"
$env:SONAR_TOKEN     = "<votre-token-sonarqube>"   # ne jamais committer
$env:SONAR_PROJECT_KEY = "healthplatform-api-mail"
```

### Prérequis
- SonarQube server en cours d'exécution sur `http://localhost:9001`
- `dotnet-sonarscanner` installé globalement :
  `dotnet tool install --global dotnet-sonarscanner`
- Token SonarQube valide avec permissions d'analyse, exporté dans
  `$env:SONAR_TOKEN`

## Procédure d'analyse complète

### 1. Préparation de l'environnement
```powershell
# Se placer dans le dossier de la solution (relatif à la racine du repo)
Set-Location Api/Mail

# Nettoyer et recréer le répertoire de résultats de tests
if (Test-Path "TestResults") { Remove-Item -Path "TestResults" -Recurse -Force }
New-Item -ItemType Directory -Path "TestResults" -Force
```

### 2. Démarrage de l'analyse SonarQube
```powershell
dotnet sonarscanner begin `
    /k:"$env:SONAR_PROJECT_KEY" `
    /d:sonar.host.url="$env:SONAR_HOST_URL" `
    /d:sonar.token="$env:SONAR_TOKEN" `
    /d:sonar.sourceEncoding=UTF-8 `
    /d:sonar.exclusions="**/devops/**,**/load-tests/**,**/AppHost/**" `
    /d:sonar.cs.opencover.reportsPaths="TestResults/**/coverage.opencover.xml" `
    /d:sonar.coverage.exclusions="**/obj/**,**/bin/**,**/tests/**,**/AppHost/**,**/Infrastructure.Mock/**"
```

### 3. Construction du projet
```powershell
dotnet build HealthPlatform.Api.Mail.sln --configuration Release --verbosity quiet
```

### 4. Exécution des tests avec couverture
```powershell
$testProjects = @(
    "tests/mss.mail.domain.tests/mss.mail.domain.tests.csproj",
    "tests/mss.mail.application.tests/mss.mail.application.tests.csproj",
    "tests/mss.mail.infrastructure.tests/mss.mail.infrastructure.tests.csproj",
    "tests/mss.mail.api.tests/mss.mail.api.tests.csproj",
    "tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj"
)

foreach ($proj in $testProjects) {
    dotnet test $proj `
        --configuration Release `
        --collect:"XPlat Code Coverage;Format=opencover" `
        --results-directory TestResults `
        --logger "console;verbosity=minimal"
}
```

### 5. Finalisation et envoi à SonarQube
```powershell
dotnet sonarscanner end /d:sonar.token="$env:SONAR_TOKEN"
```

## Résolution des problèmes courants

### Warnings NuGet et AutoMapper
Si vous rencontrez des erreurs liées aux vulnérabilités AutoMapper (NU1903),
vous pouvez temporairement désactiver `TreatWarningsAsErrors` dans
`Directory.Build.props` :

```xml
<TreatWarningsAsErrors>false</TreatWarningsAsErrors>
<NuGetAudit>false</NuGetAudit>
```

**Important** : Réactivez ces paramètres après l'analyse pour maintenir la
qualité du code.

### docker-compose.dcproj
Le projet docker-compose peut causer des erreurs lors du build de la solution
complète. Utilisez les projets individuels plutôt que la solution complète.

### Vérification des rapports de couverture
```powershell
$reports = Get-ChildItem -Path "TestResults" -Recurse -Filter "coverage.opencover.xml"
if ($reports.Count -gt 0) {
    Write-Host "✓ $($reports.Count) rapport(s) de couverture OpenCover trouvé(s)"
    $reports | ForEach-Object { Write-Host "  - $($_.FullName) ($($_.Length) octets)" }
} else {
    Write-Host "✗ Pas de rapport de couverture trouvé"
}
```

## Métriques de référence

### Projets de tests
- **mss.mail.domain.tests** : tests du domaine
- **mss.mail.application.tests** : tests de la couche application
- **mss.mail.infrastructure.tests** : tests de l'infrastructure
- **mss.mail.api.tests** : tests de l'API
- **mss.mail.integration.tests** : tests d'intégration

### Structure des projets
```
Api/Mail/
├── HealthPlatform.Api.Mail.sln
├── src/
│   ├── Api/                  # mss.mail.api
│   ├── Application/          # mss.mail.application
│   ├── Domain/               # mss.mail.domain
│   ├── Infrastructure/       # mss.mail.infrastructure
│   ├── Infrastructure.Mock/  # mss.mail.infrastructure.mock
│   └── AppHost/              # mss.mail.AppHost (Aspire)
└── tests/
    ├── mss.mail.domain.tests/
    ├── mss.mail.application.tests/
    ├── mss.mail.infrastructure.tests/
    ├── mss.mail.api.tests/
    └── mss.mail.integration.tests/
```

## Bonnes pratiques

1. **Toujours exécuter les tests avant l'analyse** pour s'assurer que le code fonctionne
2. **Générer la couverture de code** pour avoir des métriques complètes dans SonarQube
3. **Vérifier les rapports de couverture** avant de finaliser l'analyse
4. **Restaurer la configuration stricte** après l'analyse (`TreatWarningsAsErrors=true`)
5. **Nettoyer les anciens résultats** avant chaque nouvelle analyse

## Attendre la fin du traitement côté serveur

Après `sonarscanner end`, le serveur traite le rapport de façon asynchrone.
Plutôt qu'un `Start-Sleep` fixe, interroger l'API `ce/activity` jusqu'à ce que
la dernière tâche d'analyse soit `SUCCESS` :

```powershell
$deadline = (Get-Date).AddMinutes(3)
do {
    Start-Sleep -Seconds 5
    $ce = Invoke-RestMethod -Uri "$env:SONAR_HOST_URL/api/ce/activity?component=$env:SONAR_PROJECT_KEY&onlyCurrents=true&ps=1" `
        -Headers @{ Authorization = "Bearer $env:SONAR_TOKEN" }
    $status = if ($ce.tasks.Count -gt 0) { $ce.tasks[0].status } else { "PENDING" }
    Write-Host "Statut traitement SonarQube : $status"
} while ($status -in @("PENDING","IN_PROGRESS") -and (Get-Date) -lt $deadline)
```

## Compte rendu des KPI après analyse

À la fin de chaque analyse, récupérer et afficher les KPI sous forme de tableau
markdown :

```powershell
$metrics = "bugs,vulnerabilities,code_smells,coverage,line_coverage,branch_coverage,duplicated_lines_density,ncloc,sqale_index,reliability_rating,security_rating,sqale_rating,security_hotspots"
$result = Invoke-RestMethod -Uri "$env:SONAR_HOST_URL/api/measures/component?component=$env:SONAR_PROJECT_KEY&metricKeys=$metrics" `
    -Headers @{ Authorization = "Bearer $env:SONAR_TOKEN" }

# Construire un dictionnaire des mesures
$measures = @{}
$result.component.measures | ForEach-Object { $measures[$_.metric] = $_.value }

# Fonctions utilitaires — compatibles PowerShell 5.1 (pas d'opérateur ??)
function GetMetric($key) { if ($measures[$key]) { $measures[$key] } else { 'N/A' } }
function GetRating($key) { $val = $measures[$key]; if ($val) { @('','A','B','C','D','E')[[int][double]$val] } else { 'N/A' } }

Write-Host "`n===== RAPPORT SONARQUBE - KPI ====="
Write-Host "| Métrique                    | Valeur |"
Write-Host "|-----------------------------|--------|"
Write-Host "| Lignes de code (ncloc)      | $(GetMetric 'ncloc') |"
Write-Host "| Couverture globale          | $(GetMetric 'coverage')% |"
Write-Host "| Couverture lignes           | $(GetMetric 'line_coverage')% |"
Write-Host "| Couverture branches         | $(GetMetric 'branch_coverage')% |"
Write-Host "| Bugs                        | $(GetMetric 'bugs') |"
Write-Host "| Vulnérabilités              | $(GetMetric 'vulnerabilities') |"
Write-Host "| Security Hotspots           | $(GetMetric 'security_hotspots') |"
Write-Host "| Code Smells                 | $(GetMetric 'code_smells') |"
Write-Host "| Dette technique (min)       | $(GetMetric 'sqale_index') |"
Write-Host "| Duplication                 | $(GetMetric 'duplicated_lines_density')% |"
Write-Host "| Fiabilité (Rating)          | $(GetRating 'reliability_rating') |"
Write-Host "| Sécurité (Rating)           | $(GetRating 'security_rating') |"
Write-Host "| Maintenabilité (Rating)     | $(GetRating 'sqale_rating') |"
Write-Host "===================================="
```

## Accès aux résultats
- **Interface SonarQube** : `http://localhost:9001`
- **Projet** : `healthplatform-api-mail`
