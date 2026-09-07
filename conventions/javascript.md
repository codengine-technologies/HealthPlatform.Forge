# conventions/javascript.md — Conventions JavaScript apprises par la forge

> **Portée** : le JavaScript **hors Angular/Ionic** écrit par la forge dans les
> repos .NET — aujourd'hui le harnais de tir k6 d'`api-mail`
> (`Api/Mail/tests/loadtest-k6/`), demain tout outillage JS analysé par
> SonarJS. Le TypeScript Angular/Ionic relève de `conventions/angular.md`.
> **Lu par** : `/develop` (avant d'écrire du JS dans un repo .NET).
> **Alimenté par** : `/sonar` (l'analyse est multi-langage : le JS d'`api-mail`
> est scanné au même titre que le C#, et compte dans le new code du Quality Gate).
> **Jamais édité à la main** sauf pour retirer une convention devenue fausse.

## Protocole d'alimentation

Identique à `conventions/csharp.md` : une entrée dès la **première** correction
manuelle d'une règle sur du new code, puis incrément d'**Occurrences** à chaque
récidive.

## Format d'entrée

```markdown
### {règle-sonar-ou-slug} — {titre court}
- **Règle** : {clé Sonar exacte (ex. javascript:S6661)}
- **Repos** : {api-mail | tous repos .NET}
- **Consigne** : {ce que /develop doit faire d'emblée}
- **Origine** : task-NNN (/sonar, N occurrences corrigées)
- **Occurrences** : {n}
```

---

## Le runtime k6 accepte le JS moderne — vérifié, pas supposé

Avant task-174, la tentation était d'écrire du JS défensif « à l'ancienne »
(`Object.assign`, `a && a.b`, `indexOf(x) === 0`) par crainte du moteur
embarqué. **C'est inutile** : mesuré sur k6 v1.4.2 (moteur sobek), tous ces
constructs fonctionnent nativement —

| Construct | Statut |
|---|---|
| spread d'objet `{ ...o }` | ✅ |
| spread d'appel `f(...xs)` / `push(...xs)` | ✅ |
| `Array.prototype.flatMap` | ✅ |
| optional chaining `a?.b` | ✅ |
| nullish coalescing `a ?? b` | ✅ |
| `String#startsWith` / `endsWith` | ✅ |

Écrire la forme moderne d'emblée évite six des sept règles ci-dessous.
Vérification rapide d'un script sans backend : `k6 inspect <script.js>`
(exécute le contexte d'init, donc valide la syntaxe **et** les imports).

---

## Conventions actives

### javascript:S6661 — Spread d'objet plutôt que `Object.assign`
- **Règle** : `javascript:S6661`
- **Repos** : tous repos .NET (JS)
- **Consigne** : construire un objet dérivé avec `{ ...base, ...extra }`, jamais
  `Object.assign({ ... }, extra || {})`. Le `|| {}` devient inutile : `{ ...undefined }`
  est légal et n'ajoute rien.
- **Origine** : task-174 (/sonar, 4 occurrences corrigées)
- **Occurrences** : 1

### javascript:S4624 — Pas de template literal imbriqué
- **Règle** : `javascript:S4624`
- **Repos** : tous repos .NET (JS)
- **Consigne** : ne jamais interpoler un template dans un template
  (`` `a ${x ? `b ${y}` : ''}` ``). Extraire la branche dans une variable locale
  ou une petite fonction nommée, puis l'interpoler à plat. Fréquent dans le
  rendu de rapports — c'est là que la règle se déclenche.
- **Origine** : task-174 (/sonar, 4 occurrences corrigées)
- **Occurrences** : 1

### javascript:S6582 — Optional chaining plutôt que garde `&&`
- **Règle** : `javascript:S6582`
- **Repos** : tous repos .NET (JS)
- **Consigne** : écrire `a?.b` et non `a && a.b`. Attention au choix du
  fallback : `a?.b ?? d` retombe sur `d` quand `b` vaut `undefined`, alors que
  `a?.b ? a.b : d` retombe aussi sur toute valeur *falsy* (`0`, `''`). Choisir
  celle qui préserve la sémantique existante — un `0` transformé en défaut est
  une régression silencieuse dans un rapport de métriques.
- **Origine** : task-174 (/sonar, 3 occurrences corrigées)
- **Occurrences** : 1

### javascript:S6557 — `startsWith` plutôt que `indexOf(...) === 0`
- **Règle** : `javascript:S6557`
- **Repos** : tous repos .NET (JS)
- **Consigne** : `s.startsWith(p)` / `s.endsWith(p)`, jamais
  `s.indexOf(p) === 0` ni `s.slice(-n) === p`.
- **Origine** : task-174 (/sonar, 1 occurrence corrigée)
- **Occurrences** : 1

### javascript:S3863 — Un seul `import` par module
- **Règle** : `javascript:S3863`
- **Repos** : tous repos .NET (JS)
- **Consigne** : regrouper tous les symboles importés d'un même module dans une
  unique déclaration `import`. Le piège classique : ajouter un symbole plus tard
  (`import { X } from './config.js'` en bas de la liste) alors que le module est
  déjà importé en haut.
- **Origine** : task-174 (/sonar, 1 occurrence corrigée)
- **Occurrences** : 1

### javascript:S3776 — Complexité cognitive <= 15 (aussi en JS)
- **Règle** : `javascript:S3776`
- **Repos** : tous repos .NET (JS)
- **Consigne** : le plafond S3776 s'applique au JS comme au C#. Deux formes le
  font déborder sans qu'on le voie venir : (1) une fonction de rendu qui
  enchaîne sections, boucles et ternaires — la découper en **un builder par
  section** retournant un tableau de lignes, puis concaténer ; (2) une boucle
  dont le corps enchaîne `continue` et `if` imbriqués — extraire le corps dans
  une fonction qui **retourne** son résultat (ex. la liste d'erreurs), et
  remplacer la boucle par `map`/`flatMap`/`filter`.
  Contrairement au C#, il n'existe pas de commande dédiée `/sonar-s3776` pour
  le JS (elle est spécifique à `api-mail` C# et écrit des tests de
  caractérisation `dotnet`) : ces findings se traitent dans le run `/sonar`.
- **Origine** : task-174 (/sonar, 2 occurrences corrigées)
- **Occurrences** : 1

### javascript:S1940 — `!(x > 0)` : le fix suggéré change la sémantique NaN
- **Règle** : `javascript:S1940`
- **Repos** : tous repos .NET (JS)
- **Consigne** : Sonar propose de remplacer `!(x > 0)` par `x <= 0`. **Ne pas
  l'appliquer tel quel** : toute comparaison avec `NaN` est fausse, donc
  `!(NaN > 0)` vaut `true` alors que `NaN <= 0` vaut `false`. Le « fix » retire
  silencieusement la garde qui rattrape un `Number('vite')` ou une variable
  d'environnement illisible. Écrire d'emblée l'intention complète :
  `if (!Number.isFinite(x) || x <= 0)` — la règle est satisfaite **et** le cas
  NaN reste couvert. Même chose pour un plafond optionnel :
  `const bounded = Number.isFinite(c) && c > 0;`.
- **Origine** : task-209 (/sonar, 3 occurrences corrigées)
- **Occurrences** : 1

### javascript:S2245 — `Math.random()` est un security hotspot
- **Règle** : `javascript:S2245`
- **Repos** : tous repos .NET (JS)
- **Consigne** : tout `Math.random()` ouvre un **hotspot** que le Quality Gate
  exige de revoir (`new_security_hotspots_reviewed = 100%`), donc il bloque
  tant qu'il n'est pas traité. Dans un harnais de charge (tirage d'un profil,
  d'une rotation de session) l'usage est légitime : le marquer `SAFE` avec
  justification, ne pas le remplacer par de la crypto. Dans tout code produisant
  un identifiant, un token, un sel ou un secret : `Math.random()` est interdit —
  utiliser une source cryptographique.
- **Origine** : task-174 (/sonar, 2 hotspots revus `SAFE`)
- **Occurrences** : 1
