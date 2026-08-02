# done-task-218.md — Retirer `ICacheService` du SDK : un cache sans budget de temps, sans disjoncteur et sans tolérance à la panne, que 58 appels traversent

**Repos**: sdk, api-mail, client-blazor
**Epic**: E015
**Single frontend**: false
**Dependencies**: **task-217 (doit être mergée)** — elle marque `ICacheService`
`[Obsolete]`, ajoute les tests du SDK et publie le paquet. Sans elle, cette US
migrerait vers un `IResilientCacheService` dont rien ne garantit encore le
budget de temps.
**Priorité**: **2** — les deux chemins chauds identifiés en juillet
(`UserSettingsRepository`, `SearchHistoryService`) ont déjà été sortis par le
contournement de task-205, et le chemin mesuré en août est traité par task-217.
Ce qui reste est bloquant mais moins sollicité.

> **Seconde moitié d'un chantier découpé.** L'inventaire complet donnait 64
> appels sur 52 fichiers, au-dessus du plafond de la règle 5. task-217 a pris le
> chemin mesuré (6 appels) ; celle-ci prend le reste (58) et **supprime**
> l'interface.

## Objective

Qu'il ne reste qu'**une seule** abstraction de cache dans le SDK, et qu'aucune
I/O synchrone n'y subsiste.

## Le défaut

`ICacheService` (`Get<T>` / `Set<T>` / `Remove`) descend sur
`IDistributedCache.GetString` / `SetString` / `Remove`, donc sur
`StackExchange.Redis.RedisBase.ExecuteSync` : un aller-retour réseau
**bloquant** sur un thread du pool, **sans budget de temps** et **sans
disjoncteur**.

Deux symptômes de son inadéquation, déjà dans le code :

- api-mail a dû écrire `SafeCacheExtensions` (task-074) pour l'entourer de
  `try/catch` — l'interface ne tolère pas la panne, il a fallu la lui ajouter
  par-dessus ;
- task-205 a dû **contourner** le SDK en descendant sur `IDistributedCache`
  pour obtenir de l'asynchrone sur deux chemins chauds.

`IResilientCacheService` fait déjà tout ce que ces deux rustines apportent :
async, budget de 500 ms, disjoncteur, compteurs de santé.

## Périmètre chiffré

| Cible | Volume |
|---|---|
| Appels `Get` / `Set` / `Remove` dans api-mail | **58** |
| Fichiers de production api-mail | ~26 — dont `ImapService`, `ImapFolderService` (la moitié des appels), `BaseRepository` et ~15 dépôts |
| Fichiers de tests api-mail référençant `ICacheService` | **26** |
| client-blazor | **1** ligne d'enregistrement DI (`Src/Shell/Extensions/ServiceCollectionExtensions.cs:20`) |

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la migration est un simple remplacement de type.**
  `ICacheService` **lève** en cas de panne Redis ; `IResilientCacheService`
  **avale et retourne `default`**. Un appelant qui distinguait « erreur » de
  « absent » par un `try/catch` change de sémantique. Recenser ces appelants
  **avant** de convertir, et écrire pour chacun que l'équivalence est vraie —
  ou traiter le cas.
- **Ne pas présumer que `default` vaut « absent » partout.** Pour un cache c'est
  presque toujours vrai, mais `CrlValidationService` et `OcspValidationService`
  cachent des éléments de **validation de certificat** : un « absent » silencieux
  y déclenche une revalidation, pas une acceptation par défaut. À **vérifier**,
  parce que l'inverse serait un défaut de sécurité.
- **Ne pas présumer que l'asynchronisation s'arrête au site d'appel.**
  `BaseRepository` expose `protected ICacheService CacheService` : le changement
  remonte dans une quinzaine de dépôts, et rendre `async` une méthode
  aujourd'hui synchrone se propage à ses appelants. Mesurer la cascade avant de
  commencer ; si elle déborde le plafond de la règle 5, **re-découper** plutôt
  que de livrer une PR de 80 fichiers.
- **Ne pas présumer que le contournement de task-205 se supprime sans garde.**
  Les variantes `Safe*Async` de `SafeCacheExtensions` sérialisent, d'après leur
  commentaire, « exactement » comme le SDK (JSON par défaut, valeur en string).
  **À prouver par un test** : une entrée écrite par une voie doit rester lisible
  par l'autre, sinon la bascule invalide silencieusement le cache en production.

## Contenu attendu

1. **SDK** : `ICacheService` et `CacheService` **supprimés** ;
   `ServiceCollectionExtensions.AddSdk` mis en cohérence. Publication + bump.
2. **api-mail** : 58 appels migrés vers `IResilientCacheService`, `BaseRepository`
   et les dépôts adaptés, et **retrait** des variantes redondantes de
   `SafeCacheExtensions` (`SafeGet` / `SafeSet` / `SafeRemove` et leurs
   équivalents `Async`) devenues sans objet.
3. **client-blazor** : enregistrement DI mis en cohérence, build + tests verts.
4. **Un test par appelant dont la sémantique d'erreur change** — c'est le risque
   principal de cette US, pas la compilation.
5. **Compatibilité de sérialisation** prouvée par test.

## Hors scope

- `IMarkdownService.ToHtml` — calculatoire, reste synchrone (déjà tranché par
  task-217).
- Le réglage des valeurs du disjoncteur.

## Definition of Done

- [x] Build passes (0 erreur) et tests verts sur **les trois repos**
- [x] Plus aucune occurrence d'`ICacheService` dans les trois repos
- [x] **Aucune** I/O synchrone ne subsiste dans le SDK — garde par test
      (`NoSynchronousCacheIoTests`, par réflexion, avec garde anti-vacuité)
- [x] Chaque appelant dont la sémantique d'erreur change est **nommé** dans le
      `## Develop log`, avec la raison pour laquelle l'équivalence tient
- [x] `CrlValidationService` et `OcspValidationService` : test prouvant qu'une
      panne de cache déclenche une **revalidation**, jamais une acceptation
      (7 gardes, sur la pile de cache réelle)
- [x] Test de compatibilité de sérialisation ancienne voie → nouvelle voie
      (`CacheSerializationCompatibilityTests`, dont égalité **octet pour octet**)
- [x] `Directory.Packages.props` bumpé dans api-mail **et** client-blazor
      (10.0.0 → 12.0.0)
- [x] Tests **constatés RED avant le correctif** — voir la nuance honnête au
      §7 du `## Develop log` : les gardes de sécurité sont **vertes avant ET
      après** par construction, et c'est précisément ce qui démontre
      l'équivalence. Le RED classique n'était pas applicable ici ; la régression
      réellement attrapée l'a été par 6 tests passés au rouge (§6).

### Dû au banc (ne bloque pas la PR, bloque la clôture de l'US)

- [ ] Tir 500 praticiens : aucun thread applicatif parqué dans `ExecuteSync`
      (contrôle par pile, sur le modèle de task-205)

## Manual Test Plan

```bash
cd Api/Mail && dotnet run --project src/AppHost
```

**Écran** : la messagerie — ouvrir la liste des dossiers, un message, lancer une
recherche.

**Ce que l'humain doit voir** :
- comportement inchangé, Redis debout ;
- après `docker stop` du conteneur Redis : l'application **continue de
  fonctionner** (repli sur la source), sans attente de plusieurs secondes ;
- ⚠️ **le contrôle qui compte** : ouvrir un message dont le certificat est à
  valider pendant que Redis est arrêté — la validation doit être **refaite**,
  jamais court-circuitée en « valide ».

**Blazor** : `cd Client/Blazor && dotnet run` — l'application démarre.

**Données de test** : compte de développement, aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — robustesse interne.
- **Exigences DSR honorées** : aucune nouvelle.
- **INS** : non manipulée. **Authentification PS** : inchangée.
- **Habilitations** : ⚠️ les clés de cache portent l'email du praticien. Le
  cloisonnement par clé doit être **conservé à l'identique** — une clé dont le
  praticien disparaîtrait ferait servir le message d'un praticien à un autre.
  Test de garde exigé.
- ⚠️ **Sécurité — le point dur de cette US** : `CrlValidationService` et
  `OcspValidationService` cachent des éléments de validation de certificat. Le
  passage d'une sémantique « lève » à une sémantique « retourne `default` » ne
  doit **jamais** transformer une panne de cache en acceptation d'un certificat.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun évènement métier touché.
- **Hébergement HDS** : non applicable.
- **AIPD / impact RGPD** : inchangé. Durées de conservation du cache inchangées.

## Branches
- `sdk` (pushed) : fix/task-218-remove-icacheservice
- `api-mail` (pushed) : fix/task-218-remove-icacheservice
- `client-blazor` (pushed) : fix/task-218-remove-icacheservice
- `dtos-mss` (pushed, auto-inclus) : fix/task-218-remove-icacheservice — aucun contrat attendu

> Ordre cross-repo imposé : **sdk → publication NuGet → bump → api-mail /
> client-blazor**. Le SDK doit être publié avant que les consommateurs
> compilent contre le nouveau contrat.
>
> Pré-flight : `host` n'a pas de `.git` (corrigé au CLAUDE.md ce jour, le
> pré-flight ne mesure rien sur lui) ; `client-mobile` n'est pas cloné.

## Develop log — en cours

### 1. Six appels sur 61 étaient du code mort

`FolderCacheManager` et `IFolderCacheManager` n'avaient **aucun appelant de
production** et n'étaient **pas enregistrés en DI** — seul leur propre test
unitaire les référençait. Supprimés (3 fichiers). Build vert.

### 2. Le point dur du DOD, instruit par lecture — les deux services de sécurité

Le risque nommé par la task : `ICacheService` **lève** en cas de panne,
`IResilientCacheService` **avale et rend `default`**. Pour un service qui valide
un certificat, confondre « panne de cache » et « rien en cache » pourrait
transformer une indisponibilité en acceptation.

**Vérifié : les deux traitent déjà la panne comme une absence.**

| Service | Ce que fait le code aujourd'hui | Effet de la bascule |
|---|---|---|
| `CrlValidationService.GetCrlAsync` | `try/catch` autour du `Get`, `LogWarning` puis **téléchargement du CRL** | **aucun** — le repli existe déjà |
| `OcspValidationService.TryGetCachedEntry` | `try/catch`, retourne `null`, commentaire de task-069 : « *a cache outage must not abort the validation : the online OCSP check still runs* » | **aucun** |
| `OcspValidationService.TryGetCachedIssuerData` | idem, retourne `null` → re-téléchargement du certificat émetteur | **aucun** |

Autrement dit, la sémantique cible est **déjà** celle qu'ils implémentent à la
main. La bascule supprime leur `try/catch`, elle ne change pas leur
comportement. Des tests le verrouilleront quand même — c'est une propriété de
sécurité, elle ne doit pas dépendre d'une relecture.

⚠️ **Cascade à prévoir** : `TryGetCachedEntry` et `TryGetCachedIssuerData` sont
des méthodes **privées synchrones**. Les passer en async remonte à leurs
appelants.

### 3. Reste à faire

| Cible | Appels |
|---|---|
| `ImapFolderService` | 16 |
| `ImapService` | 13 |
| `src/Infrastructure/` (`BaseRepository` + ~15 dépôts) | 18 |
| `OcspValidationService` | 4 |
| `CrlValidationService` | 2 |
| `SyncCoverageService` | 2 |
| `BackgroundSyncService` | 1 |
| ~~`FolderCacheManager`~~ | ~~6~~ — **supprimé** |

Puis : retrait des helpers redondants de `SafeCacheExtensions`, retrait
d'`ICacheService`/`CacheService` du SDK, publication, bump des deux
consommateurs.

**Ordre retenu** : migrer api-mail **d'abord**, contre le SDK 10.0.0 déjà
publié — `IResilientCacheService` y existe déjà, aucun changement de SDK n'est
nécessaire pour cette étape. Le retrait côté SDK devient ensuite une simple
suppression, une fois qu'il n'a plus d'appelant.

### 4. Point de reprise — session du 2026-08-02 interrompue volontairement

**Rien n'est en suspens.** Tous les dépôts sont commités et poussés ; la branche
`fix/task-218-remove-icacheservice` existe sur les quatre repos, et seul
`api-mail` y porte un commit (`127e7b9`, retrait du code mort).

**Par où reprendre**, dans cet ordre :

1. **`OcspValidationService` et `CrlValidationService`** — commencer par eux.
   Ce sont les seuls porteurs d'un risque de sécurité, l'analyse est faite
   (§2 ci-dessus) et ils sont petits : 6 appels à eux deux. **Écrire d'abord les
   tests** qui prouvent qu'une panne de cache déclenche une revalidation et
   jamais une acceptation — ils doivent être verts AVANT et APRÈS la migration,
   c'est ce qui démontre l'équivalence.
2. **`SyncCoverageService`** (2) et **`BackgroundSyncService`** (1) — petits,
   sans piège identifié.
3. **`src/Infrastructure/`** (18) — `BaseRepository` expose
   `protected ICacheService CacheService` et `CacheServiceOrNull` ; c'est la
   racine de la cascade vers une quinzaine de dépôts. Mesurer la cascade avant
   de commencer.
4. **`ImapFolderService`** (16) et **`ImapService`** (13) — le plus gros, à
   garder pour la fin : la majorité de leurs méthodes est déjà `async`, donc la
   cascade devrait y être faible.
5. **`SafeCacheExtensions`** — retirer les helpers devenus redondants, avec le
   test de compatibilité de sérialisation exigé par le DOD.
6. **SDK** — retirer `ICacheService`/`CacheService`, mettre `AddSdk` en
   cohérence, publier, bumper les deux consommateurs.
7. **`client-blazor`** — retirer l'enregistrement DI
   (`Src/Shell/Extensions/ServiceCollectionExtensions.cs:20`) et bumper.

**Si la cascade fait déborder le plafond de ~30 fichiers de la règle 5** :
re-découper plutôt que livrer une PR de 80 fichiers. Le point de coupe naturel
est entre l'étape 4 et l'étape 5.

**Rappels d'outillage acquis aujourd'hui** :
- Le poste n'a **pas** de `GH_TOKEN`. Utiliser `GH_TOKEN=$(gh auth token)` en
  ligne devant `dotnet restore` / `build` — le jeton `gh` porte
  `write:packages`. Ne jamais le faire transiter par un fichier.
- NuGet **ne retélécharge pas** un paquet déjà en cache global : après
  publication d'une nouvelle version, purger
  `~/.nuget/packages/healthplatform.host.sdk/{version}` avant de restaurer,
  sinon le `contentHash` inscrit dans les lock files sera celui d'un pack local
  et la CI échouera en `NU1403`.
- La CI du SDK publie **une version par poussée** (numéro de run). Le SDK est
  aujourd'hui publié en **11.0.0** ; les consommateurs épinglent **10.0.0**.

---

## Develop log — terminé le 2026-08-02

### 5. La cascade redoutée n'existait pas

La task annonçait `src/Infrastructure/` comme le risque principal :
`BaseRepository` expose le cache à une quinzaine de dépôts, et rendre `async`
une méthode synchrone remonte à ses appelants. **Mesuré : la cascade est
mécanique, pas asynchrone.**

| Ce qui était redouté | Ce qui a été mesuré |
|---|---|
| ~15 dépôts à asynchroniser | **3** utilisent le cache (Contact, Patient, UserSettings) ; les 12 autres ne faisaient que **passer le paramètre** au constructeur de base |
| cascade débordant sur les appelants | **5 sites** seulement ont eu besoin de devenir `async`, tous privés |
| changement d'API publique | **aucun** |

Ordre effectivement suivi : api-mail d'abord contre le SDK 10.0.0 déjà publié,
puis retrait côté SDK devenu une simple suppression sans appelant.

### 6. Les trois rustines tombent ensemble

Le cœur de l'US n'était pas la compilation, mais le fait que **trois**
compensations historiques disparaissent avec l'interface :

| Rustine | Ce qu'elle compensait | Remplacée par |
|---|---|---|
| `SafeCacheExtensions` (task-074) | l'interface **levait** en cas de panne | le contrat rend `default`/`false` |
| contournement `IDistributedCache` (task-205) | l'interface était **synchrone** | le contrat est async, borné à 500 ms |
| nullabilité (`CacheServiceOrNull`, params par défaut) | le cache pouvait être **absent** | `NoOpResilientCacheService` |

Conséquence : **tous** les `try/catch` et **toutes** les gardes `null` autour du
cache disparaissent des appelants. `SafeCacheExtensions` est supprimé.

**Régression réellement attrapée.** Retirer le `try/catch` de
`BackgroundSyncService.InvalidateCoverageCache` a supprimé une tolérance qui ne
concernait **pas** le cache : `GetRequiredService` **lève** quand aucun cache
n'est enregistré, et une invalidation ne doit pas faire échouer une synchro qui
vient d'aboutir. **6 tests sont passés au rouge** et l'ont révélée. Corrigé par
`GetService` (cache optionnel), qui *dit* la chose au lieu de la masquer.

### 7. Les gardes de sécurité — la méthode, et sa nuance honnête

Les 7 gardes ont été écrites et constatées **VERTES contre l'ancien contrat**
(mock qui lève) **AVANT** la bascule, puis re-vérifiées vertes **après**. C'est
cette **invariance** qui démontre l'équivalence exigée au DOD.

⚠️ **Nuance à ne pas maquiller** : ces gardes ne sont donc **jamais passées par
un état RED**, contrairement à la lettre du DOD. C'est structurel, pas un
manquement : elles vérifient qu'un comportement **ne change pas**. Un test
d'équivalence qui serait rouge avant la bascule prouverait l'inverse de ce
qu'on cherche. Le RED classique s'est produit ailleurs, en §6.

Les gardes portent sur la **pile de cache RÉELLE** (`ResilientCacheService`
au-dessus d'un `IDistributedCache` en panne), pas sur un mock. Raison : après la
bascule, un mock à qui on dit « rends `null` » est **indiscernable** d'un cache
vide — il ne prouverait plus rien. Trois doubles de test qui décrivaient la
panne en **levant** ont été recâblés sur la pile réelle pour la même raison ;
deux tests devenus incapables de décrire une panne ont été retirés et remplacés
par des gardes strictement plus fortes.

### 8. Compatibilité de sérialisation — le risque silencieux

Sans cette preuve, la bascule aurait pu **invalider silencieusement tout le
cache en production** : chaque entrée écrite avant le déploiement illisible
après, sans aucune erreur, juste un effondrement du taux de hit sur des chemins
chauds (les réglages sont lus à presque chaque requête).

Les trois voies écrivaient à l'identique : `JsonSerializer.Serialize(item)` aux
options **par défaut**, valeur stockée en string. `CacheSerializationCompatibilityTests`
le prouve dans les deux sens, **plus** l'égalité **octet pour octet**, **plus**
une garde contre un futur format enveloppé. Le test épingle le **format de fil**
et non les méthodes supprimées — il survit donc à leur suppression, et c'est
bien ce format qui est présent dans Redis au moment du déploiement.

### 9. Écart de norme assumé — règle 5

Cette US touche **~56 fichiers**, contre un plafond de ~30. Le point de coupe
que la task suggérait (entre étapes 4 et 5) donnait encore ~49 fichiers, donc ne
résolvait rien. **Arbitré explicitement avec l'humain** : tout finir dans
task-218, parce que le diff est massivement mécanique (2 lignes dans ~20
fichiers) et que la **règle 11** fait qu'un découpage ne ferait pas merger plus
tôt. Décision prise en connaissance du plafond, justifiée dans le corps de la PR.

### 10. Résultat

| Repo | Build | Tests | PR |
|---|---|---|---|
| `sdk` | vert | **16** | [#2](https://github.com/codengine-technologies/HealthPlatform.Host.Sdk/pull/2) — publié en **12.0.0** |
| `api-mail` | vert | **3 256** | [#146](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/146) |
| `client-blazor` | vert | **144** | [#68](https://github.com/codengine-technologies/HealthPlatform.Client/pull/68) |
| `dtos-mss` | — | — | aucune PR : aucun contrat touché, comme prévu |

Détail api-mail : 102 domain + 393 infrastructure + 639 api + 204 integration
+ 1 918 application. Les trois PRs portent `awaiting-human-merge`.

**Ordre de merge imposé** : SDK d'abord (déjà publié en 12.0.0), puis api-mail
et client-blazor.

### 11. Contre-épreuve au banc — tirée le 2026-08-02 au soir

- [x] Tir 500 praticiens : **aucun thread applicatif parqué dans `ExecuteSync`**

Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-08-02/report-mixed-mssante-60vu-230054.md`
(section « Contre-épreuve task-218 »), piles dans `stacks-task218-230600/`.
Les rapports sont *gitignored* par convention du dépôt — seul `INDEX.md` est
versionné, donc l'essentiel est recopié ici.

**Le contrôle par pile — tenu.** `dotnet-stack report` sous charge, 3 rounds
× 5 réplicas :

| | Avant (2026-07-31) | Après |
|---|---|---|
| Threads capturés | 236 | **731** |
| Frames `ExecuteSync` | **20** | **0** |
| Frames `CacheService` | 17 | **0** |

Ce qui rend le résultat **attribuable** et non fortuit : les appelants parqués
*avant* nomment exactement le code que task-218 a supprimé ou migré —
`CacheService.Get` (17), `SafeCacheExtensions.SafeGet` (10),
`ImapService.GetFoldersAsync` (7), `UserSettingsRepository.GetSettingsAsync` (5),
`SearchHistoryService.Record` (5).

Les frames StackExchange.Redis restantes sont légitimes : threads d'arrière-plan
de la bibliothèque et **machines à états asynchrones**. Corroboré statiquement —
tous les appels StackExchange.Redis d'api-mail sont désormais `*Async`.

**Corollaire mesuré** : `RedisTimeoutException` **7 155 → 0**. Erreurs
**0,00 %**, tous marqueurs de régression à 0, 819 parsings CDA,
`enrich_short_circuited = 0`.

⚠️ **Le gain de débit reste NON MESURÉ — ce qui n'est pas « non obtenu ».**
Plateau 735,8 req/s contre 743,3 pour la référence, p95 2 632 contre 1 593 ms.
Cet écart n'est **pas** imputable à task-218 :

1. la référence (2026-08-01 15:10) **précède** le merge de task-213
   (`42f21ed`, 16:08), dont la contre-épreuve `598821c` a établi qu'elle
   **ralentit l'envoi** — `send` planifié 1,18 s, mesuré **2,72 s** (×2,3) ;
2. le maildir est passé de 8,2 à **9,0 Go**, et à 500 praticiens le coût
   dominant suit le volume des boîtes ;
3. les deux tirs sont formellement **invalides** (abandons > 1 %) des deux côtés.

Le rapport impute les abandons au **dimensionnement du harnais** (file ThreadPool
max **34** sur un seuil de 100 → serveur calme), pas à l'application.

Il n'existe à ce jour **aucun couple de tirs à 500 praticiens** partageant
budget, lignée de code **et** volume de maildir. Mesurer le gain demanderait un
**A/B à harnais et lignée identiques** — même commit, `ICacheService` retiré ou
remis. **Reste dû.**
