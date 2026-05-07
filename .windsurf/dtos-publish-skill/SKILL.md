---
name: dtos-publish
description: **WORKFLOW SKILL** — Commit + push automatique du dépôt `HealthPlatform.Dtos.Mss` à chaque modification d'un DTO. Le projet `Dtos/` est un sous-repo Git distinct dont la publication NuGet est déclenchée par un push GitHub. Sans ce push, les consommateurs (mss.mail.api, Blazor, psc-auth-proxy) ne peuvent pas récupérer la nouvelle version du contrat. USE FOR&nbsp;: ajouter un champ à un DTO, modifier une enum partagée, créer un nouveau DTO. INVOKES&nbsp;: git status / add / commit / push.
applyTo:
  - "Dtos/**/*.cs"
  - "Dtos/**/*.csproj"
---

# DTOs publish skill

Le dossier `Dtos/` est un dépôt Git **indépendant** (`origin =
https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss.git`).
Le package NuGet `HealthPlatform.Dtos.Mss` est publié par la CI GitHub à chaque
push. Tant que le push n'a pas eu lieu, l'API backend, le shell Blazor et les
proxies (`psc-auth-proxy`) consomment la version précédente et ne peuvent pas
référencer les nouveaux champs.

## Quand déclencher ce skill

Dès qu'un fichier sous `Dtos/` est ajouté, modifié ou supprimé :

- nouveau DTO (`*.cs`)
- ajout / suppression / renommage d'une propriété sur un DTO existant
- mise à jour de `HealthPlatform.Dtos.Mss.csproj` (version, dépendances)
- changement d'enum partagée (`AuditActionType`, `MailEnrichmentStatus`,
  `UrgencyLevel`, etc.)

## Procédure obligatoire

1. **Vérifier l'état du sous-repo**

   ```powershell
   git -C d:\TechWatch\HealthPlatform\Dtos status --short
   git -C d:\TechWatch\HealthPlatform\Dtos rev-parse --abbrev-ref HEAD
   ```

2. **Confirmer la branche cible** avec l'utilisateur si elle diffère de la
   branche feature en cours (ex. `feat/task-017-impression-export-email-audit`).
   Ne jamais pousser sur `master` / `main` sans accord explicite.

3. **Stager uniquement les fichiers DTO modifiés** (jamais `bin/`, `obj/`,
   `artifacts/`)&nbsp;:

   ```powershell
   git -C d:\TechWatch\HealthPlatform\Dtos add <fichiers explicites>
   ```

4. **Commit avec un message conventionnel** (préfixe `feat`, `fix`, `chore`)
   décrivant le changement de contrat&nbsp;:

   ```powershell
   git -C d:\TechWatch\HealthPlatform\Dtos commit -m "feat(dto): add AttachmentCount on MailDto"
   ```

5. **Push sur l'origine GitHub**&nbsp;:

   ```powershell
   git -C d:\TechWatch\HealthPlatform\Dtos push origin <branche-courante>
   ```

   Si la branche n'existe pas encore distante, ajouter `--set-upstream`.

6. **Attendre la fin de la CI GitHub Actions** (workflow `.NET` du repo
   `HealthPlatform.Dtos.Mss`). C'est elle qui pack + push le package NuGet
   sur `https://nuget.pkg.github.com/codengine-technologies`. Tant qu'elle
   n'est pas `success`, **ne pas mettre à jour les références consommateurs**.

   ```powershell
   # Récupérer le SHA du commit que l'on vient de pousser
   $sha = git -C d:\TechWatch\HealthPlatform\Dtos rev-parse HEAD

   # Récupérer l'ID du run associé à ce SHA (peut prendre quelques secondes
   # pour apparaître après le push)
   $runId = gh run list `
       --repo codengine-technologies/HealthPlatform.Dtos.Mss `
       --commit $sha --limit 1 --json databaseId --jq '.[0].databaseId'

   # Bloquer jusqu'à la fin du run (exit code != 0 si la CI échoue)
   gh run watch $runId --repo codengine-technologies/HealthPlatform.Dtos.Mss --exit-status
   ```

   Si la CI échoue, **arrêter le skill** et remonter l'erreur à
   l'utilisateur (lien `gh run view <id> --web`). Ne pas modifier les
   `Directory.Packages.props`.

7. **Récupérer la version NuGet publiée** (le workflow utilise
   `-p:Version=${{ github.run_number }}` ⇒ la version vaut `<run_number>`,
   stockée comme `<run_number>.0.0` côté NuGet) :

   ```powershell
   $runNumber = gh run view $runId `
       --repo codengine-technologies/HealthPlatform.Dtos.Mss `
       --json number --jq '.number'
   $nugetVersion = "$runNumber.0.0"
   ```

8. **Mettre à jour les références consommateurs** (systématique, dès que la
   CI a réussi). Le bump est appliqué **sans demander confirmation** à
   l'utilisateur, même pour un changement cosmétique : cela garantit que
   tous les consommateurs convergent vers la dernière version publiée et
   évite la fragmentation des versions consommées. La version est
   centralisée par `Directory.Packages.props`, donc un seul fichier par
   solution est à modifier. Cibles **obligatoires**&nbsp;:

   - `Api/Mail/Directory.Packages.props` (mss.mail.api)
   - `Client/Blazor/Directory.Packages.props` (shell Blazor)

   Pour chaque fichier, remplacer la ligne&nbsp;:

   ```xml
   <PackageVersion Include="HealthPlatform.Dtos.Mss" Version="<ancienne>" />
   ```

   par la nouvelle valeur `$nugetVersion`. **Ne pas toucher** aux autres
   `Directory.Packages.props` (ex.&nbsp;: `psc-auth-proxy`) qui ne sont pas
   dans ce workspace.

   Si l'un des fichiers est déjà à `$nugetVersion` (cas d'un re-run sans
   nouveau commit DTO), passer à l'étape suivante sans modification.

9. **Commiter la bump dans CHAQUE repo consommateur** (multi-repo, pas un
   monorepo). `Api/Mail` et `Client/Blazor` sont des repos Git distincts,
   gitignorés par `HealthPlatform.Forge` (cf. `.gitignore` du repo parent,
   entrées `Api/` et `Client/`). Il faut donc commiter dans leurs roots
   respectifs, jamais dans `HealthPlatform.Forge`&nbsp;:

   ```powershell
   # Mail API
   git -C d:\TechWatch\HealthPlatform\Api\Mail add Directory.Packages.props
   git -C d:\TechWatch\HealthPlatform\Api\Mail commit -m "chore(deps): bump HealthPlatform.Dtos.Mss to $nugetVersion"

   # Blazor
   git -C d:\TechWatch\HealthPlatform\Client\Blazor add Directory.Packages.props
   git -C d:\TechWatch\HealthPlatform\Client\Blazor commit -m "chore(deps): bump HealthPlatform.Dtos.Mss to $nugetVersion"
   ```

   **Important** : ne stager **que** `Directory.Packages.props`. Les
   `packages.lock.json` peuvent contenir du travail en cours et seront
   régénérés au prochain `dotnet restore --force-evaluate` ; ne pas les
   inclure dans ce commit.

   Le push reste à la discrétion de l'utilisateur (souvent regroupé avec
   les changements de code consommateurs sur la même branche feature).

10. **Informer l'utilisateur** dans le message de réponse&nbsp;:
    - Hash du commit DTO produit + branche / repo cible.
    - ID du run CI + statut (`success`).
    - Version NuGet publiée (`<run_number>.0.0`).
    - Liste des `Directory.Packages.props` mis à jour (ou raison de ne pas
      les avoir touchés).

## Garde-fous

- **Toujours utiliser `git -C d:\TechWatch\HealthPlatform\Dtos`** : le repo
  parent (`HealthPlatform.Forge`) ne doit pas recevoir les changements DTO.
- **Ne jamais committer en parallèle dans les deux repos** dans le même appel
  de tool : faire d'abord le sous-repo, ensuite le repo principal pour les
  changements consommateurs.
- **Ne pas régénérer de fichiers `.md` de documentation** dans ce repo (rule
  utilisateur).
- Si l'utilisateur a des commits non poussés sur la branche, **ne jamais
  forcer un `--force`**. Demander confirmation.

## Outils MCP / CLI disponibles

- `mcp3_git_status`, `mcp3_git_add`, `mcp3_git_commit` (sur `repo_path =
  d:/TechWatch/HealthPlatform/Dtos`).
- Le push n'est pas exposé par le MCP&nbsp;: utiliser `run_command` avec
  `git push` (commande non destructrice mais qui mute l'état distant, donc
  jamais en `SafeToAutoRun=true`).
- `gh` (GitHub CLI) pour la CI&nbsp;: `gh run list`, `gh run watch`,
  `gh run view`. Authentification via `gh auth status` (token déjà
  configuré). Les commandes `gh run *` en lecture sont sûres en
  `SafeToAutoRun=true`.

## Pré-requis CI

- `gh` doit être installé et authentifié sur le compte ayant accès au repo
  `codengine-technologies/HealthPlatform.Dtos.Mss`.
- Le workflow `.NET` (`.github/workflows/dotnet.yml`) publie sur
  `nuget.pkg.github.com/codengine-technologies` avec `Version =
  github.run_number`. Si le workflow change (ex.&nbsp;: schéma de version
  semver), mettre à jour le calcul de `$nugetVersion` ci-dessus.

## Exemple complet (cas typique : ajout d'une propriété)

```powershell
# 1. État
git -C d:\TechWatch\HealthPlatform\Dtos status --short

# 2. Stage du seul fichier modifié
git -C d:\TechWatch\HealthPlatform\Dtos add MailDto.cs

# 3. Commit
git -C d:\TechWatch\HealthPlatform\Dtos commit -m "feat(dto): add AttachmentCount on MailDto"

# 4. Push
$branch = 'feat/task-017-impression-export-email-audit'
git -C d:\TechWatch\HealthPlatform\Dtos push origin $branch

# 5. Attendre la CI
$sha = git -C d:\TechWatch\HealthPlatform\Dtos rev-parse HEAD
Start-Sleep -Seconds 5  # laisser le temps à GitHub d'enregistrer le run
$runId = gh run list --repo codengine-technologies/HealthPlatform.Dtos.Mss `
    --commit $sha --limit 1 --json databaseId --jq '.[0].databaseId'
gh run watch $runId --repo codengine-technologies/HealthPlatform.Dtos.Mss --exit-status

# 6. Récupérer la version NuGet publiée
$runNumber = gh run view $runId --repo codengine-technologies/HealthPlatform.Dtos.Mss `
    --json number --jq '.number'
$nugetVersion = "$runNumber.0.0"

# 7. Bump dans le repo consommateur (Mail API)
# Editer Api/Mail/Directory.Packages.props : remplacer la version par $nugetVersion
# puis :
git -C d:\TechWatch\HealthPlatform add Api/Mail/Directory.Packages.props
git -C d:\TechWatch\HealthPlatform commit -m "chore(deps): bump HealthPlatform.Dtos.Mss to $nugetVersion"
```
