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

**Occurrences : 2** (task-203, task-289 — récidive sur du code frais, et
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

**Occurrences : 1** (task-184)

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
