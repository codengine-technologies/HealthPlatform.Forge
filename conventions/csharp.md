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

**Occurrences : 2** (task-200, task-191 — récidive sur code frais : une méthode
d'orchestration de test privée, `RaceTwoIngestionsAsync(connectionString, …)`, qui
reçoit tout en paramètre et ne lit aucun champ de la classe de test. Un helper de
test qui ne touche pas à la fixture injectée est `static` — la règle ne se limite
pas aux propriétés qui relaient une constante)

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

**Occurrences : 3** (task-203, task-273 — récidive sur code frais : tableaux
attendus d'un `Assert.Equal` dans un test de sollicitations ; la consigne vaut
aussi pour les attendus de test ; task-334 — `l.SequenceEqual(new[] { 2u })` dans un
`Arg.Is` NSubstitute, réécrit en `l.Count == 1 && l[0] == 2u`)

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

**Occurrences : 7** (task-203, task-289, task-299, task-188, task-345, task-353, task-354 — septième récidive, relevée par `/sonar` : un helper privé de test `MssanteRefusal()` déclaré `Exception` alors qu'il ne construit qu'une `SmtpProtocolException` — le réflexe « type large pour une fabrique d'exception de test » ; écrire le type construit. Sixième récidive.
Variante task-353 : un helper privé `PurgeVanishedMailsAsync(folder, IReadOnlyCollection<uint>)`
dont les deux appelants passent un `uint[]` — écrit « large » par réflexe pendant la passe
`/simplify`, comme sur task-289 : **un paramètre de helper privé prend le type de ce que ses
appelants ont déjà en main**.
Variante task-345 : un helper privé `ArrayOf(JsonElement, …)` déclaré
`IEnumerable<JsonElement>` pour unifier `EnumerateArray()` et un repli vide — le type
concret est ici `JsonElement[]` (`[.. array.EnumerateArray()] : []`).
Variante task-299 : une méthode privée `async`-sans-`await` qui **rendait
directement** la tâche concrète d'un appelé (`Task<bool>` du cache) sous un type
déclaré `Task`. La consigne vaut donc aussi pour le **relais d'une tâche** : soit
on déclare le type concret, soit on `await` — mais on ne masque pas un `Task<T>`
derrière un `Task`. Variante task-188, **dans un test** : une variable locale
typée par l'interface pour *documenter* que le conteneur sert ce contrat. Le
commentaire porte cette intention aussi bien, et gratuitement — la règle frappe
les locales de test exactement comme celles de production.)

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

**Occurrences : 3** (task-283 ; task-295, entrée suivante ; task-339 — `ReadTagViewAsync` d'un helper de
test HTTP, écrit APRÈS lecture de ce fichier : la consigne était lue, pas appliquée au moment d'écrire
un `Deserialize` « vite fait ». Réflexe : chercher `new JsonSerializerOptions(` dans son diff avant de
commiter.)

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

**Occurrences : 3** (task-184, task-342 — variante : une boucle qui **filtre**,
`foreach … if (pred) list.Add(x.Uid)`, s'écrit `Where(pred).Select(…).ToList()` ;
task-325 — **récidive sur du code frais**, écrite pendant la passe `/simplify` elle-même :
une boucle qui **cherche et rend** l'élément, `foreach (var k in Enum.GetValues<T>()) if (…) return k;`,
s'écrit `FirstOrDefault`. Piège sur un enum : `FirstOrDefault` rend la **première valeur**
quand rien ne correspond, pas une absence ; projeter d'abord en `T?`
(`.Select(k => (T?)k).FirstOrDefault(…)`), puis `if (kind is { } found)`)

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

**Occurrences : 14** (task-334 — ×3, « …throws "Host is null" ; task-334 — … » et « par défaut ; WireExisting… », attrapées par le contrôle mécanique §Q 2b avant la passe qualité ; task-354 — « …would demand a registry ; » dans un commentaire d'un banc d'intégration, attrapé par le contrôle mécanique §Q 2b avant le commit ; task-344 — ×2 dans l'extension « reprise des étiquetages IA », attrapées par le contrôle mécanique avant le commit ; task-348 — deux commentaires « … public ; c'est … », « … Toxiproxy ; with », attrapés par le contrôle mécanique lancé pendant `/sonar` ; task-184, task-292, task-188, task-322, task-171, task-342, task-191, task-330,
task-331 — neuvième, **attrapée par le contrôle mécanique avant le commit**, comme prévu : « …pas
l'objet ; le parcours… » au milieu d'un commentaire du seed e2e. Le contrôle marche. Le réflexe
d'écriture, lui, ne tient toujours pas : en français, l'espace avant le point-virgule est la
typographie normale, donc la faute vient naturellement. Écrire un point. —
huitième récidive : « …est INDISPONIBLE (503) ; » en fin de ligne d'un commentaire d'intention
de `SmtpService`, alors que le contrôle `git diff | grep -E "^\+\s*//.* ;"` ci-dessous aurait
rendu deux lignes. Le contrôle n'a pas été joué avant le commit : il fait désormais partie de la
passe qualité de `/develop`, au même titre que le build —
septième récidive : « The rule addresses a sender retiring the document it sent ; »
et « …kept this reading from having any effect ; the fix », deux « espace +
point-virgule » dans un commentaire d'intention ajouté au-dessus d'une méthode
existante. Réécrits avec une virgule et une conjonction. Le réflexe à prendre
avant de committer : `git diff | grep -E "^\+\s*//.* ;"` doit rester vide —
sixième récidive : « the first role gives profession, specialty and structure ; »,
un point-virgule en fin de ligne dans un commentaire d'intention. Cinquième
récidive sur code frais. Variante task-171 : deux commentaires d'intention en anglais
« « online » means a PSC token is obtainable through the proxy ; the token itself is
resolved at authentication time » — guillemets typographiques, point-virgule et
verbe technique suffisent. Reformulés en prose française sans ponctuation de code.
Quatrième récidive sur
code frais. Variante task-322 : une **condition entre accents graves** citée dans un
commentaire d'intention — `` `if (mail.Content == null) …` `` — pour désigner le
comportement d'un client. Un fragment conditionnel avec parenthèses et opérateur
suffit à déclencher la règle ; le paraphraser en français (« ils ne rechargent le
contenu que s'il manque ») porte la même information.) Historique : troisième récidive sur code
frais. Variante task-188 : une **liste à puces** `//   • …` dans un commentaire
d'intention, dont chaque item se terminait par `;` et portait des identifiants
entre accents graves. La puce, l'indentation et le point-virgule réunis suffisent
— la règle n'a pas besoin d'un vrai fragment de C#.)

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

**Consigne** : dans un commentaire, éviter le point-virgule en fin de ligne, les
fins de ligne en `)` ou `}`, **et les listes à puces indentées**. Écrire des
phrases. Le coût est nul et cela évite une issue qu'on est ensuite tenté
d'« accepter », ce qui use la crédibilité des exemptions.

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

**Occurrences : 3** (task-342, relevé par le `/sonar` de task-325 — `private readonly TimeProvider clock =
timeProvider ?? TimeProvider.System;` dans `ImapService` et `OfflineMailDataProvider` : un **défaut de repli**
sur un paramètre optionnel est aussi un initialiseur. Correctif sans constructeur explicite quand la valeur ne
coûte rien à recalculer : une propriété `private TimeProvider Clock => timeProvider ?? TimeProvider.System;` ;
task-297, task-343 — **récidive sur du code frais**, ×3 : `InMemoryAiConversationStorage`.
Variante task-343 : l'initialiseur ne dérivait d'**aucun** paramètre — `private readonly object _gate = new();`,
`private readonly Dictionary<…> _entries = [];` — et il a été signalé quand même, parce que la classe avait un
constructeur primaire. Idem pour une propriété `Stored { get; } = stored;` d'une classe interne à
constructeur primaire : un **record positionnel** la remplace sans initialiseur. Seuls les titres de
ce fichier avaient été lus avant d'écrire : la règle vaut pour **tout** initialiseur de membre
d'instance, dès qu'il y a un constructeur primaire)

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

**Occurrences : 5** (task-348 — `MailServerResolver.ResolveAsync` : `throw new ArgumentException` explicite en tête de la méthode `async`, **invisible au contrôle mécanique §Q 2b**, qui ne cherche que `ThrowIf…` ; contrôle sauté de surcroît, la passe qualité ayant été faite à la main ; task-329 — `OutgoingMailService.SendAsync` : `ThrowIfNull(mail)` en tête de la
méthode `async` publique, écrit alors que cette entrée existait ; d'où le contrôle mécanique de
`agents/develop.md` §Q 2b ; task-299, task-300, task-171 — `PscTokenProvider.GetModeAsync` /
`GetAccessTokenAsync` : `ThrowIfNull(key)` en tête d'une méthode `async`, corrigé en
enveloppe synchrone + `…CoreAsync` privée)

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

**Occurrences : 3** (task-297 le 2026-09-13 — 10 appels, CI `develop` cassée ;
task-303 le même jour — 12 appels, attrapés avant le push ; task-329 — 3 appels
`DidNotReceiveWithAnyArgs().SendMailAsync(default!, default)`, attrapés par le build : le
`default` d'un `CancellationToken` dans une vérification de substitut compte aussi)

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

---

## S138 — une méthode de plus de 80 lignes doit être découpée

**Occurrences : 1** (task-188)

Le piège n'est pas la méthode « fourre-tout » : c'est la méthode **qui enfile
trois temps distincts** sans que rien ne les sépare. Dans `StartSyncAsync`, la
réservation de la boîte (locale puis inter-instances), le corps du travail mis
en file, et la clôture du run cohabitaient dans un seul corps de 94 lignes. Le
seuil n'a fait que signaler ce que la lecture montrait déjà : trois
responsabilités, un seul nom.

```csharp
// ❌ AVANT — un seul corps : garde de préférence, réservation locale,
//            créneau distribué, closure de travail, clôture dans le finally
public async Task StartSyncAsync(UserContextInfo userContext, …)
{
    …                                   // 94 lignes
}

// ✅ APRÈS — chaque temps porte un nom, et devient testable seul
var runtime = await TryReserveRunAsync(userEmail, cancellationToken);
if (runtime is null) return;
…
finally { await CompleteRunAsync(userEmail, runtime, outcome); }
```

**Consigne** : quand une méthode orchestre une closure d'arrière-plan, sortir
d'emblée **ce qui précède** la mise en file (acquisition, garde, réservation) et
**ce qui suit** l'exécution (clôture, libération). Le corps restant est alors le
seul vrai sujet de la méthode. Ne pas attendre que Sonar compte les lignes : le
découpage d'après-coup oblige à re-valider un code déjà vert.

---

## S103 — une ligne de plus de 150 caractères doit être scindée

**Occurrences : 5** (task-334 — ×5, variante **assertion NSubstitute** : `Received(1).EnrichEmailsAsync("INBOX", Arg.Is<List<uint>>(…), Arg.Any<bool>(), Arg.Any<CancellationToken>())` après l'ajout d'un paramètre, scindées après la parenthèse ouvrante par le contrôle mécanique ; task-341 — variante **motif d'expression régulière** : le `[GeneratedRegex]` du garde de journalisation, une alternation de seize noms sur une ligne. Attrapé par le contrôle mécanique §Q 2b avant le commit, et scindé en trois littéraux `@"…" + @"…"`, ce qu'un attribut accepte puisque la concaténation reste une constante ; task-188, task-192 — ×11, variante **requête EF** : une
condition LINQ `x => filtre vide || EF.Functions.ILike(colonne, motif, SearchQueryHelper.LikeEscapeCharacter)`,
et un `select new Projection { A = …, B = …, … }` tenu sur une ligne. Corrigé par un
alias `private const string LikeEscape = SearchQueryHelper.LikeEscapeCharacter;` — une
constante reste traduisible par EF, contrairement à une méthode d'aide — et par un
initialiseur d'objet déplié à un membre par ligne)

task-333 : le message du balayage de `IheXdmScratch` a pris « or extraction folder(s) » en cours de route, et a franchi 150 caractères d'un seul. Récidive sur un message **modifié**, pas créé : la relecture de la consigne vaut aussi quand on allonge un gabarit existant.

Presque toujours un **gabarit de journalisation** : le message structuré grossit
naturellement (préfixe du composant, deux ou trois placeholders, puis la phrase
qui explique la conséquence pour l'exploitant), et il passe les 150 caractères
sans qu'on y prenne garde.

```csharp
// ❌ AVANT — 167 caractères
_logger.LogError(ex, "[X] Failed to broadcast the close order for {Email} Session={ClientSessionId} — other instances will fall back on session expiry", …);

// ✅ APRÈS — deux littéraux concaténés : le gabarit reste constant à la
//            compilation, donc la journalisation structurée est intacte
_logger.LogError(
    ex,
    "[X] Failed to broadcast the close order for {Email} "
    + "Session={ClientSessionId} — other instances will fall back on session expiry",
    …);
```

**Consigne** : scinder par **concaténation de littéraux** (`"…" + "…"`), jamais
par interpolation ni par `string.Format` — un gabarit qui cesse d'être une
constante fait perdre le nom des propriétés structurées et déclenche à son tour
les règles de journalisation. Découper au mot, pas au milieu d'un placeholder.
Dans une requête EF, un nom qualifié long répété (`SearchQueryHelper.LikeEscapeCharacter`)
se remplace par une `const` locale à la classe, et une projection `select new X { … }`
de plus de trois membres s'écrit d'emblée un membre par ligne.

## S134 — pas plus de trois niveaux de structures de contrôle imbriquées

**Occurrences : 1** (task-333 — `ImapService.PersistEnrichedBatchAsync` : un `try/catch` ajouté autour d'un `if` dans un `foreach`, lui-même dans le `try` du verrou de persistance)

Le piège : protéger **un appel** d'une boucle qui tourne déjà dans un `try`. Le `try` ajouté compte comme un niveau, et la boucle d'orchestration passe à quatre.

```csharp
// ❌ AVANT — try (verrou) > foreach > try > if
foreach (var mail in fetched)
{
    try
    {
        if (await PersistAsync(mail, ct)) { processed++; }
    }
    catch (IheXdmTechnicalFailureException) { failures.Add(mail.Uid); }
}

// ✅ APRÈS — l'appel protégé rend un booléen, la boucle reste à trois niveaux
foreach (var mail in fetched)
{
    if (await PersistUnlessArchiveUnreadableAsync(mail, failures, ct)) { processed++; }
}
```

**Consigne** : un `catch` qui ne concerne qu'**un appel** d'une boucle sort dans une méthode dédiée qui rend le résultat normalisé (booléen, `Result`). C'est le même geste que la consigne de S3776 sur les `catch` multiples : l'appelant reste linéaire.

## S3925 — une exception garde le triplet de constructeurs recommandé

**Occurrences : 4** (task-171 — `UnauthorizedException`, `PscIdentityConflictException` ; task-320 — `MailboxIncompatibleException` ; task-330 — `SmtpDeliveryUncertainException`, triplet présent, marquée FALSE-POSITIVE comme prévu ; task-352 — `NotFoundException`, classe **non scellée** qui reçoit une propriété `ErrorCode` : la règle se lève sur une exception existante dès qu'on lui ajoute un membre, triplet présent, FALSE-POSITIVE)

La passe qualité avait **retiré** les constructeurs « inutilisés » de deux
exceptions neuves pour ne garder que celui réellement appelé. Sonar réclame le
motif de sérialisation recommandé : sans-argument, `(string message)` et
`(string message, Exception innerException)`, même si personne ne les appelle.

```csharp
// ❌ AVANT — un seul constructeur, celui que le code appelle
public sealed class UnauthorizedException(string message, string? errorCode) : Exception(message) { … }

// ✅ APRÈS — le triplet, plus le constructeur métier
public UnauthorizedException() { }
public UnauthorizedException(string message) : base(message) { }
public UnauthorizedException(string message, string? errorCode) : base(message) { ErrorCode = errorCode; }
public UnauthorizedException(string message, Exception innerException) : base(message, innerException) { }
```

**Consigne** : une nouvelle exception porte toujours les trois constructeurs
standards — et une passe « simplification » ne les retire jamais, même
inutilisés : ce n'est pas du code mort, c'est le contrat de la règle.

**Et une fois le triplet présent, la règle reste levée** (task-320) : sur .NET 8+
elle réclame encore le constructeur de sérialisation `ISerializable`, lui-même
obsolète (SYSLIB0051). Ne pas l'ajouter, ne pas « corriger » la classe : marquer
l'issue FALSE-POSITIVE avec ce motif, comme toutes les exceptions voisines de
`Application/Exceptions/`.

## S3776 — un `try/catch` ajouté à une méthode déjà chargée la fait déborder

**Occurrences : 1** (task-330 — `DraftService.SendDraftAsync`, complexité cognitive 16)

La méthode tenait sous le seuil. Le changement de contrat de `SmtpService` (il lève là où il
rendait un `Result`) a demandé trois `catch` autour de l'appel SMTP. Chacun compte, imbriqué dans
le `try/finally` du verrou d'envoi : le seuil de 15 est franchi d'un point.

**Consigne** : protéger un appel par plusieurs `catch` **dans une méthode qui a déjà un
`try/finally` ou plusieurs branches** se fait dans une méthode dédiée. Celle-ci rend le résultat
normalisé (ici `SendThroughSmtpAsync`, qui rend un `Result`), et l'appelant reste linéaire. La
blacklist S3776 ne vaut que pour la dette legacy : sur du code neuf, la règle se corrige toujours.

## S1075 — pas de délimiteur de chemin ou d'URI en dur

**Occurrences : 1** (task-171 — `DependencyInjection.AddPscProxyClient`)

Garantir le slash final d'une base d'URL par `TrimEnd('/') + "/"` déclenche la
règle sur le littéral `"/"`. `UriBuilder` fait le même travail sans littéral.

```csharp
// ❌ AVANT
if (Uri.TryCreate(options.BaseUrl.TrimEnd('/') + "/", UriKind.Absolute, out var baseAddress)) …

// ✅ APRÈS
if (Uri.TryCreate(options.BaseUrl, UriKind.Absolute, out var baseAddress))
{
    var builder = new UriBuilder(baseAddress);
    if (!builder.Path.EndsWith('/')) { builder.Path += '/'; }
    client.BaseAddress = builder.Uri;
}
```

**Consigne** : normaliser une URL avec `UriBuilder` (et des `char`), jamais par
concaténation d'un littéral `"/"`.

## S1172 — un paramètre que la méthode n'utilise plus se retire

**Occurrences : 1** (task-171 — `AddPscProxyClient(services, configuration)`)

Une méthode d'enregistrement DI lisait la configuration pour lier ses options ;
la passe qualité a basculé la lecture sur `IOptions<>` au moment de la
résolution, et le paramètre `IConfiguration` est resté dans la signature.

**Consigne** : après avoir déplacé la lecture d'une dépendance, relire la
signature de la méthode et son appelant — un paramètre orphelin est le résidu
le plus courant d'un refactor « lu au point d'usage plutôt qu'à l'enregistrement ».

---

## S2302 — un nom de paramètre cité dans un message s'écrit `nameof(...)`

**Occurrences : 1** (task-342 — `MailController.DownloadAttachment`)

Un message d'exception de validation qui **contient le nom du paramètre** comme
mot (« The attachment occurrence must be zero or positive. », paramètre
`occurrence`) est signalé : si le paramètre est renommé, le message ment.

```csharp
// ❌ AVANT
throw new ValidationException("The attachment occurrence must be zero or positive.");

// ✅ APRÈS — même texte, lié au symbole
throw new ValidationException($"The attachment {nameof(occurrence)} must be zero or positive.");
```

**Consigne** : dans un message qui nomme un paramètre, utiliser `nameof`. En
français, le piège est l'homonymie (« du contact {contactId} » avec un paramètre
`contact`) : reformuler (« de la fiche {contactId} ») plutôt que d'injecter un
identifiant anglais dans une phrase française.

---

## S4136 — les surcharges d'une méthode sont adjacentes

**Occurrences : 1** (task-342 — `Infrastructure.Mock/Repository/MailRepository`)

Ajouter une surcharge (ici le paramètre `occurrence` de `GetAttachmentAsync` /
`UpdateAttachmentAsync`) **en bas de la classe** ou groupée avec l'autre
surcharge nouvelle sépare chaque surcharge de sa sœur.

**Consigne** : une nouvelle surcharge s'insère **juste sous** la surcharge
existante du même nom, jamais en bloc « les nouveautés ensemble ».

---

## xUnit1045 — une donnée de théorie `object` n'est pas sérialisable

**Occurrences : 2** (task-342 — `RuleTwelveRemainingResponsesIntegrationTests` ; task-330 —
`TheoryData<Exception>` des coupures de transport de `SmtpServiceCoverageTests`. Une exception
n'est pas plus sérialisable qu'un objet anonyme : la théorie prend une chaîne, et le test construit
l'exception)

`TheoryData<string, string, object>` avec des objets anonymes comme corps de
requête : xUnit ne peut pas sérialiser la ligne, l'explorateur de tests ne voit
qu'un seul cas.

```csharp
// ❌ AVANT
public static TheoryData<string, string, object> InvalidModels => new()
{
    { "POST", "/api/v1/search/semantic", new { query = "bilan", maxResults = 999 } },
};
// ... Content = JsonContent.Create(body)

// ✅ APRÈS — le corps voyage en JSON
private static string Json(object body) => JsonSerializer.Serialize(body);
public static TheoryData<string, string, string> InvalidModels => new()
{
    { "POST", "/api/v1/search/semantic", Json(new { query = "bilan", maxResults = 999 }) },
};
// ... Content = new StringContent(body, Encoding.UTF8, "application/json")
```

**Consigne** : les données de théorie sont des types primitifs, des chaînes ou
des types `IXunitSerializable` — un corps de requête se passe en chaîne JSON.

---

## xUnit2032 — `Assert.IsAssignableFrom` se dit `Assert.IsType(…, exactMatch: false)`

**Occurrences : 1** (task-329 — `MailControllerCoverageTests`, sur un `IStatusCodeActionResult`)

xUnit 3 signale `Assert.IsAssignableFrom<T>(x)` : le nom laisse croire à une comparaison exacte. La
même vérification s'écrit `Assert.IsType<T>(x, exactMatch: false)`.

**Consigne** : pour vérifier qu'une valeur est d'un type ou d'un de ses dérivés (une interface
comme `IStatusCodeActionResult`), écrire `Assert.IsType<T>(x, exactMatch: false)`, jamais
`IsAssignableFrom`.

## S2699 — un test « ne lève pas » affirme quelque chose

**Occurrences : 1** (task-342 — `UserMailServerHostPolicyTests`, deux tests
`…_Succeeds` réduits à un `await` sans assertion)

**Consigne** : un test dont l'attendu est « aucune exception » s'écrit
`var error = await Record.ExceptionAsync(() => …); Assert.Null(error);` — et
ajoute, quand il existe, l'effet de bord qui prouve le chemin pris (par exemple
`DidNotReceiveWithAnyArgs()` sur le collaborateur qui ne doit pas être appelé).

---

## memoire-vers-redis-chemins-faillibles — un état qui quitte la mémoire rend faillibles des chemins qui ne l'étaient pas

**Occurrences : 1** (task-343, revue — ×2 dans la même task)

Déplacer un état de la mémoire du processus vers Redis (pour le partager entre réplicas) ne
change pas seulement **où** il vit : chaque lecture et chaque écriture peuvent désormais **échouer**
(délai, connexion, conflit de version). Les appelants avaient été écrits pour une opération
infaillible, et deux chemins sont passés au travers :

- **le démarrage** : un abonnement Redis posé dans `IHostedService.StartAsync` lève une
  `RedisConnectionException` → l'hôte avorte → tous les pods redémarrent en boucle pendant une
  panne Redis au déploiement ;
- **un flux en streaming** (`IAsyncEnumerable`) : l'écriture finale du tour lève après que la
  réponse a été envoyée → le client reçoit un `SERVER_ERROR` générique, et une réponse qu'il a lue
  n'est pas conservée, sans qu'il le sache.

**Consigne** : quand un état passe de la mémoire à un magasin distant, **lister chaque appelant**
et décider explicitement ce qu'il fait d'un échec :

- **démarrage** → ne jamais faire échouer `StartAsync` pour une fonction dont l'API peut se passer
  un temps ; réessayer en arrière-plan jusqu'au succès ou à l'arrêt (et le tester, Redis en pause
  au démarrage) ;
- **streaming** → attraper `ConflictException` / `RedisException` / `TimeoutException` à
  l'écriture et émettre un **événement d'erreur explicite** (un code par cause) au lieu de l'événement
  final ;
- **journalisation** → le type de l'exception, jamais son message si elle vient d'une
  désérialisation : il cite le document, qui cite des mails.
- **abonnement pub/sub raté** → StackExchange.Redis (2.7) a déjà **attaché** la
  `ChannelMessageQueue` au multiplexeur quand `SubscribeAsync` lève : la détacher
  (`UnsubscribeAsync`) avant de réessayer, sinon chaque réessai laisse une file orpheline qui, Redis
  revenu, bufférise sans borne tout le canal. Invisible à `PUBSUB NUMSUB` (un seul abonné côté
  serveur) : le garde compte les files attachées (`FailedSubscriptionAttempts_LeaveNoOrphanQueueBehind`).

**Preuve** : `SseBackplaneTests.SubscriptionService_WhenRedisIsDownAtStartup_…`,
`MultiReplicaRedisIntegrationTests.Replica_StartedWhileRedisDoesNotAnswer_…`,
`AiConversationTurnPersistenceTests` (rouges sur le code d'avant la reprise).

---

## collection-postgresql-partagee — un test d'intégration qui écrit en base partagée nettoie ce qu'il écrit

**Occurrences : 1** (task-325, `/sonar` — rouge en Release seulement)

Les tests de `[Collection("PostgreSql")]` partagent **un seul** conteneur Postgres, sans purge
entre classes. Une ligne laissée par un test est lue par les autres, et le résultat dépend
de l'ordre d'exécution.

Constaté sur task-325 :
- `SemanticSearchEmbeddingModelTests` laissait des vecteurs de 3 et 5 dimensions ;
- `AiDiagnosticsControllerIntegrationTests` balaie **tous** les vecteurs stockés contre une
  requête de 1536 dimensions, et pgvector a levé `different vector dimensions 3 and 1536` ;
- la suite était verte en Debug et rouge en Release, avec le même code.

Le test lésé portait déjà un commentaire qui décrivait exactement ce piège. Il n'avait pas été
lu.

**Consigne** :
- Tout test de la collection qui **insère** des lignes les **supprime** en fin de test :
  `IAsyncDisposable`, et `ExecuteDeleteAsync` sur ce que le test a créé, repéré par un dossier
  ou un identifiant qui lui est propre.
- Un vecteur stocké en base partagée fait **1536 dimensions**, la dimension de production, sauf
  quand le test prouve justement un écart de dimension. Dans ce cas, le nettoyage est encore plus
  indispensable.
- Avant d'écrire un test d'intégration sur une table déjà exercée, lire les tests existants de
  cette table : leurs commentaires disent ce qu'ils attendent de la base.

**Preuve** : `SemanticSearchEmbeddingModelTests.DisposeAsync`. Sans lui,
`AiDiagnosticsControllerIntegrationTests` échoue en Release, deux exécutions sur deux ; avec lui,
673 tests passent.

---

## defaut-de-dev-dans-appsettings — `appsettings.json` est la configuration de production

**Occurrences : 1** (task-325, `/review`)

`src/Api/appsettings.json` n'est pas un fichier de développement. C'est la configuration de
**tout déploiement qui ne passe pas par l'AppHost** : les configmaps de Prod et de Staging
(dépôt `DevOps`) ne surchargent que quelques clés. task-325 y avait inscrit le défaut hybride
« de développement et de banc », un chat Ollama sur `127.0.0.1:11434`. Aucun pod n'a
d'Ollama : le démarrage aurait réussi, puis l'étiquetage, le résumé et l'assistant auraient
échoué en silence.

**Consigne** :
- Un défaut propre au développement ou au banc se pose **dans l'AppHost**
  (`WithEnvironment`), jamais dans `appsettings.json`.
- Une valeur de `appsettings.json` qui change le comportement d'un déploiement se vérifie contre
  `DevOps/Prod/configmap.yaml` et `DevOps/Staging/configmap.yaml`, et un test la garde.
- Une DOD qui dit « défaut livré » doit préciser **où** : AppHost ou `appsettings.json`.

**Preuve** : `EmbeddingOptionsConsistencyTests.AppSettings_ShipsAllOpenAi_BecauseDeploymentsHaveNoOllama`,
rouge sur le défaut hybride.

---

## sortie-de-modele-non-fiable — Une réponse de LLM appliquée au texte se contrôle en entier

**Occurrences : 1** (task-349, revue)

Le garde de la correction orthographique (`SpellingCorrectionGuard`) comparait les noms de
balises et les `href`, pas les autres attributs. Une réponse du modèle qui ajoutait `onclick`,
`style` ou `class` à une balise était donc acceptée et appliquée au message. Or le texte envoyé
peut venir d'un tiers (une sélection dans un message reçu), et donc porter une injection de prompt.

**Consigne** : tout HTML rendu par un modèle et destiné à remplacer le texte du praticien est
comparé à l'original sur **tout** ce qui n'a pas le droit de changer : balises, **tous** les
attributs normalisés (nom en minuscules, valeur décodée, ordre alphabétique), termes protégés. Le
test rouge d'abord pose l'attribut qu'un attaquant ajouterait (`onclick`).

**Preuve** : `SpellingCorrectionGuardTests.Check_AnAddedOrAlteredAttribute_IsRefused`, rouge sur
les trois cas avant le correctif.

---

## S1067 — un filtre EF à critères optionnels se compose, il ne s'écrit pas en une expression

**Occurrences : 1** (task-338, ×3 — filtres patient, dates de document, dates de biologie de
`SemanticSearchRepository`)

Le motif vient naturellement quand plusieurs critères **facultatifs** doivent porter sur **le
même** enregistrement lié : on écrit un seul `Any(...)` qui enchaîne `(x == null || col == x)`
pour chaque critère. Sonar compte les opérateurs conditionnels (7 pour trois critères), et le SQL
produit traîne des `@x IS NULL OR …` que le planificateur ne simplifie pas toujours.

```csharp
// ❌ AVANT — une expression, trois critères optionnels, 7 opérateurs
query.Where(m => db.MailMedicalDocuments.Any(md =>
    md.MailId == m.Id
    && (!hasLastName || EF.Functions.ILike(md.PatientLastName, pattern, LikeEscape))
    && (ins == null || md.Ins == ins)
    && (patientId == null || md.PatientId == patientId)));

// ✅ APRÈS — chaque critère présent restreint un même ensemble, un seul EXISTS le lit
var documents = db.MailMedicalDocuments.AsQueryable();
if (hasLastName) documents = documents.Where(md => EF.Functions.ILike(md.PatientLastName, pattern, LikeEscape));
if (ins != null) documents = documents.Where(md => md.Ins == ins);
if (patientId != null) documents = documents.Where(md => md.PatientId == patientId);
query = query.Where(m => documents.Any(md => md.MailId == m.Id));
```

**Consigne** : dès qu'un filtre combine plus de deux critères facultatifs, construire un
`IQueryable` intermédiaire par `if` successifs, puis le tester par un `Any` unique. EF Core inline
la sous-requête capturée ; la sémantique « tous les critères sur le même enregistrement » est
conservée, et seuls les critères présents atteignent le SQL. Garder un test d'intégration qui
combine deux critères sur deux enregistrements différents — c'est lui qui prouve que l'on n'a pas
glissé vers « un critère par enregistrement ».

---

## executeupdate-copie-suivie-perimee — après un `ExecuteUpdate`, une entité suivie ment

**Occurrences : 1** (task-330, `/develop` — deux faces du même piège dans `PendingActionRepository`)

`ExecuteUpdateAsync` écrit en base **sans passer par le suivi d'entités** : une copie déjà suivie
par le contexte garde ses anciennes valeurs, et une requête suivie (`FirstOrDefaultAsync`) renvoie
cette copie, pas la ligne relue. Deux effets, constatés le même jour :

- **Modifier la copie ne modifie rien.** La réclamation passe la ligne en `Processing` par
  `ExecuteUpdate`. La copie suivie dit encore `Pending`. Remettre `Status = Pending` n'est vu comme
  aucun changement, donc `SaveChanges` n'écrit pas le statut. La ligne reste `Processing` en base.
  Cela arrive dès que le contexte vit d'une passe à l'autre : c'est le cas de la synchronisation de
  fond, qui garde son scope.
- **Décider sur la copie, c'est décider sur un état passé.** `GetByIdAsync` suivi lisait
  « confirmable » alors que la base disait « remise incertaine ».

```csharp
// ❌ copie suivie, peut-être périmée par un ExecuteUpdate antérieur
var action = await db.PendingActions.FirstOrDefaultAsync(pa => pa.Id == id);
action.Status = PendingActionStatus.Pending;          // « inchangé » pour EF
await db.SaveChangesAsync();

// ✅ relire avant de modifier, et lire sans suivi pour décider
await db.Entry(action).ReloadAsync();
// … et pour une lecture de décision : .AsNoTracking().FirstOrDefaultAsync(...)
```

**Consigne** :
- Un dépôt qui mêle `ExecuteUpdate` et lecture-modification-`SaveChanges` sur **la même table**
  relit (`ReloadAsync`) avant de modifier, ou fait toute la transition en `ExecuteUpdate`.
- Une lecture qui sert à **décider** (« peut-on confirmer ? ») est `AsNoTracking()`.
- Un test d'intégration ne relit **jamais** son verdict par le contexte du serveur : il le relit
  dans un scope neuf. Sinon il constate la copie périmée, et donne un vert qui ment.

**Preuve** : `PendingSendConfirmationIntegrationTests.AGestureWhoseReplayFails_…` et
`AReplayAbandonedMidway_…` sont rouges sans `ReloadAsync`, et
`ADeliveryUncertainConfirmation_…` est rouge (404 au lieu de 409) sans `AsNoTracking`.
Preuve par mutation.

---

## index-de-cle-etrangere-absent-en-base — une colonne de filtre sans index, que la fixture fait croire indexée

**Occurrences : 2**
- task-322 : les index `MailId` de `MailAttachments` et `MailMedicalDocuments` n'existaient pas en base.
- task-331 : `MailMedicalDocuments.PatientId` est devenu le filtre du dossier patient, sans index en base.

PostgreSQL ne crée **aucun** index pour une clé étrangère, et FluentMigrator, qui construit les
bases praticien, non plus. La base de la fixture `PostgreSql`, elle, est construite par
`EnsureCreated`, et EF y crée un index par clé étrangère **par convention**. Un test lu sur la
fixture (`pg_indexes`, un plan d'exécution, un temps de réponse) est donc vert sans la migration.
En production, chaque page parcourt la table.

**Consigne** :
- Toute requête qui filtre, groupe ou joint sur une colonne que la task met au premier plan
  (clé étrangère comprise) : vérifier dans `SetupMigration` **et** les migrations suivantes qu'un
  index la mène. S'il manque, une migration FluentMigrator le crée, et `MailDataContext` le déclare
  sous le même nom.
- La preuve rejoue **le coureur de production** sur une base neuve, sur le modèle de
  `MailIdIndexesMigrationTests` et `PatientFolderIndexMigrationTests`, jamais `pg_indexes` sur la
  fixture.

---

## projection-dto-dupliquee — une projection entité → DTO s'écrit une fois

**Occurrences : 2**
- task-184 : `PatientRepository.ToDto` ne portait pas `Id`.
- task-331 : les deux copies inline de la même projection, dans la recherche et dans « patients
  du jour », ne le portaient toujours pas. Le dossier ouvert depuis ces listes répondait 404.

Trois copies à la main de la même projection `new MailPatientDto { … }` : une correction en atteint
une, les autres divergent en silence. Chaque champ ajouté au DTO doit être reporté en N endroits.

```csharp
// ❌ une copie par requête
.Select(p => new MailPatientDto { FirstName = p.FirstName ?? string.Empty, /* … */ })

// ✅ une seule expression : traduite en SQL par les listes, compilée pour une entité chargée
private static readonly Expression<Func<MailPatient, MailPatientDto>> DtoProjection = p => new MailPatientDto { Id = p.Id, /* … */ };
private static readonly Func<MailPatient, MailPatientDto> ToDtoCompiled = DtoProjection.Compile();
.Select(DtoProjection)
```

**Consigne** : avant d'écrire un `Select(x => new XxxDto { … })`, chercher une projection ou un
mapper existant du même DTO dans le dépôt. S'il en existe un, le réutiliser. S'il en faut une
version SQL, en faire une `Expression` partagée, jamais une copie.

---

## S4581 — un `Guid` attendu « n'importe lequel » s'écrit `Arg.Any<Guid>()`, pas `default`

**Occurrences : 1** (task-331, `client-blazor` — `PatientAttachmentDialogTests`, deux
`DidNotReceiveWithAnyArgs().AttachDocumentToPatientAsync(default, default, default)`)

Les analyseurs Sonar du build `client-blazor` traitent l'avertissement en erreur : un `default` passé
pour un `Guid` est lu comme un `new Guid()` vide, et le build casse sans qu'aucun test ne tourne.

```csharp
// ❌ S4581 — « Use Guid.NewGuid() or Guid.Empty »
_patients.DidNotReceiveWithAnyArgs().AttachDocumentToPatientAsync(default, default, default);

// ✅ l'intention dite par l'argument lui-même
_patients.DidNotReceive().AttachDocumentToPatientAsync(Arg.Any<Guid>(), Arg.Any<Guid>(), Arg.Any<CancellationToken>());
```

**Consigne** : dans un `Received` / `DidNotReceive` NSubstitute, ne jamais passer `default` pour un
`Guid`. Écrire `Arg.Any<Guid>()`, ou la valeur attendue.

---

## S6562 — un `DateTime` de test précise son `DateTimeKind`

**Occurrences : 1** (task-331, `client-blazor` — `PatientAttachmentDialogTests`, trois dates de
naissance `new DateTime(1982, 6, 14)`)

Même mécanisme que S4581 : erreur de build dans `client-blazor`.

**Consigne** : `new DateTime(a, m, j, 0, 0, 0, DateTimeKind.Unspecified)` pour une date sans heure
(une date de naissance), `DateTimeKind.Utc` pour un instant. Jamais le constructeur sans `Kind`.

---

## marqueur-derive-apres-filtrage — un drapeau qui résume des lignes se calcule depuis les lignes retenues

**Occurrences : 1** (task-338, reprise au HAG — filtre « Biologie » de la recherche : 23 faux
positifs sur 35 dans une boîte de formation)

Un booléen dénormalisé (`HasBiologyResults`, `HasPatientSummary`, `HasAttachments`…) résume des
lignes enfants. Quand on le pose **avant** le filtrage de ces lignes, il ment dès que toutes sont
écartées : la colonne dit « il y a des résultats », la table n'en contient aucun.

Constaté sur task-338 :
- `CdaParsingService.ProcessBiologyResults` posait `HasBiologyResults = true` en entrée de méthode,
  puis écartait chaque ligne sans valeur (`continue`) ;
- le parseur `interop-cda` rangeait les sections Antécédents en biologie, donc toutes leurs lignes
  étaient écartées ; le document restait marqué, et le mail héritait du marqueur ;
- la lecture recalculait le drapeau depuis les lignes (`MailRepository`, `Count > 0`) : l'écran de
  détail était juste, la recherche, qui filtre sur la colonne, ne l'était pas. **Deux vérités pour
  la même donnée.**

```csharp
// ❌ AVANT — le drapeau dit ce que le parseur a vu passer
document.HasBiologyResults = true;
foreach (var item in items)
{
    if (item.Value == null) continue;
    document.BiologyResults.Add(Map(item));
}

// ✅ APRÈS — le drapeau dit ce qui sera persisté, avec le même critère que le dépôt
foreach (var item in items) { … }
document.HasBiologyResults = document.BiologyResults.Exists(r => !string.IsNullOrEmpty(r.Name));
```

**Consigne** :
- Un drapeau dénormalisé se pose **après** le filtrage, depuis la collection retenue, avec le
  **même critère** que la couche qui persiste (ici : libellé non vide, comme `AddBiologyResultsToDocument`).
- Si la lecture recalcule le drapeau et que l'écriture le stocke, vérifier que les deux calculs sont
  identiques : la recherche lit la colonne stockée, pas le calcul de lecture.
- Une **vérité terrain relevée en exécutant le code sous test** grave ses défauts. `CdaSampleCorpus`
  déclarait la fiche de cardiologie « porteuse de biologie » parce que le parseur le disait. Avant
  d'écrire une valeur attendue, la vérifier dans la source (le CDA lui-même), pas dans la sortie.

**Preuve** : `SearchBiologyFilterFromCdaIntegrationTests` (vraies archives → ingestion PostgreSQL →
`POST /search/semantic`). Rouge sur l'ancien code (la fiche de cardiologie remonte), et rouge par
mutation avec le seul correctif api-mail sur Interop 93 (le compte rendu HPV qualitatif disparaît).

---

## S4143 — une même clé de dictionnaire écrite deux fois d'affilée

**Occurrences : 1** (task-331, `client-blazor` — `ManualAttachmentPanel.razor`, réserver une clé
puis l'écraser après un `await`)

Les analyseurs Sonar du build `client-blazor` signalent en **erreur** deux affectations successives
de la même clé, même séparées par un `await`. Le cas légitime (réserver une entrée pour qu'un rendu
concurrent ne relance pas l'appel, puis la remplir) se réécrit en deux passes distinctes.

```csharp
// ❌ S4143
_names[id] = string.Empty;
_names[id] = (await service.GetAsync(id))?.Name ?? string.Empty;

// ✅ réserver toutes les clés, puis remplir
missing.ForEach(id => _names.Add(id, string.Empty));
var records = await Task.WhenAll(missing.Select(id => service.GetAsync(id)));
foreach (var (id, record) in missing.Zip(records)) { _names[id] = record?.Name ?? string.Empty; }
```

**Consigne** : pour réserver puis remplir une entrée autour d'un appel asynchrone, écrire la
réservation (`Add` / `TryAdd`) et le remplissage dans deux boucles distinctes ; en bonus, les appels
partent en parallèle.

---

## CA1854 — `ContainsKey` puis indexeur : un `TryGetValue`

**Occurrences : 1** (task-331, `api-mail` — `PatientRepository.AttachDocumentToPatientAsync`, relevé par
`/sonar` sur le nouveau code)

```csharp
// ❌ deux recherches dans le dictionnaire
if (!parties.ContainsKey(patientId)) { return NotFound; }
...
return Attached(parties[patientId]);

// ✅ une seule, et la valeur nommée
if (!parties.TryGetValue(patientId, out var chosen)) { return NotFound; }
...
return Attached(chosen);
```

**Consigne** : dès qu'un `ContainsKey` garde un accès par indexeur à la même clé, écrire
`TryGetValue(key, out var value)` et utiliser `value`.

---

## test-de-rejet-attribuable — un test de refus doit échouer pour la raison qu'il nomme

**Occurrences : 1** (task-348, `/develop` — repéré par mutation, avant la revue)

Un test « l'hôte X est rejeté » peut passer alors que la règle qu'il prétend éprouver est
absente : il suffit qu'une **autre** règle rejette X avant elle. Constaté sur task-348 :
`DiscoverAsync_XmlPointingToAnIpLiteral_IsRejected` restait **vert** une fois le garde des IP
littérales retiré, parce que le DNS scripté du test ne connaissait pas le littéral et que
l'hôte était refusé comme « ne se résout pas ». Les quatre cas (127.0.0.1, 10.0.0.1, …) étaient
en outre tous non publics : le contrôle des plages les aurait refusés de toute façon.

**Consigne** :
- Pour chaque règle de refus, au moins un cas que **seule** cette règle refuse. Ici : une IP
  littérale **publique** (`203.0.113.10`), que le contrôle des plages laisse passer.
- Les doublures se comportent comme le vrai fournisseur sur le point testé : le DNS réel rend un
  littéral tel quel, le DNS scripté aussi.
- Prouver par mutation : retirer la règle, voir le test rougir **sur son assertion**, restaurer.
  Un test qui reste vert sous mutation est un vert qui ment, pas une couverture.

**Preuve** : `AutoconfigServiceTests.DiscoverAsync_XmlPointingToAnIpLiteral_IsRejected`,
cas `203.0.113.10` et `[2001:db8::25]` rouges sans le garde, verts avec.

---

## premisse-de-test-integration — un test d'intégration affirme d'abord que le chemin éprouvé a eu lieu

**Occurrences : 2** (task-339 — deux fois sur la même task, repérées par mutation)

Un test d'intégration peut passer alors que le chemin qu'il prétend éprouver n'a jamais été emprunté :
une précondition manquante le fait sauter, et le défaut ne peut alors pas se produire. Constaté deux fois :
- **trace du déplacement** : le test restait vert sous la mutation « contexte lu après la ré-indexation ».
  Le dossier cible, créé par un autre client, n'avait pas encore de ligne `MailFolders`. Sans sa
  génération, `RekeyMovedMailsAsync` saute la ré-indexation, et la ligne restait lisible sous le chemin
  source ;
- **serveur sans UIDPLUS** : le test était vert sur le code d'avant. Rien ne prouvait que la session avait
  bien perdu UIDPLUS, jusqu'à ce que le test affirme l'UID de destination nul.

**Consigne** :
- Écrire, dans le test, l'assertion qui prouve que la **prémisse** est réunie : la ligne a bien été
  ré-indexée, la session n'a pas rendu d'UID, le chemin de repli a bien été pris. Son message dit
  « le test n'éprouve rien », pas « le code est faux ».
- Créer la précondition comme l'application la crée (lister les dossiers avant de déplacer), pas par
  un raccourci qui la saute.
- Prouver par mutation (cf. `test-de-rejet-attribuable`) : un test qui reste vert sous mutation désigne
  d'abord une prémisse absente.

**Preuve** : `FolderOperationsEndToEndTests.MovingMessages_…_AndTracesTheMoveWithItsSubject` (mutation
verte avant la garde, rouge après) ; `OnAServerWithoutUidPlus_…` (UID de destination affirmé nul).

---

## S1313 — une borne de plage réseau ne s'écrit pas comme une adresse en dur

**Occurrences : 1** (task-348, `/sonar` — 11 hotspots sur `NonPublicNetworkAddress`)

La règle signale toute adresse IP littérale dans une chaîne (`IPAddress.Parse("10.0.0.0")`) comme un
hotspot « adresse codée en dur ». Pour une table de plages non publiques, ce sont des bornes de
réseau, pas des adresses à joindre : la règle se trompe de sens, mais chaque ligne laisse un hotspot
`TO_REVIEW` qui bloque le Quality Gate du nouveau code. Marquer « safe » sur le serveur ne suit pas
le code : le statut se perd sur un autre serveur ou une re-création du projet.

```csharp
// ❌ AVANT — 11 hotspots
(IPAddress.Parse("10.0.0.0"), 8),
(IPAddress.Parse("fc00::"), 7),

// ✅ APRÈS — mêmes réseaux, construits en octets, la notation usuelle en commentaire
(V4(10, 0), 8),         // 10.0.0.0/8 — privée
(V6(0xFC, 0x00), 7),    // fc00::/7 — unique locale
// IPAddress.IPv6Any / IPv6Loopback pour :: et ::1
```

**Consigne** : une adresse IP qui sert de borne ou de constante de réseau se construit en octets
(ou par les constantes d'`IPAddress`), avec sa notation usuelle en commentaire. Une adresse à
joindre, elle, vient de la configuration, jamais du code.

---

## CA1845 — `AsSpan` / `string.Concat` : sans objet dans une expression traduite en SQL

**Occurrences : 1** (task-339 — `FolderRepository.RenameFolderAsync`, deux `ExecuteUpdate`)

L'analyseur propose de remplacer `a + b.Substring(n)` par `string.Concat(a, b.AsSpan(n))`. Dans un
lambda que **EF Core traduit en SQL** (`Where`, `Select`, `SetProperty` d'`ExecuteUpdate`), c'est
impossible : un arbre d'expression ne peut porter ni `Span` ni `AsSpan`, et la forme d'origine est
exactement celle qu'EF traduit (`@p || substr(...)`).

```csharp
// CA1845 ne s'applique pas ici : expressions traduites en SQL par EF Core,
// un arbre d'expression ne peut porter ni Span ni AsSpan.
#pragma warning disable CA1845
await db.Mails
    .Where(m => m.FolderPath == oldPath || m.FolderPath.StartsWith(oldPrefix))
    .ExecuteUpdateAsync(set => set.SetProperty(
        m => m.FolderPath, m => newPath + m.FolderPath.Substring(oldPath.Length)));
#pragma warning restore CA1845
```

**Consigne** : dans une expression EF, garder `Substring` et suspendre CA1845 **localement**, la raison
écrite au-dessus (même forme que CA1862 dans `PatientRepository`). Hors EF (code exécuté en mémoire),
la règle s'applique normalement.

---

## unicite-garantie-par-la-base — un verrou de processus n'est pas une garantie entre réplicas, et un correctif d'écriture vaut pour ses chemins jumeaux

**Occurrences : 1** (task-344, AUD-18 b — promotion « en-têtes seuls » → contenu analysé)

Deux défauts dans la même méthode, `MailRepository.UpdateExistingMailWithContentAsync` :

- **Le garde était local au processus.** La promotion était sérialisée par un `SemaphoreSlim`
  (`enrich:{email}:{folder}`) et protégée par une lecture « déjà promu ? » faite **avant**
  l'écriture. Deux réplicas lisaient tous deux « non », puis écrivaient chacun un contenu et un jeu
  de documents médicaux : l'index `IX_MailContents_MailId` n'était pas unique. Le dossier patient
  montrait le compte rendu deux fois.
- **Le correctif d'atomicité n'avait été posé que sur un des deux chemins.** AUD-36 (task-342) avait
  mis l'insertion d'un mail neuf (`PersistNewMailAsync`) dans une transaction couvrant le chaînage de
  versions et les étiquettes. La promotion, son **jumeau** (même matériau, mail déjà présent), gardait
  ces écritures hors transaction : une panne après le `SaveChanges` laissait le mail « analysé » sans
  ses étiquettes, et il n'était jamais rejoué.

**Consigne** :
- Une règle « au plus une ligne par X » se garantit **en base** (index unique), jamais par un verrou
  ni par une lecture préalable. Le verrou (local ou Redis) n'est qu'une **économie** de travail ; le
  perdant de la course reçoit la violation d'unicité **nommée** (`ConstraintName`) et la traite comme
  « déjà fait », sans journaliser d'erreur.
- Un correctif sur un chemin d'écriture (atomicité, garde, détection) se reporte sur ses **chemins
  jumeaux** dans la même task : chercher les autres méthodes qui écrivent la même table avec le même
  matériau (ici, l'écrivain listé par `MailContentWriterScanTests` à côté de celui qu'on corrige).
- La preuve rejoue la course avec **deux contextes indépendants** et un intercepteur qui les retient
  ensemble juste avant l'écriture, sur une base construite par le coureur de production (l'index
  n'existe pas sur la fixture `EnsureCreated` d'avant le modèle).

**Preuve** : `MailPromotionUniquenessTests.TwoReplicasPromotingTheSameHeaderOnlyMail_…` (rouge sur
develop : 2 contenus, 2 documents, 4 lignes de biologie) et `APromotionFailingAfterItsDocuments_…`
(rouge sur develop : contenu et documents committés malgré la panne).

---

## declencheur-reellement-atteint — un traitement accroché à un cycle existant hérite de ses conditions de déclenchement

**Occurrences : 1** (task-344, extension « reprise des étiquetages IA » — attrapé par la passe qualité, angle altitude,
avant le push)

La reprise des étiquetages IA manqués a d'abord été accrochée à la fin de `BackgroundSyncService.SyncAllFoldersAsync`,
« la synchronisation de fond, par boîte ». Les tests unitaires de l'accroche étaient verts. Mais cette synchronisation
complète ne part que du **bouton du praticien** (`SyncController`, `forceManual: true`) : sans lui, elle est coupée par
`EnableFullSync=false`, réglage par défaut. La reprise n'aurait presque jamais tourné, en production comme au banc.

**Consigne** :
- Avant d'accrocher un traitement à un cycle existant (synchronisation, consommateur, tâche planifiée), **remonter ses
  appelants jusqu'au déclencheur réel** (`grep` des appels, réglages par défaut, flags) et l'écrire dans la doc du
  traitement : qui l'appelle, à quelle fréquence, sous quelle condition.
- Un test d'accroche (« X est appelé en fin de Y ») ne prouve rien si Y ne tourne pas : la DOD qui nomme un déclencheur
  nomme aussi sa fréquence attendue.
- Un traitement de rattrapage se branche sur le geste que **tout** praticien actif provoque (ici : l'enrichissement),
  borné par une cadence partagée entre réplicas, jamais sur une fonction optionnelle.

**Preuve** : `ImapServiceEnrichmentCoverageTests.EnrichEmailsAsync_SchedulesTheAiTaggingRecovery_…` (mutation : planificateur
jamais appelé → rouge) ; `AiTaggingRecoverySchedulerTests` (cadence, identité, panne Redis).

---

## S3358 — pas d'opérateur ternaire imbriqué

**Occurrences : 1** (task-334 — `EnrichedMailPersistence`, la raison de ne pas notifier un nouveau
mail, écrite `a ? "x" : b ? "y" : null`)

Un ternaire dans la branche d'un autre se lit mal et Sonar le signale dès qu'il apparaît dans du code
neuf. Le motif naît quand on condense une suite de cas en une seule expression.

```csharp
// ❌ AVANT
var skipReason = !isIncrementalSync ? "initialSync"
    : MailFolderNamingRule.IsSelfActionName(folder) ? "selfActionFolder"
    : null;

// ✅ APRÈS — une petite méthode, un retour par cas
private static string? SkipReasonOf(MailDto mail, bool isIncrementalSync)
{
    if (!isIncrementalSync)
    {
        return "initialSync";
    }

    return MailFolderNamingRule.IsSelfActionName(mail.FolderPath) ? "selfActionFolder" : null;
}
```

**Consigne** : au-delà de deux issues, une méthode à retours successifs, ou une expression `switch`.

---

## CA1875 — `Regex.Count`, pas `Regex.Matches(...).Count`

**Occurrences : 1** (task-334, ×2 — garde de source `MassTransitSingleRetryPolicyScanTests`)

`Matches(...).Count` construit une collection de correspondances pour n'en lire que la taille.
`Count(source)` compte sans rien allouer, et vaut aussi pour les regex générées (`[GeneratedRegex]`).

**Consigne** : pour compter des correspondances, `MaRegex().Count(texte)`. Les scans de source des
tests d'architecture sont le terrain habituel de ce motif.

---

## Exécution des tests — jamais de `--artifacts-path` hors du dépôt

**Occurrences : 1** (task-356 — `/review` : `dotnet test HealthPlatform.Api.Mail.sln
--artifacts-path <dossier temporaire>` → **177 faux échecs** dans `mss.mail.integration.tests`, plus
des échecs dans `api.tests` et `application.tests` : « Répertoire src/ introuvable depuis …\artifacts\bin\… » ;
rejoué compilé dans le dépôt : 0 échec)

Plusieurs tests d'api-mail retrouvent les fichiers du dépôt (`src/`, `src/Api/appsettings.json`) **en
remontant depuis le dossier de leurs binaires**. Compilés hors du dépôt, ils ne les trouvent plus.
Le rouge est alors faux, et il masque les vrais.

Le détour paraît tentant quand un AppHost ou Visual Studio verrouille `bin/` (« The file is locked
by: mss.mail.api.exe, devenv.exe »).

**Consigne** :
- valider (`/develop`, `/review`) **toujours dans le dépôt** : `dotnet build` / `dotnet test`
  sans `--artifacts-path` ;
- si `bin/` est verrouillé, demander à l'humain d'arrêter son AppHost ou de fermer la solution :
  ne pas contourner ;
- un `--artifacts-path` reste acceptable **seulement** pour un test ciblé qui ne lit aucun
  fichier du dépôt (exemple : `FeatureFlagEndpointIntegrationTests`). Le noter dans le Develop log.
