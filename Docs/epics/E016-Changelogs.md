# E016 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Document frère (vue produit)** : [`E016-socle-multi-tenant.md`](./E016-socle-multi-tenant.md)
> **Dernière mise à jour** : 2026-09-13

Historique détaillé des changements de l'EPIC **E016 — Socle multi-tenant**.
Une entrée par task ayant atteint `done-*` ou `archived-*`. Append-only : une
entrée existante n'est jamais réécrite.

---

## Historique détaillé des changelogs

### v1.0 — task-305 : `HealthPlatform.Host.Sdk` retiré de `client-blazor`

**Statut** : `done` — PR [HealthPlatform.Client#73](https://github.com/codengine-technologies/HealthPlatform.Client/pull/73), label `awaiting-human-merge`
**Branche** : `chore/task-305-retirer-sdk-de-blazor` (base `origin/develop` @ `d4a0730`)
**Repos** : `client-blazor` (3 commits) ; `dtos-mss` (auto-inclus, **0 commit**, pas de PR)
**Cycle mesuré** : 14 min 02 s au total — `/start` 40 s, `/develop` 10 min 30 s (4 builds / 4 suites), `/review` 2 min 51 s (2 builds / 1 suite)

#### Objet

Le SDK redevient un paquet **strictement backend**, avec `api-mail` pour seul
consommateur. Préalable à task-299 : tant que `client-blazor` le référençait, tout
contrat de plateforme publié dedans (`ITenantRegistryClient`, `IAuditSink`) partait
dans la charge utile WASM du navigateur et imposait un bump de version à un
consommateur qui n'en consommait rien.

#### Constat — la référence était morte

| Fait | Preuve |
|---|---|
| `AddSdk` n'est **jamais** appelé dans `Client/Blazor/Src` | seul `AddShellService` l'est (`Src/Shell/Program.cs:63`) |
| Donc `IResilientCacheService` n'était ni enregistré ni injecté | unique occurrence dans le dépôt : le commentaire de `Src/Shell/Extensions/ServiceCollectionExtensions.cs:23` affirmant le contraire — **faux**, reliquat de task-218 |
| `using HealthPlatform.Host.Sdk.Services;` mort | `Src/Shell/Extensions/ServiceCollectionExtensions.cs:2`, aucun type du SDK utilisé dans le fichier |
| `IMarkdownService` / `MarkdownService` dupliqués | `Src/Component/Shared/Services/IMarkdownService.cs` + `Src/Modules/Mss/Plugin/Services/MarkdownService.cs` ; les 7 `@inject IMarkdownService` résolvent le contrat Blazor |
| `ICacheService` dupliqué | `Src/Component/Shared/Services/ICacheService.cs` + `InMemoryCacheService` — contrat différent de celui du SDK |
| Assembly expédié au navigateur | `HealthPlatform.Components.Shared.csproj` porte `<SupportedPlatform Include="browser" />` |

#### Deux dépendances transitives — le fichier de task n'en annonçait qu'une

Le §Piège de `todo-task-305.md` qualifiait `Markdig` de « seul effet de bord réel ».
**C'était faux**, et le build l'a montré au retrait. Le task file a été corrigé.

1. **`Markdig`** — réellement utilisé par `Src/Modules/Mss/Plugin/Services/MarkdownService.cs:1`
   sans `PackageReference` propre. Déclaré explicitement **dans un commit séparé,
   avant le retrait** (`Directory.Packages.props` + `HealthPlatform.Module.Mss.Plugin.csproj`,
   version `0.40.0` — celle qu'apportait le SDK), pour que le build ne soit jamais rouge.
2. **`Microsoft.Extensions.Caching.StackExchangeRedis`** — alimentait l'unique
   `AddStackExchangeRedisCache` de `Src/Shell/Extensions/ServiceCollectionExtensions.cs`.
   Enregistrement **inerte**, vérifié : aucun `IDistributedCache` injecté dans
   `Client/Blazor/Src` (grep), pas de `AddSession` / `UseSession`, pas de
   `AddOutputCache`, pas de backplane SignalR, et `AddDataProtection()`
   (`Src/Shell/Program.cs:57`) est **en mémoire** (pas de `PersistKeysToStackExchangeRedis`).
   Le seul consommateur possible aurait été le `CacheService` du SDK, enregistré par
   `AddSdk` — jamais appelé. **Retiré** avec son paramètre `IConfiguration`, devenu
   sans objet (appelant unique mis à jour : `Program.cs:63`).

La clé `RedisConnectionString` est **laissée** dans `appsettings.json` /
`appsettings.Test.json` : la retirer toucherait la surface de déploiement pour un
gain nul.

#### Fichiers touchés

| Fichier | Changement |
|---|---|
| `Directory.Packages.props` | `-PackageVersion HealthPlatform.Host.Sdk 12.0.0` ; `+PackageVersion Markdig 0.40.0` |
| `Src/Component/Shared/HealthPlatform.Components.Shared.csproj` | `-PackageReference HealthPlatform.Host.Sdk` |
| `Src/Modules/Mss/Plugin/HealthPlatform.Module.Mss.Plugin.csproj` | `+PackageReference Markdig` |
| `Src/Shell/Extensions/ServiceCollectionExtensions.cs` | `using` morts retirés, `AddStackExchangeRedisCache` retiré, signature sans `IConfiguration`, commentaire faux de task-218 corrigé |
| `Src/Shell/Program.cs` | appelant unique de `AddShellService` mis à jour |
| `tests/…/SdkReferenceGuardTests.cs` | **nouveau** — garde-fou anti-récidive (2 tests) |
| `tests/…/RepoScan.cs` | **nouveau** — helper partagé (passe qualité) |
| `tests/…/ClientSensitiveDataScanTests.cs` | refactor : délègue `RepoRoot` / `git ls-files` à `RepoScan` |

#### Garde-fou anti-récidive

`SdkReferenceGuardTests` — 2 tests :
- `ProductionProjects_DoNotReferenceTheBackendSdk` : aucun `Include="HealthPlatform.Host.Sdk"`
  dans `Src/**/*.csproj` ni `Directory.Packages.props` ;
- `ProductionSources_DoNotImportTheBackendSdk` : aucun `HealthPlatform.Host.Sdk.` dans
  `Src/**/*.{cs,razor}`, **hors lignes de commentaire** — documenter le retrait est le
  sujet de la task.

Deux précautions méthodologiques :
- **Vérifié par réinjection de la régression** : la ligne `PackageVersion` remise dans
  `Directory.Packages.props` fait virer le test au rouge, en pointant
  `Directory.Packages.props:8`. Puis restauré.
- **Protégé du faux vert** par `Assert.NotEmpty(files)` : si `git ls-files` échouait ou
  si `RepoRoot()` se résolvait mal, les deux assertions passeraient **à vide**. Un test
  qui ne peut pas échouer est pire qu'un test absent.
- `tests/` est exclu du scan : ce fichier nomme le paquet, un guard qui échoue sur
  lui-même est du bruit.

#### Passe qualité (`/simplify`, sous-étape de `/develop`)

**Reuse** : les deux gardes de balayage du dépôt (task-184 données sensibles, task-305
référence SDK) avaient chacune leur copie de « remonter jusqu'au `.sln`, puis
`git ls-files` ». Extraites dans `RepoScan` (`RepoRoot()`, `TrackedFiles(root, filter)`).
Deux copies d'un helper de parcours dérivent, et la dérive est invisible puisque chaque
garde continue de passer sur ses propres termes. Refactor fidèle : filtre et sémantique
identiques (`Src/Modules/Mss/` + `.cs|.razor`), `IEnumerable` → `List` (consommé une fois
en `foreach`). **184 tests verts avant comme après.**

#### Validation

- `dotnet build HealthPlatform.Client.sln` : **0 erreur, 0 avertissement**
- `dotnet test HealthPlatform.Client.sln` : **184 réussis / 0 échec / 2 ignorés**
  (skips préexistants de `BiologyAckPanelComponentTests`)
- `dotnet build HealthPlatform.Dtos.Mss.csproj` : 0 erreur (branche sans commit)
- `/sonar`, `/lint-angular`, `/lint-mobile`, `/verify-visual` : **skipped** — repos non touchés

#### Code review — APPROVED, 0 bloquant, 2 suggestions

1. **`ClientSensitiveDataScanTests` peut passer à vide.** Ce garde-fou de sécurité
   (task-184 : INS dans les URLs, journalisation nominative) n'assert pas que son
   énumération de fichiers est non vide : si `git ls-files` échouait, il passerait
   **sans rien garder**. Le nouveau `SdkReferenceGuardTests` s'en protège ; l'ancien
   mérite le même `Assert.NotEmpty`, d'autant qu'il partage désormais `RepoScan`.
   **Faiblesse préexistante**, non introduite par cette task.
2. **Deux résidus morts possibles** : `Microsoft.AspNetCore.DataProtection.StackExchangeRedis`
   reste déclaré dans `Directory.Packages.props` alors qu'`AddDataProtection()`
   (`Program.cs:57`) est en mémoire ; et trois `using` de `ServiceCollectionExtensions.cs`
   (`Ardalis.Result`, `System.Net`, `System.Net.Http.Headers`) ne correspondent à aucun
   type du fichier après nettoyage. `/review` est en lecture seule sur le code —
   signalés, pas corrigés.

#### Dette laissée

- Les deux suggestions ci-dessus, candidates à une task d'hygiène.
- `RedisConnectionString` reste dans les `appsettings*.json` (choix assumé).

---

## Annexe A — Cartographie des briques applicatives

### Contrats de plateforme (à venir, task-299 / task-300)

| Brique | Emplacement prévu | Rôle |
|---|---|---|
| `ITenantRegistryClient` + DTOs | `Sdk/` — `HealthPlatform.Host.Sdk.TenantRegistry.V1` | Contrat du registre : comptes, messageries, tenants, dormance |
| `PostgresTenantRegistryClient` | `Api/Mail/src/Infrastructure/` | **Seule** implémentation ; test d'architecture garantit que le `DbContext` du registre n'est référencé nulle part ailleurs |
| `IAuditSink` / `IAuditReader` | `Sdk/` — `HealthPlatform.Host.Sdk.Audit.V1` | Contrat du journal mutualisé (écriture par lots / lecture scopée tenant) |

> **Nommage — piège connu.** `DirectoryController` (`api/v{version}/Directory`,
> `AnnuaireSanteService`) sert l'**Annuaire Santé de l'ANS** (`practitioners/search`,
> `specialties`, `professions`). Le registre de cet EPIC n'a rien à voir : ses
> identifiants portent **`TenantRegistry`**, jamais `Directory`, et il n'expose aucune
> route sous `/directory`.

### Briques touchées par task-305

| Brique | Emplacement | État |
|---|---|---|
| `RepoScan` | `Client/Blazor/tests/HealthPlatform.Module.Mss.Plugin.Tests/RepoScan.cs` | Helper partagé des gardes de balayage |
| `SdkReferenceGuardTests` | même répertoire | Garde-fou anti-récidive du retrait du SDK |
| `ServiceCollectionExtensions.AddShellService` | `Client/Blazor/Src/Shell/Extensions/` | Signature sans `IConfiguration` depuis task-305 |

---

## Annexe B — Inventaire fonctionnel (2026-09-13)

| Grandeur | Valeur |
|---|---|
| Tasks déclarant `**Epic**: E016` | 7 (299, 300, 301, 303, 304, 305, 306) |
| Tasks `done` | 1 (task-305) |
| Tasks `todo` | 6 |
| Questions ouvertes bloquantes | 1 (`questions/task-302.md` — identité et habilitation des administrateurs) |
| PRs ouvertes | 1 (HealthPlatform.Client#73, `awaiting-human-merge`) |
| Paquets NuGet publiés par l'EPIC | 0 |
| Consommateurs du SDK après task-305 | **1** (`api-mail`) — contre 2 avant |

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Apport | Repos | Statut |
|---|---|---|---|
| task-299 | Registre des tenants : comptes (`sub` Keycloak + RPPS), messageries, **tenants** (compte × messagerie, porteurs de la base isolée et de `TenantId`), horodatages de connexion et dormance. Contrat `ITenantRegistryClient` dans le SDK, implémentation Postgres dans `api-mail` | `sdk`, `api-mail` | 🔜 todo |
| task-300 | Journal d'audit en base commune : table partitionnée par mois, `TenantId` = id du **tenant**, RLS + rôles lecture/écriture séparés, purge planifiée s'appuyant sur `AuditRetentionPolicy.FamilyOf`, lecture double source transitoire | `sdk`, `api-mail` | 🔜 todo |
| task-301 | Reprise de l'historique d'audit à débit borné (≤ 4 bases simultanées), vérification par comptage par tenant, puis retrait de la table par tenant et de la configuration morte | `api-mail` | 🔜 todo |
| task-303 | Vague 1 multi-BAL : la boîte devient une sélection par requête validée contre le registre **et** l'identité PSC ; disparition des claims `mssEmail`/`mssSub`/`mssRpps` ; bascule = fin de session + nouvelle session (garde `SESSION_MAILBOX_MISMATCH`) ; `AuditActionType` + 5 membres | `sdk`, `api-mail` | 🔜 todo |
| task-304 | Vague 2 multi-BAL : onboarding par le registre, écran de sélection, avatar → sélecteur, gestion des comptes, purge totale de l'état à la bascule — parité Blazor / Angular / mobile. Inclut la remise à niveau de l'outillage de capture visuelle | `client-blazor`, `client-angular`, `client-mobile` | 🔜 todo |
| task-305 | **Le SDK redevient backend-only** : retrait de la référence morte dans `client-blazor`, déclaration explicite de `Markdig`, retrait de l'enregistrement Redis inerte, garde-fou anti-récidive | `client-blazor` | ✅ done |
| task-306 | Banc de charge multi-BAL : dimension « boîtes par compte » (défaut 1, iso E015), parcours avec bascule réelle (`/sync/logout` + rotation de session), restitution du coût de bascule et de la résolution de registre | `api-mail` | 🔜 todo |

### Question ouverte

| Fichier | Objet | Blocage |
|---|---|---|
| `questions/task-302.md` | Accès des administrateurs et de la sécurité au journal mutualisé | **Aucun modèle de rôles n'existe dans `api-mail`** : la politique globale est `RequireAuthenticatedUser()` seule (`Program.cs:133`) et le gate de rôle « Doctor » a été désactivé le 2026-05-11 (`BiologyAcksController.cs:15`). Ouvrir un accès transverse dans cet état le rendrait accessible à tout utilisateur authentifié, sur un historique porteur de données de santé de tout le parc |

---

*Document vivant, régénéré par la forge à chaque fin de cycle. La vue produit vit dans
[`E016-socle-multi-tenant.md`](./E016-socle-multi-tenant.md).*
