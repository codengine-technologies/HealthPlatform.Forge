# todo-task-217.md — Le SDK expose des entrées/sorties Redis synchrones qui échappent au budget de 500 ms de son propre disjoncteur

> ### ⚠️ Périmètre restreint après chiffrage — lire avant tout
>
> L'inventaire a donné **64 appels** sur **52 fichiers** (26 de production, 26
> de tests), au-dessus du plafond de ~30 fichiers par PR de la **règle 5**.
> Découpé en **deux US indépendantes**, chacune fonctionnellement complète donc
> mergeable seule (règle 11 respectée) :
>
> | US | Périmètre | Taille |
> |---|---|---|
> | **task-217 (celle-ci)** | Le chemin **mesuré** : les 3 membres `Try*` d'`IResilientCacheService`, qui **échappent au budget de 500 ms** — 7 155 timeouts à 5 000 ms au banc. Plus les tests du SDK, la publication et le bump des consommateurs. | ~12 fichiers |
> | **task-218** | Les 58 appels d'`ICacheService`, et son **retrait** | ~40 fichiers |
>
> **Conséquence directe** : task-217 **ne peut pas** retirer `ICacheService` —
> ses 58 appelants ne compileraient plus. Elle le marque `[Obsolete]` avec le
> motif et le renvoi vers task-218. Le SDK garde donc de l'I/O synchrone à
> l'issue de cette US, et **c'est assumé** : ce qui est retiré ici est l'I/O
> synchrone **qui sort du budget de temps**, c'est-à-dire la seule dont on ait
> la preuve qu'elle nuit.

**Repos**: sdk, api-mail, client-blazor
**Epic**: E015
**Single frontend**: false
**Dependencies**: aucune bloquante. task-205 (mergée) a **diagnostiqué** ce
défaut et l'a contourné sans le corriger ; task-215 (PR #143) l'a re-mesuré
sous charge.
**Priorité**: **1** — c'est le plus gros levier de capacité encore identifié, et
un **contaminant de toute mesure future** : confirmer des correctifs de latence
pendant qu'un appel bloquant de 5 s reste sur le chemin de requête, c'est
mesurer à travers un défaut qui les domine.

> **Ce défaut a déjà été trouvé, mesuré, et délibérément non corrigé.**
> `SafeCacheExtensions` (api-mail, task-205) le dit en toutes lettres : « On ne
> touche pas au contrat du SDK (republication NuGet + impact `client-blazor` /
> `host`) : on descend d'une couche sur `IDistributedCache` ». Cette US lève ce
> report.

## Objective

Qu'aucun appel au cache distant passant par `IResilientCacheService` ne puisse
dépasser le budget de temps que le SDK s'est lui-même donné — aujourd'hui, la
moitié de ses membres en sortent d'un facteur dix.

Objectif d'ensemble, atteint avec task-218 : plus aucune I/O synchrone dans le
SDK.

## Le défaut — et il y en a deux, pas un

### 1. Des allers-retours réseau bloquants sur un thread du pool

| Membre | Fichier | Descend sur |
|---|---|---|
| `ICacheService.Get<T>` / `Set<T>` / `Remove` | `Services/CacheService.cs` | `IDistributedCache.GetString` / `SetString` / `Remove` |
| `IResilientCacheService.TryGet<T>` / `TrySet<T>` / `TryRemove` | `Services/ResilientCacheService.cs:155,186,215` | idem |

Tous finissent sur `StackExchange.Redis.RedisBase.ExecuteSync` — un aller-retour
réseau **bloquant**, exécuté sur un thread de travail du ThreadPool.

### 2. Le plus grave : ces chemins échappent au budget de 500 ms

`ResilientCacheService` se donne un `_operationTimeout` de **500 ms** et
l'applique — par `CancellationTokenSource.CreateLinkedTokenSource` +
`CancelAfter` — dans `GetAsync`, `SetAsync` et `RemoveAsync`. **Les variantes
`Try*` ne l'appliquent pas.** Elles héritent donc du défaut de
StackExchange.Redis : **5 000 ms**.

Autrement dit : le disjoncteur existe pour **borner la latence du cache**, et la
voie synchrone sort de cette borne d'un facteur **dix**. C'est exactement ce que
le banc observe — `Timeout performing HMGET (5000ms)`, jamais 500.

### Ce que les deux mesures établissent

| Campagne | Constat |
|---|---|
| **2026-07-31** (task-205) | **10 des 35 threads applicatifs** des 5 réplicas parqués dans `ExecuteSync` — moitié sous `UserSettingsRepository.GetSettingsAsync`, moitié sous `SearchHistoryService.Record`. Piles jointes au rapport (`reports/2026-07-31/stacks-170058/`) |
| **2026-08-02** (task-215) | **7 155 `RedisTimeoutException`** (HMGET, 5 000 ms) **+ 4 474 `RedisConnectionException`** sur trois tirs, depuis `MailController.GetEmailAsync` → `ResilientCacheService.TryGet<T>` |

C'est la **même classe de défaut que celle retirée par task-205** du chemin
`read_list` (`IMailStore.GetFolder` synchrone) — à ceci près qu'elle vit dans le
SDK, ce qui est précisément pourquoi elle a survécu.

## Ce qu'il ne faut PAS présumer

- **« Retirer tout ce qui est synchrone » ne veut pas dire « tout passer en
  `async` ».** `IMarkdownService.ToHtml` est **calculatoire**, pas I/O :
  l'envelopper dans une `Task` serait du faux asynchrone — un changement de
  contrat qui coûte une allocation et n'affranchit aucun thread. Il **reste
  synchrone**, et cette décision doit être écrite.
  Idem pour `IsAvailable` et `GetHealthStatus()` : état en mémoire.
- **`ICacheService` ne survivra pas, mais pas ici.** Il n'a **ni budget de
  temps, ni disjoncteur, ni tolérance à la panne** — au point qu'api-mail a dû
  écrire `SafeCacheExtensions` pour l'entourer de `try/catch`.
  `IResilientCacheService` fait déjà tout cela. Son retrait est **task-218**
  (58 appelants) ; ici on se contente de le marquer `[Obsolete]` pour qu'aucun
  nouvel appelant n'apparaisse entre les deux US.
- **Ne pas présumer que l'impact sur `client-blazor` est lourd.** Vérifié : le
  seul point de contact est **une ligne d'enregistrement DI**
  (`Src/Shell/Extensions/ServiceCollectionExtensions.cs:20`). Blazor possède par
  ailleurs son **propre** `ICacheService` (`Src/Component/Shared/Services/`),
  sans rapport avec celui du SDK — ne pas les confondre.
- **Ne pas présumer que `host` est concerné.** Le CLAUDE.md racine annonce que
  `host` consomme le SDK ; **c'est faux aujourd'hui** — aucun `.csproj` de
  `Host/Modules` ne le référence. Vérifié. À corriger dans le CLAUDE.md.
- **Ne pas toucher au contournement de task-205 ici.** Les variantes
  `SafeGetAsync` / `SafeSetAsync` / `SafeRemoveAsync` de `SafeCacheExtensions`
  deviendront redondantes, mais leur retrait appartient à **task-218**, avec la
  garde qui va avec : prouver qu'une entrée écrite par une voie reste lisible
  par l'autre — le commentaire de task-205 affirme reproduire « exactement » la
  sérialisation du SDK (JSON par défaut, valeur en string), et si c'est faux la
  bascule invalide silencieusement le cache en production.

## Contenu attendu

1. **SDK** — l'I/O synchrone qui échappe au budget disparaît :
   - `IResilientCacheService` : `TryGet` / `TrySet` / `TryRemove` **retirés**
     (les équivalents async existent déjà et portent le budget de 500 ms) ;
   - `ICacheService` / `CacheService` : marqués **`[Obsolete]`** avec le motif
     — pas de budget de temps, pas de disjoncteur, I/O bloquante — et le renvoi
     vers task-218 qui les retire. **Pas de retrait ici** : 58 appelants.
   - `ServiceCollectionExtensions.AddSdk` inchangé tant qu'`ICacheService` vit.
2. **Le budget de temps devient une propriété vérifiable, pas un champ privé.**
   Aujourd'hui `_operationTimeout`, `_circuitBreakerThreshold` et
   `_circuitBreakerDuration` sont des `readonly` codés en dur, et rien ne prouve
   qu'ils sont appliqués. Un test doit établir qu'**aucun** chemin du SDK ne
   peut dépasser le budget.
3. **Des tests dans le SDK — il n'en a aucun.** Un paquet partagé qui porte un
   disjoncteur, un budget de temps et des compteurs de santé, sans un seul test,
   est l'endroit exact où une régression passe inaperçue. Créer le projet de
   tests et l'ajouter au CLAUDE.md racine (colonne « Test cmd » de `sdk`,
   aujourd'hui `n/a`).
4. **Publication + bump** — la CI du SDK (`.github/workflows/dotnet.yml`)
   package avec `-p:Version=${{github.run_number}}`, donc la version est le
   **numéro de run**, un entier (`N` → `N.0.0`). Attendre la publication, puis
   bumper `Directory.Packages.props` :
   - `api-mail` : **8.0.0** → version publiée ;
   - `client-blazor` : **7.0.0** → version publiée. ⚠️ **Il a une majeure de
     retard** : le saut embarque aussi les changements de la 8.0.0, qu'il n'a
     jamais reçus. À vérifier avant de bumper, pas après.
5. **api-mail** — les **6 appels mesurés** migrés vers l'async, tous déjà
   situés dans des méthodes `async` :
   `MailController` (`:374` `TryGet`, `:385` `TrySet`, `:411` `TryGet`,
   `:421` `TrySet`) et `MailCacheInvalidator` (`:35`, `:36` `TryRemove`).
   Les 58 appels d'`ICacheService` et le retrait des variantes redondantes de
   `SafeCacheExtensions` sont **hors périmètre** — task-218.
6. **client-blazor** — impact attendu : **le seul bump de version**.
   `ICacheService` survit à cette US, donc l'enregistrement DI
   (`Src/Shell/Extensions/ServiceCollectionExtensions.cs:20`) ne change pas.
   Build + tests verts restent exigés : c'est ce qui prouve que le bump de
   **deux majeures** (7.0.0 → version publiée) ne casse rien.

## Hors scope

- `IMarkdownService.ToHtml` — calculatoire, reste synchrone.
- Le réglage des valeurs du disjoncteur (500 ms, 5 échecs, 30 s) : cette US
  **applique** le budget existant, elle ne le rediscute pas.
- Le tir de confirmation de capacité — c'est la phase suivante du plan, sur la
  baseline valide qui reste à produire.

## Definition of Done

- [ ] Build passes (0 erreur) et tests verts sur **les trois repos**
- [ ] Aucun membre d'`IResilientCacheService` ne fait d'I/O synchrone — garde
      par test, pas par relecture
- [ ] Test : **aucun** chemin de cache ne dépasse le budget de 500 ms, y compris
      quand le serveur ne répond pas (constaté RED sur le binaire actuel, où
      `TryGet` attend 5 000 ms)
- [ ] Test : le disjoncteur s'ouvre après 5 échecs consécutifs et se referme
- [ ] `ICacheService` / `CacheService` marqués `[Obsolete]`, motif et renvoi
      vers task-218 écrits sur place
- [ ] `IMarkdownService.ToHtml` **inchangé**, avec la raison écrite sur place
- [ ] Projet de tests du SDK créé et **inscrit au CLAUDE.md racine**
- [ ] Compatibilité de sérialisation prouvée par un test : une entrée écrite par
      l'ancienne voie reste lisible par la nouvelle
- [ ] `Directory.Packages.props` bumpé dans api-mail **et** client-blazor, sur
      la version réellement publiée par la CI
- [ ] CLAUDE.md racine corrigé : `host` ne consomme pas le SDK
- [ ] Tests **constatés RED avant le correctif** (preuve dans le `## Develop log`)

### Dû au banc (ne bloque pas la PR, bloque la clôture de l'US)

- [ ] Tir 500 praticiens : **0** `RedisTimeoutException` à 5 000 ms — toute
      attente de cache est désormais coupée à 500 ms
- [ ] Aucun thread applicatif parqué dans `ExecuteSync` (contrôle par pile, sur
      le modèle de task-205)

## Manual Test Plan

**Lancer api-mail** (profil normal, Redis requis) :

```bash
cd Api/Mail
dotnet run --project src/AppHost
```

**Écran / URL** : la messagerie, ouverture d'un message déjà consulté (chemin
`GET /api/v1/mail/folders/INBOX/emails/content/{uid}`, celui qui portait
`TryGet`).

**Ce que l'humain doit voir** :
- le message s'affiche, servi depuis le cache, sans régression visible ;
- après un **`docker stop`** du conteneur Redis : le message s'affiche
  **toujours** (repli sur la source), et la réponse ne prend **pas** 5 secondes
  — c'est le cœur de l'US ;
- au redémarrage de Redis, le cache reprend (disjoncteur refermé), trace
  `[Cache] ✅ Cache recovered` dans les logs.

**Blazor** : `cd Client/Blazor && dotnet run` — vérifier que l'application
démarre (l'impact attendu est une seule ligne d'enregistrement DI).

**Données de test** : compte de développement, aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — robustesse et performance internes.
- **Exigences DSR honorées** : aucune nouvelle. L'US ne change aucun contrat
  fonctionnel ni aucun écran.
- **INS** : non manipulée. **Authentification PS** : inchangée.
- **Habilitations** : ⚠️ **point de vigilance**. Les clés de cache portent
  l'email du praticien (`mail:email:{email}:{dossier}:{uid}`,
  `usersettings:{hash}`). Toute réécriture de la couche de cache doit
  **conserver le cloisonnement par clé** — une clé dont le praticien
  disparaîtrait ferait servir le message d'un praticien à un autre. Un test doit
  le garder.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun évènement métier touché. ⚠️ Les journaux de cache
  écrivent la **clé**, qui contient un email — comportement **existant**, à ne
  pas aggraver ; ne pas y ajouter de contenu de message.
- **Consentement patient** : non applicable.
- **Hébergement HDS** : non applicable — pas de nouvelle donnée persistée.
- **AIPD / impact RGPD** : inchangé. Durées de conservation du cache
  inchangées (60 min absolu / 30 min glissant).

## Branches
- `sdk` (pushed) : fix/task-217-sdk-async-cache
- `api-mail` (pushed) : fix/task-217-sdk-async-cache
- `client-blazor` (pushed) : fix/task-217-sdk-async-cache
- `dtos-mss` (pushed, auto-inclus) : fix/task-217-sdk-async-cache — aucun contrat attendu

> Ordre de construction cross-repo imposé : **sdk → publication NuGet → bump des
> consommateurs → api-mail / client-blazor**. Le SDK doit être publié par sa CI
> avant que les consommateurs puissent compiler contre le nouveau contrat.

## Develop log

### Ce que le travail a fait apparaître, et qui n'était pas dans l'énoncé

**1. Le `.csproj` du SDK compilait le projet de tests DANS le paquet publié.**
Il n'a aucun `Compile` explicite : il globbe donc `**/*.cs` depuis la racine du
dépôt. Constaté au premier build — les erreurs pointaient le SDK alors que le
code fautif était dans `tests/`. Exclusion ajoutée.

**2. La CI du SDK ne lançait aucun test** et ne construisait que le `.csproj`
racine. Étape `dotnet test` ajoutée, cibles rendues explicites, `dotnet pack`
restreint au SDK. **Pas de fichier solution à dessein** : `dotnet new sln`
produit désormais un `.slnx` que le SDK 9.0.x du runner ne sait pas forcément
lire — on construit donc le projet de **tests**, qui entraîne le SDK par
référence.

**3. Le `[Obsolete]` a été posé puis retiré.** api-mail compile avec
`TreatWarningsAsErrors` : `CS0618` y devient une **erreur**, sur 26 fichiers. Le
taire aurait demandé 26 `#pragma` ou un `NoWarn` global — qui aurait aussi
masqué les *nouveaux* appelants, c'est-à-dire exactement ce que l'attribut
devait empêcher. **L'attribut appartient à la PR qui retire l'interface**
(task-218), pas à celle d'avant. La raison est écrite dans la doc XML.

**4. Le poste n'a pas de credential GitHub Packages**, donc le paquet publié
n'était pas restaurable. Première validation faite contre un `.nupkg` packé
localement depuis le commit exact publié — puis **refaite contre le paquet
réel** après que l'humain a autorisé l'usage du jeton `gh` (scope
`write:packages`), employé **en ligne** sans transiter par un fichier ni par la
conversation. **La précaution était justifiée** : le `contentHash` du pack local
(`KPkHHC6SK0jR/…`) diffère de celui de GitHub Packages (`syljtnUFb+TpA4ZRG63/…`).
Committer le premier aurait fait échouer les deux CI consommatrices en `NU1403`.
Piège à connaître : NuGet **ne retélécharge pas** un paquet déjà présent dans le
cache global — il a fallu purger `~/.nuget/packages/healthplatform.host.sdk/10.0.0`
pour obtenir le vrai.

**5. Deux versions publiées, 9.0.0 puis 10.0.0.** La CI package avec
`-p:Version=${{github.run_number}}` et se déclenche sur `pull_request` : chaque
poussée sur la PR publie une version. La 9.0.0 portait le `[Obsolete]`, la
10.0.0 ne le porte plus. C'est la 10.0.0 qui est consommée.

### Tests constatés RED avant le correctif (DOD)

```
ResilientCacheBudgetTests.TheSynchronousCachePathIsGone(retired: "TryGet")    [FAIL]
ResilientCacheBudgetTests.TheSynchronousCachePathIsGone(retired: "TrySet")    [FAIL]
ResilientCacheBudgetTests.TheSynchronousCachePathIsGone(retired: "TryRemove") [FAIL]
ResilientCacheBudgetTests.EveryCacheOperationOnTheContractIsAsynchronous      [FAIL]
Failed!  - Failed: 4, Passed: 10, Total: 14
```

Les 10 autres **caractérisent l'existant avant modification** — disjoncteur,
distinction manque/panne, et compatibilité de sérialisation dans les deux sens,
cette dernière étant une garde destinée à task-218.

### Résultats

| Repo | Build | Tests |
|---|---|---|
| `sdk` | ✅ | **14 réussis**, 0 échec (aucun test n'existait) |
| `api-mail` | ✅ | **3 259 réussis**, 0 échec, 103 ignorés |
| `client-blazor` | ✅ | **144 réussis**, 0 échec, 2 ignorés |

### Réserve signalée — sans rapport avec cette US

`client-blazor` ne restaure pas, **ni avec ni sans ce bump** : `NU1902`,
AngleSharp 1.2.0 porte une vulnérabilité connue et `NuGetAudit` est en
warning-as-error. **Vérifié identique sur `develop`** en remisant le changement.
Build et tests joués avec `-p:NuGetAudit=false`. Sa CI sera donc rouge pour
cette raison. À traiter dans une US dédiée.

## PRs
- `sdk` : https://github.com/codengine-technologies/HealthPlatform.Host.Sdk/pull/1 — label `awaiting-human-merge` (label créé, il n'existait pas dans ce dépôt)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/145 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/66 — label `awaiting-human-merge`
- `dtos-mss` : branche sans commit, aucune PR

> **Ordre de merge imposé** : `sdk` d'abord (le paquet 10.0.0 est déjà publié,
> donc les deux autres peuvent en réalité merger sans attendre), puis `api-mail`
> et `client-blazor` dans n'importe quel ordre.

## Suite
- `todo-task-218.md` — retrait d'`ICacheService` et de ses 58 appelants.
- US à créer : la vulnérabilité AngleSharp de `client-blazor`.

## Merged (partiel — assumé)

- `sdk` : **894e9fb** — squash de la PR #1, mergée le 2026-08-02. Ref distant supprimé.
- `api-mail` : **08d893f** — squash de la PR #145, mergée le 2026-08-02. Ref distant supprimé.
- `client-blazor` : **PR #66 laissée OUVERTE**.

### Pourquoi un merge partiel, et pourquoi c'est licite

La CI de `client-blazor` échoue — **`NU1902`, AngleSharp 1.2.0, transitif de
`bunit`**. Vérifié en remisant le changement : **le rouge préexiste sur
`develop`**, il n'est imputable ni au bump ni à cette US.

`/merge` aurait refusé (barrière n° 4, CI rouge) et il est tout-ou-rien par
task : le CLAUDE.md renvoie explicitement au merge à la main pour ce cas.

Retenir le correctif **mesuré** — 7 155 timeouts à 5 000 ms — derrière une
vulnérabilité qui rougissait `develop` avant nous n'aurait servi personne. Et la
règle 11 est respectée : **task-217 est fonctionnellement complète sans le bump
Blazor**, puisque Blazor n'appelle aucun des membres retirés. Son bump est de
l'hygiène de version, pas de la fonction.

### Résolu le jour même

`task-219` a levé le rouge AngleSharp (mergée, **2f46bf5**). La PR #66 a ensuite
été débloquée par une fusion de `develop` (rule 4, merge et non rebase), sa CI
est passée verte, et elle a été **mergée : 522021a**.

**task-217 est donc complète sur les trois repos** :
- `sdk` : 894e9fb
- `api-mail` : 08d893f
- `client-blazor` : 522021a

Le merge partiel n'aura duré que le temps de corriger une vulnérabilité qui
préexistait à l'US.

⚠️ **Interaction à connaître avant de lancer task-218** : la PR #66 modifie
`Client/Blazor/Directory.Packages.props`. Si task-218 rebumpe le SDK sur ce même
fichier depuis une autre branche, les deux PR entreront en conflit. Deux issues :
traiter task-219 puis merger #66 avant task-218, ou exclure `client-blazor` du
périmètre de task-218 et le bumper dans un second temps.
