# conventions/csharp.md — Conventions de code C# apprises par la forge

> **Portée** : tous les repos .NET écrits par la forge (`api-mail` en
> premier lieu ; `client-blazor`, `sdk`, `host`, `interop-cda` par extension).
> **Lu par** : `/develop` (avant d'écrire du code C#).
> **Alimenté par** : `/sonar` (voir protocole).
> **Jamais édité à la main** sauf pour retirer une convention devenue fausse.
>
> ⚠️ **Ce fichier ne couvre que le C#.** L'analyse Sonar d'`api-mail` est
> multi-langage : le JavaScript **et le Python** du repo (harnais k6,
> `tests/loadtest-k6/` — scénarios en JS, moteur de rapport en Python) sont
> scannés par SonarJS / SonarPython et comptent dans le new code du Quality
> Gate. Avant d'écrire du **JS** dans un repo .NET, lire
> `conventions/javascript.md` ; avant d'écrire du **Python**,
> `conventions/python.md`.

## Protocole d'alimentation (/sonar)

À la fin d'un run (Mode A ou B), pour **chaque règle Sonar corrigée
manuellement** sur du code écrit par `/develop` (Phase 1 new-code en
priorité — c'est là que la forge se corrige elle-même ; les fixes Phase 2
sur du legacy antérieur à la forge ne comptent que si la règle est
susceptible de se reproduire dans du code neuf) :

1. Si une entrée existe pour cette règle → incrémenter **Occurrences**,
   ajouter la task à **Origine**.
2. Sinon → créer l'entrée avec le format ci-dessous, `Occurrences : 1`.
3. Une entrée existe dès la **première** correction sur du new code : la
   prévention est immédiate, pas de seuil.

`/develop` lit ce fichier avant d'écrire du code C# : chaque « Consigne »
est un pattern à appliquer d'emblée — un finding Sonar new-code récurrent
sur du code frais est un échec de lecture de ce fichier.

## Format d'entrée

```markdown
### {règle-sonar-ou-slug} — {titre court}
- **Règle** : {clé Sonar exacte (ex. csharpsquid:S1481), ou "convention projet"}
- **Repos** : {api-mail | tous .NET | ...}
- **Consigne** : {ce que /develop doit faire d'emblée}
- **Origine** : task-NNN (/sonar, N occurrences corrigées)
- **Occurrences** : {n}
```

---

## Conventions actives

### problemdetails-rfc7807 — Erreurs API via GlobalExceptionHandler uniquement
- **Règle** : convention projet (CLAUDE.md règle 12 — rappel préventif ici)
- **Repos** : api-mail (et tout futur service .NET)
- **Consigne** : jamais de `try/catch` boilerplate par action, jamais de
  `StatusCode(500, "...")` ni de string brute. Lever une exception métier
  typée (`NotFoundException` → 404, `ValidationException` → 400,
  `ConflictException` → 409, `UnavailableException` → 503) ; le
  `GlobalExceptionHandler` produit le `ProblemDetails`. Aucun détail
  technique ni donnée de santé dans le `detail` exposé.
- **Origine** : task-055 (gravée dans CLAUDE.md)
- **Occurrences** : n/a (préventif)

### html-sanitize-anglesharp — Assainir le HTML avec AngleSharp, pas Ganss
- **Règle** : convention projet (choix de dépendance)
- **Repos** : api-mail
- **Consigne** : tout assainissement HTML côté backend passe par une
  allowlist sur **AngleSharp 1.5** — jamais `HtmlSanitizer` (Ganss), qui
  épingle AngleSharp 0.17.x (incompatible) et traîne l'advisory NU1902.
  Cf. mémoire `reference_html_sanitizer_use_anglesharp`.
- **Origine** : gravée avant la création de ce fichier
- **Occurrences** : n/a (préventif)

### xUnit2032 — `Assert.IsType<T>(obj, exactMatch: false)`, pas `IsAssignableFrom`
- **Règle** : `xUnit2032`
- **Repos** : tous .NET (projets de tests xUnit)
- **Consigne** : pour asserter qu'un objet est d'un type **ou d'un sous-type**,
  écrire `Assert.IsType<T>(obj, exactMatch: false)` — jamais
  `Assert.IsAssignableFrom<T>(obj)`, dont le nommage est jugé ambigu par
  l'analyseur. Cas typique : une API qui renvoie une classe de base
  (`MimeKit` renvoie une sous-classe concrète de `MimePart`).
- **Origine** : task-195 (/sonar, 1 occurrence corrigée sur du new code)
- **Occurrences** : 1

### CA1822 — Membre de test sans état d'instance ⇒ `static`
- **Règle** : `external_roslyn:CA1822`
- **Repos** : tous .NET (surtout les projets de tests)
- **Consigne** : tout helper privé d'une classe de test qui n'accède à aucun champ
  d'instance doit être déclaré `static` d'emblée (fabriques `Arrange*`, builders de
  substituts, constructeurs de données). C'est le cas de la majorité des helpers de
  test : le réflexe par défaut est `private static`.
- **Origine** : task-195 (/sonar, 1 occurrence corrigée — comptée sur le new code
  par la période `PREVIOUS_VERSION`)
- **Occurrences** : 1

### S103 — Signature > 150 caractères ⇒ un paramètre par ligne
- **Règle** : `csharpsquid:S103`
- **Repos** : tous .NET
- **Consigne** : ajouter un paramètre à une signature déjà longue la fait
  franchir la limite de 150 caractères — cas typique quand on propage une
  nouvelle dimension (identité, tenant, corrélation) à travers une interface et
  ses implémentations. **Dès qu'une signature dépasse ~120 caractères, la passer
  d'emblée en un paramètre par ligne** (interface *et* implémentations *et*
  fabriques de test), plutôt que d'attendre le finding. Vérification rapide avant
  commit :
  `awk 'length($0)>150 {print FILENAME":"NR}' {fichiers-modifiés}`
- **Origine** : task-175 (/sonar, 4 occurrences — 3 implémentations de
  `IMailEnrichmentNotifier` + 1 fabrique de test) ; task-176 (/sonar, 1
  occurrence — **récidive sur du code frais** : un message de log interpolé
  dépassait 150 caractères. L'entrée existait déjà : appliquer le contrôle `awk`
  **avant** le commit, pas après le finding Sonar)
- **Occurrences** : 5

### S125 — Un commentaire `//` ne finit JAMAIS par `;`
- **Règle** : `csharpsquid:S125` (sections de code commenté)
- **Repos** : tous .NET
- **Consigne** : documenter le contrat d'un **membre d'interface** dans un bloc
  de commentaires `//` multi-ligne se fait signaler comme « code commenté » dès
  que le texte cite des identifiants (`(folderPath, uid)`, `MailContent`,
  `GetMailAsync`) et ponctue ses puces par des `;` — l'heuristique n'y voit plus
  de la prose. **Écrire d'emblée un commentaire de documentation XML**
  (`<summary>` / `<remarks>` / `<returns>`, puces en `<list type="bullet">`).
  Ce n'est pas un contournement : c'est la forme attendue à cet endroit, elle
  est visible à l'appel (IntelliSense) et elle est référençable par
  `<see cref>` depuis l'implémentation.

  **Le déclencheur mécanique, isolé par task-271 : la ponctuation en fin de
  ligne.** Le finding n'exige ni interface ni liste à puces — il suffit qu'une
  ligne de commentaire `//` **se termine par `;`** pour que l'heuristique la
  prenne pour une instruction. Le cas de task-271 était de la prose ordinaire
  au fil du texte :

  ```csharp
  // is a scope that cannot be narrowed. The label does not shrink the hold;
  // it makes the two populations addressable.
  ```

  Remplacer le `;` par une virgule ou un tiret suffit — le sens ne change pas.
  **Contrôle avant commit** (coût nul, à passer sur le diff) :

  ```bash
  git diff --cached -U0 -- '*.cs' | grep -nE "^\+\s*//.*;\s*$"
  ```

  Toute sortie non vide est un S125 à venir.
- **Origine** : task-222 (/sonar, 1 occurrence sur du new code) ; **récidive
  task-271** (1 occurrence, prose au fil du texte — d'où la généralisation
  ci-dessus, la consigne d'origine ne couvrait que les blocs d'interface)
- **Occurrences** : 2

### no-sync-io-response-body — Jamais d'IO synchrone sur Response.Body
- **Règle** : apparentée `csharpsquid:S6966` (méthodes async disponibles)
  + contrainte Kestrel `AllowSynchronousIO=false`
- **Repos** : api-mail
- **Consigne** : `ZipArchive.Dispose()` (et tout writer qui flush en
  synchrone) est interdit directement sur `Response.Body` : bufferiser via
  `FileBufferingWriteStream` puis drainer en async (`DrainBufferAsync`).
  Un test controller sur `MemoryStream` ne détecte PAS ce bug — exiger un
  vrai test d'intégration endpoint. Cf. mémoire
  `reference_ziparchive_kestrel_sync_io`.
- **Origine** : gravée avant la création de ce fichier
- **Occurrences** : n/a (préventif)
