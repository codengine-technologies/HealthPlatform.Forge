# /publish-dtos — Publish DTO package and update consumer projects

Publish the shared DTO NuGet package (`HealthPlatform.Dtos.Mss`) to GitHub Packages
and update the version in all consumer projects.

## Steps

1. Read the current version from `Dtos/HealthPlatform.Dtos.Mss.csproj`
2. Increment the major version (X.0.0 → X+1.0.0), or use the version passed as argument
3. Update the `<Version>` in the .csproj
4. Build and pack: `dotnet pack Dtos --configuration Release --output Dtos/artifacts -p:Version={version}`
5. Publish: `dotnet nuget push Dtos/artifacts/*.nupkg --api-key $GITHUB_TOKEN --source https://nuget.pkg.github.com/codengine-technologies/index.json --skip-duplicate`
6. Update the version in both `Directory.Packages.props`:
   - `Api/Mail/Directory.Packages.props`
   - `Client/Directory.Packages.props`
7. Restore both projects: `dotnet restore Api/Mail` and `dotnet restore Client`
8. Commit and push the DTO repo:
   ```bash
   cd Dtos && git add -A && git commit -m "feat(dtos): bump to {version}" && git push
   ```
9. Report the new version number

## Prerequisites

- `GITHUB_TOKEN` or `GITUB_TOKEN_CODENGINE` environment variable must be set

## Usage

```
/publish-dtos           # auto-increment
/publish-dtos 165.0.0   # force specific version
```
