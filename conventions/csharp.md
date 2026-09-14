# conventions/csharp.md — règles apprises côté C#

> **Boucle d'auto-amélioration** (CLAUDE.md § « Conventions apprises »).
> Alimenté par `/sonar` à chaque règle corrigée **à la main** sur du code frais.
> Lu par `/develop` **avant** d'écrire du C#.
>
> Les corrections de l'auto-fixer ne comptent pas (elles sont gratuites). Seules
> les règles qu'un humain ou la forge a dû corriger manuellement entrent ici :
> ce sont celles qui coûtent un aller-retour et qu'il faut donc éviter d'emblée.
>
> **Protocole** : première correction manuelle d'une règle → nouvelle entrée,
> `Occurrences: 1`. Récidive sur du code frais → incrémenter le compteur (une
> récidive signale que ce fichier n'a pas été lu avant de coder). Ne jamais
> supprimer une entrée sans justification dans le commit.
>
> Ce fichier complète, sans le remplacer,
> [`Api/Mail/.github/instructions/dotnet-coding-rules.instructions.md`](../Api/Mail/.github/instructions/dotnet-coding-rules.instructions.md)
> — la source de vérité des règles de codage d'`api-mail`, qui reste à lire pour
> tout code C# de ce repo.

---

## CA1822 — un membre qui n'accède pas à l'état d'instance doit être `static`

**Occurrences : 1** (task-200)

Le piège classique en test : exposer une valeur constante par une **propriété
d'instance** qui enveloppe un `private const`. La propriété n'accède à aucun
état d'instance, donc CA1822 la signale — et l'indirection n'apportait rien.

```csharp
// ❌ AVANT — propriété d'instance qui ne fait que relayer une constante
private const string Database = "mail_pooler_test";
public string DatabaseName => Database;

// ✅ APRÈS — une seule déclaration, publique
public const string DatabaseName = "mail_pooler_test";
```

**Consigne** : avant d'écrire `public X Truc => _constante;`, vérifier si la
constante ne peut pas être exposée directement. Dans une fixture de test, une
valeur fixe partagée par les tests est une `public const`, pas une propriété.
Corollaire : les sites d'appel deviennent `MaClasse.DatabaseName` et non
`_fixture.DatabaseName` — c'est le signe attendu, pas une gêne.

---

## S2068 — ne pas multiplier les littéraux de mot de passe

**Occurrences : 1** (task-200)

Les bancs de test ont des identifiants synthétiques en clair, assumés et
documentés. S2068 ne se déclenche pas sur leur existence mais sur **chaque
occurrence** : un refactor qui construit une seconde chaîne de connexion avec le
même `Password=…` crée une nouvelle issue pour zéro information ajoutée.

```csharp
// ❌ AVANT — deux littéraux pour les mêmes identifiants
const string direct = "Host=127.0.0.1;Port=5432;Username=postgres;Password=postgres";
var data = "Host=127.0.0.1;Port=6432;Username=postgres;Password=postgres" + pooling;

// ✅ APRÈS — identifiants déclarés une fois
const string credentials = "Username=postgres;Password=postgres";
const string direct = $"Host=127.0.0.1;Port=5432;{credentials}";
var data = $"Host=127.0.0.1;Port=6432;{credentials}{pooling}";
```

**Consigne** : quand une US ajoute une variante d'une chaîne de connexion
existante (autre port, autres bornes de pooling), extraire la partie
identifiants en constante **avant** de dupliquer. Vaut pour tout secret de banc
(mots de passe IMAP, clés de bypass) : une déclaration, N usages.

---

## CA1861 — pas de tableau littéral en argument d'appel

**Occurrences : 2** (task-203, task-273 — récidive sur code frais : tableaux
attendus d'un `Assert.Equal` dans un test de sollicitations ; la consigne vaut
aussi pour les attendus de test)

Un tableau littéral passé en argument est **réalloué à chaque appel**. Le motif
apparaît naturellement quand on préfixe des segments de chemin ou qu'on
construit une liste courte « à la volée » — y compris dans du code de test, où
l'analyseur ne fait pas de remise.

```csharp
// ❌ AVANT — le préfixe est réalloué à chaque résolution
internal static string? TryResolveAppHostFile(params string[] segments)
    => TryResolveRepoFile([.. new[] { "src", "AppHost" }.Concat(segments)]);

// ✅ APRÈS — préfixe déclaré une fois, et l'appel se lit mieux
private static readonly string[] AppHostSegments = ["src", "AppHost"];

internal static string? TryResolveAppHostFile(params string[] segments)
    => TryResolveRepoFile([.. AppHostSegments, .. segments]);
```

**Consigne** : dès qu'un tableau littéral (`["a", "b"]` ou `new[] { … }`) apparaît
**dans un argument**, le hisser en `private static readonly`. Bonus de lisibilité
en C# 12 : deux spreads valent mieux qu'un `Concat`.

---

## CA1859 — type concret plutôt qu'interface pour un helper local

**Occurrences : 3** (task-203, task-289, task-299 — troisième récidive. Variante
task-299 : une méthode privée `async`-sans-`await` qui **rendait directement** la
tâche concrète d'un appelé (`Task<bool>` du cache) sous un type déclaré `Task`.
La consigne vaut donc aussi pour le **relais d'une tâche** : soit on déclare le
type concret, soit on `await` — mais on ne masque pas un `Task<T>` derrière un
`Task`.)

**Occurrences (historique) : 2** (task-203, task-289 — récidive sur du code frais, et
c'est la **passe qualité `/simplify` elle-même** qui l'a introduite : une revue
a proposé `IReadOnlyList<string>` au motif que « le helper ne mute rien », ce
qui est vrai mais hors sujet. Le paramètre d'un helper **privé** dont l'unique
appelant construit déjà un `List<string>` n'a rien à abstraire. Leçon : la
consigne ci-dessous vaut **aussi contre une recommandation de revue**, et vaut
pour les **paramètres**, pas seulement les valeurs de retour.)

Renvoyer une interface depuis une fabrique **privée** dont tous les appelants
sont dans le même fichier fait payer un appel virtuel sans rien abstraire.
L'analyseur le signale, et le type concret révèle souvent une information que
l'interface masquait — ici que l'objet est **jetable**.

```csharp
// ❌ AVANT — ILogger cache le fait que l'objet doit être libéré
private static ILogger LoggerFrom(string? level) => new LoggerConfiguration()…CreateLogger();
var logger = LoggerFrom("Information");        // fuite silencieuse

// ✅ APRÈS — type concret, et le `using` devient évident
private static Logger LoggerFrom(string? level) => new LoggerConfiguration()…CreateLogger();
using var logger = LoggerFrom("Information");
```

**Consigne** : un helper `private` rend — et **reçoit** — le **type concret**,
pas l'abstraction. On n'introduit une interface que lorsqu'un second
implémenteur existe, ou que le type traverse une frontière publique. Vérifier au
passage si ce type concret est `IDisposable` : c'est fréquent, et l'interface le
dissimulait. `using Serilog.Core;` est nécessaire pour `Logger` (`Serilog` seul
ne suffit pas).

**Ne pas confondre avec l'immuabilité.** « Ce helper ne mute pas son argument »
n'est pas une raison de prendre `IReadOnlyList<T>` : sur un helper privé, cette
garantie se lit dans les cinq lignes du corps, et l'interface la paie d'un appel
virtuel. `IReadOnlyList<T>` se justifie sur une API **publique**, où l'appelant
ne voit pas le corps.

---

## S1135 — le mot « TODO » dans une prose n'est pas un TODO

**Occurrences : 1** (task-283)

Citer une task en attente sous sa forme de fichier (`onhold/todo-task-171`)
place le mot-clé **TODO** dans un commentaire. S1135 le relève et demande de
« terminer la tâche associée » — alors que la phrase documente précisément un
choix de **ne pas** faire quelque chose maintenant.

```csharp
// ❌ AVANT — le nom de fichier de la task porte le mot-clé
/// L'ADR backend-pull (<c>onhold/todo-task-171</c>) le supprimera.

// ✅ APRÈS — même information, sans déclencheur
/// L'ADR backend-pull (task-171, en attente) le supprimera.
```

**Consigne** : dans un commentaire ou un doc XML, citer une task par son
**numéro** (`task-171`), jamais par son nom de fichier `todo-*` / `wip-*`. Le
préfixe de cycle de vie n'apporte rien au lecteur du code — il change au fil
du temps, et `todo-` fabrique un faux positif. Vaut aussi pour `FIXME` et
`HACK` cités entre guillemets.

---

## CA1869 — `JsonSerializerOptions` se construit une fois, pas à chaque appel

**Occurrences : 1** (task-283)

Écrit sans y penser dans un helper de test qui désérialise à chaque cas :
l'objet est coûteux à construire et conçu pour être **mis en cache et
partagé**. La règle vaut autant en test qu'en production — un helper appelé par
N tests, c'est N instances.

```csharp
// ❌ AVANT — une instance par désérialisation
return JsonSerializer.Deserialize<ProblemDetails>(
    json, new JsonSerializerOptions(JsonSerializerDefaults.Web))!;

// ✅ APRÈS — une déclaration, N usages
private static readonly JsonSerializerOptions ProblemJson = new(JsonSerializerDefaults.Web);
...
return JsonSerializer.Deserialize<ProblemDetails>(json, ProblemJson)!;
```

**Consigne** : dès qu'un `new JsonSerializerOptions(...)` apparaît **dans un
argument d'appel**, le hisser en `private static readonly`. Même réflexe que
CA1861 pour les tableaux littéraux : ce qui est constant au fil des appels se
déclare une fois.

---

## S3267 — une boucle qui ne fait que chercher s'écrit avec `Contains`/`Any`

**Occurrences : 1** (task-184)

Écrit sans y penser dans un helper d'appartenance : un `foreach` sur un tableau
de constantes, un `if` de comparaison, un `return true`. La forme explicite
n'ajoute rien et **répète la règle de comparaison** — ici l'insensibilité à la
casse — à chaque ajout d'entrée dans le tableau.

```csharp
// ❌ AVANT — huit lignes pour une appartenance
private static bool IsSensitiveQueryKey(string key)
{
    foreach (var sensitive in SensitiveQueryKeys)
    {
        if (string.Equals(key, sensitive, StringComparison.OrdinalIgnoreCase))
            return true;
    }
    return false;
}

// ✅ APRÈS — le comparateur porte la règle, une fois
private static bool IsSensitiveQueryKey(string key) =>
    SensitiveQueryKeys.Contains(key, StringComparer.OrdinalIgnoreCase);
```

**Consigne** : une boucle dont le corps se réduit à `if (…) return true;` est une
appartenance — écrire `Contains` (avec un `StringComparer` quand la comparaison
n'est pas ordinale stricte) ou `Any`. Attention au couple : `StringComparison`
dans `string.Equals`, mais `StringComparer` dans `Contains`.

---

## S125 — une prose qui « ressemble à du code » est signalée comme code commenté

**Occurrences : 2** (task-184, task-292 — récidive sur code frais : un commentaire DI
de trois lignes avec une parenthèse fermante puis « : » en milieu de phrase)

Un commentaire d'intention parfaitement légitime a été relevé comme du code mis
en commentaire, uniquement à cause de sa **ponctuation** : un point-virgule en
fin de proposition, au milieu d'une phrase anglaise.

```csharp
// ❌ AVANT — le `;` en fin de ligne suffit à déclencher la règle
// raw path is still what routing and the skip/debug predicates see;
// only what reaches a sink is masked.

// ✅ APRÈS — même information, ponctuation de prose
// Routing and the skip/debug predicates keep reading the raw path, because
// only what reaches a sink needs masking.
```

**Consigne** : dans un commentaire, éviter le point-virgule en fin de ligne et
les fins de ligne en `)` ou `}`. Écrire des phrases. Le coût est nul et cela
évite une issue qu'on est ensuite tenté d'« accepter », ce qui use la crédibilité
des exemptions.

---

## S3604 — pas d'initialiseur de membre qui ne fait que copier un paramètre de constructeur primaire

**Occurrences : 1** (task-292, ×2 dans le même run)

Avec un **constructeur primaire**, un champ initialisé depuis un paramètre
(`private readonly AuditOptions _options = options.Value;`) est signalé :
l'analyseur lit « tous les constructeurs affectent le membre », donc
l'initialiseur est redondant. Le motif apparaît naturellement quand on ajoute
un paramètre optionnel avec repli (`backlog ?? new AuditBacklog()`).

```csharp
// ❌ AVANT — champ recopié depuis le paramètre primaire
public sealed class RedisAuditSpillStore(IOptions<AuditOptions> options)
{
    private readonly AuditOptions _options = options.Value;
    private int MaxSpillLength => _options.SpillMaxLength;
}

// ✅ APRÈS — le paramètre primaire est capturé, on le lit directement
public sealed class RedisAuditSpillStore(IOptions<AuditOptions> options)
{
    private int MaxSpillLength => options.Value.SpillMaxLength;
}
```

**Consigne** : dans une classe à constructeur primaire, **lire le paramètre**
capturé plutôt que le recopier dans un champ. Et un repli `?? new X()` sur un
paramètre optionnel est le signe qu'il devrait être **obligatoire** : rendre le
paramètre requis et passer l'instance explicitement dans les tests (c'est ce qui
porte l'invariant « une instance par processus » au compilateur).

---

## CA1869 — une seule instance de `JsonSerializerOptions`, jamais une par appel

**Occurrences : 1** (task-295 — corrigée sur du new code de task-292 : deux
appels `JsonSerializer.Serialize` / `Deserialize` dans un test de charge utile)

`JsonSerializerOptions` construit sa **cache de métadonnées de contrat** à la
première sérialisation d'un type. Une instance neuve à chaque appel la
reconstruit intégralement — le coût est invisible en test unitaire, réel sur un
chemin chaud. La règle se déclenche sur `new JsonSerializerOptions { … }` passé
directement en argument.

```csharp
// ❌ AVANT — deux instances, deux caches, et deux endroits où la convention peut diverger
var json = JsonSerializer.Serialize(trace, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
var back = JsonSerializer.Deserialize<MssAuditTrace>(json, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase })!;

// ✅ APRÈS — une instance partagée, et la symétrie garantie par construction
private static readonly JsonSerializerOptions CamelCase =
    new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

var json = JsonSerializer.Serialize(trace, CamelCase);
var back = JsonSerializer.Deserialize<MssAuditTrace>(json, CamelCase)!;
```

**Consigne** : ne jamais écrire `new JsonSerializerOptions { … }` dans un
argument. Déclarer un `private static readonly JsonSerializerOptions` nommé par
sa convention (`CamelCase`, `Indented`…) et le réutiliser. Vaut **aussi dans les
tests** — l'analyseur ne fait pas de remise, et un aller-retour
sérialise/désérialise qui partage l'instance ne peut pas diverger sur la
convention de nommage.

---

## S3604 — un constructeur primaire n'accepte pas d'initialiseur de champ

**Occurrences : 1** (task-297)

Le motif se forme naturellement quand on veut **capturer une fois** une valeur
de configuration dans une classe à constructeur primaire : on déclare un champ
`readonly` initialisé depuis un paramètre du constructeur primaire. Sonar lit
alors « initialiseur de membre redondant, tous les constructeurs affectent déjà
ce membre » et ouvre un finding sur du code frais.

```csharp
// ❌ AVANT — l'initialiseur de champ dans une classe à constructeur primaire
public sealed class SizeBoundedCacheService(
    IResilientCacheService inner,
    IOptions<CacheOptions> options,
    ILogger<SizeBoundedCacheService> logger) : IResilientCacheService
{
    private readonly int _maxEntryBytes = options.Value.MaxEntryBytes;   // S3604

// ✅ APRÈS — constructeur explicite, et l'intention devient lisible
public sealed class SizeBoundedCacheService : IResilientCacheService
{
    private readonly IResilientCacheService _inner;
    private readonly int _maxEntryBytes;

    public SizeBoundedCacheService(
        IResilientCacheService inner, IOptions<CacheOptions> options, ILogger<…> logger)
    {
        _inner = inner;
        _maxEntryBytes = options.Value.MaxEntryBytes;
    }
```

**Consigne** : le constructeur primaire est parfait tant qu'on **consomme
directement** ses paramètres dans les corps de méthode (`inner.GetAsync(…)`).
Dès qu'il faut **dériver et retenir** une valeur — lire un `IOptions`, calculer
une borne, résoudre un chemin —, écrire un **constructeur explicite**. Ne pas
« corriger » en relisant `options.Value` à chaque appel : sur un chemin chaud
c'est payer à chaque passage une valeur qui ne bouge pas, et c'est justement ce
que la capture évitait.


---

## S1854 — une affectation qu'on écrase aussitôt est morte, même si elle « documente »

**Occurrences : 1** (task-299)

Le piège vient d'une **passe de simplification**. Le code créait la ligne puis
la relisait pour absorber une course perdue entre réplicas :

```csharp
var row = await EnsureAccountRowAsync(db, subject, ct);   // ← morte
await SaveIdempotentAsync(db, ct);
row = await db.Accounts.FirstAsync(a => a.Subject == subject, ct);
```

La première affectation ne sert à rien : la relecture est **systématique**, pas
conditionnelle. On l'avait gardée parce qu'elle « se lisait bien » — ce qui est
exactement ce que le commentaire doit faire, pas la variable.

**Consigne** : quand une relecture suit inconditionnellement une écriture, ne pas
capturer le résultat de l'écriture. Si le lecteur a besoin de comprendre pourquoi
on relit, c'est un commentaire qu'il faut, pas une variable morte.

---

## S4457 — la validation des arguments se fait hors du corps `async`

**Occurrences : 2** (task-299, task-300)

> ⚠️ **Récidive sur du code frais (task-300).** `PostgresAuditSink.WriteBatchAsync`
> et `PostgresAuditReader.GetTracesAsync` ont été écrites avec un `ThrowIfNull` en
> tête d'une méthode `async`, alors que la consigne ci-dessous existait déjà. Le
> protocole des conventions dit ce que signale une récidive : le fichier n'a pas
> été lu avant d'écrire. À relire **avant** tout nouveau contrat asynchrone.

Dans une méthode `async`, le corps ne s'exécute qu'à la première consommation de
la tâche. Un `ArgumentException.ThrowIfNullOrWhiteSpace` placé en tête d'une
méthode `async` ne lève donc **pas à l'appel** : il lève au premier `await` de
l'appelant, dans une pile déroulée où l'appel fautif n'apparaît plus.

**Consigne** : méthode publique **non-`async`** qui valide puis délègue à un
`…CoreAsync` privé.

```csharp
public Task<T> DoAsync(Request request, CancellationToken ct = default)
{
    ArgumentNullException.ThrowIfNull(request);      // lève À L'APPEL
    return DoCoreAsync(request, ct);
}

private async Task<T> DoCoreAsync(Request request, CancellationToken ct) { … }
```

S'applique dès qu'une méthode `async` publique valide ses arguments — donc à
presque toute méthode de contrat.

---

## CA1068 — le `CancellationToken` est le **dernier** paramètre

**Occurrences : 1** (task-299, 4 occurrences dans la même task)

Toutes sur des **helpers privés** dont la signature avait été calquée sur celle
du contrat public, lequel porte `(…, CancellationToken ct = default, string?
correlationId = null)` — un ordre imposé par la compatibilité des paramètres
optionnels côté contrat.

**Consigne** : ne pas recopier l'ordre du contrat dans les helpers privés. Sur un
privé, le jeton va **en dernier**, et les paramètres de corrélation ou de contexte
passent avant.

```csharp
// contrat public (ordre contraint par les valeurs par défaut)
Task<T> ReadAsync(string key, CancellationToken ct = default, string? correlationId = null);

// helper privé
private Task<T> ReadCoreAsync(string key, string? correlationId, CancellationToken ct);
```

---

## xUnit1051 — un test qui appelle une méthode à `CancellationToken` doit passer celui du contexte

**Occurrences : 2** (task-297 le 2026-09-13 — 10 appels, CI `develop` cassée ;
task-303 le même jour — 12 appels, attrapés avant le push)

La migration vers **xUnit v3** (`cf685ac`) a fait passer cet analyseur en
**erreur**. Tout appel de test vers une méthode qui accepte un
`CancellationToken` — y compris les vérifications NSubstitute
(`DidNotReceiveWithAnyArgs().Méthode(…)`) — doit passer
`TestContext.Current.CancellationToken`, jamais `default` ni rien.

**Consigne** : déclarer le raccourci en tête de classe de test et l'utiliser
partout, dès la première écriture.

```csharp
private static CancellationToken Ct => TestContext.Current.CancellationToken;

var result = await Sut.DoAsync(arg, Ct);
await _dependency.DidNotReceiveWithAnyArgs().DoAsync(default!, Ct);
```

**Pourquoi ça coûte cher** : la première occurrence est passée **verte sur la PR
et rouge sur `develop`** — l'écart entre les deux builds n'a jamais été expliqué
(voir `questions/merge-task-297.md`). Tant qu'il ne l'est pas, la seule
protection est d'écrire le token dès le départ : la garde « CI verte avant
merge » ne l'attrape pas de façon fiable.

---

## IDE1006 — le suffixe `Async` ne s'applique pas aux noms de tests

**Occurrences : 1** (task-303 le 2026-09-14 — 1777 méthodes de test en erreur
dans Visual Studio, dont 181 sur le seul `mss.mail.infrastructure.tests`)

`Api/Mail/.editorconfig` déclare `async_methods_end_in_async` en
**`severity = error`** sur tout `[*.cs]` : toute méthode `async` doit finir par
`Async`. CLAUDE.md règle 1 impose de son côté le format
`Method_Context_ExpectedResult` pour les tests. **Les deux règles se
contredisent frontalement** — un test conforme aux deux s'appellerait
`GetByIdAsync_NotFound_ReturnsNull_Async`.

La règle est désormais **désactivée sous `tests/`**, et reste `error` sous
`src/` :

```ini
# Api/Mail/.editorconfig
[tests/**/*.cs]
dotnet_naming_rule.async_methods_end_in_async.severity = none
```

**Consigne** : ne **jamais** renommer une méthode de test pour satisfaire
IDE1006, et ne jamais proposer un `#pragma` ou un `SuppressMessage` par fichier.
Si l'avertissement réapparaît sur un test, c'est la portée de la règle qui est
en cause, pas le nom du test. Sur `src/`, en revanche, le suffixe reste
obligatoire dès la première écriture.

**Pourquoi la règle n'a pas de sens sur un test** : le suffixe `Async` existe
pour distinguer, **sur un appelant**, la surcharge asynchrone de la synchrone.
Un test n'a ni appelant ni surcharge — xUnit le découvre par son attribut,
personne ne l'appelle par son nom, et ce nom sert à **une** chose : lire ce qui
a échoué dans le rapport de test. La règle n'y protégeait rien et coûtait la
lisibilité de 1777 méthodes.

**Piège de diagnostic** : IDE1006 est un analyseur **IDE uniquement** — il ne
remonte **pas** au `dotnet build`, même avec `EnforceCodeStyleInBuild=true`.
Visual Studio ne le signale que pour les fichiers **ouverts**, ce qui fait
passer un problème de 1777 occurrences pour un problème local à un fichier.
Pour mesurer la portée réelle avant de corriger :

```bash
dotnet format style {projet}.csproj --verify-no-changes --diagnostics IDE1006
```
