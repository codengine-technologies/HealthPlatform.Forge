---
name: sonar-skill
description: Describe what this skill does and when to use it. Include keywords that help agents identify relevant tasks.
---


---
name: sonar-analysis
description: **WORKFLOW SKILL** — Gestion complète de l'analyse SonarQube pour le projet Api\Mail\HealthPlatform.Api.Mail.sln. Configuration, exécution des tests, génération des rapports de couverture et envoi vers SonarQube. USE FOR: lancer une analyse SonarQube complète; configurer l'environnement SonarQube; exécuter les tests avec couverture de code; résoudre les problèmes de build; valider la qualité du code. INVOKES: dotnet CLI, SonarScanner, tests unitaires, rapports de couverture.
applyTo:
  - "**/*.cs"
  - "**/*.csproj" 
  - "**/*.sln"
  - ".env"
  - "Directory.Build.props"
---

# SonarQube Analysis Skill

Ce skill documente la procédure complète pour effectuer une analyse SonarQube sur le projet Api\Mail\HealthPlatform.Api.Mail.sln.

## Configuration SonarQube

### Variables d'environnement (`.env`)
```bash
# SonarQube Configuration
SONAR_HOST_URL=http://localhost:9001
SONAR_TOKEN=squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df
SONAR_PROJECT_KEY=healthplatform
```

### Prérequis
- SonarQube server en cours d'exécution sur http://localhost:9001
- dotnet-sonarscanner installé globalement : `dotnet tool install --global dotnet-sonarscanner`
- Token SonarQube valide avec permissions d'analyse

## Procédure d'analyse complète

### 1. Préparation de l'environnement
```powershell
# Charger les variables d'environnement
$env:SONAR_HOST_URL="http://localhost:9001"
$env:SONAR_TOKEN="squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df"
$env:SONAR_PROJECT_KEY="healthplatform"

# Se placer dans le dossier de la solution
Set-Location Api\Mail

# Créer le répertoire de résultats de tests
if (Test-Path "TestResults") { Remove-Item -Path "TestResults" -Recurse -Force }
New-Item -ItemType Directory -Path "TestResults" -Force
```

### 2. Démarrage de l'analyse SonarQube
```powershell
dotnet sonarscanner begin `
    /k:"healthplatform-api-mail" `
    /d:sonar.host.url="http://localhost:9001" `
    /d:sonar.token="squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df" `
    /d:sonar.sourceEncoding=UTF-8 `
    /d:sonar.verbose=true `
    /d:sonar.exclusions="**/devops/**,**/load-tests/**,**/AppHost/**" `
    /d:sonar.cs.opencover.reportsPaths="TestResults/**/coverage.opencover.xml" `
    /d:sonar.coverage.exclusions="**/obj/**,**/bin/**,**/tests/**,**/AppHost/**,**/Infrastructure.Mock/**"
```

### 3. Construction du projet
```powershell
# Build de la solution complète
dotnet build HealthPlatform.Api.Mail.sln --configuration Release --verbosity quiet
```

### 4. Exécution des tests avec couverture
```powershell
# Tous les projets de test (format OpenCover pour SonarQube)
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
dotnet sonarscanner end /d:sonar.token="squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df"
```

## Résolution des problèmes courants

### Problème avec les warnings NuGet et AutoMapper
Si vous rencontrez des erreurs liées aux vulnérabilités AutoMapper (NU1903), vous pouvez temporairement désactiver `TreatWarningsAsErrors` dans `Directory.Build.props` :

```xml
<TreatWarningsAsErrors>false</TreatWarningsAsErrors>
<NuGetAudit>false</NuGetAudit>
```

**Important** : Réactivez ces paramètres après l'analyse pour maintenir la qualité du code.

### Problème avec docker-compose.dcproj
Le projet docker-compose peut causer des erreurs lors du build de la solution complète. Utilisez les projets individuels plutôt que la solution complète.

### Vérification des rapports de couverture
```powershell
# Vérifier que les rapports OpenCover ont été générés
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
4. **Restaurer la configuration stricte** après l'analyse (TreatWarningsAsErrors=true)
5. **Nettoyer les anciens résultats** avant chaque nouvelle analyse

## Script d'automatisation rapide

Pour une analyse complète en une seule commande :

```powershell
# Analyse SonarQube complète (à exécuter depuis Api/Mail)
$env:SONAR_HOST_URL="http://localhost:9001"
$env:SONAR_TOKEN="squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df" 
$env:SONAR_PROJECT_KEY="healthplatform-api-mail"

# Nettoyage et préparation
if (Test-Path "TestResults") { Remove-Item -Path "TestResults" -Recurse -Force }
New-Item -ItemType Directory -Path "TestResults" -Force

# Analyse SonarQube
dotnet sonarscanner begin /k:"healthplatform-api-mail" /d:sonar.host.url="http://localhost:9001" /d:sonar.token="squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df" /d:sonar.sourceEncoding=UTF-8 /d:sonar.exclusions="**/devops/**,**/load-tests/**,**/AppHost/**" /d:sonar.cs.opencover.reportsPaths="TestResults/**/coverage.opencover.xml" /d:sonar.coverage.exclusions="**/obj/**,**/bin/**,**/tests/**,**/AppHost/**,**/Infrastructure.Mock/**"

# Build et tests
dotnet build HealthPlatform.Api.Mail.sln --configuration Release --verbosity quiet
$testProjects = @("tests/mss.mail.domain.tests/mss.mail.domain.tests.csproj", "tests/mss.mail.application.tests/mss.mail.application.tests.csproj", "tests/mss.mail.infrastructure.tests/mss.mail.infrastructure.tests.csproj", "tests/mss.mail.api.tests/mss.mail.api.tests.csproj", "tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj")
foreach ($proj in $testProjects) { dotnet test $proj --configuration Release --collect:"XPlat Code Coverage;Format=opencover" --results-directory TestResults --logger "console;verbosity=minimal" }

# Finalisation
dotnet sonarscanner end /d:sonar.token="squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df"

Write-Host "✓ Analyse SonarQube terminée - Vérifiez les résultats sur http://localhost:9001"
```

## Compte rendu des KPI après analyse

À la fin de chaque analyse SonarQube, récupérer et afficher les KPI sous forme de tableau markdown :

```powershell
# Attendre le traitement du rapport par SonarQube
Start-Sleep -Seconds 10

# Récupérer les métriques
$metrics = "bugs,vulnerabilities,code_smells,coverage,line_coverage,branch_coverage,duplicated_lines_density,ncloc,sqale_index,reliability_rating,security_rating,sqale_rating,security_hotspots"
$result = Invoke-RestMethod -Uri "http://localhost:9001/api/measures/component?component=healthplatform-api-mail&metricKeys=$metrics" -Headers @{Authorization="Bearer squ_4cdebf15496a5b8ea6c5b19406cadd3f0aee73df"}

# Construire un dictionnaire des mesures
$measures = @{}
$result.component.measures | ForEach-Object { $measures[$_.metric] = $_.value }

# Fonctions utilitaires (noms longs pour éviter les conflits avec les alias PowerShell comme R=Invoke-History)
# Compatible PowerShell 5.1 (pas d'opérateur ?? ni de null-coalescing)
function GetMetric($key) { if ($measures[$key]) { $measures[$key] } else { 'N/A' } }
function GetRating($key) { $val = $measures[$key]; if ($val) { @('','A','B','C','D','E')[[int][double]$val] } else { 'N/A' } }

# Afficher le tableau
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

**Format attendu du compte rendu :**

| Métrique                    | Valeur |
|-----------------------------|--------|
| Lignes de code (ncloc)      | xxxx   |
| Couverture globale          | xx.x%  |
| Couverture lignes           | xx.x%  |
| Couverture branches         | xx.x%  |
| Bugs                        | x      |
| Vulnérabilités              | x      |
| Security Hotspots           | x      |
| Code Smells                 | x      |
| Dette technique (min)       | x      |
| Duplication                 | x.x%   |
| Fiabilité (Rating)          | A-E    |
| Sécurité (Rating)           | A-E    |
| Maintenabilité (Rating)     | A-E    |

## Accès aux résultats
- **Interface SonarQube** : http://localhost:9001
- **Projet** : healthplatform-api-mail
- **Rapports de couverture** : Api/Mail/TestResults/**/coverage.opencover.xml