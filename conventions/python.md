# conventions/python.md — Conventions Python apprises par la forge

> **Portée** : le Python écrit par la forge dans les repos .NET — aujourd'hui le
> moteur de rapport du banc de charge d'`api-mail`
> (`Api/Mail/tests/loadtest-k6/report.py`, `observe.ps1`'s companions, les
> `test_*.py`), demain tout outillage Python analysé par SonarPython.
> **Lu par** : `/develop` (avant d'écrire du Python dans un repo .NET).
> **Alimenté par** : `/sonar` (l'analyse est multi-langage : le Python d'`api-mail`
> est scanné au même titre que le C# et le JS, et compte dans le new code du
> Quality Gate).
> **Jamais édité à la main** sauf pour retirer une convention devenue fausse.

## Protocole d'alimentation

Identique à `conventions/csharp.md` : une entrée dès la **première** correction
manuelle d'une règle sur du new code, puis incrément d'**Occurrences** à chaque
récidive.

## Format d'entrée

```markdown
### {règle-sonar-ou-slug} — {titre court}
- **Règle** : {clé Sonar exacte (ex. python:S1481)}
- **Repos** : {api-mail | tous repos .NET}
- **Consigne** : {ce que /develop doit faire d'emblée}
- **Origine** : task-NNN (/sonar, N occurrences corrigées)
- **Occurrences** : {n}
```

---

## Conventions actives

### python:S1192 — Un littéral cité 3 fois devient une constante de module
- **Règle** : `python:S1192`
- **Repos** : tous repos .NET (Python)
- **Consigne** : dès qu'une **clé** ou un **fragment de format** est cité 3 fois,
  le remonter en constante de module nommée. Les récidivistes du moteur de
  rapport sont les clés de métriques k6 (`"p(95)"`) et les fragments
  d'horodatage (`"+00:00"`, `"Z"`) — une faute de frappe sur l'une d'elles rend
  `None` sans rien dire, ce qui est exactement le mode d'échec silencieux que ce
  rapport existe pour empêcher. La règle ne se déclenche pas sur les littéraux
  courts (< 10 caractères), donc elle ne force pas à constantiser `"read"`.
- **Origine** : task-209 (/sonar, 2 littéraux corrigés — 7 occurrences)
- **Occurrences** : 1

### python:S1764 — `x == x` n'est pas la bonne façon de tester NaN
- **Règle** : `python:S1764`
- **Repos** : tous repos .NET (Python)
- **Consigne** : l'idiome historique `if value == value:` pour écarter un `NaN`
  est compté par Sonar comme un **bug** (`reliability_rating` dégradé à C sur une
  seule occurrence). Écrire `if not math.isnan(value):`. Cas typique :
  filtrer les points `NaN` que `histogram_quantile` rend côté Prometheus.
- **Origine** : task-209 (/sonar, 1 bug corrigé)
- **Occurrences** : 1

### python:S5713 — Pas de classe d'exception redondante dans un `except`
- **Règle** : `python:S5713`
- **Repos** : tous repos .NET (Python)
- **Consigne** : ne pas citer dans le même tuple `except` une exception et l'une
  de ses ancêtres. Le piège concret :
  `except (urllib.error.URLError, OSError, ...)` — `URLError` **dérive**
  d'`OSError`, donc la citer est un bruit qui laisse croire à deux cas traités.
  Écrire `except (OSError, json.JSONDecodeError, ValueError)`.
- **Origine** : task-209 (/sonar, 2 occurrences corrigées)
- **Occurrences** : 1

### python:S1481 — Variable inutilisée d'un dépaquetage : `_`
- **Règle** : `python:S1481`
- **Repos** : tous repos .NET (Python)
- **Consigne** : quand un helper de test rend un tuple dont on n'utilise qu'une
  partie, dépaqueter avec `_` : `_, _, telemetry = palier(key)` plutôt que
  `ctx, metrics, telemetry = ...`. La règle s'applique **aussi aux fichiers de
  test** — ils ne sont pas exclus de l'analyse (seulement de la couverture).
- **Origine** : task-209 (/sonar, 2 occurrences corrigées)
- **Occurrences** : 1

### python:S5332 / python:S5852 — Deux hotspots qu'on revoit, on ne « corrige » pas
- **Règle** : `python:S5332` (URL `http://`), `python:S5852` (regex à backtracking)
- **Repos** : tous repos .NET (Python)
- **Consigne** : ces deux règles ouvrent des **hotspots**, que le Quality Gate
  exige de revoir à 100 % (`new_security_hotspots_reviewed`) — donc ils bloquent
  tant qu'ils ne sont pas traités, mais leur traitement est souvent un
  **classement `SAFE` argumenté**, pas un changement de code :
  - `S5332` sur une URL `http://127.0.0.1:…` de **fixture de test** qui ne
    déclenche aucun appel réseau → `SAFE`, en disant pourquoi rien ne transite.
    Sur une URL réellement appelée : passer en HTTPS, sans discussion.
  - `S5852` sur un motif dont **l'entrée est produite par le harnais lui-même**
    (ex. `context.duration` du JSON k6) → `SAFE`, en nommant l'appelant et en
    montrant que l'entrée ne peut pas venir d'un tiers. Sur une entrée
    utilisateur : réécrire le motif.
  Un hotspot laissé `TO_REVIEW` bloque le Quality Gate — le silence n'est pas
  une option.
- **Origine** : task-209 (/sonar, 2 hotspots revus `SAFE`)
- **Occurrences** : 1

### python:S3776 — Complexité cognitive <= 15 (aussi en Python)
- **Règle** : `python:S3776`
- **Repos** : tous repos .NET (Python)
- **Consigne** : le plafond s'applique au Python comme au C# et au JS, et il n'y
  a **pas** de commande dédiée (`/sonar-s3776` est spécifique au C# d'`api-mail`)
  : ces findings se traitent dans le run `/sonar`. La forme qui déborde dans le
  moteur de rapport est toujours la même — une fonction qui enchaîne collecte,
  branches de repli et rendu. La découper en **un builder par section**
  retournant une liste de lignes, puis concaténer.
- **Origine** : task-209 (/sonar, 0 corrigée — 3 occurrences pré-existantes
  constatées et documentées, cf. le `## Sonar log` de la task)
- **Occurrences** : 0
