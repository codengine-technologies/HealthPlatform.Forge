# todo-task-210.md — Supprimer le cache synchrone du SDK : plus aucune porte bloquante vers Redis

**Repos**: api-mail, sdk, client-blazor
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-205 — **satisfaite** (PR #131 mergée le 2026-07-31, squash `06f8a62`)

> **Origine** : demande humaine du 2026-07-31, dans la continuité directe de
> task-205. La campagne de charge de l'EPIC a établi que le facteur limitant
> d'`api-mail` n'est ni le CPU, ni Postgres, ni Dovecot, mais **des threads du
> ThreadPool parqués sur des I/O bloquantes**. task-205 a fermé une de ces
> portes (`IMailStore.GetFolder`). Celle-ci ferme l'autre, la plus large : le
> **cache**.

## Objective

Supprimer du SDK toute API de cache synchrone, et migrer les **77 sites d'appel**
d'`api-mail` (dont 6 en code mort, à supprimer) sur les pendants asynchrones. À la fin de cette US, **il n'existe
plus aucun chemin de code permettant d'atteindre Redis en bloquant un thread
du pool** — parce que la méthode qui le permettait n'existe plus.

C'est une US de **dette de performance**, pas de fonctionnalité : aucun
comportement observable par le praticien ne change. La valeur est la capacité
du service sous charge.

### Ce qui est mesuré, et ce qui est déduit

Mesuré (task-204, escalier du 2026-07-29) : la file du ThreadPool passe de 11
à 432 éléments entre 486 et 972 req/s, **à CPU quasi constant** (1,19 cœur sur
24 pour le réplica le plus chargé). Ce n'est pas une famine de CPU, c'est du
blocage d'I/O.

Mesuré (banc du 2026-07-31, cité dans `SafeCacheExtensions.cs`) : sur les
5 réplicas, **10 des 35 threads applicatifs** étaient parqués exactement sur
`CacheService.Get` → `StackExchange.Redis.ExecuteSync`, moitié sous
`UserSettingsRepository.GetSettingsAsync`, moitié sous
`SearchHistoryService.Record`. Piles jointes au rapport de tir
(`reports/2026-07-31/stacks-170058/`).

**Mesuré (banc du 2026-07-31, après task-205)** : la migration de ces **deux**
sites a suffi à éteindre la famine — file ThreadPool de 159/132/131 à
**8/6/6/5/4** au palier 882, débit de 857,9 à **940,3 req/s** au palier 972.

Déduit, et **à ne pas surestimer** : que fermer les 71 sites restants produise
un gain supplémentaire. Rien ne l'indique — le gain de capacité semble déjà
encaissé. La valeur de cette US est la **garantie structurelle** (le défaut
devient irréproductible), pas un second saut de performance. Voir « Réserve
honnête » en fin de document.

### Le défaut, en une ligne de code

`Sdk/Services/CacheService.cs:9` — `cache.GetString(key)` sur un
`IDistributedCache` Redis descend jusqu'à `StackExchange.Redis.ExecuteSync` :
un aller-retour réseau **bloquant**, exécuté sur un thread de travail du
ThreadPool. L'interface `ICacheService` n'expose **que** ce mode : ses trois
méthodes sont synchrones, il n'y a aucune échappatoire pour l'appelant.

`IResilientCacheService` porte le même défaut sur trois de ses méthodes
(`TryGet` / `TrySet` / `TryRemove`, `ResilientCacheService.cs:155/186/215`) —
avec cette circonstance aggravante que ses pendants asynchrones
(`GetAsync` / `SetAsync` / `RemoveAsync`) **existent déjà juste au-dessus dans
le même fichier**.

## Décisions arbitrées avec l'humain (2026-07-31)

Trois décisions ont été prises avant rédaction ; elles cadrent l'implémentation
et ne sont pas à re-litiger par `/develop`.

| Décision | Choix retenu |
|---|---|
| **Périmètre** | `ICacheService` + `CacheService` **et** les 3 méthodes sync de `IResilientCacheService`. Le SDK ne doit plus laisser **aucune** porte synchrone vers Redis. |
| **Cible de migration** | **`IResilientCacheService` async** (`GetAsync` / `SetAsync` / `RemoveAsync`), déjà enregistré en singleton par `AddSdk`. Une seule abstraction de cache pour tout `api-mail`, avec timeout 500 ms + circuit breaker + métriques de santé. |
| **Découpage** | **1 US, 1 PR**, malgré ~60 fichiers touchés. Dépassement assumé du guide « ~30 fichiers max par PR » (règle 5) : voir « Dérogation à la règle 5 ». |

## Contenu attendu

### 1. SDK — supprimer la surface synchrone

- **Supprimer** `Sdk/Services/ICacheService.cs` et `Sdk/Services/CacheService.cs`.
- **Supprimer** `TryGet<T>`, `TrySet<T>`, `TryRemove` de `IResilientCacheService`
  (`IResilientCacheService.cs:11-15`) et de `ResilientCacheService`
  (`ResilientCacheService.cs:155-234`).
- **Retirer** `services.AddScoped<ICacheService, CacheService>()` de
  `Sdk/Extensions/ServiceCollectionExtensions.cs:15`. `AddStackExchangeRedisCache`
  et l'enregistrement singleton de `IResilientCacheService` restent.
- **Republier le SDK en version majeure** (`8.0.0` → `9.0.0`) : la suppression
  de types publics est une rupture de contrat.

### 2. `api-mail` — migrer les 71 sites d'appel restants

> **Inventaire recompté sur `develop` le 2026-07-31, après le merge de
> task-205.** Le comptage initial (« ~57 sites, 26 fichiers ») sous-estimait :
> le chiffre réel est **77 sites synchrones dans 15 fichiers**, sur **30
> fichiers** portant la dépendance. Commande de contrôle :
> `grep -rlE "ICacheService|IResilientCacheService" --include=*.cs Api/Mail/src`
> puis, par fichier, comptage de
> `SafeGet<|SafeSet\(|SafeRemove\(|\.TryGet<|\.TrySet\(|\.TryRemove\(|cacheService\.(Get<|Set\(|Remove\()`.

| Zone | Fichiers | Sites | Points durs |
|---|---|---|---|
| **`BaseRepository`** | `Infrastructure/Repository/BaseRepository.cs` | 0 | Diffuse le cache à ~15 repositories via les propriétés `CacheService` (`:28`) / `CacheServiceOrNull` (`:32`) et **3 constructeurs** (`:48`, `:55`, `:66`). N'appelle lui-même jamais le cache, mais c'est **le nœud** : le changer casse la compilation de tous les repositories d'un coup. |
| **Repositories** | `ContactRepository` **(12)**, `PatientRepository` (3), `UserSettingsRepository` (3) | **18** | ⚠️ **Correction du relevé initial** : `ContactRepository` est le **3ᵉ plus gros porteur de l'US**, pas un simple relais — il était classé « ne fait que porter la dépendance », c'est faux. Les ~10 autres repositories, eux, ne font effectivement que porter la dépendance via `BaseRepository`. |
| **Services applicatifs** | `ImapFolderService` **(16)**, `ImapService` **(13)**, `OcspValidationService` (5), `CrlValidationService` (2), `SyncCoverageService` (2), `AutoconfigService` (2), `MailboxQuotaService` (2), `BackgroundSyncService` (1) | **43** | Le gros du volume. Voir les cas nommés ci-dessous. |
| **Controllers / helpers** | `MailController:374/385/411/421` (4), `MailCacheInvalidator:35/36` (2) | **6** | Sites `Try*`, déjà dans des méthodes `async` : conversion directe. |
| **Code mort** | `FolderCacheManager` | **6** | À **supprimer**, pas à migrer (§ 3). |
| **Helpers** | `Application/Helpers/SafeCacheExtensions.cs` | **4** | Le trio synchrone disparaît ; le trio async ajouté par task-205 est à retarger ou supprimer. |
| **DI** | `Api/DependencyInjection.cs:25` | — | **Doublon** de la registration du SDK — `api-mail` réenregistre `ICacheService` par-dessus `AddSdk`. À supprimer. |

**Soit 77 sites, dont 6 à supprimer (code mort) → ~71 à migrer effectivement.**

**Cas nommés qui ne sont pas une substitution mécanique :**

- **`ImapService.TrySetCache<T>` (`:160`)** — helper **synchrone** privé enroulant
  `cacheService.Set` dans un `try/catch`. Devient `TrySetCacheAsync`, et ses
  appelants doivent l'`await` (aujourd'hui appelé en fire-and-forget implicite).
- **`BackgroundSyncService.InvalidateCoverageCache` (`:208`)** — méthode
  **synchrone** qui résout `ICacheService` depuis `IServiceProvider` puis
  `Remove`. Devient asynchrone ; son appelant doit l'`await`.
- **`SafeCacheExtensions`** — la tolérance au `null` (cache optionnel des
  constructeurs de `BaseRepository`) et la tolérance à la panne posées par
  **task-074** doivent être **préservées**. `ResilientCacheService` absorbe déjà
  les pannes en interne (retourne `default`, log, circuit breaker) ; la
  tolérance au `null` reste à porter, soit par des helpers retargetés sur
  `IResilientCacheService?`, soit en rendant la dépendance non-optionnelle.
- **Propagation du `CancellationToken`** — les méthodes async de
  `IResilientCacheService` en acceptent un. Il doit être **passé** partout où
  la méthode appelante en a déjà un, pas ignoré.

### 3. `FolderCacheManager` — code mort, à supprimer

`FolderCacheManager` (6 sites de cache) et `IFolderCacheManager` sont
**morts** : aucune registration DI (`Api/DependencyInjection.cs` ne les
mentionne pas), aucune injection en production, seul `FolderCacheManagerTests`
les instancie. **Supprimer les trois fichiers** plutôt que migrer 6 sites
d'appel que personne n'exerce.

### 4. `client-blazor` — une ligne, et un saut de version

- **Supprimer** `Client/Blazor/Src/Shell/Extensions/ServiceCollectionExtensions.cs:20`
  (`AddScoped<Host.Sdk.Services.ICacheService, CacheService>()`). C'est le
  **seul** usage du cache SDK côté Blazor : aucun consommateur n'injecte ce type.
- ⚠️ **Hors périmètre, ne pas y toucher** : `HealthPlatform.Components.Shared.Services.ICacheService`
  + `InMemoryCacheService` (`Shell.Wasm/Program.cs:17`) sont un **type
  homonyme mais distinct** — un cache in-memory côté WASM, sans Redis et sans
  I/O. Il reste tel quel.
- ⚠️ **Risque de version** : `client-blazor` est sur le SDK **7.0.0** quand
  `api-mail` est sur **8.0.0** (`Directory.Packages.props`). Le passage à
  `9.0.0` lui fait sauter **deux** majeures d'un coup. Le build Blazor est le
  garde-fou ; s'il casse pour une raison étrangère au cache, **s'arrêter et
  ouvrir `questions/task-210.md`** plutôt que d'élargir l'US.

### 5. Verrouiller par test

Une garde de non-régression qui **échoue si une API de cache synchrone
réapparaît**, sur le modèle de celle de task-205 (`ReadListNonBlockingTests`,
qui a été constatée RED avant correctif) :

- garde de **surface publique** (réflexion sur l'assembly du SDK) : ni
  `ICacheService`, ni `CacheService`, ni `TryGet`/`TrySet`/`TryRemove` sur
  `IResilientCacheService` ;
- garde d'**analyseur IL** : aucune référence de `mss.mail.application` /
  `mss.mail.infrastructure` / `mss.mail.api` à `IDistributedCache.Get`,
  `GetString`, `Set`, `SetString`, `Refresh` (les surcharges synchrones).

⚠️ **Leçon de la passe `/simplify` de task-205** : une garde par analyseur doit
d'abord **retrouver un témoin positif** (une référence légitime dont on sait
qu'elle existe) avant qu'on croie son verdict négatif. Sans témoin, un scanner
qui ne trouve plus rien annonce un succès à vide.

## Hors scope

- **Le `.GetAwaiter().GetResult()` de `BaseRepository.cs:115`** — task-205 l'a
  innocenté par la mesure (fast-path statique par processus : après le premier
  contact de chaque base, la tâche est déjà complétée). Réel, mais pas le
  facteur limitant. Une task pour lui-même si on veut solder le sync-over-async
  résiduel du démarrage.
- **`MailClientSession.cs:234`** (`DisconnectAsync().GetAwaiter().GetResult()`
  dans `Dispose`) et **`EmailFlagService.cs:44/67/77/89`** (`AddFlags`/
  `RemoveFlags` IMAP synchrones) — même famille, signalés par task-205,
  **une task chacun**.
- **Le cache in-memory de `client-blazor` WASM** — pas de réseau, pas de
  ThreadPool serveur.
- **`Sdk` cible `net9.0`** quand le reste du workspace est en .NET 10. Écart
  réel, **hors périmètre** : ne pas en profiter pour bumper le TFM au passage.
- **Le tir de banc de re-mesure** — c'est une session de banc, pas du code
  (voir « Ce qui restera dû »).

## Dépendance task-205 — levée le 2026-07-31

PR #131 **mergée** (squash `06f8a62`), task archivée en
`tasks/archived/archived-task-205.md`, `api-mail` et `dtos-mss` revenus sur
`develop` avec des arbres propres. **Le pre-flight de `/start` passe.**

Ce que task-205 a laissé sur `develop`, et qui conditionne cette US :

- **Deux sites déjà migrés** — `UserSettingsRepository.GetSettingsAsync` et
  `SearchHistoryService` — mais sur **`IDistributedCache` +
  `SafeCacheExtensions` async**, **pas** sur `IResilientCacheService`. La
  décision d'abstraction unique impose de **les converger** ici : ils sont donc
  à migrer une seconde fois, ce n'est pas du travail déjà fait.
- **`UserSettingsRepository` porte un repli synchrone** (`CacheServiceOrNull.SafeGet`
  quand `IDistributedCache` est absent, pour les constructeurs de test) — d'où
  ses 3 sites synchrones encore comptés dans l'inventaire ci-dessous. Ce repli
  disparaît avec la convergence.
- **`SafeCacheExtensions` porte les deux trios** : synchrone (`SafeGet`/`SafeSet`/
  `SafeRemove`, à supprimer) et asynchrone sur `IDistributedCache`
  (`SafeGetAsync`/`SafeSetAsync`/`SafeRemoveAsync`, ajouté par task-205, à
  retarger sur `IResilientCacheService` ou à supprimer selon la forme retenue).

## Dérogation à la règle 5 (~30 fichiers max par PR)

Assumée et arbitrée par l'humain. Estimation **révisée au 2026-07-31** :
**~60 fichiers** — 30 `src/` porteurs dans `api-mail` (dont 15 avec des sites
d'appel réels), ~20 tests, 5 dans `sdk`, 1 dans `client-blazor`, 3 supprimés
(`FolderCacheManager` et ses deux compagnons).

Justification : le point de passage obligé est `BaseRepository`, qui expose le
cache à quinze repositories. Le changer casse la compilation de tous
simultanément — il n'existe pas de découpe qui laisse un état intermédiaire
compilable **et** honnête. Un découpage aurait produit des PRs
`awaiting-us-completion` (règle 11) sans réduire le risque.

Contrepartie exigée : le diff doit être **massivement mécanique**. Toute
modification qui n'est pas une substitution `sync → async` + propagation
d'`await`/`CancellationToken` doit être **listée nommément** dans le
`## Develop log`.

## Definition of Done

- [ ] Build passes sur `api-mail`, `sdk`, `client-blazor` (0 erreur)
- [ ] Tests pass (0 échec) — suite complète `api-mail`, baseline 3 207 tests verts
- [ ] `Sdk/Services/ICacheService.cs` et `Sdk/Services/CacheService.cs` **n'existent plus**
- [ ] `IResilientCacheService` n'expose plus `TryGet` / `TrySet` / `TryRemove`
- [ ] `FolderCacheManager`, `IFolderCacheManager` et `FolderCacheManagerTests` **supprimés**
- [ ] `grep -rn "ICacheService" --include=*.cs Api/Mail/src Sdk Client/Blazor/Src` ne remonte **que** `HealthPlatform.Components.Shared.Services.ICacheService` (le cache WASM, hors périmètre)
- [ ] Aucune registration résiduelle : `Sdk/Extensions/ServiceCollectionExtensions.cs`, `Api/Mail/src/Api/DependencyInjection.cs:25`, `Client/Blazor/.../ServiceCollectionExtensions.cs:20`
- [ ] SDK republié en **9.0.0** ; `Directory.Packages.props` de `api-mail` (8.0.0 → 9.0.0) **et** de `client-blazor` (7.0.0 → 9.0.0) bumpés
- [ ] Garde de **surface publique** : échoue si une API de cache synchrone réapparaît sur le SDK
- [ ] Garde d'**analyseur IL** : échoue sur toute référence d'`api-mail` aux surcharges synchrones d'`IDistributedCache` — **avec témoin positif** qui prouve que le scanner voit encore quelque chose
- [ ] Les deux gardes **constatées RED avant le correctif** (preuve dans le `## Develop log`)
- [ ] Test unitaire par méthode rendue asynchrone (>= 1), y compris `TrySetCacheAsync` et `InvalidateCoverageCacheAsync`
- [ ] La tolérance au `null` et à la panne de **task-074** est préservée et testée (une panne Redis dégrade vers la source, ne fait jamais échouer l'opération métier)
- [ ] `CancellationToken` propagé partout où la méthode appelante en porte un
- [ ] La clé de cache patient reste **hachée SHA-256** (`PatientRepository.PatientCacheKey`) — aucune INS en clair dans une clé Redis
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) — les logs du cache ne journalisent que la clé, déjà hachée
- [ ] `## Develop log` liste nommément toute modification qui n'est pas une substitution mécanique

## Manual Test Plan

### A — Vérification fonctionnelle (non-régression)

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/Api`
2. Lancer Blazor : `cd Client/Blazor && dotnet run`
3. Se connecter via PSC, ouvrir la messagerie.
4. **Parcours de cache à exercer**, chacun deux fois de suite (2ᵉ passage = lecture depuis Redis) :
   - liste des dossiers, puis ouverture d'un dossier → liste des messages
   - ouverture d'un message, puis retour et réouverture du même message
   - marquer lu / non lu → le compteur du dossier se met à jour
   - déplacer un message entre deux dossiers → les deux dossiers sont cohérents
   - ouvrir les paramètres utilisateur, modifier une valeur, recharger la page
   - rechercher, puis rouvrir la recherche → l'historique est présent
   - ouvrir un patient rattaché → sa fiche s'affiche
5. **Attendu** : comportement identique à `develop`, aucune latence perçue en
   plus, aucune donnée périmée affichée après une invalidation.

### B — Résilience Redis (le filet de task-074)

6. `docker stop` le conteneur Redis, puis rejouer les parcours du point 4.
7. **Attendu** : l'application **reste fonctionnelle** (dégradation vers la
   source : IMAP / base). Aucun 500. Le circuit breaker s'ouvre au bout de
   5 échecs consécutifs et les logs montrent
   `[Cache] 🔴 Circuit breaker OPEN`, puis `🔄 half-open` après 30 s.
8. `docker start` Redis → les logs montrent `[Cache] ✅ Cache recovered`.

### C — Re-mesure au banc (c'est ici que se juge la valeur de l'US)

9. Monter le banc en profil loadtest (skill `loadtest-skill`), 200 praticiens,
   **tables mail purgées** (sinon le chemin chaud n'est pas exercé).
10. Échantillonneur : `tests/loadtest-k6/observe.sh start 900`
11. Palier de référence :
    ```bash
    BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 \
    SESSION_ROTATION=0.001 RPS=980 VU_TAIL_FACTOR=8 ENRICH_SHARE=0.05 \
      tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=3m
    ```
12. `tests/loadtest-k6/report.sh <json> --expected 100`, table « Par réplica
    api-mail », colonne « File ThreadPool (max) ».
13. ⚠️ **La baseline a changé — ne pas se comparer à 136.** Le chiffre de 136
    (pire réplica au palier 882) date d'**avant** task-205. Depuis son merge,
    la file est déjà **plate** : mesuré le 2026-07-31 après correctif,
    **8 / 6 / 6 / 5 / 4** au palier 882 et **13 / 11 / 6 / 5 / 4** au palier 972.
    Se comparer à 136 ferait déclarer une victoire triviale.

    **Baseline opposable pour cette US** (post-task-205, banc du 2026-07-31) :

    | Palier | File ThreadPool | `read_list` moy | Débit plateau | Abandons |
    |---|---|---|---|---|
    | 882 req/s | 8 / 6 / 6 / 5 / 4 | 718 ms | 863,0 req/s | 1,6 % |
    | 972 req/s | 13 / 11 / 6 / 5 / 4 | 641 ms | 940,3 req/s | 2,3 % |

    **Attendu de cette US** : la file reste plate (elle l'est déjà) **et** le
    débit progresse, ou à défaut `read_list` baisse. Si aucun des deux ne bouge,
    c'est un résultat en soi — il faudra le dire, et il orientera vers les
    pistes de « Hors scope ».

14. Capturer une pile (`dotnet-stack`) pendant le plateau : **plus aucun thread
    parqué sur `StackExchange.Redis.ExecuteSync`** — c'est **le** critère qui
    teste vraiment cette US, et le seul qui soit binaire.

    ⚠️ Le chiffre « 10 threads sur 35 » date d'**avant** task-205, qui a migré
    2 des sites concernés (`UserSettingsRepository`, `SearchHistoryService`).
    **Capturer une pile de référence AVANT de coder** : c'est elle qui dira
    combien de threads restent bloqués sur les 71 sites restants, et donc si
    l'hypothèse de gain de cette US tient.

## Ce que le cycle autonome peut livrer, et ce qui restera dû

| Item | `/develop` | Banc / HAG |
|---|---|---|
| Suppression SDK + migration des sites d'appel | ✅ | — |
| Build / tests verts sur les 3 repos | ✅ | — |
| Gardes de non-régression (surface + IL), constatées RED | ✅ | — |
| Republication NuGet 9.0.0 + bump des 2 consommateurs | ✅ | — |
| Parcours fonctionnels A | — | ✅ |
| Résilience Redis B | — | ✅ |
| File ThreadPool + pile sans `ExecuteSync` (C) | — | ✅ |

Précédent explicite : task-204 et task-205 ont toutes deux séparé la moitié
« code » de la moitié « mesure ». La DOD ci-dessus est **entièrement
vérifiable par `/review`** ; les tirs de banc sont dans le Manual Test Plan,
donc portés par l'humain au HAG (règle 10).

**Réserve honnête, et elle s'est renforcée depuis le relevé initial.** Deux
sites migrés par task-205 ont suffi à **éteindre la famine** : la file est
passée de 159/132/131 à 8/6/6/5/4 au palier 882, et le débit de 803 à 940 req/s
au palier 972. Autrement dit, **l'essentiel du gain de capacité est déjà
encaissé** — cette US ne le rejouera pas.

Ce qu'elle apporte est donc de nature différente, et il faut l'assumer :

- **Une garantie structurelle** — supprimer l'API rend le défaut
  *irréproductible*, là où task-205 n'a fermé que deux portes sur 73. C'est la
  vraie valeur, et elle est de robustesse, pas de performance.
- **Un gain résiduel incertain** : les 71 sites restants sont en bonne partie
  **froids** (OCSP, CRL, autoconfig, quota) et ne pèsent pas sous charge. Les
  candidats réellement chauds sont `ImapFolderService` (16), `ImapService` (13)
  et `ContactRepository` (12) — c'est sur eux que se jouera un éventuel gain.

**Ne pas vendre cette US comme un gain de capacité.** Si la re-mesure ne montre
aucun mouvement, c'est le résultat attendu, pas un échec : le critère binaire
reste « plus aucun thread sur `ExecuteSync` ». Les pistes de gain suivantes sont
ailleurs, et déjà nommées — sérialisation de `read_list` (verrou IMAP de session
+ sémaphore + verrou distribué), `MailClientSession.Dispose`, `EmailFlagService`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — la messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — refactoring technique interne, aucune exigence
  de référencement n'est créée ni modifiée.
- **Exigences DSR honorées** : aucune nouvelle. L'US **préserve** les exigences
  déjà tenues par les chemins qu'elle refactore (MSSanté-2.4 pour la lecture
  des messages) ; elle n'en ajoute pas.
- **INS** : manipulée **indirectement** — `PatientRepository` met en cache un
  `MailPatientDto` sous une clé dérivée de l'INS. La clé est **hachée SHA-256
  tronquée à 16 octets** (`PatientCacheKey`, `PatientRepository.cs:35`) et doit
  le rester à l'identique : c'est un garde-fou existant, pas une décision de
  cette US. Aucun changement de statut INS (qualifié / récupéré / provisoire).
- **Authentification PS** : inchangée — PSC / e-CPS, niveau eIDAS substantiel.
  Aucun chemin d'authentification n'est touché.
- **Habilitations** : inchangées — le cache est cloisonné par email de
  praticien (`RedisKeys.*`), le refactoring **ne doit pas** altérer la
  composition des clés. Une régression ici serait une **fuite inter-praticiens**
  (voir `CrossTenantOwnershipTests`, à garder vert).
- **Interop CI-SIS** : non applicable — aucun document CDA, aucune ressource
  FHIR, aucun échange métier n'est produit ni consommé par cette US.
- **Tracé PGSSI-S** : aucun **nouvel** évènement à journaliser. Les évènements
  existants (consultation de message, accès patient) sont émis par les couches
  appelantes, en amont du cache, et ne sont pas touchés. Durées de conservation
  inchangées.
- **Consentement patient** : non applicable — aucune écriture DMP / Mon Espace
  Santé, aucun partage inter-PS créé.
- **Référentiels métier** : aucun — pas de CIM-10, SNOMED, LOINC, CCAM, NABM
  ni CIS-CIP dans le périmètre.
- **Hébergement HDS** : oui — Redis héberge des DSCP (fiches patient,
  résumés de messages MSSanté) et reste dans le périmètre HDS existant. Cette
  US **ne change ni le contenu mis en cache, ni sa durée de rétention** : mêmes
  TTL (60 min absolu / 30 min glissant par défaut, 5 min pour le patient), mêmes
  clés, même sérialisation JSON. Seul le **mode d'appel** change.
- **AIPD / impact RGPD** : **inchangée** — aucune nouvelle finalité, aucune
  nouvelle donnée collectée, aucun nouveau destinataire, aucune modification de
  durée de conservation. Refactoring de performance sans effet sur le
  traitement au sens RGPD.

### Le point de vigilance santé de cette US

Il est unique et il est **la composition des clés de cache**. Un refactoring de
57 sites d'appel qui altérerait une clé produirait, selon le sens de l'erreur,
soit une perte de cache bénigne, soit **le service d'une donnée de santé d'un
praticien à un autre**. `CrossTenantOwnershipTests` et
`PatientRepositoryCacheTests` sont les gardes existantes : elles doivent rester
vertes, et **aucune clé ne doit être réécrite au passage** — la substitution
porte sur la méthode appelée, jamais sur son argument.
