# todo-task-305.md — Le SDK redevient un paquet de backend : retirer `HealthPlatform.Host.Sdk` de `client-blazor`, qui n'en consomme rien et en a dupliqué le code

**Repos**: client-blazor
**Dependencies**: — (aucune ; US autonome, **préalable à task-299**)
**Epic**: E016
**Priorité**: **1** — préalable à E016. Tant que Blazor référence le SDK, tout contrat de
plateforme publié dedans (task-299, task-300) part dans la charge utile WASM du navigateur et
impose un bump de version à un consommateur qui ne s'en sert pas.

## Objective

Que `HealthPlatform.Host.Sdk` soit un paquet **strictement backend**, avec `api-mail` pour seul
consommateur. `client-blazor` cesse de le référencer — il n'en consomme **aucun membre** et a
déjà sa propre implémentation des deux services concernés.

### Constat — vérifié dans le code, pas supposé

| Fait | Preuve |
|---|---|
| **Blazor n'appelle jamais `AddSdk`** | `AddSdk` n'apparaît nulle part dans `Client/Blazor/Src` — seul `AddShellService` est appelé (`Src/Shell/Program.cs:63`) |
| Donc `IResilientCacheService` n'est **ni enregistré ni consommé** | unique occurrence dans tout Blazor : la ligne de commentaire `Src/Shell/Extensions/ServiceCollectionExtensions.cs:23` qui affirme le contraire — **le commentaire est faux** (reliquat de task-218) |
| Le `using` du SDK est **mort** | `Src/Shell/Extensions/ServiceCollectionExtensions.cs:2` — `using HealthPlatform.Host.Sdk.Services;` ; aucun type du SDK n'est utilisé dans le fichier |
| `IMarkdownService` / `MarkdownService` sont **dupliqués** dans Blazor | `Src/Component/Shared/Services/IMarkdownService.cs` + `Src/Modules/Mss/Plugin/Services/MarkdownService.cs`, enregistrés en `AddScoped<IMarkdownService, MarkdownService>()` — les 7 `@inject IMarkdownService` résolvent **le contrat Blazor**, jamais celui du SDK |
| `ICacheService` est **dupliqué** aussi | `Src/Component/Shared/Services/ICacheService.cs` + `InMemoryCacheService` — contrat différent de celui du SDK, task-218 l'avait déjà noté |
| L'assembly part bien dans le navigateur | `HealthPlatform.Components.Shared.csproj` porte `<SupportedPlatform Include="browser" />` |
| Le SDK y traîne ses propres dépendances | `Markdig`, **`Microsoft.Extensions.Caching.StackExchangeRedis`**, `Microsoft.Extensions.Configuration.Abstractions` — un client Redis embarqué dans une application WASM |

**Bilan : la référence est morte.** Elle ne coûte pas seulement de la charge utile — elle impose
un bump de version à chaque publication du SDK et elle a laissé croire (task-299, première
rédaction) que le SDK était contraint par le navigateur, ce qui a failli faire sortir des
contrats de plateforme du paquet où ils ont leur place.

### ⚠️ Le piège : **deux** paquets arrivent transitivement par le SDK

> **Corrigé à l'implémentation (2026-09-13).** Cette section n'en annonçait qu'un et le
> qualifiait de « seul effet de bord réel » — c'était faux, le build l'a montré au retrait.

1. **`Markdig`** — réellement utilisé. `Src/Modules/Mss/Plugin/Services/MarkdownService.cs:1` fait
   `using Markdig;` alors qu'**aucun `PackageReference Markdig` n'existe dans `client-blazor`**.
   Déclaré explicitement **avant** le retrait, pour que le build ne soit jamais rouge.
2. **`Microsoft.Extensions.Caching.StackExchangeRedis`** — servait l'unique
   `AddStackExchangeRedisCache` de `Src/Shell/Extensions/ServiceCollectionExtensions.cs`. Vérifié
   à l'implémentation : cet enregistrement est **inerte**. Aucun `IDistributedCache` n'est injecté
   nulle part dans `client-blazor`, il n'y a ni session ASP.NET, ni output cache, ni backplane
   SignalR, et `AddDataProtection()` (`Program.cs:57`) est **en mémoire**. Le seul consommateur
   possible aurait été le `CacheService` du SDK, enregistré par `AddSdk` — jamais appelé ici.
   **Retiré** avec son paramètre `IConfiguration`, devenu sans objet (appelant unique mis à jour),
   conformément à ce que la section Conformité annonçait déjà : « un client de cache distribué
   **et sa configuration**, qui n'y avaient aucun usage ».

### Ce que ce n'est pas

Ni une unification des deux `IMarkdownService` / `ICacheService` (Blazor garde les siens : ce sont
eux qui sont utilisés), ni une modification du SDK lui-même, ni un changement de comportement
applicatif — le retrait de `AddStackExchangeRedisCache` n'en est pas un : **rien ne consommait**
le service qu'il enregistrait (démonstration au §Piège). La clé `RedisConnectionString` est
laissée telle quelle dans `appsettings*.json` : la retirer toucherait la surface de déploiement
pour un gain nul.

## Definition of Done

- [x] `Markdig` déclaré **explicitement** dans `client-blazor` (`Directory.Packages.props` +
      `PackageReference` du projet qui l'utilise), à la version que le SDK apportait
      jusqu'ici (`0.40.0`) — **fait avant** le retrait, pour que le build ne soit jamais rouge
- [x] `<PackageReference Include="HealthPlatform.Host.Sdk" />` retiré de
      `Src/Component/Shared/HealthPlatform.Components.Shared.csproj`
- [x] `<PackageVersion Include="HealthPlatform.Host.Sdk" ... />` retiré de
      `Client/Blazor/Directory.Packages.props`
- [x] `using HealthPlatform.Host.Sdk.Services;` retiré de
      `Src/Shell/Extensions/ServiceCollectionExtensions.cs`
- [x] Le commentaire faux de ce même fichier (« `IResilientCacheService` est enregistré par
      `AddSdk` ») **corrigé ou supprimé** — `AddSdk` n'est pas appelé dans ce dépôt. Ne pas
      laisser une affirmation fausse derrière soi : c'est elle qui a masqué le fait que la
      référence était morte
- [x] Test / vérification : plus **aucune** occurrence de `HealthPlatform.Host.Sdk` dans
      `Client/Blazor` (hors commentaires documentant le retrait). Livré comme **garde-fou
      anti-récidive** et non comme grep ponctuel : `SdkReferenceGuardTests` (2 tests — paquet et
      `using`), **vérifié en réinjectant la régression** (rouge, pointant
      `Directory.Packages.props:8`), et protégé du faux vert par un `Assert.NotEmpty` sur
      l'énumération des fichiers
- [x] `dotnet build HealthPlatform.Client.sln` → 0 erreur ; `dotnet test HealthPlatform.Client.sln`
      → 0 échec (les 7 `@inject IMarkdownService` continuent de résoudre le contrat Blazor)
- [x] Aucune régression fonctionnelle : le rendu Markdown (corps de mail, synthèse, chat IA,
      timeline) est inchangé — c'est le même `MarkdownService` Blazor qu'avant

## Manual Test Plan

- **Lancer** : `cd Client/Blazor && dotnet run --project Src/Shell` (ou le Shell habituel), avec
  `api-mail` démarré (`cd Api/Mail && aspire run --project src/AppHost`).
- **Écran / URL** : la messagerie, sur un mail dont le corps est en Markdown, puis la synthèse
  clinique et le panneau de chat IA.
- **Ce que l'humain doit voir** :
  1. Le corps de mail, la synthèse et les réponses du chat s'affichent **en HTML rendu**
     (gras, listes, liens) — exactement comme avant. C'est la preuve que `Markdig` est toujours là.
  2. La page de gestion (`ManagementPage`) et la timeline de documents rendent leur Markdown.
  3. Aucune erreur dans la console du navigateur, aucun avertissement de résolution de service
     au démarrage.
  4. Optionnel, mais parlant : comparer la taille du dossier `_framework` publié avant / après
     (`dotnet publish`) — le retrait de `Microsoft.Extensions.Caching.StackExchangeRedis` et de
     ses dépendances doit se voir.
- **Données de test** : aucune donnée réelle nécessaire — un mail de démonstration suffit.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — hygiène de dépendances
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient touchée
- **Authentification PS** : inchangée — aucun code d'authentification modifié
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Sécurité / confidentialité** : **amélioration** — retire de la charge utile livrée au
  navigateur un client de cache distribué (`StackExchangeRedis`) et sa configuration, qui n'y
  avaient aucun usage. Réduire la surface expédiée au poste du praticien est un gain net
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangée — aucun traitement, aucune donnée

## Branches

- `client-blazor` (pushed) : `chore/task-305-retirer-sdk-de-blazor` — base `origin/develop` @ d4a0730
  https://github.com/codengine-technologies/HealthPlatform.Client/tree/chore/task-305-retirer-sdk-de-blazor
- `dtos-mss` (pushed, auto-inclus par la regle CLAUDE.md) : `chore/task-305-retirer-sdk-de-blazor` — base `origin/develop` @ f20f310
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/chore/task-305-retirer-sdk-de-blazor
  **Aucun changement de contrat attendu** : cette US ne touche qu'une reference de paquet dans
  Blazor. La branche restera sans commit et **aucune PR ne sera ouverte** pour ce repo.

> Prefixe `chore/` : hygiene de dependances — ni fonctionnalite, ni correction de bug visible.

## PRs

- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/73
  — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — branche auto-incluse, **0 commit** (aucun changement de contrat,
  comme le prévoyait la section `## Branches`)

## Code Review Summary

**APPROVED** — 8 fichiers revus, **0 bloquant**, 2 suggestions.

Build `HealthPlatform.Client.sln` : 0 erreur, 0 avertissement. Tests : **184 réussis, 0 échec**,
2 ignorés (skips préexistants de `BiologyAckPanelComponentTests`).

### Écart par rapport au fichier de task, assumé et documenté

Le §Piège n'annonçait **qu'une** dépendance transitive (`Markdig`) et la qualifiait de « seul
effet de bord réel ». Le build en a révélé une **seconde** au retrait :
`Microsoft.Extensions.Caching.StackExchangeRedis`, qui servait l'unique `AddStackExchangeRedisCache`
du Shell. Vérification faite, cet enregistrement est **inerte** (aucun `IDistributedCache` injecté,
ni session, ni output cache, ni backplane SignalR, `AddDataProtection()` en mémoire) : il a été
retiré plutôt que réalimenté par une déclaration de paquet — ce que la section Conformité
annonçait déjà (« un client de cache distribué **et sa configuration**, qui n'y avaient aucun
usage »). Le fichier de task a été corrigé en conséquence.

### Suggestions non bloquantes (hors périmètre — `/review` est en lecture seule sur le code)

1. **`ClientSensitiveDataScanTests` peut passer à vide.** Ce garde-fou de sécurité (task-184 :
   INS dans les URLs, journalisation nominative) n'assert pas que son énumération de fichiers est
   non vide : si `git ls-files` échouait, il passerait **sans rien garder**. Le nouveau
   `SdkReferenceGuardTests` s'en protège par un `Assert.NotEmpty` ; l'ancien mérite le même,
   d'autant qu'il partage désormais le helper `RepoScan`. **Faiblesse préexistante**, non
   introduite par cette task — candidate naturelle à une task d'hygiène.
2. **Deux résidus morts possibles** : `Microsoft.AspNetCore.DataProtection.StackExchangeRedis`
   reste déclaré alors qu'`AddDataProtection()` (`Program.cs:57`) est en mémoire ; et trois
   `using` de `ServiceCollectionExtensions.cs` (`Ardalis.Result`, `System.Net`,
   `System.Net.Http.Headers`) ne correspondent à aucun type du fichier après nettoyage.

## Merged

- **Date** : 2026-09-13, sur attestation humaine `--i-tested`
- `client-blazor` : PR [#73](https://github.com/codengine-technologies/HealthPlatform.Client/pull/73)
  **squash-mergée** sur `develop` — commit `d3fd8581029f74c83c19c78219e1a2f46f016f79`
  (`d3fd858`). Référence distante `chore/task-305-retirer-sdk-de-blazor` supprimée ;
  **branche locale conservée** (piège `gh pr merge --delete-branch`, qui supprime aussi le local).
- `dtos-mss` : aucune PR (branche auto-incluse sans commit). Référence distante
  `chore/task-305-retirer-sdk-de-blazor` supprimée par hygiène ; local sur `develop`.
- `client-angular` : hors périmètre de cette task et hors périmètre de `/merge` — aucune
  opération git.
- Branche staging : **aucune** — task-305 n'est pas issue d'un run `/forge`.

> ⚠️ **CI `develop` non observée verte.** Le merge a déclenché la suppression de la ref distante
> et la synchronisation locale, mais **aucun run GitHub Actions n'était apparu sur `develop`**
> après ~3 min 30 de sondage (dernier run `develop` connu : `d4a0730`, 2026-09-08, succès —
> le merge précédent avait bien déclenché son run `push`). Le critère « CI verte sous 2 min »
> (CLAUDE.md règle 5) n'est donc **ni validé ni infirmé** : à vérifier à la main sur
> l'onglet Actions du dépôt.

## Timings

*(généré par `tools/timing/report.sh --task task-305 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 40 s | — | — | — | — |
| /develop | ok | 10 min 30 s | 4 (1 min 16 s) | 4 (52 s) | — | client-blazor 4B/4T |
| /review | ok | 2 min 51 s | 2 (12 s) | 1 (11 s) | — | client-blazor 1B/1T, dtos-mss 1B/0T |
| /tech-writer | ok | 3 min 30 s | — | — | — | — |
| **Total cycle** | | **17 min 33 s** | **6 (1 min 29 s)** | **5 (1 min 03 s)** | **0 (0.0 s)** | |
