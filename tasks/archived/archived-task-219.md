# todo-task-219.md — La CI de `client-blazor` est rouge sur `develop` : une vulnérabilité AngleSharp remontée en erreur par NuGetAudit

**Repos**: client-blazor
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune.
**Priorité**: **1** — ce n'est pas la gravité de l'avis qui presse, c'est que
**`develop` est rouge**. Toute PR ouverte sur ce dépôt hérite d'une CI en échec,
donc plus aucune n'est jugeable sur son propre mérite. C'est déjà le cas de la
PR #66 de task-217.

> **Ce défaut n'a pas été introduit par une US : il est apparu tout seul.**
> `NuGetAudit` compare les dépendances au fil des avis publiés. Le code n'a pas
> bougé ; c'est l'avis qui est arrivé.

## Objective

Que `dotnet restore` réussisse sur `client-blazor` sans neutraliser l'audit, et
que la CI de `develop` redevienne verte.

## Le défaut, qualifié

```
error NU1902: Warning As Error: Package 'AngleSharp' 1.2.0 has a known moderate
severity vulnerability — HealthPlatform.Module.Mss.Plugin.Tests
```

| Fait | Valeur |
|---|---|
| Avis | [GHSA-pgww-w46g-26qg](https://github.com/advisories/GHSA-pgww-w46g-26qg) — *mXSS via `annotation-xml` HTML Integration Point Bypass* |
| Sévérité | **moyenne** |
| Versions vulnérables | `< 1.5.0` |
| **Première version corrigée** | **1.5.0** |
| Version présente | **1.2.0**, **transitive** de `bunit` 1.40.0 |
| Portée | **un seul projet**, `HealthPlatform.Module.Mss.Plugin.Tests` (144 tests) |
| Exposition production | **aucune** — AngleSharp n'entre que par le moteur de rendu de test de bunit |

**Vérifié sur `develop` sans aucune modification locale** : le rouge préexiste,
il n'est imputable à aucune PR ouverte.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que « c'est du test, donc on supprime l'avis ».**
  L'exposition est nulle en production, mais un `NuGetAuditSuppress` posé une
  fois ne se relit jamais : le jour où AngleSharp entre par un chemin de
  production, l'audit se taira aussi. Si cette voie est retenue, elle doit être
  **datée et bornée**, avec la condition explicite de sa levée.
- **Ne pas présumer que monter `bunit` est neutre.** Il porte les 144 tests de
  composants du module MSS. Vérifier d'abord si une version de `bunit`
  dépend d'AngleSharp ≥ 1.5.0 — et à quel prix en changements d'API.
- **Ne pas présumer que forcer AngleSharp est sans risque non plus.** bunit
  1.40.0 est compilé contre 1.2.0 ; monter la dépendance transitive à 1.5.0
  suppose une compatibilité binaire que **seuls les 144 tests peuvent
  démontrer**. C'est précisément ce qui rend cette voie testable.
- **Ne pas présumer que le problème est isolé à ce dépôt.** api-mail résout déjà
  AngleSharp **1.5.0** par un autre chemin. Vérifier avant de conclure que
  `client-blazor` est le seul concerné.

## Les trois voies, à trancher par écrit

| Voie | Geste | Ce qu'elle coûte |
|---|---|---|
| **A — forcer la transitive** *(recommandée)* | `<PackageVersion Include="AngleSharp" Version="1.5.0" />` + `<PackageReference>` explicite dans le projet de test | Une ligne. Le risque de compatibilité binaire avec bunit est **démontrable** par les 144 tests |
| **B — monter `bunit`** | Vers une version dépendant d'AngleSharp ≥ 1.5.0 | Plus propre sur le fond, mais change le socle de test — API, comportements de rendu |
| **C — qualifier l'avis** | `NuGetAuditSuppress` daté et borné | Ne corrige rien, et éteint le signal. À réserver au cas où A et B échouent |

## Contenu attendu

1. La voie retenue, appliquée, et **l'argument écrit dans le `.csproj` ou les
   `Directory.Packages.props`** — pas seulement dans le commit.
2. Les deux voies écartées, chacune avec sa raison.
3. Si la voie C est retenue : une **date de revue** et la condition de levée,
   écrites sur place.

## Hors scope

- Toute autre alerte d'audit qui apparaîtrait sur un autre dépôt : une US par
  dépôt, sinon le correctif devient une chasse sans fin.
- Le bump du SDK de task-217 (PR #66), qui merge une fois ce rouge levé.

## Definition of Done

- [ ] `dotnet restore HealthPlatform.Client.sln` réussit **sans**
      `-p:NuGetAudit=false`
- [ ] Build passes (0 erreur) — **144 tests verts**, 2 ignorés
- [ ] La voie retenue et les deux écartées sont écrites dans le dépôt
- [ ] La CI de `develop` est **verte** après merge
- [ ] Aucun `NuGetAuditSuppress` non daté

## Manual Test Plan

```bash
cd Client/Blazor
dotnet restore HealthPlatform.Client.sln     # doit réussir SANS -p:NuGetAudit=false
dotnet build HealthPlatform.Client.sln
dotnet test HealthPlatform.Client.sln
dotnet run
```

**Ce que l'humain doit voir** :
- le `restore` passe sans neutraliser l'audit — c'est le critère ;
- 144 tests verts, 2 ignorés ;
- l'application démarre et la messagerie s'affiche.

**Données de test** : compte de développement, aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — hygiène de dépendances.
- **Exigences DSR honorées** : aucune nouvelle.
- **INS** : non manipulée. **Authentification PS** : inchangée.
- **Habilitations** : inchangées.
- ⚠️ **Sécurité** : l'avis porte sur un **mXSS** dans un analyseur HTML. Son
  exposition est aujourd'hui nulle — AngleSharp n'entre que par le moteur de
  rendu de test. C'est ce qui rend l'urgence faible **et** la suppression de
  l'avis tentante ; c'est aussi pourquoi une suppression non datée serait le
  mauvais geste.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun évènement touché.
- **Hébergement HDS** : non applicable.
- **AIPD / impact RGPD** : inchangé.

## Branches
- `client-blazor` (pushed) : fix/task-219-anglesharp-audit — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-219-anglesharp-audit
- `dtos-mss` (pushed, auto-inclus par la règle du CLAUDE.md) : fix/task-219-anglesharp-audit — aucun contrat attendu, US d'hygiène de dépendances

> Pré-flight : `client-blazor` et `dtos-mss` étaient restés sur
> `fix/task-217-sdk-async-cache`. Branches de forge, poussées, arbres propres →
> rebasculées sur `develop` sous l'autorisation donnée par l'humain pour cette
> session. La PR #66 reste ouverte et intacte.

## Develop log

### Voie retenue (DOD 1 et 2)

**Voie A — remonter la transitive**, appliquée. `<PackageVersion Include="AngleSharp" Version="1.5.0" />` dans
`Directory.Packages.props` + `<PackageReference Include="AngleSharp" />` dans le
projet de test. L'arbitrage complet, avec les deux voies écartées et la
condition de retrait, est écrit **dans les deux fichiers**, pas seulement dans
le commit.

**Ce qui fait de A la bonne voie, et pas seulement la plus courte** : le seul
risque réel est la compatibilité binaire de `bunit` 1.40.0 avec une AngleSharp
plus récente que celle contre laquelle il a été compilé. Ce risque est
**démontrable** — 144 tests de composants en dépendent. Ils sont tous verts.
Les deux autres voies se seraient jugées sur parole.

**Voie B écartée** : la dernière version de `bunit` est **2.8.6**, une majeure
complète au-dessus de la 1.40.0 utilisée ici (vérifié sur l'index nuget.org).
Migration du socle de test, pas correctif de vulnérabilité.

**Voie C écartée** : `NuGetAuditSuppress` ne corrige rien et éteint le signal.

### Résultats

| Contrôle | Résultat |
|---|---|
| `dotnet restore` **sans** `-p:NuGetAudit=false` | ✅ réussit — c'est le critère de l'US |
| Build | ✅ 0 erreur, 0 avertissement |
| Tests | ✅ **144 réussis**, 2 ignorés |
| CI de la PR | ✅ build pass, `mergeStateStatus: CLEAN` |

### Aucun `NuGetAuditSuppress` posé

Le DOD l'exigeait : aucun n'a été introduit, et l'avis est réellement corrigé,
pas masqué.

## PRs
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/67 — label `awaiting-human-merge`
- `dtos-mss` : branche sans commit, aucune PR

## Suite
Une fois #67 mergée, la PR **#66** (bump SDK de task-217) se débloque : il suffit
d'y fusionner `develop` pour qu'elle passe au vert. Puis **task-218**.

> **Observation de processus** : la règle d'auto-inclusion de `dtos-mss` a créé
> ici une **troisième** branche vide inutile — cette US est un correctif de
> dépendance sur un dépôt frontend, aucun contrat DTO n'est concevable. Ces
> branches vides sont précisément ce qui a fait échouer trois pré-flights
> aujourd'hui. À arbitrer : restreindre l'auto-inclusion aux US qui touchent du
> code, ou nettoyer la branche à l'archivage.

## Merged
- `client-blazor` : **2f46bf5** — squash de la PR #67, mergée le 2026-08-02
- `dtos-mss` : aucune PR (branche sans commit)

Refs distants supprimés sur les deux repos, **y compris la branche vide de
`dtos-mss`** — voir l'observation de processus ci-dessus. Branches locales
conservées côté `client-blazor`.

> **Effet immédiat** : la CI de `develop` sur `client-blazor` est de nouveau
> verte, et la PR #66 (bump SDK, task-217) a pu être débloquée par une fusion de
> `develop`.
